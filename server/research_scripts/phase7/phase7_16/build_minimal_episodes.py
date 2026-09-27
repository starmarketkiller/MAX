#!/usr/bin/env python3
"""Phase 7.16 punto 3 - episodi minimi (1 reale + 3 sintetici) che
dimostrano il meccanismo esatto della divergenza causale (touched su
bars[i] vs bars[i+1]) con input congelati e valori attesi derivati A
MANO (aritmetica sui numeri grezzi), NON facendo girare le funzioni
sotto verifica - stessa disciplina gia' applicata in Phase 7.9K/7.13.

Episodio 1 (REALE, dati locali gia' disponibili, nessun nuovo run):
  prima divergenza causale trovata in build_first_divergence.py, bar
  D1 indice 49 (2023-12-07 -> 2023-12-08), lato BUY.
Episodi 2-4 (SINTETICI, minimi, per isolare la regola generale nelle
  due direzioni + un controllo negativo dove le due versioni
  concordano).
"""
import os
import sys

PHASE716_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE716_DIR, "..", "phase7_13"))
ROOT = os.path.abspath(os.path.join(PHASE716_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, PHASE713_DIR)
from nxs_order_block_replica import OBState, ob_update_side  # noqa: E402

sys.path.insert(0, PHASE716_DIR)
from nxs_order_block_replica_corrected import ob_update_side_corrected  # noqa: E402


def _bar(o, h, l, c, ot, ct):
    return {"open": o, "high": h, "low": l, "close": c, "open_time": ot, "close_time": ct}


def _make_active_zone_state(ob_lo, ob_hi, bars_waited=0, last_bar_time="PREV"):
    st = OBState()
    st.active, st.ob_lo, st.ob_hi, st.bars_waited = True, ob_lo, ob_hi, bars_waited
    st.last_bar_time = last_bar_time
    return st


EPISODES = []

# --- Episodio 1: REALE, D1 GOLD, bar D1 indice 49, lato BUY -----------------
# Zona BUY attiva: ob_lo=1989.72, ob_hi=1998.38 (creata prima, dati locali).
# bar[49] (shift1, "ieri", chiusa 2023-12-08): O=2025.56 H=2039.79 L=2020.09 C=2028.39
# bar[50] (shift0, "oggi", in formazione): O=2028.26 H=2033.93 L=1994.5 C=2004.2
# ORIGINALE (touched su bar[49]): low(2020.09) > ob_hi(1998.38) -> NESSUNA sovrapposizione -> touched=False -> WAITING_NO_TOUCH.
# CORRETTO (touched su bar[50]): low(1994.5) <= ob_hi(1998.38) E high(2033.93) >= ob_lo(1989.72) -> sovrapposizione -> touched=True.
#   rejection (SEMPRE su bar[49], invariata): c1(2028.39) > o1(2025.56) -> True (BUY) -> RETEST_SIGNAL_FIRED.
EP1_BARS = [
    _bar(2025.56, 2039.79, 2020.09, 2028.39, "2023-12-07T01:00:00", "2023-12-08T01:00:00"),  # bar[49] = shift1 = "bars[i]"
    _bar(2028.26, 2033.93, 1994.5, 2004.2, "2023-12-08T01:00:00", "2023-12-11T01:00:00"),      # bar[50] = shift0 = "bars[i+1]"
]
EPISODES.append({
    "id": "EP1_REAL_D1_GOLD_bar49_BUY",
    "source": "Dati LOCALI reali gia' disponibili (phase7_13/multi_tf_dataset_v1.json, D1 "
             "indice 49-50) - nessun nuovo run/download",
    "direction": "BUY",
    "atr_at_this_point": 28.31355110210303,
    "input_common": {"ob_lo": 1989.72, "ob_hi": 1998.38, "bar_shift1_bars_i": EP1_BARS[0],
                     "bar_shift0_bars_i_plus_1": EP1_BARS[1]},
    "state_initial": {"active": True, "ob_lo": 1989.72, "ob_hi": 1998.38, "bars_waited": 4,
                      "last_bar_time": "2023-12-07T01:00:00"},
    "hand_derivation": {
        "original_touched_check": "usa bar[i]=bar[49]: low=2020.09 > ob_hi=1998.38 -> "
                                  "NESSUNA sovrapposizione con [1989.72, 1998.38] -> "
                                  "touched=False",
        "original_expected_op": "WAITING_NO_TOUCH",
        "corrected_touched_check": "usa bar[i+1]=bar[50]: low=1994.5 <= ob_hi=1998.38 E "
                                   "high=2033.93 >= ob_lo=1989.72 -> sovrapposizione -> "
                                   "touched=True",
        "rejection_check_shared": "c1(bar[49].close=2028.39) > o1(bar[49].open=2025.56) -> "
                                  "True (candela di rigetto rialzista) - INVARIATA in "
                                  "entrambe le versioni",
        "corrected_expected_op": "RETEST_SIGNAL_FIRED, segnale BUY",
    },
    "ea_real_trace_confirms": "L'EA reale post-fix (Phase 7.14) NON ha un evento esattamente "
                              "il 2023-12-08 nel trace curato - questo episodio dimostra il "
                              "MECCANISMO della divergenza fra le due ricostruzioni Python, "
                              "non un confronto diretto con l'EA su questa specifica data "
                              "(vedi punto 2 per il confronto aggregato EA vs Python corretto).",
})

# --- Episodio 2 (sintetico): l'ORIGINALE spara, il CORRETTO no (SELL) -------
# Zona SELL attiva [100,105]. bar[i] (shift1) tocca E chiude ribassista ->
# ORIGINALE spara. bar[i+1] (shift0) NON tocca -> CORRETTO non spara.
EP2_BARS_SHIFT1 = _bar(106.0, 107.0, 99.0, 104.0, "T0", "T1")   # tocca [100,105], chiude ribassista (104<106)
EP2_BARS_SHIFT0 = _bar(110.0, 112.0, 108.0, 111.0, "T1", "T2")  # NON tocca (low 108 > ob_hi 105)
EPISODES.append({
    "id": "EP2_SYNTHETIC_original_fires_corrected_does_not_SELL",
    "source": "Sintetico, minimo, calcolabile a mano",
    "direction": "SELL",
    "atr_at_this_point": 1.0,
    "input_common": {"ob_lo": 100.0, "ob_hi": 105.0,
                     "bar_shift1_bars_i": EP2_BARS_SHIFT1, "bar_shift0_bars_i_plus_1": EP2_BARS_SHIFT0},
    "state_initial": {"active": True, "ob_lo": 100.0, "ob_hi": 105.0, "bars_waited": 0, "last_bar_time": "PREV"},
    "hand_derivation": {
        "original_touched_check": "usa bar[i]: low=99.0<=105.0 e high=107.0>=100.0 -> "
                                  "sovrapposizione -> touched=True",
        "rejection_check_shared": "c1(104.0) < o1(106.0) -> True (candela di rigetto "
                                  "ribassista, SELL) - INVARIATA",
        "original_expected_op": "RETEST_SIGNAL_FIRED, segnale SELL",
        "corrected_touched_check": "usa bar[i+1]: low=108.0 > ob_hi=105.0 -> NESSUNA "
                                   "sovrapposizione -> touched=False",
        "corrected_expected_op": "WAITING_NO_TOUCH (nessun segnale, zona resta attiva)",
    },
    "consequence": "L'ORIGINALE produce un segnale SPURIO (basato sul range di IERI, gia' "
                  "superato) che il CORRETTO non produce - coerente con la scoperta che "
                  "l'ORIGINALE produce piu' 'solo in Python' rispetto all'EA reale "
                  "(Phase 7.14/7.15) rispetto al CORRETTO.",
})

# --- Episodio 3 (sintetico): il CORRETTO spara, l'ORIGINALE no (BUY) -------
# bar[i] (shift1): NON tocca la zona (sopra ob_hi, non sotto ob_lo - se fosse
# sotto ob_lo attiverebbe ANCHE l'invalidazione, che usa la stessa barra
# shift1 e andrebbe a mascherare l'effetto che vogliamo isolare) ma E'
# comunque una candela di rigetto rialzista (close>open).
EP3_BARS_SHIFT1 = _bar(106.0, 108.0, 105.5, 107.0, "T0", "T1")  # NON tocca (low 105.5 > ob_hi 105); rigetto rialzista (107>106); c1=107 non invalida (107 non < ob_lo=100)
EP3_BARS_SHIFT0 = _bar(103.0, 104.5, 102.0, 104.0, "T1", "T2")  # tocca [100,105]
EPISODES.append({
    "id": "EP3_SYNTHETIC_corrected_fires_original_does_not_BUY",
    "source": "Sintetico, minimo, calcolabile a mano",
    "direction": "BUY",
    "atr_at_this_point": 1.0,
    "input_common": {"ob_lo": 100.0, "ob_hi": 105.0,
                     "bar_shift1_bars_i": EP3_BARS_SHIFT1, "bar_shift0_bars_i_plus_1": EP3_BARS_SHIFT0},
    "state_initial": {"active": True, "ob_lo": 100.0, "ob_hi": 105.0, "bars_waited": 0, "last_bar_time": "PREV"},
    "hand_derivation": {
        "newbar_invalidation_check_first": "c1(bar[i].close=107.0) < ob_lo(100.0)? NO -> "
                                           "zona NON invalidata (bar[i] e' sopra la zona, "
                                           "non sotto - scelto cosi' apposta per non far "
                                           "scattare l'invalidazione, che userebbe la "
                                           "stessa barra e maschererebbe l'effetto da "
                                           "isolare)",
        "original_touched_check": "usa bar[i]: low=105.5 > ob_hi=105.0 -> NESSUNA "
                                  "sovrapposizione -> touched=False",
        "original_expected_op": "WAITING_NO_TOUCH",
        "corrected_touched_check": "usa bar[i+1]: low=102.0<=105.0 e high=104.5>=100.0 -> "
                                   "sovrapposizione -> touched=True",
        "rejection_check_shared": "c1(bar[i].close=107.0) > o1(bar[i].open=106.0) -> True "
                                  "(candela di rigetto rialzista) - INVARIATA, usa sempre "
                                  "bar[i]",
        "corrected_expected_op": "RETEST_SIGNAL_FIRED, segnale BUY",
    },
    "consequence": "Speculare all'Episodio 2: qui e' il CORRETTO a produrre un segnale che "
                  "l'ORIGINALE perde - stessa forma dell'Episodio 1 (reale) con numeri "
                  "tondi per una verifica a mano piu' agevole.",
})

# --- Episodio 4 (controllo negativo): nessuna divergenza (entrambe concordano) --
# bar[i] E bar[i+1] toccano ENTRAMBE la zona -> touched=True in entrambe le
# versioni indipendentemente da quale barra si usi - dimostra che la
# correzione non altera SEMPRE l'esito, solo quando le due barre disaccordano
# sulla sovrapposizione con la zona.
EP4_BARS_SHIFT1 = _bar(103.0, 104.5, 102.0, 104.0, "T0", "T1")  # tocca [100,105], rigetto rialzista (104>103)
EP4_BARS_SHIFT0 = _bar(102.0, 103.0, 101.0, 102.5, "T1", "T2")  # anch'essa tocca [100,105]
EPISODES.append({
    "id": "EP4_NEGATIVE_CONTROL_both_agree_BUY",
    "source": "Sintetico, minimo, calcolabile a mano - CONTROLLO NEGATIVO",
    "direction": "BUY",
    "atr_at_this_point": 1.0,
    "input_common": {"ob_lo": 100.0, "ob_hi": 105.0,
                     "bar_shift1_bars_i": EP4_BARS_SHIFT1, "bar_shift0_bars_i_plus_1": EP4_BARS_SHIFT0},
    "state_initial": {"active": True, "ob_lo": 100.0, "ob_hi": 105.0, "bars_waited": 0, "last_bar_time": "PREV"},
    "hand_derivation": {
        "original_touched_check": "usa bar[i]: low=102.0<=105.0 e high=104.5>=100.0 -> "
                                  "touched=True",
        "corrected_touched_check": "usa bar[i+1]: low=101.0<=105.0 e high=103.0>=100.0 -> "
                                   "touched=True (STESSO esito di sovrapposizione, "
                                   "entrambe le barre sono dentro la zona)",
        "rejection_check_shared": "c1(bar[i].close=104.0) > o1(bar[i].open=103.0) -> True "
                                  "(BUY) - INVARIATA",
        "original_expected_op": "RETEST_SIGNAL_FIRED, segnale BUY",
        "corrected_expected_op": "RETEST_SIGNAL_FIRED, segnale BUY (STESSO esito "
                                 "dell'originale)",
    },
    "consequence": "CONFERMA che la correzione non e' un cambiamento sistematico che "
                  "altera SEMPRE l'esito - le due versioni concordano quando la barra di "
                  "ieri e quella di oggi si trovano ENTRAMBE dentro la zona (il caso piu' "
                  "comune quando il prezzo si muove poco da un giorno all'altro); "
                  "divergono solo quando le due barre disaccordano sulla sovrapposizione "
                  "con la zona (Episodi 1-3).",
})


def build():
    payload = {
        "method": "1 episodio REALE (dati locali gia' disponibili) + 3 episodi SINTETICI "
                 "minimi, calcolabili a mano, con valori attesi derivati indipendentemente "
                 "(aritmetica sui numeri grezzi, non dalla stessa funzione sotto verifica) - "
                 "vedi EP4 per l'unica eccezione dichiarata esplicitamente.",
        "episodes": EPISODES,
        "n_episodes": len(EPISODES),
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE716_DIR, "minimal_episodes_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  episodi: {payload['n_episodes']}")


if __name__ == "__main__":
    main()
