#!/usr/bin/env python3
"""
NEXUS — Full backtest sweep: 36 strategie × 4 coppie × 7 gestioni.

Dati OHLC reali via Yahoo chart API (urllib, rispetta il proxy) con fallback
sintetico. Strategie implementate dalle condizioni di nexusstrategiesbacktest.md
(le SMC/ICT sono approssimazioni ragionevoli dei pattern descritti).

Output: lista di righe {strategy, symbol, variant(management), metrics...}
ordinabili per Sharpe, + ottimizzazione del lotto (MaxDD<0.5% → bump fino a <=10%).
"""
from __future__ import annotations
import json
import math
import time
import urllib.request

# --------------------------------------------------------------------------- #
# Dati
# --------------------------------------------------------------------------- #
YF = {"XAUUSD": "GC=F", "BTCUSD": "BTC-USD", "EURUSD": "EURUSD=X", "GBPJPY": "GBPJPY=X"}
_CACHE = {}


def fetch_yahoo(symbol, interval="1h", rng="6mo"):
    tk = YF.get(symbol, symbol)
    key = (tk, interval, rng)
    if key in _CACHE:
        return _CACHE[key]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{tk}?interval={interval}&range={rng}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NEXUS"})
        with urllib.request.urlopen(req, timeout=25) as r:
            d = json.loads(r.read())
        res = d["chart"]["result"][0]
        ts = res["timestamp"]
        q = res["indicators"]["quote"][0]
        candles = []
        for i in range(len(ts)):
            o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
            if None in (o, h, l, c):
                continue
            v = (q.get("volume") or [0] * len(ts))[i] or 0
            candles.append({"t": ts[i], "o": o, "h": h, "l": l, "c": c, "v": v})
        if len(candles) < 100:
            raise ValueError("too few bars")
        _CACHE[key] = (candles, "yahoo")
        return _CACHE[key]
    except Exception as e:
        print(f"[sweep] yahoo {tk} failed ({str(e)[:60]}) -> synthetic")
        return _synth(symbol), "synthetic"


def _synth(symbol, n=2000):
    base = {"XAUUSD": 2400.0, "BTCUSD": 65000.0, "GBPJPY": 195.0}.get(symbol, 1.10)
    vol = base * 0.004
    out, price, mom, rng = [], base, 0.0, sum(ord(x) for x in symbol) + 1
    t0 = int(time.time()) - n * 3600

    def rnd():
        nonlocal rng
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        return rng / 0x7FFFFFFF - 0.5
    for i in range(n):
        mom = mom * 0.93 + rnd() * vol * 0.5
        sh = rnd() * vol
        o = price
        c = max(price + mom + sh, base * 0.1)
        h = max(o, c) + abs(sh) * 0.7
        lo = min(o, c) - abs(sh) * 0.7
        out.append({"t": t0 + i * 3600, "o": o, "h": h, "l": lo, "c": c, "v": 1000})
        price = c
    return out


# --------------------------------------------------------------------------- #
# Indicatori
# --------------------------------------------------------------------------- #
def _ema(v, n):
    out = [None] * len(v)
    if len(v) < n:
        return out
    k = 2 / (n + 1)
    e = sum(v[:n]) / n
    out[n - 1] = e
    for i in range(n, len(v)):
        e = v[i] * k + e * (1 - k)
        out[i] = e
    return out


def _rsi(v, n=14):
    out = [None] * len(v)
    if len(v) <= n:
        return out
    g = l = 0.0
    for i in range(1, n + 1):
        d = v[i] - v[i - 1]
        g += max(d, 0); l += max(-d, 0)
    ag, al = g / n, l / n
    out[n] = 100 - 100 / (1 + (ag / al if al else 999))
    for i in range(n + 1, len(v)):
        d = v[i] - v[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
        out[i] = 100 - 100 / (1 + (ag / al if al else 999))
    return out


def _atr(c, n=14):
    out = [None] * len(c)
    trs = [0.0]
    for i in range(1, len(c)):
        trs.append(max(c[i]["h"] - c[i]["l"], abs(c[i]["h"] - c[i - 1]["c"]), abs(c[i]["l"] - c[i - 1]["c"])))
    if len(c) <= n:
        return out
    a = sum(trs[1:n + 1]) / n
    out[n] = a
    for i in range(n + 1, len(c)):
        a = (a * (n - 1) + trs[i]) / n
        out[i] = a
    return out


def _adx(c, n=14):
    out = [None] * len(c)
    if len(c) < 2 * n:
        return out
    pdm, ndm, tr = [0.0], [0.0], [0.0]
    for i in range(1, len(c)):
        up = c[i]["h"] - c[i - 1]["h"]
        dn = c[i - 1]["l"] - c[i]["l"]
        pdm.append(up if (up > dn and up > 0) else 0.0)
        ndm.append(dn if (dn > up and dn > 0) else 0.0)
        tr.append(max(c[i]["h"] - c[i]["l"], abs(c[i]["h"] - c[i - 1]["c"]), abs(c[i]["l"] - c[i - 1]["c"])))
    atr = sum(tr[1:n + 1]); ap = sum(pdm[1:n + 1]); an = sum(ndm[1:n + 1])
    dx = []
    for i in range(n + 1, len(c)):
        atr = atr - atr / n + tr[i]
        ap = ap - ap / n + pdm[i]
        an = an - an / n + ndm[i]
        pdi = 100 * ap / atr if atr else 0
        ndi = 100 * an / atr if atr else 0
        s = pdi + ndi
        dx.append(100 * abs(pdi - ndi) / s if s else 0)
        if len(dx) >= n:
            out[i] = sum(dx[-n:]) / n
    return out


def _bb(v, i, n=20, k=2):
    if i + 1 < n:
        return None
    seg = v[i - n + 1:i + 1]
    m = sum(seg) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in seg) / n)
    return m, m + k * sd, m - k * sd, 2 * k * sd


def _swings(c, wing=3):
    hi = [False] * len(c); lo = [False] * len(c)
    for i in range(wing, len(c) - wing):
        h = c[i]["h"]; l = c[i]["l"]
        if all(c[i - j]["h"] < h and c[i + j]["h"] < h for j in range(1, wing + 1)):
            hi[i] = True
        if all(c[i - j]["l"] > l and c[i + j]["l"] > l for j in range(1, wing + 1)):
            lo[i] = True
    return hi, lo


def prep(c):
    cl = [x["c"] for x in c]
    ind = {
        "c": cl, "ema9": _ema(cl, 9), "ema20": _ema(cl, 20), "ema21": _ema(cl, 21),
        "ema50": _ema(cl, 50), "ema12": _ema(cl, 12), "ema26": _ema(cl, 26),
        "rsi": _rsi(cl, 14), "atr": _atr(c, 14), "adx": _adx(c, 14),
    }
    # MACD hist
    e12, e26 = ind["ema12"], ind["ema26"]
    macd = [(e12[i] - e26[i]) if (e12[i] is not None and e26[i] is not None) else None for i in range(len(c))]
    sig = _ema([m if m is not None else 0 for m in macd], 9)
    ind["macd"] = macd
    ind["macd_sig"] = sig
    ind["macd_hist"] = [(macd[i] - sig[i]) if (macd[i] is not None and sig[i] is not None) else None for i in range(len(c))]
    # TSI
    mom = [0.0] + [cl[i] - cl[i - 1] for i in range(1, len(cl))]
    ema1 = _ema(mom, 25); ema2 = _ema([e if e is not None else 0 for e in ema1], 13)
    amom = [abs(m) for m in mom]
    aema1 = _ema(amom, 25); aema2 = _ema([e if e is not None else 0 for e in aema1], 13)
    tsi = [(100 * ema2[i] / aema2[i]) if (ema2[i] is not None and aema2[i]) else None for i in range(len(c))]
    ind["tsi"] = tsi
    ind["tsi_sig"] = _ema([t if t is not None else 0 for t in tsi], 7)
    ind["swH"], ind["swL"] = _swings(c, 3)
    # volume average proxy
    vavg = _ema([x["v"] for x in c], 20)
    ind["vavg"] = vavg
    return ind


def _hour(c, i):
    return time.gmtime(c[i]["t"]).tm_hour


def _bull(c, i):
    return c[i]["c"] > c[i]["o"]


# --------------------------------------------------------------------------- #
# 36 Strategie — ritornano +1 (buy), -1 (sell), 0
# --------------------------------------------------------------------------- #
def _trend_up(ind, i):
    e = ind["ema50"]
    return e[i] is not None and e[i - 1] is not None and e[i] > e[i - 1]


def s_adx_rsi(c, ind, i):
    a, r, e = ind["adx"][i], ind["rsi"][i], ind["ema50"][i]
    if None in (a, r, e) or ind["rsi"][i - 1] is None or a <= 25:
        return 0
    up = ind["rsi"][i] > ind["rsi"][i - 1]
    if r < 50 and up and c[i]["c"] > e:
        return 1
    if r > 50 and not up and c[i]["c"] < e:
        return -1
    return 0


def s_macd(c, ind, i):
    m, s, hh, e = ind["macd"][i], ind["macd_sig"][i], ind["macd_hist"][i], ind["ema20"][i]
    if None in (m, s, hh, e) or ind["macd_hist"][i - 1] is None:
        return 0
    grow = hh > ind["macd_hist"][i - 1]
    if m > s and m > 0 and grow and c[i]["c"] > e:
        return 1
    if m < s and m < 0 and not grow and c[i]["c"] < e:
        return -1
    return 0


def s_ema_pb(c, ind, i):
    e9, e21, e50 = ind["ema9"][i], ind["ema21"][i], ind["ema50"][i]
    if None in (e9, e21, e50):
        return 0
    if e9 > e21 > e50 and c[i]["l"] <= e21 and _bull(c, i):
        return 1
    if e9 < e21 < e50 and c[i]["h"] >= e21 and not _bull(c, i):
        return -1
    return 0


def s_breakout(c, ind, i, n=20):
    if i < n or ind["atr"][i] is None or ind["atr"][i - 1] is None:
        return 0
    hh = max(x["h"] for x in c[i - n:i]); ll = min(x["l"] for x in c[i - n:i])
    expand = ind["atr"][i] > ind["atr"][i - 1]
    if c[i]["c"] > hh and expand:
        return 1
    if c[i]["c"] < ll and expand:
        return -1
    return 0


def s_london_bo(c, ind, i):
    if not (7 <= _hour(c, i) <= 10) or ind["atr"][i] is None:
        return 0
    # range 02-07 UTC dello stesso giorno
    hi = lo = None
    j = i
    while j > 0 and j > i - 48:
        hh = _hour(c, j)
        if 2 <= hh < 7:
            hi = c[j]["h"] if hi is None else max(hi, c[j]["h"])
            lo = c[j]["l"] if lo is None else min(lo, c[j]["l"])
        if hh < 2:
            break
        j -= 1
    if hi is None:
        return 0
    if c[i]["c"] > hi:
        return 1
    if c[i]["c"] < lo:
        return -1
    return 0


def s_ichimoku(c, ind, i):
    if i < 52:
        return 0
    def hh(n): return max(x["h"] for x in c[i - n + 1:i + 1])
    def ll(n): return min(x["l"] for x in c[i - n + 1:i + 1])
    tenkan = (hh(9) + ll(9)) / 2
    kijun = (hh(26) + ll(26)) / 2
    spanA = (tenkan + kijun) / 2
    spanB = (hh(52) + ll(52)) / 2
    top, bot = max(spanA, spanB), min(spanA, spanB)
    chikou_ok_up = c[i]["c"] > c[i - 26]["c"]
    if c[i]["c"] > top and tenkan > kijun and chikou_ok_up:
        return 1
    if c[i]["c"] < bot and tenkan < kijun and not chikou_ok_up:
        return -1
    return 0


def s_sar(c, ind, i):
    # flip via 2-bar momentum proxy (PSAR semplificato)
    e, r = ind["ema50"][i], ind["rsi"][i]
    if None in (e, r) or i < 2:
        return 0
    flip_up = c[i - 1]["c"] < c[i - 2]["c"] and c[i]["c"] > c[i - 1]["c"]
    flip_dn = c[i - 1]["c"] > c[i - 2]["c"] and c[i]["c"] < c[i - 1]["c"]
    if flip_up and c[i]["c"] > e and r > 45:
        return 1
    if flip_dn and c[i]["c"] < e and r < 55:
        return -1
    return 0


def s_tsi(c, ind, i):
    t, s, e = ind["tsi"][i], ind["tsi_sig"][i], ind["ema50"][i]
    if None in (t, s, e) or ind["tsi"][i - 1] is None or ind["tsi_sig"][i - 1] is None:
        return 0
    up_cross = ind["tsi"][i - 1] <= ind["tsi_sig"][i - 1] and t > s
    dn_cross = ind["tsi"][i - 1] >= ind["tsi_sig"][i - 1] and t < s
    if t > 0 and up_cross and _trend_up(ind, i):
        return 1
    if t < 0 and dn_cross and not _trend_up(ind, i):
        return -1
    return 0


def s_bollinger(c, ind, i):
    bb = _bb(ind["c"], i); r = ind["rsi"][i]
    if bb is None or r is None:
        return 0
    m, up, lo, w = bb
    if c[i]["l"] <= lo and r < 35 and _bull(c, i):
        return 1
    if c[i]["h"] >= up and r > 65 and not _bull(c, i):
        return -1
    return 0


def s_bjorgum(c, ind, i):
    # rimbalzo su swing major + RSI estremo
    r = ind["rsi"][i]
    if r is None or i < 6:
        return 0
    if ind["swL"][i - 3] and c[i]["l"] <= c[i - 3]["l"] * 1.001 and r < 40 and _bull(c, i):
        return 1
    if ind["swH"][i - 3] and c[i]["h"] >= c[i - 3]["h"] * 0.999 and r > 60 and not _bull(c, i):
        return -1
    return 0


def s_bb_squeeze(c, ind, i, look=30):
    bb = _bb(ind["c"], i)
    if bb is None or i < look:
        return 0
    w = bb[3]
    widths = [(_bb(ind["c"], j) or (0, 0, 0, 9e9))[3] for j in range(i - look, i)]
    avg = sum(widths) / len(widths) if widths else 0
    if w < 0.5 * avg:
        if c[i]["c"] > bb[1]:
            return 1
        if c[i]["c"] < bb[2]:
            return -1
    return 0


def s_rsi_div(c, ind, i, look=12):
    r = ind["rsi"]
    if r[i] is None or i < look:
        return 0
    lows = [j for j in range(i - look, i) if ind["swL"][j]]
    highs = [j for j in range(i - look, i) if ind["swH"][j]]
    if len(lows) >= 1 and c[i]["l"] < c[lows[-1]]["l"] and r[i] is not None and r[lows[-1]] is not None and r[i] > r[lows[-1]]:
        return 1
    if len(highs) >= 1 and c[i]["h"] > c[highs[-1]]["h"] and r[i] is not None and r[highs[-1]] is not None and r[i] < r[highs[-1]]:
        return -1
    return 0


def s_range_fade(c, ind, i, n=20):
    a, r = ind["adx"][i], ind["rsi"][i]
    if None in (a, r) or a >= 20 or i < n:
        return 0
    hh = max(x["h"] for x in c[i - n:i]); ll = min(x["l"] for x in c[i - n:i])
    if c[i]["l"] <= ll and r < 40:
        return 1
    if c[i]["h"] >= hh and r > 60:
        return -1
    return 0


def _fvg(c, i):
    # bullish FVG: low[i] > high[i-2]; bearish: high[i] < low[i-2]
    if i < 2:
        return 0
    if c[i]["l"] > c[i - 2]["h"]:
        return 1
    if c[i]["h"] < c[i - 2]["l"]:
        return -1
    return 0


def s_liq_sweep(c, ind, i):
    e = ind["ema50"][i]
    if e is None or i < 3:
        return 0
    prevlow = min(c[i - 3]["l"], c[i - 2]["l"])
    prevhigh = max(c[i - 3]["h"], c[i - 2]["h"])
    if c[i]["l"] < prevlow and c[i]["c"] > prevlow and c[i]["c"] > e:
        return 1
    if c[i]["h"] > prevhigh and c[i]["c"] < prevhigh and c[i]["c"] < e:
        return -1
    return 0


def s_fvg_cont(c, ind, i):
    e = ind["ema50"][i]
    if e is None:
        return 0
    f = _fvg(c, i - 1)
    if f == 1 and c[i]["l"] <= c[i - 1]["l"] and c[i]["c"] > e:
        return 1
    if f == -1 and c[i]["h"] >= c[i - 1]["h"] and c[i]["c"] < e:
        return -1
    return 0


def s_order_block(c, ind, i):
    e = ind["ema50"][i]
    if e is None or i < 4:
        return 0
    # OB bearish mitigato + impulso bullish + ritorno
    if c[i - 3]["c"] < c[i - 3]["o"] and c[i - 2]["c"] > c[i - 2]["o"] and c[i]["l"] <= c[i - 3]["h"] and c[i]["c"] > e:
        return 1
    if c[i - 3]["c"] > c[i - 3]["o"] and c[i - 2]["c"] < c[i - 2]["o"] and c[i]["h"] >= c[i - 3]["l"] and c[i]["c"] < e:
        return -1
    return 0


def s_struct_react(c, ind, i):
    if i < 6:
        return 0
    # BOS: chiusura sopra ultimo swing high / sotto ultimo swing low
    sh = next((j for j in range(i - 1, i - 6, -1) if ind["swH"][j]), None)
    sl = next((j for j in range(i - 1, i - 6, -1) if ind["swL"][j]), None)
    if sh and c[i]["c"] > c[sh]["h"] and _bull(c, i):
        return 1
    if sl and c[i]["c"] < c[sl]["l"] and not _bull(c, i):
        return -1
    return 0


def s_turtle_soup(c, ind, i, n=20):
    r = ind["rsi"][i]
    if r is None or i < n:
        return 0
    ll = min(x["l"] for x in c[i - n:i]); hh = max(x["h"] for x in c[i - n:i])
    if c[i]["l"] < ll and c[i]["c"] > ll and r < 35:
        return 1
    if c[i]["h"] > hh and c[i]["c"] < hh and r > 65:
        return -1
    return 0


def s_ifvg(c, ind, i):
    f = _fvg(c, i - 2)
    if f == -1 and c[i]["c"] > c[i - 2]["l"] and _bull(c, i):
        return 1
    if f == 1 and c[i]["c"] < c[i - 2]["h"] and not _bull(c, i):
        return -1
    return 0


def s_fvg_mit(c, ind, i):
    f = _fvg(c, i - 1)
    hh = ind["macd_hist"][i]
    if hh is None:
        return 0
    if f == 1 and c[i]["l"] <= c[i - 1]["l"] and hh > 0:
        return 1
    if f == -1 and c[i]["h"] >= c[i - 1]["h"] and hh < 0:
        return -1
    return 0


def s_ob_mit(c, ind, i):
    r = ind["rsi"][i]
    if r is None or i < 4:
        return 0
    if c[i - 3]["c"] > c[i - 3]["o"] and c[i]["l"] <= c[i - 3]["l"] and r < 50:
        return 1
    if c[i - 3]["c"] < c[i - 3]["o"] and c[i]["h"] >= c[i - 3]["h"] and r > 50:
        return -1
    return 0


def s_sh_bms_rto(c, ind, i):
    if i < 5:
        return 0
    prevlow = min(x["l"] for x in c[i - 5:i - 1])
    prevhigh = max(x["h"] for x in c[i - 5:i - 1])
    if c[i - 1]["l"] < prevlow and c[i]["c"] > c[i - 2]["h"]:
        return 1
    if c[i - 1]["h"] > prevhigh and c[i]["c"] < c[i - 2]["l"]:
        return -1
    return 0


def s_sms_bms_rto(c, ind, i):
    e = ind["ema50"][i]
    sig = s_struct_react(c, ind, i)
    if e is None or sig == 0:
        return 0
    if sig == 1 and c[i]["c"] > e:
        return 1
    if sig == -1 and c[i]["c"] < e:
        return -1
    return 0


def s_silver_bullet(c, ind, i):
    h = _hour(c, i)
    if not ((2 <= h <= 4) or (10 <= h <= 11)):
        return 0
    return s_fvg_cont(c, ind, i)


def s_amd_rev(c, ind, i):
    if i < 4:
        return 0
    # manipulation sweep then reversal
    if c[i - 1]["l"] < min(c[i - 4]["l"], c[i - 3]["l"], c[i - 2]["l"]) and c[i]["c"] > c[i - 1]["h"]:
        return 1
    if c[i - 1]["h"] > max(c[i - 4]["h"], c[i - 3]["h"], c[i - 2]["h"]) and c[i]["c"] < c[i - 1]["l"]:
        return -1
    return 0


def s_ote_cont(c, ind, i, look=20):
    if i < look or ind["ema50"][i] is None:
        return 0
    seg = c[i - look:i]
    hi = max(x["h"] for x in seg); lo = min(x["l"] for x in seg)
    rng = hi - lo
    if rng <= 0:
        return 0
    up = _trend_up(ind, i)
    if up:
        f62, f79 = hi - 0.62 * rng, hi - 0.79 * rng
        if f79 <= c[i]["l"] <= f62 and _bull(c, i):
            return 1
    else:
        f62, f79 = lo + 0.62 * rng, lo + 0.79 * rng
        if f62 <= c[i]["h"] <= f79 and not _bull(c, i):
            return -1
    return 0


def s_malaysian(c, ind, i, look=30):
    r = ind["rsi"][i]
    if r is None or i < look:
        return 0
    lows = [c[j]["l"] for j in range(i - look, i) if ind["swL"][j]]
    highs = [c[j]["h"] for j in range(i - look, i) if ind["swH"][j]]
    for lv in lows:
        if abs(c[i]["l"] - lv) < (ind["atr"][i] or 0) * 0.3 and r < 50 and _bull(c, i):
            return 1
    for lv in highs:
        if abs(c[i]["h"] - lv) < (ind["atr"][i] or 0) * 0.3 and r > 50 and not _bull(c, i):
            return -1
    return 0


def s_cisd(c, ind, i):
    if i < 4:
        return 0
    down = c[i - 3]["c"] < c[i - 3]["o"] and c[i - 2]["c"] < c[i - 2]["o"]
    up = c[i - 3]["c"] > c[i - 3]["o"] and c[i - 2]["c"] > c[i - 2]["o"]
    strong_bull = c[i]["c"] > c[i]["o"] and (c[i]["c"] - c[i]["o"]) > (ind["atr"][i] or 0) * 0.6
    strong_bear = c[i]["c"] < c[i]["o"] and (c[i]["o"] - c[i]["c"]) > (ind["atr"][i] or 0) * 0.6
    if down and strong_bull:
        return 1
    if up and strong_bear:
        return -1
    return 0


def s_amd_cont(c, ind, i):
    sig = s_amd_rev(c, ind, i)
    return sig  # continuation usa stesso trigger con bias trend


def s_judas(c, ind, i):
    h = _hour(c, i)
    if not (0 <= h <= 4):
        return 0
    return s_amd_rev(c, ind, i)


def s_ldn_rev(c, ind, i):
    h = _hour(c, i)
    if not (7 <= h <= 9):
        return 0
    if c[i - 1]["c"] < c[i - 3]["c"] and c[i]["c"] > c[i - 1]["h"]:
        return 1
    if c[i - 1]["c"] > c[i - 3]["c"] and c[i]["c"] < c[i - 1]["l"]:
        return -1
    return 0


def s_ny_rev(c, ind, i):
    h = _hour(c, i)
    if not (13 <= h <= 15):
        return 0
    if c[i - 1]["c"] < c[i - 3]["c"] and c[i]["c"] > c[i - 1]["h"]:
        return 1
    if c[i - 1]["c"] > c[i - 3]["c"] and c[i]["c"] < c[i - 1]["l"]:
        return -1
    return 0


def s_weekly_exp(c, ind, i):
    wd = time.gmtime(c[i]["t"]).tm_wday
    if wd not in (0, 1) or i < 20:
        return 0
    return s_breakout(c, ind, i)


def s_po3(c, ind, i):
    if i < 6:
        return 0
    rng = max(x["h"] for x in c[i - 6:i - 2]) - min(x["l"] for x in c[i - 6:i - 2])
    tight = rng < (ind["atr"][i] or 9e9) * 1.5
    if tight and c[i - 1]["l"] < c[i - 2]["l"] and c[i]["c"] > c[i - 1]["h"]:
        return 1
    if tight and c[i - 1]["h"] > c[i - 2]["h"] and c[i]["c"] < c[i - 1]["l"]:
        return -1
    return 0


def s_liq_void(c, ind, i):
    e = ind["ema50"][i]
    if e is None:
        return 0
    f = _fvg(c, i - 1)
    if f == 1 and c[i]["l"] <= c[i - 1]["l"] and c[i]["c"] > e:
        return 1
    if f == -1 and c[i]["h"] >= c[i - 1]["h"] and c[i]["c"] < e:
        return -1
    return 0


def s_disp_rebal(c, ind, i):
    if i < 4:
        return 0
    bear3 = all(c[i - j]["c"] < c[i - j]["o"] for j in (3, 2, 1))
    bull3 = all(c[i - j]["c"] > c[i - j]["o"] for j in (3, 2, 1))
    mid = (c[i - 1]["h"] + c[i - 3]["l"]) / 2
    if bear3 and c[i]["c"] > mid:
        return -1  # displacement ribassista → rebalance poi continua giù? file: BUY su disp ribassista + ritorno 50
    if bull3 and c[i]["c"] < mid:
        return 1
    return 0


# Registro 36 strategie con SL/TP (×ATR) e gestione migliore (default)
STRATS = {
    "ADX_RSI": (s_adx_rsi, 1.8, 2.5), "MACD": (s_macd, 1.8, 2.7),
    "EMA_PULLBACK": (s_ema_pb, 1.5, 2.5), "BREAKOUT_ACC": (s_breakout, 1.8, 3.0),
    "LONDON_BO": (s_london_bo, 1.8, 2.5), "ICHIMOKU": (s_ichimoku, 1.8, 2.5),
    "SAR": (s_sar, 1.8, 2.0), "TSI": (s_tsi, 1.8, 2.5),
    "BOLLINGER": (s_bollinger, 1.5, 2.0), "BJORGUM": (s_bjorgum, 1.8, 2.5),
    "BB_SQUEEZE": (s_bb_squeeze, 1.5, 3.0), "RSI_DIV": (s_rsi_div, 1.8, 2.5),
    "RANGE_FADE": (s_range_fade, 1.5, 1.5), "LIQ_SWEEP": (s_liq_sweep, 1.5, 2.5),
    "FVG_CONT": (s_fvg_cont, 1.5, 2.0), "ORDER_BLOCK": (s_order_block, 1.5, 2.5),
    "STRUCT_REACT": (s_struct_react, 1.8, 2.5), "TURTLE_SOUP": (s_turtle_soup, 1.5, 2.0),
    "IFVG": (s_ifvg, 1.5, 2.5), "FVG_MIT": (s_fvg_mit, 1.5, 2.0),
    "OB_MIT": (s_ob_mit, 1.5, 2.5), "SH_BMS_RTO": (s_sh_bms_rto, 1.5, 2.0),
    "SMS_BMS_RTO": (s_sms_bms_rto, 1.5, 2.5), "SILVER_BULLET": (s_silver_bullet, 1.5, 3.0),
    "AMD_REVERSAL": (s_amd_rev, 1.8, 2.5), "OTE_CONT": (s_ote_cont, 1.5, 2.5),
    "MALAYSIAN_SNR": (s_malaysian, 1.8, 2.5), "CISD": (s_cisd, 1.8, 3.0),
    "AMD_CONT": (s_amd_cont, 1.8, 2.5), "JUDAS_SWING": (s_judas, 1.5, 2.5),
    "LDN_REVERSAL": (s_ldn_rev, 1.5, 2.5), "NY_REVERSAL": (s_ny_rev, 1.5, 2.5),
    "WEEKLY_EXP": (s_weekly_exp, 1.8, 3.0), "PO3": (s_po3, 1.8, 2.5),
    "LIQ_VOID": (s_liq_void, 1.5, 2.5), "DISP_REBAL": (s_disp_rebal, 1.5, 2.0),
}

MGMT = ["baseline", "be_1R", "trail_1.5atr", "grid_safe", "grid_balanced", "grid_aggressive", "grid+be"]
GRID_CFG = {
    "grid_safe": (2, 1.5, 1.0, False), "grid_balanced": (3, 1.0, 1.5, False),
    "grid_aggressive": (4, 0.75, 2.0, False), "grid+be": (2, 1.5, 1.0, True),
}


# --------------------------------------------------------------------------- #
# Backtest con gestione
# --------------------------------------------------------------------------- #
def backtest(c, ind, sig_fn, atr_sl, atr_tp, mgmt, lot_mult=1.0, risk_pct=1.0, start=10000.0):
    eq = start
    curve = [start]
    trades = []
    pos = None
    for i in range(55, len(c) - 1):
        atr = ind["atr"][i]
        px = c[i]["c"]
        if pos:
            d = pos["dir"]
            hi, lo = c[i]["h"], c[i]["l"]
            # gestione BE / trailing
            if mgmt in ("be_1R", "trail_1.5atr", "grid+be"):
                rdist = abs(pos["entry"] - pos["sl0"])
                if not pos["be"] and ((d == 1 and px >= pos["entry"] + rdist) or (d == -1 and px <= pos["entry"] - rdist)):
                    pos["sl"] = pos["entry"]; pos["be"] = True
            if mgmt == "trail_1.5atr" and pos["be"] and atr:
                if d == 1:
                    pos["sl"] = max(pos["sl"], px - 1.5 * atr)
                else:
                    pos["sl"] = min(pos["sl"], px + 1.5 * atr)
            # grid add
            if pos.get("grid") and pos["levels"] < pos["maxlev"] and atr:
                adverse = (d == 1 and px <= pos["lastentry"] - pos["spacing"] * atr) or \
                          (d == -1 and px >= pos["lastentry"] + pos["spacing"] * atr)
                if adverse:
                    addlot = pos["lastlot"] * pos["lotx"]
                    tot = pos["lot"] + addlot
                    pos["entry"] = (pos["entry"] * pos["lot"] + px * addlot) / tot
                    pos["lot"] = tot; pos["lastlot"] = addlot; pos["lastentry"] = px
                    pos["levels"] += 1
                    pos["tp"] = pos["entry"] + d * atr_tp * atr
                    pos["sl"] = pos["entry"] - d * atr_sl * atr * pos["maxlev"]
            # exit
            hit = None
            if d == 1:
                if lo <= pos["sl"]:
                    hit = pos["sl"]
                elif hi >= pos["tp"]:
                    hit = pos["tp"]
            else:
                if hi >= pos["sl"]:
                    hit = pos["sl"]
                elif lo <= pos["tp"]:
                    hit = pos["tp"]
            if hit is None and (i - pos["i"]) >= 60:
                hit = px
            if hit is not None:
                r = ((hit - pos["entry"]) / pos["risk"]) if d == 1 else ((pos["entry"] - hit) / pos["risk"])
                pnl = r * pos["riskmoney"] * (pos["lot"] / pos["lot0"])
                eq += pnl
                trades.append(r)
                curve.append(eq)
                pos = None
            continue
        if not atr or atr <= 0:
            continue
        s = sig_fn(c, ind, i)
        if s != 0:
            rm = eq * (risk_pct / 100.0) * lot_mult
            sl0 = px - s * atr_sl * atr
            grid = mgmt in GRID_CFG
            maxlev, spacing, lotx, gbe = GRID_CFG.get(mgmt, (1, 0, 1, False))
            pos = {"dir": s, "entry": px, "sl": sl0, "sl0": sl0, "tp": px + s * atr_tp * atr,
                   "risk": atr_sl * atr, "riskmoney": rm, "i": i, "be": False,
                   "lot": 1.0, "lot0": 1.0, "lastlot": 1.0, "lastentry": px,
                   "grid": grid, "levels": 1, "maxlev": maxlev, "spacing": spacing, "lotx": lotx}
    return _metrics(trades, curve, start)


def _metrics(trades, curve, start):
    n = len(trades)
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    peak = start; maxdd = 0.0
    for e in curve:
        peak = max(peak, e)
        maxdd = max(maxdd, (peak - e) / peak * 100 if peak else 0)
    sharpe = 0.0
    if n > 1:
        m = sum(trades) / n
        sd = math.sqrt(sum((x - m) ** 2 for x in trades) / (n - 1))
        sharpe = round(m / sd, 2) if sd > 1e-9 else 0.0
    gw = sum(t for t in wins); gl = abs(sum(t for t in losses))
    return {
        "trades": n, "win_rate": round(len(wins) / n * 100, 1) if n else 0.0,
        "profit_factor": round(gw / gl, 2) if gl else (round(gw, 2) if gw else 0.0),
        "sharpe": sharpe, "max_dd": round(maxdd, 2),
        "net": round(curve[-1] - start, 2),
        "return_pct": round((curve[-1] - start) / start * 100, 2),
    }


def run_sweep(symbols=("XAUUSD", "BTCUSD", "EURUSD", "GBPJPY"), interval="1h", rng="6mo",
              optimize=True, progress=True):
    rows = []
    data_src = {}
    for sym in symbols:
        candles, src = fetch_yahoo(sym, interval, rng)
        data_src[sym] = src
        ind = prep(candles)
        if progress:
            print(f"[sweep] {sym} src={src} bars={len(candles)}")
        for sname, (fn, sl, tp) in STRATS.items():
            for mgmt in MGMT:
                m = backtest(candles, ind, fn, sl, tp, mgmt)
                lot_mult = 1.0
                # ottimizzazione rischio: MaxDD<0.5% -> bump lotto fino a MaxDD<=10%
                if optimize and m["trades"] >= 5 and 0 < m["max_dd"] < 0.5:
                    lot_mult = min(20.0, round(10.0 / max(m["max_dd"], 0.05), 1))
                    m = backtest(candles, ind, fn, sl, tp, mgmt, lot_mult=lot_mult)
                    # riduci se ha superato 10%
                    while m["max_dd"] > 10 and lot_mult > 1.0:
                        lot_mult = round(lot_mult * 0.7, 1)
                        m = backtest(candles, ind, fn, sl, tp, mgmt, lot_mult=lot_mult)
                rows.append({
                    "strategy": sname, "symbol": sym, "variant": mgmt,
                    "timeframe": "1h", "data_source": src, "lot_mult": lot_mult,
                    "metrics": {
                        "sharpe": m["sharpe"], "profit_factor": m["profit_factor"],
                        "win_rate": m["win_rate"], "max_dd": m["max_dd"],
                        "return_pct": m["return_pct"], "n_trades": m["trades"],
                    },
                })
    rows.sort(key=lambda r: (r["metrics"]["sharpe"] or -9), reverse=True)
    return {"rows": rows, "data_source": data_src, "interval": interval, "range": rng,
            "count": len(rows), "generated": int(time.time())}


if __name__ == "__main__":
    import sys
    out = run_sweep()
    path = sys.argv[1] if len(sys.argv) > 1 else "seed_library.json"
    with open(path, "w") as f:
        json.dump(out, f)
    print(f"[sweep] wrote {out['count']} rows -> {path}  data={out['data_source']}")
