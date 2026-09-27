#!/usr/bin/env python3
"""Phase 7.17 punto 3 - casi minimi calcolabili a mano: price -> EMA1 ->
EMA2 -> TSI/state -> signal, confrontando A (comportamento multi-TF
attuale, contaminato) vs B (comportamento TF-scoped, inteso).

Disciplina di indipendenza: i valori attesi sono calcolati da
`_reference_recursion()` sotto, una reimplementazione SEPARATA in
aritmetica RAZIONALE ESATTA (fractions.Fraction, non float) - NON e' la
funzione `tsi_update()` sotto verifica (nxs_tsi_replica.py), ed e'
insensibile agli errori di arrotondamento float che potrebbero
mascherare un disaccordo reale. La stessa disciplina di Phase 7.9K/
7.13/7.16 (valori attesi non prodotti dalla stessa funzione testata).
"""
import os
import sys
from fractions import Fraction

PHASE717_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE717_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE717_DIR)
from nxs_tsi_replica import TSIState, tsi_update, LONG_PERIOD, SHORT_PERIOD, SIGNAL_PERIOD  # noqa: E402

A_LONG_EXACT = Fraction(2, LONG_PERIOD + 1)
A_SHORT_EXACT = Fraction(2, SHORT_PERIOD + 1)
A_SIG_EXACT = Fraction(2, SIGNAL_PERIOD + 1)


def _reference_recursion(sm1, sm1abs, sm2, sm2abs, signal, prev_close, close):
    """Reimplementazione INDIPENDENTE (Fraction esatta) di un singolo
    passo della ricorsione TSI - NON e' tsi_update(), usata solo per
    calcolare i valori attesi."""
    pc = Fraction(close) - Fraction(prev_close)
    apc = abs(pc)
    sm1n = pc * A_LONG_EXACT + Fraction(sm1) * (1 - A_LONG_EXACT)
    sm1absn = apc * A_LONG_EXACT + Fraction(sm1abs) * (1 - A_LONG_EXACT)
    sm2n = sm1n * A_SHORT_EXACT + Fraction(sm2) * (1 - A_SHORT_EXACT)
    sm2absn = sm1absn * A_SHORT_EXACT + Fraction(sm2abs) * (1 - A_SHORT_EXACT)
    tsi_now = Fraction(100) * sm2n / sm2absn if sm2absn != 0 else Fraction(0)
    signaln = tsi_now * A_SIG_EXACT + Fraction(signal) * (1 - A_SIG_EXACT)
    return {"sm1": sm1n, "sm1abs": sm1absn, "sm2": sm2n, "sm2abs": sm2absn,
           "tsi": tsi_now, "signal": signaln}


# --- Stato condiviso all'inizio della finestra di divergenza (gia'
# oltre il warmup, valori arbitrari ma realistici) ---
INIT = {"sm1": 1.0, "sm1abs": 3.0, "sm2": 1.0, "sm2abs": 3.0,
       "signal": 100.0 / 3.0, "prev_close": 2000.0}


def build():
    # --- Passo 0 (condiviso A e B): chiusura D1_1 = 2010.0 ---
    step0 = _reference_recursion(INIT["sm1"], INIT["sm1abs"], INIT["sm2"], INIT["sm2abs"],
                                 INIT["signal"], INIT["prev_close"], 2010.0)

    # --- Stream A: due passaggi H4 CONTAMINANTI prima della prossima D1 ---
    step_h4a = _reference_recursion(step0["sm1"], step0["sm1abs"], step0["sm2"], step0["sm2abs"],
                                    step0["signal"], 2010.0, 2008.0)
    step_h4b = _reference_recursion(step_h4a["sm1"], step_h4a["sm1abs"], step_h4a["sm2"],
                                    step_h4a["sm2abs"], step_h4a["signal"], 2008.0, 2015.0)
    step_a_d1_2 = _reference_recursion(step_h4b["sm1"], step_h4b["sm1abs"], step_h4b["sm2"],
                                       step_h4b["sm2abs"], step_h4b["signal"], 2015.0, 2020.0)

    # --- Stream B: TF-scoped, ignora H4, va DIRETTAMENTE da D1_1 a D1_2 ---
    step_b_d1_2 = _reference_recursion(step0["sm1"], step0["sm1abs"], step0["sm2"], step0["sm2abs"],
                                       step0["signal"], 2010.0, 2020.0)

    def _f2s(d):
        return {k: (str(v) if isinstance(v, Fraction) else v) for k, v in d.items()}

    def _f2float(d):
        return {k: float(v) for k, v in d.items()}

    # --- Verifica incrociata con tsi_update() (float, la funzione REALE
    # sotto verifica) - stessa sequenza di eventi, per confermare che
    # l'implementazione float concorda con la reference esatta entro
    # tolleranza numerica. ---
    def _run_float_sequence(events):
        st = TSIState()
        st.init = True
        st.sm1, st.sm1_abs = INIT["sm1"], INIT["sm1abs"]
        st.sm2, st.sm2_abs = INIT["sm2"], INIT["sm2abs"]
        st.signal = INIT["signal"]
        st.prev_close = INIT["prev_close"]
        st.last_bar_time = "T_INIT"
        st.bars_seen = 1000  # oltre il warmup, per osservare tsi/signal ad ogni passo
        recs = []
        for curbar0, c1 in events:
            sig, rec = tsi_update(st, c1, curbar0, seed_close=INIT["prev_close"])
            recs.append(rec)
        return recs

    events_a = [("T1", 2010.0), ("T2_H4a", 2008.0), ("T3_H4b", 2015.0), ("T4", 2020.0)]
    events_b = [("T1", 2010.0), ("T4", 2020.0)]  # B salta gli eventi H4 (non canonici)
    recs_a = _run_float_sequence(events_a)
    recs_b = _run_float_sequence(events_b)

    tol = 1e-9
    cross_check_a = abs(recs_a[-1]["tsi"] - float(step_a_d1_2["tsi"])) < tol
    cross_check_b = abs(recs_b[-1]["tsi"] - float(step_b_d1_2["tsi"])) < tol

    payload = {
        "method": "Reimplementazione INDIPENDENTE in aritmetica razionale esatta "
                 "(fractions.Fraction) per i valori attesi, poi confrontata con "
                 "tsi_update() (float, la funzione sotto verifica) entro tolleranza "
                 "1e-9 - NON e' la stessa funzione, elimina anche il rischio di "
                 "mascheramento da arrotondamento float.",
        "shared_initial_state": INIT,
        "step_0_shared_D1_1_close_2010": _f2s(step0),
        "stream_A_contaminated": {
            "description": "D1_1 (2010) -> H4_a (2008, NON canonico) -> H4_b (2015, NON "
                          "canonico) -> D1_2 (2020)",
            "step_h4a": _f2s(step_h4a), "step_h4b": _f2s(step_h4b), "step_d1_2": _f2s(step_a_d1_2),
            "pc_used_for_D1_2": str(Fraction(2020) - Fraction(2015)),
        },
        "stream_B_tf_scoped": {
            "description": "D1_1 (2010) -> D1_2 (2020) DIRETTAMENTE (i passaggi H4 non "
                          "toccano mai lo stato)",
            "step_d1_2": _f2s(step_b_d1_2),
            "pc_used_for_D1_2": str(Fraction(2020) - Fraction(2010)),
        },
        "divergence_at_D1_2": {
            "tsi_stream_A": float(step_a_d1_2["tsi"]), "tsi_stream_B": float(step_b_d1_2["tsi"]),
            "signal_stream_A": float(step_a_d1_2["signal"]), "signal_stream_B": float(step_b_d1_2["signal"]),
            "tsi_difference": float(step_a_d1_2["tsi"] - step_b_d1_2["tsi"]),
            "note": "Sulla STESSA barra D1_2, con lo STESSO prezzo di chiusura (2020.0), le "
                   "due ricostruzioni producono un TSI e una signal-line NUMERICAMENTE "
                   "DIVERSI - non solo un segnale diverso, il VALORE DELL'INDICATORE "
                   "stesso diverge (coerente con la formalizzazione del punto 2: un "
                   "filtro ricorsivo continuo non puo' 'ripulirsi').",
        },
        "float_implementation_cross_check": {
            "tsi_update_stream_A_matches_exact_reference": cross_check_a,
            "tsi_update_stream_B_matches_exact_reference": cross_check_b,
            "tolerance": tol,
        },
        "expected_values_computed_independently_not_from_function_under_test": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE717_DIR, "tsi_minimal_cases_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  TSI stream A: {payload['divergence_at_D1_2']['tsi_stream_A']:.6f}")
    print(f"  TSI stream B: {payload['divergence_at_D1_2']['tsi_stream_B']:.6f}")
    print(f"  differenza: {payload['divergence_at_D1_2']['tsi_difference']:.6f}")
    cc = payload["float_implementation_cross_check"]
    print(f"  cross-check float vs esatto: A={cc['tsi_update_stream_A_matches_exact_reference']} "
          f"B={cc['tsi_update_stream_B_matches_exact_reference']}")


if __name__ == "__main__":
    main()
