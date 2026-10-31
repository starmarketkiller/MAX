"""Static gate: l'EA deve emettere event=open sul path ledger OPEN.

NEXUS-WF-002 — senza MetaEditor non compilare; si verifica il sorgente.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EA = ROOT / "MQL5" / "Experts" / "NEXUS_EA_v2.mq5"


def test_on_trade_transaction_handles_ledger_open():
    src = EA.read_text(encoding="utf-8", errors="replace")
    assert "NXS_LEDGER_EV_OPEN" in src
    assert 'eventKind' in src or '"open"' in src
    # Il push open deve passare da PushTradeReason (stesso canale di close).
    assert "NXS_Prot_PushTradeReason" in src
    # Deve aggregare la position prima del push (niente payload inventato).
    assert "NXS_Ledger_AggregatePosition" in src


def test_open_push_uses_open_event_literal():
    src = EA.read_text(encoding="utf-8", errors="replace")
    # Cerca il blocco OPEN vicino al ledger event.
    idx = src.find("NXS_LEDGER_EV_OPEN")
    assert idx >= 0
    window = src[idx : idx + 1200]
    assert '"open"' in window
    assert "NXS_Prot_PushTradeReason" in window
