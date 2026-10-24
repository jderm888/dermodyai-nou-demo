"""USASpending.gov API client. No API key is required."""

from __future__ import annotations

from datetime import date, timedelta

import httpx

from records import clean_text, format_money, parse_amount, usaspending_award_url

BASE_URL = "https://api.usaspending.gov/api/v2"
TIMEOUT = 30.0
DEFAULT_AGENCY = "Department of Defense"


def _http_post(url: str, payload: dict) -> httpx.Response:
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response


def fiscal_window(today: date | None = None) -> tuple[date, date, str]:
    """Current fiscal year plus the previous one. Federal FY starts October 1."""
    today = today or date.today()
    fy_start_year = today.year if today.month >= 10 else today.year - 1
    start = date(fy_start_year - 1, 10, 1)
    label = f"{start.isoformat()} through {today.isoformat()} (current and previous fiscal years)"
    return start, today, label


def fetch_recent_awards(
    naics_codes: list[str],
    days_back: int = 180,
    limit: int = 25,
    agency_name: str = DEFAULT_AGENCY,
    today: date | None = None,
) -> dict:
    """Fetch recent contract awards for the given NAICS codes. Returns the raw API payload."""
    end = today or date.today()
    start = end - timedelta(days=max(1, int(days_back)))
    payload = {
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],
            "naics_codes": naics_codes,
            "time_period": [
                {
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                }
            ],
            "agencies": [
                {"type": "awarding", "tier": "toptier", "name": agency_name}
            ],
        },
        "fields": [
            "Award ID",
            "Recipient Name",
            "Description",
            "Award Amount",
            "Start Date",
            "End Date",
            "Awarding Agency",
            "Awarding Sub Agency",
            "NAICS Code",
            "NAICS Description",
            "Award Type",
            "Place of Performance State Code",
            "generated_internal_id",
        ],
        "sort": "Award Amount",
        "order": "desc",
        "limit": limit,
        "page": 1,
    }
    return _http_post(f"{BASE_URL}/search/spending_by_award/", payload).json()


def fetch_agency_spending_by_naics(
    naics_codes: list[str],
    limit: int = 10,
    today: date | None = None,
) -> dict:
    """Aggregate DoD contract spend by awarding sub-agency.

    The category is part of the path. A POST to /spending_by_category/ with no
    category suffix returns HTTP 404.
    """
    start, end, _label = fiscal_window(today)
    payload = {
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],
            "naics_codes": naics_codes,
            "time_period": [
                {"start_date": start.isoformat(), "end_date": end.isoformat()}
            ],
            "agencies": [
                {"type": "awarding", "tier": "toptier", "name": DEFAULT_AGENCY}
            ],
        },
        "category": "awarding_subagency",
        "spending_level": "awards",
        "page": 1,
        "limit": limit,
        "order": "desc",
        "sort": "amount",
    }
    url = f"{BASE_URL}/search/spending_by_category/awarding_subagency/"
    return _http_post(url, payload).json()


def normalize_awards(raw: dict) -> list[dict]:
    """Map spending_by_award results. Rows without an Award ID are dropped."""
    normalized = []
    for row in raw.get("results") or []:
        if not isinstance(row, dict):
            continue
        award_id = clean_text(row.get("Award ID"))
        if not award_id:
            continue
        recipient = clean_text(row.get("Recipient Name"))
        if recipient.lower() == "unknown":
            recipient = ""
        naics = row.get("NAICS Code")
        normalized.append(
            {
                "source": "USASpending.gov",
                "record_type": "award",
                "id": award_id,
                "aliases": [award_id],
                "title": clean_text(row.get("Description")) or award_id,
                "agency": clean_text(row.get("Awarding Agency")),
                "sub_agency": clean_text(row.get("Awarding Sub Agency")),
                "naics_code": "" if naics is None else clean_text(naics),
                "naics_description": clean_text(row.get("NAICS Description")),
                "set_aside": "",
                "description": clean_text(row.get("Description")),
                "description_url": "",
                "posted_date": clean_text(row.get("Start Date")),
                "deadline": "",
                "end_date": clean_text(row.get("End Date")),
                "amount": parse_amount(row.get("Award Amount")),
                "recipient": recipient,
                "award_number": award_id,
                "state": clean_text(row.get("Place of Performance State Code")),
                "url": usaspending_award_url(clean_text(row.get("generated_internal_id"))),
            }
        )
    return normalized


def format_market_context(raw: dict, window_label: str) -> str:
    """Render only rows returned by USASpending. Missing amounts stay missing."""
    results = raw.get("results") or []
    if not results:
        return (
            "No aggregate spending rows were returned by USASpending.gov for this query. "
            "No market totals were estimated."
        )
    lines = [
        "USASpending.gov awarding-subagency contract totals "
        f"({window_label}). Each figure is the amount field on that source row."
    ]
    for row in results:
        if not isinstance(row, dict):
            continue
        name = clean_text(row.get("name")) or "Unknown agency"
        amount = row.get("amount")
        if amount is None:
            amount = row.get("aggregated_amount")
        if amount is None:
            lines.append(f"- {name}: amount not present on the source row (source: USASpending.gov spending_by_category)")
        else:
            lines.append(
                f"- {name}: {format_money(parse_amount(amount))} "
                "(source: USASpending.gov spending_by_category, awarding_subagency)"
            )
    return "\n".join(lines)
