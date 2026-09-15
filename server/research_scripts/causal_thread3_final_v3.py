"""
NEXUS Causal Research Thread 3 - FINAL RE-RUN on v3 Causal Population.

Il verdict precedente (NO_PROMISING_HYPOTHESIS, ottenuto durante la validazione
di Phase C) e' dichiarato PROVVISORIO in 'NEXUS - Phase C1 Orphan TRUE_BREAK
Audit' perche' la population e' cambiata materialmente (159->344 risolti dopo
la chiusura dei 288 orphan TRUE_BREAK via episode_sweep_link). Questo script
rilancia la STESSA identica metodologia pre-registrata (nessuna soglia, nessuna
feature, nessun target cambiato) sulla population v3.

Population: usa SOLO episode_sweep_link (fonte causale, scritta nell'istante
della transizione IDLE->SWEPT) per risolvere episodio->sweep canonico, tramite
assign_episodes_v3() + episodes[ep_id] (autoritativo, gestisce correttamente
il caso molti-episodeSeq->un canonical event - MAI il fragile sweeps_by_episode
derivato da un singolo campo per riga, che e' la causa stessa degli orphan v2).

Feature set CONGELATO (identico al Thread 3 precedente, nessuna aggiunta):
direction, side, tb_source_tf, tb_regime_at_event, tb_structure_trend_at_event,
tb_atr_at_event, tb_penetration_pips, tb_penetration_per_atr,
sweep_penetration_per_atr, sweep_source_tf, sweep_regime_at_event,
sweep_structure_trend_at_event, regime_changed_sweep_to_break,
direction_trend_aligned_at_break, regime_category_same_sweep_to_break.

Metodologia CONGELATA: base rate, bucket univariati con Wilson CI ed effect
size, logistic regression minimale, shallow tree (depth<=2). Stesse soglie
(MIN_EFFECT=0.10, MIN_N_TRAIN=30, MIN_N_OOS=20, MIN_N_TAG_DOMINANCE=0.60,
MIN_N_MONTH_DOMINANCE=0.60) del Thread 3 precedente - MAI abbassate.

Split temporale CONGELATO: DISCOVERY=wA+w0, VALIDATION=w1-w4, nessun random
split, nessun reshuffling.
"""
import csv
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime

import build_structural_dataset_v1 as bds
import causal_thread3_true_break_quality as c3
import phase_c1_orphan_audit as p1

OUT_DIR = r"C:\Users\User\ClaudeWork\MAX\results\causal_thread3_final_v3"
os.makedirs(OUT_DIR, exist_ok=True)

PIP_SIZE = bds.PIP_SIZE
R_PIPS = bds.R_PIPS
MIN_RESOLVED_TOTAL = 150
MIN_EFFECT = 0.10
MIN_N_TRAIN = 30
MIN_N_OOS = 20
MIN_N_SIDE = 15
MIN_N_MONTH_DOMINANCE = 0.60
MIN_N_TAG_DOMINANCE = 0.60
MIN_RETEST_RESOLVED = 50

wilson_ci = c3.wilson_ci
regime_bucket = c3.regime_bucket


def regime_bucket_of(regime):
    return regime_bucket(regime)


def build_population_v3(all_events, all_links, m1_by_window, window_end_by_id):
    """Population AT_TRUE_BREAK con linkage v3 (episode_sweep_link), feature set
    congelato identico al Thread 3 precedente. Replica ESATTAMENTE la logica di
    causal_thread3_true_break_quality.py (stesso R, stesso orizzonte, stessa
    esclusione post-close) ma usa episodes[ep_id] (autoritativo) al posto del
    fragile sweeps_by_episode - unica differenza rispetto all'originale."""
    (lifecycle_link, episodes, true_orphans,
     redundant_after_close, true_break_after_close, orphan_reasons) = bds.assign_episodes_v3(all_events, all_links)
    episode_lifecycle = bds.build_episode_lifecycle_index(all_events, lifecycle_link)
    redundant_ids = set((e["window_id"], e["event_id"]) for e in redundant_after_close)
    tbac_ids = set((e["window_id"], e["event_id"]) for e in true_break_after_close)
    ev_by_id = {(e["window_id"], e["event_id"]): e for e in all_events}
    malformed = [e for e in all_events if e["direction"] == "NONE" or not e.get("side") or e["level_price"] <= 0]
    orphan_true_break = [e for e in true_orphans if e["event_type"] == "TRUE_BREAK"]

    tb_rows = []
    excluded_reasons = Counter()
    for ep_id, ep_info in episodes.items():
        peers = episode_lifecycle.get(ep_id, [])
        tb_list = sorted([p for p in peers if p["event_type"] == "TRUE_BREAK"], key=lambda x: int(x["event_id"]))
        if not tb_list:
            continue
        b = tb_list[0]
        if (b["window_id"], b["event_id"]) in redundant_ids or (b["window_id"], b["event_id"]) in tbac_ids:
            excluded_reasons["lifecycle_redundant_or_after_close"] += 1
            continue

        win = b["window_id"]
        sweep_ev = ev_by_id.get((win, ep_info["sweep_event_id"]))
        if sweep_ev is None:
            excluded_reasons["sweep_event_missing_unexpected"] += 1
            continue
        sw_atr = float(sweep_ev["atr_at_event"]) if sweep_ev["atr_at_event"] not in (None, "") else None
        sw_pen_pips = float(sweep_ev["penetration_pips"])
        sw_pen_per_atr = (sw_pen_pips * PIP_SIZE / sw_atr) if (sw_atr and sw_atr > 0) else None

        tb_atr = float(b["atr_at_event"]) if b["atr_at_event"] not in (None, "") else None
        tb_pen_pips = float(b["penetration_pips"])
        tb_pen_per_atr = (tb_pen_pips * PIP_SIZE / tb_atr) if (tb_atr and tb_atr > 0) else None

        dsign = 1 if b["direction"] == "BUY" else (-1 if b["direction"] == "SELL" else 0)
        m1_tuple = m1_by_window[win]
        window_end = window_end_by_id[win]
        # causal safety: scan_forward_labels cammina SOLO su barre M1 con time > obs_time
        # (mai <=), mai oltre window_end - nessun future leakage per costruzione.
        fwd = bds.scan_forward_labels(m1_tuple, window_end, b["timestamp"], float(b["price_at_event"]), dsign, tb_atr)

        rt = sorted([p for p in peers if p["event_type"] == "RETEST"], key=lambda x: int(x["event_id"]))
        retest_outcome = "N/A_NO_RETEST"
        if rt:
            r0 = rt[0]
            r_fwd = bds.scan_forward_labels(m1_tuple, window_end, r0["timestamp"], float(r0["price_at_event"]), dsign, None)
            retest_outcome = {
                "PLUS_1R_FIRST": "HOLD", "MINUS_1R_FIRST": "FAIL",
                "AMBIGUOUS_SAME_BAR": "AMBIGUOUS", "CENSORED": "CENSORED",
            }[r_fwd["plus1r_before_minus1r"]]

        regime_changed = (b["regime_at_event"] != sweep_ev["regime_at_event"])
        trend_aligned = (
            (b["direction"] == "BUY" and b["structure_trend_at_event"] == "UP") or
            (b["direction"] == "SELL" and b["structure_trend_at_event"] == "DOWN")
        )
        regime_cat_same = (regime_bucket_of(b["regime_at_event"]) == regime_bucket_of(sweep_ev["regime_at_event"]))

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
            "period": "DISCOVERY" if win in c3.DISCOVERY_WINDOWS else "VALIDATION",
        })

    audit = {
        "orphan_true_break": len(orphan_true_break),
        "malformed_rows": len(malformed),
        "unexplained_orphan": sum(1 for v in orphan_reasons.values() if v == "UNEXPLAINED"),
        "excluded_reasons": dict(excluded_reasons),
    }
    return tb_rows, audit


def rate_of(subset):
    n = len(subset)
    k = sum(1 for r in subset if r["plus1r_before_minus1r"] == "PLUS_1R_FIRST")
    return k, n, (k / n if n else float("nan"))


def main():
    all_events = []
    all_links = []
    m1_by_window = {}
    window_end_by_id = {}
    for win in c3.ALL_WINDOWS:
        ev = c3.load_window_events(win)
        all_events.extend(ev)
        all_links.extend(p1.load_window_links(win))
        m1_by_window[win["id"]] = c3.load_window_m1(win)
        window_end_by_id[win["id"]] = datetime.strptime(win["to"], "%Y.%m.%d")

    # ============================================================
    # 1. Population v3 - required checks
    # ============================================================
    tb_rows, audit = build_population_v3(all_events, all_links, m1_by_window, window_end_by_id)
    print("=== 1. POPULATION (v3, episode_sweep_link) ===")
    print(f"Orphan TRUE_BREAK residui: {audit['orphan_true_break']}  (atteso: 0)")
    print(f"Unexplained orphan: {audit['unexplained_orphan']}  (atteso: 0)")
    print(f"Malformed rows: {audit['malformed_rows']}  (atteso: 0)")
    print(f"Esclusioni post-close/redundant: {dict(audit['excluded_reasons'])}  (atteso: {{}})")
    print(f"TRUE_BREAK validi in population: {len(tb_rows)}  (atteso: ~558)")

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
    print(f"n RISOLTI totali: {n_resolved}  (atteso: ~344)")
    print(f"BUY: {n_buy}  SELL: {n_sell}")

    if n_resolved < MIN_RESOLVED_TOTAL:
        print(f"\n=== VERDICT: HOLD_INSUFFICIENT_TRUE_BREAK_SAMPLE ===")
        verdict = "HOLD_INSUFFICIENT_TRUE_BREAK_SAMPLE"
        _save_and_exit(tb_rows, audit, n_total, n_resolved, n_ambiguous, n_censored, n_buy, n_sell, verdict)
        return

    # ============================================================
    # 2. Ambiguity sensitivity (descrittivo, MAI usato per promuovere)
    # ============================================================
    print(f"\n=== AMBIGUITY SENSITIVITY (descrittivo, non usato per il target primario) ===")
    n_plus = sum(1 for r in resolved if r["plus1r_before_minus1r"] == "PLUS_1R_FIRST")
    worst_case = n_plus / n_total  # tutti gli ambiguous contati come FAIL
    best_case = (n_plus + n_ambiguous) / n_total  # tutti gli ambiguous contati come SUCCESS
    print(f"Ambiguous rate: {n_ambiguous}/{n_total} = {n_ambiguous/n_total:.1%}")
    print(f"Worst-case (ambiguous=FAIL): {worst_case:.3f}")
    print(f"Best-case (ambiguous=SUCCESS): {best_case:.3f}")
    print(f"Range di incertezza: [{worst_case:.3f}, {best_case:.3f}] - solo descrittivo")

    # ============================================================
    # 3. Split temporale CONGELATO
    # ============================================================
    train = [r for r in resolved if r["period"] == "DISCOVERY"]
    oos = [r for r in resolved if r["period"] == "VALIDATION"]
    print(f"\n=== SPLIT TEMPORALE ===")
    print(f"DISCOVERY (wA+w0, 2025-05-01->2026-01-01): n={len(train)}")
    print(f"VALIDATION (w1-w4, 2026-01-01->2026-08-25): n={len(oos)}")

    k_tr, n_tr, base_tr = rate_of(train)
    k_oos, n_oos_, base_oos = rate_of(oos)
    k_all, n_all, base_all = rate_of(resolved)
    lo_all, hi_all = wilson_ci(k_all, n_all)
    print(f"\n=== BASE RATE (PLUS_1R_FIRST) ===")
    print(f"Totale: {k_all}/{n_all} = {base_all:.3f} CI95=[{lo_all:.3f},{hi_all:.3f}]")
    print(f"DISCOVERY: {k_tr}/{n_tr}={base_tr:.3f}   VALIDATION: {k_oos}/{n_oos_}={base_oos:.3f}")

    # ============================================================
    # 4. Feature set CONGELATO + 5. Discovery (univariata, Wilson CI, effect size)
    # ============================================================
    def quartiles_train(feat_fn):
        vals = sorted(v for v in (feat_fn(r) for r in train) if v is not None)
        n = len(vals)
        if n < 8:
            return None
        return [vals[n // 4], vals[n // 2], vals[3 * n // 4]]

    def qbucket(val, qs):
        if val is None or qs is None:
            return None
        if val <= qs[0]: return "Q1"
        if val <= qs[1]: return "Q2"
        if val <= qs[2]: return "Q3"
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
                "fn": fn,
            })
        return results

    all_univariate = []
    for name, fn in specs:
        all_univariate.extend(bucket_report(name, fn))
    n_hyp = len(all_univariate)
    print(f"\n=== ANALISI UNIVARIATA ({n_hyp} bucket/ipotesi testate - multiple comparison, stesso set del Thread 3 precedente) ===")
    for r in all_univariate:
        print(f"  {r['feature']:36s}={r['bucket']:14s} TRAIN n={r['n_train']:4d} rate={r['rate_train']:.3f} "
              f"uplift={r['uplift_train']:+.3f}  OOS n={r['n_oos']:4d} rate={r['rate_oos']:.3f} uplift={r['uplift_oos']:+.3f}  "
              f"stessa_dir={r['same_direction']}  top_tag_frac={r['top_levelTag_frac_train']:.2f}  top_month_frac={r['top_month_frac_train']:.2f}")

    # ============================================================
    # 6. Multiple comparisons - stesse soglie, MAI abbassate
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
            cls, reason = "WEAK_HINT", f"dipende per >={MIN_N_TAG_DOMINANCE:.0%} da un solo levelTag"
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

    # ============================================================
    # 7. Robustness obbligatoria sui top 3 pattern (per |uplift_train|, tra WEAK_HINT/PROMISING)
    # ============================================================
    candidates = [c for c in classified if c["classification"] in ("WEAK_HINT", "PROMISING_HYPOTHESIS")]
    candidates_sorted = sorted(candidates, key=lambda c: abs(c["uplift_train"]), reverse=True)
    top3 = candidates_sorted[:3]
    print(f"\n=== ROBUSTNESS SUI TOP {len(top3)} PATTERN (per |uplift_train|) ===")
    robustness_report = []
    mid_time = c3.DISCOVERY_WINDOWS  # placeholder, ridefinito sotto con split temporale reale
    all_resolved_sorted = sorted(resolved, key=lambda r: r["timestamp"])
    half_idx = len(all_resolved_sorted) // 2
    first_half_ids = set(id(r) for r in all_resolved_sorted[:half_idx])

    for c in top3:
        fn = c["fn"]
        bucket = c["bucket"]
        matching = [r for r in resolved if str(fn(r)) == bucket]
        buy_m = [r for r in matching if r["direction"] == "BUY"]
        sell_m = [r for r in matching if r["direction"] == "SELL"]
        first_m = [r for r in matching if id(r) in first_half_ids]
        second_m = [r for r in matching if id(r) not in first_half_ids]
        kb, nb, pb = rate_of(buy_m)
        ks, ns, ps = rate_of(sell_m)
        kf, nf, pf = rate_of(first_m)
        ksec, nsec, psec = rate_of(second_m)
        month_counts_all = Counter(r["timestamp"].strftime("%Y-%m") for r in matching)
        tag_counts_all = Counter(r["side"] for r in matching)
        top_month_all = (month_counts_all.most_common(1)[0][1] / len(matching)) if matching else 0
        top_tag_all = (tag_counts_all.most_common(1)[0][1] / len(matching)) if matching else 0
        single_dominated = (
            (nb < MIN_N_SIDE or ns < MIN_N_SIDE) or
            top_month_all >= MIN_N_MONTH_DOMINANCE or
            top_tag_all >= MIN_N_TAG_DOMINANCE
        )
        entry = {
            "feature": c["feature"], "bucket": bucket, "classification": c["classification"],
            "n_total": len(matching),
            "discovery_rate": c["rate_train"], "discovery_uplift": c["uplift_train"],
            "validation_rate": c["rate_oos"], "validation_uplift": c["uplift_oos"],
            "first_half_n": nf, "first_half_rate": pf,
            "second_half_n": nsec, "second_half_rate": psec,
            "buy_n": nb, "buy_rate": pb, "sell_n": ns, "sell_rate": ps,
            "top_month_frac": top_month_all, "top_tag_frac": top_tag_all,
            "single_factor_dominated": single_dominated,
            "final_after_robustness": "REJECTED_SINGLE_FACTOR_DOMINATED" if (single_dominated and c["classification"] == "PROMISING_HYPOTHESIS") else c["classification"],
        }
        robustness_report.append(entry)
        print(f"  {c['feature']}={bucket} [{c['classification']}]: "
              f"DISC={c['rate_train']:.3f}(n={c['n_train']}) VALID={c['rate_oos']:.3f}(n={c['n_oos']}) "
              f"1a_meta={pf:.3f}(n={nf}) 2a_meta={psec:.3f}(n={nsec}) "
              f"BUY={pb:.3f}(n={nb}) SELL={ps:.3f}(n={ns}) "
              f"top_month={top_month_all:.2f} top_tag={top_tag_all:.2f} "
              f"single_factor_dominated={single_dominated}")

    n_promising_after_robustness = sum(1 for e in robustness_report if e["final_after_robustness"] == "PROMISING_HYPOTHESIS")

    # ============================================================
    # Logistic regression + shallow tree (IDENTICI al Thread 3 precedente)
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
    # 9. Retest analysis
    # ============================================================
    retest_all = [r for r in tb_rows if r["retest_outcome"] != "N/A_NO_RETEST"]
    retest_resolved = [r for r in retest_all if r["retest_outcome"] in ("HOLD", "FAIL")]
    retest_counts = Counter(r["retest_outcome"] for r in retest_all)
    print(f"\n=== RETEST ANALYSIS ===")
    print(f"n retest osservati: {len(retest_all)}  breakdown: {dict(retest_counts)}")
    retest_status = "RETEST_SAMPLE_INSUFFICIENT" if len(retest_resolved) < MIN_RETEST_RESOLVED else "RETEST_SAMPLE_ADEQUATE"
    print(f"n risolti (HOLD/FAIL): {len(retest_resolved)}  status: {retest_status}")

    # ============================================================
    # 10. Decision gate
    # ============================================================
    verdict = "PROMISING_HYPOTHESIS_FOUND" if n_promising_after_robustness > 0 else "NO_PROMISING_HYPOTHESIS"
    print(f"\n=== VERDICT: {verdict} ===")
    if verdict == "PROMISING_HYPOTHESIS_FOUND":
        print("Congelata SOLO la feature/cutoff/direction/target/observation-point che ha superato il gate "
              "di robustezza (§7) - nessuna implementazione, nessuna ricerca di cutoff migliore, come da istruzione.")

    results = {
        "generated_at": datetime.now().isoformat(),
        "linkage": "v3 (episode_sweep_link, causale)",
        "population": {
            "n_total_true_break": n_total, "n_ambiguous": n_ambiguous, "n_censored": n_censored,
            "n_resolved": n_resolved, "n_buy": n_buy, "n_sell": n_sell,
            "orphan_true_break": audit["orphan_true_break"], "unexplained_orphan": audit["unexplained_orphan"],
            "malformed_rows": audit["malformed_rows"], "excluded_reasons": dict(audit["excluded_reasons"]),
        },
        "ambiguity_sensitivity": {"rate": n_ambiguous / n_total, "worst_case": worst_case, "best_case": best_case},
        "discovery_validation_split": {"n_discovery": len(train), "n_validation": len(oos)},
        "base_rate": {"all": base_all, "discovery": base_tr, "validation": base_oos, "ci95_all": [lo_all, hi_all]},
        "n_hypotheses_tested": n_hyp,
        "classification_summary": {"NO_SIGNAL": n_no_signal, "WEAK_HINT": n_weak, "PROMISING_HYPOTHESIS": n_promising},
        "univariate_results": [{k: v for k, v in r.items() if k != "fn"} for r in classified],
        "top3_robustness": robustness_report,
        "n_promising_after_robustness": n_promising_after_robustness,
        "logistic_regression": {"features": log_names, "weights": w_fit, "bias": b_fit,
                                 "accuracy_discovery": acc_tr, "accuracy_validation": acc_oos,
                                 "majority_baseline_validation": maj_base_oos},
        "decision_tree": {"feature_names": tree_names, "structure_text": tree_lines,
                           "validation_leaf_check": {str(k): {"n": v[1], "rate": v[0]/v[1] if v[1] else None} for k, v in leaf_oos.items()}},
        "retest": {"n_observed": len(retest_all), "breakdown": dict(retest_counts),
                   "n_resolved": len(retest_resolved), "status": retest_status},
        "verdict": verdict,
    }
    with open(os.path.join(OUT_DIR, "thread3_final_v3_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    tb_fields = ["episode_id", "window_id", "true_break_event_id", "sweep_event_id", "timestamp", "direction", "side",
                 "tb_source_tf", "tb_regime_at_event", "tb_structure_trend_at_event", "tb_atr_at_event",
                 "tb_penetration_pips", "tb_penetration_per_atr", "sweep_penetration_per_atr", "sweep_source_tf",
                 "sweep_regime_at_event", "sweep_structure_trend_at_event", "regime_changed_sweep_to_break",
                 "direction_trend_aligned_at_break", "regime_category_same_sweep_to_break",
                 "plus1r_before_minus1r", "continuation_1atr_before_failure", "retest_outcome", "period"]
    with open(os.path.join(OUT_DIR, "thread3_final_v3_at_true_break.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=tb_fields)
        writer.writeheader()
        for r in tb_rows:
            writer.writerow({k: r.get(k) for k in tb_fields})

    print(f"\nOutput salvato in {OUT_DIR}")


def _save_and_exit(tb_rows, audit, n_total, n_resolved, n_ambiguous, n_censored, n_buy, n_sell, verdict):
    results = {
        "generated_at": datetime.now().isoformat(),
        "population": {"n_total_true_break": n_total, "n_resolved": n_resolved, "n_ambiguous": n_ambiguous,
                        "n_censored": n_censored, "n_buy": n_buy, "n_sell": n_sell, **audit},
        "verdict": verdict,
    }
    with open(os.path.join(OUT_DIR, "thread3_final_v3_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
