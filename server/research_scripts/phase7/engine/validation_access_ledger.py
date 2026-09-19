#!/usr/bin/env python3
"""Phase 7.0B sec.6-7 - Validation/Holdout Access Ledger: enforcement
TECNICO (non solo logging) contro il riuso invisibile di locked_validation
e final_holdout. Legge validation_access_policy_v1.json come unica fonte
di verita' (mai duplicata a mano nel codice - vedi Integrity Patch
Phase 7.0 per il motivo di questa scelta).

Un candidato non puo' leggere due volte lo stesso split one-shot senza:
- nuova hypothesis/candidate identity;
- motivazione esplicita (allow_contaminated_reentry=True + reason);
- stato precedente marcato CONTAMINATED/REUSED.
"""
import json
import os
from datetime import datetime, timezone


class ValidationAccessViolation(Exception):
    pass


def load_policy(policy_path: str = None) -> dict:
    if policy_path is None:
        policy_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "policies", "validation_access_policy_v1.json")
    with open(policy_path, encoding="utf-8") as f:
        return json.load(f)


class ValidationAccessLedger:
    def __init__(self, policy: dict):
        self.policy = policy
        self.log = []
        self._counts = {}  # (candidate_id, split) -> n accessi gia' concessi

    def record_access(self, candidate_id: str, split: str, run_id: str, dataset_version_hash: str,
                       purpose: str, caller: str, allow_contaminated_reentry: bool = False,
                       prior_state: str = None, reentry_reason: str = None) -> dict:
        split_policy = self.policy["splits"].get(split)
        if split_policy is None:
            raise ValueError(f"split sconosciuto in validation_access_policy_v1.json: {split}")

        key = (candidate_id, split)
        current_count = self._counts.get(key, 0)
        max_reads = split_policy.get("max_reads_per_candidate")

        if max_reads is not None and current_count >= max_reads:
            reentry_allowed = (allow_contaminated_reentry and prior_state in ("CONTAMINATED", "REUSED")
                                and bool(reentry_reason))
            if not reentry_allowed:
                raise ValidationAccessViolation(
                    f"[{candidate_id}] accesso a '{split}' rifiutato: gia' {current_count}/{max_reads} "
                    f"letture consentite esaurite. Serve nuova hypothesis/candidate identity, oppure "
                    f"allow_contaminated_reentry=True con prior_state in {{CONTAMINATED,REUSED}} e una "
                    f"reentry_reason esplicita (mai un'eccezione silenziosa)."
                )

        access_id = f"ACC-{len(self.log) + 1:06d}"
        record = {
            "access_id": access_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "candidate_id": candidate_id,
            "split": split,
            "dataset_version_hash": dataset_version_hash,
            "purpose": purpose,
            "caller": caller,
            "access_count_for_candidate_split": current_count + 1,
            "reentry_of_contaminated": bool(allow_contaminated_reentry and current_count >= (max_reads or 0)),
            "reentry_reason": reentry_reason,
        }
        self.log.append(record)
        self._counts[key] = current_count + 1
        return record

    def export_log(self) -> list:
        return list(self.log)


if __name__ == "__main__":
    policy = load_policy()
    ledger = ValidationAccessLedger(policy)

    # Caso valido: prima lettura di locked_validation per un candidato.
    r1 = ledger.record_access("CAND-001", "locked_validation", "RUN-001", "DSHASH-DEMO",
                               purpose="verdetto primario", caller="research_pipeline")
    print("Primo accesso a locked_validation:", r1["access_id"], "count=", r1["access_count_for_candidate_split"])
    assert r1["access_count_for_candidate_split"] == 1

    # Caso rotto: secondo accesso allo stesso split per LO STESSO candidato -> bloccato.
    try:
        ledger.record_access("CAND-001", "locked_validation", "RUN-002", "DSHASH-DEMO",
                              purpose="tentativo di rileggere lo stesso split", caller="research_pipeline")
        print("ERRORE: il secondo accesso avrebbe dovuto essere bloccato!")
    except ValidationAccessViolation as e:
        print(f"Secondo accesso correttamente bloccato: {e}")

    # Stesso identico tentativo su final_holdout -> anch'esso bloccato dopo la prima lettura.
    ledger.record_access("CAND-002", "final_holdout", "RUN-001", "DSHASH-DEMO",
                          purpose="verdetto finale", caller="research_pipeline")
    try:
        ledger.record_access("CAND-002", "final_holdout", "RUN-003", "DSHASH-DEMO",
                              purpose="secondo sguardo", caller="research_pipeline")
        print("ERRORE: il secondo accesso a final_holdout avrebbe dovuto essere bloccato!")
    except ValidationAccessViolation as e:
        print(f"Secondo accesso a final_holdout correttamente bloccato: {e}")

    # Caso di eccezione esplicita e motivata (nuova hypothesis, stato precedente CONTAMINATED) -> ammesso.
    r_reentry = ledger.record_access("CAND-001", "locked_validation", "RUN-004", "DSHASH-DEMO",
                                      purpose="nuova hypothesis dopo contaminazione dichiarata", caller="research_pipeline",
                                      allow_contaminated_reentry=True, prior_state="CONTAMINATED",
                                      reentry_reason="Candidato precedente marcato CONTAMINATED - nuova hypothesis_id H-DEMO-002 aperta.")
    print("Re-accesso motivato ammesso:", r_reentry["access_id"], "reentry=", r_reentry["reentry_of_contaminated"])
    assert r_reentry["reentry_of_contaminated"] is True

    # internal_validation: LIMITED a 3 letture, non one-shot.
    for i in range(3):
        ledger.record_access("CAND-003", "internal_validation", "RUN-001", "DSHASH-DEMO",
                              purpose=f"iterazione {i+1}", caller="research_pipeline")
    try:
        ledger.record_access("CAND-003", "internal_validation", "RUN-001", "DSHASH-DEMO",
                              purpose="quarta iterazione", caller="research_pipeline")
        print("ERRORE: la quarta lettura di internal_validation avrebbe dovuto essere bloccata!")
    except ValidationAccessViolation as e:
        print(f"Quarta lettura di internal_validation correttamente bloccata: {e}")

    # discovery: ITERABLE, nessun limite.
    for i in range(10):
        ledger.record_access("CAND-004", "discovery", "RUN-001", "DSHASH-DEMO",
                              purpose=f"iterazione {i+1}", caller="research_pipeline")
    print("10 accessi a discovery tutti ammessi (ITERABLE, nessun limite).")

    print(f"\nLog totale: {len(ledger.export_log())} accessi registrati.")
