from datetime import date

import httpx

import sam_client
from sam_client import MISSING_SAM_KEY_MESSAGE, fetch_opportunities

from tests.samples import JsonResponse, SAM_ROW


def test_missing_key_does_not_call_sam(monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("SAM.gov was called without an API key")

    monkeypatch.setattr(sam_client, "_http_get", boom)
    result = fetch_opportunities(naics_codes=["541511"], api_key=None, today=date(2026, 10, 24))
    assert result.status == "not_configured"
    assert result.records == []
    assert result.message == MISSING_SAM_KEY_MESSAGE
    assert "SAM.gov API key is not set" in result.message


def test_request_key_overrides_env_and_is_sent_on_every_request(monkeypatch):
    monkeypatch.setenv("SAM_GOV_API_KEY", "env-key")
    calls = []

    def fake_get(url, params):
        calls.append((url, dict(params)))
        return JsonResponse({"opportunitiesData": [SAM_ROW]})

    monkeypatch.setattr(sam_client, "_http_get", fake_get)
    result = fetch_opportunities(
        naics_codes=["541511", "541512"],
        api_key="request-key",
        limit=4,
        days_back=10,
        today=date(2026, 10, 24),
    )
    assert result.status == "ok"
    assert calls
    assert {params["ncode"] for _url, params in calls} == {"541511", "541512"}
    for _url, params in calls:
        assert params["api_key"] == "request-key"
        assert "naicsCode" not in params
        assert params["postedFrom"] == "10/14/2026"
        assert params["postedTo"] == "10/24/2026"
        assert params["ptype"] == sam_client.SOLICITATION_PTYPES
        assert "active" not in params
    assert "request-key" not in result.message
    assert result.records[0]["id"] == "NOTICE-EXAMPLE-1"
    assert result.records[0]["recipient"] == ""
    assert "api_key" not in result.records[0]["description_url"]


def test_env_key_is_used_when_the_request_omits_one(monkeypatch):
    monkeypatch.setenv("SAM_API_KEY", "alias-key")
    calls = []

    def fake_get(_url, params):
        calls.append(params["api_key"])
        return JsonResponse({"opportunitiesData": []})

    monkeypatch.setattr(sam_client, "_http_get", fake_get)
    result = fetch_opportunities(naics_codes=["541511"], api_key="  ", today=date(2026, 10, 24))
    assert calls == ["alias-key"]
    assert result.status == "ok"
    assert "alias-key" not in result.message


def test_invalid_key_is_a_clear_status(monkeypatch):
    request = httpx.Request("GET", "https://api.sam.gov/opportunities/v2/search")
    response = httpx.Response(403, request=request, text='{"message":"An invalid api_key was supplied"}')

    def fake_get(_url, params):
        raise httpx.HTTPStatusError("bad", request=request, response=response)

    monkeypatch.setattr(sam_client, "_http_get", fake_get)
    result = fetch_opportunities(naics_codes=["541511"], api_key="not-a-real-key", today=date(2026, 10, 24))
    assert result.status == "invalid_key"
    assert result.records == []
    assert "rejected the API key" in result.message
    assert "not-a-real-key" not in result.message


def test_normalize_copies_awardee_only_when_the_payload_has_one():
    raw = {
        "opportunitiesData": [
            {
                **SAM_ROW,
                "award": {
                    "number": "FA1234-26-C-0001",
                    "amount": "10000",
                    "awardee": {"name": "Example Recipient LLC"},
                },
            }
        ]
    }
    record = sam_client.normalize_opportunities(raw)[0]
    assert record["recipient"] == "Example Recipient LLC"
    assert record["award_number"] == "FA1234-26-C-0001"
    assert record["amount"] == 10000
