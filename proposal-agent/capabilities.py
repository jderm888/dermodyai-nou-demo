"""
Capability data for the active company profile (see shared/company_profiles.py).
Set COMPANY_PROFILE in .env to switch companies.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from company_profiles import COMPANY  # noqa: E402

CAPABILITIES = COMPANY["capabilities"]


def get_capabilities_for_matching() -> str:
    """Return a formatted string of capabilities suitable for LLM context."""
    lines = []
    for key, cap in CAPABILITIES.items():
        lines.append(f"## {cap['name']}")
        lines.append(cap["summary"])
        lines.append("Key offerings:")
        for h in cap["highlights"]:
            lines.append(f"  - {h}")
        lines.append(f"Relevant keywords: {', '.join(cap['keywords'][:10])}")
        lines.append("")
    return "\n".join(lines)


def get_capability_keywords() -> list[str]:
    """Flat list of all capability keywords for quick matching."""
    keywords = []
    for cap in CAPABILITIES.values():
        keywords.extend(cap["keywords"])
    return list(set(keywords))
