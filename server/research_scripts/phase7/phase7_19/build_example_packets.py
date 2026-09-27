#!/usr/bin/env python3
"""Phase 7.19 punto 10 - almeno 3 EVENT_AUDIT_PACKET_V1 dimostrativi
usando artifact GIA' disponibili (nessun dato fabbricato). Le tre
strategie scelte per mostrare la generalita' dello schema:

  1. BREAKOUT_ACC - meccanismo a soglia+cooldown, evento REALE con fill
     e path anatomy completi (Phase 7.9H, Fidelity A/B).
  2. ORDER_BLOCK - meccanismo a zona/state machine SMC, evento REALE
     post-fix con stato di zona catturato dal vivo (Phase 7.14,
     Fidelity B/C).
  3. SH_BMS_RTO - meccanismo sweep+struttura, NESSUN trace reale
     disponibile in questo progetto - packet SOLO strutturale
     (Fidelity D), scelto ESPLICITAMENTE al posto di TSI perche' TSI e'
     "ancora in modifica" in questa sessione (Phase 7.18, fix live in
     corso) - vedi nota below.

Nessun campo mancante viene generato: dove il dato reale non esiste in
nessun artifact disponibile, il campo usa absence_reason
(NOT_AVAILABLE / NOT_RECORDED / UNKNOWN / NOT_APPLICABLE).
"""
import os
import sys

PHASE719_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE719_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def _absent(reason, note=None):
    d = {"status": "ABSENT", "reason": reason}
    if note:
        d["note"] = note
    return d


def _present(value):
    return {"status": "PRESENT", "value": value}


def _priced(value, source, fidelity, is_proxy=False, proxy_reason=None, ts=None):
    d = {"value": value, "source": source, "fidelity": fidelity, "is_proxy": is_proxy}
    if proxy_reason:
        d["proxy_reason"] = proxy_reason
    if ts:
        d["timestamp"] = ts
    return d


def _ts(value, source, precision, confidence, timezone="BROKER_SERVER_TZ"):
    return {"value": value, "source": source, "timezone": timezone, "precision": precision, "confidence": confidence}


def _feature(name, value, available, depends_future, verified, method=None, closed_only=None):
    d = {"name": name, "value": value, "available_at_decision_time": available,
        "depends_on_future_data": depends_future, "causality_verified": verified}
    if method:
        d["causality_verification_method"] = method
    if closed_only is not None:
        d["uses_closed_bar_only"] = closed_only
    return d


# =====================================================================
# Packet 1 - BREAKOUT_ACC (evento REALE, Phase 7.9H, event_id evt_1209b7abca9456d1)
# =====================================================================
def build_packet_breakout_acc():
    doc = load_json(os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9h",
                                 "breakout_acc_intended_d1_v1_dataset.json"))
    ev = next(e for e in doc["payload"]["events"] if e["event_id"] == "evt_1209b7abca9456d1")

    return {
        "schema_version": "EVENT_AUDIT_PACKET_V1",
        "identity": {
            "event_id": ev["event_id"], "strategy_id": "BREAKOUT_ACC",
            "canonical_strategy_identity": "BREAKOUT_ACC_INTENDED_D1_V1",
            "strategy_version": "post-fix Phase 7.9F/7.9G (guardia TF applicata)",
            "implementation_identity": "MQL5_LIVE",
            "code_commit_sha": "e6ce816 (periodo del trace live citato nel dataset)",
            "build_id": "NOT_RECORDED - nessun RUNTIME_IDENTITY_MANIFEST_V1 emesso all'epoca",
            "runtime_fingerprint": "NOT_AVAILABLE - manifest non ancora implementato (vedi "
                                  "IMPLEMENTATION_ROADMAP_V1)",
            "dataset_version": "breakout_acc_intended_d1_v1_dataset.json (Phase 7.9H)",
            "tenant_id": "NOT_APPLICABLE - architettura mono-cliente in questa fase",
            "ea_instance_id": "NOT_APPLICABLE", "account_scope_id": "NOT_APPLICABLE",
        },
        "environment": {
            "symbol": "GOLD", "broker": "NOT_RECORDED nel dataset (noto storicamente: XM Global)",
            "server": "NOT_RECORDED", "account_mode": "UNKNOWN",
            "leverage": "NOT_RECORDED", "contract_specification": {"note": "NOT_RECORDED"},
            "minimum_lot": 0.01, "lot_step": "NOT_RECORDED",
            "terminal_build": "NOT_RECORDED",
            "ea_name": "NEXUS_EA_v2", "ea_version": "NOT_RECORDED",
            "chart_symbol": "GOLD", "chart_timeframe": ev["entry_tf"],
            "strategy_canonical_timeframe": ev["canonical_tf"],
            "timezone": "BROKER_SERVER_TZ (non ulteriormente specificato nel dataset)",
            "dst_convention": "UNKNOWN",
        },
        "timeline": {
            "event_detection_time": _ts(ev["d1_bar_date"], "MT5_BAR_CLOSE_D1", "BAR_CLOSE", "VERIFIED"),
            "signal_time": _ts(ev["entry_fill_time"], "NXS_LogTradeCSV_OPEN_row", "MINUTE", "VERIFIED",
                              timezone="BROKER_SERVER_TZ - identico a fill_time per costruzione M15 (Phase 7.9K)"),
            "decision_time": _ts(ev["entry_fill_time"], "NXS_LogTradeCSV_OPEN_row", "MINUTE", "VERIFIED"),
            "order_request_time": _ts(ev["entry_fill_time"], "inferito dal fill (signal_to_fill_slippage=0)", "MINUTE", "PROBABLE"),
            "broker_acceptance_time": _absent("NOT_RECORDED", "broker_accept_reject=ACCEPT ma senza timestamp dedicato nel dataset"),
            "broker_rejection_time": _absent("NOT_APPLICABLE", "evento accettato, non rifiutato"),
            "fill_time": _ts(ev["entry_fill_time"], "HistoryDealGetDouble(DEAL_TIME)", "SECOND", "VERIFIED"),
            "exit_time": _ts(ev["exit_fill_time"], "HistoryDealGetDouble(DEAL_TIME)", "SECOND", "VERIFIED"),
        },
        "prices": {
            "market_reference_price": _priced(ev["upstream_range_hi"], "D1_bar_high_of_range", "B"),
            "bid": _absent("NOT_RECORDED", "nessun tick BID isolato nel dataset D1"),
            "ask": _absent("NOT_RECORDED"),
            "last": _absent("NOT_APPLICABLE"),
            "signal_price": _priced(ev["signal_price"], ev["signal_price_source"], "A"),
            "requested_price": _priced(ev["signal_price"], "coincide col signal_price (slippage=0 dichiarato)", "A"),
            "actual_fill_price": _priced(ev["entry_fill_price"], ev["entry_fill_price_source"], "A", is_proxy=False),
            "exit_fill_price": _priced(ev["exit_fill_price"], "HistoryDealGetDouble(DEAL_PRICE)", "A", is_proxy=False),
            "spread": _absent("NOT_RECORDED"),
            "slippage": _priced(ev["signal_to_fill_slippage_price_units"], "differenza signal_price/fill_price", "A"),
        },
        "strategy_state": {
            "state_before": {
                "strategy_state_kind": "COOLDOWN_TIMER",
                "fields": {"accept_up": ev["upstream_accept_up"], "accept_dn": ev["upstream_accept_dn"],
                          "range_hi": ev["upstream_range_hi"], "range_lo": ev["upstream_range_lo"]},
                "capture_method": "RECONSTRUCTED_OFFLINE",
            },
            "state_after": {
                "strategy_state_kind": "COOLDOWN_TIMER",
                "fields": {"cooldown_started": True, "direction": ev["direction"]},
                "capture_method": "RECONSTRUCTED_OFFLINE",
            },
        },
        "decision_time_features": {
            "available_at_decision_time": [
                _feature("accept_up", ev["upstream_accept_up"], True, False, True, "shift1/shift2 su barra D1 chiusa (post-fix Phase 7.9F)", closed_only=True),
                _feature("range_hi_20d1", ev["upstream_range_hi"], True, False, True, "iHighest su 20 barre D1 chiuse", closed_only=True),
            ],
            "future_information_excluded": ["post_entry_path_anatomy.*", "realized_pnl", "exit_fill_price", "exit_fill_time", "exit_reason_comment"],
            "anti_leakage_check_passed": True,
            "anti_leakage_check_method": "Phase 7.9J/7.9K - causalita' EMA100/forward-path verificata e corretta",
        },
        "pre_entry_feature_snapshot": {
            "trend": _feature("htf_filter_stage", ev["htf_filter_stage"], True, False, False,
                             "discriminante empirico osservato, NON un gate causale verificato nel codice attuale (vedi upstream_context_provenance nel dataset)"),
            "volatility": None, "atr": None, "momentum": None,
            "htf_context": None, "market_structure": None, "level_distance": None,
            "breakout_magnitude": _feature("range_width", ev["upstream_range_hi"] - ev["upstream_range_lo"], True, False, True),
            "sweep_depth": None, "session": None, "spread_feature": None, "volume": None,
            "time_since_previous_event": None, "distance_from_previous_event": None,
            "current_exposure": None, "margin_state": None, "portfolio_overlap": None, "regime_descriptors": None,
        },
        "multi_timeframe_context": {
            "required_timeframes": ["D1"], "available_timeframes": ["D1"],
            "bars_by_timeframe": {"D1": {"current_bar": {
                "timeframe": "D1", "open_time": ev["d1_bar_date"], "close_time": None,
                "open": None, "high": ev["upstream_range_hi"], "low": ev["upstream_range_lo"], "close": None,
                "status": "CLOSED", "source": "nxs_breakoutacc_cadence_diag_prefix_isolated.csv"}}},
        },
        "outcome_path": {
            "signal_relative_path": {
                "mfe": _present(ev["post_entry_path_anatomy"]["mfe_price_units"]),
                "mae": _present(ev["post_entry_path_anatomy"]["mae_price_units"]),
                "time_to_mfe": _present(ev["post_entry_path_anatomy"]["bars_to_mfe_d1"]),
                "time_to_mae": _present(ev["post_entry_path_anatomy"]["bars_to_mae_d1"]),
                "fixed_horizon_returns": {f"{k}": _present(v) for k, v in ev["post_entry_path_anatomy"]["horizons"].items()},
                "censored": False,
            },
            "fill_relative_path": {"note": _absent("NOT_RECORDED", "il dataset Phase 7.9H fornisce solo il path signal-relative")},
            "pnl": _present(ev["realized_pnl"]),
            "final_classification": "FAILURE" if ev["realized_pnl"] < 0 else "CONTINUATION",
        },
        "edge_discovery_compatibility": {
            "eligible_as_feature": ["accept_up", "range_hi_20d1", "breakout_magnitude"],
            "excluded_for_leakage": ["post_entry_path_anatomy.*", "realized_pnl"],
            "dataset_split_tag": "UNASSIGNED", "experiment_provenance": "Phase 7.9H canonical dataset",
            "hypothesis_id": "NOT_APPLICABLE - nessuna discovery eseguita in questa fase",
        },
        "source_of_truth": {
            "execution_source": "MT5_RUNTIME_TRACE", "event_identity_source": "MT5_CANONICAL_IMPLEMENTATION",
            "statistical_analysis_source": "NOT_APPLICABLE", "visual_context_source": "NOT_AVAILABLE",
            "narrative_source": "NOT_APPLICABLE", "python_is_event_level_authoritative": False,
        },
        "fidelity": {
            "tier": "B",
            "criteria_met": ["real_fill (entry_fill_price non proxy)", "same_ohlc_feed"],
            "criteria_missing": ["tick_or_m1_available (solo D1)", "runtime_identity_verified (nessun manifest)"],
            "note": "Fill reale e path anatomy reali - manca solo il manifest di runtime "
                   "identity (non ancora implementato) per Fidelity A.",
        },
    }


# =====================================================================
# Packet 2 - ORDER_BLOCK (evento REALE post-fix, Phase 7.14, 2023.10.13 SELL)
# =====================================================================
def build_packet_order_block():
    import csv
    path = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_14",
                        "nxs_orderblock_realtrace_diag_postfix_curated.csv")
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    ev = next(r for r in rows if r["close_time_srv"] == "2023.10.13 00:00:00" and r["op"] == "RETEST_SIGNAL_FIRED")

    return {
        "schema_version": "EVENT_AUDIT_PACKET_V1",
        "identity": {
            "event_id": "ob_realtrace_postfix_20231013_sell",
            "strategy_id": "ORDER_BLOCK",
            "canonical_strategy_identity": "ORDER_BLOCK_IMPL_V2_TF_GUARDED",
            "strategy_version": "post-fix Phase 7.14 (commit 17da794)",
            "implementation_identity": "MQL5_LIVE",
            "code_commit_sha": "17da794",
            "build_id": "compile_final_clean.log (Phase 7.14) - timestamp incrociato col "
                       "binario deployato, non un vero build_id univoco",
            "runtime_fingerprint": "NOT_AVAILABLE - manifest non ancora implementato",
            "dataset_version": "nxs_orderblock_realtrace_diag_postfix_curated.csv (Phase 7.14)",
            "tenant_id": "NOT_APPLICABLE", "ea_instance_id": "NOT_APPLICABLE", "account_scope_id": "NOT_APPLICABLE",
        },
        "environment": {
            "symbol": "GOLD", "broker": "NOT_RECORDED nel CSV (run Tester, non un conto live)",
            "server": "NOT_RECORDED", "account_mode": "TESTER",
            "leverage": "500 (da nxs_orderblock_realtrace_postfix.ini)", "contract_specification": {"note": "NOT_RECORDED"},
            "minimum_lot": 0.01, "lot_step": "NOT_RECORDED", "terminal_build": "NOT_RECORDED",
            "ea_name": "NEXUS_EA_v2", "ea_version": "NOT_RECORDED",
            "chart_symbol": "GOLD", "chart_timeframe": "H4 (Period del Tester, non il TF di esecuzione strategia)",
            "strategy_canonical_timeframe": ev["canonical_tf"],
            "timezone": "BROKER_SERVER_TZ", "dst_convention": "UNKNOWN",
        },
        "timeline": {
            "event_detection_time": _ts(ev["close_time_srv"], "NXS_OB_DiagWrite (Phase 7.14)", "SECOND", "VERIFIED"),
            "signal_time": _ts(ev["close_time_srv"], "NXS_OB_DiagWrite", "SECOND", "VERIFIED"),
            "decision_time": _ts(ev["close_time_srv"], "NXS_OB_DiagWrite", "SECOND", "VERIFIED"),
            "order_request_time": _absent("NOT_RECORDED", "trace diagnostico cattura solo lo stato zona, non l'invio ordine (Research Mode)"),
            "broker_acceptance_time": _absent("NOT_APPLICABLE", "nessun ordine reale inviato in questo run diagnostico"),
            "broker_rejection_time": _absent("NOT_APPLICABLE"),
            "fill_time": _absent("NOT_RECORDED", "nessun fill tracciato dal trace diagnostico di stato"),
            "exit_time": _absent("NOT_RECORDED"),
        },
        "prices": {
            "market_reference_price": _absent("NOT_RECORDED", "il trace cattura obLo/obHi, non il prezzo di mercato al momento del retest"),
            "bid": _absent("NOT_RECORDED", "usato internamente da MT5 (SymbolInfoDouble) ma non loggato in questo trace"),
            "ask": _absent("NOT_RECORDED"), "last": _absent("NOT_APPLICABLE"),
            "signal_price": _priced((float(ev["pre_lo"]) + float(ev["pre_hi"])) / 2, "centro della zona OB al momento del retest (proxy)", "C", is_proxy=True, proxy_reason="il trace diagnostico non ha loggato il prezzo esatto di tocco/rigetto, solo i bound della zona"),
            "requested_price": _absent("NOT_APPLICABLE", "nessun ordine reale in questo run"),
            "actual_fill_price": _absent("NOT_RECORDED"), "exit_fill_price": _absent("NOT_RECORDED"),
            "spread": _absent("NOT_RECORDED"), "slippage": _absent("NOT_APPLICABLE"),
        },
        "strategy_state": {
            "state_before": {
                "strategy_state_kind": "DISCRETE_ZONE",
                "fields": {"active": bool(int(ev["pre_active"])), "obLo": float(ev["pre_lo"]), "obHi": float(ev["pre_hi"]), "barsWaited": int(ev["pre_bars_waited"])},
                "captured_at": _ts(ev["close_time_srv"], "NXS_OB_DiagWrite", "SECOND", "VERIFIED"),
                "capture_method": "LIVE_EA_INSTRUMENTATION",
            },
            "state_after": {
                "strategy_state_kind": "DISCRETE_ZONE",
                "fields": {"active": bool(int(ev["post_active"])), "obLo": float(ev["post_lo"]), "obHi": float(ev["post_hi"]), "barsWaited": int(ev["post_bars_waited"])},
                "captured_at": _ts(ev["close_time_srv"], "NXS_OB_DiagWrite", "SECOND", "VERIFIED"),
                "capture_method": "LIVE_EA_INSTRUMENTATION",
            },
        },
        "decision_time_features": {
            "available_at_decision_time": [
                _feature("zone_lo", float(ev["pre_lo"]), True, False, True, "stato zona catturato live dall'istrumentazione diagnostica"),
                _feature("zone_hi", float(ev["pre_hi"]), True, False, True, "idem"),
                _feature("bars_waited", int(ev["pre_bars_waited"]), True, False, True, "idem"),
            ],
            "future_information_excluded": ["outcome_path.*"],
            "anti_leakage_check_passed": True,
            "anti_leakage_check_method": "guardia TF-scoped verificata (Phase 7.14) - nessuna "
                                        "mutazione su passaggi non canonici post-fix",
        },
        "pre_entry_feature_snapshot": {
            "trend": None, "volatility": None,
            "atr": _feature("atr_at_zone_creation", None, True, False, False, "NOT_RECORDED nel trace di Phase 7.14 (solo lo stato zona, non g_atr)"),
            "momentum": None, "htf_context": None, "market_structure": None,
            "level_distance": _feature("zone_width", float(ev["pre_hi"]) - float(ev["pre_lo"]), True, False, True),
            "breakout_magnitude": None, "sweep_depth": None, "session": None, "spread_feature": None,
            "volume": None, "time_since_previous_event": None, "distance_from_previous_event": None,
            "current_exposure": None, "margin_state": None, "portfolio_overlap": None, "regime_descriptors": None,
        },
        "multi_timeframe_context": {
            "required_timeframes": ["D1"], "available_timeframes": ["D1"],
            "bars_by_timeframe": {"D1": {"current_bar": {
                "timeframe": "D1", "open_time": ev["close_time_srv"], "close_time": None,
                "open": None, "high": None, "low": None, "close": None,
                "status": "CLOSED", "source": "NOT_RECORDED - il trace non ha loggato OHLC grezzi (gap dichiarato in Phase 7.16)"}}},
        },
        "outcome_path": {
            "signal_relative_path": {"note": _absent("NOT_RECORDED", "questo run diagnostico non ha misurato MFE/MAE - scopo era solo validare la guardia TF")},
            "fill_relative_path": {"note": _absent("NOT_APPLICABLE", "nessun fill reale in questo run")},
            "pnl": _absent("NOT_APPLICABLE"),
            "final_classification": "NOT_YET_DETERMINED",
        },
        "edge_discovery_compatibility": {
            "eligible_as_feature": ["zone_lo", "zone_hi", "bars_waited", "zone_width"],
            "excluded_for_leakage": ["outcome_path.*"],
            "dataset_split_tag": "UNASSIGNED", "experiment_provenance": "Phase 7.14 parity validation",
            "hypothesis_id": "NOT_APPLICABLE",
        },
        "source_of_truth": {
            "execution_source": "MT5_RUNTIME_TRACE", "event_identity_source": "MT5_CANONICAL_IMPLEMENTATION",
            "statistical_analysis_source": "NOT_APPLICABLE", "visual_context_source": "NOT_AVAILABLE",
            "narrative_source": "NOT_APPLICABLE", "python_is_event_level_authoritative": False,
        },
        "fidelity": {
            "tier": "B",
            "criteria_met": ["same_ohlc_feed (tick reali MT5 Model=4)", "state_partially_reconstructed (live, ma non fill reale)"],
            "criteria_missing": ["real_fill (Research Mode, nessun fill reale)", "runtime_identity_verified"],
            "note": "Stato di zona catturato DAL VIVO nell'EA reale (non ricostruito offline) "
                   "ma senza fill/prezzo di mercato reale associato - questo gap e' "
                   "esattamente cio' che GAP_ANALYSIS_V1 raccomanda di colmare.",
        },
    }


# =====================================================================
# Packet 3 - SH_BMS_RTO (SOLO strutturale, Fidelity D - nessun trace reale)
# =====================================================================
def build_packet_sh_bms_rto():
    return {
        "schema_version": "EVENT_AUDIT_PACKET_V1",
        "identity": {
            "event_id": "sh_bms_rto_structural_illustrative_only",
            "strategy_id": "SH_BMS_RTO", "canonical_strategy_identity": "SH_BMS_RTO",
            "strategy_version": "current HEAD (nessun fix applicato, nessuna diagnosi dedicata svolta)",
            "implementation_identity": "MQL5_LIVE",
            "code_commit_sha": "NOT_APPLICABLE - nessun evento reale, solo identita' statica",
            "build_id": "NOT_APPLICABLE", "runtime_fingerprint": "NOT_APPLICABLE",
            "dataset_version": "NOT_APPLICABLE - nessun dataset di eventi per questa strategia in questo progetto",
            "tenant_id": "NOT_APPLICABLE", "ea_instance_id": "NOT_APPLICABLE", "account_scope_id": "NOT_APPLICABLE",
        },
        "environment": {
            "symbol": "GOLD", "broker": "NOT_APPLICABLE", "server": "NOT_APPLICABLE",
            "account_mode": "UNKNOWN", "leverage": "NOT_APPLICABLE", "contract_specification": {"note": "NOT_APPLICABLE"},
            "minimum_lot": "NOT_APPLICABLE", "lot_step": "NOT_APPLICABLE", "terminal_build": "NOT_APPLICABLE",
            "ea_name": "NEXUS_EA_v2", "ea_version": "NOT_APPLICABLE",
            "chart_symbol": "GOLD", "chart_timeframe": "PERIOD_D1 (dichiarato dal registro)",
            "strategy_canonical_timeframe": "PERIOD_D1 (NXS_Profile_TF, verificato nel codice sorgente)",
            "timezone": "NOT_APPLICABLE", "dst_convention": "NOT_APPLICABLE",
        },
        "timeline": {
            "event_detection_time": _absent("NOT_AVAILABLE", "nessun evento reale - packet puramente illustrativo"),
            "signal_time": _absent("NOT_AVAILABLE"), "decision_time": _absent("NOT_AVAILABLE"),
            "order_request_time": _absent("NOT_APPLICABLE"), "broker_acceptance_time": _absent("NOT_APPLICABLE"),
            "broker_rejection_time": _absent("NOT_APPLICABLE"), "fill_time": _absent("NOT_APPLICABLE"),
            "exit_time": _absent("NOT_APPLICABLE"),
        },
        "prices": {
            "signal_price": _absent("NOT_AVAILABLE", "nessun evento reale disponibile"),
            "market_reference_price": _absent("NOT_AVAILABLE"), "bid": _absent("NOT_AVAILABLE"),
            "ask": _absent("NOT_AVAILABLE"), "last": _absent("NOT_APPLICABLE"),
            "requested_price": _absent("NOT_APPLICABLE"), "actual_fill_price": _absent("NOT_APPLICABLE"),
            "exit_fill_price": _absent("NOT_APPLICABLE"), "spread": _absent("NOT_APPLICABLE"), "slippage": _absent("NOT_APPLICABLE"),
        },
        "strategy_state": {
            "state_before": {
                "strategy_state_kind": "STATE_MACHINE",
                "fields": {"note": "Struttura dello stato NON verificata riga-per-riga in questa fase "
                                  "(fuori scope - questa e' una fase di specifica, non un audit "
                                  "SH_BMS_RTO dedicato) - la strategia e' nota per meccanismo "
                                  "sweep+break-structure+return-to-origin dal nome e dalla coda "
                                  "priorita' Phase 7.12, dove e' stata posizionata insieme alla "
                                  "famiglia SMC"},
                "capture_method": "NOT_CAPTURED",
            },
            "state_after": {"strategy_state_kind": "STATE_MACHINE", "fields": {}, "capture_method": "NOT_CAPTURED"},
        },
        "decision_time_features": {"available_at_decision_time": [], "future_information_excluded": [],
                                   "anti_leakage_check_passed": None,
                                   "anti_leakage_check_method": "NOT_APPLICABLE - nessuna feature reale da verificare in questo packet illustrativo"},
        "pre_entry_feature_snapshot": {},
        "multi_timeframe_context": {"required_timeframes": ["D1"], "available_timeframes": []},
        "outcome_path": {"final_classification": "NOT_YET_DETERMINED"},
        "edge_discovery_compatibility": {"eligible_as_feature": [], "excluded_for_leakage": [],
                                         "dataset_split_tag": "UNASSIGNED",
                                         "experiment_provenance": "NOT_APPLICABLE", "hypothesis_id": "NOT_APPLICABLE"},
        "source_of_truth": {
            "execution_source": "NOT_AVAILABLE", "event_identity_source": "MT5_CANONICAL_IMPLEMENTATION",
            "statistical_analysis_source": "NOT_APPLICABLE", "visual_context_source": "NOT_AVAILABLE",
            "narrative_source": "NOT_APPLICABLE", "python_is_event_level_authoritative": False,
        },
        "fidelity": {
            "tier": "D",
            "criteria_met": ["structural_only_no_runtime_trace"],
            "criteria_missing": ["ANY runtime evidence"],
            "note": "Packet PURAMENTE ILLUSTRATIVO - dimostra solo che lo schema riesce a "
                   "rappresentare una terza famiglia strutturale (sweep+struttura) diversa da "
                   "BREAKOUT_ACC (soglia+cooldown) e ORDER_BLOCK (zona SMC) - NESSUNA "
                   "conclusione su SH_BMS_RTO puo' essere tratta da questo packet.",
        },
        "why_not_tsi": "TSI e' stato deliberatamente escluso da questi esempi: al momento della "
                       "stesura di questa fase (Phase 7.19), TSI ha un fix live in corso "
                       "(Phase 7.18, run diagnostico MT5 in background + istrumentazione "
                       "temporanea non ancora rimossa da MQL5/Include/NEXUS_v1/"
                       "NXS_Strategies.mqh) - usare TSI qui, anche in sola lettura di artifact "
                       "GIA' committati (Phase 7.17), avrebbe reso ambiguo se questa fase "
                       "specifica interferisse con quel lavoro. Scelta esplicita per SH_BMS_RTO "
                       "come terza strategia strutturalmente diversa e genuinamente STABILE "
                       "(nessun lavoro in corso su di essa).",
    }


def build():
    return {
        "packets": {
            "BREAKOUT_ACC": build_packet_breakout_acc(),
            "ORDER_BLOCK": build_packet_order_block(),
            "SH_BMS_RTO": build_packet_sh_bms_rto(),
        },
        "no_fabricated_data": True,
        "third_strategy_choice_documented": True,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE719_DIR, "example_packets_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    for k, v in payload["packets"].items():
        print(f"  {k}: fidelity {v['fidelity']['tier']}")


if __name__ == "__main__":
    main()
