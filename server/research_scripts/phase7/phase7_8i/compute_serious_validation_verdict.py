#!/usr/bin/env python3
"""Phase 7.8I - Calcola il verdetto PREREGISTRATO (7.8B/7.8C) sui raw
output del TERZO run. Sanity gate (punto 5, corretto rispetto a 7.8H):
NON richiede la stringa testuale 'strategy=VOLATILITY_BREAKOUT_CONFIRMED'
nel journal (NXS_ResearchSelectorName non mappa ancora il case 56, quindi
stamperebbe 'selector_56' anche a router raggiunto correttamente) - il
gate verifica invece, indipendentemente dal nome: InpResearchMode=true,
selector=56, InpStrat_VolBreakoutConfirmed=true nell'ini usato, l'assenza
di [RESEARCH][FATAL] nel journal, e se il router/funzione strategia sia
stato realmente raggiunto (trade con strategy=VOLATILITY_BREAKOUT_
CONFIRMED nel CSV - quel nome e' impostato DIRETTAMENTE nella funzione
segnale, non tramite la lookup - oppure, se n=0, la presenza della riga
[RESEARCH][INIT] con selector=56 senza errori fatali).

Stesso metodo di costo/formule gia' documentato in 7.8G/7.8H."""
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


# Header autorevole da NXS_Logging.mqh:45 (NXS_LogTradeCSV) - riusato
# identico, non riderivato dalla prima riga del CSV. In questo run il
# file NEXUS_trades.csv non porta la riga di intestazione (isNew=false
# al primo utilizzo per un motivo non verificabile da qui - il file era
# comunque assente prima dell'avvio, confermato) - la prima riga reale
# e' gia' un record OPEN. Rilevata dinamicamente per essere robusti a
# entrambi i casi (con o senza header), mai assunta a priori.
CSV_HEADER = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
              "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]


def load_trades_csv(path):
    with open(path, encoding="utf-16") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    if not lines:
        return []
    first_fields = lines[0].split(",")
    has_header = first_fields[:2] == ["time", "action"]
    data_lines = lines[1:] if has_header else lines
    return [dict(zip(CSV_HEADER, ln.split(","))) for ln in data_lines]


TIMEOUT_BARS_H4_SECONDS = 40 * 4 * 3600  # 40 barre H4 (~6.7 giorni), timeout congelato in 7.8B
SL_TP_MATCH_CONFIDENCE_THRESHOLD = 50.0  # USD - vedi rationale sotto
TIME_MATCH_CONFIDENCE_THRESHOLD_SEC = 8 * 3600  # 8h - vedi rationale sotto


def build_trade_records(rows):
    # NXS_LogTradeCSV("OPEN", 0, ...) logga SEMPRE ticket=0 nel percorso
    # "profili per-strategia" (NEXUS_EA_v2.mq5) - il matching per ticket e'
    # quindi impossibile per le righe OPEN (tutte "0"). Il conto e' in
    # HEDGING mode (log terminale: "hedging mode") - MULTIPLE posizioni
    # della stessa strategia possono restare aperte simultaneamente
    # (osservato: fino a 5 OPEN consecutive prima di una CLOSE), quindi un
    # semplice FIFO assumerebbe un ordine di chiusura NON garantito.
    #
    # Matching EVIDENCE-BASED: per ogni CLOSE, tra le posizioni pendenti
    # (aperte, non ancora chiuse), sceglie quella la cui evidenza combacia
    # col reason della chiusura - SL/TP nominale vicino al prezzo di
    # chiusura (reason=sl/tp), o tempo di apertura + 40 barre H4 vicino al
    # close_time (reason=time). Se il miglior candidato non e'
    # NETTAMENTE piu' vicino di ogni alternativa (soglie sotto), il trade e'
    # flaggato MATCH_AMBIGUOUS invece di assumere silenziosamente - stesso
    # principio del bracket worst/best gia' congelato per l'ambiguita'
    # SL/TP intrabarra (7.8B/7.8C).
    strat_rows = sorted((r for r in rows if r.get("strategy") == CANDIDATE_ID), key=lambda r: r["time"])
    pending = []
    trades = []
    unmatched_closes = []
    ambiguous_matches = []
    for r in strat_rows:
        if r["action"] == "OPEN":
            pending.append(r)
        elif r["action"] == "CLOSE":
            if not pending:
                unmatched_closes.append(r)
                continue
            close_price = float(r["price"])
            close_time_dt = parse_dt(r["time"])
            reason = r["reason"]
            scored = []
            for o in pending:
                if reason == "sl":
                    dist = abs(float(o["sl"]) - close_price)
                    threshold = SL_TP_MATCH_CONFIDENCE_THRESHOLD
                elif reason == "tp":
                    dist = abs(float(o["tp"]) - close_price)
                    threshold = SL_TP_MATCH_CONFIDENCE_THRESHOLD
                elif reason == "time":
                    expected_close = parse_dt(o["time"]).timestamp() + TIMEOUT_BARS_H4_SECONDS
                    dist = abs(expected_close - close_time_dt.timestamp())
                    threshold = TIME_MATCH_CONFIDENCE_THRESHOLD_SEC
                else:
                    dist = (close_time_dt - parse_dt(o["time"])).total_seconds()  # FIFO fallback
                    threshold = None
                scored.append((dist, o, threshold))
            scored.sort(key=lambda x: x[0])
            best_dist, best_open, threshold = scored[0]
            is_ambiguous = False
            if threshold is not None:
                if best_dist > threshold:
                    is_ambiguous = True
                elif len(scored) > 1 and scored[1][0] < threshold and scored[1][0] < best_dist * 3:
                    is_ambiguous = True  # secondo candidato quasi altrettanto plausibile
            alt_open = scored[1][1] if is_ambiguous and len(scored) > 1 else None
            pending.remove(best_open)
            entry, sl = float(best_open["price"]), float(best_open["sl"])
            rd = abs(entry - sl)

            def make_leg(o):
                e, s = float(o["price"]), float(o["sl"])
                return {"entry": e, "sl": s, "rd": abs(e - s), "direction": "SELL" if e > s else "BUY"}

            trade = {
                "ticket": r["ticket"], "open_time": best_open["time"], "close_time": r["time"],
                "entry": entry, "sl": sl, "rd": rd,
                "direction": "SELL" if entry > sl else "BUY",
                "r_multiple_broker_baseline": float(r["r_multiple"]),
                "reason": reason, "hold_sec": float(r["hold_sec"]),
                "match_confidence_distance": best_dist, "match_ambiguous": is_ambiguous,
                "alt_leg": make_leg(alt_open) if alt_open is not None else None,
            }
            trades.append(trade)
            if is_ambiguous:
                ambiguous_matches.append(trade["ticket"])
    diagnostics = {"n_open_rows": sum(1 for r in strat_rows if r["action"] == "OPEN"),
                   "n_close_rows": sum(1 for r in strat_rows if r["action"] == "CLOSE"),
                   "n_matched_trades": len(trades),
                   "n_unmatched_opens_at_end": len(pending),
                   "n_unmatched_closes": len(unmatched_closes),
                   "n_ambiguous_matches": len(ambiguous_matches),
                   "ambiguous_match_tickets": ambiguous_matches,
                   "sl_tp_confidence_threshold_usd": SL_TP_MATCH_CONFIDENCE_THRESHOLD,
                   "time_confidence_threshold_sec": TIME_MATCH_CONFIDENCE_THRESHOLD_SEC}
    return trades, diagnostics


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


def sanity_gate_check(manifest, n_nominal_from_csv):
    """Punto 5/8: indipendente dal nome testuale del selettore (fallback
    'selector_56' atteso e non un fallimento - vedi 7.8I punto 5)."""
    result = {
        "research_mode_true_in_ini": None, "selector_56_in_ini": None,
        "master_switch_true_in_ini": None, "total_trades_per_official_report": None,
        "fatal_research_errors_count": None, "research_init_line_found": None,
        "gate_status": None,
    }
    ini_entry = manifest["payload"]["collected_files"].get("tester_ini_used")
    if ini_entry:
        with open(os.path.join(ROOT, ini_entry["dest_path"]), encoding="utf-8") as f:
            ini_text = f.read()
        result["research_mode_true_in_ini"] = "InpResearchMode=true" in ini_text
        result["selector_56_in_ini"] = "InpStrategySelector=56" in ini_text
        result["master_switch_true_in_ini"] = "InpStrat_VolBreakoutConfirmed=true" in ini_text

    report_entry = manifest["payload"]["collected_files"].get("report_htm")
    if report_entry:
        with open(os.path.join(ROOT, report_entry["dest_path"]), encoding="utf-16", errors="ignore") as f:
            report_text = f.read()
        idx = report_text.find("Operazioni di Trading Totali")
        m = re.search(r"<b>(.*?)</b>", report_text[idx: idx + 300]) if idx >= 0 else None
        result["total_trades_per_official_report"] = m.group(1).strip() if m else None

    journal_entries = manifest["payload"]["collected_files"].get("tester_journal_logs", [])
    fatal_count, init_found = 0, False
    for entry in journal_entries:
        jpath = os.path.join(ROOT, entry["dest_path"])
        try:
            with open(jpath, encoding="utf-16-le", errors="ignore") as f:
                content = f.read()
        except OSError:
            continue
        fatal_count += content.count("[RESEARCH][FATAL]")
        idx = content.rfind("[RESEARCH][INIT]")
        if idx >= 0 and "selector=56" in content[idx: idx + 260]:
            init_found = True
    result["fatal_research_errors_count"] = fatal_count
    result["research_init_line_found"] = init_found

    prereqs_ok = (result["research_mode_true_in_ini"] and result["selector_56_in_ini"]
                  and result["master_switch_true_in_ini"])

    if n_nominal_from_csv > 0:
        result["gate_status"] = "PASS_TRADES_PRESENT"
    elif not prereqs_ok:
        result["gate_status"] = "TECHNICAL_EXECUTION_FAILURE_CONFIG_STILL_WRONG"
    elif fatal_count > 0:
        result["gate_status"] = "TECHNICAL_EXECUTION_FAILURE_RESEARCH_PREFLIGHT_FATAL"
    elif not init_found:
        result["gate_status"] = "TECHNICAL_EXECUTION_FAILURE_STRATEGY_NEVER_INITIALIZED"
    else:
        result["gate_status"] = "ZERO_MARKET_SIGNALS_STRATEGY_EVALUATED_BUT_NEVER_TRIGGERED"
    return result


def compute():
    manifest = load_json(os.path.join(PHASE78I_DIR, "immutable_run_manifest_run3_v1.json"))
    trades_csv_entry = manifest["payload"]["collected_files"].get("trade_log_csv")

    all_trades = []
    matching_diagnostics = None
    if trades_csv_entry:
        rows = load_trades_csv(os.path.join(ROOT, trades_csv_entry["dest_path"]))
        all_trades, matching_diagnostics = build_trade_records(rows)

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
            "phase": "7.8I", "artifact_role": "SERIOUS_VALIDATION_RESULT", "candidate_id": CANDIDATE_ID,
            "sanity_gate": sanity, "sample": {"n_nominal_fresh": 0},
            "trade_matching_diagnostics": matching_diagnostics,
            "final_classification": sanity["gate_status"], "no_statistical_verdict_computed": True,
            "note": "n=0 nel run corretto - il sanity gate ha classificato la causa invece di applicare "
                   "automaticamente INSUFFICIENT_SAMPLE.",
        }
        return payload

    # r_multiple_broker_baseline e' letto DIRETTAMENTE dal CSV (P&L reale /
    # rischio reale della posizione che si e' effettivamente chiusa) - NON
    # dipende da quale OPEN il matching sceglie di abbinare. L'ambiguita' di
    # matching (12/183 trade, 6.6%) influenza SOLO rd/direction usati per
    # gli scenari di costo extra (CONSERVATIVE/STRESS) e il diagnostic
    # BUY/SELL - il PRIMARY endpoint (BROKER_BASELINE) e' quindi SOLIDO
    # indipendentemente da questa ambiguita'.
    r_broker = [t["r_multiple_broker_baseline"] for t in fresh_trades]
    expectancy_broker = statistics.fmean(r_broker)

    def stress_bracket(mult, use_alt):
        vals = []
        for t in fresh_trades:
            leg = t if not (use_alt and t.get("match_ambiguous") and t.get("alt_leg")) else \
                {**t, "rd": t["alt_leg"]["rd"]}
            vals.append(apply_stress_scenario(leg, mult))
        return vals

    r_stress_a, r_stress_b = stress_bracket(SCENARIO_MULT["STRESS"], False), stress_bracket(SCENARIO_MULT["STRESS"], True)
    r_cons_a, r_cons_b = stress_bracket(SCENARIO_MULT["CONSERVATIVE"], False), stress_bracket(SCENARIO_MULT["CONSERVATIVE"], True)
    expectancy_stress_a, expectancy_stress_b = statistics.fmean(r_stress_a), statistics.fmean(r_stress_b)
    expectancy_conservative_a, expectancy_conservative_b = statistics.fmean(r_cons_a), statistics.fmean(r_cons_b)
    matching_ambiguity_changes_cost_robustness = (expectancy_stress_a > 0) != (expectancy_stress_b > 0)
    # Scenario riportato come STRESS/CONSERVATIVE primario: quello coerente col matching scelto (A) -
    # B e' il bracket alternativo, riportato per trasparenza.
    r_stress, r_conservative = r_stress_a, r_cons_a
    expectancy_stress, expectancy_conservative = expectancy_stress_a, expectancy_conservative_a
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
    t_ok = n_segments_nonneg >= 2 and not concentration_violation
    t_both_violated = n_segments_nonneg < 2 and concentration_violation

    def classify(cost_robustness_value):
        if insufficient_sample:
            return "INSUFFICIENT_SAMPLE"
        if not sign_criterion:
            return "FAIL"
        n_failed_hard = sum([not uncertainty_requirement, not cost_robustness_value, t_both_violated,
                              one_side_materially_negative_saving_aggregate])
        if n_failed_hard >= 2:
            return "FAIL"
        if n_failed_hard == 0 and t_ok and not one_side_materially_negative_saving_aggregate:
            return "PASS"
        return "BORDERLINE"

    cost_robustness = expectancy_stress_a > 0
    cost_robustness_alt = expectancy_stress_b > 0
    verdict_a = classify(cost_robustness)
    verdict_b = classify(cost_robustness_alt)
    matching_ambiguity_changes_verdict = verdict_a != verdict_b

    verdict = "EXECUTION_ORDER_UNRESOLVED_BLOCKS_VERDICT" if matching_ambiguity_changes_verdict else verdict_a

    payload = {
        "phase": "7.8I", "artifact_role": "SERIOUS_VALIDATION_RESULT", "candidate_id": CANDIDATE_ID,
        "sanity_gate": sanity,
        "trade_matching_diagnostics": matching_diagnostics,
        "preregistration_source": {
            "prereg_7_8b_sha256": "4eadc5fd9c529e1bb8722add4dcb5784ae85327e991c6c1c6712c163f4d827e8",
            "authorization_7_8c_sha256": "239ad329967ac0668965f89e3fe217f8b4dec7826b23593a510eba118f6eda78",
        },
        "sample": {
            "n_nominal_fresh": n_nominal, "n_excluded_pre_fresh_window": len(excluded_pre_fresh),
            "excluded_pre_fresh_tickets": [t["ticket"] for t in excluded_pre_fresh],
            "effective_sample_size": "DEPENDENCE_ADJUSTMENT_NOT_APPLIED",
            "effective_sample_size_note": "fallback esplicitamente autorizzato dal prereg 7.8B - solo n "
                "nominale come gate, nessun ESS inventato.",
        },
        "primary_endpoint": {
            "metric": "expectancy_R", "scenario": "BROKER_BASELINE", "window": "PRIMARY_FRESH_VERDICT_WINDOW",
            "value": expectancy_broker,
            "ci95_moving_block_bootstrap": {"lower": ci_lo, "upper": ci_hi, "block_length_L": block_len,
                                             "n_bootstrap": N_BOOTSTRAP, "seed": RNG_SEED},
        },
        "cost_scenarios": {
            "ZERO_COST": "NOT_DIRECTLY_ESTIMABLE_FROM_REAL_TESTER_EXECUTION",
            "BROKER_BASELINE": {"expectancy_R": expectancy_broker, "role": "PRIMARY_FOR_VERDICT",
                                "note": "Letto direttamente dal CSV (P&L reale/rischio reale) - NON "
                                       "dipende dal matching OPEN/CLOSE, quindi immune all'ambiguita' "
                                       "di matching sotto."},
            "CONSERVATIVE": {"expectancy_R": expectancy_conservative, "role": "STRESS_DIAGNOSTIC",
                             "bracket_alt_matching": expectancy_conservative_b},
            "STRESS": {"expectancy_R": expectancy_stress, "role": "STRESS_DIAGNOSTIC",
                      "bracket_alt_matching": expectancy_stress_b},
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
            "note": "Nessuna ambiguita' SL/TP intrabarra - Model=4 con tick reali risolve l'ordine "
                   "meccanicamente. L'ambiguita' rilevante in questo run e' di matching OPEN/CLOSE "
                   "(vedi trade_matching_ambiguity_bracket sotto), causa diversa ma stesso principio "
                   "di gestione (bracket worst/best, mai un'assunzione silenziosa).",
        },
        "trade_matching_ambiguity_bracket": {
            "cause": "Conto in hedging mode (log terminale: 'hedging mode') - multiple posizioni della "
                    "stessa strategia possono restare aperte simultaneamente; le righe OPEN nel CSV "
                    "hanno sempre ticket=0 (non distinguibili), quindi il matching OPEN/CLOSE per i "
                    "trade con 2+ posizioni pendenti simultanee e' evidence-based (SL/TP/timeout piu' "
                    "vicino), non certo.",
            "n_trades_ambiguous": matching_diagnostics["n_ambiguous_matches"],
            "n_trades_total": n_nominal,
            "pct_ambiguous": round(100 * matching_diagnostics["n_ambiguous_matches"] / n_nominal, 2),
            "primary_endpoint_unaffected": True,
            "primary_endpoint_unaffected_reason": "r_multiple_broker_baseline e' letto direttamente dal "
                "CSV, indipendente da quale OPEN e' abbinata dal matching - SOLO gli extra-costi "
                "CONSERVATIVE/STRESS e la direzione BUY/SELL dipendono dal matching.",
            "cost_robustness_scenario_A_matched_leg": cost_robustness,
            "cost_robustness_scenario_B_alt_leg": cost_robustness_alt,
            "verdict_scenario_A": verdict_a,
            "verdict_scenario_B": verdict_b,
            "matching_ambiguity_changes_verdict": matching_ambiguity_changes_verdict,
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
    out_path = os.path.join(PHASE78I_DIR, "volatility_breakout_serious_3y_result_v1.json")
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
