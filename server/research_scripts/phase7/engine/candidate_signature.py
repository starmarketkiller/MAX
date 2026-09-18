#!/usr/bin/env python3
"""Phase 7 sec.25 - Candidate Signature: firma canonica per rilevare
duplicati concettuali. Due candidati semanticamente identici (stesso
evento, direzione, condizioni di stato, outcome) non devono contare
come due ipotesi separate nel multiple-testing ledger.

Nessun semantic-AI matching in questa fase (esplicitamente vietato,
sec.24) - solo normalizzazione di ID stabili e ordine di campo fisso.
"""
import hashlib


def canonical_signature(event_family: str, direction: str, state_conditions: list, outcome_definition: str) -> str:
    """state_conditions: lista di dict {feature_id, operator, threshold}.
    Ordinati per feature_id per garantire che l'ordine di inserimento
    non cambi la firma (STATE.trend=DOWN + STATE.volatility=HIGH deve
    dare la STESSA firma di STATE.volatility=HIGH + STATE.trend=DOWN)."""
    parts = [f"EVENT={event_family.upper()}", f"DIR={direction.upper()}"]
    sorted_conditions = sorted(state_conditions, key=lambda c: c["feature_id"])
    for c in sorted_conditions:
        parts.append(f"STATE.{c['feature_id']}{c['operator']}{c['threshold']}")
    parts.append(f"OUTCOME={outcome_definition}")
    return "\n".join(parts)


def signature_hash(signature: str) -> str:
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()


def is_duplicate(sig_a: str, sig_b: str) -> bool:
    return sig_a == sig_b


if __name__ == "__main__":
    # Esempio dalla richiesta (sec.25)
    sig1 = canonical_signature(
        event_family="SWEEP", direction="SELL",
        state_conditions=[
            {"feature_id": "volatility", "operator": "=", "threshold": "HIGH"},
            {"feature_id": "trend", "operator": "=", "threshold": "DOWN"},
        ],
        outcome_definition="+1ATR_before_-1ATR_40H4",
    )
    print(sig1)
    print("hash:", signature_hash(sig1))
    print()

    # Stesso candidato, condizioni inserite in ordine diverso -> DEVE dare la stessa firma
    sig2 = canonical_signature(
        event_family="SWEEP", direction="SELL",
        state_conditions=[
            {"feature_id": "trend", "operator": "=", "threshold": "DOWN"},
            {"feature_id": "volatility", "operator": "=", "threshold": "HIGH"},
        ],
        outcome_definition="+1ATR_before_-1ATR_40H4",
    )
    print("Duplicato rilevato (ordine campi diverso, stesso concetto):", is_duplicate(sig1, sig2))
    assert is_duplicate(sig1, sig2)

    # Candidato genuinamente diverso (direzione opposta) -> NON deve risultare duplicato
    sig3 = canonical_signature(
        event_family="SWEEP", direction="BUY",
        state_conditions=[
            {"feature_id": "volatility", "operator": "=", "threshold": "HIGH"},
            {"feature_id": "trend", "operator": "=", "threshold": "DOWN"},
        ],
        outcome_definition="+1ATR_before_-1ATR_40H4",
    )
    print("Candidato con direzione diversa correttamente NON duplicato:", not is_duplicate(sig1, sig3))
    assert not is_duplicate(sig1, sig3)
