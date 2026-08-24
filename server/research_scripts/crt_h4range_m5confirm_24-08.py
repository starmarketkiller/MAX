#!/usr/bin/env python3
"""
24/08 - ipotesi dell'utente su CRT: per le altre strategie la conferma
(aspettare una barra in piu' prima di entrare) si e' spesso rivelata
controproducente (vedi vault "NEXUS EA - Stop Strutturale M5 su Segnali
H1 16-08", Test 2: nessun miglioramento su 6 strategie), ma per CRT
potrebbe servire perche' il problema noto di CRT e' lo stop troppo
stretto ancorato al wick della candela di sweep (saga costi-dominanti,
vedi _crt_series in backtest.py) - una conferma piu' fine (M5 invece
dello stesso TF) potrebbe dare uno stop piu' preciso senza allargarlo
artificialmente come fa min_stop_atr oggi.

Meccanismo (variante NUOVA, non il CRT esistente - CRT classico usa 3
candele consecutive sulla STESSA TF; qui il range viene da un H4 CHIUSO,
la conferma da candele M5 durante il periodo H4 successivo, quindi
possono nascere piu' segnali nello stesso giorno):

1. CRH/CRL = high/low dell'ultima candela H4 CHIUSA.
2. Durante il periodo H4 successivo (candela H4 ancora in formazione),
   ogni candela M5 e' un potenziale sweep: se il suo high supera CRH ma
   chiude sotto CRH (rientro) -> SELL, stop = high di quella candela M5
   (il massimo appena formato). Speculare per il low/CRL -> BUY.
3. Entrata a mercato all'apertura della M5 successiva (stessa convenzione
   "mai dentro la barra del segnale" gia' in uso ovunque nel motore).
4. Uscita a rapporto fisso 1:2 (non ATR - richiesta esplicita
   dell'utente: "vale la pena provare rapporto rischio/rendimento 1:2").

Assunzione dichiarata (l'unica lettura ambigua della richiesta): "chiude
sotto il range" e' stato interpretato come "chiude sotto CRH" (rientra
dentro o sotto il range), non "chiude sotto CRL" (rientro totale) - stessa
semantica del CRT esistente ("swept_high ... close<=crh"). Da confermare
con l'utente se il risultato sembra promettente.

Nessun filtro di regime applicato qui (una sola ipotesi per esperimento -
questa e' sul MECCANISMO di entrata/conferma, non sul regime; e' comunque
concettualmente un fade di un breakout, non un trend-follow, quindi il
filtro ER-trend usato altrove non e' ovviamente applicabile).
"""
import sys
import os
import json
import bisect

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

RR = 2.0
MAX_HOLD_M5 = 2400  # ~8 giorni, stesso ordine di grandezza dei 200 bar H1 usati altrove


def load_m5():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                         "data_cache_m5", "dukascopy_xauusd_m5.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pf(rs):
    g = sum(r for r in rs if r > 0)
    l = -sum(r for r in rs if r < 0)
    return g / l if l > 0 else (float("inf") if g > 0 else 0.0)


def walk_forward(rs, nw=5):
    n = len(rs)
    if n < nw * 5:
        return None
    size = n // nw
    out = []
    for w in range(nw):
        seg = rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]
        out.append((len(seg), pf(seg)))
    return out


def main():
    h4, src = bt._fetch_real("XAUUSD", "4h", 110000)
    h4_times = [c["time"] for c in h4]
    m5 = load_m5()
    nm5 = len(m5)
    print(f"H4: {len(h4)} candele ({src}). M5: {nm5} candele (cache).", flush=True)

    trades = []
    for i in range(nm5 - 1):
        t = m5[i]["time"]
        idx = bisect.bisect_right(h4_times, t) - 1
        if idx < 1:
            continue
        prev = h4[idx - 1]
        crh, crl = prev["high"], prev["low"]
        cur = m5[i]
        sig, stop = 0, None
        if cur["high"] > crh and cur["close"] < crh:
            sig, stop = -1, cur["high"]
        elif cur["low"] < crl and cur["close"] > crl:
            sig, stop = 1, cur["low"]
        if sig == 0:
            continue
        entry = m5[i + 1]["open"]
        risk_dist = abs(entry - stop)
        if risk_dist <= 0:
            continue
        tp = entry + sig * RR * risk_dist
        exit_r = None
        for j in range(i + 2, min(i + 2 + MAX_HOLD_M5, nm5)):
            hi, lo = m5[j]["high"], m5[j]["low"]
            if sig == 1:
                if lo <= stop:
                    exit_r = -1.0
                    break
                elif hi >= tp:
                    exit_r = RR
                    break
            else:
                if hi >= stop:
                    exit_r = -1.0
                    break
                elif lo <= tp:
                    exit_r = RR
                    break
        if exit_r is None:
            continue
        trades.append({"entry": entry, "risk_dist": risk_dist, "raw_r": exit_r})

    print(f"--- CRT H4-range / M5-confirm, RR=1:{RR:.0f}: {len(trades)} trade grezzi ---", flush=True)
    for preset in ("retail_standard", "ecn"):
        net = []
        for t in trades:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            net.append(t["raw_r"] - cost_r)
        wf = walk_forward(net)
        wf_str = " | ".join(f"PF={p:.2f}" for _, p in wf) if wf else "n/a"
        n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
        mid = len(net) // 2
        h1_, h2_ = net[:mid], net[mid:]
        print(f"  {preset:16s} aggPF={pf(net):.2f} sumR={sum(net):+.1f} "
              f"finestre_PF>=1:{n_pos}/{len(wf) if wf else 0}  [{wf_str}]", flush=True)
        print(f"    due meta': prima n={len(h1_)} PF={pf(h1_):.2f} sumR={sum(h1_):+.1f}  |  "
              f"seconda n={len(h2_)} PF={pf(h2_):.2f} sumR={sum(h2_):+.1f}", flush=True)


if __name__ == "__main__":
    main()
