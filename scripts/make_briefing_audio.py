"""Build a deterministic planner briefing and voice it with ElevenLabs TTS.

Text-to-speech only: no LLM is involved. The text is a fixed template filled
from frozen artifacts. The API key is read from ELEVENLABS_API_KEY only.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACTS = ROOT / "data" / "artifacts" / "real"
DEFAULT_VOICE = "21m00Tcm4TXrEUJWWWm"
MODEL_ID = "eleven_multilingual_v2"
API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
OUT_DIR = ROOT / "frontend" / "public"


def _mean_final_capture(rows: list[dict], policy_id: str) -> float:
    vals = [
        float(r["asset_capture"])
        for r in rows
        if r["split"] == "final" and r["policy_id"] == policy_id
    ]
    if not vals:
        raise ValueError(f"no final-test rows for policy {policy_id}")
    return sum(vals) / len(vals)


def _pct(x: float) -> str:
    return f"{x * 100:.1f} percent"


def build_briefing(artifacts: Path) -> str:
    artifacts = Path(artifacts)
    audit = json.loads((artifacts / "audit_summary.json").read_text(encoding="utf-8"))
    with (artifacts / "validation_results.csv").open(newline="", encoding="utf-8") as f:
        val = list(csv.DictReader(f))
    with (artifacts / "escalation.csv").open(newline="", encoding="utf-8") as f:
        n_esc = sum(1 for _ in csv.DictReader(f))

    v1 = audit["v1_policy_id"]
    sel = audit["selected_policy_id"]
    gate = audit["revision_gate"]
    years = audit["final_test"]["outcome_years"]
    cap_sel = _mean_final_capture(val, sel)
    cap_v1 = _mean_final_capture(val, v1)
    cap_co = _mean_final_capture(val, "count_only")
    candidates = sorted({r["policy_id"] for r in val if r["policy_id"].startswith("C")})

    if audit.get("v2_equals_v1"):
        outcome = "The gate kept the first policy, so version two equals version one."
    else:
        outcome = (
            f"The revision gate accepted candidate {sel}, which became version two, "
            "the selected policy."
        )
    parts = [
        "Pipe Dreams planner briefing.",
        f"The agent started from version one. It tested {len(candidates)} candidate revisions, "
        f"{candidates[0]} through {candidates[-1]}, on validation data. "
        f"A candidate had to win at least {gate['min_origin_wins']} of "
        f"{gate['n_origins']} origins and improve by at least "
        f"{gate['min_improvement_in_se']:g} standard error. {outcome}",
        f"On the final test, {years[0]} to {years[-1]}, version two caught "
        f"{_pct(cap_sel)} of future breaking assets on average across budgets, "
        f"versus {_pct(cap_v1)} for version one and {_pct(cap_co)} for a simple count-only baseline.",
        f"{n_esc:,} assets are escalated for human review.",
        "Limits: this is relative inspection priority, not failure prediction.",
    ]
    return " ".join(parts)


def synthesize(text: str, api_key: str, voice_id: str) -> bytes:
    req = urllib.request.Request(
        API_URL.format(voice_id=voice_id),
        data=json.dumps({"text": text, "model_id": MODEL_ID}).encode("utf-8"),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--dry-run", action="store_true", help="print text, no API call")
    args = ap.parse_args(argv)

    text = build_briefing(args.artifacts)
    if args.dry_run:
        print(text)
        return 0
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        print("ERROR: set the ELEVENLABS_API_KEY environment variable.", file=sys.stderr)
        return 2
    try:
        audio = synthesize(text, key, args.voice)
    except urllib.error.HTTPError as e:
        print(f"ERROR: ElevenLabs returned HTTP {e.code}: {e.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"ERROR: could not reach ElevenLabs: {e.reason}", file=sys.stderr)
        return 1
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "briefing.mp3").write_bytes(audio)
    (args.out_dir / "briefing.txt").write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {args.out_dir / 'briefing.mp3'} and briefing.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
