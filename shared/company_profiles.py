"""
Company profiles that both agents are framed around.

Pick the active profile with the COMPANY_PROFILE env var (in each agent's .env):
    COMPANY_PROFILE=lockheed_martin   (default)
    COMPANY_PROFILE=nou_systems

All capability content is ILLUSTRATIVE demo data drawn from public, high-level
descriptions of each company. It is not internal company data, contains no real
contract numbers, and does not represent the company's actual positions.
"""

import os

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv(usecwd=True))  # the agent's .env (uvicorn runs from the agent folder)


LOCKHEED_MARTIN = {
    "name": "Lockheed Martin",
    "location": "Bethesda, MD",
    "disclaimer": "Illustrative demo — not affiliated with or endorsed by Lockheed Martin",
    "bd_context": """
Lockheed Martin is a large prime contractor headquartered in Bethesda, MD, organized into
four business areas:
- Aeronautics: F-35, F-16 Block 70, C-130J, Skunk Works advanced development
- Missiles and Fire Control (MFC): PAC-3 MSE, THAAD, GMLRS, PrSM, JASSM/LRASM, hypersonics
- Rotary and Mission Systems (RMS): Sikorsky (Black Hawk, CH-53K), Aegis, C6ISR, training & simulation
- Space: Orion, GPS III/IIIF, Next-Gen OPIR, Trident II D5, missile warning & tracking

Cross-cutting strengths: digital engineering / MOSA, cyber & mission assurance,
sustainment & logistics, test & evaluation, modeling & simulation.

Typical contracts: $100M to multi-billion, multi-year production, sustainment, and development
Role: prime on major programs; also a key sub/teammate on competitors' programs
Target customers: Army (PEO MS, PEO Aviation, AFC), Air Force (AFLCMC, AFRL), Navy (NAVSEA, NAVAIR),
Space Force (SSC, SDA), MDA, DARPA
Alabama footprint: Huntsville (Redstone Arsenal programs), Courtland (hypersonics), Troy (missile assembly)
Large business — NOT eligible for small-business set-asides. Treat set-aside items as
small-business teaming / supplier-base opportunities, not prime pursuits.
If an award's recipient is Lockheed Martin, treat it as an incumbent position to defend
(recompete risk, follow-on, expansion), not a new pursuit.
""",
    "why_us_guidance": (
        "proven performance at scale on major DoD programs, production capacity and supply "
        "chain depth, integration expertise across air, land, sea, space, and cyber, "
        "digital engineering maturity, and commitment to mission success"
    ),
    "capabilities": {
        "precision_fires_amd": {
            "name": "Precision Fires & Integrated Air and Missile Defense",
            "keywords": [
                "missile defense", "IAMD", "interceptor", "PAC-3", "THAAD", "hit-to-kill",
                "precision fires", "GMLRS", "PrSM", "long range", "JASSM", "LRASM",
                "hypersonic", "fire control", "production",
            ],
            "summary": (
                "Lockheed Martin Missiles and Fire Control designs, produces, and sustains "
                "hit-to-kill interceptors, precision strike weapons, and fire control systems, "
                "with high-rate production lines and a mature supplier base."
            ),
            "highlights": [
                "Hit-to-kill interceptor design and production (PAC-3 MSE, THAAD)",
                "Precision fires family: GMLRS, PrSM, JASSM, LRASM",
                "Hypersonic strike development and production",
                "Production ramp planning and supply chain resilience",
                "Fire control radar and sensor integration",
                "Alabama production footprint (Troy, Courtland) near Redstone Arsenal",
            ],
        },
        "advanced_aircraft": {
            "name": "Advanced Aircraft & Air Mobility",
            "keywords": [
                "fighter", "aircraft", "F-35", "F-16", "C-130", "airlift", "tactical aircraft",
                "Skunk Works", "rapid prototyping", "air vehicle", "avionics", "upgrade",
            ],
            "summary": (
                "Lockheed Martin Aeronautics develops, produces, and modernizes fifth- and "
                "fourth-generation fighters and tactical airlift, with Skunk Works driving "
                "rapid prototyping of next-generation air systems."
            ),
            "highlights": [
                "5th-generation fighter production, modernization, and sustainment (F-35)",
                "F-16 Block 70 production and fleet upgrades",
                "C-130J tactical airlift and special mission variants",
                "Skunk Works rapid prototyping and advanced development",
                "Open-architecture avionics and mission systems upgrades",
                "Performance-based logistics and global fleet sustainment",
            ],
        },
        "rotary_mission_systems": {
            "name": "Rotary Wing & Mission Systems (C6ISR)",
            "keywords": [
                "helicopter", "rotary wing", "Sikorsky", "Black Hawk", "CH-53K", "C2",
                "C4ISR", "C6ISR", "Aegis", "combat system", "radar", "JADC2",
                "command and control", "naval", "electronic warfare",
            ],
            "summary": (
                "Lockheed Martin Rotary and Mission Systems delivers Sikorsky rotorcraft, the "
                "Aegis combat system, radars, and C6ISR solutions that connect sensors and "
                "shooters across domains."
            ),
            "highlights": [
                "Sikorsky Black Hawk and CH-53K production and sustainment",
                "Aegis combat system integration and modernization",
                "Ground- and ship-based radar systems",
                "Joint All-Domain Command and Control (JADC2) integration",
                "Electronic warfare and ISR mission systems",
                "Training and simulation for aircrew and operators",
            ],
        },
        "space_systems": {
            "name": "Space Systems & Missile Warning",
            "keywords": [
                "space", "satellite", "GPS", "OPIR", "missile warning", "missile tracking",
                "SDA", "Space Force", "SSC", "Orion", "strategic", "Trident", "PNT",
                "resilient", "ground system",
            ],
            "summary": (
                "Lockheed Martin Space builds national security satellites, missile warning and "
                "tracking constellations, strategic missiles, and human spaceflight systems."
            ),
            "highlights": [
                "GPS III/IIIF navigation satellites and ground integration",
                "Next-Gen OPIR missile warning satellites",
                "Proliferated LEO tracking and transport layer satellites",
                "Strategic deterrence systems (Trident II D5)",
                "Resilient, cyber-hardened satellite architectures",
                "Satellite ground systems and mission operations",
            ],
        },
        "digital_engineering": {
            "name": "Digital Engineering & Open Architecture",
            "keywords": [
                "digital engineering", "digital twin", "digital thread", "MBSE", "SysML",
                "MOSA", "open architecture", "model-based", "systems engineering",
                "requirements", "integration", "DevSecOps", "software",
            ],
            "summary": (
                "Lockheed Martin applies model-based systems engineering, digital twins, and a "
                "Modular Open Systems Approach (MOSA) across programs to speed upgrades, cut "
                "integration risk, and lower lifecycle cost."
            ),
            "highlights": [
                "Enterprise digital thread from requirements to production and sustainment",
                "Digital twins for design trades, production, and predictive maintenance",
                "MBSE with SysML across major program baselines",
                "MOSA architectures enabling rapid third-party capability insertion",
                "Software factories and DevSecOps pipelines for embedded and mission software",
                "Systems integration labs and hardware-in-the-loop testing",
            ],
        },
        "cyber_mission_assurance": {
            "name": "Cyber & Mission Assurance",
            "keywords": [
                "cybersecurity", "cyber", "RMF", "ATO", "zero trust", "CMMC", "NIST",
                "mission assurance", "supply chain security", "cyber resilience",
                "weapon system cyber", "STIG",
            ],
            "summary": (
                "Lockheed Martin protects weapon systems, networks, and supply chains with "
                "cyber-resilient design, RMF/ATO support, and threat-informed mission assurance."
            ),
            "highlights": [
                "Weapon system cyber resiliency built in from design",
                "RMF lifecycle support through ATO and continuous monitoring",
                "Zero Trust architecture for classified and unclassified environments",
                "Supply chain risk management and CMMC flow-down to suppliers",
                "Threat-informed red teaming and cyber test",
                "Cyber Kill Chain-based threat intelligence methodology",
            ],
        },
        "sustainment_te": {
            "name": "Sustainment, Test & Evaluation",
            "keywords": [
                "sustainment", "logistics", "PBL", "depot", "readiness", "spares",
                "test and evaluation", "T&E", "DT&E", "OT&E", "flight test", "TEMP",
                "modeling", "simulation", "training",
            ],
            "summary": (
                "Lockheed Martin sustains fleets worldwide through performance-based logistics "
                "and supports developmental and operational test from planning through data analysis."
            ),
            "highlights": [
                "Performance-based logistics tied to readiness outcomes",
                "Depot partnerships and global spares management",
                "Predictive maintenance using fleet data analytics",
                "Flight and live-fire test planning and execution support",
                "Modeling, simulation, and wargaming for operational analysis",
                "Data-driven readiness dashboards for program offices",
            ],
        },
    },
    "naics_profiles": {
        "missiles_space_vehicles": {
            "label": "Missiles & Space Vehicles",
            "codes": ["336414", "336415", "336419"],
            "description": "Guided missiles, space vehicles, propulsion units and parts",
        },
        "aircraft": {
            "label": "Aircraft & Rotorcraft",
            "codes": ["336411", "336413"],
            "description": "Aircraft manufacturing, aircraft parts and auxiliary equipment",
        },
        "mission_systems": {
            "label": "Mission Systems & Sensors",
            "codes": ["334511", "334220", "541512"],
            "description": "Radar/navigation/guidance instruments, comms equipment, C2 software",
        },
        "engineering_rnd": {
            "label": "Engineering & R&D",
            "codes": ["541330", "541715"],
            "description": "Engineering services, R&D in physical/engineering sciences",
        },
        "sustainment_training": {
            "label": "Sustainment & Training",
            "codes": ["488190", "333318", "541330"],
            "description": "Aircraft support services, simulators, logistics engineering",
        },
    },
}


NOU_SYSTEMS = {
    "name": "NOU Systems",
    "location": "Huntsville, AL",
    "disclaimer": "Demo — placeholder capability data",
    "bd_context": """
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
""",
    "why_us_guidance": (
        "small business agility, deep Huntsville/Redstone Arsenal presence, relevant "
        "certifications, and commitment to mission success"
    ),
    "capabilities": {
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
    },
    "naics_profiles": {
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
    },
}


PROFILES = {
    "lockheed_martin": LOCKHEED_MARTIN,
    "nou_systems": NOU_SYSTEMS,
}

_profile_key = os.getenv("COMPANY_PROFILE", "lockheed_martin").strip().lower()
if _profile_key not in PROFILES:
    raise ValueError(
        f"Unknown COMPANY_PROFILE '{_profile_key}'. Choose one of: {', '.join(PROFILES)}"
    )

COMPANY = PROFILES[_profile_key]
