"""scripts/make_briefing_audio.py: template builder and mocked HTTP call."""

import importlib.util
import json
from unittest import mock

from conftest import ROOT

spec = importlib.util.spec_from_file_location("make_briefing_audio", ROOT / "scripts" / "make_briefing_audio.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def _fixture(tmp_path):
    (tmp_path / "audit_summary.json").write_text(
        json.dumps(
            {
                "selected_policy_id": "C3",
                "v1_policy_id": "V1",
                "v2_equals_v1": False,
                "revision_gate": {"min_origin_wins": 2, "n_origins": 3, "min_improvement_in_se": 1.0},
                "final_test": {"outcome_years": [2023, 2024, 2025]},
            }
        )
    )
    rows = ["split,policy_id,asset_capture"]
    for p, v in [("V1", 0.1), ("C1", 0.2), ("C4", 0.2), ("C3", 0.3), ("count_only", 0.2)]:
        rows.append(f"validation,{p},0.5")
        rows += [f"final,{p},{v}", f"final,{p},{v}"]
    (tmp_path / "validation_results.csv").write_text("\n".join(rows) + "\n")
    (tmp_path / "escalation.csv").write_text("asset_id,x\na,1\nb,2\nc,3\n")
    return tmp_path


def test_template_uses_fixture_numbers(tmp_path):
    text = mod.build_briefing(_fixture(tmp_path))
    assert "30.0 percent" in text and "10.0 percent" in text and "20.0 percent" in text
    assert "3 assets are escalated" in text
    assert "C1 through C4" in text and "not failure prediction" in text
    assert text == mod.build_briefing(tmp_path)  # deterministic


def test_synthesize_posts_expected_request():
    resp = mock.MagicMock()
    resp.__enter__.return_value.read.return_value = b"MP3"
    with mock.patch.object(mod.urllib.request, "urlopen", return_value=resp) as uo:
        assert mod.synthesize("hi", "KEY", "VOICE") == b"MP3"
    req = uo.call_args[0][0]
    assert req.full_url.endswith("/v1/text-to-speech/VOICE")
    assert req.get_header("Xi-api-key") == "KEY"
    assert json.loads(req.data) == {"text": "hi", "model_id": "eleven_multilingual_v2"}


def test_missing_key_exits(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    assert mod.main(["--artifacts", str(_fixture(tmp_path)), "--out-dir", str(tmp_path)]) == 2
    assert "ELEVENLABS_API_KEY" in capsys.readouterr().err
