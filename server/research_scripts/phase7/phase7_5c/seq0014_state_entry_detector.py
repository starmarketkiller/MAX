#!/usr/bin/env python3
"""Phase 7.5C - SEQ-0014 (MECH-23) State-Entry Detector v1.

Detector MINIMALE, nuovo (nessun detector MECH-23 preesisteva in Phase
5/7.1). Trasforma una classificazione di STATO continua (directional_
efficiency in tercile LOW) in un event set STATE-ENTRY (transizione
0->1), MAI un evento per ogni barra dello stato.

Congelato PRIMA di calcolare qualunque evento su development_discovery
- vedi seq0014_frozen_structural_spec_v1.json per i tercile cutpoints
(fittati su discovery) e il rationale completo. Nessun dato di outcome
e' mai richiesto o accettato da questo modulo."""


def compute_in_state(directional_efficiency_by_row: dict, cutpoint_low_med: float) -> dict:
    """in_state[row] = True se directional_efficiency[row] <= cutpoint_low_med
    (terzile LOW - i cutpoint sono gia' stati fittati SOLO su
    development_discovery dal chiamante, mai ricalcolati qui). Causale
    per costruzione: directional_efficiency[row] e' interamente noto a
    close(row) (feature_registry_v2.json: observation_time=bar_close)."""
    return {row: (value <= cutpoint_low_med) for row, value in directional_efficiency_by_row.items()}


def compute_state_entry_rows(in_state_by_row: dict) -> list:
    """event_a = prima barra t della transizione in_state[t-1]=False ->
    in_state[t]=True. Una corsa di N barre consecutive con in_state=True
    produce UN SOLO evento (la prima barra della corsa) - MAI N eventi.
    Le uscite (1->0) non sono contate come eventi propri. Il flicker
    (uscita breve poi ri-entrata) NON e' gestito qui - e' delegato al
    secondo livello gia' esistente (episode_gap_rule/sequence_episode_
    engine.py), per non duplicare la stessa funzione con un meccanismo
    di reset indipendente (decisione esplicita, vedi frozen spec sec.
    state_entry_event_definition.re_entry_and_minimum_reset_rule)."""
    sorted_rows = sorted(in_state_by_row.keys())
    entries = []
    for i, row in enumerate(sorted_rows):
        if not in_state_by_row[row]:
            continue
        prev_row = sorted_rows[i - 1] if i > 0 else None
        prev_in_state = in_state_by_row.get(prev_row, False) if prev_row is not None else False
        # Una transizione e' riconosciuta SOLO fra righe CONSECUTIVE nella
        # serie (prev_row immediatamente precedente nell'indice fornito) -
        # se il chiamante fornisce una serie con dei buchi (barre mancanti),
        # una entrata dopo un buco e' comunque trattata come una nuova
        # transizione (nessun dato mancante puo' MAI essere assunto False
        # o True per costruzione: e' semplicemente assente dall'input).
        if not prev_in_state:
            entries.append(row)
    return entries


def compute_state_durations(in_state_by_row: dict) -> list:
    """Diagnostica STRUTTURALE (nessun outcome coinvolto): durata in
    barre di ciascuna corsa contigua con in_state=True - usata solo per
    riportare durata media/mediana dello stato (sec.10 della richiesta),
    mai per scegliere una soglia o un parametro del gate."""
    sorted_rows = sorted(in_state_by_row.keys())
    durations = []
    current_run = 0
    for i, row in enumerate(sorted_rows):
        if in_state_by_row[row]:
            current_run += 1
        else:
            if current_run > 0:
                durations.append(current_run)
            current_run = 0
    if current_run > 0:
        durations.append(current_run)
    return durations


if __name__ == "__main__":
    # ---- Self-test su dati sintetici (nessun dato NEXUS) ----
    import statistics

    # Caso 1: corsa di 5 barre consecutive in stato -> 1 SOLO evento (non 5).
    de = {100: 0.05, 101: 0.04, 102: 0.06, 103: 0.05, 104: 0.03, 105: 0.50}  # esce a 105
    in_state = compute_in_state(de, cutpoint_low_med=0.10)
    assert in_state == {100: True, 101: True, 102: True, 103: True, 104: True, 105: False}
    entries = compute_state_entry_rows(in_state)
    assert entries == [100], f"atteso [100] (1 solo evento per una corsa di 5 barre), ottenuto {entries}"
    print(f"Caso 1 OK: corsa di 5 barre in stato -> {len(entries)} evento (mai 5): {entries}")

    # Caso 2: due corse separate -> 2 eventi distinti (uno per corsa).
    de2 = {100: 0.05, 101: 0.05, 102: 0.50, 103: 0.50, 104: 0.04, 105: 0.04, 106: 0.50}
    in_state2 = compute_in_state(de2, cutpoint_low_med=0.10)
    entries2 = compute_state_entry_rows(in_state2)
    assert entries2 == [100, 104], f"atteso [100,104], ottenuto {entries2}"
    print(f"Caso 2 OK: due corse separate -> 2 eventi (uno per corsa): {entries2}")

    # Caso 3: stato gia' attivo alla primissima riga fornita -> conta comunque come 1 entrata
    # (nessuna riga precedente disponibile = trattata come False, quindi 0->1 alla prima riga).
    de3 = {200: 0.05, 201: 0.05, 202: 0.50}
    entries3 = compute_state_entry_rows(compute_in_state(de3, cutpoint_low_med=0.10))
    assert entries3 == [200]
    print(f"Caso 3 OK: stato attivo dalla primissima riga fornita -> 1 entrata: {entries3}")

    # Caso 4: durate di stato correttamente calcolate.
    durations = compute_state_durations(in_state)  # de originale: corsa di 5 (100-104), poi False
    assert durations == [5], f"atteso [5], ottenuto {durations}"
    durations2 = compute_state_durations(in_state2)  # due corse: (100,101)=2, (104,105)=2
    assert durations2 == [2, 2], f"atteso [2,2], ottenuto {durations2}"
    print(f"Caso 4 OK: durate di stato -> {durations2} (mediana={statistics.median(durations2)})")

    # Caso 5: nessuna barra in stato -> nessun evento, nessuna durata.
    de5 = {300: 0.50, 301: 0.60}
    assert compute_state_entry_rows(compute_in_state(de5, cutpoint_low_med=0.10)) == []
    assert compute_state_durations(compute_in_state(de5, cutpoint_low_med=0.10)) == []
    print("Caso 5 OK: nessuna barra in stato -> 0 eventi, 0 durate.")

    print("\nTutti i casi del SEQ-0014 State-Entry Detector verificati.")
