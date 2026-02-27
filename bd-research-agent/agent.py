"""
BD Research Agent — Claude-powered analysis layer.

Takes raw opportunity/award data from SAM.gov and USASpending.gov,
then produces:
  1. Per-opportunity pursuit scores + rationale (JSON)
  2. A streaming BD Intelligence Brief (Markdown)
"""

import json
import re
from typing import AsyncIterator

from dotenv import load_dotenv
load_dotenv()

import anthropic

from naics_config import NAICS_PROFILES

MODEL = "claude-sonnet-4-6"

_client = anthropic.Anthropic()
_async_client = anthropic.AsyncAnthropic()

COMPANY_CONTEXT = """
NOU Systems is a small defense contractor headquartered in Huntsville, AL.
Core competencies:
- Systems Engineering & MBSE (SysML, DOORS NG, Cameo)
- Modeling & Simulation (LVC, HLA/DIS, AFSIM, physics-based)
- Cybersecurity & RMF (NIST, DISA STIG, ATO support, Zero Trust)
- Digital Engineering (digital twins, digital thread, MOSA)
- Test & Evaluation (TEMP, DT&E/OT&E support, data analysis)

Typical contracts: $1M–$50M, 3–5 year PoP, prime or major sub
Target agencies: Army (RDECOM/AFC/PEO), Air Force (AFLCMC, AFRL), MDA, DARPA
Strong Huntsville presence; can support Redstone Arsenal programs
Small business — eligible for SBA, 8(a), WOSB set-asides
"""


# ---------------------------------------------------------------------------
# Step 1: Score and classify opportunities
# ---------------------------------------------------------------------------

SCORE_SYSTEM = """You are a BD analyst for a defense contractor. Your job is to
evaluate contract opportunities and awards for strategic fit. Be concise and realistic.
Respond with valid JSON only — no markdown fences."""

SCORE_USER = """Evaluate these contract opportunities/awards for NOU Systems.

COMPANY PROFILE:
{company}

OPPORTUNITIES/AWARDS DATA:
{data}

For each item, return a JSON array where each element has:
{{
  "id": "the award_id or notice_id or sol_number",
  "title": "short title (max 60 chars)",
  "pursuit_score": 1-10,
  "priority": "High" | "Medium" | "Low" | "Monitor",
  "rationale": "1-2 sentences on fit",
  "key_factors": ["2-3 bullet factors"],
  "estimated_value_m": estimated value in $M as a number or null,
  "deadline": "response deadline or end date, or null",
  "agency_short": "short agency name",
  "naics": "NAICS code",
  "set_aside": "set-aside type or 'Full & Open'",
  "flags": ["list of notable flags: e.g. 'Recompete', 'Incumbent Risk', 'Expiring Soon', 'AL location', 'Small Biz Only']"
}}

Return ONLY the JSON array, nothing else."""


def score_opportunities(opportunities: list[dict]) -> list[dict]:
    """Score a list of opportunities/awards for NOU Systems fit."""
    if not opportunities:
        return []

    # Trim to avoid token overflow — send up to 30 items
    sample = opportunities[:30]
    data_str = json.dumps(sample, indent=2, default=str)

    response = _client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=SCORE_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": SCORE_USER.format(company=COMPANY_CONTEXT, data=data_str),
            }
        ],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        scored = json.loads(raw)
        if isinstance(scored, list):
            return sorted(scored, key=lambda x: x.get("pursuit_score", 0), reverse=True)
        return scored
    except json.JSONDecodeError:
        return [{"parse_error": raw[:300]}]


# ---------------------------------------------------------------------------
# Step 2: Stream BD Intelligence Brief
# ---------------------------------------------------------------------------

BRIEF_SYSTEM = """You are a senior BD strategist for a defense contractor in Huntsville, AL.
Write sharp, actionable intelligence briefs. Be specific. Avoid filler."""

BRIEF_USER = """Write a BD Intelligence Brief for NOU Systems based on this market data.

COMPANY PROFILE:
{company}

FOCUS AREAS: {focus_areas}

SCORED OPPORTUNITIES (top results):
{scored_json}

MARKET CONTEXT (USASpending award totals by sub-agency):
{market_context}

---
Write the following sections in Markdown:

## Executive Summary
(2-3 sentences: what the data shows, top takeaway)

## Top Pursuit Opportunities
(For each High/Medium priority item: 1 paragraph with the opportunity name bolded,
why it fits NOU, key risks, recommended next action)

## Market Landscape
(What the award data tells us about spending trends, dominant primes/incumbents,
and where NOU can win)

## Recommended BD Actions
(Numbered list of 5-7 specific, actionable steps NOU should take in the next 30-60 days)

## Watch List
(Brief notes on Monitor-priority items worth tracking)
"""


async def stream_brief(
    scored: list[dict],
    market_context: str,
    focus_areas: list[str],
) -> AsyncIterator[str]:
    """Async generator: streams the BD Intelligence Brief."""
    areas_str = ", ".join(focus_areas) if focus_areas else "all focus areas"
    top = [s for s in scored if s.get("priority") in ("High", "Medium")][:15]

    async with _async_client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        system=BRIEF_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": BRIEF_USER.format(
                    company=COMPANY_CONTEXT,
                    focus_areas=areas_str,
                    scored_json=json.dumps(top, indent=2, default=str),
                    market_context=market_context,
                ),
            }
        ],
    ) as stream:
        async for text in stream.text_stream:
            yield text


def build_market_context(agency_spending: dict) -> str:
    """Convert USASpending category data into a readable string for the brief."""
    results = agency_spending.get("results", [])
    if not results:
        return "No aggregate spending data available."
    lines = ["Top DoD sub-agencies by contract spend (selected NAICS):"]
    for r in results[:10]:
        name = r.get("name", "Unknown")
        amount = r.get("aggregated_amount", 0)
        lines.append(f"  - {name}: ${amount:,.0f}")
    return "\n".join(lines)
