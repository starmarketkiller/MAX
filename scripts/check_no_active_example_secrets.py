#!/usr/bin/env python3
"""Fail when the public NEXUS example token is active in tracked runtime config.

The check deliberately distinguishes executable/default assignments from
comments, security regression fixtures, and versioned non-runtime artifacts.
It scans Git's tracked-file list so generated/untracked files cannot affect CI.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable

EXAMPLE_TOKEN = "NEXUS_BRIDGE_TOKEN_2026"
CI_FIXTURE_MARKER = "CI_NEGATIVE_SECURITY_FIXTURE"
COMMENT_PREFIXES = ("#", "//", "/*", "*", "<!--")
DOCUMENT_SUFFIXES = {".md", ".rst"}


def _is_test_fixture(path: PurePosixPath) -> bool:
    return "tests" in path.parts or path.name.startswith("test_") or path.name.endswith("_test.py")


def _is_non_runtime_artifact(path: PurePosixPath) -> bool:
    return bool(path.parts and path.parts[0] == "results")


def find_active_occurrences(path: str, text: str) -> list[tuple[int, str]]:
    """Return example-token occurrences that can configure active runtime code."""
    repo_path = PurePosixPath(path.replace("\\", "/"))
    if repo_path.suffix.lower() in DOCUMENT_SUFFIXES:
        return []
    if _is_test_fixture(repo_path) or _is_non_runtime_artifact(repo_path):
        return []
    if repo_path.as_posix() == "scripts/check_no_active_example_secrets.py":
        return []

    lines = text.splitlines()
    violations = []
    for index, line in enumerate(lines):
        if EXAMPLE_TOKEN not in line:
            continue
        stripped = line.lstrip()
        if stripped.startswith(COMMENT_PREFIXES):
            continue
        # Explicit placeholder rejection is a security guard, not a default.
        if re.search(r"(?:==|!=|compare_digest\s*\(|_is_placeholder\s*\()", line):
            continue
        # A CI negative test must opt in locally; no path-wide workflow allowlist.
        context = "\n".join(lines[max(0, index - 8):index + 1])
        if repo_path.parts[:2] == (".github", "workflows") and CI_FIXTURE_MARKER in context:
            continue
        violations.append((index + 1, line.strip()))
    return violations


def tracked_files(root: Path) -> Iterable[str]:
    output = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True,
    ).stdout.decode("utf-8", errors="surrogateescape")
    return (item for item in output.split("\0") if item)


def check_repository(root: Path) -> list[tuple[str, int, str]]:
    violations = []
    for relative in tracked_files(root):
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_no, line in find_active_occurrences(relative, text):
            violations.append((relative, line_no, line))
    return violations


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    violations = check_repository(root)
    if violations:
        print("Active public example token found in runtime/configurable context:", file=sys.stderr)
        for path, line_no, line in violations:
            print(f"  {path}:{line_no}: {line}", file=sys.stderr)
        return 1
    print("OK: no active public example token in tracked runtime/configurable files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
