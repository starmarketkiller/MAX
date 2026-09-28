#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - Router (Fase 3 del task).

Implementa ROUTING_POLICY_V1 esattamente come specificato in
docs/architecture/18_ORCHESTRATOR_AGENT_ROUTING_V1.md §5:

    IF deterministic workflow exists          -> TIER 0
    ELSE IF local capability sufficient
         AND risk acceptable                  -> TIER 1/2 (LOCAL)
    ELSE IF scientific reasoning required      -> TIER 3 (CLAUDE)
    ELSE IF complex multi-file coding required -> TIER 4 (CODEX)
    ELSE                                       -> LOCAL + VERIFIER

Le escalation premium (TIER3/TIER4) sono per ora SEMPRE manuali (Fase 3 del
task): il Router produce una decisione ESCALATION_REQUIRED con motivazione
e CONTEXT_PACKET_V1 gia' pronto, ma NON invoca mai Claude/Codex in
automatico - nessuna API key/chiamata automatica esiste in questo modulo."""
import sys
import os

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.dirname(CORE_DIR)
sys.path.insert(0, ORCH_DIR)

from core import deterministic_worker  # noqa: E402
from core.capability import find_capable_agents  # noqa: E402


class RouteDecision:
    def __init__(self, tier, executor=None, reason="", agent=None):
        self.tier = tier  # "TIER0_DETERMINISTIC" | "TIER1_LOCAL_CHEAP" | "TIER2_LOCAL_STRONG" |
                          # "ESCALATION_REQUIRED"
        self.executor = executor  # agent_id o "deterministic_worker"
        self.reason = reason
        self.agent = agent  # record completo dell'agente, se LOCAL

    def __repr__(self):
        return f"RouteDecision(tier={self.tier}, executor={self.executor}, reason={self.reason!r})"


def route(task_record):
    """Decide il tier per UN task, secondo l'ordine esatto della routing
    policy. Non esegue nulla - solo decide."""
    manifest = task_record["manifest"]
    action = task_record.get("action")

    # 1. Deterministic workflow exists?
    if action and action in deterministic_worker.ACTIONS:
        return RouteDecision("TIER0_DETERMINISTIC", executor="deterministic_worker",
                            reason=f"azione '{action}' e' un workflow deterministico noto - "
                                  "mai chiamare un modello per questo (§6 premium/local "
                                  "gating).")

    # 2. Local capability sufficient AND risk acceptable?
    capable_agents = find_capable_agents(manifest)
    if capable_agents:
        agent = capable_agents[0]  # gia' ordinati per cost_class, il piu' economico prima
        tier = "TIER2_LOCAL_STRONG" if "STRONG" in agent["agent_id"] else "TIER1_LOCAL_CHEAP"
        return RouteDecision(tier, executor=agent["agent_id"], agent=agent,
                            reason=f"'{agent['agent_id']}' supera il capability match "
                                  "(bake-off) per questo task_type/required_capabilities/"
                                  "risk_level.")

    # 3. Scientific reasoning required?
    if manifest["scientific_risk"] in ("MEDIUM", "HIGH"):
        return RouteDecision("ESCALATION_REQUIRED", executor="TIER3_CLAUDE",
                            reason=f"scientific_risk={manifest['scientific_risk']} - nessun "
                                  "agente locale puo' fare giudizio scientifico/causale per "
                                  "costruzione (§6).")

    # 4. Complex multi-file coding required?
    if manifest["code_risk"] == "HIGH" or manifest["estimated_complexity"] in ("LARGE", "XLARGE"):
        return RouteDecision("ESCALATION_REQUIRED", executor="TIER4_CODEX",
                            reason=f"code_risk={manifest['code_risk']}, "
                                  f"estimated_complexity={manifest['estimated_complexity']} - "
                                  "nessun agente locale ha dimostrato capacita' sufficiente "
                                  "nel bake-off per un refactor multi-file complesso.")

    # 5. Else -> nessun agente locale capace, ma il rischio non giustifica ancora
    #    un'escalation premium automatica - richiede revisione manuale (mai un
    #    'tanto vale tentare' silenzioso).
    return RouteDecision("ESCALATION_REQUIRED", executor="MANUAL_REVIEW",
                        reason="Nessun agente locale supera il capability match e il task non "
                              "rientra chiaramente in scientific_risk o code_risk alti - "
                              "classificazione ambigua, serve revisione umana (mai un tier "
                              "scelto a caso).")
