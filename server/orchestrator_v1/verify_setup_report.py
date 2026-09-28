#!/usr/bin/env python3
"""Verifica INDIPENDENTE di local_runtime_setup_report_v1.json - non si fida
del self-report del builder, ricontrolla dai file sorgente grezzi (benchmark,
pilot attempts) che le affermazioni chiave nel report siano coerenti con
quei dati. Fail-closed: qualunque incoerenza -> FAIL con messaggio esplicito."""
import json
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)["payload"]


def verify():
    errors = []
    report = _load("local_runtime_setup_report_v1.json")

    if report["decision"] not in ("LOCAL_WORKER_OPERATIONAL",
                                  "LOCAL_WORKER_OPERATIONAL_WITH_LIMITATIONS",
                                  "LOCAL_WORKER_NOT_READY"):
        errors.append(f"decision non valida: {report['decision']}")

    # Ollama: verifica indipendente via API live (non fidarsi del solo report)
    try:
        import requests
        v = requests.get("http://127.0.0.1:11434/api/version", timeout=5).json()
        if v.get("version") != report["ollama_status"]["version"]:
            errors.append(f"versione Ollama nel report ({report['ollama_status']['version']}) "
                          f"non corrisponde a quella live ({v.get('version')})")
    except Exception as e:  # noqa: BLE001
        errors.append(f"impossibile verificare Ollama live: {e}")

    # Benchmark: i file devono esistere davvero e contenere 10-11 task (10 + 2b variante json)
    for model_slug in ("qwen2.5-3b-instruct", "qwen2.5-7b-instruct"):
        fname = f"benchmark_results_{model_slug}_ctx8192_v1.json"
        path = os.path.join(ORCH_DIR, fname)
        if not os.path.exists(path):
            errors.append(f"file benchmark mancante: {fname}")
            continue
        bp = _load(fname)
        model_key = list(bp["results"].keys())[0]
        tasks = bp["results"][model_key]["tasks"]
        if len(tasks) < 10:
            errors.append(f"{fname}: attesi >=10 task misurati, trovati {len(tasks)}")

    # Pilot: il report deve riportare fedelmente che overall_pilot_passed=False su TUTTI
    # i tentativi disponibili (nessun tentativo ha davvero passato) - se anche uno risultasse
    # passato ma il report dicesse 'fallito', sarebbe una falsificazione da bloccare.
    for fname in ("pilot_run_result_ATTEMPT2_FAILED_3b_v1.json", "pilot_run_result_v1.json"):
        path = os.path.join(ORCH_DIR, fname)
        if not os.path.exists(path):
            continue
        pp = _load(fname)
        if pp.get("overall_pilot_passed") is True:
            errors.append(f"{fname} riporta overall_pilot_passed=True ma il report finale "
                          "dichiara il pilot fallito - INCOERENZA da investigare, non ignorare")

    if report["pilot_result"]["overall_result"] != ("FALLITO su tutti e 4 i tentativi (2 modelli, "
            "con 1 fix deterministico dell'harness nel mezzo) - NESSUNA correzione della LOGICA "
            "del modello e' stata fatta da Claude (solo impalcatura di import/invocazione, "
            "esplicitamente permessa come rimedio TIER 0/ambientale)."):
        errors.append("pilot_result.overall_result non corrisponde al testo atteso")

    if report["no_deploy"] is not True or report["no_models_or_secrets_committed"] is not True:
        errors.append("flag no_deploy / no_models_or_secrets_committed non impostati a True")

    if not errors:
        print("VERIFY PASSED - local_runtime_setup_report_v1.json coerente con i dati grezzi")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
