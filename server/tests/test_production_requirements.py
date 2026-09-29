from pathlib import Path

from smoke_production_imports import REQUIRED_RUNTIME_MODULES


SERVER = Path(__file__).resolve().parents[1]


def test_requests_is_pinned_in_intent_and_hashed_lock():
    intent = (SERVER / "requirements.txt").read_text(encoding="utf-8").lower()
    lock = (SERVER / "requirements.lock.txt").read_text(encoding="utf-8").lower()
    assert "requests==2.32.5" in intent
    assert "requests==2.32.5" in lock
    requests_block = lock.split("requests==2.32.5", 1)[1].split("\n\n", 1)[0]
    assert "--hash=sha256:" in requests_block


def test_production_smoke_covers_jarvis_ollama_and_app():
    assert REQUIRED_RUNTIME_MODULES == (
        "app",
        "jarvis_v1.service",
        "orchestrator_v1.core.ollama_worker",
    )
