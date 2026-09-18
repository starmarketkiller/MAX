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
"""


class InvalidTransitionError(Exception):
    pass


TERMINAL_STATES = {"SUPPORTED", "BORDERLINE", "REFUTED", "INSUFFICIENT_SAMPLE",
                    "DEPENDENCE_SENSITIVE", "CONTAMINATED", "NON_TRANSFERABLE"}

# Stato corrente -> insieme di stati raggiungibili in UNA transizione.
# Ogni riga e' stata scelta per riflettere esattamente il percorso
# dichiarato in sec.14, piu' le uscite laterali ammesse da quel punto.
ALLOWED_TRANSITIONS = {
    "GENERATED": {"DISCOVERY_SIGNAL", "INSUFFICIENT_SAMPLE", "CONTAMINATED"},
    "DISCOVERY_SIGNAL": {"INTERNAL_VALIDATION", "INSUFFICIENT_SAMPLE", "CONTAMINATED"},
    "INTERNAL_VALIDATION": {"PRE_REGISTERED_CANDIDATE", "INSUFFICIENT_SAMPLE",
                             "DEPENDENCE_SENSITIVE", "CONTAMINATED", "REFUTED"},
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
        return self.state in TERMINAL_STATES and not ALLOWED_TRANSITIONS.get(self.state)


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
