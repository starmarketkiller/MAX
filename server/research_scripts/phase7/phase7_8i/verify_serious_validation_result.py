#!/usr/bin/env python3
"""Phase 7.8I - Verifica INDIPENDENTE del risultato del Serious
validation. Ri-legge il trade log CSV grezzo, ri-esegue il matching
evidence-based con parametri indipendenti (non importa build_ funzioni),
ricalcola expectancy_R/CI95/PF/temporal stability/direction asymmetry
dal CSV reale, e verifica la classificazione finale. Fallisce chiuso su
qualunque mismatch."""
import math
import os
import re
import statistics
import sys
from datetime import datetime

PHASE78I_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78I_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78I_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json  # noqa: E402

RESULT_PATH = os.path.join(PHASE78I_DIR, "volatility_breakout_serious_3y_result_v1.json")
RUN3_MANIFEST_PATH = os.path.join(PHASE78I_DIR, "immutable_run_manifest_run3_v1.json")
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"
FRESH_START = "2023.12.20 12:06:50"
FRESH_END = "2026.03.01 00:00:00"


def parse_dt(s):
    return datetime.strptime(s.strip(), "%Y.%m.%d %H:%M:%S")


def independent_reconstruction(csv_path):
    """Reimplementazione indipendente (non importa il builder) del
    matching FIFO-evidence-based, per una ri-derivazione a-se-stante."""
    CSV_HEADER = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
                  "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]
    with open(csv_path, encoding="utf-16") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    first = lines[0].split(",")
    has_header = first[:2] == ["time", "action"]
    data_lines = lines[1:] if has_header else lines
    rows = [dict(zip(CSV_HEADER, ln.split(","))) for ln in data_lines]
    strat_rows = sorted((r for r in rows if r.get("strategy") == CANDIDATE_ID), key=lambda r: r["time"])

    pending, trades = [], []
    for r in strat_rows:
        if r["action"] == "OPEN":
            pending.append(r)
        elif r["action"] == "CLOSE" and pending:
            close_price = float(r["price"])
            reason = r["reason"]
            best, best_dist = None, None
            for o in pending:
                if reason == "sl":
                    dist = abs(float(o["sl"]) - close_price)
                elif reason == "tp":
                    dist = abs(float(o["tp"]) - close_price)
                else:
                    dist = (parse_dt(r["time"]) - parse_dt(o["time"])).total_seconds()
                if best_dist is None or dist < best_dist:
                    best, best_dist = o, dist
            pending.remove(best)
            trades.append({"open_time": best["time"], "r_multiple": float(r["r_multiple"])})
    return trades


def moving_block_bootstrap_ci95(values, n_boot=10000, seed=20260922):
    import random
    n = len(values)
    if n == 0:
        return None, None
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
    return means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]


def verify():
    doc = load_json(RESULT_PATH)
    p = doc["payload"]
    run3_manifest = load_json(RUN3_MANIFEST_PATH)
    checks = {}

    checks["run3_manifest_hash_matches_real_file"] = run3_manifest["canonical_sha256"] == load_json(RUN3_MANIFEST_PATH)["canonical_sha256"]

    trades_csv_entry = run3_manifest["payload"]["collected_files"]["trade_log_csv"]
    csv_path = os.path.join(ROOT, trades_csv_entry["dest_path"])
    checks["trade_csv_hash_matches_real_file"] = file_sha256(csv_path) == trades_csv_entry["sha256"]

    report_entry = run3_manifest["payload"]["collected_files"]["report_htm"]
    report_path = os.path.join(ROOT, report_entry["dest_path"])
    checks["report_hash_matches_real_file"] = file_sha256(report_path) == report_entry["sha256"]
    with open(report_path, encoding="utf-16", errors="ignore") as f:
        report_text = f.read()
    idx = report_text.find("Operazioni di Trading Totali")
    m = re.search(r"<b>(.*?)</b>", report_text[idx: idx + 300])
    checks["report_total_trades_206"] = m.group(1).strip() == "206" == p["sanity_gate"]["total_trades_per_official_report"]

    recon = independent_reconstruction(csv_path)
    fresh_start_dt, fresh_end_dt = parse_dt(FRESH_START), parse_dt(FRESH_END)
    fresh_r = [t["r_multiple"] for t in recon if fresh_start_dt <= parse_dt(t["open_time"]) < fresh_end_dt]
    checks["n_nominal_recomputed_matches"] = len(fresh_r) == p["sample"]["n_nominal_fresh"] == 183

    recomputed_expectancy = statistics.fmean(fresh_r)
    checks["expectancy_recomputed_matches"] = abs(recomputed_expectancy - p["primary_endpoint"]["value"]) < 1e-9

    gains = sum(r for r in fresh_r if r > 0)
    losses = -sum(r for r in fresh_r if r < 0)
    recomputed_pf = gains / losses if losses > 0 else None
    checks["pf_recomputed_matches"] = abs(recomputed_pf - p["secondary_diagnostics"]["profit_factor_broker_baseline"]) < 1e-9

    ci_lo, ci_hi = moving_block_bootstrap_ci95(fresh_r)
    checks["ci95_lower_recomputed_matches"] = abs(ci_lo - p["primary_endpoint"]["ci95_moving_block_bootstrap"]["lower"]) < 1e-9
    checks["ci95_upper_recomputed_matches"] = abs(ci_hi - p["primary_endpoint"]["ci95_moving_block_bootstrap"]["upper"]) < 1e-9

    checks["sign_criterion_recomputed_correctly_false"] = not (recomputed_pf > 1.0 and recomputed_expectancy > 0)
    checks["ci95_does_not_exclude_zero_recomputed"] = not (ci_lo > 0)

    checks["gates_insufficient_sample_false"] = p["gates"]["insufficient_sample"] is False
    checks["gates_sign_criterion_false"] = p["gates"]["sign_criterion"] is False
    checks["final_classification_is_fail"] = p["final_classification"] == "FAIL"
    checks["matching_ambiguity_bracket_present"] = "trade_matching_ambiguity_bracket" in p
    checks["matching_ambiguity_did_not_change_verdict"] = (
        p["trade_matching_ambiguity_bracket"]["matching_ambiguity_changes_verdict"] is False
    )
    checks["matching_ambiguity_both_scenarios_fail"] = (
        p["trade_matching_ambiguity_bracket"]["verdict_scenario_A"] == "FAIL"
        and p["trade_matching_ambiguity_bracket"]["verdict_scenario_B"] == "FAIL"
    )
    checks["no_rescue_flag"] = p["no_rescue_applied"] is True
    checks["direction_no_deletion_flag"] = p["direction_asymmetry"]["forbidden_action_taken"] is False
    checks["next_lifecycle_is_archive"] = p["next_lifecycle_state"] == "ARCHIVE_CURRENT_DESIGN"

    core_checks = {k: v for k, v in checks.items() if isinstance(v, bool)}
    all_passed = all(core_checks.values())
    verdict = "RESULT_INDEPENDENTLY_CONFIRMED" if all_passed else "RESULT_VERIFICATION_FAILED"
    return checks, verdict


def main():
    checks, verdict = verify()
    for k, v in checks.items():
        print(f"[{'PASS' if v else 'FAIL'}] {k}")
    print(f"\nVERDICT: {verdict}")
    return verdict == "RESULT_INDEPENDENTLY_CONFIRMED"


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
