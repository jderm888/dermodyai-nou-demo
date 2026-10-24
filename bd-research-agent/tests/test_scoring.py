import json
from datetime import date

from agent import build_score_prompt, rule_score_record, score_opportunities
from profile import load_default_profile
from rubric import RUBRIC, coerce_score, priority_for_score, rubric_prompt_block
from signals import derive_signals

from tests.samples import SAM_ROW, USA_ROW
from sam_client import normalize_opportunities
from usaspending_client import normalize_awards


def _award():
    return normalize_awards({"results": [USA_ROW]})[0]


def _notice():
    return normalize_opportunities({"opportunitiesData": [SAM_ROW]})[0]


def test_coerce_score_accepts_only_one_to_five():
    assert coerce_score(4) == 4
    assert coerce_score(4.0) == 4
    assert coerce_score("5") == 5
    for bad in (0, 6, 8, 10, "6", "1-10", 3.5, None, True):
        try:
            coerce_score(bad)
        except ValueError as exc:
            assert "outside 1-5" in str(exc)
        else:
            raise AssertionError(f"{bad!r} should be invalid")


def test_priority_follows_the_same_bands():
    assert priority_for_score(5) == "High"
    assert priority_for_score(4) == "Medium"
    assert priority_for_score(3) == "Low"
    assert priority_for_score(2) == "Monitor"
    assert priority_for_score(1) == "Monitor"


def test_prompt_uses_the_shared_rubric_and_the_example_profile():
    prompt = build_score_prompt(load_default_profile(), [_award()])
    assert rubric_prompt_block() in prompt
    assert RUBRIC[5] in prompt
    assert "1, 2, 3, 4, and 5" in prompt
    assert "1-10" not in prompt
    assert "NOU" not in prompt
    assert "Northwind" in prompt
    assert "FICTIONAL" in prompt


def test_model_score_outside_scale_is_not_published():
    profile = load_default_profile()
    record = _notice()

    def complete(_system, _user):
        return json.dumps(
            [
                {
                    "id": record["id"],
                    "pursuit_score": 8,
                    "title": "HALLUCINATED TITLE",
                    "rationale": "Incumbent is Initech LLC on award ZZ999999.",
                    "key_factors": ["invented"],
                }
            ]
        )

    outcome = score_opportunities([record], profile, complete_fn=complete, today=date(2026, 10, 24))
    assert outcome.items[0]["pursuit_score"] != 8
    assert 1 <= outcome.items[0]["pursuit_score"] <= 5
    assert outcome.items[0]["title"] == "Telemetry support services"
    assert outcome.items[0]["scoring_method"] == "rules"
    assert "Initech" not in outcome.items[0]["rationale"]
    assert any("outside 1-5" in error for error in outcome.errors)


def test_valid_model_score_keeps_source_facts():
    profile = load_default_profile()
    record = _award()

    def complete(_system, user):
        assert "1-10" not in user
        return json.dumps(
            [
                {
                    "id": "NOT-A-REAL-9",
                    "pursuit_score": 5,
                    "rationale": "This record was not retrieved.",
                    "key_factors": [],
                },
                {
                    "id": record["id"],
                    "pursuit_score": "4",
                    "title": "HALLUCINATED TITLE",
                    "estimated_value_m": 3,
                    "rationale": "The source title overlaps the contractor profile.",
                    "key_factors": ["profile overlap"],
                },
            ]
        )

    outcome = score_opportunities([record], profile, complete_fn=complete, today=date(2026, 10, 24))
    assert len(outcome.items) == 1
    item = outcome.items[0]
    assert item["id"] == "AWARD-EXAMPLE-1"
    assert item["pursuit_score"] == 4
    assert item["priority"] == "Medium"
    assert item["rubric"] == RUBRIC[4]
    assert item["title"] == record["title"]
    assert item["amount"] == 125000
    assert item["recipient"] == "Example Recipient LLC"
    assert item["scoring_method"] == "llm"
    assert any("unknown id" in error for error in outcome.errors)
    labels = item["flag_labels"]
    assert "Recompete window" in labels
    assert "Incumbent on record" in labels


def test_missing_model_key_uses_rules_on_the_same_scale(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    outcome = score_opportunities([_award()], load_default_profile(), today=date(2026, 10, 24))
    assert outcome.method == "rules"
    assert any("ANTHROPIC_API_KEY" in error for error in outcome.errors)
    assert 1 <= outcome.items[0]["pursuit_score"] <= 5
    assert "/5" in outcome.items[0]["rationale"]


def test_rules_score_counts_profile_overlap():
    score, rationale, factors = rule_score_record(_notice(), load_default_profile())
    assert score == 5  # base 1 + NAICS + agency + keyword + set-aside
    assert score <= 5
    assert factors
    assert "1-10" not in rationale


def test_signals_do_not_invent_an_incumbent():
    notice = _notice()
    assert notice["recipient"] == ""
    assert derive_signals(notice, today=date(2026, 10, 24)) == []

    far = dict(_award())
    far["end_date"] = "2029-01-01"
    far["recipient"] = ""
    labels = [item["flag"] for item in derive_signals(far, today=date(2026, 10, 24))]
    assert labels == []


def test_empty_input_scores_nothing():
    outcome = score_opportunities([], load_default_profile())
    assert outcome.items == []
    assert outcome.method == "none"
