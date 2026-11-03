"""Read-only bar store for H1-A. Reuses, byte-for-byte, the already
verified XAUUSD H4 loader from phase5e_causal_replay_v1.dataset
(manifest hash check, DISCOVERY_REUSE classification, excludes the
final boundary bar touching the old H006 holdout) - nothing here
regenerates, resamples or refits a single bar.

Adds the one thing that loader does not expose: an as_of / available_at
query surface, so the decision engine can never see a bar that has
not closed yet relative to a given replay instant.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
for _p in (str(_REPO_ROOT / "server"), str(_REPO_ROOT / "server" / "research_scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from phase5e_causal_replay_v1 import dataset as _dataset  # noqa: E402

SYMBOL = _dataset.SYMBOL
TIMEFRAME = _dataset.TIMEFRAME
BAR_SECONDS = _dataset.BAR_SECONDS
DATASET_ID = _dataset.DATASET_ID
IntegrityError = _dataset.IntegrityError


def _available_at_utc(bar: dict[str, Any]) -> datetime:
    """A bar's information is available only once it has closed -
    open_time + BAR_SECONDS, never earlier. Same rule as
    phase5e_causal_replay_v1.replay._bar_close_timestamp, reused."""
    open_dt = datetime.fromisoformat(bar["bar_open_utc"].replace("Z", "+00:00"))
    if open_dt.tzinfo is None:
        raise ValueError(f"bar_open_utc has no timezone: {bar['bar_open_utc']!r}")
    return open_dt.astimezone(timezone.utc) + timedelta(seconds=BAR_SECONDS)


class BarStore:
    """Immutable, verified, read-only view over the XAUUSD H4 dataset."""

    def __init__(self) -> None:
        self._bars: list[dict[str, Any]] = _dataset.load_bars()
        for bar in self._bars:
            bar["available_at_utc"] = _available_at_utc(bar).isoformat().replace("+00:00", "Z")
        # re-verify strict ascending order after annotation (defensive,
        # mirrors the same check dataset.load_bars already does)
        epochs = [b["bar_epoch"] for b in self._bars]
        if epochs != sorted(epochs) or len(set(epochs)) != len(epochs):
            raise IntegrityError("bar store is not strictly increasing after annotation")

    def all_bars(self) -> list[dict[str, Any]]:
        """Full verified series, ascending. Callers that need causal
        behaviour MUST use bars_as_of(), not this, for anything that
        touches a decision."""
        return list(self._bars)

    def bars_as_of(self, as_of_utc: str) -> list[dict[str, Any]]:
        """Every bar whose available_at_utc <= as_of_utc - i.e. every
        bar that has actually closed by the replay instant as_of_utc.
        Never returns a bar still in formation or in the future."""
        cutoff = datetime.fromisoformat(as_of_utc.replace("Z", "+00:00"))
        if cutoff.tzinfo is None:
            raise ValueError("as_of_utc must be timezone-aware")
        out = []
        for bar in self._bars:
            available = datetime.fromisoformat(bar["available_at_utc"].replace("Z", "+00:00"))
            if available <= cutoff:
                out.append(bar)
            else:
                break  # bars are ascending; nothing later can qualify either
        return out

    def coverage(self) -> dict[str, Any]:
        if not self._bars:
            return {"first_bar_open_utc": None, "last_bar_open_utc": None, "row_count": 0}
        return {
            "first_bar_open_utc": self._bars[0]["bar_open_utc"],
            "last_bar_open_utc": self._bars[-1]["bar_open_utc"],
            "last_bar_available_at_utc": self._bars[-1]["available_at_utc"],
            "row_count": len(self._bars),
        }
