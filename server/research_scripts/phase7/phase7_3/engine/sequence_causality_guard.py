#!/usr/bin/env python3
"""Phase 7.3 sec.3 - Temporal Causality Enforcement RUNTIME (non solo
dichiarazione nello schema). Ogni sequence_event prodotto da un
detector deve passare da qui PRIMA di essere accettato nella pipeline -
fail-closed: se una condizione fallisce, si solleva
SequenceCausalityViolation, l'evento NON viene silenziosamente scartato
o corretto.

Condizioni verificate:
  max(feature_timestamp) <= observation_cutoff_index
  transition_complete_index <= prediction_start_index
  prediction_start_index < outcome_window_start_index
"""


class SequenceCausalityViolation(Exception):
    pass


class DetectorVersionMismatchError(Exception):
    pass


def assert_detector_version_unchanged(frozen_detector_version: str, event_detector_version: str,
                                       sequence_event_id: str = "UNKNOWN"):
    """Sec.17 red-team ('detector cambia dopo outcome') - un sequence_event
    prodotto da una versione di detector diversa da quella congelata nel
    frozen spec della family non puo' essere accettato nella stessa run.
    Un detector modificato a meta' run (anche per una 'piccola correzione')
    invaliderebbe silenziosamente la comparabilita' fra eventi gia'
    processati e nuovi."""
    if event_detector_version != frozen_detector_version:
        raise DetectorVersionMismatchError(
            f"[{sequence_event_id}] detector_version dell'evento ('{event_detector_version}') "
            f"non corrisponde alla versione congelata nel frozen spec ('{frozen_detector_version}') - "
            f"il detector e' cambiato durante la run, rifiutato."
        )
    return True


def enforce_temporal_causality(observation_cutoff_index: int, max_feature_timestamp_index: int,
                                transition_complete_index: int, prediction_start_index: int,
                                outcome_window_start_index: int, sequence_event_id: str = "UNKNOWN"):
    """Fail-closed: solleva SequenceCausalityViolation alla PRIMA
    condizione violata - non prova a 'correggere' o proseguire con un
    evento parzialmente invalido."""
    if max_feature_timestamp_index > observation_cutoff_index:
        raise SequenceCausalityViolation(
            f"[{sequence_event_id}] SEQUENCE_CAUSALITY_VIOLATION: una feature dello state_snapshot usa "
            f"informazione fino a t={max_feature_timestamp_index}, oltre observation_cutoff_index="
            f"{observation_cutoff_index} - lookahead nel setup stesso."
        )
    if transition_complete_index > prediction_start_index:
        raise SequenceCausalityViolation(
            f"[{sequence_event_id}] SEQUENCE_CAUSALITY_VIOLATION: transition_complete_index="
            f"{transition_complete_index} > prediction_start_index={prediction_start_index} - la previsione "
            f"comincerebbe prima che la transition sia risolta."
        )
    if not (prediction_start_index < outcome_window_start_index):
        raise SequenceCausalityViolation(
            f"[{sequence_event_id}] SEQUENCE_CAUSALITY_VIOLATION: outcome_window_start_index="
            f"{outcome_window_start_index} non e' strettamente successivo a prediction_start_index="
            f"{prediction_start_index} - nessun gap causale fra previsione e misura dell'outcome."
        )
    return True


def validate_sequence_event(event: dict, outcome_window_start_index: int, max_feature_timestamp_index: int = None):
    """Wrapper che estrae i campi rilevanti da un sequence_event conforme
    a sequence_detector_contract_v1.json e applica enforce_temporal_causality.
    Se max_feature_timestamp_index non e' fornito, si assume conservativamente
    che coincida con observation_cutoff_index (nessuna feature puo' MAI
    guardare oltre il proprio stesso observation_cutoff per costruzione
    del detector - qui si verifica comunque esplicitamente quando disponibile)."""
    obs_cutoff = event["observation_cutoff_index"]
    max_feat = max_feature_timestamp_index if max_feature_timestamp_index is not None else obs_cutoff
    return enforce_temporal_causality(
        observation_cutoff_index=obs_cutoff, max_feature_timestamp_index=max_feat,
        transition_complete_index=event["transition_complete_index"],
        prediction_start_index=event["prediction_start_index"],
        outcome_window_start_index=outcome_window_start_index,
        sequence_event_id=event.get("sequence_event_id", "UNKNOWN"),
    )


if __name__ == "__main__":
    # Caso 1 (positivo): evento causalmente valido -> True, nessuna eccezione.
    ok = enforce_temporal_causality(observation_cutoff_index=10, max_feature_timestamp_index=10,
                                     transition_complete_index=10, prediction_start_index=10,
                                     outcome_window_start_index=11, sequence_event_id="DEMO-001")
    print(f"Caso 1 (evento valido): enforce_temporal_causality -> {ok}")
    assert ok is True

    # Caso 2 (negativo): una feature dello snapshot guarda oltre observation_cutoff -> violazione.
    try:
        enforce_temporal_causality(observation_cutoff_index=10, max_feature_timestamp_index=12,
                                    transition_complete_index=10, prediction_start_index=10,
                                    outcome_window_start_index=11, sequence_event_id="DEMO-002")
        print("ERRORE: violazione feature-oltre-cutoff non rilevata!")
    except SequenceCausalityViolation as e:
        print(f"Caso 2 (feature oltre cutoff) correttamente bloccato: {type(e).__name__}")

    # Caso 3 (negativo): prediction_start precede il completamento della transition -> violazione.
    try:
        enforce_temporal_causality(observation_cutoff_index=10, max_feature_timestamp_index=10,
                                    transition_complete_index=10, prediction_start_index=5,
                                    outcome_window_start_index=11, sequence_event_id="DEMO-003")
        print("ERRORE: violazione transition>prediction_start non rilevata!")
    except SequenceCausalityViolation as e:
        print(f"Caso 3 (prediction_start prematuro) correttamente bloccato: {type(e).__name__}")

    # Caso 4 (negativo): outcome_window non strettamente dopo prediction_start -> violazione.
    try:
        enforce_temporal_causality(observation_cutoff_index=10, max_feature_timestamp_index=10,
                                    transition_complete_index=10, prediction_start_index=10,
                                    outcome_window_start_index=10, sequence_event_id="DEMO-004")
        print("ERRORE: violazione outcome_window<=prediction_start non rilevata!")
    except SequenceCausalityViolation as e:
        print(f"Caso 4 (outcome_window non successivo) correttamente bloccato: {type(e).__name__}")

    # Caso 5 (positivo): detector_version dell'evento coincide con quella congelata -> True.
    ok_v = assert_detector_version_unchanged("toy-v1", "toy-v1", sequence_event_id="DEMO-005")
    print(f"Caso 5 (detector_version invariata): assert_detector_version_unchanged -> {ok_v}")
    assert ok_v is True

    # Caso 6 (negativo): il detector e' cambiato a meta' run -> violazione.
    try:
        assert_detector_version_unchanged("toy-v1", "toy-v2-hotfix", sequence_event_id="DEMO-006")
        print("ERRORE: cambio di detector_version durante la run non rilevato!")
    except DetectorVersionMismatchError as e:
        print(f"Caso 6 (detector_version cambiata) correttamente bloccato: {type(e).__name__}")

    print("\nTutti i casi del causality guard verificati (fail-closed).")
