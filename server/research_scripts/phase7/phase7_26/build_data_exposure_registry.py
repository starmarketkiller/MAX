#!/usr/bin/env python3
"""Phase 7.26 punto A - GLOBAL_DATA_EXPOSURE_REGISTRY_V1. Backfill da
BREAKOUT_ACC (phase7_21), ORDER_BLOCK (phase7_22), TSI (phase7_17/18),
LIQ_SWEEP (phase7_23/24/25) - ogni record deriva da un artifact GIA'
ESISTENTE (data_exposure_map di ogni fase, o il decision card quando
non esiste una mappa esposizione dedicata, come per TSI). Nessun
periodo/data inventato: se una fase non ha mai dichiarato un confine
temporale, il campo resta None."""
import os
import sys

PHASE726_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE726_DIR, "..", "..", "..", ".."))
P7 = os.path.join(ROOT, "server", "research_scripts", "phase7")
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE726_DIR)
from nxs_schemas import DATA_EXPOSURE_REQUIRED_FIELDS, missing_required  # noqa: E402


def _record(**kw):
    r = {k: kw.get(k) for k in DATA_EXPOSURE_REQUIRED_FIELDS}
    missing = missing_required(r, DATA_EXPOSURE_REQUIRED_FIELDS)
    assert not missing, f"campi mancanti: {missing}"
    return r


def _breakout_acc_records():
    return [
        _record(dataset_id="BREAKOUT_ACC::2019.02.21_2026.06.09", symbol="GOLD",
               timeframe="D1", date_range=["2019.02.21", "2026.06.09"],
               strategy_identity="BREAKOUT_ACC", implementation_identity="BREAKOUT_ACC_INTENDED_D1_V2",
               experiment_run_ids=["GOLD_2019.02.03 00:00:00_sel9_r002/r003"],
               first_seen_date="2026-09 (Phase 7.9G/H/I/J/K)",
               development_exposure=True, integrity_audit_exposure=True,
               mechanism_discovery_exposure=True, visual_review_exposure=True,
               optimization_exposure=False, validation_exposure=True,
               oos_exposure=False, forward_exposure=False,
               holdout_status="EXPOSED_DISCOVERY_AND_BASELINE - usato per scoprire l'asimmetria "
                              "BUY/SELL (H2) e come baseline economica descrittiva (H1, prima "
                              "analisi economica su questi eventi, Phase 7.21) - MAI un vero "
                              "holdout indipendente."),
        _record(dataset_id="BREAKOUT_ACC::2026.06.10_2026.08.14", symbol="GOLD", timeframe="D1",
               date_range=["2026.06.10", "2026.08.14"], strategy_identity="BREAKOUT_ACC",
               implementation_identity="BREAKOUT_ACC_INTENDED_D1_V2",
               experiment_run_ids=["GOLD_2019.02.03 00:00:00_sel9_r002"],
               first_seen_date="Phase 7.21", development_exposure=False,
               integrity_audit_exposure=False, mechanism_discovery_exposure=False,
               visual_review_exposure=False, optimization_exposure=False,
               validation_exposure=False, oos_exposure=False, forward_exposure=False,
               holdout_status="NO_EVENTS - attraversato dal run ma zero segnali generati, "
                              "riportato solo per trasparenza."),
        _record(dataset_id="BREAKOUT_ACC::2026.08.15_2026.09.27", symbol="GOLD", timeframe="D1",
               date_range=["2026.08.15", "2026.09.27"], strategy_identity="BREAKOUT_ACC",
               implementation_identity="BREAKOUT_ACC_INTENDED_D1_V2",
               experiment_run_ids=["nxs_breakoutacc_forward_oos.ini (Phase 7.21)"],
               first_seen_date="Phase 7.21", development_exposure=False,
               integrity_audit_exposure=False, mechanism_discovery_exposure=False,
               visual_review_exposure=False, optimization_exposure=False,
               validation_exposure=False, oos_exposure=True, forward_exposure=True,
               holdout_status="CONSUMED_AS_OOS - vero holdout al momento di Phase 7.21, gia' "
                              "attraversato (1 trade, perdente) - non piu' disponibile come "
                              "holdout futuro."),
        _record(dataset_id="BREAKOUT_ACC::pre_2019.02.03", symbol="GOLD", timeframe="D1",
               date_range=[None, "2019.02.03"], strategy_identity="BREAKOUT_ACC",
               implementation_identity="BREAKOUT_ACC_INTENDED_D1_V2", experiment_run_ids=[],
               first_seen_date=None, development_exposure="SCONOSCIUTO", integrity_audit_exposure=None,
               mechanism_discovery_exposure=None, visual_review_exposure=None,
               optimization_exposure=None, validation_exposure=None, oos_exposure=None,
               forward_exposure=None, holdout_status="UNVERIFIED - disponibilita'/qualita' dati "
                              "non controllata, non usato in nessuna fase."),
    ]


def _order_block_records():
    return [
        _record(dataset_id="ORDER_BLOCK::pre_2023.10.02", symbol="GOLD", timeframe="D1",
               date_range=[None, "2023.10.02"], strategy_identity="ORDER_BLOCK",
               implementation_identity="ORDER_BLOCK_V2_TF_GUARDED", experiment_run_ids=[],
               first_seen_date=None, development_exposure="SCONOSCIUTO", integrity_audit_exposure=None,
               mechanism_discovery_exposure=None, visual_review_exposure=None,
               optimization_exposure=None, validation_exposure=None, oos_exposure=None,
               forward_exposure=None, holdout_status="NOT_USED"),
        _record(dataset_id="ORDER_BLOCK::2023.10.02_2026.08.24", symbol="GOLD", timeframe="D1",
               date_range=["2023.10.02", "2026.08.24"], strategy_identity="ORDER_BLOCK",
               implementation_identity="ORDER_BLOCK_V2_TF_GUARDED",
               experiment_run_ids=["Phase 7.14 diagnostic run (log persistente)", "Phase 7.22 base cert"],
               first_seen_date="Phase 7.13/7.14", development_exposure=False,
               integrity_audit_exposure=True, mechanism_discovery_exposure=True,
               visual_review_exposure=True, optimization_exposure=False, validation_exposure=True,
               oos_exposure=False, forward_exposure=False,
               holdout_status="SEEN_FOR_SIGNALS_NOT_FOR_ECONOMICS - Phase 7.13/7.14/7.16 hanno "
                              "guardato questa finestra per l'integrita' del fix (segnali/zone), "
                              "MAI per P&L - Phase 7.22 e' la prima analisi economica in assoluto "
                              "(13 trade)."),
        _record(dataset_id="ORDER_BLOCK::2026.08.25_2026.09.27", symbol="GOLD", timeframe="D1",
               date_range=["2026.08.25", "2026.09.27"], strategy_identity="ORDER_BLOCK",
               implementation_identity="ORDER_BLOCK_V2_TF_GUARDED",
               experiment_run_ids=["nxs_orderblock_forward_oos.ini (Phase 7.22)"],
               first_seen_date="Phase 7.22", development_exposure=False,
               integrity_audit_exposure=False, mechanism_discovery_exposure=False,
               visual_review_exposure=False, optimization_exposure=False, validation_exposure=False,
               oos_exposure=True, forward_exposure=True,
               holdout_status="CONSUMED_AS_OOS - 0 trade generati (INSUFFICIENT_OOS_SAMPLE), non "
                              "piu' disponibile come holdout futuro."),
    ]


def _tsi_records():
    return [
        _record(dataset_id="TSI::2026.01.01_2026.08.25_short_diag", symbol="GOLD", timeframe="H4",
               date_range=["2026.01.01", "2026.08.25"], strategy_identity="TSI",
               implementation_identity="TSI_TF_SCOPED_POSTFIX",
               experiment_run_ids=["Phase 7.18 pre/post-fix diagnostic run"],
               first_seen_date="Phase 7.18", development_exposure=False,
               integrity_audit_exposure=True, mechanism_discovery_exposure=True,
               visual_review_exposure=False, optimization_exposure=False, validation_exposure=True,
               oos_exposure=None, forward_exposure=None,
               holdout_status="NOT_APPLICABLE_NO_ECONOMIC_DATASET - TSI non ha mai avuto un "
                              "dataset economico: questa finestra e' stata usata SOLO per "
                              "verificare causalmente il fix (guardia TF-scoped), decisione "
                              "FIX_CAUSALLY_VALIDATED - concetto di holdout economico non "
                              "applicabile per costruzione."),
    ]


def _liq_sweep_records():
    return [
        _record(dataset_id="LIQ_SWEEP::pre_2023.10.02", symbol="GOLD", timeframe="D1",
               date_range=[None, "2023.10.02"], strategy_identity="LIQ_SWEEP",
               implementation_identity="LIQ_SWEEP_SEL7_POSTFIX_DETECTOR_20260914",
               experiment_run_ids=[], first_seen_date=None, development_exposure="SCONOSCIUTO",
               integrity_audit_exposure=None, mechanism_discovery_exposure=None,
               visual_review_exposure=None, optimization_exposure=None, validation_exposure=None,
               oos_exposure=None, forward_exposure=None, holdout_status="NOT_USED"),
        _record(dataset_id="LIQ_SWEEP::2023.10.02_2026.06.30", symbol="GOLD", timeframe="D1",
               date_range=["2023.10.02", "2026.06.30"], strategy_identity="LIQ_SWEEP",
               implementation_identity="LIQ_SWEEP_SEL7_POSTFIX_DETECTOR_20260914",
               experiment_run_ids=["Phase 7.23 diagnostic run (harness isolato)"],
               first_seen_date="Phase 7.23", development_exposure=False,
               integrity_audit_exposure=True, mechanism_discovery_exposure=True,
               visual_review_exposure=True, optimization_exposure=False, validation_exposure=True,
               oos_exposure=False, forward_exposure=False,
               holdout_status="SEEN_FOR_NET_PNL_TOTALE_NOT_FOR_GRANULAR_STATS - Phase 7.24 ha gia' "
                              "calcolato e riportato il net P&L aggregato ALL (+$1.076,30) - Phase "
                              "7.25 e' la prima analisi granulare (expectancy per direzione, "
                              "concentrazione, CI, path anatomy)."),
        _record(dataset_id="LIQ_SWEEP::2026.07.01_2026.09.27", symbol="GOLD", timeframe="D1",
               date_range=["2026.07.01", "2026.09.27"], strategy_identity="LIQ_SWEEP",
               implementation_identity="LIQ_SWEEP_SEL7_POSTFIX_DETECTOR_20260914",
               experiment_run_ids=["Phase 7.25 OOS forward run (harness isolato)"],
               first_seen_date="Phase 7.25", development_exposure=False,
               integrity_audit_exposure=False, mechanism_discovery_exposure=False,
               visual_review_exposure=False, optimization_exposure=False, validation_exposure=False,
               oos_exposure=True, forward_exposure=True,
               holdout_status="CONSUMED_AS_OOS - 6 trade, esito negativo, non piu' disponibile "
                              "come holdout futuro."),
    ]


def build():
    records = _breakout_acc_records() + _order_block_records() + _tsi_records() + _liq_sweep_records()
    by_id = {r["dataset_id"]: r for r in records}
    payload = {
        "records": records, "n_records": len(records),
        "backfilled_strategies": ["BREAKOUT_ACC", "ORDER_BLOCK", "TSI", "LIQ_SWEEP"],
        "query_function_name": "is_genuinely_untouched(dataset_id)",
        "holdout_status_values_seen": sorted(set(r["holdout_status"].split(" - ")[0] for r in records)),
    }
    return payload, by_id


def is_genuinely_untouched(dataset_id, by_id=None):
    """Risponde 'questa finestra e' ancora genuinamente untouched?' -
    True SOLO per holdout_status che inizia con 'NOT_USED' o 'UNVERIFIED'
    (mai ancora attraversato) - qualunque 'CONSUMED_AS_OOS'/'SEEN_*'/
    'EXPOSED_*' e' NO per costruzione."""
    if by_id is None:
        _, by_id = build()
    r = by_id.get(dataset_id)
    if r is None:
        return None  # dataset_id sconosciuto - MAI assunto untouched per default
    status = r["holdout_status"].split(" - ")[0]
    return status in ("NOT_USED", "UNVERIFIED")


def main():
    payload, _ = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE726_DIR, "data_exposure_registry_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  {payload['n_records']} record, strategie: {payload['backfilled_strategies']}")


if __name__ == "__main__":
    main()
