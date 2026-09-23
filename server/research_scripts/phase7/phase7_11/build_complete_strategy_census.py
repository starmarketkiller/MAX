#!/usr/bin/env python3
"""Phase 7.11 - Complete Strategy Census. Costruisce l'inventario
completo di TUTTE le identita' strategia mai trovate nel repository,
incrociando fonti multiple - non assume che contracts/strategy-registry.json
sia esaustivo, lo verifica direttamente contro il codice sorgente.

Nessuna correzione o ritest applicato in questa fase - solo censimento.
"""
import json
import os
import re
import sys

PHASE711_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE711_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "cddf8a929f3bfc259fd1a56ee454d9c8f6508798"


def load_registry():
    return json.load(open(os.path.join(ROOT, "contracts", "strategy-registry.json"), encoding="utf-8"))


def load_strategy_database():
    return json.load(open(os.path.join(ROOT, "knowledge", "strategy_database.json"), encoding="utf-8"))


def extract_nxs_strategy_known():
    text = open(os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyRegistry.mqh"), encoding="utf-8").read()
    m = re.search(r"bool NXS_StrategyKnown\(string strategyId\)\{(.*?)\n\}", text, re.S)
    return set(re.findall(r'id=="([A-Z0-9_]+)"', m.group(1)))


def extract_nxs_strategy_id_at():
    text = open(os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyRegistry.mqh"), encoding="utf-8").read()
    pairs = re.findall(r'if\(i==(\d+)\) return "([A-Z0-9_]+)";', text)
    return [name for _, name in sorted(pairs, key=lambda t: int(t[0]))]


def extract_profile_tf():
    text = open(os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyProfiles.mqh"), encoding="utf-8").read()
    m = re.search(r"ENUM_TIMEFRAMES NXS_Profile_TF\(const string name\)\{(.*?)\n\}", text, re.S)
    pairs = re.findall(r'if\(name == "([A-Z0-9_]+)"\)\s*return (PERIOD_[A-Z0-9]+);', m.group(1))
    return dict(pairs)


def extract_backtest_strategies_dispatch():
    text = open(os.path.join(ROOT, "server", "backtest.py"), encoding="utf-8").read()
    m = re.search(r"^STRATEGIES\s*=\s*\{(.*?)\n\}", text, re.S | re.M)
    body = m.group(1)
    pairs = re.findall(r'["\']([A-Z0-9_]+)["\']\s*:\s*(sig_[a-z0-9_]+)', body)
    all_sig_defs = set(re.findall(r"^def (sig_[a-z0-9_]+)", text, re.M))
    dispatched_fns = set(fn for _, fn in pairs)
    orphaned = all_sig_defs - dispatched_fns
    return dict(pairs), sorted(orphaned)


def vault_doc_presence():
    strategie_dir = os.path.join(ROOT, "vault", "01-Trading", "Strategie")
    present = {}
    for fn in os.listdir(strategie_dir):
        if not fn.endswith(".md"):
            continue
        id_guess = fn[:-3].upper().replace(" ", "_")
        present[id_guess] = fn
    return present


# Trovato leggendo direttamente NXS_Strat_CRT()/NXS_Strat_FVG_Mitigation_Window() e i loro
# call site nel router (NEXUS_EA_v2.mq5) - VERIFICATO che entrambe le funzioni sono
# implementate e RAGGIUNGIBILI (selettore reale, chiamate dal collector), ma NESSUNA delle
# due e' presente in NXS_StrategyKnown() - quindi NXS_OpenTrade() le rifiuterebbe SEMPRE
# con gate UNKNOWN_STRATEGY se mai producessero dir!=DIR_NONE.
UNKNOWN_STRATEGY_REGISTRY_GAP = {
    "CRT": {"selector": 38, "default_enabled": False, "input_flag": "InpUseStrat_CRT"},
    "FVG_MIT_WINDOW": {"selector": 39, "default_enabled": True, "input_flag": "InpStrat_FVG_MIT_WINDOW"},
}

# Trovato leggendo NXS_ReusePerformancePack.mqh: 4 funzioni NXR_Strat_* definite ma con
# ZERO call site verificati in tutto l'albero MQL5/ (grep esaustivo) - contraddice una nota
# storica del vault ("NEXUS EA - Guida Completa...") che le descriveva come "il motore che
# esegue DAVVERO i trade live" per queste 4 identita' - correzione verificata sul codice
# attuale, non sulla narrazione storica.
NXR_SHADOW_ENGINE_FUNCTIONS = {
    "IFVG": "NXR_Strat_IFVG_Reversal", "FVG_MIT": "NXR_Strat_FVG_Mitigation",
    "OB_MIT": "NXR_Strat_OB_Mitigation", "MALAYSIAN_SNR": "NXR_Strat_MalaysianSNR",
}
NXR_ALIAS_SUFFIX_STRATEGIES = ["IFVG", "FVG_MIT", "OB_MIT", "MALAYSIAN_SNR", "STRUCT_REACT"]

# Trovato leggendo direttamente la funzione dispatcher: OB_MIT riusa BYTE PER BYTE
# NXS_Strat_OrderBlock()/NXS_OB_UpdateSide() - stesso trigger di ORDER_BLOCK, solo
# stratName/score floor diversi. Non e' un alias nel registro (ha un proprio selettore/
# stratName), ma condivide interamente l'implementazione.
SHARED_IMPLEMENTATION_NOTES = {
    "OB_MIT": "Condivide byte-per-byte l'implementazione di NXS_Strat_OrderBlock() - "
        "stesso trigger di ORDER_BLOCK, solo stratName/score floor diversi. Verificato "
        "leggendo NXS_Strategies.mqh riga ~355 (NXS_Strat_OB_Mitigation_Structural chiama "
        "NXS_OB_UpdateSide, la stessa funzione core di ORDER_BLOCK).",
}

# Trovato confrontando i commenti datati in server/backtest.py (STRATEGIES dispatch dict)
# contro PROXY_MAP in contracts/generate_registry.py: 4 delle 6 voci del PROXY_MAP sono
# STALE - le strategie hanno gia' una propria implementazione dedicata dal 04/08, ma
# PROXY_MAP (una mappa statica manuale, non derivata dinamicamente dal dispatch dict) non
# e' mai stata aggiornata. Verificato leggendo direttamente il dispatch dict corrente.
PROXY_MAP_STALENESS = {
    "LONDON_BO": {"registry_says_proxy_for": "BREAKOUT_ACC", "actual_dispatch_function": "sig_london_bo",
                  "verdict": "STALE - ha una propria implementazione dedicata dal 04/08 "
                             "(commento: 'fedele a NXS_Strat_LondonBO, prima proxy generico')."},
    "WEEKLY_EXP": {"registry_says_proxy_for": "BREAKOUT_ACC", "actual_dispatch_function": "sig_weekly_exp",
                   "verdict": "STALE - propria implementazione dal 04/08 (commento: 'fedele "
                              "a NXS_Strat_WeeklyRangeExp, prima condivideva sig_breakout con "
                              "LONDON_BO')."},
    "SH_BMS_RTO": {"registry_says_proxy_for": "OB_MIT", "actual_dispatch_function": "sig_sh_bms_rto",
                   "verdict": "STALE - propria implementazione dal 04/08 (commento: 'fedele a "
                              "NXS_SHBMS_UpdateSide, prima proxy sig_ob_mit')."},
    "SMS_BMS_RTO": {"registry_says_proxy_for": "OB_MIT", "actual_dispatch_function": "sig_sms_bms_rto",
                    "verdict": "STALE - propria implementazione dal 04/08 (commento: 'fedele a "
                               "NXS_Strat_SMS_BMS_RTO, prima proxy sig_ob_mit')."},
    "RANGE_FADE": {"registry_says_proxy_for": "BOLLINGER", "actual_dispatch_function": "sig_bollinger",
                   "verdict": "ACCURATO - ancora un proxy genuino, dispatch dict conferma "
                              "sig_bollinger."},
    "LIQ_VOID": {"registry_says_proxy_for": "FVG_CONT", "actual_dispatch_function": "sig_fvg_cont_ext",
                 "verdict": "ACCURATO - ancora un proxy genuino, dispatch dict conferma "
                            "sig_fvg_cont_ext."},
}

# I 20 candidati gia' classificati in Phase 7.10 per CROSS_TIMEFRAME_STATE_CONTAMINATION -
# riportati qui per popolare known_implementation_defects senza rileggere il codice.
PHASE_7_10_CLASSIFICATIONS = {
    "BREAKOUT_ACC": "DEFECT_CONFIRMED_FIXED_IN_7_9G", "BAR_UPDN": "DEFECT_CONFIRMED",
    "PIVOT_WICK": "DEFECT_CONFIRMED", "PMAX": "DEFECT_CONFIRMED", "TSI": "DEFECT_CONFIRMED",
    "BB_SQUEEZE": "DEFECT_CONFIRMED", "ORDER_BLOCK": "DEFECT_CONFIRMED",
    "SH_BMS_RTO": "DEFECT_CONFIRMED", "SH_BMS_RTO_V2": "DEFECT_CONFIRMED",
    "SILVER_BULLET": "DEFECT_CONFIRMED", "RANGE_FADE": "DEFECT_CONFIRMED",
    "MACD_SMA200": "SUSPECT", "ICHIMOKU_HULL_MACD": "SUSPECT", "3COMMAS_BOT": "SUSPECT",
    "RSI_DIV_PINE": "SUSPECT", "BOLLINGER": "SUSPECT",
    "LEVEL_CONFLUENCE": "SAFE", "LEVEL_CONFLUENCE_M5": "SAFE",
    "LEVEL_REACTION": "SAFE", "LEVEL_REACTION_M5": "SAFE",
    "WEEKLY_EXP": "SAFE", "WICK_SWEEP_RECLAIM": "SAFE", "WICK_SWEEP_REV": "SAFE",
}


def build():
    registry = load_registry()
    strat_db = load_strategy_database()
    known_set = extract_nxs_strategy_known()
    id_at_list = extract_nxs_strategy_id_at()
    profile_tf = extract_profile_tf()
    dispatch, orphaned_sig_fns = extract_backtest_strategies_dispatch()
    vault_docs = vault_doc_presence()
    strat_db_ids = set(s["nome"] for s in strat_db["strategie"])

    census_rows = []
    for s in registry["strategies"]:
        sid = s["strategy_id"]
        vault_doc_key = sid  # cerca match esatto, poi con spazi->underscore gia' fatto
        vault_present = vault_doc_key in vault_docs

        lineage_notes = []
        if sid in SHARED_IMPLEMENTATION_NOTES:
            lineage_notes.append(SHARED_IMPLEMENTATION_NOTES[sid])
        if sid in PROXY_MAP_STALENESS:
            pm = PROXY_MAP_STALENESS[sid]
            lineage_notes.append(f"contracts/generate_registry.py PROXY_MAP dichiara proxy_for="
                                  f"{pm['registry_says_proxy_for']} ma {pm['verdict']} (dispatch "
                                  f"reale: {pm['actual_dispatch_function']}).")
        if sid in NXR_ALIAS_SUFFIX_STRATEGIES:
            lineage_notes.append(f"Ha un alias storico '{sid}_NXR' (NXS_ReusePerformancePack.mqh, "
                                  f"'attribution fix' v2.0.27) - NXS_StrategyCanonicalId() lo "
                                  f"canonicalizza a {sid}. La funzione dedicata "
                                  f"{NXR_SHADOW_ENGINE_FUNCTIONS.get(sid, '')} esiste ma ha ZERO "
                                  f"call site verificati nel codice MQL5 attuale (contraddice una "
                                  f"nota storica del vault che la descriveva come motore live "
                                  f"attivo) - NOT_ENOUGH_EVIDENCE per confermare se sia dead code "
                                  f"o invocata altrove non individuato in questo census.")
        if sid == "BREAKOUT_ACC" or sid == "LONDON_BO":
            lineage_notes.append("Storicamente condivideva la funzione Python generica "
                                  "sig_breakout() (mai promossa a identita' propria, ora "
                                  "orfana/non dispatchata - vedi orphaned_python_functions) "
                                  "prima di ricevere ciascuna la propria implementazione "
                                  "dedicata.")

        row = {
            "canonical_strategy_id": sid,
            "aliases": s.get("aliases", []) + ([f"{sid}_NXR"] if sid in NXR_ALIAS_SUFFIX_STRATEGIES else []),
            "variant_of": s.get("proxy_for"),
            "first_seen": "UNKNOWN - non ricostruito in questa fase (richiederebbe git blame "
                          "per-strategia, fuori scope di un census strutturale)",
            "last_seen": "current (presente in HEAD)",
            "current_status": s["status"],
            "live_mql5": s["live_implementation"],
            "python_implementation": s["research_implementation"],
            "vault_documentation": "PRESENT" if vault_present else "ABSENT",
            "registry_presence": {
                "contracts_strategy_registry_json": True,
                "knowledge_strategy_database_json": sid in strat_db_ids,
                "nxs_strategy_id_at_mqh": sid in id_at_list,
                "nxs_strategy_known_mqh": sid in known_set,
            },
            "profile_presence": profile_tf.get(sid, "NOT_FOUND_OR_PERIOD_CURRENT"),
            "selector_presence": s["selector_index"],
            "stateful": PHASE_7_10_CLASSIFICATIONS.get(sid, "NOT_AUDITED_IN_7_10") != "NOT_AUDITED_IN_7_10",
            "canonical_tf": profile_tf.get(sid, s.get("supported_timeframes", ["UNKNOWN"])[0] if s.get("supported_timeframes") else "UNKNOWN"),
            "historical_tests": next((s2.get("ultimo_sweep") for s2 in strat_db["strategie"] if s2["nome"] == sid), None),
            "known_parity_status": s.get("research_parity"),
            "known_implementation_defects": PHASE_7_10_CLASSIFICATIONS.get(sid, "NOT_AUDITED_IN_PHASE_7_10"),
            "evidence_status": "SEE_PHASE_7_10_CASE_STUDY" if sid == "BREAKOUT_ACC" else "NOT_ASSESSED_IN_THIS_CENSUS",
            "lineage_notes": lineage_notes if lineage_notes else None,
        }
        # aggiunge il gap UNKNOWN_STRATEGY_REGISTRY_GAP se pertinente - e CORREGGE
        # live_mql5/selector_presence con la verita' di base verificata direttamente sul
        # codice (il registro dichiara live_implementation=False per questi due, ma
        # NXS_Strat_CRT()/NXS_Strat_FVG_Mitigation_Window() sono REALMENTE implementate,
        # raggiungibili dal collector con un selettore reale - il registro stesso e' quindi
        # impreciso su questo campo specifico, non solo NXS_StrategyKnown()).
        if sid in UNKNOWN_STRATEGY_REGISTRY_GAP:
            gap = UNKNOWN_STRATEGY_REGISTRY_GAP[sid]
            row["live_mql5"] = True
            row["live_mql5_registry_said"] = s["live_implementation"]
            row["live_mql5_correction_note"] = ("Il registro dichiara live_implementation="
                f"{s['live_implementation']} (status={s['status']}) ma NXS_Strat_{sid.title().replace('_','')}"
                "() esiste realmente in NXS_Strategies_SMC.mqh, viene chiamata dal collector "
                "con un selettore reale, e produce segnali che il router valuterebbe - "
                "VERIFICATO leggendo il codice sorgente direttamente, non assunto dal "
                "registro.")
            row["selector_presence"] = gap["selector"]
            row["registry_gap_UNKNOWN_STRATEGY_REGISTRY_GAP"] = {
                "verified": True,
                "detail": f"Implementata (selettore {gap['selector']}, raggiungibile dal "
                          f"collector) ma ASSENTE da NXS_StrategyKnown() - NXS_OpenTrade() "
                          f"la rifiuterebbe SEMPRE con gate UNKNOWN_STRATEGY se mai producesse "
                          f"un segnale. default_enabled={gap['default_enabled']} "
                          f"({gap['input_flag']}).",
                "severity": "HIGH - default enabled, mai potrebbe aprire un trade reale" if gap["default_enabled"]
                            else "MEDIUM - disabilitata di default, ma stesso difetto se mai attivata",
            }
        census_rows.append(row)

    return {
        "phase": "7.11", "baseline_commit": BASELINE_COMMIT,
        "no_corrections_or_retests_applied": True,
        "sources_scanned": [
            "contracts/strategy-registry.json (autoritativo combinato, generato da "
            "knowledge/strategy_database.json + backtest.py STRATEGIES)",
            "knowledge/strategy_database.json (53 live, con storico sweep)",
            "MQL5/Include/NEXUS_v1/NXS_StrategyRegistry.mqh (NXS_StrategyKnown, NXS_StrategyIdAt)",
            "MQL5/Include/NEXUS_v1/NXS_StrategyProfiles.mqh (NXS_Profile_TF)",
            "MQL5/Include/NEXUS_v1/NXS_Strategies*.mqh (4 file, funzioni NXS_Strat_*)",
            "MQL5/Include/NEXUS_v1/NXS_ReusePerformancePack.mqh (motore NXR)",
            "server/backtest.py (STRATEGIES dispatch dict, 71 funzioni sig_*)",
            "vault/01-Trading/Strategie/ (39 file)",
            "vault/01-Trading/NEXUS EA - Guida Completa Architettura e Tutte le Strategie.md "
            "(riconciliazione preesistente, riverificata contro il codice attuale)",
            "contracts/generate_registry.py (PROXY_MAP, ALIASES - verificato staleness)",
            "server/research_scripts/phase7/phase7_10/* (classificazioni CROSS_TIMEFRAME_"
            "STATE_CONTAMINATION gia' note)",
        ],
        "census_rows": census_rows,
        "orphaned_python_functions": {
            "list": orphaned_sig_fns,
            "note": "Funzioni sig_* definite in backtest.py ma MAI presenti come valore nel "
                "dispatch dict STRATEGIES - non raggiungibili da run_backtest() con nessun "
                "nome strategia. 4 di queste (sig_order_block, sig_ob_mit, sig_fvg_cont, "
                "sig_liq_sweep) sono versioni PRE-'_ext' superate dalle rispettive varianti "
                "'_ext' ora effettivamente dispatchate (stessa identita' di strategia, "
                "implementazione Python legacy conservata per riferimento) - "
                "sig_breakout e' l'unica funzione MAI stata un'identita' propria (proxy "
                "condiviso storico fra BREAKOUT_ACC/LONDON_BO/WEEKLY_EXP prima che ciascuna "
                "ricevesse la propria implementazione dedicata).",
        },
        "nxr_shadow_engine_finding": {
            "functions_defined": list(NXR_SHADOW_ENGINE_FUNCTIONS.values()),
            "call_sites_found_in_mql5_tree": 0,
            "correction_to_prior_vault_note": "Una nota precedente ('NEXUS EA - Guida "
                "Completa...') affermava che questo motore 'esegue DAVVERO i trade live' per "
                "IFVG/FVG_MIT/OB_MIT/MALAYSIAN_SNR - VERIFICATO FALSO sul codice attuale "
                "(grep esaustivo, 0 call site) - o la nota era gia' obsoleta quando scritta, "
                "o il meccanismo di invocazione reale non e' stato individuato da questo "
                "census (dichiarato NOT_ENOUGH_EVIDENCE, non affermato con certezza in nessuna "
                "direzione).",
        },
        "unknown_strategy_registry_gap_finding": UNKNOWN_STRATEGY_REGISTRY_GAP,
        "proxy_map_staleness_finding": PROXY_MAP_STALENESS,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE711_DIR, "complete_strategy_census_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"total_rows={len(payload['census_rows'])}")
    return doc


if __name__ == "__main__":
    main()
