"""CHART-HISTORICAL-EXPANSION-01 — il modello di autorizzazione persistente del candidato cumulativo coincide ESATTAMENTE con le finestre gia' autorizzate e non sfiora sigilli."""
import datetime as dt
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server"))
import chart_authority_ctl as ctl  # noqa: E402
import chart_guard  # noqa: E402

TEMPLATE = ROOT / "docs" / "chart" / "historical" / "chart_authorization.persistent.cumulative.TEMPLATE.json"
PHASE7 = ROOT / "server" / "research_scripts" / "phase7"
DS = "DUKASCOPY_XAUUSD_PHASE7"


def ep(s):
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


@pytest.fixture(scope="module")
def tpl():
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def test_template_is_accepted_by_the_operator_tool_and_has_exactly_two_datasets(tpl):
    ok, why, _doc = ctl.validate_record_bytes(TEMPLATE.read_bytes())
    assert ok, why
    assert set(tpl["datasets"]) == {DS, "XM-GOLD-2026-11-16-20"}
    assert all(r["kind"] == "EXPLICIT_WINDOWS" for r in tpl["datasets"].values())


def test_dukascopy_window_equals_the_development_discovery_partition_and_nothing_else(tpl):
    part = json.loads((PHASE7 / "partition_manifest_v1.json").read_text(encoding="utf-8"))["payload"]["segments"]
    seg = {s["name"]: s for s in part}
    d = seg["development_discovery"]
    (a, b), = tpl["datasets"][DS]["windows_utc"]
    assert ep(a) == ep(d["declared_start"] + "T00:00:00Z")
    assert ep(b) == ep(d["declared_end"] + "T00:00:00Z") + 86400
    for other in ("development_internal_validation", "locked_validation", "final_holdout"):
        assert not (ep(a) < ep(seg[other]["declared_end"] + "T00:00:00Z") + 86400 and ep(b) > ep(seg[other]["declared_start"] + "T00:00:00Z")), other
    seal = json.loads((PHASE7 / "final_holdout_seal_v1.json").read_text(encoding="utf-8"))["payload"]["date_range"]
    assert ep(b) <= ep(seal["start"] + "T00:00:00Z")                                   # nessuna intersezione con il sigillo


def test_xm_window_is_unchanged_with_respect_to_the_approved_development_record(tpl):
    dev = json.loads((ROOT / "server" / "chart_authorization.json").read_text(encoding="utf-8"))
    assert tpl["datasets"]["XM-GOLD-2026-11-16-20"]["windows_utc"] == dev["datasets"]["XM-GOLD-2026-11-16-20"]["windows_utc"]


def test_real_guard_admits_only_the_discovery_window_with_this_template(tpl, tmp_path):
    p = tmp_path / "rec.json"
    p.write_bytes(TEMPLATE.read_bytes())
    g = chart_guard.Guard(auth_path=p)
    assert g.error is None
    day = lambda s: (ep(s + "T00:00:00Z"), ep(s + "T00:00:00Z") + 86400)
    for ok in ("2023-02-04", "2023-12-31", "2024-08-03"):
        g.check(DS, *day(ok))
    for denied in ("2023-02-03", "2024-08-04", "2025-06-01", "2026-03-01"):                # prima, subito dopo, validazione bloccata, holdout sigillato
        with pytest.raises(chart_guard.PartitionDenied):
            g.check(DS, *day(denied))
    with pytest.raises(chart_guard.PartitionDenied):
        g.check(DS, ep("2024-08-03T12:00:00Z"), ep("2024-08-04T12:00:00Z"))                # una richiesta a cavallo del confine e' negata per intero
    g.check("XM-GOLD-2026-11-16-20", ep("2026-11-16T00:00:00Z"), ep("2026-11-17T00:00:00Z"))
