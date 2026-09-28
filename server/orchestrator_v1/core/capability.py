#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - Capability enforcement (Fase 6 del task).

Il worker locale puo' ricevere SOLO task che corrispondono alle capacita'
DIMOSTRATE dal bake-off (server/orchestrator_v1/agent_capability_registry_v1.json)
- non alle capacita' teoriche del modello. Fail-closed: se un task chiede
una capability non nella lista dell'agente, o un task_type in
forbidden_task_types, il matching fallisce e il router deve escalare, mai
forzare l'esecuzione locale."""
import json
import os

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.dirname(CORE_DIR)


def load_registry():
    path = os.path.join(ORCH_DIR, "agent_capability_registry_v1.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["payload"]


class CapabilityMismatch:
    def __init__(self, agent_id, reasons):
        self.agent_id = agent_id
        self.reasons = reasons

    def __bool__(self):
        return False  # un mismatch e' sempre "falsy" - comodo per if match:

    def __repr__(self):
        return f"CapabilityMismatch({self.agent_id}, {self.reasons})"


class CapabilityMatch:
    def __init__(self, agent_id):
        self.agent_id = agent_id

    def __bool__(self):
        return True


def check_agent_for_task(agent, manifest):
    """Ritorna CapabilityMatch se l'agente puo' legittimamente eseguire questo
    task, altrimenti CapabilityMismatch con i motivi espliciti (mai un
    booleano nudo - i motivi servono per il RESULT_PACKET/escalation)."""
    reasons = []

    if agent["availability"] != "ONLINE":
        reasons.append(f"agente non ONLINE (availability={agent['availability']})")
    if agent["quota_state"] not in ("AVAILABLE",):
        reasons.append(f"quota non disponibile (quota_state={agent['quota_state']})")

    task_type = manifest["task_type"]
    if task_type in agent["forbidden_task_types"]:
        reasons.append(f"task_type '{task_type}' esplicitamente in forbidden_task_types")
    if task_type not in agent["allowed_task_types"]:
        reasons.append(f"task_type '{task_type}' non in allowed_task_types "
                       f"({agent['allowed_task_types']})")

    required = set(manifest["required_capabilities"])
    available = set(agent["capabilities"])
    missing = required - available
    if missing:
        reasons.append(f"capabilities richieste non dimostrate dal bake-off: {sorted(missing)}")

    # Risk gate (§5.2 della routing policy): un task ad alto rischio finanziario/
    # scientifico non puo' mai andare a un agente SANDBOXED.
    if manifest["financial_risk"] in ("MEDIUM", "HIGH") and agent["trust_level"] == "SANDBOXED":
        reasons.append(f"financial_risk={manifest['financial_risk']} incompatibile con "
                       f"trust_level=SANDBOXED")
    if manifest["scientific_risk"] in ("MEDIUM", "HIGH"):
        reasons.append(f"scientific_risk={manifest['scientific_risk']} richiede giudizio "
                       "scientifico - mai un agente locale per costruzione (§6 premium gating)")

    if reasons:
        return CapabilityMismatch(agent["agent_id"], reasons)
    return CapabilityMatch(agent["agent_id"])


def find_capable_agents(manifest, registry=None):
    """Ritorna la lista degli agent_id dell'AGENT_CAPABILITY_REGISTRY_V1 che
    superano il capability check per questo manifest, in ordine di
    cost_class (piu' economico prima) - §5.4 della routing policy."""
    registry = registry or load_registry()
    cost_rank = {"FREE": 0, "LOCAL_COMPUTE": 1, "CHEAP_PREMIUM": 2, "EXPENSIVE_PREMIUM": 3}
    matches = []
    for agent in registry["agents"]:
        result = check_agent_for_task(agent, manifest)
        if result:
            matches.append(agent)
    matches.sort(key=lambda a: cost_rank.get(a["cost_class"], 9))
    return matches
