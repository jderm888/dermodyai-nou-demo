"""Parsing helpers for source records. These functions do not call the network."""

from __future__ import annotations

from datetime import date, datetime


def parse_amount(value):
    """Return a float copied from a source field, or None when the field is empty."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("$", "").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def parse_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "")
    text = text.split("T")[0].split(" ")[0]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def format_money(amount) -> str:
    if amount is None:
        return "not disclosed in the source record"
    number = float(amount)
    if number.is_integer():
        return f"${number:,.0f}"
    return f"${number:,.2f}"


def usaspending_award_url(generated_internal_id: str | None) -> str:
    if not generated_internal_id:
        return ""
    return f"https://www.usaspending.gov/award/{generated_internal_id}"


def sam_notice_url(notice_id: str, ui_link: str | None = None) -> str:
    if ui_link:
        return str(ui_link)
    if not notice_id:
        return ""
    return f"https://sam.gov/opp/{notice_id}/view"


def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()
