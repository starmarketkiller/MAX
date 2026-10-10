"""Which account the EA reports it is trading on, read from its own push.

NEXUS-ACCT-001: the EA (NXS_AccountGuard.mqh) is what blocks new exposure on a
non-DEMO account. This module only reads what the EA declared. It never
authorizes anything, and an EA that does not declare its account stays
UNREPORTED rather than being assumed DEMO.
"""
from __future__ import annotations

KNOWN_MODES = {"DEMO", "LIVE", "CONTEST", "TESTER"}


def _bool(value):
    return value is True or (isinstance(value, str) and value.lower() == "true")


def classify(payload):
    payload = payload if isinstance(payload, dict) else {}
    mode = str(payload.get("accountTradeMode") or "").upper()
    login = payload.get("accountLogin")
    if not mode:
        return {"verdict": "UNREPORTED", "trade_mode": None, "account_login": None,
                "account_server": None, "entries_allowed": None, "live_armed": False,
                "note": "EA build without NEXUS-ACCT-001: account type unknown"}
    entries = _bool(payload.get("accountEntriesAllowed"))
    armed = _bool(payload.get("liveTradingArmed"))
    has_login = login not in (None, "", 0, "0")
    if mode not in KNOWN_MODES:
        verdict = "UNKNOWN"
    elif mode == "DEMO" and not has_login:
        # Un DEMO senza login e' un conto non ancora letto, non un DEMO.
        verdict = "UNKNOWN"
    elif mode in {"DEMO", "TESTER"}:
        verdict = f"{mode}_REPORTED"
    elif armed and entries:
        verdict = "LIVE_ARMED"
    else:
        verdict = "LIVE_BLOCKED"
    return {"verdict": verdict, "trade_mode": mode,
            "account_login": str(login) if login not in (None, "") else None,
            "account_server": payload.get("accountServer"),
            "entries_allowed": entries, "live_armed": armed,
            "note": "reported by the EA; a DEMO report is not an owner verification"}
