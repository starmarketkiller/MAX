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
from strategy_registry import LIVE_STRATEGY_IDS, require_strategies

# ----------------------------------------------------------------------------- #
# Dati storici
# ----------------------------------------------------------------------------- #
_CACHE: dict = {}          # ticker -> (timestamp, candles)
_CACHE_TTL = 3600

# Profili di costo XAUUSD (31/07) - VERIFICATI via ricerca web, non stimati:
# "1 pip su gold = $0.10, spread retail standard tipico 20-50 pip ($2-5),
# ECN 15-25 pip ($1.5-2.5) + commissione $4-8/lotto round-trip" (fonti:
# DailyForex, ForexSpreadCompare, Tradingpedia - confrontate il 31/07/2026).
# "none" = comportamento di sempre (nessun costo, invariato). Gli altri due
# vanno passati esplicitamente a run_backtest/optimize via **COST_PRESETS[x]
# - MAI applicati di default, per non cambiare risultati gia' salvati altrove
# senza che sia una scelta esplicita di chi chiama.
#
# Nota onesta sulla commissione ECN ($4-8/lotto round-trip): NON e' inclusa
# come commission_r qui. commission_r e' un costo FISSO in R, ma una
# commissione per lotto va convertita in R dividendo per risk_dist (identico
# a come si fa per spread_price) - varia da trade a trade in base alla
# distanza dello stop, non e' una costante. Approssimarla con un numero
# fisso avrebbe richiesto un valore inventato, non derivato. Il preset "ecn"
# qui sotto quindi SOTTOSTIMA il costo reale di un conto ECN di quella parte
# di commissione - i risultati con questo preset sono un limite superiore
# ottimistico, non il costo ECN vero e proprio.
COST_PRESETS = {
    "none": {"spread_price": 0.0, "commission_r": 0.0, "slippage_price": 0.0},
    "retail_standard": {"spread_price": 2.50, "commission_r": 0.0, "slippage_price": 0.50},
    "ecn": {"spread_price": 0.90, "commission_r": 0.0, "slippage_price": 0.15},
    # 04/08 - "stress": costi aumentati per il gate Fase 4 (NQROS v3.1) -
    # spread al limite superiore del range retail gia' verificato ($2-5,
    # non un valore inventato) + slippage raddoppiato rispetto a
    # retail_standard, per simulare esecuzione peggiore (news/bassa
    # liquidita') senza uscire dal range reale osservato.
    "stress": {"spread_price": 4.00, "commission_r": 0.0, "slippage_price": 1.00},
}


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
    atr_s = atr_series(candles, 14)
    sess = _session_amd_series(candles)
    sb_signal, sb_sweep_level = _silver_bullet_series(candles, sess, atr_s)
    weekly_pwh, weekly_pwl, weekly_open = _weekly_levels_series(candles)
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
        "atr": atr_s,
        "psar": psar,
        "psar_trend": psar_trend,
        "adx": adx_series(candles, 14),
        "sess": sess,
        "choch_int": _fractal_choch_series(candles, wing=3),
        "choch_ext": _external_choch_series(candles, factor=4, wing=3),  # (trend, up, down)
        "swing_ext": _external_swing_price_series(candles, factor=4, wing=3),  # (hi, lo) su TF esterno reale
        "sb_signal": sb_signal, "sb_sweep_level": sb_sweep_level,  # precalcolato, vedi _silver_bullet_series
        "weekly_pwh": weekly_pwh, "weekly_pwl": weekly_pwl, "weekly_open": weekly_open,
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


def _weekly_levels_series(candles):
    """Per ogni barra: (PWH, PWL della settimana civile PRECEDENTE gia'
    completata, apertura della settimana CORRENTE) - nessun look-ahead,
    la settimana precedente e' sempre gia' conclusa quando la si legge."""
    from datetime import datetime
    n = len(candles)
    week_key = [None] * n
    for i, cd in enumerate(candles):
        d = datetime.strptime(cd["time"].split(" ")[0], "%Y-%m-%d")
        week_key[i] = d.isocalendar()[:2]   # (iso_year, iso_week)

    week_hi, week_lo, week_open = {}, {}, {}
    for i, cd in enumerate(candles):
        wk = week_key[i]
        week_hi[wk] = max(week_hi.get(wk, -1e18), cd["high"])
        week_lo[wk] = min(week_lo.get(wk, 1e18), cd["low"])
        if wk not in week_open:
            week_open[wk] = cd["open"]

    weeks_sorted = sorted(week_hi.keys())
    prev_week = {wk: weeks_sorted[idx - 1] for idx, wk in enumerate(weeks_sorted) if idx > 0}

    pwh, pwl, wopen = [None] * n, [None] * n, [None] * n
    for i in range(n):
        wk = week_key[i]
        pw = prev_week.get(wk)
        if pw is not None:
            pwh[i], pwl[i] = week_hi.get(pw), week_lo.get(pw)
        wopen[i] = week_open.get(wk)
    return pwh, pwl, wopen


def sig_london_bo(c, ind, i):
    # 04/08 - fedelta' verificata riga-per-riga con NXS_Strat_LondonBO
    # (MQL5 reale): prima "LONDON_BO" e "WEEKLY_EXP" condividevano lo
    # stesso proxy generico sig_breakout() (rottura di un massimo/minimo a
    # 20 barre qualsiasi, nessun gate sessione, nessun filtro) - le due
    # strategie MQL5 vere sono completamente diverse (vedi sig_weekly_exp
    # sotto), la "collisione" era un artefatto del motore, non della realta'.
    # Vera logica: gate sessione LONDON, rottura del range ASIATICO (non un
    # massimo/minimo qualsiasi a 20 barre), corpo minimo 0.5xATR, buffer
    # 0.15xATR oltre il livello, Close Location Value >= 0.6 (chiusura
    # vicina all'estremo della barra = convinzione, non un tocco marginale).
    sess = ind["sess"]
    if sess["session"][i] != "LONDON":
        return 0
    ah, al = sess["asian_hi"][i], sess["asian_lo"][i]
    if ah is None or al is None:
        return 0
    atr = ind["atr"][i]
    if not atr:
        return 0
    cur = c[i]
    o1, c1, h1, l1 = cur["open"], cur["close"], cur["high"], cur["low"]
    body1 = abs(c1 - o1)
    range1 = h1 - l1
    if body1 < atr * 0.5 or range1 <= 0:
        return 0
    clv_up = (c1 - l1) / range1
    clv_down = (h1 - c1) / range1
    if c1 > ah + atr * 0.15 and clv_up >= 0.6:
        return 1
    if c1 < al - atr * 0.15 and clv_down >= 0.6:
        return -1
    return 0


def sig_weekly_exp(c, ind, i):
    # 04/08 - fedelta' verificata riga-per-riga con NXS_Strat_WeeklyRangeExp
    # (MQL5 reale, girato su H4): sconto/premio rispetto al midpoint della
    # settimana PRECEDENTE (PWH/PWL), displacement H4 (corpo>=0.8xATR H4)
    # che rompe uno swing H4 a 15 barre (BOS), reclaim dell'apertura della
    # settimana CORRENTE, CHoCH di conferma - non un semplice breakout a 20
    # barre come faceva il proxy condiviso con LONDON_BO prima.
    pwh, pwl, wopen = ind["weekly_pwh"][i], ind["weekly_pwl"][i], ind["weekly_open"][i]
    if pwh is None or pwl is None or wopen is None:
        return 0
    atr = ind["atr"][i]
    if not atr or i < 15:
        return 0
    cur = c[i]
    o1, c1 = cur["open"], cur["close"]
    if abs(c1 - o1) < atr * 0.8:
        return 0
    window = c[i - 15:i]
    swing_hi = max(x["high"] for x in window)
    swing_lo = min(x["low"] for x in window)
    w_mid = (pwh + pwl) / 2.0
    choch_up, choch_down = ind["choch_int"][1][i], ind["choch_int"][2][i]
    if c1 < w_mid and c1 > o1 and c1 > swing_hi and c1 > wopen and choch_up:
        return 1
    if c1 > w_mid and c1 < o1 and c1 < swing_lo and c1 < wopen and choch_down:
        return -1
    return 0


def _weekly_exp_sl_tp(c, ind, i, direction, entry, atr):
    pwh, pwl = ind["weekly_pwh"][i], ind["weekly_pwl"][i]
    if pwh is None or pwl is None:
        return None
    leg = pwh - pwl
    if direction == 1:
        sl = min(pwl, entry - 1.5 * atr)
        risk = entry - sl
        if risk <= 0:
            return None
        fib1272 = pwh + 0.272 * leg
        tp = max(pwh, fib1272, entry + 2.6 * risk)
        return sl, tp
    sl = max(pwh, entry + 1.5 * atr)
    risk = sl - entry
    if risk <= 0:
        return None
    fib1272 = pwl - 0.272 * leg
    tp = min(pwl, fib1272, entry - 2.6 * risk)
    return sl, tp


def sig_breakout_acc(c, ind, i, n=20):
    # v2.5.1 - bug trovato il 16/07 (stesso tipo di SAR/BJORGUM/MACD/RSI_DIV):
    # BREAKOUT_ACC usava sig_breakout() generico (1 sola chiusura oltre il
    # range) mentre la vera NXS_Strat_BreakoutAcc() richiede ACCEPTANCE -
    # DUE chiusure consecutive oltre il range, non una - e' il concetto
    # stesso nel nome ("Acc" = Acceptance), non solo un dettaglio. Trovato
    # controllando sistematicamente le altre strategie su richiesta
    # dell'utente dopo i 4 bug gia' trovati su SAR/BJORGUM/MACD/RSI_DIV.
    if i < n + 2:
        return 0
    hh = max(x["high"] for x in c[i - n - 1:i - 1])
    ll = min(x["low"] for x in c[i - n - 1:i - 1])
    c1, c2 = c[i]["close"], c[i - 1]["close"]
    if c1 > hh and c2 > hh:
        return 1
    if c1 < ll and c2 < ll:
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
    #
    # 04/08 - fedelta' verificata riga-per-riga: off-by-one trovato. MQL5 usa
    # shift1 (barra appena chiusa) per la close E la finestra pivot parte da
    # shift2 (iHighest/iLowest con start=2, count=30 -> shift2..31). In
    # questo motore shift1 MQL5 == indice i (stessa convenzione gia' usata
    # per AMD_CONT/SILVER_BULLET/IFVG/LONDON_BO/WEEKLY_EXP) - qui invece
    # c1 usava c[i-1] e la finestra c[i-32:i-2], entrambi spostati indietro
    # di una barra in piu' del dovuto. Corretto: c1=c[i], finestra=c[i-30:i].
    atr = ind["atr"][i]
    if not atr or i < 30:
        return 0
    window = c[i - 30:i]
    if not window:
        return 0
    piv_hi = max(x["high"] for x in window)
    piv_lo = min(x["low"] for x in window)
    c1 = c[i]["close"]
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


def sig_order_block_ext(c, ind, i):
    # 16/07 - variante "esterna" (non un gate sullo stesso bar, una lente
    # diversa sull'origine dell'impulso): richiede che la candela impulso
    # sia nata mentre il trend ESTERNO (timeframe superiore reale,
    # ind["choch_ext"]) era gia' nella stessa direzione - "questo blocco
    # e' l'origine di una gamba strutturale vera", non un impulso qualsiasi.
    atr = ind["atr"][i]
    if not atr or i < 12:
        return 0
    ext_trend = ind["choch_ext"][0]
    for k in range(3, 11):
        idx = i - k
        cd = c[idx]
        if _body(cd) < 1.2 * atr:
            continue
        top, bot = max(cd["open"], cd["close"]), min(cd["open"], cd["close"])
        mid = (top + bot) / 2
        cur = c[i]
        if _bull(cd) and ext_trend[idx] == 1 and cur["low"] <= top \
                and _bull(cur) and cur["close"] > mid:
            return 1
        if _bear(cd) and ext_trend[idx] == -1 and cur["high"] >= bot \
                and _bear(cur) and cur["close"] < mid:
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


def sig_ob_mit_ext(c, ind, i):
    # 16/07 - variante "esterna": stessa logica di sig_ob_mit (impulso +
    # BOS interno a 5 barre) con l'aggiunta del trend ESTERNO vero
    # all'origine dell'impulso, stessa lente di sig_order_block_ext.
    atr = ind["atr"][i]
    if not atr or i < 14:
        return 0
    ext_trend = ind["choch_ext"][0]
    for k in range(3, 11):
        idx = i - k
        cd = c[idx]
        if _body(cd) < 1.2 * atr:
            continue
        top, bot = max(cd["open"], cd["close"]), min(cd["open"], cd["close"])
        mid = (top + bot) / 2
        cur = c[i]
        phi, plo = _hh(c, 5, idx - 1), _ll(c, 5, idx - 1)
        if _bull(cd) and phi and cd["close"] > phi and ext_trend[idx] == 1 \
                and cur["low"] <= top and _bull(cur) and cur["close"] > mid:
            return 1
        if _bear(cd) and plo and cd["close"] < plo and ext_trend[idx] == -1 \
                and cur["high"] >= bot and _bear(cur) and cur["close"] < mid:
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


def sig_fvg_cont_ext(c, ind, i):
    # 16/07 - variante "esterna": stesso gap a 3 candele, ma il filtro
    # EMA50 (proxy di trend locale) e' sostituito dal trend ESTERNO vero
    # (timeframe superiore reale) - "questo gap fa parte di una gamba
    # strutturale maggiore", non solo "il prezzo e' sopra una media".
    if i < 3:
        return 0
    ext_trend = ind["choch_ext"][0][i]
    if c[i]["low"] > c[i - 2]["high"] and ext_trend == 1:
        return 1
    if c[i]["high"] < c[i - 2]["low"] and ext_trend == -1:
        return -1
    return 0


def sig_fvg_mit(c, ind, i):
    # 04/08 - fedelta' verificata riga-per-riga con NXS_Strat_FVG_Mitigation
    # (MQL5 reale): i nomi delle variabili MQL5 sono fuorvianti ("h2/l2" e'
    # in realta' shift5, "h0/l0" e' shift7, non shift2/shift0) - il proxy
    # precedente aveva scambiato quali candele definiscono il gap e la
    # condizione stessa (confrontava candele/direzioni non corrispondenti
    # a nessuno dei due rami MQL5). Riscritta seguendo esattamente MQL5
    # (shift5->i-4, shift7->i-6, shift1->i), "bid" approssimato dal range
    # [low,high] della barra (tocco della zona), non solo la close.
    atr = ind["atr"][i]
    if not atr or i < 7:
        return 0
    h2, l2 = c[i - 4]["high"], c[i - 4]["low"]
    h0, l0 = c[i - 6]["high"], c[i - 6]["low"]
    c1, o1 = c[i]["close"], c[i]["open"]
    cur_lo, cur_hi = c[i]["low"], c[i]["high"]
    body_abs = abs(c1 - o1)
    rejection_bull = (c1 > o1) and (body_abs > atr * 0.35)
    rejection_bear = (c1 < o1) and (body_abs > atr * 0.35)
    if l0 > h2 + atr * 0.15:
        fvg_lo, fvg_hi = h2, l0
        if cur_hi >= fvg_lo and cur_lo <= fvg_hi and rejection_bull:
            return 1
    if h0 < l2 - atr * 0.15:
        fvg_lo, fvg_hi = h0, l2
        if cur_hi >= fvg_lo and cur_lo <= fvg_hi and rejection_bear:
            return -1
    return 0


def _fvg_mit_sl_tp(c, ind, i, direction, entry, atr):
    h2 = c[i - 4]["high"]
    l2 = c[i - 4]["low"]
    if direction == 1:
        return h2 - 0.4 * atr, entry + 2.5 * atr
    return l2 + 0.4 * atr, entry - 2.5 * atr


def sig_ifvg(c, ind, i):
    # 04/08 - fedelta' verificata riga-per-riga con NXS_Strat_IFVG_Reversal
    # (MQL5 reale): il concetto di base (gap violato -> flip) era gia'
    # presente, ma mancavano: buffer ATR sul gap (0.2xATR, non un tocco
    # marginale), filtro di forza sulla candela di reazione (corpo>0.3xATR),
    # e la conferma CHoCH - senza queste il proxy prendeva flip deboli che
    # la vera strategia scarta. Mappatura shift MQL5->indice Python (shift1
    # = barra appena chiusa = i): h2/l2=c[i-1], h4/l4=c[i-3], c1/o1=c[i].
    if i < 4:
        return 0
    atr = ind["atr"][i]
    if not atr:
        return 0
    h2, l2 = c[i - 1]["high"], c[i - 1]["low"]
    h4, l4 = c[i - 3]["high"], c[i - 3]["low"]
    c1, o1 = c[i]["close"], c[i]["open"]
    body1 = abs(c1 - o1)
    reaction_bear = (c1 < o1) and (body1 > atr * 0.3)
    reaction_bull = (c1 > o1) and (body1 > atr * 0.3)
    choch_up, choch_down = ind["choch_int"][1][i], ind["choch_int"][2][i]
    if l2 > h4 + atr * 0.2 and c1 < h4 and reaction_bear and choch_down:
        return -1
    if h2 < l4 - atr * 0.2 and c1 > l4 and reaction_bull and choch_up:
        return 1
    return 0


def _ifvg_sl_tp(c, ind, i, direction, entry, atr):
    h2, l2 = c[i - 1]["high"], c[i - 1]["low"]
    if direction == 1:
        return h2 - 0.5 * atr, entry + 2.4 * atr
    return l2 + 0.5 * atr, entry - 2.4 * atr


def sig_liq_sweep(c, ind, i):
    # sweep del max/min a 20 barre + chiusura di rientro (reversal)
    # NOTA: superata da sig_liq_sweep_ext() il 16/07 - tenuta per riferimento.
    if i < 21:
        return 0
    ph, pl = _hh(c, 20, i - 1), _ll(c, 20, i - 1)
    cur = c[i]
    if ph and cur["high"] > ph and cur["close"] < ph:
        return -1
    if pl and cur["low"] < pl and cur["close"] > pl:
        return 1
    return 0


def sig_liq_sweep_ext(c, ind, i):
    # 16/07 - bug trovato: era l'unica strategia rimasta sul generico
    # "estremo di 20 barre qualsiasi" (sig_liq_sweep sopra) mentre
    # TURTLE_SOUP/SH_BMS_RTO/JUDAS_SWING/LDN_REVERSAL/PO3/AMD_REVERSAL/
    # SILVER_BULLET usano gia' NXS_DetectSweepExt() (PDH/PDL/Asia High-Low),
    # i veri riferimenti di liquidita' ICT. Riusa _sweep_ext_at() (stessa
    # funzione scritta per le 7 strategie a sessione). Test A/B: su 4h senza
    # HTF, PF 0.86->1.32 e DD quasi dimezzato; su D1+HTF (config profilo)
    # il campione cresce 14->141 trade restando positivo - risolve il
    # problema di campione troppo piccolo di LIQ_SWEEP (26 trade reali in
    # 8 anni). Non uniforme su ogni TF, vedi vault per il dettaglio.
    #
    # 16/07 seguito: l'utente ha mostrato 2 esempi reali di trader ICT (screenshot)
    # - in entrambi lo sweep coincide SEMPRE con una vera candela Order Block
    # (corpo forte, "delivery candle"), non un rimbalzo qualsiasi. Aggiunto
    # lo stesso filtro corpo>=0.7xATR gia' usato da TURTLE_SOUP (li' 0.4x,
    # qui serve piu' forte). Test A/B sulla config reale (D1+HTF): PF
    # 1.27->1.63, DD quasi dimezzato (14.25%->6.62%). Migliora su 3 config
    # su 4, peggiora solo sulla combinazione 4h-no-HTF (gia' la migliore
    # trovata prima del fix) - vedi vault per il dettaglio completo.
    sess = ind["sess"]
    sw = _sweep_ext_at(c, sess, i)
    if not sw or not sw["confirmed"]:
        return 0
    atr = ind["atr"][i]
    if not atr:
        return 0
    c1, o1 = c[i]["close"], c[i]["open"]
    if abs(c1 - o1) < 0.7 * atr:
        return 0
    if sw["dir"] == 1 and c1 > o1:
        return 1
    if sw["dir"] == -1 and c1 < o1:
        return -1
    return 0


def _liq_sweep_target(c, ind, i, direction, entry, atr, min_rr=1.2, sl_mult=1.5, pick="nearest"):
    """TP dinamico sulla liquidita' OPPOSTA (PDH/PDL/Asia High-Low + ultimo
    swing esterno confermato) invece di un multiplo fisso di ATR - come
    mostrato negli screenshot dell'utente (setup ICT reali: sweep+OB,
    target sul pool di liquidita' del lato opposto). Ritorna None se non
    c'e' un livello valido -> fallback al TP ATR fisso normale.
    16/07: aggiunto swing_ext (ultimo massimo/minimo confermato su TF
    esterno) - PDH/PDL da solo e' spesso troppo vicino su D1 (e' il giorno
    subito prima, non un vero pool di liquidita' distante) e la condizione
    di RR minimo lo scartava quasi sempre."""
    sess = ind["sess"]
    pdh, pdl = sess["pdh"][i], sess["pdl"][i]
    ah, al = sess["asian_hi"][i], sess["asian_lo"][i]
    swing_hi, swing_lo = ind["swing_ext"][0][i], ind["swing_ext"][1][i]
    risk = atr * sl_mult
    if direction == 1:
        cands = [x for x in (pdh, ah, swing_hi) if x is not None and x > entry]
        if not cands:
            return None
        target = min(cands) if pick == "nearest" else max(cands)
        if (target - entry) < min_rr * risk:
            return None
    else:
        cands = [x for x in (pdl, al, swing_lo) if x is not None and x < entry]
        if not cands:
            return None
        target = max(cands) if pick == "nearest" else min(cands)
        if (entry - target) < min_rr * risk:
            return None
    return target


def _judas_swing_target(c, ind, i, direction, entry, atr, min_rr=0, sl_mult=1.5, pick=None):
    # Fedele a NXS_Strat_JudasSwing: tp = MAX(asianHigh, entry+2.5xrisk) per
    # buy / MIN(asianLow, entry-2.5xrisk) per sell - prende il piu' ambizioso.
    ah, al = ind["sess"]["asian_hi"][i], ind["sess"]["asian_lo"][i]
    risk = atr * sl_mult
    if direction == 1:
        fixed = entry + 2.5 * risk
        return max(ah, fixed) if ah is not None else fixed
    fixed = entry - 2.5 * risk
    return min(al, fixed) if al is not None else fixed


def _ldn_reversal_target(c, ind, i, direction, entry, atr, min_rr=0, sl_mult=1.5, pick=None):
    # Fedele a NXS_Strat_LondonReversal: tp = MAX(asianHigh, entry+2.0xrisk)
    # per buy / MIN(asianLow, entry-2.0xrisk) per sell.
    ah, al = ind["sess"]["asian_hi"][i], ind["sess"]["asian_lo"][i]
    risk = atr * sl_mult
    if direction == 1:
        fixed = entry + 2.5 * risk
        tgt = ah if ah is not None else fixed
        return max(tgt, entry + 2.0 * risk)
    fixed = entry - 2.5 * risk
    tgt = al if al is not None else fixed
    return min(tgt, entry - 2.0 * risk)


def _po3_target(c, ind, i, direction, entry, atr, min_rr=0, sl_mult=1.5, pick=None):
    # Fedele a NXS_Strat_PO3: tp = MAX(asianHigh, entry+2.6xrisk) per buy /
    # MIN(asianLow, entry-2.6xrisk) per sell.
    ah, al = ind["sess"]["asian_hi"][i], ind["sess"]["asian_lo"][i]
    risk = atr * sl_mult
    if direction == 1:
        fixed = entry + 2.6 * risk
        return max(ah, fixed) if ah is not None else fixed
    fixed = entry - 2.6 * risk
    return min(al, fixed) if al is not None else fixed


# TP dinamico (livello di liquidita' opposta invece di ATR fisso), due gruppi:
#
# STRATEGY_TARGETS_ALWAYS - e' cosi' che la vera NXS_Strat_* MQL5 calcola
# il TP di queste strategie (MAX/MIN tra target dinamico e multiplo fisso,
# gia' nel codice reale) - applicato SEMPRE, per fedelta', non come test.
# Il primo giro di test del 16/07 sulle 7 strategie a sessione usava per
# errore lo stesso SL/TP ATR generico per tutte, omettendo questa parte
# gia' presente in MQL5 per queste 3.
STRATEGY_TARGETS_ALWAYS = {
    "JUDAS_SWING": _judas_swing_target,
    "LDN_REVERSAL": _ldn_reversal_target,
    "PO3": _po3_target,
}
# STRATEGY_TARGETS_OPTIN - ipotesi TESTATA ma NON presente nel vero
# NXS_Strat_LiqSweep() MQL5 (che usa solo NXS_DefaultSLTP, ATR fisso) -
# testata su richiesta dell'utente (16/07), risultato misto/non decisivo
# (vedi vault Liq Sweep), quindi resta opt-in (use_dynamic_tp=True),
# NON applicata di default.
STRATEGY_TARGETS_OPTIN = {
    "LIQ_SWEEP": _liq_sweep_target,
}


def sig_turtle_soup(c, ind, i):
    # 04/08 - fedelta' verificata riga-per-riga con NXS_Strat_TurtleSoup
    # (MQL5 reale): usava un falso-breakout su estremo GENERICO a 20 barre,
    # ma la vera strategia (SNXSSweepExt &sw nella firma MQL5) usa il
    # rilevatore di sweep ESTESO (PDH/PDL, priorita' Asia/daily) gia'
    # disponibile in questo motore via _sweep_ext_at() e gia' usato da
    # altre strategie (sig_liq_sweep_ext, sig_silver_bullet) - TURTLE_SOUP
    # semplicemente non lo riusava. Corretto.
    atr = ind["atr"][i]
    if not atr:
        return 0
    c1, o1 = c[i]["close"], c[i]["open"]
    body = abs(c1 - o1)
    if body < atr * 0.4:
        return 0
    sw = _sweep_ext_at(c, ind["sess"], i)
    if not sw:
        return 0
    if sw["sweptPDH"] and c1 < o1 and sw["refHigh"] is not None and c1 < sw["refHigh"]:
        return -1
    if sw["sweptPDL"] and c1 > o1 and sw["refLow"] is not None and c1 > sw["refLow"]:
        return 1
    return 0


def _turtle_soup_sl_tp(c, ind, i, direction, entry, atr):
    sw = _sweep_ext_at(c, ind["sess"], i)
    if not sw:
        return None
    if direction == 1:
        if sw["refLow"] is None:
            return None
        sl = sw["refLow"] - 0.5 * atr
        risk = entry - sl
        if risk <= 0:
            return None
        return sl, entry + 2.0 * risk
    if sw["refHigh"] is None:
        return None
    sl = sw["refHigh"] + 0.5 * atr
    risk = sl - entry
    if risk <= 0:
        return None
    return sl, entry - 2.0 * risk


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


# ---------------------------------------------------------------------------- #
# Strategie a sessione (16/07) - AMD_CONT, AMD_REVERSAL, JUDAS_SWING,
# LDN_REVERSAL, NY_REVERSAL, PO3, SILVER_BULLET. Prima assenti dal motore
# sito ("non testabile", si pensava per limite strutturale dei dati). In
# realta' _fetch_real() scarica gia' candele intraday con timestamp GMT
# reali (vedi sweep multi-TF di TURTLE_SOUP) - il pezzo mancante erano
# queste funzioni, non il dato. Richiedono candele intraday (1h/4h/15m);
# su D1 le sessioni non si distinguono e semplicemente non generano segnali
# (comportamento corretto, non un bug).
#
# Sessioni GMT fedeli a NXS_Sessions.mqh: ASIAN 00-07, LONDON 07-12,
# OVERLAP 12-15, NY 15-20, AFTERNY 20-24.
# AMD fedele a NXS_AMDModel.mqh: state machine per-giorno accumulation ->
# manipulation -> continuation_distribution (2+ close oltre lo stesso lato)
# / reversal_distribution (chiusura di rientro dopo la manipolazione).
# CHoCH: stesso proxy failure-swing gia' usato per TURTLE_SOUP/IFVG (non è
# il vero g_struct fractal-based di MQL5 - approssimazione dichiarata).
def _session_amd_series(candles):
    n = len(candles)
    hour = [None] * n
    date = [None] * n
    for i, cd in enumerate(candles):
        d, hm = cd["time"].split(" ")
        date[i] = d
        hour[i] = int(hm.split(":")[0])

    def _sess(h):
        if h is None:
            return None
        if 0 <= h < 7:
            return "ASIAN"
        if 7 <= h < 12:
            return "LONDON"
        if 12 <= h < 15:
            return "OVERLAP"
        if 15 <= h < 20:
            return "NY"
        return "AFTERNY"

    session = [_sess(h) for h in hour]

    asian_hi_by_date, asian_lo_by_date = {}, {}
    day_hi, day_lo = {}, {}
    for i in range(n):
        d = date[i]
        day_hi[d] = max(day_hi.get(d, -1e18), candles[i]["high"])
        day_lo[d] = min(day_lo.get(d, 1e18), candles[i]["low"])
        if session[i] == "ASIAN":
            asian_hi_by_date[d] = max(asian_hi_by_date.get(d, -1e18), candles[i]["high"])
            asian_lo_by_date[d] = min(asian_lo_by_date.get(d, 1e18), candles[i]["low"])

    dates_sorted = sorted(day_hi.keys())
    pdh_by_date, pdl_by_date = {}, {}
    for idx in range(1, len(dates_sorted)):
        prev = dates_sorted[idx - 1]
        pdh_by_date[dates_sorted[idx]] = day_hi[prev]
        pdl_by_date[dates_sorted[idx]] = day_lo[prev]

    asian_hi = [asian_hi_by_date.get(date[i]) for i in range(n)]
    asian_lo = [asian_lo_by_date.get(date[i]) for i in range(n)]
    pdh = [pdh_by_date.get(date[i]) for i in range(n)]
    pdl = [pdl_by_date.get(date[i]) for i in range(n)]

    amd_phase = [None] * n
    phase, manip_dir, beyond_count, cur_day = None, 0, 0, None
    for i in range(n):
        ah, al = asian_hi[i], asian_lo[i]
        if ah is None or al is None:
            continue
        if date[i] != cur_day:
            cur_day = date[i]
            phase, manip_dir, beyond_count = "ACCUMULATION", 0, 0
        c1 = candles[i]["close"]
        beyond_high, beyond_low = c1 > ah, c1 < al
        if phase == "ACCUMULATION":
            if beyond_high:
                phase, manip_dir, beyond_count = "MANIPULATION", 1, 1
            elif beyond_low:
                phase, manip_dir, beyond_count = "MANIPULATION", -1, 1
        elif phase in ("MANIPULATION", "CONTINUATION_DISTRIBUTION"):
            still_beyond = beyond_high if manip_dir == 1 else beyond_low
            if still_beyond:
                beyond_count += 1
                phase = "CONTINUATION_DISTRIBUTION" if beyond_count >= 2 else "MANIPULATION"
            else:
                phase = "REVERSAL_DISTRIBUTION"
        elif phase == "REVERSAL_DISTRIBUTION":
            opp_beyond = beyond_low if manip_dir == 1 else beyond_high
            if opp_beyond:
                manip_dir, phase, beyond_count = -manip_dir, "MANIPULATION", 1
        amd_phase[i] = (phase, manip_dir)

    return {"hour": hour, "date": date, "session": session,
            "asian_hi": asian_hi, "asian_lo": asian_lo, "pdh": pdh, "pdl": pdl,
            "amd_phase": amd_phase}


def _sweep_ext_at(candles, sess, i):
    if i < 1:
        return None
    h1, l1, c1 = candles[i]["high"], candles[i]["low"], candles[i]["close"]
    ah, al = sess["asian_hi"][i], sess["asian_lo"][i]
    pdh, pdl = sess["pdh"][i], sess["pdl"][i]
    d, level, ref_hi, ref_lo, confirmed = 0, 0, None, None, False
    swept_asia_hi = swept_asia_lo = swept_pdh = swept_pdl = False
    if ah is not None and h1 > ah and c1 < ah:
        swept_asia_hi, d, level, ref_hi, confirmed = True, -1, ah, ah, True
    if pdh is not None and h1 > pdh and c1 < pdh:
        swept_pdh = True
        if not confirmed or pdh > (ref_hi if ref_hi is not None else -1e18):
            d, level, ref_hi, confirmed = -1, pdh, pdh, True
    if al is not None and l1 < al and c1 > al:
        swept_asia_lo, d, level, ref_lo, confirmed = True, 1, al, al, True
    if pdl is not None and l1 < pdl and c1 > pdl:
        swept_pdl = True
        if not confirmed or pdl < (ref_lo if ref_lo is not None else 1e18):
            d, level, ref_lo, confirmed = 1, pdl, pdl, True
    return {"dir": d, "level": level, "refHigh": ref_hi, "refLow": ref_lo,
            "confirmed": confirmed, "sweptAsiaHigh": swept_asia_hi,
            "sweptAsiaLow": swept_asia_lo, "sweptPDH": swept_pdh, "sweptPDL": swept_pdl}


def _choch_at(c, i, look=10):
    # Proxy "grezzo" (rolling-extreme) - lasciato per compatibilita' dov'era
    # gia' usato (TURTLE_SOUP/IFVG test A/B del 16/07 mattina). Superato da
    # _fractal_choch_series()/choch_int-choch_ext per i test successivi.
    if i < 2 * look:
        return (False, False)
    hi_recent = max(x["high"] for x in c[i - look:i])
    hi_older = max(x["high"] for x in c[i - 2 * look:i - look])
    lo_recent = min(x["low"] for x in c[i - look:i])
    lo_older = min(x["low"] for x in c[i - 2 * look:i - look])
    return (lo_recent > lo_older, hi_recent < hi_older)  # (chochUp, chochDown)


# ---------------------------------------------------------------------------- #
# Struttura interna/esterna (16/07) - su richiesta dell'utente: "interna" =
# swing minori sul timeframe di ingresso, "esterna" = swing maggiori su un
# timeframe superiore reale (non solo una finestra piu' larga sullo stesso
# TF). Fedele a NXS_ComputeStructureCore (fractal swing simmetrico, HH+HL/
# LH+LL con isteresi) invece del proxy a rolling-extreme usato finora -
# g_struct/g_structH1 in MQL5 fanno esattamente questo, ma g_structH1 non
# viene mai letta da nessuna strategia (infrastruttura pronta, mai
# collegata - vedi vault NEXUS EA - Audit Fedelta Trigger).
def _fractal_choch_series(candles, wing=3):
    n = len(candles)
    trend = [0] * n
    choch_up = [False] * n
    choch_down = [False] * n
    last_hi = prev_hi = last_lo = prev_lo = None
    cur_trend = 0
    for i in range(n):
        idx = i - wing
        if idx - wing >= 0:
            h, l = candles[idx]["high"], candles[idx]["low"]
            is_hi = all(candles[idx - k]["high"] < h for k in range(1, wing + 1)) and \
                    all(candles[idx + k]["high"] < h for k in range(1, wing + 1))
            is_lo = all(candles[idx - k]["low"] > l for k in range(1, wing + 1)) and \
                    all(candles[idx + k]["low"] > l for k in range(1, wing + 1))
            if is_hi:
                prev_hi, last_hi = last_hi, h
            if is_lo:
                prev_lo, last_lo = last_lo, l
        trend_before = cur_trend
        if None not in (last_hi, prev_hi, last_lo, prev_lo):
            if last_hi > prev_hi and last_lo > prev_lo:
                cur_trend = 1
            elif last_hi < prev_hi and last_lo < prev_lo:
                cur_trend = -1
        c1 = candles[i]["close"]
        cu = last_hi is not None and c1 > last_hi and trend_before == -1
        cd = last_lo is not None and c1 < last_lo and trend_before == 1
        trend[i], choch_up[i], choch_down[i] = cur_trend, cu, cd
    return trend, choch_up, choch_down


def _swing_price_series(candles, wing=3):
    """Prezzo dell'ultimo swing high/low CONFERMATO come di ogni barra
    (stessa logica fractal di _fractal_choch_series, ma qui serve il
    livello di prezzo, non solo il trend/CHoCH) - usato come pool di
    liquidita' piu' significativo di PDH/PDL per il TP dinamico."""
    n = len(candles)
    last_hi_s = [None] * n
    last_lo_s = [None] * n
    last_hi = last_lo = None
    for i in range(n):
        idx = i - wing
        if idx - wing >= 0:
            h, l = candles[idx]["high"], candles[idx]["low"]
            if all(candles[idx - k]["high"] < h for k in range(1, wing + 1)) and \
               all(candles[idx + k]["high"] < h for k in range(1, wing + 1)):
                last_hi = h
            if all(candles[idx - k]["low"] > l for k in range(1, wing + 1)) and \
               all(candles[idx + k]["low"] > l for k in range(1, wing + 1)):
                last_lo = l
        last_hi_s[i], last_lo_s[i] = last_hi, last_lo
    return last_hi_s, last_lo_s


def _external_swing_price_series(candles, factor=4, wing=3):
    """Prezzo dell'ultimo swing high/low su timeframe superiore reale
    (ricampionato), mappato indietro su ogni barra originale con
    forward-fill sull'ultima barra esterna GIA' completata (stesso
    schema di _external_choch_series, niente look-ahead)."""
    n = len(candles)
    resampled = _resample_ohlc(candles, factor)
    r_hi, r_lo = _swing_price_series(resampled, wing=wing)
    ext_hi = [None] * n
    ext_lo = [None] * n
    for i in range(n):
        r_idx = i // factor - 1
        if 0 <= r_idx < len(r_hi):
            ext_hi[i] = r_hi[r_idx]
            ext_lo[i] = r_lo[r_idx]
    return ext_hi, ext_lo


def _resample_ohlc(candles, factor):
    out = []
    n = len(candles) - (len(candles) % factor)
    for i in range(0, n, factor):
        g = candles[i:i + factor]
        out.append({"time": g[0]["time"], "open": g[0]["open"],
                     "high": max(x["high"] for x in g), "low": min(x["low"] for x in g),
                     "close": g[-1]["close"]})
    return out


def _external_choch_series(candles, factor=4, wing=3):
    """CHoCH/trend su timeframe superiore reale (resample di `factor`
    candele), mappato indietro su ogni barra originale con forward-fill
    (solo l'ultima barra esterna GIA' completata, niente look-ahead).
    Ritorna (trend, chochUp, chochDown) come _fractal_choch_series()."""
    n = len(candles)
    resampled = _resample_ohlc(candles, factor)
    r_trend, r_up, r_down = _fractal_choch_series(resampled, wing=wing)
    ext_trend = [0] * n
    ext_up = [False] * n
    ext_down = [False] * n
    for i in range(n):
        r_idx = i // factor - 1   # ultima barra esterna completata prima di i
        if 0 <= r_idx < len(r_up):
            ext_trend[i] = r_trend[r_idx]
            ext_up[i] = r_up[r_idx]
            ext_down[i] = r_down[r_idx]
    return ext_trend, ext_up, ext_down


def sig_amd_cont(c, ind, i):
    # 04/08 - fedelta' verificata riga-per-riga con NXS_Strat_AMD_Continuation
    # (MQL5 reale): il retest usava la CLOSE per entrambe le condizioni
    # (rottura E retest) - la stessa imprecisione che l'MQL5 aveva gia'
    # corretto il 17/07 ("mescolava close della barra 1 con bid live - due
    # punti temporali diversi"). MQL5 usa il LOW della barra per il retest
    # (l1 <= asianHigh+atr*0.6), non la close - un vero "tocco" della
    # fascia, non "la chiusura e' rimasta vicina". Corretto qui.
    sess = ind["sess"]
    ah, al = sess["asian_hi"][i], sess["asian_lo"][i]
    if ah is None or al is None or i < 1:
        return 0
    ph = sess["amd_phase"][i]
    if ph is None or ph[0] != "CONTINUATION_DISTRIBUTION":
        return 0
    if sess["session"][i] not in ("LONDON", "OVERLAP", "NY"):
        return 0
    atr = ind["atr"][i]
    if not atr:
        return 0
    e200, e200p = ind["ema200"][i], ind["ema200"][i - 1] if i > 0 else None
    htf_bull_or_neutral = e200 is None or e200p is None or c[i]["close"] >= e200 or e200 >= e200p
    htf_bear_or_neutral = e200 is None or e200p is None or c[i]["close"] <= e200 or e200 <= e200p
    c1, l1, h1 = c[i]["close"], c[i]["low"], c[i]["high"]
    if c1 > ah and l1 <= ah + atr * 0.6 and htf_bull_or_neutral:
        return 1
    if c1 < al and h1 >= al - atr * 0.6 and htf_bear_or_neutral:
        return -1
    return 0


def _amd_cont_sl_tp(c, ind, i, direction, entry, atr):
    # Fedele a NXS_Strat_AMD_Continuation: SL = min(asianHigh-0.3xATR, mid)
    # per buy (max per sell), TP = entry +/- 2.4x la distanza di rischio
    # COSI' CALCOLATA - non un multiplo ATR libero come usava prima il
    # motore (quel parametro, ottimizzato in una Fase 6 precedente, non
    # esiste nella forma testata nell'EA reale - vedi AMD_CONT_DEEPDIVE.md).
    sess = ind["sess"]
    ah, al = sess["asian_hi"][i], sess["asian_lo"][i]
    if ah is None or al is None:
        return None
    mid = (ah + al) / 2.0
    if direction == 1:
        sl = min(ah - 0.3 * atr, mid)
        risk = entry - sl
        if risk <= 0:
            return None
        return sl, entry + 2.4 * risk
    sl = max(al + 0.3 * atr, mid)
    risk = sl - entry
    if risk <= 0:
        return None
    return sl, entry - 2.4 * risk


def sig_amd_reversal(c, ind, i):
    sess = ind["sess"]
    ph = sess["amd_phase"][i] if i < len(sess["amd_phase"]) else None
    if ph is None or ph[0] != "REVERSAL_DISTRIBUTION":
        return 0
    sw = _sweep_ext_at(c, sess, i)
    if not sw:
        return 0
    choch_up, choch_down = _choch_at(c, i)
    if sw["sweptAsiaHigh"] and choch_down:
        return -1
    if sw["sweptAsiaLow"] and choch_up:
        return 1
    return 0


def sig_judas_swing(c, ind, i):
    sess = ind["sess"]
    if sess["session"][i] not in ("LONDON", "NY"):
        return 0
    h = sess["hour"][i]
    # v2.0: London open 7-10 GMT, NY open 12-15 GMT (kill zone di apertura)
    if not ((7 <= h < 10) or (12 <= h < 15)):
        return 0
    ah, al = sess["asian_hi"][i], sess["asian_lo"][i]
    if ah is None or al is None:
        return 0
    atr = ind["atr"][i]
    if not atr:
        return 0
    sw = _sweep_ext_at(c, sess, i)
    choch_up, choch_down = _choch_at(c, i)
    c1, l1, h1 = c[i]["close"], c[i]["low"], c[i]["high"]
    wicked_down = (sw and (sw["sweptAsiaLow"])) or l1 < al
    if wicked_down and c1 > al and choch_up:
        return 1
    wicked_up = (sw and (sw["sweptAsiaHigh"])) or h1 > ah
    if wicked_up and c1 < ah and choch_down:
        return -1
    return 0


def sig_ldn_reversal(c, ind, i):
    sess = ind["sess"]
    if sess["session"][i] not in ("LONDON", "OVERLAP"):
        return 0
    sw = _sweep_ext_at(c, sess, i)
    if not sw or not sw["confirmed"]:
        return 0
    choch_up, choch_down = _choch_at(c, i)
    c1 = c[i]["close"]
    if (sw["sweptAsiaHigh"] or sw["sweptPDH"]) and c1 < sw["refHigh"] and choch_down:
        return -1
    if (sw["sweptAsiaLow"] or sw["sweptPDL"]) and c1 > sw["refLow"] and choch_up:
        return 1
    return 0


def sig_ny_reversal(c, ind, i, look=48):
    sess = ind["sess"]
    if sess["session"][i] not in ("NY", "OVERLAP"):
        return 0
    if i < look:
        return 0
    london_hi, london_lo = None, None
    for k in range(1, look + 1):
        j = i - k
        if j < 0:
            break
        if sess["hour"][j] is not None and 6 <= sess["hour"][j] < 12:
            hh, ll = c[j]["high"], c[j]["low"]
            london_hi = hh if london_hi is None else max(london_hi, hh)
            london_lo = ll if london_lo is None else min(london_lo, ll)
    if london_hi is None or london_lo is None:
        return 0
    choch_up, choch_down = _choch_at(c, i)
    c1, h1, l1 = c[i]["close"], c[i]["high"], c[i]["low"]
    if h1 > london_hi and c1 < london_hi and choch_down:
        return -1
    if l1 < london_lo and c1 > london_lo and choch_up:
        return 1
    return 0


def sig_po3(c, ind, i):
    sess = ind["sess"]
    ah, al = sess["asian_hi"][i], sess["asian_lo"][i]
    if ah is None or al is None:
        return 0
    atr = ind["atr"][i]
    if not atr:
        return 0
    c1, o1 = c[i]["close"], c[i]["open"]
    if abs(c1 - o1) < atr * 0.6:
        return 0
    sw = _sweep_ext_at(c, sess, i)
    choch_up, choch_down = _choch_at(c, i)
    if sw and sw["sweptAsiaLow"] and c1 > al and c1 > o1 and choch_up:
        return 1
    if sw and sw["sweptAsiaHigh"] and c1 < ah and c1 < o1 and choch_down:
        return -1
    return 0


def _us_dst_start_end(year):
    """Prima domenica di novembre e 2a di marzo (regola USA EDT/EST, DIVERSA
    dalla BST inglese) - granularita' a livello di data (non l'ora esatta
    delle 2:00 locali del cambio), coerente con la precisione oraria gia'
    usata dal resto del motore (sessioni dedotte dal timestamp della
    candela)."""
    import datetime as _dt
    d = _dt.date(year, 3, 1)
    first_sun_mar = d + _dt.timedelta(days=(6 - d.weekday()) % 7)
    dst_start = first_sun_mar + _dt.timedelta(days=7)   # 2a domenica di marzo
    d2 = _dt.date(year, 11, 1)
    dst_end = d2 + _dt.timedelta(days=(6 - d2.weekday()) % 7)   # 1a domenica di novembre
    return dst_start, dst_end


def _is_us_edt(date_str):
    import datetime as _dt
    d = _dt.datetime.strptime(date_str, "%Y-%m-%d").date()
    start, end = _us_dst_start_end(d.year)
    return start <= d < end


def _silver_bullet_series(candles, sess, atr):
    # 04/08 - fedelta' verificata riga-per-riga con NXS_Strat_SilverBullet/
    # NXS_SB_UpdateSide (MQL5 reale): la vera Silver Bullet e' una state
    # machine a 3 stadi su piu' barre (IDLE -> SWEPT -> WAITING_RETURN),
    # non un segnale a barra singola come faceva il proxy precedente (sparava
    # subito al solo sweep-in-killzone, saltando displacement/BOS/FVG/
    # ritorno - confermato anche contro fonti ICT pubbliche esterne, vedi
    # SILVER_BULLET_DEEPDIVE.md). Precalcolato qui (come choch_int/swing_ext)
    # perche' la logica ha memoria fra barre, cosa che le sig_*() stateless
    # del motore non supportano.
    #
    # Mappatura shift MQL5 -> indice Python (questo motore lavora solo su
    # barre chiuse, shift1 MQL5 = barra i corrente):
    #   shift1 (barra appena chiusa)      -> i
    #   shift2 (candela di displacement)  -> i-1
    #   shift3 (candela1 del FVG)         -> i-2
    #   finestra swing (shift 3..14)      -> candles[i-13 : i-1]
    MAX_BARS = 15          # InpSB_MaxBars
    DISP_BODY_ATR = 0.8    # InpSB_DispBodyATR
    SWING_LOOKBACK = 12    # InpSB_SwingLookback
    IDLE, SWEPT, WAITING = 0, 1, 2
    n = len(candles)
    out_sig = [0] * n
    out_level = [None] * n
    st = {d: {"state": IDLE, "bars_waited": 0, "sweep_level": None,
               "fvg_lo": None, "fvg_hi": None} for d in (1, -1)}

    def in_killzone(i):
        h = sess["hour"][i]
        if h is None:
            return False
        edt = _is_us_edt(sess["date"][i])
        kz_ldn_open = (7 <= h < 8) if edt else (8 <= h < 9)     # 03-04 ET
        kz_am = (14 <= h < 15) if edt else (15 <= h < 16)       # 10-11 ET
        kz_pm = (18 <= h < 19) if edt else (19 <= h < 20)       # 14-15 ET
        return kz_ldn_open or kz_am or kz_pm

    for i in range(14, n):
        a = atr[i]
        if not a:
            continue
        for d in (1, -1):
            s = st[d]
            if s["state"] == IDLE:
                sw = _sweep_ext_at(candles, sess, i)
                if in_killzone(i) and sw and sw["confirmed"] and sw["dir"] == d:
                    s["state"], s["bars_waited"], s["sweep_level"] = SWEPT, 0, sw["level"]
                continue
            if s["state"] == SWEPT:
                s["bars_waited"] += 1
                if s["bars_waited"] > MAX_BARS:
                    s["state"] = IDLE
                    continue
                o2, c2 = candles[i - 1]["open"], candles[i - 1]["close"]
                body2 = abs(c2 - o2)
                right_color = (c2 > o2) if d == 1 else (c2 < o2)
                if body2 < a * DISP_BODY_ATR or not right_color:
                    continue
                window = candles[max(0, i - 1 - SWING_LOOKBACK):i - 1]
                if not window:
                    continue
                swing_ref = max(x["high"] for x in window) if d == 1 else min(x["low"] for x in window)
                bos = (c2 > swing_ref) if d == 1 else (c2 < swing_ref)
                if not bos:
                    continue
                c1_high, c1_low = candles[i - 2]["high"], candles[i - 2]["low"]
                c3_high, c3_low = candles[i]["high"], candles[i]["low"]
                if d == 1 and c3_low > c1_high:
                    s["fvg_lo"], s["fvg_hi"] = c1_high, c3_low
                    s["state"], s["bars_waited"] = WAITING, 0
                elif d == -1 and c3_high < c1_low:
                    s["fvg_lo"], s["fvg_hi"] = c3_high, c1_low
                    s["state"], s["bars_waited"] = WAITING, 0
                continue
            if s["state"] == WAITING:
                s["bars_waited"] += 1
                if s["bars_waited"] > MAX_BARS:
                    s["state"] = IDLE
                    continue
                c1 = candles[i]["close"]
                if (d == 1 and c1 < s["sweep_level"]) or (d == -1 and c1 > s["sweep_level"]):
                    s["state"] = IDLE
                    continue
                if s["fvg_hi"] is None or s["fvg_hi"] <= s["fvg_lo"]:
                    continue
                lo, hi = candles[i]["low"], candles[i]["high"]
                if hi < s["fvg_lo"] or lo > s["fvg_hi"]:
                    continue
                out_sig[i] = d
                out_level[i] = s["sweep_level"]
                s["state"] = IDLE
    return out_sig, out_level


def sig_silver_bullet(c, ind, i):
    return ind["sb_signal"][i]


def _silver_bullet_sl_tp(c, ind, i, direction, entry, atr):
    # Fedele a NXS_SB_UpdateSide: SL = sweepLevel -/+ 0.6xATR, TP a multiplo
    # ATR FISSO dall'entry (2.8x, via _smc_tp in MQL5 - non un R-multiplo
    # dello stop, la stessa distinzione gia' documentata per altre
    # strategie SMC in questa sessione).
    level = ind["sb_sweep_level"][i]
    if level is None:
        return None
    if direction == 1:
        return level - 0.6 * atr, entry + 2.8 * atr
    return level + 0.6 * atr, entry - 2.8 * atr


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


# 04/08 - SL/TP strutturale FEDELE (non un multiplo ATR libero) per le
# strategie dove la vera NXS_Strat_* MQL5 lo calcola da livelli di prezzo
# (range asiatico, sweep level, ...) invece che da atr_sl/atr_tp - verificato
# riga-per-riga durante l'audit di fedelta' del 04/08. Applicato SEMPRE
# (bypassa completamente sl/tp generico), non opt-in: e' cosi' che la
# strategia funziona davvero, non un'ipotesi da testare.
STRATEGY_SLTP_ALWAYS = {
    "AMD_CONT": _amd_cont_sl_tp,
    "SILVER_BULLET": _silver_bullet_sl_tp,
    "WEEKLY_EXP": _weekly_exp_sl_tp,
    "IFVG": _ifvg_sl_tp,
    "TURTLE_SOUP": _turtle_soup_sl_tp,
    "FVG_MIT": _fvg_mit_sl_tp,
}


# Strategie con logica Python reale (le altre usano i risultati reali importati)
STRATEGIES = {
    "SCALP_EMA": sig_scalp_ema,
    "SCALP_BB_FADE": sig_scalp_bb_fade,
    "SCALP_RSI_SNAP": sig_scalp_rsi_snap,
    "SCALP_RANGE_BRK": sig_scalp_range_brk,
    "EMA_PULLBACK": sig_ema_pullback,
    "MACD": sig_macd,
    "RSI_DIV": sig_rsi_div,
    "BREAKOUT_ACC": sig_breakout_acc,
    "ADX_RSI": sig_adx_rsi,
    "BOLLINGER": sig_bollinger,
    "BB_SQUEEZE": sig_bb_squeeze,
    "TSI": sig_tsi,
    "ICHIMOKU": sig_ichimoku,
    "LONDON_BO": sig_london_bo,        # 04/08: fedele a NXS_Strat_LondonBO (prima proxy generico)
    "RANGE_FADE": sig_bollinger,      # mean-reversion proxy
    # --- strutturali / SMC (nuove, v2.2.8) ---
    "SAR": sig_sar,
    "BJORGUM": sig_bjorgum,
    "ORDER_BLOCK": sig_order_block_ext,
    "OB_MIT": sig_ob_mit_ext,
    "FVG_CONT": sig_fvg_cont_ext,
    "FVG_MIT": sig_fvg_mit,
    "IFVG": sig_ifvg,
    "LIQ_SWEEP": sig_liq_sweep_ext,
    "TURTLE_SOUP": sig_turtle_soup,
    "STRUCT_REACT": sig_struct_react,
    "MALAYSIAN_SNR": sig_malaysian_snr,
    "OTE_CONT": sig_ote_cont,
    "DISP_REBAL": sig_disp_rebal,
    # Fase A / MM-08: la chiave e' l'id CANONICO. L'alias storico "CISD" resta
    # accettato ovunque tramite RESEARCH_ALIASES, ma non e' piu' l'unica chiave:
    # chi iterava STRATEGIES e confrontava con il registro concludeva che
    # THREE_BAR_DELIVERY_BREAK non avesse implementazione research. Ce l'ha.
    "THREE_BAR_DELIVERY_BREAK": sig_cisd,
    "WEEKLY_EXP": sig_weekly_exp,      # 04/08: fedele a NXS_Strat_WeeklyRangeExp (prima condivideva sig_breakout con LONDON_BO)
    "LIQ_VOID": sig_fvg_cont,         # liquidity void = FVG proxy
    "SH_BMS_RTO": sig_ob_mit,         # sweep+BOS+return proxy
    "SMS_BMS_RTO": sig_ob_mit,        # proxy
    # --- strategie a sessione (16/07) - richiedono candele intraday reali ---
    "AMD_CONT": sig_amd_cont,
    "AMD_REVERSAL": sig_amd_reversal,
    "JUDAS_SWING": sig_judas_swing,
    "LDN_REVERSAL": sig_ldn_reversal,
    "NY_REVERSAL": sig_ny_reversal,
    "PO3": sig_po3,
    "SILVER_BULLET": sig_silver_bullet,
}

# Fase A / MM-08 — retrocompatibilita' esplicita degli id storici.
# Nessun id viene riscritto senza questa mappa: un chiamante che passa "CISD"
# continua a funzionare, e la chiave primaria resta quella canonica.
RESEARCH_ALIASES = {"CISD": "THREE_BAR_DELIVERY_BREAK"}


def resolve_research_key(name: str) -> str:
    """Id storico -> chiave canonica di STRATEGIES. Sconosciuto: invariato."""
    return RESEARCH_ALIASES.get(name, name)


# Canonical live list. Keep the legacy alias temporarily for API compatibility.
STRAT_NAMES = list(LIVE_STRATEGY_IDS)
STRAT_NAMES_36 = STRAT_NAMES


# ----------------------------------------------------------------------------- #
# Backtest engine
# ----------------------------------------------------------------------------- #
def run_backtest(symbol="XAUUSD", timeframe="D1", strategy="ADX_RSI",
                 risk_pct=1.0, atr_sl=1.5, atr_tp=3.0, start_equity=10000.0,
                 max_hold=40, bars=800, strategies=None,
                 htf_filter=False, trend_period=50,
                 breakeven_r=0.0, trailing_atr=0.0, cooldown_bars=0,
                 use_dynamic_tp=False, dynamic_tp_pick="nearest",
                 confirm_bars=0, loss_cooldown_bars=0,
                 spread_price=0.0, commission_r=0.0, slippage_price=0.0,
                 strategy_profiles=None, bar_range=None, session_filter=None):
    # Dati reali via Yahoo per il timeframe scelto (fallback su get_ohlc).
    # GATE applicati (coerenza col backtest): htf_filter (solo nel senso del trend
    # su SMA trend_period), breakeven_r (SL a BE dopo N x rischio), trailing_atr
    # (trailing a N x ATR), cooldown_bars (barre minime tra un trade e il successivo).
    # 17/07 - due leve nuove richieste dall'utente (ipotesi "serve conferma
    # prima di entrare" / "dopo uno stop protetto da BE si puo' rientrare
    # subito, dopo una perdita vera no"):
    # confirm_bars: il segnale deve restare valido per N barre consecutive
    # PRIMA di quella corrente (stessa direzione) prima di essere preso -
    # filtra i cross/condizioni che durano un solo tick e si invertono subito.
    # loss_cooldown_bars: cooldown applicato SOLO dopo un'uscita in perdita
    # vera (pnl<0) - un'uscita a breakeven/trailing (pnl>=0) non blocca il
    # rientro immediato, indipendente dal cooldown_bars generico sopra.
    # 31/07 - due leve di realismo mai presenti prima (11_BACKTEST_CAPABILITY_MATRIX.md
    # elencava "spread/commission/slippage: Missing" come difetto): a
    # spread_price=0/commission_r=0 (default, invariato) il comportamento e'
    # identico a prima.
    # spread_price: spread in unita' di prezzo grezzo (es. 0.30 per XAUUSD a
    # $0.30) applicato UNA VOLTA per trade round-trip (convenzione
    # semplificata: costa quanto attraversare bid/ask una volta, non due
    # meta' separate su entry+exit) - convertito in R dividendo per
    # risk_dist del trade specifico, cosi' pesa di piu' sugli SL stretti
    # (dove infatti pesa di piu' anche nella realta').
    # commission_r: costo fisso in multipli di R per round-trip, alternativa
    # semplice a una % sul nozionale - questo motore lavora in R-multipli
    # astratti (risk_money), non in lotti/nozionale reali, quindi una
    # percentuale di commissione avrebbe bisogno di un valore-lotto che qui
    # non esiste; un costo fisso in R e' l'approssimazione onesta compatibile
    # con l'astrazione esistente, non una simulazione di commissione vera.
    # slippage_price: movimento avverso aggiuntivo (unita' di prezzo grezzo)
    # su ogni fill "a mercato" - APPLICATO all'entry (sempre a mercato) e
    # all'uscita SL/TIME (anch'esse a mercato, quindi soggette a slittare),
    # MAI alla TP (ordine limite: si presume riempito al prezzo richiesto o
    # meglio, come nella prassi broker reale). Convertito in R come spread.
    # 04/08 - strategy_profiles: {strat_id: {"atr_sl":.., "atr_tp":.., "breakeven_r":..,
    # "trailing_atr":..}} - override PER STRATEGIA di sl/tp/gestione, usato SOLO
    # quando piu' strategie girano insieme (strategies=[...]) e ognuna ha il
    # proprio profilo ottimizzato (find_best_profiles.py). Senza questo, un
    # test multi-strategia applicava lo stesso sl/tp/be/trail a TUTTE
    # indipendentemente da chi genera il segnale - non e' come funziona l'EA
    # reale (NXS_DefaultSLTP e' gia' keyed by stratName in MQL5). Strategia
    # assente dal dict o strategy_profiles=None -> usa i parametri globali
    # (comportamento invariato).
    candles, src = _fetch_real(symbol, timeframe, bars)
    # 04/08 - bar_range: (start_frac, end_frac) su [0,1], per isolare una
    # finestra temporale CONTIGUA della stessa serie (es. (0.0,0.6)=prime 60%
    # "in-sample", (0.6,1.0)=ultime 40% "out-of-sample", MAI viste durante
    # Fase 1-3 - NQROS Fase 4). None (default) = comportamento invariato,
    # tutta la serie disponibile. Gli indicatori (EMA/ATR/...) si ri-scaldano
    # dall'inizio della finestra tagliata, non hanno memoria del "prima" -
    # tradeoff standard del walk-forward testing, non un bug.
    if bar_range is not None:
        n = len(candles)
        i0 = max(0, int(n * bar_range[0]))
        i1 = min(n, int(n * bar_range[1]))
        candles = candles[i0:i1]
    ind = _prep(candles)
    strat_list = strategies or ([strategy] if strategy else list(STRATEGIES))
    strat_list = list(require_strategies(strat_list, research=True))
    # Un chiamante puo' passare id storico e id canonico della stessa strategia
    # (es. "CISD" e "THREE_BAR_DELIVERY_BREAK"): risolti alla stessa chiave, la
    # strategia girerebbe due volte e comparirebbe due volte nei risultati.
    strat_list = list(dict.fromkeys(resolve_research_key(s) for s in strat_list))
    unavailable = [s for s in strat_list if s not in STRATEGIES]
    if unavailable:
        raise ValueError(f"research engine implementation missing: {', '.join(unavailable)}")

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
    last_loss_i = -10 ** 9    # per il loss_cooldown_bars (solo perdite vere)

    for i in range(2, len(candles)):
        px = candles[i]["close"]
        # gestione posizione aperta
        if pos:
            hi, lo = candles[i]["high"], candles[i]["low"]
            risk_dist = pos["risk_dist"]
            # --- MAE/MFE: massima escursione avversa/favorevole in R, sul
            # rischio ORIGINALE (non su uno SL spostato da BE/trailing).
            # Nota (31/07): il MAE da solo NON distingue "stop troppo
            # stretto" da "segnale sbagliato" per i trade usciti in SL - e'
            # quasi sempre >= 1R per costruzione. E' il MFE dei perdenti
            # (quanto erano andati a favore prima di girare) il segnale
            # diagnostico utile - vedi _metrics().
            if risk_dist > 0:
                adverse = (pos["entry"] - lo) if pos["dir"] == 1 else (hi - pos["entry"])
                favorable = (hi - pos["entry"]) if pos["dir"] == 1 else (pos["entry"] - lo)
                pos["mae_r"] = max(pos["mae_r"], adverse / risk_dist)
                pos["mfe_r"] = max(pos["mfe_r"], favorable / risk_dist)
            # --- BREAKEVEN: SL a entry dopo breakeven_r x rischio ---
            # (04/08: usa l'override per-strategia se presente, altrimenti il
            # parametro globale - vedi nota strategy_profiles sopra)
            pos_be = pos.get("breakeven_r", breakeven_r)
            pos_trail = pos.get("trailing_atr", trailing_atr)
            if pos_be > 0 and risk_dist > 0:
                prog = (hi - pos["entry"]) if pos["dir"] == 1 else (pos["entry"] - lo)
                if prog >= pos_be * risk_dist:
                    if pos["dir"] == 1:
                        pos["sl"] = max(pos["sl"], pos["entry"])
                    else:
                        pos["sl"] = min(pos["sl"], pos["entry"])
            # --- TRAILING ATR: insegue lo SL a trailing_atr x ATR ---
            if pos_trail > 0:
                a = ind["atr"][i] or 0
                if a > 0:
                    if pos["dir"] == 1:
                        pos["sl"] = max(pos["sl"], px - pos_trail * a)
                    else:
                        pos["sl"] = min(pos["sl"], px + pos_trail * a)
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
                # Costi di realismo (31/07): spread convertito in R sul rischio di
                # QUESTO trade (pesa di piu' su SL stretti), commissione gia' in R.
                spread_r = (spread_price / rd) if spread_price > 0 else 0.0
                # Slippage: sull'entry (sempre a mercato) + sull'uscita SE a
                # mercato (SL/TIME). La TP (ordine limite) non slitta contro
                # di noi - assunzione standard broker.
                slip_r = 0.0
                if slippage_price > 0:
                    slip_r = slippage_price / rd   # entry, sempre
                    if reason in ("SL", "TIME"):
                        slip_r += slippage_price / rd   # uscita a mercato
                r_mult_net = r_mult - spread_r - commission_r - slip_r
                pnl = round(r_mult_net * pos["risk_money"], 2)
                equity += pnl
                trades.append({
                    "ticket": len(trades) + 1, "symbol": symbol, "strategy": pos["strat"],
                    "side": "BUY" if pos["dir"] == 1 else "SELL",
                    "openPrice": round(pos["entry"], 5), "closePrice": round(exitpx, 5),
                    "pnl": pnl, "r": round(r_mult_net, 2), "r_gross": round(r_mult, 2),
                    "mae_r": round(pos["mae_r"], 2), "mfe_r": round(pos["mfe_r"], 2),
                    "reason": reason,
                    "openTime": candles[pos["open_i"]]["time"], "closeTime": candles[i]["time"],
                })
                curve.append({"i": i, "equity": round(equity, 2),
                              "ts": str(candles[i]["time"]), "close": candles[i]["close"]})
                pos = None
                last_close_i = i
                if pnl < 0:
                    last_loss_i = i
            continue
        # --- COOLDOWN: barre minime tra un trade e il successivo ---
        if cooldown_bars > 0 and (i - last_close_i) < cooldown_bars:
            continue
        # --- LOSS COOLDOWN: barre minime SOLO dopo una perdita vera (pnl<0) ---
        if loss_cooldown_bars > 0 and (i - last_loss_i) < loss_cooldown_bars:
            continue
        # nuovo segnale
        atr = ind["atr"][i]
        if not atr or atr <= 0:
            continue
        sig, who = 0, None
        for s in strat_list:
            v = STRATEGIES[s](candles, ind, i)
            if v == 0:
                continue
            # --- CONFIRM: il segnale deve reggere per N barre precedenti
            # consecutive nella stessa direzione prima di essere preso ---
            if confirm_bars > 0:
                ok = True
                for k in range(1, confirm_bars + 1):
                    if i - k < 0 or STRATEGIES[s](candles, ind, i - k) != v:
                        ok = False
                        break
                if not ok:
                    continue
            sig, who = v, s
            break
        # --- HTF FILTER: prendi solo nel senso del trend (close vs SMA) ---
        if sig != 0 and htf_filter:
            sma = _sma(i, int(trend_period))
            if sma is not None:
                if (sig == 1 and px < sma) or (sig == -1 and px > sma):
                    sig = 0
        # --- SESSION FILTER (04/08): prendi solo se la sessione GMT della
        # barra e' tra quelle ammesse - gate AGGIUNTIVO sopra quello gia'
        # interno alle strategie a sessione (es. sig_amd_cont ammette
        # LONDON/OVERLAP/NY; session_filter puo' restringere ulteriormente,
        # es. {"LONDON","NY"} per escludere una sessione debole trovata in
        # analisi). None (default) = nessun filtro, comportamento invariato.
        if sig != 0 and session_filter is not None:
            cur_sess = ind["sess"]["session"][i]
            if cur_sess not in session_filter:
                sig = 0
        if sig != 0:
            # 04/08: override per-strategia (solo per chi e' presente nel dict -
            # le altre restano sui parametri globali passati alla funzione).
            prof = (strategy_profiles or {}).get(who, {})
            eff_sl = prof.get("atr_sl", atr_sl)
            eff_tp = prof.get("atr_tp", atr_tp)
            risk_money = equity * (risk_pct / 100.0)
            sl = px - sig * atr * eff_sl
            tp = px + sig * atr * eff_tp
            # STRATEGY_SLTP_ALWAYS: SL *E* TP strutturali fedeli al vero
            # MQL5 (non un multiplo ATR) - bypassa completamente il calcolo
            # generico sopra, sempre attivo dove presente.
            sltp_fn = STRATEGY_SLTP_ALWAYS.get(who)
            if sltp_fn:
                dyn = sltp_fn(candles, ind, i, sig, px, atr)
                if dyn is not None:
                    sl, tp = dyn
            # STRATEGY_TARGETS_ALWAYS: fedelta' al vero calcolo MQL5, sempre attivo.
            target_fn = STRATEGY_TARGETS_ALWAYS.get(who)
            # STRATEGY_TARGETS_OPTIN: ipotesi non presente in MQL5, solo se richiesta.
            if not target_fn and use_dynamic_tp:
                target_fn = STRATEGY_TARGETS_OPTIN.get(who)
            if target_fn and not sltp_fn:
                dyn_tp = target_fn(candles, ind, i, sig, px, atr,
                                    sl_mult=eff_sl, pick=dynamic_tp_pick)
                if dyn_tp is not None:
                    tp = dyn_tp
            pos = {"dir": sig, "entry": px, "sl": sl, "tp": tp, "open_i": i,
                   "risk_money": risk_money, "strat": who,
                   "risk_dist": abs(px - sl), "mae_r": 0.0, "mfe_r": 0.0,
                   "breakeven_r": prof.get("breakeven_r", breakeven_r),
                   "trailing_atr": prof.get("trailing_atr", trailing_atr)}

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
    # 31/07 - corretto un mio errore di analisi durante il primo run reale di
    # prova: il MAE di un trade uscito in SL e' quasi tautologicamente >= 1R
    # (per finire in perdita lo stop DEVE essere stato toccato, cioe' il
    # prezzo E' andato contro di ~1R per definizione) - "vicino al MAE" non
    # distingue nulla, viene ~100% su qualunque strategia. Il segnale utile
    # e' il MFE dei perdenti: quanto il prezzo era andato A FAVORE prima di
    # girare e stoppare. MFE alto (vicino al target) = trade quasi vincente,
    # rigirato - un trailing/TP piu' vicino potrebbe aiutare. MFE vicino a 0
    # = il trade era sbagliato fin dall'inizio, nessun aggiustamento di
    # uscita lo salva.
    loss_mfes = [t["mfe_r"] for t in losses if "mfe_r" in t]
    avg_loss_mfe_r = round(sum(loss_mfes) / len(loss_mfes), 2) if loss_mfes else None
    near_miss_losses = sum(1 for m in loss_mfes if m >= 0.5)   # arrivato a meta' strada verso un 1:1 prima di girare
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
        "avg_loss_mfe_r": avg_loss_mfe_r,
        "near_miss_loss_pct": round(near_miss_losses / len(losses) * 100, 1) if losses else None,
        "equity_curve": curve,
        "trade_list": trades[-200:],
    }


def optimize(symbol="XAUUSD", strategy="ADX_RSI", sweep_management=False, **kw):
    # 31/07 - griglia SL/TP invariata di default (stesso comportamento di
    # prima). sweep_management=True aggiunge breakeven_r/trailing_atr, gia'
    # accettati da run_backtest ma mai spazzolati qui - 3x3x3x3=81 run invece
    # di 9, usare con giudizio (ogni run e' cache-friendly sullo stesso feed,
    # ma comunque piu' lento).
    be_grid = (0.0, 1.0, 1.5) if sweep_management else (0.0,)
    trail_grid = (0.0, 1.5, 2.5) if sweep_management else (0.0,)
    results = []
    for sl in (1.0, 1.5, 2.0):
        for tp in (2.0, 3.0, 4.0):
            for be in be_grid:
                for trail in trail_grid:
                    r = run_backtest(symbol=symbol, strategy=strategy, atr_sl=sl, atr_tp=tp,
                                     breakeven_r=be, trailing_atr=trail, **kw)
                    row = {"atr_sl": sl, "atr_tp": tp, "profit_factor": r["profit_factor"],
                           "net_pnl": r["net_pnl"], "win_rate": r["win_rate"],
                           "max_dd_pct": r["max_dd_pct"], "trades": r["trades"]}
                    if sweep_management:
                        row["breakeven_r"] = be
                        row["trailing_atr"] = trail
                    results.append(row)
    ranked = sorted(results, key=lambda x: (x["profit_factor"] or 0), reverse=True)
    return {"demo": False, "symbol": symbol, "strategy": strategy,
            "sweep_management": sweep_management,
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
