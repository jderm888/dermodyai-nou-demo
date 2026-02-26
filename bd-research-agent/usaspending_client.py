"""
USASpending.gov API client — no API key required.
Fetches recent DoD contract awards by NAICS code.
"""

import httpx
from datetime import datetime, timedelta
from typing import Optional


BASE_URL = "https://api.usaspending.gov/api/v2"
TIMEOUT = 30.0


def fetch_recent_awards(
    naics_codes: list[str],
    days_back: int = 180,
    limit: int = 25,
    agency_name: str = "Department of Defense",
) -> dict:
    """
    Fetch recent DoD contract awards for given NAICS codes.
    Returns raw API response dict.
    """
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days_back)

    payload = {
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],  # Contracts only
            "naics_codes": naics_codes,
            "time_period": [
                {
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
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
        ],
        "sort": "Award Amount",
        "order": "desc",
        "limit": limit,
        "page": 1,
    }

    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(f"{BASE_URL}/search/spending_by_award/", json=payload)
        resp.raise_for_status()
        return resp.json()


def fetch_agency_spending_by_naics(naics_codes: list[str], limit: int = 10) -> dict:
    """
    Fetch aggregate spending by sub-agency for given NAICS codes (last 2 fiscal years).
    Useful for market sizing.
    """
    payload = {
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],
            "naics_codes": naics_codes,
            "agencies": [
                {"type": "awarding", "tier": "toptier", "name": "Department of Defense"}
            ],
        },
        "category": "awarding_subagency",
        "subaward": False,
        "page": 1,
        "limit": limit,
        "order": "desc",
        "sort": "aggregated_amount",
    }

    with httpx.Client(timeout=TIMEOUT) as client:
        resp = client.post(f"{BASE_URL}/search/spending_by_category/", json=payload)
        resp.raise_for_status()
        return resp.json()


def normalize_awards(raw: dict) -> list[dict]:
    """Normalize USASpending results into a flat list of opportunity dicts."""
    results = raw.get("results", [])
    normalized = []
    for r in results:
        normalized.append(
            {
                "source": "USASpending.gov",
                "type": "award",
                "award_id": r.get("Award ID", ""),
                "recipient": r.get("Recipient Name", "Unknown"),
                "description": r.get("Description", ""),
                "amount": r.get("Award Amount", 0),
                "start_date": r.get("Start Date", ""),
                "end_date": r.get("End Date", ""),
                "agency": r.get("Awarding Agency", ""),
                "sub_agency": r.get("Awarding Sub Agency", ""),
                "naics_code": r.get("NAICS Code", ""),
                "naics_description": r.get("NAICS Description", ""),
                "award_type": r.get("Award Type", ""),
                "state": r.get("Place of Performance State Code", ""),
            }
        )
    return normalized
