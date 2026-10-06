"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - costruzione dei Trade Episode.

Un Trade Episode aggrega i deal di una stessa posizione (stesso position_id
MT5 reale, quando disponibile) in un'unica riga "la posizione X e' stata
apera il giorno Y e chiusa il giorno Z con risultato W". Due percorsi
distinti, perche' i due formati verificati nel census portano informazioni
diverse (vedi csv_formats.py):

- from_native_deals(): position_id REALE (da NATIVE_DEAL_EXPORT) -> episodi
  affidabili, pairing_method="POSITION_ID_EXACT".
- from_ea_trade_log(): nessun position_id reale sulle righe OPEN (sempre
  ticket=0) -> pairing EURISTICO sequenziale per strategia (FIFO: la
  prima OPEN non ancora chiusa di quella strategia si accoppia alla
  prossima CLOSE della stessa strategia). Scelta deliberata: MAI dichiarare
  questo pairing come esatto - pairing_method="SEQUENTIAL_HEURISTIC_PER_STRATEGY"
  resta sempre visibile nel provenance, e la verifier segnala (non blocca)
  se nello stesso periodo esistono piu' OPEN consecutive della stessa
  strategia senza una CLOSE intermedia (il caso in cui il FIFO potrebbe
  sbagliare l'accoppiamento).
"""
from __future__ import annotations

from collections import defaultdict
from typing import List, Optional


def _episode_base(account_id: str, position_id: int, provenance: dict) -> dict:
    return {
        "episode_id": f"{account_id}:{position_id}",
        "account_id": account_id,
        "position_id": position_id,
        "symbol": None,
        "strategy_attribution": {"status": "UNKNOWN"},
        "side": "UNKNOWN",
        "open_time": None,
        "close_time": None,
        "volume_opened": 0.0,
        "volume_closed": 0.0,
        "avg_open_price": None,
        "avg_close_price": None,
        "realized_pnl": None,
        "swap_total": 0.0,
        "commission_total": 0.0,
        "r_multiple": None,
        "status": "OPEN",
        "deal_ids": [],
        "provenance": provenance,
    }


def from_native_deals(deals: List[dict], account_id: str, provenance: dict) -> List[dict]:
    """deals: output di csv_formats.parse_native_deal_export(), con account_id
    gia' assegnato dal chiamante (il formato raw non lo contiene)."""
    by_position: dict = defaultdict(list)
    for d in deals:
        if d["type"] in ("DEAL_TYPE_BALANCE", "DEAL_TYPE_CREDIT", "DEAL_TYPE_CHARGE",
                         "DEAL_TYPE_CORRECTION", "DEAL_TYPE_BONUS") and d["position_id"] == 0:
            continue  # movimenti di conto, non di posizione - niente episodio
        by_position[d["position_id"]].append(d)

    episodes = []
    for position_id, pdeal in sorted(by_position.items()):
        pdeal.sort(key=lambda x: (x["time"], x["deal_ticket"]))
        ep = _episode_base(account_id, position_id, provenance)
        ep["symbol"] = next((x["symbol"] for x in pdeal if x["symbol"]), None)
        ep["deal_ids"] = [x["deal_ticket"] for x in pdeal]

        open_deals = [x for x in pdeal if x["entry"] == "DEAL_ENTRY_IN"]
        close_deals = [x for x in pdeal if x["entry"] in ("DEAL_ENTRY_OUT", "DEAL_ENTRY_OUT_BY")]

        if open_deals:
            ep["side"] = "BUY" if open_deals[0]["type"] == "DEAL_TYPE_BUY" else "SELL"
            ep["open_time"] = open_deals[0]["time"]
            total_vol = sum(x["volume"] for x in open_deals)
            if total_vol:
                ep["avg_open_price"] = sum(x["price"] * x["volume"] for x in open_deals) / total_vol
            ep["volume_opened"] = total_vol

        vol_closed = sum(x["volume"] for x in close_deals)
        ep["volume_closed"] = vol_closed
        if close_deals:
            ep["close_time"] = close_deals[-1]["time"]
            if vol_closed:
                ep["avg_close_price"] = sum(x["price"] * x["volume"] for x in close_deals) / vol_closed
            ep["realized_pnl"] = sum(x["profit"] or 0.0 for x in close_deals)

        ep["swap_total"] = sum((x["swap"] or 0.0) for x in pdeal)
        ep["commission_total"] = sum((x["commission"] or 0.0) for x in pdeal)

        if not close_deals:
            ep["status"] = "OPEN"
        elif ep["volume_opened"] and vol_closed < ep["volume_opened"] - 1e-9:
            ep["status"] = "PARTIALLY_CLOSED"
        else:
            ep["status"] = "CLOSED"

        ep["provenance"] = {**provenance, "pairing_method": "POSITION_ID_EXACT"}
        episodes.append(ep)
    return episodes


def from_ea_trade_log(events: List[dict], account_id: str, symbol: Optional[str], provenance: dict) -> List[dict]:
    """events: output di csv_formats.parse_ea_trade_log(). symbol va passato
    dal chiamante (il formato non lo contiene - vedi csv_formats.py)."""
    open_queue: dict = defaultdict(list)  # strategy -> list of pending OPEN events (FIFO)
    episodes = []
    synthetic_counter = -1
    ambiguous_strategies = set()

    for ev in events:
        strat = ev["strategy"]
        if ev["action"] == "OPEN":
            if open_queue[strat]:
                ambiguous_strategies.add(strat)  # OPEN consecutiva senza CLOSE intermedia
            open_queue[strat].append(ev)
        elif ev["action"] == "CLOSE":
            if open_queue[strat]:
                open_ev = open_queue[strat].pop(0)
            else:
                open_ev = None  # CLOSE senza una OPEN nota in questa finestra (es. troncata all'inizio)

            position_id = ev["ticket"] if ev["ticket"] > 0 else synthetic_counter
            if ev["ticket"] <= 0:
                synthetic_counter -= 1

            ep = _episode_base(account_id, position_id, provenance)
            ep["symbol"] = symbol
            ep["strategy_attribution"] = {"status": "VERIFIED", "strategy_name": strat}
            ep["status"] = "CLOSED"
            ep["close_time"] = ev["time"]
            ep["avg_close_price"] = ev["price"]
            ep["realized_pnl"] = ev["score_or_pnl"]
            ep["r_multiple"] = ev["r_multiple"]
            ep["deal_ids"] = [ev["ticket"]] if ev["ticket"] > 0 else []
            if open_ev is not None:
                ep["open_time"] = open_ev["time"]
                ep["avg_open_price"] = open_ev["price"]
                ep["volume_opened"] = open_ev["lots"]
                ep["volume_closed"] = open_ev["lots"]
                ep["side"] = "UNKNOWN"  # il formato non porta la direzione (sez. limiti)

            pairing_note = ("AMBIGUOUS_FIFO_MULTIPLE_OPEN_PENDING" if strat in ambiguous_strategies
                            else "SEQUENTIAL_HEURISTIC_PER_STRATEGY")
            ep["provenance"] = {**provenance, "pairing_method": pairing_note}
            episodes.append(ep)

    # OPEN rimaste senza CLOSE -> episodi ancora aperti alla fine della finestra osservata
    for strat, pending in open_queue.items():
        for open_ev in pending:
            synthetic_counter -= 1
            ep = _episode_base(account_id, synthetic_counter, provenance)
            ep["symbol"] = symbol
            ep["strategy_attribution"] = {"status": "VERIFIED", "strategy_name": strat}
            ep["status"] = "OPEN"
            ep["open_time"] = open_ev["time"]
            ep["avg_open_price"] = open_ev["price"]
            ep["volume_opened"] = open_ev["lots"]
            ep["provenance"] = {**provenance, "pairing_method": "SEQUENTIAL_HEURISTIC_PER_STRATEGY"}
            episodes.append(ep)

    return episodes
