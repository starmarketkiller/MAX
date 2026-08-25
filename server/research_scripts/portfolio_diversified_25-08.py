#!/usr/bin/env python3
"""
25/08 - prossimo passo esplicitamente raccomandato ieri (vedi
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]): invece di
correggere il bucket condiviso (gia' provato, non risolve), scegliere
DELIBERATAMENTE un sottoinsieme a bassa correlazione reciproca invece
di tutto il catalogo, e confrontare con la simulazione a rosa intera.

Riusa collect_all() da correlation_updated_25-08.py (config vincenti
di oggi, 24 strategie) e simulate_portfolio_capped da
portfolio_regime_sim_16-08.py (stessi parametri della simulazione del
16-24/08 per un confronto diretto: conto EUR1000, rischio EUR10/trade,
tetto 0.10 lotti, max 2 posizioni concorrenti, tetto rischio EUR40).

Due portafogli confrontati:
  (a) TUTTO il catalogo (24 strategie) - baseline aggiornata
  (b) DIVERSIFICATO: le 8 migliori diversificatrici (corr. media piu'
      bassa: FVG_MIT/OTE_CONT/STRUCT_REACT/RSI_DIV/LDN_REVERSAL/
      BOLLINGER/TURTLE_SOUP/EMA_PULLBACK) + 1 sola rappresentante del
      cluster trend (ADX_RSI, la piu' solida/verificata) invece di
      tutti e 8 i membri correlati
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("cu", os.path.join(HERE, "correlation_updated_25-08.py"))
cu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cu)

RISK_EUR = 10.0
MAX_LOTS_CAP = 0.10
MAX_CONCURRENT = 2
START_EQUITY = 1000.0
MAX_RISK_EUR_CAP = 40.0


def simulate_portfolio_capped(trades, start_equity, risk_eur, max_lots_cap, max_concurrent,
                               max_risk_eur_cap=None):
    equity = start_equity
    peak = start_equity
    max_dd_pct = 0.0
    open_positions = []
    n_taken, n_skipped_bucket, n_skipped_cap = 0, 0, 0
    for t in trades:
        if equity <= 0:
            break
        open_positions = [ct for ct in open_positions if ct > t["open_time"]]
        if len(open_positions) >= max_concurrent:
            n_skipped_bucket += 1
            continue
        lots = risk_eur / (100.0 * t["risk_dist"]) if t["risk_dist"] > 0 else 0
        lots = min(round(lots * 100) / 100.0, max_lots_cap)
        lots = max(lots, 0.01)
        actual_risk_eur = lots * 100 * t["risk_dist"]
        if max_risk_eur_cap is not None and actual_risk_eur > max_risk_eur_cap:
            n_skipped_cap += 1
            continue
        open_positions.append(t["close_time"])
        pnl_eur = t["net_r"] * actual_risk_eur
        equity += pnl_eur
        peak = max(peak, equity)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (peak - equity) / peak * 100)
        n_taken += 1
    return {"final_equity": equity, "max_dd_pct": max_dd_pct, "n_taken": n_taken,
            "n_skipped_bucket": n_skipped_bucket, "n_skipped_cap": n_skipped_cap,
            "net_pnl": equity - start_equity}


DIVERSIFIED_SET = {
    "FVG_MIT", "OTE_CONT", "STRUCT_REACT", "RSI_DIV", "LDN_REVERSAL",
    "BOLLINGER", "TURTLE_SOUP", "EMA_PULLBACK", "ADX_RSI",
}


def per_strategy_breakdown(trades):
    from collections import defaultdict
    by = defaultdict(list)
    for t in trades:
        by[t["strat"]].append(t["net_r"])
    print("  --- contributo grezzo per strategia (somma R, PRIMA del bucket a 2 slot) ---")
    for s in sorted(by, key=lambda k: -sum(by[k])):
        print(f"    {s:26s} n={len(by[s]):4d} sumR={sum(by[s]):+8.1f}")


def main():
    all_trades = cu.collect_all()
    all_trades.sort(key=lambda t: t["open_time"])
    print(f"Totale trade grezzi (tutte le 24 strategie): {len(all_trades)}", flush=True)

    print("\n=== (a) PORTAFOGLIO COMPLETO (24 strategie) ===", flush=True)
    res_a = simulate_portfolio_capped(all_trades, START_EQUITY, RISK_EUR, MAX_LOTS_CAP,
                                       MAX_CONCURRENT, MAX_RISK_EUR_CAP)
    print(f"  equity finale=EUR{res_a['final_equity']:.0f} (netPnL={res_a['net_pnl']:+.0f}) "
          f"DD_max={res_a['max_dd_pct']:.1f}% trade_presi={res_a['n_taken']} "
          f"scartati_bucket={res_a['n_skipped_bucket']} scartati_cap={res_a['n_skipped_cap']}", flush=True)

    div_trades = [t for t in all_trades if t["strat"] in DIVERSIFIED_SET]
    print(f"\nTotale trade grezzi (9 strategie diversificate): {len(div_trades)}", flush=True)
    print("\n=== (b) PORTAFOGLIO DIVERSIFICATO (8 diversificatrici + 1 ADX_RSI) ===", flush=True)
    res_b = simulate_portfolio_capped(div_trades, START_EQUITY, RISK_EUR, MAX_LOTS_CAP,
                                       MAX_CONCURRENT, MAX_RISK_EUR_CAP)
    print(f"  equity finale=EUR{res_b['final_equity']:.0f} (netPnL={res_b['net_pnl']:+.0f}) "
          f"DD_max={res_b['max_dd_pct']:.1f}% trade_presi={res_b['n_taken']} "
          f"scartati_bucket={res_b['n_skipped_bucket']} scartati_cap={res_b['n_skipped_cap']}", flush=True)
    per_strategy_breakdown(div_trades)

    print("\n=== (c) PORTAFOGLIO DIVERSIFICATO, max_concurrent=3 (piu' spazio alle 9) ===", flush=True)
    res_c = simulate_portfolio_capped(div_trades, START_EQUITY, RISK_EUR, MAX_LOTS_CAP,
                                       3, MAX_RISK_EUR_CAP)
    print(f"  equity finale=EUR{res_c['final_equity']:.0f} (netPnL={res_c['net_pnl']:+.0f}) "
          f"DD_max={res_c['max_dd_pct']:.1f}% trade_presi={res_c['n_taken']} "
          f"scartati_bucket={res_c['n_skipped_bucket']} scartati_cap={res_c['n_skipped_cap']}", flush=True)


if __name__ == "__main__":
    main()
