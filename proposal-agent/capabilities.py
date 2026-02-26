"""
Placeholder capability data for NOU Systems (Huntsville, AL).
Swap this out with real content before the live demo.
"""

CAPABILITIES = {
    "systems_engineering": {
        "name": "Systems Engineering",
        "keywords": [
            "systems engineering", "SE", "MBSE", "requirements management",
            "architecture", "systems integration", "V&V", "verification",
            "validation", "interface control", "ICD", "ConOps", "SRR", "PDR", "CDR",
        ],
        "summary": (
            "NOU Systems provides full-lifecycle systems engineering support using "
            "Model-Based Systems Engineering (MBSE) methodologies. We deliver rigorous "
            "requirements management, system architecture development, interface definition, "
            "and verification & validation planning for complex DoD programs."
        ),
        "highlights": [
            "SysML/UML model development using Cameo and DOORS NG",
            "Requirements decomposition from mission-level to component-level",
            "Interface Control Document (ICD) development and management",
            "Systems Integration Laboratory (SIL) design and operation",
            "Technical baseline management through all milestone reviews",
            "Digital Thread integration connecting requirements to test results",
        ],
    },
    "modeling_simulation": {
        "name": "Modeling & Simulation",
        "keywords": [
            "modeling", "simulation", "M&S", "LVC", "constructive", "HLA", "DIS",
            "live virtual constructive", "wargaming", "training", "JTLS", "AFSIM",
            "physics-based", "agent-based", "simulation environment",
        ],
        "summary": (
            "NOU Systems designs and develops high-fidelity modeling & simulation "
            "environments for DoD test, training, and analysis. Our M&S capabilities "
            "span physics-based engagement simulations, constructive wargaming environments, "
            "and Live-Virtual-Constructive (LVC) federation architectures."
        ),
        "highlights": [
            "LVC federation design using HLA/DIS standards",
            "Physics-based sensor and RF environment modeling",
            "AFSIM scenario development for air and missile defense analysis",
            "Real-time hardware-in-the-loop (HiL) integration",
            "Simulation environment accreditation support (VV&A)",
            "Distributed simulation infrastructure on AWS GovCloud and on-prem",
        ],
    },
    "cybersecurity": {
        "name": "Cybersecurity & RMF",
        "keywords": [
            "cybersecurity", "RMF", "risk management framework", "NIST", "DISA",
            "STIG", "ATO", "authorization to operate", "vulnerability", "pen test",
            "zero trust", "CMMC", "DoD cyber", "IA", "information assurance",
            "SIEM", "threat hunting", "DevSecOps",
        ],
        "summary": (
            "NOU Systems delivers end-to-end cybersecurity support for DoD programs, "
            "from NIST RMF package development through ATO and continuous monitoring. "
            "Our team holds active clearances and relevant certifications (CISSP, CEH, "
            "Security+) to support classified and unclassified environments."
        ),
        "highlights": [
            "Full RMF lifecycle: Categorize, Select, Implement, Assess, Authorize, Monitor",
            "STIG implementation and compliance scanning (ACAS, SCAP)",
            "System Security Plan (SSP) and POAM development",
            "Zero Trust Architecture (ZTA) design per DoD ZT Reference Architecture",
            "Penetration testing and red team exercises on classified networks",
            "DevSecOps pipeline integration with automated security scanning",
        ],
    },
    "digital_engineering": {
        "name": "Digital Engineering",
        "keywords": [
            "digital engineering", "DE", "digital twin", "digital thread",
            "model-based", "authoritative source of truth", "MOSA", "open architecture",
            "data management", "PLM", "digital transformation",
        ],
        "summary": (
            "NOU Systems supports DoD digital engineering transformation initiatives "
            "by establishing authoritative sources of truth, implementing digital thread "
            "strategies, and creating digital twins for complex weapon systems."
        ),
        "highlights": [
            "Digital Engineering Strategy development per OSD DE Strategy",
            "Authoritative Source of Truth (ASoT) framework implementation",
            "Digital Twin development for predictive maintenance and readiness",
            "Model-Based Definition (MBD) and 3D annotated technical data packages",
            "Modular Open Systems Approach (MOSA) architecture design",
            "Tool integration across DOORS, Cameo, JIRA, Confluence, and CI/CD pipelines",
        ],
    },
    "test_evaluation": {
        "name": "Test & Evaluation",
        "keywords": [
            "test and evaluation", "T&E", "DT&E", "OT&E", "TEMP", "test planning",
            "developmental test", "operational test", "ATEC", "AFOTEC", "NAVAIR",
            "live fire", "range", "instrumentation", "data analysis",
        ],
        "summary": (
            "NOU Systems provides comprehensive Test & Evaluation support from TEMP "
            "development through execution and post-test data analysis. We support "
            "DT&E and OT&E across Army, Navy, and Air Force test ranges."
        ),
        "highlights": [
            "Test & Evaluation Master Plan (TEMP) development",
            "Test procedure design and safety review documentation",
            "Range instrumentation and telemetry data collection",
            "Post-test data reduction and statistical analysis",
            "Independent Evaluation support for MDAPs",
            "Automated test reporting dashboards and traceability matrices",
        ],
    },
}


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
