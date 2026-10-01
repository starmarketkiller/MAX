import importlib.util
import json
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

def load(name, path):
    spec=importlib.util.spec_from_file_location(name, ROOT/path); module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module); return module

classifier=load("deploy_risk", "scripts/classify_deploy_risk.py")
trigger=load("deploy_trigger", "scripts/trigger_render_deploy.py")

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

def test_workflow_trigger_is_fail_fast_and_not_masked_by_tee():
    text=(ROOT/".github/workflows/safe-deploy.yml").read_text(encoding="utf-8")
    assert "set -euo pipefail" in text
    assert "python scripts/trigger_render_deploy.py > deploy-trigger.json" in text
    assert "trigger_render_deploy.py | tee" not in text
