"""
NEXUS Causal Research - Experiment 2: Confirmatory test of Friday + Level Age

CONFERMATIVO, non esplorativo. Nessuna nuova feature, nessuna nuova
combinazione, nessuna soglia ricalcolata sui nuovi dati. Riusa la stessa
logica di parsing/labeling di Experiment 1 (stessa definizione di 1R, stesse
regole di esclusione ambiguous/censored), applicata a un periodo
INDIPENDENTE (2026-04-01 -> 2026-06-01, mai usato in Experiment 1).

Soglia OLD/YOUNG CONGELATA da Experiment 1: 20700 secondi (mediana calcolata
sia sul solo train W1+W2 sia sull'intero risolto Fase 1 - i due valori
coincidono esattamente, nessuna ambiguita' su quale usare). NON ricalcolata
qui.
"""
import re
import math
import csv
import json
from datetime import datetime
from collections import defaultdict, Counter

PIP = 0.10
R_PIPS = 25.0
R_PRICE = R_PIPS * PIP
FROZEN_AGE_THRESHOLD_SECONDS = 20700.0  # da Experiment 1, non ricalcolata

EVENTS_PATH = r"C:\Users\User\.claude\jobs\703d44b4\tmp\phaseExp2_results\indep_events.txt"
BARS_PATH = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\Common\Files\nxs_research_bars_m1_exp2.csv"
WINDOW_ID = "INDEP_2026-04-01_2026-06-01"

EVENT_RE = re.compile(
    r"\[LEVELENGINE\]\[EVENT\] event_id=(\d+) level_id=(\d+) type=(\w+) side=(\w+) dir=(-?\d+) "
    r"price=([\d.]+) pen=([\d.\-]+) touch_count=(\d+) reclaim=(\w+) tf=(\S+) strat=(\S*) "
    r"time=([\d.: ]+) reason=(\S*)"
)


def parse_dt(s):
    return datetime.strptime(s.strip(), "%Y.%m.%d %H:%M:%S")


def load_events(path):
    events = []
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = EVENT_RE.search(line)
        if not m:
            continue
        events.append(dict(
            event_id_local=int(m.group(1)), level_id_local=int(m.group(2)), type=m.group(3),
            side=m.group(4), dir=int(m.group(5)), price=float(m.group(6)), pen=float(m.group(7)),
            touch_count=int(m.group(8)), reclaim=(m.group(9) == "true"), tf=m.group(10),
            strat=m.group(11), timestamp=parse_dt(m.group(12)), reason=m.group(13),
        ))
    return events


def load_bars(path):
    bars = []
    with open(path, encoding="utf-16") as f:
        f.readline()
        for line in f:
            parts = line.strip().split(",")
            if len(parts) != 5:
                continue
            t, o, h, l, c = parts
            bars.append((parse_dt(t), float(o), float(h), float(l), float(c)))
    bars.sort(key=lambda r: r[0])
    return bars


def session_bucket(hour):
    if 0 <= hour < 8:
        return "ASIA"
    if 8 <= hour < 13:
        return "LONDON"
    if 13 <= hour < 22:
        return "NY"
    return "LATE"


def find_outcome(bars, from_ts, entry_ref, direction, dataset_end):
    if direction < 0:
        favorable_level = entry_ref - R_PRICE
        adverse_level = entry_ref + R_PRICE
    else:
        favorable_level = entry_ref + R_PRICE
        adverse_level = entry_ref - R_PRICE
    for (t, o, h, l, c) in bars:
        if t <= from_ts:
            continue
        if t > dataset_end:
            break
        if direction < 0:
            hit_fav = l <= favorable_level
            hit_adv = h >= adverse_level
        else:
            hit_fav = h >= favorable_level
            hit_adv = l <= adverse_level
        if hit_fav and hit_adv:
            return ("AMBIGUOUS_SAME_BAR", (t - from_ts).total_seconds())
        if hit_fav:
            return ("PLUS_1R_FIRST", (t - from_ts).total_seconds())
        if hit_adv:
            return ("MINUS_1R_FIRST", (t - from_ts).total_seconds())
    return ("CENSORED", None)


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((center - margin) / denom, (center + margin) / denom)


def diff_ci(k1, n1, k2, n2, z=1.96):
    """CI approssimato (normale) per la differenza di due proporzioni indipendenti."""
    if n1 == 0 or n2 == 0:
        return (float("nan"), float("nan"))
    p1, p2 = k1 / n1, k2 / n2
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = p1 - p2
    return (d - z * se, d + z * se)


def main():
    print("Caricamento eventi periodo indipendente...")
    events = load_events(EVENTS_PATH)
    print(f"  {len(events)} eventi grezzi")
    bars = load_bars(BARS_PATH)
    print(f"  {len(bars)} barre M1, {bars[0][0]} -> {bars[-1][0]}")
    dataset_end = bars[-1][0]

    by_level = defaultdict(list)
    for e in events:
        by_level[e["level_id_local"]].append(e)

    records = []
    dq = dict(total_sweep_events=0, resolved=0, censored=0, ambiguous_same_bar=0,
              duplicate_level_sweep=0, missing_created_time=0, incoherent=0)

    for lvl, evs in by_level.items():
        evs.sort(key=lambda e: e["event_id_local"])
        creates = [e for e in evs if e["type"] == "CREATE"]
        sweeps = [e for e in evs if e["type"] == "SWEEP"]
        if not sweeps:
            continue
        if len(sweeps) > 1:
            dq["duplicate_level_sweep"] += 1
        sweep = sweeps[0]
        dq["total_sweep_events"] += 1

        created_time = creates[0]["timestamp"] if creates else None
        if not creates:
            dq["missing_created_time"] += 1

        side = sweep["side"]
        direction = sweep["dir"]
        level_price = sweep["price"]
        penetration_pips = sweep["pen"]
        touch_count_before_sweep = sweep["touch_count"]

        entry_ref = level_price + penetration_pips * PIP if direction < 0 else level_price - penetration_pips * PIP

        level_age_seconds = None
        if created_time is not None:
            if created_time <= sweep["timestamp"]:
                level_age_seconds = (sweep["timestamp"] - created_time).total_seconds()
            else:
                dq["incoherent"] += 1

        label, ttf = find_outcome(bars, sweep["timestamp"], entry_ref, direction, dataset_end)
        if label == "CENSORED":
            dq["censored"] += 1
        elif label == "AMBIGUOUS_SAME_BAR":
            dq["ambiguous_same_bar"] += 1
        else:
            dq["resolved"] += 1

        records.append(dict(
            event_id=f"{WINDOW_ID}_{sweep['event_id_local']}",
            level_id=f"{WINDOW_ID}_{lvl}",
            timestamp=sweep["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            side=side, direction=("SELL" if direction < 0 else "BUY"),
            level_price=level_price, entry_ref=round(entry_ref, 2),
            created_time=(created_time.strftime("%Y-%m-%d %H:%M:%S") if created_time else None),
            level_age_seconds=level_age_seconds,
            touch_count_before_sweep=touch_count_before_sweep,
            penetration_pips=penetration_pips, sweep_depth_pips=penetration_pips,
            session_bucket=session_bucket(sweep["timestamp"].hour), hour=sweep["timestamp"].hour,
            day_of_week=sweep["timestamp"].strftime("%A"), source_tf=sweep["tf"],
            window_id=WINDOW_ID, outcome=label, time_to_outcome_seconds=ttf,
        ))

    eids = [r["event_id"] for r in records]
    lids = [r["level_id"] for r in records]
    dq["duplicate_event_id_global"] = len(eids) - len(set(eids))
    dq["duplicate_level_id_global"] = len(lids) - len(set(lids))

    out_csv = r"C:\Users\User\ClaudeWork\MAX\results\causal_experiment_1\wick_sweep_1r_dataset_exp2_confirmation.csv"
    out_json = r"C:\Users\User\ClaudeWork\MAX\results\causal_experiment_1\wick_sweep_1r_dataset_exp2_confirmation.json"
    fieldnames = list(records[0].keys())
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow(r)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str)

    print("\n=== DATA QUALITY ===")
    for k, v in dq.items():
        print(f"  {k}: {v}")
    print(f"\nRecord totali: {len(records)}")
    print("Distribuzione finestra:", Counter(r["window_id"] for r in records))
    print("Distribuzione sessione:", Counter(r["session_bucket"] for r in records))
    print("Distribuzione direction:", Counter(r["direction"] for r in records))
    print("Distribuzione outcome:", Counter(r["outcome"] for r in records))

    resolved = [r for r in records if r["outcome"] in ("PLUS_1R_FIRST", "MINUS_1R_FIRST")]
    n_resolved = len(resolved)
    base_hits = sum(1 for r in resolved if r["outcome"] == "PLUS_1R_FIRST")
    base_rate = base_hits / n_resolved
    print(f"\nBASE RATE indipendente: {base_hits}/{n_resolved} = {base_rate:.3f}")

    def rate(subset):
        if not subset:
            return (0, 0, float("nan"))
        k = sum(1 for r in subset if r["outcome"] == "PLUS_1R_FIRST")
        return (k, len(subset), k / len(subset))

    # --- H1: Friday vs Non-Friday ---
    print("\n=== H1: FRIDAY vs NON-FRIDAY (pre-registrato) ===")
    fri = [r for r in resolved if r["day_of_week"] == "Friday"]
    nonfri = [r for r in resolved if r["day_of_week"] != "Friday"]
    kf, nf, pf = rate(fri)
    kn, nn, pn = rate(nonfri)
    lo_f, hi_f = wilson_ci(kf, nf)
    lo_n, hi_n = wilson_ci(kn, nn)
    abs_uplift = pf - pn
    rel_uplift = (pf - pn) / pn if pn else float("nan")
    dlo, dhi = diff_ci(kf, nf, kn, nn)
    print(f"  Friday:     n={nf:3d}  rate={pf:.3f}  CI95=[{lo_f:.3f},{hi_f:.3f}]")
    print(f"  Non-Friday: n={nn:3d}  rate={pn:.3f}  CI95=[{lo_n:.3f},{hi_n:.3f}]")
    print(f"  Absolute uplift (Friday - NonFriday): {abs_uplift:+.3f}")
    print(f"  Relative uplift: {rel_uplift:+.1%}")
    print(f"  CI95 differenza (Friday-NonFriday): [{dlo:.3f},{dhi:.3f}]")
    print(f"  Experiment 1 (per confronto): Friday=0.657 (n=35), NonFriday~0.523 (n=155 circa)")

    # --- H2: OLD vs YOUNG (soglia congelata) ---
    print(f"\n=== H2: OLD vs YOUNG (soglia congelata Experiment 1 = {FROZEN_AGE_THRESHOLD_SECONDS:.0f}s = "
          f"{FROZEN_AGE_THRESHOLD_SECONDS/3600:.2f}h) ===")
    old = [r for r in resolved if r["level_age_seconds"] and float(r["level_age_seconds"]) >= FROZEN_AGE_THRESHOLD_SECONDS]
    young = [r for r in resolved if r["level_age_seconds"] and float(r["level_age_seconds"]) < FROZEN_AGE_THRESHOLD_SECONDS]
    ko, no_, po = rate(old)
    ky, ny, py = rate(young)
    lo_o, hi_o = wilson_ci(ko, no_)
    lo_y, hi_y = wilson_ci(ky, ny)
    abs_uplift2 = po - py
    rel_uplift2 = (po - py) / py if py else float("nan")
    dlo2, dhi2 = diff_ci(ko, no_, ky, ny)
    print(f"  OLD:   n={no_:3d}  rate={po:.3f}  CI95=[{lo_o:.3f},{hi_o:.3f}]")
    print(f"  YOUNG: n={ny:3d}  rate={py:.3f}  CI95=[{lo_y:.3f},{hi_y:.3f}]")
    print(f"  Absolute uplift (OLD - YOUNG): {abs_uplift2:+.3f}")
    print(f"  Relative uplift: {rel_uplift2:+.1%}")
    print(f"  CI95 differenza (OLD-YOUNG): [{dlo2:.3f},{dhi2:.3f}]")
    print(f"  Experiment 1 (per confronto): OLD=0.578 (n=102), YOUNG=0.511 (n=88)")

    # --- Robustness: sub-periodi temporali grossolani (split a meta') ---
    print("\n=== ROBUSTNESS: split temporale grossolano (prima meta' vs seconda meta') ===")
    resolved_sorted = sorted(resolved, key=lambda r: r["timestamp"])
    half = len(resolved_sorted) // 2
    first_half, second_half = resolved_sorted[:half], resolved_sorted[half:]
    for label, subset in [("Prima meta'", first_half), ("Seconda meta'", second_half)]:
        fri_s = [r for r in subset if r["day_of_week"] == "Friday"]
        nonfri_s = [r for r in subset if r["day_of_week"] != "Friday"]
        _, _, pf_s = rate(fri_s)
        _, _, pn_s = rate(nonfri_s)
        old_s = [r for r in subset if r["level_age_seconds"] and float(r["level_age_seconds"]) >= FROZEN_AGE_THRESHOLD_SECONDS]
        young_s = [r for r in subset if r["level_age_seconds"] and float(r["level_age_seconds"]) < FROZEN_AGE_THRESHOLD_SECONDS]
        _, _, po_s = rate(old_s)
        _, _, py_s = rate(young_s)
        print(f"  {label}: n={len(subset)}  Friday(n={len(fri_s)})={pf_s:.3f} NonFriday(n={len(nonfri_s)})={pn_s:.3f}  "
              f"OLD(n={len(old_s)})={po_s:.3f} YOUNG(n={len(young_s)})={py_s:.3f}")

    # --- Robustness: BUY/SELL separati (solo robustness check, non nuove regole) ---
    print("\n=== ROBUSTNESS: BUY/SELL separati ===")
    for d in ("BUY", "SELL"):
        subset = [r for r in resolved if r["direction"] == d]
        fri_s = [r for r in subset if r["day_of_week"] == "Friday"]
        nonfri_s = [r for r in subset if r["day_of_week"] != "Friday"]
        _, _, pf_s = rate(fri_s)
        _, _, pn_s = rate(nonfri_s)
        old_s = [r for r in subset if r["level_age_seconds"] and float(r["level_age_seconds"]) >= FROZEN_AGE_THRESHOLD_SECONDS]
        young_s = [r for r in subset if r["level_age_seconds"] and float(r["level_age_seconds"]) < FROZEN_AGE_THRESHOLD_SECONDS]
        _, _, po_s = rate(old_s)
        _, _, py_s = rate(young_s)
        print(f"  {d}: n={len(subset)}  Friday(n={len(fri_s)})={pf_s:.3f} NonFriday(n={len(nonfri_s)})={pn_s:.3f}  "
              f"OLD(n={len(old_s)})={po_s:.3f} YOUNG(n={len(young_s)})={py_s:.3f}")


if __name__ == "__main__":
    main()
