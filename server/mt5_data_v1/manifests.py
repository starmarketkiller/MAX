"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - costruzione Run Manifest e Account
Manifest (contracts/mt5-run-manifest-v1.schema.json,
contracts/mt5-account-manifest-v1.schema.json). Generalizza il pattern
IMMUTABLE_RUN_MANIFEST di server/research_scripts/phase7/phase7_8g/
collect_immutable_run_manifest.py: raccolta PRIMA di ogni interpretazione,
nessun verdetto qui dentro.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from . import canonical


def make_artifact_entry(artifact_type: str, source_path: str, sha256: str,
                        dest_path: Optional[str] = None, size_bytes: Optional[int] = None,
                        row_count: Optional[int] = None) -> dict:
    return {
        "artifact_type": artifact_type,
        "source_path": str(source_path).replace("\\", "/"),
        "dest_path": str(dest_path).replace("\\", "/") if dest_path else None,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "row_count": row_count,
        "collected_at": canonical.utc_now_iso(),
    }


def artifact_entry_from_file(artifact_type: str, path: str | Path, dest_path: Optional[str] = None,
                             row_count: Optional[int] = None) -> dict:
    p = Path(path)
    return make_artifact_entry(
        artifact_type=artifact_type,
        source_path=str(p),
        sha256=canonical.file_sha256(p),
        dest_path=dest_path,
        size_bytes=p.stat().st_size if p.exists() else None,
        row_count=row_count,
    )


def build_run_manifest(run_id: str, account_id: str, artifacts: List[dict], *,
                       terminal_role: str = "UNKNOWN", ea_name: Optional[str] = None,
                       ea_version: Optional[str] = None, strategy_registry_version: Optional[str] = None,
                       symbol: Optional[str] = None, timeframe: Optional[str] = None,
                       period_start: Optional[str] = None, period_end: Optional[str] = None,
                       ea_build_identity: Optional[dict] = None) -> dict:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "account_id": account_id,
        "terminal_role": terminal_role,
        "ea_name": ea_name,
        "ea_version": ea_version,
        "strategy_registry_version": strategy_registry_version,
        "symbol": symbol,
        "timeframe": timeframe,
        "period_start": period_start,
        "period_end": period_end,
        "generated_at": canonical.utc_now_iso(),
        "collected_before_any_interpretation": True,
        "no_verdict_computed_here": True,
        "ea_build_identity": ea_build_identity or {"ex5_sha256": None, "source_sha256": None, "ex5_mtime": None},
        "artifacts": artifacts,
    }


def build_account_manifest(account_id: str, *, environment: str = "UNKNOWN",
                           broker: Optional[str] = None, server: Optional[str] = None,
                           base_currency: Optional[str] = None, runs: Optional[List[dict]] = None,
                           import_log: Optional[List[dict]] = None, data_quality: Optional[dict] = None,
                           redaction_applied: bool = False) -> dict:
    return {
        "schema_version": 1,
        "account_id": account_id,
        "generated_at": canonical.utc_now_iso(),
        "environment": environment,
        "broker": broker,
        "server": server,
        "base_currency": base_currency,
        "runs": runs or [],
        "import_log": import_log or [],
        "data_quality": data_quality or {"status": "NOT_VERIFIED", "checks_passed": [], "checks_failed": []},
        "redaction_applied": redaction_applied,
    }
