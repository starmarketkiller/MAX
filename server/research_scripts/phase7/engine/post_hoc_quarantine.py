#!/usr/bin/env python3
"""Phase 7 sec.15 - Post-hoc Quarantine. Qualunque pattern notato DOPO il
test primario (guardando direction split, quarter, subgroup, failure
anatomy, residuo) diventa automaticamente POST_HOC_OBSERVATION - non
puo' essere promosso a hypothesis/candidate NELLA STESSA run.

Questo modulo non "decide" se un'osservazione e' interessante - impone
solo che qualunque cosa passi da questa funzione NON possa mai ricevere
uno status di candidato valido senza un nuovo ciclo (nuovo hypothesis_id,
freeze, dati non ancora usati)."""


class PostHocPromotionBlocked(Exception):
    pass


FORBIDDEN_PROMOTION_TARGETS = {
    "SUPPORTED", "BORDERLINE", "PRE_REGISTERED_CANDIDATE", "INDEPENDENT_VALIDATION",
}


def register_post_hoc_observation(observation_id: str, derived_from_id: str,
                                   discovered_via: str, run_id: str) -> dict:
    """discovered_via: uno fra 'direction_split','quarter_split',
    'subgroup_split','failure_anatomy','residual_analysis' - qualunque
    canale diverso dal test primario pre-registrato."""
    allowed_channels = {"direction_split", "quarter_split", "subgroup_split",
                         "failure_anatomy", "residual_analysis"}
    if discovered_via not in allowed_channels:
        raise ValueError(f"canale di scoperta sconosciuto: {discovered_via}")
    return {
        "observation_id": observation_id,
        "status": "POST_HOC_OBSERVATION",
        "derived_from_id": derived_from_id,
        "discovered_via": discovered_via,
        "discovered_in_run": run_id,
        "is_edge": False,
        "is_validated": False,
        "requires_new_hypothesis": True,
        "requires_new_holdout": True,
        "requires_unused_data": True,
        "eligible_for_promotion_in_same_run": False,
    }


def attempt_promotion(observation: dict, target_state: str, same_run: bool):
    """Qualunque tentativo di promuovere un'osservazione post-hoc DENTRO
    la stessa run viene rifiutato meccanicamente, non solo per policy."""
    if observation.get("status") != "POST_HOC_OBSERVATION":
        return  # non e' un'osservazione post-hoc, non e' questo il gate competente
    if target_state in FORBIDDEN_PROMOTION_TARGETS and same_run:
        raise PostHocPromotionBlocked(
            f"Promozione vietata: '{observation['observation_id']}' e' POST_HOC_OBSERVATION "
            f"(scoperta via {observation['discovered_via']} nella run {observation['discovered_in_run']}) "
            f"- non puo' diventare {target_state} nella STESSA run. Serve: nuovo hypothesis_id, "
            f"freeze esplicito, dati mai usati per questa osservazione."
        )


if __name__ == "__main__":
    # Dimostrazione: replica esattamente il caso SELL_SWEEP_RECLAIM_ASYMMETRY
    # (Phase 6.5/6.6) con dati fittizi, per provare che il gate blocca
    # meccanicamente cio' che finora era garantito solo da disciplina umana.
    obs = register_post_hoc_observation(
        observation_id="DEMO_SELL_ASYMMETRY",
        derived_from_id="DEMO-CANDIDATE-001",
        discovered_via="direction_split",
        run_id="DEMO-RUN-001",
    )
    print("Osservazione registrata:", obs["status"], "is_edge=", obs["is_edge"])

    try:
        attempt_promotion(obs, target_state="SUPPORTED", same_run=True)
        print("ERRORE: la promozione avrebbe dovuto essere bloccata!")
    except PostHocPromotionBlocked as e:
        print(f"Promozione correttamente bloccata: {e}")

    # In una run FUTURA (same_run=False), con un nuovo hypothesis_id, il
    # gate qui non si oppone piu' - ma la responsabilita' di aprire un
    # nuovo ciclo (freeze + holdout indipendente) resta di chi orchestra
    # la run, non di questo modulo.
    try:
        attempt_promotion(obs, target_state="SUPPORTED", same_run=False)
        print("Promozione in una NUOVA run non bloccata da questo gate (corretto - richiede comunque nuovo hypothesis_id a monte).")
    except PostHocPromotionBlocked as e:
        print(f"ERRORE: non doveva essere bloccata fuori dalla run originale: {e}")
