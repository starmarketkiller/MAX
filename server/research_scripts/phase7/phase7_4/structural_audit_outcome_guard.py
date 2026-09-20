#!/usr/bin/env python3
"""Phase 7.4A Baseline Matching Topology Audit sec.12 - guard fail-closed
che vieta qualunque colonna/chiave che assomigli a un OUTCOME nel
dataset dell'audit strutturale (event id/index/time, control id/index/
time, direction, split, match distance, reuse count - MAI target/stop/
mfe/mae/return/pnl/delta_p/delta_e/future/profit).

ATTENZIONE ai falsi positivi (pattern gia' visto in tutte le fasi
precedenti): 'return_direction' e 'roc' sono feature CAUSAL_SAFE gia'
approvate in feature_registry_v2.json (non sono outcome nonostante
contengano sottostringhe ambigue) - un match a sottostringa grezza le
segnalerebbe erroneamente. Il controllo qui e' a livello di PAROLA
intera (split su '_'/spazio), con un allowlist esplicito per i pochi
nomi gia' noti e vetted."""
import re

FORBIDDEN_WHOLE_WORDS = {
    "outcome", "target", "stop", "mfe", "mae", "return", "pnl", "future",
    "profit", "profitability", "win", "loss", "hit", "reward",
}
FORBIDDEN_SUBSTRINGS = {
    "delta_p", "delta_e", "time_to_mfe", "time_to_target", "path_efficiency",
    "continuation_probability", "reversal_probability", "realized_volatility_after_setup",
}
# Feature CAUSAL_SAFE gia' vetted in feature_registry_v2.json che contengono
# per coincidenza una parola nella lista sopra ("return_direction" contiene
# "return") - NON sono outcome, dichiarato esplicitamente qui.
ALLOWLIST_CAUSAL_SAFE_NAMES = {"return_direction", "roc"}


class StructuralAuditOutcomeLeakage(Exception):
    pass


def assert_no_outcome_columns(columns_or_keys, context: str = ""):
    """Solleva StructuralAuditOutcomeLeakage (fail-closed) se una
    colonna/chiave del dataset dell'audit assomiglia a un outcome.
    Da chiamare su OGNI struttura dati caricata/costruita in questo
    audit prima di usarla."""
    for col in columns_or_keys:
        col_str = str(col)
        if col_str in ALLOWLIST_CAUSAL_SAFE_NAMES:
            continue
        col_l = col_str.lower()
        words = set(re.split(r"[_\s]+", col_l))
        bad_words = words & FORBIDDEN_WHOLE_WORDS
        if bad_words:
            raise StructuralAuditOutcomeLeakage(
                f"STRUCTURAL_AUDIT_OUTCOME_LEAKAGE{' (' + context + ')' if context else ''}: "
                f"colonna/chiave '{col_str}' contiene la/e parola/e vietata/e {bad_words} - "
                f"un dataset di audit strutturale non puo' contenere outcome."
            )
        for sub in FORBIDDEN_SUBSTRINGS:
            if sub in col_l:
                raise StructuralAuditOutcomeLeakage(
                    f"STRUCTURAL_AUDIT_OUTCOME_LEAKAGE{' (' + context + ')' if context else ''}: "
                    f"colonna/chiave '{col_str}' contiene la sottostringa vietata '{sub}'."
                )
    return True


if __name__ == "__main__":
    print("=== Self-test structural_audit_outcome_guard (dati SINTETICI) ===")

    # Caso 1: colonne strutturali legittime -> nessuna eccezione.
    safe_cols = ["event_id", "event_index", "control_id", "control_index", "direction",
                "split", "match_distance", "reuse_count", "bar_time_utc", "atr_percentile", "ema_slope_atr_norm"]
    assert assert_no_outcome_columns(safe_cols) is True
    print(f"Caso 1 OK: colonne strutturali {safe_cols} accettate.")

    # Caso 2: falso-positivo evitato - feature causal-safe gia' vetted con sottostringa ambigua.
    assert assert_no_outcome_columns(["return_direction", "roc"]) is True
    print("Caso 2 OK: 'return_direction'/'roc' (causal-safe, gia' vetted) NON segnalate come outcome.")

    # Caso 3: outcome espliciti -> rifiutati.
    for bad_col in ["mfe_ATR", "target_hit", "delta_p", "future_return", "pnl_realized", "path_efficiency_ratio"]:
        try:
            assert_no_outcome_columns([bad_col])
            print(f"ERRORE: '{bad_col}' avrebbe dovuto essere rifiutata!")
        except StructuralAuditOutcomeLeakage as e:
            print(f"Caso 3 OK: '{bad_col}' correttamente rifiutata: {type(e).__name__}")

    # Caso 4: 'return' come parola intera in un nome diverso -> rifiutato (non e' nell'allowlist).
    try:
        assert_no_outcome_columns(["realized_return"])
        print("ERRORE: 'realized_return' avrebbe dovuto essere rifiutata!")
    except StructuralAuditOutcomeLeakage:
        print("Caso 4 OK: 'realized_return' (non in allowlist) correttamente rifiutata.")

    print("\nSelf-test completato su dati SINTETICI.")
