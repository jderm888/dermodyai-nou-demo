"""Render a BD intelligence brief from validated scores and source fields.

The model does not write award numbers, amounts, or incumbents into this document.
Those lines are copied from the scored item, which was copied from the source record.
"""

from __future__ import annotations

import re
from datetime import date

from records import format_money
from rubric import PRIORITY_FOR_SCORE, RUBRIC, SCORE_MAX, SCORE_MIN

_ID_TOKEN = re.compile(r"\b(?=[A-Z0-9-]*\d)[A-Z][A-Z0-9-]{5,}\b")
_INCUMBENT = re.compile(r"(?i)\b(?:incumbent|awardee|awarded to|recipient)\b[^.\n]{0,120}")
_MISSING_INCUMBENT = (
    "not identified",
    "not inferred",
    "not present",
    "not disclosed",
    "no incumbent",
    "no recipient",
)


def _norm_id(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def claim_violations(text: str, *, allowed_ids: set[str], allowed_recipients: set[str]) -> list[str]:
    """Flag model prose that introduces an award id, a dollar amount, or an incumbent."""
    if not text or not text.strip():
        return []
    violations: list[str] = []
    allowed_norm = {_norm_id(item) for item in allowed_ids if item}
    for match in _ID_TOKEN.finditer(text.upper()):
        token = match.group(0)
        norm = _norm_id(token)
        if norm in allowed_norm:
            continue
        if any(len(existing) >= 6 and (norm in existing or existing in norm) for existing in allowed_norm):
            continue
        violations.append(f"unsupported identifier {token}")
    if "$" in text:
        violations.append("dollar amount in model prose")
    for match in _INCUMBENT.finditer(text):
        window = match.group(0).strip()
        lowered = window.lower()
        if any(phrase in lowered for phrase in _MISSING_INCUMBENT):
            continue
        if any(name and name.lower() in lowered for name in allowed_recipients):
            continue
        violations.append(f"unsupported incumbent claim: {window}")
    return violations


def _cite(item: dict) -> str:
    return f"(source: {item.get('source') or 'unknown source'} {item.get('id') or 'unknown id'})"


def _present(value: str, item: dict, field: str) -> str:
    if value:
        return f"{value} {_cite(item)}, field {field}"
    return f"not present in the source record {_cite(item)}"


def _item_section(item: dict) -> list[str]:
    score = item["pursuit_score"]
    lines = [
        f"### {item.get('title') or item['id']} — {score}/{SCORE_MAX} {item.get('priority')}",
        f"Rubric: {item.get('rubric') or RUBRIC[score]}",
        "",
        (
            f"- Record: {item.get('source')} `{item.get('id')}` "
            f"({item.get('record_type') or 'record'}) {_cite(item)}"
        ),
    ]
    if item.get("url"):
        lines.append(f"- Link: {item['url']} {_cite(item)}")
    lines.append(f"- Agency: {_present(item.get('agency') or '', item, 'agency')}")
    if item.get("sub_agency"):
        lines.append(f"- Sub-agency: {item['sub_agency']} {_cite(item)}")
    lines.append(f"- NAICS: {_present(item.get('naics') or '', item, 'NAICS')}")
    if item.get("amount") is None:
        lines.append(f"- Value: not disclosed in the source record {_cite(item)}")
    else:
        lines.append(f"- Value: {format_money(item.get('amount'))} {_cite(item)}")
    lines.append(f"- Set-aside: {_present(item.get('set_aside') or '', item, 'set-aside')}")
    if item.get("record_type") == "award":
        lines.append(f"- End date: {_present(item.get('end_date') or '', item, 'End Date')}")
    else:
        lines.append(f"- Response deadline: {_present(item.get('deadline') or '', item, 'response deadline')}")
    recipient = (item.get("recipient") or "").strip()
    if recipient:
        field = "Recipient Name" if item.get("record_type") == "award" else "award.awardee.name"
        lines.append(f"- Incumbent: {recipient} {_cite(item)}, field {field}")
    else:
        lines.append(
            "- Incumbent: not identified in the source record — not inferred "
            f"{_cite(item)}"
        )
    award_number = (item.get("award_number") or "").strip()
    # On USASpending rows the award number is the Award ID, already cited above.
    if item.get("record_type") == "solicitation":
        if award_number:
            lines.append(f"- Award number: {award_number} {_cite(item)}, field award.number")
        else:
            lines.append(f"- Award number: not present in the source record {_cite(item)}")
    if item.get("description_url"):
        lines.append(
            "- Description link (API key is not included): "
            f"{item['description_url']} {_cite(item)}"
        )
    flags = item.get("flags") or []
    if flags:
        for flag in flags:
            lines.append(
                f"- Signal: {flag.get('flag')} — {flag.get('detail')} {_cite(item)}"
            )
    else:
        lines.append(f"- Signals: none. No recompete date or recipient was on the source record {_cite(item)}")
    lines.append(f"- Rationale: {item.get('rationale') or 'No rationale was produced.'}")
    factors = item.get("key_factors") or []
    if factors:
        lines.append("- Factors: " + "; ".join(str(factor) for factor in factors))
    lines.append(f"- Scoring method: {item.get('scoring_method') or 'unspecified'}")
    lines.append("")
    return lines


def _actions(items: list[dict]) -> list[str]:
    actionable = [item for item in items if item.get("priority") in {"High", "Medium"}]
    if not actionable:
        return [
            "No High or Medium records were scored. Widen the date window or edit the contractor profile, then run again."
        ]
    actions = []
    for item in actionable[:5]:
        when = item.get("deadline") or item.get("end_date")
        timing = (
            f"Date on the source record: {when}."
            if when
            else "No response deadline or end date is present on the source record."
        )
        actions.append(
            f"Review {item.get('source')} record {item.get('id')} ({item.get('title')}) before acting. {timing}"
        )
    return actions


def _summary(items: list[dict], sam_count: int, usa_count: int) -> str:
    high = sum(1 for item in items if item.get("pursuit_score") == 5)
    medium = sum(1 for item in items if item.get("pursuit_score") == 4)
    return (
        f"Retrieved {len(items)} source records ({sam_count} from SAM.gov, {usa_count} from USASpending.gov). "
        f"{high} scored 5/{SCORE_MAX} (High) and {medium} scored 4/{SCORE_MAX} (Medium) on the 1–5 rubric. "
        "Incumbent names and award amounts appear only when those fields were present on a source record."
    )


def build_brief(
    *,
    profile_name: str,
    example_data: bool,
    disclaimer: str = "",
    scored: list[dict],
    market_text: str,
    sam_message: str,
    usaspending_message: str,
    generated_on: date | None = None,
) -> str:
    generated_on = generated_on or date.today()
    lines = [
        "# BD Intelligence Brief",
        "",
        f"**Contractor profile:** {profile_name}",
        f"**Generated:** {generated_on.isoformat()}",
        f"**Score scale:** {SCORE_MIN}–{SCORE_MAX}",
        "",
    ]
    if example_data:
        lines.extend(
            [
                "> EXAMPLE DATA. This brief was scored against a fictional contractor profile.",
                "",
            ]
        )
    if disclaimer.strip():
        lines.extend([disclaimer.strip(), ""])

    lines.extend(["## Score rubric", ""])
    lines.append("Scores are integers from 1 to 5. Priority is taken from the score.")
    lines.append("")
    for score in range(SCORE_MAX, SCORE_MIN - 1, -1):
        lines.append(f"- **{score}** ({PRIORITY_FOR_SCORE[score]}) — {RUBRIC[score]}")
    lines.append("")
    lines.extend(["## Source status", "", f"- SAM.gov: {sam_message}", f"- USASpending.gov: {usaspending_message}", ""])

    if not scored:
        lines.extend(
            [
                "## Executive summary",
                "",
                "No solicitation or award records were returned for this profile and date window.",
                "No opportunities were scored. Incumbents and award numbers were not inferred from an empty result.",
                "",
                "## Top pursuit opportunities",
                "",
                "None.",
                "",
                "## Market landscape",
                "",
                market_text,
                "",
                "## Recommended BD actions",
                "",
                "1. Confirm the contractor profile NAICS codes and the date window, then run the search again.",
                "",
                "## Watch list",
                "",
                "None.",
                "",
                "Every figure in this brief is copied from a cited source record or from the run status above. "
                "Nothing was estimated.",
                "",
            ]
        )
        return "\n".join(lines)

    sam_count = sum(1 for item in scored if item.get("source") == "SAM.gov")
    usa_count = sum(1 for item in scored if item.get("source") == "USASpending.gov")
    lines.extend(["## Executive summary", "", _summary(scored, sam_count, usa_count), ""])

    top = [item for item in scored if item.get("priority") in {"High", "Medium"}]
    watch = [item for item in scored if item.get("priority") in {"Low", "Monitor"}]
    lines.extend(["## Top pursuit opportunities", ""])
    if top:
        for item in top:
            lines.extend(_item_section(item))
    else:
        lines.extend(["No records scored 4 or 5.", ""])

    lines.extend(["## Market landscape", "", market_text, ""])
    lines.extend(["## Recommended BD actions", ""])
    for index, action in enumerate(_actions(scored), start=1):
        lines.append(f"{index}. {action}")
    lines.append("")
    lines.extend(["## Watch list", ""])
    if watch:
        lines.append("Lower scores stay on the watch list. Facts below are still copied from the source record.")
        lines.append("")
        for item in watch:
            lines.extend(_item_section(item))
    else:
        lines.extend(["None.", ""])
    lines.append(
        "Every figure above is copied from the cited source record. "
        "No award numbers or incumbents were added."
    )
    lines.append("")
    return "\n".join(lines)


def chunk_text(text: str, size: int = 500):
    for index in range(0, len(text), size):
        yield text[index : index + size]
