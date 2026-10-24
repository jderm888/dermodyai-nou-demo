# BD research demo runbook

This is the development demo of the business-development research agent. It searches SAM.gov solicitations and USASpending.gov awards, scores each record from 1 to 5, flags recompete and incumbent signals that are actually on the record, and writes a BD intelligence brief.

The shipped profile is **fictional**. Northwind Range Systems is not a real company. Use it for a prospect demo, or copy it and fill in another contractor. Do not point a demo at the archived client profile.

Nothing in this runbook deploys the app. The daily workflow is manual and does not run unless repository secrets are set.

## Capability table

| Capability | Status |
| --- | --- |
| On-demand research API and local page (`/` , `/api/research`, `/api/brief`) | Working now |
| USASpending.gov award search | Working now. No API key. Verified live against `spending_by_award` on 24 Oct 2026. |
| USASpending.gov sub-agency totals | Working now. No API key. The request goes to `/search/spending_by_category/awarding_subagency/`. |
| 1–5 pursuit scores and the printed rubric | Working now. Rules scoring runs without a model key. Model scoring needs `ANTHROPIC_API_KEY`. |
| Recompete window and incumbent flags | Working now. Computed from the source end date and recipient/awardee fields. Missing fields stay missing. |
| BD intelligence brief with a source citation on each fact | Working now. Rendered in code from the scored records. |
| Contractor profile (NAICS, agencies, keywords, past performance) | Working now. Default file is `profiles/example_contractor.yaml`. A request may also send an inline `profile` object. |
| SAM.gov solicitation search | Needs a key. Set `SAM_GOV_API_KEY`, or pass `sam_api_key` on the request. The key is sent as the `api_key` query parameter on every search. A missing key skips SAM.gov and says so; USASpending still runs. |
| Model-written fit rationale | Needs `ANTHROPIC_API_KEY`. Without it, the 1–5 rules rubric is used and the brief says so. Rationales that cite an award id, a dollar amount, or an incumbent that is not on the source records are dropped. |
| One-shot daily entry point (`scheduler.py`) | Working now. It writes files locally. It does not register a schedule. |
| GitHub Actions daily run | Manual only (`.github/workflows/bd-daily-research.yml`). The job exits before any search when both secrets are unset. No cron trigger is configured. |
| Public hosting | Not deployed. Do not add a public host for this demo. |
| Email or chat delivery of the brief | Not built. |

## Score rubric

The same sentences are in the model prompt, the score parser, and the brief.

| Score | Priority | Meaning |
| --- | --- | --- |
| 5 | High | Strong fit — NAICS, agency, and keywords align, and the record is actionable now. |
| 4 | Medium | Good fit — most profile criteria align; worth capture effort. |
| 3 | Low | Partial fit — some overlap; teaming or monitoring may be appropriate. |
| 2 | Monitor | Weak fit — limited overlap with the contractor profile. |
| 1 | Monitor | Poor fit — outside the profile or missing the core criteria. |

A score of 6 or higher is invalid. It is not rescaled. That record is scored again with the rules rubric, and the error is returned with the research result.

Rules scoring starts at 1 and adds one point, up to 5, for each of these that is true on the source record: NAICS is on the profile, agency text contains a profile agency, a profile keyword appears in the title or description, set-aside text contains a profile set-aside.

## What a fact is allowed to say

- Award id, amount, dates, agency, NAICS, set-aside, and recipient are copied from the SAM.gov or USASpending row.
- An incumbent is named only when that row has a recipient or `award.awardee.name`. Otherwise the brief says the incumbent was not identified and was not inferred.
- A recompete flag is the award end date falling inside 548 days (18 months), or having ended within the last 180 days. Solicitations do not get that flag from a response deadline.
- Profile past performance is scoring context only. It is not printed as a contract award.
- An empty search produces a brief that says no records came back. It does not fill in sample awards.

## Setup

From `bd-research-agent/`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

Environment variables, all optional for a USASpending-only walkthrough:

| Variable | Purpose |
| --- | --- |
| `SAM_GOV_API_KEY` | Public SAM.gov key. Sent on every opportunities search. `SAM_API_KEY` is accepted as an alias. A value on the request overrides both. |
| `ANTHROPIC_API_KEY` | Enables model scoring. Without it, rules scoring still returns 1–5. |
| `BD_PROFILE_PATH` | Operator override for the profile YAML. Leave unset for the example profile. |
| `BD_ALLOW_ARCHIVED_PROFILES` | Must be `1` before an archived client file will load. Leave unset for a demo. |

Get a SAM.gov public key from the account details page on [sam.gov](https://sam.gov). Do not put the key in a profile file or in git.

## Run the local demo

```bash
cd bd-research-agent
uvicorn main:app --reload --port 8001
```

Open `http://127.0.0.1:8001/`. The banner names the example profile. Pick focus areas and run research.

- With no SAM key, the status line explains that solicitation search was skipped. Award cards still appear when USASpending returns rows.
- Paste a key in the box only if you do not want it in the environment. The box overrides `SAM_GOV_API_KEY` for that request.
- Scores render as `n/5`. Generate the brief after a run. Every fact line ends with the source record id.

Useful API checks:

```bash
curl -s http://127.0.0.1:8001/api/profile
curl -s http://127.0.0.1:8001/api/rubric
curl -s -X POST http://127.0.0.1:8001/api/research \
  -H 'content-type: application/json' \
  -d '{"focus_areas":["range_software"],"days_back":30,"limit":5}'
```

`/api/profiles` lists demo profiles only. `nou_systems` is not one of them.

## Run one daily pass

The scheduler looks back 2 days by default so a daily pass is a sweep of new records, not the 180-day interactive window. SAM.gov caps the posted-date window at 365 days.

```bash
cd bd-research-agent
python scheduler.py --output-dir output --days-back 2
```

That writes `output/YYYY-MM-DD/brief.md`, `scores.json`, and `run.json`. `schedule_enabled` in `run.json` is false. The command does not deploy anything.

To use another contractor, copy the example file and edit it:

```bash
cp profiles/example_contractor.yaml profiles/my_contractor.yaml
# edit name, NAICS, agencies, keywords, set-asides, and past performance
# set example_data: false only when the file describes a real contractor you are allowed to use
BD_PROFILE_PATH=profiles/my_contractor.yaml python scheduler.py
```

You can also POST an inline profile to `/api/research` under the `profile` key (name plus NAICS codes or focus areas). A request cannot point at a filesystem path.

Award search always uses the Department of Defense toptier on USASpending. Agencies on the profile change the score, not the award query. SAM.gov is queried once per NAICS code with `ncode` (a single code) and `ptype=o,k,p,r,s` (solicitation, combined synopsis, presolicitation, sources sought, special notice).

## Tests

```bash
cd bd-research-agent
python -m pytest
```

The tests mock SAM.gov, USASpending, and the language model. They do not need network access or API keys. They use made-up record ids such as `AWARD-EXAMPLE-1` and `NOTICE-EXAMPLE-1`.

## GitHub Actions

Workflow: `.github/workflows/bd-daily-research.yml`.

Trigger: **Run workflow** only. There is no `schedule` trigger.

If `SAM_GOV_API_KEY` and `ANTHROPIC_API_KEY` are both empty, the job logs that the daily run stays disabled and does not start `scheduler.py`. USASpending would not be called either, on purpose, so a click without credentials is not a live search.

To run it for real later, add those repository secrets, then run the workflow by hand. Do not add a cron entry until someone has accepted a live daily run. Do not add a deploy step.

## Archived client profile

The previous default was a real client's scoring context (NOU Systems: Huntsville competencies, NAICS groups, and target agencies). That text is no longer in the prompt, the page, or the default profile.

It was not deleted. It is in `bd-research-agent/profiles/archived/nou_systems.yaml`. The loader will not read it unless both of these are set:

```bash
BD_PROFILE_PATH=bd-research-agent/profiles/archived/nou_systems.yaml
BD_ALLOW_ARCHIVED_PROFILES=1
```

Do not set those for a prospect demo. `proposal-agent/` is a separate app and still contains that client's proposal copy; it is not part of this BD demo.

## Remaining limits

- SAM.gov was not called with a live key in this workspace, because no key is configured. An unauthenticated request returns HTTP 404 with an empty body, which matches the API's "no api_key was supplied" behavior. The client does not send that request when the key is missing.
- Model name is `claude-sonnet-4-6` in `agent.py`. A rejected or renamed model falls back to rules scoring; the brief labels `scoring_method` as `rules`.
- The brief's recommended actions are generated from the scored records, not from a second freeform model pass. That is intentional: the model only supplies a fit rationale, and only when it stays inside the source ids.
- Descriptions on SAM.gov are often a download link. The link is stored without appending the API key.
