#!/usr/bin/env python3
"""Phase 7.11 - sintesi finale del Complete Strategy Census: i 6 output
richiesti esplicitamente."""
import os
import sys

PHASE711_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE711_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "cddf8a929f3bfc259fd1a56ee454d9c8f6508798"


def build():
    census = load_json(os.path.join(PHASE711_DIR, "complete_strategy_census_v1.json"))["payload"]
    rows = census["census_rows"]

    total = len(rows)
    live_rows = [r for r in rows if r["live_mql5"]]
    research_rows = [r for r in rows if r["python_implementation"]]
    legacy_deprecated = [r for r in rows if r["current_status"] == "DISABLED"]
    alias_rows = [r for r in rows if r["aliases"]]
    partial_rows = [r for r in rows if r["live_mql5"] != r["python_implementation"]]
    never_fully_implemented = [r["canonical_strategy_id"] for r in rows
                                if r.get("registry_gap_UNKNOWN_STRATEGY_REGISTRY_GAP")]
    never_fully_implemented.append("sig_breakout (Python, mai una propria identita' - vedi "
                                    "orphaned_python_functions)")

    lineage_map = {r["canonical_strategy_id"]: r["variant_of"] for r in rows if r["variant_of"]}
    lineage_map.update({f"{a}": r["canonical_strategy_id"] for r in rows for a in r["aliases"]})

    presence_matrix = []
    for r in rows:
        rp = r["registry_presence"]
        present_in = [k for k, v in rp.items() if v] + (["vault_docs"] if r["vault_documentation"] == "PRESENT" else [])
        absent_from = [k for k, v in rp.items() if not v] + (["vault_docs"] if r["vault_documentation"] == "ABSENT" else [])
        if absent_from and present_in:
            presence_matrix.append({
                "strategy": r["canonical_strategy_id"], "present_in": present_in, "absent_from": absent_from,
                "notable": bool(r.get("registry_gap_UNKNOWN_STRATEGY_REGISTRY_GAP")),
            })

    possibly_excluded_from_prior_audits = [
        {"strategy": "CRT", "reason": "Assente da NXS_StrategyKnown() - un audit basato sul "
            "registro (come Phase 7.10, che ha scansionato NXS_Strategies*.mqh direttamente "
            "quindi NON escluso li', ma un audit basato SOLO sulla lista dei 53 nomi noti "
            "l'avrebbe saltata)."},
        {"strategy": "FVG_MIT_WINDOW", "reason": "Stesso motivo di CRT - inoltre default "
            "ENABLED, quindi il rischio pratico e' piu' alto."},
        {"strategy": "IFVG / FVG_MIT / OB_MIT / MALAYSIAN_SNR (motore NXR)",
         "reason": "Il motore NXR (NXS_ReusePerformancePack.mqh) non e' mai stato scansionato "
            "da Phase 7.10 (che ha guardato solo NXS_Strategies*.mqh) - se le funzioni "
            "NXR_Strat_* fossero davvero raggiungibili (non confermato, 0 call site trovati "
            "in questo census), sarebbero un candidato NON ancora auditato per "
            "CROSS_TIMEFRAME_STATE_CONTAMINATION o pattern simili."},
        {"strategy": "OB_MIT", "reason": "Condivide codice con ORDER_BLOCK (gia' "
            "DEFECT_CONFIRMED in Phase 7.10) - MAI auditato separatamente perche' assunto "
            "'stessa cosa di ORDER_BLOCK', ma ha un proprio stratName/selettore/stato "
            "derivato indipendentemente a runtime (NXS_OB_UpdateSide chiamata con "
            "g_obBuy/g_obSell CONDIVISI fra le due identita' - un potenziale canale di "
            "contaminazione INCROCIATA fra ORDER_BLOCK e OB_MIT stesso, mai verificato)."},
    ]

    additional_cross_tf_candidates = [
        {"strategy": "OB_MIT", "pattern": "CROSS_STRATEGY_STATE_SHARING (nuovo, distinto da "
            "CROSS_TIMEFRAME_STATE_CONTAMINATION)", "note": "ORDER_BLOCK e OB_MIT chiamano "
            "ENTRAMBI NXS_OB_UpdateSide() sugli STESSI g_obBuy/g_obSell globali (verificato: "
            "nessuna istanza separata per OB_MIT) - se entrambe abilitate simultaneamente, "
            "potrebbero corrompersi a vicenda lo stato indipendentemente da qualunque "
            "problema di timeframe. NOT_ENOUGH_EVIDENCE per confermare l'impatto pratico - "
            "richiederebbe la stessa metodologia sperimentale di 7.9E/F, non eseguita qui."},
        {"strategy": "CRT, FVG_MIT_WINDOW", "pattern": "UNKNOWN_STRATEGY_REGISTRY_GAP (nuovo)",
         "note": "Non e' cross-TF contamination, ma un pattern di rischio strutturale "
            "distinto e altrettanto silenzioso: un segnale generato correttamente viene "
            "SEMPRE rifiutato da un gate di sicurezza indipendente (NXS_StrategyKnown()) "
            "perche' il registro non lo riconosce - zero trade garantiti a prescindere dalla "
            "qualita' del segnale, indistinguibile da 'nessun edge' senza ispezionare il "
            "codice."},
    ]

    return {
        "phase": "7.11", "baseline_commit": BASELINE_COMMIT,
        "no_corrections_or_retests_applied": True,
        "output_1_total_unique_identities": total,
        "output_2_counts_by_category": {
            "live": len(live_rows), "research": len(research_rows),
            "legacy_deprecated": len(legacy_deprecated), "alias": len(alias_rows),
            "partial": len(partial_rows), "never_fully_implemented": len(never_fully_implemented),
            "never_fully_implemented_list": never_fully_implemented,
        },
        "output_3_lineage_variant_map": lineage_map,
        "output_4_source_presence_discrepancies": presence_matrix,
        "output_5_possibly_excluded_from_prior_audits": possibly_excluded_from_prior_audits,
        "output_6_additional_cross_tf_or_new_pattern_candidates": additional_cross_tf_candidates,
        "count_discrepancy_explanations": {
            "knowledge_strategy_database_json_says_53": "Copre SOLO le strategie live "
                "(live_implementation=true) - e' la fonte primaria da cui "
                "contracts/strategy-registry.json deriva i 53 'live', poi arricchita con i "
                "30 research-only trovati in backtest.py per arrivare a 83 totali.",
            "nxs_strategy_known_mqh_says_53_but_2_live_functions_absent": "NXS_StrategyKnown() "
                "e NXS_StrategyIdAt() sono generati/mantenuti insieme (stesso file, "
                "probabilmente stesso processo di generazione) e concordano fra loro (53=53) "
                "- ma NON con la realta' del codice: CRT e FVG_MIT_WINDOW hanno funzioni "
                "NXS_Strat_* reali e raggiungibili (verificato) ma non sono in QUESTA lista - "
                "il file NXS_StrategyRegistry.mqh stesso (dichiarato 'Generated by "
                "contracts/generate_registry.py. Do not edit.') non e' stato rigenerato dopo "
                "l'aggiunta di queste due strategie, o il generatore non le include per un "
                "motivo non verificato in questo census.",
            "contracts_strategy_registry_json_live_implementation_false_for_CRT_FVG_MIT_WINDOW":
                "Il generatore (contracts/generate_registry.py) deriva live_implementation "
                "presumibilmente dalla stessa fonte di NXS_StrategyKnown()/NXS_StrategyIdAt() "
                "(entrambe non le includono) invece di scansionare direttamente "
                "NXS_Strat_CRT()/NXS_Strat_FVG_Mitigation_Window() nel codice sorgente - "
                "stessa causa radice del punto precedente, verificata separatamente su "
                "questo file.",
        },
        "no_strategies_merged_by_name_similarity": True,
        "no_identities_split_without_code_evidence": True,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE711_DIR, "census_summary_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"total identities: {payload['output_1_total_unique_identities']}")
    print(f"by category: {payload['output_2_counts_by_category']}")
    return doc


if __name__ == "__main__":
    main()
