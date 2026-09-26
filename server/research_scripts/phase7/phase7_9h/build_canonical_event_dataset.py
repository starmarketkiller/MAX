#!/usr/bin/env python3
"""Phase 7.9H - BREAKOUT_ACC_INTENDED_D1_V1: dataset canonico event-level.

Popolazione = EVENTI (non solo trade aperti). Funnel intero preservato:
RAW_ACCEPTANCE_EVENT -> COOLDOWN -> HTF_FILTER -> GENERATED_SIGNAL ->
EXECUTION_GATES -> BROKER_ACCEPT/REJECT -> ORDER -> FILL -> POST_ENTRY_PATH.

Nessuna optimization, nessuna ricerca di edge. Nessun P&L usato per
decidere la metodologia. UNKNOWN/NA dove i dati non permettono la
ricostruzione - mai inventati.
"""
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta

PHASE79H_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79G_DIR = os.path.abspath(os.path.join(PHASE79H_DIR, "..", "phase7_9g"))
ROOT = os.path.abspath(os.path.join(PHASE79H_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "8fab0dd"  # HEAD dopo Phase 7.11
RUN_ID = "GOLD_2019.02.03 00:00:00_sel9_r003"
RAW_DIR = os.path.join(PHASE79H_DIR, "raw_data")

# I 8 eventi B-only, causalmente classificati (task dedicato, vedi
# build_b_only_residual_classification.py per il dettaglio completo).
B_ONLY_RESIDUAL_DATES = {
    "2019.02.21": 1, "2019.04.18": -1, "2019.05.15": 1, "2019.12.27": 1,
    "2021.09.07": 1, "2021.09.20": -1, "2022.01.21": 1, "2023.08.21": -1,
}

# Orizzonti PREREGISTRATI per il path anatomy (in barre D1) - definiti
# PRIMA di guardare qualunque P&L, non ottimizzati sui risultati.
PREREGISTERED_HORIZONS_D1 = [1, 3, 5, 10, 20, 40, 60]


def _read_csv(path, encoding="utf-8-sig"):
    with open(path, encoding=encoding) as f:
        return list(csv.DictReader(f))


def event_id(strategy, direction, date_str):
    """event_id causale e stabile: hash deterministico di
    (strategia, direzione, data D1 dell'evento) - non dipende da
    ticket/position_id (che possono cambiare fra run identici) ne'
    dall'ordine di inserimento nel dataset."""
    seed = f"{strategy}|{direction}|{date_str}"
    return "evt_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def load_generated_population():
    """Popolazione GENERATED_SIGNAL->EXECUTION_GATES->BROKER_ACCEPT/REJECT
    dal trace reale del run 7.9G/7.9H (67 eventi, funnel completo, nessun
    selection bias - blocked/broker_reject restano nel dataset)."""
    rows = _read_csv(os.path.join(PHASE79G_DIR, "raw_data", "postfix_live_ea_trace_events.csv"))
    out = []
    for r in rows:
        direction = 1 if "above_range" in r["generated_detail"] else -1
        date_str = r["timestamp"].split(" ")[0]
        out.append({
            "signal_id": r["signal_id"], "timestamp": r["timestamp"], "date": date_str,
            "direction": direction, "generated_detail": r["generated_detail"],
            "terminal_stage": r["terminal_stage"],
        })
    return out


def load_upstream_context():
    """Contesto RAW_ACCEPTANCE_EVENT->COOLDOWN->HTF_FILTER dalla
    ricostruzione D1-isolata (NXS_BreakoutAccCadenceDiagnostic.mq5).
    Fonte DIVERSA dal trace live - marcato esplicitamente come tale
    (provenance separata, non fondere le due fonti silenziosamente)."""
    rows = _read_csv(os.path.join(PHASE79G_DIR, "raw_data",
                                   "nxs_breakoutacc_cadence_diag_prefix_isolated.csv"))
    by_date = {r["d1_bar_time"]: r for r in rows}
    return by_date


def load_deals():
    """Deal reali (fill price verificato) dal run diagnostico Phase 7.9H."""
    rows = _read_csv(os.path.join(RAW_DIR, "nxs_diag_deals_export_r003.csv"))
    by_position = {}
    for r in rows:
        if r["symbol"] != "GOLD":
            continue  # riga 1 e' il DEAL_TYPE_BALANCE del deposito iniziale
        by_position.setdefault(r["position_id"], []).append(r)
    return by_position


def load_signal_reference_prices():
    """Prezzo di riferimento del segnale (refP, PRIMA dell'invio ordine) da
    NEXUS_trades.csv (Common\\Files, file condiviso fra run identici e
    deterministici - join per time+sl+tp, MAI per riga posizionale)."""
    path = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\Common\Files\NEXUS_trades.csv"
    with open(path, encoding="utf-16") as f:
        rows = list(csv.reader(f, delimiter=","))
    opens = [r for r in rows[1:] if len(r) > 3 and r[3] == "BREAKOUT_ACC" and r[1] == "OPEN"]
    by_key = {}
    for r in opens:
        key = (r[0], r[6], r[7])  # (time, sl, tp) - univoco per BREAKOUT_ACC single-selector run
        by_key[key] = {"signal_reference_price": float(r[4]), "score_at_signal": float(r[8]),
                       "reason": r[9]}
    return by_key


def load_d1_bars():
    rows = _read_csv(os.path.join(RAW_DIR, "nxs_d1_gold_phase79h.csv"))
    bars = []
    for r in rows:
        bars.append({
            "time": datetime.strptime(r["time"], "%Y.%m.%d %H:%M"),
            "open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"]),
        })
    bars.sort(key=lambda b: b["time"])
    return bars


def compute_path_anatomy(bars, entry_time, entry_price, direction):
    """MFE/MAE/tempo-a-MFE/tempo-a-MAE/forward returns a orizzonti
    PREREGISTRATI (barre D1), NON basati su TP/SL della strategia. Sola
    lettura di prezzo, nessuna assunzione su quando la posizione si
    sarebbe realmente chiusa (quello e' gia' coperto separatamente dal
    fill di uscita reale)."""
    idx = None
    for i, b in enumerate(bars):
        if b["time"] >= entry_time:
            idx = i
            break
    if idx is None:
        return {"status": "UNKNOWN_NO_BARS_AFTER_ENTRY"}

    result = {"status": "OK", "entry_bar_index": idx, "horizons": {}}
    max_h = max(PREREGISTERED_HORIZONS_D1)
    window = bars[idx:idx + max_h + 1]
    if len(window) < 2:
        return {"status": "UNKNOWN_INSUFFICIENT_FORWARD_BARS"}

    best_favorable = 0.0
    best_adverse = 0.0
    bars_to_mfe = None
    bars_to_mae = None
    for j, b in enumerate(window[1:], start=1):
        if direction == 1:
            fav = b["high"] - entry_price
            adv = entry_price - b["low"]
        else:
            fav = entry_price - b["low"]
            adv = b["high"] - entry_price
        if fav > best_favorable:
            best_favorable = fav
            bars_to_mfe = j
        if adv > best_adverse:
            best_adverse = adv
            bars_to_mae = j

    result["mfe_price_units"] = round(best_favorable, 5)
    result["mae_price_units"] = round(best_adverse, 5)
    result["bars_to_mfe_d1"] = bars_to_mfe
    result["bars_to_mae_d1"] = bars_to_mae

    for h in PREREGISTERED_HORIZONS_D1:
        if h >= len(window):
            result["horizons"][f"fwd_return_{h}d1_price_units"] = None
            continue
        px = window[h]["close"]
        ret = (px - entry_price) if direction == 1 else (entry_price - px)
        result["horizons"][f"fwd_return_{h}d1_price_units"] = round(ret, 5)
    return result


def build():
    generated = load_generated_population()
    upstream_by_date = load_upstream_context()
    deals_by_position = load_deals()
    signal_refs = load_signal_reference_prices()
    d1_bars = load_d1_bars()

    rows = []
    for ev in generated:
        d1_date_mql = ev["date"]  # gia' in formato YYYY.MM.DD
        upstream = upstream_by_date.get(d1_date_mql)

        row = {
            "event_id": event_id("BREAKOUT_ACC", ev["direction"], d1_date_mql),
            "population_source": "LIVE_TRACE_GENERATED",
            "canonical_strategy_id": "BREAKOUT_ACC",
            "canonical_tf": "PERIOD_D1",
            "entry_tf": "PERIOD_M15",
            "signal_id_live_trace": ev["signal_id"],
            "d1_bar_date": d1_date_mql,
            "direction": ev["direction"],
            "generated_detail": ev["generated_detail"],
            "funnel_terminal_stage": ev["terminal_stage"],
            "raw_acceptance_event": True,
            "cooldown_stage": "PASS" if (upstream and upstream["cooldown_ok"] == "1") else
                              ("UNKNOWN_NO_UPSTREAM_ROW" if upstream is None else "FAIL_INCONSISTENT_WITH_LIVE"),
            "htf_filter_stage": ("PASS" if upstream and upstream["htf_ok"] == "1" else
                                 ("UNKNOWN_NO_UPSTREAM_ROW" if upstream is None else "FAIL_INCONSISTENT_WITH_LIVE")),
            "upstream_context_provenance": ("nxs_breakoutacc_cadence_diag_prefix_isolated.csv "
                "(ricostruzione MQL5 D1-isolata, fonte DIVERSA dal trace live - vedi nota "
                "metodologica su htf_ok nel report: non corrisponde a un gate verificato nel "
                "codice attuale di NXS_Strat_BreakoutAcc(), trattato come discriminante "
                "empirico osservato, non come meccanismo causale accertato)"),
        }

        if upstream:
            row["upstream_accept_up"] = upstream["accept_up"]
            row["upstream_accept_dn"] = upstream["accept_dn"]
            row["upstream_range_hi"] = float(upstream["range_hi"])
            row["upstream_range_lo"] = float(upstream["range_lo"])
        else:
            row["upstream_accept_up"] = "UNKNOWN"
            row["upstream_accept_dn"] = "UNKNOWN"
            row["upstream_range_hi"] = "UNKNOWN"
            row["upstream_range_lo"] = "UNKNOWN"

        if ev["terminal_stage"] == "OPENED":
            row["execution_gates_stage"] = "PASS"
            row["broker_accept_reject"] = "ACCEPT"
            entry_deal = exit_deal = None
            best_match = None
            for pos_id, deals in deals_by_position.items():
                ins = [d for d in deals if d["entry"] == "DEAL_ENTRY_IN"]
                if not ins:
                    continue
                d_in = ins[0]
                if d_in["time"] == ev["timestamp"]:
                    best_match = pos_id
                    break
            if best_match:
                deals = deals_by_position[best_match]
                entry_deal = next((d for d in deals if d["entry"] == "DEAL_ENTRY_IN"), None)
                exit_deal = next((d for d in deals if d["entry"] == "DEAL_ENTRY_OUT"), None)
            if entry_deal is None:
                row["order_stage"] = "UNKNOWN_NO_DEAL_MATCH"
                row["fill_stage"] = "UNKNOWN_NO_DEAL_MATCH"
            else:
                row["order_stage"] = "SENT"
                row["fill_stage"] = "FILLED"
                row["entry_fill_price"] = float(entry_deal["price"])
                row["entry_fill_price_source"] = ("HistoryDealGetDouble(DEAL_PRICE) - deal "
                    "reale, run diagnostico Phase 7.9H (nxs_diag_deals_export_r003.csv)")
                row["entry_fill_time"] = entry_deal["time"]
                row["entry_volume"] = float(entry_deal["volume"])
                row["entry_sl"] = float(entry_deal["sl"])
                row["entry_tp"] = float(entry_deal["tp"])

                key = (ev["timestamp"], entry_deal["sl"], entry_deal["tp"])
                ref = signal_refs.get(key)
                if ref:
                    row["signal_price"] = ref["signal_reference_price"]
                    row["signal_price_source"] = ("NXS_LogTradeCSV OPEN row (refP, prezzo di "
                        "riferimento PRIMA dell'invio ordine) - NEXUS_trades.csv, join per "
                        "time+sl+tp")
                    row["signal_to_fill_slippage_price_units"] = round(
                        row["entry_fill_price"] - ref["signal_reference_price"], 5)
                else:
                    row["signal_price"] = "UNKNOWN_NO_MATCH_IN_NEXUS_TRADES_CSV"
                    row["signal_price_source"] = "UNKNOWN"
                    row["signal_to_fill_slippage_price_units"] = "UNKNOWN"

                if exit_deal is not None:
                    row["exit_fill_price"] = float(exit_deal["price"])
                    row["exit_fill_time"] = exit_deal["time"]
                    row["exit_reason_comment"] = exit_deal["comment"]
                    row["realized_pnl"] = float(exit_deal["profit"])
                    row["realized_swap"] = float(exit_deal["swap"])
                    row["realized_commission"] = float(exit_deal["commission"])
                else:
                    row["exit_fill_price"] = "UNKNOWN_POSITION_STILL_OPEN_AT_TEST_END"
                    row["exit_fill_time"] = "UNKNOWN"
                    row["exit_reason_comment"] = "UNKNOWN"

                entry_dt = datetime.strptime(entry_deal["time"], "%Y.%m.%d %H:%M:%S")
                path = compute_path_anatomy(d1_bars, entry_dt, row["entry_fill_price"],
                                             ev["direction"])
                row["post_entry_path_anatomy"] = path
        elif ev["terminal_stage"] == "BLOCKED":
            row["execution_gates_stage"] = "BLOCKED"
            row["broker_accept_reject"] = "NOT_APPLICABLE_BLOCKED_BEFORE_ORDER"
            row["order_stage"] = "NOT_SENT"
            row["fill_stage"] = "NOT_APPLICABLE"
        elif ev["terminal_stage"] == "BROKER_REJECT":
            row["execution_gates_stage"] = "PASS"
            row["broker_accept_reject"] = "REJECT"
            row["order_stage"] = "SENT_REJECTED"
            row["fill_stage"] = "NOT_APPLICABLE"
        else:
            row["execution_gates_stage"] = "UNKNOWN_MISSING_TERMINAL_STAGE"
            row["broker_accept_reject"] = "UNKNOWN"
            row["order_stage"] = "UNKNOWN"
            row["fill_stage"] = "UNKNOWN"

        rows.append(row)

    # --- gli 8 eventi B-only (mai visti nel trace live) - RITENUTI, non eliminati. ---
    b_only_classification = load_json(os.path.join(
        PHASE79H_DIR, "b_only_residual_classification_v1.json"))["payload"]["events"]
    b_only_by_date = {e["d1_bar_date"]: e for e in b_only_classification}

    for date_str, direction in B_ONLY_RESIDUAL_DATES.items():
        upstream = upstream_by_date.get(date_str)
        cls = b_only_by_date.get(date_str, {})
        row = {
            "event_id": event_id("BREAKOUT_ACC", direction, date_str),
            "population_source": "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY",
            "canonical_strategy_id": "BREAKOUT_ACC",
            "canonical_tf": "PERIOD_D1",
            "entry_tf": "PERIOD_M15",
            "signal_id_live_trace": None,
            "d1_bar_date": date_str,
            "direction": direction,
            "generated_detail": "Acceptance_above_range" if direction == 1 else "Acceptance_below_range",
            "funnel_terminal_stage": "NEVER_OBSERVED_IN_LIVE_TRACE",
            "raw_acceptance_event": True,
            "cooldown_stage": "PASS" if upstream and upstream["cooldown_ok"] == "1" else "UNKNOWN",
            "htf_filter_stage": "PASS" if upstream and upstream["htf_ok"] == "1" else "UNKNOWN",
            "upstream_context_provenance": ("nxs_breakoutacc_cadence_diag_prefix_isolated.csv "
                "(unica fonte disponibile per questi eventi - MAI osservati nel trace live "
                "reale)"),
            "upstream_accept_up": upstream["accept_up"] if upstream else "UNKNOWN",
            "upstream_accept_dn": upstream["accept_dn"] if upstream else "UNKNOWN",
            "upstream_range_hi": float(upstream["range_hi"]) if upstream else "UNKNOWN",
            "upstream_range_lo": float(upstream["range_lo"]) if upstream else "UNKNOWN",
            "execution_gates_stage": "NOT_APPLICABLE_NEVER_GENERATED",
            "broker_accept_reject": "NOT_APPLICABLE_NEVER_GENERATED",
            "order_stage": "NOT_APPLICABLE_NEVER_GENERATED",
            "fill_stage": "NOT_APPLICABLE_NEVER_GENERATED",
            "causal_classification": cls.get("causal_status", "NOT_CLASSIFIED"),
            "causal_ruled_out": cls.get("ruled_out", []),
            "causal_candidate_mechanisms": cls.get("candidate_mechanisms", []),
            "causal_notes": cls.get("notes", ""),
        }
        rows.append(row)

    return {
        "phase": "7.9H", "dataset_name": "BREAKOUT_ACC_INTENDED_D1_V1",
        "baseline_commit": BASELINE_COMMIT, "run_id": RUN_ID,
        "no_optimization_no_edge_search": True,
        "population_definition": ("Tutti gli eventi (non solo i trade aperti): 67 dal trace "
            "live reale (47 OPENED, 11 BLOCKED, 9 BROKER_REJECT) + 8 dalla ricostruzione "
            "offline isolata mai osservati nel trace live (ritenuti, non eliminati, con "
            "classificazione causale dedicata)."),
        "total_events": len(rows),
        "counts_by_population_source": {
            "LIVE_TRACE_GENERATED": sum(1 for r in rows if r["population_source"] == "LIVE_TRACE_GENERATED"),
            "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY": sum(
                1 for r in rows if r["population_source"] == "OFFLINE_ISOLATED_RECONSTRUCTION_ONLY"),
        },
        "counts_by_terminal_stage": {
            "OPENED": sum(1 for r in rows if r["funnel_terminal_stage"] == "OPENED"),
            "BLOCKED": sum(1 for r in rows if r["funnel_terminal_stage"] == "BLOCKED"),
            "BROKER_REJECT": sum(1 for r in rows if r["funnel_terminal_stage"] == "BROKER_REJECT"),
            "NEVER_OBSERVED_IN_LIVE_TRACE": sum(
                1 for r in rows if r["funnel_terminal_stage"] == "NEVER_OBSERVED_IN_LIVE_TRACE"),
        },
        "preregistered_horizons_d1_bars": PREREGISTERED_HORIZONS_D1,
        "events": rows,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE79H_DIR, "breakout_acc_intended_d1_v1_dataset.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"total_events={payload['total_events']}")
    print(payload["counts_by_population_source"])
    print(payload["counts_by_terminal_stage"])
    return doc


if __name__ == "__main__":
    main()
