#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - API read-only minimale (Fase 15 del task).

APIRouter FastAPI AUTONOMO, NON montato su server/app.py (7189 righe,
backend di produzione live per l'EA MQL5 + dashboard - fuori scope e
rischioso toccarlo qui). Questo modulo e' pensato per essere importato e
montato da Codex quando fara' l'integrazione UI/Product Platform vera
(Fase 15 del task: 'Codex fara' l'integrazione UI successivamente').

Espone SOLO lettura: task list/detail, queue, agents, ledger, escalation
requests - nessun endpoint di scrittura/azione in questa fase."""
import os
import sys

from fastapi import APIRouter, HTTPException

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.dirname(CORE_DIR)
sys.path.insert(0, ORCH_DIR)

from core.task_queue import TaskQueue  # noqa: E402
from core.ledger import EventLedger  # noqa: E402
from core.capability import load_registry  # noqa: E402

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator-readonly"])

_queue = TaskQueue()
_ledger = EventLedger()


@router.get("/tasks")
def list_tasks(state: str = None):
    tasks = _queue.list_all()
    if state:
        tasks = [t for t in tasks if t["state"] == state]
    return {"count": len(tasks), "tasks": tasks}


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    try:
        return _queue.get(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"task non trovato: {task_id}")


@router.get("/queue")
def queue_summary():
    tasks = _queue.list_all()
    by_state = {}
    for t in tasks:
        by_state.setdefault(t["state"], []).append(t["task_id"])
    return {"total": len(tasks), "by_state": by_state}


@router.get("/agents")
def list_agents():
    return load_registry()


@router.get("/ledger")
def ledger_events(task_id: str = None, limit: int = 200):
    events = _ledger.read_for_task(task_id) if task_id else _ledger.read_all()
    return {"count": len(events), "events": events[-limit:]}


@router.get("/escalations")
def list_escalations():
    tasks = _queue.list_by_state("ESCALATION_REQUIRED") + _queue.list_by_state("WAITING_APPROVAL")
    return {"count": len(tasks), "tasks": tasks}
