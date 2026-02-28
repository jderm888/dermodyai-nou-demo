"""
3-step proposal agent pipeline:
  1. extract_requirements  — pull structure out of raw RFP text
  2. match_capabilities    — align RFP requirements to company capabilities
  3. stream_draft          — generate proposal sections (streaming)
"""

import json
import re
from typing import AsyncIterator

from dotenv import load_dotenv
load_dotenv()

import anthropic

from capabilities import get_capabilities_for_matching

MODEL = "claude-sonnet-4-6"

_client = anthropic.Anthropic()
_async_client = anthropic.AsyncAnthropic()


# ---------------------------------------------------------------------------
# Step 1: Extract requirements
# ---------------------------------------------------------------------------

EXTRACT_SYSTEM = """You are a proposal analyst specializing in U.S. government defense contracts.
Your job is to read RFP documents and extract structured information.
Always respond with valid JSON only — no markdown fences, no explanation."""

EXTRACT_USER = """Extract the key information from this RFP text and return a JSON object with exactly these fields:

{{
  "program_name": "string or null",
  "agency": "string or null",
  "solicitation_number": "string or null",
  "naics_codes": ["list of NAICS codes found, or empty list"],
  "technical_requirements": ["list of distinct technical requirements"],
  "evaluation_criteria": ["list of evaluation factors/criteria"],
  "deliverables": ["list of required deliverables"],
  "period_of_performance": "string describing PoP, or null",
  "set_aside": "small business set-aside type or null",
  "key_themes": ["3-7 dominant themes or focus areas in the RFP"]
}}

RFP TEXT:
{rfp_text}"""


def extract_requirements(rfp_text: str) -> dict:
    response = _client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=EXTRACT_SYSTEM,
        messages=[{"role": "user", "content": EXTRACT_USER.format(rfp_text=rfp_text)}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown fences if the model adds them anyway
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"parse_error": raw}


# ---------------------------------------------------------------------------
# Step 2: Match capabilities
# ---------------------------------------------------------------------------

MATCH_SYSTEM = """You are a business development expert for NOU Systems, a defense contractor
based in Huntsville, AL. Your role is to identify which company capabilities best respond
to an RFP and how to position them. Always respond with valid JSON only."""

MATCH_USER = """Given the RFP requirements below and our company capabilities, identify the
best capability matches and any coverage gaps.

Return a JSON object with this structure:
{{
  "primary_capabilities": [
    {{
      "capability_name": "string",
      "relevance_score": 1-10,
      "why_relevant": "one sentence",
      "key_differentiators": ["list of 2-3 specific things we can say"]
    }}
  ],
  "coverage_gaps": ["any requirements we do not directly address"],
  "win_themes": ["2-4 high-level win themes to thread through the proposal"],
  "recommended_teaming": "brief note on subcontractor/partner gaps, if any"
}}

RFP REQUIREMENTS:
{requirements_json}

OUR CAPABILITIES:
{capabilities}"""


def match_capabilities(requirements: dict) -> dict:
    capabilities_text = get_capabilities_for_matching()
    req_json = json.dumps(requirements, indent=2)

    response = _client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=MATCH_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": MATCH_USER.format(
                    requirements_json=req_json,
                    capabilities=capabilities_text,
                ),
            }
        ],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"parse_error": raw}


# ---------------------------------------------------------------------------
# Step 3: Stream draft proposal sections
# ---------------------------------------------------------------------------

DRAFT_SYSTEM = """You are a senior proposal writer for NOU Systems, a defense contractor
in Huntsville, AL. You write compelling, technically precise, and compliant proposal sections
for U.S. government contracts. Your writing is specific, active-voice, and avoids boilerplate.
Reference the company's actual capabilities and tailor every section to the specific RFP."""

DRAFT_USER = """Write a full proposal response for the following opportunity. Use the
requirements and matched capabilities to tailor every section specifically to this RFP.

---
PROGRAM: {program_name}
AGENCY: {agency}
---

RFP REQUIREMENTS SUMMARY:
{requirements_json}

MATCHED CAPABILITIES & WIN THEMES:
{matched_json}

---

Write the following proposal sections in order. Use Markdown with clear section headers (##).
Be specific — reference actual capability names, methodologies, and tools. Avoid generic filler.

## Executive Summary
(3-4 paragraphs: what we're offering, why we win, key differentiators)

## Technical Approach
(Detailed response to technical requirements, organized by requirement area. Include specific
methodologies, tools, and how we address each key requirement.)

## Management Approach
(Program management structure, staffing plan, team org chart narrative, risk management,
communication cadence, and transition-in plan)

## Quality Assurance
(QA/QC methodology, process controls, metrics and reporting, deliverable review process,
compliance with government QA requirements; reference ISO 9001 or CMMI if applicable)

## Relevant Experience & Past Performance
(2-3 relevant program examples — use [PLACEHOLDER] for actual contract numbers, but describe
the type of work, scope, and measurable outcomes realistically)

## Why NOU Systems
(1-2 paragraphs: our unique value proposition for this specific opportunity — small business
agility, deep Huntsville/Redstone Arsenal presence, relevant certifications, and commitment
to mission success)

## Footer
(One-line document control: Company — NOU Systems | Program — {program_name} |
Solicitation — [SOLICITATION NUMBER] | Prepared: [DATE] |
PROPRIETARY — For Government Use Only)
"""


async def stream_draft(
    requirements: dict, matched: dict
) -> AsyncIterator[dict]:
    """Async generator that streams proposal draft text token by token."""
    program = requirements.get("program_name") or "This Opportunity"
    agency = requirements.get("agency") or "the Government"

    # Compress: drop fields unused in prose generation to reduce prompt tokens
    req_slim = {k: requirements[k] for k in (
        "program_name", "agency", "technical_requirements",
        "evaluation_criteria", "deliverables", "period_of_performance",
        "set_aside", "key_themes",
    ) if k in requirements}

    matched_slim = {
        "primary_capabilities": [
            {
                "capability_name": c.get("capability_name"),
                "key_differentiators": c.get("key_differentiators", []),
            }
            for c in matched.get("primary_capabilities", [])
        ],
        "win_themes": matched.get("win_themes", []),
        "coverage_gaps": matched.get("coverage_gaps", []),
        "recommended_teaming": matched.get("recommended_teaming", ""),
    }

    prompt = DRAFT_USER.format(
        program_name=program,
        agency=agency,
        requirements_json=json.dumps(req_slim, indent=2),
        matched_json=json.dumps(matched_slim, indent=2),
    )

    async with _async_client.messages.stream(
        model=MODEL,
        max_tokens=64000,
        system=DRAFT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield {"text": text}
        final = await stream.get_final_message()
        yield {"stop_reason": final.stop_reason}
