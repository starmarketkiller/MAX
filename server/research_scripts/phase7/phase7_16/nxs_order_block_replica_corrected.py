#!/usr/bin/env python3
"""Phase 7.16 - versione CORRETTA di ob_update_side, isolata rispetto
all'originale (server/research_scripts/phase7/phase7_13/
nxs_order_block_replica.py, congelato e MAI modificato) per non
alterare un artifact storico.

UNICA DIFFERENZA rispetto all'originale: il test 'touched' usa
bars[i+1] (la barra che si sta formando al momento della valutazione,
shift 0 - quella durante la quale il bid live dell'EA si muoverebbe
davvero) invece di bars[i] (la barra appena chiusa, shift 1 - gia'
usata per 'rejection', per costruzione un giorno troppo indietro).
Tutto il resto (displacement, BOS, origine, invalidazione, scadenza,
rejection) e' IDENTICO all'originale, incluso l'array-shift helper.

Vedi vault "NEXUS - Phase 7.16 Semantic Contract e Fedelta' Python"
per la dimostrazione causale completa.
"""
import os
import sys

PHASE716_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE713_DIR = os.path.abspath(os.path.join(PHASE716_DIR, "..", "phase7_13"))
sys.path.insert(0, PHASE713_DIR)
from nxs_order_block_replica import (  # noqa: E402
    OBState, SWING_LOOKBACK, MAX_WAIT_BARS, BODY_ATR_MULT,
    DISPLACEMENT_SHIFT_LO, DISPLACEMENT_SHIFT_HI, ORIGIN_SEARCH_SPAN,
    _shift_idx, _highest_shift,
)


def ob_update_side_corrected(direction, state, bars, i, atr, curbar0_time):
    """Identica a ob_update_side() dell'originale (Phase 7.13) in ogni
    ramo TRANNE il test 'touched', che qui usa bars[i+1] (shift 0,
    barra in formazione) invece di bars[i] (shift 1, barra chiusa)."""
    new_bar = (state.last_bar_time != curbar0_time)
    rec = {
        "pre": state.snapshot(), "new_bar": new_bar, "op": "NONE",
        "signal_dir": None, "signal_reason": "",
    }

    if not state.active:
        if not new_bar:
            rec["post"] = state.snapshot()
            return None, "", rec
        state.last_bar_time = curbar0_time
        rec["op"] = "SEARCH_DISPLACEMENT_NO_MATCH"
        for shift in range(DISPLACEMENT_SHIFT_LO, DISPLACEMENT_SHIFT_HI + 1):
            idx = _shift_idx(i, shift)
            if idx < 0:
                continue
            o, c = bars[idx]["open"], bars[idx]["close"]
            body = abs(c - o)
            if body < BODY_ATR_MULT * atr:
                continue
            right_color = (c > o) if direction == 1 else (c < o)
            if not right_color:
                continue
            hi_shift = _highest_shift(bars, i, shift + 1, SWING_LOOKBACK, "high")
            lo_shift = _highest_shift(bars, i, shift + 1, SWING_LOOKBACK, "low")
            if direction == 1:
                swing_ref = bars[_shift_idx(i, hi_shift)]["high"] if hi_shift is not None else 0
                bos = swing_ref > 0 and c > swing_ref
            else:
                swing_ref = bars[_shift_idx(i, lo_shift)]["low"] if lo_shift is not None else 0
                bos = swing_ref > 0 and c < swing_ref
            if not bos:
                continue
            origin_a, origin_b, found = o, c, False
            for k in range(shift + 1, shift + ORIGIN_SEARCH_SPAN + 1):
                kidx = _shift_idx(i, k)
                if kidx < 0:
                    break
                ok, ck = bars[kidx]["open"], bars[kidx]["close"]
                opposite = (ck < ok) if direction == 1 else (ck > ok)
                if opposite:
                    origin_a, origin_b, found = ok, ck, True
                    break
            if not found:
                continue
            state.ob_lo = min(origin_a, origin_b)
            state.ob_hi = max(origin_a, origin_b)
            state.active = True
            state.bars_waited = 0
            rec["op"] = "ZONE_CREATED"
            break
        rec["post"] = state.snapshot()
        return None, "", rec

    if new_bar:
        state.last_bar_time = curbar0_time
        state.bars_waited += 1
        if state.bars_waited > MAX_WAIT_BARS:
            state.active = False
            rec["op"] = "ZONE_EXPIRED"
            rec["post"] = state.snapshot()
            return None, "", rec
        c1 = bars[_shift_idx(i, 1)]["close"]
        invalidated = (direction == 1 and c1 < state.ob_lo) or (direction == -1 and c1 > state.ob_hi)
        if invalidated:
            state.active = False
            rec["op"] = "ZONE_INVALIDATED"
            rec["post"] = state.snapshot()
            return None, "", rec

    if state.ob_hi is None or state.ob_hi <= state.ob_lo:
        rec["op"] = "DEGENERATE_ZONE_SKIP"
        rec["post"] = state.snapshot()
        return None, "", rec

    # --- CORREZIONE (unica differenza rispetto all'originale): 'touched'
    # usa la barra in FORMAZIONE al momento della valutazione (shift 0,
    # bars[i+1] nello storico completo disponibile offline), non la barra
    # gia' chiusa (shift 1, bars[i]) - fedele a MT5, dove 'bid' e' il
    # prezzo LIVE del tick corrente durante la formazione della barra di
    # OGGI (NXS_Strategies.mqh riga 2126), mentre 'rejection' resta
    # correttamente su shift 1 (barra di IERI, NXS_Strategies.mqh riga
    # 2129 - iClose/iOpen(tf,1), INVARIATO qui).
    if i + 1 < len(bars):
        forming_bar = bars[i + 1]
        touched = forming_bar["low"] <= state.ob_hi and forming_bar["high"] >= state.ob_lo
    else:
        touched = False  # nessuna barra futura nota (fine serie) - non causale conoscerla comunque
    if not touched:
        rec["op"] = "WAITING_NO_TOUCH"
        rec["post"] = state.snapshot()
        return None, "", rec
    c1, o1 = bars[i]["close"], bars[i]["open"]   # rejection INVARIATA: shift 1
    rejection = (c1 > o1) if direction == 1 else (c1 < o1)
    if not rejection:
        rec["op"] = "TOUCHED_NO_REJECTION"
        rec["post"] = state.snapshot()
        return None, "", rec

    state.active = False
    rec["op"] = "RETEST_SIGNAL_FIRED"
    rec["post"] = state.snapshot()
    sig_dir = "BUY" if direction == 1 else "SELL"
    reason = "OB_retest_bull" if direction == 1 else "OB_retest_bear"
    rec["signal_dir"] = sig_dir
    rec["signal_reason"] = reason
    return sig_dir, reason, rec
