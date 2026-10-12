"""BL-01 discovery results in Research Memory: transcription, run record, analysis, proposals.

No market data is read: the run happened on the research PC; the repo holds a
declared transcription of its summary.json with the original file's sha256.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

RESEARCH = Path(__file__).resolve().parents[1] / "research_scripts"
sys.path.insert(0, str(RESEARCH))

from bl01_results_v1 import record_results  # noqa: E402
from research_intelligence_v1 import pilot  # noqa: E402
from research_intelligence_v1.memory import ResearchMemory, sha256_file  # noqa: E402

MEMORY = RESEARCH / "research_intelligence_v1" / "memory"
RUN = record_results.RUN_RECORD
ORIGINAL_SUMMARY_SHA = "61a5cd9b15dfc0def98b72cd81664473b6796e854bbba4cc3a05868fa3cc78bb"


def test_transcription_is_consistent_with_the_run():
    s = json.loads(Path(record_results.SUMMARY).read_text())
    assert s["transcription"]["source_sha256"] == ORIGINAL_SUMMARY_SHA
    assert s["params_sha256"] == pilot.PARAMS_SHA
    assert s["data_checks"]["manifest"]["verdict"] == "MATCH"
    cells = s["vs_control_stratified"]["cells"]
    assert len(cells) == s["vs_control_stratified"]["cells_used"] == 25
    assert sum(c["events"]["n"] for c in cells) == s["events"]["n_closed"] == s["funnel_events"]["CLOSED"] == 49
    assert sum(c["events"]["exp"] > c["controls"]["exp"] for c in cells) == s["vs_control_stratified"]["cells_event_better"]
    assert sum(s["funnel_events"].values()) == s["selection"]["events_seen"] == 95
    checks = s["decision"]["checks"]
    assert s["decision"]["decision"] == "INVESTIGATE" and sorted(k for k, v in checks.items() if not v) == sorted(
        s["decision"]["reasons"])


def test_committed_memory_holds_the_run_and_its_analysis():
    mem = ResearchMemory(str(MEMORY / "research_memory_v1.jsonl"))
    assert mem.verify() == []
    run = mem.get(RUN)
    assert run["provenance"][0]["sha256"] == ORIGINAL_SUMMARY_SHA
    assert run["provenance"][1]["sha256"] == sha256_file(record_results.SUMMARY)
    assert mem.get("EXP-BL-01-DISCOVERY.R1")["body"]["status"] == "NOT_RUN"  # placeholder kept
    cur = mem.current("EXP-BL-01-DISCOVERY")
    assert cur["record_id"] == RUN + ".A1"
    body = cur["body"]
    assert (body["status"], body["result"], body["decision"]) == ("COMPLETED", "INCONCLUSIVE", "INVESTIGATE")
    assert body["evidence_level"] == "DISCOVERY_ONLY" and body["alternative_explanations"]
    assert body["metrics"]["expectancy_ci95"][0] < 0 < body["metrics"]["expectancy_ci95"][1]
    assert any("not evidence of an edge" in c for c in body["conclusions"])
    for rid in ("OBS-BL01-FEASIBILITY-OBSERVED-V1", "PROP-H4_CONTEXT_VS_MATCHED_CONTROL-19CF306D7B",
                "PROP-RUN_ARTIFACT_TRANSFER-F4B0454967", "PROP-WINDOWS_PEAK_RSS-4C689D1E02"):
        assert mem.get(rid), rid
    for p in mem.of_type("IMPROVEMENT_PROPOSAL"):
        assert p["body"]["status"] == "PROPOSED"  # nothing approved automatically
    assert mem.of_type("ACTION") == []  # the AUTO_SAFE cycles planned and executed nothing


def test_record_is_idempotent(tmp_path):
    for name in ("research_memory_v1.jsonl", "research_memory_v1.checkpoints.jsonl"):
        shutil.copy(MEMORY / name, tmp_path / name)
    mem = ResearchMemory(str(tmp_path / "research_memory_v1.jsonl"))
    n = len(mem.records)
    assert record_results.record(mem) == []
    assert len(mem.records) == n and mem.verify() == []
