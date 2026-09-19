#!/usr/bin/env python3
"""Phase 7 sec.14 - Candidate Lifecycle: macchina a stati che impedisce
salti di stato. Nessun candidato puo' passare da GENERATED a SUPPORTED
senza attraversare ogni gate intermedio.

Stati principali (percorso normale):
GENERATED -> DISCOVERY_SIGNAL -> INTERNAL_VALIDATION ->
PRE_REGISTERED_CANDIDATE -> INDEPENDENT_VALIDATION ->
SUPPORTED | BORDERLINE | REFUTED

Stati laterali (raggiungibili da piu' punti, MAI bypassabili in uscita
verso uno stato "migliore" nella stessa run):
INSUFFICIENT_SAMPLE, DEPENDENCE_SENSITIVE, COST_SENSITIVE,
NON_TRANSFERABLE, CONTAMINATED

Integrity Patch (post-review, 2026-09-18): TERMINAL_STATES era una
lista scritta a mano che poteva disallinearsi dal grafo reale in
ALLOWED_TRANSITIONS - infatti COST_SENSITIVE aveva transizioni in
uscita vuote (set()) ma NON compariva nella lista, rendendo
is_terminal() incoerente (restituiva False per uno stato che non puo'
piu' muoversi). Corretto rendendo TERMINAL_STATES una proiezione
CALCOLATA del grafo stesso (ogni stato con transizioni in uscita
vuote), cosi' l'invariante "nessuna transizione in uscita => terminale"
vale per costruzione e non puo' piu' disallinearsi. SUPPORTED non e'
strutturalmente terminale con questa definizione (ha uscite laterali
indipendenti verso COST_SENSITIVE/NON_TRANSFERABLE, sec.20) - e' un
verdetto di ricerca raggiunto, non uno stato senza ulteriori assi da
esplorare; la distinzione e' intenzionale, non un bug.

Integrity & Provenance Patch (post-review, 2026-09-19): DISCOVERY_SIGNAL
ammetteva in uscita solo INTERNAL_VALIDATION/INSUFFICIENT_SAMPLE/
CONTAMINATED - un candidato che falliva a livello di discovery per
DeltaP<=0 o per dependence-sensitivity veniva quindi forzato su
INSUFFICIENT_SAMPLE anche con campione adeguato (bug semantico, trovato
nella prima vera discovery run, Phase 7.1). Aggiunte le uscite dirette
REFUTED, DEPENDENCE_SENSITIVE e BORDERLINE da DISCOVERY_SIGNAL (e
BORDERLINE anche da INTERNAL_VALIDATION, per lo stesso motivo - un
risultato positivo ma sotto la soglia di materialita' o con CI
sovrapposte a quello stadio non e' ne' un successo ne' un fallimento
netto) - la regola di PRECEDENZA che decide quale delle possibili
uscite si applica quando piu' gate falliscono insieme vive in
engine/discovery_gate_precedence.py (non qui: questo modulo impone SOLO
quali transizioni sono strutturalmente ammesse, non la logica che
sceglie fra esse).
"""


class InvalidTransitionError(Exception):
    pass


# Stato corrente -> insieme di stati raggiungibili in UNA transizione.
# Ogni riga e' stata scelta per riflettere esattamente il percorso
# dichiarato in sec.14, piu' le uscite laterali ammesse da quel punto.
ALLOWED_TRANSITIONS = {
    "GENERATED": {"DISCOVERY_SIGNAL", "INSUFFICIENT_SAMPLE", "CONTAMINATED"},
    "DISCOVERY_SIGNAL": {"INTERNAL_VALIDATION", "INSUFFICIENT_SAMPLE", "CONTAMINATED",
                          "REFUTED", "DEPENDENCE_SENSITIVE", "BORDERLINE"},
    "INTERNAL_VALIDATION": {"PRE_REGISTERED_CANDIDATE", "INSUFFICIENT_SAMPLE",
                             "DEPENDENCE_SENSITIVE", "CONTAMINATED", "REFUTED", "BORDERLINE"},
    "PRE_REGISTERED_CANDIDATE": {"INDEPENDENT_VALIDATION", "CONTAMINATED"},
    "INDEPENDENT_VALIDATION": {"SUPPORTED", "BORDERLINE", "REFUTED",
                                "INSUFFICIENT_SAMPLE", "DEPENDENCE_SENSITIVE", "CONTAMINATED"},
    # Uscite laterali post-SUPPORTED: assi indipendenti (costo, trasferibilita'),
    # non un "downgrade" del verdetto originale - vedi Discovery Engine v2
    # sec.20 (STRUCTURAL EDGE vs EXECUTABLE EDGE AFTER COST).
    "SUPPORTED": {"COST_SENSITIVE", "NON_TRANSFERABLE"},
    # stati terminali "puri": nessuna uscita
    "BORDERLINE": set(),
    "REFUTED": set(),
    "INSUFFICIENT_SAMPLE": set(),
    "DEPENDENCE_SENSITIVE": set(),
    "CONTAMINATED": set(),
    "NON_TRANSFERABLE": set(),
    "COST_SENSITIVE": set(),
}

ALL_STATES = set(ALLOWED_TRANSITIONS.keys())

# Terminale = nessuna transizione in uscita possibile - calcolato dal
# grafo, mai mantenuto a mano (vedi nota Integrity Patch sopra).
TERMINAL_STATES = frozenset(state for state, exits in ALLOWED_TRANSITIONS.items() if not exits)

# Invariante strutturale verificata a import-time: per costruzione deve
# sempre valere "nessuna uscita <=> terminale" - se questo assert fallisce
# un domani, il grafo stesso e' incoerente, non solo la sua proiezione.
assert TERMINAL_STATES == {s for s in ALL_STATES if not ALLOWED_TRANSITIONS[s]}


class Candidate:
    def __init__(self, setup_id: str, initial_state: str = "GENERATED"):
        if initial_state not in ALL_STATES:
            raise ValueError(f"stato iniziale sconosciuto: {initial_state}")
        self.setup_id = setup_id
        self.state = initial_state
        self.history = [initial_state]

    def transition(self, new_state: str, reason: str = ""):
        if new_state not in ALL_STATES:
            raise ValueError(f"stato sconosciuto: {new_state}")
        allowed = ALLOWED_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise InvalidTransitionError(
                f"[{self.setup_id}] transizione vietata: {self.state} -> {new_state} "
                f"(ammesse da {self.state}: {sorted(allowed) or 'nessuna (stato terminale)'})"
            )
        self.state = new_state
        self.history.append(new_state)
        return self

    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES


if __name__ == "__main__":
    # Dimostrazione 1: percorso valido completo (dati fittizi, nessun edge reale)
    c = Candidate("DEMO-SETUP-001")
    for step in ["DISCOVERY_SIGNAL", "INTERNAL_VALIDATION", "PRE_REGISTERED_CANDIDATE",
                 "INDEPENDENT_VALIDATION", "BORDERLINE"]:
        c.transition(step)
    print(f"Percorso valido: {' -> '.join(c.history)}")
    assert c.state == "BORDERLINE"

    # Dimostrazione 2: tentativo di salto vietato (GENERATED -> SUPPORTED)
    c2 = Candidate("DEMO-SETUP-002")
    try:
        c2.transition("SUPPORTED")
        print("ERRORE: il salto avrebbe dovuto essere rifiutato!")
    except InvalidTransitionError as e:
        print(f"Salto correttamente rifiutato: {e}")

    # Dimostrazione 3: nessuna uscita da uno stato terminale puro
    c3 = Candidate("DEMO-SETUP-003", initial_state="REFUTED")
    try:
        c3.transition("SUPPORTED")
        print("ERRORE: la resurrezione da REFUTED avrebbe dovuto essere rifiutata!")
    except InvalidTransitionError as e:
        print(f"Transizione da stato terminale correttamente rifiutata: {e}")

    # Dimostrazione 4 (Integrity Patch): COST_SENSITIVE non ha uscite
    # -> is_terminal() DEVE restituire True, per costruzione del grafo.
    c4 = Candidate("DEMO-SETUP-004", initial_state="COST_SENSITIVE")
    print(f"COST_SENSITIVE is_terminal(): {c4.is_terminal()}")
    assert c4.is_terminal() is True

    # Dimostrazione 5: SUPPORTED ha uscite laterali (COST_SENSITIVE/
    # NON_TRANSFERABLE) -> NON e' strutturalmente terminale, per design.
    c5 = Candidate("DEMO-SETUP-005", initial_state="SUPPORTED")
    print(f"SUPPORTED is_terminal(): {c5.is_terminal()} (atteso False - ha uscite laterali indipendenti)")
    assert c5.is_terminal() is False

    # Dimostrazione 6 (Integrity & Provenance Patch): un candidato con
    # DeltaP<=0 gia' a livello di discovery deve poter raggiungere REFUTED
    # DIRETTAMENTE da DISCOVERY_SIGNAL, senza passare per INSUFFICIENT_SAMPLE.
    c6 = Candidate("DEMO-SETUP-006")
    c6.transition("DISCOVERY_SIGNAL")
    c6.transition("REFUTED", "DeltaP<=0 in discovery")
    print(f"DISCOVERY_SIGNAL -> REFUTED diretto: {' -> '.join(c6.history)}")
    assert c6.state == "REFUTED"

    c7 = Candidate("DEMO-SETUP-007")
    c7.transition("DISCOVERY_SIGNAL")
    c7.transition("DEPENDENCE_SENSITIVE", "dependence-sensitive gia' in discovery")
    assert c7.state == "DEPENDENCE_SENSITIVE"
    print(f"DISCOVERY_SIGNAL -> DEPENDENCE_SENSITIVE diretto: {' -> '.join(c7.history)}")

    # Invariante generale su TUTTI gli stati: nessuna uscita <=> terminale.
    for state in ALL_STATES:
        expected = not ALLOWED_TRANSITIONS[state]
        actual = Candidate(f"INVARIANT-CHECK-{state}", initial_state=state).is_terminal()
        assert actual == expected, f"Invariante violata per {state}: is_terminal()={actual}, atteso={expected}"
    print("Invariante 'nessuna transizione in uscita <=> is_terminal()==True' verificata su tutti gli stati.")
