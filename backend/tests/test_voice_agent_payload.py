"""Payload builder for scripts/create_voice_agent.py (no network)."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "create_voice_agent.py"
spec = importlib.util.spec_from_file_location("create_voice_agent", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

EXPECTED_TOOLS = {
    "get_priority_plan",
    "explain_asset",
    "compare_v1_v2",
    "get_community_priorities",
    "focus_community",
}


def test_payload_is_public_with_voice_and_prompt():
    p = mod.build_payload()
    assert p["platform_settings"]["auth"]["enable_auth"] is False
    assert p["conversation_config"]["tts"]["voice_id"] == "JBFqnCBsd6RMkjVDRZzb"
    agent = p["conversation_config"]["agent"]
    assert agent["first_message"].startswith("Hi, I'm Pipe Dreams.")
    assert "Never invent" in agent["prompt"]["prompt"]
    assert "not a failure probability" in agent["prompt"]["prompt"]


def test_payload_declares_the_five_client_tools():
    tools = mod.build_payload()["conversation_config"]["agent"]["prompt"]["tools"]
    assert {t["name"] for t in tools} == EXPECTED_TOOLS
    for t in tools:
        assert t["type"] == "client"
        assert t["expects_response"] is True
        assert t["parameters"]["type"] == "object"
        assert t["description"]


def test_required_params_match_frontend_tools():
    tools = {t["name"]: t for t in mod.build_payload()["conversation_config"]["agent"]["prompt"]["tools"]}
    assert tools["explain_asset"]["parameters"]["required"] == ["asset_id"]
    assert tools["focus_community"]["parameters"]["required"] == ["community_id"]


def test_dry_run_prints_json_and_needs_no_key(capsys, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert mod.main(["--dry-run"]) == 0
    assert '"conversation_config"' in capsys.readouterr().out
