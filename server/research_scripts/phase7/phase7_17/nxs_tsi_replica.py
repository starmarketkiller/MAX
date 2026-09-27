#!/usr/bin/env python3
"""Phase 7.17 - porting fedele, riga per riga, di NXS_Strat_TSI()
(MQL5/Include/NEXUS_v1/NXS_Strategies.mqh:1354-1414). Istrumentazione
diagnostica Python - non tocca l'EA/MQL5 canonico.
"""

LONG_PERIOD = 25
SHORT_PERIOD = 13
SIGNAL_PERIOD = 7
A_LONG = 2.0 / (LONG_PERIOD + 1.0)
A_SHORT = 2.0 / (SHORT_PERIOD + 1.0)
A_SIG = 2.0 / (SIGNAL_PERIOD + 1.0)
WARMUP_BARS = LONG_PERIOD * 3


class TSIState:
    __slots__ = ("init", "last_bar_time", "sm1", "sm2", "sm1_abs", "sm2_abs",
                "signal", "tsi_prev", "signal_prev", "prev_close", "bars_seen")

    def __init__(self):
        self.init = False
        self.last_bar_time = None
        self.sm1 = 0.0
        self.sm2 = 0.0
        self.sm1_abs = 0.0
        self.sm2_abs = 0.0
        self.signal = 0.0
        self.tsi_prev = 0.0
        self.signal_prev = 0.0
        self.prev_close = 0.0
        self.bars_seen = 0

    def snapshot(self):
        return {k: getattr(self, k) for k in self.__slots__}


def tsi_update(state, c1, curbar0_time, seed_close):
    """Replica di NXS_Strat_TSI (minus il gate InpStrat_TSI/selettore,
    valutato dal chiamante). `seed_close` = iClose(tf,2) al momento
    della PRIMISSIMA chiamata (usato solo se state.init era False)."""
    rec = {"pre": state.snapshot(), "mutated": False}
    if not state.init:
        state.init = True
        state.prev_close = seed_close
        state.last_bar_time = None  # equivalente a 0 in MQL5: sempre != a un vero curBar0
        state.bars_seen = 0

    if state.last_bar_time != curbar0_time:
        rec["mutated"] = True
        state.tsi_prev = (100.0 * state.sm2 / state.sm2_abs) if state.sm2_abs > 0 else 0.0
        state.signal_prev = state.signal

        pc = c1 - state.prev_close
        apc = abs(pc)
        state.sm1 = pc * A_LONG + state.sm1 * (1.0 - A_LONG)
        state.sm1_abs = apc * A_LONG + state.sm1_abs * (1.0 - A_LONG)
        state.sm2 = state.sm1 * A_SHORT + state.sm2 * (1.0 - A_SHORT)
        state.sm2_abs = state.sm1_abs * A_SHORT + state.sm2_abs * (1.0 - A_SHORT)
        tsi_now = (100.0 * state.sm2 / state.sm2_abs) if state.sm2_abs > 0 else 0.0
        state.signal = tsi_now * A_SIG + state.signal * (1.0 - A_SIG)

        state.prev_close = c1
        state.last_bar_time = curbar0_time
        state.bars_seen += 1

    sig_dir = None
    if state.bars_seen >= WARMUP_BARS:
        tsi = (100.0 * state.sm2 / state.sm2_abs) if state.sm2_abs > 0 else 0.0
        signal = state.signal
        cross_up = (state.tsi_prev <= state.signal_prev) and (tsi > signal)
        cross_down = (state.tsi_prev >= state.signal_prev) and (tsi < signal)
        if cross_up:
            sig_dir = "BUY"
        elif cross_down:
            sig_dir = "SELL"
        rec["tsi"] = tsi
        rec["signal_line"] = signal

    rec["post"] = state.snapshot()
    rec["signal_dir"] = sig_dir
    return sig_dir, rec
