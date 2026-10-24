"""Pursuit-score rubric shared by the prompt, the parser, and the brief."""

from __future__ import annotations

SCORE_MIN = 1
SCORE_MAX = 5

# Same sentences are interpolated into the model prompt and printed on the brief.
RUBRIC: dict[int, str] = {
    5: "Strong fit — NAICS, agency, and keywords align, and the record is actionable now.",
    4: "Good fit — most profile criteria align; worth capture effort.",
    3: "Partial fit — some overlap; teaming or monitoring may be appropriate.",
    2: "Weak fit — limited overlap with the contractor profile.",
    1: "Poor fit — outside the profile or missing the core criteria.",
}

PRIORITY_FOR_SCORE: dict[int, str] = {
    5: "High",
    4: "Medium",
    3: "Low",
    2: "Monitor",
    1: "Monitor",
}


class InvalidScore(ValueError):
    """A model score was missing or outside the 1–5 scale."""


def priority_for_score(score: int) -> str:
    return PRIORITY_FOR_SCORE[score]


def coerce_score(value) -> int:
    """Accept only an integer from 1 to 5. Do not rescale a 1–10 value."""
    if isinstance(value, bool) or value is None:
        raise InvalidScore(f"pursuit_score {value!r} is outside 1-5")
    if isinstance(value, str):
        text = value.strip()
        if text not in {"1", "2", "3", "4", "5"}:
            raise InvalidScore(f"pursuit_score {value!r} is outside 1-5")
        return int(text)
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not value.is_integer():
            raise InvalidScore(f"pursuit_score {value!r} is outside 1-5")
        score = int(value)
        if score < SCORE_MIN or score > SCORE_MAX:
            raise InvalidScore(f"pursuit_score {score} is outside 1-5")
        return score
    raise InvalidScore(f"pursuit_score {value!r} is outside 1-5")


def rubric_prompt_block() -> str:
    lines = ["Score each record from 1 to 5 using this rubric:"]
    for score in range(SCORE_MAX, SCORE_MIN - 1, -1):
        lines.append(f"  {score} — {RUBRIC[score]}")
    lines.append(
        "The only allowed scores are 1, 2, 3, 4, and 5. "
        "Scores of 6 or higher are invalid and will be discarded."
    )
    lines.append(
        "Priority is derived from the score and is not yours to choose: "
        "5 High, 4 Medium, 3 Low, 2 Monitor, 1 Monitor."
    )
    return "\n".join(lines)


def rubric_pairs() -> list[dict[str, object]]:
    """Ordered 5-to-1 rubric for JSON and the demo page."""
    return [{"score": score, "text": RUBRIC[score], "priority": PRIORITY_FOR_SCORE[score]} for score in range(5, 0, -1)]
