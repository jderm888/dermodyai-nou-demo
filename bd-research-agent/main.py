"""
BD Research Agent — FastAPI server
Run with: uvicorn main:app --reload --port 8001
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from markupsafe import Markup
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from brief import build_brief, chunk_text
from profile import ArchivedProfileError, ProfileError, list_demo_profiles, load_default_profile, resolve_profile
from research import run_research
from rubric import RUBRIC, InvalidScore, coerce_score, priority_for_score, rubric_pairs

app = FastAPI(title="BD Research Agent", version="0.2.0")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
templates.env.filters["tojson"] = lambda value: Markup(json.dumps(value))


class ResearchRequest(BaseModel):
    focus_areas: list[str] = Field(default_factory=list)
    sam_api_key: str | None = None
    days_back: int = Field(default=180, ge=1, le=730)
    limit: int = Field(default=25, ge=1, le=50)
    set_aside_filter: list[str] | None = None
    profile_id: str | None = None
    profile: dict | None = None


def _profile_or_http(profile_id: str | None, inline: dict | None):
    try:
        return resolve_profile(profile_id=profile_id, inline=inline)
    except ArchivedProfileError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProfileError as exc:
        status = 422 if inline else 404
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        profile = load_default_profile()
    except (ProfileError, ArchivedProfileError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "focus_areas": profile.focus_area_map(),
            "profile": profile.public_dict(),
            "rubric": rubric_pairs(),
        },
    )


@app.get("/api/profile")
async def current_profile():
    try:
        profile = load_default_profile()
    except (ProfileError, ArchivedProfileError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return profile.public_dict()


@app.get("/api/profiles")
async def profiles():
    return {"profiles": list_demo_profiles()}


@app.get("/api/rubric")
async def rubric():
    return {"min": 1, "max": 5, "levels": rubric_pairs()}


@app.get("/api/naics-profiles")
async def naics_profiles():
    """Focus areas on the active profile. Kept for the original route name."""
    try:
        profile = load_default_profile()
    except (ProfileError, ArchivedProfileError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return profile.focus_area_map()


@app.post("/api/research")
async def research(req: ResearchRequest):
    """Fetch USASpending awards and, when a key is configured, SAM.gov solicitations. Score 1–5."""
    profile = _profile_or_http(req.profile_id, req.profile)
    result = run_research(
        profile,
        sam_api_key=req.sam_api_key,
        days_back=req.days_back,
        limit=req.limit,
        set_aside_filter=req.set_aside_filter,
        focus_areas=req.focus_areas,
    )
    if (
        result["raw_count"] == 0
        and result["usaspending_status"] == "error"
        and result["sam_status"] != "ok"
    ):
        raise HTTPException(
            status_code=502,
            detail=" ".join(
                part
                for part in (result["usaspending_message"], result["sam_message"])
                if part
            ),
        )
    # The markdown is also available from /api/brief. Omit the duplicate body here
    # so the scored JSON stays the response the page renders.
    public = dict(result)
    public.pop("brief_markdown", None)
    return public


def _clean_scored(items: list) -> tuple[list[dict], list[str]]:
    clean = []
    notes = []
    if not isinstance(items, list):
        return [], ["Scored payload was not a list."]
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            notes.append("Dropped a scored item with no source id.")
            continue
        try:
            score = coerce_score(item.get("pursuit_score"))
        except InvalidScore as exc:
            notes.append(f"Dropped {item.get('id')}: {exc}.")
            continue
        copied = dict(item)
        copied["pursuit_score"] = score
        copied["priority"] = priority_for_score(score)
        copied["rubric"] = RUBRIC[score]
        clean.append(copied)
    return clean, notes


@app.post("/api/brief")
async def brief(request: Request):
    """Stream a brief rendered from scored records. Does not call the model."""
    body = await request.json()
    scored, notes = _clean_scored(body.get("scored") or [])
    profile_name = body.get("profile_name") or "Contractor profile"
    example_data = bool(body.get("example_data"))
    disclaimer = body.get("disclaimer") or ""
    try:
        active = load_default_profile()
        if not body.get("profile_name"):
            profile_name = active.name
            example_data = active.example_data
            disclaimer = active.disclaimer
    except (ProfileError, ArchivedProfileError):
        pass
    market_text = body.get("market_context") or (
        "No aggregate spending rows were returned by USASpending.gov for this query. "
        "No market totals were estimated."
    )
    sam_message = body.get("sam_message") or "SAM.gov status was not included with this brief request."
    usa_message = body.get("usaspending_message") or "USASpending.gov status was not included with this brief request."
    if notes:
        sam_message = sam_message + " " + " ".join(notes)
    text = build_brief(
        profile_name=profile_name,
        example_data=example_data,
        disclaimer=disclaimer,
        scored=scored,
        market_text=market_text,
        sam_message=sam_message,
        usaspending_message=usa_message,
    )

    async def event_stream():
        try:
            for chunk in chunk_text(text):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
