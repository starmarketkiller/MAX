"""Operations V2 realistic dry run on real public evidence.  No irreversible action.

real trend/product source -> evidence captured -> product candidate -> store
gate -> viral format analysis (canonical Orchestrator) -> content brief ->
Elena/Nova -> Higgsfield pack -> WAITING_APPROVAL -> Jarvis state.

Run from server/:  python -m business_units.ai_fashion_agency.dry_run_v2
Writes examples/dry_run_v2_result.json.
"""
from __future__ import annotations

import json
import tempfile
from datetime import date
from pathlib import Path

from orchestrator_v1.core.ledger import EventLedger
from orchestrator_v1.core.orchestrator import Orchestrator

from . import pipeline, store_integration
from .content_engine import brief_card
from .events import ledger_sink
from .projection import agency_answer, agency_state, business_unit_state, jarvis_summary
from .scouting import ingest_scout_result
from .skills import AgencyTaskCoordinator, verify_agency_output
from .store import AgencyStore

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "examples" / "real_evidence_2026-10-07.json"
TODAY = date(2026, 10, 7)

# Structure extracted from the verbatim quotes E1-E3 by the supervising Claude
# session after the local worker could not be reached (see orchestrator_task).
SESSION_ANALYSIS = {
    "format_name": "Fan Transition", "hook_pattern": "overhead shot, creator lying flat in a full look",
    "beats": ["overhead camera, lying flat in look 1", "fan blade sweeps across the lens",
              "outfit swapped to look 2 behind the blade", "repeat for looks 3-4",
              "last look holds + caption question"],
    "payoff": "four fall looks revealed in about 19 seconds",
    "comment_bait": "Which look wins: 1, 2, 3 or 4?", "audio_strategy": "PLATFORM_LIBRARY",
    "duration_seconds": 19, "evidence": ["E1", "E2", "E3"],
    "limitations": ["view counts not captured; single editorial source"]}


def run(workdir):
    workdir = Path(workdir)
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    ledger = EventLedger(path=str(workdir / "ledger.jsonl"))
    store = AgencyStore(workdir / "agency.json", event_sink=ledger_sink(ledger))
    orch = Orchestrator(queue_path=str(workdir / "queue.json"),
                        ledger_path=str(workdir / "orchestrator_ledger.jsonl"))
    coordinator = AgencyTaskCoordinator(orch)
    transitions = []

    # 1. evidence captured -> scout results -> inputs/products
    records = {}
    for item in evidence["scout_results"]:
        record, created = ingest_scout_result(store, item)
        records[item["kind"]] = record
        transitions.append({"step": "SCOUT_INGEST", "kind": item["kind"], "created": created,
                            "dedup_key": record["dedup_key"]})

    # 2. product candidate -> store gate (no supplier/price known -> blocked)
    pid = records["FASHION_ITEM_SCOUT"]["product_id"]
    product = store_integration.evaluate_product(store, pid)
    transitions.append({"step": "STORE_GATE", "product_id": pid, "status": product["status"],
                        "blocked_reasons": product.get("blocked_reasons")})
    commercial = pipeline.build_content_brief(
        store, title="Suede jacket fall styling", content_category="fashion",
        hook="Suede season is here", script="styling", caption="Shop the jacket #ad",
        product_id=pid)
    transitions.append({"step": "COMMERCIAL_BRIEF", "status": commercial["status"],
                        "store_gate_status": commercial["store_gate_status"]})

    # 3. viral format analysis through the canonical Orchestrator (real call)
    trend_input = store.get("inputs", records["VIRAL_FORMAT_SCOUT"]["input_id"])
    context = {"evidence_records": [{"evidence_id": e["evidence_id"], "text": e["quote"]}
                                    for e in records["VIRAL_FORMAT_SCOUT"]["evidence"]]}
    task_id = coordinator.submit("VIRAL_FORMAT_ANALYSIS", context=context,
                                 references={"input_id": trend_input["input_id"]})
    record = orch.process_task(task_id)
    orchestrator_task = {"task_id": task_id, "state": record["state"],
                         "executor": record.get("executor"),
                         "escalation_target": (record.get("escalation") or {}).get("target")}
    if record["state"] == "COMPLETED":
        from jarvis_v1.ministral_task_compiler import decode_bounded_output
        analysis = decode_bounded_output(record["result_packet"]["artifacts_created"])
        analysis = {k: v for k, v in analysis.items() if k not in {"template_id", "task_id"}}
        analysis_provenance = "LOCAL_WORKER_VERIFIED"
    else:
        analysis = SESSION_ANALYSIS
        analysis_provenance = "SUPERVISING_CLAUDE_SESSION_AFTER_LOCAL_ESCALATION"
    ok, errors = verify_agency_output("VIRAL_FORMAT_ANALYSIS", analysis, context)
    if not ok:
        raise RuntimeError(f"analysis failed the canonical verifier: {errors}")
    reference = pipeline.viral_reference_from_input(trend_input, analysis)
    reference["analysis_provenance"] = analysis_provenance
    transitions.append({"step": "VIRAL_ANALYSIS", **orchestrator_task,
                        "analysis_provenance": analysis_provenance, "verifier_passed": ok})

    # 4. non-commercial original content brief from the trend
    brief = pipeline.build_content_brief(
        store, title="Fan Transition: four quiet-luxury fall looks", content_category="fashion",
        hook="Four fall looks, one fan", script=" / ".join(analysis["beats"]),
        caption="Which look wins? 1, 2, 3 or 4 #AIcreator #falloutfits",
        cta="Comment your number", viral_reference=reference, platform="tiktok",
        objective="engagement", duration_seconds=analysis["duration_seconds"])
    assignment = pipeline.assign_model(store, brief["brief_id"], actor="model_assignment")
    pack = pipeline.build_generation_pack(store, brief["brief_id"], today=TODAY)
    transitions += [{"step": "CONTENT_BRIEF", "brief_id": brief["brief_id"],
                     "status": brief["status"]},
                    {"step": "MODEL_ASSIGNMENT", "model_id": assignment["model_id"],
                     "ranking": assignment["ranking"][:3]},
                    {"step": "GENERATION_PACK", "pack_id": pack["pack_id"],
                     "state": pack["state"], "quoted_credits": pack["quoted_credits"],
                     "unquoted_steps": pack["unquoted_steps"]}]

    state = agency_state(store, queue=orch.queue)
    questions = ["come va l'agenzia?", "quali modelle stanno lavorando?",
                 "abbiamo prodotti pronti?", "cosa devo approvare per l'agenzia?",
                 "quanto sta guadagnando l'agenzia?", "quale campagna è più promettente?",
                 "quali modelle hanno account?"]
    snapshot = store.snapshot()
    return {
        "schema_version": "AGENCY_DRY_RUN_V2_RESULT", "evidence_file": EVIDENCE.name,
        "provenance": {"collector": evidence["collector_detail"],
                       "sources": sorted({r["url"] for r in snapshot["scout_results"]}),
                       "captured_at": evidence["captured_at"]},
        "transitions": transitions, "brief_card": brief_card(store, brief["brief_id"]),
        "generation_pack": pack, "events": [
            {k: e[k] for k in ("event_type", "entity_id", "summary", "requires_human_action")}
            for e in snapshot["event_outbox"]],
        "ledger_event_types": [e["event_type"] for e in ledger.read_all()],
        "agency_state": state, "business_unit_state": business_unit_state(store, queue=orch.queue),
        "jarvis_summary": jarvis_summary(state),
        "jarvis_answers": {q: agency_answer(q, store, queue=orch.queue)[0] for q in questions},
        "guarantees": {"credits_spent": state["credits_spent"], "published_content": state["published"],
                       "external_outreach": 0, "store_opened": False},
    }


def main():
    with tempfile.TemporaryDirectory() as tmp:
        result = run(tmp)
    for item in result["agency_state"]["approvals"]:
        item.pop("id", None)  # random ids are noise in the committed artifact
    out = HERE / "examples" / "dry_run_v2_result.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(result["jarvis_summary"])
    for step in result["transitions"]:
        print(" -", step["step"], {k: v for k, v in step.items() if k in
                                   ("status", "state", "model_id", "analysis_provenance",
                                    "quoted_credits", "created")})
    print("guarantees:", result["guarantees"])


if __name__ == "__main__":
    main()
