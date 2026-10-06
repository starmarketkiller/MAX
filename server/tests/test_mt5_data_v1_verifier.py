"""Test per verifier.py: duplicate deal ids, chronologia, volume negativo,
account mismatch, hash corrotto (sez.18 della richiesta)."""
from mt5_data_v1 import identity, verifier

ACCOUNT_ID = identity.derive_account_id("555666", "TestBroker", "TestServer")
OTHER_ACCOUNT_ID = identity.derive_account_id("777888", "TestBroker", "TestServer")
PROV = {"raw_source_path": "x.csv", "raw_source_sha256": "a" * 64,
       "parser_name": "test", "parser_version": "1.0.0", "normalized_at": "2026-01-01T00:00:00+00:00"}


def _episode(**kw):
    base = {"episode_id": "e1", "account_id": ACCOUNT_ID, "position_id": 1, "symbol": "EURUSD",
           "strategy_attribution": {"status": "UNKNOWN"}, "side": "BUY",
           "open_time": "2026-01-01T10:00:00+00:00", "close_time": "2026-01-01T12:00:00+00:00",
           "volume_opened": 0.1, "volume_closed": 0.1, "avg_open_price": 1.1, "avg_close_price": 1.12,
           "realized_pnl": 20.0, "swap_total": 0.0, "commission_total": 0.0, "r_multiple": None,
           "status": "CLOSED", "deal_ids": [1, 2], "provenance": PROV}
    base.update(kw)
    return base


def _deal(**kw):
    base = {"deal_ticket": 1, "position_id": 1, "order_ticket": 1, "account_id": ACCOUNT_ID,
           "time": "2026-01-01T10:00:00+00:00", "time_msc": None, "symbol": "EURUSD", "magic": 1,
           "type": "DEAL_TYPE_BUY", "entry": "DEAL_ENTRY_IN", "price": 1.1, "volume": 0.1, "sl": None,
           "tp": None, "profit": None, "swap": None, "commission": None, "comment": None,
           "reason": "DEAL_REASON_EXPERT", "strategy_attribution": {"status": "UNKNOWN"}, "provenance": PROV}
    base.update(kw)
    return base


def test_clean_bundle_passes():
    bundle = {"deals": [_deal()], "trade_episodes": [_episode()], "provenance": PROV}
    result = verifier.verify_bundle(bundle, ACCOUNT_ID)
    assert result["status"] == "CLEAN"
    assert result["checks_failed"] == []


def test_duplicate_deal_ids_detected():
    bundle = {"deals": [_deal(deal_ticket=5), _deal(deal_ticket=5)], "trade_episodes": [], "provenance": PROV}
    result = verifier.verify_bundle(bundle, ACCOUNT_ID)
    failed_checks = {f["check"] for f in result["checks_failed"]}
    assert "no_duplicate_deal_ids" in failed_checks


def test_negative_volume_detected():
    bundle = {"deals": [_deal(volume=-0.1)], "trade_episodes": [], "provenance": PROV}
    result = verifier.verify_bundle(bundle, ACCOUNT_ID)
    failed_checks = {f["check"] for f in result["checks_failed"]}
    assert "no_negative_volume" in failed_checks


def test_exit_before_entry_detected():
    bundle = {"deals": [], "trade_episodes": [_episode(
        open_time="2026-01-02T00:00:00+00:00", close_time="2026-01-01T00:00:00+00:00")], "provenance": PROV}
    result = verifier.verify_bundle(bundle, ACCOUNT_ID)
    failed_checks = {f["check"] for f in result["checks_failed"]}
    assert "exit_not_before_entry" in failed_checks


def test_account_mismatch_detected():
    bundle = {"deals": [_deal(account_id=OTHER_ACCOUNT_ID)], "trade_episodes": [], "provenance": PROV}
    result = verifier.verify_bundle(bundle, ACCOUNT_ID)
    failed_checks = {f["check"] for f in result["checks_failed"]}
    assert "account_id_matches_expected" in failed_checks


def test_corrupted_raw_file_hash_mismatch_detected(tmp_path):
    raw = tmp_path / "raw.csv"
    raw.write_text("original content", encoding="utf-8")
    from mt5_data_v1 import canonical
    prov = {**PROV, "raw_source_sha256": canonical.file_sha256(raw)}
    bundle = {"deals": [], "trade_episodes": [], "provenance": prov}

    raw.write_text("TAMPERED content after normalization", encoding="utf-8")
    result = verifier.verify_bundle(bundle, ACCOUNT_ID, raw_path=raw)
    failed_checks = {f["check"] for f in result["checks_failed"]}
    assert "raw_hash_matches_disk" in failed_checks


def test_status_escalates_to_failed_with_multiple_issues():
    bundle = {"deals": [_deal(deal_ticket=1), _deal(deal_ticket=1), _deal(volume=-1, deal_ticket=2)],
             "trade_episodes": [_episode(account_id=OTHER_ACCOUNT_ID)], "provenance": PROV}
    result = verifier.verify_bundle(bundle, ACCOUNT_ID)
    assert result["status"] == "FAILED"
