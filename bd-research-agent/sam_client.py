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

    # SAM.gov's "ncode" parameter accepts only ONE NAICS code at a time;
    # a comma-separated list silently returns zero records. Query each code
    # separately and merge, deduping by noticeId, up to the overall limit.
    merged: list[dict] = []
    seen: set = set()

    with httpx.Client(timeout=TIMEOUT) as client:
        for code in naics_codes:
            if len(merged) >= limit:
                break

            # Parameter names per the SAM.gov Get Opportunities v2 API
            params = {
                "api_key": api_key,
                "ncode": code,
                "status": "active",
                "limit": limit,
                "offset": 0,
                "postedFrom": posted_from,
                "postedTo": posted_to,
            }
            if set_aside_codes:
                params["typeOfSetAside"] = ",".join(set_aside_codes)

            resp = client.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            for o in (data.get("opportunitiesData") or []):
                nid = o.get("noticeId")
                if nid in seen:
                    continue
                seen.add(nid)
                merged.append(o)
                if len(merged) >= limit:
                    break

    return {"opportunitiesData": merged, "totalRecords": len(merged)}


def normalize_opportunities(raw: dict) -> list[dict]:
    """Normalize SAM.gov results into a flat list of opportunity dicts."""
    opps = raw.get("opportunitiesData") or []
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
                "award_amount": o.get("estimatedTotalValue") or (o.get("award") or {}).get("amount", 0),
                # SAM returns a link to the description, not the text itself
                "description_url": o.get("description") or "",
                "active": o.get("active", ""),
                "url": f"https://sam.gov/opp/{o.get('noticeId', '')}/view",
            }
        )
    return normalized
