"""End-to-end Agency simulation without spending credits or publishing.

Product Scout -> STORE_GATE -> STORE_READY -> trend video -> Viral Adapter
(skill routed by the canonical Orchestrator) -> Content Brief -> model
selection -> Higgsfield Generation Pack -> WAITING_APPROVAL -> Jarvis state.

Run:  python -m business_units.ai_fashion_agency.simulation  (from server/)
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

from orchestrator_v1.core.orchestrator import Orchestrator
from jarvis_v1.ministral_task_compiler import decode_bounded_output

from . import pipeline
from .projection import agency_state, business_unit_state, jarvis_summary
from .skills import AgencyTaskCoordinator
from .store import AgencyStore

SIMULATION_TODAY = date(2026, 10, 7)
STUB_VIRAL_ANALYSIS = {
    "format_name": "Outfit transition on the beat", "hook_pattern": "POV mid-action reveal",
    "beats": ["mirror selfie in hoodie", "hand covers lens on beat drop",
              "reveal in trend dress", "spin + caption question"],
    "payoff": "full look reveal synced to drop", "comment_bait": "Look 1 or look 2?",
    "audio_strategy": "PLATFORM_LIBRARY", "duration_seconds": 12,
    "evidence": ["E1", "E2"], "limitations": ["view counts supplied by scout, not verified"]}


def _stub_local_model(*args, **kwargs):
    return {"success": True, "response_text": json.dumps(STUB_VIRAL_ANALYSIS),
            "model": "ministral-3:3b (simulation stub)", "wall_seconds": 0.01}


def run_simulation(workdir, *, local_model=_stub_local_model, today=SIMULATION_TODAY):
    workdir = Path(workdir)
    store = AgencyStore(workdir / "agency_registry_v1.json")
    orch = Orchestrator(queue_path=str(workdir / "queue.json"),
                        ledger_path=str(workdir / "ledger.jsonl"))
    coordinator = AgencyTaskCoordinator(orch)
    trace = []

    # 1. NEXUS Product Scout finds a trending dress.
    product_input = pipeline.receive_input(store, "FASHION_ITEM", {
        "title": "Satin slip midi dress", "category": "dresses", "supplier": "SIM_SUPPLIER_1",
        "unit_cost_eur": 14.0, "target_price_eur": 39.0,
        "trend_evidence": ["E1: 'slip dress' search interest rising (scout record)"],
        "source_url": "simulation://scout/slip-dress"},
        source="nexus.product_scout", idempotency_key="sim-product-1")
    product = pipeline.product_from_input(store, product_input)
    trace.append(("PRODUCT_RECEIVED", product["status"]))

    # 2. Store gate: blocked until listed.
    early = pipeline.build_content_brief(
        store, title="Slip dress try-on", content_category="fashion", hook="This dress?",
        script="try-on", caption="Link in bio #ad", product_id=product["product_id"])
    trace.append(("COMMERCIAL_BRIEF_BEFORE_STORE", early["status"]))

    viability = pipeline.evaluate_viability(product)
    pipeline.transition_product(store, product["product_id"], "EVALUATING", actor="store_gate")
    pipeline.transition_product(store, product["product_id"], "STORE_PENDING",
                                actor="store_gate", viability=viability)
    product = pipeline.transition_product(
        store, product["product_id"], "STORE_READY", actor="store_gate",
        listing={"kind": "OWN_STORE", "url": "simulation://store/slip-dress",
                 "simulated": True}, approved_by="SIMULATION_USER")
    trace.append(("STORE_GATE", product["status"]))

    # 3. Trend video discovered -> Viral Adapter skill through the Orchestrator.
    trend = pipeline.receive_input(store, "TREND_VIDEO", {
        "source_url": "simulation://tiktok/trend-123", "platform": "tiktok",
        "observed_views": 2400000},
        source="nexus.trend_scout", idempotency_key="sim-trend-1")
    context = {"evidence_records": [
        {"evidence_id": "E1", "text": "Creator covers lens on beat drop, outfit changes"},
        {"evidence_id": "E2", "text": "Trending platform-library sound, 12 seconds"}]}
    orchestrator_module = sys.modules[Orchestrator.__module__]
    original = orchestrator_module.ollama_worker.call_local_model
    orchestrator_module.ollama_worker.call_local_model = local_model
    try:
        task_id = coordinator.submit("VIRAL_FORMAT_ANALYSIS", context=context,
                                     references={"input_id": trend["input_id"]})
        record = orch.process_task(task_id)
    finally:
        orchestrator_module.ollama_worker.call_local_model = original
    analysis = decode_bounded_output(record["result_packet"]["artifacts_created"])
    analysis = {k: v for k, v in analysis.items() if k not in {"template_id", "task_id"}}
    reference = pipeline.viral_reference_from_input(trend, analysis)
    trace.append(("VIRAL_ADAPTER", record["state"], record["executor"]))

    # 4. Content brief (commercial, store-ready product, original recreation).
    brief = pipeline.build_content_brief(
        store, title="Satin slip dress transition", content_category="fashion",
        hook="POV: hoodie to date night", script=" / ".join(analysis["beats"]),
        caption="Look 1 or look 2? #ad #AIcreator", cta="Shop the dress in bio",
        viral_reference=reference, product_id=product["product_id"])
    trace.append(("CONTENT_BRIEF", brief["status"]))

    # 5. Model selection + assignment.
    assignment = pipeline.assign_model(store, brief["brief_id"], actor="model_assignment")
    trace.append(("MODEL_ASSIGNMENT", assignment["model_id"]))

    # 6. Higgsfield generation pack -> WAITING_APPROVAL (no spend).
    pack = pipeline.build_generation_pack(store, brief["brief_id"], today=today)
    trace.append(("GENERATION_PACK", pack["state"], pack["quoted_credits"]))

    state = agency_state(store, queue=orch.queue)
    return {"trace": trace, "product": product, "brief_rejected_before_store": early,
            "brief": store.get("briefs", brief["brief_id"]), "assignment": assignment,
            "generation_pack": pack, "agency_state": state,
            "business_unit_state": business_unit_state(store, queue=orch.queue),
            "jarvis_summary": jarvis_summary(state), "credits_spent": state["credits_spent"]}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        result = run_simulation(tmp)
    out = Path(__file__).resolve().parent / "examples" / "e2e_simulation_v1.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=list) + "\n",
                   encoding="utf-8")
    print(result["jarvis_summary"])
    print(f"credits_spent={result['credits_spent']}  ->  {out}")


if __name__ == "__main__":
    main()
