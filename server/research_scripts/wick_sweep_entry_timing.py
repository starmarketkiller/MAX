"""WICK_SWEEP_REV - studio timing di ingresso, v2 (10/09).

FIX rispetto a v1 (wick_sweep_entry_timing.py): v1 trattava OGNI wick H4
qualificante come un livello INDIPENDENTE E PERMANENTE, mai rimosso - risultato
18232 "trigger" nella sola finestra Fast Smoke contro i 181 realmente visti
dal vivo (fattore ~100x). Causa: _NXS_WickSweep_UpdateLevel() nella strategia
reale mantiene UN SOLO livello attivo per lato (alto/basso): ogni nuova wick
H4 qualificante SOSTITUISCE il livello precedente, anche se non ancora
sweeppato - un livello vecchio "dimenticato" non puo' piu' generare touch.

Questa v2 replica ESATTAMENTE quella semantica: simulazione sequenziale
(non piu' un loop per-livello indipendente) che tiene traccia del SOLO
livello attivo per lato, aggiornato ogni barra H4 esattamente come dal vivo.
Un cambio di livello attivo AZZERA qualunque episodio di touch in corso su
quello vecchio (esattamente come dal vivo: NXS_Strat_WickSweepReversal legge
SOLO g_wickHigh/g_wickLow correnti, mai una wick precedente).

Tutto il resto (trigger a 35 pip, i 6 entry model, SL25/TP100 baseline,
niente lookahead) resta come in v1.
"""
from __future__ import annotations
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, ".")
from struct_level_sweep_dataset import load_m15, resample_ohlc, PIP, WICK_MIN_PIPS
from wick_sweep_entry_timing import wilder_atr, find_micro_swings_m15, simulate_sl_tp, ATR_LEN, SWEEP_PIPS, HORIZON_DAYS, BARS_PER_DAY_M15, MAX_TOUCHES_PER_LEVEL, RETEST_WINDOW_BARS, RETEST_TOL_PIPS


def build_active_level_series(h4, min_pips):
    """Replica _NXS_WickSweep_UpdateLevel bar per bar: un solo livello attivo
    per lato, sostituito (non accumulato) a ogni nuova wick qualificante.
    Ritorna, per ogni barra H4, level_id/price attivo per lato (level_id
    incrementa a ogni SOSTITUZIONE, cosi' un cambio e' rilevabile)."""
    min_dist = min_pips * PIP
    n = len(h4)
    high_price = np.full(n, np.nan)
    high_id = np.full(n, -1, dtype=int)
    high_created = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    low_price = np.full(n, np.nan)
    low_id = np.full(n, -1, dtype=int)
    low_created = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")

    cur_high_price, cur_high_id, cur_high_created = np.nan, -1, pd.NaT
    cur_low_price, cur_low_id, cur_low_created = np.nan, -1, pd.NaT
    next_id = 0
    opens = h4["open"].values; closes = h4["close"].values
    highs = h4["high"].values; lows = h4["low"].values
    times = h4.index

    for i in range(n):
        body_top = max(opens[i], closes[i]); body_bot = min(opens[i], closes[i])
        upper_wick = highs[i] - body_top
        lower_wick = body_bot - lows[i]
        created_at = times[i] + pd.Timedelta(hours=4)   # chiusura di QUESTA barra H4
        if upper_wick >= min_dist:
            cur_high_price = highs[i]; cur_high_id = next_id; next_id += 1; cur_high_created = created_at
        if lower_wick >= min_dist:
            cur_low_price = lows[i]; cur_low_id = next_id; next_id += 1; cur_low_created = created_at
        # il livello aggiornato in QUESTA barra vale da created_at in poi, quindi
        # lo registriamo a partire dalla barra i+1 (niente lookahead sulla i corrente)
        if i + 1 < n:
            high_price[i + 1] = cur_high_price; high_id[i + 1] = cur_high_id; high_created[i + 1] = cur_high_created
            low_price[i + 1] = cur_low_price; low_id[i + 1] = cur_low_id; low_created[i + 1] = cur_low_created
    return dict(high_price=high_price, high_id=high_id, high_created=high_created,
                low_price=low_price, low_id=low_id, low_created=low_created)


def main():
    global h4_ohlc_open, h4_ohlc_close, micro_swing_low, micro_swing_high

    m15 = load_m15()
    print(f"M15: {len(m15)} barre")
    h4 = resample_ohlc(m15, "4h", origin="start_day")
    atr_h4 = wilder_atr(h4, ATR_LEN)
    active = build_active_level_series(h4, WICK_MIN_PIPS)
    print(f"H4: {len(h4)} barre. Livelli distinti generati (con sostituzione, come dal vivo): "
          f"alto={active['high_id'].max()+1}, basso={active['low_id'].max()+1}")

    m15_times = m15.index.values
    m15_high = m15["high"].values
    m15_low = m15["low"].values
    m15_close = m15["close"].values
    n = len(m15_times)
    h4_times_idx = h4.index
    h4_ohlc_open = h4["open"].values
    h4_ohlc_close = h4["close"].values
    atr_h4_vals = atr_h4.values
    horizon_bars = int(HORIZON_DAYS * BARS_PER_DAY_M15)

    print("Calcolo micro-swing M15 (wing=2)...")
    micro_swing_low, micro_swing_high = find_micro_swings_m15(m15_high, m15_low, wing=2)

    # mappa ogni barra M15 all'indice H4 corrente (barra H4 in corso in quel momento)
    h4_pos_for_m15 = np.searchsorted(h4_times_idx.values, m15_times, side="right") - 1
    h4_pos_for_m15 = np.clip(h4_pos_for_m15, 0, len(h4) - 1)

    all_rows = []
    trigger_dist = SWEEP_PIPS * PIP

    for side, price_arr, id_arr, created_arr, direction in [
        ("high", active["high_price"], active["high_id"], active["high_created"], "SELL"),
        ("low", active["low_price"], active["low_id"], active["low_created"], "BUY"),
    ]:
        print(f"--- lato {side} ({direction}) ---")
        cur_id = -1
        touch_active = False
        ep_start_idx = None
        touch_number = 0
        already_triggered_this_level = False

        i = 0
        while i < n:
            h4pos = h4_pos_for_m15[i]
            level_id = id_arr[h4pos]
            level_price = price_arr[h4pos]
            if level_id != cur_id:
                # nuovo livello attivo (o nessuno): reset completo dello stato, come dal vivo
                cur_id = level_id
                touch_active = False
                touch_number = 0
                already_triggered_this_level = False
            if level_id < 0 or pd.isna(level_price):
                i += 1
                continue

            breach = (m15_high[i] - level_price) if direction == "SELL" else (level_price - m15_low[i])
            if not touch_active:
                if breach >= 0:
                    touch_active = True
                    ep_start_idx = i
                    touch_number += 1
                i += 1
                continue

            # in un episodio di touch sul livello CORRENTE - cerca il trigger (35 pip) UNA VOLTA per livello
            if breach >= trigger_dist and not already_triggered_this_level and touch_number <= MAX_TOUCHES_PER_LEVEL:
                already_triggered_this_level = True
                trigger_idx = i
                created_at = pd.Timestamp(created_arr[h4pos])
                row = build_trigger_row(level_id, level_price, direction, created_at, touch_number,
                                         trigger_idx, m15_times, m15_high, m15_low, m15_close,
                                         h4_times_idx, atr_h4_vals, n, horizon_bars, trigger_dist,
                                         id_arr, h4_pos_for_m15)
                if row is not None:
                    all_rows.append(row)
            # fine episodio: se il prezzo torna sotto il livello (per SELL) o sopra (per BUY), l'episodio si chiude
            # e un nuovo touch potra' iniziare - ma resta lo STESSO livello (nessun cambio id)
            if breach < 0:
                touch_active = False
            i += 1

    ev = pd.DataFrame(all_rows)
    print(f"\nTrigger events totali (v2, un livello attivo per lato): {len(ev)}")
    ev.to_csv("wick_sweep_entry_timing_events_v2.csv", index=False)
    print("Scritto wick_sweep_entry_timing_events_v2.csv")


def build_trigger_row(level_id, price, direction, created_at, touch_number, trigger_idx,
                       m15_times, m15_high, m15_low, m15_close, h4_times_idx, atr_h4_vals,
                       n, horizon_bars, trigger_dist, id_arr, h4_pos_for_m15):
    trigger_price = (price + trigger_dist) if direction == "SELL" else (price - trigger_dist)
    penetration_at_trigger = trigger_dist / PIP   # per definizione, il trigger scatta appena si supera 35 pip

    # il livello resta "attivo" (per il resto del calcolo: reclaim/reversal/entry models)
    # finche' non viene sostituito - troviamo fino a dove id_arr resta invariato
    end_bound = min(trigger_idx + horizon_bars, n - 1)
    same_level = id_arr[h4_pos_for_m15[trigger_idx:end_bound + 1]] == level_id
    if not same_level.all():
        last_same = trigger_idx + int(np.flatnonzero(~same_level)[0]) - 1
        end_bound = max(trigger_idx, last_same)
    level_replaced_before_horizon = end_bound < min(trigger_idx + horizon_bars, n - 1)

    breach_arr_local = (m15_high[trigger_idx:end_bound + 1] - price) if direction == "SELL" else (price - m15_low[trigger_idx:end_bound + 1])
    if len(breach_arr_local) == 0:
        return None
    max_pen_after_idx = trigger_idx + int(breach_arr_local.argmax())
    max_penetration_after = float(breach_arr_local.max()) / PIP
    max_additional_penetration = max_penetration_after - penetration_at_trigger
    time_to_max_pen_h = (pd.Timestamp(m15_times[max_pen_after_idx]) - pd.Timestamp(m15_times[trigger_idx])) / np.timedelta64(1, "h")

    if direction == "SELL":
        reclaim_level_mask = m15_close[trigger_idx:end_bound + 1] <= price
        reclaim_trigger_mask = m15_close[trigger_idx:end_bound + 1] <= trigger_price
    else:
        reclaim_level_mask = m15_close[trigger_idx:end_bound + 1] >= price
        reclaim_trigger_mask = m15_close[trigger_idx:end_bound + 1] >= trigger_price
    rl = np.flatnonzero(reclaim_level_mask)
    rt = np.flatnonzero(reclaim_trigger_mask)
    reclaim_level_idx = trigger_idx + int(rl[0]) if rl.size else None
    reclaim_trigger_idx = trigger_idx + int(rt[0]) if rt.size else None
    time_to_reclaim_level_h = ((pd.Timestamp(m15_times[reclaim_level_idx]) - pd.Timestamp(m15_times[trigger_idx])) / np.timedelta64(1, "h")) if reclaim_level_idx is not None else np.nan
    time_to_reclaim_trigger_h = ((pd.Timestamp(m15_times[reclaim_trigger_idx]) - pd.Timestamp(m15_times[trigger_idx])) / np.timedelta64(1, "h")) if reclaim_trigger_idx is not None else np.nan

    h4_pos = h4_pos_for_m15[trigger_idx]
    atr_h4 = atr_h4_vals[h4_pos] if 0 <= h4_pos < len(atr_h4_vals) else np.nan

    rev_times = {}
    if pd.notna(atr_h4):
        for mult, label in [(0.25, "0.25ATR"), (0.5, "0.5ATR"), (1.0, "1ATR")]:
            target = mult * atr_h4
            if direction == "SELL":
                fav = trigger_price - m15_low[trigger_idx:end_bound + 1]
            else:
                fav = m15_high[trigger_idx:end_bound + 1] - trigger_price
            hit = np.flatnonzero(fav >= target)
            rev_times[label] = ((pd.Timestamp(m15_times[trigger_idx + int(hit[0])]) - pd.Timestamp(m15_times[trigger_idx])) / np.timedelta64(1, "h")) if hit.size else np.nan
    else:
        rev_times = {"0.25ATR": np.nan, "0.5ATR": np.nan, "1ATR": np.nan}

    row = dict(
        level_id=level_id, level_price=price, direction=direction, source="WICK_H4", source_tf="H4",
        created_at=created_at, touch_number=touch_number,
        age_at_trigger_hours=round((pd.Timestamp(m15_times[trigger_idx]) - created_at) / np.timedelta64(1, "h"), 2),
        trigger_time=pd.Timestamp(m15_times[trigger_idx]), trigger_price=trigger_price,
        penetration_at_trigger_pips=round(penetration_at_trigger, 2),
        max_additional_penetration_after_trigger_pips=round(max_additional_penetration, 2),
        time_to_max_penetration_hours=round(time_to_max_pen_h, 2),
        time_to_first_reclaim_level_hours=round(time_to_reclaim_level_h, 2) if pd.notna(time_to_reclaim_level_h) else np.nan,
        time_to_reclaim_trigger_price_hours=round(time_to_reclaim_trigger_h, 2) if pd.notna(time_to_reclaim_trigger_h) else np.nan,
        time_to_reversal_0_25ATR_hours=round(rev_times["0.25ATR"], 2) if pd.notna(rev_times["0.25ATR"]) else np.nan,
        time_to_reversal_0_5ATR_hours=round(rev_times["0.5ATR"], 2) if pd.notna(rev_times["0.5ATR"]) else np.nan,
        time_to_reversal_1ATR_hours=round(rev_times["1ATR"], 2) if pd.notna(rev_times["1ATR"]) else np.nan,
        atr_h4_at_trigger_pips=round(atr_h4 / PIP, 2) if pd.notna(atr_h4) else np.nan,
        level_replaced_before_horizon=bool(level_replaced_before_horizon),
    )

    outcome, _ = simulate_sl_tp(trigger_idx, trigger_price, direction, m15_high, m15_low, horizon_bars)
    row["IMMEDIATE_FADE_available"] = True
    row["IMMEDIATE_FADE_entry_price"] = trigger_price
    row["IMMEDIATE_FADE_entry_delay_hours"] = 0.0
    row["IMMEDIATE_FADE_outcome"] = outcome

    if reclaim_level_idx is not None:
        outcome, _ = simulate_sl_tp(reclaim_level_idx, price, direction, m15_high, m15_low, horizon_bars)
        row.update({"RECLAIM_LEVEL_available": True, "RECLAIM_LEVEL_entry_price": price,
                    "RECLAIM_LEVEL_entry_delay_hours": time_to_reclaim_level_h, "RECLAIM_LEVEL_outcome": outcome})
    else:
        row.update({"RECLAIM_LEVEL_available": False, "RECLAIM_LEVEL_entry_price": np.nan,
                    "RECLAIM_LEVEL_entry_delay_hours": np.nan, "RECLAIM_LEVEL_outcome": "NO_ENTRY"})

    if reclaim_trigger_idx is not None:
        outcome, _ = simulate_sl_tp(reclaim_trigger_idx, trigger_price, direction, m15_high, m15_low, horizon_bars)
        row.update({"RECLAIM_TRIGGER_available": True, "RECLAIM_TRIGGER_entry_price": trigger_price,
                    "RECLAIM_TRIGGER_entry_delay_hours": time_to_reclaim_trigger_h, "RECLAIM_TRIGGER_outcome": outcome})
    else:
        row.update({"RECLAIM_TRIGGER_available": False, "RECLAIM_TRIGGER_entry_price": np.nan,
                    "RECLAIM_TRIGGER_entry_delay_hours": np.nan, "RECLAIM_TRIGGER_outcome": "NO_ENTRY"})

    h4_after = h4_times_idx[(h4_times_idx > pd.Timestamp(m15_times[trigger_idx])) & (h4_times_idx <= h4_times_idx[min(h4_pos + 20, len(h4_times_idx)-1)])]
    reaction_entry_time = reaction_entry_price = None
    for h4t in h4_after:
        h4_idx = h4_times_idx.get_loc(h4t)
        if id_arr[h4_idx] != level_id:
            break   # il livello e' stato sostituito - la reazione non ha piu' senso su questo livello
        o, c = h4_ohlc_open[h4_idx], h4_ohlc_close[h4_idx]
        is_reversal = (c < o) if direction == "SELL" else (c > o)
        if is_reversal:
            next_h4_idx = h4_idx + 1
            if next_h4_idx >= len(h4_times_idx):
                break
            reaction_entry_time = h4_times_idx[next_h4_idx]
            reaction_entry_price = h4_ohlc_open[next_h4_idx]
            break
    if reaction_entry_time is not None:
        entry_m15_idx = np.searchsorted(m15_times, np.datetime64(reaction_entry_time), side="left")
        if entry_m15_idx < n:
            outcome, _ = simulate_sl_tp(entry_m15_idx, reaction_entry_price, direction, m15_high, m15_low, horizon_bars)
            row.update({"REACTION_CANDLE_available": True, "REACTION_CANDLE_entry_price": reaction_entry_price,
                        "REACTION_CANDLE_entry_delay_hours": (reaction_entry_time - pd.Timestamp(m15_times[trigger_idx])) / np.timedelta64(1, "h"),
                        "REACTION_CANDLE_outcome": outcome})
        else:
            row.update({"REACTION_CANDLE_available": False, "REACTION_CANDLE_outcome": "NO_ENTRY"})
    else:
        row.update({"REACTION_CANDLE_available": False, "REACTION_CANDLE_entry_price": np.nan,
                    "REACTION_CANDLE_entry_delay_hours": np.nan, "REACTION_CANDLE_outcome": "NO_ENTRY"})

    micro_idx = None
    for j in range(trigger_idx, end_bound + 1):
        ref = micro_swing_low[j] if direction == "SELL" else micro_swing_high[j]
        if pd.isna(ref):
            continue
        broke = (m15_close[j] < ref) if direction == "SELL" else (m15_close[j] > ref)
        if broke:
            micro_idx = j
            break
    if micro_idx is not None and micro_idx + 1 < n:
        entry_i = micro_idx + 1
        entry_p = m15_close[micro_idx]
        outcome, _ = simulate_sl_tp(entry_i, entry_p, direction, m15_high, m15_low, horizon_bars)
        row.update({"MICRO_STRUCTURE_SHIFT_available": True, "MICRO_STRUCTURE_SHIFT_entry_price": entry_p,
                    "MICRO_STRUCTURE_SHIFT_entry_delay_hours": (pd.Timestamp(m15_times[micro_idx]) - pd.Timestamp(m15_times[trigger_idx])) / np.timedelta64(1, "h"),
                    "MICRO_STRUCTURE_SHIFT_outcome": outcome})
    else:
        row.update({"MICRO_STRUCTURE_SHIFT_available": False, "MICRO_STRUCTURE_SHIFT_entry_price": np.nan,
                    "MICRO_STRUCTURE_SHIFT_entry_delay_hours": np.nan, "MICRO_STRUCTURE_SHIFT_outcome": "NO_ENTRY"})

    if reclaim_level_idx is not None:
        retest_end = min(reclaim_level_idx + RETEST_WINDOW_BARS, end_bound)
        tol = RETEST_TOL_PIPS * PIP
        retest_idx = None
        for j in range(reclaim_level_idx + 1, retest_end + 1):
            dist = (price - m15_high[j]) if direction == "SELL" else (m15_low[j] - price)
            if abs(dist) <= tol:
                retest_idx = j
                break
        if retest_idx is not None:
            outcome, _ = simulate_sl_tp(retest_idx, price, direction, m15_high, m15_low, horizon_bars)
            row.update({"LIMIT_RETEST_available": True, "LIMIT_RETEST_entry_price": price,
                        "LIMIT_RETEST_entry_delay_hours": (pd.Timestamp(m15_times[retest_idx]) - pd.Timestamp(m15_times[trigger_idx])) / np.timedelta64(1, "h"),
                        "LIMIT_RETEST_outcome": outcome})
        else:
            row.update({"LIMIT_RETEST_available": False, "LIMIT_RETEST_entry_price": np.nan,
                        "LIMIT_RETEST_entry_delay_hours": np.nan, "LIMIT_RETEST_outcome": "NO_ENTRY"})
    else:
        row.update({"LIMIT_RETEST_available": False, "LIMIT_RETEST_entry_price": np.nan,
                    "LIMIT_RETEST_entry_delay_hours": np.nan, "LIMIT_RETEST_outcome": "NO_ENTRY"})

    return row


if __name__ == "__main__":
    main()
