#!/usr/bin/env python3
"""Phase 7.13 punto 2/3 - dimostrazione causale con una serie sintetica
piccola e calcolabile A MANO (stesso principio di rigore di Phase
7.9K/6): costruiamo un solo scenario minimo in cui una zona ORDER_BLOCK
attiva (bull, ob_lo=100, ob_hi=105) viene condivisa fra un passaggio D1
(canonico) e 6 passaggi H4 (non canonici) intercalati nello stesso
periodo, e dimostriamo che:

  1. una chiamata su un TF non canonico (H4, passaggio n.5 della
     sequenza) muta lo stato condiviso (consuma la zona: active True->False);
  2. il segnale prodotto da quella chiamata (BUY, "OB_retest_bull") e'
     un raw trigger reale ma verrebbe scartato dal router perche'
     NXS_Profile_TF("ORDER_BLOCK")=D1 != passaggio H4 (mai un segnale
     "generated" della strategia);
  3. quella stessa mutazione impedisce che un evento successivo sul TF
     CANONICO (la barra D1 #2, che da sola - se la zona non fosse gia'
     stata consumata da H4 - soddisferebbe touch+rejection e produrrebbe
     un segnale D1 genuino e tenuto) produca alcunche'.

I valori attesi (EXPECTED_*) sono stati derivati A MANO tracciando
l'algoritmo (vedi commenti sotto), NON facendo girare la funzione sotto
verifica - la stessa disciplina di indipendenza gia' applicata in
Phase 7.9K/verify_phase_7_9k.py.
"""
import os
import sys

PHASE713_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE713_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE713_DIR)
from nxs_order_block_replica import OBState, ob_update_side  # noqa: E402

ATR = 1.0  # scelto per rendere 1.2*ATR=1.2 > qualunque body delle barre "quiete" sotto

# ---------------------------------------------------------------------------
# Serie D1 (canonica) - 2 barre. bars[i] rappresenta shift 1 al momento della
# chiamata su bars[i] stessa (curbar0_time = tempo apertura barra successiva,
# o un marcatore sintetico se non esiste ancora).
# ---------------------------------------------------------------------------
D1_BARS = [
    {"open": 110.0, "high": 112.0, "low": 108.0, "close": 111.0, "open_time": "D1_1_OPEN", "close_time": "D1_1_CLOSE"},
    {"open": 106.0, "high": 112.0, "low": 101.0, "close": 109.0, "open_time": "D1_2_OPEN", "close_time": "D1_2_CLOSE"},
]

# ---------------------------------------------------------------------------
# Serie H4 (non canonica) - 6 barre intercalate fra D1#1 e D1#2 nello stesso
# periodo nominale. H4_5 e' la barra contaminante: tocca [100,105] e chiude
# rialzista (rigetto) -> consuma la zona (one-shot) su un passaggio H4.
# ---------------------------------------------------------------------------
H4_BARS = [
    {"open": 109.0, "high": 110.0, "low": 107.0, "close": 108.0, "open_time": "H4_1_OPEN", "close_time": "H4_1_CLOSE"},
    {"open": 109.0, "high": 110.0, "low": 106.0, "close": 108.0, "open_time": "H4_2_OPEN", "close_time": "H4_2_CLOSE"},
    {"open": 108.0, "high": 109.0, "low": 106.0, "close": 107.0, "open_time": "H4_3_OPEN", "close_time": "H4_3_CLOSE"},
    {"open": 107.0, "high": 108.0, "low": 106.0, "close": 106.5, "open_time": "H4_4_OPEN", "close_time": "H4_4_CLOSE"},
    {"open": 103.0, "high": 104.5, "low": 102.0, "close": 104.0, "open_time": "H4_5_OPEN", "close_time": "H4_5_CLOSE"},
    {"open": 106.0, "high": 107.0, "low": 105.5, "close": 106.5, "open_time": "H4_6_OPEN", "close_time": "H4_6_CLOSE"},
]

INIT_LAST_BAR_TIME = "INIT_SENTINEL_BEFORE_ANY_PASS"


def _make_active_state():
    st = OBState()
    st.active = True
    st.ob_lo = 100.0
    st.ob_hi = 105.0
    st.bars_waited = 0
    st.last_bar_time = INIT_LAST_BAR_TIME
    return st


def _curbar0_time_for(bars, i):
    return bars[i + 1]["open_time"] if i + 1 < len(bars) else bars[i]["close_time"]


def run_stream_a():
    """Come implementato oggi: OGNI passaggio (D1 e H4) chiama
    ob_update_side sullo stesso stato condiviso g_obBuy - fedele a
    NXS_CollectRaw che chiama NXS_Strat_OrderBlock() ad ogni passaggio
    multi-TF senza guardia (NXS_Strategies.mqh:2141-2148, chiamata
    incondizionata in NEXUS_EA_v2.mq5:535)."""
    state = _make_active_state()
    trace = []
    # D1 bar #1 - stesso evento in A e B, nessuna contaminazione ancora.
    sig, reason, mut = ob_update_side(+1, state, D1_BARS, 0, ATR, _curbar0_time_for(D1_BARS, 0))
    trace.append({"pass_tf": "D1", "bar": "D1_1", "signal": sig, "reason": reason, "mutation": mut})
    # 6 passaggi H4 NON canonici, stesso stato condiviso.
    for k in range(len(H4_BARS)):
        sig, reason, mut = ob_update_side(+1, state, H4_BARS, k, ATR, _curbar0_time_for(H4_BARS, k))
        trace.append({"pass_tf": "H4", "bar": f"H4_{k+1}", "signal": sig, "reason": reason, "mutation": mut})
    # D1 bar #2 - evento futuro sul TF canonico, stato gia' contaminato.
    sig, reason, mut = ob_update_side(+1, state, D1_BARS, 1, ATR, _curbar0_time_for(D1_BARS, 1))
    trace.append({"pass_tf": "D1", "bar": "D1_2", "signal": sig, "reason": reason, "mutation": mut})
    return trace, state


def run_stream_b():
    """Ricostruzione diagnostica TF-scoped: i passaggi H4 non toccano
    MAI lo stato ORDER_BLOCK (guardia equivalente a
    `if(tf != NXS_Profile_TF("ORDER_BLOCK")) return s;` valutata PRIMA
    di qualunque lettura/mutazione - non applicata al sorgente reale in
    questa fase, solo in questa ricostruzione diagnostica)."""
    state = _make_active_state()
    trace = []
    sig, reason, mut = ob_update_side(+1, state, D1_BARS, 0, ATR, _curbar0_time_for(D1_BARS, 0))
    trace.append({"pass_tf": "D1", "bar": "D1_1", "signal": sig, "reason": reason, "mutation": mut})
    for k in range(len(H4_BARS)):
        trace.append({"pass_tf": "H4", "bar": f"H4_{k+1}", "signal": None, "reason": "",
                      "mutation": {"op": "SKIPPED_NON_CANONICAL_TF_GUARD", "pre": state.snapshot(), "post": state.snapshot()}})
    sig, reason, mut = ob_update_side(+1, state, D1_BARS, 1, ATR, _curbar0_time_for(D1_BARS, 1))
    trace.append({"pass_tf": "D1", "bar": "D1_2", "signal": sig, "reason": reason, "mutation": mut})
    return trace, state


# ---------------------------------------------------------------------------
# Valori attesi calcolati A MANO (vedi ragionamento nel docstring del
# modulo e nel vault report) - NON prodotti facendo girare il codice.
# ---------------------------------------------------------------------------
EXPECTED_STREAM_A_SIGNALS = [
    ("D1_1", None), ("H4_1", None), ("H4_2", None), ("H4_3", None), ("H4_4", None),
    ("H4_5", "BUY"),  # contaminazione: retest consumato su passaggio non canonico
    ("H4_6", None),
    ("D1_2", None),   # EFFETTO: zona gia' consumata, nessun segnale D1 genuino
]
EXPECTED_STREAM_B_SIGNALS = [
    ("D1_1", None), ("H4_1", None), ("H4_2", None), ("H4_3", None), ("H4_4", None),
    ("H4_5", None), ("H4_6", None),
    ("D1_2", "BUY"),  # segnale D1 genuino, MAI raggiunto in Stream A
]
EXPECTED_H4_5_OP = "RETEST_SIGNAL_FIRED"
EXPECTED_D1_2_OP_STREAM_A = "SEARCH_DISPLACEMENT_NO_MATCH"  # active=False -> ramo IDLE, nessun displacement nella mini-serie sintetica
EXPECTED_D1_2_OP_STREAM_B = "RETEST_SIGNAL_FIRED"


def build():
    trace_a, final_state_a = run_stream_a()
    trace_b, final_state_b = run_stream_b()
    payload = {
        "scenario": "SYNTHETIC_MINIMAL_BUY_ZONE_D1_VS_H4_CONTAMINATION",
        "initial_state": {"active": True, "ob_lo": 100.0, "ob_hi": 105.0, "bars_waited": 0, "direction": "BUY"},
        "atr_used": ATR,
        "d1_bars": D1_BARS,
        "h4_bars": H4_BARS,
        "stream_a_as_implemented": trace_a,
        "stream_b_tf_scoped_diagnostic": trace_b,
        "final_state_stream_a": final_state_a.snapshot(),
        "final_state_stream_b": final_state_b.snapshot(),
        "causal_demonstration": {
            "1_call_on_non_canonical_tf": "H4_5 (passaggio H4, TF non canonico per ORDER_BLOCK=D1)",
            "2_state_mutation": "g_obBuy.active True->False al passaggio H4_5 (RETEST_SIGNAL_FIRED, one-shot)",
            "3_output_discarded": "il segnale BUY prodotto a H4_5 verrebbe scartato dal router "
                                  "(NXS_Profile_TF('ORDER_BLOCK')==D1 != passaggio H4, "
                                  "NEXUS_EA_v2.mq5:710) - mai un segnale 'generated' della strategia",
            "4_effect_on_future_canonical_event": "D1_2 (evento futuro sul TF canonico) non produce "
                                                  "alcun segnale in Stream A (zona gia' consumata), "
                                                  "mentre in Stream B (nessuna contaminazione H4) D1_2 "
                                                  "produce un segnale BUY genuino e valido",
        },
        "defect_exists_vs_material_impact": {
            "defect_exists": True,
            "material_impact_on_this_scenario": True,
            "note": "in questo scenario minimo il difetto non solo esiste strutturalmente ma "
                    "CAMBIA l'esito (un segnale D1 genuino viene soppresso) - la quantificazione "
                    "su dati reali (build_ab_simulation.py) stabilisce la frequenza di questo "
                    "effetto nel periodo studiato, che puo' essere diversa da 'sempre'",
        },
        "expected_values_computed_by_hand_not_by_running_code": {
            "stream_a_signals": EXPECTED_STREAM_A_SIGNALS,
            "stream_b_signals": EXPECTED_STREAM_B_SIGNALS,
            "h4_5_op": EXPECTED_H4_5_OP,
            "d1_2_op_stream_a": EXPECTED_D1_2_OP_STREAM_A,
            "d1_2_op_stream_b": EXPECTED_D1_2_OP_STREAM_B,
        },
        "no_ea_modification": True,
        "no_guard_applied_to_real_source": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE713_DIR, "synthetic_causal_proof_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    a_sigs = [(e["bar"], e["signal"]) for e in payload["stream_a_as_implemented"]]
    b_sigs = [(e["bar"], e["signal"]) for e in payload["stream_b_tf_scoped_diagnostic"]]
    assert a_sigs == EXPECTED_STREAM_A_SIGNALS, f"Stream A non combacia con l'attesa a mano: {a_sigs}"
    assert b_sigs == EXPECTED_STREAM_B_SIGNALS, f"Stream B non combacia con l'attesa a mano: {b_sigs}"
    print("OK: Stream A e Stream B combaciano con i valori attesi calcolati a mano.")


if __name__ == "__main__":
    main()
