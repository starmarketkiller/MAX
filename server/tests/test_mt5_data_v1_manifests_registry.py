"""Test per manifests.py e account_registry.py: round-trip su disco,
conformita' minima ai contracts/mt5-*.schema.json (controllo manuale,
niente libreria jsonschema - stessa scelta di contracts/validate_registry.py)."""
import json
from pathlib import Path

from mt5_data_v1 import account_registry, canonical, identity, manifests

REPO_ROOT = Path(__file__).resolve().parents[2]
ACCOUNT_ID = identity.derive_account_id("manifest_test", "Broker", "Server")


def test_run_manifest_round_trip(tmp_path):
    artifact = manifests.make_artifact_entry(
        "RAW_DEAL_EXPORT", "C:/fake/path.csv", sha256="a" * 64, size_bytes=123, row_count=5)
    run_manifest = manifests.build_run_manifest(
        "run_001", ACCOUNT_ID, [artifact], terminal_role="TESTER_TERMINAL", symbol="EURUSD")

    path = tmp_path / "run_manifest.json"
    canonical.save_json(path, run_manifest)
    loaded = canonical.load_json(path)

    assert loaded["schema_version"] == 1
    assert loaded["run_id"] == "run_001"
    assert loaded["account_id"] == ACCOUNT_ID
    assert loaded["collected_before_any_interpretation"] is True
    assert loaded["no_verdict_computed_here"] is True
    assert loaded["artifacts"][0]["artifact_type"] == "RAW_DEAL_EXPORT"


def test_account_manifest_round_trip(tmp_path):
    account_manifest = manifests.build_account_manifest(
        ACCOUNT_ID, environment="DEMO", broker="TestBroker", server="TestServer",
        runs=[{"run_id": "run_001", "artifact_count": 1}],
        import_log=[{"source_sha256": "b" * 64, "import_mode": "IMPORT_NEW",
                     "imported_at": canonical.utc_now_iso()}],
        data_quality={"status": "CLEAN", "checks_passed": ["no_duplicate_deal_ids"], "checks_failed": []},
    )
    path = tmp_path / "account_manifest.json"
    canonical.save_json(path, account_manifest)
    loaded = canonical.load_json(path)

    assert loaded["account_id"] == ACCOUNT_ID
    assert loaded["environment"] == "DEMO"
    assert loaded["data_quality"]["status"] == "CLEAN"
    assert loaded["runs"][0]["run_id"] == "run_001"


def test_schemas_are_valid_json():
    for name in ("mt5-account-registry-v1", "mt5-trade-history-v1",
                "mt5-run-manifest-v1", "mt5-account-manifest-v1"):
        path = REPO_ROOT / "contracts" / f"{name}.schema.json"
        with open(path, encoding="utf-8") as f:
            schema = json.load(f)
        assert schema["$schema"] == "http://json-schema.org/draft-07/schema#"
        assert "title" in schema


def test_account_registry_upsert_and_round_trip(tmp_path):
    registry = account_registry.new_registry()
    registry = account_registry.upsert_account(
        registry, ACCOUNT_ID, environment="REAL", identity_source="DERIVED_FROM_DEAL_EXPORT",
        broker="TestBroker", server="TestServer", base_currency="USD", leverage=100)

    path = tmp_path / "registry.json"
    account_registry.save_registry(path, registry)
    loaded = account_registry.load_registry(path)

    account = account_registry.get_account(loaded, ACCOUNT_ID)
    assert account is not None
    assert account["environment"] == "REAL"
    assert account["base_currency"] == "USD"
    assert account["first_seen_at"] == account["last_seen_at"]


def test_account_registry_upsert_updates_last_seen_without_losing_first_seen(tmp_path):
    registry = account_registry.new_registry()
    registry = account_registry.upsert_account(
        registry, ACCOUNT_ID, environment="REAL", identity_source="DERIVED_FROM_DEAL_EXPORT")
    first_seen = account_registry.get_account(registry, ACCOUNT_ID)["first_seen_at"]

    registry = account_registry.upsert_account(
        registry, ACCOUNT_ID, environment="REAL", identity_source="DERIVED_FROM_DEAL_EXPORT",
        display_label="Updated Label")
    account = account_registry.get_account(registry, ACCOUNT_ID)
    assert account["first_seen_at"] == first_seen
    assert account["display_label"] == "Updated Label"
    assert len(registry["accounts"]) == 1  # nessun duplicato
