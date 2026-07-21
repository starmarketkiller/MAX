import math
import re
from pathlib import Path

import pytest

import app
import settings_contract as sc


def test_backend_defaults_derive_from_canonical_artifact():
    assert app.DEFAULT_SETTINGS == sc.DEFAULT_SETTINGS
    assert sc.DEFAULT_SETTINGS["MaxTradesPerDay"] == 12
    assert sc.DEFAULT_SETTINGS["MaxConcurrent"] == 4
    assert sc.DEFAULT_SETTINGS["MinEntryScore"] == 50


def test_core_defaults_match_ea_inputs():
    path = Path(__file__).resolve().parents[2] / "MQL5" / "Include" / "NEXUS_v1" / "NXS_Inputs.mqh"
    source = path.read_text(encoding="utf-8")
    expected = {
        "RiskPercent": ("InpRiskPercent", float),
        "MaxLot": ("InpMaxLot", float),
        "MaxTradesPerDay": ("InpMaxTradesPerDay", int),
        "MaxConcurrent": ("InpMaxConcurrent", int),
        "MaxDailyDDPct": ("InpMaxDailyDDPct", float),
        "MinEntryScore": ("InpMinEntryScore", int),
    }
    for key, (mql_name, cast) in expected.items():
        match = re.search(rf"\b{mql_name}\s*=\s*([0-9.]+)", source)
        assert match, mql_name
        assert sc.DEFAULT_SETTINGS[key] == cast(float(match.group(1)))


@pytest.mark.parametrize("payload", [
    {"UnknownKnob": 1},
    {"RiskPercent": math.nan},
    {"RiskPercent": math.inf},
    {"MaxConcurrent": 2.5},
    {"MaxDailyDDPct": -1},
    {"UseNewsFilter": "true"},
])
def test_invalid_settings_are_rejected(payload):
    with pytest.raises(sc.SettingsValidationError):
        sc.validate_settings(payload)


def test_profile_versions_and_checksum_are_deterministic():
    first = sc.version_profile({"saved_at": "2026-07-21T00:00:00Z", "params": {"RiskPct": 1.0}}, created_by="test")
    second = sc.version_profile({"saved_at": "2026-07-21T00:01:00Z", "params": {"RiskPct": 1.0}}, first, created_by="test")
    changed = sc.version_profile({"saved_at": "2026-07-21T00:02:00Z", "params": {"RiskPct": 2.0}}, second, created_by="test")
    assert first["version"] == 1 and second["version"] == 2 and changed["version"] == 3
    assert first["profile_id"] == second["profile_id"] == changed["profile_id"]
    assert first["checksum"] == second["checksum"]
    assert changed["checksum"] != second["checksum"]
    assert len(changed["checksum"]) == 64
