#!/usr/bin/env python3
"""PR7 — Generatore del contratto Settings (schema + default canonici).

Elimina i default divergenti: oggi i valori vivono in `NXS_Inputs.mqh`, backend
`DEFAULT_SETTINGS`, fallback frontend e seed. Qui il backend diventa la fonte da
cui si estraggono i **default canonici** una volta, e lo **schema metadata**
(tipo/bound/scope/safety) formalizza validazione e range.

Emette:
- `contracts/default-settings.json`  (valori canonici, schema_version)
- `contracts/settings.schema.json`   (metadata per chiave)

Rigenerare: `python3 contracts/generate_settings_schema.py` (idempotente).
"""
from __future__ import annotations
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_VERSION = 2

# Override curati per chiave: bound, scope, safety_class, hot_reload, descr.
# Le chiavi non elencate ricevono un default euristico dal tipo del valore.
META = {
    "RiskPercent":     dict(min=0.0, max=10.0, safety="RISK", desc="Rischio % per trade"),
    "MaxLot":          dict(min=0.0, max=100.0, safety="RISK", desc="Lotto massimo"),
    "MaxTradesPerDay": dict(min=0, max=500, safety="RISK", desc="Trade massimi al giorno"),
    "MaxConcurrent":   dict(min=0, max=50, safety="RISK", desc="Posizioni simultanee massime"),
    "MaxDailyDDPct":   dict(min=0.0, max=100.0, safety="RISK", desc="Drawdown giornaliero massimo %"),
    "MaxLossPosPct":   dict(min=0.0, max=100.0, safety="RISK", desc="Perdita massima per posizione %"),
    "ESL_Value":       dict(min=0.0, max=100.0, safety="RISK", desc="Equity stop loss"),
    "DPT_Value":       dict(min=0.0, max=100.0, safety="RISK", desc="Daily profit target"),
    "MinEntryScore":   dict(min=0, max=100, safety="STANDARD", desc="Score minimo di ingresso"),
    "MaxHoldHours":    dict(min=0, max=168, safety="STANDARD", desc="Ore massime di holding"),
    "AutoCloseMin":    dict(min=0, max=1440, safety="STANDARD"),
    "MarketCloseGMT":  dict(min=0, max=23, safety="STANDARD", desc="Ora GMT chiusura mercato"),
    "AntiRevengeMin":  dict(min=0, max=1440),
    "StrategyCooldownMin": dict(min=0, max=1440),
}
# score-like -> 0..100; ATR-mult-like -> 0..50
SCORE_KEYS = {"AsianScoreMin", "LondonScoreMin", "OverlapScoreMin", "NYScoreMin",
              "AfterNYScoreMin", "ADXRsiScoreCap", "ConfluenceBonus2",
              "ConfluenceBonus3", "ConfluenceBonus4"}


def infer(key, val):
    if isinstance(val, bool):
        t = "boolean"
    elif isinstance(val, int):
        t = "integer"
    else:
        t = "number"
    m = dict(META.get(key, {}))
    lo = m.get("min")
    hi = m.get("max")
    if t != "boolean" and lo is None:
        if key in SCORE_KEYS:
            lo, hi = 0.0, 100.0
        elif key.endswith(("ATR", "_Mult", "Pct", "AtrPct")) or "ATR" in key:
            lo, hi = 0.0, 50.0
        else:
            lo, hi = 0.0, 1e6
    rec = {
        "key": key,
        "type": t,
        "default": val,
        "scope": m.get("scope", "INSTANCE"),
        "hot_reload": m.get("hot_reload", True),
        "requires_restart": m.get("requires_restart", False),
        "safety_class": m.get("safety", "STANDARD"),
        "description": m.get("desc", key),
    }
    if t != "boolean":
        rec["minimum"] = lo
        rec["maximum"] = hi
    return rec


def load_defaults():
    """Seed dai default correnti del backend (una volta), poi idempotente."""
    sys.path.insert(0, os.path.join(ROOT, "server"))
    import app
    return dict(app.DEFAULT_SETTINGS)


def build():
    defaults = load_defaults()
    settings = [infer(k, v) for k, v in defaults.items()]
    settings.sort(key=lambda r: r["key"])
    schema = {
        "schema_version": SCHEMA_VERSION,
        "generator": "contracts/generate_settings_schema.py",
        "allow_unknown_keys": False,   # regola 1: chiavi ignote rifiutate
        "settings": settings,
    }
    default_doc = {
        "schema_version": SCHEMA_VERSION,
        "generated_from": "server DEFAULT_SETTINGS (seed) — poi fonte canonica",
        "settings": {r["key"]: r["default"] for r in settings},
    }
    return schema, default_doc


def main():
    schema, default_doc = build()
    with open(os.path.join(ROOT, "contracts", "settings.schema.json"), "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2); f.write("\n")
    with open(os.path.join(ROOT, "contracts", "default-settings.json"), "w", encoding="utf-8") as f:
        json.dump(default_doc, f, ensure_ascii=False, indent=2); f.write("\n")
    print(f"settings: {len(schema['settings'])} chiavi | schema_version {SCHEMA_VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
