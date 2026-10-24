"""Generic set-aside labels.

NAICS selections live on the contractor profile (see profiles/example_contractor.yaml).
The previous client-specific NAICS map was moved to profiles/archived/nou_systems.yaml
and is not loaded by the demo.
"""

SET_ASIDE_LABELS = {
    "SBA": "Total Small Business Set-Aside (FAR 19.5)",
    "SBP": "Partial Small Business Set-Aside (FAR 19.5)",
    "8A": "8(a) Set-Aside (FAR 19.8)",
    "8AN": "8(a) Sole Source (FAR 19.8)",
    "HZC": "HUBZone Set-Aside (FAR 19.13)",
    "HZS": "HUBZone Sole Source (FAR 19.13)",
    "SDVOSBC": "SDVOSB Set-Aside (FAR 19.14)",
    "SDVOSBS": "SDVOSB Sole Source (FAR 19.14)",
    "WOSB": "WOSB Set-Aside (FAR 19.15)",
    "WOSBSS": "WOSB Sole Source (FAR 19.15)",
    "EDWOSB": "EDWOSB Set-Aside (FAR 19.15)",
    "EDWOSBSS": "EDWOSB Sole Source (FAR 19.15)",
    "NONE": "Full & Open",
    "": "Full & Open",
}
