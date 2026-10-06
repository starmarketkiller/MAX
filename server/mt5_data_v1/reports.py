"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - report per-account (sez.24) e
executive summary multi-account per Jarvis (sez.25). Puro assemblaggio di
dati gia' calcolati da analytics.py - nessuna nuova metrica qui dentro."""
from __future__ import annotations

from typing import List, Optional

from . import analytics, canonical


def build_account_performance_summary(account_id: str, episodes: List[dict], *,
                                       data_quality: Optional[dict] = None) -> dict:
    account_metrics = analytics.compute_account_metrics(episodes)
    strategy_metrics = analytics.compute_strategy_metrics(episodes)
    return {
        "schema": "ACCOUNT_PERFORMANCE_SUMMARY_V1",
        "account_id": account_id,
        "generated_at": canonical.utc_now_iso(),
        "account_metrics": account_metrics,
        "strategy_metrics": strategy_metrics,
        "data_quality": data_quality or {"status": "NOT_VERIFIED"},
    }


def build_multi_account_executive_summary(per_account_summaries: List[dict], *,
                                          comparison: Optional[dict] = None) -> dict:
    """per_account_summaries: output di build_account_performance_summary() per
    ogni account noto. `comparison` (opzionale): output di
    analytics.compare_accounts() - solo se i dati per normalizzare (balance/
    currency) erano disponibili, altrimenti None e lo riporta esplicitamente."""
    flagged = [s["account_id"] for s in per_account_summaries
              if s.get("data_quality", {}).get("status") == "FAILED"]
    return {
        "schema": "MT5_MULTI_ACCOUNT_EXECUTIVE_SUMMARY_V1",
        "generated_at": canonical.utc_now_iso(),
        "accounts_summarized": len(per_account_summaries),
        "accounts_with_failed_data_quality": flagged,
        "per_account": per_account_summaries,
        "cross_account_comparison": comparison,
        "cross_account_comparison_available": comparison is not None,
    }
