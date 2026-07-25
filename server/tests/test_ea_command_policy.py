"""Contratto dei comandi EA e tetti di rischio server-side.

Copre AUD0-CMD-001..004, AUD0-BE-CMD-005..008, AUD0-RISK-001/002 e
AUD0-VAL-002.
"""
from __future__ import annotations

import pytest

import nexus_policy as policy


# --------------------------------------------------------------------------- #
# Target obbligatorio — AUD0-CMD-002 / AUD0-BE-CMD-005
# --------------------------------------------------------------------------- #
VALID_TARGET = {"account_id": "123456", "symbol": "XAUUSD", "magic": 20260101}


def test_comando_senza_target_viene_rifiutato():
    with pytest.raises(policy.CommandValidationError):
        policy.build_command(action="pause", target=None)
    with pytest.raises(policy.CommandValidationError):
        policy.build_command(action="pause", target={"symbol": "XAUUSD"})
    with pytest.raises(policy.CommandValidationError):
        policy.build_command(action="pause", target={"account_id": "1"})


def test_comando_con_target_valido_passa():
    cmd = policy.build_command(action="pause", target=VALID_TARGET)
    assert cmd["target"]["account_id"] == "123456"
    assert cmd["target"]["symbol"] == "XAUUSD"
    assert cmd["action"] == "pause"


def test_il_target_riconosce_solo_la_propria_istanza():
    target = policy.validate_target(VALID_TARGET)
    assert target.matches(account_id="123456", symbol="XAUUSD", magic=20260101)
    assert not target.matches(account_id="999999", symbol="XAUUSD", magic=20260101)
    assert not target.matches(account_id="123456", symbol="EURUSD", magic=20260101)
    assert not target.matches(account_id="123456", symbol="XAUUSD", magic=1)


def test_campi_target_malformati_rifiutati():
    with pytest.raises(policy.CommandValidationError):
        policy.validate_target({"account_id": "a b c", "symbol": "XAUUSD"})
    with pytest.raises(policy.CommandValidationError):
        policy.validate_target({"account_id": "1", "symbol": "XAU USD"})
    with pytest.raises(policy.CommandValidationError):
        policy.validate_target({"account_id": "1", "symbol": "X", "magic": "non-numerico"})


# --------------------------------------------------------------------------- #
# Conferma esplicita — AUD0-CMD-004 / AUD0-FE-CMD-002
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("action", [
    "close_all", "close_position", "partial_close",
    "reset_daily", "reset_protections", "reset_anti_revenge", "resume",
])
def test_azioni_ad_alto_impatto_richiedono_conferma(action):
    assert policy.requires_confirmation(action)
    payload = {"ticket": 1, "volume": 0.1}
    with pytest.raises(policy.CommandValidationError):
        policy.build_command(action=action, target=VALID_TARGET,
                             payload=payload, reason="motivo", confirmed=False)


def test_azioni_di_routine_non_richiedono_conferma():
    assert not policy.requires_confirmation("pause")
    assert not policy.requires_confirmation("resync_trades")
    cmd = policy.build_command(action="pause", target=VALID_TARGET)
    assert cmd["risk_class"] == policy.RISK_CLASS_ROUTINE


def test_azione_confermata_richiede_una_motivazione():
    with pytest.raises(policy.CommandValidationError):
        policy.build_command(action="close_all", target=VALID_TARGET,
                             confirmed=True, reason="")
    cmd = policy.build_command(action="close_all", target=VALID_TARGET,
                               confirmed=True, reason="drawdown oltre soglia")
    assert cmd["reason"] == "drawdown oltre soglia"


def test_il_testo_di_conferma_dichiara_tutti_gli_effetti():
    # AUD0-FE-CMD-003: la dialog diceva solo "Trades-today -> 0", omettendo la
    # riscrittura della baseline di drawdown.
    effetti = " ".join(policy.confirmation_text("reset_daily")).lower()
    assert "drawdown" in effetti
    assert "trade giornalieri" in effetti

    effetti_close = " ".join(policy.confirmation_text("close_all")).lower()
    assert "non è reversibile" in effetti_close


# --------------------------------------------------------------------------- #
# Validazione payload — AUD0-API-002 / AUD0-WEB-007
# --------------------------------------------------------------------------- #
def test_close_position_richiede_un_ticket_valido():
    with pytest.raises(policy.CommandValidationError):
        policy.build_command(action="close_position", target=VALID_TARGET,
                             confirmed=True, reason="motivazione di test", payload={})
    with pytest.raises(policy.CommandValidationError):
        policy.build_command(action="close_position", target=VALID_TARGET,
                             confirmed=True, reason="motivazione di test", payload={"ticket": -1})
    cmd = policy.build_command(action="close_position", target=VALID_TARGET,
                               confirmed=True, reason="motivazione di test", payload={"ticket": 42})
    assert cmd["payload"] == {"ticket": 42}


def test_partial_close_valida_volume():
    with pytest.raises(policy.CommandValidationError):
        policy.build_command(action="partial_close", target=VALID_TARGET,
                             confirmed=True, reason="motivazione di test", payload={"ticket": 1})
    with pytest.raises(policy.CommandValidationError):
        policy.build_command(action="partial_close", target=VALID_TARGET,
                             confirmed=True, reason="motivazione di test",
                             payload={"ticket": 1, "volume": 0})
    cmd = policy.build_command(action="partial_close", target=VALID_TARGET,
                               confirmed=True, reason="motivazione di test",
                               payload={"ticket": 1, "volume": 0.5})
    assert cmd["payload"]["volume"] == 0.5


def test_azione_sconosciuta_rifiutata():
    with pytest.raises(policy.CommandValidationError):
        policy.build_command(action="rm_-rf", target=VALID_TARGET)


# --------------------------------------------------------------------------- #
# TTL con limite superiore — AUD0-VAL-002
# --------------------------------------------------------------------------- #
def test_ttl_ha_un_massimo():
    cmd = policy.build_command(action="pause", target=VALID_TARGET,
                               ttl_seconds=10 ** 9)
    assert cmd["ttl_seconds"] == policy.MAX_TTL_SECONDS


def test_ttl_ha_un_minimo():
    cmd = policy.build_command(action="pause", target=VALID_TARGET, ttl_seconds=1)
    assert cmd["ttl_seconds"] == policy.MIN_TTL_SECONDS


def test_ttl_di_default_dal_contratto():
    cmd = policy.build_command(action="close_all", target=VALID_TARGET,
                               confirmed=True, reason="motivazione di test")
    assert cmd["ttl_seconds"] == policy.EA_ACTIONS["close_all"]["ttl"]


# --------------------------------------------------------------------------- #
# Stati terminali — AUD0-FE-CMD-001 / NXS-FE-TRUST-002
# --------------------------------------------------------------------------- #
def test_leased_non_e_uno_stato_terminale():
    # "consegnato" non prova l'esecuzione da parte del broker.
    assert policy.CMD_LEASED not in policy.EA_TERMINAL_STATUSES
    assert policy.CMD_RUNNING not in policy.EA_TERMINAL_STATUSES
    assert policy.CMD_SUCCEEDED in policy.EA_TERMINAL_STATUSES
    assert policy.CMD_FAILED_FINAL in policy.EA_TERMINAL_STATUSES


def test_ack_accetta_solo_stati_dichiarabili_dall_ea():
    assert policy.CMD_EXPIRED not in policy.EA_ACK_STATUSES
    assert policy.CMD_CANCELLED not in policy.EA_ACK_STATUSES
    assert policy.CMD_SUCCEEDED in policy.EA_ACK_STATUSES


# --------------------------------------------------------------------------- #
# Tetti di rischio — AUD0-RISK-001 / AUD0-AI-002 / AUD0-AI-003
# --------------------------------------------------------------------------- #
def test_moltiplicatore_10x_rifiutato_in_produzione():
    with pytest.raises(policy.RiskPolicyDenied):
        policy.enforce_cap("strategy_multiplier", 10.0, hardened=True)
    # In sviluppo resta possibile per la ricerca.
    assert policy.enforce_cap("strategy_multiplier", 10.0, hardened=False) == 10.0


def test_rischio_percentuale_limitato_in_produzione():
    with pytest.raises(policy.RiskPolicyDenied):
        policy.enforce_cap("risk_percent", 10.0, hardened=True)
    assert policy.enforce_cap("risk_percent", 1.0, hardened=True) == 1.0


def test_valori_non_numerici_o_negativi_rifiutati():
    for bad in ("abc", None, -1.0, float("inf"), float("nan")):
        with pytest.raises(policy.RiskPolicyDenied):
            policy.enforce_cap("risk_percent", bad, hardened=True)


def test_il_valore_oltre_soglia_non_viene_troncato_in_silenzio():
    # AUD0-FE-OPT-006: il clamp silenzioso nascondeva all'operatore che il
    # valore applicato non era quello richiesto.
    with pytest.raises(policy.RiskPolicyDenied) as exc:
        policy.enforce_cap("risk_percent", 5.0, hardened=True)
    assert exc.value.requested == 5.0
    assert exc.value.cap == policy.HARD_CAPS_HARDENED["risk_percent"]


def test_i_tetti_di_produzione_sono_piu_stretti_di_quelli_di_sviluppo():
    prod = policy.caps_for(True)
    dev = policy.caps_for(False)
    for field in prod:
        assert prod[field] <= dev[field], field
