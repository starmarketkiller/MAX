"""Macro event gate V1 — NFP/CPI/FOMC non-directional microstructure (MEG-NFP-CPI-FOMC-001).

Phase 1 asks whether spread and realized range in the event window exceed the
same local clock on non-event days. Ceiling: EXPLORATORY_ONLY. Never claims
VALIDATED. No real XAUUSD outcomes in this package; calendar timestamps must
be supplied by the research PC (see fixtures/ + macro_calendar_v1/SOURCES.md).
"""

__all__ = ["__version__"]
__version__ = "1.0.0"
