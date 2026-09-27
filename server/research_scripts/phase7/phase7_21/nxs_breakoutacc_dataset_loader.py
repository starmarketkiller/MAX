#!/usr/bin/env python3
"""Phase 7.21 - loader condiviso per il dataset canonico V2 di
BREAKOUT_ACC (Phase 7.9K). Nessuna logica di detection/strategia
reimplementata qui - solo lettura e calcoli economici derivati
(net P&L, R-multiple) sui campi GIA' presenti nel dataset."""
import json
import os

PHASE79K_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "phase7_9k"))
DATASET_PATH = os.path.join(PHASE79K_DIR, "breakout_acc_intended_d1_v2_dataset.json")


def load_all_events():
    with open(DATASET_PATH, encoding="utf-8") as f:
        doc = json.load(f)
    return doc["payload"]["events"], doc["canonical_sha256"]


def load_opened_events():
    """Solo gli eventi con esito economico reale (OPENED, 47/75) - gli
    unici su cui una P&L esiste."""
    events, _ = load_all_events()
    return [e for e in events if e["funnel_terminal_stage"] == "OPENED"]


def net_pnl(e):
    """P&L netto reale: realized_pnl (deal profit, gross) + swap +
    commissione - tutti campi gia' presenti nel dataset, nessun nuovo
    dato inventato."""
    return e["realized_pnl"] + e["realized_swap"] + e["realized_commission"]


def gross_pnl(e):
    return e["realized_pnl"]


def risk_r(e):
    """Distanza SL in price units (= $ a lotto fisso 0.01 per GOLD,
    verificato: |entry_fill_price - entry_sl| coincide esattamente col
    |realized_pnl| dei trade usciti a SL)."""
    return abs(e["entry_fill_price"] - e["entry_sl"])


def net_pnl_in_r(e):
    r = risk_r(e)
    if r <= 0:
        return None
    return net_pnl(e) / r


def direction_label(e):
    return "BUY" if e["direction"] == 1 else "SELL"


def split_by_direction(events):
    return ({"ALL": events, "BUY": [e for e in events if e["direction"] == 1],
            "SELL": [e for e in events if e["direction"] == -1]})
