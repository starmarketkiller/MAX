#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - Deterministic Worker (Fase 4 del task, TIER 0).

Regola fondamentale: se un task e' risolvibile deterministicamente, il
Router non deve MAI chiamare Ministral - questo modulo e' quindi il primo
tentativo per ogni task, prima di considerare TIER 1/2.

Ogni azione ritorna un dict uniforme:
    {"success": bool, "output": <qualcosa>, "errors": [str], "files_read": [...],
     "files_changed": [...], "tools_or_commands": [...]}
cosi' il Router/RESULT_PACKET builder non deve sapere nulla dei dettagli di
ogni singola azione."""
import hashlib
import json
import os
import subprocess
import sys

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR = os.path.dirname(CORE_DIR)
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))

sys.path.insert(0, ORCH_DIR)
from nxs_schema_validator import validate  # noqa: E402


def _base_result():
    return {"success": False, "output": None, "errors": [], "files_read": [],
           "files_changed": [], "tools_or_commands": []}


def run_pytest(test_path, extra_args=None, timeout=120):
    """Esegue pytest su un path specifico - non l'intera suite per default
    (troppo lento/rumoroso per un singolo task orchestrato)."""
    r = _base_result()
    cmd = [sys.executable, "-m", "pytest", test_path, "-q"] + (extra_args or [])
    r["tools_or_commands"].append(" ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        r["errors"].append(f"pytest timeout dopo {timeout}s")
        return r
    r["output"] = {"returncode": proc.returncode, "stdout": proc.stdout[-4000:],
                  "stderr": proc.stderr[-2000:]}
    r["success"] = proc.returncode == 0
    if not r["success"]:
        r["errors"].append(f"pytest returncode={proc.returncode}")
    return r


def run_verifier(verifier_script, args=None, timeout=60):
    """Esegue uno script verify_*.py indipendente (convenzione gia' stabilita
    in tutto il progetto) e interpreta returncode 0 = PASS."""
    r = _base_result()
    path = os.path.join(ROOT, verifier_script) if not os.path.isabs(verifier_script) else verifier_script
    if not os.path.exists(path):
        r["errors"].append(f"verifier non trovato: {verifier_script}")
        return r
    cmd = [sys.executable, path] + (args or [])
    r["tools_or_commands"].append(" ".join(cmd))
    r["files_read"].append(os.path.relpath(path, ROOT))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        r["errors"].append(f"verifier timeout dopo {timeout}s")
        return r
    r["output"] = {"returncode": proc.returncode, "stdout": proc.stdout[-2000:],
                  "stderr": proc.stderr[-1000:]}
    r["success"] = proc.returncode == 0
    if not r["success"]:
        r["errors"].append(f"verifier returncode={proc.returncode}")
    return r


def validate_json_schema(instance_path, schema_path):
    r = _base_result()
    try:
        with open(instance_path, encoding="utf-8") as f:
            instance = json.load(f)
            instance = instance.get("payload", instance)
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        r["errors"].append(str(e))
        return r
    r["files_read"] = [instance_path, schema_path]
    errors = validate(instance, schema)
    r["output"] = {"schema_errors": errors[:20]}
    r["success"] = len(errors) == 0
    if errors:
        r["errors"] = [f"{len(errors)} errori di validazione schema"]
    return r


def rebuild_registry(builder_script, timeout=60):
    """Esegue un build_*.py esistente (convenzione gia' stabilita in tutto il
    progetto per ricostruire un registry/artifact deterministico) - MAI
    scrive logica nuova qui, solo invoca lo script gia' esistente."""
    r = _base_result()
    path = os.path.join(ROOT, builder_script) if not os.path.isabs(builder_script) else builder_script
    if not os.path.exists(path):
        r["errors"].append(f"builder non trovato: {builder_script}")
        return r
    cmd = [sys.executable, path]
    r["tools_or_commands"].append(" ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        r["errors"].append(f"builder timeout dopo {timeout}s")
        return r
    r["output"] = {"returncode": proc.returncode, "stdout": proc.stdout[-2000:]}
    r["success"] = proc.returncode == 0
    if not r["success"]:
        r["errors"].append(f"builder returncode={proc.returncode}: {proc.stderr[-500:]}")
    return r


def check_file_hash(path, expected_sha256=None):
    r = _base_result()
    full = os.path.join(ROOT, path) if not os.path.isabs(path) else path
    if not os.path.exists(full):
        r["errors"].append(f"file non trovato: {path}")
        return r
    r["files_read"].append(path)
    with open(full, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    r["output"] = {"sha256": digest, "exists": True}
    if expected_sha256 is not None:
        r["success"] = digest == expected_sha256
        if not r["success"]:
            r["errors"].append(f"hash mismatch: atteso {expected_sha256[:16]}..., trovato "
                              f"{digest[:16]}...")
    else:
        r["success"] = True
    return r


def check_files_exist(paths):
    r = _base_result()
    missing = [p for p in paths if not os.path.exists(os.path.join(ROOT, p))]
    r["files_read"] = paths
    r["success"] = len(missing) == 0
    r["output"] = {"missing": missing}
    if missing:
        r["errors"].append(f"file mancanti: {missing}")
    return r


def run_metric_builder(builder_script, timeout=120):
    """Alias esplicito di rebuild_registry - stessa meccanica (esegue uno
    script deterministico gia' esistente), nome separato per chiarezza
    semantica nel RESULT_PACKET (un metric builder non e' concettualmente
    un registry, anche se il meccanismo di esecuzione e' identico)."""
    return rebuild_registry(builder_script, timeout=timeout)


def git_status_diff(paths=None):
    r = _base_result()
    cmd_status = ["git", "status", "--short"] + (paths or [])
    r["tools_or_commands"].append(" ".join(cmd_status))
    proc = subprocess.run(cmd_status, capture_output=True, text=True, cwd=ROOT)
    cmd_diff = ["git", "diff"] + (paths or [])
    r["tools_or_commands"].append(" ".join(cmd_diff))
    proc_diff = subprocess.run(cmd_diff, capture_output=True, text=True, cwd=ROOT)
    r["output"] = {"status": proc.stdout, "diff": proc_diff.stdout[-4000:]}
    r["success"] = proc.returncode == 0 and proc_diff.returncode == 0
    if not r["success"]:
        r["errors"].append("git status/diff returncode != 0")
    return r


def verify_artifact(artifact_path, required_keys=None):
    """'Artifact verification' generica: il file esiste, e' JSON valido, ha
    un blob 'payload' e (opzionale) contiene le chiavi richieste - NON
    interpreta il contenuto scientificamente (principio gia' stabilito:
    Control Plane non deriva mai verdetti)."""
    r = _base_result()
    full = os.path.join(ROOT, artifact_path) if not os.path.isabs(artifact_path) else artifact_path
    if not os.path.exists(full):
        r["errors"].append(f"artifact non trovato: {artifact_path}")
        return r
    r["files_read"].append(artifact_path)
    try:
        with open(full, encoding="utf-8") as f:
            doc = json.load(f)
    except json.JSONDecodeError as e:
        r["errors"].append(f"JSON non valido: {e}")
        return r
    if "payload" not in doc:
        r["errors"].append("manca il blob 'payload' (provenance canonica attesa)")
        return r
    missing = [k for k in (required_keys or []) if k not in doc["payload"]]
    r["output"] = {"has_payload": True, "missing_required_keys": missing}
    r["success"] = len(missing) == 0
    if missing:
        r["errors"].append(f"chiavi richieste mancanti nel payload: {missing}")
    return r


ACTIONS = {
    "run_pytest": run_pytest, "run_verifier": run_verifier,
    "validate_json_schema": validate_json_schema, "rebuild_registry": rebuild_registry,
    "check_file_hash": check_file_hash, "check_files_exist": check_files_exist,
    "run_metric_builder": run_metric_builder, "git_status_diff": git_status_diff,
    "verify_artifact": verify_artifact,
}


def execute(action, params):
    if action not in ACTIONS:
        r = _base_result()
        r["errors"].append(f"azione deterministica sconosciuta: {action} (disponibili: "
                          f"{sorted(ACTIONS)})")
        return r
    return ACTIONS[action](**params)
