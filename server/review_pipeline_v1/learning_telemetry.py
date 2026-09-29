#!/usr/bin/env python3
"""NEXUS TASK #0008 punto 16 - registra un record per ogni WORK_PRODUCT_V1
concluso, append-only (stessa convenzione di core/ledger.py). Nessun
fine-tuning qui: questo dataset serve in futuro al Router per imparare quali
task_type/work_type Ministral puo' gestire da solo - la lettura/uso di
questi dati resta un passo successivo, non svolto in #0008."""
import json
import os
from datetime import datetime, timezone

REVIEW_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME_STATE_DIR = os.path.join(REVIEW_DIR, "runtime_state")
DEFAULT_PATH = os.path.join(RUNTIME_STATE_DIR, "learning_telemetry_v1.jsonl")

_REQUIRED_FIELDS = ["producer_success", "review_required", "reviewer_selected", "issues_found",
                   "revision_count", "final_success", "premium_needed", "task_duration_seconds",
                   "failure_class"]


def record_learning_event(record, path=None):
    path = path or DEFAULT_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    missing = [f for f in _REQUIRED_FIELDS if f not in record]
    if missing:
        raise AssertionError(f"learning telemetry record incompleto, mancano: {missing}")
    entry = {"recorded_at": datetime.now(timezone.utc).isoformat(), **record}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_learning_events(path=None):
    path = path or DEFAULT_PATH
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
