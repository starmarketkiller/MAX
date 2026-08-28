#!/usr/bin/env python3
"""
25/08 - stress-test del rischio di coda del portafoglio diversificato
a 14 strategie (vedi portfolio_diversified_25-08.py). Il drawdown
storico (25.2%, febbraio 2022) e' un solo percorso - un solo episodio
laterale nello storico disponibile non basta per escludere qualcosa
di peggiore. Bootstrap a BLOCCHI trimestrali (non giorno-per-giorno,
per non distruggere il raggruppamento temporale di un regime laterale):
i 901 giorni di trade divisi in blocchi da ~90 giorni, ricampionati con
reinserimento 500 volte, per stimare la distribuzione di drawdown
plausibili con lo stesso materiale storico riordinato diversamente.
"""
import sys, os, random, statistics, datetime as dt
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("cu", os.path.join(HERE, "correlation_updated_25-08.py"))
cu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cu)
spec2 = importlib.util.spec_from_file_location("pd_", os.path.join(HERE, "portfolio_diversified_25-08.py"))
pd_ = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(pd_)

BLOCK_DAYS = 90
N_RESAMPLES = 500
MAX_CONCURRENT = 3


def parse(d):
    return dt.datetime.strptime(d.split(" ")[0], "%Y-%m-%d")


def sim_dd(trade_list):
    equity = pd_.START_EQUITY
    peak = pd_.START_EQUITY
    max_dd = 0.0
    open_positions = []
    for t in trade_list:
        if equity <= 0:
            break
        open_positions = [ct for ct in open_positions if ct > t["open_time"]]
        if len(open_positions) >= MAX_CONCURRENT:
            continue
        lots = pd_.RISK_EUR / (100.0 * t["risk_dist"]) if t["risk_dist"] > 0 else 0
        lots = min(round(lots * 100) / 100.0, pd_.MAX_LOTS_CAP)
        lots = max(lots, 0.01)
        actual_risk_eur = lots * 100 * t["risk_dist"]
        if actual_risk_eur > pd_.MAX_RISK_EUR_CAP:
            continue
        open_positions.append(t["close_time"])
        equity += t["net_r"] * actual_risk_eur
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * 100)
    return max_dd, equity


def main():
    all_trades = cu.collect_all()
    all_trades.sort(key=lambda t: t["open_time"])
    extended_set = pd_.DIVERSIFIED_SET | {"TSI", "LIQ_SWEEP", "SAR_FLIP", "LONDON_BO", "FVG_CONT_V2"}
    trades = [t for t in all_trades if t["strat"] in extended_set]
    print(f"n trade: {len(trades)}", flush=True)

    start = parse(trades[0]["open_time"])
    end = parse(trades[-1]["open_time"])
    total_days = (end - start).days
    n_blocks = total_days // BLOCK_DAYS + 1
    blocks = [[] for _ in range(n_blocks)]
    for t in trades:
        idx = (parse(t["open_time"]) - start).days // BLOCK_DAYS
        blocks[idx].append(t)
    blocks = [b for b in blocks if b]
    print(f"n blocchi trimestrali: {len(blocks)}, dimensione media: {sum(len(b) for b in blocks) / len(blocks):.1f}", flush=True)

    dd_hist, _ = sim_dd(trades)
    print(f"DD storico (ordine reale, non ricampionato): {dd_hist:.1f}%", flush=True)

    random.seed(42)
    dds = []
    for _ in range(N_RESAMPLES):
        sample_blocks = [random.choice(blocks) for _ in range(len(blocks))]
        resampled = [t for b in sample_blocks for t in b]
        dd, _ = sim_dd(resampled)
        dds.append(dd)
    dds.sort()

    print(f"\nDistribuzione DD su {N_RESAMPLES} ricampionamenti a blocchi trimestrali:", flush=True)
    print(f"  mediana: {statistics.median(dds):.1f}%", flush=True)
    print(f"  90-esimo percentile: {dds[int(0.9 * len(dds))]:.1f}%", flush=True)
    print(f"  95-esimo percentile: {dds[int(0.95 * len(dds))]:.1f}%", flush=True)
    print(f"  99-esimo percentile: {dds[int(0.99 * len(dds))]:.1f}%", flush=True)
    print(f"  peggiore osservato: {dds[-1]:.1f}%", flush=True)


if __name__ == "__main__":
    main()
