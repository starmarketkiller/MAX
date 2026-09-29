#!/usr/bin/env python3
"""Verifica INDIPENDENTE di NEXUS TASK #0006 (Funding Framework Completion
& Hardening) - non si fida del self-report: ricalcola hard gates/capital
scenarios/capability coverage/score da zero, ricontrolla ogni artifact
contro il proprio schema, e verifica che la generazione delle 13
INITIAL_HYPOTHESIS sia avvenuta solo via TIER0/TIER1 locale (nessuna
chiamata premium automatica). Fail-closed."""
import json
import os
import subprocess
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
FUNDING_DIR = os.path.join(ROOT, "server", "funding_v1")
CONTRACTS_DIR = os.path.join(ROOT, "contracts")

sys.path.insert(0, FUNDING_DIR)
sys.path.insert(0, ORCH_DIR)

_FORBIDDEN_PHRASES = ["garantito", "sicuramente", "certamente redditizio", "validato dal "
                     "mercato", "domanda confermata", "dati di mercato mostrano",
                     "e' un edge", "ha gia' clienti"]


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def verify():
    errors = []
    from nxs_schema_validator import validate
    from opportunity_scoring import score_funding_priority, score_technical_priority
    from capability_coverage import compute_capability_coverage, ALL_CAPABILITIES
    from capital_scenarios import compute_capital_scenarios
    from hard_gates import compute_hard_gate
    from opportunity_lifecycle import STATES, ALLOWED_TRANSITIONS

    opp_schema = _load(os.path.join(CONTRACTS_DIR, "opportunity.schema.json"))
    opportunities = _load(os.path.join(FUNDING_DIR, "example_instances",
                                      "opportunities_v1.json"))["payload"]["opportunities"]

    if len(opportunities) != 18:
        errors.append(f"attese 18 opportunity (5 #0005 + 13 #0006), trovate {len(opportunities)}")

    for opp in opportunities:
        oid = opp["opportunity_id"]
        schema_errors = validate(opp, opp_schema)
        if schema_errors:
            errors.append(f"{oid}: {schema_errors}")

        recomputed_funding, funding_breakdown = score_funding_priority(opp["dimensions"])
        recomputed_technical, _ = score_technical_priority(opp["technical_priority"]["criteria"])
        if abs(recomputed_funding - opp["funding_priority"]["score"]) > 1e-6:
            errors.append(f"{oid}: funding_priority salvato non corrisponde al ricalcolo")
        if abs(recomputed_technical - opp["technical_priority"]["score"]) > 1e-6:
            errors.append(f"{oid}: technical_priority salvato non corrisponde al ricalcolo")

        recomputed_coverage = compute_capability_coverage(opp["required_capabilities"])
        if recomputed_coverage != opp["capability_coverage"]:
            errors.append(f"{oid}: capability_coverage salvata non corrisponde al ricalcolo")

        recomputed_scenarios = compute_capital_scenarios(opp["dimensions"], funding_breakdown)
        if recomputed_scenarios != opp["capital_scenario_priorities"]:
            errors.append(f"{oid}: capital_scenario_priorities salvati non corrispondono al "
                         "ricalcolo")

        recomputed_gate = compute_hard_gate(
            legal_or_policy_risk_flag=opp["legal_or_policy_risk_flag"],
            capital_scenarios=recomputed_scenarios, capability_coverage=recomputed_coverage,
            evidence_confidence=opp["evidence_confidence"],
            has_next_cheapest_validation_step=bool(opp["next_cheapest_validation_step"]))
        if recomputed_gate != opp["hard_gate"]:
            errors.append(f"{oid}: hard_gate salvato ({opp['hard_gate']}) non corrisponde al "
                         f"ricalcolo ({recomputed_gate})")

        if opp["input_type"] == "ASSUMPTION" and opp["priority_status"] not in (
                "PROVISIONAL", "HYPOTHESIS_BASED"):
            errors.append(f"{oid}: input_type=ASSUMPTION ma priority_status="
                         f"{opp['priority_status']} - fake precision")
        if opp["evidence_confidence"] == "VALIDATED":
            errors.append(f"{oid}: evidence_confidence=VALIDATED non atteso in questo dataset "
                         "(nessun dato di mercato reale raccolto finora)")

    # Il gate legale deve avere la precedenza assoluta sul punteggio (#0006 punto 3).
    signal_opp = next((o for o in opportunities
                      if o["opportunity_id"] == "OPP_MT5_STRATEGY_SIGNAL_SUBSCRIPTION"), None)
    if signal_opp is None:
        errors.append("OPP_MT5_STRATEGY_SIGNAL_SUBSCRIPTION mancante dal dataset")
    elif signal_opp["hard_gate"] != "BLOCKED_BY_LEGAL_OR_POLICY_RISK":
        errors.append("OPP_MT5_STRATEGY_SIGNAL_SUBSCRIPTION non ha hard_gate="
                     "BLOCKED_BY_LEGAL_OR_POLICY_RISK nonostante legal_or_policy_risk_flag=True")

    if len(STATES) != 13:
        errors.append(f"lifecycle: attesi 13 stati, trovati {len(STATES)}")
    if ALLOWED_TRANSITIONS.get("SCALABLE") != [] or ALLOWED_TRANSITIONS.get("REJECTED") != []:
        errors.append("lifecycle: SCALABLE/REJECTED devono essere stati terminali ([])")
    if len(ALL_CAPABILITIES) != 15:
        errors.append(f"attese 15 capacita' nominate, trovate {len(ALL_CAPABILITIES)}")

    # Artifact canonici: schema + presenza.
    for schema_name, instance_path, label in [
        ("opportunity-priority-queue.schema.json",
         os.path.join(FUNDING_DIR, "opportunity_priority_queue_v1.json"), "priority queue"),
        ("opportunity-lifecycle.schema.json",
         os.path.join(FUNDING_DIR, "example_instances", "opportunity_lifecycle_v1.json"),
         "lifecycle"),
        ("self-funding-loop.schema.json",
         os.path.join(FUNDING_DIR, "example_instances", "self_funding_loop_v1.json"),
         "self-funding loop"),
    ]:
        schema = _load(os.path.join(CONTRACTS_DIR, schema_name))
        payload = _load(instance_path)["payload"]
        schema_errors = validate(payload, schema)
        if schema_errors:
            errors.append(f"{label}: {schema_errors}")

    brief_schema = _load(os.path.join(CONTRACTS_DIR, "opportunity-brief.schema.json"))
    briefs_doc = _load(os.path.join(FUNDING_DIR, "opportunity_briefs_v1.json"))["payload"]
    if len(briefs_doc["briefs"]) != 18:
        errors.append(f"attesi 18 brief, trovati {len(briefs_doc['briefs'])}")
    for brief in briefs_doc["briefs"]:
        schema_errors = validate(brief, brief_schema)
        if schema_errors:
            errors.append(f"brief {brief['opportunity_id']}: {schema_errors}")
        text = brief["short_voice_summary"]
        if any(c in text for c in ("*", "#", "`", "[", "]")):
            errors.append(f"brief {brief['opportunity_id']}: short_voice_summary contiene "
                         "markdown/simboli")
        if any(p in text.lower() for p in _FORBIDDEN_PHRASES):
            errors.append(f"brief {brief['opportunity_id']}: short_voice_summary contiene "
                         "un'affermazione di mercato non supportata")

    # Narrative generate da Ministral: nessuna chiamata premium, nessun markdown, nessun
    # risultato mancante, nessuna frase di mercato non supportata.
    narratives_doc = _load(os.path.join(ORCH_DIR, "nexus_task_0006_narratives_v1.json"))
    tier_counts = narratives_doc["tier_counts"]
    if any(k.startswith("TIER3") or k.startswith("TIER4") for k in tier_counts):
        errors.append(f"tier_counts contiene escalation premium: {tier_counts}")
    if sum(tier_counts.values()) < 13:
        errors.append(f"attesi almeno 13 task instradati, tier_counts={tier_counts}")
    for oid, narrative in narratives_doc["results"].items():
        if narrative is None:
            errors.append(f"{oid}: narrativa mancante - non deve essere stata inventata da "
                         "Claude al posto del worker")
            continue
        text = " ".join(narrative.values())
        if any(c in text for c in ("*", "#", "`")):
            errors.append(f"{oid}: narrativa contiene markdown")
        if any(p in text.lower() for p in _FORBIDDEN_PHRASES):
            errors.append(f"{oid}: narrativa contiene un'affermazione di mercato non supportata")

    proc = subprocess.run([sys.executable, "-m", "pytest", "server/tests/test_funding_v1.py",
                          "-q"], capture_output=True, text=True, cwd=ROOT, timeout=120)
    if proc.returncode != 0:
        errors.append(f"test_funding_v1.py non passa: {proc.stdout[-1500:]}")

    if not errors:
        print("VERIFY PASSED - NEXUS TASK #0006 coerente (18 opportunity, hard gates/capital "
             "scenarios/capability coverage ricalcolati indipendentemente, lifecycle/self-"
             "funding-loop/brief validati contro schema, 0 escalation premium nella "
             "generazione delle 13 INITIAL_HYPOTHESIS, nessuna fake precision)")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
