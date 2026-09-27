#!/usr/bin/env python3
"""Phase 7.21 punto 1/2 - DATA_EXPOSURE_MAP. Congela la hypothesis
PRIMA di guardare nuovi risultati e determina quali dati sono davvero
untouched. Nessuna statistica economica calcolata qui - solo mappatura
della provenienza/esposizione.
"""
import os
import sys

PHASE721_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE79H_DIR = os.path.abspath(os.path.join(PHASE721_DIR, "..", "phase7_9h"))
PHASE79K_DIR = os.path.abspath(os.path.join(PHASE721_DIR, "..", "phase7_9k"))
ROOT = os.path.abspath(os.path.join(PHASE721_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, load_json  # noqa: E402


def build():
    hypothesis = {
        "canonical_strategy": "BREAKOUT_ACC_INTENDED_D1_V1",
        "dataset_implementation": "Esclusivamente l'implementazione post-fix canonica (cooldown "
            "per-direzione, Phase 7.9G) e il dataset/event definitions gia' validate: "
            "phase7_9k/breakout_acc_intended_d1_v2_dataset.json (schema V2, offset corretto) - "
            "NON il v1 (Phase 7.9H, superseded). Nessuna modifica alla strategia in questa fase.",
        "hypothesis_primary": {
            "id": "H1_NET_EXPECTANCY_POSITIVE",
            "statement": "La strategia (ALL, aggregata BUY+SELL) possiede expectancy netta positiva "
                        "dopo costi realistici.",
        },
        "hypothesis_secondary": {
            "id": "H2_BUY_MORE_ROBUST_THAN_SELL",
            "statement": "Il lato BUY possiede expectancy positiva piu' robusta del lato SELL.",
            "status": "POST_HOC rispetto alla ricerca precedente (Phase 7.9I/J/K hanno scoperto "
                     "l'asimmetria BUY/SELL guardando l'INTERO campione di 75 eventi) - richiede "
                     "esplicitamente evidenza NUOVA E INDIPENDENTE, non una ri-conferma sugli stessi "
                     "eventi gia' usati per formulare l'ipotesi.",
        },
        "no_strategy_modification_to_favor_buy": True,
        "frozen_before_any_new_result_examined": True,
    }

    exposure_map = {
        "principle": "Un periodo e' UNTOUCHED per una data ipotesi solo se nessun essere umano o "
                    "script di ricerca lo ha mai esaminato per QUELLA domanda specifica, prima "
                    "d'ora. 'Esiste nel dataset' non equivale a 'e' stato guardato per decidere "
                    "qualcosa'.",
        "source_run_identity": {
            "run_id": "GOLD_2019.02.03 00:00:00_sel9_r002/r003",
            "period_covered_by_the_mt5_tester_run_itself": "2019.02.04 01:00:00 - 2026.08.14 23:57:59 "
                "(dal certificate Phase 7.9G/H, VERDICT=PASS)",
            "n_generated_signals_in_raw_trace": 67,
            "last_generated_signal_timestamp": "2026.06.09 04:30:00",
            "note_on_the_gap": "Il run e' arrivato fino al 2026.08.14 ma l'ULTIMO segnale generato e' "
                "del 2026.06.09 - verificato riga per riga sul trace raw "
                "(phase7_9g/raw_data/postfix_live_ea_trace_events.csv, 67 righe): NESSUNA riga oltre "
                "il 2026.06.09 - non e' censura di dati, la strategia semplicemente non ha generato "
                "altri segnali in quella finestra (dato informativo di per se', non un evento nuovo).",
        },
        "periods": [
            {
                "period": "2019.02.21 - 2026.06.09 (i 75 eventi del dataset canonico V2)",
                "used_for_development": True,
                "seen_in_reports": True,
                "used_for_mechanism_discovery": True,
                "used_to_choose_buy_vs_sell": True,
                "used_for_tuning": "Solo il cooldown (Phase 7.9G, un fix strutturale gia' applicato "
                                  "prima che questo dataset esistesse) - nessun parametro economico "
                                  "(SL/TP/size) mai ottimizzato su questi eventi.",
                "genuinely_untouched": False,
                "verdict": "COMPLETAMENTE ESPOSTO per H2 (usato per scoprire l'asimmetria BUY/SELL in "
                          "Phase 7.9I/J). Utilizzabile SOLO come BASELINE DESCRITTIVA per H1 (nessuno "
                          "aveva mai calcolato expectancy in $/R/PF/costi su questi eventi prima - "
                          "quella e' un'analisi NUOVA, anche se sugli STESSI eventi) - non come "
                          "conferma indipendente.",
            },
            {
                "period": "2026.06.10 - 2026.08.14 (coperto dal run MT5 stesso, zero segnali generati)",
                "used_for_development": False,
                "seen_in_reports": False,
                "used_for_mechanism_discovery": False,
                "used_to_choose_buy_vs_sell": False,
                "used_for_tuning": False,
                "genuinely_untouched": "PARZIALMENTE - la finestra temporale non e' mai stata "
                                       "esaminata per un evento specifico (perche' non ne esiste "
                                       "nessuno), ma il FATTO che sia stata attraversata dal run r002 "
                                       "senza generare segnali era gia' implicitamente visibile nel "
                                       "trace raw (67 righe, nessuna in questa finestra) - non e' "
                                       "stato pero' mai esplicitamente riportato o usato in nessuna "
                                       "decisione economica prima di questa fase.",
                "verdict": "Non contiene eventi - non utilizzabile ne' come discovery ne' come OOS. "
                          "Riportato qui solo per completezza/trasparenza.",
            },
            {
                "period": "2026.08.15 - oggi (2026.09.27)",
                "used_for_development": False, "seen_in_reports": False,
                "used_for_mechanism_discovery": False, "used_to_choose_buy_vs_sell": False,
                "used_for_tuning": False,
                "genuinely_untouched": True,
                "verdict": "VERO HOLDOUT - mai attraversato da NESSUNA versione dell'EA (il run r002 "
                          "si fermava al 2026.08.14), mai osservato da nessun essere umano o script "
                          "di ricerca. Candidato OOS forward - vedi build_oos_forward_analysis.py. "
                          "Finestra corta (~6 settimane) - atteso pochissimi eventi data la cadenza "
                          "storica (9-16/anno), possibile INSUFFICIENT_OOS_SAMPLE (esito ammesso, non "
                          "un fallimento).",
            },
            {
                "period": "prima del 2019.02.03",
                "used_for_development": "SCONOSCIUTO - non investigato in questa fase.",
                "genuinely_untouched": "NON VERIFICATO - disponibilita' e qualita' dati (tick reali vs "
                                       "sintetici) per questo simbolo/broker prima del 2019.02.03 non "
                                       "controllata in questa fase.",
                "verdict": "NON USATO come opzione OOS in questa fase - il run r002/r003 stesso "
                          "(identita' canonica di riferimento per questa strategia) parte da "
                          "2019.02.04, e sweep37 (l'altro run multi-strategia a tick reali del "
                          "progetto) copre 2019.07.11 in poi - nessuna evidenza raccolta finora nel "
                          "progetto suggerisce dati di qualita' comparabile prima di quella soglia. "
                          "Scelta esplicita: usare SOLO il periodo forward (sopra), non investigare "
                          "l'arcivio pre-2019 in questa fase (fuori scope tempo/beneficio).",
            },
        ],
        "conclusion": "NESSUN vero holdout STORICO esiste all'interno del campione gia' raccolto "
                     "(2019.02-2026.06) - l'intero campione e' stato usato per mechanism discovery E "
                     "per scegliere BUY vs SELL. L'UNICA opzione genuinamente untouched e' un nuovo "
                     "periodo FORWARD (2026.08.15+, successivo al cutoff del run r002) - opzione "
                     "esplicitamente ammessa dalla task. Eseguito un nuovo run MT5 isolato "
                     "(selettore 9, stessa identita' canonica, stessa configurazione fingerprint di "
                     "r002) per questa finestra - vedi build_oos_forward_analysis.py per il risultato.",
    }

    payload = {"hypothesis_preregistration": hypothesis, "data_exposure_map": exposure_map}
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE721_DIR, "data_exposure_map_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")


if __name__ == "__main__":
    main()
