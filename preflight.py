"""
Demo checkup: confirms the things both agents need before you present.

Run by start_demo.sh, or on its own with an agent's Python:
    bd-research-agent/.venv/bin/python preflight.py
"""

import re
import sys
from pathlib import Path

import anthropic
import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
AGENTS = ["proposal-agent", "bd-research-agent"]


def line(ok: bool, label: str, fix: str = "") -> bool:
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if not ok and fix:
        print(f"         -> {fix}")
    return ok


def read_key(agent: str) -> str:
    key = (dotenv_values(ROOT / agent / ".env").get("ANTHROPIC_API_KEY") or "").strip()
    return "" if key in ("", "your-key-here") else key


def check_claude(agent: str, key: str) -> bool:
    model = re.search(r'^MODEL = "([^"]+)"', (ROOT / agent / "agent.py").read_text(), re.M).group(1)
    label = f"{agent}: Claude answers ({model})"
    try:
        anthropic.Anthropic(api_key=key, max_retries=0, timeout=60).messages.create(
            model=model,
            max_tokens=64,
            messages=[{"role": "user", "content": "Reply with the word ready."}],
        )
    except anthropic.AuthenticationError:
        return line(False, label, f"The key in {agent}/.env was rejected. Copy it again from console.anthropic.com -> API Keys.")
    except anthropic.NotFoundError:
        return line(False, label, f"This key cannot use {model}. Check model access in console.anthropic.com.")
    except anthropic.RateLimitError:
        return line(False, label, "Rate limited right now. Wait a minute and run this again.")
    except anthropic.APIStatusError as e:
        if e.status_code == 402 or "credit balance" in str(e).lower():
            return line(False, label, "No API credits. Add credits at console.anthropic.com -> Billing, then run this again.")
        return line(False, label, f"Claude API error {e.status_code}: {str(e)[:150]}")
    except anthropic.APIConnectionError:
        return line(False, label, "Could not reach api.anthropic.com. Check your internet connection.")
    return line(True, label)


def check_usaspending() -> bool:
    label = "USASpending.gov reachable (BD agent's contract data)"
    try:
        httpx.get("https://api.usaspending.gov/api/v2/references/toptier_agencies/", timeout=30).raise_for_status()
    except httpx.HTTPError as e:
        return line(False, label, f"Could not reach USASpending.gov ({type(e).__name__}). Check internet/VPN; the BD agent needs it.")
    return line(True, label)


def main() -> int:
    print("\nDemo checkup")
    results = []
    checked: dict[str, bool] = {}
    for agent in AGENTS:
        key = read_key(agent)
        if not line(bool(key), f"{agent}: API key saved in .env",
                    f"Open {agent}/.env and set ANTHROPIC_API_KEY=<your key> (one line, no quotes)."):
            results.append(False)
            continue
        # Same key + same model in both agents only needs one paid test call
        model_line = re.search(r'^MODEL = .*$', (ROOT / agent / "agent.py").read_text(), re.M).group(0)
        cache_id = key + model_line
        if cache_id not in checked:
            checked[cache_id] = check_claude(agent, key)
        else:
            line(checked[cache_id], f"{agent}: Claude answers (same key as above)")
        results.append(checked[cache_id])
    results.append(check_usaspending())

    ok = all(results)
    print("\n  ALL GOOD - ready to demo.\n" if ok else "\n  NOT READY - fix the FAIL lines above, then run ./start_demo.sh again.\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
