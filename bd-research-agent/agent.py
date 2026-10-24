"""Score source records from 1 to 5.

Facts (amounts, recipients, award numbers, dates) are copied from the source
record. The model may only return an id, a 1–5 score, a rationale, and factors.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from brief import claim_violations
from profile import ContractorProfile
from rubric import RUBRIC, InvalidScore, coerce_score, priority_for_score, rubric_prompt_block
from signals import derive_signals

MODEL = "claude-sonnet-4-6"
MAX_SCORED = 30

SCORE_SYSTEM = """You are a BD analyst scoring contract records for fit with one contractor profile.
Use only the records and the profile in the user message. Do not invent award numbers, dollar amounts, incumbents, or records.
Respond with a JSON array only — no markdown fences."""


def build_score_prompt(profile: ContractorProfile, records: list[dict]) -> str:
    payload = [_prompt_record(record) for record in records[:MAX_SCORED]]
    return f"""Evaluate these source records for the contractor profile.

CONTRACTOR PROFILE:
{profile.to_prompt()}

{rubric_prompt_block()}

SOURCE RECORDS (cite these ids exactly; do not add records):
{json.dumps(payload, indent=2, default=str)}

Return a JSON array. Each element must be:
{{
  "id": "the id field copied from one source record",
  "pursuit_score": 1,
  "rationale": "1-2 sentences on profile fit only",
  "key_factors": ["up to 3 short factors drawn from the profile and that record"]
}}

Do not include dollar amounts, award numbers, or incumbent names in the rationale or key factors.
Do not estimate a value. Do not add flags. Pursuit_score must be an integer from 1 to 5.
Return ONLY the JSON array."""


def _prompt_record(record: dict) -> dict:
    return {
        "id": record.get("id"),
        "source": record.get("source"),
        "record_type": record.get("record_type"),
        "title": record.get("title") or "",
        "agency": record.get("agency") or "",
        "sub_agency": record.get("sub_agency") or "",
        "naics_code": record.get("naics_code") or "",
        "set_aside": record.get("set_aside") or "",
        "description": (record.get("description") or "")[:500],
        "deadline": record.get("deadline") or "",
        "end_date": record.get("end_date") or "",
        "recipient": record.get("recipient") or "",
        "amount": record.get("amount"),
        "award_number": record.get("award_number") or "",
    }


def complete_json(system: str, user: str) -> str:
    """Call Claude. Imported lazily so tests and missing-key runs can import this module."""
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


def parse_model_scores(raw: str) -> list:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if isinstance(data, dict):
        for key in ("scores", "items", "opportunities", "results"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            raise ValueError("model JSON was not a list")
    if not isinstance(data, list):
        raise ValueError("model JSON was not a list")
    return data


def _index_records(records: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for record in records:
        indexed.setdefault(record["id"], record)
        for alias in record.get("aliases") or []:
            if alias:
                indexed.setdefault(alias, record)
    return indexed


def _allowed_ids(records: list[dict]) -> set[str]:
    allowed: set[str] = set()
    for record in records:
        if record.get("id"):
            allowed.add(str(record["id"]))
        for alias in record.get("aliases") or []:
            if alias:
                allowed.add(str(alias))
        if record.get("award_number"):
            allowed.add(str(record["award_number"]))
    return allowed


def rule_score_record(record: dict, profile: ContractorProfile) -> tuple[int, str, list[str]]:
    """Same 1–5 bands as the model rubric, using only profile overlap that is visible on the record."""
    matches: list[str] = []
    naics = str(record.get("naics_code") or "")
    if naics and naics in set(profile.all_naics()):
        matches.append(f"NAICS {naics} is on the contractor profile")
    agency_text = f"{record.get('agency') or ''} {record.get('sub_agency') or ''}".lower()
    # SAM.gov often abbreviates "Department" as "DEPT". Expand it before matching.
    agency_text = re.sub(r"\bdept\b", "department", agency_text)
    for agency in profile.agencies:
        if agency and agency.lower() in agency_text:
            matches.append(f"agency text matches profile agency {agency}")
            break
    blob = f"{record.get('title') or ''} {record.get('description') or ''}".lower()
    for keyword in profile.keywords:
        if keyword and keyword.lower() in blob:
            matches.append(f"keyword {keyword!r} appears in the source title or description")
            break
    set_aside = (record.get("set_aside") or "").lower()
    for code in profile.set_asides:
        if code and code.lower() in set_aside:
            matches.append(f"set-aside text matches profile set-aside {code}")
            break
    score = min(5, 1 + len(matches))
    if matches:
        rationale = f"Score {score}/5. Profile checks that matched: {', '.join(matches)}."
    else:
        rationale = (
            f"Score {score}/5. None of the profile checks "
            "(NAICS, agency, keyword, set-aside) matched this record."
        )
    return score, rationale, matches[:3]


def assemble_item(
    record: dict,
    score: int,
    rationale: str,
    factors: list[str],
    method: str,
    today=None,
) -> dict:
    signals = derive_signals(record, today=today)
    amount = record.get("amount")
    return {
        "id": record["id"],
        "title": record.get("title") or record["id"],
        "pursuit_score": score,
        "priority": priority_for_score(score),
        "rubric": RUBRIC[score],
        "rationale": rationale,
        "key_factors": factors,
        "scoring_method": method,
        "source": record.get("source") or "",
        "record_type": record.get("record_type") or "",
        "url": record.get("url") or "",
        "agency": record.get("agency") or "",
        "sub_agency": record.get("sub_agency") or "",
        "naics": record.get("naics_code") or "",
        "set_aside": record.get("set_aside") or "",
        "amount": amount,
        "deadline": record.get("deadline") or "",
        "end_date": record.get("end_date") or "",
        "recipient": record.get("recipient") or "",
        "award_number": record.get("award_number") or "",
        "description_url": record.get("description_url") or "",
        "flags": signals,
        "flag_labels": [signal["flag"] for signal in signals],
    }


@dataclass
class ScoringOutcome:
    items: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    method: str = "none"


def score_opportunities(
    records: list[dict],
    profile: ContractorProfile,
    complete_fn=None,
    today=None,
) -> ScoringOutcome:
    """Score records. Invalid model scores are dropped and replaced with the rules rubric."""
    if not records:
        return ScoringOutcome(items=[], errors=[], method="none")

    working = list(records)
    errors: list[str] = []
    if len(working) > MAX_SCORED:
        errors.append(f"Only the first {MAX_SCORED} records were scored.")
        working = working[:MAX_SCORED]

    indexed = _index_records(working)
    allowed_ids = _allowed_ids(working)
    allowed_recipients = {record["recipient"] for record in working if record.get("recipient")}
    model_scores: dict[str, tuple[int, str, list[str]]] = {}
    use_rules_only = False

    if complete_fn is None and not os.getenv("ANTHROPIC_API_KEY"):
        use_rules_only = True
        errors.append(
            "ANTHROPIC_API_KEY is not set. Scores use the 1-5 rules rubric instead of the language model."
        )
    else:
        fn = complete_fn or complete_json
        try:
            parsed = parse_model_scores(fn(SCORE_SYSTEM, build_score_prompt(profile, working)))
        except Exception as exc:
            use_rules_only = True
            parsed = []
            errors.append(
                f"Language model scoring failed ({type(exc).__name__}). "
                "Scores use the 1-5 rules rubric instead."
            )
        if not use_rules_only:
            for entry in parsed:
                if not isinstance(entry, dict):
                    errors.append("Ignored a non-object score entry.")
                    continue
                raw_id = str(entry.get("id") or "").strip()
                record = indexed.get(raw_id)
                if record is None:
                    errors.append(f"Ignored model score for unknown id {raw_id!r}.")
                    continue
                try:
                    score = coerce_score(entry.get("pursuit_score"))
                except InvalidScore as exc:
                    errors.append(f"Record {record['id']}: {exc}. Rules score applied.")
                    continue
                rationale = str(entry.get("rationale") or "").strip()
                raw_factors = entry.get("key_factors") or []
                if not isinstance(raw_factors, list):
                    raw_factors = []
                factors = [str(item).strip() for item in raw_factors if str(item).strip()]
                violations = claim_violations(
                    " ".join([rationale, *factors]),
                    allowed_ids=allowed_ids,
                    allowed_recipients=allowed_recipients,
                )
                if violations:
                    errors.append(
                        f"Record {record['id']}: model rationale omitted ({'; '.join(violations)})."
                    )
                    rationale = (
                        "Rationale omitted because it cited data that is not in the source records."
                    )
                    factors = []
                # First accepted score for a record wins. Facts still come from the record.
                model_scores.setdefault(record["id"], (score, rationale, factors))

    items = []
    methods: set[str] = set()
    for record in working:
        if record["id"] in model_scores:
            score, rationale, factors = model_scores[record["id"]]
            method = "llm"
        else:
            score, rationale, factors = rule_score_record(record, profile)
            method = "rules"
            if not use_rules_only and not any(record["id"] in error for error in errors):
                errors.append(f"Record {record['id']} was not scored by the model. Rules score applied.")
        methods.add(method)
        items.append(assemble_item(record, score, rationale, factors, method, today=today))

    items.sort(key=lambda item: item["pursuit_score"], reverse=True)
    if methods == {"llm"}:
        method_name = "llm"
    elif methods == {"rules"}:
        method_name = "rules"
    elif not methods:
        method_name = "none"
    else:
        method_name = "mixed"
    return ScoringOutcome(items=items, errors=errors, method=method_name)
