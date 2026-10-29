# dermodyai-nou-demo

Demo project showcasing AI agents for proposal generation and BD research.

## Structure

- `/proposal-agent` — Agent responsible for generating proposals
- `/bd-research-agent` — Agent responsible for business development research
- `/shared` — Shared utilities, prompts, and configurations

## Setup

Requires Python 3.10+ and an Anthropic API key (https://console.anthropic.com).

Each agent is a separate FastAPI app with its own dependencies. In each agent folder, create a `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-...
```

`.env` is gitignored — never commit it.

## Proposal Agent (RFP → proposal draft)

```bash
cd proposal-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000, upload an RFP (PDF) or paste its text. The agent:

1. Extracts requirements from the RFP
2. Matches them to NOU capabilities (`capabilities.py`)
3. Streams a draft proposal

## BD Research Agent (opportunity scoring + BD brief)

```bash
cd bd-research-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Open http://localhost:8001. The agent pulls awards from USASpending.gov (no key needed) and, optionally, open solicitations from SAM.gov, filtered by the NAICS profiles in `naics_config.py`. It scores each opportunity and streams a BD Intelligence Brief.

**SAM.gov key (optional):** get a free key at https://sam.gov/profile → API keys, then paste it into the form in the app. Without it, only USASpending.gov data is used.

## Model

Both agents use `claude-sonnet-5-5`, set by `MODEL` at the top of each `agent.py`.
