"""
NEXUS Causal Research Thread 2 - Structural Causal Experiment 3: Economic Bridge.

Domanda: il predittore strutturale confermato (penetration_per_atr > soglia
congelata da Experiment 1/2) ha anche valore economico (+1R prima di -1R)
dopo TRUE_BREAK, o predice solo l'evento strutturale senza tradursi in un
esito favorevole?

NON discovery, NON nuova soglia, NON nuova combinazione. Soglia
penetration/ATR CONGELATA da Experiment 1/2. R=25 pip fisso (stessa
convenzione di tutti gli esperimenti causali precedenti in questo thread).

Puro standard library, riusa build_structural_dataset_v1.py e
structural_causal_experiment_2_confirmatory.py (stessa logica di
popolazione/linkage/test, nessuna riscrittura).
"""
import csv
import json
import math
import os
import random
from datetime import datetime, timedelta
from collections import defaultdict, Counter

import build_structural_dataset_v1 as bds
import structural_causal_experiment_2_confirmatory as sce2

HARVEST_DIR = r"C:\Users\User\.claude\jobs\703d44b4\tmp\structural_dataset_v1\harvest"
OUT_DIR = r"C:\Users\User\ClaudeWork\MAX\results\structural_causal_experiment_3"
os.makedirs(OUT_DIR, exist_ok=True)

WA = {"id": "wA", "from": "2025.05.01", "to": "2025.09.01"}
WINDOW_END = datetime(2025, 9, 1)

PEN_ATR_Q4_THRESHOLD = sce2.PEN_ATR_Q4_THRESHOLD  # 0.058713928652578955, congelata - MAI ricalcolata
R_PIPS = bds.R_PIPS      # 25 pip, congelato
PIP_SIZE = bds.PIP_SIZE

MIN_EFFECT = 0.10
MIN_N_GROUP = 20
MIN_N_HALF = 8
MIN_N_SIDE = 15

random.seed(20260914)  # riproducibilita' del cluster bootstrap


def load_wA_events():
    rows = bds.read_structural_csv(os.path.join(HARVEST_DIR, f"structural_events_{WA['id']}.csv"))
    for r in rows:
        r["window_id"] = WA["id"]
    return rows


def load_wA_m1():
    return bds.read_m1_csv(os.path.join(HARVEST_DIR, f"nxs_m1_struct_{WA['id']}.csv"))


def main():
    all_events = load_wA_events()
    m1_tuple = load_wA_m1()

    lifecycle_link, episodes, true_orphans, redundant_after_close, true_break_after_close = bds.assign_episodes(all_events)
    episode_lifecycle = bds.build_episode_lifecycle_index(all_events, lifecycle_link)
    redundant_ids = set(e["event_id"] for e in redundant_after_close)
    tbac_ids = set(e["event_id"] for e in true_break_after_close)
    sweeps_by_episode = {e["structural_episode_id"]: e for e in all_events if e["event_type"] == "SWEEP"}

    malformed = [e for e in all_events if e["direction"] == "NONE" or not e.get("side") or e["level_price"] <= 0]

    # ============================================================
    # §2/§3: Population + structural replication (identica a Experiment 2, nessuna modifica)
    # ============================================================
    valid_population = []
    n_no_lifecycle = 0
    n_excluded_redundant = 0
    for ep_id in episodes:
        peers = episode_lifecycle.get(ep_id, [])
        tb = sorted([p for p in peers if p["event_type"] == "TRUE_BREAK"], key=lambda x: int(x["event_id"]))
        inv_swept = sorted([p for p in peers if p["event_type"] == "INVALIDATE" and p["state_before"] == "SWEPT"],
                            key=lambda x: int(x["event_id"]))
        if not tb and not inv_swept:
            n_no_lifecycle += 1
            continue
        determinant = tb[0] if tb else inv_swept[0]
        outcome = "TRUE_BREAK_OBSERVED" if tb else "INVALIDATED_NO_BREAK"
        if determinant["event_id"] in redundant_ids or determinant["event_id"] in tbac_ids:
            n_excluded_redundant += 1
            continue
        sweep_row = sweeps_by_episode.get(ep_id)
        if sweep_row is None:
            continue
        atr = float(sweep_row["atr_at_event"]) if sweep_row["atr_at_event"] not in (None, "") else None
        pen_pips = float(sweep_row["penetration_pips"])
        pen_per_atr = (pen_pips * PIP_SIZE / atr) if (atr and atr > 0) else None
        valid_population.append({
            "episode_id": ep_id, "outcome": outcome, "timestamp": sweep_row["timestamp"],
            "direction": sweep_row["direction"], "penetration_per_atr": pen_per_atr,
            "side": sweep_row["side"],
        })

    pop_stats = {
        "total_episodes": len(episodes), "no_lifecycle_observed": n_no_lifecycle,
        "excluded_redundant_outcome": n_excluded_redundant, "orphan_events": len(true_orphans),
        "malformed_rows": len(malformed), "valid_population": len(valid_population),
    }
    print("=== PERIODO ===")
    print(f"wA: {WA['from']} -> {WA['to']} (zero overlap con w0/w1-w4: 2025-09-01 -> 2026-08-25)")
    print("\n=== POPULATION (identica exclusion policy di Experiment 1/2) ===")
    print(json.dumps(pop_stats, indent=2))

    replication = sce2.test_hint(
        "penetration_per_atr_Q4_REPLICATION", valid_population,
        lambda r: r["penetration_per_atr"] is not None and r["penetration_per_atr"] > PEN_ATR_Q4_THRESHOLD,
        exp1_uplift_sign=+1)
    print("\n=== STRUCTURAL REPLICATION (stessa soglia congelata, nessuna modifica) ===")
    print(json.dumps(replication, indent=2, default=str))

    # ============================================================
    # §4-7: Economic bridge - AT_TRUE_BREAK, causal join alla penetration/ATR dello SWEEP originario
    # ============================================================
    # Semantica BUY/SELL verificata nel codice (NXS_Strategies_SMC.mqh, NXS_SHBMS_UpdateSide,
    # blocco RETEST): dir==+1 -> s.dir=DIR_BUY, dir==-1 -> s.dir=DIR_SELL. sw.dir e' congelato in
    # st.structDir al momento dello SWEEP e riportato invariato su TRUE_BREAK/RETEST/INVALIDATE -
    # il campo "direction" del rigo TRUE_BREAK e' quindi la STESSA direzione dello sweep originario,
    # nessuna ambiguita', nessuna assunzione.
    tb_rows = []
    orphan_true_break_no_sweep_join = 0
    for ep_id, sweep_ev in sweeps_by_episode.items():
        peers = episode_lifecycle.get(ep_id, [])
        tb = sorted([p for p in peers if p["event_type"] == "TRUE_BREAK"], key=lambda x: int(x["event_id"]))
        if not tb:
            continue
        b = tb[0]
        if b["event_id"] in redundant_ids or b["event_id"] in tbac_ids:
            continue  # stesso criterio di esclusione della population primaria (outcome post-close non affidabile)

        # JOIN CAUSALE ESPLICITO: penetration/ATR presa dallo SWEEP originario (sweep_ev),
        # MAI ricalcolata sui campi propri del rigo TRUE_BREAK (che descrivono lo stato AL
        # MOMENTO del true break, non allo sweep).
        sw_atr = float(sweep_ev["atr_at_event"]) if sweep_ev["atr_at_event"] not in (None, "") else None
        sw_pen_pips = float(sweep_ev["penetration_pips"])
        sw_pen_per_atr = (sw_pen_pips * PIP_SIZE / sw_atr) if (sw_atr and sw_atr > 0) else None

        dsign_val = 1 if b["direction"] == "BUY" else (-1 if b["direction"] == "SELL" else 0)
        fwd = bds.scan_forward_labels(m1_tuple, WINDOW_END, b["timestamp"], float(b["price_at_event"]), dsign_val, None)

        rt = sorted([p for p in peers if p["event_type"] == "RETEST"], key=lambda x: int(x["event_id"]))
        retest_hold_or_fail = "N/A_NO_RETEST"
        if rt:
            r0 = rt[0]
            r_fwd = bds.scan_forward_labels(m1_tuple, WINDOW_END, r0["timestamp"], float(r0["price_at_event"]), dsign_val, None)
            retest_hold_or_fail = {
                "PLUS_1R_FIRST": "HOLD", "MINUS_1R_FIRST": "FAIL",
                "AMBIGUOUS_SAME_BAR": "AMBIGUOUS", "CENSORED": "CENSORED",
            }[r_fwd["plus1r_before_minus1r"]]

        tb_rows.append({
            "episode_id": ep_id, "true_break_event_id": b["event_id"], "sweep_event_id": sweep_ev["event_id"],
            "timestamp": b["timestamp"], "direction": b["direction"], "side": sweep_ev["side"],
            "sweep_penetration_per_atr": sw_pen_per_atr,
            "plus1r_before_minus1r": fwd["plus1r_before_minus1r"],
            "retest_hold_or_fail": retest_hold_or_fail,
        })

    n_tb_total = len(tb_rows)
    ambiguous = [r for r in tb_rows if r["plus1r_before_minus1r"] == "AMBIGUOUS_SAME_BAR"]
    censored = [r for r in tb_rows if r["plus1r_before_minus1r"] == "CENSORED"]
    resolved = [r for r in tb_rows if r["plus1r_before_minus1r"] in ("PLUS_1R_FIRST", "MINUS_1R_FIRST")]

    print(f"\n=== AT_TRUE_BREAK (economic bridge) ===")
    print(f"TRUE_BREAK totali (esito affidabile, non post-close): {n_tb_total}")
    print(f"Risolti (PLUS_1R_FIRST/MINUS_1R_FIRST): {len(resolved)}  "
          f"Ambiguous (stessa barra): {len(ambiguous)} ({len(ambiguous)/n_tb_total:.1%})  "
          f"Censored: {len(censored)} ({len(censored)/n_tb_total:.1%})")

    def plus1r_rate(subset):
        n = len(subset)
        k = sum(1 for r in subset if r["plus1r_before_minus1r"] == "PLUS_1R_FIRST")
        return k, n, (k / n if n else float("nan"))

    group_A = resolved  # tutti i TRUE_BREAK risolti (baseline)
    group_B = [r for r in resolved if r["sweep_penetration_per_atr"] is not None and
               r["sweep_penetration_per_atr"] > PEN_ATR_Q4_THRESHOLD]

    kA, nA, rateA = plus1r_rate(group_A)
    kB, nB, rateB = plus1r_rate(group_B)
    loA, hiA = sce2.wilson_ci(kA, nA)
    loB, hiB = sce2.wilson_ci(kB, nB)
    uplift = rateB - rateA if nB else float("nan")
    diff, z, pval = sce2.two_proportion_z(kB, nB, kA - kB, nA - nB) if nB else (float("nan"),) * 3

    print(f"\nGruppo A (TUTTI i TRUE_BREAK validi, baseline): n={nA} PLUS_1R_FIRST={kA} rate={rateA:.3f} CI95=[{loA:.3f},{hiA:.3f}]")
    print(f"Gruppo B (TRUE_BREAK da sweep con penetration/ATR > soglia): n={nB} PLUS_1R_FIRST={kB} rate={rateB:.3f} CI95=[{loB:.3f},{hiB:.3f}]")
    print(f"Uplift assoluto B vs A: {uplift:+.3f}   diff-of-proportions z={z:.2f} p={pval:.4f}")

    # BUY/SELL su Gruppo B
    buy_B = [r for r in group_B if r["direction"] == "BUY"]
    sell_B = [r for r in group_B if r["direction"] == "SELL"]
    kbuy, nbuy, ratebuy = plus1r_rate(buy_B)
    ksell, nsell, ratesell = plus1r_rate(sell_B)
    print(f"\nGruppo B - BUY: n={nbuy} rate={ratebuy:.3f}   SELL: n={nsell} rate={ratesell:.3f}")

    # meta' temporale su Gruppo B (mediana sull'intero gruppo B)
    ts_sorted = sorted(r["timestamp"] for r in group_B)
    median_ts = ts_sorted[len(ts_sorted) // 2] if ts_sorted else None
    first_half = [r for r in group_B if median_ts and r["timestamp"] < median_ts]
    second_half = [r for r in group_B if median_ts and r["timestamp"] >= median_ts]
    kf, nf, ratef = plus1r_rate(first_half)
    ks, ns, rates = plus1r_rate(second_half)
    print(f"Gruppo B - prima meta': n={nf} rate={ratef:.3f}   seconda meta': n={ns} rate={rates:.3f}")

    # ============================================================
    # §6: secondary bridge - RETEST_HOLD_OR_FAIL sul Gruppo B
    # ============================================================
    retest_B = [r for r in group_B if r["retest_hold_or_fail"] != "N/A_NO_RETEST"]
    retest_counts = Counter(r["retest_hold_or_fail"] for r in retest_B)
    print(f"\n=== SECONDARY BRIDGE: RETEST_HOLD_OR_FAIL sul Gruppo B ===")
    print(f"n episodi Gruppo B con RETEST osservato: {len(retest_B)}  breakdown: {dict(retest_counts)}")
    if len(retest_B) < 15:
        print("Campione troppo piccolo per un giudizio - NON usato per promuovere/bocciare la candidata (per istruzione).")

    # ============================================================
    # §8: concentrazione / cluster
    # ============================================================
    # recupera structural_level_id per i row del gruppo B (dall'evento SWEEP originario)
    level_of_episode = {}
    for ep_id, sweep_ev in sweeps_by_episode.items():
        level_of_episode[ep_id] = sweep_ev["structural_level_id"]
    for r in tb_rows:
        r["structural_level_id"] = level_of_episode.get(r["episode_id"])

    unique_episodes_B = len(set(r["episode_id"] for r in group_B))
    unique_levels_B = len(set(r["structural_level_id"] for r in group_B))
    by_day = Counter(r["timestamp"].date() for r in group_B)
    by_side = Counter(r["side"] for r in group_B)
    top_days = by_day.most_common(5)

    print(f"\n=== CONCENTRAZIONE (Gruppo B) ===")
    print(f"unique structural_episode_id: {unique_episodes_B}  unique structural_level_id: {unique_levels_B}  "
          f"(n_totale={nB})")
    print(f"top 5 giorni per numero di episodi: {top_days}")
    print(f"per levelTag: {dict(by_side)}")

    # cluster bootstrap per giorno (percentile CI, 2000 resample, resampling di GIORNI interi con
    # rimpiazzo, non di singoli episodi - corregge per correlazione infra-giorno)
    days = sorted(by_day.keys())
    day_groups = defaultdict(list)
    for r in group_B:
        day_groups[r["timestamp"].date()].append(r)

    def cluster_bootstrap_ci(day_groups_dict, days_list, n_boot=2000):
        if len(days_list) < 3:
            return (float("nan"), float("nan"), "troppo pochi giorni distinti per un bootstrap significativo")
        rates = []
        for _ in range(n_boot):
            sample_days = [random.choice(days_list) for _ in days_list]
            k_tot, n_tot = 0, 0
            for d in sample_days:
                grp = day_groups_dict[d]
                n_tot += len(grp)
                k_tot += sum(1 for r in grp if r["plus1r_before_minus1r"] == "PLUS_1R_FIRST")
            if n_tot > 0:
                rates.append(k_tot / n_tot)
        rates.sort()
        lo = rates[int(0.025 * len(rates))]
        hi = rates[int(0.975 * len(rates))]
        return (lo, hi, f"{len(days_list)} giorni distinti, {n_boot} resample")

    # bootstrap solo sui row RISOLTI del gruppo B (coerente con rateB sopra)
    day_groups_resolved = defaultdict(list)
    for r in group_B:
        if r["plus1r_before_minus1r"] in ("PLUS_1R_FIRST", "MINUS_1R_FIRST"):
            day_groups_resolved[r["timestamp"].date()].append(r)
    days_resolved = sorted(day_groups_resolved.keys())
    clo, chi, cnote = cluster_bootstrap_ci(day_groups_resolved, days_resolved)
    print(f"\nCI95 clusterizzato per giorno (bootstrap, Gruppo B, risolti): [{clo:.3f},{chi:.3f}]  ({cnote})")
    print(f"(confronto: CI95 naive non-clusterizzato: [{loB:.3f},{hiB:.3f}])")

    # ============================================================
    # Gate di classificazione (§9)
    # ============================================================
    reasons = []
    structural_ok = replication["classification"] == "CONFIRMED"
    economic_material = (not math.isnan(uplift)) and uplift >= MIN_EFFECT
    same_dir_struct = (not math.isnan(uplift)) and uplift > 0  # stessa direzione = B rende di piu' di A
    no_destructive_bs = True
    if nbuy >= MIN_N_SIDE and nsell >= MIN_N_SIDE:
        no_destructive_bs = not ((ratebuy - rateA < -MIN_EFFECT and ratesell > rateA) or
                                  (ratesell - rateA < -MIN_EFFECT and ratebuy > rateA))
    else:
        reasons.append("BUY/SELL non entrambi con campione sufficiente per un giudizio pieno di robustezza")
    halves_ok = True
    if nf >= MIN_N_HALF and ns >= MIN_N_HALF:
        halves_ok = (ratef - rateA > 0) == (rates - rateA > 0)
    else:
        reasons.append("almeno una meta' temporale con campione insufficiente per un giudizio pieno")
    sample_ok = nB >= MIN_N_GROUP

    if not structural_ok:
        verdict = "STRUCTURAL_HYPOTHESIS_REFUTED_FINAL"
        verdict_reason = "la replicazione strutturale su questo terzo periodo indipendente non conferma il predittore (vedi §3)"
    elif same_dir_struct and economic_material and no_destructive_bs and halves_ok and sample_ok:
        verdict = "ECONOMIC_BRIDGE_CONFIRMED"
        verdict_reason = "structural uplift confermato, PLUS_1R_FIRST migliora materialmente rispetto alla baseline, " \
                          "nessuna inversione distruttiva BUY/SELL, meta' temporali coerenti, campione adeguato" + \
                          (f" (note: {'; '.join(reasons)})" if reasons else "")
    else:
        verdict = "STRUCTURAL_ONLY_NOT_TRADABLE"
        verdict_reason = f"il predittore resta strutturalmente valido ma l'esito economico non soddisfa il gate: " \
                          f"same_dir={same_dir_struct} material={economic_material} no_destructive_bs={no_destructive_bs} " \
                          f"halves_ok={halves_ok} sample_ok={sample_ok}"

    print(f"\n=== VERDICT: {verdict} ===")
    print(verdict_reason)

    output = {
        "generated_at": datetime.now().isoformat(),
        "period": WA,
        "population": pop_stats,
        "structural_replication": replication,
        "economic_bridge": {
            "n_true_break_total_reliable": n_tb_total,
            "n_resolved": len(resolved), "n_ambiguous_same_bar": len(ambiguous), "n_censored": len(censored),
            "ambiguous_rate": len(ambiguous) / n_tb_total if n_tb_total else None,
            "censored_rate": len(censored) / n_tb_total if n_tb_total else None,
            "group_A_baseline": {"k": kA, "n": nA, "rate": rateA, "ci95": [loA, hiA]},
            "group_B_filtered": {"k": kB, "n": nB, "rate": rateB, "ci95": [loB, hiB]},
            "uplift_B_vs_A": uplift, "z": z, "p_value": pval,
            "buy": {"n": nbuy, "rate": ratebuy}, "sell": {"n": nsell, "rate": ratesell},
            "first_half": {"n": nf, "rate": ratef}, "second_half": {"n": ns, "rate": rates},
        },
        "secondary_bridge_retest": {"n": len(retest_B), "breakdown": dict(retest_counts)},
        "concentration": {
            "unique_structural_episode_id_group_B": unique_episodes_B,
            "unique_structural_level_id_group_B": unique_levels_B,
            "top5_days_group_B": [[str(d), c] for d, c in top_days],
            "by_levelTag_group_B": dict(by_side),
            "cluster_bootstrap_ci95_by_day": [clo, chi], "cluster_bootstrap_note": cnote,
            "naive_ci95": [loB, hiB],
        },
        "verdict": verdict, "verdict_reason": verdict_reason,
    }

    def _default(o):
        return str(o)

    with open(os.path.join(OUT_DIR, "experiment_3_results.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=_default)

    tb_fields = ["episode_id", "true_break_event_id", "sweep_event_id", "timestamp", "direction", "side",
                 "structural_level_id", "sweep_penetration_per_atr", "plus1r_before_minus1r", "retest_hold_or_fail"]
    with open(os.path.join(OUT_DIR, "experiment_3_at_true_break.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=tb_fields)
        writer.writeheader()
        for r in tb_rows:
            writer.writerow({k: r.get(k) for k in tb_fields})

    print(f"\nOutput salvato in {OUT_DIR}")


if __name__ == "__main__":
    main()
