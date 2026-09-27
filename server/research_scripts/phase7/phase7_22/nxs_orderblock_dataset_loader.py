#!/usr/bin/env python3
"""Phase 7.22 - loader condiviso per il dataset economico canonico
ORDER_BLOCK (build_canonical_economic_dataset.py)."""
import json
import os

PHASE722_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(PHASE722_DIR, "canonical_economic_dataset_v1.json")


def load_events():
    with open(DATASET_PATH, encoding="utf-8") as f:
        doc = json.load(f)
    payload = doc["payload"]
    if payload.get("status") == "RUN_NOT_YET_CAPTURED":
        return []
    return payload["events"]


def net_pnl(e):
    return e["net_pnl"]


def risk_r(e):
    """Distanza SL in price units (= $ a lotto fisso 0.01 su GOLD),
    calcolata indipendentemente dal campo r_multiple del CSV (ambiguo -
    vedi nota nel dataset)."""
    return abs(e["entry_price"] - e["entry_sl"])


def net_pnl_in_r(e):
    r = risk_r(e)
    if r <= 0:
        return None
    return net_pnl(e) / r


def direction_label(e):
    return {1: "BUY", -1: "SELL", 0: "UNKNOWN"}[e["direction"]]


def split_by_direction(events):
    return {"ALL": events, "BUY": [e for e in events if e["direction"] == 1],
           "SELL": [e for e in events if e["direction"] == -1]}
