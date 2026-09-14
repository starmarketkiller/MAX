"""
NEXUS Causal Research Thread 2 - Structural Causal Experiment 1: Discovery.

Domanda: alcune feature note AL MOMENTO dello SWEEP predicono
TRUE_BREAK_OBSERVED vs INVALIDATED_NO_BREAK?

Discovery, non ottimizzazione. Nessuna strategia implementata qui.
Riusa la logica di linkage episodio gia' validata in
build_structural_dataset_v1.py (import diretto, nessuna riscrittura).

Puro standard library (nessun pandas/numpy/sklearn/scipy disponibili).
"""
import csv
import json
import math
import os
import random
from collections import defaultdict, Counter
from datetime import datetime

import build_structural_dataset_v1 as bds

OUT_DIR = r"C:\Users\User\ClaudeWork\MAX\results\structural_causal_experiment_1"
os.makedirs(OUT_DIR, exist_ok=True)

TRAIN_OOS_SPLIT_DATE = datetime(2026, 6, 1)  # meta' di w3 (2026-05-01 -> 2026-07-01)
PIP_SIZE = bds.PIP_SIZE


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((center - margin) / denom, (center + margin) / denom)


def main():
    all_events, ev_by_window, m1_by_window = bds.load_all()
    lifecycle_link, episodes, true_orphans, redundant_after_close, true_break_after_close = bds.assign_episodes(all_events)
    episode_lifecycle = bds.build_episode_lifecycle_index(all_events, lifecycle_link)

    redundant_ids = set(e["event_id"] for e in redundant_after_close)
    true_break_after_close_ids = set(e["event_id"] for e in true_break_after_close)

    sweeps_by_episode = {e["structural_episode_id"]: e for e in all_events if e["event_type"] == "SWEEP"}

    # ============================================================
    # 1. Population: episodi con lifecycle osservabile (esclude NO_LIFECYCLE_OBSERVED)
    # ============================================================
    total_sh_bms_episodes = len(episodes)
    no_lifecycle_count = 0
    excluded_redundant_outcome = []
    excluded_ambiguous_both = []
    valid_population = []

    for ep_id in episodes:
        peers = episode_lifecycle.get(ep_id, [])
        tb = sorted([p for p in peers if p["event_type"] == "TRUE_BREAK"], key=lambda x: int(x["event_id"]))
        inv_swept = sorted([p for p in peers if p["event_type"] == "INVALIDATE" and p["state_before"] == "SWEPT"],
                            key=lambda x: int(x["event_id"]))

        if not tb and not inv_swept:
            no_lifecycle_count += 1
            continue

        # Determinante dell'esito = il PRIMO evento (per event_id) che stabilisce l'esito.
        # Punto 7: se la determinante e' essa stessa "redundant_after_close" o
        # "true_break_after_close", l'episodio e' escluso dalla population valida -
        # il suo esito non e' affidabile (l'evento e' arrivato quando l'episodio era
        # gia' chiuso, sintomo del desync multi-TF-pass documentato nell'audit linkage).
        if tb:
            determinant = tb[0]
            outcome = "TRUE_BREAK_OBSERVED"
        else:
            determinant = inv_swept[0]
            outcome = "INVALIDATED_NO_BREAK"

        if determinant["event_id"] in redundant_ids or determinant["event_id"] in true_break_after_close_ids:
            excluded_redundant_outcome.append((ep_id, outcome, determinant["event_id"]))
            continue

        sweep_row = sweeps_by_episode.get(ep_id)
        if sweep_row is None:
            continue  # non dovrebbe accadere: ogni episodio ha per costruzione un proprio SWEEP

        valid_population.append({"episode_id": ep_id, "sweep": sweep_row, "outcome": outcome,
                                  "window_id": sweep_row["window_id"]})

    n_excluded_no_lifecycle = no_lifecycle_count
    n_excluded_redundant = len(excluded_redundant_outcome)
    n_valid = len(valid_population)

    print("=== POPULATION ===")
    print(f"Episodi SH_BMS_RTO totali: {total_sh_bms_episodes}")
    print(f"Esclusi NO_LIFECYCLE_OBSERVED: {n_excluded_no_lifecycle}")
    print(f"Esclusi per esito determinato da evento redundant_after_close/true_break_after_close: {n_excluded_redundant}")
    print(f"Population valida (TRUE_BREAK_OBSERVED vs INVALIDATED_NO_BREAK, esito affidabile): {n_valid}")

    # ============================================================
    # 2. Causal safety check esplicito (punto 3/7)
    # ============================================================
    print("\n=== CAUSAL SAFETY CHECK: observed_by / observation_count ===")
    print("Verificato nel codice (NXS_StructuralResearchLog.mqh, righe 241-246): "
          "observation_count e osserved_by vengono MUTATI (incrementati/estesi) ogni volta che un "
          "consumer/pass successivo osserva la stessa riga SWEEP, fino a OnDeinit (fine run). "
          "L'export CSV cattura lo stato FINALE, non quello al momento della creazione. "
          "ESCLUSI da ogni feature causale in questo esperimento. "
          "Il campo 'consumer' (chi ha creato l'evento) e' invece impostato UNA SOLA VOLTA alla "
          "creazione e mai piu' toccato - ammesso come feature categorica.")

    # ============================================================
    # 3. Feature extraction (SOLO campi noti al momento dello SWEEP)
    # ============================================================
    def features(row):
        s = row["sweep"]
        atr = float(s["atr_at_event"]) if s["atr_at_event"] not in (None, "") else None
        pen_pips = float(s["penetration_pips"])
        pen_price = pen_pips * PIP_SIZE
        pen_per_atr = (pen_price / atr) if (atr and atr > 0) else None
        age = float(s["age_seconds"]) if s["age_seconds"] not in (None, "") else -1
        age_valid = age >= 0
        return {
            "side": s["side"], "source_tf": s["source_tf"], "direction": s["direction"],
            "regime_at_event": s["regime_at_event"], "structure_trend_at_event": s["structure_trend_at_event"],
            "consumer": s["consumer"], "penetration_pips": pen_pips, "atr_at_event": atr,
            "penetration_per_atr": pen_per_atr, "age_seconds": age if age_valid else None,
            "age_valid": age_valid,
        }

    for row in valid_population:
        row["f"] = features(row)
        row["timestamp"] = row["sweep"]["timestamp"]

    # ============================================================
    # 4. Split temporale (dichiarato PRIMA di guardare risultati per-feature)
    # ============================================================
    train = [r for r in valid_population if r["window_id"] in ("w1", "w2") or
             (r["window_id"] == "w3" and r["timestamp"] < TRAIN_OOS_SPLIT_DATE)]
    oos = [r for r in valid_population if (r["window_id"] == "w3" and r["timestamp"] >= TRAIN_OOS_SPLIT_DATE) or
           r["window_id"] == "w4"]
    print(f"\n=== SPLIT TEMPORALE ===")
    print(f"TRAIN (w1+w2+w3 fino al {TRAIN_OOS_SPLIT_DATE.date()}): n={len(train)}")
    print(f"OOS (w3 dal {TRAIN_OOS_SPLIT_DATE.date()} + w4): n={len(oos)}")

    def base_rate_of(subset):
        n = len(subset)
        k = sum(1 for r in subset if r["outcome"] == "TRUE_BREAK_OBSERVED")
        return k, n, (k / n if n else float("nan"))

    k_all, n_all, base_all = base_rate_of(valid_population)
    k_tr, n_tr, base_tr = base_rate_of(train)
    k_oos, n_oos, base_oos = base_rate_of(oos)
    lo_all, hi_all = wilson_ci(k_all, n_all)
    print(f"\n=== BASE RATE (TRUE_BREAK_OBSERVED) ===")
    print(f"Totale: {k_all}/{n_all} = {base_all:.3f}  CI95=[{lo_all:.3f},{hi_all:.3f}]")
    print(f"TRAIN: {k_tr}/{n_tr} = {base_tr:.3f}    OOS: {k_oos}/{n_oos} = {base_oos:.3f}")

    # ============================================================
    # 5. Analisi univariata (bucket dichiarati PRIMA su TRAIN, poi verificati su OOS)
    # ============================================================
    def bucket_report(name, bucket_fn, subset_train, subset_oos, base_tr, base_oos):
        results = []
        buckets_seen = set()
        for r in subset_train:
            b = bucket_fn(r["f"])
            if b is not None:
                buckets_seen.add(b)
        for b in sorted(buckets_seen, key=str):
            tr_b = [r for r in subset_train if bucket_fn(r["f"]) == b]
            oos_b = [r for r in subset_oos if bucket_fn(r["f"]) == b]
            kt, nt, pt = base_rate_of(tr_b)
            ko, no_, po = base_rate_of(oos_b)
            lo, hi = wilson_ci(kt, nt) if nt else (float("nan"), float("nan"))
            uplift_tr = (pt - base_tr) if nt else float("nan")
            uplift_oos = (po - base_oos) if no_ else float("nan")
            same_dir = "N/A"
            if nt >= 10 and no_ >= 10 and not math.isnan(pt) and not math.isnan(po):
                same_dir = "SI" if (uplift_tr > 0) == (uplift_oos > 0) else "NO"
            results.append({
                "feature": name, "bucket": str(b), "n_train": nt, "rate_train": pt,
                "ci95_train": [lo, hi], "uplift_train": uplift_tr,
                "n_oos": no_, "rate_oos": po, "uplift_oos": uplift_oos, "same_direction": same_dir,
            })
        return results

    univariate_specs = [
        ("side", lambda f: f["side"]),
        ("source_tf", lambda f: f["source_tf"]),
        ("direction", lambda f: f["direction"]),
        ("regime_at_event", lambda f: f["regime_at_event"]),
        ("structure_trend_at_event", lambda f: f["structure_trend_at_event"]),
        ("consumer", lambda f: f["consumer"]),
        ("penetration_pips_quartile", lambda f: _quartile_bucket(f["penetration_pips"], PEN_Q)),
        ("penetration_per_atr_quartile", lambda f: _quartile_bucket(f["penetration_per_atr"], PEN_ATR_Q) if f["penetration_per_atr"] is not None else None),
        ("age_seconds_bucket", lambda f: _age_bucket(f["age_seconds"]) if f["age_valid"] else "NOT_CAUSALLY_VALID"),
    ]

    # quartili calcolati SOLO su TRAIN (mai su OOS, per non far trapelare informazione dal futuro)
    pen_vals_train = sorted(r["f"]["penetration_pips"] for r in train)
    PEN_Q = _quartiles(pen_vals_train)
    pen_atr_vals_train = sorted(r["f"]["penetration_per_atr"] for r in train if r["f"]["penetration_per_atr"] is not None)
    PEN_ATR_Q = _quartiles(pen_atr_vals_train)

    all_univariate = []
    n_hypotheses = 0
    for name, fn in univariate_specs:
        res = bucket_report(name, fn, train, oos, base_tr, base_oos)
        all_univariate.extend(res)
        n_hypotheses += len(res)

    print(f"\n=== ANALISI UNIVARIATA ({n_hypotheses} bucket/ipotesi testate in totale - multiple comparison) ===")
    for r in all_univariate:
        print(f"  {r['feature']:32s} = {r['bucket']:16s} "
              f"TRAIN n={r['n_train']:4d} rate={r['rate_train']:.3f} uplift={r['uplift_train']:+.3f} "
              f"CI95=[{r['ci95_train'][0]:.3f},{r['ci95_train'][1]:.3f}]  "
              f"OOS n={r['n_oos']:4d} rate={r['rate_oos']:.3f} uplift={r['uplift_oos']:+.3f}  "
              f"stessa_direzione={r['same_direction']}")

    # ============================================================
    # 6. Classificazione anti-data-mining
    # ============================================================
    MIN_N_TRAIN = 30
    MIN_N_OOS = 20
    MIN_EFFECT = 0.10  # 10 punti percentuali di uplift assoluto, soglia dichiarata

    classified = []
    for r in all_univariate:
        if r["n_train"] < MIN_N_TRAIN or r["n_oos"] < MIN_N_OOS:
            cls = "NO_SIGNAL"
            reason = f"campione insufficiente (train={r['n_train']}, oos={r['n_oos']}, soglie={MIN_N_TRAIN}/{MIN_N_OOS})"
        elif r["same_direction"] != "SI":
            cls = "NO_SIGNAL"
            reason = "direzione non coerente train/oos o non misurabile"
        elif abs(r["uplift_train"]) < MIN_EFFECT or abs(r["uplift_oos"]) < MIN_EFFECT:
            cls = "WEAK_HINT"
            reason = f"direzione coerente ma effetto sotto soglia {MIN_EFFECT:.2f} in almeno un set"
        else:
            cls = "PROMISING_HYPOTHESIS"
            reason = "effetto grande, direzione coerente, campione sufficiente"
        classified.append({**r, "classification": cls, "reason": reason})

    n_no_signal = sum(1 for c in classified if c["classification"] == "NO_SIGNAL")
    n_weak = sum(1 for c in classified if c["classification"] == "WEAK_HINT")
    n_promising = sum(1 for c in classified if c["classification"] == "PROMISING_HYPOTHESIS")
    print(f"\n=== CLASSIFICAZIONE ({n_hypotheses} ipotesi testate) ===")
    print(f"NO_SIGNAL: {n_no_signal}   WEAK_HINT: {n_weak}   PROMISING_HYPOTHESIS: {n_promising}")
    promising = [c for c in classified if c["classification"] == "PROMISING_HYPOTHESIS"]
    weak = [c for c in classified if c["classification"] == "WEAK_HINT"]
    for c in promising:
        print(f"  PROMISING: {c['feature']}={c['bucket']}  train_uplift={c['uplift_train']:+.3f} oos_uplift={c['uplift_oos']:+.3f}")

    # ============================================================
    # 7. Logistic regression minimale (gradient descent, feature causali numeriche)
    # ============================================================
    def logistic_features(f):
        pen_atr = f["penetration_per_atr"] if f["penetration_per_atr"] is not None else 0.0
        age = f["age_seconds"] if f["age_valid"] and f["age_seconds"] is not None else 0.0
        atr = f["atr_at_event"] if f["atr_at_event"] else 0.0
        trend = {"UP": 1.0, "DOWN": -1.0, "RANGE": 0.0}.get(f["structure_trend_at_event"], 0.0)
        return [pen_atr, age / 3600.0, atr, trend]  # age in ore per scala comparabile

    def standardize(train_X):
        n = len(train_X)
        p = len(train_X[0])
        means = [sum(row[j] for row in train_X) / n for j in range(p)]
        stds = [max(1e-9, math.sqrt(sum((row[j] - means[j]) ** 2 for row in train_X) / n)) for j in range(p)]
        return means, stds

    def apply_std(X, means, stds):
        return [[(row[j] - means[j]) / stds[j] for j in range(len(row))] for row in X]

    X_train_raw = [logistic_features(r["f"]) for r in train]
    y_train = [1 if r["outcome"] == "TRUE_BREAK_OBSERVED" else 0 for r in train]
    X_oos_raw = [logistic_features(r["f"]) for r in oos]
    y_oos = [1 if r["outcome"] == "TRUE_BREAK_OBSERVED" else 0 for r in oos]

    means, stds = standardize(X_train_raw)
    X_train = apply_std(X_train_raw, means, stds)
    X_oos = apply_std(X_oos_raw, means, stds)

    def sigmoid(z):
        if z < -30:
            return 0.0
        if z > 30:
            return 1.0
        return 1.0 / (1.0 + math.exp(-z))

    def fit_logistic(X, y, lr=0.05, epochs=2000, l2=0.01):
        n, p = len(X), len(X[0])
        w = [0.0] * p
        b = 0.0
        for _ in range(epochs):
            grad_w = [0.0] * p
            grad_b = 0.0
            for i in range(n):
                z = b + sum(w[j] * X[i][j] for j in range(p))
                pred = sigmoid(z)
                err = pred - y[i]
                for j in range(p):
                    grad_w[j] += err * X[i][j]
                grad_b += err
            for j in range(p):
                w[j] -= lr * (grad_w[j] / n + l2 * w[j])
            b -= lr * (grad_b / n)
        return w, b

    def eval_logistic(X, y, w, b):
        correct = 0
        preds = []
        for i in range(len(X)):
            z = b + sum(w[j] * X[i][j] for j in range(len(w)))
            p = sigmoid(z)
            preds.append(p)
            pred_label = 1 if p >= 0.5 else 0
            correct += (pred_label == y[i])
        acc = correct / len(X) if X else float("nan")
        return acc, preds

    log_feature_names = ["penetration_per_atr", "age_hours", "atr_at_event", "structure_trend(+1up/-1down)"]
    w_fit, b_fit = fit_logistic(X_train, y_train)
    acc_train, _ = eval_logistic(X_train, y_train, w_fit, b_fit)
    acc_oos, _ = eval_logistic(X_oos, y_oos, w_fit, b_fit)
    majority_baseline_oos = max(base_oos, 1 - base_oos) if not math.isnan(base_oos) else float("nan")

    print(f"\n=== LOGISTIC REGRESSION (discovery, non un modello di produzione) ===")
    print(f"Feature: {log_feature_names}")
    print(f"Pesi (su feature standardizzate): {[round(x, 3) for x in w_fit]}  bias={round(b_fit, 3)}")
    print(f"Accuracy TRAIN: {acc_train:.3f}   Accuracy OOS: {acc_oos:.3f}   Baseline maggioranza OOS: {majority_baseline_oos:.3f}")

    # ============================================================
    # 8. Albero decisionale shallow (max depth 2), Gini, split greedy
    # ============================================================
    def gini(y):
        n = len(y)
        if n == 0:
            return 0.0
        p1 = sum(y) / n
        return 1 - p1 * p1 - (1 - p1) * (1 - p1)

    def best_split(X, y, feature_idx_range):
        n = len(y)
        best = None
        for j in feature_idx_range:
            vals = sorted(set(row[j] for row in X))
            if len(vals) < 2:
                continue
            thresholds = [(vals[i] + vals[i + 1]) / 2 for i in range(len(vals) - 1)]
            for t in thresholds:
                left_y = [y[i] for i in range(n) if X[i][j] <= t]
                right_y = [y[i] for i in range(n) if X[i][j] > t]
                if len(left_y) < 10 or len(right_y) < 10:
                    continue
                g = (len(left_y) * gini(left_y) + len(right_y) * gini(right_y)) / n
                if best is None or g < best[0]:
                    best = (g, j, t)
        return best

    def build_tree(X, y, depth, max_depth):
        n = len(y)
        rate = sum(y) / n if n else 0.0
        node = {"n": n, "rate": rate}
        if depth >= max_depth or n < 20:
            node["leaf"] = True
            return node
        b = best_split(X, y, range(len(X[0])))
        if b is None:
            node["leaf"] = True
            return node
        g, j, t = b
        left_idx = [i for i in range(n) if X[i][j] <= t]
        right_idx = [i for i in range(n) if X[i][j] > t]
        node["leaf"] = False
        node["feature_idx"] = j
        node["threshold"] = t
        node["left"] = build_tree([X[i] for i in left_idx], [y[i] for i in left_idx], depth + 1, max_depth)
        node["right"] = build_tree([X[i] for i in right_idx], [y[i] for i in right_idx], depth + 1, max_depth)
        return node

    def print_tree(node, feature_names, indent=""):
        lines = []
        if node["leaf"]:
            lines.append(f"{indent}LEAF n={node['n']} rate={node['rate']:.3f}")
        else:
            fname = feature_names[node["feature_idx"]]
            lines.append(f"{indent}IF {fname} <= {node['threshold']:.3f} (n={node['n']}, rate={node['rate']:.3f}):")
            lines.extend(print_tree(node["left"], feature_names, indent + "  "))
            lines.append(f"{indent}ELSE:")
            lines.extend(print_tree(node["right"], feature_names, indent + "  "))
        return lines

    def apply_tree(node, x):
        if node["leaf"]:
            return node["rate"], node["n"]
        j, t = node["feature_idx"], node["threshold"]
        if x[j] <= t:
            return apply_tree(node["left"], x)
        return apply_tree(node["right"], x)

    tree_feature_names = ["penetration_per_atr", "age_hours", "atr_at_event", "structure_trend"]
    tree = build_tree(X_train_raw, y_train, 0, max_depth=3)
    tree_lines = print_tree(tree, tree_feature_names)
    print(f"\n=== SHALLOW DECISION TREE (max depth 3, Gini, split minimo 10 per lato) ===")
    for line in tree_lines:
        print(line)

    # valutazione OOS: per ogni riga OOS, trova la foglia e confronta rate stimato in TRAIN vs esito reale OOS medio nella stessa foglia
    oos_leaf_stats = defaultdict(lambda: [0, 0])
    for i, x in enumerate(X_oos_raw):
        rate_pred, n_train_leaf = apply_tree(tree, x)
        key = round(rate_pred, 3)
        oos_leaf_stats[key][0] += y_oos[i]
        oos_leaf_stats[key][1] += 1
    print("\nVerifica foglie su OOS (rate stimato in TRAIN vs rate osservato in OOS per la stessa foglia):")
    for k, (hits, n) in sorted(oos_leaf_stats.items()):
        oos_rate = hits / n if n else float("nan")
        print(f"  foglia_train_rate={k:.3f}  OOS: n={n} rate_oos={oos_rate:.3f}")

    # ============================================================
    # Output
    # ============================================================
    top3 = sorted(classified, key=lambda c: -abs(c["uplift_train"]) if not math.isnan(c["uplift_train"]) else 0)[:3]

    verdict = "PROMISING_HYPOTHESIS_FOUND" if n_promising > 0 else "NO_PROMISING_HYPOTHESIS"

    results = {
        "generated_at": datetime.now().isoformat(),
        "population": {
            "total_sh_bms_rto_episodes": total_sh_bms_episodes,
            "excluded_no_lifecycle_observed": n_excluded_no_lifecycle,
            "excluded_redundant_outcome_event": n_excluded_redundant,
            "valid_population": n_valid,
        },
        "split": {"train_n": len(train), "oos_n": len(oos), "split_date": str(TRAIN_OOS_SPLIT_DATE)},
        "base_rate": {"all": base_all, "train": base_tr, "oos": base_oos, "ci95_all": [lo_all, hi_all]},
        "n_hypotheses_tested": n_hypotheses,
        "classification_summary": {"NO_SIGNAL": n_no_signal, "WEAK_HINT": n_weak, "PROMISING_HYPOTHESIS": n_promising},
        "univariate_results": classified,
        "top3_by_train_uplift": top3,
        "logistic_regression": {
            "features": log_feature_names, "weights": w_fit, "bias": b_fit,
            "accuracy_train": acc_train, "accuracy_oos": acc_oos, "majority_baseline_oos": majority_baseline_oos,
        },
        "decision_tree": {"feature_names": tree_feature_names, "structure_text": tree_lines,
                           "oos_leaf_validation": {str(k): {"n": v[1], "rate_oos": v[0] / v[1] if v[1] else None}
                                                    for k, v in oos_leaf_stats.items()}},
        "verdict": verdict,
    }

    def _default(o):
        return str(o)

    with open(os.path.join(OUT_DIR, "experiment_1_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=_default)

    # dataset usato (per riproducibilita')
    ds_fields = ["episode_id", "window_id", "outcome", "side", "source_tf", "direction",
                 "regime_at_event", "structure_trend_at_event", "consumer", "penetration_pips",
                 "atr_at_event", "penetration_per_atr", "age_seconds", "age_valid", "timestamp"]
    with open(os.path.join(OUT_DIR, "experiment_1_population.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ds_fields)
        writer.writeheader()
        for r in valid_population:
            writer.writerow({
                "episode_id": r["episode_id"], "window_id": r["window_id"], "outcome": r["outcome"],
                "side": r["f"]["side"], "source_tf": r["f"]["source_tf"], "direction": r["f"]["direction"],
                "regime_at_event": r["f"]["regime_at_event"],
                "structure_trend_at_event": r["f"]["structure_trend_at_event"],
                "consumer": r["f"]["consumer"], "penetration_pips": r["f"]["penetration_pips"],
                "atr_at_event": r["f"]["atr_at_event"], "penetration_per_atr": r["f"]["penetration_per_atr"],
                "age_seconds": r["f"]["age_seconds"], "age_valid": r["f"]["age_valid"], "timestamp": r["timestamp"],
            })

    print(f"\n=== VERDICT: {verdict} ===")
    print(f"Output salvato in {OUT_DIR}")


def _quartiles(sorted_vals):
    n = len(sorted_vals)
    if n < 4:
        return [sorted_vals[0]] * 3 if sorted_vals else [0, 0, 0]
    return [sorted_vals[n // 4], sorted_vals[n // 2], sorted_vals[3 * n // 4]]


def _quartile_bucket(val, q):
    if val is None:
        return None
    if val <= q[0]:
        return "Q1"
    if val <= q[1]:
        return "Q2"
    if val <= q[2]:
        return "Q3"
    return "Q4"


def _age_bucket(age_seconds):
    hours = age_seconds / 3600.0
    if hours < 1:
        return "<1h"
    if hours < 6:
        return "1-6h"
    if hours < 24:
        return "6-24h"
    return ">=24h"


if __name__ == "__main__":
    main()
