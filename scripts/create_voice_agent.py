#!/usr/bin/env python3
"""Create the public "Ask Pipe Dreams" ElevenLabs voice agent (stdlib only).

Usage (PowerShell):
    $env:ELEVENLABS_API_KEY = "sk_..."
    python scripts/create_voice_agent.py            # creates the agent
    python scripts/create_voice_agent.py --dry-run  # prints the JSON payload only

The API key needs the ElevenAgents "Write" permission. The agent is public (no
auth) so the browser connects with the agent id alone; never commit the key.
The agent holds no data: every fact comes from client tools that run in the
browser against the Pipe Dreams API (frontend/src/voice/tools.ts).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://api.elevenlabs.io/v1/convai/agents/create"
VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
AGENT_NAME = "Pipe Dreams Voice Copilot"
FIRST_MESSAGE = (
    "Hi, I'm Pipe Dreams. Ask me where to inspect first, why a pipe was chosen, "
    "or which communities need attention."
)
SYSTEM_PROMPT = (
    "You are the voice interface to Pipe Dreams, an inspection-planning agent for Calgary water mains. "
    "Never invent pipe rankings, failure probabilities, consequences, recommended actions, validation "
    "results, community priorities or any infrastructure facts. For every factual answer, call a tool "
    "and answer only from its result. Describe likelihood_score as a ranking signal, not a failure "
    "probability. If evidence_confidence is LOW_VERIFY, say the evidence needs verification. Never "
    "recommend replacement; only use MONITOR, VERIFY, INSPECT or CONDITION_ASSESS. Be brief: 2-3 "
    "sentences per answer. Say pipe ids as 'pipe ending in' plus the last 4 characters."
)


def _tool(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "client",
        "name": name,
        "description": description,
        "expects_response": True,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    }


def build_tools() -> list[dict]:
    return [
        _tool(
            "get_priority_plan",
            "Get the top pipes to inspect first from the plan. Also focuses the map. Use for 'where should "
            "we inspect first' questions. plan is 'v1' (original) or 'v2' (revised, default).",
            {
                "plan": {"type": "string", "enum": ["v1", "v2"], "description": "Plan to read. Default v2."},
                "top_n": {"type": "integer", "description": "How many pipes to return (1-8). Default 5."},
            },
        ),
        _tool(
            "explain_asset",
            "Explain one pipe: rank in V1 and V2, whether it was selected, scores, consequence tier, "
            "evidence confidence, recommended action and why the revision moved it. Opens its panel.",
            {"asset_id": {"type": "string", "description": "The full asset id, as returned by get_priority_plan."}},
            ["asset_id"],
        ),
        _tool(
            "compare_v1_v2",
            "Compare the original plan (V1) with the revised plan (V2): the revision gate decision for "
            "each candidate and the final-test capture of V2, V1 and the count-only baseline. Opens the audit page.",
            {},
        ),
        _tool(
            "get_community_priorities",
            "List the communities with the highest historical breaks per km. Opens the communities page.",
            {"top_n": {"type": "integer", "description": "How many communities to return (1-8). Default 5."}},
        ),
        _tool(
            "focus_community",
            "Focus one community and return its name and pipe counts (total and selected for inspection).",
            {"community_id": {"type": "string", "description": "Community id, for example one returned by get_community_priorities."}},
            ["community_id"],
        ),
    ]


def build_payload() -> dict:
    return {
        "name": AGENT_NAME,
        "conversation_config": {
            "agent": {
                "first_message": FIRST_MESSAGE,
                "language": "en",
                "prompt": {"prompt": SYSTEM_PROMPT, "tools": build_tools()},
            },
            "tts": {"voice_id": VOICE_ID},
        },
        # Public agent: the browser connects with the agent id alone.
        "platform_settings": {"auth": {"enable_auth": False}},
    }


def create_agent(api_key: str, payload: dict) -> str:
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        hint = ""
        if exc.code in (401, 403):
            hint = "\nThe API key needs the ElevenAgents 'Write' permission (create a new key with it enabled)."
        raise SystemExit(f"ElevenLabs returned HTTP {exc.code}: {detail}{hint}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach ElevenLabs: {exc.reason}") from exc
    agent_id = body.get("agent_id")
    if not agent_id:
        raise SystemExit(f"Unexpected response (no agent_id): {body}")
    return str(agent_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="print the JSON payload and exit")
    args = parser.parse_args(argv)

    payload = build_payload()
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        print(
            "ELEVENLABS_API_KEY is not set. Create a key with the ElevenAgents 'Write' permission, then in "
            'PowerShell: $env:ELEVENLABS_API_KEY = "sk_..."',
            file=sys.stderr,
        )
        return 2

    agent_id = create_agent(api_key, payload)
    print(f"Created agent: {agent_id}")
    print("Put this line in frontend/.env.local, then restart the frontend:")
    print(f"VITE_ELEVENLABS_AGENT_ID={agent_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
