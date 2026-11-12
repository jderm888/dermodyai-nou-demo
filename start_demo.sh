#!/usr/bin/env bash
# One command to run the demo:  ./start_demo.sh
# Sets up both agents, checks keys and data access, starts them, opens the browser.
# Press Ctrl+C in this window to stop both agents.

set -u
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python) || { echo "Python 3 is not installed. Get it from python.org/downloads, then run this again."; exit 1; }
"$PY" -c 'import sys; sys.exit(sys.version_info < (3, 10))' || { echo "Python 3.10 or newer is required (found $("$PY" --version)). Get it from python.org/downloads."; exit 1; }

missing_key=0
for agent in proposal-agent bd-research-agent; do
  if [ ! -x "$agent/.venv/bin/python" ]; then
    echo "Setting up $agent (first run only, about a minute)..."
    "$PY" -m venv "$agent/.venv" || exit 1
  fi
  "$agent/.venv/bin/python" -m pip install -q --disable-pip-version-check -r "$agent/requirements.txt" || { echo "Install failed for $agent."; exit 1; }
  if ! grep -q '^ANTHROPIC_API_KEY=..' "$agent/.env" 2>/dev/null || grep -q '^ANTHROPIC_API_KEY=your-key-here' "$agent/.env"; then
    [ -f "$agent/.env" ] || echo "ANTHROPIC_API_KEY=your-key-here" > "$agent/.env"
    missing_key=1
    command -v open >/dev/null && open -e "$agent/.env"
  fi
done

if [ "$missing_key" = 1 ]; then
  echo
  echo "Your Anthropic API key is missing. In each .env file (opened in TextEdit if you're on a Mac):"
  echo "  replace your-key-here with your key, save (Cmd+S), close, then run ./start_demo.sh again."
  exit 1
fi

bd-research-agent/.venv/bin/python preflight.py
checkup=$?

# Free the ports in case an earlier run is still going
for port in 8000 8001; do
  pids=$(lsof -ti tcp:$port 2>/dev/null) && [ -n "$pids" ] && kill $pids 2>/dev/null && sleep 1
done

(cd proposal-agent && exec .venv/bin/python -m uvicorn main:app --port 8000 --log-level warning) &
p1=$!
(cd bd-research-agent && exec .venv/bin/python -m uvicorn main:app --port 8001 --log-level warning) &
p2=$!
trap 'kill $p1 $p2 2>/dev/null; echo; echo "Both agents stopped."; exit 0' INT TERM

sleep 3
if ! kill -0 $p1 2>/dev/null || ! kill -0 $p2 2>/dev/null; then
  echo "An agent failed to start. The error is printed above."
  kill $p1 $p2 2>/dev/null
  exit 1
fi

echo "RFP / Proposal agent:  http://localhost:8000"
echo "BD Research agent:     http://localhost:8001"
[ "$checkup" = 0 ] || echo "The checkup found problems (see FAIL lines above). The pages will open, but fix those before presenting."
echo "Leave this window open during the demo. Press Ctrl+C here to stop."
command -v open >/dev/null && open http://localhost:8000 http://localhost:8001
wait
