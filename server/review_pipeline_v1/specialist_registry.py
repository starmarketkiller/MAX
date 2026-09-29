#!/usr/bin/env python3
"""NEXUS TASK #0008 punto 4/6 - Specialist Registry: legge
AGENT_CAPABILITY_REGISTRY_V1 (esteso in #0008 con specialist_role/
integration_status) per rispondere a 'chi puo' fare da SPECIALIST_ROLE X
adesso?' senza mai assumere disponibilita' permanente di un provider."""
import os
import sys

REVIEW_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.dirname(REVIEW_DIR)
ORCH_DIR = os.path.join(SERVER_DIR, "orchestrator_v1")
sys.path.insert(0, ORCH_DIR)
from core.capability import load_registry  # noqa: E402

SPECIALIST_ROLES = ["DETERMINISTIC", "LOCAL_GENERALIST", "SCIENTIFIC_RESEARCHER",
                   "CODE_SPECIALIST", "STRATEGIC_GENERALIST", "SECOND_OPINION",
                   "DEPLOYMENT_SPECIALIST"]

# Un provider e' "utilizzabile in automatico" solo se availability=ONLINE, il
# suo quota_state non e' esaurito/sconosciuto, e il connettore e' realmente
# configurato - fail-closed, mai simulato.
_USABLE_QUOTA_STATES = ("AVAILABLE", "LOW_QUOTA")
_USABLE_INTEGRATION_STATUSES = ("CONFIGURED", "AVAILABLE")


def _is_usable(agent):
    return (agent.get("availability") == "ONLINE"
           and agent.get("quota_state") in _USABLE_QUOTA_STATES
           and agent.get("integration_status") in _USABLE_INTEGRATION_STATUSES)


def find_specialists(role, *, registry=None):
    """Tutti gli agenti con questo specialist_role, i disponibili prima
    (mai un solo candidato hardcoded - punto 6: un provider indisponibile
    non deve bloccare il sistema se esiste un'alternativa compatibile)."""
    registry = registry or load_registry()
    candidates = [a for a in registry["agents"] if a.get("specialist_role") == role
                 or (role == "SECOND_OPINION" and a.get("specialist_role")
                     in ("SCIENTIFIC_RESEARCHER", "STRATEGIC_GENERALIST"))]
    candidates.sort(key=lambda a: (not _is_usable(a), a["agent_id"]))
    return candidates


def select_specialist(role, *, exclude_agent_ids=(), registry=None):
    """Ritorna (agent_or_None, status_dict). status_dict riflette SEMPRE lo
    stato reale osservato nel registry, mai un valore ottimistico assunto."""
    candidates = [a for a in find_specialists(role, registry=registry)
                 if a["agent_id"] not in exclude_agent_ids]
    if not candidates:
        return None, {"found": False, "reason": f"nessun agente con specialist_role={role}"}
    usable = [a for a in candidates if _is_usable(a)]
    chosen = usable[0] if usable else None
    status = {
        "found": True, "usable_now": bool(usable),
        "candidates": [{"agent_id": a["agent_id"], "availability": a.get("availability"),
                       "quota_state": a.get("quota_state"),
                       "integration_status": a.get("integration_status")} for a in candidates],
    }
    return chosen, status


def readiness_for_manual_delivery(role, *, registry=None):
    """NEXUS TASK #0008 punti 14-15 - quando nessun candidato e' usabile in
    automatico, il sistema deve poter dire 'ho preparato la richiesta, serve
    invio manuale' invece di bloccarsi silenziosamente o inventare una
    risposta. Ritorna sempre un agent_id anche se OFFLINE/NOT_CONFIGURED,
    cosi' il Review Context Packet sa per chi e' stato preparato."""
    candidates = find_specialists(role, registry=registry)
    if not candidates:
        return None
    return candidates[0]["agent_id"]
