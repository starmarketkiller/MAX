#!/usr/bin/env python3
"""Phase 7.3 sec.7-8 - Outcome Surface v3: interfaccia, NON usata su una
discovery reale in questa fase. Distingue PRIMARY_OUTCOME (congelato
prima della run), SECONDARY_PREDECLARED_OUTCOMES (pre-registrati, con
correzione multiple-testing) e DIAGNOSTIC_ONLY_OUTCOMES (mai usati per
un verdetto). Il motore non puo' calcolare N outcome e scegliere il
migliore chiamandolo edge (sec.8) - l'enforcement e' strutturale: solo
il PRIMARY_OUTCOME alimenta candidate_lifecycle, i DIAGNOSTIC_ONLY non
raggiungono mai multiple_testing_v2."""

ALL_OUTCOME_DEFINITIONS = {
    "P_PLUS_0_25ATR_BEFORE_MINUS_1ATR": "P(+0.25 ATR before -1 ATR)",
    "P_PLUS_0_5ATR_BEFORE_MINUS_1ATR": "P(+0.5 ATR before -1 ATR)",
    "P_PLUS_1ATR_BEFORE_MINUS_1ATR": "P(+1 ATR before -1 ATR)",
    "P_PLUS_1_5ATR_BEFORE_MINUS_1ATR": "P(+1.5 ATR before -1 ATR)",
    "P_PLUS_2ATR_BEFORE_MINUS_1ATR": "P(+2 ATR before -1 ATR)",
    "MFE": "Maximum Favorable Excursion",
    "MAE": "Maximum Adverse Excursion",
    "TIME_TO_MFE": "Barre fino al MFE",
    "TIME_TO_TARGET": "Barre fino al raggiungimento del target primario",
    "CONTINUATION_PROBABILITY": "P(continuazione nella direzione dell'evento)",
    "REVERSAL_PROBABILITY": "P(inversione rispetto alla direzione dell'evento)",
    "REALIZED_VOLATILITY_AFTER_SETUP": "Volatilita' realizzata nell'orizzonte post-setup",
    "PATH_EFFICIENCY": "Rapporto fra movimento netto e percorso totale nell'orizzonte",
}

TIER_PRIMARY = "PRIMARY_OUTCOME"
TIER_SECONDARY = "SECONDARY_PREDECLARED_OUTCOMES"
TIER_DIAGNOSTIC = "DIAGNOSTIC_ONLY_OUTCOMES"


class OutcomeShoppingBlocked(Exception):
    pass


class OutcomeSurfaceV3:
    """Un'istanza rappresenta la dichiarazione CONGELATA (frozen spec) di
    quali outcome sono primary/secondary/diagnostic per UNA sequence
    family - mai modificabile dopo la creazione (sec.8/9: 'primary
    outcome deve essere congelato prima della run')."""

    def __init__(self, primary_outcome: str, secondary_outcomes: list, diagnostic_outcomes: list):
        if primary_outcome not in ALL_OUTCOME_DEFINITIONS:
            raise ValueError(f"primary_outcome sconosciuto: {primary_outcome}")
        for o in secondary_outcomes + diagnostic_outcomes:
            if o not in ALL_OUTCOME_DEFINITIONS:
                raise ValueError(f"outcome sconosciuto: {o}")
        overlap = set(secondary_outcomes) & set(diagnostic_outcomes)
        if overlap:
            raise ValueError(f"un outcome non puo' essere sia secondary sia diagnostic: {overlap}")
        if primary_outcome in secondary_outcomes or primary_outcome in diagnostic_outcomes:
            raise ValueError("primary_outcome non puo' comparire anche come secondary/diagnostic")

        self._primary = primary_outcome
        self._secondary = tuple(secondary_outcomes)  # tuple = immutabile dopo il freeze
        self._diagnostic = tuple(diagnostic_outcomes)
        self._frozen = True

    @property
    def primary_outcome(self):
        return self._primary

    @property
    def secondary_outcomes(self):
        return self._secondary

    @property
    def diagnostic_outcomes(self):
        return self._diagnostic

    def inferential_family_size(self) -> int:
        """Quanti outcome sono REALMENTE testati inferenzialmente (primary
        + secondary) - i diagnostic NON contano ai fini di multiple
        testing perche' non producono mai un verdetto (sec.7: 'Multiple
        testing deve conoscere quanti outcome inferenziali sono realmente
        testati')."""
        return 1 + len(self._secondary)

    def assert_no_post_hoc_outcome_addition(self, requested_outcome: str, already_saw_results: bool):
        """sec.8: il motore non puo' 'scoprire' un decimo outcome dopo aver
        visto i risultati e trattarlo come se fosse stato pre-registrato."""
        if requested_outcome in (self._primary, *self._secondary, *self._diagnostic):
            return True
        if already_saw_results:
            raise OutcomeShoppingBlocked(
                f"Outcome '{requested_outcome}' non era pre-registrato (ne' primary ne' secondary ne' diagnostic) "
                f"e i risultati sono gia' stati osservati - aggiunta post-hoc bloccata. Se genuinamente interessante, "
                f"va registrato come POST_HOC_OBSERVATION (post_hoc_quarantine.py), mai come outcome di questa run."
            )
        raise ValueError(f"Outcome '{requested_outcome}' non dichiarato nel frozen spec - "
                          f"anche prima di vedere risultati, ogni outcome usato deve essere dichiarato ex-ante.")

    def select_best_of_secondary_as_primary(self, *args, **kwargs):
        """Metodo deliberatamente presente SOLO per essere bloccato - il
        Sequence Discovery Engine non deve MAI poter promuovere un
        secondary outcome a primary sulla base del risultato osservato."""
        raise OutcomeShoppingBlocked(
            "select_best_of_secondary_as_primary non e' un'operazione ammessa in nessuna circostanza (sec.8/9) - "
            "il primary outcome e' immutabile dopo il freeze del frozen spec."
        )


if __name__ == "__main__":
    surface = OutcomeSurfaceV3(
        primary_outcome="P_PLUS_1ATR_BEFORE_MINUS_1ATR",
        secondary_outcomes=["MFE", "TIME_TO_TARGET"],
        diagnostic_outcomes=["MAE", "REALIZED_VOLATILITY_AFTER_SETUP", "PATH_EFFICIENCY"],
    )
    print(f"primary={surface.primary_outcome}, secondary={surface.secondary_outcomes}, "
          f"diagnostic={surface.diagnostic_outcomes}")
    print(f"inferential_family_size (per multiple testing) = {surface.inferential_family_size()}")
    assert surface.inferential_family_size() == 3  # 1 primary + 2 secondary, i 3 diagnostic NON contano

    # Caso positivo: un outcome gia' pre-registrato puo' essere richiesto senza problemi.
    assert surface.assert_no_post_hoc_outcome_addition("MFE", already_saw_results=True) is True
    print("Caso 1 OK: outcome pre-registrato (MFE) richiesto dopo i risultati -> ammesso.")

    # Caso negativo: un outcome MAI dichiarato, richiesto DOPO aver visto risultati -> bloccato.
    try:
        surface.assert_no_post_hoc_outcome_addition("CONTINUATION_PROBABILITY", already_saw_results=True)
        print("ERRORE: outcome shopping post-hoc avrebbe dovuto essere bloccato!")
    except OutcomeShoppingBlocked as e:
        print(f"Caso 2 OK: outcome non pre-registrato richiesto dopo risultati -> bloccato ({type(e).__name__})")

    # Caso negativo: tentativo di promuovere un secondary a primary -> sempre bloccato.
    try:
        surface.select_best_of_secondary_as_primary()
        print("ERRORE: la promozione del 'miglior secondary' avrebbe dovuto essere bloccata!")
    except OutcomeShoppingBlocked as e:
        print(f"Caso 3 OK: promozione post-hoc di un secondary a primary -> bloccata ({type(e).__name__})")

    print("\nOutcomeSurfaceV3 verificata (nessun outcome shopping possibile).")
