#!/usr/bin/env python3
"""
10/08 (4) - richiesta esplicita dell'utente: non testare solo le 3
strategie che sono andate bene (MACD/TURTLE_SOUP/BREAKOUT_ACC), ma tutto
il pool (incluse quelle deboli/mai brillate), e costruire un vero motore
a voto con ~10-15 strategie insieme - non coppie/triple isolate come
nella Fase 2, non 2-3 strategie "buone" scelte a mano.

Due parti:
1. baseline IS/OOS per TUTTE le strategie attive del registro
   (bars=60000, storico Dukascopy pieno post-fix) - il quadro onesto
   completo, non solo i vincitori gia' noti.
2. ricerca GREEDY (non esaustiva - C(35,15) e' intrattabile) di un
   ensemble a voto: si parte vuoti, ad ogni round si aggiunge la
   strategia che migliora di piu' il punteggio in-sample dell'engine a
   voto, si ferma quando la dimensione target e' raggiunta o i
   miglioramenti si esauriscono.

10/08 (5) - parametrizzato (symbol/tf/bars non piu' costanti globali)
per riuso su altri mercati (BTCUSD) e generalizzato con due varianti
opzionali richieste dall'utente dopo il primo esito negativo su oro:
- voto PESATO (peso = PF individuale IS della strategia, non 1 voto
  ciascuna) invece di uniforme;
- filtro di REGIME (_regime_series gia' esistente in backtest.py) sopra
  l'ensemble trovato, per vedere se filtrare per regime di mercato
  aiuta un ensemble che a voto pieno non batte la singola migliore.
"""
import sys
import os
import time
import json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
import bt_verdict

MIN_TRADES = 8
START_EQUITY = 10000.0
RISK_PCT = 1.0
MAX_HOLD = 40
ATR_SL, ATR_TP = 1.5, 3.0
TARGET_SIZE = 15
ENSEMBLE_MIN_TRADES = 20


def pool_for(symbol):
    reg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                             "contracts", "strategy-registry.json")
    reg = json.load(open(reg_path, encoding="utf-8"))
    active = [x["strategy_id"] for x in reg["strategies"]
              if x.get("research_implementation") and x.get("status") == "ACTIVE"]
    return sorted(s for s in active if s in bt.STRATEGIES)


# --------------------------------------------------------------------- #
# Parte 1: baseline individuale IS/OOS per tutto il pool
# --------------------------------------------------------------------- #
def baseline_all(pool, symbol, tf, bars):
    results = []
    for strat in pool:
        row = {"strategy": strat}
        for label, br in [("is", (0.0, 0.6)), ("oos", (0.6, 1.0))]:
            try:
                r = bt.run_backtest(symbol=symbol, timeframe=tf, strategy=strat, strategies=[strat],
                                     risk_pct=RISK_PCT, atr_sl=ATR_SL, atr_tp=ATR_TP,
                                     start_equity=START_EQUITY, bar_range=br, bars=bars)
            except Exception as e:
                row[label] = {"error": str(e)[:60]}
                continue
            n = r.get("trades", 0)
            pf = r.get("profit_factor") or 0.0
            exp = r.get("expectancy_r", 0.0)
            v, why = bt_verdict._verdict(
                {"executed": n, "profit_factor": pf, "expectancy_R": exp,
                 "winrate_pct": r.get("win_rate", 0), "setup": n}, MIN_TRADES)
            row[label] = {"trades": n, "pf": round(pf, 2), "verdict": v}
        results.append(row)
    return results


def print_baseline(base):
    base_sorted = sorted(base, key=lambda r: (r.get("oos", {}).get("pf") or 0), reverse=True)
    print(f"{'Strategia':<26}{'IS PF':>7}{'IS n':>6}{'IS V':>9}   {'OOS PF':>7}{'OOS n':>6}{'OOS V':>9}")
    for r in base_sorted:
        i, o = r.get("is", {}), r.get("oos", {})
        print(f"{r['strategy']:<26}{i.get('pf','-'):>7}{i.get('trades','-'):>6}{i.get('verdict','-'):>9}   "
              f"{o.get('pf','-'):>7}{o.get('trades','-'):>6}{o.get('verdict','-'):>9}")


# --------------------------------------------------------------------- #
# Parte 2: motore a voto - precompute dei segnali per velocita'
# --------------------------------------------------------------------- #
def load_slice(symbol, tf, bars, frac_range):
    candles, src = bt._fetch_real(symbol, tf, bars=bars)
    n = len(candles)
    i0, i1 = int(n * frac_range[0]), int(n * frac_range[1])
    candles = candles[i0:i1]
    intraday = bt._load_dukascopy_m15(symbol) if src == "dukascopy" else None
    ind = bt._prep(candles, intraday_ref=intraday)
    return candles, ind


def precompute_signals(candles, ind, pool):
    sigs = {}
    for s in pool:
        fn = bt.STRATEGIES[s]
        sigs[s] = [fn(candles, ind, i) for i in range(len(candles))]
    return sigs


def simulate(candles, ind, sigs, combo, min_votes, weights=None, regime_ok=None):
    """weights: dict strategia->peso (default 1.0 ciascuna, voto uniforme).
    regime_ok: se dato, set di codici regime (_REGIME_*) in cui e' permesso
    aprire - il resto del bar viene ignorato anche se i voti bastano."""
    atr = ind["atr"]
    regime = ind.get("regime") if regime_ok is not None else None
    equity = START_EQUITY
    trades = []
    position = None
    for i in range(60, len(candles)):
        px = candles[i]["close"]
        if position is not None:
            hi, lo = candles[i]["high"], candles[i]["low"]
            hit = None
            if position["dir"] == 1:
                if lo <= position["sl"]:
                    hit = ("SL", position["sl"])
                elif hi >= position["tp"]:
                    hit = ("TP", position["tp"])
            else:
                if hi >= position["sl"]:
                    hit = ("SL", position["sl"])
                elif lo <= position["tp"]:
                    hit = ("TP", position["tp"])
            if not hit and (i - position["open_i"]) >= MAX_HOLD:
                hit = ("TIME", px)
            if hit:
                _, exitpx = hit
                rd = position["risk_dist"] if position["risk_dist"] > 0 else 1e-9
                r_mult = ((exitpx - position["entry"]) / rd) if position["dir"] == 1 \
                    else ((position["entry"] - exitpx) / rd)
                pnl = round(r_mult * position["risk_money"], 2)
                equity += pnl
                trades.append({"pnl": pnl, "r": r_mult})
                position = None
            continue
        a = atr[i]
        if not a:
            continue
        if regime_ok is not None and regime[i] not in regime_ok:
            continue
        if weights:
            votes = sum(sigs[s][i] * weights.get(s, 1.0) for s in combo)
        else:
            votes = sum(sigs[s][i] for s in combo)
        if votes >= min_votes:
            dir_ = 1
        elif votes <= -min_votes:
            dir_ = -1
        else:
            continue
        entry = px
        sl_dist = a * ATR_SL
        tp_dist = a * ATR_TP
        sl = entry - sl_dist if dir_ == 1 else entry + sl_dist
        tp = entry + tp_dist if dir_ == 1 else entry - tp_dist
        position = {"dir": dir_, "entry": entry, "sl": sl, "tp": tp, "open_i": i,
                    "risk_dist": sl_dist, "risk_money": equity * (RISK_PCT / 100.0)}
    gw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gl = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gw / gl, 2) if gl > 0 else (None if gw == 0 else float("inf"))
    exp_r = round(sum(t["r"] for t in trades) / len(trades), 3) if trades else 0.0
    return {"trades": len(trades), "pf": pf, "exp_r": exp_r,
            "net": round(equity - START_EQUITY, 2)}


def score(res):
    """10/08 (2) - PRIMA VERSIONE (bug): premiava il PF grezzo con soglia
    a 8 trade -> la ricerca greedy convergeva su strategie troppo rare
    per giudicare, PF in-sample fino a 9.51 su 8-20 trade, OOS in perdita.
    Corretto: punteggio = expectancy_R * sqrt(trade), soglia dura a
    ENSEMBLE_MIN_TRADES=20 - vedi nota di modulo per il dettaglio."""
    if res["pf"] is None or res["trades"] < ENSEMBLE_MIN_TRADES:
        return -999
    return res["exp_r"] * (res["trades"] ** 0.5)


def robust_pool(baseline, min_is_trades=30):
    """Esclude le strategie troppo magre anche a periodo intero e i proxy
    duplicati (LIQ_VOID==FVG_CONT, RANGE_FADE==BOLLINGER) - non esclude
    le strategie deboli/CRITICA, quelle restano nel pool di proposito."""
    DUPES = {"LIQ_VOID", "RANGE_FADE"}
    keep = []
    for row in baseline:
        sid = row["strategy"]
        if sid in DUPES:
            continue
        is_n = row.get("is", {}).get("trades", 0)
        if isinstance(is_n, int) and is_n >= min_is_trades:
            keep.append(sid)
    return sorted(keep)


def greedy_search(pool, symbol, tf, bars, weights=None):
    candles_is, ind_is = load_slice(symbol, tf, bars, (0.0, 0.6))
    candles_oos, ind_oos = load_slice(symbol, tf, bars, (0.6, 1.0))
    sigs_is = precompute_signals(candles_is, ind_is, pool)
    sigs_oos = precompute_signals(candles_oos, ind_oos, pool)

    # bug 10/08: partiva da 2, ma con un combo di 1 strategia i voti
    # possono valere al massimo il peso di quella sola strategia -
    # nessuna soglia >=2 era mai raggiungibile al primo round.
    VOTE_THRESHOLDS = [1, 2, 3, 4, 5, 6]
    if weights:
        # con pesi non-interi le soglie fisse vanno scalate sul range
        # tipico dei pesi (PF individuali, in genere 0.5-2.5)
        VOTE_THRESHOLDS = [0.5, 1, 1.5, 2, 3, 4, 5, 6, 8]
    combo = []
    history = []
    remaining = list(pool)

    while remaining and len(combo) < TARGET_SIZE:
        best = None
        for cand in remaining:
            trial = combo + [cand]
            for mv in VOTE_THRESHOLDS:
                res_is = simulate(candles_is, ind_is, sigs_is, trial, mv, weights=weights)
                sc = score(res_is)
                if best is None or sc > best["score"]:
                    best = {"cand": cand, "mv": mv, "score": sc, "is": res_is}
        if best is None or best["score"] <= -900:
            break
        combo.append(best["cand"])
        res_oos = simulate(candles_oos, ind_oos, sigs_oos, combo, best["mv"], weights=weights)
        history.append({"size": len(combo), "added": best["cand"], "min_votes": best["mv"],
                         "is": best["is"], "oos": res_oos, "combo": list(combo)})
        remaining.remove(best["cand"])
        print(f"[{len(combo)}] +{best['cand']:<18} mv={best['mv']} "
              f"IS pf={best['is']['pf']} n={best['is']['trades']}   "
              f"OOS pf={res_oos['pf']} n={res_oos['trades']}", flush=True)

    return history


def main(symbol="XAUUSD", tf="4h", bars=60000, out_name="ensemble_engine_results.json"):
    pool = pool_for(symbol)
    print(f"=== Parte 1: baseline individuale ({symbol} {tf}, pool completo: {len(pool)}) ===", flush=True)
    t0 = time.time()
    base = baseline_all(pool, symbol, tf, bars)
    print(f"fatto in {time.time()-t0:.0f}s\n", flush=True)
    print_baseline(base)

    pool2 = robust_pool(base, min_is_trades=30)
    print(f"\nPool per l'ensemble (>=30 trade IS, deduplicato): {len(pool2)} strategie")
    print(", ".join(pool2))

    print("\n=== Parte 2: ricerca greedy dell'ensemble a voto ===", flush=True)
    hist = greedy_search(pool2, symbol, tf, bars)

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), out_name)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"symbol": symbol, "tf": tf, "baseline": base, "pool_ensemble": pool2, "greedy": hist}, f, indent=2)
    print(f"\nSalvato: {out_path}")
    return base, pool2, hist


if __name__ == "__main__":
    main()
