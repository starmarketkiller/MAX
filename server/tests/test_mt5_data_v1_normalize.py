"""Test per normalize.py - determinismo, provenance, rifiuto account_id non
valido, orari non convertiti silenziosamente (MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1)."""
from pathlib import Path

import pytest

from mt5_data_v1 import canonical, identity, normalize

REPO_ROOT = Path(__file__).resolve().parents[2]
NATIVE_DEAL_SAMPLE = REPO_ROOT / "server/research_scripts/phase7/phase7_9h/raw_data/nxs_diag_deals_export_r003.csv"

ACCOUNT_ID = identity.derive_account_id("111222", "TestBroker", "TestServer")


def test_normalize_rejects_invalid_account_id():
    with pytest.raises(ValueError, match="account_id non valido"):
        normalize.normalize_native_deal_export(NATIVE_DEAL_SAMPLE, "not-a-valid-id")


def test_normalize_native_deal_export_is_deterministic_in_payload():
    """Due normalizzazioni dello stesso file devono produrre lo stesso
    contenuto canonico (a parte normalized_at, volatile) - stesso principio
    di canonical_sha256 di phase6_6/canonical_utils.py."""
    b1 = normalize.normalize_native_deal_export(NATIVE_DEAL_SAMPLE, ACCOUNT_ID)
    b2 = normalize.normalize_native_deal_export(NATIVE_DEAL_SAMPLE, ACCOUNT_ID)

    def strip_volatile(bundle):
        deals = [{k: v for k, v in d.items() if k != "provenance"} for d in bundle["deals"]]
        episodes = [{k: v for k, v in e.items() if k != "provenance"} for e in bundle["trade_episodes"]]
        return canonical.canonical_sha256({"deals": deals, "episodes": episodes})

    assert strip_volatile(b1) == strip_volatile(b2)


def test_normalize_provenance_hash_matches_real_file_on_disk():
    bundle = normalize.normalize_native_deal_export(NATIVE_DEAL_SAMPLE, ACCOUNT_ID)
    expected = canonical.file_sha256(NATIVE_DEAL_SAMPLE)
    assert bundle["provenance"]["raw_source_sha256"] == expected
    for d in bundle["deals"]:
        assert d["provenance"]["raw_source_sha256"] == expected


def test_normalize_does_not_modify_raw_file(tmp_path):
    copy = tmp_path / "copy.csv"
    copy.write_bytes(NATIVE_DEAL_SAMPLE.read_bytes())
    before = copy.read_bytes()
    normalize.normalize_native_deal_export(copy, ACCOUNT_ID)
    after = copy.read_bytes()
    assert before == after


def test_normalize_auto_detects_native_deal_export():
    bundle = normalize.normalize_auto(NATIVE_DEAL_SAMPLE, ACCOUNT_ID)
    assert bundle["source_format"] == "NATIVE_DEAL_EXPORT"


def test_normalize_auto_rejects_unknown_format(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("foo,bar\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="formato CSV non riconosciuto"):
        normalize.normalize_auto(bad, ACCOUNT_ID)


def test_time_is_tagged_utc_without_silent_conversion():
    """Limite dichiarato: MT5 non porta un timezone esplicito nei suoi
    export - il parser NON tenta nessuna conversione, tagga semplicemente
    come UTC l'ora cosi' com'e' nel file. Se due fonti (es. account reali su
    server diversi) hanno offset diversi, il disallineamento resta visibile
    nei timestamp, non viene silenziosamente corretto."""
    bundle = normalize.normalize_native_deal_export(NATIVE_DEAL_SAMPLE, ACCOUNT_ID)
    raw_text = NATIVE_DEAL_SAMPLE.read_text(encoding="utf-8")
    first_data_line = [l for l in raw_text.splitlines() if l.strip()][1]
    raw_time = first_data_line.split(",")[3]  # "2019.02.03 00:00:00"
    assert bundle["deals"][0]["time"].startswith(raw_time.split(" ")[0].replace(".", "-"))
    assert bundle["deals"][0]["time"].endswith("+00:00")
