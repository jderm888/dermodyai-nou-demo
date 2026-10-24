"""SAM.gov Get Opportunities API client.

The public API requires an api_key query parameter on every search.
The key is read from the request, then from SAM_GOV_API_KEY, then from SAM_API_KEY.
A missing key does not call the network.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from datetime import date, timedelta

import httpx

from records import clean_text, parse_amount, sam_notice_url

BASE_URL = "https://api.sam.gov/opportunities/v2/search"
TIMEOUT = 30.0
SAM_MAX_WINDOW_DAYS = 365
MAX_NAICS_QUERIES = 8
# Solicitation, combined synopsis, presolicitation, sources sought, special notice.
SOLICITATION_PTYPES = "o,k,p,r,s"

MISSING_SAM_KEY_MESSAGE = (
    "SAM.gov API key is not set. Set the SAM_GOV_API_KEY environment variable "
    "or pass sam_api_key with the request. The key is sent as the api_key query "
    "parameter on every SAM.gov search. Solicitation search was skipped; "
    "USASpending.gov does not need a key and was still queried."
)
INVALID_SAM_KEY_MESSAGE = (
    "SAM.gov rejected the API key. Check SAM_GOV_API_KEY or the sam_api_key "
    "passed with the request. Solicitation search was skipped."
)


@dataclass
class SamResult:
    status: str
    message: str
    records: list[dict] = field(default_factory=list)


def resolve_sam_api_key(request_key: str | None = None) -> str:
    """Per-request key wins. Otherwise the environment. Blank means unset."""
    if request_key and request_key.strip():
        return request_key.strip()
    for name in ("SAM_GOV_API_KEY", "SAM_API_KEY"):
        value = os.getenv(name, "")
        if value and value.strip():
            return value.strip()
    return ""


def _redact(text: str, api_key: str) -> str:
    if api_key and api_key in text:
        return text.replace(api_key, "[redacted]")
    return text


def _http_get(url: str, params: dict) -> httpx.Response:
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response


def _classify_http_error(exc: httpx.HTTPStatusError, api_key: str) -> tuple[str, str]:
    status_code = exc.response.status_code
    body = _redact(exc.response.text or "", api_key)
    lowered = body.lower()
    if status_code in (401, 403) or "invalid api_key" in lowered or "no api_key" in lowered:
        return "invalid_key", INVALID_SAM_KEY_MESSAGE
    if status_code == 404 and not body.strip():
        return (
            "error",
            "SAM.gov returned HTTP 404 with an empty body. An API key is required on every "
            "search; confirm SAM_GOV_API_KEY is a public key from the SAM.gov account page.",
        )
    snippet = body.strip().replace("\n", " ")[:180]
    detail = f" HTTP body: {snippet}" if snippet else ""
    return (
        "error",
        f"SAM.gov request failed with HTTP {status_code}.{detail} Solicitation search was skipped.",
    )


def _strip_description(value: str) -> tuple[str, str]:
    """SAM often returns a description URL. Never append the API key to it."""
    text = clean_text(value)
    if text.lower().startswith("http"):
        # Drop any key that a caller may have already appended.
        without_key = text.split("api_key=")[0].rstrip("?&")
        return "", without_key
    return text[:1000], ""


def normalize_opportunities(raw: dict) -> list[dict]:
    """Map SAM.gov opportunitiesData into source records. Missing fields stay empty."""
    opportunities = raw.get("opportunitiesData") or []
    normalized = []
    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            continue
        active = clean_text(opportunity.get("active"))
        if active and active.lower() not in {"yes", "true"}:
            continue
        notice_id = clean_text(opportunity.get("noticeId"))
        solicitation_number = clean_text(opportunity.get("solicitationNumber"))
        if not notice_id and not solicitation_number:
            continue
        award = opportunity.get("award") if isinstance(opportunity.get("award"), dict) else {}
        awardee = award.get("awardee") if isinstance(award.get("awardee"), dict) else {}
        description, description_url = _strip_description(opportunity.get("description") or "")
        record_id = notice_id or solicitation_number
        aliases = [value for value in dict.fromkeys([notice_id, solicitation_number]) if value]
        normalized.append(
            {
                "source": "SAM.gov",
                "record_type": "solicitation",
                "id": record_id,
                "aliases": aliases,
                "title": clean_text(opportunity.get("title")),
                "agency": clean_text(
                    opportunity.get("fullParentPathName")
                    or opportunity.get("department")
                    or opportunity.get("organizationName")
                ),
                "sub_agency": clean_text(opportunity.get("subTier") or opportunity.get("office")),
                "naics_code": clean_text(opportunity.get("naicsCode") or opportunity.get("ncode")),
                "set_aside": clean_text(
                    opportunity.get("typeOfSetAsideDescription")
                    or opportunity.get("setAside")
                    or opportunity.get("typeOfSetAside")
                ),
                "description": description,
                "description_url": description_url,
                "posted_date": clean_text(opportunity.get("postedDate")),
                "deadline": clean_text(opportunity.get("responseDeadLine") or opportunity.get("reponseDeadLine")),
                "end_date": "",
                "amount": parse_amount(award.get("amount")),
                "recipient": clean_text(awardee.get("name")),
                "award_number": clean_text(award.get("number")),
                "url": sam_notice_url(notice_id, opportunity.get("uiLink")),
            }
        )
    return normalized


def fetch_opportunities(
    naics_codes: list[str],
    api_key: str | None = None,
    limit: int = 20,
    set_aside_codes: list[str] | None = None,
    days_back: int = 90,
    today: date | None = None,
    ptype: str = SOLICITATION_PTYPES,
) -> SamResult:
    """Search solicitations. One request per NAICS code, because ncode is a single code."""
    key = resolve_sam_api_key(api_key)
    if not key:
        return SamResult(status="not_configured", message=MISSING_SAM_KEY_MESSAGE, records=[])

    today = today or date.today()
    window_days = max(1, int(days_back))
    capped = False
    if window_days > SAM_MAX_WINDOW_DAYS:
        window_days = SAM_MAX_WINDOW_DAYS
        capped = True
    posted_from = today - timedelta(days=window_days)
    codes = [clean_text(code) for code in naics_codes if clean_text(code)]
    if not codes:
        return SamResult(
            status="error",
            message="SAM.gov search needs at least one NAICS code from the contractor profile.",
            records=[],
        )
    truncated = False
    if len(codes) > MAX_NAICS_QUERIES:
        codes = codes[:MAX_NAICS_QUERIES]
        truncated = True

    per_code = max(1, min(1000, math.ceil(limit / len(codes))))
    set_aside = ""
    if set_aside_codes:
        set_aside = clean_text(set_aside_codes[0])

    records: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []
    invalid = False

    for code in codes:
        params = {
            "api_key": key,
            "ncode": code,
            "postedFrom": posted_from.strftime("%m/%d/%Y"),
            "postedTo": today.strftime("%m/%d/%Y"),
            "ptype": ptype,
            "limit": per_code,
            "offset": 0,
        }
        if set_aside:
            # The API accepts one set-aside code per request.
            params["typeOfSetAside"] = set_aside
        try:
            response = _http_get(BASE_URL, params)
            for record in normalize_opportunities(response.json()):
                if record["id"] in seen:
                    continue
                seen.add(record["id"])
                records.append(record)
        except httpx.HTTPStatusError as exc:
            status, message = _classify_http_error(exc, key)
            if status == "invalid_key":
                invalid = True
                errors.append(message)
                break
            errors.append(message)
        except Exception as exc:
            errors.append(
                f"SAM.gov request failed for NAICS {code}: {_redact(type(exc).__name__, key)}."
            )

    records = records[: max(1, limit)]
    notes: list[str] = []
    if capped:
        notes.append(
            f"SAM.gov postedFrom/postedTo was capped at {SAM_MAX_WINDOW_DAYS} days, which is the API maximum."
        )
    if truncated:
        notes.append(f"SAM.gov was queried for the first {MAX_NAICS_QUERIES} NAICS codes only.")
    if set_aside_codes and len([code for code in set_aside_codes if clean_text(code)]) > 1:
        notes.append(
            f"SAM.gov accepts one set-aside code per request. This run used {set_aside}."
        )

    if invalid and not records:
        return SamResult(status="invalid_key", message=" ".join([INVALID_SAM_KEY_MESSAGE, *notes]).strip(), records=[])
    if records:
        message = f"SAM.gov returned {len(records)} solicitation records."
        if errors:
            message += " Some NAICS queries failed: " + " ".join(errors)
        if notes:
            message += " " + " ".join(notes)
        return SamResult(status="ok", message=message.strip(), records=records)
    if errors:
        message = " ".join(errors + notes)
        status = "invalid_key" if invalid else "error"
        return SamResult(status=status, message=message.strip(), records=[])
    message = "SAM.gov returned 0 solicitation records."
    if notes:
        message += " " + " ".join(notes)
    return SamResult(status="ok", message=message.strip(), records=[])
