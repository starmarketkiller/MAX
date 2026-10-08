#!/usr/bin/env python3
"""NEXUS MT5 Terminal Identity Guard V1.

Minimal enforcement of docs/MT5_TERMINAL_ISOLATION_POLICY_V1.md: before the
local worker executes any action, verify that the terminal it is actually
configured against matches the role it claims to be (`terminal_role` in
nexus_worker.config.json), using the expected-path profile registry in this
same directory.

Schema implemented here (see docs/MT5_TERMINAL_ISOLATION_POLICY_V1.md):

    requested role
      -> resolve terminal profile
      -> verify terminal path
      -> verify data directory
      -> verify identity/fingerprint (path-based, see limitation below)
      -> verify allowed operation
      -> acquire lock
      -> execute (execution itself happens in the caller, not here)

Explicit, documented limitation (V1 scope, not hidden): this verifies "is
the worker pointed at the expected directory for this role" - it does NOT
verify "is this exactly the expected binary/terminal instance". No mechanism
was found anywhere in this repository to independently re-derive MetaTrader
5's own internal terminal-data-folder hash, or to attest a specific
terminal64.exe binary. "Identity" here is a path-substring match against a
declared profile (plus an optional exact fingerprint pin a machine owner may
set over that same path-derived value) - never describe this as
cryptographic attestation of the terminal binary/instance in logs, docs, or
error messages. A path/profile mismatch still fails closed (IdentityMismatch,
not retryable) regardless of this limitation - the limitation is about what
"verified" means, not about whether a mismatch is enforced. See docs/
MT5_TERMINAL_IDENTITY_GUARD_V1.md for the full discussion.

This module does nothing on import beyond defining functions/constants - it
never touches a real terminal, never opens a network connection, never
modifies MQL5/risk/execution. It is imported and called by
nexus_local_worker.py.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any, Dict, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
PROFILES_PATH_OVERRIDE = SCRIPT_DIR / "nexus_terminal_profiles.config.json"
PROFILES_PATH_EXAMPLE = SCRIPT_DIR / "nexus_terminal_profiles.config.example.json"
LOCK_DIR = SCRIPT_DIR / ".terminal_locks"

#: Margine generoso oltre al timeout di 120s di handle_compile_ea - usato
#: SOLO come soglia "vecchio" quando il processo che detiene il lock risulta
#: già morto (reclaim rapido di un lock orfano). Un processo ancora vivo NON
#: viene mai considerato stale solo per questo (vedi acquire_lock).
STALE_LOCK_SEC = 180

#: Soglia molto più alta, usata SOLO come valvola di sicurezza quando il
#: processo che detiene il lock risulta ancora vivo ma lo trattiene da più
#: tempo di qualunque operazione nota (compile=120s, restart/deploy più
#: brevi). Deliberatamente separata da STALE_LOCK_SEC: un processo lento ma
#: vivo non deve perdere il lock solo perché "vecchio" - serve un margine
#: molto più ampio ed esplicito prima di forzare il reclaim.
HARD_STALE_LOCK_SEC = 900

VALID_ROLES = ("LIVE_TERMINAL", "TESTER_TERMINAL")


class IdentityMismatch(RuntimeError):
    """Terminal identity/role/operation mismatch - NOT retryable (config problem)."""


class LockBusy(RuntimeError):
    """Another operation already holds the role lock - retryable."""


@dataclass
class VerifiedIdentity:
    role: str
    terminal_path: str
    data_dir: str
    fingerprint: str
    action: str

    def __str__(self) -> str:  # structured-enough for a single log line
        return (f"role={self.role} action={self.action} "
                f"terminal_path={self.terminal_path} data_dir={self.data_dir} "
                f"fingerprint={self.fingerprint}")


def _load_profiles() -> Dict[str, Any]:
    path = PROFILES_PATH_OVERRIDE if PROFILES_PATH_OVERRIDE.exists() else PROFILES_PATH_EXAMPLE
    if not path.exists():
        raise IdentityMismatch(
            f"nessun registro di profili terminale trovato "
            f"({PROFILES_PATH_OVERRIDE.name} o {PROFILES_PATH_EXAMPLE.name}) - "
            f"impossibile verificare l'identita' del terminale"
        )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("schema_version") != 1:
        raise IdentityMismatch(f"schema_version non supportata in {path.name}")
    return data


def _resolve_data_dir(cfg: Dict[str, Any]) -> str:
    """.../MQL5/Experts -> la data directory del terminale (due livelli sopra)."""
    experts = str(cfg.get("mql5_experts") or "").strip()
    if not experts:
        raise IdentityMismatch(
            "mql5_experts non configurato: impossibile risolvere la data directory del terminale"
        )
    # A bridge configuration may be validated in a Linux CI process while
    # describing the Windows host on which MT5 runs.  Path.resolve() on POSIX
    # treats ``C:\\...`` as a relative POSIX path and destroys the declared
    # identity.  Preserve Windows path semantics without touching the host FS.
    if _looks_like_windows_path(experts):
        return str(PureWindowsPath(experts).parent.parent)
    return str(Path(experts).resolve().parent.parent)


def _looks_like_windows_path(value: str) -> bool:
    """Return whether *value* is an absolute drive/UNC Windows path."""
    path = PureWindowsPath(value)
    return bool(path.drive and path.root)


def _resolve_declared_terminal_path(value: str) -> str:
    """Resolve native paths but preserve a declared remote Windows identity."""
    if _looks_like_windows_path(value):
        return str(PureWindowsPath(value))
    path = Path(value)
    return str(path.resolve()) if path.exists() else value


def resolve_and_verify(cfg: Dict[str, Any], action: str) -> VerifiedIdentity:
    """Steps 1-5 of the schema: role -> profile -> path -> data dir -> operation.

    Raises IdentityMismatch (permanent, do-not-retry) on any failure.
    """
    role = str(cfg.get("terminal_role") or "").strip()
    if role not in VALID_ROLES:
        raise IdentityMismatch(
            f"terminal_role non configurato o non valido: {role!r} "
            f"(deve essere uno di {VALID_ROLES})"
        )

    profiles = _load_profiles().get("profiles", {})
    profile = profiles.get(role)
    if not profile:
        raise IdentityMismatch(f"nessun profilo definito per il ruolo {role!r}")

    terminal_path_raw = str(cfg.get("mt5_path") or "")
    if not terminal_path_raw:
        raise IdentityMismatch("mt5_path non configurato")
    terminal_path = _resolve_declared_terminal_path(terminal_path_raw)

    expected_path_sub = profile.get("expected_terminal_path_substring")
    if expected_path_sub and expected_path_sub.lower() not in terminal_path.lower():
        raise IdentityMismatch(
            f"mismatch di identita': terminal_role={role} richiede un path contenente "
            f"{expected_path_sub!r}, ma mt5_path configurato e' {terminal_path!r}"
        )

    data_dir = _resolve_data_dir(cfg)
    expected_data_sub = profile.get("expected_data_dir_substring")
    if expected_data_sub and expected_data_sub.lower() not in data_dir.lower():
        raise IdentityMismatch(
            f"mismatch di identita': terminal_role={role} richiede una data directory "
            f"contenente {expected_data_sub!r}, ma la data directory risolta e' {data_dir!r}"
        )

    # Fingerprint: NON un hash crittografico verificato di MT5 - solo una firma
    # derivata dai due path sopra, utile per logging/pin opzionale. Vedi il
    # limite dichiarato nel docstring del modulo.
    fingerprint = hashlib.sha256(
        f"{terminal_path.lower()}|{data_dir.lower()}".encode()
    ).hexdigest()[:16]
    pinned = profile.get("pinned_terminal_id")
    if pinned and pinned != fingerprint:
        raise IdentityMismatch(
            f"mismatch di identita': fingerprint {fingerprint} non corrisponde al pin "
            f"dichiarato {pinned} per il ruolo {role}"
        )

    allowed = set(profile.get("allowed_operations") or [])
    forbidden = set(profile.get("forbidden_operations") or [])
    if action in forbidden or (allowed and action not in allowed):
        raise IdentityMismatch(
            f"operazione non permessa: {action!r} non e' consentita per terminal_role={role} "
            f"(allowed={sorted(allowed)}, forbidden={sorted(forbidden)})"
        )

    return VerifiedIdentity(role=role, terminal_path=terminal_path, data_dir=data_dir,
                            fingerprint=fingerprint, action=action)


def _lock_path(role: str) -> Path:
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    return LOCK_DIR / f"{role}.lock"


def _pid_is_alive(pid: int) -> bool:
    """Best-effort liveness check. Deliberatamente conservativo: qualunque
    incertezza (piattaforma non gestita, tasklist non disponibile, errore)
    ritorna True (vivo) - meglio rifiutare un reclaim di troppo che
    scippare il lock a un processo realmente ancora attivo."""
    if pid <= 0:
        return False
    try:
        if platform.system().lower() == "windows":
            out = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=10, check=False
            ).stdout
            return str(pid) in out
        else:
            os.kill(pid, 0)
            return True
    except ProcessLookupError:
        return False
    except Exception:
        return True  # incerto -> conservativo, assume vivo


def acquire_lock(identity: VerifiedIdentity, action: str,
                 job_id: Optional[str] = None) -> Path:
    """Step 6: lock esclusivo per ruolo, creazione atomica (O_EXCL).

    Policy di reclaim di un lock stale, deterministica, in due livelli -
    NON un semplice "troppo vecchio" (rischio: scippare il lock a un
    processo lento ma ancora vivo):

    1. Il processo che detiene il lock (pid registrato) non esiste più ->
       lock orfano, reclaim immediato (nessun rischio: nessuno lo sta
       davvero usando).
    2. Il processo esiste ancora MA il lock ha superato HARD_STALE_LOCK_SEC
       (900s, molto oltre qualunque operazione nota) -> valvola di
       sicurezza esplicita contro un deadlock permanente, loggata ad alta
       visibilita', non silenziosa.
    3. In ogni altro caso (processo vivo, eta' sotto la soglia hard) ->
       LockBusy, mai reclaimato solo perche' "vecchio".
    """
    path = _lock_path(identity.role)
    now = time.time()
    payload = json.dumps({
        "pid": os.getpid(), "ts": now, "action": action,
        "role": identity.role, "job_id": job_id,
    }).encode("utf-8")

    for attempt in range(2):
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, payload)
            finally:
                os.close(fd)
            return path
        except FileExistsError:
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                existing_pid = int(existing.get("pid", -1))
                age = now - float(existing.get("ts", 0))
                existing_action = existing.get("action", "?")
                existing_job = existing.get("job_id")
            except Exception:
                # Lock illeggibile: non possiamo determinare pid/eta' in modo
                # affidabile. Trattato come orfano (reclaim), non come "vecchio
                # quindi reclaimabile" - un file corrotto non e' prova che il
                # processo sia morto, ma qui scegliamo di procedere per non
                # bloccare tutto a causa di un file di lock danneggiato.
                existing_pid = -1
                age = 0.0
                existing_action = "?"
                existing_job = None

            pid_alive = _pid_is_alive(existing_pid)
            reclaimable = (not pid_alive) or (age >= HARD_STALE_LOCK_SEC)

            if reclaimable and attempt == 0:
                reason = ("processo terminato" if not pid_alive
                         else f"HARD_STALE_LOCK_SEC ({HARD_STALE_LOCK_SEC}s) superato "
                              f"con processo ancora attivo - valvola di sicurezza")
                print(f"[NEXUS TerminalGuard] reclaim lock {identity.role}.lock "
                     f"(pid={existing_pid}, eta'={age:.0f}s): {reason}")
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
                continue  # un solo retry dopo la pulizia

            raise LockBusy(
                f"lock gia' attivo per terminal_role={identity.role} "
                f"(pid={existing_pid}, vivo={pid_alive}, azione={existing_action!r}, "
                f"job_id={existing_job!r}, eta'={age:.0f}s) - riprova piu' tardi"
            )
    raise LockBusy(f"impossibile acquisire il lock per terminal_role={identity.role}")


def release_lock(lock_path: Optional[Path]) -> None:
    if lock_path is not None and lock_path.exists():
        try:
            lock_path.unlink()
        except Exception:
            pass
