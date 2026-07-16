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


_REAL_CACHE: dict = {}   # (symbol, interval) -> (ts, candles, src)


def _fetch_real(symbol: str, interval: str = "1d", bars: int = 800):
    """Dati OHLC reali via Yahoo (riusa sweep.fetch_yahoo, che passa dal proxy).
    Converte {t,o,h,l,c} -> {time,open,high,low,close}. Fallback su get_ohlc.
    Cache per (symbol, interval): l'ottimizzazione multi-TF fa migliaia di run
    sullo stesso feed -> senza cache ri-scaricherebbe ogni volta."""
    ckey = (symbol, interval)
    hit = _REAL_CACHE.get(ckey)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return hit[1], hit[2]
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
        out = candles[-_REAL_BARS_CAP:]
        _REAL_CACHE[ckey] = (time.time(), out, src)
        return out, src
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


def psar_series(candles, af_step=0.02, af_max=0.2):
    """Vero Parabolic SAR (AF/extreme-point/flip standard). Sostituisce il
    vecchio proxy sig_sar() che era in realta' un incrocio EMA20/EMA50
    identico a sig_ema_pullback() (bug trovato e corretto il 15/07 - vedi
    vault NEXUS EA - Motore Sito: Audit e Confronto 10Y)."""
    n = len(candles)
    psar = [None] * n
    trend = [0] * n
    if n < 3:
        return psar, trend
    trend[1] = 1 if candles[1]["close"] > candles[0]["close"] else -1
    psar[1] = candles[0]["low"] if trend[1] == 1 else candles[0]["high"]
    ep = candles[1]["high"] if trend[1] == 1 else candles[1]["low"]
    af = af_step
    for i in range(2, n):
        p = psar[i - 1] + af * (ep - psar[i - 1])
        if trend[i - 1] == 1:
            p = min(p, candles[i - 1]["low"], candles[i - 2]["low"])
            if candles[i]["low"] < p:
                trend[i] = -1; p = ep; ep = candles[i]["low"]; af = af_step
            else:
                trend[i] = 1
                if candles[i]["high"] > ep:
                    ep = candles[i]["high"]; af = min(af + af_step, af_max)
        else:
            p = max(p, candles[i - 1]["high"], candles[i - 2]["high"])
            if candles[i]["high"] > p:
                trend[i] = 1; p = ep; ep = candles[i]["high"]; af = af_step
            else:
                trend[i] = -1
                if candles[i]["low"] < ep:
                    ep = candles[i]["low"]; af = min(af + af_step, af_max)
        psar[i] = p
    return psar, trend


def adx_series(candles, period=14):
    """ADX(14) di Wilder standard. Nessuna delle vecchie sig_adx_rsi (sito e
    MQL5) lo calcolava mai nonostante il nome - vedi vault NEXUS EA -
    Ricerca Esterna e Test A-B per Strategia (bug trovato e corretto 15/07)."""
    n = len(candles)
    plus_dm = [0.0] * n; minus_dm = [0.0] * n; tr = [0.0] * n
    for i in range(1, n):
        up = candles[i]["high"] - candles[i - 1]["high"]
        dn = candles[i - 1]["low"] - candles[i]["low"]
        plus_dm[i] = up if (up > dn and up > 0) else 0.0
        minus_dm[i] = dn if (dn > up and dn > 0) else 0.0
        tr[i] = max(candles[i]["high"] - candles[i]["low"],
                    abs(candles[i]["high"] - candles[i - 1]["close"]),
                    abs(candles[i]["low"] - candles[i - 1]["close"]))

    def _wilder_smooth(vals, p):
        out = [None] * len(vals)
        out[p] = sum(vals[1:p + 1])
        for i in range(p + 1, len(vals)):
            out[i] = out[i - 1] - out[i - 1] / p + vals[i]
        return out

    tr_s = _wilder_smooth(tr, period)
    pdm_s = _wilder_smooth(plus_dm, period)
    mdm_s = _wilder_smooth(minus_dm, period)
    adx = [None] * n
    dx = [None] * n
    for i in range(period, n):
        if tr_s[i] and tr_s[i] > 0:
            pdi = 100 * pdm_s[i] / tr_s[i]
            mdi = 100 * mdm_s[i] / tr_s[i]
            dx[i] = 100 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) > 0 else 0
    first = period * 2
    if first < n:
        vals = [x for x in dx[period:first] if x is not None]
        if vals:
            adx[first] = sum(vals) / len(vals)
            for i in range(first + 1, n):
                if dx[i] is not None and adx[i - 1] is not None:
                    adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period
    return adx


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


def _macd_signal_series(ema12, ema26, period=9):
    """9-EMA della linea MACD (ema12-ema26), come il segnale MQL5 (g_macdSig)."""
    n = len(ema12)
    macd_line = [None] * n
    for i in range(n):
        if ema12[i] is not None and ema26[i] is not None:
            macd_line[i] = ema12[i] - ema26[i]
    sig = [None] * n
    k = 2.0 / (period + 1)
    seed_i = next((idx for idx, v in enumerate(macd_line) if v is not None), None)
    if seed_i is None:
        return macd_line, sig
    e = macd_line[seed_i]
    for i in range(seed_i, n):
        if macd_line[i] is None:
            continue
        e = macd_line[i] * k + e * (1 - k)
        sig[i] = e
    return macd_line, sig


def _prep(candles):
    closes = [c["close"] for c in candles]
    psar, psar_trend = psar_series(candles)
    ema12 = ema_series(closes, 12)
    ema26 = ema_series(closes, 26)
    macd_line, macd_sig = _macd_signal_series(ema12, ema26)
    return {
        "candles": candles,
        "close": closes,
        "ema5": ema_series(closes, 5),
        "ema9": ema_series(closes, 9),
        "ema20": ema_series(closes, 20),
        "ema50": ema_series(closes, 50),
        "ema12": ema12,
        "ema26": ema26,
        "ema200": ema_series(closes, 200),
        "macd_line": macd_line,
        "macd_signal": macd_sig,
        "rsi": rsi_series(closes, 14),
        "rsi7": rsi_series(closes, 7),
        "atr": atr_series(candles, 14),
        "psar": psar,
        "psar_trend": psar_trend,
        "adx": adx_series(candles, 14),
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
    # v2.5.1 - era un incrocio MACD-line/zero (bug trovato il 16/07): la vera
    # NXS_Strat_MACD() MQL5 e' MACD-line vs SIGNAL-line (9-EMA della MACD-
    # line) + MACD dallo stesso lato dello zero + prezzo vs EMA200 - tre
    # condizioni, non una. Il proxy vecchio non testava mai la vera
    # strategia (stesso tipo di bug di SAR/BJORGUM). Vedi vault NEXUS EA -
    # Ricerca Esterna e Test A-B per Strategia.
    macd, sig = ind["macd_line"][i], ind["macd_signal"][i]
    e200, px = ind["ema200"][i], ind["close"][i]
    if None in (macd, sig, e200):
        return 0
    if macd > sig and macd > 0 and px > e200:
        return 1
    if macd < sig and macd < 0 and px < e200:
        return -1
    return 0


def sig_rsi_div(c, ind, i):
    # v2.5.1 - era un semplice rientro RSI da ipercomprato/ipervenduto (bug
    # trovato il 16/07): la vera NXS_Strat_RSIDiv() MQL5 e' una divergenza
    # reale prezzo/RSI su una finestra di 8 barre (minimo di prezzo piu'
    # basso ma RSI piu' alto = divergenza rialzista, e viceversa) - non
    # testava mai la vera divergenza. Stesso tipo di bug di SAR/BJORGUM/MACD.
    rsi = ind["rsi"]
    if i < 8 or rsi[i] is None or rsi[i - 7] is None:
        return 0
    l1, l8 = c[i]["low"], c[i - 7]["low"]
    h1, h8 = c[i]["high"], c[i - 7]["high"]
    if l1 < l8 and rsi[i] > rsi[i - 7] and rsi[i] < 40:
        return 1
    if h1 > h8 and rsi[i] < rsi[i - 7] and rsi[i] > 60:
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
    # v2.5.1 - aggiunto filtro ADX reale (prima non veniva mai calcolato,
    # nonostante il nome: bug trovato e corretto il 15/07, vedi vault NEXUS
    # EA - Ricerca Esterna e Test A-B per Strategia). Soglia 20, non 25 "da
    # manuale": testato in A/B su XAUUSD D1 10y, ADX>25 peggiora PF e DD,
    # ADX>20 dimezza circa il drawdown mantenendo PF e campione.
    e50 = ind["ema50"][i]
    r = ind["rsi"][i]
    a = ind["adx"][i]
    if None in (e50, r, ind["ema50"][i - 1]) or a is None or a < 20.0:
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
    # proxy momentum (come nel MQL5: RSI/EMA): RSI>52 e prezzo>ema20 in salita.
    # NOTA (15/07): non e' il vero True Strength Index (doppio smoothing EMA
    # del momentum) - ne' qui ne' in MQL5 (NXS_Strat_TSI, commento esplicito
    # "simplified RSI/EMA proxy"). Test A/B col vero TSI (vedi tsi_series() e
    # NEXUS EA - Ricerca Esterna e Test A-B per Strategia): PF migliora
    # (1.35->1.42) e DD si dimezza (10.57%->4.99%), ma i trade crollano
    # (245->67 su 10y sito, verosimilmente -90% anche su MT5 dove oggi fa 721
    # trade/6y) - non sostituito qui senza una decisione esplicita
    # sull'accettare molta meno frequenza per una qualita' migliore.
    r = ind["rsi"][i]
    e = ind["ema20"][i]
    if None in (r, e, ind["ema20"][i - 1]):
        return 0
    if r > 52 and ind["close"][i] > e and e > ind["ema20"][i - 1]:
        return 1
    if r < 48 and ind["close"][i] < e and e < ind["ema20"][i - 1]:
        return -1
    return 0


def tsi_series(closes, r=25, s=13):
    """Vero True Strength Index (doppio smoothing EMA del momentum, William
    Blau). Disponibile per confronto A/B - non ancora usato da sig_tsi(),
    vedi nota sopra sul trade-off frequenza/qualita'."""
    n = len(closes)
    mom = [0.0] * n
    for i in range(1, n):
        mom[i] = closes[i] - closes[i - 1]

    def _ema(vals, period):
        out = [None] * len(vals)
        k = 2.0 / (period + 1)
        seed_i = next((idx for idx, v in enumerate(vals) if v is not None), None)
        if seed_i is None:
            return out
        out[seed_i] = vals[seed_i]
        for i in range(seed_i + 1, len(vals)):
            prev = out[i - 1] if out[i - 1] is not None else vals[i]
            out[i] = vals[i] * k + prev * (1 - k)
        return out

    ema2_mom = _ema(_ema(mom, r), s)
    ema2_abs = _ema(_ema([abs(x) for x in mom], r), s)
    tsi = [None] * n
    for i in range(n):
        if ema2_mom[i] is not None and ema2_abs[i] not in (None, 0):
            tsi[i] = 100.0 * ema2_mom[i] / ema2_abs[i]
    return tsi


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


# ---------------------------------------------------------------------------- #
# Strategie strutturali / SMC (implementazioni su OHLC daily). Le session/AMD/
# Elliott vere (JUDAS, SILVER_BULLET, PO3, ...) servono dati intraday -> MT5.
# ---------------------------------------------------------------------------- #
def _body(cd): return abs(cd["close"] - cd["open"])
def _bull(cd): return cd["close"] > cd["open"]
def _bear(cd): return cd["close"] < cd["open"]


def sig_sar(c, ind, i):
    # v2.5.1 - prima era un proxy EMA20/EMA50 identico, trade per trade, a
    # sig_ema_pullback() (bug trovato il 15/07, vedi vault NEXUS EA - Motore
    # Sito: Audit e Confronto 10Y): non testava mai Parabolic SAR. Ora usa
    # il vero Parabolic SAR (psar_series) + allineamento EMA20, che in test
    # A/B su XAUUSD D1 10y batte nettamente il vecchio proxy (PF 1.17->1.28,
    # drawdown quasi dimezzato). Non aggiungere filtro ADX: testato, peggiora.
    if i < 22:
        return 0
    trend, trend_p = ind["psar_trend"][i], ind["psar_trend"][i - 1]
    e20 = ind["ema20"][i]
    if trend is None or trend_p is None or e20 is None:
        return 0
    px = ind["close"][i]
    if trend == 1 and trend_p == -1 and px > e20:
        return 1
    if trend == -1 and trend_p == 1 and px < e20:
        return -1
    return 0


def sig_bjorgum(c, ind, i):
    # v2.5.1 - era un proxy EMA ribbon (12/26/50), bug trovato il 16/07: la
    # vera NXS_Strat_Bjorgum() in MQL5 e' un rimbalzo su pivot a 30 barre
    # (mean-reversion agli estremi), non un trigger trend-following con EMA -
    # concetti opposti. Non testava mai la vera strategia (stesso tipo di bug
    # gia' trovato su SAR il 15/07). Vedi vault NEXUS EA - Ricerca Esterna e
    # Test A-B per Strategia.
    atr = ind["atr"][i]
    if not atr or i < 32:
        return 0
    window = c[i - 32:i - 2]
    if not window:
        return 0
    piv_hi = max(x["high"] for x in window)
    piv_lo = min(x["low"] for x in window)
    c1 = c[i - 1]["close"]
    dist = atr * 0.5
    if abs(c1 - piv_lo) <= dist and c1 > piv_lo:
        return 1
    if abs(c1 - piv_hi) <= dist and c1 < piv_hi:
        return -1
    return 0


def sig_order_block(c, ind, i):
    # impulso (body>1.2 ATR) 3-10 barre fa, poi retest del body con rifiuto
    atr = ind["atr"][i]
    if not atr or i < 12:
        return 0
    for k in range(3, 11):
        cd = c[i - k]
        if _body(cd) < 1.2 * atr:
            continue
        top, bot = max(cd["open"], cd["close"]), min(cd["open"], cd["close"])
        mid = (top + bot) / 2
        cur = c[i]
        if _bull(cd) and cur["low"] <= top and _bull(cur) and cur["close"] > mid:
            return 1
        if _bear(cd) and cur["high"] >= bot and _bear(cur) and cur["close"] < mid:
            return -1
    return 0


def sig_ob_mit(c, ind, i):
    # order block CON displacement/BOS: l'impulso rompe lo swing a 5 barre
    atr = ind["atr"][i]
    if not atr or i < 14:
        return 0
    for k in range(3, 11):
        cd = c[i - k]
        if _body(cd) < 1.2 * atr:
            continue
        top, bot = max(cd["open"], cd["close"]), min(cd["open"], cd["close"])
        mid = (top + bot) / 2
        cur = c[i]
        phi, plo = _hh(c, 5, i - k - 1), _ll(c, 5, i - k - 1)
        if _bull(cd) and phi and cd["close"] > phi and cur["low"] <= top \
                and _bull(cur) and cur["close"] > mid:
            return 1
        if _bear(cd) and plo and cd["close"] < plo and cur["high"] >= bot \
                and _bear(cur) and cur["close"] < mid:
            return -1
    return 0


def sig_fvg_cont(c, ind, i):
    # FVG (gap a 3 candele) continuazione nel senso del trend
    e50 = ind["ema50"][i]
    if i < 3 or e50 is None:
        return 0
    if c[i]["low"] > c[i - 2]["high"] and c[i]["close"] > e50:
        return 1
    if c[i]["high"] < c[i - 2]["low"] and c[i]["close"] < e50:
        return -1
    return 0


def sig_fvg_mit(c, ind, i):
    # ritorno in un FVG vecchio (~5 barre fa) + rifiuto
    atr = ind["atr"][i]
    if not atr or i < 8:
        return 0
    lo_e, hi_e = c[i - 6]["high"], c[i - 4]["low"]          # FVG bull
    cur = c[i]
    if hi_e > lo_e and lo_e - 0.3 * atr <= cur["low"] <= hi_e \
            and _bull(cur) and cur["close"] > (lo_e + hi_e) / 2:
        return 1
    lo_b, hi_b = c[i - 4]["high"], c[i - 6]["low"]          # FVG bear
    if hi_b > lo_b and lo_b <= cur["high"] <= hi_b + 0.3 * atr \
            and _bear(cur) and cur["close"] < (lo_b + hi_b) / 2:
        return -1
    return 0


def sig_ifvg(c, ind, i):
    # inverse FVG: un FVG che viene violato -> flip nella direzione della rottura
    if i < 4:
        return 0
    if c[i - 1]["low"] > c[i - 3]["high"] and c[i]["close"] < c[i - 3]["high"]:
        return -1
    if c[i - 1]["high"] < c[i - 3]["low"] and c[i]["close"] > c[i - 3]["low"]:
        return 1
    return 0


def sig_liq_sweep(c, ind, i):
    # sweep del max/min a 20 barre + chiusura di rientro (reversal)
    if i < 21:
        return 0
    ph, pl = _hh(c, 20, i - 1), _ll(c, 20, i - 1)
    cur = c[i]
    if ph and cur["high"] > ph and cur["close"] < ph:
        return -1
    if pl and cur["low"] < pl and cur["close"] > pl:
        return 1
    return 0


def sig_turtle_soup(c, ind, i):
    # falso breakout: sweep del min/max a 20 + candela di reversal forte
    atr = ind["atr"][i]
    if not atr or i < 21:
        return 0
    pl, ph = _ll(c, 20, i - 1), _hh(c, 20, i - 1)
    cur = c[i]
    if pl and cur["low"] < pl and cur["close"] > pl and _bull(cur) and _body(cur) > 0.4 * atr:
        return 1
    if ph and cur["high"] > ph and cur["close"] < ph and _bear(cur) and _body(cur) > 0.4 * atr:
        return -1
    return 0


def sig_struct_react(c, ind, i):
    # reazione (rifiuto con ombra) su un livello di swing a 20 barre
    atr = ind["atr"][i]
    if not atr or i < 22:
        return 0
    ph, pl = _hh(c, 20, i - 1), _ll(c, 20, i - 1)
    cur = c[i]
    tol = 0.4 * atr
    lw = min(cur["open"], cur["close"]) - cur["low"]
    uw = cur["high"] - max(cur["open"], cur["close"])
    if pl and abs(cur["low"] - pl) < tol and _bull(cur) and lw > _body(cur):
        return 1
    if ph and abs(cur["high"] - ph) < tol and _bear(cur) and uw > _body(cur):
        return -1
    return 0


def sig_malaysian_snr(c, ind, i):
    # rifiuto su S/R basati su chiusura (swing close a 20)
    atr = ind["atr"][i]
    if not atr or i < 22:
        return 0
    closes = ind["close"]
    hi, lo = max(closes[i - 20:i]), min(closes[i - 20:i])
    cur = c[i]
    tol = 0.5 * atr
    if abs(cur["low"] - lo) < tol and _bull(cur):
        return 1
    if abs(cur["high"] - hi) < tol and _bear(cur):
        return -1
    return 0


def sig_ote_cont(c, ind, i):
    # optimal trade entry: ritracciamento 62-79% dell'ultimo swing, nel trend
    if i < 30:
        return 0
    e50, e50p = ind["ema50"][i], ind["ema50"][i - 1]
    if None in (e50, e50p):
        return 0
    shi, slo = _hh(c, 20, i - 1), _ll(c, 20, i - 1)
    if None in (shi, slo) or shi <= slo:
        return 0
    rng, px = shi - slo, c[i]["close"]
    if e50 > e50p and 0.62 <= (shi - px) / rng <= 0.79 and _bull(c[i]):
        return 1
    if e50 < e50p and 0.62 <= (px - slo) / rng <= 0.79 and _bear(c[i]):
        return -1
    return 0


def sig_disp_rebal(c, ind, i):
    # displacement (>2 ATR) poi pullback che la ribilancia -> continuazione
    atr = ind["atr"][i]
    if not atr or i < 6:
        return 0
    for k in range(1, 5):
        cd = c[i - k]
        if _body(cd) <= 2 * atr:
            continue
        mid = (cd["open"] + cd["close"]) / 2
        cur = c[i]
        if _bull(cd) and cur["low"] <= mid and cur["close"] > mid and _bull(cur):
            return 1
        if _bear(cd) and cur["high"] >= mid and cur["close"] < mid and _bear(cur):
            return -1
    return 0


def sig_cisd(c, ind, i):
    # change in state of delivery: rottura dell'estremo dell'ultima serie di 3
    if i < 5:
        return 0
    recent = c[i - 3:i]
    cur = c[i]
    if all(_bear(x) for x in recent) and cur["close"] > max(x["high"] for x in recent):
        return 1
    if all(_bull(x) for x in recent) and cur["close"] < min(x["low"] for x in recent):
        return -1
    return 0


# --------------------------------------------------------------------------- #
# SCALP / profit-taker (v2.3.0) - pensate per M15/M30: ingressi veloci, TP
# stretto. Registrate nel motore per l'ottimizzazione multi-TF sui TF bassi.
# --------------------------------------------------------------------------- #
def sig_scalp_ema(c, ind, i):
    # Momentum pop: EMA5 incrocia EMA9 nel senso del micro-trend (EMA20),
    # con RSI7 non estremo. Cavalca lo scatto, esce presto (TP basso).
    e5, e9, e20 = ind["ema5"][i], ind["ema9"][i], ind["ema20"][i]
    e5p, e9p = ind["ema5"][i - 1], ind["ema9"][i - 1]
    r = ind["rsi7"][i]
    if None in (e5, e9, e20, e5p, e9p, r):
        return 0
    if e5p <= e9p and e5 > e9 and ind["close"][i] > e20 and r < 75:
        return 1
    if e5p >= e9p and e5 < e9 and ind["close"][i] < e20 and r > 25:
        return -1
    return 0


def sig_scalp_bb_fade(c, ind, i):
    # Mean-reversion profit-taker: chiusura oltre la banda 2sigma e RIENTRO ->
    # snap-back veloce verso la media. Classico scalp di ritorno.
    closes = ind["close"]
    if i < 21 or closes[i] is None:
        return 0
    m = sma(closes, 20, i)
    sd = _std(closes, 20, i)
    if m is None or sd is None or sd == 0:
        return 0
    up, lo = m + 2.0 * sd, m - 2.0 * sd
    px, ppx = closes[i], closes[i - 1]
    if ppx < lo and px > lo:      # rientro dal basso
        return 1
    if ppx > up and px < up:      # rientro dall'alto
        return -1
    return 0


def sig_scalp_rsi_snap(c, ind, i):
    # RSI7 estremo + candela di reversal: rimbalzo veloce. TP stretto.
    r, rp = ind["rsi7"][i], ind["rsi7"][i - 1]
    if None in (r, rp) or i < 2:
        return 0
    cur = c[i]
    if rp < 20 and r >= rp and _bull(cur):
        return 1
    if rp > 80 and r <= rp and _bear(cur):
        return -1
    return 0


def sig_scalp_range_brk(c, ind, i, n=12):
    # Micro-breakout momentum: rompe il massimo/minimo delle ultime n barre con
    # corpo pieno (momentum). Profit-taker: entra sullo scatto, TP corto.
    if i < n + 1:
        return 0
    atr = ind["atr"][i]
    if atr is None or atr == 0:
        return 0
    cur = c[i]
    hh = max(x["high"] for x in c[i - n:i])
    ll = min(x["low"] for x in c[i - n:i])
    body = abs(cur["close"] - cur["open"])
    if cur["close"] > hh and body > 0.4 * atr and _bull(cur):
        return 1
    if cur["close"] < ll and body > 0.4 * atr and _bear(cur):
        return -1
    return 0


# Strategie con logica Python reale (le altre usano i risultati reali importati)
STRATEGIES = {
    "SCALP_EMA": sig_scalp_ema,
    "SCALP_BB_FADE": sig_scalp_bb_fade,
    "SCALP_RSI_SNAP": sig_scalp_rsi_snap,
    "SCALP_RANGE_BRK": sig_scalp_range_brk,
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
    # --- strutturali / SMC (nuove, v2.2.8) ---
    "SAR": sig_sar,
    "BJORGUM": sig_bjorgum,
    "ORDER_BLOCK": sig_order_block,
    "OB_MIT": sig_ob_mit,
    "FVG_CONT": sig_fvg_cont,
    "FVG_MIT": sig_fvg_mit,
    "IFVG": sig_ifvg,
    "LIQ_SWEEP": sig_liq_sweep,
    "TURTLE_SOUP": sig_turtle_soup,
    "STRUCT_REACT": sig_struct_react,
    "MALAYSIAN_SNR": sig_malaysian_snr,
    "OTE_CONT": sig_ote_cont,
    "DISP_REBAL": sig_disp_rebal,
    "CISD": sig_cisd,
    "WEEKLY_EXP": sig_breakout,       # range expansion proxy
    "LIQ_VOID": sig_fvg_cont,         # liquidity void = FVG proxy
    "SH_BMS_RTO": sig_ob_mit,         # sweep+BOS+return proxy
    "SMS_BMS_RTO": sig_ob_mit,        # proxy
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
                 max_hold=40, bars=800, strategies=None,
                 htf_filter=False, trend_period=50,
                 breakeven_r=0.0, trailing_atr=0.0, cooldown_bars=0):
    # Dati reali via Yahoo per il timeframe scelto (fallback su get_ohlc).
    # GATE applicati (coerenza col backtest): htf_filter (solo nel senso del trend
    # su SMA trend_period), breakeven_r (SL a BE dopo N x rischio), trailing_atr
    # (trailing a N x ATR), cooldown_bars (barre minime tra un trade e il successivo).
    candles, src = _fetch_real(symbol, timeframe, bars)
    ind = _prep(candles)
    strat_list = strategies or ([strategy] if strategy else list(STRATEGIES))
    strat_list = [s for s in strat_list if s in STRATEGIES] or ["ADX_RSI"]

    closes = [c["close"] for c in candles]

    def _sma(idx, p):
        if idx < p - 1:
            return None
        return sum(closes[idx - p + 1: idx + 1]) / p

    equity = start_equity
    curve = [{"i": 0, "equity": round(equity, 2),
              "ts": str(candles[0]["time"]), "close": candles[0]["close"]}]
    trades = []
    pos = None  # {dir, entry, sl, tp, open_i, risk_money, strat, risk_dist}
    last_close_i = -10 ** 9   # per il cooldown

    for i in range(2, len(candles)):
        px = candles[i]["close"]
        # gestione posizione aperta
        if pos:
            hi, lo = candles[i]["high"], candles[i]["low"]
            risk_dist = pos["risk_dist"]
            # --- BREAKEVEN: SL a entry dopo breakeven_r x rischio ---
            if breakeven_r > 0 and risk_dist > 0:
                prog = (hi - pos["entry"]) if pos["dir"] == 1 else (pos["entry"] - lo)
                if prog >= breakeven_r * risk_dist:
                    if pos["dir"] == 1:
                        pos["sl"] = max(pos["sl"], pos["entry"])
                    else:
                        pos["sl"] = min(pos["sl"], pos["entry"])
            # --- TRAILING ATR: insegue lo SL a trailing_atr x ATR ---
            if trailing_atr > 0:
                a = ind["atr"][i] or 0
                if a > 0:
                    if pos["dir"] == 1:
                        pos["sl"] = max(pos["sl"], px - trailing_atr * a)
                    else:
                        pos["sl"] = min(pos["sl"], px + trailing_atr * a)
            hit = None
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
                # R sul RISCHIO ORIGINALE (lo SL puo' essere stato spostato a BE/trail).
                rd = pos["risk_dist"] if pos["risk_dist"] > 0 else 1e-9
                r_mult = ((exitpx - pos["entry"]) / rd) if pos["dir"] == 1 \
                    else ((pos["entry"] - exitpx) / rd)
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
                last_close_i = i
            continue
        # --- COOLDOWN: barre minime tra un trade e il successivo ---
        if cooldown_bars > 0 and (i - last_close_i) < cooldown_bars:
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
        # --- HTF FILTER: prendi solo nel senso del trend (close vs SMA) ---
        if sig != 0 and htf_filter:
            sma = _sma(i, int(trend_period))
            if sma is not None:
                if (sig == 1 and px < sma) or (sig == -1 and px > sma):
                    sig = 0
        if sig != 0:
            risk_money = equity * (risk_pct / 100.0)
            sl = px - sig * atr * atr_sl
            tp = px + sig * atr * atr_tp
            pos = {"dir": sig, "entry": px, "sl": sl, "tp": tp, "open_i": i,
                   "risk_money": risk_money, "strat": who,
                   "risk_dist": abs(px - sl)}

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
