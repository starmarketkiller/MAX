"""LOCAL_OPERABILITY_FIX_01. Missing-model refusal and listener identity."""
import importlib.util
import socket
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATEWAY_PATH = ROOT / "LocalBridge" / "nexus_local_inference_gateway.py"
PROCESS_PATH = ROOT / "LocalBridge" / "gateway_process.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


gw = _load("nexus_local_inference_gateway_fix01", GATEWAY_PATH)
process = _load("gateway_process_fix01", PROCESS_PATH)
from orchestrator_v1.core import ollama_worker  # noqa: E402


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def test_absent_model_returns_before_generate(monkeypatch):
    posts = []

    def get(url, timeout=None):
        return _Response(200, {"models": [{"name": "qwen2.5:3b-instruct"}]})

    def post(*args, **kwargs):
        posts.append(args)
        raise AssertionError("generate was called")

    monkeypatch.setattr(ollama_worker.requests, "get", get)
    monkeypatch.setattr(ollama_worker.requests, "post", post)
    result = ollama_worker.call_local_model(
        "ciao", model="ministral-3:3b", timeout=3, ensure_single_resident=False)
    assert result["success"] is False
    assert result["error"] == "MODEL_NOT_INSTALLED: ministral-3:3b"
    assert posts == []


def test_generate_error_is_not_a_successful_call(monkeypatch):
    def get(url, timeout=None):
        return _Response(200, {"models": [{"name": "ministral-3:3b"}]})

    def post(*args, **kwargs):
        return _Response(404, {"error": "model not found"})

    monkeypatch.setattr(ollama_worker.requests, "get", get)
    monkeypatch.setattr(ollama_worker.requests, "post", post)
    result = ollama_worker.call_local_model(
        "ciao", model="ministral-3:3b", timeout=3, ensure_single_resident=False)
    assert result["success"] is False
    assert result["error"] == "model not found"


def test_closed_port_is_absent():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    assert process.identify(port) == "absent"


def test_foreign_listener_is_not_a_healthy_gateway():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    try:
        assert process.identify(port) == "foreign"
    finally:
        sock.close()


def test_slow_health_is_still_our_gateway(monkeypatch):
    def slow(timeout=2):
        time.sleep(timeout)
        return False

    monkeypatch.setattr(gw.ollama_worker, "is_ollama_reachable", slow)
    gw.GatewayHandler.auth_token = "c" * 32
    server = ThreadingHTTPServer(("127.0.0.1", 0), gw.GatewayHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert process.identify(server.server_address[1]) == "gateway"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_matching_health_is_our_gateway(monkeypatch):
    monkeypatch.setattr(gw.ollama_worker, "is_ollama_reachable", lambda timeout=2: False)
    gw.GatewayHandler.auth_token = "b" * 32
    server = ThreadingHTTPServer(("127.0.0.1", 0), gw.GatewayHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        assert process.identify(port) == "gateway"
        conn_identity = process.identify(port)
        assert conn_identity == "gateway"
    finally:
        server.shutdown()
        thread.join(timeout=2)
