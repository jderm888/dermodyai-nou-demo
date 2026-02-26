"""
BD Research Agent — FastAPI server
Run with: uvicorn main:app --reload --port 8001
"""

import json
import os
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import agent
import usaspending_client as usa
import sam_client as sam
from naics_config import NAICS_PROFILES, ALL_NAICS_CODES

app = FastAPI(title="BD Research Agent", version="0.1.0")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
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
    return templates.TemplateResponse("index.html", {
        "request": request,
        "focus_areas": NAICS_PROFILES,
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
    selected_codes = list(set(selected_codes)) or ALL_NAICS_CODES

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
        try:
            raw_opps = sam.fetch_opportunities(
                naics_codes=selected_codes,
                api_key=req.sam_api_key.strip(),
                limit=req.limit,
                set_aside_codes=req.set_aside_filter,
            )
            opps = sam.normalize_opportunities(raw_opps)
            all_items.extend(opps)
            sam_status = f"ok ({len(opps)} opportunities)"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                sam_status = "invalid_key"
                errors.append("SAM.gov: Invalid or expired API key.")
            else:
                sam_status = "error"
                errors.append(f"SAM.gov HTTP {e.response.status_code}")
        except Exception as e:
            sam_status = "error"
            errors.append(f"SAM.gov error: {e}")

    if not all_items and errors:
        raise HTTPException(status_code=502, detail="; ".join(errors))

    # --- Score with Claude ---
    scored = []
    if all_items:
        try:
            scored = agent.score_opportunities(all_items)
        except Exception as e:
            errors.append(f"Scoring error: {e}")
            scored = []

    return {
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
