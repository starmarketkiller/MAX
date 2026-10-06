"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - layer di normalizzazione.

raw (file originale, mai modificato) -> parser (csv_formats.py) -> canonico
(Deal / Trade Episode, contracts/mt5-trade-history-v1.schema.json) -> verifier
(verifier.py, chiamato dal chiamante dopo la normalizzazione, non qui dentro -
normalize.py produce dati, non giudica la loro qualita').

Ogni record canonico porta `provenance` con l'hash del file raw e l'indice di
riga esatto - sempre possibile tornare alla fonte (sez.6/9 della richiesta).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import canonical, csv_formats, trade_episodes
from .identity import is_valid_account_id

PARSER_VERSION = "1.0.0"


def _require_account_id(account_id: str) -> None:
    if not is_valid_account_id(account_id):
        raise ValueError(f"account_id non valido: {account_id!r} (atteso formato acct_<16 hex>)")


def _provenance_base(path: str | Path, parser_name: str) -> dict:
    return {
        "raw_source_path": str(path).replace("\\", "/"),
        "raw_source_sha256": canonical.file_sha256(path),
        "parser_name": parser_name,
        "parser_version": PARSER_VERSION,
        "normalized_at": canonical.utc_now_iso(),
    }


def _deal_type_to_side_hint(deal_type: str) -> Optional[str]:
    if deal_type == "DEAL_TYPE_BUY":
        return "BUY"
    if deal_type == "DEAL_TYPE_SELL":
        return "SELL"
    return None


def _to_canonical_deal(raw: dict, account_id: str, prov_base: dict) -> dict:
    return {
        "deal_ticket": raw["deal_ticket"],
        "position_id": raw["position_id"],
        "order_ticket": raw["order_ticket"],
        "account_id": account_id,
        "time": raw["time"],
        "time_msc": raw["time_msc"],
        "symbol": raw["symbol"],
        "magic": raw["magic"],
        "type": raw["type"] if raw["type"] else "UNKNOWN",
        "entry": raw["entry"],
        "price": raw["price"],
        "volume": raw["volume"],
        "sl": raw["sl"],
        "tp": raw["tp"],
        "profit": raw["profit"],
        "swap": raw["swap"],
        "commission": raw["commission"],
        "comment": raw["comment"],
        "reason": raw["reason"] if raw["reason"] else "UNKNOWN",
        "strategy_attribution": {"status": "UNKNOWN"},
        "provenance": {**prov_base, "raw_source_row_index": raw["row_index"]},
    }


def normalize_native_deal_export(path: str | Path, account_id: str) -> dict:
    """Formato preferito quando disponibile: position_id reale."""
    _require_account_id(account_id)
    prov_base = _provenance_base(path, "normalize.normalize_native_deal_export")
    raw_rows = csv_formats.parse_native_deal_export(path)
    deals = [_to_canonical_deal(r, account_id, prov_base) for r in raw_rows]
    episodes = trade_episodes.from_native_deals(raw_rows, account_id, prov_base)
    return {"source_format": "NATIVE_DEAL_EXPORT", "deals": deals, "trade_episodes": episodes,
            "provenance": prov_base}


def normalize_ea_trade_log(path: str | Path, account_id: str, symbol: Optional[str] = None) -> dict:
    """Nessun position_id reale in questo formato (vedi csv_formats.py) -
    produce solo trade_episode, con pairing euristico dichiarato nel
    provenance di ciascun episodio. `symbol` va fornito dal chiamante."""
    _require_account_id(account_id)
    prov_base = _provenance_base(path, "normalize.normalize_ea_trade_log")
    raw_rows = csv_formats.parse_ea_trade_log(path)
    episodes = trade_episodes.from_ea_trade_log(raw_rows, account_id, symbol, prov_base)
    return {"source_format": "EA_TRADE_LOG", "deals": [], "trade_episodes": episodes,
            "provenance": prov_base}


def normalize_auto(path: str | Path, account_id: str, symbol: Optional[str] = None) -> dict:
    """Rileva il formato dall'header e chiama il normalizzatore giusto.
    UNKNOWN -> ValueError esplicito, mai un tentativo silenzioso con il
    parser sbagliato."""
    fmt = csv_formats.detect_format_from_file(path)
    if fmt == csv_formats.CsvFormat.NATIVE_DEAL_EXPORT:
        return normalize_native_deal_export(path, account_id)
    if fmt == csv_formats.CsvFormat.EA_TRADE_LOG:
        return normalize_ea_trade_log(path, account_id, symbol)
    raise ValueError(f"{path}: formato CSV non riconosciuto (ne' EA_TRADE_LOG ne' NATIVE_DEAL_EXPORT)")
