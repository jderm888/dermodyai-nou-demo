from datetime import date

import usaspending_client as usa
from usaspending_client import format_market_context, normalize_awards

from tests.samples import JsonResponse, USA_ROW


def test_award_normalize_keeps_only_source_fields():
    records = normalize_awards({"results": [USA_ROW, {"Description": "missing id"}]})
    assert len(records) == 1
    record = records[0]
    assert record["id"] == "AWARD-EXAMPLE-1"
    assert record["recipient"] == "Example Recipient LLC"
    assert record["amount"] == 125000
    assert record["url"] == "https://www.usaspending.gov/award/CONT_AWD_EXAMPLE"
    assert record["naics_code"] == "541511"


def test_blank_recipient_is_not_replaced_with_a_guess():
    row = dict(USA_ROW)
    row["Recipient Name"] = None
    row["Award Amount"] = None
    row["NAICS Code"] = None
    record = normalize_awards({"results": [row]})[0]
    assert record["recipient"] == ""
    assert record["amount"] is None
    assert record["naics_code"] == ""


def test_category_request_uses_the_category_path(monkeypatch):
    calls = []

    def fake_post(url, payload):
        calls.append((url, payload))
        return JsonResponse({"results": [{"name": "Department of the Air Force", "amount": 1000}]})

    monkeypatch.setattr(usa, "_http_post", fake_post)
    raw = usa.fetch_agency_spending_by_naics(["541511"], limit=2, today=date(2026, 10, 24))
    assert calls[0][0].endswith("/search/spending_by_category/awarding_subagency/")
    assert calls[0][1]["filters"]["time_period"][0]["start_date"] == "2025-10-01"
    text = format_market_context(raw, "2025-10-01 through 2026-10-24")
    assert "$1,000" in text
    assert "Department of the Air Force" in text
    assert "source: USASpending.gov spending_by_category" in text


def test_empty_market_payload_does_not_invent_totals():
    text = format_market_context({"results": []}, "window")
    assert "No aggregate spending rows" in text
    assert "No market totals were estimated" in text
    assert "$" not in text
