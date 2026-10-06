"""Test per csv_formats.py (MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1).

Usa i file CSV reali trovati nel census di questa sessione (non fixture
sintetiche per il rilevamento formato) + fixture sintetiche per i casi di
errore (malformato), che per definizione non devono esistere nel repo.
"""
from pathlib import Path

import pytest

from mt5_data_v1 import csv_formats

REPO_ROOT = Path(__file__).resolve().parents[2]
NATIVE_DEAL_SAMPLE = REPO_ROOT / "server/research_scripts/phase7/phase7_9h/raw_data/nxs_diag_deals_export_r003.csv"
EA_LOG_SAMPLE_NO_HEADER = (REPO_ROOT /
    "server/research_scripts/phase7/phase7_8i/immutable_run_output/NEXUS_trades_serious_3y_run3.csv")


def test_native_deal_export_detected_real_file():
    assert csv_formats.detect_format_from_file(NATIVE_DEAL_SAMPLE) == csv_formats.CsvFormat.NATIVE_DEAL_EXPORT


def test_native_deal_export_is_plain_utf8_not_utf16():
    sniffed = csv_formats.sniff_and_decode(NATIVE_DEAL_SAMPLE)
    assert sniffed.encoding == "utf-8"


def test_ea_trade_log_headerless_real_file_detected():
    # File reale che inizia direttamente con una riga dati, senza header -
    # caso reale di accodamento su Common\Files (vedi csv_formats.py).
    assert csv_formats.detect_format_from_file(EA_LOG_SAMPLE_NO_HEADER) == csv_formats.CsvFormat.EA_TRADE_LOG


def test_ea_trade_log_sample_is_utf16_with_bom():
    sniffed = csv_formats.sniff_and_decode(EA_LOG_SAMPLE_NO_HEADER)
    assert sniffed.encoding == "utf-16"


def test_parse_native_deal_export_row_count_matches_data_lines():
    rows = csv_formats.parse_native_deal_export(NATIVE_DEAL_SAMPLE)
    raw_text = NATIVE_DEAL_SAMPLE.read_text(encoding="utf-8")
    data_lines = [l for l in raw_text.splitlines() if l.strip()][1:]  # - header
    assert len(rows) == len(data_lines)


def test_parse_native_deal_export_first_row_is_balance_deposit():
    rows = csv_formats.parse_native_deal_export(NATIVE_DEAL_SAMPLE)
    first = rows[0]
    assert first["type"] == "DEAL_TYPE_BALANCE"
    assert first["position_id"] == 0
    assert first["symbol"] is None  # i deal di balance non hanno simbolo


def test_parse_ea_trade_log_headerless_file_parses_all_rows_as_data():
    rows = csv_formats.parse_ea_trade_log(EA_LOG_SAMPLE_NO_HEADER)
    assert len(rows) > 0
    assert all(r["action"] in ("OPEN", "CLOSE") for r in rows)


def test_malformed_csv_wrong_field_count_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "deal_ticket,position_id,order_ticket,time,time_msc,symbol,magic,type,entry,price,volume,sl,tp,profit,swap,commission,comment,reason\n"
        "1,2,3,2024.01.01 00:00:00\n",  # troppi pochi campi
        encoding="utf-8",
    )
    with pytest.raises(csv_formats.MalformedCsvError):
        csv_formats.parse_native_deal_export(bad)


def test_malformed_csv_unrecognized_header_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("foo,bar,baz\n1,2,3\n", encoding="utf-8")
    with pytest.raises(csv_formats.MalformedCsvError):
        csv_formats.parse_native_deal_export(bad)
    assert csv_formats.detect_format_from_file(bad) == csv_formats.CsvFormat.UNKNOWN


def test_empty_file_detected_as_unknown(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    assert csv_formats.detect_format_from_file(empty) == csv_formats.CsvFormat.UNKNOWN


def test_parse_native_deal_export_rejects_ea_trade_log_file():
    # Un file EA_TRADE_LOG passato al parser sbagliato deve fallire
    # esplicitamente, non produrre righe sbagliate silenziosamente.
    with pytest.raises(csv_formats.MalformedCsvError):
        csv_formats.parse_native_deal_export(EA_LOG_SAMPLE_NO_HEADER)
