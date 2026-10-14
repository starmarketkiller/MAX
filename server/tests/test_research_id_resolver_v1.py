"""Hypothesis ID alias resolver (research_intelligence_v1.id_resolver).

Synthetic only: every memory and manifest lives in tmp_path; a guard fails the
test on any attempt to open market data, holdout or dataset files."""
from __future__ import annotations

import builtins
import json
import re
import sys
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from research_intelligence_v1 import id_resolver, lessons, pilot, priority_queue  # noqa: E402
from research_intelligence_v1.hypotheses import FamilyBudget, signature_of  # noqa: E402
from research_intelligence_v1.loop import ResearchLoop  # noqa: E402
from research_intelligence_v1.memory import ResearchMemory  # noqa: E402

T0 = "2026-10-14T00:00:00+00:00"
FAMILY = "NXL2-CP2-PILOT"
PKG = "a" * 64
REAL_MANIFEST = RESEARCH / "research_intelligence_v1" / "manifests" / "nxl2_cp2_pilot_a_001_v1.json"
FORBIDDEN = ("dukascopy", "holdout", "market_state", ".csv", ".parquet", "datasets")
RECORD_ID = re.compile(r"^(EXP|HYP|OBS|REV|PROP|PRIO|LOOP|PLAN|ACT|EVAL|TRIAL)-[A-Z0-9][A-Z0-9_.-]{2,100}$")
HIDS = [f"NXL2-{s}-{side}-{tf}-ctx{ctx}-A"
        for s, tf in (("BOLLINGER", "H4"), ("EMA_PULLBACK", "H4"), ("Z_SCORE_BREAKOUT", "H1"))
        for side in ("BUY", "SELL") for ctx in ("NONE", "HTF1")]


@pytest.fixture(autouse=True)
def no_real_data(monkeypatch):
    real_open = builtins.open

    def guarded(path, *a, **kw):
        low = str(path).lower()
        if any(f in low for f in FORBIDDEN):
            raise AssertionError(f"synthetic test tried to read real data: {path}")
        return real_open(path, *a, **kw)
    monkeypatch.setattr(builtins, "open", guarded)


@pytest.fixture
def mem(tmp_path):
    return ResearchMemory(str(tmp_path / "memory.jsonl"))


def _draft_sha(i):
    return f"{i:02d}".ljust(64, "d")


def add_hyp(mem, hid, i):
    spec = dict(pilot.BL001_SPEC, event_family=f"SYNTH_NXL2_CELL_{i}")
    sig, sig_hash = signature_of(spec)
    body = {"hypothesis_id": hid, "statement": f"synthetic cell {i}", "version": "1",
            "lifecycle_state": "PREREGISTERED", "signature": sig, "signature_sha256": sig_hash,
            "mechanism": spec["mechanism"], "falsification": spec["falsification"],
            "data_needed": ["SYNTHETIC"], "overfitting_risk": "MEDIUM", "expected_information_value": "HIGH",
            "evidence_level": "NONE_PROPOSAL", "is_proposal_only": False}
    # record ids are written explicitly by the test; the resolver never derives them
    return mem.append("HYPOTHESIS", f"HYP-SYN-CELL-{i:02d}", body, author="synthetic", origin="HUMAN",
                      project="NEXUS", family=FAMILY, created_at=T0,
                      provenance=[{"kind": "FILE", "ref": "pkg.tar.gz", "sha256": PKG},
                                  {"kind": "FILE", "ref": f"draft{i}.json", "sha256": _draft_sha(i)}])


def manifest_for(records, **over):
    data = {"manifest_schema": id_resolver.MANIFEST_SCHEMA, "manifest_id": "SYN-v1",
            "package": {"sha256": PKG},
            "aliases": [{"alias": r["body"]["hypothesis_id"], "record_id": r["record_id"],
                         "record_hash": r["record_hash"], "signature_sha256": r["body"]["signature_sha256"],
                         "draft_sha256": _draft_sha(i)} for i, r in enumerate(records)]}
    data.update(over)
    return data


@pytest.fixture
def cells(mem):
    return [add_hyp(mem, hid, i) for i, hid in enumerate(HIDS)]


def test_all_twelve_resolve_without_collisions(mem, cells):
    m = [("syn.json", manifest_for(cells))]
    got = [id_resolver.resolve(mem, h, manifests=m) for h in HIDS]
    assert got == [c["record_id"] for c in cells]
    assert len(set(got)) == 12
    table, conflicts = id_resolver.alias_table(m)
    assert len(table) == 12 and conflicts == []


def test_old_exact_rule_matches_none_and_no_uppercasing(mem, cells):
    assert all(mem.get(f"HYP-{h}") is None for h in HIDS)
    assert all(id_resolver.resolve(mem, h, manifests=[]) is None for h in HIDS)
    assert id_resolver.resolve(mem, HIDS[0].upper(), manifests=[("syn.json", manifest_for(cells))]) is None


def test_unknown_rejected(mem, cells):
    m = [("syn.json", manifest_for(cells))]
    for bad in ("NXL2-UNKNOWN-ctxNONE-A", "", None, 42):
        assert id_resolver.resolve(mem, bad, manifests=m) is None


def test_ambiguous_alias_rejected(mem, cells):
    a = manifest_for(cells)
    b = manifest_for(cells)
    b["aliases"][0] = dict(b["aliases"][0], record_id=cells[1]["record_id"])
    m = [("a.json", a), ("b.json", b)]
    table, conflicts = id_resolver.alias_table(m)
    assert conflicts == [HIDS[0]]
    assert id_resolver.resolve(mem, HIDS[0], manifests=m) is None
    assert id_resolver.resolve(mem, HIDS[1], manifests=m) == cells[1]["record_id"]


def test_identical_duplicate_declaration_is_not_a_conflict(mem, cells):
    m = [("a.json", manifest_for(cells)), ("b.json", manifest_for(cells))]
    assert id_resolver.alias_table(m)[1] == []
    assert id_resolver.resolve(mem, HIDS[0], manifests=m) == cells[0]["record_id"]


def test_missing_target_rejected(mem, cells):
    data = manifest_for(cells)
    data["aliases"][0] = dict(data["aliases"][0], record_id="HYP-SYN-DOES-NOT-EXIST")
    assert id_resolver.resolve(mem, HIDS[0], manifests=[("m.json", data)]) is None


def test_non_hypothesis_target_rejected(mem):
    pilot.seed(mem, created_at=T0)
    obs = "OBS-BL-H4-SELECTIVITY-2019-2022"
    assert mem.get(obs)["record_type"] == "OBSERVATION"
    data = {"manifest_schema": id_resolver.MANIFEST_SCHEMA, "aliases": [{"alias": "SYN-ctx-X", "record_id": obs}]}
    assert id_resolver.resolve(mem, "SYN-ctx-X", manifests=[("m.json", data)], validate_provenance=False) is None


@pytest.mark.parametrize("field,value", [("record_hash", "0" * 64), ("signature_sha256", "1" * 64),
                                         ("draft_sha256", "2" * 64)])
def test_bad_entry_provenance_rejected(mem, cells, field, value):
    data = manifest_for(cells)
    data["aliases"][0] = dict(data["aliases"][0], **{field: value})
    m = [("m.json", data)]
    assert id_resolver.resolve(mem, HIDS[0], manifests=m) is None
    assert id_resolver.resolve(mem, HIDS[0], manifests=m, validate_provenance=False) == cells[0]["record_id"]


def test_bad_package_sha_rejected(mem, cells):
    m = [("m.json", manifest_for(cells, package={"sha256": "3" * 64}))]
    assert all(id_resolver.resolve(mem, h, manifests=m) is None for h in HIDS)


def test_alias_pointing_to_other_hypothesis_rejected(mem, cells):
    data = manifest_for(cells)
    data["aliases"][0] = dict(data["aliases"][1], alias=HIDS[0])
    assert id_resolver.resolve(mem, HIDS[0], manifests=[("m.json", data)]) is None


def test_bl001_exact_lookup_unchanged(mem, tmp_path):
    pilot.seed(mem, created_at=T0)
    assert id_resolver.resolve(mem, "BL-H4M15-IPC-001", manifests=[]) == "HYP-BL-H4M15-IPC-001"
    hijack = {"manifest_schema": id_resolver.MANIFEST_SCHEMA, "aliases": [
        {"alias": "BL-H4M15-IPC-001", "record_id": "HYP-SOMETHING-ELSE"}]}
    assert id_resolver.resolve(mem, "BL-H4M15-IPC-001", manifests=[("h.json", hijack)]) == "HYP-BL-H4M15-IPC-001"


def test_load_manifests_reads_only_declared_schema(tmp_path):
    (tmp_path / "ok.json").write_text(json.dumps({"manifest_schema": id_resolver.MANIFEST_SCHEMA, "aliases": []}))
    (tmp_path / "other.json").write_text(json.dumps({"manifest_schema": "something-else"}))
    assert [n for n, _ in id_resolver.load_manifests(str(tmp_path))] == ["ok.json"]


def _summary(hid, n):
    return {"run_id": f"SYN-NXL2-RUN-{n:02d}", "hypothesis_id": hid, "split": "discovery",
            "split_start": "2023-02-04", "split_end": "2024-08-04", "params_sha256": "c" * 64,
            "git_commit": "d" * 40, "decision": {"decision": "INVESTIGATE"},
            "events": {"n_closed": 10, "expectancy_r_net": 0.0, "expectancy_r_net_ci95_month_blocks": [-0.1, 0.1],
                       "p_target_first": 0.3},
            "data_checks": {"manifest": {"verdict": "OK", "sha256": "e" * 64}}}


def _family_state(mem):
    hyps = [r for r in mem.of_type("HYPOTHESIS") if r["family"] == FAMILY]
    brief = lessons.briefing(mem, FAMILY, max_per_family=12, family_alpha=0.10)
    scores = [priority_queue.score(mem, h, {})["novelty"] for h in hyps]
    return len(hyps), brief["hypotheses"], brief["per_test_alpha"], FamilyBudget(mem, 12).remaining(FAMILY), scores


def test_step_observe_ingests_twelve_synthetic_reports(mem, cells, tmp_path, monkeypatch):
    mdir = tmp_path / "manifests"
    mdir.mkdir()
    (mdir / "syn.json").write_text(json.dumps(manifest_for(cells)))
    monkeypatch.setattr(id_resolver, "MANIFEST_DIR", str(mdir))
    inbox = []
    for n, hid in enumerate(HIDS):
        p = tmp_path / f"summary_{n:02d}.json"
        p.write_text(json.dumps(_summary(hid, n)))
        inbox.append(str(p))
    before = _family_state(mem)
    out = ResearchLoop(mem, inbox=inbox, created_at=T0)._step_observe("SYN", T0, {}, {})
    assert len(out["ingested"]) == 12 and out["skipped_reports"] == []
    tested = {rel["target"] for e in mem.of_type("EXPERIMENT") for rel in e["relations"] if rel["type"] == "TESTS"}
    assert tested == {c["record_id"] for c in cells}
    after = _family_state(mem)
    assert before == after
    assert after[0] == 12 and after[1] == 12 and after[2] == pytest.approx(0.10 / 12) and after[3] == 0
    assert mem.verify() == []


def test_step_observe_without_manifest_skips_fail_closed(mem, cells, tmp_path, monkeypatch):
    monkeypatch.setattr(id_resolver, "MANIFEST_DIR", str(tmp_path / "none"))
    p = tmp_path / "summary.json"
    p.write_text(json.dumps(_summary(HIDS[0], 0)))
    out = ResearchLoop(mem, inbox=[str(p)], created_at=T0)._step_observe("SYN", T0, {}, {})
    assert out["ingested"] == [] and len(out["skipped_reports"]) == 1
    assert not mem.of_type("EXPERIMENT")


def test_shipped_manifest_is_aliases_and_provenance_only():
    data = json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))
    assert data["manifest_schema"] == id_resolver.MANIFEST_SCHEMA
    assert data["experiment_id"] == "NXL2-CP2-PILOT-A-001"
    assert data["package"]["sha256"] == "e4dd83215d45df41d4ea9a0746d30bcf82c265955359a38055a1857568b820d7"
    assert data["seeds"]["seed_base"] == 20261014
    assert data["seeds"]["rng_rule"] == "numpy default_rng([seed_base, cell_index, event_bar_index])"
    assert data["statistical_family"]["primary"] == {"name": "NXL2-CP2-PRIMARY", "size": 12,
                                                     "method": "Benjamini-Yekutieli", "q": 0.1}
    assert "canonical" in data["canonical_source_note"]
    aliases = data["aliases"]
    assert len(aliases) == 12
    assert len({a["alias"] for a in aliases}) == 12 and len({a["record_id"] for a in aliases}) == 12
    assert {a["alias"] for a in aliases} == set(HIDS)
    for a in aliases:
        assert RECORD_ID.match(a["record_id"]) and not RECORD_ID.match("HYP-" + a["alias"])
        assert all(re.fullmatch(r"[0-9a-f]{64}", a[k]) for k in ("record_hash", "signature_sha256", "draft_sha256"))
        assert set(a) == {"alias", "record_id", "record_hash", "signature_sha256", "draft_file", "draft_sha256"}
    assert all(re.fullmatch(r"[0-9a-f]{64}", v) for v in data["frozen_file_hashes"].values())
    text = REAL_MANIFEST.read_text(encoding="utf-8").lower()
    assert not any(k in text for k in ("password", "secret", "token", "api_key", "private_key"))


def test_shipped_manifest_fails_closed_until_records_exist(mem):
    """Before the preregistration records are in memory the aliases resolve to nothing."""
    m = id_resolver.load_manifests()
    assert any(d.get("experiment_id") == "NXL2-CP2-PILOT-A-001" for _, d in m)
    assert all(id_resolver.resolve(mem, h, manifests=m) is None for h in HIDS)
