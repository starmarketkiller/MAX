"""Test per il Funding Priority & Opportunity Framework V1 (NEXUS TASK
#0005) e per il suo hardening (NEXUS TASK #0006). Verifica: schemi validi,
separazione TECHNICAL_PRIORITY/FUNDING_PRIORITY, pesi di scoring espliciti
(sommano 1.0), determinismo dei builder, coerenza della priority queue
generata, hard gates, capital scenarios, capability coverage, lifecycle
fail-closed, no-fake-precision su evidence/priority_status."""
import json
import os
import sys

FUNDING_DIR = os.path.join(os.path.dirname(__file__), "..", "funding_v1")
ORCH_DIR = os.path.join(os.path.dirname(__file__), "..", "orchestrator_v1")
CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "contracts")
sys.path.insert(0, os.path.abspath(FUNDING_DIR))
sys.path.insert(0, os.path.abspath(ORCH_DIR))

from opportunity_scoring import (FUNDING_DIMENSION_WEIGHTS, TECHNICAL_CRITERIA_WEIGHTS,  # noqa: E402
                                 score_funding_priority, score_technical_priority)
from nxs_schema_validator import validate  # noqa: E402
from build_example_opportunities import build as build_opportunities  # noqa: E402
from build_opportunity_priority_queue import build as build_queue  # noqa: E402
from capability_coverage import compute_capability_coverage, ALL_CAPABILITIES  # noqa: E402
from capital_scenarios import compute_capital_scenarios, SCENARIO_CEILING  # noqa: E402
from hard_gates import compute_hard_gate  # noqa: E402
from opportunity_lifecycle import (STATES, ALLOWED_TRANSITIONS,  # noqa: E402
                                   validate_transition, build_lifecycle_definition)
from self_funding_loop import build_self_funding_loop  # noqa: E402
from opportunity_assembly import assemble_opportunity  # noqa: E402
from opportunity_brief_builder import build_brief_skeleton  # noqa: E402


def _load_schema(name):
    with open(os.path.join(CONTRACTS_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def test_funding_weights_sum_to_one():
    assert abs(sum(FUNDING_DIMENSION_WEIGHTS.values()) - 1.0) < 1e-9


def test_technical_weights_sum_to_one():
    assert abs(sum(TECHNICAL_CRITERIA_WEIGHTS.values()) - 1.0) < 1e-9


def test_scoring_functions_return_0_to_100():
    dims = {k: list(v.keys())[0] for k, v in __import__("opportunity_scoring")
           .FUNDING_DIMENSION_POINTS.items()}
    score, breakdown = score_funding_priority(dims)
    assert 0 <= score <= 100
    assert set(breakdown.keys()) == set(FUNDING_DIMENSION_WEIGHTS.keys())


def test_all_example_opportunities_validate_against_schema():
    schema = _load_schema("opportunity.schema.json")
    payload = build_opportunities()
    assert len(payload["opportunities"]) == 18, (
        "5 opportunity originali di #0005 + 13 INITIAL_HYPOTHESIS di #0006")
    for opp in payload["opportunities"]:
        errors = validate(opp, schema)
        assert errors == [], f"{opp['opportunity_id']}: {errors}"


def test_technical_and_funding_priority_are_genuinely_independent_axes():
    """Il test che conta di piu': il ranking per technical_priority NON deve
    essere identico al ranking per funding_priority - altrimenti i due assi
    sarebbero de facto fusi, contraddicendo l'obiettivo esplicito del
    framework."""
    payload = build_opportunities()
    by_technical = sorted(payload["opportunities"], key=lambda o: -o["technical_priority"]["score"])
    by_funding = sorted(payload["opportunities"], key=lambda o: -o["funding_priority"]["score"])
    technical_order = [o["opportunity_id"] for o in by_technical]
    funding_order = [o["opportunity_id"] for o in by_funding]
    assert technical_order != funding_order, "i due ranking non devono essere identici"


def test_priority_queue_validates_against_schema():
    schema = _load_schema("opportunity-priority-queue.schema.json")
    payload = build_queue()
    errors = validate(payload, schema)
    assert errors == [], errors


def test_priority_queue_builder_is_deterministic():
    p1 = build_queue()
    p2 = build_queue()
    # generated_at cambia (volatile) - il resto no
    p1.pop("generated_at")
    p2.pop("generated_at")
    assert p1 == p2


def test_funding_can_finance_technical_is_never_auto_inferred():
    """funding_can_finance_technical deve essere dichiarato esplicitamente
    (None o una lista scritta a mano) - MAI calcolato da una correlazione
    statistica fra i due punteggi."""
    payload = build_queue()
    from build_opportunity_priority_queue import FUNDING_CAN_FINANCE_TECHNICAL
    for entry in payload["combined_view"]:
        oid = entry["opportunity_id"]
        expected = FUNDING_CAN_FINANCE_TECHNICAL.get(oid)
        assert entry["funding_can_finance_technical"] == expected


# ---------------------------------------------------------------------------
# NEXUS TASK #0006 - hardening: hard gates, capital scenarios, capability
# coverage, lifecycle fail-closed, no-fake-precision, brief generation.
# ---------------------------------------------------------------------------

def test_capability_coverage_covers_all_15_named_capabilities():
    coverage = compute_capability_coverage(["orchestrator", "voice"])
    assert set(coverage["per_capability"].keys()) == set(ALL_CAPABILITIES)
    assert len(ALL_CAPABILITIES) == 15


def test_capability_coverage_blockers_only_missing_or_external():
    """Bug trovato e corretto durante #0006: 'blockers' includeva anche lo
    stato PARTIAL, contraddicendo la descrizione dello schema stesso (solo
    MISSING/EXTERNAL_SERVICE_REQUIRED). Non deve ripresentarsi."""
    coverage = compute_capability_coverage(list(ALL_CAPABILITIES))
    for blocker_entry in coverage["blockers"]:
        cap, status = blocker_entry.split(": ")
        assert coverage["per_capability"][cap] == status
        assert status in ("MISSING", "EXTERNAL_SERVICE_REQUIRED"), (
            f"{cap} ha stato {status} ma e' finito nei blockers")
    partial_caps = [c for c, s in coverage["per_capability"].items() if s == "PARTIAL"]
    assert partial_caps, "il test presuppone che esista almeno una capacita' PARTIAL"
    assert not any(cap in b for cap in partial_caps for b in coverage["blockers"]), (
        "PARTIAL non deve mai comparire nei blockers")


def test_capability_coverage_not_required_marks_capabilities_outside_scope():
    coverage = compute_capability_coverage(["research"])
    assert coverage["per_capability"]["voice"] == "NOT_REQUIRED"
    assert coverage["per_capability"]["research"] != "NOT_REQUIRED"


def test_capital_scenarios_infeasible_opportunity_gets_zero_priority():
    dims = {"capital_required": "HIGH", "time_to_cash": "SHORT_LT_1M",
           "sales_difficulty": "LOW", "margin": "HIGH", "recurrence": "SUBSCRIPTION",
           "automation_level": "FULLY_AUTOMATED", "skills_available": "FULLY_AVAILABLE",
           "premium_tool_dependency": "NONE", "strategic_reuse": "HIGH", "risk": "LOW",
           "human_time_required": "MINIMAL"}
    _, breakdown = score_funding_priority(dims)
    scenarios = compute_capital_scenarios(dims, breakdown)
    assert scenarios["BOOTSTRAP_0_100"]["feasible"] is False
    assert scenarios["BOOTSTRAP_0_100"]["adjusted_funding_priority"] == 0.0
    assert scenarios["GROWTH_2000_PLUS"]["feasible"] is True


def test_capital_scenario_ceilings_are_ordered():
    order = ["NONE", "LOW", "MEDIUM", "HIGH"]
    levels = [SCENARIO_CEILING[k] for k in
             ("BOOTSTRAP_0_100", "BOOTSTRAP_100_500", "BOOTSTRAP_500_2000", "GROWTH_2000_PLUS")]
    assert [order.index(lv) for lv in levels] == sorted(order.index(lv) for lv in levels)


def test_hard_gate_legal_risk_beats_everything_else():
    """Un punteggio alto non deve MAI bypassare un flag legale/policy -
    requisito esplicito dell'utente in NEXUS TASK #0006 punto 3."""
    payload = build_opportunities()
    signal_opp = next(o for o in payload["opportunities"]
                      if o["opportunity_id"] == "OPP_MT5_STRATEGY_SIGNAL_SUBSCRIPTION")
    assert signal_opp["legal_or_policy_risk_flag"] is True
    assert signal_opp["hard_gate"] == "BLOCKED_BY_LEGAL_OR_POLICY_RISK"
    assert signal_opp["funding_priority"]["score"] > 50, (
        "il test ha senso solo se il punteggio SAREBBE stato alto senza il gate")


def test_hard_gate_precedence_order():
    base = dict(legal_or_policy_risk_flag=False,
              capital_scenarios={"BOOTSTRAP_0_100": {"feasible": True}},
              capability_coverage={"per_capability": {"voice": "AVAILABLE_NOW"}, "blockers": []},
              evidence_confidence="HIGH", has_next_cheapest_validation_step=True)
    assert compute_hard_gate(**{**base, "legal_or_policy_risk_flag": True}) == \
        "BLOCKED_BY_LEGAL_OR_POLICY_RISK"
    infeasible = {**base, "capital_scenarios": {"BOOTSTRAP_0_100": {"feasible": False}}}
    assert compute_hard_gate(**infeasible) == "BLOCKED_BY_CAPITAL"
    blocked_cap = {**base, "capability_coverage": {
        "per_capability": {"voice": "MISSING"}, "blockers": ["voice: MISSING"]}}
    assert compute_hard_gate(**blocked_cap) == "BLOCKED_BY_CAPABILITY"


def test_no_fake_precision_all_current_opportunities_are_provisional():
    """Nessuna opportunity nel dataset iniziale ha oggi dati di mercato
    reali - priority_status non deve MAI essere VALIDATED finche'
    input_type resta ASSUMPTION."""
    payload = build_opportunities()
    for opp in payload["opportunities"]:
        assert opp["input_type"] == "ASSUMPTION"
        assert opp["priority_status"] in ("PROVISIONAL", "HYPOTHESIS_BASED")
        assert opp["evidence_confidence"] != "VALIDATED"


def test_lifecycle_has_13_states_and_is_fail_closed():
    assert len(STATES) == 13
    assert ALLOWED_TRANSITIONS["SCALABLE"] == []
    assert ALLOWED_TRANSITIONS["REJECTED"] == []
    assert validate_transition("IDEA", "MARKET_TEST")[0] is False, (
        "nessun salto automatico da IDEA a MARKET_TEST")
    assert validate_transition("IDEA", "RESEARCH_REQUIRED")[0] is True


def test_lifecycle_definition_validates_against_schema():
    schema = _load_schema("opportunity-lifecycle.schema.json")
    payload = build_lifecycle_definition()
    errors = validate(payload, schema)
    assert errors == [], errors


def test_self_funding_loop_has_no_revenue_forecast():
    payload = build_self_funding_loop()
    assert len(payload["stages"]) == 9
    assert "forecast" not in payload["no_forecast_declaration"].lower() or \
        "non" in payload["no_forecast_declaration"].lower()
    schema = _load_schema("self-funding-loop.schema.json")
    errors = validate(payload, schema)
    assert errors == [], errors


def test_opportunity_brief_skeleton_validates_and_flags_blocker():
    payload = build_opportunities()
    opp = next(o for o in payload["opportunities"]
              if o["opportunity_id"] == "OPP_MT5_STRATEGY_SIGNAL_SUBSCRIPTION")
    skeleton = build_brief_skeleton(opp, "server/funding_v1/example_instances/"
                                   "opportunities_v1.json", "0" * 64)
    assert skeleton["main_blocker"] is not None
    assert skeleton["approval_required"] is not None
    schema = _load_schema("opportunity-brief.schema.json")
    skeleton_with_voice = {**skeleton, "short_voice_summary": "Placeholder di test."}
    errors = validate(skeleton_with_voice, schema)
    assert errors == [], errors


def test_routing_used_only_local_tiers_for_hypothesis_generation():
    """Verifica indipendente del requisito centrale di #0006 punto 14: le
    13 narrative devono essere state generate SENZA nessuna chiamata
    premium automatica."""
    narratives_path = os.path.join(ORCH_DIR, "nexus_task_0006_narratives_v1.json")
    with open(narratives_path, encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["tier_counts"].get("TIER1_LOCAL_CHEAP", 0) >= 1
    assert not any(k.startswith("TIER3") or k.startswith("TIER4") for k in doc["tier_counts"])
    assert all(v is not None for v in doc["results"].values()), (
        "tutte le 13 narrative devono essere state completate (eventualmente dopo retry "
        "del prompt/verificatore, mai inventate a mano)")


# ---------------------------------------------------------------------------
# NEXUS TASK #0007 - adozione del framework: pura governance, verificata per
# hash indipendente (nessuna modifica a scoring/gate/dataset ammessa).
# ---------------------------------------------------------------------------

def test_framework_adoption_decision_is_adopted_with_unmodified_logic():
    import hashlib
    adoption_path = os.path.join(FUNDING_DIR, "framework_adoption_decision_v1.json")
    with open(adoption_path, encoding="utf-8") as f:
        decision_doc = json.load(f)
    decision = decision_doc["payload"]
    canonical_payload = json.dumps(
        decision, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
    ).encode("utf-8")
    assert hashlib.sha256(canonical_payload).hexdigest() == decision_doc["canonical_sha256"]
    assert decision["new_status"] == "ADOPTED"
    assert decision["decision"] == "FUNDING_FRAMEWORK_V1_ADOPTED"
    assert all(v is False for v in decision["scope_declaration"].values()
              if isinstance(v, bool))
    for name, expected_hash in decision["frozen_logic_file_sha256"].items():
        with open(os.path.join(FUNDING_DIR, name), "rb") as f:
            # The frozen hashes describe the canonical Git content (LF).  A
            # Windows checkout may materialize the same blob with CRLF; hash
            # normalized bytes so the integrity assertion remains about the
            # source logic rather than the developer's core.autocrlf setting.
            canonical_bytes = f.read().replace(b"\r\n", b"\n")
            actual = hashlib.sha256(canonical_bytes).hexdigest()
        assert actual == expected_hash, f"{name} e' stato modificato dopo l'adozione"
