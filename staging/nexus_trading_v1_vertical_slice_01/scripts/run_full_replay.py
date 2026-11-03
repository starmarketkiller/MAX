"""run_full_replay.py - end-to-end driver: BarStore -> decision_engine
-> paper_engine -> journal, over the FULL reused dataset. Produces
logs/decisions.jsonl and logs/paper_attempts.jsonl (hash-chained,
append-only) plus logs/run_summary.json.

PAPER-ONLY. No MT5, no broker, no network. No economic claim is made
by this script - see LIMITATIONS.md.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data_layer.bar_store import BarStore  # noqa: E402
from decision_engine import engine as decision_engine  # noqa: E402
from paper_engine.simulator import PaperEngine  # noqa: E402
from journal import journal  # noqa: E402

LOGS_DIR = _ROOT / "logs"
DECISIONS_LOG = LOGS_DIR / "decisions.jsonl"
ATTEMPTS_LOG = LOGS_DIR / "paper_attempts.jsonl"


def main() -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    for p in (DECISIONS_LOG, ATTEMPTS_LOG):
        if p.exists():
            p.unlink()  # fresh run; journal itself stays append-only within a single run

    store = BarStore()
    bars = store.all_bars()
    bars_by_epoch = {b["bar_epoch"]: b for b in bars}
    epochs_sorted = [b["bar_epoch"] for b in bars]

    paper = PaperEngine(bars_by_epoch, epochs_sorted)

    from collections import deque
    import decision_engine.h1a_detector as det

    highs: deque[float] = deque(maxlen=det.LOOKBACK_N)
    lows: deque[float] = deque(maxlen=det.LOOKBACK_N)

    decision_records = []
    for bar in bars:
        # advance any open attempt BEFORE evaluating a new decision on
        # this bar, so a same-bar exit is recorded before a same-bar
        # new signal could ever be considered (still only one open at
        # a time either way, but keeps event ordering sane in the log)
        paper.advance_open_attempt(bar)

        if len(highs) < det.LOOKBACK_N:
            level_high = level_low = None
        else:
            level_high, level_low = max(highs), min(lows)
        buffer = float(bar.get("avg_spread") or 0.0)
        record = decision_engine.evaluate_bar(bar, level_high, level_low, buffer, paper.has_open_attempt())
        decision_records.append(record)

        if record["h1a_decision"] in ("BUY", "SELL"):
            paper.open_from_candidate(record)

        highs.append(bar["high"])
        lows.append(bar["low"])

    last_bar = bars[-1]
    paper.close_still_open_at_dataset_end(last_bar)

    journal.append_records(decision_records, DECISIONS_LOG)
    journal.append_records([a.to_dict() for a in paper.all_attempts()], ATTEMPTS_LOG)

    decisions_chain_ok = journal.verify_chain(DECISIONS_LOG)
    attempts_chain_ok = journal.verify_chain(ATTEMPTS_LOG)

    decision_counts = Counter(r["h1a_decision"] for r in decision_records)
    reason_counts = Counter(r["h1a_reason_code"] for r in decision_records)
    outcome_counts = Counter(a.outcome for a in paper.all_attempts())

    summary = {
        "dataset_coverage": store.coverage(),
        "total_bars_processed": len(bars),
        "decision_counts": dict(decision_counts),
        "reason_counts": dict(reason_counts),
        "total_paper_attempts": len(paper.all_attempts()),
        "outcome_counts": dict(outcome_counts),
        "final_equity": paper.equity,
        "starting_equity": 10_000.0,
        "decisions_log_chain_verified": decisions_chain_ok,
        "attempts_log_chain_verified": attempts_chain_ok,
        "strategy_id": "H1_A",
        "strategy_version": "H1_A_V1",
    }
    (LOGS_DIR / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
