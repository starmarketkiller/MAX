#!/usr/bin/env python3
"""
Applica meccanicamente la disciplina NQROS v3.1 usata a mano su AMD_CONT e
SILVER_BULLET a tutte le strategie sopravvissute alla Fase 1
(multi_tf_baseline.py): baseline -> toggle uno alla volta (htf_filter,
confirm_bars) -> SL/TP/breakeven/trailing uno alla volta -> combinazione
dichiarata dei singoli vincitori -> ri-validazione Out-of-Sample (60/40).

Non sostituisce un deep-dive completo (Fase 0/2/9/10 restano manuali, qui
c'e' solo la parte meccanizzabile: 1/3/5/6/8-lite/4). Ogni strategia
ottiene un verdetto: PASS (il gate OOS regge), MARGINALE (regge ma con
degrado vistoso o campione sotto soglia), FAIL (crolla fuori campione o
baseline gia' negativa).

Esegui dalla root del repo: python3 server/research_scripts/find_all_configs.py
"""
import sys
import time
sys.path.insert(0, "server")
import backtest as bt

MIN_TRADES = 15
COSTS = bt.COST_PRESETS["retail_standard"]
STRESS = bt.COST_PRESETS["stress"]

# 04/08 (11) - lista ricostruita da zero dopo il giro di fedelta' completo
# della sessione (tutte le 39 strategie testate su 6 TF con parametri di
# default, vedi BATCH_CONFIG_SEARCH_04-08.md aggiornamento 10): ogni
# strategia con almeno un TF sopra soglia campione (25 trade), al suo
# MIGLIOR TF per numero di trade/PF. La lista precedente (16/07) era
# basata su proxy in gran parte gia' superati (IFVG/OB_MIT/ORDER_BLOCK/
# PO3/BJORGUM/TURTLE_SOUP fra gli altri sono stati riscritti da allora) -
# ricalcolata, non solo aggiornata a mano. AMD_CONT, SILVER_BULLET,
# TURTLE_SOUP restano escluse: hanno gia' un deep-dive manuale completo
# (Fase 0-10) piu' approfondito di quanto questo script automatizzi.
CANDIDATES = {
    "ADX_RSI": "1d", "BJORGUM": "1h", "BOLLINGER": "1h",
    "BREAKOUT_ACC": "1wk", "EMA_PULLBACK": "1d", "FVG_CONT": "1wk",
    "FVG_MIT": "30m", "ICHIMOKU": "30m", "LIQ_SWEEP": "1d",
    "LIQ_VOID": "1wk", "LONDON_BO": "1h", "MACD": "1wk",
    "MALAYSIAN_SNR": "4h", "OTE_CONT": "1d", "RANGE_FADE": "1h",
    "RSI_DIV": "4h", "SAR": "1wk", "SCALP_BB_FADE": "4h",
    "SCALP_EMA": "4h", "SCALP_RANGE_BRK": "1wk", "SCALP_RSI_SNAP": "1h",
    "SH_BMS_RTO": "1d", "STRUCT_REACT": "4h", "TSI": "1h",
}


MIN_BASELINE_TRADES = 25   # cosi' i due tagli OOS hanno >=10 trade ciascuno
MIN_OOS_TRADES = 10        # per lato (in-sample e out-of-sample)
MAX_DECLARED_PARAMS = 2    # come fatto a mano su AMD_CONT/SILVER_BULLET: al
                            # massimo un toggle + UN parametro di gestione,
                            # mai impilare 4-5 cose insieme senza controllo


def process(strategy, tf):
    common = dict(symbol="XAUUSD", strategy=strategy, timeframe=tf, **COSTS)
    baseline = bt.run_backtest(**common, atr_sl=1.5, atr_tp=3.0)
    if baseline["profit_factor"] is None or baseline["trades"] < MIN_BASELINE_TRADES:
        return {"strategy": strategy, "tf": tf, "verdict": "SKIP",
                "reason": f"baseline sotto {MIN_BASELINE_TRADES} trade ({baseline['trades']})"}
    base_pf = baseline["profit_factor"]

    declared = {}  # parametro -> valore vincente (tipi primitivi, non dict)

    # Fase 3: toggle uno alla volta (al massimo UNO entra nella combinazione)
    toggle_wins = []
    for name, kw in [("htf_filter", {"htf_filter": True}), ("confirm_bars", {"confirm_bars": 1})]:
        r = bt.run_backtest(**common, atr_sl=1.5, atr_tp=3.0, **kw)
        if r["profit_factor"] is not None and r["trades"] >= MIN_BASELINE_TRADES and r["profit_factor"] > base_pf:
            toggle_wins.append((name, kw, r["profit_factor"]))
    if toggle_wins:
        toggle_wins.sort(key=lambda x: x[2], reverse=True)
        best_name, best_kw, _ = toggle_wins[0]
        declared[best_name] = best_kw[best_name]

    base_kw = dict(common)
    if "htf_filter" in declared:
        base_kw["htf_filter"] = True
    if "confirm_bars" in declared:
        base_kw["confirm_bars"] = declared["confirm_bars"]

    # Fase 6: SL/TP/breakeven/trailing uno alla volta - candidati raccolti,
    # ma solo il SINGOLO migliore (per PF, a campione sufficiente) entra
    # nella combinazione finale, non tutti insieme.
    mgmt_candidates = []
    for v in (1.0, 2.0, 2.5, 3.0):
        r = bt.run_backtest(**base_kw, atr_sl=v, atr_tp=3.0)
        if r["profit_factor"] and r["trades"] >= MIN_BASELINE_TRADES and r["profit_factor"] > base_pf:
            mgmt_candidates.append(("atr_sl", v, r["profit_factor"]))
    for v in (2.0, 4.0, 5.0):
        r = bt.run_backtest(**base_kw, atr_sl=1.5, atr_tp=v)
        if r["profit_factor"] and r["trades"] >= MIN_BASELINE_TRADES and r["profit_factor"] > base_pf:
            mgmt_candidates.append(("atr_tp", v, r["profit_factor"]))
    for v in (1.0, 1.5, 2.0):
        r = bt.run_backtest(**base_kw, atr_sl=1.5, atr_tp=3.0, breakeven_r=v)
        if r["profit_factor"] and r["trades"] >= MIN_BASELINE_TRADES and r["profit_factor"] > base_pf:
            mgmt_candidates.append(("breakeven_r", v, r["profit_factor"]))
    # 04/08 (12) - piramidazione sul profitto (richiesta esplicita
    # dell'utente): stessa disciplina delle altre leve, provata da sola,
    # entra nella combinazione SOLO se batte la baseline a campione
    # sufficiente - se per una strategia il TP e' troppo vicino perche' il
    # prezzo raggiunga mai il primo livello di piramide, semplicemente non
    # cambia nulla rispetto alla baseline e non viene scelta, senza
    # bisogno di escluderla a mano.
    for v in (1, 2):
        r = bt.run_backtest(**base_kw, atr_sl=1.5, atr_tp=3.0,
                             pyramid_max_legs=v, pyramid_r=1.0, pyramid_risk_mult=1.0)
        if r["profit_factor"] and r["trades"] >= MIN_BASELINE_TRADES and r["profit_factor"] > base_pf:
            mgmt_candidates.append(("pyramid_max_legs", v, r["profit_factor"]))
    for v in (2.0, 2.5):
        r = bt.run_backtest(**base_kw, atr_sl=1.5, atr_tp=3.0, trailing_atr=v)
        if r["profit_factor"] and r["trades"] >= MIN_BASELINE_TRADES and r["profit_factor"] > base_pf:
            mgmt_candidates.append(("trailing_atr", v, r["profit_factor"]))
    # 04/08 (19) - flip (richiesta esplicita: "correggiamo tutto quello
    # che abbiamo trovato"): risultato onesto sul campione pilota - aiuta
    # le strategie da inversione (TURTLE_SOUP/LIQ_SWEEP), danneggia
    # quelle da trend (TSI/ADX_RSI/SCALP_EMA) - stessa disciplina delle
    # altre leve, entra SOLO se batte la baseline, non attivato a priori.
    r = bt.run_backtest(**base_kw, atr_sl=1.5, atr_tp=3.0, allow_flip=True)
    if r["profit_factor"] and r["trades"] >= MIN_BASELINE_TRADES and r["profit_factor"] > base_pf:
        mgmt_candidates.append(("allow_flip", True, r["profit_factor"]))

    if mgmt_candidates:
        mgmt_candidates.sort(key=lambda x: x[2], reverse=True)
        pname, pval, _ = mgmt_candidates[0]
        declared[pname] = pval

    if len(declared) > MAX_DECLARED_PARAMS:
        # non dovrebbe succedere (max 1 toggle + 1 mgmt = 2), ma per sicurezza
        declared = dict(list(declared.items())[:MAX_DECLARED_PARAMS])

    if not declared:
        return {"strategy": strategy, "tf": tf, "baseline_pf": base_pf, "verdict": "FAIL",
                "reason": "nessun parametro batte la baseline con campione sufficiente", "declared": {}}

    final_kw = dict(common)
    final_kw.update(declared)
    if "atr_sl" not in final_kw:
        final_kw["atr_sl"] = 1.5
    if "atr_tp" not in final_kw:
        final_kw["atr_tp"] = 3.0

    combo = bt.run_backtest(**final_kw)
    if combo["profit_factor"] is None or combo["trades"] < MIN_BASELINE_TRADES:
        return {"strategy": strategy, "tf": tf, "baseline_pf": base_pf, "verdict": "FAIL",
                "reason": "combinazione sotto soglia trade", "declared": declared}

    # Fase 4: ri-validazione OOS della combinazione (stesso rigore, sempre)
    oos_kw = {k: v for k, v in final_kw.items() if k not in ("spread_price", "commission_r", "slippage_price")}
    is_r = bt.run_backtest(**oos_kw, bar_range=(0.0, 0.6), **COSTS)
    oos_r = bt.run_backtest(**oos_kw, bar_range=(0.6, 1.0), **COSTS)
    oos_stress = bt.run_backtest(**oos_kw, bar_range=(0.6, 1.0), **STRESS)

    verdict, reason = "FAIL", ""
    if oos_r["profit_factor"] is None or oos_r["trades"] < MIN_OOS_TRADES or is_r["trades"] < MIN_OOS_TRADES:
        reason = f"campione OOS troppo piccolo (in={is_r['trades']}, out={oos_r['trades']}, soglia={MIN_OOS_TRADES})"
        verdict = "MARGINALE"
    elif oos_r["profit_factor"] < 1.0:
        reason = "PF crolla sotto 1.0 fuori campione"
        verdict = "FAIL"
    elif oos_r["profit_factor"] > 3.0:
        reason = "PF OOS sopra 3.0 - troppo bello per fidarsi senza revisione manuale, anche a campione sufficiente"
        verdict = "MARGINALE"
    elif is_r["profit_factor"] and oos_r["profit_factor"] < is_r["profit_factor"] * 0.6:
        reason = "degrado OOS >40% relativo, sospetto overfitting"
        verdict = "MARGINALE"
    else:
        reason = "regge OOS"
        verdict = "PASS"

    return {
        "strategy": strategy, "tf": tf, "baseline_pf": base_pf, "combo_pf": combo["profit_factor"],
        "combo_trades": combo["trades"], "declared": declared,
        "is_pf": is_r["profit_factor"], "is_trades": is_r["trades"],
        "oos_pf": oos_r["profit_factor"], "oos_trades": oos_r["trades"],
        "oos_stress_pf": oos_stress["profit_factor"],
        "verdict": verdict, "reason": reason,
    }


def main():
    t0 = time.time()
    results = []
    for i, (strat, tf) in enumerate(sorted(CANDIDATES.items()), 1):
        try:
            res = process(strat, tf)
        except Exception as e:
            res = {"strategy": strat, "tf": tf, "verdict": "ERRORE", "reason": str(e)[:100]}
        results.append(res)
        print(f"[{i}/{len(CANDIDATES)}] {strat} -> {res['verdict']} ({time.time()-t0:.1f}s)", flush=True)

    order = {"PASS": 0, "MARGINALE": 1, "FAIL": 2, "SKIP": 3, "ERRORE": 4}
    results.sort(key=lambda r: (order.get(r["verdict"], 9), -(r.get("combo_pf") or 0)))

    print("\n" + "=" * 130)
    for r in results:
        print(f"\n{r['strategy']} ({r['tf']}) - {r['verdict']}: {r.get('reason','')}")
        if "baseline_pf" in r:
            print(f"  Baseline PF {r['baseline_pf']}")
        if "combo_pf" in r:
            decl = ", ".join(f"{k}={v}" for k, v in r.get('declared', {}).items()) or "(nessuna, baseline vince)"
            print(f"  Config dichiarata: {decl}")
            print(f"  Combo: PF {r['combo_pf']} / {r['combo_trades']} trade")
            print(f"  OOS: in-sample PF {r['is_pf']} ({r['is_trades']}tr) -> out-of-sample PF {r['oos_pf']} "
                  f"({r['oos_trades']}tr), stress PF {r['oos_stress_pf']}")
    print("=" * 130)
    print(f"Tempo totale: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
