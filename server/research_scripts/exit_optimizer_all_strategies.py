#!/usr/bin/env python3
"""
12/08 - stessa ricerca di uscite (SL/TP/breakeven/trailing) fatta oggi per
CRT/FVG_CONT, estesa a TUTTE le 58 strategie del motore (nucleo + fuori
nucleo), richiesta esplicita dell'utente.

METODOLOGIA CORRETTA (dopo la scoperta di oggi sull'overlay trailing
sempre attivo - vedi vault "Ottimizzazione Uscite Strutturali CRT e
FVG_CONT (12-08)", sezione "Scoperta critica"):

1. Il vero baseline "live" di ogni strategia NON e' il flat sl1.5/tp3.0 -
   e' quello che gira davvero: se la strategia ha un profilo in
   NXS_Profile_Get (MQL5), si usano QUEI valori (slMult/tpMult/htf/beR/
   trailATR) come punto di partenza, non un default piatto. Parsing
   diretto dal file .mqh (non trascritto a mano - se il profilo cambia,
   questo script resta corretto).
2. L'overlay ATR trailing (NXS_TrailingATR.mqh) e' SEMPRE attivo di
   default per tutte le strategie (InpUseAtrTrail=true), larghezza da
   NXS_Profile_TrailK(nome) o fallback globale InpAtrTrailMult=2.5,
   attivazione dopo InpAtrTrailActivateATR=1.0 x ATR di profitto - non
   esiste uno switch per-strategia per spegnerlo. Trattato quindi come
   VINCOLO FISSO (trailing_atr=overlay_width, trailing_activate_atr=1.0),
   non come variabile della griglia - la griglia sweepa solo
   htf/sl/tp/be sopra questo vincolo.
3. Se sl/tp del profilo sono strutturalmente inerti per una strategia
   (es. CRT - SL/TP ancorato al pattern, non ad ATR - vedi
   STRATEGY_SLTP_ALWAYS in backtest.py), rilevato EMPIRICAMENTE (due
   sl/tp molto diversi danno lo stesso risultato) e la griglia sl/tp
   viene saltata per quella strategia, non sprecata.
4. Filtro anti-overfitting IS adattivo: le strategie D1/1w hanno
   naturalmente pochi trade - soglia proporzionale al campione IS del
   baseline (non un n>50 fisso che scarterebbe ogni candidato per una
   strategia gia' sottile in partenza).
5. Un candidato deve battere l'OOS del vero baseline live per essere
   segnalato. Per il migliore: walk-forward a 5 finestre + punteggi di
   robustezza/calmar (stessa formula di oggi).

Risultati salvati incrementalmente in JSON (resume-safe, salta le
strategie gia' completate) - il giro su 58 strategie e' lungo, pensato
per girare in background.
"""
import sys
import os
import re
import json
import time
import statistics
import itertools

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import backtest as bt

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
MQH_PROFILES = os.path.join(REPO_ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyProfiles.mqh")
OUT_PATH = os.path.join(REPO_ROOT, "server", "research_scripts", "exit_optimizer_all_results.json")

BARS = 110000
IS_RANGE, OOS_RANGE = (0.0, 0.6), (0.6, 1.0)
N_WINDOWS = 5
GLOBAL_TRAIL_WIDTH = 2.5     # InpAtrTrailMult
GLOBAL_TRAIL_ACTIVATE = 1.0  # InpAtrTrailActivateATR

TF_MAP = {  # fallback TF per strategie senza profilo MQL5 (da site_census.py)
    "BREAKOUT_ACC": "1d", "TURTLE_SOUP": "1h", "MACD": "4h", "LONDON_BO": "4h",
    "FVG_MIT": "4h", "LIQ_SWEEP": "1d", "AMD_CONT": "30m", "FVG_CONT": "4h",
    "TSI": "1d", "ADX_RSI": "1d", "SAR": "4h", "EMA_PULLBACK": "1h",
    "THREE_BAR_DELIVERY_BREAK": "4h", "LDN_REVERSAL": "15m", "AMD_REVERSAL": "15m",
    "CRT": "30m", "BB_SQUEEZE": "1d", "BJORGUM": "4h", "BOLLINGER": "1d",
    "DISP_REBAL": "4h", "ICHIMOKU": "4h", "IFVG": "4h", "LIQ_VOID": "4h",
    "MALAYSIAN_SNR": "1d", "OB_MIT": "30m", "ORDER_BLOCK": "30m", "OTE_CONT": "15m",
    "RANGE_FADE": "1d", "RSI_DIV": "1h", "SH_BMS_RTO": "1h", "SMS_BMS_RTO": "1d",
    "STRUCT_REACT": "1h", "WEEKLY_EXP": "1h", "FVG_CONT_V2": "4h",
    "ORDER_BLOCK_V2": "30m", "OTE_CONT_V2": "15m", "SH_BMS_RTO_V2": "1h",
    "SILVER_BULLET_V2": "1h", "SILVER_BULLET": "1h", "MALAYSIAN_SNR_BREAKOUT": "4h",
    "MALAYSIAN_SNR_V2_RETEST": "1h", "MALAYSIAN_SNR_V2_STAGE1": "1h",
    "MALAYSIAN_SNR_V2_STAGE3": "1h", "JUDAS_SWING": "1h", "NY_REVERSAL": "1h",
    "PO3": "1h", "SCALP_BB_FADE": "15m", "SCALP_EMA": "15m",
    "SCALP_RANGE_BRK": "15m", "SCALP_RSI_SNAP": "15m", "CISD_TRUE": "1h",
    "FVG_MIT_WINDOW": "4h", "IFVG_CHOCH_WINDOW": "4h",
    "MALAYSIAN_SNR_V2_RETEST_OUTRANGE": "30m", "NY_REVERSAL_CHOCH_WINDOW": "1h",
    "SMS_BMS_RTO_CHOCH_WINDOW": "1d", "TSI_EXTREME": "1d", "TURTLE_SOUP_CHOCH": "4h",
}

PERIOD_TO_TF = {
    "M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m",
    "H1": "1h", "H4": "4h", "D1": "1d", "W1": "1w", "CURRENT": None,
}


def extract_function_body(text, signature_start):
    idx = text.index(signature_start)
    brace_start = text.index("{", idx)
    depth = 0
    i = brace_start
    while True:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start:i + 1]
        i += 1


def parse_mql5_profiles():
    with open(MQH_PROFILES) as f:
        text = f.read()

    get_body = extract_function_body(text, "bool NXS_Profile_Get(const string name")
    tf_body = extract_function_body(text, "ENUM_TIMEFRAMES NXS_Profile_TF(const string name)")
    trailk_body = extract_function_body(text, "double NXS_Profile_TrailK(const string name)")

    profiles = {}
    pat = re.compile(
        r'if\(name == "([A-Z0-9_]+)"\)\s*\{\s*'
        r'slMult=([\d.]+);\s*tpMult=([\d.]+);\s*htf=(true|false)\s*;\s*'
        r'beR=([\d.]+);\s*trailATR=([\d.]+);\s*return true;\s*\}'
    )
    for m in pat.finditer(get_body):
        name, sl, tp, htf, be, trail = m.groups()
        profiles[name] = {
            "sl": float(sl), "tp": float(tp), "htf": htf == "true",
            "be": float(be), "trailATR": float(trail),
        }

    tf_pat = re.compile(r'if\(name == "([A-Z0-9_]+)"\)\s*return PERIOD_(\w+);')
    tfs = {}
    for m in tf_pat.finditer(tf_body):
        name, period = m.groups()
        tf = PERIOD_TO_TF.get(period)
        if tf:
            tfs[name] = tf

    trailk_pat = re.compile(r'if\(name == "([A-Z0-9_]+)"\)\s*return ([\d.]+);')
    trailks = {}
    for m in trailk_pat.finditer(trailk_body):
        name, k = m.groups()
        trailks[name] = float(k)

    return profiles, tfs, trailks


def live_config(strat, profiles, tfs, trailks):
    p = profiles.get(strat)
    tf = tfs.get(strat) or TF_MAP.get(strat, "1d")
    overlay_width = trailks.get(strat, GLOBAL_TRAIL_WIDTH)
    if p:
        return {
            "tf": tf, "sl": p["sl"], "tp": p["tp"], "htf": p["htf"], "be": p["be"],
            "overlay_width": overlay_width, "overlay_act": GLOBAL_TRAIL_ACTIVATE,
            "has_profile": True,
        }
    return {
        "tf": tf, "sl": 1.5, "tp": 3.0, "htf": False, "be": 0.0,
        "overlay_width": overlay_width, "overlay_act": GLOBAL_TRAIL_ACTIVATE,
        "has_profile": False,
    }


def call(tf, strat, bar_range, sl, tp, be, htf, trail_width):
    # trail_width e' la LARGHEZZA dell'overlay (NXS_Profile_TrailK, configurabile
    # per-strategia) - MAI 0: l'overlay e' sempre attivo (InpUseAtrTrail=true di
    # default, nessuno switch per-strategia), solo la larghezza si puo' portare.
    # L'attivazione (InpAtrTrailActivateATR) resta fissa a 1.0 - quella si',
    # globale e non per-strategia (rimossa la versione per-strategia in v2.4.7).
    return bt.run_backtest(symbol="XAUUSD", timeframe=tf, strategy=strat, strategies=[strat],
                            risk_pct=1.0, bars=BARS, bar_range=bar_range, atr_sl=sl, atr_tp=tp,
                            breakeven_r=be, trailing_atr=trail_width,
                            trailing_activate_atr=GLOBAL_TRAIL_ACTIVATE, htf_filter=htf)


def probe_sltp_inert(cfg, strat):
    """Empirico: sl/tp fanno differenza per questa strategia? (CRT-style override)."""
    a = call(cfg["tf"], strat, IS_RANGE, 1.0, 2.0, 0.0, cfg["htf"], cfg["overlay_width"])
    b = call(cfg["tf"], strat, IS_RANGE, 2.5, 6.0, 0.0, cfg["htf"], cfg["overlay_width"])
    if a.get("trades", 0) == 0 and b.get("trades", 0) == 0:
        return None  # nessun trade in IS a prescindere - strategia troppo rara, gestito a monte
    same_n = a.get("trades") == b.get("trades")
    same_pf = a.get("profit_factor") == b.get("profit_factor")
    return same_n and same_pf


def wf_stats(tf, strat, sl, tp, be, htf, trail_width):
    vals = []
    for w in range(N_WINDOWS):
        br = (w / N_WINDOWS, (w + 1) / N_WINDOWS)
        r = call(tf, strat, br, sl, tp, be, htf, trail_width)
        vals.append(r.get("profit_factor") or 0.0)
    mean = statistics.mean(vals)
    std = statistics.pstdev(vals)
    return vals, round(mean, 3), round(std, 3), round(mean - std, 3)


def optimize_strategy(strat, profiles, tfs, trailks):
    cfg = live_config(strat, profiles, tfs, trailks)
    tf = cfg["tf"]
    base_oos = call(tf, strat, OOS_RANGE, cfg["sl"], cfg["tp"], cfg["be"], cfg["htf"], cfg["overlay_width"])
    base_is = call(tf, strat, IS_RANGE, cfg["sl"], cfg["tp"], cfg["be"], cfg["htf"], cfg["overlay_width"])
    base_pf = base_oos.get("profit_factor") or 0.0
    base_n = base_oos.get("trades", 0)
    is_n = base_is.get("trades", 0)

    result = {
        "strategy": strat, "tf": tf, "has_profile": cfg["has_profile"],
        "live_config": {k: cfg[k] for k in ("sl", "tp", "htf", "be", "overlay_width")},
        "baseline_oos": {"pf": base_pf, "n": base_n, "dd": base_oos.get("max_dd_pct"),
                          "wr": base_oos.get("win_rate")},
    }

    if is_n < 15:
        result["status"] = "troppo_sottile"
        return result

    inert = probe_sltp_inert(cfg, strat)
    if inert is None:
        result["status"] = "nessun_trade_is"
        return result

    min_is_trades = max(15, int(is_n * 0.4)) if is_n < 100 else 50
    min_is_pf = 1.10

    # 12/08 - griglia ridotta dopo il collaudo tempi: CRT (30m, inert, 18 combo)
    # 7m38s; FVG_CONT (4h, 156 combo) 8m57s; SCALP_RSI_SNAP (15m, 156 combo)
    # 50m6s - una griglia da 162 combo su 58 strategie (parecchie 15m/30m ad
    # alta frequenza) avrebbe richiesto 12-15+ ore. Dimezzata su ogni asse
    # (estremi strutturali, non i valori medi) per restare in ordine di
    # qualche ora: ~32 combo max (non inert), ~8 (inert) invece di 162/18.
    sl_grid = [1.0, 2.0] if not inert else [cfg["sl"]]
    tp_grid = [3.0, 6.0] if not inert else [cfg["tp"]]
    be_grid = [0.0, 1.5]
    htf_grid = [True, False]
    trail_grid = [1.5, 3.0]   # larghezza overlay, mai 0 - vedi nota su call()

    candidates = []
    tested = 0
    for htf, sl, tp, be, trail in itertools.product(htf_grid, sl_grid, tp_grid, be_grid, trail_grid):
        if not inert and be > 0 and be >= (tp / sl):
            continue
        tested += 1
        is_r = call(tf, strat, IS_RANGE, sl, tp, be, htf, trail)
        pf_is = is_r.get("profit_factor") or 0.0
        if pf_is <= min_is_pf or is_r.get("trades", 0) < min_is_trades:
            continue
        oos_r = call(tf, strat, OOS_RANGE, sl, tp, be, htf, trail)
        pf_oos = oos_r.get("profit_factor") or 0.0
        if pf_oos > base_pf:
            candidates.append({
                "sl": sl, "tp": tp, "be": be, "htf": htf, "trail": trail, "oos_pf": pf_oos,
                "oos_n": oos_r.get("trades"), "oos_dd": oos_r.get("max_dd_pct"),
                "is_pf": pf_is, "is_n": is_r.get("trades"),
            })

    result["combos_tested"] = tested
    result["inert_sltp"] = bool(inert)
    result["candidates_beating_baseline"] = len(candidates)

    if not candidates:
        result["status"] = "nessun_miglioramento"
        return result

    for c in candidates:
        vals, mean, std, robust = wf_stats(tf, strat, c["sl"], c["tp"], c["be"], c["htf"], c["trail"])
        c["wf"] = [round(v, 2) for v in vals]
        c["wf_mean"] = mean
        c["robustness"] = robust
        c["calmar"] = round(mean / c["oos_dd"], 4) if c["oos_dd"] else None

    candidates.sort(key=lambda c: c["robustness"], reverse=True)
    best = candidates[0]
    base_wf_vals, base_wf_mean, _, base_robust = wf_stats(
        tf, strat, cfg["sl"], cfg["tp"], cfg["be"], cfg["htf"], cfg["overlay_width"])
    result["baseline_wf"] = [round(v, 2) for v in base_wf_vals]
    result["baseline_robustness"] = base_robust
    result["best"] = best
    result["top3"] = candidates[:3]
    result["status"] = "migliorato"
    return result


def load_results():
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH) as f:
            return json.load(f)
    return {}


def save_results(results):
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(results, f, indent=1)
    os.replace(tmp, OUT_PATH)


def main():
    profiles, tfs, trailks = parse_mql5_profiles()
    print(f"Profili MQL5 parsati: {len(profiles)} con slMult/tpMult/htf/be/trailATR, "
          f"{len(tfs)} con TF dedicato, {len(trailks)} con TrailK overlay dedicato.", flush=True)

    strategies = sorted(bt.STRATEGIES.keys())
    results = load_results()
    print(f"{len(strategies)} strategie totali, {len(results)} gia' completate.", flush=True)

    for i, strat in enumerate(strategies):
        if strat in results:
            continue
        t0 = time.time()
        try:
            r = optimize_strategy(strat, profiles, tfs, trailks)
        except Exception as e:
            r = {"strategy": strat, "status": "errore", "error": str(e)}
        dt = time.time() - t0
        results[strat] = r
        save_results(results)
        status = r.get("status")
        extra = ""
        if status == "migliorato":
            b = r["best"]
            extra = (f" -> best sl={b['sl']} tp={b['tp']} be={b['be']} htf={b['htf']} "
                     f"OOS pf={r['baseline_oos']['pf']}->{b['oos_pf']} "
                     f"dd={r['baseline_oos']['dd']}->{b['oos_dd']}%")
        print(f"[{i+1}/{len(strategies)}] {strat} ({dt:.0f}s): {status}{extra}", flush=True)

    print("\nFATTO. Riepilogo:", flush=True)
    by_status = {}
    for r in results.values():
        by_status.setdefault(r.get("status"), []).append(r["strategy"])
    for status, names in by_status.items():
        print(f"  {status}: {len(names)} -> {names}", flush=True)


if __name__ == "__main__":
    main()
