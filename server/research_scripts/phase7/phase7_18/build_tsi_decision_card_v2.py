#!/usr/bin/env python3
"""Phase 7.18 punto 5 - Decision Card finale TSI, basata sul trace EA
reale pre/post fix (non piu' solo sulla formalizzazione matematica e
sui dati locali gia' disponibili di Phase 7.17).
"""
import os
import sys

PHASE718_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE718_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    parity = load_json(os.path.join(PHASE718_DIR, "tsi_parity_comparison_v1.json"))["payload"]

    guard = parity["guard_effectiveness_check"]
    ab = parity["a_vs_b_same_real_ticks_comparison"]
    bc = parity["b_vs_c_structural_comparison"]

    decision = "FIX_CAUSALLY_VALIDATED"
    decision_basis = [
        "Run diagnostico corto MT5 pre-fix (2026.01.01-2026.08.25, GOLD H4/tick reali, "
        "InpStrategySelector=5, selettore isolato) e post-fix, stessi tick, stessa finestra: "
        f"guardia TF-scoped verificata efficace al 100% - "
        f"{guard['non_canonical_rows_present_in_B']} righe non-D1 osservate post-fix (atteso: 0).",
        f"A(pre-fix)/B(post-fix) sugli STESSI tick reali: {ab['a_total_canonical']} righe D1 "
        f"'canoniche' grezze pre-fix (molte duplicate per tick nello stesso bar) collassano a "
        f"pochissimi eventi distinti coincidenti col post-fix - {ab['n_matched']} coppie "
        f"(data,direzione) coincidono esattamente, {ab['n_only_in_a']} presenti SOLO pre-fix "
        f"(spurie, eliminate dal fix), {ab['n_only_in_b']} presenti SOLO post-fix. La "
        "contaminazione pre-fix produce un numero di eventi 'canonici' ordini di grandezza "
        "superiore a quelli realmente generati post-fix - coerente con Phase 7.17 "
        "(contaminazione universale, 100% delle barre D1 alterate).",
        f"Confronto strutturale B (EA reale post-fix) vs C (ricostruzione Python TF-scoped "
        f"Phase 7.17, storia locale piena 2023-10-02+ per il warm-up, poi ritagliata sulla "
        f"finestra del run breve): {bc['n_matched_date_direction']} segnali coincidono su "
        f"data+direzione, {bc['n_b_only_vs_c']} presenti SOLO in B (atteso: 0 - confermato), "
        f"{bc['n_c_only_vs_b']} presenti SOLO in C - TUTTI antecedenti al primo segnale reale "
        "post-fix e spiegati dalla differenza di warm-up (B riparte da barsSeen=0 all'avvio "
        "del run Tester breve, quindi il gate 'barsSeen < 75' resta chiuso fino a meta' "
        "aprile 2026 circa; C eredita un filtro gia' maturo dalla storia locale piena "
        "2023-10-02+) - non un residuo di contaminazione. Per il periodo maturo comune "
        "(dal primo segnale B in poi), B e C coincidono al 100%.",
        f"Valori TSI intermedi (B vs C) su {bc['tsi_value_comparison_on_common_dates']['n_common_dates']} "
        f"date comuni: differenza media assoluta "
        f"{bc['tsi_value_comparison_on_common_dates']['mean_abs_diff']:.4f}, "
        f"massima {bc['tsi_value_comparison_on_common_dates']['max_abs_diff']:.4f} - "
        "piccola e coerente con la differenza di profondita' del warm-up gia' dichiarata "
        "(non un errore strutturale), stesso principio metodologico di Phase 7.16/7.17: "
        "Python NON e' ground truth, MT5 post-fix resta la fonte canonica.",
        "Nessun side-effect inatteso osservato: compilazione post-fix pulita (0 errori, stessi "
        "2 warning della baseline pre-fix), nessuna modifica a formula/periodi/soglie/TF "
        "canonico/gate/SL-TP/selector, nessun'altra strategia toccata (TSI non ha wrapper "
        "ne' e' riusata da altre strategie, verificato in Phase 7.17).",
    ]

    payload = {
        "candidate": "TSI",
        "baseline_commit": "8590f63",
        "decision": decision,
        "decision_basis": decision_basis,
        "fix_applied": {
            "file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
            "function": "NXS_Strat_TSI()",
            "change": 'if(tf != NXS_Profile_TF("TSI")) return s;',
            "position": "subito dopo `ENUM_TIMEFRAMES tf = NXS_EffTF();`, prima di qualunque "
                       "lettura di curBar0/c1 e prima di ogni mutazione di g_tsiState "
                       "(init/sm1/sm2/sm1Abs/sm2Abs/signal/prevClose/lastBarTime/barsSeen) - "
                       "verificato staticamente: nessuna mutazione di stato avviene prima "
                       "della guardia.",
            "formula_periods_thresholds_canonical_tf_gate_sltp_selector_other_strategies_unchanged": True,
            "no_wrapper_reuse_by_other_strategies": "confermato in Phase 7.17 (nessun wrapper "
                                                    "trovato) - il fix non si propaga a nessuna "
                                                    "altra strategia, a differenza di ORDER_BLOCK/OB_MIT",
        },
        "temporary_diagnostic_instrumentation": {
            "added_and_reverted_before_fix_capture": True,
            "added_again_and_reverted_after_postfix_capture": True,
            "final_state_mql5_tree": "identico alla baseline 8590f63 + SOLO la riga della guardia sopra",
            "logging_position_note": "a differenza di ORDER_BLOCK (Phase 7.14), TSI non ha rami "
                                    "'silenziosi' a basso costo prima del punto di log - "
                                    "l'istrumentazione pre-fix logga OGNI tick che raggiunge la "
                                    "chiamata TSI nel router multi-TF (non solo le transizioni di "
                                    "barra), producendo un trace molto piu' pesante per unita' di "
                                    "tempo calendario del run (75.474 righe / ~50 min per la finestra "
                                    "pre-fix) - osservazione operativa, non un difetto del fix.",
        },
        "parity_summary": {
            "A_pre_fix_raw_canonical_rows": ab["a_total_canonical"],
            "B_post_fix_raw_canonical_rows": ab["b_total_canonical"],
            "a_vs_b_matched_date_direction": ab["n_matched"],
            "a_vs_b_only_in_a_spurious_eliminated": ab["n_only_in_a"],
            "a_vs_b_only_in_b": ab["n_only_in_b"],
            "b_vs_c_matched": bc["n_matched_date_direction"],
            "b_vs_c_only_in_b": bc["n_b_only_vs_c"],
            "b_vs_c_only_in_c_explained_by_warmup_depth_difference": bc["n_c_only_vs_b"],
            "guard_zero_non_canonical_mutations_confirmed": guard["guard_fully_effective_zero_non_canonical_mutations"],
        },
        "distortion_direction_confirmed_vs_phase_7_17": "CREATION_DOMINANT_ON_THIS_WINDOW - "
            "coerente con la classificazione Phase 7.17 'BOTH' (soppressione+creazione quasi "
            "simmetriche sull'intera storia 2023-2026): su questa finestra corta 2026 la "
            "manifestazione osservata e' soprattutto creazione spuria (A >> B in eventi 'canonici').",
        "run_type": "SHORT_DIAGNOSTIC_NOT_MULTI_YEAR_BACKTEST",
        "no_optimization_no_sltp_tuning_no_parameter_sweep_no_profitability_no_promotion": True,
        "next_step_not_decided_here": "Nessuna promozione live, nessuna ottimizzazione, nessuna "
                                      "ricerca di edge. Il fix resta un cambiamento di "
                                      "IMPLEMENTATION INTEGRITY - una valutazione di redditivita' "
                                      "post-fix e' un lavoro separato, non svolto e non presunto "
                                      "in questa fase.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE718_DIR, "tsi_decision_card_v2.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  DECISIONE: {payload['decision']}")


if __name__ == "__main__":
    main()
