"""One research pass shared by the API and the daily entry point."""

from __future__ import annotations

from datetime import date

import usaspending_client as usa
import sam_client as sam
from agent import score_opportunities
from brief import build_brief
from profile import ContractorProfile
from rubric import rubric_pairs
from usaspending_client import fiscal_window

AWARD_SEARCH_NOTE = (
    "Award search uses the Department of Defense toptier on USASpending.gov. "
    "Profile agencies are used for scoring fit, not as a second award query."
)


def fetch_awards(*, naics_codes, days_back, limit, today=None):
    try:
        raw = usa.fetch_recent_awards(
            naics_codes=naics_codes,
            days_back=days_back,
            limit=limit,
            today=today,
        )
        records = usa.normalize_awards(raw)
        return (
            records,
            "ok",
            f"USASpending.gov returned {len(records)} award records. No API key is required. {AWARD_SEARCH_NOTE}",
        )
    except Exception as exc:
        return [], "error", f"USASpending.gov request failed ({type(exc).__name__}). No award totals were estimated."


def fetch_solicitations(*, naics_codes, api_key, limit, set_aside_codes, days_back, today=None):
    result = sam.fetch_opportunities(
        naics_codes=naics_codes,
        api_key=api_key,
        limit=limit,
        set_aside_codes=set_aside_codes,
        days_back=days_back,
        today=today,
    )
    return result.records, result.status, result.message


def fetch_market(*, naics_codes, today=None) -> str:
    _start, _end, label = fiscal_window(today)
    try:
        raw = usa.fetch_agency_spending_by_naics(naics_codes, limit=10, today=today)
        return usa.format_market_context(raw, label)
    except Exception:
        return (
            "USASpending.gov aggregate spending was not available for this run. "
            "No market totals were estimated."
        )


def run_research(
    profile: ContractorProfile,
    *,
    sam_api_key: str | None = None,
    days_back: int = 180,
    limit: int = 25,
    set_aside_filter: list[str] | None = None,
    focus_areas: list[str] | None = None,
    today: date | None = None,
    complete_fn=None,
) -> dict:
    today = today or date.today()
    naics_codes = profile.codes_for(focus_areas)
    awards, usa_status, usa_message = fetch_awards(
        naics_codes=naics_codes,
        days_back=days_back,
        limit=limit,
        today=today,
    )
    solicitations, sam_status, sam_message = fetch_solicitations(
        naics_codes=naics_codes,
        api_key=sam_api_key,
        limit=limit,
        set_aside_codes=set_aside_filter,
        days_back=days_back,
        today=today,
    )
    records = [*awards, *solicitations]
    market_text = fetch_market(naics_codes=naics_codes, today=today)
    outcome = score_opportunities(records, profile, complete_fn=complete_fn, today=today)
    brief = build_brief(
        profile_name=profile.name,
        example_data=profile.example_data,
        disclaimer=profile.disclaimer,
        scored=outcome.items,
        market_text=market_text,
        sam_message=sam_message,
        usaspending_message=usa_message,
        generated_on=today,
    )
    errors = []
    notices = []
    if usa_status == "error":
        errors.append(usa_message)
    if sam_status in {"error", "invalid_key"}:
        errors.append(sam_message)
    for message in outcome.errors:
        # A missing model key is an expected fallback, not a failed search.
        if message.startswith("ANTHROPIC_API_KEY is not set"):
            notices.append(message)
        else:
            errors.append(message)
    return {
        "scored": outcome.items,
        "raw_count": len(records),
        "naics_codes": naics_codes,
        "sam_status": sam_status,
        "sam_message": sam_message,
        "usaspending_status": usa_status,
        "usaspending_message": usa_message,
        "market_context": market_text,
        "errors": errors,
        "notices": notices,
        "scoring_method": outcome.method,
        "scoring_errors": outcome.errors,
        "scoring_scale": {"min": 1, "max": 5, "rubric": rubric_pairs()},
        "profile": {
            "id": profile.id,
            "name": profile.name,
            "example_data": profile.example_data,
            "disclaimer": profile.disclaimer,
        },
        "brief_markdown": brief,
        "focus_areas": profile.focus_area_map(),
    }
