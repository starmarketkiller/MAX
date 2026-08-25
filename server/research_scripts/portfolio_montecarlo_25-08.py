#!/usr/bin/env python3
"""25/08 - Monte Carlo a blocchi trimestrali del portafoglio diversificato
(14 strategie, vedi portfolio_tail_risk_bootstrap_25-08.py) per un fan
chart dell'equity nel tempo, non solo la distribuzione del DD massimo.
Stessa metodologia: blocchi da ~90 giorni ricampionati con reinserimento
(preserva il raggruppamento temporale interno a ciascun blocco, rompe solo
l'ORDINE dei blocchi fra loro), cosi' un regime laterale/una crisi di
correlazione restano intatti come episodio, non spalmati via.

Ogni path ricampionato ha un numero diverso di trade effettivamente presi
(dipende da come si sovrappongono nel tempo dopo il rimescolamento) - per
un fan chart comparabile, l'equity di ogni path viene interpolata su una
griglia comune 0-100% della sequenza di trade, poi si calcolano i
percentili (5/25/50/75/95) a ogni punto della griglia sui 400 path.

Esporta un JSON con: griglia percentili equity, distribuzione DD max,
distribuzione equity finale, il path storico reale (ordine non
ricampionato) come riferimento.
"""
import sys, os, random, statistics, datetime as dt, json
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
N_RESAMPLES = 400
MAX_CONCURRENT = 3
GRID_POINTS = 101


def parse(d):
    return dt.datetime.strptime(d.split(" ")[0], "%Y-%m-%d")


def sim_equity_path(trade_list):
    equity = pd_.START_EQUITY
    peak = pd_.START_EQUITY
    max_dd = 0.0
    open_positions = []
    path = [equity]
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
        path.append(equity)
    return path, max_dd, equity


def resample_to_grid(path, grid_points):
    n = len(path)
    if n < 2:
        return [path[0]] * grid_points if path else [pd_.START_EQUITY] * grid_points
    out = []
    for g in range(grid_points):
        pos = g / (grid_points - 1) * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        out.append(path[lo] * (1 - frac) + path[hi] * frac)
    return out


def percentile(sorted_vals, pct):
    n = len(sorted_vals)
    idx = min(n - 1, max(0, int(round(pct / 100.0 * (n - 1)))))
    return sorted_vals[idx]


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
    print(f"n blocchi trimestrali: {len(blocks)}  (~{total_days/365.25:.1f} anni di storico)", flush=True)

    hist_path, hist_dd, hist_final = sim_equity_path(trades)
    print(f"Path storico reale: equity finale=EUR{hist_final:.0f}  DD_max={hist_dd:.1f}%  n_trade_presi={len(hist_path)-1}", flush=True)

    random.seed(42)
    grids = []
    dds = []
    finals = []
    for _ in range(N_RESAMPLES):
        sample_blocks = [random.choice(blocks) for _ in range(len(blocks))]
        resampled = [t for b in sample_blocks for t in b]
        path, dd, final = sim_equity_path(resampled)
        grids.append(resample_to_grid(path, GRID_POINTS))
        dds.append(dd)
        finals.append(final)

    dds.sort()
    finals.sort()

    pct_bands = {}
    for pct in (5, 25, 50, 75, 95):
        pct_bands[pct] = [percentile(sorted(col), pct) for col in zip(*grids)]

    n_ruin = sum(1 for f in finals if f <= pd_.START_EQUITY * 0.20)
    n_loss = sum(1 for f in finals if f < pd_.START_EQUITY)

    out = {
        "start_equity": pd_.START_EQUITY,
        "risk_eur": pd_.RISK_EUR,
        "max_concurrent": MAX_CONCURRENT,
        "n_resamples": N_RESAMPLES,
        "n_trades_total": len(trades),
        "years_history": round(total_days / 365.25, 1),
        "strategies": sorted(extended_set),
        "hist_path_grid": resample_to_grid(hist_path, GRID_POINTS),
        "hist_dd": round(hist_dd, 1),
        "hist_final": round(hist_final, 0),
        "pct_bands": pct_bands,
        "dd_sorted": [round(d, 1) for d in dds],
        "final_sorted": [round(f, 0) for f in finals],
        "dd_median": round(statistics.median(dds), 1),
        "dd_p90": round(percentile(dds, 90), 1),
        "dd_p95": round(percentile(dds, 95), 1),
        "dd_p99": round(percentile(dds, 99), 1),
        "dd_worst": round(dds[-1], 1),
        "final_median": round(statistics.median(finals), 0),
        "final_p5": round(percentile(finals, 5), 0),
        "final_p95": round(percentile(finals, 95), 0),
        "n_ruin_pct": round(100.0 * n_ruin / N_RESAMPLES, 1),
        "n_loss_pct": round(100.0 * n_loss / N_RESAMPLES, 1),
    }
    with open(os.path.join(HERE, "portfolio_montecarlo_25-08.json"), "w") as f:
        json.dump(out, f)
    print(json.dumps({k: v for k, v in out.items() if k not in ("dd_sorted", "final_sorted", "pct_bands", "hist_path_grid")}, indent=2), flush=True)


if __name__ == "__main__":
    main()
