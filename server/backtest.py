#!/usr/bin/env python3
"""
NEXUS — motore di backtest reale (pure Python, nessuna dipendenza extra).

- Scarica OHLC storici REALI (Stooq, daily) con fallback sintetico se la rete
  non è disponibile (flag `data_source`).
- Implementa strategie REALI in Python (re-implementazioni standard dei nomi
  usati dall'EA — non copia 1:1 del MQL5 proprietario).
- Esegue un backtest event-driven con SL/TP basati su ATR e sizing a rischio %,
  e calcola metriche reali (net P&L, profit factor, win rate, max DD, Sharpe,
  expectancy, equity curve, lista trade).

NB: dati daily. L'intraday (M15) richiede un feed dati a pagamento; il motore
accetta il parametro `timeframe` ma lavora sui dati disponibili.
"""
from __future__ import annotations

import csv
import io
import math
import time
import urllib.request
from typing import Optional

# ----------------------------------------------------------------------------- #
# Dati storici
# ----------------------------------------------------------------------------- #
_CACHE: dict = {}          # ticker -> (timestamp, candles)
_CACHE_TTL = 3600

STOOQ_MAP = {
    "EURUSD": "eurusd", "GBPUSD": "gbpusd", "USDJPY": "usdjpy", "USDCHF": "usdchf",
    "AUDUSD": "audusd", "USDCAD": "usdcad", "NZDUSD": "nzdusd", "XAUUSD": "xauusd",
    "BTCUSD": "btcusd", "ETHUSD": "ethusd", "US30": "^dji", "NAS100": "^ndq",
    "SPX500": "^spx", "GER40": "^dax",
}


def _fetch_stooq(symbol: str, bars: int) -> Optional[list]:
    ticker = STOOQ_MAP.get(symbol.upper())
    if not ticker:
        return None
    url = f"https://stooq.com/q/d/l/?s={ticker}&i=d"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NEXUS"})
        with urllib.request.urlopen(req, timeout=15) as r:
            text = r.read().decode("utf-8", "replace")
        rows = list(csv.DictReader(io.StringIO(text)))
        candles = []
        for row in rows:
            try:
                candles.append({
                    "time": row["Date"], "open": float(row["Open"]),
                    "high": float(row["High"]), "low": float(row["Low"]),
                    "close": float(row["Close"]),
                })
            except (ValueError, KeyError):
                continue
        return candles[-bars:] if len(candles) > bars else candles or None
    except Exception:
        return None


def _synthetic(symbol: str, bars: int) -> list:
    """Serie deterministica con momentum/trend persistenti (fallback se no rete)."""
    base = {"XAUUSD": 2300.0, "BTCUSD": 65000.0, "US30": 39000.0,
            "NAS100": 18000.0}.get(symbol.upper(), 1.10)
    vol = base * 0.008
    candles, price, mom = [], base, 0.0
    rng = sum(ord(c) for c in symbol) + 1

    def rnd():
        nonlocal rng
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        return rng / 0x7FFFFFFF - 0.5

    for i in range(bars):
        mom = mom * 0.93 + rnd() * vol * 0.55     # momentum → trend con pullback
        shock = rnd() * vol
        o = price
        c = max(price + mom + shock, base * 0.1)
        h = max(o, c) + abs(shock) * 0.7
        low = min(o, c) - abs(shock) * 0.7
        candles.append({"time": f"d{i}", "open": round(o, 5), "high": round(h, 5),
                        "low": round(low, 5), "close": round(c, 5)})
        price = c
    return candles


def get_ohlc(symbol: str, bars: int = 800):
    """Ritorna (candles, data_source)."""
    key = symbol.upper()
    now = time.time()
    if key in _CACHE and now - _CACHE[key][0] < _CACHE_TTL:
        return _CACHE[key][1], "stooq-cache"
    candles = _fetch_stooq(symbol, bars)
    src = "stooq"
    if not candles or len(candles) < 60:
        candles = _synthetic(symbol, bars)
        src = "synthetic"
    else:
        _CACHE[key] = (now, candles)
    return candles, src


# Mappa timeframe UI -> (intervallo Yahoo, range). 4h non è nativo: prendo 1h
# e ricampiono ×4. Gli intraday Yahoo hanno limiti di range (60g per <1h).
_YF_INTERVAL = {
    "1d": ("1d", "10y"), "1wk": ("1wk", "10y"),
    "4h": ("1h", "2y"),  "1h": ("1h", "2y"),
    "30m": ("30m", "60d"), "15m": ("15m", "60d"), "5m": ("5m", "60d"),
}
_REAL_BARS_CAP = 2500  # tieni le ultime N barre (equilibrio realismo/velocità)


def _resample_4h(candles):
    out = []
    n = len(candles) - (len(candles) % 4)
    for i in range(0, n, 4):
        g = candles[i:i + 4]
        out.append({
            "time": g[0]["time"], "open": g[0]["open"],
            "high": max(x["high"] for x in g), "low": min(x["low"] for x in g),
            "close": g[-1]["close"],
        })
    return out


def _fetch_real(symbol: str, interval: str = "1d", bars: int = 800):
    """Dati OHLC reali via Yahoo (riusa sweep.fetch_yahoo, che passa dal proxy).
    Converte {t,o,h,l,c} -> {time,open,high,low,close}. Fallback su get_ohlc."""
    try:
        import sweep
        yf_int, yf_rng = _YF_INTERVAL.get(interval, ("1d", "10y"))
        raw, src = sweep.fetch_yahoo(symbol, yf_int, yf_rng)
        candles = [{
            "time": time.strftime("%Y-%m-%d %H:%M", time.gmtime(c["t"])),
            "open": c["o"], "high": c["h"], "low": c["l"], "close": c["c"],
        } for c in raw]
        if interval == "4h":
            candles = _resample_4h(candles)
        if len(candles) < 60:
            raise ValueError("troppe poche barre reali")
        return candles[-_REAL_BARS_CAP:], src
    except Exception as e:
        print(f"[backtest] real fetch fallita {symbol}/{interval}: {str(e)[:80]}")
        return get_ohlc(symbol, bars)


# ----------------------------------------------------------------------------- #
# Indicatori (pure Python)
# ----------------------------------------------------------------------------- #
def sma(vals, n, i):
    if i + 1 < n:
        return None
    return sum(vals[i - n + 1:i + 1]) / n


def ema_series(vals, n):
    out = [None] * len(vals)
    if len(vals) < n:
        return out
    k = 2 / (n + 1)
    e = sum(vals[:n]) / n
    out[n - 1] = e
    for i in range(n, len(vals)):
        e = vals[i] * k + e * (1 - k)
        out[i] = e
    return out


def atr_series(candles, n=14):
    trs = [0.0]
    for i in range(1, len(candles)):
        h, l, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    out = [None] * len(candles)
    if len(candles) <= n:
        return out
    a = sum(trs[1:n + 1]) / n
    out[n] = a
    for i in range(n + 1, len(candles)):
        a = (a * (n - 1) + trs[i]) / n
        out[i] = a
    return out


def rsi_series(vals, n=14):
    out = [None] * len(vals)
    if len(vals) <= n:
        return out
    gains, losses = 0.0, 0.0
    for i in range(1, n + 1):
        d = vals[i] - vals[i - 1]
        gains += max(d, 0); losses += max(-d, 0)
    ag, al = gains / n, losses / n
    out[n] = 100 - 100 / (1 + (ag / al if al else 999))
    for i in range(n + 1, len(vals)):
        d = vals[i] - vals[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
        out[i] = 100 - 100 / (1 + (ag / al if al else 999))
    return out


# ----------------------------------------------------------------------------- #
# Strategie (signal: +1 long, -1 short, 0 nessun segnale al bar i)
# ----------------------------------------------------------------------------- #
def _std(vals, n, i):
    if i + 1 < n:
        return None
    m = sum(vals[i - n + 1:i + 1]) / n
    return math.sqrt(sum((x - m) ** 2 for x in vals[i - n + 1:i + 1]) / n)


def _hh(candles, n, i):
    return max(x["high"] for x in candles[i - n + 1:i + 1]) if i + 1 >= n else None


def _ll(candles, n, i):
    return min(x["low"] for x in candles[i - n + 1:i + 1]) if i + 1 >= n else None


def _prep(candles):
    closes = [c["close"] for c in candles]
    return {
        "candles": candles,
        "close": closes,
        "ema20": ema_series(closes, 20),
        "ema50": ema_series(closes, 50),
        "ema12": ema_series(closes, 12),
        "ema26": ema_series(closes, 26),
        "ema200": ema_series(closes, 200),
        "rsi": rsi_series(closes, 14),
        "atr": atr_series(candles, 14),
    }


def sig_ema_pullback(c, ind, i):
    e20, e50 = ind["ema20"][i], ind["ema50"][i]
    if None in (e20, e50, ind["ema20"][i - 1]):
        return 0
    up = e20 > e50
    px, ppx = ind["close"][i], ind["close"][i - 1]
    if up and ppx < ind["ema20"][i - 1] and px > e20:
        return 1
    if not up and ppx > ind["ema20"][i - 1] and px < e20:
        return -1
    return 0


def sig_macd(c, ind, i):
    if None in (ind["ema12"][i], ind["ema26"][i], ind["ema12"][i - 1], ind["ema26"][i - 1]):
        return 0
    m, mp = ind["ema12"][i] - ind["ema26"][i], ind["ema12"][i - 1] - ind["ema26"][i - 1]
    if mp <= 0 < m:
        return 1
    if mp >= 0 > m:
        return -1
    return 0


def sig_rsi_div(c, ind, i):
    r, rp = ind["rsi"][i], ind["rsi"][i - 1]
    if None in (r, rp):
        return 0
    if rp < 30 <= r:
        return 1
    if rp > 70 >= r:
        return -1
    return 0


def sig_breakout(c, ind, i, n=20):
    if i < n:
        return 0
    hh = max(x["high"] for x in c[i - n:i])
    ll = min(x["low"] for x in c[i - n:i])
    px = c[i]["close"]
    if px > hh:
        return 1
    if px < ll:
        return -1
    return 0


def sig_adx_rsi(c, ind, i):
    e50 = ind["ema50"][i]
    r = ind["rsi"][i]
    if None in (e50, r, ind["ema50"][i - 1]):
        return 0
    trend_up = e50 > ind["ema50"][i - 1]
    if trend_up and 45 < r < 65 and ind["close"][i] > e50:
        return 1
    if not trend_up and 35 < r < 55 and ind["close"][i] < e50:
        return -1
    return 0


def sig_bollinger(c, ind, i):
    closes = ind["close"]
    sd = _std(closes, 20, i)
    mid = sma(closes, 20, i)
    if None in (sd, mid) or sd == 0:
        return 0
    upper, lower = mid + 2 * sd, mid - 2 * sd
    px, ppx = closes[i], closes[i - 1]
    if ppx <= lower < px:          # rientro dalla banda inferiore
        return 1
    if ppx >= upper > px:          # rientro dalla banda superiore
        return -1
    return 0


def sig_bb_squeeze(c, ind, i, look=40):
    closes = ind["close"]
    sd = _std(closes, 20, i)
    mid = sma(closes, 20, i)
    if None in (sd, mid) or i < look:
        return 0
    width = 4 * sd
    widths = [(_std(closes, 20, j) or 0) * 4 for j in range(i - look, i)]
    if not widths:
        return 0
    if width <= min(widths) * 1.05:   # squeeze: banda strettissima
        hi, lo = _hh(c, 20, i - 1), _ll(c, 20, i - 1)
        if hi and closes[i] > hi:
            return 1
        if lo and closes[i] < lo:
            return -1
    return 0


def sig_tsi(c, ind, i):
    # proxy momentum (come nel MQL5: RSI/EMA): RSI>52 e prezzo>ema20 in salita
    r = ind["rsi"][i]
    e = ind["ema20"][i]
    if None in (r, e, ind["ema20"][i - 1]):
        return 0
    if r > 52 and ind["close"][i] > e and e > ind["ema20"][i - 1]:
        return 1
    if r < 48 and ind["close"][i] < e and e < ind["ema20"][i - 1]:
        return -1
    return 0


def sig_ichimoku(c, ind, i):
    # Kumo break semplificato: tenkan/kijun + prezzo vs nuvola
    if i < 52:
        return 0
    tenkan = (_hh(c, 9, i) + _ll(c, 9, i)) / 2
    kijun = (_hh(c, 26, i) + _ll(c, 26, i)) / 2
    spanA = (tenkan + kijun) / 2
    spanB = (_hh(c, 52, i) + _ll(c, 52, i)) / 2
    top, bot = max(spanA, spanB), min(spanA, spanB)
    px, ppx = ind["close"][i], ind["close"][i - 1]
    if ppx <= top < px and tenkan > kijun:
        return 1
    if ppx >= bot > px and tenkan < kijun:
        return -1
    return 0


# Strategie con logica Python reale (le altre 36 usano i risultati reali importati)
STRATEGIES = {
    "EMA_PULLBACK": sig_ema_pullback,
    "MACD": sig_macd,
    "RSI_DIV": sig_rsi_div,
    "BREAKOUT_ACC": sig_breakout,
    "ADX_RSI": sig_adx_rsi,
    "BOLLINGER": sig_bollinger,
    "BB_SQUEEZE": sig_bb_squeeze,
    "TSI": sig_tsi,
    "ICHIMOKU": sig_ichimoku,
    "LONDON_BO": sig_breakout,        # breakout-based proxy
    "RANGE_FADE": sig_bollinger,      # mean-reversion proxy
}

# Tutte le 36 strategie dell'EA (dai sorgenti MQL5).
STRAT_NAMES_36 = [
    "ADX_RSI", "AMD_CONT", "AMD_REVERSAL", "BB_SQUEEZE", "BJORGUM", "BOLLINGER",
    "BREAKOUT_ACC", "CISD", "DISP_REBAL", "EMA_PULLBACK", "FVG_CONT", "FVG_MIT",
    "ICHIMOKU", "IFVG", "JUDAS_SWING", "LDN_REVERSAL", "LIQ_SWEEP", "LIQ_VOID",
    "LONDON_BO", "MACD", "MALAYSIAN_SNR", "NY_REVERSAL", "OB_MIT", "ORDER_BLOCK",
    "OTE_CONT", "PO3", "RANGE_FADE", "RSI_DIV", "SAR", "SH_BMS_RTO",
    "SILVER_BULLET", "SMS_BMS_RTO", "STRUCT_REACT", "TSI", "TURTLE_SOUP", "WEEKLY_EXP",
]


# ----------------------------------------------------------------------------- #
# Backtest engine
# ----------------------------------------------------------------------------- #
def run_backtest(symbol="XAUUSD", timeframe="D1", strategy="ADX_RSI",
                 risk_pct=1.0, atr_sl=1.5, atr_tp=3.0, start_equity=10000.0,
                 max_hold=40, bars=800, strategies=None):
    # Dati reali via Yahoo per il timeframe scelto (fallback su get_ohlc).
    candles, src = _fetch_real(symbol, timeframe, bars)
    ind = _prep(candles)
    strat_list = strategies or ([strategy] if strategy else list(STRATEGIES))
    strat_list = [s for s in strat_list if s in STRATEGIES] or ["ADX_RSI"]

    equity = start_equity
    curve = [{"i": 0, "equity": round(equity, 2),
              "ts": str(candles[0]["time"]), "close": candles[0]["close"]}]
    trades = []
    pos = None  # {dir, entry, sl, tp, open_i, risk_money, strat}

    for i in range(2, len(candles)):
        px = candles[i]["close"]
        # gestione posizione aperta
        if pos:
            hit = None
            hi, lo = candles[i]["high"], candles[i]["low"]
            if pos["dir"] == 1:
                if lo <= pos["sl"]:
                    hit = ("SL", pos["sl"])
                elif hi >= pos["tp"]:
                    hit = ("TP", pos["tp"])
            else:
                if hi >= pos["sl"]:
                    hit = ("SL", pos["sl"])
                elif lo <= pos["tp"]:
                    hit = ("TP", pos["tp"])
            if not hit and (i - pos["open_i"]) >= max_hold:
                hit = ("TIME", px)
            if hit:
                reason, exitpx = hit
                r_mult = ((exitpx - pos["entry"]) / (pos["entry"] - pos["sl"])) if pos["dir"] == 1 \
                    else ((pos["entry"] - exitpx) / (pos["sl"] - pos["entry"]))
                pnl = round(r_mult * pos["risk_money"], 2)
                equity += pnl
                trades.append({
                    "ticket": len(trades) + 1, "symbol": symbol, "strategy": pos["strat"],
                    "side": "BUY" if pos["dir"] == 1 else "SELL",
                    "openPrice": round(pos["entry"], 5), "closePrice": round(exitpx, 5),
                    "pnl": pnl, "r": round(r_mult, 2), "reason": reason,
                    "openTime": candles[pos["open_i"]]["time"], "closeTime": candles[i]["time"],
                })
                curve.append({"i": i, "equity": round(equity, 2),
                              "ts": str(candles[i]["time"]), "close": candles[i]["close"]})
                pos = None
            continue
        # nuovo segnale
        atr = ind["atr"][i]
        if not atr or atr <= 0:
            continue
        sig, who = 0, None
        for s in strat_list:
            v = STRATEGIES[s](candles, ind, i)
            if v != 0:
                sig, who = v, s
                break
        if sig != 0:
            risk_money = equity * (risk_pct / 100.0)
            sl = px - sig * atr * atr_sl
            tp = px + sig * atr * atr_tp
            pos = {"dir": sig, "entry": px, "sl": sl, "tp": tp, "open_i": i,
                   "risk_money": risk_money, "strat": who}

    res = _metrics(symbol, timeframe, strat_list, start_equity, equity, trades, curve, src)
    res["bars"] = len(candles)
    return res


def _metrics(symbol, tf, strat_list, start_equity, equity, trades, curve, src):
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] < 0]
    gw = sum(t["pnl"] for t in wins)
    gl = abs(sum(t["pnl"] for t in losses))
    # max drawdown sulla equity curve
    peak, maxdd = start_equity, 0.0
    for p in curve:
        peak = max(peak, p["equity"])
        maxdd = max(maxdd, (peak - p["equity"]) / peak * 100 if peak else 0)
    # Sharpe/SQN-like: media/dev.std dei R-multipli dei trade (bounded, robusto)
    rs = [t["r"] for t in trades]
    sharpe = 0.0
    if len(rs) > 1:
        mean = sum(rs) / len(rs)
        var = sum((x - mean) ** 2 for x in rs) / (len(rs) - 1)
        sd = math.sqrt(var)
        sharpe = mean / sd if sd > 1e-9 else 0.0
    n = len(trades)
    return {
        "demo": False, "data_source": src, "symbol": symbol, "timeframe": tf,
        "strategies": strat_list,
        "net_pnl": round(equity - start_equity, 2),
        "return_pct": round((equity - start_equity) / start_equity * 100, 2),
        "final_equity": round(equity, 2),
        "trades": n, "wins": len(wins), "losses": len(losses),
        "win_rate": round(len(wins) / n * 100, 1) if n else 0,
        "profit_factor": round(gw / gl, 2) if gl else None,
        "avg_win": round(gw / len(wins), 2) if wins else 0,
        "avg_loss": round(-gl / len(losses), 2) if losses else 0,
        "expectancy_r": round(sum(t["r"] for t in trades) / n, 3) if n else 0,
        "max_dd_pct": round(maxdd, 2),
        "sharpe": round(sharpe, 2),
        "equity_curve": curve,
        "trade_list": trades[-200:],
    }


def optimize(symbol="XAUUSD", strategy="ADX_RSI", **kw):
    results = []
    for sl in (1.0, 1.5, 2.0):
        for tp in (2.0, 3.0, 4.0):
            r = run_backtest(symbol=symbol, strategy=strategy, atr_sl=sl, atr_tp=tp)
            results.append({"atr_sl": sl, "atr_tp": tp, "profit_factor": r["profit_factor"],
                            "net_pnl": r["net_pnl"], "win_rate": r["win_rate"],
                            "max_dd_pct": r["max_dd_pct"], "trades": r["trades"]})
    ranked = sorted(results, key=lambda x: (x["profit_factor"] or 0), reverse=True)
    return {"demo": False, "symbol": symbol, "strategy": strategy,
            "results": ranked, "best": ranked[0] if ranked else None}


def multi_tf_report(symbol="XAUUSD", strategy="ADX_RSI"):
    rows = []
    for tf, bars in (("D1", 800), ("D1-long", 1500)):
        r = run_backtest(symbol=symbol, strategy=strategy, timeframe=tf, bars=bars)
        rows.append({"tf": tf, "pf": r["profit_factor"], "trades": r["trades"],
                     "win_rate": r["win_rate"], "net_pnl": r["net_pnl"],
                     "max_dd_pct": r["max_dd_pct"]})
    return {"demo": False, "symbol": symbol, "data_source": rows and "see-run", "timeframes": rows}


def management_report(symbol="XAUUSD", strategy="ADX_RSI"):
    r = run_backtest(symbol=symbol, strategy=strategy)
    return {"demo": False, "data_source": r["data_source"], "symbol": symbol, "rows": [
        {"metric": "Net P&L", "value": r["net_pnl"]},
        {"metric": "Return %", "value": r["return_pct"]},
        {"metric": "Profit Factor", "value": r["profit_factor"]},
        {"metric": "Win Rate %", "value": r["win_rate"]},
        {"metric": "Expectancy (R)", "value": r["expectancy_r"]},
        {"metric": "Max Drawdown %", "value": r["max_dd_pct"]},
        {"metric": "Sharpe", "value": r["sharpe"]},
        {"metric": "Trades", "value": r["trades"]},
    ]}
