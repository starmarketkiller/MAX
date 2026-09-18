#!/usr/bin/env python3
"""Phase 7 sec.25 - Candidate Signature: firma canonica per rilevare
duplicati concettuali. Due candidati semanticamente identici (stesso
evento, direzione, condizioni di stato, outcome) non devono contare
come due ipotesi separate nel multiple-testing ledger.

Nessun semantic-AI matching in questa fase (esplicitamente vietato,
sec.24) - solo normalizzazione deterministica di stringhe/numeri e
ordine di campo fisso.

Integrity Patch (post-review, 2026-09-18): la canonicalizzazione
iniziale ordinava le condizioni ma non normalizzava i VALORI - due
candidati scritti come threshold=1 e threshold=1.0, o con casing/
whitespace diversi su feature_id/operator/soglie categoriche, potevano
produrre firme diverse e sfuggire alla dedup. Corretto qui con
canonicalize_threshold/canonicalize_operator/canonicalize_feature_id,
sempre senza alcuna componente semantica/AI - solo parsing numerico e
normalizzazione di stringa deterministici.
"""
import hashlib

# "=" e "==" sono lo stesso operatore scritto in due modi - normalizzati
# entrambi al simbolo canonico "==". Nessun altro alias e' ammesso senza
# aggiornare esplicitamente questa mappa.
_OPERATOR_CANONICAL = {
    "=": "==", "==": "==", "eq": "==",
    ">": ">", ">=": ">=", "<": "<", "<=": "<=",
    "!=": "!=", "ne": "!=",
}


def canonicalize_feature_id(feature_id: str) -> str:
    return feature_id.strip().lower()


def canonicalize_operator(operator: str) -> str:
    key = operator.strip().lower()
    return _OPERATOR_CANONICAL.get(key, operator.strip())


def canonicalize_threshold(threshold) -> str:
    """Un threshold numerico (1, 1.0, "1.000", " 1 ") deve normalizzare
    sempre alla stessa stringa canonica. Un threshold categorico (es.
    "HIGH", " high ") normalizza a maiuscolo/trim - stessa convenzione
    gia' usata per event_family/direction in questo modulo."""
    s = str(threshold).strip()
    try:
        f = float(s)
    except (TypeError, ValueError):
        return s.upper()
    if f == 0:
        f = 0.0  # elimina il segno di "-0.0"
    if f == int(f) and abs(f) < 1e15:
        return repr(int(f))
    normalized = f"{f:.10f}".rstrip("0").rstrip(".")
    return normalized


def canonical_signature(event_family: str, direction: str, state_conditions: list, outcome_definition: str) -> str:
    """state_conditions: lista di dict {feature_id, operator, threshold}.
    Ordinati per feature_id CANONICO per garantire che ordine di
    inserimento, casing e rappresentazione numerica non cambino la
    firma di due candidati concettualmente identici."""
    parts = [f"EVENT={event_family.strip().upper()}", f"DIR={direction.strip().upper()}"]
    normalized_conditions = [
        {
            "feature_id": canonicalize_feature_id(c["feature_id"]),
            "operator": canonicalize_operator(c["operator"]),
            "threshold": canonicalize_threshold(c["threshold"]),
        }
        for c in state_conditions
    ]
    sorted_conditions = sorted(normalized_conditions, key=lambda c: c["feature_id"])
    for c in sorted_conditions:
        parts.append(f"STATE.{c['feature_id']}{c['operator']}{c['threshold']}")
    parts.append(f"OUTCOME={' '.join(outcome_definition.strip().split())}")
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

    # --- Integrity Patch: test di canonicalizzazione dei valori ---

    # threshold numerico: 1 / 1.0 / "1.000" / " 1 " devono dare la stessa firma
    sig_num_a = canonical_signature("SWEEP", "SELL",
                                     [{"feature_id": "trend", "operator": "=", "threshold": 1}],
                                     "OUT")
    sig_num_b = canonical_signature("SWEEP", "SELL",
                                     [{"feature_id": "trend", "operator": "=", "threshold": 1.0}],
                                     "OUT")
    sig_num_c = canonical_signature("SWEEP", "SELL",
                                     [{"feature_id": "trend", "operator": "=", "threshold": "1.000"}],
                                     "OUT")
    sig_num_d = canonical_signature("SWEEP", "SELL",
                                     [{"feature_id": "trend", "operator": "=", "threshold": " 1 "}],
                                     "OUT")
    print("threshold 1 / 1.0 / '1.000' / ' 1 ' -> stessa firma:",
          sig_num_a == sig_num_b == sig_num_c == sig_num_d)
    assert sig_num_a == sig_num_b == sig_num_c == sig_num_d

    # casing/whitespace su feature_id, operator, threshold categorico
    sig_case_a = canonical_signature("sweep", "sell",
                                      [{"feature_id": "Volatility", "operator": "==", "threshold": " high "}],
                                      "OUT")
    sig_case_b = canonical_signature("SWEEP", "SELL",
                                      [{"feature_id": "volatility", "operator": "=", "threshold": "HIGH"}],
                                      "OUT")
    print("casing/whitespace diversi (event/direction/feature/operator/threshold) -> stessa firma:",
          sig_case_a == sig_case_b)
    assert sig_case_a == sig_case_b

    # falso positivo da evitare: soglie numeriche DIVERSE non devono collassare
    sig_diff_a = canonical_signature("SWEEP", "SELL",
                                      [{"feature_id": "trend", "operator": "=", "threshold": 1.0}],
                                      "OUT")
    sig_diff_b = canonical_signature("SWEEP", "SELL",
                                      [{"feature_id": "trend", "operator": "=", "threshold": 1.5}],
                                      "OUT")
    print("threshold 1.0 vs 1.5 correttamente NON duplicati:", not is_duplicate(sig_diff_a, sig_diff_b))
    assert not is_duplicate(sig_diff_a, sig_diff_b)

    print("\nTutti i test di canonicalizzazione superati.")
