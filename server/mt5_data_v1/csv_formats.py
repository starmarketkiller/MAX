"""MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 - rilevazione e parsing dei formati
CSV realmente trovati nel census (sez.1 della richiesta). Solo due formati
sono stati verificati byte-per-byte in questa sessione, non inventati:

1. EA_TRADE_LOG - prodotto da NXS_LogTradeCSV (MQL5/Include/NEXUS_v1/
   NXS_Logging.mqh:36, FileOpen(..., FILE_CSV, ',') -> MQL5 scrive sempre
   UTF-16LE con BOM per questo flag, verificato su
   server/research_scripts/phase7/phase7_8i/immutable_run_output/
   NEXUS_trades_serious_3y_run3.csv e su
   results/cost_calibration_67_rerun/breakoutacc_maxhist_trades.csv
   (stesso BOM FF FE, stesso encoding, file diverso). Colonne (riga header
   reale): time,action,ticket,strategy,price,lots,sl,tp,score_or_pnl,
   reason,hold_sec,r_multiple,resolved_tf.
   Limite reale del formato, non un bug di questo parser: "ticket" vale
   sempre 0 sulle righe action=OPEN (il ticket di posizione non esiste
   ancora quando l'EA scrive la riga, prima dell'invio ordine) - il join
   OPEN->CLOSE per questo formato e' quindi necessariamente euristico
   (sequenziale per strategia), mai un vero position_id. Il formato non
   contiene nemmeno il symbol (un'istanza EA = un simbolo): va fornito
   dal chiamante (es. dal run manifest), non inventato.

2. NATIVE_DEAL_EXPORT - prodotto da NXS_DIAG_ExportDeals() via
   HistoryDealGet*, verificato su server/research_scripts/phase7/
   phase7_9h/raw_data/nxs_diag_deals_export_r003.csv: ASCII puro, NON
   UTF-16 (verificato via lettura bytes raw). Colonne: deal_ticket,
   position_id,order_ticket,time,time_msc,symbol,magic,type,entry,price,
   volume,sl,tp,profit,swap,commission,comment,reason - mappa 1:1 sui
   campi MT5 HistoryDealGetInteger/Double/String(DEAL_*). Questa e' la
   fonte PREFERITA quando disponibile: ha un vero position_id.

Qualunque altro formato incontrato (es. export manuale del broker dal tab
History del terminale) torna CsvFormat.UNKNOWN - nessuna euristica
inventata per formati non verificati in questa sessione.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List


class CsvFormat(str, Enum):
    EA_TRADE_LOG = "EA_TRADE_LOG"
    NATIVE_DEAL_EXPORT = "NATIVE_DEAL_EXPORT"
    UNKNOWN = "UNKNOWN"


EA_TRADE_LOG_HEADER = ["time", "action", "ticket", "strategy", "price", "lots", "sl", "tp",
                       "score_or_pnl", "reason", "hold_sec", "r_multiple", "resolved_tf"]

NATIVE_DEAL_EXPORT_HEADER = ["deal_ticket", "position_id", "order_ticket", "time", "time_msc",
                            "symbol", "magic", "type", "entry", "price", "volume", "sl", "tp",
                            "profit", "swap", "commission", "comment", "reason"]


class MalformedCsvError(ValueError):
    """Header assente, non riconosciuto, o righe con numero di campi errato."""


@dataclass
class SniffedFile:
    encoding: str  # "utf-16" o "utf-8"
    text: str


def sniff_and_decode(path: str | Path) -> SniffedFile:
    """BOM FF FE (little-endian) -> utf-16 (copre MQL5 FileOpen(FILE_CSV)).
    Nessun BOM -> utf-8. Nessun'altra euristica: un file in un terzo encoding
    non verificato in questa sessione fa fallire la decodifica esplicitamente
    (fail-closed), non viene indovinato."""
    raw = Path(path).read_bytes()
    if raw[:2] == b"\xff\xfe":
        return SniffedFile(encoding="utf-16", text=raw.decode("utf-16"))
    return SniffedFile(encoding="utf-8", text=raw.decode("utf-8"))


def detect_format(header_row: List[str]) -> CsvFormat:
    normalized = [h.strip() for h in header_row]
    if normalized == EA_TRADE_LOG_HEADER:
        return CsvFormat.EA_TRADE_LOG
    if normalized == NATIVE_DEAL_EXPORT_HEADER:
        return CsvFormat.NATIVE_DEAL_EXPORT
    return CsvFormat.UNKNOWN


def _parse_mt5_time(value: str) -> str:
    """'2024.01.08 13:18:28' -> ISO 8601 UTC. MT5 non porta un timezone
    esplicito nei suoi export - si assume il tempo del server/terminale
    cosi' com'e', MAI una conversione silenziosa a un'altra timezone."""
    dt = datetime.strptime(value.strip(), "%Y.%m.%d %H:%M:%S")
    return dt.replace(tzinfo=timezone.utc).isoformat()


def _read_rows(text: str) -> List[List[str]]:
    reader = csv.reader(io.StringIO(text))
    return [row for row in reader if row and any(cell.strip() for cell in row)]


def _looks_like_ea_trade_log_data_row(row: List[str]) -> bool:
    """True se la riga ha la shape giusta e action in {OPEN,CLOSE} - usato
    per riconoscere un file EA_TRADE_LOG SENZA header. Caso reale, non
    ipotetico: NXS_LogTradeCSV scrive l'header solo se FileSize(h)==0 al
    momento dell'apertura (MQL5/Include/NEXUS_v1/NXS_Logging.mqh:38) - se il
    file Common\\Files\\NEXUS_trades.csv esisteva gia' non vuoto (es. un run
    precedente non ancora archiviato, lo stesso rischio di collisione
    LIVE/TESTER gia' documentato in MT5_TERMINAL_ISOLATION_POLICY_V1), le
    righe successive si accodano senza un secondo header. Verificato su
    server/research_scripts/phase7/phase7_8i/immutable_run_output/
    NEXUS_trades_serious_3y_run3.csv, che inizia direttamente con una riga
    dati."""
    return len(row) == len(EA_TRADE_LOG_HEADER) and row[1].strip() in ("OPEN", "CLOSE")


def parse_ea_trade_log(path: str | Path) -> List[dict]:
    sniffed = sniff_and_decode(path)
    rows = _read_rows(sniffed.text)
    if not rows:
        raise MalformedCsvError(f"{path}: file vuoto")
    fmt = detect_format(rows[0])
    if fmt == CsvFormat.EA_TRADE_LOG:
        data_rows = rows[1:]
    elif _looks_like_ea_trade_log_data_row(rows[0]):
        data_rows = rows  # file senza header (vedi _looks_like_ea_trade_log_data_row)
    else:
        raise MalformedCsvError(f"{path}: header non corrisponde a EA_TRADE_LOG: {rows[0]!r}")

    out = []
    for i, row in enumerate(data_rows, start=1):
        if len(row) != len(EA_TRADE_LOG_HEADER):
            raise MalformedCsvError(
                f"{path}: riga {i} ha {len(row)} campi, attesi {len(EA_TRADE_LOG_HEADER)}: {row!r}"
            )
        rec = dict(zip(EA_TRADE_LOG_HEADER, row))
        out.append({
            "row_index": i,
            "time": _parse_mt5_time(rec["time"]),
            "action": rec["action"].strip(),
            "ticket": int(rec["ticket"]),
            "strategy": rec["strategy"].strip(),
            "price": float(rec["price"]),
            "lots": float(rec["lots"]),
            "sl": float(rec["sl"]),
            "tp": float(rec["tp"]),
            "score_or_pnl": float(rec["score_or_pnl"]),
            "reason": rec["reason"].strip(),
            "hold_sec": float(rec["hold_sec"]),
            "r_multiple": float(rec["r_multiple"]),
            "resolved_tf": rec["resolved_tf"].strip(),
        })
    return out


def parse_native_deal_export(path: str | Path) -> List[dict]:
    sniffed = sniff_and_decode(path)
    rows = _read_rows(sniffed.text)
    if not rows:
        raise MalformedCsvError(f"{path}: file vuoto")
    fmt = detect_format(rows[0])
    if fmt != CsvFormat.NATIVE_DEAL_EXPORT:
        raise MalformedCsvError(f"{path}: header non corrisponde a NATIVE_DEAL_EXPORT: {rows[0]!r}")

    out = []
    for i, row in enumerate(rows[1:], start=1):
        if len(row) != len(NATIVE_DEAL_EXPORT_HEADER):
            raise MalformedCsvError(
                f"{path}: riga {i} ha {len(row)} campi, attesi {len(NATIVE_DEAL_EXPORT_HEADER)}: {row!r}"
            )
        rec = dict(zip(NATIVE_DEAL_EXPORT_HEADER, row))
        out.append({
            "row_index": i,
            "deal_ticket": int(rec["deal_ticket"]),
            "position_id": int(rec["position_id"]),
            "order_ticket": int(rec["order_ticket"]) if rec["order_ticket"] else None,
            "time": _parse_mt5_time(rec["time"]),
            "time_msc": int(rec["time_msc"]) if rec["time_msc"] else None,
            "symbol": rec["symbol"].strip() or None,
            "magic": int(rec["magic"]) if rec["magic"] else None,
            "type": rec["type"].strip() or "UNKNOWN",
            "entry": rec["entry"].strip() or None,
            "price": float(rec["price"]) if rec["price"] else 0.0,
            "volume": float(rec["volume"]) if rec["volume"] else 0.0,
            "sl": float(rec["sl"]) if rec["sl"] else None,
            "tp": float(rec["tp"]) if rec["tp"] else None,
            "profit": float(rec["profit"]) if rec["profit"] else None,
            "swap": float(rec["swap"]) if rec["swap"] else None,
            "commission": float(rec["commission"]) if rec["commission"] else None,
            "comment": rec["comment"].strip() or None,
            "reason": rec["reason"].strip() or None,
        })
    return out


def detect_format_from_file(path: str | Path) -> CsvFormat:
    sniffed = sniff_and_decode(path)
    rows = _read_rows(sniffed.text)
    if not rows:
        return CsvFormat.UNKNOWN
    fmt = detect_format(rows[0])
    if fmt != CsvFormat.UNKNOWN:
        return fmt
    if _looks_like_ea_trade_log_data_row(rows[0]):
        return CsvFormat.EA_TRADE_LOG
    return CsvFormat.UNKNOWN
