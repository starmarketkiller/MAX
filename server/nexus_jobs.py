"""Coda di job durevole per i carichi computazionali.

L'audit ha classificato come P0 il fatto che backtest, optimizer e build della
strategy library girassero **dentro** la richiesta HTTP:

* AUD0-COMPUTE-001 / AUD0-BE-BT-001 — CPU-bound nel processo API: un client
  autenticato poteva affamare le rotte di controllo del trading.
* AUD0-COMPUTE-002 — spazio di ricerca senza tetto: esplosione combinatoria.
* AUD0-COMPUTE-003 — le eccezioni diventavano "nessun candidato valido".
* AUD0-COMPUTE-004 — i risultati mutavano lo stato operativo nel KV.
* AUD0-COMPUTE-005 — `GET /optimize/{job_id}` ignorava l'id e restituiva
  sempre l'ultimo risultato globale.
* AUD0-BE-BT-003 — nessun envelope di riproducibilità.
* AUD0-BE-BT-012 — la build della library rispondeva `queued` dopo aver già
  eseguito tutto in modo sincrono.

Il modulo è indipendente da FastAPI: riceve una connection factory e una
callable, e persiste ogni transizione.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional

SCHEMA_VERSION = 1

# Stati del job (coerenti con la spec A3.2).
JOB_QUEUED = "QUEUED"
JOB_RUNNING = "RUNNING"
JOB_SUCCEEDED = "SUCCEEDED"
JOB_FAILED = "FAILED"
JOB_CANCELLED = "CANCELLED"

TERMINAL_STATES = frozenset({JOB_SUCCEEDED, JOB_FAILED, JOB_CANCELLED})

#: AUD0-COMPUTE-002: tetto assoluto alle combinazioni di una ricerca.
MAX_SEARCH_COMBINATIONS = 2000

#: Quante esecuzioni concorrenti sono ammesse. Volutamente basso: la macchina
#: serve prima di tutto il control plane del trading.
DEFAULT_WORKERS = 2

#: Job attivi per utente, per evitare che uno solo saturi la coda.
MAX_ACTIVE_JOBS_PER_USER = 3


class JobRejected(ValueError):
    """Il job non può essere accettato (quota o dimensione)."""


class SearchSpaceTooLarge(JobRejected):
    def __init__(self, combinations: int, maximum: int):
        self.combinations = combinations
        self.maximum = maximum
        super().__init__(
            f"lo spazio di ricerca richiede {combinations} combinazioni, "
            f"massimo consentito {maximum}"
        )


def estimate_combinations(*dimensions: Any) -> int:
    """Cardinalità del prodotto cartesiano delle dimensioni fornite."""
    total = 1
    for dim in dimensions:
        try:
            size = len(dim)
        except TypeError:
            size = int(dim or 1)
        total *= max(1, size)
    return total


def guard_search_space(*dimensions: Any, maximum: int = MAX_SEARCH_COMBINATIONS) -> int:
    """Rifiuta prima di eseguire una ricerca troppo grande (AUD0-COMPUTE-002)."""
    combinations = estimate_combinations(*dimensions)
    if combinations > maximum:
        raise SearchSpaceTooLarge(combinations, maximum)
    return combinations


def manifest(payload: dict, *, engine_version: str, app_version: str,
             requested_by: str, extra: Optional[dict] = None) -> dict:
    """Envelope di riproducibilità di un job (AUD0-BE-BT-003).

    Senza questo, due esecuzioni dello stesso backtest non sono confrontabili
    e un risultato non può essere riprodotto in modo indipendente.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    out = {
        "schema_version": SCHEMA_VERSION,
        "app_version": app_version,
        "engine_version": engine_version,
        "requested_by": requested_by,
        "params_hash": hashlib.sha256(canonical.encode()).hexdigest(),
        "params": payload,
    }
    if extra:
        out.update(extra)
    return out


class JobStore:
    """Persistenza dei job su SQLite, con transizioni tracciate."""

    DDL = """
    CREATE TABLE IF NOT EXISTS compute_jobs (
        job_id        TEXT PRIMARY KEY,
        job_type      TEXT,
        status        TEXT,
        requested_by  TEXT,
        manifest      TEXT,
        result        TEXT,
        error         TEXT,
        progress      REAL DEFAULT 0,
        cancel_requested INTEGER DEFAULT 0,
        created_at    REAL,
        started_at    REAL,
        finished_at   REAL
    );
    CREATE INDEX IF NOT EXISTS idx_compute_jobs_owner
        ON compute_jobs(requested_by, created_at DESC);
    """

    def __init__(self, connect: Callable[[], Any]):
        self._connect = connect

    def init_schema(self) -> None:
        with self._connect() as c:
            c.executescript(self.DDL)

    def create(self, *, job_type: str, requested_by: str, job_manifest: dict) -> str:
        job_id = secrets.token_hex(8)
        with self._connect() as c:
            active = c.execute(
                "SELECT COUNT(*) FROM compute_jobs WHERE requested_by=? AND status IN (?,?)",
                (requested_by, JOB_QUEUED, JOB_RUNNING)).fetchone()[0]
            if active >= MAX_ACTIVE_JOBS_PER_USER:
                raise JobRejected(
                    f"hai già {active} job attivi (massimo {MAX_ACTIVE_JOBS_PER_USER}): "
                    "attendi o annullane uno")
            c.execute(
                "INSERT INTO compute_jobs(job_id,job_type,status,requested_by,manifest,"
                "progress,cancel_requested,created_at) VALUES(?,?,?,?,?,0,0,?)",
                (job_id, job_type, JOB_QUEUED, requested_by,
                 json.dumps(job_manifest, default=str), time.time()),
            )
        return job_id

    def mark_running(self, job_id: str) -> None:
        with self._connect() as c:
            c.execute("UPDATE compute_jobs SET status=?, started_at=? WHERE job_id=?",
                      (JOB_RUNNING, time.time(), job_id))

    def set_progress(self, job_id: str, progress: float) -> None:
        with self._connect() as c:
            c.execute("UPDATE compute_jobs SET progress=? WHERE job_id=?",
                      (max(0.0, min(1.0, float(progress))), job_id))

    def finish(self, job_id: str, *, status: str, result: Any = None,
               error: str = "") -> None:
        with self._connect() as c:
            c.execute(
                "UPDATE compute_jobs SET status=?, result=?, error=?, progress=1, "
                "finished_at=? WHERE job_id=?",
                (status, json.dumps(result, default=str) if result is not None else None,
                 error[:2000], time.time(), job_id),
            )

    def request_cancel(self, job_id: str, requested_by: str) -> bool:
        with self._connect() as c:
            row = c.execute("SELECT status, requested_by FROM compute_jobs WHERE job_id=?",
                            (job_id,)).fetchone()
            if not row:
                return False
            status, owner = row[0], row[1]
            # AUD0-COMPUTE-005: i job hanno un proprietario, non sono globali.
            if owner != requested_by:
                return False
            if status in TERMINAL_STATES:
                return False
            c.execute("UPDATE compute_jobs SET cancel_requested=1 WHERE job_id=?", (job_id,))
            if status == JOB_QUEUED:
                c.execute("UPDATE compute_jobs SET status=?, finished_at=? WHERE job_id=?",
                          (JOB_CANCELLED, time.time(), job_id))
        return True

    def cancel_requested(self, job_id: str) -> bool:
        with self._connect() as c:
            row = c.execute("SELECT cancel_requested FROM compute_jobs WHERE job_id=?",
                            (job_id,)).fetchone()
        return bool(row and row[0])

    def get(self, job_id: str) -> Optional[dict]:
        with self._connect() as c:
            row = c.execute("SELECT * FROM compute_jobs WHERE job_id=?", (job_id,)).fetchone()
        if not row:
            return None
        job = dict(row)
        for field in ("manifest", "result"):
            if job.get(field):
                try:
                    job[field] = json.loads(job[field])
                except Exception:
                    pass
        return job

    def list(self, requested_by: Optional[str] = None, limit: int = 50) -> list:
        query = "SELECT job_id,job_type,status,requested_by,progress,error," \
                "created_at,started_at,finished_at FROM compute_jobs"
        params: list = []
        if requested_by:
            query += " WHERE requested_by=?"
            params.append(requested_by)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, min(200, limit)))
        with self._connect() as c:
            return [dict(r) for r in c.execute(query, params)]

    def reap_orphans(self) -> int:
        """Un riavvio lascia job RUNNING senza worker: vanno chiusi.

        Dichiararli falliti è l'unica affermazione onesta: il processo che li
        eseguiva non esiste più e nessuno può provare che siano finiti.
        """
        with self._connect() as c:
            cur = c.execute(
                "UPDATE compute_jobs SET status=?, error=?, finished_at=? "
                "WHERE status IN (?,?)",
                (JOB_FAILED, "interrotto dal riavvio del backend", time.time(),
                 JOB_QUEUED, JOB_RUNNING))
        return cur.rowcount or 0


class JobRunner:
    """Esegue i job su un pool separato dal thread che serve le richieste."""

    def __init__(self, store: JobStore, workers: int = DEFAULT_WORKERS):
        self.store = store
        self._pool = ThreadPoolExecutor(max_workers=workers,
                                        thread_name_prefix="nexus-job")
        self._lock = threading.Lock()

    def submit(self, job_id: str, fn: Callable[[], Any]) -> None:
        self._pool.submit(self._run, job_id, fn)

    def _run(self, job_id: str, fn: Callable[[], Any]) -> None:
        if self.store.cancel_requested(job_id):
            self.store.finish(job_id, status=JOB_CANCELLED)
            return
        self.store.mark_running(job_id)
        try:
            result = fn()
        except Exception as exc:
            # AUD0-COMPUTE-003: le eccezioni venivano inghiottite e riportate
            # come "strategia senza risultati validi". Ora il job fallisce in
            # modo esplicito e la traccia resta nei log.
            print(f"[NEXUS][JOB] {job_id} fallito: {exc}\n{traceback.format_exc()[:2000]}")
            self.store.finish(job_id, status=JOB_FAILED, error=f"{type(exc).__name__}: {exc}")
            return
        if self.store.cancel_requested(job_id):
            self.store.finish(job_id, status=JOB_CANCELLED)
            return
        self.store.finish(job_id, status=JOB_SUCCEEDED, result=result)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
