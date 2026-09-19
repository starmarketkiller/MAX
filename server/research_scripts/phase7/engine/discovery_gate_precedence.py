#!/usr/bin/env python3
"""Phase 7.1 Integrity & Provenance Patch (post-review, 2026-09-19) -
regola di precedenza esplicita per classificare PERCHE' un candidato ha
fallito una fase di screening (discovery/internal_validation/locked_
validation), invece di appiattire ogni fallimento su INSUFFICIENT_SAMPLE.

Bug corretto: la prima Phase 7.1 usava INSUFFICIENT_SAMPLE anche per
candidati con campione adeguato che fallivano per ΔP<=0, CI sovrapposte
o dependence-sensitivity - semanticamente scorretto (INSUFFICIENT_SAMPLE
deve significare "il campione stesso e' insufficiente", non "qualunque
motivo di fallimento").

Precedenza (dal motivo piu' fondamentale al meno fondamentale - il primo
che si applica decide lo stato, gli altri restano solo diagnostici):
1. pool di controllo insufficiente per uno o piu' eventi -> INSUFFICIENT_SAMPLE
   (un DeltaP calcolato su un sottoinsieme con match falliti non e' affidabile,
   controllato PRIMA di qualunque altra cosa)
2. n_nominal sotto il minimo dichiarato -> INSUFFICIENT_SAMPLE
3. DeltaP nullo/negativo -> REFUTED (l'effetto primario non c'e' o e' invertito)
4. dependence-sensitive -> DEPENDENCE_SENSITIVE (l'effetto nominale non regge
   al confronto EVENT vs EPISODE view)
5. CI95 sovrapposte (ma DeltaP>0, non dependence-sensitive, n adeguato) -> BORDERLINE
   (segnale positivo ma non ancora distinguibile dal rumore)
"""

INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
REFUTED = "REFUTED"
DEPENDENCE_SENSITIVE = "DEPENDENCE_SENSITIVE"
BORDERLINE = "BORDERLINE"


def classify_discovery_outcome(n_nominal: int, min_n: int, delta_p, ci_non_overlapping,
                                dependence_sensitive, n_rejected_insufficient_pool: int = 0,
                                materiality_threshold: float = 0.0):
    """Ritorna (target_state, reason_code, human_reason). Da chiamare SOLO
    quando le gate sono gia' state valutate come fallite (ok=False) - non
    decide se il candidato passa, solo PERCHE' non e' passato.

    materiality_threshold (default 0.0 = nessuna gate di materialita'
    applicata oltre a DeltaP>0): se un candidato pre-registra una soglia
    di materialita' minima (es. 0.15, vedi effect_size_first_policy.json),
    un DeltaP positivo ma sotto quella soglia e' trattato come BORDERLINE
    (segnale rilevabile ma non abbastanza ampio da contare come materiale),
    non come un fallimento equivalente a un DeltaP negativo."""
    if n_rejected_insufficient_pool > 0:
        return (INSUFFICIENT_SAMPLE, "INSUFFICIENT_CONTROL_POOL",
                f"{n_rejected_insufficient_pool} evento/i con pool di controllo insufficiente - "
                f"il DeltaP calcolato sul sottoinsieme rimanente non e' affidabile.")
    if n_nominal < min_n:
        return (INSUFFICIENT_SAMPLE, "LOW_N_NOMINAL",
                f"n_nominal={n_nominal} sotto il minimo dichiarato ({min_n}).")
    if delta_p is None or delta_p <= 0:
        return (REFUTED, "NON_POSITIVE_DELTA_P",
                f"DeltaP={delta_p} <= 0 o non calcolabile - l'effetto primario non c'e' o e' invertito.")
    if dependence_sensitive:
        return (DEPENDENCE_SENSITIVE, "DEPENDENCE_SENSITIVE",
                "L'effetto nominale (positivo in EVENT VIEW) non regge al confronto con la EPISODE VIEW "
                "(cambio di segno o sotto la soglia di materialita').")
    if delta_p < materiality_threshold:
        return (BORDERLINE, "BELOW_MATERIALITY_THRESHOLD",
                f"DeltaP={delta_p:.4f} positivo e non dependence-sensitive, ma sotto la soglia di materialita' "
                f"pre-registrata ({materiality_threshold}) - segnale rilevabile ma non materiale.")
    if not ci_non_overlapping:
        return (BORDERLINE, "CI95_OVERLAPPING",
                "DeltaP positivo, sopra la soglia di materialita' e non dependence-sensitive, ma CI95 Wilson "
                "(evento) e (baseline) si sovrappongono - segnale non ancora distinguibile dal rumore con il campione attuale.")
    raise ValueError(
        "classify_discovery_outcome chiamata su un candidato che non fallisce nessuna gate nota - "
        "il chiamante deve verificare ok=False prima di invocare questa funzione."
    )


if __name__ == "__main__":
    # Caso 1 (Integrity Patch): n adeguato + DeltaP<0 -> REFUTED, MAI INSUFFICIENT_SAMPLE.
    state, code, reason = classify_discovery_outcome(n_nominal=179, min_n=30, delta_p=-0.068,
                                                       ci_non_overlapping=False, dependence_sensitive=True)
    print(f"Caso 1 (n=179, DeltaP=-0.068, dependence_sensitive=True): {state} ({code})")
    assert state == REFUTED, "DeltaP<=0 deve avere precedenza su dependence-sensitivity e CI overlap"

    # Caso 2: fallimento causato SOLO da dependence (DeltaP positivo, CI comunque sovrapposte per costruzione tipica) -> DEPENDENCE_SENSITIVE.
    state, code, reason = classify_discovery_outcome(n_nominal=150, min_n=30, delta_p=0.05,
                                                       ci_non_overlapping=False, dependence_sensitive=True)
    print(f"Caso 2 (n=150, DeltaP=0.05, dependence_sensitive=True): {state} ({code})")
    assert state == DEPENDENCE_SENSITIVE

    # Caso 3: n genuinamente basso -> INSUFFICIENT_SAMPLE, anche con DeltaP positivo forte.
    state, code, reason = classify_discovery_outcome(n_nominal=12, min_n=30, delta_p=0.30,
                                                       ci_non_overlapping=True, dependence_sensitive=False)
    print(f"Caso 3 (n=12<30, DeltaP=0.30): {state} ({code})")
    assert state == INSUFFICIENT_SAMPLE

    # Caso 4: pool di controllo insufficiente per alcuni eventi -> INSUFFICIENT_SAMPLE, anche con n_nominal alto.
    state, code, reason = classify_discovery_outcome(n_nominal=200, min_n=30, delta_p=0.25,
                                                       ci_non_overlapping=True, dependence_sensitive=False,
                                                       n_rejected_insufficient_pool=3)
    print(f"Caso 4 (n=200, ma 3 eventi con pool insufficiente): {state} ({code})")
    assert state == INSUFFICIENT_SAMPLE and code == "INSUFFICIENT_CONTROL_POOL"

    # Caso 5: n adeguato, DeltaP positivo, non dependence-sensitive, ma CI sovrapposte -> BORDERLINE.
    state, code, reason = classify_discovery_outcome(n_nominal=80, min_n=30, delta_p=0.08,
                                                       ci_non_overlapping=False, dependence_sensitive=False)
    print(f"Caso 5 (n=80, DeltaP=0.08, CI sovrapposte, non dependence-sensitive): {state} ({code})")
    assert state == BORDERLINE

    # Caso 6: DeltaP positivo, CI NON sovrapposte, ma sotto la soglia di
    # materialita' pre-registrata -> BORDERLINE (non un fallimento pieno).
    state, code, reason = classify_discovery_outcome(n_nominal=200, min_n=30, delta_p=0.05,
                                                       ci_non_overlapping=True, dependence_sensitive=False,
                                                       materiality_threshold=0.15)
    print(f"Caso 6 (n=200, DeltaP=0.05<0.15 materialita', CI non sovrapposte): {state} ({code})")
    assert state == BORDERLINE and code == "BELOW_MATERIALITY_THRESHOLD"

    # Caso negativo: chiamata su un candidato che non fallisce nulla -> ValueError, non un default silenzioso.
    try:
        classify_discovery_outcome(n_nominal=100, min_n=30, delta_p=0.30, ci_non_overlapping=True, dependence_sensitive=False)
        print("ERRORE: avrebbe dovuto sollevare ValueError!")
    except ValueError as e:
        print(f"Chiamata su candidato senza gate fallite correttamente rifiutata: {type(e).__name__}")

    print("\nTutti i casi di precedenza verificati.")
