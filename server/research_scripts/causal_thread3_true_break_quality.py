"""
NEXUS Causal Research Thread 3: True Break Quality - Continuation vs Failure.

Domanda: DOPO che un TRUE_BREAK e' gia' avvenuto, esistono feature causali
note in quel momento che predicono CONTINUATION (PLUS_1R_FIRST) vs FAILURE
(MINUS_1R_FIRST)? Discovery, non strategia.

Non riapre le ipotesi del Thread 2 (penetration/ATR allo SWEEP, age<1h,
source_tf=D1 sono chiuse). Le usa eventualmente solo come feature candidate
fra molte altre, su un target/observation-point diverso.

Puro standard library, riusa build_structural_dataset_v1.py.
"""
import csv
import json
import math
import os
from datetime import datetime
from collections import defaultdict, Counter

import build_structural_dataset_v1 as bds

HARVEST_DIR = r"C:\Users\User\.claude\jobs\703d44b4\tmp\structural_dataset_v1\harvest"
OUT_DIR = r"C:\Users\User\ClaudeWork\MAX\results\causal_thread3_true_break_quality"
os.makedirs(OUT_DIR, exist_ok=True)

ALL_WINDOWS = [
    {"id": "wA", "from": "2025.05.01", "to": "2025.09.01"},
    {"id": "w0", "from": "2025.09.01", "to": "2026.01.01"},
    {"id": "w1", "from": "2026.01.01", "to": "2026.03.01"},
    {"id": "w2", "from": "2026.03.01", "to": "2026.05.01"},
    {"id": "w3", "from": "2026.05.01", "to": "2026.07.01"},
    {"id": "w4", "from": "2026.07.01", "to": "2026.08.25"},
]
DISCOVERY_WINDOWS = {"wA", "w0"}
VALIDATION_WINDOWS = {"w1", "w2", "w3", "w4"}

PIP_SIZE = bds.PIP_SIZE
R_PIPS = bds.R_PIPS
MIN_RESOLVED_TOTAL = 150
MIN_EFFECT = 0.10
MIN_N_TRAIN = 30
MIN_N_OOS = 20
MIN_N_SIDE = 15
MIN_N_MONTH_DOMINANCE = 0.60  # se un solo mese copre >=60% del bucket, segnalato come rischio artefatto
MIN_N_TAG_DOMINANCE = 0.60


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((center - margin) / denom, (center + margin) / denom)


def load_window_events(win):
    rows = bds.read_structural_csv(os.path.join(HARVEST_DIR, f"structural_events_{win['id']}.csv"))
    for r in rows:
        r["window_id"] = win["id"]
    return rows


def load_window_m1(win):
    return bds.read_m1_csv(os.path.join(HARVEST_DIR, f"nxs_m1_struct_{win['id']}.csv"))


def regime_bucket(regime):
    if regime in ("STRONG_TREND", "WEAK_TREND"):
        return "TREND"
    if regime in ("RANGING",):
        return "RANGE"
    return "OTHER"  # VOLATILE, CHOPPY, UNKNOWN


def main():
    all_events = []
    m1_by_window = {}
    window_end_by_id = {}
    for win in ALL_WINDOWS:
        ev = load_window_events(win)
        all_events.extend(ev)
        m1_by_window[win["id"]] = load_window_m1(win)
        window_end_by_id[win["id"]] = datetime.strptime(win["to"], "%Y.%m.%d")

    lifecycle_link, episodes, true_orphans, redundant_after_close, true_break_after_close = bds.assign_episodes(all_events)
    episode_lifecycle = bds.build_episode_lifecycle_index(all_events, lifecycle_link)
    redundant_ids = set(e["event_id"] for e in redundant_after_close)
    tbac_ids = set(e["event_id"] for e in true_break_after_close)
    sweeps_by_episode = {e["structural_episode_id"]: e for e in all_events if e["event_type"] == "SWEEP"}
    malformed = [e for e in all_events if e["direction"] == "NONE" or not e.get("side") or e["level_price"] <= 0]

    # [Phase C.1 fix] chiave (window_id, event_id), MAI event_id da solo - event_id
    # riparte da 1 ad ogni run/finestra (vedi Structural Causal Experiment 1); un
    # set sul solo event_id qui sottostimava il conteggio orphan di 5 unita' su 288
    # per collisione cross-window (bug scoperto in Phase C.1 Orphan TRUE_BREAK Audit).
    orphan_true_break_ids = set((e["window_id"], e["event_id"]) for e in true_orphans if e["event_type"] == "TRUE_BREAK")

    # ============================================================
    # 1. Population: AT_TRUE_BREAK, episodio valido, esito non post-close, non orphan
    # ============================================================
    tb_rows = []
    excluded_reasons = Counter()
    for ep_id, sweep_ev in sweeps_by_episode.items():
        peers = episode_lifecycle.get(ep_id, [])
        tb_list = sorted([p for p in peers if p["event_type"] == "TRUE_BREAK"], key=lambda x: int(x["event_id"]))
        if not tb_list:
            continue
        b = tb_list[0]  # il PRIMO true break dell'episodio (episodio per costruzione ne ha al piu' uno "reale")
        if b["event_id"] in redundant_ids or b["event_id"] in tbac_ids:
            excluded_reasons["lifecycle_redundant_or_after_close"] += 1
            continue

        win = b["window_id"]
        sw_atr = float(sweep_ev["atr_at_event"]) if sweep_ev["atr_at_event"] not in (None, "") else None
        sw_pen_pips = float(sweep_ev["penetration_pips"])
        sw_pen_per_atr = (sw_pen_pips * PIP_SIZE / sw_atr) if (sw_atr and sw_atr > 0) else None

        tb_atr = float(b["atr_at_event"]) if b["atr_at_event"] not in (None, "") else None
        tb_pen_pips = float(b["penetration_pips"])
        tb_pen_per_atr = (tb_pen_pips * PIP_SIZE / tb_atr) if (tb_atr and tb_atr > 0) else None

        dsign = 1 if b["direction"] == "BUY" else (-1 if b["direction"] == "SELL" else 0)
        m1_tuple = m1_by_window[win]
        window_end = window_end_by_id[win]
        fwd = bds.scan_forward_labels(m1_tuple, window_end, b["timestamp"], float(b["price_at_event"]), dsign, tb_atr)

        rt = sorted([p for p in peers if p["event_type"] == "RETEST"], key=lambda x: int(x["event_id"]))
        retest_outcome = "N/A_NO_RETEST"
        if rt:
            r0 = rt[0]
            r_dsign = dsign
            r_fwd = bds.scan_forward_labels(m1_tuple, window_end, r0["timestamp"], float(r0["price_at_event"]), r_dsign, None)
            retest_outcome = {
                "PLUS_1R_FIRST": "HOLD", "MINUS_1R_FIRST": "FAIL",
                "AMBIGUOUS_SAME_BAR": "AMBIGUOUS", "CENSORED": "CENSORED",
            }[r_fwd["plus1r_before_minus1r"]]

        regime_changed = (b["regime_at_event"] != sweep_ev["regime_at_event"])
        trend_aligned = (
            (b["direction"] == "BUY" and b["structure_trend_at_event"] == "UP") or
            (b["direction"] == "SELL" and b["structure_trend_at_event"] == "DOWN")
        )
        regime_cat_same = (regime_bucket(b["regime_at_event"]) == regime_bucket(sweep_ev["regime_at_event"]))

        tb_rows.append({
            "episode_id": ep_id, "window_id": win, "true_break_event_id": b["event_id"],
            "sweep_event_id": sweep_ev["event_id"], "timestamp": b["timestamp"],
            "direction": b["direction"], "side": b["side"], "tb_source_tf": b["source_tf"],
            "tb_regime_at_event": b["regime_at_event"], "tb_structure_trend_at_event": b["structure_trend_at_event"],
            "tb_atr_at_event": tb_atr, "tb_penetration_pips": tb_pen_pips, "tb_penetration_per_atr": tb_pen_per_atr,
            "sweep_penetration_per_atr": sw_pen_per_atr, "sweep_source_tf": sweep_ev["source_tf"],
            "sweep_regime_at_event": sweep_ev["regime_at_event"],
            "sweep_structure_trend_at_event": sweep_ev["structure_trend_at_event"],
            "regime_changed_sweep_to_break": regime_changed,
            "direction_trend_aligned_at_break": trend_aligned,
            "regime_category_same_sweep_to_break": regime_cat_same,
            "plus1r_before_minus1r": fwd["plus1r_before_minus1r"],
            "continuation_1atr_before_failure": fwd["continuation_1atr_before_failure"],
            "retest_outcome": retest_outcome,
            "period": "DISCOVERY" if win in DISCOVERY_WINDOWS else "VALIDATION",
        })

    print("=== POPULATION AUDIT ===")
    print(f"Episodi con almeno un TRUE_BREAK: {sum(1 for ep in sweeps_by_episode if any(p['event_type']=='TRUE_BREAK' for p in episode_lifecycle.get(ep, [])))}")
    print(f"Esclusioni: {dict(excluded_reasons)}")
    print(f"Orphan TRUE_BREAK (nessun episodio aperto - dovrebbe essere 0): {len(orphan_true_break_ids)}")
    print(f"Malformed rows totali nel dataset grezzo (dovrebbe essere 0): {len(malformed)}")
    print(f"TRUE_BREAK validi in population: {len(tb_rows)}")

    n_total = len(tb_rows)
    n_ambiguous = sum(1 for r in tb_rows if r["plus1r_before_minus1r"] == "AMBIGUOUS_SAME_BAR")
    n_censored = sum(1 for r in tb_rows if r["plus1r_before_minus1r"] == "CENSORED")
    resolved = [r for r in tb_rows if r["plus1r_before_minus1r"] in ("PLUS_1R_FIRST", "MINUS_1R_FIRST")]
    n_resolved = len(resolved)
    n_buy = sum(1 for r in tb_rows if r["direction"] == "BUY")
    n_sell = sum(1 for r in tb_rows if r["direction"] == "SELL")

    print(f"\n=== SAMPLE SUFFICIENCY ===")
    print(f"n totale TRUE_BREAK validi: {n_total}")
    print(f"PLUS_1R_FIRST: {sum(1 for r in resolved if r['plus1r_before_minus1r']=='PLUS_1R_FIRST')}")
    print(f"MINUS_1R_FIRST: {sum(1 for r in resolved if r['plus1r_before_minus1r']=='MINUS_1R_FIRST')}")
    print(f"AMBIGUOUS_SAME_BAR: {n_ambiguous} ({n_ambiguous/n_total:.1%})")
    print(f"CENSORED: {n_censored} ({n_censored/n_total:.1%})")
    print(f"n RISOLTI totali: {n_resolved}")
    print(f"BUY: {n_buy}  SELL: {n_sell}")

    if n_resolved < MIN_RESOLVED_TOTAL:
        print(f"\n=== VERDICT: HOLD_INSUFFICIENT_TRUE_BREAK_SAMPLE ===")
        print(f"n_resolved={n_resolved} < soglia richiesta {MIN_RESOLVED_TOTAL}. STOP, nessuna discovery multivariata.")
        _save_minimal(tb_rows, n_total, n_resolved, n_ambiguous, n_censored, n_buy, n_sell,
                       "HOLD_INSUFFICIENT_TRUE_BREAK_SAMPLE")
        tb_fields = ["episode_id", "window_id", "true_break_event_id", "sweep_event_id", "timestamp", "direction", "side",
                     "tb_source_tf", "tb_regime_at_event", "tb_structure_trend_at_event", "tb_atr_at_event",
                     "tb_penetration_pips", "tb_penetration_per_atr", "sweep_penetration_per_atr", "sweep_source_tf",
                     "sweep_regime_at_event", "sweep_structure_trend_at_event", "regime_changed_sweep_to_break",
                     "direction_trend_aligned_at_break", "regime_category_same_sweep_to_break",
                     "plus1r_before_minus1r", "continuation_1atr_before_failure", "retest_outcome", "period"]
        with open(os.path.join(OUT_DIR, "thread3_at_true_break.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=tb_fields)
            writer.writeheader()
            for r in tb_rows:
                writer.writerow({k: r.get(k) for k in tb_fields})
        return

    # ============================================================
    # 6-9: Discovery/Validation split, univariata, logistic, tree
    # ============================================================
    train = [r for r in resolved if r["period"] == "DISCOVERY"]
    oos = [r for r in resolved if r["period"] == "VALIDATION"]
    print(f"\n=== SPLIT TEMPORALE ===")
    print(f"DISCOVERY (wA+w0, 2025-05-01->2026-01-01): n={len(train)}")
    print(f"VALIDATION (w1-w4, 2026-01-01->2026-08-25): n={len(oos)}")

    def rate_of(subset):
        n = len(subset)
        k = sum(1 for r in subset if r["plus1r_before_minus1r"] == "PLUS_1R_FIRST")
        return k, n, (k / n if n else float("nan"))

    k_tr, n_tr, base_tr = rate_of(train)
    k_oos, n_oos_, base_oos = rate_of(oos)
    k_all, n_all, base_all = rate_of(resolved)
    lo_all, hi_all = wilson_ci(k_all, n_all)
    print(f"\n=== BASE RATE (PLUS_1R_FIRST) ===")
    print(f"Totale: {k_all}/{n_all} = {base_all:.3f} CI95=[{lo_all:.3f},{hi_all:.3f}]")
    print(f"DISCOVERY: {k_tr}/{n_tr}={base_tr:.3f}   VALIDATION: {k_oos}/{n_oos_}={base_oos:.3f}")

    def q(vals, k):
        s = sorted(vals)
        n = len(s)
        if n == 0:
            return None
        return s[min(n - 1, int(n * k))]

    def quartiles_train(feat_fn):
        vals = sorted(v for v in (feat_fn(r) for r in train) if v is not None)
        n = len(vals)
        if n < 8:
            return None
        return [vals[n // 4], vals[n // 2], vals[3 * n // 4]]

    def qbucket(val, qs):
        if val is None or qs is None:
            return None
        if val <= qs[0]:
            return "Q1"
        if val <= qs[1]:
            return "Q2"
        if val <= qs[2]:
            return "Q3"
        return "Q4"

    tb_pen_atr_q = quartiles_train(lambda r: r["tb_penetration_per_atr"])
    sweep_pen_atr_q = quartiles_train(lambda r: r["sweep_penetration_per_atr"])
    tb_pen_pips_q = quartiles_train(lambda r: r["tb_penetration_pips"])

    specs = [
        ("direction", lambda r: r["direction"]),
        ("side", lambda r: r["side"]),
        ("tb_source_tf", lambda r: r["tb_source_tf"]),
        ("sweep_source_tf", lambda r: r["sweep_source_tf"]),
        ("tb_regime_at_event", lambda r: r["tb_regime_at_event"]),
        ("sweep_regime_at_event", lambda r: r["sweep_regime_at_event"]),
        ("tb_structure_trend_at_event", lambda r: r["tb_structure_trend_at_event"]),
        ("sweep_structure_trend_at_event", lambda r: r["sweep_structure_trend_at_event"]),
        ("regime_changed_sweep_to_break", lambda r: r["regime_changed_sweep_to_break"]),
        ("direction_trend_aligned_at_break", lambda r: r["direction_trend_aligned_at_break"]),
        ("regime_category_same_sweep_to_break", lambda r: r["regime_category_same_sweep_to_break"]),
        ("tb_penetration_per_atr_quartile", lambda r: qbucket(r["tb_penetration_per_atr"], tb_pen_atr_q)),
        ("sweep_penetration_per_atr_quartile", lambda r: qbucket(r["sweep_penetration_per_atr"], sweep_pen_atr_q)),
        ("tb_penetration_pips_quartile", lambda r: qbucket(r["tb_penetration_pips"], tb_pen_pips_q)),
    ]

    def bucket_report(name, fn):
        results = []
        buckets = set(fn(r) for r in train if fn(r) is not None)
        for bkt in sorted(buckets, key=str):
            tr_b = [r for r in train if fn(r) == bkt]
            oos_b = [r for r in oos if fn(r) == bkt]
            kt, nt, pt = rate_of(tr_b)
            ko, no_, po = rate_of(oos_b)
            lo, hi = wilson_ci(kt, nt) if nt else (float("nan"), float("nan"))
            up_tr = (pt - base_tr) if nt else float("nan")
            up_oos = (po - base_oos) if no_ else float("nan")
            same_dir = "N/A"
            if nt >= 10 and no_ >= 10 and not math.isnan(pt) and not math.isnan(po):
                same_dir = "SI" if (up_tr > 0) == (up_oos > 0) else "NO"
            # composizione per side/mese (per il pattern di robustezza, calcolata sul TRAIN)
            side_counts = Counter(r["side"] for r in tr_b)
            month_counts = Counter(r["timestamp"].strftime("%Y-%m") for r in tr_b)
            top_tag_frac = (side_counts.most_common(1)[0][1] / nt) if nt and side_counts else 0
            top_month_frac = (month_counts.most_common(1)[0][1] / nt) if nt and month_counts else 0
            results.append({
                "feature": name, "bucket": str(bkt), "n_train": nt, "rate_train": pt, "ci95_train": [lo, hi],
                "uplift_train": up_tr, "n_oos": no_, "rate_oos": po, "uplift_oos": up_oos,
                "same_direction": same_dir, "top_levelTag_frac_train": top_tag_frac,
                "top_month_frac_train": top_month_frac,
                "levelTag_composition_train": dict(side_counts), "month_composition_train": dict(month_counts),
            })
        return results

    all_univariate = []
    for name, fn in specs:
        all_univariate.extend(bucket_report(name, fn))
    n_hyp = len(all_univariate)
    print(f"\n=== ANALISI UNIVARIATA ({n_hyp} bucket/ipotesi testate - multiple comparison) ===")
    for r in all_univariate:
        print(f"  {r['feature']:36s}={r['bucket']:14s} TRAIN n={r['n_train']:4d} rate={r['rate_train']:.3f} "
              f"uplift={r['uplift_train']:+.3f}  OOS n={r['n_oos']:4d} rate={r['rate_oos']:.3f} uplift={r['uplift_oos']:+.3f}  "
              f"stessa_dir={r['same_direction']}  top_tag_frac={r['top_levelTag_frac_train']:.2f}  top_month_frac={r['top_month_frac_train']:.2f}")

    # ============================================================
    # Classificazione anti-data-mining (con controllo artefatto tag/mese, lezione da age<1h)
    # ============================================================
    classified = []
    for r in all_univariate:
        if r["n_train"] < MIN_N_TRAIN or r["n_oos"] < MIN_N_OOS:
            cls, reason = "NO_SIGNAL", f"campione insufficiente (train={r['n_train']}, oos={r['n_oos']})"
        elif r["same_direction"] != "SI":
            cls, reason = "NO_SIGNAL", "direzione non coerente train/oos"
        elif abs(r["uplift_train"]) < MIN_EFFECT or abs(r["uplift_oos"]) < MIN_EFFECT:
            cls, reason = "WEAK_HINT", "direzione coerente ma effetto sotto soglia in almeno un set"
        elif r["top_levelTag_frac_train"] >= MIN_N_TAG_DOMINANCE:
            cls, reason = "WEAK_HINT", f"dipende per >={MIN_N_TAG_DOMINANCE:.0%} da un solo levelTag (rischio artefatto tipo age<1h)"
        elif r["top_month_frac_train"] >= MIN_N_MONTH_DOMINANCE:
            cls, reason = "WEAK_HINT", f"dipende per >={MIN_N_MONTH_DOMINANCE:.0%} da un solo mese"
        else:
            cls, reason = "PROMISING_HYPOTHESIS", "effetto grande, direzione coerente, campione adeguato, non concentrato su un solo tag/mese"
        classified.append({**r, "classification": cls, "reason": reason})

    n_no_signal = sum(1 for c in classified if c["classification"] == "NO_SIGNAL")
    n_weak = sum(1 for c in classified if c["classification"] == "WEAK_HINT")
    n_promising = sum(1 for c in classified if c["classification"] == "PROMISING_HYPOTHESIS")
    print(f"\n=== CLASSIFICAZIONE ({n_hyp} ipotesi) ===  NO_SIGNAL={n_no_signal}  WEAK_HINT={n_weak}  PROMISING_HYPOTHESIS={n_promising}")
    for c in classified:
        if c["classification"] == "PROMISING_HYPOTHESIS":
            print(f"  PROMISING: {c['feature']}={c['bucket']}  train_uplift={c['uplift_train']:+.3f} oos_uplift={c['uplift_oos']:+.3f}")

    # Target secondario (CONTINUATION_1ATR_BEFORE_FAILURE): mai usato per promuovere una feature
    # da solo (per istruzione) - la promozione sopra usa esclusivamente il target primario.
    # Per ogni PROMISING_HYPOTHESIS, il tasso sul secondario e' comunque riportato nel report per
    # controllo di coerenza (fatto manualmente in fase di scrittura, non qui via codice).
    def cont_rate(subset):
        d = [r for r in subset if r["continuation_1atr_before_failure"] in ("CONTINUATION_FIRST", "FAILURE_FIRST")]
        k = sum(1 for r in d if r["continuation_1atr_before_failure"] == "CONTINUATION_FIRST")
        return (k / len(d)) if d else float("nan")

    # ============================================================
    # Logistic regression minimale + shallow tree (depth<=2)
    # ============================================================
    def logf(r):
        pen = r["tb_penetration_per_atr"] or 0.0
        swpen = r["sweep_penetration_per_atr"] or 0.0
        aligned = 1.0 if r["direction_trend_aligned_at_break"] else 0.0
        changed = 1.0 if r["regime_changed_sweep_to_break"] else 0.0
        return [pen, swpen, aligned, changed]

    Xtr = [logf(r) for r in train]
    ytr = [1 if r["plus1r_before_minus1r"] == "PLUS_1R_FIRST" else 0 for r in train]
    Xoos = [logf(r) for r in oos]
    yoos = [1 if r["plus1r_before_minus1r"] == "PLUS_1R_FIRST" else 0 for r in oos]

    def standardize(X):
        n, p = len(X), len(X[0])
        means = [sum(row[j] for row in X) / n for j in range(p)]
        stds = [max(1e-9, math.sqrt(sum((row[j] - means[j]) ** 2 for row in X) / n)) for j in range(p)]
        return means, stds

    def applys(X, means, stds):
        return [[(row[j] - means[j]) / stds[j] for j in range(len(row))] for row in X]

    means, stds = standardize(Xtr)
    Xtr_s, Xoos_s = applys(Xtr, means, stds), applys(Xoos, means, stds)

    def sigmoid(z):
        if z < -30: return 0.0
        if z > 30: return 1.0
        return 1.0 / (1.0 + math.exp(-z))

    def fit(X, y, lr=0.05, epochs=2000, l2=0.01):
        n, p = len(X), len(X[0])
        w, b = [0.0] * p, 0.0
        for _ in range(epochs):
            gw, gb = [0.0] * p, 0.0
            for i in range(n):
                z = b + sum(w[j] * X[i][j] for j in range(p))
                err = sigmoid(z) - y[i]
                for j in range(p):
                    gw[j] += err * X[i][j]
                gb += err
            for j in range(p):
                w[j] -= lr * (gw[j] / n + l2 * w[j])
            b -= lr * (gb / n)
        return w, b

    def acc(X, y, w, b):
        c = 0
        for i in range(len(X)):
            z = b + sum(w[j] * X[i][j] for j in range(len(w)))
            pred = 1 if sigmoid(z) >= 0.5 else 0
            c += (pred == y[i])
        return c / len(X) if X else float("nan")

    w_fit, b_fit = fit(Xtr_s, ytr)
    acc_tr, acc_oos = acc(Xtr_s, ytr, w_fit, b_fit), acc(Xoos_s, yoos, w_fit, b_fit)
    maj_base_oos = max(base_oos, 1 - base_oos)
    log_names = ["tb_penetration_per_atr", "sweep_penetration_per_atr", "direction_trend_aligned", "regime_changed"]
    print(f"\n=== LOGISTIC REGRESSION ===")
    print(f"Feature: {log_names}")
    print(f"Pesi: {[round(x,3) for x in w_fit]}  bias={round(b_fit,3)}")
    print(f"Accuracy DISCOVERY: {acc_tr:.3f}  VALIDATION: {acc_oos:.3f}  Baseline maggioranza VALIDATION: {maj_base_oos:.3f}")

    def gini(y):
        n = len(y)
        if n == 0: return 0.0
        p1 = sum(y) / n
        return 1 - p1 * p1 - (1 - p1) * (1 - p1)

    def best_split(X, y):
        n = len(y)
        best = None
        for j in range(len(X[0])):
            vals = sorted(set(row[j] for row in X))
            for i in range(len(vals) - 1):
                t = (vals[i] + vals[i + 1]) / 2
                ly = [y[k] for k in range(n) if X[k][j] <= t]
                ry = [y[k] for k in range(n) if X[k][j] > t]
                if len(ly) < 15 or len(ry) < 15:
                    continue
                g = (len(ly) * gini(ly) + len(ry) * gini(ry)) / n
                if best is None or g < best[0]:
                    best = (g, j, t)
        return best

    def build_tree(X, y, depth, max_depth=2):
        n = len(y)
        rate = sum(y) / n if n else 0.0
        node = {"n": n, "rate": rate, "leaf": True}
        if depth >= max_depth or n < 30:
            return node
        b = best_split(X, y)
        if b is None:
            return node
        g, j, t = b
        li = [i for i in range(n) if X[i][j] <= t]
        ri = [i for i in range(n) if X[i][j] > t]
        node.update({"leaf": False, "feature_idx": j, "threshold": t,
                     "left": build_tree([X[i] for i in li], [y[i] for i in li], depth + 1, max_depth),
                     "right": build_tree([X[i] for i in ri], [y[i] for i in ri], depth + 1, max_depth)})
        return node

    def print_tree(node, names, indent=""):
        lines = []
        if node["leaf"]:
            lines.append(f"{indent}LEAF n={node['n']} rate={node['rate']:.3f}")
        else:
            lines.append(f"{indent}IF {names[node['feature_idx']]} <= {node['threshold']:.3f} (n={node['n']}, rate={node['rate']:.3f}):")
            lines.extend(print_tree(node["left"], names, indent + "  "))
            lines.append(f"{indent}ELSE:")
            lines.extend(print_tree(node["right"], names, indent + "  "))
        return lines

    tree_names = ["tb_penetration_per_atr", "sweep_penetration_per_atr", "direction_trend_aligned", "regime_changed"]
    Xtr_raw = [logf(r) for r in train]
    tree = build_tree(Xtr_raw, ytr, 0, max_depth=2)
    tree_lines = print_tree(tree, tree_names)
    print(f"\n=== SHALLOW TREE (depth<=2) ===")
    for l in tree_lines:
        print(l)

    def apply_tree(node, x):
        if node["leaf"]:
            return node["rate"]
        j, t = node["feature_idx"], node["threshold"]
        return apply_tree(node["left"] if x[j] <= t else node["right"], x)

    leaf_oos = defaultdict(lambda: [0, 0])
    Xoos_raw = [logf(r) for r in oos]
    for i, x in enumerate(Xoos_raw):
        rate_pred = round(apply_tree(tree, x), 3)
        leaf_oos[rate_pred][0] += yoos[i]
        leaf_oos[rate_pred][1] += 1
    print("Verifica foglie su VALIDATION:")
    for k, (hit, n) in sorted(leaf_oos.items()):
        print(f"  foglia_train_rate={k:.3f}  VALIDATION n={n} rate={hit/n if n else float('nan'):.3f}")

    # ============================================================
    # Retest analysis separata
    # ============================================================
    retest_all = [r for r in tb_rows if r["retest_outcome"] != "N/A_NO_RETEST"]
    retest_resolved = [r for r in retest_all if r["retest_outcome"] in ("HOLD", "FAIL")]
    retest_counts = Counter(r["retest_outcome"] for r in retest_all)
    print(f"\n=== RETEST ANALYSIS ===")
    print(f"n retest osservati: {len(retest_all)}  breakdown: {dict(retest_counts)}")
    retest_status = "RETEST_SAMPLE_INSUFFICIENT" if len(retest_resolved) < 50 else "RETEST_SAMPLE_ADEQUATE"
    print(f"n risolti (HOLD/FAIL): {len(retest_resolved)}  status: {retest_status}")

    # ============================================================
    # Output
    # ============================================================
    verdict = "PROMISING_HYPOTHESIS_FOUND" if n_promising > 0 else "NO_PROMISING_HYPOTHESIS"
    print(f"\n=== VERDICT: {verdict} ===")

    results = {
        "generated_at": datetime.now().isoformat(),
        "windows": ALL_WINDOWS, "discovery_windows": list(DISCOVERY_WINDOWS), "validation_windows": list(VALIDATION_WINDOWS),
        "population": {
            "n_total_true_break": n_total, "n_ambiguous": n_ambiguous, "n_censored": n_censored,
            "n_resolved": n_resolved, "n_buy": n_buy, "n_sell": n_sell,
            "excluded_reasons": dict(excluded_reasons), "orphan_true_break": len(orphan_true_break_ids),
            "malformed_rows": len(malformed),
        },
        "base_rate": {"all": base_all, "discovery": base_tr, "validation": base_oos, "ci95_all": [lo_all, hi_all]},
        "n_hypotheses_tested": n_hyp,
        "classification_summary": {"NO_SIGNAL": n_no_signal, "WEAK_HINT": n_weak, "PROMISING_HYPOTHESIS": n_promising},
        "univariate_results": classified,
        "logistic_regression": {"features": log_names, "weights": w_fit, "bias": b_fit,
                                 "accuracy_discovery": acc_tr, "accuracy_validation": acc_oos,
                                 "majority_baseline_validation": maj_base_oos},
        "decision_tree": {"feature_names": tree_names, "structure_text": tree_lines,
                           "validation_leaf_check": {str(k): {"n": v[1], "rate": v[0]/v[1] if v[1] else None} for k, v in leaf_oos.items()}},
        "retest": {"n_observed": len(retest_all), "breakdown": dict(retest_counts),
                   "n_resolved": len(retest_resolved), "status": retest_status},
        "verdict": verdict,
    }

    def _default(o):
        return str(o)

    with open(os.path.join(OUT_DIR, "thread3_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=_default)

    tb_fields = ["episode_id", "window_id", "true_break_event_id", "sweep_event_id", "timestamp", "direction", "side",
                 "tb_source_tf", "tb_regime_at_event", "tb_structure_trend_at_event", "tb_atr_at_event",
                 "tb_penetration_pips", "tb_penetration_per_atr", "sweep_penetration_per_atr", "sweep_source_tf",
                 "sweep_regime_at_event", "sweep_structure_trend_at_event", "regime_changed_sweep_to_break",
                 "direction_trend_aligned_at_break", "regime_category_same_sweep_to_break",
                 "plus1r_before_minus1r", "continuation_1atr_before_failure", "retest_outcome", "period"]
    with open(os.path.join(OUT_DIR, "thread3_at_true_break.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=tb_fields)
        writer.writeheader()
        for r in tb_rows:
            writer.writerow({k: r.get(k) for k in tb_fields})

    print(f"\nOutput salvato in {OUT_DIR}")


def _save_minimal(tb_rows, n_total, n_resolved, n_ambiguous, n_censored, n_buy, n_sell, verdict):
    results = {
        "generated_at": datetime.now().isoformat(),
        "population": {"n_total_true_break": n_total, "n_resolved": n_resolved, "n_ambiguous": n_ambiguous,
                        "n_censored": n_censored, "n_buy": n_buy, "n_sell": n_sell},
        "verdict": verdict,
    }
    with open(os.path.join(OUT_DIR, "thread3_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
