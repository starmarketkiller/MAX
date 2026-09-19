import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "check_no_active_example_secrets.py"
SPEC = importlib.util.spec_from_file_location("secret_check", SCRIPT)
secret_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(secret_check)


def test_active_default_fails():
    text = 'TOKEN = os.environ.get("NEXUS_BRIDGE_TOKEN", "NEXUS_BRIDGE_TOKEN_2026")'
    assert secret_check.find_active_occurrences("server/runtime.py", text)


def test_test_fixture_passes():
    text = 'TOKEN = "NEXUS_BRIDGE_TOKEN_2026"'
    assert secret_check.find_active_occurrences("server/tests/test_security.py", text) == []


def test_comment_passes():
    assert secret_check.find_active_occurrences(
        "MQL5/Include/config.mqh", '// old default: "NEXUS_BRIDGE_TOKEN_2026"'
    ) == []


def test_historical_results_artifact_passes():
    text = 'input string InpWebToken = "NEXUS_BRIDGE_TOKEN_2026";'
    assert secret_check.find_active_occurrences("results/archive/source.txt", text) == []


def test_runtime_guard_comparison_passes():
    text = 'if(token == "NEXUS_BRIDGE_TOKEN_2026") return false;'
    assert secret_check.find_active_occurrences("MQL5/Include/security.mqh", text) == []
