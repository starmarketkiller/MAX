#!/usr/bin/env python3
"""PR6 — Generatore deterministico del Canonical Strategy Registry.

Costruisce `contracts/strategy-registry.json` (unica fonte di verita') a partire
dalle fonti REALI del repository, senza inventare:

- `knowledge/strategy_database.json` -> id canonici (37 live), selector_index,
  stato, nota di rename (ELLIOTT);
- `MQL5/Include/NEXUS_v1/NXS_StrategyProfiles.mqh` (`NXS_Profile_TF`) -> timeframe
  supportato (source of truth EA);
- `server/backtest.py` (`STRAT_MAP`) -> presenza research + le 4 SCALP_* research-only.

Campi FATTUALI (id, alias, selector_index, live/research_implementation, TF, status)
derivano dai dati. Campi di TASSONOMIA (`family`) usano una mappa DOCUMENTATA e
provvisoria (FAMILY_MAP qui sotto): modificabile senza toccare il codice.

Rigenerare: `python3 contracts/generate_registry.py`  (idempotente).
Validare:   `python3 contracts/validate_registry.py`
"""
from __future__ import annotations
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_VERSION = 1

# Alias noti: id canonico -> alias storici usati nel codice/dati.
ALIASES = {"THREE_BAR_DELIVERY_BREAK": ["CISD"]}

# Implementazioni research che oggi riusano esplicitamente un'altra logica.
PROXY_MAP = {
    "LONDON_BO": "BREAKOUT_ACC", "RANGE_FADE": "BOLLINGER",
    "WEEKLY_EXP": "BREAKOUT_ACC", "LIQ_VOID": "FVG_CONT",
    "SH_BMS_RTO": "OB_MIT", "SMS_BMS_RTO": "OB_MIT",
}

# Mappa famiglia — TASSONOMIA PROVVISORIA (domain judgment, revisionabile).
# Non e' un dato estratto: e' un raggruppamento documentato per la UI.
FAMILY_MAP = {
    "ADX_RSI": "MOMENTUM", "MACD": "MOMENTUM", "TSI": "MOMENTUM",
    "RSI_DIV": "MOMENTUM", "SAR": "MOMENTUM",
    "BREAKOUT_ACC": "TREND", "EMA_PULLBACK": "TREND", "ICHIMOKU": "TREND",
    "LONDON_BO": "TREND", "Z_SCORE_BREAKOUT": "TREND",
    "BOLLINGER": "VOLATILITY", "BB_SQUEEZE": "VOLATILITY", "RANGE_FADE": "VOLATILITY",
    "FVG_CONT": "SMC", "FVG_MIT": "SMC", "IFVG": "SMC", "OB_MIT": "SMC",
    "ORDER_BLOCK": "SMC", "OTE_CONT": "SMC", "LIQ_VOID": "SMC", "DISP_REBAL": "SMC",
    "LIQ_SWEEP": "LIQUIDITY", "SH_BMS_RTO": "LIQUIDITY", "SMS_BMS_RTO": "LIQUIDITY",
    "STRUCT_REACT": "LIQUIDITY", "TURTLE_SOUP": "LIQUIDITY", "MALAYSIAN_SNR": "LIQUIDITY",
    "THREE_BAR_DELIVERY_BREAK": "LIQUIDITY", "BJORGUM": "LIQUIDITY",
    "SWING_FALSEBREAK": "LIQUIDITY",
    "JUDAS_SWING": "SESSION", "LDN_REVERSAL": "SESSION", "NY_REVERSAL": "SESSION",
    "SILVER_BULLET": "SESSION", "WEEKLY_EXP": "SESSION",
    "AMD_CONT": "AMD", "AMD_REVERSAL": "AMD", "PO3": "AMD",
    "ELLIOTT": "PATTERN",
    "SCALP_EMA": "SCALP", "SCALP_BB_FADE": "SCALP",
    "SCALP_RSI_SNAP": "SCALP", "SCALP_RANGE_BRK": "SCALP",
}

DISPLAY = {  # solo dove il nome leggibile differisce in modo non banale
    "ADX_RSI": "ADX + RSI", "RSI_DIV": "RSI Divergence", "MACD": "MACD",
    "SAR": "Parabolic SAR", "TSI": "True Strength Index",
    "THREE_BAR_DELIVERY_BREAK": "Three-Bar Delivery Break (CISD)",
    "ELLIOTT": "Elliott (rename pending: FIVE_SWING_IMPULSE)",
}


def _read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def parse_ea_tf_map():
    """Estrae NXS_Profile_TF: id -> timeframe (source of truth EA)."""
    txt = _read("MQL5/Include/NEXUS_v1/NXS_StrategyProfiles.mqh")
    m = re.search(r"NXS_Profile_TF\(const string name\)\{(.+?)\n\}", txt, re.S)
    tf = {}
    if m:
        for name, period in re.findall(r'name == "([A-Z0-9_]+)"\)\s*return (PERIOD_\w+)', m.group(1)):
            tf[name] = period.replace("PERIOD_", "")
    return tf   # es. {"ADX_RSI": "D1", ...}; assenti = nessun vincolo (*)


def backtest_names():
    sys.path.insert(0, os.path.join(ROOT, "server"))
    import backtest
    smap = getattr(backtest, "STRATEGIES", {}) or {}   # dict id->signal fn
    return set(smap.keys())


def status_from_stato(stato):
    s = (stato or "").lower()
    if "disabilitata in produzione" in s:
        return "DISABLED"
    if s == "attiva":
        return "ACTIVE"
    return "EXPERIMENTAL"


def build():
    kn = json.load(open(os.path.join(ROOT, "knowledge/strategy_database.json"),
                       encoding="utf-8"))["strategie"]
    ea_tf = parse_ea_tf_map()
    bt = backtest_names()
    canon_ids = {s["nome"] for s in kn}

    records = []

    # --- 37 strategie LIVE (dal knowledge canonico) ---
    for s in sorted(kn, key=lambda x: x["nome"]):
        sid = s["nome"]
        aliases = ALIASES.get(sid, [])
        # research: presente in backtest per id o per un alias
        research = sid in bt or any(a in bt for a in aliases)
        status = status_from_stato(s.get("stato"))
        tf = ea_tf.get(sid)
        records.append({
            "strategy_id": sid,
            "display_name": DISPLAY.get(sid, sid.replace("_", " ").title()),
            "aliases": aliases,
            "family": FAMILY_MAP.get(sid, "UNCLASSIFIED"),
            "status": status,
            "selector_index": s.get("selector_index"),
            "live_implementation": True,
            "research_implementation": bool(research),
            "research_parity": "PROXY" if sid in PROXY_MAP else ("APPROXIMATE" if research else "NOT_IMPLEMENTED"),
            "proxy_for": PROXY_MAP.get(sid),
            "supported_symbols": ["*"],
            "supported_timeframes": [tf] if tf else ["*"],
            "default_enabled": status == "ACTIVE",
            "auto_disable_eligible": status == "ACTIVE",
            "risk_class": "STANDARD",
            "schema_version": SCHEMA_VERSION,
        })

    # --- strategie RESEARCH_ONLY (SCALP_*, native del simulatore Python) ---
    for sid in sorted(bt - canon_ids - {a for al in ALIASES.values() for a in al}):
        records.append({
            "strategy_id": sid,
            "display_name": sid.replace("_", " ").title(),
            "aliases": [],
            "family": FAMILY_MAP.get(sid, "SCALP"),
            "status": "RESEARCH_ONLY",
            "selector_index": None,
            "live_implementation": False,
            "research_implementation": True,
            "research_parity": "NOT_IMPLEMENTED",   # nessuna controparte live
            "proxy_for": None,
            "supported_symbols": ["*"],
            "supported_timeframes": ["*"],
            "default_enabled": False,
            "auto_disable_eligible": False,
            "risk_class": "RESEARCH",
            "schema_version": SCHEMA_VERSION,
        })

    records.sort(key=lambda r: r["strategy_id"])
    out = {
        "schema_version": SCHEMA_VERSION,
        "generator": "contracts/generate_registry.py",
        "sources": [
            "knowledge/strategy_database.json",
            "MQL5/Include/NEXUS_v1/NXS_StrategyProfiles.mqh (NXS_Profile_TF)",
            "server/backtest.py (STRAT_MAP)",
        ],
        "note_family": "FAMILY_MAP e' una tassonomia provvisoria (domain judgment), non un dato estratto.",
        "counts": {
            "total": len(records),
            "live": sum(1 for r in records if r["live_implementation"]),
            "research_only": sum(1 for r in records if r["status"] == "RESEARCH_ONLY"),
        },
        "strategies": records,
    }
    return out


def main():
    out = build()
    path = os.path.join(ROOT, "contracts", "strategy-registry.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    write_adapters(out)
    print(f"scritto {path}: {out['counts']}")
    return 0


def write_adapters(out):
    """Genera gli adapter frontend e MQL dallo stesso artefatto canonico."""
    rows = []
    for r in out["strategies"]:
        values = [r["strategy_id"], r["display_name"], r["family"],
                  r["live_implementation"], r["research_implementation"]]
        rows.append("  " + json.dumps(values, ensure_ascii=False, separators=(",", ":")) + ",")
    js = """// Generated by contracts/generate_registry.py. Do not edit.\nexport const STRATEGY_REGISTRY = [\n%s\n].map(([strategy_id, display_name, family, live_implementation, research_implementation]) => ({\n  strategy_id, display_name, family, live_implementation, research_implementation,\n}));\n\nexport const LIVE_STRATEGIES = STRATEGY_REGISTRY.filter((s) => s.live_implementation);\nexport const LIVE_STRATEGY_IDS = LIVE_STRATEGIES.map((s) => s.strategy_id);\nexport const LIVE_STRATEGY_COUNT = LIVE_STRATEGIES.length;\nexport const RESEARCH_STRATEGY_IDS = STRATEGY_REGISTRY.filter((s) => s.research_implementation).map((s) => s.strategy_id);\n\nexport function requireStrategy(strategyId) {\n  const record = STRATEGY_REGISTRY.find((s) => s.strategy_id === strategyId);\n  if (!record) throw new Error(`unknown strategy_id: ${strategyId}`);\n  return record;\n}\n""" % "\n".join(rows)
    js_path = os.path.join(ROOT, "frontend", "src", "contracts", "strategyRegistry.js")
    os.makedirs(os.path.dirname(js_path), exist_ok=True)
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js)

    live = [r for r in out["strategies"] if r["live_implementation"]]
    aliases = [(a, r["strategy_id"]) for r in live for a in r.get("aliases", [])]
    alias_lines = "\n".join(f'   if(id=="{a}") id="{sid}";' for a, sid in aliases)
    known = " ||\n          ".join(f'id=="{r["strategy_id"]}"' for r in live)
    # AUD0-WEB-013: la telemetria elencava a mano un sottoinsieme "classico"
    # delle strategie, quindi il backend vedeva 16 voci su 37 e la deriva non
    # era rilevabile. L'elenco viene ora generato da QUESTO registro, unica
    # fonte di verita', ed esposto all'EA come tabella indicizzata.
    id_lines = "\n".join(
        f'   if(i=={i}) return "{r["strategy_id"]}";' for i, r in enumerate(live))
    mql = f'''// Generated by contracts/generate_registry.py. Do not edit.\n#ifndef __NXS_STRATEGY_REGISTRY_MQH__\n#define __NXS_STRATEGY_REGISTRY_MQH__\n\n#define NXS_STRATEGY_REGISTRY_SCHEMA {out["schema_version"]}\n#define NXS_LIVE_STRATEGY_COUNT {len(live)}\n\nstring NXS_StrategyCanonicalId(string strategyId){{\n   string id=strategyId;\n   int n=StringLen(id);\n   if(n>4 && StringSubstr(id,n-4)=="_NXR") id=StringSubstr(id,0,n-4);\n{alias_lines}\n   return id;\n}}\n\nbool NXS_StrategyKnown(string strategyId){{\n   string id=NXS_StrategyCanonicalId(strategyId);\n   return {known};\n}}\n\n// AUD0-WEB-013: elenco canonico indicizzato (0..NXS_LIVE_STRATEGY_COUNT-1).\n// La telemetria lo usa per dichiarare TUTTE le strategie live, invece di un\n// sottoinsieme scritto a mano che restava indietro a ogni aggiunta.\nstring NXS_StrategyIdAt(int i){{\n{id_lines}\n   return "";\n}}\n\n#endif\n'''
    mql_path = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyRegistry.mqh")
    with open(mql_path, "w", encoding="utf-8") as f:
        f.write(mql)


if __name__ == "__main__":
    sys.exit(main())
