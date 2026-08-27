#!/usr/bin/env python3
"""25/08 - Monte Carlo a blocchi trimestrali della composizione REALE di
NEXUS v3.0 (12 strategie live-verificate stanotte con la ricetta esatta,
vedi nexus_v3_portfolio_trades_25-08.py), non piu' il set di ricerca
Python di ieri sera (che includeva ancora TURTLE_SOUP/LDN_REVERSAL nella
forma Python, oggi disattivate nel motore vero).

Stessa identica metodologia di portfolio_montecarlo_25-08.py (blocchi da
~90 giorni ricampionati con reinserimento, fan chart su griglia 0-100%
della sequenza di trade, percentili 5/25/50/75/95 su 400 path) - qui solo
la fonte dei trade cambia.

Avvertenza dichiarata: RSI_DIV nel dataset sotto mostra PF0.50 (n=2735),
in netto contrasto con la nota "reale PF1.21, 98 trade" gia' presente nel
codice - la funzione Python bt.STRATEGIES['RSI_DIV'] usata qui non e'
stata riverificata stanotte contro il vero segnale MQL5 (fuori dallo
scope di stasera) e potrebbe non essere fedele. Portafoglio comunque
mostrato con e senza RSI_DIV per isolarne l'impatto.
"""
import sys, os, random, statistics, datetime as dt, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("pd_", os.path.join(HERE, "portfolio_diversified_25-08.py"))
pd_ = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pd_)

BLOCK_DAYS = 90
N_RESAMPLES = 400
MAX_CONCURRENT = 4       # InpMaxConcurrent live attuale (era 3, valore di un vecchio confronto)
GRID_POINTS = 101
# 25/08 - SECONDA CORREZIONE: la prima versione usava un rischio PIATTO
# 1.0% per tutte le strategie. Il motore vero non fa cosi' - ogni
# strategia ha un tier di rischio proprio (NXS_Profile_Risk in
# NXS_StrategyProfiles.mqh, calibrato anche su storico MT5 reale dove
# disponibile, non solo backtest): da 0.3% (TSI) a 5.0% (SAR,
# EMA_PULLBACK). SAR in particolare e' sia ad altissima frequenza
# (n=7062/17891, 39% del volume) SIA al tier di rischio piu' alto (5%)
# SIA a edge sottilissimo (PF1.09) - la combinazione peggiore possibile
# per il drag da rischio percentuale composto. Con rischio piatto 1% lo
# stavo SOTTOSTIMANDO, non sovrastimando.
RISK_PCT_BY_STRAT = {
    # 27/08 - riallineato a NXS_Profile_Risk (NXS_StrategyProfiles.mqh) COME
    # E' ORA nel codice live: SAR e EMA_PULLBACK erano gia' stati abbassati
    # (5.0->1.0 e 5.0->2.5) in una sessione precedente proprio a causa di
    # QUESTO Monte Carlo - lo script pero' era rimasto con i valori vecchi.
    # Tutti gli altri invariati (confermati via grep sul codice).
    "ADX_RSI": 2.5, "SAR": 1.0, "MACD": 0.5, "FVG_CONT": 0.5,
    "EMA_PULLBACK": 2.5, "OTE_CONT": 0.5, "TSI": 0.3, "RSI_DIV": 1.5,
    "BOLLINGER": 0.6, "BREAKOUT_ACC": 0.5, "MALAYSIAN_SNR": 1.8,
    "STRUCT_REACT": 0.5,
}
RISK_PCT = 1.0          # fallback se una strategia non e' nella tabella sopra
MAX_LOTS_CAP = 0.10      # stesso tetto lotto del confronto di ieri sera
MAX_RISK_AT_MINLOT_PCT = 8.0   # InpMaxRiskAtMinLotPct: se il lotto minimo rischia oltre
                                 # questa % del saldo, l'ordine viene RIFIUTATO (motore vero)
MAX_AGGREGATE_RISK_PCT = 25.0  # cap di rischio aggregato reale (NXS_OpenRiskPct, 12/08):
                                 # se il rischio GIA' aperto su tutte le posizioni supera
                                 # questa % del saldo, un nuovo ingresso e' rifiutato a
                                 # prescindere dalla sua size - non modellato nella prima
                                 # versione (nessun cap aggregato, solo il conteggio di
                                 # posizioni) ed e' probabilmente il motivo principale
                                 # del crollo a DD>95%/rovina vista nel primo run.


def parse(d):
    return dt.datetime.strptime(d.split(" ")[0], "%Y-%m-%d")


def sim_equity_path(trade_list):
    """25/08 - CORRETTO rispetto alla prima versione: quella usava un
    rischio FISSO in euro (RISK_EUR=10, ereditato da portfolio_
    diversified_25-08.py, pensato per un confronto a parita' di euro-
    rischio) invece che una PERCENTUALE del saldo corrente come fa
    davvero l'EA (InpRiskPercent=1.0%). Con rischio fisso, un conto che
    si riduce non abbassa mai la posta - risultato: DD>100% e rovina
    all'89% dei path, un artefatto del simulatore, non necessariamente
    del portafoglio. Qui il rischio e' l'1% del saldo CORRENTE (scala
    verso il basso quando l'equity scende, verso l'alto quando sale,
    esattamente come il vero position sizing), e un ordine il cui lotto
    minimo rischierebbe piu' di MAX_RISK_AT_MINLOT_PCT% del saldo viene
    RIFIUTATO invece che eseguito comunque (fedele a NXS_CalcLotRisk /
    InpMaxRiskAtMinLotPct nel motore vero)."""
    equity = pd_.START_EQUITY
    peak = pd_.START_EQUITY
    max_dd = 0.0
    open_positions = []   # (close_time, risk_eur_alla_apertura)
    path = [equity]
    for t in trade_list:
        if equity <= 0:
            break
        open_positions = [p for p in open_positions if p[0] > t["open_time"]]
        if len(open_positions) >= MAX_CONCURRENT:
            continue
        risk_pct = RISK_PCT_BY_STRAT.get(t.get("strat"), RISK_PCT)
        risk_eur = equity * risk_pct / 100.0
        lots = risk_eur / (100.0 * t["risk_dist"]) if t["risk_dist"] > 0 else 0
        lots = min(round(lots * 100) / 100.0, MAX_LOTS_CAP)
        lots = max(lots, 0.01)
        actual_risk_eur = lots * 100 * t["risk_dist"]
        if lots <= 0.01 and actual_risk_eur > equity * MAX_RISK_AT_MINLOT_PCT / 100.0:
            continue   # rifiutato: lotto minimo troppo rischioso per il saldo attuale
        already_open_risk = sum(p[1] for p in open_positions)
        if already_open_risk + actual_risk_eur > equity * MAX_AGGREGATE_RISK_PCT / 100.0:
            continue   # rifiutato: rischio aggregato gia' al tetto (NXS_OpenRiskPct)
        open_positions.append((t["close_time"], actual_risk_eur))
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


def run(trades, label):
    trades = sorted(trades, key=lambda t: t["open_time"])
    start = parse(trades[0]["open_time"])
    end = parse(trades[-1]["open_time"])
    total_days = (end - start).days
    n_blocks = total_days // BLOCK_DAYS + 1
    blocks = [[] for _ in range(n_blocks)]
    for t in trades:
        idx = (parse(t["open_time"]) - start).days // BLOCK_DAYS
        blocks[idx].append(t)
    blocks = [b for b in blocks if b]

    hist_path, hist_dd, hist_final = sim_equity_path(trades)

    random.seed(42)
    grids, dds, finals = [], [], []
    for _ in range(N_RESAMPLES):
        sample_blocks = [random.choice(blocks) for _ in range(len(blocks))]
        resampled = [t for b in sample_blocks for t in b]
        path, dd, final = sim_equity_path(resampled)
        grids.append(resample_to_grid(path, GRID_POINTS))
        dds.append(dd)
        finals.append(final)
    dds.sort()
    finals.sort()
    pct_bands = {pct: [percentile(sorted(col), pct) for col in zip(*grids)] for pct in (5, 25, 50, 75, 95)}
    n_ruin = sum(1 for f in finals if f <= pd_.START_EQUITY * 0.20)
    n_loss = sum(1 for f in finals if f < pd_.START_EQUITY)

    print(f"\n=== {label} ===", flush=True)
    print(f"n trade: {len(trades)}  n blocchi: {len(blocks)} (~{total_days/365.25:.1f} anni)", flush=True)
    print(f"Storico reale: equity finale=EUR{hist_final:.0f} DD_max={hist_dd:.1f}% n_presi={len(hist_path)-1}", flush=True)
    print(f"MC: DD mediano={statistics.median(dds):.1f}% p90={percentile(dds,90):.1f}% "
          f"p95={percentile(dds,95):.1f}% peggiore={dds[-1]:.1f}%", flush=True)
    print(f"MC: equity finale mediana=EUR{statistics.median(finals):.0f} "
          f"p5=EUR{percentile(finals,5):.0f} p95=EUR{percentile(finals,95):.0f} "
          f"rovina={100.0*n_ruin/N_RESAMPLES:.1f}% perdita={100.0*n_loss/N_RESAMPLES:.1f}%", flush=True)

    return {
        "label": label, "start_equity": pd_.START_EQUITY, "risk_eur": pd_.RISK_EUR,
        "max_concurrent": MAX_CONCURRENT, "n_resamples": N_RESAMPLES,
        "n_trades_total": len(trades), "years_history": round(total_days / 365.25, 1),
        "hist_path_grid": resample_to_grid(hist_path, GRID_POINTS),
        "hist_dd": round(hist_dd, 1), "hist_final": round(hist_final, 0),
        "pct_bands": pct_bands, "dd_sorted": [round(d, 1) for d in dds],
        "final_sorted": [round(f, 0) for f in finals],
        "dd_median": round(statistics.median(dds), 1), "dd_p90": round(percentile(dds, 90), 1),
        "dd_p95": round(percentile(dds, 95), 1), "dd_p99": round(percentile(dds, 99), 1),
        "dd_worst": round(dds[-1], 1), "final_median": round(statistics.median(finals), 0),
        "final_p5": round(percentile(finals, 5), 0), "final_p95": round(percentile(finals, 95), 0),
        "n_ruin_pct": round(100.0 * n_ruin / N_RESAMPLES, 1), "n_loss_pct": round(100.0 * n_loss / N_RESAMPLES, 1),
    }


def main():
    with open(os.path.join(HERE, "nexus_v3_portfolio_trades_25-08.json")) as f:
        all_trades = json.load(f)
    strategies_all = sorted(set(t["strat"] for t in all_trades))
    print(f"Strategie nel dataset v3.0: {strategies_all}", flush=True)

    out_all = run(all_trades, "v3.0 completo (12 strategie)")
    out_all["strategies"] = strategies_all

    no_rsidiv = [t for t in all_trades if t["strat"] != "RSI_DIV"]
    out_norsi = run(no_rsidiv, "v3.0 senza RSI_DIV (non riverificata stanotte)")
    out_norsi["strategies"] = [s for s in strategies_all if s != "RSI_DIV"]

    with open(os.path.join(HERE, "portfolio_montecarlo_v3_25-08.json"), "w") as f:
        json.dump({"with_rsidiv": out_all, "without_rsidiv": out_norsi}, f)
    print("\nSalvato portfolio_montecarlo_v3_25-08.json", flush=True)


if __name__ == "__main__":
    main()
