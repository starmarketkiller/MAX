"""
NEXUS Phase C.1 - Orphan TRUE_BREAK Root-Cause Audit.

Ricostruisce la population AT_TRUE_BREAK con il nuovo linkage v3
(episode_sweep_link, scritto CAUSALMENTE in MQL5 all'istante della
transizione IDLE->SWEPT - vedi NXS_Structural_ObserveSweep) e confronta con
la population v2 (Phase C, 159 risolti, commit 3c1c296).

SOLO audit di popolazione e attribution degli orphan - NESSUNA discovery
multivariata (univariata/logistic/tree) eseguita qui, per istruzione esplicita.
"""
import json
import os
from datetime import datetime
from collections import Counter

import build_structural_dataset_v1 as bds
import causal_thread3_true_break_quality as c3

HARVEST_DIR = r"C:\Users\User\.claude\jobs\703d44b4\tmp\structural_dataset_v1\harvest"
OUT_DIR = r"C:\Users\User\ClaudeWork\MAX\results\phase_c1_orphan_audit"
os.makedirs(OUT_DIR, exist_ok=True)


def load_window_links(win):
    path = os.path.join(HARVEST_DIR, f"episode_sweep_link_{win['id']}.csv")
    rows = bds.read_episode_link_csv(path)
    for r in rows:
        r["window_id"] = win["id"]
    return rows


def build_population(all_events, lifecycle_link, episodes, redundant_after_close, true_break_after_close,
                      m1_by_window, window_end_by_id):
    """Replica FEDELE della logica di popolazione di causal_thread3_true_break_quality.py
    (stesso R, stesso orizzonte, stessa esclusione post-close - incluso lo stesso
    set(event_id) senza window_id usato li', per isolare SOLO l'effetto del nuovo
    linkage orphan e non confondere con altri bug), ma usa episodes[ep_id]
    (autoritativo, gestisce correttamente il caso molti-episodeSeq->un canonical
    event) al posto del fragile sweeps_by_episode ricavato da all_events."""
    episode_lifecycle = bds.build_episode_lifecycle_index(all_events, lifecycle_link)
    ev_by_id = {(e["window_id"], e["event_id"]): e for e in all_events}
    redundant_ids = set(e["event_id"] for e in redundant_after_close)
    tbac_ids = set(e["event_id"] for e in true_break_after_close)

    tb_rows = []
    excluded_reasons = Counter()
    for ep_id, ep_info in episodes.items():
        peers = episode_lifecycle.get(ep_id, [])
        tb_list = sorted([p for p in peers if p["event_type"] == "TRUE_BREAK"], key=lambda x: int(x["event_id"]))
        if not tb_list:
            continue
        b = tb_list[0]
        if b["event_id"] in redundant_ids or b["event_id"] in tbac_ids:
            excluded_reasons["lifecycle_redundant_or_after_close"] += 1
            continue
        win = b["window_id"]
        sweep_ev = ev_by_id.get((win, ep_info["sweep_event_id"]))
        if sweep_ev is None:
            excluded_reasons["sweep_event_missing_unexpected"] += 1
            continue

        dsign = 1 if b["direction"] == "BUY" else (-1 if b["direction"] == "SELL" else 0)
        m1_tuple = m1_by_window[win]
        window_end = window_end_by_id[win]
        tb_atr = float(b["atr_at_event"]) if b["atr_at_event"] not in (None, "") else None
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

        tb_rows.append({
            "episode_id": ep_id, "window_id": win, "true_break_event_id": b["event_id"],
            "sweep_event_id": sweep_ev["event_id"], "direction": b["direction"],
            "plus1r_before_minus1r": fwd["plus1r_before_minus1r"],
            "retest_outcome": retest_outcome,
            "period": "DISCOVERY" if win in c3.DISCOVERY_WINDOWS else "VALIDATION",
        })
    return tb_rows, excluded_reasons


def summarize(tb_rows, label):
    n_total = len(tb_rows)
    n_ambig = sum(1 for r in tb_rows if r["plus1r_before_minus1r"] == "AMBIGUOUS_SAME_BAR")
    n_censored = sum(1 for r in tb_rows if r["plus1r_before_minus1r"] == "CENSORED")
    resolved = [r for r in tb_rows if r["plus1r_before_minus1r"] in ("PLUS_1R_FIRST", "MINUS_1R_FIRST")]
    print(f"--- {label} ---")
    print(f"  TRUE_BREAK validi: {n_total}")
    print(f"  AMBIGUOUS_SAME_BAR: {n_ambig} ({n_ambig/n_total:.1%})" if n_total else "  AMBIGUOUS_SAME_BAR: 0")
    print(f"  CENSORED: {n_censored}")
    print(f"  RISOLTI: {len(resolved)}")
    return {"n_total": n_total, "n_ambiguous": n_ambig, "n_censored": n_censored, "n_resolved": len(resolved)}


def resolved_signature(tb_rows):
    return sorted([
        (r["window_id"], r["true_break_event_id"], r["plus1r_before_minus1r"])
        for r in tb_rows if r["plus1r_before_minus1r"] in ("PLUS_1R_FIRST", "MINUS_1R_FIRST")
    ])


def main():
    all_events = []
    all_links = []
    m1_by_window = {}
    window_end_by_id = {}
    for win in c3.ALL_WINDOWS:
        ev = c3.load_window_events(win)
        all_events.extend(ev)
        all_links.extend(load_window_links(win))
        m1_by_window[win["id"]] = c3.load_window_m1(win)
        window_end_by_id[win["id"]] = datetime.strptime(win["to"], "%Y.%m.%d")

    print(f"Eventi totali: {len(all_events)}  Link totali: {len(all_links)}")

    # ============================================================
    # 1. Conteggio esatto orphan (v2) + spiegazione discrepanza 283 vs 288
    # ============================================================
    lifecycle_link_v2, episodes_v2, true_orphans_v2, redundant_v2, tbac_v2 = bds.assign_episodes(all_events)
    tb_orphans_v2 = [e for e in true_orphans_v2 if e["event_type"] == "TRUE_BREAK"]
    orphan_set_buggy = set(e["event_id"] for e in tb_orphans_v2)
    print("\n=== 1. CONTEGGIO ORPHAN ===")
    print(f"Orphan TRUE_BREAK esatti (una riga = un evento, mai deduplicato): {len(tb_orphans_v2)}")
    print(f"Orphan TRUE_BREAK via set(event_id) SENZA window_id "
          f"(replica del print diagnostico di causal_thread3_true_break_quality.py): {len(orphan_set_buggy)}")
    print(f"Discrepanza: {len(tb_orphans_v2) - len(orphan_set_buggy)} righe perse per collisione "
          f"event_id cross-window (stesso bug gia' noto e corretto altrove - Structural Causal Experiment 1 - "
          f"ma MAI corretto in questa singola riga di stampa diagnostica)")

    # ============================================================
    # 2+3. Attribution v3 (episode_sweep_link, causale)
    # ============================================================
    (lifecycle_link_v3, episodes_v3, true_orphans_v3,
     redundant_v3, tbac_v3, orphan_reasons_v3) = bds.assign_episodes_v3(all_events, all_links)
    tb_orphans_v3 = [e for e in true_orphans_v3 if e["event_type"] == "TRUE_BREAK"]

    print("\n=== 2+3. ATTRIBUTION (v3, episode_sweep_link) ===")
    print(f"Orphan TRUE_BREAK residui dopo v3: {len(tb_orphans_v3)}")

    v2_orphan_keys = set((e["window_id"], e["event_id"]) for e in tb_orphans_v2)
    v3_still_orphan_keys = set((e["window_id"], e["event_id"]) for e in tb_orphans_v3)
    v3_resolved_keys = v2_orphan_keys - v3_still_orphan_keys
    new_orphans_in_v3 = v3_still_orphan_keys - v2_orphan_keys
    print(f"Nuovi orphan comparsi SOLO in v3 (dovrebbe essere 0 - v3 e' strettamente piu' permissivo): {len(new_orphans_in_v3)}")

    attribution = Counter()
    for key in v2_orphan_keys:
        if key in v3_resolved_keys:
            attribution["CANONICAL_DEDUP_EPISODE_COLLISION_RESOLVED"] += 1
        else:
            reason = orphan_reasons_v3.get(key, "UNEXPLAINED")
            attribution[reason] += 1

    print("\nAttribution completa (288 orphan originali v2):")
    total = sum(attribution.values())
    for k, v in attribution.most_common():
        print(f"  {k}: {v} ({v/total:.1%})")
    print(f"  TOTALE: {total}")
    unexplained = attribution.get("UNEXPLAINED", 0)
    print(f"\nUNEXPLAINED = {unexplained}  (acceptance: deve essere 0)")

    # ============================================================
    # 7. Rebuild population PRE (v2) vs POST (v3)
    # ============================================================
    print("\n=== 7. POPULATION PRE (v2) vs POST (v3) ===")
    tb_rows_v2, excl_v2 = build_population(all_events, lifecycle_link_v2, episodes_v2, redundant_v2, tbac_v2,
                                            m1_by_window, window_end_by_id)
    tb_rows_v3, excl_v3 = build_population(all_events, lifecycle_link_v3, episodes_v3, redundant_v3, tbac_v3,
                                            m1_by_window, window_end_by_id)
    print(f"Esclusioni PRE (v2): {dict(excl_v2)}")
    print(f"Esclusioni POST (v3): {dict(excl_v3)}")

    summary_v2 = summarize(tb_rows_v2, "PRE (v2, Phase C originale, commit 3c1c296)")
    summary_v3 = summarize(tb_rows_v3, "POST (v3, Phase C.1 con episode_sweep_link)")

    sig_v2 = resolved_signature(tb_rows_v2)
    sig_v3 = resolved_signature(tb_rows_v3)
    identical = (sig_v2 == sig_v3)
    added = [x for x in sig_v3 if x not in sig_v2]
    removed = [x for x in sig_v2 if x not in sig_v3]
    print(f"\n=== 8. IMPATTO SUI 159 OUTCOME ===")
    print(f"Population risolta IDENTICA bit-for-bit v2 vs v3: {identical}")
    print(f"  Aggiunti in v3 (nuovi risolti, prima orphan): {len(added)}")
    print(f"  Rimossi (erano risolti in v2, non piu' in v3): {len(removed)}")

    result = {
        "generated_at": datetime.now().isoformat(),
        "orphan_count_exact": len(tb_orphans_v2),
        "orphan_count_buggy_diagnostic_print": len(orphan_set_buggy),
        "orphan_discrepancy_explained": len(tb_orphans_v2) - len(orphan_set_buggy),
        "new_orphans_introduced_by_v3": len(new_orphans_in_v3),
        "attribution": dict(attribution),
        "unexplained": unexplained,
        "population_v2_pre": summary_v2,
        "population_v3_post": summary_v3,
        "exclusions_v2": dict(excl_v2),
        "exclusions_v3": dict(excl_v3),
        "resolved_population_identical_bit_for_bit": identical,
        "resolved_added_in_v3": added,
        "resolved_removed_in_v3": removed,
    }
    with open(os.path.join(OUT_DIR, "phase_c1_results.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nOutput salvato in {OUT_DIR}")


if __name__ == "__main__":
    main()
