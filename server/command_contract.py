"""PR8 — Contratto canonico dei comandi (LocalBridge + EA).

Stati, transizioni, lease/retry/dead-letter e busta canonica, come funzioni PURE
e testabili (nessun I/O). Il backend applica queste regole sulle tabelle comandi.

Difetti risolti (doc 09):
- niente lease robuste, retry, conteggio tentativi, dead-letter (bridge_commands);
- consumo prima della conferma; stato non canonico.
"""
from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timezone

SCHEMA_VERSION = 1

# Stati canonici (doc 09). Dead-letter = FAILED_FINAL con motivo max_attempts.
PENDING = "PENDING"
LEASED = "LEASED"
RUNNING = "RUNNING"
SUCCEEDED = "SUCCEEDED"
FAILED_RETRYABLE = "FAILED_RETRYABLE"
FAILED_FINAL = "FAILED_FINAL"
EXPIRED = "EXPIRED"
CANCELLED = "CANCELLED"

STATES = {PENDING, LEASED, RUNNING, SUCCEEDED, FAILED_RETRYABLE,
          FAILED_FINAL, EXPIRED, CANCELLED}
TERMINAL = {SUCCEEDED, FAILED_FINAL, EXPIRED, CANCELLED}

# Transizioni ammesse.
TRANSITIONS = {
    PENDING: {LEASED, EXPIRED, CANCELLED},
    LEASED: {RUNNING, PENDING, FAILED_RETRYABLE, FAILED_FINAL, EXPIRED, CANCELLED},
    RUNNING: {SUCCEEDED, FAILED_RETRYABLE, FAILED_FINAL, PENDING, EXPIRED, CANCELLED},
    FAILED_RETRYABLE: {PENDING, LEASED, FAILED_FINAL, EXPIRED, CANCELLED},
    SUCCEEDED: set(), FAILED_FINAL: set(), EXPIRED: set(), CANCELLED: set(),
}

# Mappa compatibilità col vocabolario legacy di bridge_commands.
LEGACY_TO_CANON = {"pending": PENDING, "sent": LEASED, "done": SUCCEEDED, "error": FAILED_RETRYABLE}
CANON_TO_LEGACY = {PENDING: "pending", LEASED: "sent", RUNNING: "sent",
                   SUCCEEDED: "done", FAILED_RETRYABLE: "error",
                   FAILED_FINAL: "error", EXPIRED: "error", CANCELLED: "error"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_command_id() -> str:
    return "cmd-" + secrets.token_hex(8)


def can_transition(src: str, dst: str) -> bool:
    return dst in TRANSITIONS.get(src, set())


def idempotency_key(command_type: str, target: dict, payload: dict) -> str:
    """Chiave deterministica: due enqueue identici non creano due comandi."""
    import json
    basis = json.dumps({"t": command_type, "target": target, "payload": payload},
                       sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(basis.encode()).hexdigest()[:16]


def build_envelope(command_type, target, payload=None, created_by="operator",
                   ttl_seconds=300, max_attempts=3):
    """Busta canonica (doc 09). target è scoped: instance/host/account/symbol."""
    payload = payload or {}
    target = target or {}
    from datetime import timedelta
    created = datetime.now(timezone.utc)
    return {
        "command_id": new_command_id(),
        "command_type": command_type,
        "schema_version": SCHEMA_VERSION,
        "created_at": created.isoformat(),
        "created_by": created_by,
        "target": {k: target.get(k) for k in ("instance_id", "host_id", "account_id", "symbol")},
        "payload": payload,
        "idempotency_key": idempotency_key(command_type, target, payload),
        "expires_at": (created + timedelta(seconds=ttl_seconds)).isoformat(),
        "status": PENDING,
        "attempts": 0,
        "max_attempts": max_attempts,
        "lease_until": None,
    }


# --------------------------- macchina a stati PURA -------------------------
def lease(cmd: dict, now_ts: float, lease_seconds: int = 60) -> dict:
    """PENDING/FAILED_RETRYABLE -> LEASED con scadenza; incrementa attempts."""
    src = cmd["status"]
    if src not in (PENDING, FAILED_RETRYABLE):
        raise ValueError(f"non leasabile da {src}")
    cmd = dict(cmd)
    cmd["status"] = LEASED
    cmd["attempts"] = int(cmd.get("attempts", 0)) + 1
    cmd["lease_until"] = now_ts + lease_seconds
    return cmd


def acknowledge_start(cmd: dict) -> dict:
    if not can_transition(cmd["status"], RUNNING):
        raise ValueError(f"ack start non valido da {cmd['status']}")
    cmd = dict(cmd); cmd["status"] = RUNNING
    return cmd


def complete(cmd: dict, ok: bool, retryable: bool = True) -> dict:
    """Completamento: SUCCEEDED, oppure FAILED_RETRYABLE / FAILED_FINAL
    (dead-letter) se superato max_attempts."""
    cmd = dict(cmd)
    if ok:
        cmd["status"] = SUCCEEDED
        return cmd
    if not retryable or int(cmd.get("attempts", 0)) >= int(cmd.get("max_attempts", 3)):
        cmd["status"] = FAILED_FINAL           # dead-letter
        cmd["dead_letter_reason"] = "max_attempts" if retryable else "non_retryable"
    else:
        cmd["status"] = FAILED_RETRYABLE
    return cmd


def reclaim_if_expired_lease(cmd: dict, now_ts: float) -> dict:
    """Lease scaduta: torna PENDING se restano tentativi, altrimenti dead-letter."""
    if cmd["status"] not in (LEASED, RUNNING):
        return cmd
    lu = cmd.get("lease_until")
    if lu is None or now_ts < lu:
        return cmd
    cmd = dict(cmd)
    if int(cmd.get("attempts", 0)) >= int(cmd.get("max_attempts", 3)):
        cmd["status"] = FAILED_FINAL
        cmd["dead_letter_reason"] = "lease_expired_max_attempts"
    else:
        cmd["status"] = PENDING
        cmd["lease_until"] = None
    return cmd


def expire_if_past_ttl(cmd: dict, now_ts_iso: str) -> dict:
    """expires_at superato e non terminale -> EXPIRED."""
    exp = cmd.get("expires_at")
    if not exp or cmd["status"] in TERMINAL:
        return cmd
    if now_ts_iso >= exp:
        cmd = dict(cmd); cmd["status"] = EXPIRED
    return cmd


def is_dead_letter(cmd: dict) -> bool:
    return cmd["status"] == FAILED_FINAL
