# dermodyai-nou-demo

Demo project showcasing AI agents for proposal generation and BD research, framed around
**Lockheed Martin** by default (illustrative demo data — not affiliated with or endorsed by Lockheed Martin).

## Structure

- `/proposal-agent` — Agent responsible for generating proposals
- `/bd-research-agent` — Agent responsible for business development research
- `/shared` — Shared company profiles (`company_profiles.py`) used by both agents

## Setup

Requires Python 3.10+ and an Anthropic API key (https://console.anthropic.com).

Each agent is a separate FastAPI app with its own dependencies. In each agent folder, create a `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-...
COMPANY_PROFILE=lockheed_martin   # or nou_systems
```

`.env` is gitignored — never commit it.

## Proposal Agent (RFP → proposal draft)

```bash
cd proposal-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000, upload an RFP (PDF) or paste its text — or click **Load Sample RFP**
for a fictional Army interceptor production RFP. The agent:

1. Extracts requirements from the RFP
2. Matches them to the active company's capabilities (`shared/company_profiles.py`)
3. Streams a draft proposal

## BD Research Agent (opportunity scoring + BD brief)

```bash
cd bd-research-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Open http://localhost:8001. The agent pulls awards from USASpending.gov (no key needed) and, optionally, open solicitations from SAM.gov, filtered by the active company's NAICS profiles. It scores each opportunity and streams a BD Intelligence Brief.

**SAM.gov key (optional):** get a free key at https://sam.gov/profile → API keys, then paste it into the form in the app. Without it, only USASpending.gov data is used.

## Model

Both agents use `claude-sonnet-5-5`, set by `MODEL` at the top of each `agent.py`.

## Company profiles

Both agents read the company they're framed around from `shared/company_profiles.py`.
Set `COMPANY_PROFILE` in each agent's `.env` to switch:

- `lockheed_martin` (default) — large prime; capabilities across Aeronautics, Missiles and
  Fire Control, Rotary and Mission Systems, and Space. The BD agent treats small-business
  set-asides as teaming opportunities and Lockheed-held awards as incumbent positions to defend.
- `nou_systems` — the original small-business Huntsville profile.

Capability content is illustrative, drawn from public high-level descriptions. It's not internal
company data and has no real contract numbers. USASpending.gov/SAM.gov results are real public data.
To add a company, copy a profile dict and register it in `PROFILES`.
