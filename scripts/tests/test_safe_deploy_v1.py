import importlib.util
import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

def load(name, path):
    spec=importlib.util.spec_from_file_location(name, ROOT/path); module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module); return module

classifier=load("deploy_risk", "scripts/classify_deploy_risk.py")
trigger=load("deploy_trigger", "scripts/trigger_render_deploy.py")
verifier=load("deploy_verifier", "scripts/verify_render_deploy.py")

class FakeSession:
    def __init__(self, *, login_status=200, login=None, cookies=1,
                 dispatcher_status=200, dispatcher=None, login_error=None,
                 dispatcher_error=None):
        self.login_status=login_status; self.login=login or {"ok":True}; self.cookie_count=cookies
        self.dispatcher_status=dispatcher_status
        self.dispatcher=dispatcher or {"status":"RUNNING","running":True}
        self.login_error=login_error; self.dispatcher_error=dispatcher_error
        self.calls=[]
    def request_json(self, url, *, method="GET", payload=None, headers=None):
        self.calls.append({"url":url,"method":method,"payload":payload,"headers":headers})
        if url.endswith("/api/auth/login"):
            if self.login_error: raise self.login_error
            return self.login_status, self.login
        if self.dispatcher_error: raise self.dispatcher_error
        return self.dispatcher_status, self.dispatcher

def test_low_medium_high_risk_classification():
    assert classifier.classify(["docs/a.md"])["risk"] == "LOW_RISK"
    assert classifier.classify(["server/app.py"])["risk"] == "MEDIUM_RISK"
    high=classifier.classify(["server/nexus_security.py"])
    assert high["risk"] == "HIGH_RISK" and high["approval_state"] == "WAITING_APPROVAL"
    assert high["automatic_deploy_allowed"] is False

def test_sensitive_content_is_high_risk_even_in_other_path():
    assert classifier.classify(["misc.txt"], "+ password = value")["risk"] == "HIGH_RISK"

def test_deploy_hook_uses_exact_sha_and_preserves_secret_query_without_printing_it(monkeypatch, capsys):
    monkeypatch.setenv("RENDER_DEPLOY_HOOK_URL", "https://api.render.com/deploy/srv?key=super-secret")
    monkeypatch.setenv("DEPLOY_COMMIT_SHA", "abc123")
    captured={}
    class Response:
        status=200
        def read(self): return b'{"id":"dep-1"}'
        def __enter__(self): return self
        def __exit__(self,*args): return False
    def opener(request, timeout): captured["url"]=request.full_url; return Response()
    trigger.main(opener)
    output=capsys.readouterr().out
    assert "ref=abc123" in captured["url"] and "key=super-secret" in captured["url"]
    assert "super-secret" not in output
    assert json.loads(output)["deploy_id"] == "dep-1"

@pytest.mark.parametrize("status", [400, 500])
def test_deploy_hook_http_error_fails_closed_without_leaking_secret(monkeypatch, capsys, status):
    monkeypatch.setenv("RENDER_DEPLOY_HOOK_URL", "https://api.render.com/deploy/srv?key=super-secret")
    monkeypatch.setenv("DEPLOY_COMMIT_SHA", "abc123")
    def opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, status, "rejected", {}, None)
    with pytest.raises(SystemExit, match="Render deploy trigger failed: HTTPError"):
        trigger.main(opener)
    captured=capsys.readouterr()
    assert "super-secret" not in captured.out
    assert "super-secret" not in captured.err

def test_deploy_hook_non_success_response_fails_closed(monkeypatch):
    monkeypatch.setenv("RENDER_DEPLOY_HOOK_URL", "https://api.render.com/deploy/srv?key=super-secret")
    monkeypatch.setenv("DEPLOY_COMMIT_SHA", "abc123")
    class Response:
        status=500
        def read(self): return b'{"error":"rejected"}'
        def __enter__(self): return self
        def __exit__(self,*args): return False
    with pytest.raises(SystemExit, match="Render deploy trigger failed: RuntimeError"):
        trigger.main(lambda request, timeout: Response())

def test_render_blueprint_keeps_native_autodeploy_off():
    text=(ROOT/"render.yaml").read_text(encoding="utf-8")
    assert "autoDeployTrigger: off" in text

def test_workflow_requires_ci_success_and_exact_postdeploy_gates():
    text=(ROOT/".github/workflows/safe-deploy.yml").read_text(encoding="utf-8")
    for required in ("workflow_run.conclusion == 'success'", "classify_deploy_risk.py",
                     "DEPLOY_COMMIT_SHA", "verify_render_deploy.py", "WAITING_APPROVAL"):
        assert required in text

def test_workflow_keeps_low_medium_automatic_and_high_risk_environment_gated():
    text=(ROOT/".github/workflows/safe-deploy.yml").read_text(encoding="utf-8")
    automatic=text.split("  deploy:\n", 1)[1].split("  deploy_high_risk:\n", 1)[0]
    protected=text.split("  deploy_high_risk:\n", 1)[1]

    assert "if: needs.classify.outputs.auto_allowed == 'true'" in automatic
    assert "environment: nexus-production-low-medium-risk" in automatic
    assert "if: needs.classify.outputs.risk == 'HIGH_RISK'" in protected
    assert "environment: nexus-production-high-risk" in protected
    assert "auto_allowed" not in protected

def test_both_deploy_paths_preserve_exact_sha_verification_and_ledger():
    text=(ROOT/".github/workflows/safe-deploy.yml").read_text(encoding="utf-8")
    automatic=text.split("  deploy:\n", 1)[1].split("  deploy_high_risk:\n", 1)[0]
    protected=text.split("  deploy_high_risk:\n", 1)[1]
    assert text.count("python scripts/trigger_render_deploy.py > deploy-trigger.json") == 2
    assert text.count("python scripts/verify_render_deploy.py") == 2
    assert text.count('--sha "${{ needs.classify.outputs.sha }}"') == 2
    assert text.count("deploy-ledger-${{ needs.classify.outputs.sha }}") == 2
    for job in (automatic, protected):
        assert "NEXUS_DEPLOY_VERIFY_USER" in job
        assert "NEXUS_DEPLOY_VERIFY_PASSWORD" in job

def test_workflow_trigger_is_fail_fast_and_not_masked_by_tee():
    text=(ROOT/".github/workflows/safe-deploy.yml").read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    assert "python scripts/trigger_render_deploy.py > deploy-trigger.json" in text
    assert "trigger_render_deploy.py | tee" not in text

def test_verifier_uses_hardened_cookie_session_for_dispatcher():
    session=FakeSession(cookies=2)
    check, error=verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                            lambda: session)
    assert error is None
    assert check == {"http":200,"status":"RUNNING","running":True,"auth_mode":"COOKIE"}
    assert session.calls[1]["headers"] is None

def test_http_session_preserves_httponly_cookie_end_to_end():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args): pass
        def do_POST(self):
            assert self.path == "/api/auth/login"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", "nexus_session=opaque-session; HttpOnly; Path=/; SameSite=Lax")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
        def do_GET(self):
            assert self.path == "/api/jarvis/dispatcher/status"
            if "nexus_session=opaque-session" not in (self.headers.get("Cookie") or ""):
                self.send_response(401); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"RUNNING","running":true}')
    server=ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread=threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        base=f"http://127.0.0.1:{server.server_port}"
        check, error=verifier.verify_dispatcher(base, "user", "password")
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
    assert error is None
    assert check["running"] is True
    assert check["auth_mode"] == "COOKIE"

def test_verifier_rejects_wrong_credentials_without_exposing_them():
    rejected=urllib.error.HTTPError("https://nexus.example/api/auth/login", 401,
                                    "denied", {}, None)
    check, error=verifier.verify_dispatcher("https://nexus.example", "user", "secret-password",
                                            lambda: FakeSession(login_error=rejected))
    assert error == "LOGIN_REJECTED"
    assert check == {"status":"UNVERIFIED","reason":"LOGIN_REJECTED","http":401}
    assert "secret-password" not in json.dumps(check)

def test_verifier_fails_when_credentials_are_missing():
    check, error=verifier.verify_dispatcher("https://nexus.example", "", None)
    assert error == "VERIFY_CREDENTIALS_MISSING"
    assert check["reason"] == "VERIFY_CREDENTIALS_MISSING"

def test_verifier_fails_when_login_has_no_cookie_or_legacy_token():
    check, error=verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                            lambda: FakeSession(cookies=0))
    assert error == "LOGIN_SESSION_MISSING"
    assert check["reason"] == "LOGIN_SESSION_MISSING"

def test_verifier_dispatcher_not_running_fails_success_gate():
    check, error=verifier.verify_dispatcher(
        "https://nexus.example", "user", "password",
        lambda: FakeSession(dispatcher={"status":"STOPPED","running":False}))
    assert error is None
    assert check["running"] is False

def test_verifier_preserves_legacy_bearer_compatibility():
    session=FakeSession(login={"ok":True,"token":"legacy-token"}, cookies=0)
    check, error=verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                            lambda: session)
    assert error is None
    assert check["auth_mode"] == "BEARER"
    assert session.calls[1]["headers"] == {"Authorization":"Bearer legacy-token"}
