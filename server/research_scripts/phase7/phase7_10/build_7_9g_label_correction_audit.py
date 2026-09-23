#!/usr/bin/env python3
"""Phase 7.10 - punto 1: verifica e documenta l'inversione di etichetta
only_a/only_b trovata negli artifact di parity della Phase 7.9G.

Risposta alla domanda dell'utente: SI', l'inversione esisteva, verificata
direttamente sul codice sorgente (non assunta) - vedi 'verification'
sotto per la prova esatta. I NUMERI/il VERDETTO sostanziali NON erano mai
sbagliati (il codice di decisione compensava correttamente lo scambio
posizionale) - solo i NOMI dei campi nell'artifact JSON erano fuorvianti
rispetto alla convenzione A/B usata nel resto del report.
"""
import os
import sys

PHASE710_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE710_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "651d3a2a10e5c58acfc22ba820f518810356a73c"
PHASE79G_DIR = os.path.join(ROOT, "server", "research_scripts", "phase7", "phase7_9g")
ORIGINAL_PARITY = os.path.join(PHASE710_DIR, "raw_data", "breakout_acc_postfix_signal_parity_v1_ORIGINAL_pre_label_fix.json")
ORIGINAL_DECISION = os.path.join(PHASE710_DIR, "raw_data", "breakout_acc_phase7_9g_decision_v1_ORIGINAL_pre_label_fix.json")
CORRECTED_PARITY = os.path.join(PHASE79G_DIR, "breakout_acc_postfix_signal_parity_v1.json")
CORRECTED_DECISION = os.path.join(PHASE79G_DIR, "breakout_acc_phase7_9g_decision_v1.json")


def build():
    original_parity = load_json(ORIGINAL_PARITY)["payload"]
    corrected_parity = load_json(CORRECTED_PARITY)["payload"]
    original_decision = load_json(ORIGINAL_DECISION)["payload"]
    corrected_decision = load_json(CORRECTED_DECISION)["payload"]

    orig_pairing = original_parity["exact_parity_target"]["same_feed_parity_A_vs_B"]["pairing"]
    corr_pairing = corrected_parity["exact_parity_target"]["same_feed_parity_A_vs_B"]["pairing"]

    verification = {
        "claim_checked": "Nel report 7.9G: A=EA live post-fix=67 eventi, B=ricostruzione offline "
            "MQL5=75 eventi, matched=67 -> matematicamente A-only=0, B-only=8. Le etichette "
            "only_a/only_b nell'artifact sembrano invertite rispetto alla descrizione narrativa.",
        "root_cause_found_in_code": {
            "file": "server/research_scripts/phase7/phase7_9g/build_postfix_signal_parity.py",
            "function": "pair_dates(events_a, events_b, tolerance_days=3)",
            "mechanism": "La funzione e' POSIZIONALE: only_a nel dict di ritorno e' SEMPRE il "
                "residuo del PRIMO argomento passato, only_b del SECONDO - indipendentemente da "
                "quale stream logico (A/B/C del report) venga passato per primo.",
            "original_call_sites_before_fix": [
                'same_feed_pairing = pair_dates(stream_B["final_events"], stream_A["events"])',
                'cross_feed_pairing_A_vs_C = pair_dates(stream_C["final_events"], stream_A["events"])',
                'cross_feed_pairing_B_vs_C = pair_dates(stream_C["final_events"], stream_B["final_events"])',
            ],
            "inversion_confirmed": "SI - per la sezione same_feed_parity_A_vs_B, il primo "
                "argomento passato era stream_B (offline), il secondo stream_A (live) - quindi "
                "il campo restituito 'only_a' conteneva in realta' il residuo di B (offline) e "
                "'only_b' il residuo di A (live). Lo stesso pattern di inversione si applicava "
                "identicamente alle altre due sezioni (A_vs_C, B_vs_C).",
        },
        "original_raw_values": {
            "only_a": orig_pairing["only_a"], "only_b": orig_pairing["only_b"],
            "note": "Questi valori grezzi (only_a=8, only_b=0) erano quelli EFFETTIVAMENTE "
                "presenti nell'artifact prima della correzione - only_a conteneva il residuo "
                "di B (offline), only_b il residuo di A (live), come confermato dal meccanismo "
                "sopra.",
        },
        "corrected_raw_values": {
            "only_a": corr_pairing["only_a"], "only_b": corr_pairing["only_b"],
            "note": "Dopo la correzione (argomenti passati nello stesso ordine del nome della "
                "sezione: A_vs_B -> pair_dates(A,B)), only_a=0 rappresenta correttamente il "
                "residuo di A (live, zero) e only_b=8 il residuo di B (offline).",
        },
        "substance_unchanged": {
            "matched_before": orig_pairing["matched"], "matched_after": corr_pairing["matched"],
            "residual_count_before": {orig_pairing["only_a"], orig_pairing["only_b"]} == {0, 8},
            "residual_count_after": {corr_pairing["only_a"], corr_pairing["only_b"]} == {0, 8},
            "counts_top_level_unchanged": (
                original_parity["exact_parity_target"]["counts"] == corrected_parity["exact_parity_target"]["counts"]
            ),
            "verdict_unchanged": (
                original_decision["parity_passed"] == corrected_decision["parity_passed"]
                and original_decision["next_decision"] == corrected_decision["next_decision"]
            ),
            "conclusion": "I NUMERI SOSTANZIALI (matched=67, il set {0,8} di residui, i "
                "conteggi A=67/B=75/C=83, il verdetto parity_passed=True e "
                "next_decision=BUILD_CANONICAL_BREAKOUT_ACC_DATASET) sono TUTTI invariati "
                "prima/dopo la correzione - come richiesto esplicitamente, il verdetto NON e' "
                "stato alterato perche' i numeri sostanziali restavano invariati. Solo le "
                "ETICHETTE dei campi (quale numero si chiama 'only_a' vs 'only_b') sono state "
                "corrette.",
        },
        "decision_script_was_self_consistent": {
            "note": "IMPORTANTE: il codice di DECISIONE (build_phase7_9g_decision.py) usava "
                "GIA' correttamente il significato reale dei campi (leggeva only_b per "
                "verificare 'zero residuo lato EA reale', che corrispondeva davvero al "
                "residuo di A grazie all'inversione) - il VERDETTO finale non era mai stato "
                "calcolato in modo sbagliato. Solo un lettore che avesse letto i NOMI dei "
                "campi nell'artifact JSON senza tracciare il codice (o un consumer futuro "
                "automatizzato) avrebbe potuto essere fuorviato.",
        },
    }

    other_consumers_checked = {
        "method": "grep -rln 'only_a|only_b' su server/research_scripts/phase7/ - nessun altro "
            "script del progetto (7.9C/7.9D/7.9E/7.9F, che usano nomi di campo espliciti e "
            "diversi come mt5_only/python_only/missing_in_diagnostic_run) usa questo pattern "
            "posizionale ambiguo - il problema era isolato alla sola Phase 7.9G.",
        "files_using_only_a_only_b_pattern": [
            "server/research_scripts/phase7/phase7_9g/build_postfix_signal_parity.py (CORRETTO)",
            "server/research_scripts/phase7/phase7_9g/build_phase7_9g_decision.py (CORRETTO, "
            "riferimenti only_a/only_b invertiti coerentemente)",
            "server/research_scripts/phase7/phase7_9g/test_phase_7_9g.py (CORRETTO)",
        ],
        "no_other_artifact_consumes_the_inverted_fields": True,
    }

    fix_applied = {
        "source_files_changed": [
            "server/research_scripts/phase7/phase7_9g/build_postfix_signal_parity.py "
            "(argomenti di pair_dates riordinati per corrispondere sempre al nome della "
            "sezione: A_vs_B->(A,B), A_vs_C->(A,C), B_vs_C->(B,C); commento esplicito "
            "aggiunto alla funzione)",
            "server/research_scripts/phase7/phase7_9g/build_phase7_9g_decision.py "
            "(riferimenti only_a/only_b scambiati per riflettere la nuova semantica corretta)",
            "server/research_scripts/phase7/phase7_9g/test_phase_7_9g.py (assertion "
            "aggiornate)",
        ],
        "artifacts_regenerated": [
            "server/research_scripts/phase7/phase7_9g/breakout_acc_postfix_signal_parity_v1.json",
            "server/research_scripts/phase7/phase7_9g/breakout_acc_phase7_9g_decision_v1.json",
        ],
        "original_data_preserved_at": [
            "server/research_scripts/phase7/phase7_10/raw_data/breakout_acc_postfix_signal_parity_v1_ORIGINAL_pre_label_fix.json",
            "server/research_scripts/phase7/phase7_10/raw_data/breakout_acc_phase7_9g_decision_v1_ORIGINAL_pre_label_fix.json",
        ],
        "vault_report_amended": "vault/01-Trading/NEXUS - Phase 7.9G BREAKOUT_ACC Live Fix + "
            "Parity Re-Establishment.md - nota di correzione aggiunta in testa, testo del "
            "corpo corretto dove citava direttamente only_a/only_b - NESSUNA cancellazione, "
            "cronologia preservata.",
    }

    return {
        "phase": "7.10", "task": 1, "candidate": "BREAKOUT_ACC", "baseline_commit": BASELINE_COMMIT,
        "answer_to_question_1": "SI - l'inversione only_a/only_b esisteva davvero, verificata "
            "direttamente sul codice sorgente (non assunta). I numeri sostanziali e il "
            "verdetto NON erano mai sbagliati - solo le etichette dei campi nell'artifact "
            "JSON. Corretto alla fonte, dati originali preservati, verdetto invariato.",
        "verification": verification,
        "other_consumers_checked": other_consumers_checked,
        "fix_applied": fix_applied,
    }


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    save_json(os.path.join(PHASE710_DIR, "breakout_acc_7_9g_label_correction_v1.json"), doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print("answer_to_question_1:", payload["answer_to_question_1"][:80], "...")
    return doc


if __name__ == "__main__":
    main()
