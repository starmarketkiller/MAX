#!/usr/bin/env python3
"""Local Model Bake-Off V1 - Fase 10: scorecard pesata a partire dai risultati
grezzi di build_bakeoff_benchmark.py (+ build_toolcalling_probe.py). Pesi
maggiori su reliability/structured-output/coding/constraint-compliance/
hallucination-resistance, minori su latenza pura - per istruzione esplicita
del task ("non selezionare il modello piu' intelligente in assoluto se sul
PC e' troppo lento o instabile")."""
import os
import sys

ORCH_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(ORCH_DIR, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402

MODELS = ["qwen2.5:3b-instruct", "qwen2.5:7b-instruct", "qwen3:4b", "ministral-3:3b", "gemma3:4b"]

WEIGHTS = {
    "schema_compliance_rate": 0.20,
    "coding_pass_rate": 0.15,
    "hallucination_resistance": 0.15,
    "constraint_compliance": 0.15,
    "success_rate": 0.10,
    "consistency": 0.10,
    "instruction_following": 0.10,
    "latency_score": 0.05,
}


def _load_bakeoff(model):
    fname = f"bakeoff_results_{model.replace(':', '-')}_v1.json"
    path = os.path.join(ORCH_DIR, fname)
    if not os.path.exists(path):
        return None
    return load_json(path)["payload"]


def _load_toolcalling():
    path = os.path.join(ORCH_DIR, "toolcalling_probe_results_v1.json")
    if not os.path.exists(path):
        return {}
    return load_json(path)["payload"]["results"]


def _flatten_runs(results):
    for task_id, runs in results.items():
        for r in runs:
            yield task_id, r


def compute_metrics(model, bakeoff, tool_result):
    all_runs = list(_flatten_runs(bakeoff["results"]))
    total_calls = len(all_runs)
    errored = [r for k, r in all_runs if r.get("error")]
    timeouts = [r for r in errored if "timeout" in str(r.get("error", "")).lower()
               or "timed out" in str(r.get("error", "")).lower()]
    success_rate = 1 - (len(errored) / total_calls) if total_calls else 0.0
    timeout_rate = len(timeouts) / total_calls if total_calls else 0.0

    a_runs = [r for k, r in all_runs if k.startswith("A")]
    json_valid_rate = (sum(1 for r in a_runs if r.get("scoring", {}).get("json_valid")) / len(a_runs)
                       if a_runs else 0.0)
    schema_compliance_rate = (sum(1 for r in a_runs if r.get("scoring", {}).get("schema_valid")) / len(a_runs)
                             if a_runs else 0.0)

    e_runs = [r for k, r in all_runs if k.startswith("E")]
    coding_pass_rate = (sum(1 for r in e_runs if r.get("scoring", {}).get("coding_pass")) / len(e_runs)
                       if e_runs else 0.0)

    b_run = next((r for k, r in all_runs if k == "B_artifact_reasoning"), None)
    hallucinated_b = bool(b_run and b_run.get("scoring", {}).get("hallucinated_outcome"))
    f2_run = next((r for k, r in all_runs if k == "F2_no_push_no_invent"), None)
    fabricated_f2 = bool(f2_run and f2_run.get("scoring", {}).get("fabricated_claim"))
    hallucination_events = int(hallucinated_b) + int(fabricated_f2)
    hallucination_resistance = 1 - (hallucination_events / 2)

    f1_run = next((r for k, r in all_runs if k == "F1_files_constraint"), None)
    f1_violated = bool(f1_run and f1_run.get("scoring", {}).get("constraint_violated"))
    constraint_compliance = 0.0 if f1_violated else 1.0

    c_run = next((r for k, r in all_runs if k == "C_log_analysis"), None)
    h_run = next((r for k, r in all_runs if k == "H_multi_step"), None)
    instr_events = [bool(c_run and c_run.get("scoring", {}).get("format_followed")),
                   bool(h_run and h_run.get("scoring", {}).get("all_steps_present")),
                   bool(h_run and h_run.get("scoring", {}).get("embedded_artifact_json_valid"))]
    instruction_following = sum(instr_events) / len(instr_events)

    from bakeoff_tasks import REPEATED_TASKS
    consistency_checks = []
    for task_id in REPEATED_TASKS:
        runs = bakeoff["results"].get(task_id, [])
        if len(runs) < 2:
            continue
        if task_id.startswith("A"):
            vals = [r.get("scoring", {}).get("schema_valid") for r in runs]
        else:
            vals = [r.get("scoring", {}).get("coding_pass") for r in runs]
        consistency_checks.append(1.0 if len(set(vals)) == 1 else 0.0)
    consistency = sum(consistency_checks) / len(consistency_checks) if consistency_checks else 0.0

    wall_times = [r["wall_seconds"] for k, r in all_runs if r.get("wall_seconds") is not None]
    avg_wall = sum(wall_times) / len(wall_times) if wall_times else None
    tps_values = [r["tokens_per_second"] for k, r in all_runs if r.get("tokens_per_second")]
    avg_tps = sum(tps_values) / len(tps_values) if tps_values else None
    latency_score = max(0.0, 1 - min((avg_wall or 200) / 120, 1)) if avg_wall is not None else 0.0

    tool_classification = tool_result.get("classification", "NOT_TESTED") if tool_result else "NOT_TESTED"

    return {
        "total_calls": total_calls, "errored_calls": len(errored), "timeout_calls": len(timeouts),
        "success_rate": round(success_rate, 3), "timeout_rate": round(timeout_rate, 3),
        "json_valid_rate": round(json_valid_rate, 3),
        "schema_compliance_rate": round(schema_compliance_rate, 3),
        "coding_pass_rate": round(coding_pass_rate, 3),
        "hallucination_resistance": round(hallucination_resistance, 3),
        "constraint_compliance": round(constraint_compliance, 3),
        "instruction_following": round(instruction_following, 3),
        "consistency": round(consistency, 3),
        "avg_wall_seconds": round(avg_wall, 2) if avg_wall else None,
        "avg_tokens_per_second": round(avg_tps, 2) if avg_tps else None,
        "latency_score": round(latency_score, 3),
        "tool_use_classification": tool_classification,
    }


def build_scorecard():
    tool_results = _load_toolcalling()
    scorecard = {}
    for model in MODELS:
        bakeoff = _load_bakeoff(model)
        if bakeoff is None:
            scorecard[model] = {"available": False}
            continue
        metrics = compute_metrics(model, bakeoff, tool_results.get(model))
        weighted_score = sum(WEIGHTS[k] * metrics[k] for k in WEIGHTS if k in metrics)
        scorecard[model] = {"available": True, "metrics": metrics,
                            "weighted_score": round(weighted_score, 4)}
    return scorecard


MANUAL_CORRECTIONS = {
    "gemma3:4b": {
        "reason": "Verifica manuale (Claude) del testo grezzo di B_artifact_reasoning: il "
                 "modello NON ha risposto NOT_AVAILABLE (corretto) ma ha invece generato una "
                 "stringa fabbricata mescolando/misattribuendo l'outcome del PRIMO candidato "
                 "(quello completato) al candidato SBAGLIATO (quello ancora pending, senza "
                 "outcome) - una vera allucinazione con un'etichetta plausibile ma falsa, non "
                 "rilevata dall'euristica automatica (basata su keyword letterali assenti in "
                 "quella risposta specifica). Inoltre Ollama riporta esplicitamente "
                 "'gemma3:4b does not support tools' (verificato via curl diretto) - nessun "
                 "supporto nativo di tool-calling in questa configurazione.",
        "hallucination_resistance_corrected": 0.5,
        "tool_use_classification_corrected": "NO_NATIVE_TOOL_SUPPORT (confermato dal runtime "
                                            "stesso, non solo dal probe)",
    },
}


def apply_manual_corrections(scorecard):
    for model, correction in MANUAL_CORRECTIONS.items():
        if model not in scorecard or not scorecard[model].get("available"):
            continue
        metrics = scorecard[model]["metrics"]
        old_hr = metrics["hallucination_resistance"]
        metrics["hallucination_resistance"] = correction["hallucination_resistance_corrected"]
        metrics["tool_use_classification"] = correction["tool_use_classification_corrected"]
        new_score = sum(WEIGHTS[k] * metrics[k] for k in WEIGHTS if k in metrics)
        scorecard[model]["weighted_score_before_manual_correction"] = scorecard[model]["weighted_score"]
        scorecard[model]["weighted_score"] = round(new_score, 4)
        scorecard[model]["manual_correction_applied"] = correction["reason"]
        print(f"  CORREZIONE MANUALE {model}: hallucination_resistance {old_hr} -> "
             f"{correction['hallucination_resistance_corrected']}, score "
             f"{scorecard[model]['weighted_score_before_manual_correction']} -> {scorecard[model]['weighted_score']}")
    return scorecard


def main():
    scorecard = build_scorecard()
    scorecard = apply_manual_corrections(scorecard)
    ranked = sorted([(m, d["weighted_score"]) for m, d in scorecard.items() if d.get("available")],
                    key=lambda x: -x[1])
    payload = {"weights": WEIGHTS, "scorecard": scorecard,
              "ranked_by_weighted_score": ranked,
              "methodology_note": "Pesi maggiori su reliability/structured-output/coding/"
                                 "constraint-compliance/hallucination-resistance, peso minore "
                                 "sulla sola latenza - coerente con l'istruzione esplicita di "
                                 "non premiare il modello piu' 'intelligente' se instabile/lento "
                                 "su questo hardware specifico."}
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(ORCH_DIR, "bakeoff_scorecard_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path}")
    for m, score in ranked:
        print(f"  {m}: {score}")


if __name__ == "__main__":
    main()
