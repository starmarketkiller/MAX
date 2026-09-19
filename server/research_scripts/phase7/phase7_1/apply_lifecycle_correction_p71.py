#!/usr/bin/env python3
"""Phase 7.1 Integrity & Provenance Patch (post-review, 2026-09-19) -
ricalcola SOLO l'etichetta di stato lifecycle dei 3 candidati gia'
testati, usando engine/discovery_gate_precedence.py sui numeri GIA'
prodotti e committati in phase7_1_evidence_records_v1.json (n_events,
delta_p, ci95_non_overlapping, dependence_flag) - NESSUNA nuova
discovery, NESSUN ricalcolo statistico, NESSUN accesso a validation/
locked/final holdout. Aggiorna anche i campi di provenance (sec.1) e la
decision card. Numeri, outcome per-candidato e verdetto complessivo
(NO_SUPPORTED_CANDIDATE) restano IDENTICI - cambia solo l'etichetta di
stato e la sua motivazione.
"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
PHASE7_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7")
sys.path.insert(0, os.path.join(PHASE7_DIR, "engine"))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from candidate_lifecycle import Candidate  # noqa: E402
from discovery_gate_precedence import classify_discovery_outcome, INSUFFICIENT_SAMPLE  # noqa: E402
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

EVIDENCE_PATH = os.path.join(PHASE7_DIR, "phase7_1", "phase7_1_evidence_records_v1.json")
DECISION_CARD_PATH = os.path.join(PHASE7_DIR, "phase7_1", "phase7_1_decision_card_v1.json")
MIN_N = 30
MATERIALITY_THRESHOLD = 0.15  # frozen in phase7_1_frozen_spec_v1.json, override rispetto al default 0.10

PROVENANCE_DISCLOSURE = {
    "declared_frozen_before_outcomes": True,
    "git_independently_proves_pre_registration_order": False,
    "provenance_note": (
        "phase7_1_frozen_spec_v1.json e phase7_1_evidence_records_v1.json sono stati committati "
        "nello STESSO commit (f9bfd68) - Git da solo non puo' dimostrare indipendentemente che il "
        "frozen spec sia stato scritto prima di calcolare gli outcome. La dichiarazione di pre-registrazione "
        "resta valida (contenuto del frozen spec e sequenza di esecuzione reale), ma la provenance NON e' "
        "verificabile crittograficamente da questo commit da solo. Per le run future e' obbligatoria la "
        "regola PRE-REGISTRATION COMMIT -> RUN -> RESULT COMMIT, enforced tecnicamente da "
        "engine/preregistration_provenance_guard.py (assert_frozen_spec_committed_before_run) - "
        "una futura run viene bloccata se il proprio frozen spec non e' gia' un file tracciato e pulito "
        "in un commit separato e precedente."
    ),
}


def main():
    with open(EVIDENCE_PATH, encoding="utf-8") as f:
        evidence_doc = json.load(f)
    with open(DECISION_CARD_PATH, encoding="utf-8") as f:
        decision_doc = json.load(f)

    evidence_payload = evidence_doc["payload"]
    decision_payload = decision_doc["payload"]

    if "integrity_patch_2026_09_19" in evidence_payload:
        print("Correzione gia' applicata in precedenza (chiave 'integrity_patch_2026_09_19' gia' presente) - "
              "nessuna riapplicazione per evitare testo duplicato. Nessuna modifica scritta.")
        return

    corrections = []
    for cand in evidence_payload["candidates"]:
        cid = cand["identity"]["candidate_id"]
        n_nominal = cand["sample"]["n_nominal"]
        delta_p = cand["effect"]["delta_p"]
        ci_non_overlap = cand["uncertainty"]["wilson_ci"]["non_overlapping"]
        dependence_sensitive = cand["sample"]["dependence_flag"] == "DEPENDENCE_SENSITIVE"
        old_state = cand["lifecycle_state"]
        old_history = cand["lifecycle_history"]

        # Nessuna delle 3 run ha avuto eventi con pool di controllo
        # insufficiente (n_rejected_insufficient_pool=0 per tutti e 3,
        # verificato nell'output originale della run - non ricalcolato,
        # riportato come fatto gia' noto) - la precedenza parte quindi
        # dal controllo su n_nominal.
        new_state, reason_code, human_reason = classify_discovery_outcome(
            n_nominal=n_nominal, min_n=MIN_N, delta_p=delta_p,
            ci_non_overlapping=ci_non_overlap, dependence_sensitive=dependence_sensitive,
            n_rejected_insufficient_pool=0, materiality_threshold=MATERIALITY_THRESHOLD,
        )

        # Verifica meccanica che la NUOVA transizione sia valida nel grafo
        # esteso (candidate_lifecycle.py, Integrity Patch) - non solo asserita.
        c = Candidate(cid)
        c.transition("DISCOVERY_SIGNAL", "discovery screening completato")
        c.transition(new_state, human_reason)
        assert c.state == new_state

        new_conclusion = f"{new_state}_AT_DISCOVERY" if new_state != INSUFFICIENT_SAMPLE else "INSUFFICIENT_SAMPLE_AT_DISCOVERY"
        cand["lifecycle_state"] = new_state
        cand["lifecycle_history"] = c.history
        cand["evidence_classification"]["conclusion"] = new_conclusion
        cand["evidence_classification"]["grade_cap_reason"] += (
            f" [Integrity Patch 2026-09-19: stato lifecycle corretto da '{old_state}' a '{new_state}' "
            f"({reason_code}) - {human_reason} Nessun numero (ΔP, CI, n, dependence) e' stato modificato, "
            f"solo l'etichetta di stato e la sua motivazione, secondo la regola di precedenza in "
            f"engine/discovery_gate_precedence.py.]"
        )
        cand.update(PROVENANCE_DISCLOSURE)
        corrections.append({"candidate_id": cid, "old_state": old_state, "new_state": new_state,
                             "reason_code": reason_code, "old_history": old_history, "new_history": c.history})

    evidence_payload["integrity_patch_2026_09_19"] = {
        "corrections_applied": corrections,
        "numbers_unchanged": True,
        "overall_verdict_unchanged": evidence_payload["overall_verdict"],
    }
    evidence_payload.update(PROVENANCE_DISCLOSURE)
    save_json(EVIDENCE_PATH, wrap_with_provenance(evidence_payload, "phase7/phase7_1/build_phase7_1_evidence.py + apply_lifecycle_correction_p71.py"))

    # ---- decision card: stessa correzione, stesso verdetto complessivo ----
    for cid, summary in decision_payload["per_candidate_summary"].items():
        correction = next(c for c in corrections if c["candidate_id"] == cid)
        summary["final_lifecycle_state"] = correction["new_state"]
        summary["lifecycle_correction_reason_code"] = correction["reason_code"]
    decision_payload["integrity_patch_2026_09_19"] = {
        "corrections_applied": [{"candidate_id": c["candidate_id"], "old_state": c["old_state"], "new_state": c["new_state"]} for c in corrections],
        "numbers_and_overall_verdict_unchanged": True,
    }
    decision_payload.update(PROVENANCE_DISCLOSURE)
    assert decision_payload["overall_verdict"] == "NO_SUPPORTED_CANDIDATE", "il verdetto complessivo non deve cambiare"
    save_json(DECISION_CARD_PATH, wrap_with_provenance(decision_payload, "phase7/phase7_1/build_phase7_1_evidence.py + apply_lifecycle_correction_p71.py"))

    print(json.dumps(corrections, indent=2, default=str, ensure_ascii=False))
    print(f"\nVerdetto complessivo INVARIATO: {decision_payload['overall_verdict']}")
    print(f"aggiornato: {EVIDENCE_PATH}")
    print(f"aggiornato: {DECISION_CARD_PATH}")


if __name__ == "__main__":
    main()
