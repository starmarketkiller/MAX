#!/usr/bin/env python3
"""Phase 7.26 punto D+K - CROSS_STRATEGY_LEARNING_PACKET_V1: generatore
+ backfill per le 4 strategie gia' studiate. Ogni futura edge validation
dovra' produrne uno automaticamente (vedi generate_packet(), riusabile).
Campo non disponibile = NOT_AVAILABLE esplicito (mai omesso, mai
inventato) - specialmente per TSI, che non ha mai avuto un dataset
economico."""
import json
import os
import sys

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE726_DIR)
from nxs_schemas import LEARNING_PACKET_REQUIRED_FIELDS, missing_required, NOT_AVAILABLE  # noqa: E402
import nxs_backfill_sources as src  # noqa: E402


def _buy_dominance_observations(strategy_identity):
    """Phase 7.27: aggiunge (non sostituisce) l'osservazione del test
    di benchmark trasversale sulla dominanza BUY - stessa fonte per le
    3 strategie economiche, letta da un solo posto per coerenza."""
    decision = src.BUY_DOMINANCE_BENCHMARK["decision_card"]()
    per_strat = src.BUY_DOMINANCE_BENCHMARK["per_strategy_results"]()
    if not decision or not per_strat:
        return []
    d = per_strat.get(strategy_identity, {}).get("primary_analysis_summary", {})
    return [f"Phase 7.27 BUY-dominance benchmark: direzione={d.get('direction_of_effect')} "
           f"vs benchmark long regime-matched @ h{d.get('horizon', '?').lstrip('h')} - decisione "
           f"trasversale: {decision['decision']} (dataset di discovery, non un holdout - "
           "SUPPORTED_AS_HYPOTHESIS al massimo, mai edge)."]


def _get(d, *path):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return NOT_AVAILABLE
        cur = cur[k]
    return cur if cur is not None else NOT_AVAILABLE


# --- NEXUS TASK #0003 (Approve Safety Net Backfill) --------------------------
# Amendment al builder originale: 6 campi (5 BREAKOUT_ACC + 1 ORDER_BLOCK) erano
# NOT_AVAILABLE non per mancanza di dati, ma perche' mai calcolati/propagati -
# vedi NEXUS TASK #0002 (server/orchestrator_v1/nexus_task_0002_result_v1.json)
# per l'investigazione completa e la classificazione DERIVABLE_NOW. Le formule
# qui sotto sono le STESSE gia' indipendentemente verificate in quella fase
# (reimplementate qui in Python puro, deterministico - MAI una chiamata a un
# LLM in un builder di artifact canonico, altrimenti l'artifact non sarebbe
# piu' riproducibile bit-per-bit, violando test_all_artifacts_deterministic).
# ORDER_BLOCK.exit_efficiency e' rimasto DELIBERATAMENTE NOT_AVAILABLE: il
# worker locale non e' riuscito, dopo un retry delimitato, a produrre una
# narrativa affidabile per quel campo specifico - escalation genuina a
# TIER3_CLAUDE, non ancora risolta al momento di questo amendment.

def _compute_temporal_concentration(events):
    by_year = {}
    for e in events:
        y = e["entry_time"][:4]
        by_year.setdefault(y, []).append(e["net_pnl"])
    per_year = {y: {"n_trades": len(v), "net_pnl_sum": sum(v),
                   "win_rate": sum(1 for p in v if p > 0) / len(v)}
               for y, v in by_year.items()}
    out = dict(per_year)
    out["years_with_positive_net"] = sum(1 for v in per_year.values() if v["net_pnl_sum"] > 0)
    out["years_total_with_at_least_1_trade"] = len(per_year)
    return out


def _narrative_temporal_concentration(data):
    pos = data["years_with_positive_net"]
    total = data["years_total_with_at_least_1_trade"]
    return f"{pos}/{total} anni con profitto netto positivo su {total} con almeno un trade."


def _compute_exit_efficiency(events):
    """NOTA (trovata durante la risoluzione dell'escalation ORDER_BLOCK.
    exit_efficiency): il campo 'direction' nei dataset economici (BREAKOUT_ACC,
    ORDER_BLOCK) e' un INTERO (1=BUY, -1=SELL), non la stringa 'BUY'/'SELL' -
    un confronto con la stringa non intercetta mai il caso BUY. Verificato
    algebricamente e numericamente (sia per BREAKOUT_ACC che per ORDER_BLOCK)
    che per QUESTA specifica formula a rapporto l'errore era innocuo
    (captured e available si negano entrambi in modo consistente, il
    rapporto risultante e' identico) - corretto qui comunque per robustezza,
    nessun valore gia' applicato al Vault cambia."""
    ratios, skipped = [], 0
    for e in events:
        if e["direction"] == 1:
            captured = e["exit_price"] - e["entry_price"]
            available = e["entry_tp"] - e["entry_price"]
        else:
            captured = e["entry_price"] - e["exit_price"]
            available = e["entry_price"] - e["entry_tp"]
        if available == 0:
            skipped += 1
            continue
        ratios.append(captured / available)
    return {"mean_exit_efficiency_ratio": sum(ratios) / len(ratios) if ratios else None,
           "n_events_used": len(ratios), "n_events_skipped_zero_available": skipped}


def _narrative_exit_efficiency(data):
    ratio = data["mean_exit_efficiency_ratio"]
    return (f"Rapporto medio di efficienza di uscita: {ratio:.2f} (su {data['n_events_used']} "
           f"eventi, {data['n_events_skipped_zero_available']} esclusi per assenza di target).")


def _breakout_acc_funnel_rates(execn):
    """funnel_counts GIA' presenti in execution_realism_v1.json (Phase 7.21) -
    solo mai convertiti in funnel_rates (bug di key-path nel builder
    originale: cercava la chiave piatta 'signal_pct_favorable', mai esistita -
    stessa convenzione/formula gia' usata per ORDER_BLOCK/LIQ_SWEEP)."""
    fc = execn["funnel_counts"]
    denom = fc["live_trace_generated_67"]
    return {
        "pct_generated_that_get_blocked": round(fc["blocked_by_execution_gates_11"] / denom * 100, 4),
        "pct_generated_that_get_rejected": round(
            fc["order_sent_47_plus_rejected_9"]["sent_rejected"] / denom * 100, 4),
        "pct_generated_that_open_per_certificate": round(
            fc["opened_with_real_pnl_47"] / denom * 100, 4),
    }


def _breakout_acc_favorable_adverse(path_v2, events):
    """Incrocia MFE/MAE per-evento (path_v2, Phase 7.9K) con l'esito
    vinto/perso (net_pnl, Phase 7.21) tramite event_id - nessun nuovo dato,
    solo join+media aritmetica su due artifact gia' esistenti."""
    outcome_by_id = {e["event_id"]: e["net_pnl"] for e in events}

    def _conditional_mean(field, want_win):
        vals = [pe[field] for pe in path_v2["per_event_before_after"]
               if pe["event_id"] in outcome_by_id
               and (outcome_by_id[pe["event_id"]] > 0) == want_win]
        if not vals:
            return NOT_AVAILABLE
        return {"n": len(vals), "mean": round(sum(vals) / len(vals), 4),
               "median": round(sorted(vals)[len(vals) // 2], 4)}

    return _conditional_mean("v2_mfe", want_win=False), _conditional_mean("v2_mae", want_win=True)


def _load_breakout_acc_events_for_backfill():
    sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_21"))
    from nxs_breakoutacc_dataset_loader import load_opened_events, net_pnl  # noqa: E402
    events = load_opened_events()
    return [{"event_id": e["event_id"], "entry_time": e["entry_fill_time"], "net_pnl": net_pnl(e),
            "entry_price": e["entry_fill_price"], "exit_price": e["exit_fill_price"],
            "entry_tp": e["entry_tp"], "direction": e["direction"]} for e in events]


def _load_order_block_events_for_backfill():
    path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_22",
                       "canonical_economic_dataset_v1.json")
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)["payload"]
    return [{"entry_time": e["entry_time"], "net_pnl": e["net_pnl"], "entry_price": e["entry_price"],
            "exit_price": e["exit_price"], "entry_tp": e["entry_tp"], "direction": e["direction"]}
           for e in payload["events"]]


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

    backfill_events = _load_breakout_acc_events_for_backfill()
    backfill_temporal = _compute_temporal_concentration(backfill_events)
    backfill_exit_eff = _compute_exit_efficiency(backfill_events)
    backfill_funnel_rates = _breakout_acc_funnel_rates(execn) if execn else NOT_AVAILABLE
    backfill_favorable_before_loss, backfill_adverse_before_win = (
        _breakout_acc_favorable_adverse(path_v2, backfill_events) if path_v2
        else (NOT_AVAILABLE, NOT_AVAILABLE))

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
        favorable_before_loss=backfill_favorable_before_loss,
        adverse_before_win=backfill_adverse_before_win,
        execution_degradation=backfill_funnel_rates,
        cost_sensitivity="sopravvive a COST_BASE/MODERATE/STRESS" if cost else NOT_AVAILABLE,
        exit_efficiency=_narrative_exit_efficiency(backfill_exit_eff),
        capital_efficiency=_get(mvc, "MINIMUM_VIABLE_CAPITAL_EUR"),
        concentration=_get(decision, "supporting_evidence_summary", "top_5_trades_pct_of_total_net"),
        temporal_concentration=_narrative_temporal_concentration(backfill_temporal),
        oos_behavior={"n_trades": _get(oos, "n_closed_trades_breakout_acc") or 1,
                     "decision": _get(oos, "decision")} if oos else NOT_AVAILABLE,
        failure_modes=["OUTLIER_DEPENDENT", "DIRECTION_DEPENDENT", "OOS_DEGRADATION"],
        observations=["CI95 ALL include zero", "asimmetria BUY/SELL osservata (H2, post-hoc)"]
                     + _buy_dominance_observations("BREAKOUT_ACC"),
        candidate_hypotheses=["H1_BREAKOUT_ACC_NET_EXPECTANCY_POSITIVE",
                             "H2_BREAKOUT_ACC_BUY_MORE_ROBUST_THAN_SELL"],
        confidence="MODERATA - n=47, non blind per H2",
        fidelity="EVENT_LEVEL - dataset per-evento con funnel granulare (Phase 7.9K)",
        provenance="phase7_21/*, phase7_9k/* (vedi nxs_backfill_sources.py) + auto-backfill "
                  "NEXUS TASK #0002/#0003 (temporal_concentration, exit_efficiency, "
                  "execution_degradation, favorable_before_loss, adverse_before_win - vedi "
                  "server/orchestrator_v1/nexus_task_0002_result_v1.json per provenance "
                  "dettagliata)",
    )


def _order_block_packet():
    baseline = src.ORDER_BLOCK["baseline_economics"]()
    temporal = src.ORDER_BLOCK["temporal_robustness"]()
    decision = src.ORDER_BLOCK["decision_card"]()
    oos = src.ORDER_BLOCK["oos_forward"]()
    execn = src.ORDER_BLOCK["execution_realism"]()
    mvc = src.ORDER_BLOCK["mvc"]()

    backfill_events = _load_order_block_events_for_backfill()
    backfill_temporal = _compute_temporal_concentration(backfill_events)
    # exit_efficiency: risolto da Claude (escalation TIER3, NEXUS TASK #0002) dopo che il
    # worker locale non era riuscito, dopo un retry delimitato, a produrre una narrativa
    # affidabile per questo campo - il VALORE era gia' corretto (verificato indipendentemente
    # da Claude ricalcolando dal dataset canonico), il problema era solo di generazione
    # narrativa. Vedi server/orchestrator_v1/nexus_task_0002_result_v1.json per il dettaglio
    # dell'escalation e la risoluzione.
    backfill_exit_eff = _compute_exit_efficiency(backfill_events)

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
        exit_efficiency=_narrative_exit_efficiency(backfill_exit_eff),
        capital_efficiency=_get(mvc, "MINIMUM_VIABLE_CAPITAL_EUR"),
        concentration=_get(decision, "supporting_evidence_summary", "top_5_trades_pct_of_total_net"),
        temporal_concentration=_narrative_temporal_concentration(backfill_temporal),
        oos_behavior={"n_trades": 0, "decision": _get(oos, "decision")} if oos else NOT_AVAILABLE,
        failure_modes=["OUTLIER_DEPENDENT", "LOW_SAMPLE", "OOS_DEGRADATION"],
        observations=["campione minimo (n=13)", "concentrazione estrema (196.8% top-5)",
                     "1 solo trade SELL (performance negativa, non eliminato)"]
                     + _buy_dominance_observations("ORDER_BLOCK"),
        candidate_hypotheses=["H_ORDER_BLOCK_EDGE_EXISTS"],
        confidence="BASSA - n=13", fidelity="EVENT_LEVEL ma funnel solo aggregato (Phase 7.22)",
        provenance="phase7_22/* (vedi nxs_backfill_sources.py) + auto-backfill NEXUS TASK "
                  "#0002/#0003 (temporal_concentration) + risoluzione escalation Claude "
                  "TIER3 (exit_efficiency, vedi "
                  "server/orchestrator_v1/nexus_task_0002_result_v1.json)",
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
                     "primo OOS del corpus con campione sufficiente (n=6) - risultato negativo"]
                     + _buy_dominance_observations("LIQ_SWEEP"),
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
