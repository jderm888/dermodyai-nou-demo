"""Source-only reporting: no model calls, invented scores, or inferred pursuits."""
from datetime import date


def source_items(items):
    results = []
    for item in items:
        solicitation = item.get("type") == "solicitation"
        amount = item.get("award_amount") if solicitation else item.get("amount")
        try:
            amount_m = float(amount) / 1_000_000 if amount else None
        except (TypeError, ValueError):
            amount_m = None
        results.append({
            "id": item.get("notice_id") or item.get("award_id") or item.get("sol_number"),
            "title": item.get("title") or item.get("description") or item.get("award_id") or "Untitled record",
            "priority": "Unscored", "pursuit_score": None,
            "source": item.get("source"), "record_type": item.get("type"),
            "rationale": "Source record; no AI assessment. " + (
                "Notice type and response requirements need review." if solicitation else
                "Existing award; not an open solicitation. Recipient: " + str(item.get("recipient", "Unknown"))),
            "key_factors": [], "estimated_value_m": amount_m,
            "deadline": item.get("response_deadline") if solicitation else item.get("end_date"),
            "date_type": "Due" if solicitation else "Ends",
            "agency_short": item.get("sub_agency") or item.get("agency"),
            "naics": item.get("naics_code"), "set_aside": item.get("set_aside") or "Not provided",
            "flags": ["SAM notice" if solicitation else "Existing award"],
        })
    return results


def build_source_report(items, market_context, errors=()):
    notices = [i for i in items if i.get("record_type") == "solicitation"]
    awards = [i for i in items if i.get("record_type") == "award"]
    lines = ["## Source Report — No AI Analysis", f"Retrieved {date.today().isoformat()}. {len(notices)} SAM notices and {len(awards)} existing awards. No pursuit scores or strategic recommendations were generated.",
             "## SAM.gov Notices"]
    lines += [f"- {i['title']} | ID: {i['id']} | Response deadline: {i.get('deadline') or 'Not provided'}" for i in notices] or ["No SAM notices returned. Check source status and warnings."]
    lines += ["## Existing Awards"]
    lines += [f"- {i['title']} | ID: {i['id']} | Period-of-performance end: {i.get('deadline') or 'Not provided'}" for i in awards] or ["No awards returned."]
    lines += ["## Market Landscape", market_context,
              "Aggregate data covers the last 730 days and selected NAICS. This snapshot alone does not establish trends, competitor share, or new pursuits.",
              "## Review Before Acting", "Verify notice status, response dates, eligibility, and source records. Award end dates are not proposal deadlines; award amounts are not new opportunity values."]
    lines += [f"- {e}" for e in errors]
    return "\n\n".join(lines)
