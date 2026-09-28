#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - contratto per job asincroni (Fase 11 del
task), pensato in primis per MT5 run:

    task richiede un run MT5
     -> crea un job (JOB_CREATED)
     -> il task RILASCIA il worker (non attende sincronamente)
     -> il run esegue indipendentemente
     -> RUN_COMPLETED (evento)
     -> viene creato un nuovo task di estrazione/verifica (TIER0)

Esplicitamente NON implementata l'esecuzione MT5 vera e propria in questa
fase (fuori scope, per istruzione esplicita del task: 'non serve
implementare tutto MT5 execution se aumenta troppo lo scope') - qui c'e'
SOLO il contratto/stato del job, utilizzabile da un worker MT5 reale in
futuro senza cambiare la forma."""
import json
import os
import sys
import uuid
from datetime import datetime, timezone

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.dirname(CORE_DIR)
RUNTIME_STATE_DIR = os.path.join(ORCH_DIR, "runtime_state")

sys.path.insert(0, ORCH_DIR)

JOB_STATES = ["CREATED", "RUNNING", "RUN_COMPLETED", "RUN_FAILED", "EXTRACTION_QUEUED"]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class AsyncJobStore:
    """Stesso pattern di persistenza di TaskQueue (JSON locale) - job
    separati dai task perche' un job MT5 non e' un TASK_MANIFEST_V1 (non ha
    required_capabilities/risk fields nello stesso senso), e' una risorsa
    esterna asincrona che un task puo' creare e da cui un altro task puo'
    dipendere."""

    def __init__(self, path=None):
        self.path = path or os.path.join(RUNTIME_STATE_DIR, "async_jobs_v1.json")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            self._save({})

    def _load(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_job(self, requesting_task_id, job_type, params):
        """Il task chiamante NON deve attendere: crea il job e puo'
        transizionare a WAITING_PROVIDER (o restare COMPLETED se il resto
        del suo lavoro e' gia' finito) - il job vive indipendentemente."""
        job_id = f"JOB_{uuid.uuid4().hex[:12].upper()}"
        data = self._load()
        data[job_id] = {"job_id": job_id, "requesting_task_id": requesting_task_id,
                       "job_type": job_type, "params": params, "state": "CREATED",
                       "created_at": _now_iso(), "updated_at": _now_iso(), "result": None,
                       "extraction_task_id": None}
        self._save(data)
        return data[job_id]

    def mark_running(self, job_id):
        return self._transition(job_id, "RUNNING")

    def mark_completed(self, job_id, result):
        return self._transition(job_id, "RUN_COMPLETED", result=result)

    def mark_failed(self, job_id, error):
        return self._transition(job_id, "RUN_FAILED", result={"error": error})

    def link_extraction_task(self, job_id, extraction_task_id):
        return self._transition(job_id, "EXTRACTION_QUEUED", extraction_task_id=extraction_task_id)

    def _transition(self, job_id, new_state, **updates):
        data = self._load()
        job = data[job_id]
        job["state"] = new_state
        job["updated_at"] = _now_iso()
        for k, v in updates.items():
            job[k] = v
        data[job_id] = job
        self._save(data)
        return job

    def get(self, job_id):
        return self._load()[job_id]

    def list_all(self):
        return list(self._load().values())
