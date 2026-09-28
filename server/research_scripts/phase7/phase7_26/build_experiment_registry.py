#!/usr/bin/env python3
"""Phase 7.26.B - EXPERIMENT_REGISTRY_V1. Un record per esperimento
reale gia' eseguito (run MT5 o analisi Python), backfillato dai
manifest/decision-card gia' esistenti. Campo assente = None, mai
inventato."""
import os
import sys

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE726_DIR)
from nxs_schemas import EXPERIMENT_REQUIRED_FIELDS, missing_required  # noqa: E402
import nxs_backfill_sources as src  # noqa: E402


def _record(**kw):
    for f in EXPERIMENT_REQUIRED_FIELDS:
        kw.setdefault(f, None)
    return kw


def _breakout_acc_experiments():
    baseline = src.BREAKOUT_ACC["baseline_economics"]()
    decision = src.BREAKOUT_ACC["decision_card"]()
    oos = src.BREAKOUT_ACC["oos_forward"]()
    exp = []
    if baseline:
        exp.append(_record(
            experiment_id="EXP_BREAKOUT_ACC_DISCOVERY_BASELINE",
            hypothesis_id="H1_BREAKOUT_ACC_NET_EXPECTANCY_POSITIVE",
            strategy_identity="BREAKOUT_ACC", implementation_identity="BREAKOUT_ACC_INTENDED_D1_V2",
            run_id="GOLD_2019.02.03 00:00:00_sel9_r002/r003",
            dataset_id="BREAKOUT_ACC::2019.02.21_2026.06.09",
            code_sha=None, config_hash=None,
            period=["2019.02.21", "2026.06.09"],
            method="Baseline economica su 47 eventi (fill/P&L reali), no tuning.",
            metrics={"n_trades": baseline["ALL"]["n_trades"],
                    "net_expectancy_per_trade": baseline["ALL"]["net_expectancy_per_trade"],
                    "profit_factor": baseline["ALL"]["profit_factor"]},
            artifacts=["phase7_21/baseline_economics_v1.json"],
            verdict=decision.get("decision") if decision else None,
            confidence="MODERATA - campione 47, non blind per H2 (vedi data_exposure_map)",
            limitations="Non un vero OOS - stesso campione usato per scoprire l'asimmetria BUY/SELL.",
            created_at="Phase 7.21",
        ))
    if oos:
        exp.append(_record(
            experiment_id="EXP_BREAKOUT_ACC_OOS_FORWARD",
            hypothesis_id="H1_BREAKOUT_ACC_NET_EXPECTANCY_POSITIVE",
            strategy_identity="BREAKOUT_ACC", implementation_identity="BREAKOUT_ACC_INTENDED_D1_V2",
            run_id=None, dataset_id="BREAKOUT_ACC::2026.08.15_2026.09.27",
            code_sha=None, config_hash=None, period=oos.get("window"),
            method="Run MT5 dedicato su finestra forward genuinamente untouched.",
            metrics={"n_trades": oos.get("n_closed_trades_breakout_acc") or oos.get("n_trades"),
                    "net_pnl_per_trade": oos.get("net_pnl_per_trade")},
            artifacts=["phase7_21/oos_forward_analysis_v1.json"],
            verdict=oos.get("decision"), confidence="BASSA (n=1)",
            limitations="Campione troppo piccolo per qualunque conclusione.",
            created_at="Phase 7.21",
        ))
    return exp


def _order_block_experiments():
    baseline = src.ORDER_BLOCK["baseline_economics"]()
    decision = src.ORDER_BLOCK["decision_card"]()
    oos = src.ORDER_BLOCK["oos_forward"]()
    exp = []
    if baseline:
        exp.append(_record(
            experiment_id="EXP_ORDER_BLOCK_DISCOVERY_BASELINE",
            hypothesis_id="H_ORDER_BLOCK_EDGE_EXISTS",
            strategy_identity="ORDER_BLOCK", implementation_identity="ORDER_BLOCK_V2_TF_GUARDED",
            run_id=None, dataset_id="ORDER_BLOCK::2023.10.02_2026.08.24",
            code_sha=None, config_hash=None, period=["2023.10.02", "2026.08.24"],
            method="Baseline economica su 13 trade reali gia' presenti nel log persistente.",
            metrics={"n_trades": baseline["ALL"]["n_trades"],
                    "net_expectancy_per_trade": baseline["ALL"]["net_expectancy_per_trade"],
                    "profit_factor": baseline["ALL"]["profit_factor"]},
            artifacts=["phase7_22/orderblock_baseline_economics_v1.json"],
            verdict=decision.get("decision") if decision else None,
            confidence="BASSA - campione 13, concentrazione estrema (196.8% top-5)",
            limitations="Scarto di 1 trade fra certificato e CSV non risolto.",
            created_at="Phase 7.22",
        ))
    if oos:
        exp.append(_record(
            experiment_id="EXP_ORDER_BLOCK_OOS_FORWARD",
            hypothesis_id="H_ORDER_BLOCK_EDGE_EXISTS",
            strategy_identity="ORDER_BLOCK", implementation_identity="ORDER_BLOCK_V2_TF_GUARDED",
            run_id=None, dataset_id="ORDER_BLOCK::2026.08.25_2026.09.27",
            code_sha=None, config_hash=None, period=oos.get("window"),
            method="Run MT5 dedicato su finestra forward.",
            metrics={"n_trades": oos.get("n_closed_trades_order_block") or oos.get("n_trades")},
            artifacts=["phase7_22/orderblock_oos_forward_analysis_v1.json"],
            verdict=oos.get("decision"), confidence="NULLA (n=0)",
            limitations="Zero segnali generati nella finestra.",
            created_at="Phase 7.22",
        ))
    return exp


def _tsi_experiments():
    dec = src.TSI["decision_card_v2"]()
    if not dec:
        return []
    return [_record(
        experiment_id="EXP_TSI_FIX_CAUSAL_VALIDATION",
        hypothesis_id="H_TSI_TF_GUARD_FIX_EFFECTIVE",
        strategy_identity="TSI", implementation_identity="TSI_TF_GUARDED_POSTFIX",
        run_id=None, dataset_id="TSI::2026.01.01_2026.08.25_short_diag",
        code_sha=dec.get("baseline_commit"), config_hash=None,
        period=["2026.01.01", "2026.08.25"],
        method="A/B pre/post-fix su stessi tick reali + confronto B(EA)/C(ricostruzione Python).",
        metrics={"non_d1_rows_post_fix": 0},
        artifacts=["phase7_18/tsi_decision_card_v2.json"],
        verdict=dec.get("decision"),
        confidence="ALTA per il meccanismo - NESSUNA per l'economia (nessun P&L mai misurato).",
        limitations="Puramente un fix di integrita' - non e' e non pretende di essere un'edge "
                    "validation.",
        created_at="Phase 7.18",
    )]


def _liq_sweep_experiments():
    baseline = src.LIQ_SWEEP["baseline_economics"]()
    decision = src.LIQ_SWEEP["decision_card"]()
    oos = src.LIQ_SWEEP["oos_forward"]()
    integrity = src.LIQ_SWEEP["integrity_decision"]()
    exp = []
    if integrity:
        exp.append(_record(
            experiment_id="EXP_LIQ_SWEEP_INTEGRITY_AUDIT",
            hypothesis_id="H_LIQ_SWEEP_HTF_MISMATCH", strategy_identity="LIQ_SWEEP",
            implementation_identity="LIQ_SWEEP_POSTFIX_DETECTOR",
            run_id="LIQ_SWEEP_2023.10.02_2026.06.30_66767008acee43f3_20260927T211708Z_882af939",
            dataset_id="LIQ_SWEEP::2023.10.02_2026.06.30",
            code_sha="7aba39a19ed6fe22c9d414ddf390c00036805d0e", config_hash="66767008acee43f3",
            period=["2023.10.02", "2026.06.30"],
            method="Trace statico riga-per-riga (NXS_ActivateTF->NXS_UpdateIndicators->"
                  "NXS_CollectRaw) + run diagnostico isolato.",
            metrics={"n_events": 42}, artifacts=["phase7_23/liq_sweep_decision_card_v1.json"],
            verdict=integrity.get("decision"), confidence="ALTA (verifica per costruzione)",
            limitations="Ipotesi verificata e RESPINTA - nessun mismatch trovato.",
            created_at="Phase 7.23",
        ))
    if baseline:
        exp.append(_record(
            experiment_id="EXP_LIQ_SWEEP_EDGE_BASELINE",
            hypothesis_id="H_LIQ_SWEEP_EDGE_EXISTS", strategy_identity="LIQ_SWEEP",
            implementation_identity="LIQ_SWEEP_POSTFIX_DETECTOR",
            run_id="LIQ_SWEEP_2023.10.02_2026.06.30_66767008acee43f3_20260927T211708Z_882af939",
            dataset_id="LIQ_SWEEP::2023.10.02_2026.06.30",
            code_sha="7aba39a19ed6fe22c9d414ddf390c00036805d0e", config_hash="66767008acee43f3",
            period=["2023.10.02", "2026.06.30"],
            method="Baseline su 42 eventi CLOSED, harness di isolamento (provenance completa).",
            metrics={"n_trades": baseline["ALL"]["n_trades"],
                    "net_expectancy_per_trade": baseline["ALL"]["net_expectancy_per_trade"],
                    "profit_factor": baseline["ALL"]["profit_factor"]},
            artifacts=["phase7_25/baseline_economics_v1.json"],
            verdict=decision.get("decision") if decision else None,
            confidence="MODERATA - provenance ottima, ma 'seen' per il P&L aggregato (Phase 7.24)",
            limitations="99% del netto da un solo anno (2025) - vedi temporal_robustness.",
            created_at="Phase 7.25",
        ))
    if oos:
        exp.append(_record(
            experiment_id="EXP_LIQ_SWEEP_OOS_FORWARD",
            hypothesis_id="H_LIQ_SWEEP_EDGE_EXISTS", strategy_identity="LIQ_SWEEP",
            implementation_identity="LIQ_SWEEP_POSTFIX_DETECTOR",
            run_id=oos.get("run_id"), dataset_id="LIQ_SWEEP::2026.07.01_2026.09.27",
            code_sha=None, config_hash=None, period=oos.get("window"),
            method="Run MT5 dedicato (harness isolamento) su finestra forward genuinamente "
                  "untouched.",
            metrics={"n_trades": oos.get("n_closed_trades_liq_sweep"),
                    "net_pnl_per_trade": oos.get("net_pnl_per_trade")},
            artifacts=["phase7_25/oos_forward_analysis_v1.json"],
            verdict=oos.get("decision"),
            confidence="PRIMO campione OOS del corpus >= soglia minima (n=6)",
            limitations="Risultato negativo (-$539.30) - non prova l'assenza di edge (n piccolo) "
                       "ma e' un segnale contrario reale.",
            created_at="Phase 7.25",
        ))
    return exp


def build():
    experiments = (_breakout_acc_experiments() + _order_block_experiments() +
                  _tsi_experiments() + _liq_sweep_experiments())
    for e in experiments:
        missing = missing_required(e, EXPERIMENT_REQUIRED_FIELDS)
        if missing:
            raise AssertionError(f"{e.get('experiment_id')} manca campi: {missing}")
    payload = {
        "schema_version": "EXPERIMENT_REGISTRY_V1",
        "principle": "Ogni esperimento e' un fatto gia' accaduto (run/analisi gia' eseguiti) - "
                    "backfillato dagli artifact esistenti, nessun campo mancante sostituito da "
                    "un'invenzione.",
        "experiments": experiments, "n_experiments": len(experiments),
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE726_DIR, "experiment_registry_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  n_experiments={payload['n_experiments']}")


if __name__ == "__main__":
    main()
