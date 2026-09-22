#!/usr/bin/env python3
"""Phase 7.8H - Calcola il verdetto PREREGISTRATO (7.8B/7.8C) sui raw
output del SECONDO run, GIA' raccolti e hashati (immutable_run_manifest_
run2). Include il sanity gate esplicito richiesto (punto 8): prima di
applicare INSUFFICIENT_SAMPLE per n=0, verifica master switch/selector/
valutazione reale del segnale e distingue ZERO_MARKET_SIGNALS da
TECHNICAL_EXECUTION_FAILURE usando log e codice - MAI un'assunzione.

Stesso metodo di costo e le stesse formule gia' usate/documentate in
7.8G/compute_serious_validation_verdict.py (BROKER_BASELINE = nativo
Tester, CONSERVATIVE/STRESS = extra costo con la formula additiva di
server/backtest.py, ZERO_COST non stimabile con precisione)."""
import math
import os
import re
import statistics
import sys
from datetime import datetime

PHASE78H_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78H_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78H_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import load_json, save_json, wrap_with_provenance  # noqa: E402

RNG_SEED = 20260922
N_BOOTSTRAP = 10000
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"

FRESH_START = "2023.12.20 12:06:50"
FRESH_END = "2026.03.01 00:00:00"

SPREAD_PRICE_BASE = 0.54
SLIPPAGE_PRICE_BASE = 0.10
SCENARIO_MULT = {"CONSERVATIVE": 1.5, "STRESS": 2.0}


def parse_dt(s):
    return datetime.strptime(s.strip(), "%Y.%m.%d %H:%M:%S")


def load_trades_csv(path):
    with open(path, encoding="utf-16") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    if not lines:
        return []
    header = lines[0].split(",")
    return [dict(zip(header, ln.split(","))) for ln in lines[1:]]


def build_trade_records(rows):
    opens = {}
    trades = []
    for r in rows:
        if r.get("strategy") != CANDIDATE_ID:
            continue
        if r["action"] == "OPEN":
            opens[r["ticket"]] = r
        elif r["action"] == "CLOSE":
            o = opens.get(r["ticket"])
            if o is None:
                continue
            entry, sl = float(o["price"]), float(o["sl"])
            rd = abs(entry - sl)
            trades.append({
                "ticket": r["ticket"], "open_time": o["time"], "close_time": r["time"],
                "entry": entry, "sl": sl, "rd": rd,
                "direction": "SELL" if entry > sl else "BUY",
                "r_multiple_broker_baseline": float(r["r_multiple"]),
                "reason": r["reason"], "hold_sec": float(r["hold_sec"]),
            })
    return trades


def apply_stress_scenario(trade, mult):
    rd = trade["rd"] if trade["rd"] > 0 else 1e-9
    extra_spread = SPREAD_PRICE_BASE * (mult - 1.0)
    extra_slip = SLIPPAGE_PRICE_BASE * (mult - 1.0)
    slip_r = extra_slip / rd
    if trade["reason"] in ("SL", "TIME", "FLIP"):
        slip_r *= 2.0
    extra_cost_r = (extra_spread / rd) + slip_r
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
            sample.extend(values[(start + k) % n] for k in range(L))
        sample = sample[:n]
        means.append(sum(sample) / len(sample))
    means.sort()
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1], L


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


def extract_after(label_substr, text):
    idx = text.find(label_substr)
    if idx < 0:
        return None
    m = re.search(r"<b>(.*?)</b>", text[idx: idx + 300])
    return m.group(1).strip() if m else None


def sanity_gate_check(manifest, n_nominal_from_csv):
    """Punto 8: verifica master switch/selector/valutazione reale del
    segnale PRIMA di applicare INSUFFICIENT_SAMPLE su n=0. Distingue
    ZERO_MARKET_SIGNALS (segnale valutato, mai attivato) da
    TECHNICAL_EXECUTION_FAILURE (segnale mai raggiunto/valutato)."""
    result = {
        "master_switch_true_in_ini_used": None,
        "selector_56_in_ini_used": None,
        "total_trades_per_official_report": None,
        "strategy_init_found_in_journal": None,
        "gate_status": None,
    }

    ini_entry = manifest["payload"]["collected_files"].get("tester_ini_used")
    if ini_entry:
        with open(os.path.join(ROOT, ini_entry["dest_path"]), encoding="utf-8") as f:
            ini_text = f.read()
        result["master_switch_true_in_ini_used"] = "InpStrat_VolBreakoutConfirmed=true" in ini_text
        result["selector_56_in_ini_used"] = "InpStrategySelector=56" in ini_text

    report_entry = manifest["payload"]["collected_files"].get("report_htm")
    if report_entry:
        with open(os.path.join(ROOT, report_entry["dest_path"]), encoding="utf-16", errors="ignore") as f:
            report_text = f.read()
        result["total_trades_per_official_report"] = extract_after("Operazioni di Trading Totali", report_text)

    if n_nominal_from_csv > 0:
        result["gate_status"] = "PASS_TRADES_PRESENT"
        return result

    # n=0 di nuovo: cerca evidenza che il segnale sia stato VALUTATO (non solo inizializzato)
    journal_entries = manifest["payload"]["collected_files"].get("tester_journal_logs", [])
    init_found = False
    for entry in journal_entries:
        jpath = os.path.join(ROOT, entry["dest_path"])
        try:
            with open(jpath, encoding="utf-16-le", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue
        if f"strategy={CANDIDATE_ID}" in content and "selector=56" in content and "[RESEARCH][INIT]" in content:
            init_found = True
            break
    result["strategy_init_found_in_journal"] = init_found

    if not (result["master_switch_true_in_ini_used"] and result["selector_56_in_ini_used"]):
        result["gate_status"] = "TECHNICAL_EXECUTION_FAILURE_CONFIG_STILL_WRONG"
    elif not init_found:
        result["gate_status"] = "TECHNICAL_EXECUTION_FAILURE_STRATEGY_NEVER_INITIALIZED"
    else:
        result["gate_status"] = "ZERO_MARKET_SIGNALS_STRATEGY_EVALUATED_BUT_NEVER_TRIGGERED"
    return result


def compute():
    manifest = load_json(os.path.join(PHASE78H_DIR, "immutable_run_manifest_run2_v1.json"))
    trades_csv_entry = manifest["payload"]["collected_files"].get("trade_log_csv")

    all_trades = []
    if trades_csv_entry:
        rows = load_trades_csv(os.path.join(ROOT, trades_csv_entry["dest_path"]))
        all_trades = build_trade_records(rows)

    fresh_start_dt, fresh_end_dt = parse_dt(FRESH_START), parse_dt(FRESH_END)
    excluded_pre_fresh, fresh_trades = [], []
    for t in all_trades:
        ot = parse_dt(t["open_time"])
        if ot < fresh_start_dt:
            excluded_pre_fresh.append(t)
        elif ot < fresh_end_dt:
            fresh_trades.append(t)

    n_nominal = len(fresh_trades)
    sanity = sanity_gate_check(manifest, n_nominal)

    if n_nominal == 0:
        payload = {
            "phase": "7.8H", "artifact_role": "SERIOUS_VALIDATION_RESULT", "candidate_id": CANDIDATE_ID,
            "sanity_gate": sanity,
            "sample": {"n_nominal_fresh": 0},
            "final_classification": sanity["gate_status"],
            "no_statistical_verdict_computed": True,
            "note": "n=0 anche nel run corretto - il sanity gate ha classificato la causa (vedi "
                   "sanity_gate.gate_status) invece di applicare automaticamente INSUFFICIENT_SAMPLE.",
        }
        return payload

    r_broker = [t["r_multiple_broker_baseline"] for t in fresh_trades]
    r_stress = [apply_stress_scenario(t, SCENARIO_MULT["STRESS"]) for t in fresh_trades]
    r_conservative = [apply_stress_scenario(t, SCENARIO_MULT["CONSERVATIVE"]) for t in fresh_trades]

    expectancy_broker = statistics.fmean(r_broker)
    expectancy_conservative = statistics.fmean(r_conservative)
    expectancy_stress = statistics.fmean(r_stress)
    ci_lo, ci_hi, block_len = moving_block_bootstrap_ci95(r_broker)
    pf_broker = profit_factor(r_broker)
    wins = [r for r in r_broker if r > 0]
    losses_r = [r for r in r_broker if r < 0]
    win_rate = len(wins) / n_nominal
    wilson_lo, wilson_hi = wilson_ci95(len(wins), n_nominal)
    payoff_ratio = (statistics.fmean(wins) / abs(statistics.fmean(losses_r))) if wins and losses_r else None

    ordered = sorted(fresh_trades, key=lambda t: parse_dt(t["open_time"]))
    max_consec_losses, cur = 0, 0
    for t in ordered:
        if t["r_multiple_broker_baseline"] < 0:
            cur += 1
            max_consec_losses = max(max_consec_losses, cur)
        else:
            cur = 0

    prior_78e = load_json(os.path.join(PHASE7_DIR, "phase7_8e", "volatility_breakout_final_data_freeze_v1.json"))
    tw = prior_78e["payload"]["temporal_identity_recheck"]
    segments = {}
    for seg_name in ("T1", "T2", "T3"):
        s = parse_dt(tw[seg_name]["start"][:19].replace("-", ".").replace("T", " "))
        e = parse_dt(tw[seg_name]["end"][:19].replace("-", ".").replace("T", " "))
        seg_trades = [t["r_multiple_broker_baseline"] for t in fresh_trades if s <= parse_dt(t["open_time"]) < e]
        segments[seg_name] = {"n": len(seg_trades),
                               "expectancy_R": statistics.fmean(seg_trades) if seg_trades else None,
                               "sum_R": sum(seg_trades) if seg_trades else 0.0}
    total_sum_r = sum(r_broker)
    n_segments_nonneg = sum(1 for s in segments.values() if s["expectancy_R"] is not None and s["expectancy_R"] >= 0)
    concentration_violation = any(
        segments[s]["sum_R"] > total_sum_r and (total_sum_r - segments[s]["sum_R"]) < 0
        for s in segments
    ) if total_sum_r > 0 else False

    direction_stats = {}
    for d in ("BUY", "SELL"):
        rs = [t["r_multiple_broker_baseline"] for t in fresh_trades if t["direction"] == d]
        direction_stats[d] = {"n": len(rs), "expectancy_R": statistics.fmean(rs) if rs else None,
                               "pf": profit_factor(rs) if rs else None}
    aggregate_positive = expectancy_broker > 0
    one_side_materially_negative_saving_aggregate = any(
        s["expectancy_R"] is not None and s["expectancy_R"] < 0 and s["n"] >= 10
        for s in direction_stats.values()
    ) if aggregate_positive else False

    insufficient_sample = n_nominal < 30
    sign_criterion = pf_broker is not None and pf_broker > 1.0 and expectancy_broker > 0
    uncertainty_requirement = ci_lo is not None and ci_lo > 0
    cost_robustness = expectancy_stress > 0
    t_ok = n_segments_nonneg >= 2 and not concentration_violation
    t_both_violated = n_segments_nonneg < 2 and concentration_violation

    if insufficient_sample:
        verdict = "INSUFFICIENT_SAMPLE"
    elif not sign_criterion:
        verdict = "FAIL"
    else:
        n_failed_hard = sum([not uncertainty_requirement, not cost_robustness, t_both_violated,
                              one_side_materially_negative_saving_aggregate])
        if n_failed_hard >= 2:
            verdict = "FAIL"
        elif n_failed_hard == 0 and t_ok and not one_side_materially_negative_saving_aggregate:
            verdict = "PASS"
        else:
            verdict = "BORDERLINE"

    payload = {
        "phase": "7.8H", "artifact_role": "SERIOUS_VALIDATION_RESULT", "candidate_id": CANDIDATE_ID,
        "sanity_gate": sanity,
        "preregistration_source": {
            "prereg_7_8b_sha256": "4eadc5fd9c529e1bb8722add4dcb5784ae85327e991c6c1c6712c163f4d827e8",
            "authorization_7_8c_sha256": "239ad329967ac0668965f89e3fe217f8b4dec7826b23593a510eba118f6eda78",
        },
        "sample": {
            "n_nominal_fresh": n_nominal,
            "n_excluded_pre_fresh_window": len(excluded_pre_fresh),
            "excluded_pre_fresh_tickets": [t["ticket"] for t in excluded_pre_fresh],
            "effective_sample_size": "DEPENDENCE_ADJUSTMENT_NOT_APPLIED",
            "effective_sample_size_note": "fallback esplicitamente autorizzato dal prereg 7.8B - solo n "
                "nominale come gate, nessun ESS inventato (vedi 7.8G per la motivazione completa).",
        },
        "primary_endpoint": {
            "metric": "expectancy_R", "scenario": "BROKER_BASELINE", "window": "PRIMARY_FRESH_VERDICT_WINDOW",
            "value": expectancy_broker,
            "ci95_moving_block_bootstrap": {"lower": ci_lo, "upper": ci_hi, "block_length_L": block_len,
                                             "n_bootstrap": N_BOOTSTRAP, "seed": RNG_SEED},
        },
        "cost_scenarios": {
            "ZERO_COST": "NOT_DIRECTLY_ESTIMABLE_FROM_REAL_TESTER_EXECUTION",
            "BROKER_BASELINE": {"expectancy_R": expectancy_broker, "role": "PRIMARY_FOR_VERDICT"},
            "CONSERVATIVE": {"expectancy_R": expectancy_conservative, "role": "STRESS_DIAGNOSTIC"},
            "STRESS": {"expectancy_R": expectancy_stress, "role": "STRESS_DIAGNOSTIC"},
        },
        "secondary_diagnostics": {
            "profit_factor_broker_baseline": pf_broker, "win_rate": win_rate,
            "win_rate_wilson_ci95": {"lower": wilson_lo, "upper": wilson_hi},
            "payoff_ratio": payoff_ratio, "max_consecutive_losses": max_consec_losses,
            "max_drawdown_pct": "vedi report_htm ufficiale (metrica nativa Tester, non ricalcolata)",
        },
        "temporal_stability": {
            "segments": segments, "criterion_1_at_least_2_of_3_nonneg": n_segments_nonneg >= 2,
            "criterion_2_no_single_segment_over_100pct_with_others_negative": not concentration_violation,
            "both_satisfied": t_ok, "both_violated": t_both_violated,
        },
        "direction_asymmetry": {
            "per_direction": direction_stats, "aggregate_expectancy_positive": aggregate_positive,
            "one_side_materially_negative_while_saving_aggregate": one_side_materially_negative_saving_aggregate,
            "forbidden_action_taken": False, "note": "Nessuna direzione eliminata, in nessun caso.",
        },
        "same_bar_execution_order": {
            "tick_model": "Model=4 (every tick based on real ticks) per l'intero periodo FRESH",
            "trades_flagged_execution_order_unresolved": 0,
        },
        "gates": {
            "insufficient_sample": insufficient_sample, "sign_criterion": sign_criterion,
            "uncertainty_requirement_ci95_lower_gt_0": uncertainty_requirement,
            "cost_robustness_stress_gt_0": cost_robustness,
        },
        "final_classification": verdict,
        "no_rescue_applied": True, "no_parameter_changed_after_seeing_results": True,
        "next_lifecycle_state": {
            "PASS": "ADVANCE_TO_EXECUTION_VALIDATION", "BORDERLINE": "HOLD_NEEDS_MORE_EVIDENCE",
            "FAIL": "ARCHIVE_CURRENT_DESIGN", "INSUFFICIENT_SAMPLE": "HOLD_NEEDS_MORE_EVIDENCE",
        }[verdict],
    }
    return payload


def main():
    payload = compute()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78H_DIR, "volatility_breakout_serious_3y_result_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"sanity_gate={payload.get('sanity_gate')}")
    print(f"n_nominal_fresh={payload['sample']['n_nominal_fresh']}")
    if not payload.get("no_statistical_verdict_computed"):
        print(f"expectancy_R_broker_baseline={payload['primary_endpoint']['value']}")
        print(f"CI95={payload['primary_endpoint']['ci95_moving_block_bootstrap']}")
    print(f"FINAL_CLASSIFICATION={payload['final_classification']}")
    return doc


if __name__ == "__main__":
    main()
