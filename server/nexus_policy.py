"""Risk policy e contratto canonico dei comandi EA.

Copre i finding dell'audit master:

* AUD0-RISK-001 / AUD0-AI-002 / AUD0-AI-003 / NXS-BE-RISK-001
  — moltiplicatori di rischio fino a 10x raggiungibili da dashboard e Coach.
* AUD0-CMD-001 / AUD0-CMD-002 / AUD0-BE-CMD-005..008 / NXS-BE-CMD-001..003
  — comandi EA senza target, senza scadenza, consumati al polling.
* AUD0-CMD-004 — comandi distruttivi senza target, motivazione, idempotenza.
* NEXUS-RISK-001 — nessun percorso può bypassare la valutazione di policy.

Il modulo è puro (nessun I/O, nessuna dipendenza da FastAPI) così da essere
testabile in isolamento.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

SCHEMA_VERSION = 1

# --------------------------------------------------------------------------- #
# Risk policy
# --------------------------------------------------------------------------- #
#: Tetti "hard" applicati lato server. Sono limiti di *policy di produzione*,
#: distinti dai limiti tecnici dello schema (AUD0-FE-SET-001): lo schema
#: accetta valori più larghi, la policy no.
HARD_CAPS_HARDENED = {
    "risk_percent": 2.0,
    "strategy_multiplier": 1.5,
    "max_lot": 5.0,
    "max_trades_per_day": 60,
    "max_concurrent": 8,
    "max_daily_dd_pct": 10.0,
}

#: In sviluppo i tetti restano ampi per non ostacolare la ricerca, ma non
#: illimitati: 10x resta il massimo assoluto ovunque.
HARD_CAPS_DEVELOPMENT = {
    "risk_percent": 10.0,
    "strategy_multiplier": 10.0,
    "max_lot": 100.0,
    "max_trades_per_day": 500,
    "max_concurrent": 40,
    "max_daily_dd_pct": 100.0,
}


class RiskPolicyDenied(ValueError):
    """La richiesta viola un tetto non superabile."""

    def __init__(self, field: str, requested: Any, cap: Any):
        self.field = field
        self.requested = requested
        self.cap = cap
        super().__init__(
            f"RISK_POLICY_DENIED: {field}={requested} supera il tetto di produzione {cap}"
        )


def caps_for(environment_hardened: bool) -> dict:
    return dict(HARD_CAPS_HARDENED if environment_hardened else HARD_CAPS_DEVELOPMENT)


def enforce_cap(field: str, value: Any, *, hardened: bool) -> float:
    """Rifiuta (non tronca silenziosamente) i valori oltre il tetto.

    L'audit segnalava che il clamping silenzioso nasconde all'operatore che la
    richiesta non è stata applicata come inserita (AUD0-FE-OPT-006).
    """
    caps = caps_for(hardened)
    if field not in caps:
        raise KeyError(f"unknown risk field: {field}")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise RiskPolicyDenied(field, value, caps[field]) from exc
    if numeric != numeric or numeric in (float("inf"), float("-inf")):
        raise RiskPolicyDenied(field, value, caps[field])
    if numeric < 0:
        raise RiskPolicyDenied(field, value, caps[field])
    if numeric > caps[field]:
        raise RiskPolicyDenied(field, numeric, caps[field])
    return numeric


# --------------------------------------------------------------------------- #
# Contratto comandi EA
# --------------------------------------------------------------------------- #
#: Classi di rischio: determinano se serve conferma esplicita dell'operatore.
RISK_CLASS_ROUTINE = "ROUTINE"
RISK_CLASS_TRADING = "TRADING"
RISK_CLASS_PROTECTION = "PROTECTION"

#: Registry canonico delle azioni EA. Una sola definizione condivisa da tutte
#: le rotte (AUD0-CMD-003, AUD0-BE-CMD-008, NXS-BE-ROUTE-014).
EA_ACTIONS: dict[str, dict] = {
    "pause":              {"risk_class": RISK_CLASS_ROUTINE,    "confirm": False, "ttl": 300},
    "resume":             {"risk_class": RISK_CLASS_TRADING,    "confirm": True,  "ttl": 300},
    "resync_trades":      {"risk_class": RISK_CLASS_ROUTINE,    "confirm": False, "ttl": 900},
    "close_position":     {"risk_class": RISK_CLASS_TRADING,    "confirm": True,  "ttl": 120},
    "partial_close":      {"risk_class": RISK_CLASS_TRADING,    "confirm": True,  "ttl": 120},
    "close_all":          {"risk_class": RISK_CLASS_TRADING,    "confirm": True,  "ttl": 120},
    "reset_anti_revenge": {"risk_class": RISK_CLASS_PROTECTION, "confirm": True,  "ttl": 300},
    "reset_daily":        {"risk_class": RISK_CLASS_PROTECTION, "confirm": True,  "ttl": 300},
    "reset_protections":  {"risk_class": RISK_CLASS_PROTECTION, "confirm": True,  "ttl": 300},
}

#: Testo di conferma generato dal contratto, non scritto a mano nella UI
#: (AUD0-FE-CMD-003: la dialog sottostimava gli effetti di reset_daily).
ACTION_EFFECTS: dict[str, tuple[str, ...]] = {
    "pause": ("L'EA smette di aprire nuove posizioni.",),
    "resume": ("L'EA riprende ad aprire nuove posizioni.",),
    "resync_trades": ("L'EA rinvia lo storico dei trade chiusi.",),
    "close_position": ("Chiude la posizione indicata al prezzo di mercato.",),
    "partial_close": ("Chiude parte del volume della posizione indicata.",),
    "close_all": (
        "Chiude TUTTE le posizioni NEXUS sul simbolo del target.",
        "L'operazione non è reversibile.",
    ),
    "reset_anti_revenge": (
        "Azzera il contatore di perdite consecutive.",
        "Rimuove il blocco anti-revenge attivo.",
    ),
    "reset_daily": (
        "Azzera il contatore di trade giornalieri.",
        "Riporta la baseline di drawdown giornaliero al balance corrente: "
        "la protezione di perdita giornaliera riparte da zero.",
    ),
    "reset_protections": (
        "Azzera Equity Stop Loss, Daily Profit Target e la pausa automatica.",
        "L'EA può riprendere a operare subito dopo un evento di protezione.",
    ),
}

#: Stati terminali e non terminali del comando (spec A3.2).
CMD_PENDING = "PENDING"
CMD_LEASED = "LEASED"
CMD_RUNNING = "RUNNING"
CMD_SUCCEEDED = "SUCCEEDED"
CMD_FAILED_RETRYABLE = "FAILED_RETRYABLE"
CMD_FAILED_FINAL = "FAILED_FINAL"
CMD_EXPIRED = "EXPIRED"
CMD_CANCELLED = "CANCELLED"

EA_COMMAND_STATUSES = frozenset({
    CMD_PENDING, CMD_LEASED, CMD_RUNNING, CMD_SUCCEEDED,
    CMD_FAILED_RETRYABLE, CMD_FAILED_FINAL, CMD_EXPIRED, CMD_CANCELLED,
})

#: Solo questi stati provano che il broker ha eseguito. `LEASED` (ex
#: `DELIVERED`) prova soltanto che l'EA ha ricevuto il comando
#: (AUD0-CMD-001, AUD0-FE-CMD-001, NXS-FE-TRUST-002).
EA_TERMINAL_STATUSES = frozenset({
    CMD_SUCCEEDED, CMD_FAILED_FINAL, CMD_EXPIRED, CMD_CANCELLED,
})

#: Stati che l'EA può dichiarare in ACK.
EA_ACK_STATUSES = frozenset({
    CMD_RUNNING, CMD_SUCCEEDED, CMD_FAILED_RETRYABLE, CMD_FAILED_FINAL,
})

MAX_ATTEMPTS = 3
LEASE_SECONDS = 45
MAX_TTL_SECONDS = 3600      # AUD0-VAL-002: tetto superiore mancante
MIN_TTL_SECONDS = 30

_ID_RE = re.compile(r"^[A-Za-z0-9._:\-]{1,64}$")


class CommandValidationError(ValueError):
    pass


@dataclass(frozen=True)
class EaTarget:
    """Tupla di target immutabile richiesta da ogni comando EA.

    AUD0-CMD-002 / AUD0-BE-CMD-005: il polling selezionava il comando globale
    più vecchio, senza filtrare per istanza.
    """

    account_id: str
    symbol: str
    magic: Optional[int] = None
    instance_id: Optional[str] = None
    environment: Optional[str] = None

    def as_dict(self) -> dict:
        out = {"account_id": self.account_id, "symbol": self.symbol}
        if self.magic is not None:
            out["magic"] = self.magic
        if self.instance_id:
            out["instance_id"] = self.instance_id
        if self.environment:
            out["environment"] = self.environment
        return out

    def matches(self, *, account_id: str, symbol: str,
                magic: Optional[int] = None) -> bool:
        """Un comando è consegnabile solo all'istanza esattamente indicata."""
        if str(self.account_id) != str(account_id):
            return False
        if str(self.symbol) != str(symbol):
            return False
        if self.magic is not None and magic is not None and int(self.magic) != int(magic):
            return False
        return True


def validate_action(value: Any) -> str:
    action = str(value or "").strip().lower()
    if action not in EA_ACTIONS:
        raise CommandValidationError(
            f"azione non valida: {value!r} (ammesse: {sorted(EA_ACTIONS)})"
        )
    return action


def validate_target(raw: Any) -> EaTarget:
    if not isinstance(raw, dict):
        raise CommandValidationError(
            "target obbligatorio: {account_id, symbol, [magic], [instance_id]}"
        )
    account_id = str(raw.get("account_id") or "").strip()
    symbol = str(raw.get("symbol") or "").strip()
    if not account_id or not _ID_RE.match(account_id):
        raise CommandValidationError("target.account_id mancante o non valido")
    if not symbol or not _ID_RE.match(symbol):
        raise CommandValidationError("target.symbol mancante o non valido")

    magic_raw = raw.get("magic")
    magic = None
    if magic_raw not in (None, ""):
        try:
            magic = int(magic_raw)
        except (TypeError, ValueError) as exc:
            raise CommandValidationError("target.magic deve essere un intero") from exc

    instance_id = raw.get("instance_id")
    if instance_id not in (None, ""):
        instance_id = str(instance_id)
        if not _ID_RE.match(instance_id):
            raise CommandValidationError("target.instance_id non valido")
    else:
        instance_id = None

    environment = raw.get("environment")
    environment = str(environment).upper() if environment else None

    return EaTarget(account_id=account_id, symbol=symbol, magic=magic,
                    instance_id=instance_id, environment=environment)


def validate_ttl(action: str, raw: Any) -> int:
    """TTL con minimo e, soprattutto, massimo (AUD0-VAL-002)."""
    default = EA_ACTIONS[action]["ttl"]
    if raw in (None, ""):
        return default
    try:
        ttl = int(raw)
    except (TypeError, ValueError) as exc:
        raise CommandValidationError("ttl_seconds deve essere un intero") from exc
    return max(MIN_TTL_SECONDS, min(MAX_TTL_SECONDS, ttl))


#: Limiti per i comandi LocalBridge (AUD0-VAL-002, AUD0-VAL-003).
BRIDGE_MIN_TTL_SECONDS = 60
BRIDGE_MAX_TTL_SECONDS = 6 * 3600
BRIDGE_DEFAULT_TTL_SECONDS = 3600
BRIDGE_MAX_ATTEMPTS = 5


def validate_ttl_bridge(raw: Any) -> int:
    """TTL di un comando LocalBridge, con minimo E massimo.

    AUD0-VAL-002: l'implementazione precedente calcolava `max(60, ttl)`, cioè
    imponeva solo un pavimento. Un chiamante poteva chiedere una vita utile
    arbitrariamente lunga per un'operazione distruttiva.
    """
    if raw in (None, ""):
        return BRIDGE_DEFAULT_TTL_SECONDS
    try:
        ttl = int(raw)
    except (TypeError, ValueError):
        return BRIDGE_DEFAULT_TTL_SECONDS
    return max(BRIDGE_MIN_TTL_SECONDS, min(BRIDGE_MAX_TTL_SECONDS, ttl))


def validate_max_attempts(raw: Any) -> int:
    """Numero di tentativi, con tetto superiore (AUD0-VAL-003)."""
    if raw in (None, ""):
        return MAX_ATTEMPTS
    try:
        attempts = int(raw)
    except (TypeError, ValueError):
        return MAX_ATTEMPTS
    return max(1, min(BRIDGE_MAX_ATTEMPTS, attempts))


def requires_confirmation(action: str) -> bool:
    return bool(EA_ACTIONS[validate_action(action)]["confirm"])


def confirmation_text(action: str) -> list[str]:
    """Effetti dichiarati, generati dal contratto canonico."""
    return list(ACTION_EFFECTS.get(validate_action(action), ()))


def validate_payload(action: str, payload: Any) -> dict:
    """Validazione tipata per azione: niente oggetti arbitrari (AUD0-API-002)."""
    payload = payload if isinstance(payload, dict) else {}
    action = validate_action(action)
    clean: dict[str, Any] = {}

    if action in ("close_position", "partial_close"):
        ticket = payload.get("ticket")
        try:
            ticket_int = int(ticket)
        except (TypeError, ValueError) as exc:
            raise CommandValidationError(f"{action}: payload.ticket obbligatorio") from exc
        if ticket_int <= 0:
            raise CommandValidationError(f"{action}: payload.ticket deve essere positivo")
        clean["ticket"] = ticket_int

    if action == "partial_close":
        volume = payload.get("volume")
        try:
            volume_f = float(volume)
        except (TypeError, ValueError) as exc:
            raise CommandValidationError("partial_close: payload.volume obbligatorio") from exc
        if not (0 < volume_f <= 1000):
            raise CommandValidationError("partial_close: volume fuori range (0, 1000]")
        clean["volume"] = volume_f

    return clean


def validate_reason(raw: Any, *, required: bool) -> str:
    """Motivazione operatore per le azioni ad alto impatto (AUD0-AUDIT-001)."""
    reason = str(raw or "").strip()
    if required and len(reason) < 3:
        raise CommandValidationError(
            "reason obbligatoria (minimo 3 caratteri) per questa azione"
        )
    return reason[:500]


def build_command(*, action: Any, target: Any, payload: Any = None,
                  reason: Any = None, ttl_seconds: Any = None,
                  confirmed: bool = False, idempotency_key: Any = None) -> dict:
    """Costruisce un comando canonico validato o solleva CommandValidationError."""
    action = validate_action(action)
    spec = EA_ACTIONS[action]
    ea_target = validate_target(target)
    clean_payload = validate_payload(action, payload)
    needs_confirm = bool(spec["confirm"])
    if needs_confirm and not confirmed:
        raise CommandValidationError(
            f"azione '{action}' richiede conferma esplicita: "
            f"invia confirm=true. Effetti: {' '.join(confirmation_text(action))}"
        )
    clean_reason = validate_reason(reason, required=needs_confirm)
    ttl = validate_ttl(action, ttl_seconds)

    key = idempotency_key
    if key not in (None, ""):
        key = str(key)
        if not _ID_RE.match(key):
            raise CommandValidationError("idempotency_key non valida")
    else:
        key = None

    return {
        "schema_version": SCHEMA_VERSION,
        "action": action,
        "risk_class": spec["risk_class"],
        "target": ea_target.as_dict(),
        "payload": clean_payload,
        "reason": clean_reason,
        "ttl_seconds": ttl,
        "idempotency_key": key,
    }
