"""SAFE_HIGH_RISK_AUTO_APPROVAL_V1.

Never replaces the human gate for HIGH_RISK - only decides whether a
HIGH_RISK commit ALSO qualifies for a second, narrower, pre-authorized path.
Every check here must fail closed: an uncertain or unrecognized case is
HUMAN_APPROVAL_REQUIRED, never a guess.
"""
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


approval = load("auto_approval", "scripts/evaluate_auto_approval.py")

CATEGORY = {"id": "provider_adapter_wiring_v1", "path_patterns": ["server/app.py"]}


def test_self_modification_is_always_vetoed_even_if_everything_else_qualifies():
    for path in ("scripts/evaluate_auto_approval.py", "scripts/auto_approval_allowlist.json",
                ".github/workflows/safe-deploy.yml", "scripts/classify_deploy_risk.py",
                "render.yaml"):
        result = approval.evaluate([path], "", allowlist_categories=[CATEGORY],
                                   prior_deploy_healthy=True)
        assert result["eligible"] is False
        assert result["veto"] == "SELF_MODIFICATION_ALWAYS_HUMAN_GATED"


def test_self_modification_veto_wins_even_when_mixed_with_allowlisted_files():
    # A commit cannot hide a self-modification among otherwise-safe files.
    result = approval.evaluate(["server/app.py", "scripts/evaluate_auto_approval.py"], "",
                               allowlist_categories=[CATEGORY], prior_deploy_healthy=True)
    assert result["eligible"] is False
    assert result["veto"] == "SELF_MODIFICATION_ALWAYS_HUMAN_GATED"


def test_hard_veto_paths_block_auto_approval():
    for path in ("MQL5/strategy.mq5", "server/nexus_security.py", "server/auth/jwt.py",
                "contracts/approval/x.schema.json"):
        result = approval.evaluate([path], "", allowlist_categories=[CATEGORY],
                                   prior_deploy_healthy=True)
        assert result["eligible"] is False and result["veto"] == "HARD_VETO_PATH"


def test_hard_veto_content_blocks_even_on_an_allowlisted_path():
    patch = "+ANTHROPIC_SECRET = 'sk-abc'\n"
    result = approval.evaluate(["server/app.py"], patch, allowlist_categories=[CATEGORY],
                               prior_deploy_healthy=True)
    assert result["eligible"] is False and result["veto"] == "HARD_VETO_CONTENT_PATTERN"


def test_comment_only_mention_of_a_vetoed_word_does_not_block_by_itself():
    # Reproduces the real false positive found in commit 60aad70: a comment
    # saying "secret-free" must not be treated the same as code handling a
    # secret. This test only proves the comment stripping works - eligibility
    # below still requires the allowlist/rollback checks to also pass
    # (test_full_eligible_case_requires_every_condition), never this alone.
    patch = "+    # same secret-free error logging already serving the AI Coach\n"
    result = approval.evaluate(["server/app.py"], patch, allowlist_categories=[CATEGORY],
                               prior_deploy_healthy=True)
    assert result["checks"]["hard_veto_content"]["ok"] is True
    assert result["eligible"] is True  # only because allowlist + rollback also hold


def test_same_word_on_a_real_code_line_still_vetoes():
    patch = '+ANTHROPIC_SECRET = "sk-abcdef123"  # a real assignment, not a comment\n'
    result = approval.evaluate(["server/app.py"], patch, allowlist_categories=[CATEGORY],
                               prior_deploy_healthy=True)
    assert result["eligible"] is False and result["veto"] == "HARD_VETO_CONTENT_PATTERN"


def test_files_outside_the_allowlist_fail_closed():
    result = approval.evaluate(["server/some_other_module.py"], "",
                               allowlist_categories=[CATEGORY], prior_deploy_healthy=True)
    assert result["eligible"] is False
    assert result["veto"] == "FILES_NOT_IN_AUTO_APPROVAL_ALLOWLIST"
    assert "server/some_other_module.py" in result["checks"]["allowlist_coverage"]["uncovered_files"]


def test_empty_allowlist_fails_closed_for_everything():
    result = approval.evaluate(["server/app.py"], "", allowlist_categories=[],
                               prior_deploy_healthy=True)
    assert result["eligible"] is False
    assert result["veto"] == "FILES_NOT_IN_AUTO_APPROVAL_ALLOWLIST"


def test_oversized_diff_fails_closed():
    big_patch = "\n".join(f"+line {i}" for i in range(500))
    result = approval.evaluate(["server/app.py"], big_patch, allowlist_categories=[CATEGORY],
                               prior_deploy_healthy=True)
    assert result["eligible"] is False and result["veto"] == "DIFF_TOO_LARGE_FOR_AUTO_APPROVAL"


def test_no_verified_rollback_target_fails_closed():
    result = approval.evaluate(["server/app.py"], "", allowlist_categories=[CATEGORY],
                               prior_deploy_healthy=False)
    assert result["eligible"] is False and result["veto"] == "NO_VERIFIED_ROLLBACK_TARGET"


def test_full_eligible_case_requires_every_condition():
    result = approval.evaluate(["server/app.py"], "+class Foo: pass\n",
                               allowlist_categories=[CATEGORY], prior_deploy_healthy=True)
    assert result["eligible"] is True
    assert result["decision"] == "AUTO_APPROVE"
    assert result["matched_categories"] == ["provider_adapter_wiring_v1"]
    assert all(check["ok"] for check in result["checks"].values())


def test_check_production_healthy_true_only_on_ok_ready_and_200_version():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if self.path == "/api/ready":
                self.wfile.write(b'{"ok": true}')
            else:
                self.wfile.write(b'{"git_sha": "x"}')
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        healthy = approval.check_production_healthy(f"http://127.0.0.1:{server.server_port}")
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
    assert healthy is True


def test_check_production_healthy_false_when_ready_reports_not_ok():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok": false}' if self.path == "/api/ready" else b'{}')
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        healthy = approval.check_production_healthy(f"http://127.0.0.1:{server.server_port}")
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
    assert healthy is False


def test_check_production_healthy_fails_closed_on_unreachable_host():
    assert approval.check_production_healthy("http://127.0.0.1:1") is False


def test_load_allowlist_rejects_malformed_or_missing_file(tmp_path):
    missing = approval._load_allowlist(str(tmp_path / "nope.json"))
    assert missing == []
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    assert approval._load_allowlist(str(bad)) == []
    wrong_version = tmp_path / "v2.json"
    wrong_version.write_text(json.dumps({"schema_version": 2, "categories": [CATEGORY]}),
                            encoding="utf-8")
    assert approval._load_allowlist(str(wrong_version)) == []


def test_real_allowlist_file_loads_and_is_schema_valid():
    categories = approval._load_allowlist(str(ROOT / "scripts/auto_approval_allowlist.json"))
    assert categories
    for category in categories:
        assert category.get("id") and category.get("path_patterns")


def test_workflow_has_the_three_high_risk_jobs_wired_correctly():
    text = (ROOT / ".github/workflows/safe-deploy.yml").read_text(encoding="utf-8")
    assert "evaluate_auto_approval:" in text
    assert "deploy_high_risk_auto:" in text
    assert "environment: nexus-production-high-risk-auto\n" in text
    # deploy_high_risk must now also require auto_approve != 'true', never
    # running in parallel with (or instead of) the auto path for the same commit.
    protected = text.split("  deploy_high_risk:\n", 1)[1].split("  deploy_high_risk_auto:\n", 1)[0]
    auto = text.split("  deploy_high_risk_auto:\n", 1)[1]
    assert "needs.evaluate_auto_approval.outputs.auto_approve != 'true'" in protected
    assert "needs.evaluate_auto_approval.outputs.auto_approve == 'true'" in auto
    # Exact, newline-anchored line so "nexus-production-high-risk-auto"
    # (mentioned only in the comment preceding the next job) can't satisfy it.
    assert "environment: nexus-production-high-risk\n" in protected
    assert "environment: nexus-production-high-risk-auto\n" not in protected
