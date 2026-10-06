"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - analytics account-level e
strategy-level-within-account (sez.11/12), e comparazione cross-account
normalizzata (sez.13: mai confrontare PnL grezzo fra conti con balance/
leverage/currency diversi).

Tutte le metriche operano solo su trade_episode con status in
(CLOSED, PARTIALLY_CLOSED) e realized_pnl non nullo - un episodio OPEN non
ha ancora un risultato, non viene mai forzato a 0.
"""
from __future__ import annotations

from typing import List, Optional


def _closed_with_pnl(episodes: List[dict]) -> List[dict]:
    return [e for e in episodes if e.get("status") in ("CLOSED", "PARTIALLY_CLOSED")
           and e.get("realized_pnl") is not None]


def compute_account_metrics(episodes: List[dict]) -> dict:
    closed = _closed_with_pnl(episodes)
    n = len(closed)
    if n == 0:
        return {
            "total_trades": 0, "win_rate": None, "profit_factor": None,
            "expectancy": None, "total_realized_pnl": 0.0, "max_drawdown": None,
            "note": "nessun trade episode chiuso con realized_pnl disponibile",
        }

    pnls = [e["realized_pnl"] for e in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total_pnl = sum(pnls)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    # Equity curve proxy: cumulativa dei realized_pnl ordinati per close_time.
    # Non e' la vera equity del conto (manca balance iniziale/deposit/withdraw
    # fuori dai trade) - usata solo come proxy di drawdown sui trade.
    ordered = sorted(closed, key=lambda e: e.get("close_time") or "")
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for e in ordered:
        cum += e["realized_pnl"]
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)

    return {
        "total_trades": n,
        "win_rate": len(wins) / n,
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else None,
        "expectancy": total_pnl / n,
        "total_realized_pnl": total_pnl,
        "max_drawdown": max_dd,
        "max_drawdown_basis": "CUMULATIVE_REALIZED_PNL_PROXY_NOT_ACCOUNT_EQUITY",
    }


def compute_strategy_metrics(episodes: List[dict]) -> dict:
    """Raggruppa per strategy_attribution.strategy_name. Gli episodi con
    status UNKNOWN finiscono in un bucket separato esplicito, mai mescolati
    con una strategia reale (sez.9: mai inferire silenziosamente)."""
    groups: dict = {}
    for e in episodes:
        attr = e.get("strategy_attribution", {})
        status = attr.get("status", "UNKNOWN")
        key = attr.get("strategy_name") if status != "UNKNOWN" and attr.get("strategy_name") else "__UNKNOWN__"
        groups.setdefault(key, []).append(e)

    return {name: {**compute_account_metrics(eps), "attribution_status_sample": eps[0].get(
        "strategy_attribution", {}).get("status") if eps else None}
           for name, eps in groups.items()}


def normalize_for_comparison(account_metrics: dict, starting_balance: Optional[float],
                             currency: Optional[str]) -> dict:
    """PnL in percentuale sul balance iniziale - mai il PnL grezzo, perche'
    due conti con balance diversi non sono comparabili altrimenti (sez.13).
    Se starting_balance e' assente/zero o la currency non e' nota, il
    confronto e' dichiarato NOT_COMPARABLE invece di produrre un numero
    silenziosamente scorretto."""
    total_pnl = account_metrics.get("total_realized_pnl")
    if not starting_balance or starting_balance <= 0 or not currency or total_pnl is None:
        return {"comparable": False, "reason": "starting_balance o currency non disponibili", "pnl_pct": None}
    return {"comparable": True, "currency": currency, "pnl_pct": total_pnl / starting_balance}


def compare_accounts(entries: List[dict]) -> dict:
    """entries: [{"account_id":..., "metrics":..., "starting_balance":..., "currency":...}, ...]
    Ritorna il confronto normalizzato - gli account non comparabili restano
    visibili con comparable=False, non vengono scartati silenziosamente."""
    results = []
    currencies = set()
    for entry in entries:
        norm = normalize_for_comparison(entry["metrics"], entry.get("starting_balance"), entry.get("currency"))
        if norm["comparable"]:
            currencies.add(norm["currency"])
        results.append({"account_id": entry["account_id"], **norm})

    mixed_currency_warning = len(currencies) > 1
    return {"accounts": results, "mixed_currency_warning": mixed_currency_warning,
           "currencies_seen": sorted(currencies)}
