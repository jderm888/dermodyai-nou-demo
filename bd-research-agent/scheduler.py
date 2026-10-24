"""Daily BD research entry point.

Writes a scores file and a markdown brief for one profile. It does not deploy
the service and it does not register a schedule. GitHub Actions can call it
manually; see ../.github/workflows/bd-daily-research.yml.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from profile import ArchivedProfileError, ProfileError, load_default_profile, load_profile_file
from research import run_research

PACKAGE_DIR = Path(__file__).resolve().parent


def run_daily(
    *,
    output_dir: Path,
    profile=None,
    days_back: int = 2,
    limit: int = 25,
    sam_api_key: str | None = None,
    set_aside_filter: list[str] | None = None,
    today: date | None = None,
    complete_fn=None,
) -> dict:
    """Run one pass and write brief.md, scores.json, and run.json under output_dir/YYYY-MM-DD."""
    today = today or date.today()
    profile = profile or load_default_profile()
    result = run_research(
        profile,
        sam_api_key=sam_api_key,
        days_back=days_back,
        limit=limit,
        set_aside_filter=set_aside_filter,
        today=today,
        complete_fn=complete_fn,
    )
    destination = Path(output_dir) / today.isoformat()
    destination.mkdir(parents=True, exist_ok=True)
    scores_path = destination / "scores.json"
    brief_path = destination / "brief.md"
    run_path = destination / "run.json"
    scores_path.write_text(json.dumps(result["scored"], indent=2, default=str), encoding="utf-8")
    brief_path.write_text(result["brief_markdown"], encoding="utf-8")
    summary = {
        "ran_at": today.isoformat(),
        "schedule_enabled": False,
        "profile_id": profile.id,
        "profile_name": profile.name,
        "example_data": profile.example_data,
        "days_back": days_back,
        "limit": limit,
        "sam_status": result["sam_status"],
        "sam_message": result["sam_message"],
        "usaspending_status": result["usaspending_status"],
        "usaspending_message": result["usaspending_message"],
        "record_count": result["raw_count"],
        "scored_count": len(result["scored"]),
        "scoring_method": result["scoring_method"],
        "scoring_errors": result["scoring_errors"],
        "scores_path": str(scores_path),
        "brief_path": str(brief_path),
    }
    run_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["run_path"] = str(run_path)
    return summary


def _load_profile(path: str | None):
    if path:
        allow_archived = os.getenv("BD_ALLOW_ARCHIVED_PROFILES") == "1"
        try:
            return load_profile_file(Path(path), allow_archived=allow_archived)
        except ArchivedProfileError:
            raise ArchivedProfileError(
                "That file is an archived client profile. Refusing to load it for a demo run. "
                "Set BD_ALLOW_ARCHIVED_PROFILES=1 only for a local operator run. "
                "The demo default is profiles/example_contractor.yaml."
            ) from None
    return load_default_profile()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run one BD research pass and write a brief. Does not deploy or schedule itself."
    )
    parser.add_argument("--profile", help="Profile YAML. Defaults to BD_PROFILE_PATH or the example profile.")
    parser.add_argument(
        "--output-dir",
        default=str(PACKAGE_DIR / "output"),
        help="Directory for dated brief and score files.",
    )
    parser.add_argument("--days-back", type=int, default=2, help="Lookback window. Default is 2 days for a daily pass.")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--set-aside", action="append", default=None, help="SAM.gov set-aside code. Repeatable; the API uses one.")
    args = parser.parse_args(argv)
    if args.days_back < 1:
        print("days-back must be at least 1", file=sys.stderr)
        return 2
    try:
        profile = _load_profile(args.profile)
    except ArchivedProfileError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except ProfileError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    summary = run_daily(
        output_dir=Path(args.output_dir),
        profile=profile,
        days_back=args.days_back,
        limit=args.limit,
        set_aside_filter=args.set_aside,
    )
    # Counts and paths only. Source records stay in the output files.
    printable = {
        key: summary[key]
        for key in (
            "ran_at",
            "schedule_enabled",
            "profile_id",
            "profile_name",
            "example_data",
            "sam_status",
            "usaspending_status",
            "record_count",
            "scored_count",
            "scoring_method",
            "brief_path",
            "scores_path",
        )
    }
    print(json.dumps(printable, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
