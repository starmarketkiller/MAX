"""Portable, non-sensitive source paths for read-model provenance."""
from __future__ import annotations

from pathlib import Path


def repo_safe_path(path: Path | str, repo_root: Path | str) -> str:
    """Return a repo-relative path or a deterministic external fixture label.

    Read models normally consume repository artifacts, but fault-isolation tests
    and callers may supply files outside the checkout. Absolute external paths
    are machine-specific and may disclose local filesystem details, so only the
    filename is retained for those sources.
    """
    candidate = Path(path).resolve(strict=False)
    root = Path(repo_root).resolve(strict=False)
    try:
        return candidate.relative_to(root).as_posix()
    except ValueError:
        return f"external://{candidate.name}"
