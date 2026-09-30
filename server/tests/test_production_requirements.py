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


def test_uvicorn_runtime_extras_are_portable_exact_and_hashed():
    intent = (SERVER / "requirements.txt").read_text(encoding="utf-8").lower()
    lock = (SERVER / "requirements.lock.txt").read_text(encoding="utf-8").lower()
    intent_requirements = "\n".join(
        line.strip() for line in intent.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    lock_requirements = "\n".join(
        line.strip() for line in lock.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "--hash"))
    )
    assert "uvicorn[standard]" not in intent_requirements
    assert "uvloop" not in intent_requirements
    assert "uvloop" not in lock_requirements
    for requirement in (
        "uvicorn==0.34.0",
        "httptools==0.8.0",
        "python-dotenv==1.2.3",
        "pyyaml==6.0.3",
        "watchfiles==1.3.0",
        "websockets==17.1",
    ):
        assert requirement in intent
        assert requirement in lock


def test_production_smoke_covers_jarvis_dispatcher_ollama_and_app():
    assert REQUIRED_RUNTIME_MODULES == (
        "app",
        "jarvis_v1.service",
        "orchestrator_v1.core.dispatcher",
        "orchestrator_v1.core.provider_connector",
        "orchestrator_v1.core.provider_policy",
        "orchestrator_v1.core.provider_benchmark",
        "orchestrator_v1.core.ollama_worker",
    )
