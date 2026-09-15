"""
NEXUS Causal Research Thread 4 - Retest Quality: HOLD vs FAIL.

Segue Thread 3 Final v3 (commit aa8c637, NO_PROMISING_HYPOTHESIS su TRUE_BREAK
quality). NON riapre: TRUE_BREAK quality feature search, penetration/ATR sweep
hypothesis, age<1h, source_tf=D1.

Domanda: quando un RETEST e' realmente osservato (episodio SH_BMS_RTO con
SWEEP->TRUE_BREAK->RETEST causalmente linkato via episode_sweep_link v3),
esistono feature note ENTRO l'istante del RETEST che predicono HOLD vs FAIL
e/o un outcome economico favorevole?

Population: SOLO linkage v3 (episode_sweep_link + episodeSeq) - stesso
assign_episodes_v3() di Phase C.1/Thread 3, mai il fragile sweeps_by_episode
a campo singolo.

Observation point: AT_RETEST. Ogni feature e' letta dal rigo RETEST stesso
(source_tf/regime/structure_trend/atr/price_at_event/level_price, tutti gia'
noti nell'istante del retest) o dai righi TRUE_BREAK/SWEEP che lo precedono
causalmente (mai dati successivi al retest).

Target primario (RETEST_HOLD_OR_FAIL): STESSA identica definizione gia' usata
nel dataset per costruire 'retest_outcome' in build_structural_dataset_v1.py/
causal_thread3_true_break_quality.py - HOLD=PLUS_1R_FIRST, FAIL=MINUS_1R_FIRST,
calcolati con scan_forward_labels() su (retest.timestamp, retest.price_at_event,
dsign) con R=25 pip fisso, MAI ricalcolata qui con una definizione diversa.

Target secondario 'economico' (PLUS_1R_BEFORE_MINUS_1R): stesso R=25 pip,
stesso horizon, stessa price reference (retest.price_at_event) - in questo
dataset e' LA STESSA identica computazione di scan_forward_labels usata per
HOLD/FAIL (vedi §4 del report) - documentato esplicitamente, non nascosto.
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

OUT_DIR = r"C:\Users\User\ClaudeWork\MAX\results\causal_thread4_retest_quality"
os.makedirs(OUT_DIR, exist_ok=True)

PIP_SIZE = bds.PIP_SIZE
R_PIPS = bds.R_PIPS
MIN_RESOLVED_TOTAL = 50
MIN_SPLIT_RESOLVED = 20
MIN_EFFECT = 0.10
MIN_N_TRAIN = 20   # piu' basso di Thread3 (30) per via del sample retest piu' piccolo, ma
                    # dichiarato ESPLICITAMENTE qui, non nascosto - vedi report; MIN_N_OOS
                    # segue la stessa proporzione dichiarata dal task (split gate=20)
MIN_N_OOS = 15
MIN_N_SIDE = 10
MIN_N_MONTH_DOMINANCE = 0.60
MIN_N_TAG_DOMINANCE = 0.60

wilson_ci = c3.wilson_ci
regime_bucket = c3.regime_bucket
RETEST_LABEL_MAP = bds.RETEST_LABEL_MAP


def dsign_of(direction):
    return 1 if direction == "BUY" else (-1 if direction == "SELL" else 0)


def build_retest_population(all_events, all_links, m1_by_window, window_end_by_id):
    (lifecycle_link, episodes, true_orphans, redundant_after_close,
     true_break_after_close, orphan_reasons) = bds.assign_episodes_v3(all_events, all_links)
    episode_lifecycle = bds.build_episode_lifecycle_index(all_events, lifecycle_link)
    redundant_ids = set((e["window_id"], e["event_id"]) for e in redundant_after_close)
    tbac_ids = set((e["window_id"], e["event_id"]) for e in true_break_after_close)

    n_orphan_any = len(true_orphans)
    n_unexplained = sum(1 for v in orphan_reasons.values() if v == "UNEXPLAINED")

    rows = []
    excluded = Counter()
    for ep_id, ep_info in episodes.items():
        if ep_info.get("closed_by") != "RETEST":
            continue   # niente lifecycle post-close: l'episodio deve essere chiuso DA un retest,
                        # non da un invalidate precedente seguito da un retest tardivo/redundant
        peers = episode_lifecycle.get(ep_id, [])
        tb_list = sorted([p for p in peers if p["event_type"] == "TRUE_BREAK"], key=lambda x: int(x["event_id"]))
        rt_list = sorted([p for p in peers if p["event_type"] == "RETEST"], key=lambda x: int(x["event_id"]))
        if not tb_list or not rt_list:
            excluded["missing_true_break_or_retest"] += 1
            continue
        b = tb_list[0]
        if (b["window_id"], b["event_id"]) in redundant_ids or (b["window_id"], b["event_id"]) in tbac_ids:
            excluded["true_break_redundant_or_after_close"] += 1
            continue
        r0 = rt_list[0]
        # r0 (primo RETEST per event_id) e' garantito essere esattamente l'evento che ha
        # chiuso l'episodio quando closed_by=="RETEST" (RETEST e' gia' un tipo "closing" in
        # assign_episodes_v3: first_close_id = primo RETEST/INVALIDATE per event_id) - nessun
        # retest successivo/tardivo puo' quindi essere selezionato qui.
        win = b["window_id"]
        rows.append({"ep_id": ep_id, "win": win, "b": b, "r0": r0})

    # ev_by_id per lookup sweep (fuori dal loop sopra per efficienza)
    ev_by_id = {(e["window_id"], e["event_id"]): e for e in all_events}

    tb_rows = []
    for item in rows:
        ep_id, win, b, r0 = item["ep_id"], item["win"], item["b"], item["r0"]
        ep_info = episodes[ep_id]
        sweep_ev = ev_by_id.get((win, ep_info["sweep_event_id"]))
        if sweep_ev is None:
            excluded["sweep_event_missing_unexpected"] += 1
            continue

        direction = r0["direction"]
        dsign = dsign_of(direction)

        # --- feature note ENTRO l'istante del RETEST (mai dati successivi) ---
        retest_atr = float(r0["atr_at_event"]) if r0["atr_at_event"] not in (None, "") else None
        retest_dist_pips = abs(float(r0["price_at_event"]) - float(r0["level_price"])) / PIP_SIZE
        retest_dist_per_atr = (retest_dist_pips * PIP_SIZE / retest_atr) if (retest_atr and retest_atr > 0) else None
        retest_trend_aligned = (
            (direction == "BUY" and r0["structure_trend_at_event"] == "UP") or
            (direction == "SELL" and r0["structure_trend_at_event"] == "DOWN")
        )
        regime_changed_break_to_retest = (r0["regime_at_event"] != b["regime_at_event"])

        tb_atr = float(b["atr_at_event"]) if b["atr_at_event"] not in (None, "") else None
        tb_pen_pips = float(b["penetration_pips"])
        tb_pen_per_atr = (tb_pen_pips * PIP_SIZE / tb_atr) if (tb_atr and tb_atr > 0) else None

        sw_atr = float(sweep_ev["atr_at_event"]) if sweep_ev["atr_at_event"] not in (None, "") else None
        sw_pen_pips = float(sweep_ev["penetration_pips"])
        sw_pen_per_atr = (sw_pen_pips * PIP_SIZE / sw_atr) if (sw_atr and sw_atr > 0) else None

        regime_changed_sweep_to_break = (b["regime_at_event"] != sweep_ev["regime_at_event"])

        # --- target primario (HOLD/FAIL) e secondario (PLUS_1R_BEFORE_MINUS_1R) ---
        # STESSA identica chiamata di scan_forward_labels() gia' usata nel dataset per
        # 'retest_outcome' - nessuna ridefinizione, nessun nuovo horizon/price-reference.
        m1_tuple = m1_by_window[win]
        window_end = window_end_by_id[win]
        fwd = bds.scan_forward_labels(m1_tuple, window_end, r0["timestamp"], float(r0["price_at_event"]), dsign, None)
        primary_outcome = RETEST_LABEL_MAP[fwd["plus1r_before_minus1r"]]   # HOLD | FAIL | AMBIGUOUS | CENSORED
        economic_outcome = fwd["plus1r_before_minus1r"]                    # PLUS_1R_FIRST | MINUS_1R_FIRST | AMBIGUOUS_SAME_BAR | CENSORED

        tb_rows.append({
            "episode_id": ep_id, "window_id": win,
            "true_break_event_id": b["event_id"], "retest_event_id": r0["event_id"],
            "sweep_event_id": sweep_ev["event_id"], "timestamp": r0["timestamp"],
            "direction": direction, "side": r0["side"],
            "retest_source_tf": r0["source_tf"], "retest_regime_at_event": r0["regime_at_event"],
            "retest_structure_trend_at_event": r0["structure_trend_at_event"],
            "retest_atr_at_event": retest_atr, "retest_dist_pips": retest_dist_pips,
            "retest_dist_per_atr": retest_dist_per_atr,
            "retest_trend_aligned": retest_trend_aligned,
            "regime_changed_break_to_retest": regime_changed_break_to_retest,
            "tb_source_tf": b["source_tf"], "tb_regime_at_event": b["regime_at_event"],
            "tb_structure_trend_at_event": b["structure_trend_at_event"],
            "tb_atr_at_event": tb_atr, "tb_penetration_pips": tb_pen_pips, "tb_penetration_per_atr": tb_pen_per_atr,
            "sweep_source_tf": sweep_ev["source_tf"], "sweep_regime_at_event": sweep_ev["regime_at_event"],
            "sweep_structure_trend_at_event": sweep_ev["structure_trend_at_event"],
            "sweep_penetration_per_atr": sw_pen_per_atr,
            "regime_changed_sweep_to_break": regime_changed_sweep_to_break,
            "primary_outcome": primary_outcome, "economic_outcome": economic_outcome,
            "period": "DISCOVERY" if win in c3.DISCOVERY_WINDOWS else "VALIDATION",
        })

    audit = {
        "orphan_any_type": n_orphan_any, "unexplained_orphan": n_unexplained,
        "excluded_reasons": dict(excluded),
    }
    return tb_rows, audit


def rate_of(subset, field="primary_outcome", positive="HOLD"):
    n = len(subset)
    k = sum(1 for r in subset if r[field] == positive)
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

    tb_rows, audit = build_retest_population(all_events, all_links, m1_by_window, window_end_by_id)

    print("=== 1. POPULATION (v3, episode_sweep_link, SWEEP->TRUE_BREAK->RETEST) ===")
    print(f"Orphan (qualunque tipo): {audit['orphan_any_type']}  (atteso: 0)")
    print(f"Unexplained orphan: {audit['unexplained_orphan']}  (atteso: 0)")
    print(f"Esclusioni: {dict(audit['excluded_reasons'])}")
    print(f"RETEST totali (episodi chiusi DA un RETEST, non post-invalidate): {len(tb_rows)}")

    n_hold = sum(1 for r in tb_rows if r["primary_outcome"] == "HOLD")
    n_fail = sum(1 for r in tb_rows if r["primary_outcome"] == "FAIL")
    n_ambig = sum(1 for r in tb_rows if r["primary_outcome"] == "AMBIGUOUS")
    n_censored = sum(1 for r in tb_rows if r["primary_outcome"] == "CENSORED")
    resolved = [r for r in tb_rows if r["primary_outcome"] in ("HOLD", "FAIL")]
    n_resolved = len(resolved)
    train = [r for r in resolved if r["period"] == "DISCOVERY"]
    oos = [r for r in resolved if r["period"] == "VALIDATION"]

    print(f"\n=== 3. SAMPLE GATE ===")
    print(f"RETEST totali: {len(tb_rows)}")
    print(f"HOLD: {n_hold}  FAIL: {n_fail}  AMBIGUOUS: {n_ambig}  CENSORED: {n_censored}")
    print(f"RESOLVED (HOLD+FAIL): {n_resolved}")
    print(f"DISCOVERY resolved: {len(train)}   VALIDATION resolved: {len(oos)}")

    if n_resolved < MIN_RESOLVED_TOTAL:
        verdict = "HOLD_INSUFFICIENT_RETEST_SAMPLE"
        print(f"\n=== VERDICT: {verdict} ===")
        _save_minimal(tb_rows, audit, n_hold, n_fail, n_ambig, n_censored, n_resolved, len(train), len(oos), verdict)
        return

    allow_promotion = True
    if len(train) < MIN_SPLIT_RESOLVED or len(oos) < MIN_SPLIT_RESOLVED:
        allow_promotion = False
        print(f"\nUno split ha meno di {MIN_SPLIT_RESOLVED} risolti - SOLO descrittiva, nessuna promozione consentita.")

    # ============================================================
    # 4. Target primario - definizione documentata
    # ============================================================
    print(f"\n=== 4. DEFINIZIONE HOLD/FAIL (invariata, dal dataset esistente) ===")
    print("HOLD = PLUS_1R_FIRST, FAIL = MINUS_1R_FIRST - da scan_forward_labels(m1, window_end, "
          "retest.timestamp, retest.price_at_event, dsign(direction), atr=None), R=25 pip fisso, "
          "stesso horizon (5 giorni) e stessa price reference gia' usati in tutto il progetto. "
          "Nessuna ridefinizione qui.")

    # ============================================================
    # 5. Target economico secondario - verifica identita'
    # ============================================================
    identical = all(
        (r["primary_outcome"] == "HOLD") == (r["economic_outcome"] == "PLUS_1R_FIRST") and
        (r["primary_outcome"] == "FAIL") == (r["economic_outcome"] == "MINUS_1R_FIRST")
        for r in tb_rows
    )
    print(f"\n=== 5. TARGET ECONOMICO SECONDARIO ===")
    print(f"PLUS_1R_BEFORE_MINUS_1R e' calcolato con la STESSA chiamata scan_forward_labels() "
          f"usata per HOLD/FAIL in questo dataset (stesso R, stesso horizon, stessa price reference).")
    print(f"Identita' empirica HOLD<=>PLUS_1R_FIRST e FAIL<=>MINUS_1R_FIRST verificata su tutte le "
          f"{len(tb_rows)} righe: {identical}")
    print("Conseguenza: in QUESTO dataset il controllo di coerenza strutturale/economico (§11) e' "
          "automaticamente soddisfatto per costruzione - non e' possibile che una feature predica "
          "HOLD senza predire anche PLUS_1R_FIRST, perche' sono la stessa misura. Questo NON e' stato "
          "assunto: e' stato verificato riga per riga sopra.")

    k_all, n_all, base_all = rate_of(resolved)
    lo_all, hi_all = wilson_ci(k_all, n_all)
    k_tr, n_tr, base_tr = rate_of(train)
    k_oos, n_oos_, base_oos = rate_of(oos)
    print(f"\n=== BASE RATE (HOLD) ===")
    print(f"Totale: {k_all}/{n_all} = {base_all:.3f} CI95=[{lo_all:.3f},{hi_all:.3f}]")
    print(f"DISCOVERY: {k_tr}/{n_tr}={base_tr:.3f}   VALIDATION: {k_oos}/{n_oos_}={base_oos:.3f}")
    print(f"Ambiguity rate: {n_ambig}/{len(tb_rows)} = {n_ambig/len(tb_rows):.1%}" if tb_rows else "")

    # ============================================================
    # 6+7. Feature set congelato, univariata (solo se train/oos non vuoti)
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

    retest_dist_atr_q = quartiles_train(lambda r: r["retest_dist_per_atr"])
    tb_pen_atr_q = quartiles_train(lambda r: r["tb_penetration_per_atr"])
    sweep_pen_atr_q = quartiles_train(lambda r: r["sweep_penetration_per_atr"])

    specs = [
        ("direction", lambda r: r["direction"]),
        ("side", lambda r: r["side"]),
        ("retest_source_tf", lambda r: r["retest_source_tf"]),
        ("retest_regime_at_event", lambda r: r["retest_regime_at_event"]),
        ("retest_structure_trend_at_event", lambda r: r["retest_structure_trend_at_event"]),
        ("retest_trend_aligned", lambda r: r["retest_trend_aligned"]),
        ("retest_dist_per_atr_quartile", lambda r: qbucket(r["retest_dist_per_atr"], retest_dist_atr_q)),
        ("tb_source_tf", lambda r: r["tb_source_tf"]),
        ("tb_regime_at_event", lambda r: r["tb_regime_at_event"]),
        ("tb_structure_trend_at_event", lambda r: r["tb_structure_trend_at_event"]),
        ("tb_penetration_per_atr_quartile", lambda r: qbucket(r["tb_penetration_per_atr"], tb_pen_atr_q)),
        ("sweep_source_tf", lambda r: r["sweep_source_tf"]),
        ("sweep_regime_at_event", lambda r: r["sweep_regime_at_event"]),
        ("sweep_structure_trend_at_event", lambda r: r["sweep_structure_trend_at_event"]),
        ("sweep_penetration_per_atr_quartile", lambda r: qbucket(r["sweep_penetration_per_atr"], sweep_pen_atr_q)),
        ("regime_changed_sweep_to_break", lambda r: r["regime_changed_sweep_to_break"]),
        ("regime_changed_break_to_retest", lambda r: r["regime_changed_break_to_retest"]),
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
            if nt >= 8 and no_ >= 8 and not math.isnan(pt) and not math.isnan(po):
                same_dir = "SI" if (up_tr > 0) == (up_oos > 0) else "NO"
            side_counts = Counter(r["side"] for r in tr_b)
            month_counts = Counter(r["timestamp"].strftime("%Y-%m") for r in tr_b)
            top_tag_frac = (side_counts.most_common(1)[0][1] / nt) if nt and side_counts else 0
            top_month_frac = (month_counts.most_common(1)[0][1] / nt) if nt and month_counts else 0
            results.append({
                "feature": name, "bucket": str(bkt), "n_train": nt, "rate_train": pt, "ci95_train": [lo, hi],
                "uplift_train": up_tr, "n_oos": no_, "rate_oos": po, "uplift_oos": up_oos,
                "same_direction": same_dir, "top_levelTag_frac_train": top_tag_frac,
                "top_month_frac_train": top_month_frac, "fn": fn,
            })
        return results

    all_univariate = []
    for name, fn in specs:
        all_univariate.extend(bucket_report(name, fn))
    n_hyp = len(all_univariate)
    print(f"\n=== ANALISI UNIVARIATA ({n_hyp} bucket/ipotesi, feature set congelato) ===")
    for r in all_univariate:
        print(f"  {r['feature']:34s}={r['bucket']:14s} TRAIN n={r['n_train']:4d} rate={r['rate_train']:.3f} "
              f"uplift={r['uplift_train']:+.3f}  OOS n={r['n_oos']:4d} rate={r['rate_oos']:.3f} uplift={r['uplift_oos']:+.3f}  "
              f"stessa_dir={r['same_direction']}  top_tag={r['top_levelTag_frac_train']:.2f}  top_month={r['top_month_frac_train']:.2f}")

    # ============================================================
    # 9+10. Robustness e classificazione
    # ============================================================
    classified = []
    for r in all_univariate:
        if not allow_promotion:
            cls, reason = "NO_SIGNAL", "split troppo piccolo per promozione (solo descrittiva)"
        elif r["n_train"] < MIN_N_TRAIN or r["n_oos"] < MIN_N_OOS:
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
            cls, reason = "PROMISING_HYPOTHESIS", "effetto grande, direzione coerente, campione adeguato, non concentrato"
        classified.append({**r, "classification": cls, "reason": reason})

    n_no_signal = sum(1 for c in classified if c["classification"] == "NO_SIGNAL")
    n_weak = sum(1 for c in classified if c["classification"] == "WEAK_HINT")
    n_promising = sum(1 for c in classified if c["classification"] == "PROMISING_HYPOTHESIS")
    print(f"\n=== CLASSIFICAZIONE ({n_hyp} ipotesi) ===  NO_SIGNAL={n_no_signal}  WEAK_HINT={n_weak}  PROMISING_HYPOTHESIS={n_promising}")

    # top 3 per |uplift_train| tra WEAK_HINT/PROMISING, con robustness completa
    candidates = [c for c in classified if c["classification"] in ("WEAK_HINT", "PROMISING_HYPOTHESIS")]
    candidates_sorted = sorted(candidates, key=lambda c: abs(c["uplift_train"]), reverse=True)
    top3 = candidates_sorted[:3]
    print(f"\n=== ROBUSTNESS SUI TOP {len(top3)} PATTERN ===")
    robustness_report = []
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
        dominated = (
            nb < MIN_N_SIDE or ns < MIN_N_SIDE or
            top_month_all >= MIN_N_MONTH_DOMINANCE or top_tag_all >= MIN_N_TAG_DOMINANCE or
            len(matching) < MIN_N_TRAIN
        )
        # economic consistency (§11) - per definizione identico qui, ma verificato esplicitamente
        k_econ, n_econ, econ_rate = rate_of(matching, field="economic_outcome", positive="PLUS_1R_FIRST")
        entry = {
            "feature": c["feature"], "bucket": bucket, "classification": c["classification"],
            "n_total": len(matching),
            "discovery_rate": c["rate_train"], "discovery_uplift": c["uplift_train"],
            "validation_rate": c["rate_oos"], "validation_uplift": c["uplift_oos"],
            "first_half_n": nf, "first_half_rate": pf, "second_half_n": nsec, "second_half_rate": psec,
            "buy_n": nb, "buy_rate": pb, "sell_n": ns, "sell_rate": ps,
            "top_month_frac": top_month_all, "top_tag_frac": top_tag_all,
            "single_factor_dominated": dominated,
            "economic_rate_plus1r": econ_rate,
            "structural_only_hint": False,  # in questo dataset HOLD==PLUS_1R_FIRST per costruzione (vedi §5)
            "final_after_robustness": (
                "REJECTED_SINGLE_FACTOR_DOMINATED" if (dominated and c["classification"] == "PROMISING_HYPOTHESIS")
                else c["classification"]
            ),
        }
        robustness_report.append(entry)
        print(f"  {c['feature']}={bucket} [{c['classification']}]: "
              f"DISC={c['rate_train']:.3f}(n={c['n_train']}) VALID={c['rate_oos']:.3f}(n={c['n_oos']}) "
              f"1a_meta={pf:.3f}(n={nf}) 2a_meta={psec:.3f}(n={nsec}) "
              f"BUY={pb:.3f}(n={nb}) SELL={ps:.3f}(n={ns}) "
              f"top_month={top_month_all:.2f} top_tag={top_tag_all:.2f} dominated={dominated} "
              f"econ_rate(PLUS_1R_FIRST)={econ_rate:.3f}")

    n_promising_final = sum(1 for e in robustness_report if e["final_after_robustness"] == "PROMISING_HYPOTHESIS")

    # ============================================================
    # 8. Logistic + shallow tree (identici in metodologia a Thread 3)
    # ============================================================
    def logf(r):
        d = r["retest_dist_per_atr"] or 0.0
        tbp = r["tb_penetration_per_atr"] or 0.0
        aligned = 1.0 if r["retest_trend_aligned"] else 0.0
        changed = 1.0 if r["regime_changed_break_to_retest"] else 0.0
        return [d, tbp, aligned, changed]

    Xtr = [logf(r) for r in train]
    ytr = [1 if r["primary_outcome"] == "HOLD" else 0 for r in train]
    Xoos = [logf(r) for r in oos]
    yoos = [1 if r["primary_outcome"] == "HOLD" else 0 for r in oos]

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
    log_names = ["retest_dist_per_atr", "tb_penetration_per_atr", "retest_trend_aligned", "regime_changed_break_to_retest"]
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
                if len(ly) < 10 or len(ry) < 10:
                    continue
                g = (len(ly) * gini(ly) + len(ry) * gini(ry)) / n
                if best is None or g < best[0]:
                    best = (g, j, t)
        return best

    def build_tree(X, y, depth, max_depth=2):
        n = len(y)
        rate = sum(y) / n if n else 0.0
        node = {"n": n, "rate": rate, "leaf": True}
        if depth >= max_depth or n < 20:
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

    tree_names = log_names
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
    # Verdict
    # ============================================================
    if not allow_promotion:
        verdict = "HOLD_RETEST_VALIDATION_SAMPLE_TOO_SMALL"
    elif n_promising_final > 0:
        verdict = "PROMISING_HYPOTHESIS_FOUND"
    else:
        verdict = "NO_PROMISING_HYPOTHESIS"
    print(f"\n=== VERDICT: {verdict} ===")

    results = {
        "generated_at": datetime.now().isoformat(),
        "linkage": "v3 (episode_sweep_link, causale)",
        "population": {
            "n_retest_total": len(tb_rows), "n_hold": n_hold, "n_fail": n_fail,
            "n_ambiguous": n_ambig, "n_censored": n_censored, "n_resolved": n_resolved,
            "n_discovery_resolved": len(train), "n_validation_resolved": len(oos),
            **audit,
        },
        "hold_fail_definition": "HOLD=PLUS_1R_FIRST, FAIL=MINUS_1R_FIRST via scan_forward_labels su retest.timestamp/price_at_event, R=25pip, invariata dal dataset esistente",
        "economic_target_identical_to_primary": identical,
        "base_rate": {"all": base_all, "discovery": base_tr, "validation": base_oos, "ci95_all": [lo_all, hi_all]},
        "n_hypotheses_tested": n_hyp,
        "classification_summary": {"NO_SIGNAL": n_no_signal, "WEAK_HINT": n_weak, "PROMISING_HYPOTHESIS": n_promising},
        "univariate_results": [{k: v for k, v in r.items() if k != "fn"} for r in classified],
        "top3_robustness": robustness_report,
        "n_promising_after_robustness": n_promising_final,
        "logistic_regression": {"features": log_names, "weights": w_fit, "bias": b_fit,
                                 "accuracy_discovery": acc_tr, "accuracy_validation": acc_oos,
                                 "majority_baseline_validation": maj_base_oos},
        "decision_tree": {"feature_names": tree_names, "structure_text": tree_lines,
                           "validation_leaf_check": {str(k): {"n": v[1], "rate": v[0]/v[1] if v[1] else None} for k, v in leaf_oos.items()}},
        "verdict": verdict,
    }
    with open(os.path.join(OUT_DIR, "thread4_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    tb_fields = list(tb_rows[0].keys()) if tb_rows else []
    with open(os.path.join(OUT_DIR, "thread4_at_retest.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=tb_fields)
        writer.writeheader()
        for r in tb_rows:
            writer.writerow(r)

    print(f"\nOutput salvato in {OUT_DIR}")


def _save_minimal(tb_rows, audit, n_hold, n_fail, n_ambig, n_censored, n_resolved, n_disc, n_valid, verdict):
    results = {
        "generated_at": datetime.now().isoformat(),
        "population": {"n_retest_total": len(tb_rows), "n_hold": n_hold, "n_fail": n_fail,
                        "n_ambiguous": n_ambig, "n_censored": n_censored, "n_resolved": n_resolved,
                        "n_discovery_resolved": n_disc, "n_validation_resolved": n_valid, **audit},
        "verdict": verdict,
    }
    with open(os.path.join(OUT_DIR, "thread4_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)


if __name__ == "__main__":
    main()
