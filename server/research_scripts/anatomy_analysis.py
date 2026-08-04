#!/usr/bin/env python3
"""
NQROS v3.1 Fase 2 (Anatomia): sul miglior TF di ogni strategia sopravvissuta
alla Fase 1 (multi_tf_baseline.py), guarda PERCHE' vince e perde - non
solo il PF aggregato. Usa mae_r/mfe_r per trade (gia' in backtest.py) +
motivo di uscita (SL/TP/TIME) + durata.

Obiettivo: dati per la Fase 0 (Bottleneck Analysis), non un altro numero di
PF. Le domande a cui questo script risponde per strategia:
  - Le perdite sono "segnale sbagliato" (MFE basso, mai andato a favore) o
    "quasi vincenti" (MFE alto, girate poco prima del target)?
  - Le vincite escono per TP o per TIME (max_hold raggiunto prima del TP)?
  - Quanto durano in media vincite vs perdite (barre)?

Esegui dalla root del repo: python3 server/research_scripts/anatomy_analysis.py
"""
import sys
sys.path.insert(0, "server")
import backtest as bt

COSTS = bt.COST_PRESETS["retail_standard"]

# Sopravvissuti Fase 1 (>=15 trade sul miglior TF, PF>1 nel batch baseline
# multi_tf_baseline.py) - profilo di default, NON quello gia' "toccato" con
# htf_filter/confirm_bars di prima (quello era fuori protocollo).
CANDIDATES = [
    ("FVG_CONT", "1wk"), ("MACD", "1wk"), ("THREE_BAR_DELIVERY_BREAK", "4h"),
    ("IFVG", "4h"), ("SAR", "1wk"), ("ADX_RSI", "1wk"),
    ("AMD_CONT", "4h"), ("SILVER_BULLET", "4h"), ("LIQ_VOID", "1wk"),
]


def bars_between(t1, t2, tf):
    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M"
    d1, d2 = datetime.strptime(t1, fmt), datetime.strptime(t2, fmt)
    hours = (d2 - d1).total_seconds() / 3600.0
    per_bar_hours = {"1wk": 168, "1d": 24, "4h": 4, "1h": 1}.get(tf, 24)
    return round(hours / per_bar_hours, 1)


def main():
    for strat, tf in CANDIDATES:
        r = bt.run_backtest(symbol="XAUUSD", strategy=strat, timeframe=tf, **COSTS)
        trades = r["trade_list"]
        if not trades:
            print(f"\n{strat} ({tf}): nessun trade, salto.")
            continue
        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] < 0]

        def avg(lst, key):
            return round(sum(x[key] for x in lst) / len(lst), 2) if lst else None

        reasons_win = {}
        reasons_loss = {}
        for t in wins:
            reasons_win[t["reason"]] = reasons_win.get(t["reason"], 0) + 1
        for t in losses:
            reasons_loss[t["reason"]] = reasons_loss.get(t["reason"], 0) + 1

        dur_wins = [bars_between(t["openTime"], t["closeTime"], tf) for t in wins]
        dur_losses = [bars_between(t["openTime"], t["closeTime"], tf) for t in losses]
        avg_dur_w = round(sum(dur_wins) / len(dur_wins), 1) if dur_wins else None
        avg_dur_l = round(sum(dur_losses) / len(dur_losses), 1) if dur_losses else None

        # classificazione perdite: "segnale sbagliato" (mfe<0.3) vs
        # "quasi vincente" (mfe>=0.5, giro tardi) vs intermedio
        wrong_signal = sum(1 for t in losses if t["mfe_r"] < 0.3)
        near_miss = sum(1 for t in losses if t["mfe_r"] >= 0.5)
        mid = len(losses) - wrong_signal - near_miss

        print(f"\n{'=' * 90}\n{strat} ({tf}) — PF {r['profit_factor']}, {r['trades']} trade, WR {r['win_rate']}%")
        print(f"{'=' * 90}")
        print(f"  Uscite vincenti per motivo: {reasons_win}   (durata media: {avg_dur_w} barre)")
        print(f"  Uscite perdenti per motivo: {reasons_loss}   (durata media: {avg_dur_l} barre)")
        print(f"  MFE medio vincite: {avg(wins, 'mfe_r')}R   MAE medio vincite: {avg(wins, 'mae_r')}R")
        print(f"  MFE medio perdite: {avg(losses, 'mfe_r')}R  (diagnostico: quanto andavano a favore prima di girare)")
        if losses:
            print(f"  Perdite 'segnale sbagliato' (MFE<0.3R): {wrong_signal}/{len(losses)} "
                  f"({round(100*wrong_signal/len(losses))}%)")
            print(f"  Perdite 'quasi vincenti' (MFE>=0.5R):   {near_miss}/{len(losses)} "
                  f"({round(100*near_miss/len(losses))}%)")
            print(f"  Perdite intermedie:                     {mid}/{len(losses)}")


if __name__ == "__main__":
    main()
