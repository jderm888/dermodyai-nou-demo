"""Recompete and incumbent flags computed only from fields on a source record."""

from __future__ import annotations

from datetime import date

from records import parse_date

# Eighteen months. A longer horizon is tracking, not a near-term recompete.
RECOMPETE_WINDOW_DAYS = 548
RECENTLY_ENDED_DAYS = 180


def derive_signals(record: dict, today: date | None = None) -> list[dict]:
    """Return flags that can be pointed at a field on this record.

    Solicitation rows do not get an incumbent flag unless the source payload
    included an awardee name. Nothing is inferred from the title or the description.
    """
    today = today or date.today()
    signals: list[dict] = []
    record_id = record.get("id") or ""
    source = record.get("source") or ""
    record_type = record.get("record_type") or ""

    end = parse_date(record.get("end_date"))
    if record_type == "award" and end is not None:
        days = (end - today).days
        if 0 <= days <= RECOMPETE_WINDOW_DAYS:
            signals.append(
                {
                    "flag": "Recompete window",
                    "detail": (
                        f"Source end date {end.isoformat()} is {days} days away "
                        f"(within {RECOMPETE_WINDOW_DAYS} days)."
                    ),
                    "source_id": record_id,
                    "source": source,
                    "field": "End Date",
                }
            )
        elif -RECENTLY_ENDED_DAYS <= days < 0:
            signals.append(
                {
                    "flag": "Recently ended",
                    "detail": f"Source end date {end.isoformat()} was {abs(days)} days ago.",
                    "source_id": record_id,
                    "source": source,
                    "field": "End Date",
                }
            )

    recipient = (record.get("recipient") or "").strip()
    if recipient:
        signals.append(
            {
                "flag": "Incumbent on record",
                "detail": f"{source} names recipient {recipient} on {record_id}.",
                "source_id": record_id,
                "source": source,
                "field": "Recipient Name" if record_type == "award" else "award.awardee.name",
            }
        )
    return signals
