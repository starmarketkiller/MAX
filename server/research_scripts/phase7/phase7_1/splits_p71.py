#!/usr/bin/env python3
"""Phase 7.1 - Confini di split condivisi, IDENTICI a quelli gia'
materializzati in Phase 7.0B (server/research_scripts/phase7/
partition_manifest_v1.json) - copiati qui come costanti Python per
comodita' di join su pandas, non ridichiarati/ricalcolati."""
import pandas as pd

SPLIT_BOUNDARIES_DATES = {
    "discovery": (pd.Timestamp("2023-02-04", tz="UTC"), pd.Timestamp("2024-08-03T23:59:59", tz="UTC")),
    "internal_validation": (pd.Timestamp("2024-08-04", tz="UTC"), pd.Timestamp("2025-05-03T23:59:59", tz="UTC")),
    "locked_validation": (pd.Timestamp("2025-05-04", tz="UTC"), pd.Timestamp("2026-02-03T23:59:59", tz="UTC")),
    "final_holdout": (pd.Timestamp("2026-02-04", tz="UTC"), pd.Timestamp("2026-09-16T23:59:59", tz="UTC")),
}


def assign_split_p71(bar_time_utc) -> str:
    for name, (start, end) in SPLIT_BOUNDARIES_DATES.items():
        if start <= bar_time_utc <= end:
            return name
    return "BUFFER"
