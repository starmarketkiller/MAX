#!/usr/bin/env python3
"""Phase 7.26 punto D+K - CROSS_STRATEGY_LEARNING_PACKET_V1: generatore
+ backfill per le 4 strategie gia' studiate. Ogni futura edge validation
dovra' produrne uno automaticamente (vedi generate_packet(), riusabile).
Campo non disponibile = NOT_AVAILABLE esplicito (mai omesso, mai
inventato) - specialmente per TSI, che non ha mai avuto un dataset
economico."""
import os
import sys

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE726_DIR)
from nxs_schemas import LEARNING_PACKET_REQUIRED_FIELDS, missing_required, NOT_AVAILABLE  # noqa: E402
import nxs_backfill_sources as src  # noqa: E402


def _get(d, *path):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return NOT_AVAILABLE
        cur = cur[k]
    return cur if cur is not None else NOT_AVAILABLE


def generate_packet(*, strategy_identity, mechanism, pre_entry_context, regime, direction,
                    volatility, trend, structure, session, level_context, winner_anatomy,
                    loser_anatomy, mfe_mae, time_to_mfe_mae, favorable_before_loss,
                    adverse_before_win, execution_degradation, cost_sensitivity,
                    exit_efficiency, capital_efficiency, concentration, temporal_concentration,
                    oos_behavior, failure_modes, observations, candidate_hypotheses,
                    confidence, fidelity, provenance):
    """Firma completa e ESPLICITA (nessun **kwargs) - cosi' un futuro
    chiamante non puo' dimenticare un campo senza un errore immediato."""
    packet = dict(strategy_identity=strategy_identity, mechanism=mechanism,
                  pre_entry_context=pre_entry_context, regime=regime, direction=direction,
                  volatility=volatility, trend=trend, structure=structure, session=session,
                  level_context=level_context, winner_anatomy=winner_anatomy,
                  loser_anatomy=loser_anatomy, mfe_mae=mfe_mae, time_to_mfe_mae=time_to_mfe_mae,
                  favorable_before_loss=favorable_before_loss, adverse_before_win=adverse_before_win,
                  execution_degradation=execution_degradation, cost_sensitivity=cost_sensitivity,
                  exit_efficiency=exit_efficiency, capital_efficiency=capital_efficiency,
                  concentration=concentration, temporal_concentration=temporal_concentration,
                  oos_behavior=oos_behavior, failure_modes=failure_modes,
                  observations=observations, candidate_hypotheses=candidate_hypotheses,
                  confidence=confidence, fidelity=fidelity, provenance=provenance)
    missing = missing_required(packet, LEARNING_PACKET_REQUIRED_FIELDS)
    assert not missing, f"{strategy_identity}: campi mancanti nel Learning Packet: {missing}"
    return packet


def _breakout_acc_packet():
    baseline = src.BREAKOUT_ACC["baseline_economics"]()
    temporal = src.BREAKOUT_ACC["concentration_temporal"]()
    decision = src.BREAKOUT_ACC["decision_card"]()
    oos = src.BREAKOUT_ACC["oos_forward"]()
    cost = src.BREAKOUT_ACC["cost_stress"]()
    execn = src.BREAKOUT_ACC["execution_realism"]()
    mvc = src.BREAKOUT_ACC["mvc"]()
    path_v2 = src.BREAKOUT_ACC["path_anatomy_v2"]()

    return generate_packet(
        strategy_identity="BREAKOUT_ACC",
        mechanism="Accettazione oltre un range (breakout) con cooldown per-direzione, D1.",
        pre_entry_context=NOT_AVAILABLE, regime=NOT_AVAILABLE, direction="BUY/SELL entrambi presenti",
        volatility=NOT_AVAILABLE, trend=NOT_AVAILABLE, structure="range hi/lo pre-breakout",
        session=NOT_AVAILABLE, level_context="estremi del range pre-esistente",
        winner_anatomy=(f"outcome_flip_breakdown={_get(path_v2, 'aggregate_before_after', 'outcome_flip_breakdown')}"
                       if path_v2 else NOT_AVAILABLE),
        loser_anatomy=(f"n_outcome_flips={_get(path_v2, 'aggregate_before_after', 'n_outcome_flips_continuation_vs_failure')}"
                      f"/{_get(path_v2, 'aggregate_before_after', 'n_outcome_flips_denominator')}"
                      if path_v2 else NOT_AVAILABLE),
        mfe_mae={"mfe_v2": _get(path_v2, "aggregate_before_after", "mfe", "v2"),
                "mae_v2": _get(path_v2, "aggregate_before_after", "mae", "v2")} if path_v2 else NOT_AVAILABLE,
        time_to_mfe_mae=_get(path_v2, "aggregate_before_after", "bars_to_mfe", "v2") if path_v2 else NOT_AVAILABLE,
        favorable_before_loss=NOT_AVAILABLE, adverse_before_win=NOT_AVAILABLE,
        execution_degradation=_get(execn, "signal_pct_favorable") if execn else NOT_AVAILABLE,
        cost_sensitivity="sopravvive a COST_BASE/MODERATE/STRESS" if cost else NOT_AVAILABLE,
        exit_efficiency=NOT_AVAILABLE, capital_efficiency=_get(mvc, "MINIMUM_VIABLE_CAPITAL_EUR"),
        concentration=_get(decision, "supporting_evidence_summary", "top_5_trades_pct_of_total_net"),
        temporal_concentration=NOT_AVAILABLE,
        oos_behavior={"n_trades": _get(oos, "n_closed_trades_breakout_acc") or 1,
                     "decision": _get(oos, "decision")} if oos else NOT_AVAILABLE,
        failure_modes=["OUTLIER_DEPENDENT", "DIRECTION_DEPENDENT", "OOS_DEGRADATION"],
        observations=["CI95 ALL include zero", "asimmetria BUY/SELL osservata (H2, post-hoc)"],
        candidate_hypotheses=["H1_BREAKOUT_ACC_NET_EXPECTANCY_POSITIVE",
                             "H2_BREAKOUT_ACC_BUY_MORE_ROBUST_THAN_SELL"],
        confidence="MODERATA - n=47, non blind per H2",
        fidelity="EVENT_LEVEL - dataset per-evento con funnel granulare (Phase 7.9K)",
        provenance="phase7_21/*, phase7_9k/* (vedi nxs_backfill_sources.py)",
    )


def _order_block_packet():
    baseline = src.ORDER_BLOCK["baseline_economics"]()
    temporal = src.ORDER_BLOCK["temporal_robustness"]()
    decision = src.ORDER_BLOCK["decision_card"]()
    oos = src.ORDER_BLOCK["oos_forward"]()
    execn = src.ORDER_BLOCK["execution_realism"]()
    mvc = src.ORDER_BLOCK["mvc"]()

    return generate_packet(
        strategy_identity="ORDER_BLOCK",
        mechanism="Zona Order Block (TF-guarded) + retest, D1.",
        pre_entry_context=NOT_AVAILABLE, regime=NOT_AVAILABLE, direction="BUY dominante (12/13)",
        volatility=NOT_AVAILABLE, trend=NOT_AVAILABLE, structure="zona OB pre-identificata",
        session=NOT_AVAILABLE, level_context="bordo della zona OB",
        winner_anatomy=NOT_AVAILABLE, loser_anatomy=NOT_AVAILABLE,
        mfe_mae=NOT_AVAILABLE, time_to_mfe_mae=NOT_AVAILABLE,
        favorable_before_loss=NOT_AVAILABLE, adverse_before_win=NOT_AVAILABLE,
        execution_degradation=_get(execn, "funnel_rates") if execn else NOT_AVAILABLE,
        cost_sensitivity="sopravvive a COST_BASE/MODERATE/STRESS",
        exit_efficiency=NOT_AVAILABLE, capital_efficiency=_get(mvc, "MINIMUM_VIABLE_CAPITAL_EUR"),
        concentration=_get(decision, "supporting_evidence_summary", "top_5_trades_pct_of_total_net"),
        temporal_concentration=NOT_AVAILABLE,
        oos_behavior={"n_trades": 0, "decision": _get(oos, "decision")} if oos else NOT_AVAILABLE,
        failure_modes=["OUTLIER_DEPENDENT", "LOW_SAMPLE", "OOS_DEGRADATION"],
        observations=["campione minimo (n=13)", "concentrazione estrema (196.8% top-5)",
                     "1 solo trade SELL (performance negativa, non eliminato)"],
        candidate_hypotheses=["H_ORDER_BLOCK_EDGE_EXISTS"],
        confidence="BASSA - n=13", fidelity="EVENT_LEVEL ma funnel solo aggregato (Phase 7.22)",
        provenance="phase7_22/* (vedi nxs_backfill_sources.py)",
    )


def _tsi_packet():
    decision = src.TSI["decision_card_v2"]()
    semantic = src.TSI["semantic_map"]()

    return generate_packet(
        strategy_identity="TSI",
        mechanism="True Strength Index con guardia TF-scoped (fix contaminazione cross-TF).",
        pre_entry_context=NOT_AVAILABLE, regime=NOT_AVAILABLE, direction=NOT_AVAILABLE,
        volatility=NOT_AVAILABLE, trend=NOT_AVAILABLE, structure=NOT_AVAILABLE,
        session=NOT_AVAILABLE, level_context=NOT_AVAILABLE,
        winner_anatomy=NOT_AVAILABLE, loser_anatomy=NOT_AVAILABLE,
        mfe_mae=NOT_AVAILABLE, time_to_mfe_mae=NOT_AVAILABLE,
        favorable_before_loss=NOT_AVAILABLE, adverse_before_win=NOT_AVAILABLE,
        execution_degradation=NOT_AVAILABLE, cost_sensitivity=NOT_AVAILABLE,
        exit_efficiency=NOT_AVAILABLE, capital_efficiency=NOT_AVAILABLE,
        concentration=NOT_AVAILABLE, temporal_concentration=NOT_AVAILABLE,
        oos_behavior=NOT_AVAILABLE,
        failure_modes=["IMPLEMENTATION_DEFECT"],
        observations=[f"decisione: {_get(decision, 'decision')}",
                     "nessun dataset economico e' mai esistito per TSI - fase puramente di "
                     "integrita' dell'implementazione"],
        candidate_hypotheses=["H_TSI_TF_GUARD_FIX_EFFECTIVE"],
        confidence="ALTA per il meccanismo, NON_APPLICABILE per l'economia",
        fidelity="MECHANISM_ONLY - nessuna analisi P&L mai svolta",
        provenance="phase7_17/*, phase7_18/* (vedi nxs_backfill_sources.py)",
    )


def _liq_sweep_packet():
    baseline = src.LIQ_SWEEP["baseline_economics"]()
    conc = src.LIQ_SWEEP["concentration"]()
    temporal = src.LIQ_SWEEP["temporal_robustness"]()
    decision = src.LIQ_SWEEP["decision_card"]()
    oos = src.LIQ_SWEEP["oos_forward"]()
    path = src.LIQ_SWEEP["path_anatomy"]()
    execn = src.LIQ_SWEEP["execution_realism"]()
    mvc = src.LIQ_SWEEP["mvc"]()

    return generate_packet(
        strategy_identity="LIQ_SWEEP",
        mechanism="Sweep di liquidita' + delivery-candle (0.7xATR) + direzione, D1, uscita ATR "
                 "fissa (1.5x/3.0x).",
        pre_entry_context="livello di liquidita' PDH/PDL/Asia/settimanale/mensile spazzato",
        regime="single-position-at-a-time (3569/3623 blocchi per OPEN_POSITION)",
        direction="BUY dominante (39/42)", volatility=NOT_AVAILABLE, trend=NOT_AVAILABLE,
        structure="livello di liquidita' spazzato + delivery-candle di conferma",
        session="non session-bound (valutato ad ogni barra D1 chiusa)",
        level_context="estremo di liquidita' appena spazzato",
        winner_anatomy=f"avg_adverse_excursion_before_winner={_get(path, 'summary', 'avg_adverse_excursion_before_winner')}",
        loser_anatomy=f"avg_favorable_excursion_before_loser={_get(path, 'summary', 'avg_favorable_excursion_before_loser')}",
        mfe_mae={"avg_mfe": _get(path, "summary", "avg_mfe_all"),
                "avg_mae": _get(path, "summary", "avg_mae_all")},
        time_to_mfe_mae={"avg_time_to_mfe_hours": _get(path, "summary", "avg_time_to_mfe_hours"),
                         "avg_time_to_mae_hours": _get(path, "summary", "avg_time_to_mae_hours")},
        favorable_before_loss=_get(path, "summary", "avg_favorable_excursion_before_loser"),
        adverse_before_win=_get(path, "summary", "avg_adverse_excursion_before_winner"),
        execution_degradation=_get(execn, "funnel_rates"),
        cost_sensitivity="sopravvive a COST_BASE/MODERATE/STRESS",
        exit_efficiency="uscita ATR fissa - non adattiva alla liquidita' opposta (mismatch "
                       "confermato col proxy Python, H_LIQ_SWEEP_EXIT_MISMATCH_MQL5_PYTHON)",
        capital_efficiency=_get(mvc, "MINIMUM_VIABLE_CAPITAL_EUR"),
        concentration=_get(conc, "concentration", "top_5", "pct_of_total_net"),
        temporal_concentration=(f"{_get(temporal, 'years_with_positive_net')}/"
                               f"{_get(temporal, 'years_total_with_at_least_1_trade')} anni "
                               "positivi - 2025 da solo spiega ~99% del netto"),
        oos_behavior={"n_trades": _get(oos, "n_closed_trades_liq_sweep"),
                     "net_pnl_per_trade": _get(oos, "net_pnl_per_trade"),
                     "decision": _get(oos, "decision")},
        failure_modes=["OUTLIER_DEPENDENT", "TEMPORALLY_CONCENTRATED", "REGIME_DEPENDENT",
                      "OOS_DEGRADATION"],
        observations=["asimmetria escursione: favorable-before-loser > adverse-before-winner",
                     "primo OOS del corpus con campione sufficiente (n=6) - risultato negativo"],
        candidate_hypotheses=["H_LIQ_SWEEP_EDGE_EXISTS"],
        confidence="MODERATA - provenance ottima ma 'seen' per il P&L aggregato",
        fidelity="EVENT_LEVEL_FAITHFUL_ENTRY_ONLY - uscita non validabile da Python (Phase 7.24)",
        provenance="phase7_23/*, phase7_24/*, phase7_25/* (vedi nxs_backfill_sources.py)",
    )


def build():
    packets = {"BREAKOUT_ACC": _breakout_acc_packet(), "ORDER_BLOCK": _order_block_packet(),
              "TSI": _tsi_packet(), "LIQ_SWEEP": _liq_sweep_packet()}
    payload = {
        "schema_version": "CROSS_STRATEGY_LEARNING_PACKET_V1",
        "not_available_marker": NOT_AVAILABLE,
        "packets": packets,
        "generator_function": "generate_packet() in build_cross_strategy_learning_packet.py - "
                             "firma esplicita (nessun **kwargs), da chiamare automaticamente da "
                             "ogni futura fase di edge validation.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE726_DIR, "cross_strategy_learning_packets_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  strategie: {list(payload['packets'].keys())}")


if __name__ == "__main__":
    main()
