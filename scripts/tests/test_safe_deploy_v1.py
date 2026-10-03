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
    # SAFE_HIGH_RISK_AUTO_APPROVAL_V1 added a third path (deploy_high_risk_auto)
    # - this test still only cares that the ORIGINAL human-gated path is
    # unchanged: still requires risk == 'HIGH_RISK', still environment-gated,
    # still has no auto_allowed anywhere in it. deploy_high_risk_auto has its
    # own dedicated coverage in test_auto_approval_v1.py.
    text=(ROOT/".github/workflows/safe-deploy.yml").read_text(encoding="utf-8")
    automatic=text.split("  deploy:\n", 1)[1].split("  deploy_high_risk:\n", 1)[0]
    protected=text.split("  deploy_high_risk:\n", 1)[1].split("  deploy_high_risk_auto:\n", 1)[0]

    assert "if: needs.classify.outputs.auto_allowed == 'true'" in automatic
    assert "environment: nexus-production-low-medium-risk" in automatic
    assert "needs.classify.outputs.risk == 'HIGH_RISK'" in protected
    assert "environment: nexus-production-high-risk\n" in protected
    assert "auto_allowed" not in protected

def test_both_deploy_paths_preserve_exact_sha_verification_and_ledger():
    # Now three paths (deploy, deploy_high_risk, deploy_high_risk_auto) -
    # the invariant this test checks (every path triggers/verifies/ledgers
    # the exact same way) now holds three times, not two.
    text=(ROOT/".github/workflows/safe-deploy.yml").read_text(encoding="utf-8")
    automatic=text.split("  deploy:\n", 1)[1].split("  deploy_high_risk:\n", 1)[0]
    protected=text.split("  deploy_high_risk:\n", 1)[1].split("  deploy_high_risk_auto:\n", 1)[0]
    auto=text.split("  deploy_high_risk_auto:\n", 1)[1]
    assert text.count("python scripts/trigger_render_deploy.py > deploy-trigger.json") == 3
    assert text.count("python scripts/verify_render_deploy.py") == 3
    assert text.count('--sha "${{ needs.classify.outputs.sha }}"') == 3
    assert text.count("deploy-ledger-${{ needs.classify.outputs.sha }}") == 3
    for job in (automatic, protected, auto):
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
    assert check == {"http":200,"status":"RUNNING","running":True,"auth_mode":"COOKIE",
                    "attempts":1,"reauth_used":False}
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
    assert check == {"status":"UNVERIFIED","reason":"LOGIN_REJECTED","http":401,
                    "attempts":0,"reauth_used":False}
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

def test_verifier_dispatcher_not_running_fails_after_retry_budget():
    # POST_DEPLOY_VERIFICATION_RETRY_BACKOFF: running=False gets a short,
    # BOUNDED retry window (a few seconds of restart settling), never an
    # indefinite one and never treated as success - a dispatcher still
    # reporting running=False once that budget is exhausted is a real FAIL,
    # not a transient blip. (Previously this returned error=None - that was
    # the actual bug being fixed: a genuinely stopped dispatcher could pass.)
    check, error=verifier.verify_dispatcher(
        "https://nexus.example", "user", "password",
        lambda: FakeSession(dispatcher={"status":"STOPPED","running":False}),
        sleep=lambda seconds: None)
    assert error == "DISPATCHER_NOT_RUNNING"
    assert check["running"] is False
    assert check["attempts"] == 3

def test_verifier_preserves_legacy_bearer_compatibility():
    session=FakeSession(login={"ok":True,"token":"legacy-token"}, cookies=0)
    check, error=verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                            lambda: session)
    assert error is None
    assert check["auth_mode"] == "BEARER"
    assert session.calls[1]["headers"] == {"Authorization":"Bearer legacy-token"}


# --------------------------------------------------------------------------- #
# POST_DEPLOY_VERIFICATION_RETRY_BACKOFF
# --------------------------------------------------------------------------- #
class SequencedSession:
    """Login always succeeds (unless login_responses given); the dispatcher
    endpoint returns one entry per call from `dispatcher_responses`, in
    order - an entry is either (status, body) or a raisable exception
    instance."""
    def __init__(self, dispatcher_responses, *, login_responses=None, cookies=1):
        self.dispatcher_responses = list(dispatcher_responses)
        self.login_responses = list(login_responses) if login_responses else None
        self.cookie_count = cookies
        self.login_calls = 0
        self.dispatcher_calls = 0

    def request_json(self, url, *, method="GET", payload=None, headers=None):
        if url.endswith("/api/auth/login"):
            self.login_calls += 1
            if self.login_responses:
                item = self.login_responses.pop(0)
                if isinstance(item, BaseException): raise item
                return item
            return 200, {"ok": True}
        self.dispatcher_calls += 1
        item = self.dispatcher_responses.pop(0)
        if isinstance(item, BaseException): raise item
        return item

def http_error(code):
    return urllib.error.HTTPError(
        "https://nexus.example/api/jarvis/dispatcher/status", code, "err", {}, None)

def test_transient_502_on_dispatcher_is_retried_to_success():
    session = SequencedSession([http_error(502), (200, {"status":"RUNNING","running":True})])
    check, error = verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                              lambda: session, sleep=lambda s: None)
    assert error is None and check["running"] is True and check["attempts"] == 2

def test_connection_reset_on_dispatcher_is_retried_to_success():
    session = SequencedSession([ConnectionResetError("reset"),
                                (200, {"status":"RUNNING","running":True})])
    check, error = verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                              lambda: session, sleep=lambda s: None)
    assert error is None and check["running"] is True

def test_ready_false_is_retried_to_success(monkeypatch):
    responses = [(200, {"ok": False}), (200, {"ok": True})]
    monkeypatch.setattr(verifier, "get_json", lambda url: responses.pop(0))
    check, ok = verifier.check_ready("https://nexus.example", sleep=lambda s: None)
    assert ok is True and check["attempts"] == 2

def test_dispatcher_running_false_transient_is_retried_to_success():
    session = SequencedSession([(200, {"status":"BOOTING","running":False}),
                                (200, {"status":"RUNNING","running":True})])
    check, error = verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                              lambda: session, sleep=lambda s: None)
    assert error is None and check["running"] is True and check["attempts"] == 2

def test_dispatcher_running_false_persistent_fails_after_budget():
    session = SequencedSession([(200, {"status":"STOPPED","running":False})] * 3)
    check, error = verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                              lambda: session, sleep=lambda s: None,
                                              max_attempts=3)
    assert error == "DISPATCHER_NOT_RUNNING" and check["attempts"] == 3

def test_401_triggers_one_fresh_login_then_succeeds():
    session = SequencedSession([http_error(401), (200, {"status":"RUNNING","running":True})])
    check, error = verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                              lambda: session, sleep=lambda s: None)
    assert error is None and check["running"] is True
    assert check["reauth_used"] is True
    assert session.login_calls == 2  # initial login + the one fresh re-login

def test_401_persists_after_fresh_login_fails_immediately():
    session = SequencedSession([http_error(401), http_error(401)])
    check, error = verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                              lambda: session, sleep=lambda s: None)
    assert error == "DISPATCHER_ENDPOINT_REJECTED"
    assert check["http"] == 401 and check["reauth_used"] is True
    # Never retried a third time waiting for infra to recover from a
    # persistent auth rejection - that is not what retries are for.
    assert session.dispatcher_calls == 2

def test_403_persists_fails_immediately_same_as_401():
    session = SequencedSession([http_error(403), http_error(403)])
    check, error = verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                              lambda: session, sleep=lambda s: None)
    assert error == "DISPATCHER_ENDPOINT_REJECTED" and check["http"] == 403

def test_retry_exhaustion_on_persistent_5xx_fails_closed():
    session = SequencedSession([http_error(503), http_error(503), http_error(503)])
    check, error = verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                              lambda: session, sleep=lambda s: None,
                                              max_attempts=3)
    assert error == "DISPATCHER_ENDPOINT_REJECTED"
    assert check["attempts"] == 3 and check["http"] == 503

def test_no_check_can_turn_green_just_because_retries_ran_out():
    # The exhaustion path must report the LAST real observation, never a
    # fabricated success - this is the "no false green" requirement.
    session = SequencedSession([(200, {"status":"BOOTING","running":False})] * 5)
    check, error = verifier.verify_dispatcher("https://nexus.example", "user", "password",
                                              lambda: session, sleep=lambda s: None,
                                              max_attempts=5)
    assert error == "DISPATCHER_NOT_RUNNING"
    assert check["running"] is False

def test_backoff_delays_follow_the_configured_schedule():
    delays = []
    session = SequencedSession([http_error(502), http_error(502),
                                (200, {"status":"RUNNING","running":True})])
    verifier.verify_dispatcher("https://nexus.example", "user", "password", lambda: session,
                               sleep=delays.append, backoff_seconds=(3, 6, 12))
    assert delays == [3, 6]

def test_check_ready_retries_5xx_then_succeeds(monkeypatch):
    responses = [http_error(502), (200, {"ok": True})]
    def fake_get_json(url):
        item = responses.pop(0)
        if isinstance(item, BaseException): raise item
        return item
    monkeypatch.setattr(verifier, "get_json", fake_get_json)
    check, ok = verifier.check_ready("https://nexus.example", sleep=lambda s: None)
    assert ok is True

def test_check_ready_exhausts_and_fails_closed_never_a_false_green(monkeypatch):
    responses = [(200, {"ok": False})] * 3
    monkeypatch.setattr(verifier, "get_json", lambda url: responses.pop(0))
    check, ok = verifier.check_ready("https://nexus.example", sleep=lambda s: None, max_attempts=3)
    assert ok is False and check["attempts"] == 3
