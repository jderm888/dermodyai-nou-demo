"""
NAICS code profiles relevant to NOU Systems' core competencies.
"""

NAICS_PROFILES = {
    "systems_engineering": {
        "label": "Systems Engineering",
        "codes": ["541330", "541990", "541611"],
        "description": "Engineering services, technical consulting, management consulting",
    },
    "modeling_simulation": {
        "label": "Modeling & Simulation",
        "codes": ["541512", "541519", "541715"],
        "description": "Computer systems design, R&D in engineering sciences",
    },
    "cybersecurity": {
        "label": "Cybersecurity",
        "codes": ["541512", "541513", "541519"],
        "description": "Computer systems design, network/data security services",
    },
    "digital_engineering": {
        "label": "Digital Engineering",
        "codes": ["541512", "541330", "541715"],
        "description": "MBSE, digital twin, model-based definition",
    },
    "test_evaluation": {
        "label": "Test & Evaluation",
        "codes": ["541380", "541990", "334511"],
        "description": "Testing laboratories, navigation/guidance instruments",
    },
}

# Flattened deduplicated list of all NAICS codes
ALL_NAICS_CODES: list[str] = sorted(
    set(code for p in NAICS_PROFILES.values() for code in p["codes"])
)

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
