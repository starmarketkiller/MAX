#!/usr/bin/env python3
"""Phase 7 sec.9 - Cross-split safety, imposto tecnicamente (non solo
per convenzione). Un evento in validation non puo' ricevere controlli
derivati dal discovery split. Un evento in holdout non puo' ricevere
controlli da nessun altro split. Matching within-split only, salvo
eccezione esplicita e giustificata scientificamente.
"""


class CrossSplitViolation(Exception):
    pass


def assign_split(row_index: int, split_boundaries: dict) -> str:
    """split_boundaries: {'discovery': (start,end), 'internal_validation': (start,end),
    'locked_validation': (start,end), 'final_holdout': (start,end)} - range
    a barre INCLUSIVE-esclusive [start,end)."""
    for split_name, (start, end) in split_boundaries.items():
        if start <= row_index < end:
            return split_name
    return "OUT_OF_RANGE"


def validate_baseline_matches(event_row: int, control_rows: list, split_boundaries: dict,
                               explicit_exception: bool = False, exception_reason: str = None):
    """Solleva CrossSplitViolation se un qualunque control_row appartiene
    a uno split diverso da quello dell'evento - salvo explicit_exception=True
    con una motivazione scritta (mai silenziosa)."""
    event_split = assign_split(event_row, split_boundaries)
    violations = []
    for c in control_rows:
        control_split = assign_split(c, split_boundaries)
        if control_split != event_split:
            violations.append({"control_row": c, "control_split": control_split})
    if violations and not explicit_exception:
        raise CrossSplitViolation(
            f"Evento alla riga {event_row} (split={event_split}) ha ricevuto "
            f"{len(violations)} controlli da split diversi: {violations}. "
            f"Matching within-split-only violato senza eccezione dichiarata."
        )
    if violations and explicit_exception and not exception_reason:
        raise ValueError("explicit_exception=True richiede una exception_reason non vuota - nessuna eccezione silenziosa ammessa.")
    return {"event_split": event_split, "n_controls": len(control_rows),
            "violations": violations, "exception_used": bool(violations and explicit_exception),
            "exception_reason": exception_reason if violations else None}


if __name__ == "__main__":
    boundaries = {
        "discovery": (0, 1000),
        "internal_validation": (1000, 1400),
        "locked_validation": (1400, 1800),
        "final_holdout": (1800, 2200),
    }

    # Caso 1: matching corretto, tutto within-split
    result_ok = validate_baseline_matches(event_row=1500, control_rows=[1410, 1420, 1650], split_boundaries=boundaries)
    print("Caso valido (within-split):", result_ok)

    # Caso 2: violazione reale - un evento in locked_validation riceve un
    # controllo dal discovery split (esattamente il tipo di errore che
    # sarebbe potuto sfuggire senza questo check tecnico)
    try:
        validate_baseline_matches(event_row=1500, control_rows=[1410, 500, 1650], split_boundaries=boundaries)
        print("ERRORE: la violazione avrebbe dovuto essere rilevata!")
    except CrossSplitViolation as e:
        print(f"Violazione correttamente rilevata e bloccata: {e}")

    # Caso 3: eccezione esplicita senza motivazione -> rifiutata comunque
    try:
        validate_baseline_matches(event_row=1500, control_rows=[500], split_boundaries=boundaries,
                                   explicit_exception=True, exception_reason=None)
        print("ERRORE: l'eccezione senza motivazione avrebbe dovuto essere rifiutata!")
    except ValueError as e:
        print(f"Eccezione senza motivazione correttamente rifiutata: {e}")
