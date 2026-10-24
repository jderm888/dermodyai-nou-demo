import json
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

import main
import sam_client
import usaspending_client as usa
from sam_client import MISSING_SAM_KEY_MESSAGE
from scheduler import main as scheduler_main
from scheduler import run_daily

from tests.samples import SAM_ROW, USA_ROW, JsonResponse

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
WORKFLOW = REPO / ".github" / "workflows" / "bd-daily-research.yml"


def _patch_sources(monkeypatch, *, sam_calls, usa_calls):
    def fake_get(url, params):
        sam_calls.append((url, dict(params)))
        return JsonResponse({"opportunitiesData": [SAM_ROW]})

    def fake_post(url, payload):
        usa_calls.append((url, payload))
        if "spending_by_award" in url:
            return JsonResponse({"results": [USA_ROW]})
        if "spending_by_category" in url:
            return JsonResponse({"results": [{"name": "Department of the Air Force", "amount": 1000}]})
        raise AssertionError(url)

    monkeypatch.setattr(sam_client, "_http_get", fake_get)
    monkeypatch.setattr(usa, "_http_post", fake_post)


def test_daily_run_with_mocked_sources_and_model(tmp_path, monkeypatch):
    monkeypatch.setenv("SAM_GOV_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-not-a-real-model-key")
    sam_calls = []
    usa_calls = []
    _patch_sources(monkeypatch, sam_calls=sam_calls, usa_calls=usa_calls)

    def fake_complete(system, user):
        assert "1-10" not in system
        assert "1-10" not in user
        assert "NOU" not in user
        return json.dumps(
            [
                {
                    "id": "AWARD-EXAMPLE-1",
                    "pursuit_score": 4,
                    "rationale": "Profile agencies overlap this award.",
                    "key_factors": ["agency overlap"],
                },
                {
                    "id": "NOTICE-EXAMPLE-1",
                    "pursuit_score": 10,
                    "rationale": "Incumbent is Initech LLC on award ZZ999999.",
                    "key_factors": [],
                },
            ]
        )

    monkeypatch.setattr("agent.complete_json", fake_complete)
    summary = run_daily(output_dir=tmp_path, days_back=2, today=date(2026, 10, 24))

    assert summary["schedule_enabled"] is False
    assert summary["example_data"] is True
    assert summary["sam_status"] == "ok"
    assert summary["record_count"] == 2
    assert sam_calls
    assert all(params["api_key"] == "test-key" for _url, params in sam_calls)
    assert any("spending_by_award" in url for url, _payload in usa_calls)
    assert any(url.endswith("/search/spending_by_category/awarding_subagency/") for url, _payload in usa_calls)

    scores = json.loads(Path(summary["scores_path"]).read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in scores}
    assert by_id["AWARD-EXAMPLE-1"]["pursuit_score"] == 4
    assert by_id["AWARD-EXAMPLE-1"]["scoring_method"] == "llm"
    assert by_id["AWARD-EXAMPLE-1"]["recipient"] == "Example Recipient LLC"
    assert by_id["NOTICE-EXAMPLE-1"]["pursuit_score"] != 10
    assert 1 <= by_id["NOTICE-EXAMPLE-1"]["pursuit_score"] <= 5
    assert "Initech" not in by_id["NOTICE-EXAMPLE-1"]["rationale"]
    assert all(1 <= item["pursuit_score"] <= 5 for item in scores)

    brief = Path(summary["brief_path"]).read_text(encoding="utf-8")
    assert "4/5" in brief
    assert "AWARD-EXAMPLE-1" in brief
    assert "NOTICE-EXAMPLE-1" in brief
    assert "Example Recipient LLC" in brief
    assert "(source: USASpending.gov AWARD-EXAMPLE-1)" in brief
    assert "not identified in the source record — not inferred" in brief
    assert "Initech" not in brief
    assert "ZZ999999" not in brief
    assert "$125,000" in brief
    assert "$1,000" in brief
    assert "test-key" not in brief
    assert "test-not-a-real-model-key" not in brief


def test_daily_run_without_sam_key_skips_sam_and_still_writes_a_brief(tmp_path, monkeypatch):
    def boom(*_args, **_kwargs):
        raise AssertionError("SAM.gov was called without an API key")

    monkeypatch.setattr(sam_client, "_http_get", boom)
    usa_calls = []

    def fake_post(url, payload):
        usa_calls.append(url)
        if "spending_by_award" in url:
            return JsonResponse({"results": [USA_ROW]})
        return JsonResponse({"results": []})

    monkeypatch.setattr(usa, "_http_post", fake_post)
    summary = run_daily(output_dir=tmp_path, days_back=2, today=date(2026, 10, 24))
    assert summary["sam_status"] == "not_configured"
    assert summary["sam_message"] == MISSING_SAM_KEY_MESSAGE
    assert usa_calls
    brief = Path(summary["brief_path"]).read_text(encoding="utf-8")
    assert "SAM.gov API key is not set" in brief
    assert "AWARD-EXAMPLE-1" in brief
    scores = json.loads(Path(summary["scores_path"]).read_text(encoding="utf-8"))
    assert scores[0]["scoring_method"] == "rules"
    assert 1 <= scores[0]["pursuit_score"] <= 5


def test_scheduler_cli_refuses_archived_profile(tmp_path, capsys):
    archived = ROOT / "profiles" / "archived" / "nou_systems.yaml"
    code = scheduler_main(["--profile", str(archived), "--output-dir", str(tmp_path)])
    assert code == 2
    assert "archived" in capsys.readouterr().err.lower()
    assert list(tmp_path.iterdir()) == []


def test_workflow_is_manual_and_does_not_schedule():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch" in text
    assert "bd-research-agent" in text
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert not stripped.startswith("schedule:")
        assert "cron:" not in stripped
        assert "deploy" not in stripped.lower() or "does not deploy" in stripped.lower()


def test_api_missing_sam_key_returns_usaspending_results(monkeypatch):
    monkeypatch.setattr(sam_client, "_http_get", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("called")))

    def fake_post(url, _payload):
        if "spending_by_award" in url:
            return JsonResponse({"results": [USA_ROW]})
        return JsonResponse({"results": []})

    monkeypatch.setattr(usa, "_http_post", fake_post)
    client = TestClient(main.app)
    response = client.post("/api/research", json={"days_back": 30, "limit": 5, "focus_areas": ["range_software"]})
    assert response.status_code == 200
    body = response.json()
    assert body["sam_status"] == "not_configured"
    assert "SAM.gov API key is not set" in body["sam_message"]
    assert any(note.startswith("ANTHROPIC_API_KEY is not set") for note in body["notices"])
    assert not any("ANTHROPIC_API_KEY is not set" in error for error in body["errors"])
    assert body["profile"]["example_data"] is True
    assert body["scoring_scale"]["min"] == 1
    assert body["scoring_scale"]["max"] == 5
    assert body["scored"]
    assert all(1 <= item["pursuit_score"] <= 5 for item in body["scored"])
    assert "NOU" not in response.text


def test_api_empty_result_is_not_an_error(monkeypatch):
    monkeypatch.setattr(usa, "_http_post", lambda *_args, **_kwargs: JsonResponse({"results": []}))
    client = TestClient(main.app)
    response = client.post("/api/research", json={"limit": 5, "days_back": 7})
    assert response.status_code == 200
    body = response.json()
    assert body["scored"] == []
    assert body["raw_count"] == 0
    assert "SAM.gov API key is not set" in body["sam_message"]


def test_api_upstream_failure_is_a_502(monkeypatch):
    def fake_post(*_args, **_kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr(usa, "_http_post", fake_post)
    client = TestClient(main.app)
    response = client.post("/api/research", json={"limit": 5})
    assert response.status_code == 502
    assert "USASpending" in response.json()["detail"]


def test_brief_endpoint_drops_an_out_of_range_score_and_handles_empty():
    client = TestClient(main.app)
    empty = client.post(
        "/api/brief",
        json={
            "scored": [],
            "sam_message": "SAM.gov API key is not set.",
            "usaspending_message": "USASpending.gov returned 0 award records.",
            "profile_name": "Northwind Range Systems (EXAMPLE)",
            "example_data": True,
            "market_context": "No aggregate spending rows were returned by USASpending.gov for this query. No market totals were estimated.",
        },
    )
    assert empty.status_code == 200
    assert "No solicitation or award records were returned" in empty.text
    assert "[DONE]" in empty.text

    rejected = client.post(
        "/api/brief",
        json={
            "scored": [
                {
                    "id": "ZZ999999",
                    "title": "Invented",
                    "pursuit_score": 10,
                    "source": "SAM.gov",
                    "recipient": "Initech LLC",
                    "amount": 1,
                }
            ],
            "profile_name": "Northwind Range Systems (EXAMPLE)",
            "example_data": True,
            "sam_message": "ok",
            "usaspending_message": "ok",
        },
    )
    assert "outside 1-5" in rejected.text
    assert "No solicitation or award records were returned" in rejected.text
    assert "Initech" not in rejected.text
