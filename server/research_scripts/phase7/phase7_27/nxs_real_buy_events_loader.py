#!/usr/bin/env python3
"""Phase 7.27 - estrae SOLO gli eventi BUY reali gia' esistenti per le
3 strategie (nessuna nuova detection/strategia eseguita). dataset_id
allineato esattamente al GLOBAL_DATA_EXPOSURE_REGISTRY_V1 (Phase 7.26)
per poter marcare quali dataset vengono consumati da questo test."""
import os
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
P7 = os.path.join(ROOT, "server", "research_scripts", "phase7")
sys.path.insert(0, os.path.join(P7, "phase7_21"))
sys.path.insert(0, os.path.join(P7, "phase7_24"))
sys.path.insert(0, os.path.join(P7, "phase7_22"))


def _dt(s):
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S")


def load_breakout_acc_buy_events():
    from nxs_breakoutacc_dataset_loader import load_opened_events
    events = load_opened_events()
    out = []
    for e in events:
        if e["direction"] != 1:
            continue
        out.append({
            "strategy_identity": "BREAKOUT_ACC", "event_id": e["event_id"],
            "entry_time": _dt(e["entry_fill_time"]), "signal_price": e["signal_price"],
            "fill_price": e["entry_fill_price"],
            "dataset_id": "BREAKOUT_ACC::2019.02.21_2026.06.09",
        })
    return out


def load_order_block_buy_events():
    import json
    path = os.path.join(P7, "phase7_22", "canonical_economic_dataset_v1.json")
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)["payload"]
    out = []
    for e in payload["events"]:
        if e["direction"] != 1:
            continue
        out.append({
            "strategy_identity": "ORDER_BLOCK", "event_id": e["event_id"],
            "entry_time": _dt(e["entry_time"]), "signal_price": e["entry_price"],
            "fill_price": None,
            "dataset_id": "ORDER_BLOCK::2023.10.02_2026.08.24",
        })
    return out


def load_liq_sweep_buy_events():
    import json
    path = os.path.join(P7, "phase7_24", "liq_sweep_canonical_dataset_v1.json")
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)["payload"]
    out = []
    for e in payload["events"]:
        if e["lifecycle"] != "CLOSED" or e["direction"] != "BUY":
            continue
        out.append({
            "strategy_identity": "LIQ_SWEEP", "event_id": e["event_id"],
            "entry_time": _dt(e["entry"]["timestamp"]),
            "signal_price": e["entry"]["signal_reference_price"], "fill_price": None,
            "dataset_id": "LIQ_SWEEP::2023.10.02_2026.06.30",
        })
    return out


def load_all_buy_events():
    return {
        "BREAKOUT_ACC": load_breakout_acc_buy_events(),
        "ORDER_BLOCK": load_order_block_buy_events(),
        "LIQ_SWEEP": load_liq_sweep_buy_events(),
    }
