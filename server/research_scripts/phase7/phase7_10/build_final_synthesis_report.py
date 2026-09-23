#!/usr/bin/env python3
"""Phase 7.10 - deliverable finale: risposte esplicite alle 6 domande
poste dall'utente, sintetizzando i risultati dei task 1-4."""
import os
import sys

PHASE710_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE710_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "651d3a2a10e5c58acfc22ba820f518810356a73c"


def build():
    label_correction = load_json(os.path.join(PHASE710_DIR, "breakout_acc_7_9g_label_correction_v1.json"))["payload"]
    failure_memory = load_json(os.path.join(PHASE710_DIR, "cross_timeframe_state_contamination_failure_memory_v1.json"))["payload"]
    static_audit = load_json(os.path.join(PHASE710_DIR, "stateful_strategy_static_audit_v1.json"))["payload"]
    schema_and_case = load_json(os.path.join(PHASE710_DIR, "retroactive_strategy_integrity_audit_schema_v1.json"))["payload"]

    defect_confirmed_list = [c["strategy"] for c in static_audit["candidates"] if c["classification"] == "DEFECT_CONFIRMED"]
    suspect_list = [c["strategy"] for c in static_audit["candidates"] if c["classification"] == "SUSPECT"]
    safe_list = [c["strategy"] for c in static_audit["candidates"] if c["classification"] == "SAFE"]

    return {
        "phase": "7.10", "title": "BREAKOUT_ACC come primo caso certificato del Retroactive "
            "Strategy Integrity Audit", "baseline_commit": BASELINE_COMMIT,
        "no_optimization": True, "no_edge_seeking": True, "no_new_serious_backtest": True,
        "no_parameter_tuning": True, "no_strategy_modification_beyond_7_9g": True,
        "no_economic_dataset_built": True,

        "q1_only_a_only_b_inversion": {
            "question": "L'inversione only_a/only_b esiste davvero?",
            "answer": "SI. Verificata direttamente sul codice (non assunta): la funzione "
                "pair_dates() e' posizionale, le chiamate originali passavano lo stream "
                "offline come primo argomento e quello live come secondo - quindi only_a "
                "conteneva il residuo di B (offline) e only_b il residuo di A (live), "
                "invertiti rispetto alla convenzione narrativa del report. I NUMERI e il "
                "VERDETTO sostanziali NON erano mai sbagliati (matched=67, "
                "parity_passed=True, next_decision=BUILD_CANONICAL_BREAKOUT_ACC_DATASET, "
                "tutti invariati prima/dopo) - solo le etichette dei campi. Corretto alla "
                "fonte in 3 script (build_postfix_signal_parity.py, "
                "build_phase7_9g_decision.py, test_phase_7_9g.py), artifact rigenerati, dati "
                "originali preservati in raw_data/, nessun altro consumer nel progetto usava "
                "il pattern ambiguo.",
            "detail_ref": "breakout_acc_7_9g_label_correction_v1.json",
        },

        "q2_general_risk_class": {
            "question": "Il bug BREAKOUT_ACC appartiene a una classe generale di rischio?",
            "answer": "SI. Formalizzato come CROSS_TIMEFRAME_STATE_CONTAMINATION: una "
                "strategia stateful chiamata durante pass multi-TF che non appartengono al "
                "proprio profilo, il cui output viene scartato dal router ma i cui effetti "
                "collaterali sullo stato persistono e corrompono il comportamento sul TF "
                "canonico. Il meccanismo e' invisibile a un signal-parity check "
                "tradizionale perche' quello confronta tipicamente una ricostruzione "
                "offline gia' isolata a un TF contro il conteggio finale live, senza "
                "replicare la cadenza REALE multi-pass del router - il sintomo (meno "
                "segnali del previsto) viene facilmente mal-attribuito a differenze di "
                "feed/dati (come accaduto in 7.9C prima della scoperta in 7.9D-7.9F).",
            "detail_ref": "cross_timeframe_state_contamination_failure_memory_v1.json",
        },

        "q3_other_exposed_strategies": {
            "question": "Quali altre strategie sono esposte alla stessa classe?",
            "answer": f"Audit statico completo di 19 strategie con stato persistente/"
                f"globale/statico (scansione esaustiva di NXS_Strategies*.mqh): "
                f"{len(defect_confirmed_list)} DEFECT_CONFIRMED (stesso meccanismo "
                f"strutturale di BREAKOUT_ACC, mai testato empiricamente per queste "
                f"specifiche strategie), {len(suspect_list)} SUSPECT (stesso pattern "
                f"architetturale ma rischio pratico basso, solo bare lastBarTime senza "
                f"cooldown/valore ricorsivo), {len(safe_list)} SAFE (verificato: usano un "
                f"timeframe hardcoded, immune per costruzione).",
            "defect_confirmed": defect_confirmed_list,
            "suspect": suspect_list,
            "safe": safe_list,
            "severity_note": "Fra i DEFECT_CONFIRMED, alcuni (TSI, PMAX, ORDER_BLOCK, "
                "BB_SQUEEZE, macchine a stati SMC) sono potenzialmente PIU' gravi di "
                "BREAKOUT_ACC/BAR_UPDN/PIVOT_WICK, perche' lo stato contaminato e' un "
                "VALORE RICORSIVO o una MACCHINA A STATI (rischio sia falsi negativi che "
                "falsi positivi), non solo un timestamp di cooldown (rischio quasi solo "
                "falsi negativi).",
            "no_corrections_applied": "Nessuna di queste strategie e' stata corretta in "
                "questa fase, come richiesto esplicitamente.",
            "detail_ref": "stateful_strategy_static_audit_v1.json",
        },

        "q4_bar_updn_status": {
            "question": "BAR_UPDN e' realmente affetta oppure solo strutturalmente sospetta?",
            "answer": static_audit["bar_updn_explicit_answer"]["answer"],
        },

        "q5_canonical_audit_schema": {
            "question": "Qual e' lo schema canonico con cui faremo l'audit retrospettivo "
                "dell'intero vault?",
            "answer": "RETROACTIVE_STRATEGY_INTEGRITY_AUDIT_V1 - una pipeline di 13 stage "
                "ordinati (ORIGINAL_PHENOMENON -> FORMAL_SPEC -> PYTHON_IMPLEMENTATION -> "
                "MQL5_IMPLEMENTATION -> TF/SESSION/HTF -> SIGNAL_TIMING -> STATEFUL_BEHAVIOR "
                "-> SL/TP/EXIT -> SELECTOR/PROFILE/GATES -> SIGNAL -> ORDER -> FILL -> "
                "OUTCOME/EVIDENCE), ciascuno classificabile MATCHED/PARTIAL/MISMATCH/UNKNOWN/"
                "NOT_APPLICABLE, con due classificazioni finali derivate (mai dal solo "
                "risultato economico): evidence_integrity (GENUINE_REFUTATION/"
                "GENUINE_SUPPORT/CONTAMINATED_EVIDENCE/NEVER_REALLY_TESTED/"
                "FORMALIZATION_GAP/EXECUTION_GAP/INSUFFICIENT_EVIDENCE) e "
                "distortion_direction (FALSE_NEGATIVE_RISK/FALSE_POSITIVE_RISK/BOTH/"
                "NONE_KNOWN). BREAKOUT_ACC registrata come primo case study completo: "
                "evidence_integrity_final=CONTAMINATED_EVIDENCE, "
                "distortion_direction=FALSE_NEGATIVE_RISK (il meccanismo dimostrato e' "
                "soppressivo, non generativo di falsi segnali - il risultato storico a 4 "
                "trade rischia di essere sistematicamente PIU' SCARSO della realta', non il "
                "contrario).",
            "detail_ref": "retroactive_strategy_integrity_audit_schema_v1.json",
        },

        "q6_next_single_task": {
            "question": "Qual e' la prossima singola task consigliata dopo questa fase?",
            "answer": "Restano DUE fili aperti distinti e l'utente ha gia' indicato "
                "l'ordine preferito (7.9H poi Edge Decomposition) - la raccomandazione "
                "tecnica per la PROSSIMA SINGOLA TASK, coerente con la disciplina "
                "'integrita' prima dell'economia' di questa fase, e': "
                "BUILD_CANONICAL_BREAKOUT_ACC_DATASET (= Phase 7.9H, gia' autorizzato dal "
                "next_decision della 7.9G, non ancora eseguito) - costruire il dataset "
                "canonico Python per BREAKOUT_ACC_INTENDED_D1_V1 (stato D1-only, nessuna "
                "modifica alla logica - Python era gia' corretto, vedi 7.9G) e SOLO "
                "ALLORA procedere a Edge Decomposition. Le strategie DEFECT_CONFIRMED "
                "trovate in questa fase (BAR_UPDN e le altre 8) restano backlog "
                "esplicitamente NON prioritario rispetto a questo - nessuna di esse blocca "
                "il percorso BREAKOUT_ACC.",
            "not_recommended_now": "Correggere BAR_UPDN o le altre strategie DEFECT_"
                "CONFIRMED - richiederebbe ciascuna il proprio processo di adjudication "
                "(7.9C-7.9F-style) prima di qualunque fix, fuori scope della singola "
                "prossima task.",
        },

        "historical_chronology_preserved": {
            "7_9c": "EXECUTION_GAP_DOMINANT (apparente)",
            "7_9d": "funnel di esecuzione pulito",
            "7_9e": "scoperta del meccanismo cross-TF",
            "7_9f": "IMPLEMENTATION_DEFECT_CONFIRMED",
            "7_9g": "fix applicato, parity ristabilita (con correzione di etichetta in 7.10)",
            "7_10": "generalizzazione del pattern (CROSS_TIMEFRAME_STATE_CONTAMINATION), "
                "audit statico di 19 strategie, schema di audit retrospettivo canonico",
            "no_artifacts_deleted": True,
        },
        "volbrk_not_reopened": True, "h006_not_reopened": True, "hvcw_backlog_only": True,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE710_DIR, "phase_7_10_final_synthesis_report_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    return doc


if __name__ == "__main__":
    main()
