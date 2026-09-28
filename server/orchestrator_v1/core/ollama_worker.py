#!/usr/bin/env python3
"""NEXUS Orchestrator V1 Core - Ollama Local Worker (Fase 5 del task, TIER 1/2).

Vincoli imposti per costruzione (non opzionali, non bypassabili da un
parametro a caso):
- localhost only (127.0.0.1:11434 hardcoded, mai un host arbitrario);
- timeout delimitato (default 180s, configurabile per task piu' pesanti);
- un solo retry (applicato dal Router/retry_escalation, NON qui - questo
  modulo esegue UN tentativo, non decide se ritentare);
- structured JSON via format:json quando il chiamante lo richiede
  (affidabilita' dimostrata nel bake-off: raw_valid+extracted_valid sempre
  True con format:json, meno affidabile col prompt grezzo);
- un solo modello residente in RAM: _ensure_only_this_model_loaded() scarica
  ogni altro modello prima di chiamare - stesso fix OOM scoperto durante il
  bake-off (2 modelli residenti insieme hanno esaurito la RAM);
- nessun fallback cloud automatico (se Ollama non risponde, il chiamante
  riceve un errore esplicito, mai un tentativo silenzioso su un provider
  premium)."""
import json
import time

import requests

OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
OLLAMA_BASE = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
DEFAULT_MODEL = "ministral-3:3b"  # selezionato nel Local Model Bake-Off V1 - vedi
                                 # bakeoff_final_report_v1.json, decisione
                                 # LOCAL_MODEL_SELECTION_VALIDATED
KNOWN_MODELS = ["qwen2.5:3b-instruct", "qwen2.5:7b-instruct", "qwen3:4b", "ministral-3:3b",
               "gemma3:4b"]


def _unload_other_models(keep_model):
    for m in KNOWN_MODELS:
        if m == keep_model:
            continue
        try:
            requests.post(f"{OLLAMA_BASE}/api/generate", json={"model": m, "keep_alive": 0},
                         timeout=15)
        except Exception:  # noqa: BLE001 - best-effort, il modello potrebbe non essere caricato
            pass


def call_local_model(prompt, model=DEFAULT_MODEL, num_ctx=8192, timeout=180, json_mode=False,
                    ensure_single_resident=True):
    """Un SINGOLO tentativo (nessun retry qui - vedi core/retry_escalation.py).
    Ritorna sempre un dict, mai solleva un'eccezione di rete non gestita
    (un timeout/errore di connessione e' un ESITO, non un crash del
    chiamante - stessa lezione appresa e corretta nel pilot v2 della fase
    precedente)."""
    if ensure_single_resident:
        _unload_other_models(model)

    payload = {"model": model, "prompt": prompt, "stream": False, "options": {"num_ctx": num_ctx}}
    if json_mode:
        payload["format"] = "json"

    t0 = time.time()
    try:
        resp = requests.post(f"{OLLAMA_BASE}/api/generate", json=payload, timeout=timeout)
        wall = time.time() - t0
        data = resp.json()
    except Exception as e:  # noqa: BLE001
        return {"success": False, "response_text": None, "error": str(e),
               "wall_seconds": round(time.time() - t0, 2), "model": model}

    eval_count = data.get("eval_count")
    eval_duration_ns = data.get("eval_duration")
    tps = (eval_count / (eval_duration_ns / 1e9)) if eval_count and eval_duration_ns else None

    return {"success": True, "response_text": data.get("response", ""), "error": None,
           "wall_seconds": round(wall, 2), "model": model,
           "tokens_per_second": round(tps, 2) if tps else None,
           "eval_count": eval_count}


def is_ollama_reachable(timeout=5):
    try:
        r = requests.get(f"{OLLAMA_BASE}/api/version", timeout=timeout)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def try_parse_json(text):
    """Stessa logica gia' validata in build_model_benchmark.py -
    raw-parse-poi-estrazione-{...}."""
    raw = (text or "").strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except (json.JSONDecodeError, ValueError):
            pass
    return None
