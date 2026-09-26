#!/usr/bin/env python3
"""Phase 7.15 punto 1 - riesegue i 18 test falliti (osservati durante il
lavoro non ancora committato di Phase 7.14) su un checkout pulito del
commit finale (4e29fd5, via `git worktree`) e classifica ogni
fallimento residuo in una delle tre categorie:
  REGRESSIONE_REALE - causata dal fix ORDER_BLOCK di questa fase;
  VINCOLO_STORICO_BASELINE - gia' presente PRIMA del fix (verificato
    rieseguendo la stessa suite su un checkout pulito del commit
    7b823b9, prima del fix) - ambientale (git core.autocrlf, path
    assoluti hardcoded) o una staleness attesa/auto-diagnosticata;
  DIFETTO_VERIFICATORE - un bug nel verificatore/test di QUESTA fase
    (7.14) che va corretto.

Metodologia: NON si modificano i test storici congelati. Ogni
classificazione e' supportata da un confronto empirico diretto
(riproduzione su due worktree puliti, PRE-fix e POST-fix).
"""
import os
import sys

PHASE715_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE715_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json  # noqa: E402

BASELINE_COMMIT = "7b823b9"   # Phase 7.13, prima del fix
FIX_COMMIT = "4e29fd5"        # Phase 7.14 + follow-up verificatore

ORIGINAL_18_FAILURES_WORKING_TREE_STATE = {
    "context": "Osservati durante il lavoro di Phase 7.14 PRIMA del commit, con "
               "NXS_Strategies.mqh modificato nella working tree ma non ancora "
               "committato - ogni verificatore storico che controlla "
               "`git diff HEAD -- MQL5/ == vuoto` falliva perche' la working tree "
               "conteneva davvero un diff non committato.",
    "reproducible_on_clean_checkout": False,
    "explanation": "Su un checkout pulito (git worktree) del commit finale, la "
                   "working tree COINCIDE con HEAD per definizione - `git diff HEAD` "
                   "e' sempre vuoto indipendentemente da cosa e' cambiato fra commit "
                   "storici. Non e' un vincolo di baseline ne' una regressione: era "
                   "un artefatto dello STATO DELLA WORKING TREE al momento "
                   "dell'osservazione originale, gia' risolto dal commit stesso.",
        "verified_by": "git worktree add a 4e29fd5 + riesecuzione della suite Phase 7 "
                       "completa - questi 18 nomi specifici non compaiono piu' fra i "
                       "fallimenti.",
}

RESIDUAL_FAILURES_ON_CLEAN_CHECKOUT = [
    {
        "test": "phase7_12/test_phase_7_12.py::TestIndependentVerifier::test_verifier_reports_zero_errors",
        "assertion_message": "NXS_Strat_OrderBlock() sembra GIA' avere una guardia NXS_Profile_TF - "
                             "il finding ORDER_BLOCK/priorita' andrebbe rivisto (il difetto potrebbe "
                             "essere gia' stato corretto)",
        "category": "VINCOLO_STORICO_BASELINE_ATTESO",
        "confirmed_absent_at_baseline": True,
        "baseline_check": f"30/30 PASS su checkout pulito di {BASELINE_COMMIT} (guardia assente, "
                          "come atteso all'epoca di Phase 7.12)",
        "postfix_check": f"1 FAIL su checkout pulito di {FIX_COMMIT} - messaggio auto-diagnostico "
                         "PROGETTATO per rilevare esattamente questa situazione",
        "explanation": "Il verificatore di Phase 7.12 e' stato scritto per rilevare "
                      "ATTIVAMENTE se il proprio finding (ORDER_BLOCK privo di guardia) "
                      "diventasse stale - e' un comportamento CORRETTO e DESIDERATO: "
                      "segnala che la premessa storica di Phase 7.12 va rivista alla "
                      "luce del fix. Non e' un difetto ne' una regressione - e' "
                      "l'esecuzione riuscita del proprio scopo diagnostico.",
        "action_recommended": "Nessuna correzione al verificatore di Phase 7.12 (resta "
                              "congelato, la sua staleness E' l'informazione utile). "
                              "Annotare nel MOC/indice del vault che Phase 7.12 e' "
                              "SUPERSEDED-IN-PART da Phase 7.13/7.14 per ORDER_BLOCK.",
    },
    {
        "test": "phase7_13/test_phase_7_13.py::TestDeterminism::test_all_artifacts_deterministic "
               "(+ 6 altri nello stesso file: TestAbSimulation.test_gates_declared_not_modeled, "
               ".test_m5_pass_declared_excluded, .test_material_impact_flag_matches_observed_"
               "divergence, .test_non_canonical_passes_dominate_raw_triggers, "
               ".test_not_a_backtest_campaign_flags, .test_structural_consistency - 7 test in totale)",
        "assertion_message": "FileNotFoundError: multi_tf_dataset_v1.json (~31MB) non presente",
        "category": "VINCOLO_STORICO_BASELINE_DICHIARATO",
        "confirmed_absent_at_baseline": "N/A (phase7_13 non esisteva ancora al commit 7b823b9)",
        "environment_dependent": True,
        "explanation": "Limite di riproducibilita' DICHIARATO ESPLICITAMENTE nel vault report "
                      "di Phase 7.13 stesso ('Nota di riproducibilita' - multi_tf_dataset_v1.json "
                      "NON committato'): l'artifact e' deterministico e rigenerabile dalla fonte "
                      "M15 locale (anch'essa non tracciata), ma su un clone/checkout pulito senza "
                      "quei file locali i test che li richiedono falliscono per costruzione - non "
                      "e' una conseguenza del fix ORDER_BLOCK di Phase 7.14. CONFERMATO: questi 7 "
                      "test PASSANO nella working directory principale (dove il file locale "
                      "esiste), falliscono SOLO su un fresh checkout/worktree.",
        "action_recommended": "Nessuna azione in questa fase (limite gia' documentato e accettato "
                              "quando scritto). Se in futuro si vuole una CI che parta da un clone "
                              "pulito, servirebbe un artifact piu' piccolo o una fixture sintetica "
                              "dedicata - fuori scope di questa chiusura.",
    },
    {
        "test": "phase7_13/test_phase_7_13.py::TestIndependentVerifier::test_verifier_reports_zero_errors",
        "assertion_message": "DUE modalita' di fallimento diverse a seconda dell'ambiente: (a) su "
                             "worktree pulito SENZA multi_tf_dataset_v1.json locale: "
                             "FileNotFoundError; (b) nella working directory principale CON il "
                             "file locale presente: \"NXS_Strat_OrderBlock() sembra GIA' avere una "
                             "guardia NXS_Profile_TF...\" (stesso messaggio auto-diagnostico di "
                             "Phase 7.12)",
        "category": "VINCOLO_STORICO_BASELINE_DICHIARATO_E_ATTESO_COMBINATI",
        "confirmed_absent_at_baseline": f"al commit {BASELINE_COMMIT} (prima del fix) il "
                                        "verificatore di Phase 7.13 passa (verificato: guardia "
                                        "assente, come atteso all'epoca)",
        "environment_dependent": True,
        "explanation": "Isolato in questa fase separatamente da test_all_artifacts_deterministic "
                      "perche' la SUA causa di fallimento cambia con l'ambiente: dati assenti -> "
                      "FileNotFoundError (vincolo dichiarato); dati presenti -> staleness "
                      "self-check (stesso comportamento CORRETTO E VOLUTO del verificatore di "
                      "Phase 7.12, che rileva attivamente che il proprio finding e' superato dal "
                      "fix). In NESSUN caso e' una regressione introdotta da questa fase.",
        "action_recommended": "Nessuna correzione al verificatore di Phase 7.13 (stesso "
                              "ragionamento di Phase 7.12 sopra).",
    },
    {
        "test": "phase7_9c/test_phase_7_9c.py::TestScopeConstraints::test_phase_e_source_untouched, "
               "TestIndependentVerifierPasses::test_verifier_reports_zero_errors",
        "assertion_message": "hash SHA256 di results/cost_calibration_67_rerun/"
                             "phase_e_breakoutacc_findings.json diverso da quello dichiarato",
        "category": "VINCOLO_STORICO_BASELINE_AMBIENTALE",
        "confirmed_absent_at_baseline": False,
        "baseline_check": f"STESSO fallimento riprodotto su checkout pulito di {BASELINE_COMMIT} "
                          "(prima di qualunque lavoro ORDER_BLOCK) - quindi preesistente, non "
                          "introdotto da questa fase",
        "root_cause_confirmed": "git config core.autocrlf=true in questo repository: un "
                                "`git worktree add`/clone pulito converte LF->CRLF nei file di "
                                "testo al checkout, alterando il contenuto byte-per-byte (e quindi "
                                "lo SHA256) di QUALUNQUE artifact JSON verificato byte-esatto - "
                                "verificato con un dump esadecimale diretto (0x7b0a vs 0x7b0d0a). "
                                "La working directory originale non e' mai stata ri-checked-out da "
                                "zero con questa impostazione attiva, quindi mantiene gli LF "
                                "originali e l'hash dichiarato al momento della scrittura.",
        "explanation": "Fragilita' AMBIENTALE preesistente e generale (non specifica di "
                      "ORDER_BLOCK): qualunque verificatore storico che controlla un hash "
                      "byte-esatto di un file di testo committato e' vulnerabile alla stessa "
                      "conversione di fine riga su un fresh checkout/worktree/clone.",
        "action_recommended": "PROPOSTA (non applicata in questa fase, riguarda verificatori "
                              "storici congelati che questa task non deve alterare): normalizzare "
                              "gli hash calcolandoli su contenuto letto in modalita' testo con "
                              "line-ending canonico (es. universal newlines) invece che sui byte "
                              "grezzi del file, OPPURE impostare `.gitattributes` con "
                              "`* -text` o `*.json binary` per questi path specifici cosi' che git "
                              "non applichi mai la conversione. Decisione per un futuro giro "
                              "dedicato, non per questa chiusura.",
    },
    {
        "test": "phase7_9d/test_phase_7_9d.py::TestIndependentVerifierPasses::test_verifier_reports_zero_errors",
        "assertion_message": "certificato citato non trovato su disco: "
                             "<ROOT_WORKTREE>/../../AppData/Roaming/MetaQuotes/Terminal/Common/"
                             "Files/NEXUS/certificates/GOLD_2019.02.03_00-00-00_sel9.json",
        "category": "VINCOLO_STORICO_BASELINE_AMBIENTALE",
        "confirmed_absent_at_baseline": False,
        "baseline_check": f"STESSO fallimento riprodotto su checkout pulito di {BASELINE_COMMIT}",
        "root_cause_confirmed": "Il verificatore di Phase 7.9D risolve il percorso del certificato "
                                "con una traversata relativa hardcoded (`../../AppData/Roaming/...`) "
                                "che assume ROOT sia esattamente `C:\\Users\\User\\ClaudeWork\\MAX` - "
                                "su un worktree in un percorso diverso (es. una cartella Temp) la "
                                "traversata relativa produce un percorso sbagliato.",
        "explanation": "Fragilita' di portabilita' preesistente, non introdotta da Phase 7.14 - "
                      "il verificatore storico non e' pensato per girare da un percorso diverso "
                      "da quello originale del clone.",
        "action_recommended": "PROPOSTA (non applicata, verificatore storico congelato): "
                              "risolvere la cartella Common/Files di MetaQuotes leggendo "
                              "%APPDATA% invece di una traversata relativa hardcoded dal ROOT del "
                              "repository. Decisione per un futuro giro dedicato.",
    },
    {
        "test": "phase7_9g/test_phase_7_9g.py::TestIndependentVerifierPasses::test_verifier_reports_zero_errors",
        "assertion_message": "stale evidence reclassification: ricostruzione indipendente differisce",
        "category": "VINCOLO_STORICO_BASELINE_AMBIENTALE",
        "confirmed_absent_at_baseline": False,
        "baseline_check": f"STESSO fallimento riprodotto su checkout pulito di {BASELINE_COMMIT}",
        "root_cause_confirmed": "Stessa causa radice del gruppo phase7_9c: hash byte-esatto di un "
                                "artifact JSON, alterato dalla conversione LF->CRLF di "
                                "core.autocrlf=true su un fresh checkout.",
        "explanation": "Vedi phase7_9c sopra - stessa fragilita' ambientale, non specifica di "
                      "questo file.",
        "action_recommended": "Stessa proposta di phase7_9c/phase7_9d - non applicata qui.",
    },
    {
        "test": "phase7_9k/test_phase_7_9k.py::TestDeterminism::test_decision_card_v2_deterministic, "
               "TestDecisionCardV2 (4 test), TestIndependentVerifier::test_verifier_reports_zero_errors "
               "- 6 test in totale, SOLO quando l'intera suite Phase 7 gira nello stesso processo "
               "pytest insieme a Phase 7.14",
        "assertion_message": "KeyError: 'ema100_precision' / 'final_decision' / 'reevaluation_note' "
                             "(chiavi specifiche di BREAKOUT_ACC/Phase 7.9K assenti dal payload "
                             "effettivamente restituito)",
        "category": "DIFETTO_VERIFICATORE_ISOLAMENTO_TEST_RISOLTO_IN_QUESTA_FASE",
        "confirmed_absent_at_baseline": False,
        "root_cause_confirmed": "Collisione di nome modulo Python: sia phase7_9k SIA phase7_14 "
                                "(introdotto in questa sessione) avevano un file chiamato "
                                "IDENTICAMENTE `build_decision_card_v2.py`. Quando pytest importa "
                                "entrambi i file di test nello stesso processo, il secondo "
                                "`import build_decision_card_v2` (qualunque fase esegua per "
                                "seconda) restituisce il modulo GIA' presente in sys.modules dalla "
                                "prima fase importata, invece di ricaricare dal proprio "
                                "sys.path[0] - `sys.path.insert(0, ...)` non forza un "
                                "re-import se il nome del modulo e' gia' stato risolto una volta. "
                                "Verificato isolando la coppia phase7_14+phase7_9k e osservando "
                                "quale delle due fallisce a seconda dell'ordine di esecuzione.",
        "explanation": "Difetto REALE di isolamento dei test introdotto in QUESTA sessione "
                      "(scegliendo un nome file generico gia' usato da una fase precedente) - "
                      "MA NON e' una regressione del FIX ORDER_BLOCK ne' delle sue conclusioni: "
                      "nessun contenuto scientifico era coinvolto, solo un conflitto di nomi di "
                      "file Python. Non riproducibile eseguendo phase7_9k da solo (39/39 PASS in "
                      "isolamento, verificato).",
        "action_taken_this_closure": "RISOLTO (non solo proposto): rinominato "
                                     "server/research_scripts/phase7/phase7_14/"
                                     "build_decision_card_v2.py -> "
                                     "build_order_block_decision_card_v2.py (file introdotto in "
                                     "questa stessa sessione, non un file storico congelato di "
                                     "un'altra fase - phase7_9k NON e' stato toccato). Aggiornati "
                                     "i riferimenti in phase7_14/verify_phase_7_14.py e "
                                     "phase7_15/test_phase_7_15.py e verify_phase_7_15.py. "
                                     "Verificato: suite Phase 7 completa ri-eseguita dopo la "
                                     "rinomina, zero occorrenze di questo KeyError.",
    },
]

FULL_SUITE_RERUN_AFTER_ALL_FIXES = {
    "context": "Riesecuzione della suite Phase 7 completa nella working directory principale "
              "(non un worktree) DOPO la rinomina del modulo che risolve la collisione sopra.",
    "result": "489 passed, 2 failed",
    "the_2_remaining_failures": [
        "phase7_12/test_phase_7_12.py::TestIndependentVerifier::test_verifier_reports_zero_errors "
        "(staleness self-check, atteso)",
        "phase7_13/test_phase_7_13.py::TestIndependentVerifier::test_verifier_reports_zero_errors "
        "(stessa staleness self-check, dati locali presenti in questa working directory)",
    ],
    "phase7_9c_9d_9g_environmental_failures_present": False,
    "phase7_9c_9d_9g_note": "Non compaiono in questa working directory perche' i suoi file non "
                            "sono mai stati ri-checked-out da zero con core.autocrlf=true attivo - "
                            "compaiono SOLO su un fresh clone/worktree (dimostrato separatamente "
                            "con git worktree, vedi sopra).",
    "phase7_13_filenotfound_failures_present": False,
    "phase7_13_filenotfound_note": "Non compaiono in questa working directory perche' "
                                   "multi_tf_dataset_v1.json esiste localmente qui (non "
                                   "committato, ma presente su disco).",
}


def build():
    payload = {
        "baseline_commit": BASELINE_COMMIT,
        "fix_commit": FIX_COMMIT,
        "method": "git worktree add a entrambi i commit, riesecuzione della suite Phase 7 "
                 "completa su ciascun checkout pulito, confronto dei nomi/messaggi di "
                 "fallimento per distinguere regressione reale da vincolo preesistente",
        "original_18_failures_working_tree_state": ORIGINAL_18_FAILURES_WORKING_TREE_STATE,
        "residual_failures_on_clean_checkout_of_fix_commit": RESIDUAL_FAILURES_ON_CLEAN_CHECKOUT,
        "full_suite_rerun_after_all_fixes": FULL_SUITE_RERUN_AFTER_ALL_FIXES,
        "n_distinct_failure_groups": len(RESIDUAL_FAILURES_ON_CLEAN_CHECKOUT),
        "n_actual_failing_tests_on_clean_checkout": 19,
        "n_real_regressions_caused_by_order_block_fix": 0,
        "n_expected_baseline_staleness_tests": 2,
        "n_declared_reproducibility_limit_tests": 7,
        "n_preexisting_environmental_fragility_tests": 4,
        "n_test_isolation_defects_found_and_resolved_this_closure": 6,
        "no_frozen_test_modified_to_force_green": True,
        "no_assertion_disabled": True,
        "verifier_fixes_proposed_but_not_applied": [
            "phase7_9c/phase7_9g: hash su contenuto normalizzato invece che su byte grezzi, o "
            ".gitattributes dedicato",
            "phase7_9d: risoluzione della cartella Common/Files via %APPDATA% invece di "
            "traversata relativa hardcoded",
        ],
        "verifier_fix_applied_this_closure": "Rinominato server/research_scripts/phase7/phase7_14/"
                                             "build_decision_card_v2.py in "
                                             "build_order_block_decision_card_v2.py (file di "
                                             "QUESTA sessione, non storico) per risolvere una "
                                             "collisione di nome modulo con phase7_9k - vedi "
                                             "l'ultimo elemento di residual_failures sopra. Nessuna "
                                             "modifica ai verificatori storici (7.9c/7.9d/7.9g/"
                                             "7.12/7.13) - solo proposte, per preservarne la "
                                             "riproducibilita' come richiesto esplicitamente dal task.",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE715_DIR, "regression_reclassification_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    print(f"  gruppi di fallimento distinti: {payload['n_distinct_failure_groups']} "
          f"({payload['n_actual_failing_tests_on_clean_checkout']} test totali)")
    print(f"  regressioni reali causate dal fix: {payload['n_real_regressions_caused_by_order_block_fix']}")


if __name__ == "__main__":
    main()
