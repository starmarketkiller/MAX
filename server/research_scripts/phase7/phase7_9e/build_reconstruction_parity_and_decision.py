#!/usr/bin/env python3
"""Phase 7.9E - punti 9, 10, 11: target di parity (NON raggiunto - nessun
fix applicato alla replica in questa fase, per esplicita istruzione di
non eseguire il passo successivo), verdetto finale e prossima decisione."""
import os
import sys

PHASE79E_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79E_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "ee469d4fa62a6c6aba8b228c16a422540e05c189"

ALLOWED_VERDICTS = {
    "OFFLINE_RECONSTRUCTION_PARITY_CONFIRMED", "OFFLINE_RECONSTRUCTION_PARITY_PARTIAL",
    "EVALUATION_CADENCE_MISMATCH", "STATE_SEMANTICS_MISMATCH", "HTF_TIMING_MISMATCH",
    "MULTI_CAUSE_RECONSTRUCTION_FAILURE", "OFFLINE_RECONSTRUCTION_ROOT_CAUSE_UNRESOLVED",
}
ALLOWED_NEXT_DECISIONS = {"REBUILD_CANONICAL_BREAKOUT_ACC_DATASET", "BLOCK_RESEARCH_UNTIL_RECONSTRUCTION_PARITY"}


def build():
    semantics_diff = load_json(os.path.join(PHASE79E_DIR, "breakout_acc_live_vs_offline_semantics_diff_v1.json"))["payload"]
    forensics = load_json(os.path.join(PHASE79E_DIR, "breakout_acc_missing_event_forensics_v1.json"))["payload"]

    parity_target = {
        "target_declared": "actual EA GENERATED = 4, offline reconstructed GENERATED = 4, "
            "timestamp/direzione esatti 4/4",
        "achieved": False,
        "reason_not_achieved": "Nessun fix e' stato applicato alla replica offline in questa "
            "fase (per istruzione esplicita: 'Fix only the diagnostic/research replica... "
            "Do not execute the next step'). Il MECCANISMO causale e' stato identificato e "
            "dimostrato sperimentalmente con alta confidenza (STATE_SEMANTICS_MISMATCH, "
            "collasso 95->0 in un esperimento controllato con stato condiviso multi-TF), ma "
            "NON e' stata costruita una replica corretta che riproduca esattamente 4/4.",
        "current_best_replica_result": {
            "isolated_D1_only_no_cross_tf_state": 75,
            "with_cross_tf_shared_state_simplified_pass_order": 0,
            "real_ea": 4,
            "note": "La direzione e l'ordine di grandezza del collasso sono confermati "
                "(75->~0, reale=4) - la cifra ESATTA (4) non e' stata riprodotta, perche' "
                "l'ordine esatto dei pass multi-TF nel registro reale (NXS_StrategyIdAt) non "
                "e' stato replicato bit-per-bit in questa fase - dichiarato onestamente come "
                "limite, non forzato a coincidere.",
        },
    }

    # --- Verdetto: root cause identificato con prove sperimentali dirette,
    # ma parity ESATTA non raggiunta (nessun fix eseguito) -> STATE_SEMANTICS_MISMATCH
    # e' la scelta corretta (non PARTIAL/CONFIRMED, che implicherebbero un fix
    # gia' verificato; non ROOT_CAUSE_UNRESOLVED, perche' la causa E' stata isolata
    # con prove dirette, non solo ipotizzata).
    final_verdict = "STATE_SEMANTICS_MISMATCH"
    verdict_detail = {
        "primary_cause": "g_breakoutAccState (NXS_Strategies.mqh:1531-1532) e' un unico "
            "struct GLOBALE, non scoped per-timeframe, condiviso da ogni chiamata a "
            "NXS_Strat_BreakoutAcc() indipendentemente dal timeframe attivo (g_activeTF) al "
            "momento della chiamata - la funzione viene invocata una volta per OGNI pass "
            "multi-TF del router (M5/M15/M30/H1/H4/D1), non solo durante il pass D1, perche' il "
            "suo gate di selettore non dipende dal TF attivo.",
        "secondary_contributing_cause": "HTF_TIMING_MISMATCH (px200=shift0 vs il proxy "
            "shift1 usato dagli script offline) - reale ma minore (95->75, -21%), non "
            "sufficiente da solo a spiegare il gap.",
        "ruled_out_with_direct_experiments": [
            "EVALUATION_CADENCE_DIFFERENCE (1944/1944 barre D1 rilevate correttamente)",
            "indicator activation/readiness gating (0 fallimenti su 177808 tentativi)",
            "BAR_SHIFT_SEMANTICS_DIFFERENCE (verificato algebricamente: nessun bug di "
            "indicizzazione nello script 7.9C, contrariamente al sospetto iniziale)",
        ],
        "experimental_evidence": "breakout_acc_live_vs_offline_semantics_diff_v1.json, sezione 6 "
            "(Esperimenti A e B, entrambi eseguiti nel vero Tester, zero rischio)",
    }

    # --- Prossima decisione: parity NON raggiunta -> BLOCK_RESEARCH_UNTIL_RECONSTRUCTION_PARITY
    next_decision = "BLOCK_RESEARCH_UNTIL_RECONSTRUCTION_PARITY"
    next_decision_rationale = (
        "Il meccanismo causale e' identificato con prove dirette e sperimentali (non solo "
        "un'ipotesi), ma NESSUNA replica offline e' stata corretta e verificata a produrre "
        "esattamente i 4 eventi reali con date/direzioni esatte - il target di parity "
        "dichiarato al punto 9 non e' raggiunto. REBUILD_CANONICAL_BREAKOUT_ACC_DATASET "
        "sarebbe prematuro per la stessa ragione identificata dalla 7.9D: costruire un "
        "dataset prima che la replica sia dimostrata fedele produrrebbe un numero preciso "
        "ma di provenienza incerta - questa volta pero' con una spiegazione MOLTO piu' "
        "solida del perche', pronta per essere implementata in una fase dedicata."
    )
    concrete_next_step_not_executed = (
        "Correggere la replica Python (server/backtest.py: sig_breakout_acc / "
        "_breakout_acc_cooldown_series) per condividere lo stato di cooldown fra TUTTI i "
        "timeframe usati da QUALUNQUE strategia nel motore di backtest (replicando fedelmente "
        "il bug/comportamento reale, non 'correggendolo' - l'obiettivo e' la fedelta' al "
        "motore live, non un miglioramento della strategia), producendo un artifact "
        "before/after congelato con evidenza di parity esatta (4/4, stesse date/direzioni) "
        "prima di qualunque nuova statistica. NON eseguito in questa fase."
    )

    assert final_verdict in ALLOWED_VERDICTS
    assert next_decision in ALLOWED_NEXT_DECISIONS

    payload = {
        "phase": "7.9E", "candidate": "BREAKOUT_ACC", "baseline_commit": BASELINE_COMMIT,
        "supersedes_note": {
            "7_9c_assumption": "EXECUTION_GAP_DOMINANT (assumeva che 80 SIGNAL_FIRE offline "
                "fossero equivalenti ai segnali GENERATED reali dell'EA)",
            "7_9d_finding": "il funnel di ESECUZIONE e' pulito (0 blocchi, 4/4 aperti) - "
                "l'assunzione 7.9C era nel posto sbagliato",
            "7_9e_finding": "il vero gap e' nella GENERAZIONE del segnale stesso, causato da "
                "contaminazione di stato cross-timeframe nel router live (STATE_SEMANTICS_"
                "MISMATCH) - non un problema di esecuzione ne' (principalmente) di feed/gate HTF",
            "frozen_artifacts_not_modified": ["7.9C: breakout_acc_event_parity_matrix_v1.json",
                                              "7.9D: breakout_acc_execution_parity_decision_v1.json"],
        },
        "parity_target": parity_target,
        "final_verdict": final_verdict, "final_verdict_detail": verdict_detail,
        "next_decision": next_decision, "next_decision_rationale": next_decision_rationale,
        "concrete_next_step_not_executed": concrete_next_step_not_executed,
        "next_step_not_executed": True,
        "missing_event_forensics_summary": {
            "events_checked": [e["date"] for e in forensics["events"]],
            "all_valid_in_isolation": all(e["would_fire_in_isolation"] for e in forensics["events"]),
            "all_absent_in_real_ea": True,
            "consistent_with_state_semantics_mismatch": True,
        },
        "volbrk_not_reopened": True, "h006_not_reopened": True, "hvcw_backlog_only": True,
        "live_ea_strategy_logic_unchanged": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79E_DIR, "breakout_acc_reconstruction_parity_v1.json"),
              wrap_with_provenance(payload["parity_target"], os.path.basename(__file__)))
    decision_payload = {
        "phase": payload["phase"], "candidate": payload["candidate"],
        "final_verdict": payload["final_verdict"], "final_verdict_detail": payload["final_verdict_detail"],
        "next_decision": payload["next_decision"], "next_decision_rationale": payload["next_decision_rationale"],
        "concrete_next_step_not_executed": payload["concrete_next_step_not_executed"],
        "next_step_not_executed": True, "supersedes_note": payload["supersedes_note"],
        "volbrk_not_reopened": True, "h006_not_reopened": True, "hvcw_backlog_only": True,
        "live_ea_strategy_logic_unchanged": True,
    }
    save_json(os.path.join(PHASE79E_DIR, "breakout_acc_reconstruction_decision_v1.json"),
              wrap_with_provenance(decision_payload, os.path.basename(__file__)))
    print(f"final_verdict={payload['final_verdict']}")
    print(f"next_decision={payload['next_decision']}")
    return doc


if __name__ == "__main__":
    main()
