#!/usr/bin/env python3
"""Phase 7.2B sec.2/6 - Applica sequence_semantic_leakage_guard.py alle
20 sequence esistenti, aggiunge i campi espliciti di timing
(observation_cutoff/transition_completion_time/prediction_start/
outcome_window/branch_group_id) a market_sequence_registry_v1.json, e
produce sequence_semantic_leakage_guard_v1.json col dettaglio per
sequenza. Nessun dato NEXUS coinvolto - gli offset sono simbolici
(barre relative a event_a), usati solo per verificare la COERENZA
temporale dichiarata nell'ontologia."""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE72_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_2")
sys.path.insert(0, PHASE72_DIR)
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from sequence_semantic_leakage_guard import check_sequence_leakage, PASS, FAIL, NEEDS_REFORMULATION  # noqa: E402
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

# Per-sequence: (transition_completion_offset AS DESCRITTO ORIGINARIAMENTE,
#                prediction_start_offset AS DESCRITTO ORIGINARIAMENTE,
#                outcome_window_start_offset AS DESCRITTO ORIGINARIAMENTE,
#                outcome_measures_same_event_as_trigger,
#                branch_group_id o None,
#                note_extra o None)
# N = 10 simbolico (es. reclaim_horizon/orizzonte dichiarato) - solo per
# preservare l'ORDINE relativo, non un valore NEXUS.
N = 10
AS_DESCRIBED = {
    "SEQ-0001": (0, 0, 1, False, None, None),
    "SEQ-0002": (0, 0, 1, False, None, None),
    "SEQ-0003": (1, 0, 1, False, "CBG-0002", None),
    "SEQ-0004": (1, 0, 1, False, "CBG-0002", None),
    "SEQ-0005": (1, 0, 1, False, None, None),
    "SEQ-0006": (0, 0, 1, False, None, None),
    "SEQ-0007": (0, 0, 1, False, None, None),
    "SEQ-0008": (0, 0, 1, False, None, None),
    "SEQ-0009": (0, 0, 1, False, None, None),
    "SEQ-0010": (N, 0, 1, False, "CBG-0001", None),
    "SEQ-0011": (N, 0, 1, False, "CBG-0001", None),
    "SEQ-0012": (N, 0, 1, False, "CBG-0001", "Il ramo e' definito dall'ASSENZA di reclaim entro l'intero orizzonte - non confermabile prima che l'orizzonte sia scaduto."),
    "SEQ-0013": (N, 0, 1, False, None, None),
    "SEQ-0014": (0, 0, 1, False, None, None),
    "SEQ-0015": (0, 0, 1, False, None, None),
    "SEQ-0016": (0, 0, 1, False, None, None),
    "SEQ-0017": (1, 0, 1, False, None, "Gia' NOT_IMPLEMENTABLE_AS_DESCRIBED per gap dati (value area) - leakage secondario."),
    "SEQ-0018": (1, 0, 1, False, None, "Gia' NOT_IMPLEMENTABLE_AS_DESCRIBED per gap dati (VWAP) - leakage secondario."),
    "SEQ-0019": (0, 0, 1, False, None, "Gia' NOT_IMPLEMENTABLE_AS_DESCRIBED per assenza di un secondo strumento - nessun problema di leakage proprio."),
    "SEQ-0020": (0, 0, 1, False, None, None),
}


def main():
    path = os.path.join(PHASE72_DIR, "market_sequence_registry_v1.json")
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    sequences = doc["sequences"]

    guard_results = []
    for seq in sequences:
        sid = seq["sequence_id"]
        t_completion, p_start, w_start, same_event, branch_id, extra_note = AS_DESCRIBED[sid]
        verdict, reason = check_sequence_leakage(t_completion, p_start, w_start, same_event)

        # Se FAIL o NEEDS_REFORMULATION (e non gia' bloccata da un gap dati
        # indipendente), la correzione minima e' allineare prediction_start
        # al completamento della transition.
        if verdict != PASS:
            corrected_prediction_start = t_completion
            corrected_outcome_window_start = t_completion + 1
            verdict_corrected, _ = check_sequence_leakage(t_completion, corrected_prediction_start, corrected_outcome_window_start, same_event)
        else:
            corrected_prediction_start = p_start
            corrected_outcome_window_start = w_start
            verdict_corrected = PASS

        guard_results.append({
            "sequence_id": sid, "mechanism_id": seq["mechanism_id"],
            "as_described_verdict": verdict, "as_described_reason": reason,
            "transition_completion_offset": t_completion,
            "prediction_start_offset_as_described": p_start,
            "outcome_window_start_offset_as_described": w_start,
            "corrected_prediction_start_offset": corrected_prediction_start,
            "corrected_outcome_window_start_offset": corrected_outcome_window_start,
            "verdict_after_correction": verdict_corrected,
            "extra_note": extra_note,
        })

        # Applica i campi corretti alla sequence (l'ontologia che entra in
        # Phase 7.3 e' quella CORRETTA, non quella originariamente ambigua).
        seq["observation_cutoff"] = "event_a bar close (t=0)"
        seq["transition_completion_time"] = f"t={t_completion}" + (" (variabile, entro l'orizzonte dichiarato)" if t_completion == N else "")
        seq["prediction_start"] = f"t={corrected_prediction_start} (corretto per essere >= transition_completion_time)"
        seq["outcome_window"] = f"da t={corrected_outcome_window_start}"
        seq["branch_group_id"] = branch_id
        seq["semantic_leakage_status_original"] = verdict
        seq["semantic_leakage_status_after_correction"] = verdict_corrected

        if verdict != PASS:
            seq["reformulation_note"] = (
                f"Integrity Patch Phase 7.2B: la formulazione originale implicava prediction_start=t={p_start}, "
                f"ma la transition/terminal_state si risolve solo a t={t_completion} - corretto esplicitamente a "
                f"prediction_start=t={corrected_prediction_start}, outcome_window da t={corrected_outcome_window_start}. "
                + (extra_note or "")
            )
            if seq["implementation_status"] == "READY_FOR_FORMALIZATION":
                seq["implementation_status"] = "NEEDS_ADDITIONAL_SPECIFICATION"

    save_json(path, {"schema_version": doc["schema_version"], "registry_id": doc["registry_id"],
                      "conforms_to": doc["conforms_to"], "principle": doc["principle"], "sequences": sequences})
    # market_sequence_registry_v1.json non usa wrap_with_provenance (Phase 7.2 originale l'ha scritto
    # come JSON piatto) - manteniamo lo stesso stile per non introdurre un'incoerenza di formato qui.

    n_pass = sum(1 for r in guard_results if r["as_described_verdict"] == PASS)
    n_needs_reform = sum(1 for r in guard_results if r["as_described_verdict"] == NEEDS_REFORMULATION)
    n_fail = sum(1 for r in guard_results if r["as_described_verdict"] == FAIL)

    guard_payload = {
        "n_sequences_checked": len(guard_results), "n_pass": n_pass,
        "n_needs_reformulation": n_needs_reform, "n_fail": n_fail,
        "results": guard_results,
        "note": "Verifica di COERENZA TEMPORALE dichiarata nell'ontologia (offset simbolici, nessun dato NEXUS). "
                "Le sequence FAIL/NEEDS_REFORMULATION sono state CORRETTE direttamente in market_sequence_registry_v1.json "
                "(campi prediction_start/outcome_window aggiornati, reformulation_note aggiunta) - l'ontologia che "
                "entra in Phase 7.3 e' gia' quella corretta.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_json(os.path.join(PHASE72_DIR, "sequence_semantic_leakage_guard_v1.json"),
              wrap_with_provenance(guard_payload, "phase7/phase7_2/apply_leakage_guard_and_ontology_update.py"))

    print(f"n_pass={n_pass} n_needs_reformulation={n_needs_reform} n_fail={n_fail}")
    for r in guard_results:
        if r["as_described_verdict"] != PASS:
            print(f"  {r['sequence_id']}: {r['as_described_verdict']} -> after correction: {r['verdict_after_correction']}")


if __name__ == "__main__":
    main()
