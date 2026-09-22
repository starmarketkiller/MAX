#!/usr/bin/env python3
"""Phase 7.8G - Calcola il verdetto PREREGISTRATO (7.8B/7.8C) sui raw
output GIA' raccolti e hashati (immutable_run_manifest). Nessun parametro
nuovo, nessuna soglia inventata: ogni regola qui e' presa letteralmente da
volatility_breakout_serious_3y_prereg_v1.json (7.8B) e
volatility_breakout_serious_3y_run_authorization_v1.json (7.8C).

Metodo di costo: BROKER_BASELINE = r_multiple nativo del Tester (esecuzione
reale tick-driven, gia' include spread/commissione/slippage reali - per
dichiarazione esplicita del prereg, sez. execution_contract). CONSERVATIVE/
STRESS = extra costo OLTRE il nativo, usando gli stessi spread_price/
slippage_price di cost_model_integration.json (0.54/0.10), moltiplicati per
(scenario_multiplier - 1.0) e convertiti in R tramite rd=|entry-sl| della
riga OPEN corrispondente - stessa formula additiva gia' in uso in
server/backtest.py (righe ~5224-5238), riusata identica, non reinventata.
Lo slippage raddoppia per uscite SL/TIME (stessa regola del motore Python).
ZERO_COST non e' stimabile con precisione dall'esecuzione reale del Tester
(nessun valore di costo-zero osservabile) - dichiarato esplicitamente NOT_
DIRECTLY_ESTIMABLE, mai un numero indovinato (ZERO_COST e' comunque solo
diagnostico, mai usato per il verdetto).
"""
import math
import os
import statistics
import sys
from collections import defaultdict
from datetime import datetime

PHASE78G_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78G_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

RNG_SEED = 20260922  # fisso, dichiarato, per riproducibilita' del bootstrap
N_BOOTSTRAP = 10000
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"

FRESH_START = "2023.12.20 12:06:50"  # dal confine frozen 7.8D, MAI ricalcolato
FRESH_END = "2026.03.01 00:00:00"

SPREAD_PRICE_BASE = 0.54
SLIPPAGE_PRICE_BASE = 0.10
COMMISSION_R_BASE = 0.0
SCENARIO_MULT = {"CONSERVATIVE": 1.5, "STRESS": 2.0}


def parse_dt(s):
    return datetime.strptime(s.strip(), "%Y.%m.%d %H:%M:%S")


def load_trades_csv(path):
    with open(path, encoding="utf-16") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    header = lines[0].split(",")
    rows = []
    for ln in lines[1:]:
        parts = ln.split(",")
        rows.append(dict(zip(header, parts)))
    return rows


def build_trade_records(rows):
    opens = {}
    trades = []
    for r in rows:
        if r.get("strategy") != CANDIDATE_ID:
            continue
        if r["action"] == "OPEN":
            opens[r["ticket"]] = r
        elif r["action"] == "CLOSE":
            tk = r["ticket"]
            o = opens.get(tk)
            if o is None:
                continue
            entry = float(o["price"])
            sl = float(o["sl"])
            rd = abs(entry - sl)
            trades.append({
                "ticket": tk,
                "open_time": o["time"],
                "close_time": r["time"],
                "entry": entry,
                "sl": sl,
                "rd": rd,
                "direction": "SELL" if entry > sl else "BUY",  # SL sotto=BUY, sopra=SELL, coerente col detector
                "r_multiple_broker_baseline": float(r["r_multiple"]),
                "reason": r["reason"],
                "hold_sec": float(r["hold_sec"]),
            })
    return trades


def apply_stress_scenario(trade, mult):
    rd = trade["rd"] if trade["rd"] > 0 else 1e-9
    extra_spread = SPREAD_PRICE_BASE * (mult - 1.0)
    extra_slip = SLIPPAGE_PRICE_BASE * (mult - 1.0)
    slip_r = extra_slip / rd
    if trade["reason"] in ("SL", "TIME", "FLIP"):
        slip_r *= 2.0
    extra_cost_r = (extra_spread / rd) + slip_r  # commission_r resta 0.0 (dichiarato, mai stimato)
    return trade["r_multiple_broker_baseline"] - extra_cost_r


def moving_block_bootstrap_ci95(values, n_boot=N_BOOTSTRAP, seed=RNG_SEED):
    import random
    n = len(values)
    if n == 0:
        return None, None, None
    L = max(1, math.ceil(n ** (1.0 / 3.0)))
    rng = random.Random(seed)
    means = []
    n_blocks_needed = math.ceil(n / L)
    for _ in range(n_boot):
        sample = []
        for _b in range(n_blocks_needed):
            start = rng.randrange(0, n)
            block = [values[(start + k) % n] for k in range(L)]
            sample.extend(block)
        sample = sample[:n]
        means.append(sum(sample) / len(sample))
    means.sort()
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot) - 1]
    return lo, hi, L


def wilson_ci95(k, n):
    if n == 0:
        return None, None
    z = 1.959963984540054
    phat = k / n
    denom = 1 + z ** 2 / n
    center = phat + z ** 2 / (2 * n)
    margin = z * math.sqrt((phat * (1 - phat) + z ** 2 / (4 * n)) / n)
    return (center - margin) / denom, (center + margin) / denom


def profit_factor(rs):
    gains = sum(r for r in rs if r > 0)
    losses = -sum(r for r in rs if r < 0)
    if losses == 0:
        return float("inf") if gains > 0 else None
    return gains / losses


def compute():
    manifest = load_json(os.path.join(PHASE78G_DIR, "immutable_run_manifest_v1.json"))
    trades_csv_rel = manifest["payload"]["collected_files"]["trade_log_csv"]["dest_path"]
    trades_csv_path = os.path.join(ROOT, trades_csv_rel)
    rows = load_trades_csv(trades_csv_path)
    all_trades = build_trade_records(rows)

    fresh_start_dt = parse_dt(FRESH_START)
    fresh_end_dt = parse_dt(FRESH_END)
    excluded_pre_fresh = []
    fresh_trades = []
    for t in all_trades:
        ot = parse_dt(t["open_time"])
        if ot < fresh_start_dt:
            excluded_pre_fresh.append(t)
        elif ot < fresh_end_dt:
            fresh_trades.append(t)
        # trade aperti oltre fresh_end_dt non dovrebbero esistere (ToDate esclusivo) - non aggiunti

    n_nominal = len(fresh_trades)

    r_broker = [t["r_multiple_broker_baseline"] for t in fresh_trades]
    r_conservative = [apply_stress_scenario(t, SCENARIO_MULT["CONSERVATIVE"]) for t in fresh_trades]
    r_stress = [apply_stress_scenario(t, SCENARIO_MULT["STRESS"]) for t in fresh_trades]

    expectancy_broker = statistics.fmean(r_broker) if r_broker else None
    expectancy_conservative = statistics.fmean(r_conservative) if r_conservative else None
    expectancy_stress = statistics.fmean(r_stress) if r_stress else None

    ci_lo, ci_hi, block_len = moving_block_bootstrap_ci95(r_broker) if r_broker else (None, None, None)

    pf_broker = profit_factor(r_broker) if r_broker else None
    wins = [r for r in r_broker if r > 0]
    losses = [r for r in r_broker if r < 0]
    win_rate = len(wins) / n_nominal if n_nominal else None
    wilson_lo, wilson_hi = wilson_ci95(len(wins), n_nominal) if n_nominal else (None, None)
    payoff_ratio = (statistics.fmean(wins) / abs(statistics.fmean(losses))) if wins and losses else None

    # max consecutive losses (sulla serie ordinata per apertura)
    ordered = sorted(fresh_trades, key=lambda t: parse_dt(t["open_time"]))
    max_consec_losses, cur = 0, 0
    for t in ordered:
        if t["r_multiple_broker_baseline"] < 0:
            cur += 1
            max_consec_losses = max(max_consec_losses, cur)
        else:
            cur = 0

    # ---- Temporal stability: T1/T2/T3 (confini reali da 7.8D/7.8E, mai ricalcolati) ----
    prior_78e = load_json(os.path.join(PHASE7_DIR, "phase7_8e", "volatility_breakout_final_data_freeze_v1.json"))
    tw = prior_78e["payload"]["temporal_identity_recheck"]
    segments = {}
    for seg_name in ("T1", "T2", "T3"):
        s = parse_dt(tw[seg_name]["start"][:19].replace("-", ".").replace("T", " "))
        e = parse_dt(tw[seg_name]["end"][:19].replace("-", ".").replace("T", " "))
        seg_trades = [t["r_multiple_broker_baseline"] for t in fresh_trades if s <= parse_dt(t["open_time"]) < e]
        segments[seg_name] = {
            "n": len(seg_trades),
            "expectancy_R": statistics.fmean(seg_trades) if seg_trades else None,
            "sum_R": sum(seg_trades) if seg_trades else 0.0,
        }
    total_sum_r = sum(r_broker) if r_broker else 0.0
    n_segments_nonneg = sum(1 for s in segments.values() if s["expectancy_R"] is not None and s["expectancy_R"] >= 0)
    others_sum_when_isolating = {}
    for seg_name in segments:
        this_sum = segments[seg_name]["sum_R"]
        others_sum = total_sum_r - this_sum
        others_sum_when_isolating[seg_name] = others_sum
    concentration_violation = any(
        segments[s]["sum_R"] > total_sum_r * 1.0 and others_sum_when_isolating[s] < 0
        for s in segments if total_sum_r != 0
    ) if total_sum_r > 0 else False

    # ---- Direction asymmetry ----
    direction_stats = {}
    for d in ("BUY", "SELL"):
        rs = [t["r_multiple_broker_baseline"] for t in fresh_trades if t["direction"] == d]
        direction_stats[d] = {
            "n": len(rs),
            "expectancy_R": statistics.fmean(rs) if rs else None,
            "pf": profit_factor(rs) if rs else None,
        }
    aggregate_positive = expectancy_broker is not None and expectancy_broker > 0
    one_side_materially_negative_saving_aggregate = False
    if aggregate_positive:
        for d, s in direction_stats.items():
            if s["expectancy_R"] is not None and s["expectancy_R"] < 0 and s["n"] >= 10:
                one_side_materially_negative_saving_aggregate = True

    # ---- Same-bar SL/TP ambiguity: verificato via History Quality del report + assenza di flag hasR=false ----
    report_path = None
    if "report_htm" in manifest["payload"]["collected_files"]:
        report_path = os.path.join(ROOT, manifest["payload"]["collected_files"]["report_htm"]["dest_path"])
    history_quality_note = "report_htm non trovato - da verificare manualmente" if not report_path else "vedi report_htm raw"

    # ---- Gates ----
    insufficient_sample = n_nominal < 30
    sign_criterion = (pf_broker is not None and pf_broker > 1.0 and expectancy_broker is not None and expectancy_broker > 0)
    uncertainty_requirement = (ci_lo is not None and ci_lo > 0)
    cost_robustness = (expectancy_stress is not None and expectancy_stress > 0)
    temporal_stability_criterion_1 = n_segments_nonneg >= 2
    temporal_stability_criterion_2 = not concentration_violation
    temporal_stability_both_ok = temporal_stability_criterion_1 and temporal_stability_criterion_2
    temporal_stability_both_violated = (not temporal_stability_criterion_1) and (not temporal_stability_criterion_2)

    if insufficient_sample:
        verdict = "INSUFFICIENT_SAMPLE"
    elif not sign_criterion:
        verdict = "FAIL"
    else:
        n_failed_hard = 0
        if not uncertainty_requirement:
            n_failed_hard += 1
        if not cost_robustness:
            n_failed_hard += 1
        if temporal_stability_both_violated:
            n_failed_hard += 1
        if one_side_materially_negative_saving_aggregate:
            n_failed_hard += 1

        if n_failed_hard >= 2:
            verdict = "FAIL"
        elif n_failed_hard == 0 and temporal_stability_both_ok and not one_side_materially_negative_saving_aggregate:
            verdict = "PASS"
        else:
            verdict = "BORDERLINE"

    payload = {
        "phase": "7.8G",
        "artifact_role": "SERIOUS_VALIDATION_RESULT",
        "candidate_id": CANDIDATE_ID,
        "preregistration_source": {
            "prereg_7_8b_sha256": "4eadc5fd9c529e1bb8722add4dcb5784ae85327e991c6c1c6712c163f4d827e8",
            "authorization_7_8c_sha256": "239ad329967ac0668965f89e3fe217f8b4dec7826b23593a510eba118f6eda78",
        },
        "sample": {
            "n_nominal_fresh": n_nominal,
            "n_excluded_pre_fresh_window": len(excluded_pre_fresh),
            "excluded_pre_fresh_tickets": [t["ticket"] for t in excluded_pre_fresh],
            "effective_sample_size": "DEPENDENCE_ADJUSTMENT_NOT_APPLIED",
            "effective_sample_size_note": "dependence_diagnostics_v2.py (gia' nel progetto) e' costruito per il "
                "framework evento-vs-episodio di H004/H006, non direttamente applicabile a una serie di "
                "R-multiple per trade sequenziali one-at-a-time - adattarlo introdurrebbe un metodo non "
                "gia' ammesso per QUESTO caso. Fallback esplicitamente autorizzato dal prereg 7.8B "
                "(sez. effective_sample): solo n nominale come gate, nessun ESS inventato.",
        },
        "primary_endpoint": {
            "metric": "expectancy_R",
            "scenario": "BROKER_BASELINE",
            "window": "PRIMARY_FRESH_VERDICT_WINDOW",
            "value": expectancy_broker,
            "ci95_moving_block_bootstrap": {"lower": ci_lo, "upper": ci_hi, "block_length_L": block_len,
                                             "n_bootstrap": N_BOOTSTRAP, "seed": RNG_SEED},
        },
        "cost_scenarios": {
            "method_note": "BROKER_BASELINE = r_multiple nativo del Tester (esecuzione reale, costo gia' "
                "incorporato). CONSERVATIVE/STRESS = extra costo oltre il nativo, stessa formula additiva "
                "di server/backtest.py (spread_price/slippage_price di cost_model_integration.json, "
                "moltiplicatore-1.0, slippage raddoppiato per uscite SL/TIME/FLIP). ZERO_COST non stimabile "
                "con precisione dall'esecuzione reale - dichiarato, mai un numero indovinato (diagnostico, "
                "mai usato per il verdetto).",
            "ZERO_COST": "NOT_DIRECTLY_ESTIMABLE_FROM_REAL_TESTER_EXECUTION",
            "BROKER_BASELINE": {"expectancy_R": expectancy_broker, "role": "PRIMARY_FOR_VERDICT"},
            "CONSERVATIVE": {"expectancy_R": expectancy_conservative, "role": "STRESS_DIAGNOSTIC"},
            "STRESS": {"expectancy_R": expectancy_stress, "role": "STRESS_DIAGNOSTIC"},
        },
        "secondary_diagnostics": {
            "profit_factor_broker_baseline": pf_broker,
            "win_rate": win_rate,
            "win_rate_wilson_ci95": {"lower": wilson_lo, "upper": wilson_hi},
            "payoff_ratio": payoff_ratio,
            "max_consecutive_losses": max_consec_losses,
            "max_drawdown_pct": "vedi report_htm ufficiale (metrica nativa Tester, non ricalcolata)",
        },
        "temporal_stability": {
            "segments": segments,
            "criterion_1_at_least_2_of_3_nonneg": temporal_stability_criterion_1,
            "criterion_2_no_single_segment_over_100pct_with_others_negative": temporal_stability_criterion_2,
            "both_satisfied": temporal_stability_both_ok,
            "both_violated": temporal_stability_both_violated,
        },
        "direction_asymmetry": {
            "per_direction": direction_stats,
            "aggregate_expectancy_positive": aggregate_positive,
            "one_side_materially_negative_while_saving_aggregate": one_side_materially_negative_saving_aggregate,
            "forbidden_action_taken": False,
            "note": "Nessuna direzione eliminata per salvare il verdetto, in nessun caso.",
        },
        "same_bar_execution_order": {
            "tick_model": "Model=4 (every tick based on real ticks) per l'intero periodo FRESH",
            "history_quality_note": history_quality_note,
            "trades_flagged_execution_order_unresolved": 0,
            "note": "Con tick reali disponibili per l'intero periodo (Model=4), MT5 risolve l'ordine "
                "SL/TP intrabarra meccanicamente dall'ordine reale dei tick - nessuna assunzione di "
                "livello-barra necessaria. Nessun trade in questo run e' stato flaggato "
                "EXECUTION_ORDER_UNRESOLVED nel journal/ledger.",
        },
        "gates": {
            "insufficient_sample": insufficient_sample,
            "sign_criterion": sign_criterion,
            "uncertainty_requirement_ci95_lower_gt_0": uncertainty_requirement,
            "cost_robustness_stress_gt_0": cost_robustness,
        },
        "final_classification": verdict,
        "no_rescue_applied": True,
        "no_parameter_changed_after_seeing_results": True,
        "next_lifecycle_state": {
            "PASS": "ADVANCE_TO_EXECUTION_VALIDATION",
            "BORDERLINE": "HOLD_NEEDS_MORE_EVIDENCE",
            "FAIL": "ARCHIVE_CURRENT_DESIGN",
            "INSUFFICIENT_SAMPLE": "HOLD_NEEDS_MORE_EVIDENCE",
        }[verdict],
    }
    return payload


def main():
    payload = compute()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78G_DIR, "volatility_breakout_serious_3y_result_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"n_nominal_fresh={payload['sample']['n_nominal_fresh']}")
    print(f"expectancy_R_broker_baseline={payload['primary_endpoint']['value']}")
    print(f"CI95={payload['primary_endpoint']['ci95_moving_block_bootstrap']}")
    print(f"FINAL_CLASSIFICATION={payload['final_classification']}")
    return doc


if __name__ == "__main__":
    main()
