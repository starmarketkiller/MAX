#!/usr/bin/env python3
"""Phase 7.2B sec.2 - Semantic Leakage Guard per la sequence ontology.

Una transition condition non puo' essere usata come feature del setup
se e' logicamente equivalente o troppo vicina all'outcome che il test
vorrebbe prevedere. Formalizza 4 istanti simbolici (in "barre relative
a event_a", non dati NEXUS - questa e' una verifica di COERENZA
dell'ontologia, non un calcolo su prezzi reali):

  observation_cutoff        <= ultima informazione nota quando si
                                valuta se il SETUP (initial_state+event_a)
                                esiste
  transition_completion_time = istante in cui la transition_conditions/
                                event_b_optional si risolve (puo'
                                richiedere N barre dopo event_a)
  prediction_start           = primo istante da cui si comincia a
                                "scommettere"/misurare l'outcome
  outcome_window_start       = prima barra della finestra di misura
                                dell'outcome

Requisito: observation_cutoff <= transition_completion_time <=
prediction_start < outcome_window_start, SENZA sovrapposizione fra le
barre usate per risolvere la transition e le barre usate per misurare
l'outcome.
"""

PASS = "PASS"
FAIL = "FAIL"
NEEDS_REFORMULATION = "NEEDS_REFORMULATION"


def check_sequence_leakage(transition_completion_offset: float, prediction_start_offset: float,
                            outcome_window_start_offset: float,
                            outcome_measures_same_event_as_trigger: bool = False):
    """Tutti gli offset sono ESPRESSI IN BARRE RELATIVE a event_a (event_a=0).
    Ritorna (verdict, reason). Tre esiti distinti:
    - FAIL: circolarita' fondamentale (l'outcome e' praticamente il trigger)
      - non risolvibile spostando semplicemente prediction_start, richiede
      una diversa definizione di outcome.
    - NEEDS_REFORMULATION: la formulazione AS-DESCRIBED non e' causalmente
      sicura, ma e' risolvibile allineando prediction_start/outcome_window
      al reale completamento della transition (correzione meccanica).
    - PASS: gia' causalmente sicura."""
    if outcome_measures_same_event_as_trigger:
        return (FAIL, "L'outcome misura praticamente lo stesso evento usato come trigger "
                      "(nessuna informazione nuova fra setup e outcome) - richiede una diversa "
                      "definizione di outcome, non solo uno spostamento temporale.")
    if prediction_start_offset < transition_completion_offset:
        return (NEEDS_REFORMULATION,
                f"prediction_start (t={prediction_start_offset}) precede il completamento della "
                f"transition (t={transition_completion_offset}) - richiede informazione non ancora "
                f"disponibile al momento in cui si dichiara di iniziare la previsione (lookahead). "
                f"Risolvibile allineando prediction_start al completamento della transition.")
    if outcome_window_start_offset <= prediction_start_offset:
        return (NEEDS_REFORMULATION,
                f"outcome_window_start (t={outcome_window_start_offset}) non e' strettamente successivo "
                f"a prediction_start (t={prediction_start_offset}) - nessun gap causale. Risolvibile "
                f"spostando outcome_window_start dopo prediction_start.")
    return (PASS, f"observation_cutoff<=transition_completion(t={transition_completion_offset})"
                  f"<=prediction_start(t={prediction_start_offset})<outcome_window_start"
                  f"(t={outcome_window_start_offset}) - nessuna sovrapposizione.")


def classify_relationship(same_antecedent: bool, same_observation_time: bool, same_setup_definition: bool,
                           outcomes_are_opposite: bool, divergence_due_to_later_transition: bool):
    """Sec.1/sec.8 - distingue CONTRADICTION da CONDITIONAL_BRANCH.
    Una vera CONTRADICTION richiede SAME antecedent + SAME observation
    time + SAME setup + esiti opposti E la divergenza NON deve essere
    dovuta all'osservare una transition diversa dopo l'evento comune."""
    if divergence_due_to_later_transition:
        return "CONDITIONAL_BRANCH"
    if same_antecedent and same_observation_time and same_setup_definition and outcomes_are_opposite:
        return "CONTRADICTION"
    return "UNRELATED_OR_INSUFFICIENT_INFO"


if __name__ == "__main__":
    # --- Regression: leakage guard (sec.2, sec.8) ---

    # Caso 1: transition completamente osservata prima del prediction_start -> PASS.
    v, r = check_sequence_leakage(transition_completion_offset=0, prediction_start_offset=0, outcome_window_start_offset=1)
    print(f"Caso 1 (transition risolta a t=0, outcome da t=1): {v}")
    assert v == PASS

    # Caso 2: transition che usa una barra dell'outcome window -> NEEDS_REFORMULATION
    # (prediction_start dichiarato PRIMA che la transition sia risolta - lookahead,
    # ma risolvibile spostando la previsione, non un difetto strutturale).
    v, r = check_sequence_leakage(transition_completion_offset=10, prediction_start_offset=1, outcome_window_start_offset=2)
    print(f"Caso 2 (prediction_start=1 ma transition si risolve solo a t=10): {v} - {r}")
    assert v == NEEDS_REFORMULATION

    # Caso 3: outcome definito praticamente come il trigger stesso -> FAIL
    # (circolarita' strutturale, non risolvibile spostando solo la previsione).
    v, r = check_sequence_leakage(transition_completion_offset=0, prediction_start_offset=0, outcome_window_start_offset=1,
                                   outcome_measures_same_event_as_trigger=True)
    print(f"Caso 3 (outcome == trigger): {v} - {r}")
    assert v == FAIL

    # Caso 4 (SEQ-0012 reale): la transition si risolve solo dopo l'intero orizzonte
    # (assenza di reclaim confermata solo a fine finestra) - se prediction_start fosse
    # dichiarato a t=0 (ingresso immediato "sulla scommessa" nella direzione dello sweep)
    # sarebbe lookahead - ma risolvibile ritardando l'ingresso, quindi NEEDS_REFORMULATION.
    v, r = check_sequence_leakage(transition_completion_offset=10, prediction_start_offset=0, outcome_window_start_offset=1)
    print(f"Caso 4 (SEQ-0012-style, entry immediato ma conferma solo a t=10): {v} - {r}")
    assert v == NEEDS_REFORMULATION

    # Caso 5: stessa sequenza, ma riformulata correttamente (prediction_start = t=10, dopo la conferma) -> PASS.
    v, r = check_sequence_leakage(transition_completion_offset=10, prediction_start_offset=10, outcome_window_start_offset=11)
    print(f"Caso 5 (SEQ-0012 riformulata, prediction_start=10): {v}")
    assert v == PASS

    # --- Regression: classificazione CONTRADICTION vs CONDITIONAL_BRANCH (sec.8) ---

    # same antecedent + opposite future claim (divergenza NON dovuta a una transition osservata dopo) -> CONTRADICTION
    rel = classify_relationship(same_antecedent=True, same_observation_time=True, same_setup_definition=True,
                                 outcomes_are_opposite=True, divergence_due_to_later_transition=False)
    print(f"Caso A (stesso antecedente, stesso istante, esiti opposti, NESSUNA transition successiva a spiegarli): {rel}")
    assert rel == "CONTRADICTION"

    # same antecedent + different observed transition -> CONDITIONAL_BRANCH
    rel = classify_relationship(same_antecedent=True, same_observation_time=True, same_setup_definition=True,
                                 outcomes_are_opposite=True, divergence_due_to_later_transition=True)
    print(f"Caso B (stesso antecedente, ma divergenza dovuta a transition diversa osservata dopo): {rel}")
    assert rel == "CONDITIONAL_BRANCH"

    print("\nTutti i casi di regressione del semantic leakage guard verificati.")
