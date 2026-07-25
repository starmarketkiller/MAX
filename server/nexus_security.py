"""Fail-closed production security controls for the NEXUS backend.

Copre i finding dell'audit master:

* NEXUS-SEC-001 / AUD0-SEC-001 / AUD0-SEC-004 / NXS-BE-CONFIG-001
  — credenziali di default e segreti placeholder devono impedire l'avvio
    fuori dallo sviluppo esplicito.
* AUD0-SEC-005 / NXS-BE-CONFIG-002 — il segreto JWT effimero è vietato in
  produzione.
* AUD0-SEC-002 / AUD0-BE-AUTH-003 — sessioni privilegiate a lunga durata.
* AUD0-SEC-006 / NXS-BE-AUTH-005 — login senza rate limiting.
* AUD0-SEC-009 / AUD0-BE-AUTH-005 — JWT senza iss/aud/jti/revoca.
* AUD0-SEC-008 / AUD0-BE-AUTH-007 — nessuna protezione CSRF sulle mutazioni
  autenticate via cookie.
* AUD0-DEPLOY-RENDER-001 / AUD0-LIC-001 — license mode `open` in produzione.

Il modulo è volutamente privo di dipendenze esterne (solo stdlib + PyJWT) in
modo da poter essere importato durante il preflight di avvio del container.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional

# --------------------------------------------------------------------------- #
# Ambienti canonici (spec A3.1 §5.1)
# --------------------------------------------------------------------------- #
ENV_DEVELOPMENT = "DEVELOPMENT"
ENV_SIMULATION = "SIMULATION"
ENV_DEMO = "DEMO"
ENV_PAPER = "PAPER"
ENV_LIVE = "LIVE"

VALID_ENVIRONMENTS = (
    ENV_DEVELOPMENT,
    ENV_SIMULATION,
    ENV_DEMO,
    ENV_PAPER,
    ENV_LIVE,
)

#: Ambienti in cui vanno applicati tutti i controlli fail-closed.
HARDENED_ENVIRONMENTS = (ENV_DEMO, ENV_PAPER, ENV_LIVE)

#: Valori che l'audit ha trovato nel repository e che non devono mai
#: raggiungere un ambiente non di sviluppo.
FORBIDDEN_SECRET_VALUES = frozenset({
    "nexus_bridge_token_2026",
    "admin",
    "password",
    "changeme",
    "change-me",
    "cambia_questa_password",
    "cambia_questo_segreto_lungo_e_casuale",
    "nexus123",
    "test-token",
    "secret",
})

#: Prefissi che indicano un segreto generato al volo dal processo.
EPHEMERAL_SECRET_PREFIXES = ("change-me-",)

MIN_SECRET_LENGTH = 24
MIN_PASSWORD_LENGTH = 12

#: Durata massima ammessa per una sessione privilegiata (AUD0-BE-AUTH-003).
MAX_SESSION_HOURS_HARDENED = 24

JWT_ISSUER = "nexus-backend"
JWT_AUDIENCE = "nexus-dashboard"


class SecurityPreflightError(RuntimeError):
    """Sollevata quando la configurazione non è sicura per l'ambiente scelto."""

    def __init__(self, failures: Iterable[str]):
        self.failures = list(failures)
        joined = "\n  - ".join(self.failures)
        super().__init__(
            "NEXUS security preflight FAILED — il processo non può avviarsi:\n  - "
            + joined
        )


def normalize_environment(raw: Optional[str]) -> str:
    """Normalizza NEXUS_ENV su un ambiente canonico.

    Un valore sconosciuto viene trattato come LIVE: l'impostazione di default
    deve essere la più restrittiva, non la più permissiva (fail-safe).
    """
    value = (raw or "").strip().upper()
    if not value:
        return ENV_DEVELOPMENT
    aliases = {
        "DEV": ENV_DEVELOPMENT,
        "LOCAL": ENV_DEVELOPMENT,
        "TEST": ENV_DEVELOPMENT,
        "CI": ENV_DEVELOPMENT,
        "SIM": ENV_SIMULATION,
        "STAGING": ENV_PAPER,
        "PROD": ENV_LIVE,
        "PRODUCTION": ENV_LIVE,
    }
    value = aliases.get(value, value)
    return value if value in VALID_ENVIRONMENTS else ENV_LIVE


def is_hardened(environment: str) -> bool:
    return environment in HARDENED_ENVIRONMENTS


def _is_placeholder(value: Optional[str]) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    if not normalized:
        return True
    if normalized in FORBIDDEN_SECRET_VALUES:
        return True
    return any(normalized.startswith(prefix) for prefix in EPHEMERAL_SECRET_PREFIXES)


def _weak_secret(value: Optional[str], minimum: int) -> bool:
    return value is None or len(value.strip()) < minimum


def _looks_like_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value.strip()))


@dataclass
class PreflightResult:
    """Esito del preflight: fallimenti bloccanti + warning non bloccanti."""

    environment: str
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def raise_for_status(self) -> None:
        if self.failures:
            raise SecurityPreflightError(self.failures)


def run_preflight(
    *,
    environment: str,
    bridge_token: Optional[str],
    admin_user: Optional[str],
    admin_password: Optional[str],
    jwt_secret: Optional[str],
    jwt_secret_from_env: bool,
    jwt_hours: int,
    license_mode: Optional[str],
    cookie_secure: bool,
    db_path: Optional[str],
    coach_actions_enabled: bool,
) -> PreflightResult:
    """Valuta la configurazione di avvio.

    In DEVELOPMENT/SIMULATION i problemi sono warning: lo sviluppo locale resta
    possibile. In DEMO/PAPER/LIVE ogni problema è bloccante.
    """
    result = PreflightResult(environment=environment)
    hardened = is_hardened(environment)
    sink = result.failures if hardened else result.warnings

    if _is_placeholder(bridge_token):
        sink.append(
            "NEXUS_BRIDGE_TOKEN è assente o usa il valore di esempio pubblico. "
            "Genera un token casuale: python -c \"import secrets;print(secrets.token_urlsafe(48))\""
        )
    elif _weak_secret(bridge_token, MIN_SECRET_LENGTH):
        sink.append(
            f"NEXUS_BRIDGE_TOKEN è più corto di {MIN_SECRET_LENGTH} caratteri."
        )

    if _is_placeholder(admin_password):
        sink.append(
            "NEXUS_ADMIN_PASSWORD è assente o usa un valore di default noto."
        )
    elif _weak_secret(admin_password, MIN_PASSWORD_LENGTH):
        sink.append(
            f"NEXUS_ADMIN_PASSWORD è più corta di {MIN_PASSWORD_LENGTH} caratteri."
        )

    if _is_placeholder(admin_user):
        sink.append(
            "NEXUS_ADMIN_USER usa il valore di default 'admin'. Imposta "
            "l'identità email-like attesa dalla dashboard React."
        )
    elif hardened and not _looks_like_email(admin_user or ""):
        # AUD0-DEP-003: README/render.yaml/.env.example divergevano sul formato.
        result.warnings.append(
            "NEXUS_ADMIN_USER non è un indirizzo email: la dashboard React "
            "presenta il campo come email. Allinea README, .env.example e render.yaml."
        )

    if not jwt_secret_from_env:
        sink.append(
            "NEXUS_JWT_SECRET non è impostato: il backend genererebbe un segreto "
            "effimero, invalidando ogni sessione a ogni riavvio."
        )
    elif _is_placeholder(jwt_secret):
        sink.append("NEXUS_JWT_SECRET usa un valore placeholder.")
    elif _weak_secret(jwt_secret, MIN_SECRET_LENGTH):
        sink.append(
            f"NEXUS_JWT_SECRET è più corto di {MIN_SECRET_LENGTH} caratteri."
        )

    if jwt_hours > MAX_SESSION_HOURS_HARDENED:
        sink.append(
            f"NEXUS_JWT_HOURS={jwt_hours} supera il massimo di "
            f"{MAX_SESSION_HOURS_HARDENED}h per una sessione privilegiata."
        )

    if (license_mode or "").strip().lower() != "strict":
        sink.append(
            "NEXUS_LICENSE_MODE non è 'strict': in questo stato ogni chiave di "
            "licenza viene accettata e l'enforcement è solo cosmetico."
        )

    if not cookie_secure:
        sink.append(
            "NEXUS_COOKIE_SECURE=false: il cookie di sessione viaggerebbe in chiaro."
        )

    if coach_actions_enabled:
        # AUD0-AI-001: l'AI non deve poter mutare lo stato di trading.
        sink.append(
            "NEXUS_COACH_ALLOW_ACTIONS è abilitato: l'AI Coach non può avere "
            "autorità di esecuzione in un ambiente non di sviluppo."
        )

    if hardened and db_path and not os.path.isabs(db_path):
        # AUD0-DB-015: il volume persistente è montato su un path assoluto.
        result.failures.append(
            f"NEXUS_DB_PATH='{db_path}' non è assoluto: il database non "
            "risiederebbe sul volume persistente."
        )

    return result


# --------------------------------------------------------------------------- #
# CSRF — double-submit token legato alla sessione (AUD0-SEC-008)
# --------------------------------------------------------------------------- #
CSRF_COOKIE = "nexus_csrf"
CSRF_HEADER = "x-nexus-csrf"

#: Metodi che non modificano stato: esenti dal controllo CSRF.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def make_csrf_token(session_id: str, secret: str) -> str:
    """Token CSRF derivato dal session id: non richiede storage lato server."""
    digest = hmac.new(secret.encode(), session_id.encode(), hashlib.sha256)
    return digest.hexdigest()


def csrf_token_valid(session_id: str, secret: str, presented: Optional[str]) -> bool:
    if not presented:
        return False
    return hmac.compare_digest(make_csrf_token(session_id, secret), presented)


def origin_allowed(origin: Optional[str], allowed: Iterable[str]) -> bool:
    """Verifica Origin/Referer contro una allow-list esplicita.

    Una richiesta senza Origin (client non-browser, es. curl o EA) non è un
    vettore CSRF: il browser invia sempre l'header sulle richieste cross-site.
    """
    if not origin:
        return True
    allowed_set = {a.rstrip("/") for a in allowed if a}
    if not allowed_set:
        return True
    return origin.rstrip("/") in allowed_set


# --------------------------------------------------------------------------- #
# Rate limiting login (AUD0-SEC-006)
# --------------------------------------------------------------------------- #
class RateLimiter:
    """Finestra scorrevole in memoria, per-chiave.

    In-process è sufficiente per il modello single-node attuale. Con più
    repliche va sostituito da uno store condiviso (OD-009 nel master doc).
    """

    def __init__(self, max_attempts: int = 8, window_seconds: int = 300,
                 lockout_seconds: int = 900):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._attempts: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}

    def _now(self) -> float:
        return time.time()

    def retry_after(self, key: str) -> int:
        """Secondi rimanenti di lockout, 0 se la chiave non è bloccata."""
        until = self._locked_until.get(key)
        if not until:
            return 0
        remaining = int(until - self._now())
        if remaining <= 0:
            self._locked_until.pop(key, None)
            self._attempts.pop(key, None)
            return 0
        return remaining

    def register_failure(self, key: str) -> int:
        now = self._now()
        window = self._attempts.setdefault(key, [])
        window[:] = [t for t in window if now - t < self.window_seconds]
        window.append(now)
        if len(window) >= self.max_attempts:
            self._locked_until[key] = now + self.lockout_seconds
            return self.lockout_seconds
        return 0

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)
        self._locked_until.pop(key, None)


# --------------------------------------------------------------------------- #
# Revoca di sessione (AUD0-AUTH-001, NEXUS-SEC-004)
# --------------------------------------------------------------------------- #
class SessionRegistry:
    """Registro dei `jti` revocati, con scadenza automatica.

    Il logout aggiunge il `jti` corrente; `revoke_all` invalida ogni sessione
    emessa prima di un istante dato (controllo d'emergenza spec A3.6 §39).
    """

    def __init__(self):
        self._revoked: dict[str, float] = {}
        self._revoked_before: float = 0.0

    def revoke(self, jti: str, expires_at: float) -> None:
        if jti:
            self._revoked[jti] = expires_at

    def revoke_all(self, issued_before: Optional[float] = None) -> None:
        self._revoked_before = issued_before if issued_before else time.time()

    def is_revoked(self, jti: Optional[str], issued_at: Optional[float]) -> bool:
        now = time.time()
        # pulizia opportunistica delle voci scadute
        for key, exp in list(self._revoked.items()):
            if exp and exp < now:
                self._revoked.pop(key, None)
        if jti and jti in self._revoked:
            return True
        if issued_at and self._revoked_before and issued_at < self._revoked_before:
            return True
        return False


def new_session_id() -> str:
    return secrets.token_urlsafe(24)
