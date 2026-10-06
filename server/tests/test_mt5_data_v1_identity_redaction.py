"""Test per identity.py e redaction.py: alias deterministico senza login in
chiaro, mappa privata isolata per test, redazione del login nei campi
testuali liberi (MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1 sez.9/18)."""
import pytest

from mt5_data_v1 import identity, redaction


@pytest.fixture(autouse=True)
def _isolated_private_map(tmp_path, monkeypatch):
    monkeypatch.setattr(identity, "PRIVATE_MAP_PATH", tmp_path / "account_identity_map.json")
    yield


def test_derive_account_id_is_deterministic():
    a1 = identity.derive_account_id("123456", "XMGlobal", "XMGlobal-Real7")
    a2 = identity.derive_account_id("123456", "XMGlobal", "XMGlobal-Real7")
    assert a1 == a2
    assert identity.is_valid_account_id(a1)


def test_derive_account_id_differs_by_login():
    a1 = identity.derive_account_id("123456", "XMGlobal", "XMGlobal-Real7")
    a2 = identity.derive_account_id("654321", "XMGlobal", "XMGlobal-Real7")
    assert a1 != a2


def test_account_id_never_contains_raw_login():
    account_id = identity.derive_account_id("9999999", "Broker", "Server")
    assert "9999999" not in account_id


def test_register_account_identity_persists_private_mapping():
    account_id = identity.register_account_identity("111111", "Broker", "Server")
    mapping = identity._load_private_map()
    assert mapping[account_id]["login"] == "111111"


def test_is_valid_account_id_rejects_malformed():
    assert not identity.is_valid_account_id("acct_short")
    assert not identity.is_valid_account_id("not_prefixed_at_all_0123456789abcd")
    assert not identity.is_valid_account_id("acct_ZZZZZZZZZZZZZZZZ")  # non hex


def test_redact_bundle_replaces_login_in_free_text_fields():
    account_id = identity.register_account_identity("8675309", "Broker", "Server")
    bundle = {"deals": [{"deal_ticket": 1, "comment": "deposit ref 8675309 processed"}]}
    redacted = redaction.redact_bundle(bundle, account_id)
    assert "8675309" not in redacted["deals"][0]["comment"]
    assert redaction.REDACTED_PLACEHOLDER in redacted["deals"][0]["comment"]


def test_redact_bundle_noop_when_no_login_registered():
    unknown_account_id = identity.derive_account_id("never_registered", "Broker", "Server")
    bundle = {"deals": [{"comment": "nothing sensitive here"}]}
    redacted = redaction.redact_bundle(bundle, unknown_account_id)
    assert redacted == bundle


def test_redact_bundle_does_not_mutate_original():
    account_id = identity.register_account_identity("424242", "Broker", "Server")
    bundle = {"deals": [{"comment": "acct 424242"}]}
    redaction.redact_bundle(bundle, account_id)
    assert bundle["deals"][0]["comment"] == "acct 424242"  # originale intatto
