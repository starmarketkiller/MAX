#!/usr/bin/env python3
"""SAFE_HIGH_RISK_AUTO_APPROVAL_V1 - evaluates whether a HIGH_RISK deploy
(already classified by classify_deploy_risk.py, unchanged) may skip the
human-gated environment and go through a narrower, still-audited,
non-human path instead.

This NEVER replaces the human gate - it only decides, for a HIGH_RISK
commit, whether it ALSO qualifies for a second, stricter, pre-authorized
path. Every existing HIGH_RISK commit that does not qualify here still
goes through deploy_high_risk exactly as before. Fail-closed throughout:
any check this script cannot evaluate with confidence means
HUMAN_APPROVAL_REQUIRED, never a guess.

Absolute, unconditional rule (checked first, before anything else): a
commit that touches this script, the allowlist it reads, the classifier,
or the deploy workflow itself can NEVER auto-approve - evaluated by the
version of this file that existed BEFORE the commit being evaluated would
ever run, so a commit cannot rewrite its own rules to approve itself.
"""
from __future__ import annotations
import argparse, json, re, subprocess, urllib.error, urllib.request
from pathlib import Path

# Keep in lockstep with classify_deploy_risk.py's own HIGH_PATHS entries for
# the deploy/approval machinery itself - belt-and-suspenders: those already
# make a commit HIGH_RISK via HIGH_RISK_PATH, this gives the SAME paths an
# unambiguous, dedicated veto reason here, so nobody has to infer "oh, that
# generic HIGH_RISK_PATH reason also happens to mean self-modification."
SELF_PROTECTED_PATHS = (
    ".github/workflows/safe-deploy.yml",
    "scripts/classify_deploy_risk.py",
    "scripts/evaluate_auto_approval.py",
    "scripts/auto_approval_allowlist.json",
    "scripts/verify_render_deploy.py",
    "scripts/trigger_render_deploy.py",
    "render.yaml",
)

# A narrower restatement of classify_deploy_risk.py's own hard-risk paths -
# duplicated deliberately (not imported) so a bug or edit in the classifier
# can never silently widen what this evaluator considers safe.
HARD_VETO_PATHS = (
    "MQL5/", "server/nexus_security.py", "server/command_contract.py",
    "server/settings_contract.py", "server/nexus_retention.py", "server/migrations/",
    "server/auth", "contracts/command", "contracts/approval",
)
HARD_VETO_CONTENT = re.compile(
    r"(password|billing|payment|live.?trading|order.?send|approval.?gate|drop table|"
    r"delete from|_API_KEY\s*=\s*['\"]|_SECRET\s*=\s*['\"]|_TOKEN\s*=\s*['\"])", re.I)

MAX_DIFF_LINES_DEFAULT = 150


def _matches_any(name, prefixes):
    return any(name == prefix or name.startswith(prefix) for prefix in prefixes)


def _strip_comment_lines(patch_text):
    """Best-effort only, NOT a security boundary (see module docstring and
    README note below): drops '+'/'-' diff lines that are themselves a
    single-line '#' comment, so a phrase like 'secret-free' inside a comment
    does not by itself keep a commit out of consideration. A multi-line
    docstring is not tracked across lines - an actual secret-handling change
    hidden inside one would still be caught by HARD_VETO_CONTENT running on
    the UNFILTERED text in a real code line nearby, and by the path/category
    checks below, which never depend on this filter."""
    kept = []
    for line in patch_text.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")):
            stripped = line[1:].strip()
            if stripped.startswith("#"):
                continue
        kept.append(line)
    return "\n".join(kept)


def _diff_line_count(patch_text):
    return sum(1 for line in patch_text.splitlines()
              if line.startswith(("+", "-")) and not line.startswith(("+++", "---")))


def _load_allowlist(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return []
    return [c for c in data.get("categories", []) if isinstance(c, dict) and c.get("path_patterns")]


def _uncovered_files(files, categories):
    patterns = [p for category in categories for p in category["path_patterns"]]
    return [name for name in files if not _matches_any(name, patterns)]


def evaluate(files, patch_text, *, allowlist_categories, prior_deploy_healthy,
            max_diff_lines=MAX_DIFF_LINES_DEFAULT):
    """Pure (no I/O): the CLI wrapper resolves prior_deploy_healthy via a
    real health check before calling this. Returns the full decision record,
    never just a boolean, so every refusal is traceable to a reason."""
    files = sorted(set(str(f).replace("\\", "/") for f in files if f))
    checks = {}

    self_hits = [f for f in files if _matches_any(f, SELF_PROTECTED_PATHS)]
    checks["self_modification"] = {"ok": not self_hits, "files": self_hits}
    if self_hits:
        return _decision(False, "SELF_MODIFICATION_ALWAYS_HUMAN_GATED", checks, files)

    veto_path_hits = [f for f in files if _matches_any(f, HARD_VETO_PATHS)]
    checks["hard_veto_paths"] = {"ok": not veto_path_hits, "files": veto_path_hits}
    if veto_path_hits:
        return _decision(False, "HARD_VETO_PATH", checks, files)

    filtered = _strip_comment_lines(patch_text or "")
    content_hit = bool(HARD_VETO_CONTENT.search(filtered))
    checks["hard_veto_content"] = {"ok": not content_hit}
    if content_hit:
        return _decision(False, "HARD_VETO_CONTENT_PATTERN", checks, files)

    line_count = _diff_line_count(patch_text or "")
    checks["diff_size"] = {"ok": line_count <= max_diff_lines, "lines": line_count,
                           "max_allowed": max_diff_lines}
    if line_count > max_diff_lines:
        return _decision(False, "DIFF_TOO_LARGE_FOR_AUTO_APPROVAL", checks, files)

    uncovered = _uncovered_files(files, allowlist_categories)
    checks["allowlist_coverage"] = {"ok": not uncovered, "uncovered_files": uncovered}
    if uncovered:
        return _decision(False, "FILES_NOT_IN_AUTO_APPROVAL_ALLOWLIST", checks, files)

    checks["rollback_available"] = {"ok": bool(prior_deploy_healthy)}
    if not prior_deploy_healthy:
        return _decision(False, "NO_VERIFIED_ROLLBACK_TARGET", checks, files)

    matched_ids = sorted({c["id"] for c in allowlist_categories
                          for f in files if _matches_any(f, c["path_patterns"])})
    return _decision(True, None, checks, files, matched_ids)


def _decision(eligible, veto, checks, files, matched_categories=None):
    return {"schema_version": 1, "eligible": eligible,
           "decision": "AUTO_APPROVE" if eligible else "HUMAN_APPROVAL_REQUIRED",
           "veto": veto, "matched_categories": matched_categories or [], "checks": checks,
           "files": files}


def check_production_healthy(base_url, timeout=15):
    """Read-only, unauthenticated, same two endpoints verify_render_deploy.py
    already checks post-deploy - used here PRE-deploy as the rollback-target
    precondition: if the currently-live version is not healthy, there is no
    known-good state to fall back to, so auto-approval fails closed."""
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/version", timeout=timeout) as r:
            if r.status != 200:
                return False
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/ready", timeout=timeout) as r:
            if r.status != 200:
                return False
            return bool(json.loads(r.read().decode()).get("ok"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--allowlist", default="scripts/auto_approval_allowlist.json")
    parser.add_argument("--production-url", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--github-output")
    args = parser.parse_args(argv)

    files = subprocess.check_output(
        ["git", "diff", "--name-only", args.before, args.after], text=True).splitlines()
    patch = subprocess.check_output(
        ["git", "diff", "--unified=0", args.before, args.after], text=True, errors="replace")
    categories = _load_allowlist(args.allowlist)
    prior_healthy = check_production_healthy(args.production_url) if args.production_url else False

    result = evaluate(files, patch, allowlist_categories=categories,
                      prior_deploy_healthy=prior_healthy)
    result.update({"before_sha": args.before, "commit": args.after})
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"auto_approve={str(result['eligible']).lower()}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
