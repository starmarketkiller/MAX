#!/usr/bin/env python3
"""Phase 7 sec.26 - Dati sintetici per il preflight. NESSUN dato di
mercato reale qui dentro - tutto generato con random.seed fisso, solo
per dimostrare che i gate del motore funzionano meccanicamente.

Genera 4 split contigui (discovery/internal_validation/locked_validation/
final_holdout) con eventi, direzioni, outcome, e un pool di controlli per
il baseline - abbastanza struttura per esercitare ogni gate del preflight.
"""
import random

SPLIT_BOUNDARIES = {
    "discovery": (0, 1000),
    "internal_validation": (1000, 1400),
    "locked_validation": (1400, 1800),
    "final_holdout": (1800, 2200),
}


def generate_fixture(seed: int = 42):
    rng = random.Random(seed)

    # Eventi "clean" - un pattern con un effetto reale piccolo ma genuino,
    # clusterizzato (per esercitare EVENT/EPISODE view), distribuito su
    # tutti e 4 gli split.
    event_rows, direction_by_row, outcome_by_row = [], {}, {}
    r = 5
    while r < 2190:
        n_repeats = rng.choice([1, 1, 2, 3])  # clustering realistico
        base_outcome = 1.0 if rng.random() < 0.58 else 0.0  # baseline vera ~0.50
        for _ in range(n_repeats):
            event_rows.append(r)
            direction_by_row[r] = rng.choice([1, -1])
            outcome_by_row[r] = base_outcome
            r += rng.randint(1, 3)
        r += rng.randint(10, 40)

    # Pool di controlli per baseline - copre tutti gli split, MA il test
    # di cross-split-safety deve rifiutare un controllo che attraversa
    # split diversi dall'evento (vedi caso negativo in preflight_simulation.py).
    control_pool = list(range(0, 2200, 3))

    # Feature sintetica CAUSAL_UNSAFE (leakage deliberato: guarda
    # avanti nel tempo) - usata SOLO per dimostrare che il gate la blocca,
    # mai per calcolare un vero effetto.
    fake_leaky_feature_registry_entry = {
        "feature_id": "SYNTH_FUTURE_PEEK_v1",
        "leakage_risk": "HIGH",
        "causal_status": "CAUSAL_UNSAFE",
        "note": "Fixture deliberatamente leaky (shift negativo simulato) - solo per il test negativo del preflight.",
    }

    return {
        "split_boundaries": SPLIT_BOUNDARIES,
        "event_rows": event_rows,
        "direction_by_row": direction_by_row,
        "outcome_by_row": outcome_by_row,
        "control_pool": control_pool,
        "fake_leaky_feature": fake_leaky_feature_registry_entry,
    }


def fake_baseline_p(rows, direction_by_row):
    return 0.50


if __name__ == "__main__":
    fx = generate_fixture()
    print(f"n_events={len(fx['event_rows'])} n_controls_pool={len(fx['control_pool'])}")
    print("SYNTHETIC_FIXTURE_ONLY - nessun dato di mercato reale.")
