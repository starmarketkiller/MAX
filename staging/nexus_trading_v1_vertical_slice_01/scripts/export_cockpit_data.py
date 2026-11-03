"""export_cockpit_data.py - builds a self-contained JSON data file for the
isolated Cockpit Demo (cockpit_demo/index.html). Reads from the SAME
already-produced artifacts as the rest of this slice (BarStore + the
hash-chained logs under logs/) - it does not re-run the strategy or
invent any new number.

Selects a bounded bar window (not the full 4,808 bars) so the demo
stays small and fast in a browser; the window is chosen only for
containing several complete paper trades, not for favorable outcomes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data_layer.bar_store import BarStore  # noqa: E402
from journal import journal  # noqa: E402

LOGS_DIR = _ROOT / "logs"
OUT_DIR = _ROOT / "cockpit_demo" / "data"
WINDOW_START_INDEX = 0
WINDOW_END_INDEX = 260  # ~ first 260 H4 bars; contains several TP/SL-resolved trades


def main() -> None:
    store = BarStore()
    bars = store.all_bars()[WINDOW_START_INDEX:WINDOW_END_INDEX]
    window_epochs = {b["bar_epoch"] for b in bars}
    min_epoch, max_epoch = min(window_epochs), max(window_epochs)

    decisions = journal.read_all(LOGS_DIR / "decisions.jsonl")
    decisions_in_window = [d for d in decisions if d["bar_epoch"] in window_epochs]

    attempts = journal.read_all(LOGS_DIR / "paper_attempts.jsonl")
    attempts_in_window = [
        a for a in attempts
        if a["signal_bar_epoch"] in window_epochs
        or (a.get("fill_bar_epoch") is not None and min_epoch <= a["fill_bar_epoch"] <= max_epoch)
    ]

    bars_out = [
        {
            "bar_epoch": b["bar_epoch"],
            "bar_open_utc": b.get("bar_open_utc"),
            "open": b["open"], "high": b["high"], "low": b["low"], "close": b["close"],
            "available_at_utc": b.get("available_at_utc"),
        }
        for b in bars
    ]

    data = {
        "meta": {
            "strategy_id": "H1_A",
            "strategy_version": "H1_A_V1",
            "symbol": "XAUUSD",
            "source_timeframe": "H4",
            "window_bar_count": len(bars_out),
            "generated_from": "logs/decisions.jsonl + logs/paper_attempts.jsonl + data_layer.BarStore (same slice artifacts, no re-simulation)",
            "no_economic_claim": (
                "This window is illustrative of the MECHANICS only (decision -> fill -> "
                "SL/TP resolution -> journal). It is not evidence of a trading edge: "
                "frozen DESIGN_ASSUMPTION_V1 parameters, single historical window, no "
                "statistical testing. See ../LIMITATIONS.md."
            ),
        },
        "bars": bars_out,
        "decisions": decisions_in_window,
        "attempts": attempts_in_window,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "cockpit_data.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out_path} : {len(bars_out)} bars, {len(decisions_in_window)} decisions, "
          f"{len(attempts_in_window)} attempts")


if __name__ == "__main__":
    main()
