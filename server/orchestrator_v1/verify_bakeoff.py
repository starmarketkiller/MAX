#!/usr/bin/env python3
"""Verifica INDIPENDENTE del bake-off - non si fida del self-report, ricontrolla
dai file grezzi che le affermazioni chiave del report finale siano coerenti.
Fail-closed."""
import json
import math
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))


def _load(fname):
    with open(os.path.join(ORCH_DIR, fname), encoding="utf-8") as f:
        return json.load(f)["payload"]


def _deep_isclose(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a.keys()) == set(b.keys()) and all(_deep_isclose(a[k], b[k]) for k in a)
    return a == b


def verify():
    errors = []
    report = _load("bakeoff_final_report_v1.json")

    if report["decision"] not in ("LOCAL_MODEL_SELECTION_VALIDATED", "CURRENT_MODEL_REMAINS_BEST",
                                  "LOCAL_AGENT_CAPABILITY_IMPROVED_BUT_LIMITED",
                                  "INSUFFICIENT_HARDWARE_FOR_USEFUL_TIER2"):
        errors.append(f"decisione non valida: {report['decision']}")

    # Il modello selezionato deve davvero essere il primo in classifica nella scorecard.
    scorecard = _load("bakeoff_scorecard_v1.json")
    top_model = scorecard["ranked_by_weighted_score"][0][0]
    if report["13_selected_local_fast"] != top_model:
        errors.append(f"LOCAL_FAST selezionato ({report['13_selected_local_fast']}) non "
                     f"corrisponde al primo in classifica scorecard ({top_model})")

    # qwen3:4b deve essere l'ultimo in classifica (squalifica per timeout) - fail-closed se
    # qualcuno lo promuovesse per errore.
    ranked = dict(scorecard["ranked_by_weighted_score"])
    if "qwen3:4b" in ranked and ranked["qwen3:4b"] >= 0.6:
        errors.append(f"qwen3:4b ha score {ranked['qwen3:4b']} >= 0.6 - atteso decisamente "
                     "basso per l'88% di timeout rate osservato nel bake-off grezzo")

    # Ricontrolla il timeout rate di qwen3:4b direttamente dal file grezzo.
    qwen3_raw = _load("bakeoff_results_qwen3-4b_v1.json")
    all_runs = [r for runs in qwen3_raw["results"].values() for r in runs]
    timeouts = sum(1 for r in all_runs if r.get("error") and "timed out" in str(r["error"]).lower())
    timeout_rate = timeouts / len(all_runs)
    if timeout_rate < 0.5:
        errors.append(f"timeout_rate qwen3:4b ricalcolato dai dati grezzi ({timeout_rate:.2f}) "
                     "e' inferiore a 0.5 - non coerente con la squalifica dichiarata nel report")

    # Il pilot v2 corretto deve davvero passare 4/4 se la decisione e' VALIDATED.
    pilot = _load("pilot_run_v2_result_CORRECTED_v1.json")
    if report["decision"] == "LOCAL_MODEL_SELECTION_VALIDATED" and not pilot["overall_pilot_passed"]:
        errors.append("decisione LOCAL_MODEL_SELECTION_VALIDATED ma pilot_run_v2_result_"
                     "CORRECTED_v1.json riporta overall_pilot_passed=False")

    # Ricalcola indipendentemente il match tolerante per ogni sotto-task del pilot corretto,
    # dai raw parsed_output/expected_output - non fidarsi del campo booleano gia' scritto.
    for strat, tasks in pilot["attempts"].items():
        for task_name, a in tasks.items():
            if a["parsed_output"] is not None:
                recomputed = _deep_isclose(a["parsed_output"], a["expected_output"])
                if recomputed != a["pilot_task_passed"] and a["execution"]["returncode"] == 0:
                    errors.append(f"{strat}/{task_name}: pilot_task_passed dichiarato "
                                 f"{a['pilot_task_passed']} ma il ricalcolo indipendente del "
                                 f"match tollerante da' {recomputed}")

    # Gemma3 non deve comparire come tool-capable (verificato via runtime stesso, non solo probe).
    toolcalling = _load("toolcalling_probe_results_v1.json")
    gemma_class = toolcalling["results"].get("gemma3:4b", {}).get("classification")
    if gemma_class == "TOOL_USE_CAPABLE":
        errors.append("gemma3:4b classificato TOOL_USE_CAPABLE ma Ollama riporta esplicitamente "
                     "'does not support tools' per questo modello (verificato via curl diretto)")

    # Registry deve validare contro lo schema.
    sys.path.insert(0, ORCH_DIR)
    from nxs_schema_validator import validate  # noqa: E402
    ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
    with open(os.path.join(ROOT, "contracts", "agent-capability-registry.schema.json"),
             encoding="utf-8") as f:
        schema = json.load(f)
    registry = _load("agent_capability_registry_v1.json")
    schema_errors = validate(registry, schema)
    if schema_errors:
        errors.append(f"agent_capability_registry_v1.json non valida contro lo schema: {schema_errors[:5]}")

    if not errors:
        print("VERIFY PASSED - bakeoff_final_report_v1.json coerente con i dati grezzi")
        return True
    print("VERIFY FAILED:")
    for e in errors:
        print(f"  - {e}")
    return False


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
