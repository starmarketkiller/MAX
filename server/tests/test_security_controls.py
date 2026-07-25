"""Test dei controlli di sicurezza introdotti dalla remediazione dell'audit.

Ogni test cita il finding che impedisce di regredire.
"""
from __future__ import annotations

import pytest

import nexus_security as sec


# --------------------------------------------------------------------------- #
# Preflight fail-closed — AUD0-SEC-001 / AUD0-SEC-004 / NEXUS-SEC-001
# --------------------------------------------------------------------------- #
SAFE_CONFIG = dict(
    bridge_token="k" * 48,
    admin_user="operatore@esempio.it",
    admin_password="P4ssword-Lunga-Abbastanza",
    jwt_secret="s" * 48,
    jwt_secret_from_env=True,
    jwt_hours=12,
    license_mode="strict",
    cookie_secure=True,
    db_path="/data/nexus.db",
    coach_actions_enabled=False,
)


def preflight(environment="LIVE", **overrides):
    config = dict(SAFE_CONFIG)
    config.update(overrides)
    return sec.run_preflight(environment=environment, **config)


def test_configurazione_sicura_passa_in_live():
    assert preflight().ok


@pytest.mark.parametrize("field,value", [
    ("bridge_token", "NEXUS_BRIDGE_TOKEN_2026"),
    ("bridge_token", ""),
    ("admin_password", "admin"),
    ("admin_password", "cambia_questa_password"),
    ("admin_user", "admin"),
    ("jwt_secret", "cambia_questo_segreto_lungo_e_casuale"),
    ("license_mode", "open"),
    ("cookie_secure", False),
    ("coach_actions_enabled", True),
])
def test_valori_pericolosi_bloccano_avvio_live(field, value):
    result = preflight(**{field: value})
    assert not result.ok, f"{field}={value!r} avrebbe dovuto bloccare l'avvio"
    with pytest.raises(sec.SecurityPreflightError):
        result.raise_for_status()


def test_segreto_jwt_effimero_rifiutato():
    # AUD0-SEC-005: un segreto generato al volo invalida ogni sessione al riavvio.
    result = preflight(jwt_secret_from_env=False, jwt_secret="change-me-abc123")
    assert not result.ok


def test_sessione_troppo_lunga_rifiutata():
    # AUD0-SEC-002 / AUD0-BE-AUTH-003: il default era 720h (30 giorni).
    assert not preflight(jwt_hours=720).ok
    assert preflight(jwt_hours=24).ok


def test_in_sviluppo_i_problemi_sono_warning_non_errori():
    result = preflight(environment="DEVELOPMENT",
                       bridge_token="NEXUS_BRIDGE_TOKEN_2026",
                       admin_password="admin", license_mode="open")
    assert result.ok
    assert result.warnings


def test_ambiente_sconosciuto_e_trattato_come_live():
    # Fail-safe: un typo in NEXUS_ENV non deve disattivare i controlli.
    assert sec.normalize_environment("qualcosa-di-strano") == sec.ENV_LIVE
    assert sec.normalize_environment("") == sec.ENV_DEVELOPMENT
    assert sec.normalize_environment("production") == sec.ENV_LIVE
    assert sec.is_hardened(sec.ENV_LIVE)
    assert not sec.is_hardened(sec.ENV_DEVELOPMENT)


def test_db_path_relativo_rifiutato_in_produzione():
    # AUD0-DB-015: il volume persistente è montato su un percorso assoluto.
    assert not preflight(db_path="nexus.db").ok


# --------------------------------------------------------------------------- #
# CSRF — AUD0-SEC-008 / AUD0-BE-AUTH-007
# --------------------------------------------------------------------------- #
def test_token_csrf_legato_alla_sessione():
    secret = "segreto-di-firma"
    token_a = sec.make_csrf_token("sessione-a", secret)
    token_b = sec.make_csrf_token("sessione-b", secret)
    assert token_a != token_b
    assert sec.csrf_token_valid("sessione-a", secret, token_a)
    # Il token di un'altra sessione non è accettato.
    assert not sec.csrf_token_valid("sessione-a", secret, token_b)
    assert not sec.csrf_token_valid("sessione-a", secret, None)
    assert not sec.csrf_token_valid("sessione-a", secret, "")


def test_origin_allowlist():
    allowed = ["https://nexus.example", "https://alt.example/"]
    assert sec.origin_allowed("https://nexus.example", allowed)
    assert sec.origin_allowed("https://alt.example", allowed)
    assert not sec.origin_allowed("https://evil.example", allowed)
    # Nessun Origin = client non-browser: non è un vettore CSRF.
    assert sec.origin_allowed(None, allowed)
    # Allow-list vuota = nessun vincolo configurato.
    assert sec.origin_allowed("https://qualsiasi.example", [])


# --------------------------------------------------------------------------- #
# Rate limiting login — AUD0-SEC-006
# --------------------------------------------------------------------------- #
def test_login_viene_bloccato_dopo_troppi_tentativi():
    limiter = sec.RateLimiter(max_attempts=3, window_seconds=60, lockout_seconds=120)
    assert limiter.retry_after("ip|utente") == 0
    limiter.register_failure("ip|utente")
    limiter.register_failure("ip|utente")
    assert limiter.retry_after("ip|utente") == 0
    limiter.register_failure("ip|utente")   # terzo tentativo -> lockout
    assert limiter.retry_after("ip|utente") > 0
    # Un'altra identità non è coinvolta.
    assert limiter.retry_after("ip|altro") == 0


def test_login_riuscito_azzera_il_contatore():
    limiter = sec.RateLimiter(max_attempts=2, window_seconds=60, lockout_seconds=120)
    limiter.register_failure("k")
    limiter.reset("k")
    limiter.register_failure("k")
    assert limiter.retry_after("k") == 0


# --------------------------------------------------------------------------- #
# Revoca di sessione — AUD0-AUTH-001 / NEXUS-SEC-004
# --------------------------------------------------------------------------- #
def test_logout_revoca_il_token():
    import time
    registry = sec.SessionRegistry()
    assert not registry.is_revoked("jti-1", time.time())
    registry.revoke("jti-1", time.time() + 3600)
    assert registry.is_revoked("jti-1", time.time())
    assert not registry.is_revoked("jti-2", time.time())


def test_revoca_globale_invalida_le_sessioni_precedenti():
    import time
    registry = sec.SessionRegistry()
    issued_before = time.time() - 10
    registry.revoke_all()
    assert registry.is_revoked("qualsiasi", issued_before)
    # Una sessione emessa DOPO la revoca resta valida.
    assert not registry.is_revoked("nuova", time.time() + 10)
