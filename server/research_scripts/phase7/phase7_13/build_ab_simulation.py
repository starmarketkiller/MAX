#!/usr/bin/env python3
"""Phase 7.13 punto 4 - confronto controllato A (come implementato) vs
B (ricostruzione diagnostica TF-scoped) sui dati reali multi-TF di
multi_tf_dataset_v1.json.

STREAM A - fedele a NXS_CollectRaw/NXS_CollectAllSignals: ad ogni
chiusura di barra di QUALUNQUE passaggio del set {D1,H4,H1,M30,M15}
(unione dei TF distinti fra i profili di tutte le strategie live -
vedi NXS_StrategyProfiles.mqh, NEXUS_EA_v2.mq5:670-733), viene chiamata
NXS_Strat_OrderBlock() con tf=passaggio corrente, mutando lo stato
condiviso g_obBuy/g_obSell. Il segnale prodotto viene "generated" (cioe'
sopravvive al filtro del router, NEXUS_EA_v2.mq5:710) SOLO se il
passaggio e' D1 (NXS_Profile_TF('ORDER_BLOCK')).

STREAM B - ricostruzione diagnostica: lo stato ORDER_BLOCK viene
mutato SOLO dai passaggi D1 (guardia equivalente a
`if(tf != PERIOD_D1) return s;` valutata PRIMA di ogni lettura/mutazione
- NON applicata al sorgente reale in questa fase).

LIMITE DICHIARATO (passaggio M5): il set dei TF di passaggio realmente
usati dal router include anche M5 (LEVEL_CONFLUENCE_M5/LEVEL_REACTION_M5,
vedi NXS_StrategyProfiles.mqh righe 303/307), piu' fine della
granularita' M15 della fonte disponibile in questa fase - M5 e'
ESCLUSO da questa simulazione. L'esposizione reale al meccanismo di
contaminazione e' quindi un LIMITE INFERIORE (probabilmente
sottostimato, non sovrastimato) rispetto alla configurazione live
reale.

GATE A VALLE NON MODELLATI (dichiarato, vedi anche
diagnostic_protocol_order_block_v1.json Phase 7.12): g_structH1.trend
(filtro struttura H1) e InpUseSMCReactionGate/NXS_SMCReactionOK (gate
di reazione SMC) NON sono replicati qui - il confronto avviene al
livello del RAW TRIGGER pre-gate, che e' esattamente il punto in cui
avviene la mutazione di stato sotto diagnosi. 'generated' in questo
script significa quindi 'raw trigger sul passaggio D1', non 'segnale
finale post-gate/post-esecuzione'. BLOCKED/OPENED (dipendenti da questi
gate + esecuzione broker) sono dichiarati NOT_MODELED_THIS_PHASE.
"""
import os
import sys

PHASE713_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE713_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, PHASE713_DIR)
from nxs_order_block_replica import OBState, ob_update_side  # noqa: E402

PASSES = ["D1", "H4", "H1", "M30", "M15"]
CANONICAL_TF = "D1"
EXCLUDED_PASSES_DECLARED = ["M5"]


def _curbar0_time(bars, i):
    return bars[i + 1]["open_time"] if i + 1 < len(bars) else bars[i]["close_time"]


def _global_event_order(tf_bars):
    """Unione cronologica di tutti gli eventi di chiusura barra su tutti
    i passaggi, ordinata per close_time (ties: ordine fisso D1>H4>H1>M30>M15
    per determinismo - non altera l'esito perche' un singolo istante di
    chiusura non e' MAI condiviso da due TF diversi nella pratica di
    questa serie derivata per resampling gerarchico esatto, tranne al
    limite in cui una chiusura D1 coincide con una chiusura H4/H1/M30/M15
    - in quel caso la barra piu' GROSSA chiude per ultima nella realta'
    del multi-TF loop del router, quindi processiamo prima i TF piu'
    fini)."""
    tf_rank = {"M15": 0, "M30": 1, "H1": 2, "H4": 3, "D1": 4}
    events = []
    for tf in PASSES:
        bars = tf_bars[tf]
        for i in range(len(bars)):
            events.append((bars[i]["close_time"], tf_rank[tf], tf, i))
    events.sort(key=lambda e: (e[0], e[1]))
    return events


def build():
    doc = load_json(os.path.join(PHASE713_DIR, "multi_tf_dataset_v1.json"))
    data = doc["payload"]
    tf_bars = data["tf_bars"]
    tf_atr = data["tf_atr"]
    events = _global_event_order(tf_bars)

    state_a_buy, state_a_sell = OBState(), OBState()
    state_b_buy, state_b_sell = OBState(), OBState()

    raw_triggers_a = []   # ogni segnale prodotto su QUALUNQUE passaggio in Stream A
    generated_a = []      # solo segnali su passaggio D1 in Stream A
    generated_b = []      # segnali su passaggio D1 in Stream B (unico passaggio processato)
    per_d1_comparison = []

    d1_index_lookup = {}  # close_time -> event gia' processato su D1 in A, per raccogliere anche gli op

    for close_time, _rank, tf, i in events:
        bars = tf_bars[tf]
        atr = tf_atr[tf][i]
        if atr is None:
            continue  # storia insufficiente per ATR(14) su questo TF - stesso comportamento in A e B (nessuna chiamata utile)
        curbar0 = _curbar0_time(bars, i)

        # --- Stream A: ogni passaggio muta lo stato condiviso ---
        sig_a, reason_a, mut_buy_a, mut_sell_a = None, "", None, None
        sig_a, reason_a, mut_buy_a, mut_sell_a = _run_pass(state_a_buy, state_a_sell, bars, i, atr, curbar0)
        if sig_a is not None:
            raw_triggers_a.append({"tf": tf, "close_time": close_time, "dir": sig_a, "reason": reason_a})
            if tf == CANONICAL_TF:
                generated_a.append({"close_time": close_time, "dir": sig_a, "reason": reason_a})

        # --- Stream B: solo il passaggio canonico muta lo stato ---
        if tf == CANONICAL_TF:
            sig_b, reason_b, mut_buy_b, mut_sell_b = _run_pass(state_b_buy, state_b_sell, bars, i, atr, curbar0)
            if sig_b is not None:
                generated_b.append({"close_time": close_time, "dir": sig_b, "reason": reason_b})
            per_d1_comparison.append({
                "close_time": close_time,
                "sig_a": sig_a, "sig_b": sig_b,
                "op_buy_a": mut_buy_a["op"] if mut_buy_a else None,
                "op_buy_b": mut_buy_b["op"] if mut_buy_b else None,
                "op_sell_a": mut_sell_a["op"] if mut_sell_a else None,
                "op_sell_b": mut_sell_b["op"] if mut_sell_b else None,
            })

    only_in_a = [c for c in per_d1_comparison if c["sig_a"] is not None and c["sig_b"] is None]
    only_in_b = [c for c in per_d1_comparison if c["sig_b"] is not None and c["sig_a"] is None]
    both_same_dir = [c for c in per_d1_comparison if c["sig_a"] is not None and c["sig_a"] == c["sig_b"]]
    both_diff_dir = [c for c in per_d1_comparison if c["sig_a"] is not None and c["sig_b"] is not None and c["sig_a"] != c["sig_b"]]
    same_origin_diff_lifecycle = [
        c for c in per_d1_comparison
        if c not in only_in_a and c not in only_in_b
        and (c["op_buy_a"] != c["op_buy_b"] or c["op_sell_a"] != c["op_sell_b"])
    ]

    raw_by_tf = {}
    for t in raw_triggers_a:
        raw_by_tf.setdefault(t["tf"], {"BUY": 0, "SELL": 0})
        raw_by_tf[t["tf"]][t["dir"]] += 1

    payload = {
        "passes_modeled": PASSES,
        "canonical_tf": CANONICAL_TF,
        "excluded_passes_declared": EXCLUDED_PASSES_DECLARED,
        "gates_not_modeled_declared": ["g_structH1_trend_filter", "InpUseSMCReactionGate/NXS_SMCReactionOK"],
        "period_covered": data["source_date_range"],
        "n_events_total_all_passes": len(events),
        "stream_a_raw_triggers_by_tf": raw_by_tf,
        "stream_a_raw_triggers_total": len(raw_triggers_a),
        "stream_a_raw_triggers_non_canonical_total": sum(v["BUY"] + v["SELL"] for tf, v in raw_by_tf.items() if tf != CANONICAL_TF),
        "stream_a_generated_d1_total": len(generated_a),
        "stream_b_generated_d1_total": len(generated_b),
        "stream_a_generated_d1_by_dir": {"BUY": sum(1 for g in generated_a if g["dir"] == "BUY"),
                                         "SELL": sum(1 for g in generated_a if g["dir"] == "SELL")},
        "stream_b_generated_d1_by_dir": {"BUY": sum(1 for g in generated_b if g["dir"] == "BUY"),
                                         "SELL": sum(1 for g in generated_b if g["dir"] == "SELL")},
        "n_d1_events_evaluated": len(per_d1_comparison),
        "only_in_a_signal_suppressed_in_b_denominator_note":
            "eventi con segnale D1 in A ma NON in B: la contaminazione ha CREATO un segnale che "
            "la logica TF-scoped non avrebbe prodotto",
        "only_in_a": only_in_a,
        "only_in_b_signal_suppressed_in_a_note":
            "eventi con segnale D1 in B ma NON in A: la contaminazione ha DISTRUTTO/impedito un "
            "segnale D1 genuino (il meccanismo dimostrato nella prova sintetica)",
        "only_in_b": only_in_b,
        "both_same_direction": len(both_same_dir),
        "both_different_direction": both_diff_dir,
        "same_origin_different_lifecycle_count": len(same_origin_diff_lifecycle),
        "same_origin_different_lifecycle_sample": same_origin_diff_lifecycle[:20],
        "defect_exists": sum(v["BUY"] + v["SELL"] for tf, v in raw_by_tf.items() if tf != CANONICAL_TF) > 0,
        "defect_materially_changes_behavior": (len(only_in_a) + len(only_in_b) + len(both_diff_dir)) > 0,
        "generated_vs_blocked_vs_opened_note":
            "'generated' qui = raw trigger sul passaggio D1 (pre-gate H1/SMC, pre-esecuzione). "
            "BLOCKED e OPENED dipendono da sottosistemi non replicati in questa fase "
            "(g_structH1.trend, NXS_SMCReactionOK, esecuzione broker) - NOT_MODELED_THIS_PHASE, "
            "dichiarato esplicitamente, nessuna stima di redditivita' o di tasso di esecuzione",
        "not_a_backtest_campaign": True,
        "not_used_for_profitability": True,
        "not_used_for_optimization": True,
    }
    return payload


def _run_pass(state_buy, state_sell, bars, i, atr, curbar0):
    sig_dir, reason, mut_buy = ob_update_side(+1, state_buy, bars, i, atr, curbar0)
    mut_sell = None
    if sig_dir is None:
        sig_dir, reason, mut_sell = ob_update_side(-1, state_sell, bars, i, atr, curbar0)
    return sig_dir, reason, mut_buy, mut_sell


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE713_DIR, "ab_simulation_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  eventi totali (tutti i passaggi): {payload['n_events_total_all_passes']}")
    print(f"  raw trigger Stream A (tutti i TF): {payload['stream_a_raw_triggers_total']} "
          f"(non-canonici: {payload['stream_a_raw_triggers_non_canonical_total']})")
    print(f"  generated D1 Stream A: {payload['stream_a_generated_d1_total']} "
          f"vs Stream B: {payload['stream_b_generated_d1_total']}")
    print(f"  solo in A: {len(payload['only_in_a'])} | solo in B: {len(payload['only_in_b'])} | "
          f"stessa barra direzione diversa: {len(payload['both_different_direction'])}")
    print(f"  defect_materially_changes_behavior: {payload['defect_materially_changes_behavior']}")


if __name__ == "__main__":
    main()
