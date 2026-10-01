#!/usr/bin/env python3
"""Deterministic fail-closed deploy risk classifier."""
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path

HIGH_PATHS = (
    "MQL5/", "server/nexus_security.py", "server/command_contract.py",
    "server/settings_contract.py", "server/nexus_retention.py", "server/migrations/",
    "server/auth", "contracts/command", "contracts/approval", "render.yaml",
    ".github/workflows/safe-deploy.yml", "scripts/classify_deploy_risk.py",
)
HIGH_WORDS = re.compile(r"(secret|password|billing|payment|live.?trading|order.?send|approval.?gate|drop table|delete from)", re.I)
MEDIUM_PATHS = ("server/", "frontend/", "contracts/", "deploy/", "server/Dockerfile",
                "server/requirements", "frontend/package")


def classify(files, patch_text=""):
    files = sorted(set(str(item).replace("\\", "/") for item in files if item))
    reasons = []
    for name in files:
        if any(name == prefix or name.startswith(prefix) for prefix in HIGH_PATHS):
            reasons.append(f"HIGH_RISK_PATH:{name}")
    if HIGH_WORDS.search(patch_text or ""):
        reasons.append("HIGH_RISK_CONTENT_PATTERN")
    if reasons:
        risk = "HIGH_RISK"
    elif any(any(name == prefix or name.startswith(prefix) for prefix in MEDIUM_PATHS)
             for name in files):
        risk, reasons = "MEDIUM_RISK", ["RUNTIME_OR_BUILD_CHANGE"]
    else:
        risk, reasons = "LOW_RISK", ["NON_RUNTIME_CHANGE"]
    return {"schema_version": 1, "risk": risk, "files": files, "reasons": reasons,
            "automatic_deploy_allowed": risk in {"LOW_RISK", "MEDIUM_RISK"},
            "approval_state": "WAITING_APPROVAL" if risk == "HIGH_RISK" else "NOT_REQUIRED"}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True); parser.add_argument("--after", required=True)
    parser.add_argument("--output", required=True); parser.add_argument("--github-output")
    args = parser.parse_args(argv)
    files = subprocess.check_output(["git", "diff", "--name-only", args.before, args.after], text=True).splitlines()
    patch = subprocess.check_output(["git", "diff", "--unified=0", args.before, args.after], text=True,
                                    errors="replace")
    result = {**classify(files, patch), "before_sha": args.before, "commit": args.after}
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(f"risk={result['risk']}\nauto_allowed={str(result['automatic_deploy_allowed']).lower()}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
