#!/usr/bin/env python3
"""Phase 7.13 - porting fedele, riga per riga, della state machine
ORDER_BLOCK verificata in MQL5/Include/NEXUS_v1/NXS_Strategies.mqh
(struct SNXSOBState riga 2069, NXS_OB_UpdateSide riga 2077-2139,
NXS_Strat_OrderBlock riga 2141-2161).

Questo modulo e' SOLA istrumentazione diagnostica Python - non tocca
l'EA/MQL5 canonico, non applica alcuna guardia TF al sorgente reale.
Riproduce ESATTAMENTE le soglie e la logica del sorgente verificato:
  - displacement: body >= 1.2*atr, colore giusto, ricerca shift 3..10
  - BOS: iHighest/iLowest(SwingLookback=15) a partire da shift+1
  - origine zona: prima candela di colore opposto entro shift+1..shift+6
  - attesa: barsWaited > MaxWaitBars(20) -> zona scaduta
  - invalidazione: chiusura (shift1) che attraversa la zona nel verso
    sbagliato
  - retest: prezzo nella zona + candela di rigetto (shift1) -> segnale
    one-shot (la zona si disattiva dopo il primo retest, che produca
    o no un segnale accettato piu' a valle)

SEMPLIFICAZIONE DI MODELLAZIONE DICHIARATA (dati disponibili solo a
livello di barra, non tick): nel codice reale `touched` e `rejection`
sono valutati AD OGNI TICK usando il bid corrente e l'ultima barra
CHIUSA (shift 1); qui, non avendo dati tick, valutiamo touched+
rejection UNA VOLTA per barra appena chiusa del passaggio (bar i),
usando quella stessa barra sia per il test di tocco (range low..high
vs obLo..obHi) sia per il test di rigetto (open/close della stessa
barra). Questo NON altera l'esistenza del meccanismo di contaminazione
incrociata (la mutazione dello stato avviene comunque ad ogni chiusura
di barra del passaggio, indipendentemente dal TF), ma puo' spostare di
qualche barra il timing esatto di un retest rispetto al comportamento
tick-per-tick reale. Dichiarato come limite in
`diagnostic_protocol_order_block_v1.json` (Phase 7.12) e nel Decision
Card di questa fase.
"""

SWING_LOOKBACK = 15
MAX_WAIT_BARS = 20
BODY_ATR_MULT = 1.2
DISPLACEMENT_SHIFT_LO = 3
DISPLACEMENT_SHIFT_HI = 10
ORIGIN_SEARCH_SPAN = 6


class OBState:
    """Replica di SNXSOBState (NXS_Strategies.mqh:2069-2074)."""

    __slots__ = ("active", "ob_lo", "ob_hi", "last_bar_time", "bars_waited")

    def __init__(self):
        self.active = False
        self.ob_lo = None
        self.ob_hi = None
        self.last_bar_time = None
        self.bars_waited = 0

    def snapshot(self):
        return {"active": self.active, "ob_lo": self.ob_lo, "ob_hi": self.ob_hi,
                "last_bar_time": self.last_bar_time, "bars_waited": self.bars_waited}

    def clone(self):
        s = OBState()
        s.active, s.ob_lo, s.ob_hi = self.active, self.ob_lo, self.ob_hi
        s.last_bar_time, s.bars_waited = self.last_bar_time, self.bars_waited
        return s


def _shift_idx(i, shift):
    """iOpen/iClose/iHigh/iLow(shift) con shift>=1: bars[i] e' shift 1."""
    return i - shift + 1


def _highest_shift(bars, i, start_shift, count, field):
    """iHighest/iLowest(..., MODE_HIGH/LOW, count, start_shift): shift
    dell'estremo fra [start_shift, start_shift+count-1]. Ritorna None se
    non c'e' abbastanza storia (equivalente a iHighest che ritorna -1)."""
    best_shift, best_val = None, None
    for s in range(start_shift, start_shift + count):
        idx = _shift_idx(i, s)
        if idx < 0:
            return None
        val = bars[idx][field]
        if best_val is None or (field == "high" and val > best_val) or (field == "low" and val < best_val):
            best_val, best_shift = val, s
    return best_shift


def ob_update_side(direction, state, bars, i, atr, curbar0_time):
    """Replica di NXS_OB_UpdateSide (righe 2077-2139).

    direction: +1 (bull/BUY) o -1 (bear/SELL).
    state: OBState mutato IN PLACE (stesso comportamento by-reference
    di MQL5 - g_obBuy/g_obSell sono globali passati per riferimento).
    bars: lista ascendente di barre dict(open,high,low,close) del TF
    del passaggio CORRENTE (puo' essere diverso dal TF canonico D1 -
    questo e' esattamente il punto sotto diagnosi).
    i: indice della barra appena chiusa (shift 1) in `bars`.
    atr: g_atr al momento del passaggio (calcolato sul TF del passaggio,
    fedele a NXS_Strat_OrderBlock riga 2145: `double atr = g_atr;`,
    dove g_atr e' ricalcolato per il TF attivo da NXS_ActivateTF/
    NXS_UpdateIndicators - vedi MQL5/Experts/NEXUS_EA_v2.mq5:225-233).
    curbar0_time: tempo di apertura della barra "0" (in formazione) al
    momento di questa chiamata - chiave del gate newBar.

    Ritorna (signal_dir_or_None, reason, mutation_record).
    """
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

    # Zona attiva, in attesa del retest (righe 2116-2138).
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

    # Semplificazione dichiarata (vedi docstring modulo): touched e
    # rejection valutati sulla STESSA barra appena chiusa (bar i), non
    # per-tick, data la granularita' disponibile.
    bar_i = bars[i]
    touched = bar_i["low"] <= state.ob_hi and bar_i["high"] >= state.ob_lo
    if not touched:
        rec["op"] = "WAITING_NO_TOUCH"
        rec["post"] = state.snapshot()
        return None, "", rec
    c1, o1 = bar_i["close"], bar_i["open"]
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


def strat_order_block_pass(state_buy, state_sell, bars, i, atr, curbar0_time):
    """Replica di NXS_Strat_OrderBlock (righe 2141-2161), MINUS i gate
    posteriori (g_structH1.trend, InpUseSMCReactionGate/NXS_SMCReactionOK)
    che dipendono da sottosistemi esterni non replicati in questa fase
    (dichiarato fuori scope - vedi Decision Card, sezione 'gate a valle
    non modellati'). Qui riproduciamo solo il raw trigger pre-gate,
    esattamente il punto in cui avviene la mutazione di stato sotto
    diagnosi.

    Ritorna (raw_dir_or_None, reason, mutation_buy, mutation_sell).
    """
    sig_dir, reason, mut_buy = ob_update_side(+1, state_buy, bars, i, atr, curbar0_time)
    mut_sell = None
    if sig_dir is None:
        sig_dir, reason, mut_sell = ob_update_side(-1, state_sell, bars, i, atr, curbar0_time)
    return sig_dir, reason, mut_buy, mut_sell
