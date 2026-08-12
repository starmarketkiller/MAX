#!/usr/bin/env python3
"""
12/08 - NEXUS Optimization Desk: uscite strutturali (SL/TP, breakeven, trailing)
su CRT e FVG_CONT, richiesto dall'utente con uno script architetturale di
riferimento. Adattato qui al vero `run_backtest()` (non un df/params dict:
il motore fetcha i dati da solo via symbol/timeframe/bars/bar_range e prende
atr_sl/atr_tp/breakeven_r/trailing_atr come kwargs diretti - gia' esistenti,
mai spazzolati insieme con un filtro IS anti-overfitting). Chiavi vere del
risultato: profit_factor/trades/max_dd_pct (non total_trades/max_drawdown).

ATTENZIONE CRT (verificato leggendo _open_position()/STRATEGY_SLTP_ALWAYS
prima di lanciare la griglia): la sua SL/TP e' SEMPRE quella ancorata al
wick/sweep (_crt_sl_tp), non atr_sl/atr_tp - il vettore "asimmetria SL/TP"
non ha ALCUN effetto sui suoi ingressi. Sweepare comunque sl/tp per CRT
avrebbe prodotto risultati identici ripetuti 9 volte, sprecando tempo
macchina. Per CRT si sweepano solo breakeven_r x trailing_atr (2 vettori,
non 3) - fissati a sl=1.5/tp=3.0 (valori inerti, mai usati dal motore per
questa strategia).

Nota su trailing_atr: NON e' un trigger a R come "trailing_stop_R" nello
script di riferimento suggeriva (attivato solo dopo aver raggiunto 1R) - e'
una distanza di trailing in multipli di ATR, SEMPRE attiva dalla prima barra
della posizione quando > 0 (vedi execution loop in run_backtest). Stesso
concetto ("insegue il trend"), meccanica diversa - riportato qui cosi' i
numeri si leggono con la semantica giusta, non quella ipotizzata.

Dataset: locale 2019-2026 (in-process, NON l'endpoint del sito). CRT a 30m
con migliaia di trade per finestra avrebbe quasi certamente ripetuto i 502
gia' documentati su Render per richieste pesanti a bassa TF (vedi vault
"Riverifica via Sito su Storico Esteso 2016-2026", 12/08) - e il campione
locale e' gia' enorme per questo scopo (~4700 trade OOS CRT). Il vincitore
finale, se solido, si puo' sempre far confermare dal sito in un secondo
passaggio mirato (una sola combinazione, non 100+).

Metodo: baseline OOS (sl=1.5/tp=3.0/be=0/trail=0) per confronto. Per ogni
combinazione: filtro IS (pf>1.10 e n>50, come nello script di riferimento)
prima di spendere una chiamata OOS. Il miglior candidato che batte il
baseline OOS viene poi riverificato con walk-forward a 5 finestre (baseline
compreso), perche' un solo IS/OOS non basta a fidarsi (disciplina di tutta
la sessione).
"""
import sys
import os
import itertools

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

BARS = 110000
IS_RANGE, OOS_RANGE = (0.0, 0.6), (0.6, 1.0)
N_WINDOWS = 5

TARGETS = {
    "CRT": {"symbol": "XAUUSD", "timeframe": "30m", "sweep_sltp": False},
    "FVG_CONT": {"symbol": "XAUUSD", "timeframe": "4h", "sweep_sltp": True},
}

# Griglia larga, passi strutturali (non micro-tuning) - stessa richiesta dell'utente
SL_GRID = [1.0, 1.5, 2.0]
TP_GRID = [2.0, 3.0, 4.0]
BE_GRID = [0.0, 1.0, 1.5]
TRAIL_GRID = [0.0, 1.0]

MIN_IS_PF = 1.10
MIN_IS_TRADES = 50


def call(symbol, timeframe, strategy, bar_range, sl, tp, be, trail):
    return bt.run_backtest(symbol=symbol, timeframe=timeframe, strategy=strategy,
                            strategies=[strategy], risk_pct=1.0, bars=BARS,
                            bar_range=bar_range, atr_sl=sl, atr_tp=tp,
                            breakeven_r=be, trailing_atr=trail)


def combos(sweep_sltp):
    sl_grid = SL_GRID if sweep_sltp else [1.5]
    tp_grid = TP_GRID if sweep_sltp else [3.0]
    for sl, tp, be, trail in itertools.product(sl_grid, tp_grid, BE_GRID, TRAIL_GRID):
        # BE oltre il TP in multipli di R e' irraggiungibile - filtro logico
        # dello script originale, ha senso solo dove tp/sl sono in gioco.
        if sweep_sltp and be > 0 and be >= (tp / sl):
            continue
        yield sl, tp, be, trail


def walk_forward(symbol, timeframe, strategy, sl, tp, be, trail):
    out = []
    for w in range(N_WINDOWS):
        br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
        r = call(symbol, timeframe, strategy, br, sl, tp, be, trail)
        out.append((r.get("profit_factor"), r.get("trades")))
    return out


def main():
    print("NEXUS - OPTIMIZATION DESK: uscite e multipli", flush=True)
    for strat, cfg in TARGETS.items():
        symbol, tf, sweep_sltp = cfg["symbol"], cfg["timeframe"], cfg["sweep_sltp"]
        print(f"\n{'='*72}\n{strat} @ {tf}  "
              f"(SL/TP sweep: {'si' if sweep_sltp else 'NO - override strutturale (wick/sweep) attivo'})"
              f"\n{'='*72}", flush=True)

        base_oos = call(symbol, tf, strat, OOS_RANGE, 1.5, 3.0, 0.0, 0.0)
        print(f"BASELINE OOS: pf={base_oos.get('profit_factor')} n={base_oos.get('trades')} "
              f"dd={base_oos.get('max_dd_pct')}%", flush=True)

        best = None
        tested = 0
        for sl, tp, be, trail in combos(sweep_sltp):
            tested += 1
            is_r = call(symbol, tf, strat, IS_RANGE, sl, tp, be, trail)
            pf_is = is_r.get("profit_factor") or 0
            if pf_is <= MIN_IS_PF or is_r.get("trades", 0) <= MIN_IS_TRADES:
                continue
            oos_r = call(symbol, tf, strat, OOS_RANGE, sl, tp, be, trail)
            pf_oos = oos_r.get("profit_factor") or 0
            print(f"  sl={sl} tp={tp} be={be} trail={trail} -> "
                  f"IS pf={pf_is} n={is_r.get('trades')} | "
                  f"OOS pf={pf_oos} n={oos_r.get('trades')} dd={oos_r.get('max_dd_pct')}%", flush=True)
            if pf_oos > (base_oos.get("profit_factor") or 0) and (best is None or pf_oos > best["oos_pf"]):
                best = {"sl": sl, "tp": tp, "be": be, "trail": trail, "oos_pf": pf_oos,
                        "oos_n": oos_r.get("trades"), "oos_dd": oos_r.get("max_dd_pct"),
                        "is_pf": pf_is, "is_n": is_r.get("trades")}

        print(f"-- combinazioni testate: {tested}", flush=True)
        if not best:
            print("-- Nessuna combinazione batte il baseline OOS sopravvivendo al filtro IS.", flush=True)
            continue
        print(f"-- MIGLIOR CANDIDATO: {best}", flush=True)
        print("-- walk-forward di verifica (5 finestre) candidato vs baseline...", flush=True)
        wf = walk_forward(symbol, tf, strat, best["sl"], best["tp"], best["be"], best["trail"])
        wf_base = walk_forward(symbol, tf, strat, 1.5, 3.0, 0.0, 0.0)
        print("   candidato: " + "  |  ".join(f"{pf}/{n}" for pf, n in wf), flush=True)
        print("   baseline:  " + "  |  ".join(f"{pf}/{n}" for pf, n in wf_base), flush=True)


if __name__ == "__main__":
    main()
