#!/usr/bin/env python3
"""Local Model Bake-Off V1 - Fase 5-9: benchmark NEXUS reale, ripetibile,
su un singolo modello per invocazione (per evitare contesa di risorse fra
processi Ollama su CPU-only 2 core). Esegue le categorie A-H definite in
bakeoff_tasks.py, con repeat per i task piu' decisivi (A, E), misura
performance reale (contatori ufficiali Ollama) e reliability (schema
compliance, hallucination euristica, constraint violation, coding pass rate).

Timeout deliberatamente piu' basso (180s testo / 240s coding) rispetto alla
fase precedente (che usava 600s): su questo hardware un task che non
completa in quella finestra e' gia' di per se' un dato di inaffidabilita'
pratica, non vale aspettare 10 minuti per ogni chiamata su 5 modelli x 17
task (vedi giustificazione nel report finale)."""
import json
import os
import subprocess
import sys
import time

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
BAKEOFF_SANDBOX_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_28")

sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

sys.path.insert(0, ORCH_DIR)
from bakeoff_tasks import build_tasks, REPEATED_TASKS, REPEAT_COUNT  # noqa: E402
from nxs_schema_validator import validate  # noqa: E402

import requests  # noqa: E402

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
CONTRACTS_DIR = os.path.join(ROOT, "contracts")

with open(os.path.join(CONTRACTS_DIR, "result-packet.schema.json"), encoding="utf-8") as f:
    RESULT_PACKET_SCHEMA = json.load(f)
with open(os.path.join(CONTRACTS_DIR, "task-manifest.schema.json"), encoding="utf-8") as f:
    TASK_MANIFEST_SCHEMA = json.load(f)


def _try_parse_json(text):
    raw = text.strip()
    for candidate in (raw, raw[raw.find("{"):raw.rfind("}") + 1] if "{" in raw and "}" in raw else ""):
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _call_ollama(model, prompt, num_ctx=8192, timeout=180):
    t0 = time.time()
    try:
        resp = requests.post(OLLAMA_URL, json={"model": model, "prompt": prompt, "stream": False,
                                               "options": {"num_ctx": num_ctx}}, timeout=timeout)
        wall = time.time() - t0
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        return {"error": str(e), "wall_seconds": round(time.time() - t0, 2), "response_text": ""}
    eval_count = data.get("eval_count")
    eval_duration_ns = data.get("eval_duration")
    tps = (eval_count / (eval_duration_ns / 1e9)) if eval_count and eval_duration_ns else None
    return {
        "response_text": data.get("response", ""), "wall_seconds": round(wall, 2),
        "eval_count_tokens_generated": eval_count,
        "tokens_per_second": round(tps, 2) if tps else None,
        "prompt_eval_count": data.get("prompt_eval_count"),
        "total_duration_seconds": round(data.get("total_duration", 0) / 1e9, 2) if data.get("total_duration") else None,
    }


def _extract_code(text, marker="def "):
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            if marker in p:
                return p.replace("python", "", 1).strip() if p.strip().startswith("python") else p.strip()
    return text


def _score_A(task_id, response_text):
    parsed = _try_parse_json(response_text)
    if parsed is None:
        return {"json_valid": False, "schema_valid": False, "schema_errors": ["JSON non parsabile"]}
    schema = RESULT_PACKET_SCHEMA if task_id.startswith("A1") else TASK_MANIFEST_SCHEMA
    errors = validate(parsed, schema)
    return {"json_valid": True, "schema_valid": len(errors) == 0, "schema_errors": errors[:10]}


def _score_B(response_text):
    said_not_available = "NOT_AVAILABLE" in response_text.upper()
    return {"correct_not_available": said_not_available,
           "hallucinated_outcome": (not said_not_available) and
                                  any(w in response_text for w in
                                      ["outcome", "risultato", "success", "fail", "COMPLETED"])}


def _score_C(response_text):
    has_format = all(k in response_text for k in ("ROOT_CAUSE", "CLASSIFICAZIONE", "NEXT_ACTION"))
    classification = None
    for line in response_text.splitlines():
        if "CLASSIFICAZIONE" in line.upper():
            classification = line.split(":", 1)[-1].strip() if ":" in line else line.strip()
    reasonable = classification is not None and "METODOLOGICO_SCIENTIFICO" not in (classification or "").upper()
    return {"format_followed": has_format, "classification": classification,
           "classification_reasonable": reasonable}


def _score_F1(response_text):
    text = response_text.lower()
    mentions_forbidden = "mql5" in text or "risk_utils" in text
    mentions_allowed = "phase7_28" in text or "helper.py" in text
    return {"constraint_violated": mentions_forbidden, "correct_file_chosen": mentions_allowed and not mentions_forbidden}


def _score_F2(response_text):
    text_low = response_text.lower()
    refused_to_invent = any(w in text_low for w in [
        "unknown", "non disponibil", "non ho dati", "non esiste", "sconosciut",
        "non posso confermare", "nessun dato", "non ci sono dati", "non ci sono",
        "non e' possibile", "non e possibile", "non puo' essere confrontat",
        "non puo essere confrontat", "manca", "non abbiamo dati", "non e' presente",
        "non sono disponibili"])
    fabricated_claim = any(w in text_low for w in ["e' migliore", "e migliore", "supera", "meglio del",
                                                   "e' peggiore"]) and not refused_to_invent
    return {"refused_to_invent": refused_to_invent, "fabricated_claim": fabricated_claim}


def _score_H(response_text):
    steps_present = all(s in response_text for s in
                        ("STEP1_READ", "STEP2_ANALYZE", "STEP3_ARTIFACT", "STEP4_VERIFY"))
    parsed = _try_parse_json(response_text)
    artifact_valid = isinstance(parsed, dict) and "candidate_id" in parsed and "outcome_summary" in parsed
    return {"all_steps_present": steps_present, "embedded_artifact_json_valid": artifact_valid}


def _reference_win_rate(trades):
    if not trades:
        return 0.0
    return sum(1 for t in trades if t["net_pnl"] > 0) / len(trades)


def _run_E1(model, response_text):
    code = _extract_code(response_text, "def win_rate")
    os.makedirs(BAKEOFF_SANDBOX_DIR, exist_ok=True)
    test_trades = [{"net_pnl": 10.0}, {"net_pnl": -5.0}, {"net_pnl": 3.0}, {"net_pnl": -1.0}]
    expected = _reference_win_rate(test_trades)
    invocation = f"\nprint(win_rate({test_trades!r}))\n"
    path = os.path.join(BAKEOFF_SANDBOX_DIR, f"_bakeoff_{model.replace(':', '-')}_e1_winrate.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code + invocation)
    try:
        r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=30,
                          cwd=BAKEOFF_SANDBOX_DIR)
        passed = False
        if r.returncode == 0:
            try:
                got = float(r.stdout.strip().splitlines()[-1])
                passed = abs(got - expected) < 1e-9
            except (ValueError, IndexError):
                passed = False
        return {"returncode": r.returncode, "stdout": r.stdout[-500:], "stderr": r.stderr[-500:],
               "expected": expected, "coding_pass": passed}
    except subprocess.TimeoutExpired:
        return {"coding_pass": False, "error": "timeout esecuzione sandbox (30s)"}


def _run_E2(model, response_text):
    code = _extract_code(response_text, "def ")
    os.makedirs(BAKEOFF_SANDBOX_DIR, exist_ok=True)
    path = os.path.join(BAKEOFF_SANDBOX_DIR, f"_bakeoff_{model.replace(':', '-')}_e2_test.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    try:
        r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=30,
                          cwd=BAKEOFF_SANDBOX_DIR)
        passed = r.returncode == 0 and "OK" in r.stdout
        return {"returncode": r.returncode, "stdout": r.stdout[-500:], "stderr": r.stderr[-500:],
               "coding_pass": passed}
    except subprocess.TimeoutExpired:
        return {"coding_pass": False, "error": "timeout esecuzione sandbox (30s)"}


def run_bakeoff_for_model(model):
    tasks = build_tasks()
    results = {}
    for task_id, prompt in tasks.items():
        n_runs = REPEAT_COUNT if task_id in REPEATED_TASKS else 1
        timeout = 240 if task_id.startswith("E") else 180
        runs = []
        for i in range(n_runs):
            call = _call_ollama(model, prompt, timeout=timeout)
            entry = {"run_index": i, **call}
            text = call.get("response_text", "")
            if task_id.startswith("A"):
                entry["scoring"] = _score_A(task_id, text)
            elif task_id == "B_artifact_reasoning":
                entry["scoring"] = _score_B(text)
            elif task_id == "C_log_analysis":
                entry["scoring"] = _score_C(text)
            elif task_id == "E1_small_fix":
                entry["scoring"] = _run_E1(model, text)
            elif task_id == "E2_add_test":
                entry["scoring"] = _run_E2(model, text)
            elif task_id == "F1_files_constraint":
                entry["scoring"] = _score_F1(text)
            elif task_id == "F2_no_push_no_invent":
                entry["scoring"] = _score_F2(text)
            elif task_id == "H_multi_step":
                entry["scoring"] = _score_H(text)
            runs.append(entry)
            print(f"  [{model}] {task_id} run{i}: "
                 f"{call.get('tokens_per_second', 'ERR')} tok/s, {call.get('wall_seconds', '?')}s, "
                 f"scoring={entry.get('scoring')}")
        results[task_id] = runs
    return results


ALL_CANDIDATE_MODELS = ["qwen2.5:3b-instruct", "qwen2.5:7b-instruct", "qwen3:4b",
                       "ministral-3:3b", "gemma3:4b"]


def _unload_other_models(keep_model):
    """Scarica esplicitamente ogni altro modello candidato dalla RAM prima di
    iniziare - scoperto in questa fase che il keep_alive di default di Ollama
    (5 minuti) puo' lasciare 2+ modelli residenti insieme fra un'invocazione
    dello script e la successiva, esaurendo la RAM su questo hardware (~20GB
    totali) con modelli anche piccoli (Q4, 2-5GB l'uno)."""
    for m in ALL_CANDIDATE_MODELS:
        if m == keep_model:
            continue
        try:
            requests.post(OLLAMA_URL, json={"model": m, "keep_alive": 0}, timeout=15)
        except Exception:  # noqa: BLE001 - best-effort, il modello potrebbe non essere caricato
            pass


def main():
    model = sys.argv[1]
    _unload_other_models(model)
    payload = {"model": model, "results": run_bakeoff_for_model(model),
              "measurement_note": "Misura empirica reale, timeout 180s/240s deliberatamente piu' "
                                 "bassi della fase precedente - un task che non completa in quella "
                                 "finestra e' gia' un dato di inaffidabilita' pratica su questo "
                                 "hardware."}
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, f"bakeoff_results_{model.replace(':', '-')}_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")


if __name__ == "__main__":
    main()
