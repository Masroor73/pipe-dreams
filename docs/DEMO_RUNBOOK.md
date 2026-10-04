# Demo Runbook

Windows PowerShell, run from the repo root. Python 3.11 and Node.js 20+ required.

## 1. Get the code

```powershell
git checkout main
git pull
```

## 2. Place the real artifacts

The teammate's zip contains `data/artifacts/real` and `data/audit_working`. Unzip so the repo has:

```text
pipe-dreams\data\artifacts\real\...      (served by the API)
pipe-dreams\data\audit_working\...       (audit working files)
```

`data/` is git-ignored, so these never get committed. Check:

```powershell
Test-Path data\artifacts\real\rank_changes.csv
```

## 3. One-time install

```powershell
py -3.11 -m venv backend\.venv
backend\.venv\Scripts\python -m pip install -e backend[dev]
```

This includes `pyproj`. If `backend\.venv` already exists, only the `pip install` line is needed.

## 4. Start

```powershell
python scripts/start.py --artifacts data/artifacts/real
```

API on http://localhost:8000, app on http://localhost:5173, browser opens by itself. Ctrl+C stops both. Real artifacts show no synthetic-data banner; if you see the banner, you are on the wrong artifact directory.

## 5. Five-minute click path

1. **Overview**: read the headline result (V2 = C3 vs V1 and the count-only baseline, 2023 to 2025 unseen). Point at the "How V2 moved the ranking" cards.
2. **Agent audit**: press **play** on the replay. C1 is rejected, C2 and C3 are accepted, C3 is selected.
3. **Communities**: community-level priority, the "protect first" question.
4. Open **Beltline**: its pipes are listed.
5. Click a pipe (for example **#49 citywide**): the asset panel shows the V1 and V2 rank and the rank move (a lower rank number is higher priority).
6. **Map**: selected pipes of the V2 plan, coloured by evidence confidence. Toggle V1/V2.
7. **Escalation**: cases the agent will not resolve on its own and hands to a person.
8. **Limits**: what the system does not claim.

## 6. Backup plan if venue Wi-Fi fails

- The map falls back to the offline style automatically (no basemap tiles, pipes still draw, with an on-screen note). Everything else runs on localhost and needs no internet.
- Keep the screenshots in `submission-screens\` open in a second window and narrate from them if the live app misbehaves.
- Start the app before going on stage, and load each page once so it is warm.

## 7. Known issues

- Map first load needs the online basemap tiles; on a slow connection the pipes can appear before the street background.
- `delta_rank` in `rank_changes.csv` is `rank_v1 - rank_v2` (positive means improved), while the synthetic fixtures use the opposite sign. The UI ignores the sign and derives direction from `rank_v1` and `rank_v2`.
- Large rank jumps (thousands of places) reflect per-metre normalization in C3 re-ordering the long tail; they are not predictions of failure.
- Evidence confidence is not a failure probability. Do not describe it as one, and make no claims about Bearspaw.

## 8. Voice copilot (optional)

"Ask Pipe Dreams" is an ElevenLabs voice agent. It holds no data: it calls five browser-side tools that read the same API as the UI and drive the pages. The button only appears when `VITE_ELEVENLABS_AGENT_ID` is set.

1. In ElevenLabs, create an API key with **ElevenAgents: Write** permission.
2. Create the agent (PowerShell, from the repo root; add `--dry-run` first to inspect the payload):

```powershell
$env:ELEVENLABS_API_KEY = "sk_your_key_here"
python scripts/create_voice_agent.py
```

3. Put the printed line in `frontend/.env.local` (the agent id is public; never commit the API key):

```
VITE_ELEVENLABS_AGENT_ID=agent_xxxxxxxx
```

4. Restart the frontend, allow the microphone, click **Ask Pipe Dreams** (bottom right), and ask:
   - "Where should we inspect first?"
   - "Why this pipe?"
   - "Was that chosen by the original plan or the revision?"
   - "Which communities should we protect first?"

Fallback if voice fails: use the **Play planner briefing** button on the Overview page.

Note: the top-ranked V2 pipes are very short and LOW_VERIFY (per-metre normalization), so the agent will say their evidence needs verification.
