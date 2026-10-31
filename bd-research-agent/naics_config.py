"""
NAICS code profiles for the active company profile (see shared/company_profiles.py).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from company_profiles import COMPANY  # noqa: E402

NAICS_PROFILES = COMPANY["naics_profiles"]

# Flattened deduplicated list of all NAICS codes
ALL_NAICS_CODES: list[str] = sorted(
    set(code for p in NAICS_PROFILES.values() for code in p["codes"])
)

# Capped NAICS list for SAM.gov lookups (SAM has a low daily request limit and
# only accepts one NAICS per request). Falls back to the first 3 known codes.
SAM_NAICS_CODES: list[str] = COMPANY.get("sam_naics") or ALL_NAICS_CODES[:3]

# DoD agency toptier codes (USASpending.gov)
DOD_AGENCIES = [
    {"type": "awarding", "tier": "toptier", "name": "Department of Defense"},
]

SET_ASIDE_LABELS = {
    "SBA": "Small Business",
    "8A": "8(a) Set-Aside",
    "HZC": "HUBZone",
    "HZS": "HUBZone Sole Source",
    "SBP": "Small Business Set-Aside (Partial)",
    "WNN": "Women-Owned Small Business",
    "WOSB": "WOSB Set-Aside",
    "ESB": "Emerging Small Business",
    "VSB": "Very Small Business",
    "NONE": "Full & Open",
    "": "Full & Open",
}
