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
#
# ASSUMPTION — questa mappa e' un'ASSERZIONE SCRITTA A MANO, non un dato
# estratto. Fase A ha verificato che 5 delle 6 righe indicano un bersaglio
# diverso dalla funzione realmente condivisa: `LONDON_BO` usa `sig_breakout`
# mentre `BREAKOUT_ACC` usa `sig_breakout_acc` (MM-05). La mappa NON viene
# corretta a mano — sarebbe un'altra asserzione: il generatore emette accanto
# il fatto verificabile (`research_function`, `research_shared_with`) e marca
# `proxy_target_shares_function`, cosi' la divergenza e' leggibile invece che
# nascosta. La risoluzione e' una decisione del proprietario (D4).
PROXY_MAP = {
    "LONDON_BO": "BREAKOUT_ACC", "RANGE_FADE": "BOLLINGER",
    "WEEKLY_EXP": "BREAKOUT_ACC", "LIQ_VOID": "FVG_CONT",
    "SH_BMS_RTO": "OB_MIT", "SMS_BMS_RTO": "OB_MIT",
}

# Le quattro classificazioni possibili di una collisione di implementazione,
# come definite dal proprietario. Nessuna e' assegnata automaticamente: finche'
# la collisione non e' risolta, la classificazione resta PENDING_OWNER_REVIEW.
COLLISION_CLASSIFICATIONS = (
    "INTENTIONAL_ALIAS",            # stesso concetto, due nomi
    "DISTINCT_CONCEPT_PROXY_IMPL",  # concetti diversi, implementati da un proxy
    "ACCIDENTAL_DUPLICATE",         # duplicazione non voluta
    "INCOMPLETE_PLACEHOLDER",       # segnaposto mai completato
)

# Mappa famiglia — TASSONOMIA PROVVISORIA (domain judgment, revisionabile).
# Non e' un dato estratto: e' un raggruppamento documentato per la UI.
FAMILY_MAP = {
    "ADX_RSI": "MOMENTUM", "MACD": "MOMENTUM", "TSI": "MOMENTUM",
    "RSI_DIV": "MOMENTUM", "SAR": "MOMENTUM",
    "BREAKOUT_ACC": "TREND", "EMA_PULLBACK": "TREND", "ICHIMOKU": "TREND",
    "LONDON_BO": "TREND",
    "BOLLINGER": "VOLATILITY", "BB_SQUEEZE": "VOLATILITY", "RANGE_FADE": "VOLATILITY",
    "FVG_CONT": "SMC", "FVG_MIT": "SMC", "IFVG": "SMC", "OB_MIT": "SMC",
    "ORDER_BLOCK": "SMC", "OTE_CONT": "SMC", "LIQ_VOID": "SMC", "DISP_REBAL": "SMC",
    "LIQ_SWEEP": "LIQUIDITY", "SH_BMS_RTO": "LIQUIDITY", "SMS_BMS_RTO": "LIQUIDITY",
    "STRUCT_REACT": "LIQUIDITY", "TURTLE_SOUP": "LIQUIDITY", "MALAYSIAN_SNR": "LIQUIDITY",
    "THREE_BAR_DELIVERY_BREAK": "LIQUIDITY", "BJORGUM": "LIQUIDITY",
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
    # Fase A: gli assenti NON diventano piu' "*". Un timeframe non dichiarato e'
    # un'assenza (`null`), non un'affermazione di universalita' (MM-07).
    return tf   # es. {"ADX_RSI": "D1", ...}


def backtest_functions():
    """{chiave STRATEGIES: nome della funzione di segnale} — fatto, non stima."""
    sys.path.insert(0, os.path.join(ROOT, "server"))
    import backtest
    smap = getattr(backtest, "STRATEGIES", {}) or {}
    return {k: getattr(v, "__name__", str(v)) for k, v in smap.items()}


def backtest_names():
    return set(backtest_functions())


CURRENT_ROUND = None   # dedotto dal knowledge base in build()


def evidence_of(entry):
    """Stato dell'evidenza di UNA strategia, derivato dal knowledge base.

    Tre stati, come richiesto dal proprietario:

    - `MEASURED`   passata isolata completata sul round corrente;
    - `SURROGATE`  esistono numeri, ma non del round corrente (o non
                   confermati come completati): non sono attribuibili al codice
                   di oggi e non vanno letti come se lo fossero;
    - `UNKNOWN`    nessuna passata isolata: assenza di misura, non misura di
                   assenza.
    """
    sweep = entry.get("ultimo_sweep") or {}
    trades = entry.get("trade")
    if trades is None:
        status, current = "UNKNOWN", "MISSING"
        source_round = None
    elif sweep.get("round") == CURRENT_ROUND and sweep.get("completed") is True:
        status, current = "MEASURED", "PRESENT"
        source_round = sweep.get("round")
    else:
        status, current = "SURROGATE", "MISSING"
        source_round = (sweep.get("round")
                        or (f"round precedente (file {sweep['data_file']})"
                            if sweep.get("data_file") else "non registrato"))
    return {
        "historical_status": status,
        "source_round": source_round,
        "current_isolated_run": current,
        "run_id": sweep.get("run_id"),
        "trades": trades,
        "profit_factor": entry.get("PF"),
        "winrate_pct": entry.get("WR_pct"),
        "expectancy_R": entry.get("expectancy_R"),
        "note": entry.get("nota_sweep"),
    }


def status_from_stato(stato):
    s = (stato or "").lower()
    if "disabilitata in produzione" in s:
        return "DISABLED"
    if s == "attiva":
        return "ACTIVE"
    return "EXPERIMENTAL"


def build():
    global CURRENT_ROUND
    kb = json.load(open(os.path.join(ROOT, "knowledge/strategy_database.json"),
                        encoding="utf-8"))
    kn = kb["strategie"]
    ea_tf = parse_ea_tf_map()
    funcs = backtest_functions()
    bt = set(funcs)
    canon_ids = {s["nome"] for s in kn}

    # Il round corrente non e' una costante scritta a mano: e' il round citato
    # dalle passate dichiarate completate. Se le passate non concordano, la
    # nozione stessa di "round corrente" non esiste e il generatore si ferma.
    rounds = {(s.get("ultimo_sweep") or {}).get("round")
              for s in kn if (s.get("ultimo_sweep") or {}).get("completed") is True}
    rounds.discard(None)
    if len(rounds) > 1:
        raise SystemExit(f"passate completate su round diversi: {sorted(rounds)}")
    CURRENT_ROUND = rounds.pop() if rounds else None

    # selector_index: derivato dal CODICE, non trascritto. Il knowledge base
    # resta la fonte canonica dell'anagrafica, ma su questo campo il codice ha
    # l'ultima parola e una divergenza e' un errore, non una preferenza (MM-01).
    sys.path.insert(0, os.path.join(ROOT, "contracts"))
    from extract_selectors import selector_map, toggle_map
    sel_code = selector_map()
    toggles = toggle_map()
    for s in kn:
        sid = s["nome"]
        declared, actual = s.get("selector_index"), sel_code.get(sid)
        if actual is None:
            raise SystemExit(f"{sid}: nessun selector nel codice MQL5")
        if declared is not None and declared != actual:
            raise SystemExit(
                f"{sid}: selector_index {declared} nel knowledge base, "
                f"{actual} nel codice MQL5 — riallineare il knowledge base")

    # Collisioni di implementazione: quali strategie condividono la STESSA
    # funzione di segnale. Derivato dal codice, dopo aver risolto gli alias
    # (due chiavi della stessa strategia non sono una collisione).
    alias_to_canon = {a: sid for sid, al in ALIASES.items() for a in al}
    by_func = {}
    for key, fn in funcs.items():
        by_func.setdefault(fn, set()).add(alias_to_canon.get(key, key))

    records = []

    # --- 37 strategie LIVE (dal knowledge canonico) ---
    for s in sorted(kn, key=lambda x: x["nome"]):
        sid = s["nome"]
        aliases = ALIASES.get(sid, [])
        # research: presente in backtest per id o per un alias
        research = sid in bt or any(a in bt for a in aliases)
        status = status_from_stato(s.get("stato"))
        tf = ea_tf.get(sid)
        fn = funcs.get(sid) or next((funcs[a] for a in aliases if a in funcs), None)
        shared = sorted(by_func.get(fn, set()) - {sid}) if fn else []
        proxy = PROXY_MAP.get(sid)
        tog = toggles.get(sid, {})
        code_default = tog.get("default")
        records.append({
            "strategy_id": sid,
            "display_name": DISPLAY.get(sid, sid.replace("_", " ").title()),
            "aliases": aliases,
            "family": FAMILY_MAP.get(sid, "UNCLASSIFIED"),
            "status": status,
            "selector_index": sel_code[sid],
            "live_implementation": True,
            "research_implementation": bool(research),
            "research_parity": "PROXY" if proxy else ("APPROXIMATE" if research else "NOT_IMPLEMENTED"),
            "proxy_for": proxy,
            # Fatto verificabile accanto all'asserzione PROXY_MAP: la funzione
            # research realmente usata coincide con quella del bersaglio? (MM-05)
            "proxy_target_shares_function": (
                None if not proxy else bool(fn and fn == funcs.get(proxy))),
            "research_function": fn,
            "research_shared_with": shared,
            "implementation_collision": (None if not shared else {
                "kind": "IMPLEMENTATION_COLLISION",
                "status": "UNRESOLVED",
                "classification": "PENDING_OWNER_REVIEW",
                "candidate_classifications": list(COLLISION_CLASSIFICATIONS),
                "shared_function": fn,
                "partners": shared,
                # regola operativa data dal proprietario: finche' la collisione
                # non e' risolta, le analisi di diversificazione contano il
                # gruppo come UN SOLO generatore di segnali. Gli id restano.
                "counts_as_independent_signal_generator":
                    sid == min([sid] + shared),
            }),
            # `null` = non dichiarato. Non "*", che significherebbe "tutti".
            "supported_symbols": None,
            "supported_timeframes": [tf] if tf else None,
            # `default_enabled` e `auto_disable_eligible` restano DERIVATI DALLO
            # STATO DICHIARATO: cambiarli sposterebbe il potere del control
            # plane, che in Fase A non si tocca. Il fatto operativo e'
            # `code_default_enabled`; dove i due divergono lo dice
            # `declaration_conflict` (MM-02, decisione D3).
            "default_enabled": status == "ACTIVE",
            "auto_disable_eligible": status == "ACTIVE",
            "code_toggle": tog.get("toggle"),
            "code_default_enabled": code_default,
            "declaration_conflict": (None if code_default == (status == "ACTIVE") else {
                "code_default": "ENABLED" if code_default else "DISABLED",
                "registry_status": status,
                "dashboard_auto_disable": (
                    "ALLOWED" if status == "ACTIVE" else "BLOCKED"),
                "resolution": "PENDING_OWNER_DECISION",
            }),
            "evidence": evidence_of(s),
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
            "proxy_target_shares_function": None,
            "research_function": funcs.get(sid),
            "research_shared_with": sorted(by_func.get(funcs.get(sid), set()) - {sid}),
            "implementation_collision": None,
            "supported_symbols": None,
            "supported_timeframes": None,
            "default_enabled": False,
            "auto_disable_eligible": False,
            "code_toggle": None,
            "code_default_enabled": None,
            "declaration_conflict": None,
            "evidence": {
                "historical_status": "UNKNOWN",
                "source_round": None,
                "current_isolated_run": "NOT_APPLICABLE",
                "run_id": None, "trades": None, "profit_factor": None,
                "winrate_pct": None, "expectancy_R": None,
                "note": "strategia di sola ricerca: nessuna passata isolata EA",
            },
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
            "MQL5 via contracts/extract_selectors.py (selector_index, interruttori)",
            "server/backtest.py (STRATEGIES)",
        ],
        "note_family": "FAMILY_MAP e' una tassonomia provvisoria (domain judgment), non un dato estratto.",
        "note_default_enabled": (
            "`default_enabled` e `auto_disable_eligible` derivano dallo STATO "
            "DICHIARATO nel knowledge base. Il fatto operativo e' "
            "`code_default_enabled`, letto dagli input MQL5. Dove i due "
            "divergono, `declaration_conflict` lo dichiara: la riconciliazione "
            "e' una decisione del proprietario, non del generatore."),
        "note_null": (
            "`null` in `supported_symbols`/`supported_timeframes` significa NON "
            "DICHIARATO. Non significa 'tutti': prima era scritto \"*\", che "
            "trasformava un'assenza in un'affermazione di universalita'."),
        "note_collision": (
            "Le strategie con `implementation_collision` condividono la stessa "
            "funzione del motore research. Gli id restano distinti; finche' la "
            "collisione e' UNRESOLVED, le analisi di diversificazione devono "
            "contare il gruppo come UN SOLO generatore di segnali "
            "(`counts_as_independent_signal_generator`)."),
        "current_sweep_round": CURRENT_ROUND,
        "counts": {
            "total": len(records),
            "live": sum(1 for r in records if r["live_implementation"]),
            "research_only": sum(1 for r in records if r["status"] == "RESEARCH_ONLY"),
            "evidence_measured": sum(
                1 for r in records if r["evidence"]["historical_status"] == "MEASURED"),
            "evidence_surrogate": sum(
                1 for r in records if r["evidence"]["historical_status"] == "SURROGATE"),
            "evidence_unknown": sum(
                1 for r in records
                if r["evidence"]["historical_status"] == "UNKNOWN" and r["live_implementation"]),
            "implementation_collisions": sum(
                1 for r in records if r["implementation_collision"]),
            "declaration_conflicts": sum(
                1 for r in records if r["declaration_conflict"]),
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
        coll = r.get("implementation_collision")
        values = [r["strategy_id"], r["display_name"], r["family"],
                  r["live_implementation"], r["research_implementation"],
                  # Fase A / MM-09: la dashboard mostrava 37 strategie tutte
                  # uguali. Questi tre campi sono il minimo per distinguere
                  # misurata / surrogata / ignota senza aprire il registro.
                  r["evidence"]["historical_status"],
                  r["evidence"]["source_round"],
                  bool(coll),
                  (coll or {}).get("partners") or [],
                  r.get("proxy_for")]
        rows.append("  " + json.dumps(values, ensure_ascii=False, separators=(",", ":")) + ",")
    js = """// Generated by contracts/generate_registry.py. Do not edit.
export const STRATEGY_REGISTRY = [
%s
].map(([strategy_id, display_name, family, live_implementation, research_implementation, evidence_status, evidence_source_round, has_collision, collision_partners, proxy_for]) => ({
  strategy_id, display_name, family, live_implementation, research_implementation,
  evidence_status, evidence_source_round, has_collision, collision_partners, proxy_for,
}));

export const LIVE_STRATEGIES = STRATEGY_REGISTRY.filter((s) => s.live_implementation);
export const LIVE_STRATEGY_IDS = LIVE_STRATEGIES.map((s) => s.strategy_id);
export const LIVE_STRATEGY_COUNT = LIVE_STRATEGIES.length;
export const RESEARCH_STRATEGY_IDS = STRATEGY_REGISTRY.filter((s) => s.research_implementation).map((s) => s.strategy_id);

// MEASURED  = passata isolata completata sul round corrente
// SURROGATE = esistono numeri, ma di un altro round: non descrivono questo codice
// UNKNOWN   = nessuna passata isolata (assenza di misura, non misura di assenza)
export const EVIDENCE_STATUS = { MEASURED: "MEASURED", SURROGATE: "SURROGATE", UNKNOWN: "UNKNOWN" };
export const EVIDENCE_LABEL = {
  MEASURED: "Misurata",
  SURROGATE: "Dato surrogato",
  UNKNOWN: "Mai misurata",
};

export function requireStrategy(strategyId) {
  const record = STRATEGY_REGISTRY.find((s) => s.strategy_id === strategyId);
  if (!record) throw new Error(`unknown strategy_id: ${strategyId}`);
  return record;
}

// Finche' una collisione e' irrisolta, il gruppo vale UN generatore di segnali:
// contarne due sovrastima la diversificazione. Gli id restano tutti.
export function independentSignalGenerators(ids = LIVE_STRATEGY_IDS) {
  const seen = new Set();
  return ids.filter((id) => {
    const r = STRATEGY_REGISTRY.find((s) => s.strategy_id === id);
    if (!r || !r.has_collision) return true;
    const key = [id, ...r.collision_partners].sort().join("+");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
""" % "\n".join(rows)
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
