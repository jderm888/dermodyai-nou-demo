from datetime import date

from brief import build_brief, claim_violations
from rubric import RUBRIC
from sam_client import normalize_opportunities
from usaspending_client import normalize_awards

from tests.samples import SAM_ROW, USA_ROW


def _scored_award():
    record = normalize_awards({"results": [USA_ROW]})[0]
    return {
        "id": record["id"],
        "title": record["title"],
        "pursuit_score": 4,
        "priority": "Medium",
        "rubric": RUBRIC[4],
        "rationale": "The record overlaps the profile on NAICS and agency.",
        "key_factors": ["NAICS on profile"],
        "scoring_method": "rules",
        "source": record["source"],
        "record_type": record["record_type"],
        "url": record["url"],
        "agency": record["agency"],
        "sub_agency": record["sub_agency"],
        "naics": record["naics_code"],
        "set_aside": "",
        "amount": record["amount"],
        "deadline": "",
        "end_date": record["end_date"],
        "recipient": record["recipient"],
        "award_number": record["award_number"],
        "description_url": "",
        "flags": [
            {
                "flag": "Recompete window",
                "detail": "Source end date 2027-03-01 is 128 days away (within 548 days).",
                "source_id": record["id"],
                "source": record["source"],
                "field": "End Date",
            },
            {
                "flag": "Incumbent on record",
                "detail": "USASpending.gov names recipient Example Recipient LLC on AWARD-EXAMPLE-1.",
                "source_id": record["id"],
                "source": record["source"],
                "field": "Recipient Name",
            },
        ],
        "flag_labels": ["Recompete window", "Incumbent on record"],
    }


def test_brief_cites_source_facts_and_the_rubric():
    text = build_brief(
        profile_name="Northwind Range Systems (EXAMPLE)",
        example_data=True,
        disclaimer="FICTIONAL contractor created for demonstrations.",
        scored=[_scored_award()],
        market_text=(
            "USASpending.gov awarding-subagency contract totals (window). "
            "Each figure is the amount field on that source row.\n"
            "- Department of the Air Force: $1,000 "
            "(source: USASpending.gov spending_by_category, awarding_subagency)"
        ),
        sam_message="SAM.gov API key is not set.",
        usaspending_message="USASpending.gov returned 1 award record.",
        generated_on=date(2026, 10, 24),
    )
    assert "4/5" in text
    assert RUBRIC[4] in text
    assert "AWARD-EXAMPLE-1" in text
    assert "Example Recipient LLC" in text
    assert "$125,000" in text
    assert "$1,000" in text
    assert "(source: USASpending.gov AWARD-EXAMPLE-1)" in text
    assert "https://www.usaspending.gov/award/CONT_AWD_EXAMPLE" in text
    assert "Initech" not in text
    assert "EXAMPLE DATA" in text


def test_solicitation_without_awardee_does_not_name_an_incumbent():
    record = normalize_opportunities({"opportunitiesData": [SAM_ROW]})[0]
    item = _scored_award()
    item.update(
        {
            "id": record["id"],
            "title": record["title"],
            "source": "SAM.gov",
            "record_type": "solicitation",
            "url": record["url"],
            "amount": None,
            "recipient": "",
            "award_number": "",
            "end_date": "",
            "deadline": record["deadline"],
            "flags": [],
            "flag_labels": [],
            "pursuit_score": 2,
            "priority": "Monitor",
            "rubric": RUBRIC[2],
        }
    )
    text = build_brief(
        profile_name="Northwind Range Systems (EXAMPLE)",
        example_data=True,
        scored=[item],
        market_text="No aggregate spending rows were returned by USASpending.gov for this query. No market totals were estimated.",
        sam_message="SAM.gov returned 1 solicitation record.",
        usaspending_message="USASpending.gov returned 0 award records.",
        generated_on=date(2026, 10, 24),
    )
    assert "not identified in the source record — not inferred" in text
    assert "not disclosed in the source record" in text
    assert "Award number: not present in the source record" in text
    assert "Example Recipient LLC" not in text


def test_empty_result_does_not_invent_records():
    text = build_brief(
        profile_name="Northwind Range Systems (EXAMPLE)",
        example_data=True,
        scored=[],
        market_text="No aggregate spending rows were returned by USASpending.gov for this query. No market totals were estimated.",
        sam_message="SAM.gov API key is not set. Solicitation search was skipped.",
        usaspending_message="USASpending.gov returned 0 award records.",
        generated_on=date(2026, 10, 24),
    )
    assert "No solicitation or award records were returned" in text
    assert "not inferred" in text
    assert "AWARD-" not in text
    assert "Incumbent:" not in text
    assert "$" not in text


def test_claim_checker_rejects_invented_awards_and_incumbents():
    allowed_ids = {"AWARD-EXAMPLE-1", "NOTICE-EXAMPLE-1"}
    allowed_recipients = {"Example Recipient LLC"}
    assert claim_violations(
        "Review the profile overlap.",
        allowed_ids=allowed_ids,
        allowed_recipients=allowed_recipients,
    ) == []
    invented = claim_violations(
        "Incumbent is Initech LLC on award ZZ999999 worth $4M.",
        allowed_ids=allowed_ids,
        allowed_recipients=allowed_recipients,
    )
    assert any("ZZ999999" in item for item in invented)
    assert any("Initech" in item for item in invented)
    assert any("dollar amount" in item for item in invented)
    cited = claim_violations(
        "Recipient Example Recipient LLC is already on AWARD-EXAMPLE-1.",
        allowed_ids=allowed_ids,
        allowed_recipients=allowed_recipients,
    )
    assert cited == []
