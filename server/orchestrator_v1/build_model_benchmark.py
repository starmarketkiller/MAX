#!/usr/bin/env python3
"""Orchestrator V1 - Local Runtime Setup, punto C: benchmark REALE (non
stimato) di qwen2.5:3b-instruct e qwen2.5:7b-instruct su 10 task
rappresentative NEXUS, via l'API HTTP locale di Ollama (127.0.0.1:11434,
non esposta pubblicamente - verificato). Misura tempo/first-token,
tokens/sec (dai contatori ufficiali eval_count/eval_duration di Ollama,
non stimati), RAM di sistema prima/dopo, validita' JSON dove richiesto.

NON deterministico in senso Phase-7 (le risposte di un LLM variano) -
questo script produce una MISURA empirica, non un artifact canonico
ricostruibile bit-per-bit. Salvato comunque con provenance/hash per
tracciabilita' di QUANDO e COME e' stata presa la misura."""
import json
import os
import subprocess
import sys
import time

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

import requests  # noqa: E402

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODELS = ["qwen2.5:3b-instruct", "qwen2.5:7b-instruct"]

TASKS = [
    {"id": "1_simple_response", "prompt": "Rispondi con una sola parola: quanto fa 7 piu' 5?"},
    {"id": "2_result_packet_json", "prompt": (
        "Genera un oggetto JSON valido che rispetti ESATTAMENTE questi campi (nessun altro "
        "campo, nessun testo fuori dal JSON): task_id, executor, decision, confidence "
        "(uno fra HIGH, MEDIUM, LOW, UNKNOWN), tests (oggetto con ran, passed, failed). "
        "task_id='TASK_TEST_1', executor='local-model', decision='COMPLETED', "
        "confidence='MEDIUM', tests.ran=true, tests.passed=3, tests.failed=0.")},
    {"id": "3_artifact_summary", "prompt": (
        "Riassumi in massimo 2 frasi in italiano questo JSON: "
        '{"decision": "EDGE_CANDIDATE_REQUIRES_FORWARD_VALIDATION", "n_trades": 42, '
        '"net_expectancy_per_trade": 25.63, "profit_factor": 1.48, '
        '"concentration_top5_pct": 127.4}')},
    {"id": "4_log_analysis", "prompt": (
        "Analizza questo output di test e rispondi SOLO col nome del test fallito e il motivo "
        "in una riga:\n"
        "FAILED server/tests/test_research_control_plane_v2.py::"
        "test_safety_net_registries_are_projected_without_reinterpretation - "
        "assert 9 == 8")},
    {"id": "5_small_python_fix", "prompt": (
        "Scrivi SOLO il codice Python (nessuna spiegazione) di una funzione "
        "`is_count_at_least(actual, minimum)` che ritorna True se actual >= minimum.")},
    {"id": "6_propose_patch", "prompt": (
        "In un test pytest c'e' la riga `assert model[\"overview\"][\"hypothesis_count\"] == 8` "
        "che ora fallisce perche' il conteggio reale e' 9 (un registry che cresce nel tempo). "
        "Proponi SOLO la riga di codice corretta che dovrebbe sostituirla, senza spiegazioni.")},
    {"id": "7_instruction_following", "prompt": (
        "Rispondi con ESATTAMENTE 3 punti elenco, ognuno di massimo 6 parole, "
        "sull'importanza dei test automatici. Nessun testo prima o dopo i 3 punti.")},
    {"id": "8_italian", "prompt": "Spiega in italiano, in una frase, cos'e' un profit factor."},
    {"id": "9_english", "prompt": "Explain in English, in one sentence, what a profit factor is."},
    {"id": "10_longer_context", "prompt": None},  # popolato dinamicamente sotto
]


def _build_long_context_prompt(n_lines=400):
    """Contesto sintetico (non un vero artifact - solo per misurare il
    comportamento a contesto piu' lungo, dichiarato). n_lines=400 -> circa
    4K token; n_lines=800 -> circa 8K token (verificato empiricamente via
    prompt_eval_count, non solo stimato a priori)."""
    salt = os.environ.get("NXS_BENCH_SALT", "")  # forza contenuto NUOVO (no cache-hit su prefissi
                                                 # gia' visti) per una misura onesta 'warm model,
                                                 # cold context' invece di 'warm model, warm context'
    filler = " ".join([f"Riga di log {salt}numero {i}: evento OK, nessuna anomalia rilevata."
                       for i in range(1, n_lines)])
    half = n_lines // 2
    return (f"Ecco un log lungo:\n{filler}\n\nAll'interno di questo log, SOLO UNA riga contiene "
           "la parola 'ANOMALIA_TARGET_XYZ'. Trovala e riportane il numero. "
           f"Riga di log numero {half}: ANOMALIA_TARGET_XYZ rilevata qui.\n{filler}\n\n"
           "Rispondi SOLO col numero della riga che contiene ANOMALIA_TARGET_XYZ.")


def _free_ram_gb():
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
        "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
        capture_output=True, text=True)
    try:
        return round(int(out.stdout.strip()) / 1024 / 1024, 2)
    except ValueError:
        return None


def _call_ollama(model, prompt, num_ctx=8192, timeout=600, json_mode=False):
    payload = {"model": model, "prompt": prompt, "stream": False,
              "options": {"num_ctx": num_ctx}}
    if json_mode:
        payload["format"] = "json"
    t0 = time.time()
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        wall_seconds = time.time() - t0
        data = resp.json()
    except Exception as e:  # noqa: BLE001 - misura empirica, cattura tutto e riporta
        return {"error": str(e), "wall_seconds": time.time() - t0}

    eval_count = data.get("eval_count")
    eval_duration_ns = data.get("eval_duration")
    prompt_eval_duration_ns = data.get("prompt_eval_duration")
    tokens_per_sec = (eval_count / (eval_duration_ns / 1e9)) if eval_count and eval_duration_ns else None

    return {
        "response_text": data.get("response", ""),
        "wall_seconds": round(wall_seconds, 2),
        "total_duration_seconds": round(data.get("total_duration", 0) / 1e9, 2) if data.get("total_duration") else None,
        "load_duration_seconds": round(data.get("load_duration", 0) / 1e9, 2) if data.get("load_duration") else None,
        "prompt_eval_count": data.get("prompt_eval_count"),
        "prompt_eval_duration_seconds": round(prompt_eval_duration_ns / 1e9, 2) if prompt_eval_duration_ns else None,
        "eval_count_tokens_generated": eval_count,
        "eval_duration_seconds": round(eval_duration_ns / 1e9, 2) if eval_duration_ns else None,
        "tokens_per_second": round(tokens_per_sec, 2) if tokens_per_sec else None,
    }


def run_benchmark(models=None, num_ctx=8192, long_context_lines=400):
    models = models or MODELS
    tasks = [dict(t) for t in TASKS]
    for t in tasks:
        if t["id"] == "10_longer_context":
            t["prompt"] = _build_long_context_prompt(long_context_lines)

    results = {}
    for model in models:
        ram_before = _free_ram_gb()
        model_results = []
        for t in tasks:
            r = _call_ollama(model, t["prompt"], num_ctx=num_ctx)
            r["task_id"] = t["id"]
            if t["id"] == "2_result_packet_json":
                r["json_valid"] = _try_parse_json(r.get("response_text", ""))
                r2 = _call_ollama(model, t["prompt"], num_ctx=num_ctx, json_mode=True)
                r2["task_id"] = "2b_result_packet_json_format_json_mode"
                r2["json_valid"] = _try_parse_json(r2.get("response_text", ""))
                model_results.append(r2)
                print(f"  [{model}] 2b_..._format_json_mode: "
                     f"{r2.get('tokens_per_second', 'ERR')} tok/s, "
                     f"json_valid={r2['json_valid']}")
            model_results.append(r)
            print(f"  [{model}] {t['id']}: "
                 f"{r.get('tokens_per_second', 'ERR')} tok/s, "
                 f"{r.get('wall_seconds', '?')}s totali")
        ram_after = _free_ram_gb()
        results[model] = {"tasks": model_results, "free_ram_gb_before": ram_before,
                          "free_ram_gb_after": ram_after,
                          "ram_delta_gb": (round(ram_before - ram_after, 2)
                                          if ram_before and ram_after else None)}
    return results


def _try_parse_json(text):
    """Prova prima il testo grezzo, poi estrae il primo blocco {...} (i modelli
    spesso anteponendo prosa/markdown fence al JSON, es. 'Ecco il JSON:\n```json\n{...}\n```')
    - riporta ENTRAMBI gli esiti (raw vs extracted) perche' la differenza e' essa stessa
    un dato utile su quanto il modello sia 'pulito' nell'output strutturato."""
    raw = text.strip()
    raw_valid = False
    try:
        json.loads(raw)
        raw_valid = True
    except (json.JSONDecodeError, ValueError):
        pass
    start, end = raw.find("{"), raw.rfind("}")
    extracted_valid = False
    if start != -1 and end != -1 and end > start:
        try:
            json.loads(raw[start:end + 1])
            extracted_valid = True
        except (json.JSONDecodeError, ValueError):
            pass
    return {"raw_valid": raw_valid, "extracted_valid": extracted_valid}


def main():
    num_ctx = int(sys.argv[1]) if len(sys.argv) > 1 else 8192
    models = sys.argv[2:] if len(sys.argv) > 2 else MODELS
    print(f"Benchmark su {models}, num_ctx={num_ctx}")
    results = run_benchmark(models, num_ctx=num_ctx)
    payload = {"num_ctx": num_ctx, "models_tested": models, "results": results,
              "measurement_note": "Misura empirica reale (non stimata) - le risposte di un LLM "
                                 "variano, questo NON e' un artifact deterministico in senso "
                                 "Phase-7, salvato per tracciabilita' di quando/come e' stata presa "
                                 "la misura."}
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    suffix = "_".join(m.replace(":", "-") for m in models) + f"_ctx{num_ctx}"
    out_path = os.path.join(ORCH_DIR, f"benchmark_results_{suffix}_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")


if __name__ == "__main__":
    main()
