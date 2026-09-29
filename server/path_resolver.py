"""Canonical runtime path resolution for checkout and flattened Docker layouts."""
from __future__ import annotations

import os
from pathlib import Path


def resolve_contracts_dir(start_file: str | os.PathLike[str] | None = None) -> Path:
    """Return the existing canonical contracts directory or fail closed.

    Resolution order is explicit environment configuration first, followed by
    the nearest existing ``contracts`` directory while walking up from the
    caller. This supports both ``repo/server/...`` checkouts and Render's
    flattened ``/app/...`` image without relying on a fixed parent count.
    """
    configured = os.environ.get("NEXUS_CONTRACTS_DIR")
    if configured:
        candidate = Path(configured).expanduser().resolve()
        if candidate.is_dir():
            return candidate
        raise FileNotFoundError(f"NEXUS_CONTRACTS_DIR does not exist: {candidate}")

    origin = Path(start_file or __file__).resolve()
    current = origin if origin.is_dir() else origin.parent
    for directory in (current, *current.parents):
        candidate = directory / "contracts"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"Unable to locate contracts directory from {origin}")


def resolve_project_root(start_file: str | os.PathLike[str] | None = None) -> Path:
    """Return the directory containing the canonical contracts directory."""
    return resolve_contracts_dir(start_file).parent
