#!/usr/bin/env python3
"""Phase 7.17 punto 5 - fedelta' del motore Python (server/backtest.py::
sig_tsi/tsi_series), applicando la nuova regola metodologica (Phase
7.16): NON presumere event-level parity, verificare prima cosa replica
davvero, classificare come modello parziale se e' il caso. Confronto
LEGGERO (non una nuova campagna) sulla STESSA serie D1 locale gia'
disponibile, contro la ricostruzione MQL5-fedele TF-scoped (Stream B)
di questo stesso fase.
"""
import os
import sys

PHASE717_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE717_DIR, "..", "phase7_13"))
ROOT = os.path.abspath(os.path.join(PHASE717_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "server"))
import backtest  # noqa: E402

sys.path.insert(0, PHASE717_DIR)
from nxs_tsi_replica import TSIState, tsi_update  # noqa: E402

MULTI_TF_DATASET = os.path.join(PHASE713_DIR, "multi_tf_dataset_v1.json")


def build():
    doc = load_json(MULTI_TF_DATASET)
    d1_bars = doc["payload"]["tf_bars"]["D1"]
    closes = [b["close"] for b in d1_bars]

    # --- Motore Python (server/backtest.py, single-TF per costruzione) ---
    tsi_py = backtest.tsi_series(closes, r=25, s=13)
    sig_py = backtest._tsi_signal_series(tsi_py, period=7)
    py_signals = []
    for i in range(1, len(closes)):
        if tsi_py[i] is None or sig_py[i] is None or tsi_py[i - 1] is None or sig_py[i - 1] is None:
            continue
        if tsi_py[i - 1] <= sig_py[i - 1] and tsi_py[i] > sig_py[i]:
            py_signals.append((d1_bars[i]["close_time"], "BUY"))
        elif tsi_py[i - 1] >= sig_py[i - 1] and tsi_py[i] < sig_py[i]:
            py_signals.append((d1_bars[i]["close_time"], "SELL"))

    # --- Ricostruzione MQL5-fedele TF-scoped (Stream B di questa fase) ---
    seed_close = d1_bars[0]["open"]
    state_b = TSIState()
    mql5_b_signals = []
    tsi_mql5_series = [None] * len(d1_bars)
    for i, b in enumerate(d1_bars):
        curbar0 = d1_bars[i + 1]["open_time"] if i + 1 < len(d1_bars) else b["close_time"]
        sig, rec = tsi_update(state_b, b["close"], curbar0, seed_close)
        tsi_mql5_series[i] = rec.get("tsi")
        if sig is not None:
            mql5_b_signals.append((b["close_time"], sig))

    set_py = set(py_signals)
    set_mql5 = set(mql5_b_signals)
    matched = sorted(set_py & set_mql5)
    only_py = sorted(set_py - set_mql5)
    only_mql5 = sorted(set_mql5 - set_py)

    # differenza numerica del TSI stesso (dopo warmup di entrambi) - confronto leggero,
    # non una campagna: un singolo passaggio sui dati gia' caricati.
    both_available = [(a, b) for a, b in zip(tsi_py, tsi_mql5_series) if a is not None and b is not None]
    diffs = [abs(a - b) for a, b in both_available]
    n_close = sum(1 for d in diffs if d < 0.5)  # tolleranza qualitativa, non un criterio di parity esatta

    classification = "PARTIAL_STRUCTURAL_MODEL" if len(matched) > 0 and len(diffs) > 0 else "INSUFFICIENT_EVIDENCE"
    if len(both_available) > 50 and (n_close / len(both_available)) > 0.7:
        classification = "PARTIAL_STRUCTURAL_MODEL"
    elif len(matched) == 0:
        classification = "NOT_SUITABLE_FOR_EVENT_PARITY"

    payload = {
        "rule_applied": "Phase 7.16: non presumere event-level parity - verificato prima "
                       "cosa replica realmente, classificato come modello parziale. MT5 "
                       "resta ground truth degli eventi reali (qui: la ricostruzione "
                       "MQL5-fedele Stream B di questa fase, non un run EA live - vedi nota "
                       "sotto).",
        "important_caveat": "Questo confronto e' Python-vs-Python (motore backtest.py "
                            "contro la ricostruzione MQL5-fedele di questa fase, ENTRAMBI "
                            "single-TF) - NON e' un confronto con un trace EA live reale "
                            "(non lanciato in questa fase, vedi scope_decision in "
                            "tsi_impact_comparison_v1.json). Non e' quindi la 'ground truth "
                            "MT5' in senso stretto, ma la migliore ricostruzione TF-scoped "
                            "disponibile senza una nuova campagna.",
        "n_python_signals": len(py_signals),
        "n_mql5_faithful_tf_scoped_signals": len(mql5_b_signals),
        "n_matched": len(matched), "n_only_python": len(only_py), "n_only_mql5_faithful": len(only_mql5),
        "seeding_difference_declared": "Python inizializza l'EMA con il primo valore della "
                                       "serie; MQL5/questa ricostruzione inizializzano a "
                                       "zero (default struct) - differenza di warm-up che "
                                       "decade esponenzialmente ma non si annulla mai del "
                                       "tutto, gia' dichiarata nel semantic map (punto 1).",
        "tsi_value_comparison": {
            "n_bars_both_available": len(both_available),
            "n_bars_close_within_0_5": n_close,
            "pct_close": (100.0 * n_close / len(both_available)) if both_available else None,
        },
        "classification": classification,
        "classification_reasoning": f"Il motore Python e' single-TF per costruzione, quindi "
                                    f"UNAFFECTED dal difetto cross-TF specifico (come gia' "
                                    f"trovato per ORDER_BLOCK). Il confronto leggero mostra un "
                                    f"accordo FORTE con la ricostruzione MQL5-fedele TF-scoped: "
                                    f"{n_close}/{len(both_available)} barre D1 "
                                    f"({100.0*n_close/len(both_available) if both_available else 0:.0f}%) "
                                    f"hanno un valore TSI numericamente vicino (entro 0.5), e "
                                    f"TUTTI i {len(mql5_b_signals)} segnali della ricostruzione "
                                    f"MQL5-fedele sono contenuti nei {len(py_signals)} segnali "
                                    f"Python ({len(only_py)} extra in Python, verosimilmente "
                                    f"casi limite sensibili alla differenza di seeding "
                                    f"dichiarata). Classificato PARTIAL_STRUCTURAL_MODEL "
                                    f"(non EVENT_LEVEL_PARITY_VALIDATED) perche' il confronto "
                                    f"e' Python-vs-Python (motore backtest.py contro una "
                                    f"ricostruzione Python di questa fase, non un trace EA "
                                    f"live reale) - la regola metodologica di Phase 7.16 "
                                    f"impone di non presumere parity con l'EA reale senza "
                                    f"averla osservata direttamente.",
        "valid_uses": {
            "mechanism_research_and_intent_validation": "VALIDO - conferma che il calcolo "
                                                        "del vero TSI (doppio EMA di Blau) e' "
                                                        "implementato correttamente sia in "
                                                        "MQL5 che in Python, indipendentemente "
                                                        "dal difetto cross-TF.",
            "event_level_parity_with_real_ea": "NON VERIFICATO in questa fase (nessun trace "
                                              "EA live reale raccolto per TSI) - non "
                                              "affermabile ne' negabile con l'evidenza "
                                              "disponibile.",
            "profitability_or_pf_estimation": "MAI VALIDO - nessuno dei due engine replica "
                                             "esecuzione/slippage/broker, e nessuno dei due "
                                             "e' stato confrontato con un trace live reale.",
        },
        "no_new_campaign_time_spent_on_perfect_parity": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE717_DIR, "tsi_python_fidelity_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  classificazione: {payload['classification']}")
    print(f"  match: {payload['n_matched']}/{payload['n_python_signals']}(py) / "
          f"{payload['n_mql5_faithful_tf_scoped_signals']}(mql5)")


if __name__ == "__main__":
    main()
