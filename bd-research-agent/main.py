"""
BD Research Agent — FastAPI server
Run with: uvicorn main:app --reload --port 8001
"""

import json
import os
from typing import Optional, Literal

from dotenv import load_dotenv
load_dotenv()  # loads ANTHROPIC_API_KEY (and any other vars) from .env

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import source_report
import agent
import usaspending_client as usa
import sam_client as sam
from naics_config import NAICS_PROFILES, ALL_NAICS_CODES, SAM_NAICS_CODES

app = FastAPI(title="BD Research Agent", version="0.1.0")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    analysis_mode: Literal["source", "claude"] = "source"
    focus_areas: list[str] = list(NAICS_PROFILES.keys())
    sam_api_key: Optional[str] = None
    days_back: int = 180
    limit: int = 25
    set_aside_filter: Optional[list[str]] = None  # e.g. ["SBA", "8A"]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {
        "focus_areas": NAICS_PROFILES,
        "company": agent.COMPANY,
    })


@app.get("/api/naics-profiles")
async def naics_profiles():
    return NAICS_PROFILES


@app.post("/api/research")
async def research(req: ResearchRequest):
    """
    Fetch opportunities from SAM.gov (optional) and USASpending.gov,
    then score them with Claude. Returns scored JSON.
    """
    # Collect NAICS codes for selected focus areas
    selected_codes = []
    for area in req.focus_areas:
        profile = NAICS_PROFILES.get(area)
        if profile:
            selected_codes.extend(profile["codes"])
    selected_codes = sorted(set(selected_codes))
    if not selected_codes:
        raise HTTPException(status_code=422, detail="Select at least one valid focus area.")

    all_items: list[dict] = []
    errors: list[str] = []

    # --- USASpending.gov (always) ---
    try:
        raw_awards = usa.fetch_recent_awards(
            naics_codes=selected_codes,
            days_back=req.days_back,
            limit=req.limit,
        )
        all_items.extend(usa.normalize_awards(raw_awards))
    except Exception as e:
        errors.append(f"USASpending.gov error: {e}")

    # --- SAM.gov (if key provided) ---
    sam_status = "not_configured"
    if req.sam_api_key and req.sam_api_key.strip():
        # Cap SAM lookups to the high-signal codes (SAM has a low daily request
        # limit and only accepts one NAICS per request). Respect the selected
        # focus areas; never substitute unrelated codes.
        sam_codes = [c for c in SAM_NAICS_CODES if c in selected_codes]
        try:
            if not sam_codes:
                errors.append("SAM.gov skipped: selected focus areas do not overlap the capped SAM NAICS list.")
            raw_opps = sam.fetch_opportunities(
                naics_codes=sam_codes,
                api_key=req.sam_api_key.strip(),
                limit=req.limit,
                set_aside_codes=req.set_aside_filter,
                days_posted=min(req.days_back, 364),
            )
            opps = sam.normalize_opportunities(raw_opps)
            all_items.extend(opps)
            sam_status = f"ok ({len(opps)} opportunities)" if sam_codes else "skipped (no matching capped NAICS)"
        except httpx.HTTPStatusError as e:
            code = e.response.status_code
            detail = "See SAM.gov account status for details."
            if code in (401, 403):
                sam_status = "invalid_key"
                errors.append(
                    "SAM.gov: API key or access rejected. Check your account and confirm the full key was copied."
                )
            elif code == 429:
                sam_status = "rate_limited"
                errors.append(
                    "SAM.gov: daily request limit reached for this key "
                    "Reset timing is controlled by SAM.gov; retry after the provider resets your quota."
                )
            else:
                sam_status = "error"
                errors.append(f"SAM.gov HTTP {code}: {detail}")
        except Exception as e:
            sam_status = "error"
            errors.append("SAM.gov request failed; source unavailable for this run.")

    if not all_items and any(not e.startswith("SAM.gov skipped:") for e in errors):
        raise HTTPException(status_code=502, detail="; ".join(errors))

    # --- Score with Claude ---
    scored = []
    if req.analysis_mode == "source":
        scored = source_report.source_items(all_items)
    elif all_items:
        try:
            scored = agent.score_opportunities(sorted(all_items, key=lambda i: i.get("type") != "solicitation"))
            if len(scored) < len(all_items):
                errors.append(f"Claude scored {len(scored)} of {len(all_items)} fetched records (30-record analysis cap; partial JSON may also reduce coverage).")
        except Exception as e:
            errors.append(f"Scoring error: {e}")
            scored = []

    return {
        "analysis_mode": req.analysis_mode,
        "scored": scored,
        "raw_count": len(all_items),
        "naics_codes": selected_codes,
        "sam_status": sam_status,
        "errors": errors,
    }


@app.post("/api/brief")
async def brief(request: Request):
    """
    Stream a BD Intelligence Brief given scored opportunities.
    Body: { "scored": [...], "focus_areas": [...] }
    """
    body = await request.json()
    scored = body.get("scored", [])
    focus_areas = body.get("focus_areas", list(NAICS_PROFILES.keys()))
    naics_codes = body.get("naics_codes", ALL_NAICS_CODES)

    # Fetch market context (agency spending breakdown)
    market_context = "Market data unavailable."
    try:
        raw_market = usa.fetch_agency_spending_by_naics(naics_codes, limit=10)
        market_context = agent.build_market_context(raw_market)
    except Exception:
        pass

    async def event_stream():
        if body.get("analysis_mode", "source") == "source":
            report = source_report.build_source_report(scored, market_context, body.get("errors", []))
            yield f"data: {json.dumps({'text': report})}\n\n"
            yield "data: [DONE]\n\n"
            return
        try:
            async for chunk in agent.stream_brief(scored, market_context, focus_areas):
                data = json.dumps({"text": chunk})
                yield f"data: {data}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
