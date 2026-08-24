#!/usr/bin/env python3
"""
24/08 (11) - richiesta esplicita dell'utente: le strategie a sessione
fissa (JUDAS_SWING/SILVER_BULLET/NY_REVERSAL/AMD_REVERSAL/PO3/
WEEKLY_EXP) e le SCALP_* vivono a una scala intraday - testarle su 4h/1h
con un hold fino a 200 barre (giorni) e un target multi-ATR e' la stessa
incoerenza di scala gia' diagnosticata il 15/08 per i TF piu' bassi
("il TF basso peggiora perche' amplifica il rumore relativo") ma
all'incontrario: qui il problema e' un'uscita troppo LENTA per una tesi
che si esaurisce in ore, non barre generiche.

Ricetta diversa per questa famiglia: M15/M30 (il loro TF nativo), SL/TP
piu' stretti (1.0/3.0 ATR, coerenti con mosse intraday piu' piccole), e
un'uscita forzata a FINE GIORNATA (stesso `date` calcolato da
_session_amd_series, gia' nel motore) se ne' SL ne' TP scattano prima -
non un hold generico di 200 barre. Nessun filtro ER qui: la tesi di
queste strategie e' il TIMING di sessione/AMD, non la forza del trend -
lo stesso principio gia' applicato il 17/08 per BB_SQUEEZE (filtro
scelto in base alla tesi, non imposto meccanicamente).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

CANDIDATES = ["JUDAS_SWING", "SILVER_BULLET", "SILVER_BULLET_V2", "NY_REVERSAL",
              "NY_REVERSAL_CHOCH_WINDOW", "LDN_REVERSAL", "AMD_REVERSAL", "PO3",
              "WEEKLY_EXP", "SCALP_BB_FADE", "SCALP_EMA", "SCALP_RANGE_BRK",
              "SCALP_RSI_SNAP"]
SL_MULT, TP_MULT = 1.0, 3.0
MAX_HOLD_BARS = 400  # tetto di sicurezza (mai raggiunto se l'uscita a fine giornata funziona)


def pf(rs):
    g = sum(r for r in rs if r > 0)
    l = -sum(r for r in rs if r < 0)
    return g / l if l > 0 else (float("inf") if g > 0 else 0.0)


def walk_forward(rs, nw=5):
    n = len(rs)
    if n < nw * 5:
        return None
    size = n // nw
    return [(len(rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]),
              pf(rs[w * size:(w + 1) * size] if w < nw - 1 else rs[w * size:]))
            for w in range(nw)]


def summarize(trades):
    out = {}
    for preset in ("retail_standard", "ecn"):
        net = []
        for t in trades:
            cost = bt.scaled_cost_for_price(preset, t["entry"])
            cost_r = min((cost["spread_price"] + cost["slippage_price"]) / t["risk_dist"], bt.MAX_COST_R_PER_TRADE)
            net.append(t["raw_r"] - cost_r)
        wf = walk_forward(net)
        n_pos = sum(1 for _, p in (wf or []) if p >= 1.0)
        mid = len(net) // 2
        h1, h2 = net[:mid], net[mid:]
        out[preset] = {"pf": pf(net), "sumR": sum(net), "win": n_pos, "nw": len(wf) if wf else 0,
                        "m1": pf(h1), "m2": pf(h2)}
    return out


def fmt(name, tag, n, s):
    r, e = s["retail_standard"], s["ecn"]
    return (f"{name:26s} [{tag}] n={n:4d}  "
            f"retail PF={r['pf']:.2f}(m1={r['m1']:.2f}/m2={r['m2']:.2f}) win{r['win']}/{r['nw']}  "
            f"ECN PF={e['pf']:.2f}(m1={e['m1']:.2f}/m2={e['m2']:.2f}) win{e['win']}/{e['nw']}")


def collect_session_scoped(name, candles, ind, atr, dates):
    sig_fn = bt.STRATEGIES[name]
    n = len(candles)
    trades = []
    for i in range(200, n - 2):
        a = atr[i]
        if not a:
            continue
        try:
            sig = sig_fn(candles, ind, i)
        except Exception:
            return None
        if sig == 0:
            continue
        entry = candles[i + 1]["open"]
        sl = entry - sig * SL_MULT * a
        tp = entry + sig * TP_MULT * a
        rd = abs(entry - sl)
        if rd <= 0:
            continue
        entry_date = dates[i + 1]
        exit_r = None
        last_j = min(i + 1 + MAX_HOLD_BARS, n - 1)
        for j in range(i + 2, min(i + 2 + MAX_HOLD_BARS, n)):
            hi, lo = candles[j]["high"], candles[j]["low"]
            if sig == 1:
                if lo <= sl:
                    exit_r = (sl - entry) / rd; break
                elif hi >= tp:
                    exit_r = (tp - entry) / rd; break
            else:
                if hi >= sl:
                    exit_r = (entry - sl) / rd; break
                elif lo <= tp:
                    exit_r = (entry - tp) / rd; break
            if dates[j] != entry_date:
                # fine giornata di ingresso: chiudi a mercato sulla prima
                # barra del nuovo giorno (stessa convenzione "mai dentro
                # la barra del segnale", qui applicata all'uscita)
                c = candles[j]["open"]
                exit_r = (c - entry) / rd if sig == 1 else (entry - c) / rd
                break
        if exit_r is None:
            c = candles[last_j]["close"]
            exit_r = (c - entry) / rd if sig == 1 else (entry - c) / rd
        trades.append({"entry": entry, "risk_dist": rd, "raw_r": exit_r})
    return trades


def main():
    for tf in ("15m", "30m"):
        candles, src = bt._fetch_real("XAUUSD", tf, 110000)
        ind = bt._prep(candles)
        atr = ind["atr"]
        dates = ind["sess"]["date"]
        print(f"\n### TF={tf} ({len(candles)} candele, {src}, {dates[0]} -> {dates[-1]}) ###", flush=True)
        for name in CANDIDATES:
            trades = collect_session_scoped(name, candles, ind, atr, dates)
            if trades is None:
                print(f"{name:26s} [{tf}] SALTATA (firma incompatibile)", flush=True)
                continue
            if len(trades) < 30:
                print(f"{name:26s} [{tf}] n={len(trades):4d} -> troppo pochi trade", flush=True)
                continue
            s = summarize(trades)
            flag = "  <-- CANDIDATO" if (s["retail_standard"]["pf"] >= 1.0 or s["ecn"]["pf"] >= 1.20) else ""
            print(fmt(name, tf, len(trades), s) + flag, flush=True)


if __name__ == "__main__":
    main()
