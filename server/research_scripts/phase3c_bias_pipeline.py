#!/usr/bin/env python3
"""
10/08 - Fase 3c: test "pipeline gerarchica" (master decide il bias, slave
esegue solo se allineata) proposto come alternativa al majority-vote della
Fase 2 (accordo UNANIME sulla stessa barra - troppo restrittivo, nessuna
combo ha mai battuto le singole).

Differenza chiave rispetto al voto: qui il bias del master PERSISTE (rimane
l'ultimo segnale non-zero del master) finche' non si inverte, non deve
scattare sulla stessa barra dello slave. Master = BREAKOUT_ACC (il candidato
piu' cross-validato della sessione). Slave = pool di strategie, incluse
alcune "magre" (AMD_REVERSAL, esempio dato dall'utente) per vedere se il
bias recupera operativita' senza sacrificare il PF.

Confronto isolato: stessa identica gestione (ATR SL/TP 1.5/3.0, stesso
rischio%, stesso MAX_HOLD) tra "slave da sola" e "slave filtrata dal bias
del master" - l'unica variabile che cambia e' il filtro, cosi' la differenza
misurata e' SOLO l'effetto del bias, non altre discrepanze di motore.

Split in-sample (60%)/out-of-sample(40%) come nel resto della Fase 2/3.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as bt
import majority_vote_combo as mv

SYMBOL = "XAUUSD"
TF = "4h"
MASTER = "BREAKOUT_ACC"


def _all_slaves():
    """Tutte le strategie ATTIVE del registro canonico con implementazione
    Python, escluso il master stesso - non solo un sottoinsieme scelto a
    mano. LIQ_VOID resta inclusa deliberatamente anche se e' un proxy
    letterale di FVG_CONT (stessa funzione, server/backtest.py:3311): i due
    risultati usciranno identici, ed e' informativo vederlo confermato qui
    invece di escluderlo silenziosamente."""
    import json
    reg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..",
                             "contracts", "strategy-registry.json")
    reg = json.load(open(reg_path, encoding="utf-8"))
    active = [x["strategy_id"] for x in reg["strategies"]
              if x.get("research_implementation") and x.get("status") == "ACTIVE"]
    return sorted(s for s in active if s != MASTER and s in bt.STRATEGIES)


SLAVES = _all_slaves()
MIN_OOS_TRADES = 5


def _load(frac_range):
    candles, src = bt._fetch_real(SYMBOL, TF)
    n = len(candles)
    i0, i1 = int(n * frac_range[0]), int(n * frac_range[1])
    candles = candles[i0:i1]
    intraday = bt._load_dukascopy_m15(SYMBOL) if src == "dukascopy" else None
    ind = bt._prep(candles, intraday_ref=intraday)
    return candles, ind


def _simulate(candles, ind, entry_fn):
    """entry_fn(i) -> -1/0/1 di direzione da aprire su quella barra (gia'
    filtrata secondo la logica scelta). Stessa gestione posizione/uscita
    per tutte le varianti, cosi' la sola differenza e' entry_fn."""
    atr = ind["atr"]
    equity = mv.START_EQUITY
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
            if not hit and (i - position["open_i"]) >= mv.MAX_HOLD:
                hit = ("TIME", px)
            if hit:
                _, exitpx = hit
                rd = position["risk_dist"] if position["risk_dist"] > 0 else 1e-9
                r_mult = ((exitpx - position["entry"]) / rd) if position["dir"] == 1 \
                    else ((position["entry"] - exitpx) / rd)
                pnl = round(r_mult * position["risk_money"], 2)
                equity += pnl
                trades.append({"pnl": pnl})
                position = None
            continue
        a = atr[i]
        if not a:
            continue
        dir_ = entry_fn(i)
        if dir_ not in (1, -1):
            continue
        entry = px
        sl_dist = a * 1.5
        tp_dist = a * 3.0
        sl = entry - sl_dist if dir_ == 1 else entry + sl_dist
        tp = entry + tp_dist if dir_ == 1 else entry - tp_dist
        position = {"dir": dir_, "entry": entry, "sl": sl, "tp": tp, "open_i": i,
                    "risk_dist": sl_dist, "risk_money": equity * (mv.RISK_PCT / 100.0)}
    gw = sum(t["pnl"] for t in trades if t["pnl"] > 0)
    gl = -sum(t["pnl"] for t in trades if t["pnl"] < 0)
    pf = round(gw / gl, 2) if gl > 0 else (None if gw == 0 else float("inf"))
    wr = round(100 * sum(1 for t in trades if t["pnl"] >= 0) / len(trades), 1) if trades else None
    return {"trades": len(trades), "pf": pf, "wr": wr, "net": round(equity - mv.START_EQUITY, 2)}


def run_alone(slave, frac_range):
    candles, ind = _load(frac_range)

    def entry_fn(i):
        return bt.STRATEGIES[slave](candles, ind, i)
    return _simulate(candles, ind, entry_fn)


def run_biased(master, slave, frac_range):
    candles, ind = _load(frac_range)
    bias = {"v": 0}

    def entry_fn(i):
        m = bt.STRATEGIES[master](candles, ind, i)
        if m != 0:
            bias["v"] = m
        s = bt.STRATEGIES[slave](candles, ind, i)
        if s != 0 and bias["v"] != 0 and s == bias["v"]:
            return s
        return 0
    return _simulate(candles, ind, entry_fn)


def main():
    results = []
    for slave in SLAVES:
        alone_is = run_alone(slave, (0.0, 0.6))
        alone_oos = run_alone(slave, (0.6, 1.0))
        biased_is = run_biased(MASTER, slave, (0.0, 0.6))
        biased_oos = run_biased(MASTER, slave, (0.6, 1.0))
        results.append({"slave": slave, "alone_is": alone_is, "alone_oos": alone_oos,
                         "biased_is": biased_is, "biased_oos": biased_oos})
        print(f"{slave} fatto", flush=True)

    print(f"\nMaster bias = {MASTER}, TF = {TF}\n")
    print(f"{'Slave':<16}{'Da sola OOS PF':>15}{'n':>5}   {'Con bias OOS PF':>16}{'n':>5}   {'Aiuta?':>8}")
    for r in results:
        ao, bo = r["alone_oos"], r["biased_oos"]
        helped = (bo["pf"] is not None and ao["pf"] is not None and bo["pf"] > ao["pf"]
                  and bo["trades"] >= MIN_OOS_TRADES)
        print(f"{r['slave']:<16}{str(ao['pf']):>15}{ao['trades']:>5}   "
              f"{str(bo['pf']):>16}{bo['trades']:>5}   {str(helped):>8}")

    import json
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase3c_bias_pipeline_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSalvato: {out_path}")


if __name__ == "__main__":
    main()
