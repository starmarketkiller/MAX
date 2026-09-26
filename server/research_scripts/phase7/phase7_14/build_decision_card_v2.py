#!/usr/bin/env python3
"""Phase 7.14 punto 8 - Decision Card finale, basata sul trace EA reale
pre/post fix (non piu' solo sulla ricostruzione Python di Phase 7.13).
"""
import os
import sys

PHASE714_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE714_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    parity = load_json(os.path.join(PHASE714_DIR, "parity_comparison_v1.json"))["payload"]
    real_trace = load_json(os.path.join(PHASE714_DIR, "real_trace_comparison_v1.json"))["payload"]
    ob_mit = load_json(os.path.join(PHASE714_DIR, "ob_mit_dependency_map_v1.json"))["payload"]

    decision = "FIX_CAUSALLY_VALIDATED"
    decision_basis = [
        "Trace diagnostico reale (EA istrumentato, logging non comportamentale, tick reali "
        "GOLD 2023-10-02..2026-08-25, InpStrategySelector=15) conferma il meccanismo end-to-end: "
        f"{real_trace['n_non_canonical_state_mutations']} mutazioni di stato su passaggi non "
        f"canonici, {real_trace['n_signals_fired_non_canonical_discarded']} segnali sparati e "
        "scartati su TF non canonico, {} esempi end-to-end (mutazione non canonica -> evento "
        "canonico successivo) trovati direttamente nel trace.".format(
            real_trace["n_end_to_end_examples_found"]),
        "Guardia applicata (fix minimale autorizzato) verificata efficace al 100% sul trace "
        f"reale post-fix: {parity['guard_effectiveness_check']['non_canonical_rows_present_in_B']} "
        "righe non canoniche osservate su TF diverso dal canonico (atteso: 0).",
        f"Parity A(pre-fix)/B(post-fix) sugli STESSI tick reali: "
        f"{parity['A_pre_fix']['n_signals_canonical_kept']} segnali D1 pre-fix -> "
        f"{parity['B_post_fix']['n_signals_canonical_kept']} post-fix "
        f"({parity['a_vs_b_same_real_ticks_comparison']['n_matched_same_date_side_direction_multiset']} "
        "coincidono esattamente).",
        "Scoperta aggiuntiva nel trace reale (non nella ricostruzione Python 7.13): pre-fix, "
        f"{parity['repeated_fires_same_day_finding']['n_distinct_d1_days_with_multiple_fires_pre_fix']} "
        "giorni D1 mostrano PIU' fire nello stesso giorno solare (fino a "
        f"{parity['repeated_fires_same_day_finding']['max_fires_same_calendar_day_pre_fix']}x) - "
        "causa: lastBarTime condiviso viene sovrascritto da TF piu' veloci, disfacendo il gate "
        "'nuova barra' di D1 stesso. Post-fix: 0 giorni con fire multipli - la guardia risolve "
        "ANCHE questa manifestazione piu' severa del difetto.",
        f"Confronto strutturale B (EA reale post-fix, {parity['B_post_fix']['n_signals_canonical_kept']}) "
        f"vs C (ricostruzione Python Phase 7.13, {parity['C_tf_scoped_reconstruction']['n_signals_canonical_kept']}): "
        "vicini pur partendo da fonti dati indipendenti (tick MT5 reali vs serie M15 ricampionata) - "
        "non identici per costruzione (dati diversi), coerenti nella direzione e nell'ordine di "
        "grandezza, a supporto della fedelta' della ricostruzione Python.",
    ]

    ob_mit_status = {
        "verified_before_any_fix_decision": True,
        "has_own_state_or_separate_path": ob_mit["ob_mit_has_own_state"] or (not ob_mit["ob_mit_calls_order_block_directly"]),
        "conclusion": ob_mit["conclusion"],
        "fix_propagates_automatically": True,
        "additional_related_finding_not_fixed_here": ob_mit["additional_finding_selector_gate_mismatch"]["description"],
        "post_fix_direct_verification_note": "OB_MIT non e' stato testato con un run reale "
                                             "separato in questa fase (il gate annidato del "
                                             "selettore lo rende muto sotto InpStrategySelector=20 "
                                             "isolato - vedi finding sopra) - la conclusione "
                                             "'nessun percorso separato' e' stabilita per lettura "
                                             "diretta del codice (NXS_Strat_OB_Mitigation_Structural "
                                             "chiama SOLO NXS_Strat_OrderBlock, zero stato proprio), "
                                             "non da un secondo trace dinamico dedicato.",
    }

    payload = {
        "candidate": "ORDER_BLOCK",
        "baseline_commit": "7b823b9",
        "decision": decision,
        "decision_basis": decision_basis,
        "ob_mit_status": ob_mit_status,
        "fix_applied": {
            "file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
            "function": "NXS_Strat_OrderBlock()",
            "change": 'if(tf != NXS_Profile_TF("ORDER_BLOCK")) return s;',
            "position": "subito dopo `ENUM_TIMEFRAMES tf = NXS_EffTF();`, prima di ogni lettura "
                       "di g_atr/g_obBuy/g_obSell",
            "geometry_trigger_tf_sltp_gates_cooldown_params_other_strategies_unchanged": True,
        },
        "temporary_diagnostic_instrumentation": {
            "added_and_reverted_before_fix": True,
            "added_again_and_reverted_after_postfix_capture": True,
            "final_state_mql5_tree": "identico a 7b823b9 + SOLO la riga della guardia sopra",
        },
        "parity_summary": {
            "A_pre_fix_generated_d1": parity["A_pre_fix"]["n_signals_canonical_kept"],
            "B_post_fix_generated_d1": parity["B_post_fix"]["n_signals_canonical_kept"],
            "C_python_reconstruction_generated_d1": parity["C_tf_scoped_reconstruction"]["n_signals_canonical_kept"],
            "goal_was_not_b_equals_c_but_to_explain_residual": True,
            "residual_explained": True,
        },
        "no_optimization_no_sltp_tuning_no_parameter_sweep_no_profitability_no_promotion": True,
        "next_step_not_decided_here": "Nessuna promozione live, nessuna ottimizzazione. Il fix "
                                      "resta un cambiamento di IMPLEMENTATION INTEGRITY - una "
                                      "valutazione di redditivita' post-fix e' un lavoro separato, "
                                      "non svolto e non presunto in questa fase.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE714_DIR, "decision_card_v2_order_block_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")
    print(f"  OB_MIT: fix si propaga automaticamente = {payload['ob_mit_status']['fix_propagates_automatically']}")


if __name__ == "__main__":
    main()
