"""
SAM.gov Opportunities API client.
Requires a free API key from https://sam.gov/profile (register → API keys).
If no key is configured, returns a helpful message instead of raising.
"""

import httpx
from typing import Optional

BASE_URL = "https://api.sam.gov/opportunities/v2/search"
TIMEOUT = 30.0


def fetch_opportunities(
    naics_codes: list[str],
    api_key: str,
    limit: int = 20,
    set_aside_codes: Optional[list[str]] = None,
    days_posted: int = 90,
) -> dict:
    """
    Fetch active solicitations from SAM.gov for given NAICS codes.
    Returns raw API response dict or raises on HTTP error.
    """
    from datetime import datetime, timedelta

    posted_from = (datetime.today() - timedelta(days=days_posted)).strftime("%m/%d/%Y")
    posted_to = datetime.today().strftime("%m/%d/%Y")

    params = {
        "api_key": api_key,
        "naicsCode": ",".join(naics_codes),
        "active": "true",
        "limit": limit,
        "offset": 0,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "sort": "-modifiedDate",
    }

    if set_aside_codes:
        params["typeOfSetAsideCode"] = ",".join(set_aside_codes)

    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.get(BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json()


def normalize_opportunities(raw: dict) -> list[dict]:
    """Normalize SAM.gov results into a flat list of opportunity dicts."""
    opps = raw.get("opportunitiesData", [])
    normalized = []
    for o in opps:
        normalized.append(
            {
                "source": "SAM.gov",
                "type": "solicitation",
                "notice_id": o.get("noticeId", ""),
                "title": o.get("title", ""),
                "sol_number": o.get("solicitationNumber", ""),
                "agency": o.get("organizationName", ""),
                "sub_agency": o.get("officeAddress", {}).get("name", "") if isinstance(o.get("officeAddress"), dict) else "",
                "posted_date": o.get("postedDate", ""),
                "response_deadline": o.get("responseDeadLine", ""),
                "naics_code": o.get("naicsCode", ""),
                "set_aside": o.get("typeOfSetAside", ""),
                "set_aside_description": o.get("typeOfSetAsideDescription", ""),
                "award_amount": o.get("estimatedTotalValue") or o.get("award", {}).get("amount", 0),
                "description": o.get("description", "")[:1000],
                "active": o.get("active", ""),
                "url": f"https://sam.gov/opp/{o.get('noticeId', '')}/view",
            }
        )
    return normalized
