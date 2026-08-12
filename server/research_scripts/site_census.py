#!/usr/bin/env python3
"""
12/08 - richiesta esplicita dell'utente: rifare il censimento di tutte le
59 strategie attraverso il motore DEL SITO (Render), non la chiamata
diretta a run_backtest usata finora. Scoperta durante la preparazione:
il sito ha uno storico Dukascopy piu' ampio di quello locale usato in
sessione (2016-08-11 -> oggi, contro 2019-05-20 -> oggi locale, ~3 anni
in piu') - "adesso che abbiamo tutto lo storico" si riferisce a questo,
non solo a un refresh.

Stesso metodo di server/research_scripts/full_census.py: flat baseline
SL1.5x/TP3.0x, IS(60%)/OOS(40%), un TF per strategia (real profile TF
dove noto). bars=200000 forza il motore a usare TUTTO lo storico
disponibile su ogni TF.

v2 - il primo giro ha saturato il backend (Render "starter", presumibilmente
un solo worker) dopo 2 richieste pesanti consecutive (AMD_CONT 30m su
2016-2026 = molte migliaia di barre), causando una cascata di 502 sulle
richieste successive mentre il worker era ancora occupato. Aggiunto:
retry con backoff, pausa piu' ampia tra strategie, salvataggio
incrementale (resume-safe) in results.json.
"""
import json
import os
import sys
import time
import urllib.request

BASE = "https://nexus-backend-8o4y.onrender.com"
COOKIE_FILE = "/tmp/claude-0/-home-user-MAX/34f6cd69-3d6f-5b1c-ba8c-109afa64ad27/scratchpad/nexus_cookies.txt"
RESULTS_FILE = "/tmp/claude-0/-home-user-MAX/34f6cd69-3d6f-5b1c-ba8c-109afa64ad27/scratchpad/site_census_results.json"
BARS = 200000

TF_MAP = {
    "BREAKOUT_ACC": "1d", "TURTLE_SOUP": "1h", "MACD": "4h", "LONDON_BO": "4h",
    "FVG_MIT": "4h", "LIQ_SWEEP": "1d", "AMD_CONT": "30m", "FVG_CONT": "4h",
    "TSI": "1d", "ADX_RSI": "1d", "SAR": "4h", "EMA_PULLBACK": "1h",
    "THREE_BAR_DELIVERY_BREAK": "4h", "LDN_REVERSAL": "15m", "AMD_REVERSAL": "15m",
    "CRT": "30m",
    "BB_SQUEEZE": "1d", "BJORGUM": "4h", "BOLLINGER": "1d", "DISP_REBAL": "4h",
    "ICHIMOKU": "4h", "IFVG": "4h", "LIQ_VOID": "4h", "MALAYSIAN_SNR": "1d",
    "OB_MIT": "30m", "ORDER_BLOCK": "30m", "OTE_CONT": "15m", "RANGE_FADE": "1d",
    "RSI_DIV": "1h", "SH_BMS_RTO": "1h", "SMS_BMS_RTO": "1d", "STRUCT_REACT": "1h",
    "WEEKLY_EXP": "1h",
    "FVG_CONT_V2": "4h", "ORDER_BLOCK_V2": "30m", "OTE_CONT_V2": "15m",
    "SH_BMS_RTO_V2": "1h", "SILVER_BULLET_V2": "1h", "SILVER_BULLET": "1h",
    "MALAYSIAN_SNR_BREAKOUT": "4h", "MALAYSIAN_SNR_V2_RETEST": "1h",
    "MALAYSIAN_SNR_V2_STAGE1": "1h", "MALAYSIAN_SNR_V2_STAGE3": "1h",
    "JUDAS_SWING": "1h", "NY_REVERSAL": "1h", "PO3": "1h",
    "SCALP_BB_FADE": "15m", "SCALP_EMA": "15m", "SCALP_RANGE_BRK": "15m",
    "SCALP_RSI_SNAP": "15m",
    "CISD_TRUE": "1h", "FVG_MIT_WINDOW": "4h", "IFVG_CHOCH_WINDOW": "4h",
    "MALAYSIAN_SNR_V2_RETEST_OUTRANGE": "30m", "NY_REVERSAL_CHOCH_WINDOW": "1h",
    "SMS_BMS_RTO_CHOCH_WINDOW": "1d", "TSI_EXTREME": "1d",
    "TURTLE_SOUP_CHOCH": "4h",
    "ELLIOTT": "4h",
}


def load_cookie_header():
    parts = []
    with open(COOKIE_FILE) as f:
        for raw in f:
            l = raw.strip()
            if not l:
                continue
            if l.startswith("#HttpOnly_"):
                l = l[len("#HttpOnly_"):]
            elif l.startswith("#"):
                continue
            fields = l.split("\t")
            if len(fields) >= 7:
                parts.append(f"{fields[5]}={fields[6]}")
    return "; ".join(parts)


COOKIE_HEADER = load_cookie_header()


def call(strat, tf, bar_range, retries=3):
    body = {
        "symbol": "XAUUSD", "timeframe": tf, "strategy": strat, "strategies": [strat],
        "risk_pct": 1.0, "atr_sl": 1.5, "atr_tp": 3.0,
        "bars": BARS, "bar_range": list(bar_range),
    }
    data = json.dumps(body).encode()
    last_err = ""
    for attempt in range(retries):
        req = urllib.request.Request(
            f"{BASE}/api/backtest/run", data=data, method="POST",
            headers={"Content-Type": "application/json", "Cookie": COOKIE_HEADER},
        )
        try:
            with urllib.request.urlopen(req, timeout=150) as resp:
                d = json.loads(resp.read())
                m = d.get("metrics", {})
                return {"trades": d.get("trades_count"), "pf": m.get("profit_factor"),
                        "dd": m.get("max_dd_pct")}
        except Exception as e:
            last_err = str(e)[:80]
            if attempt < retries - 1:
                time.sleep(20 * (attempt + 1))
    return {"trades": 0, "pf": None, "dd": None, "err": last_err}


def load_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return {}


def save_results(results):
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=1)


def is_complete(entry):
    return entry and not entry.get("is", {}).get("err") and not entry.get("oos", {}).get("err")


def main():
    results = load_results()
    names = sorted(TF_MAP.keys())
    for strat in names:
        tf = TF_MAP[strat]
        existing = results.get(strat)
        if is_complete(existing):
            is_r, oos_r = existing["is"], existing["oos"]
        else:
            is_r = call(strat, tf, (0.0, 0.6))
            oos_r = call(strat, tf, (0.6, 1.0))
            results[strat] = {"tf": tf, "is": is_r, "oos": oos_r}
            save_results(results)
        err = is_r.get("err") or oos_r.get("err") or ""
        print(f"{strat:<34}{tf:<5} IS pf={str(is_r['pf']):<6}n={str(is_r['trades']):<6}dd={is_r['dd']}  "
              f"OOS pf={str(oos_r['pf']):<6}n={str(oos_r['trades']):<6}dd={oos_r['dd']}  {err}", flush=True)
        time.sleep(8.0)


if __name__ == "__main__":
    main()
