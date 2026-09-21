#!/usr/bin/env python3
"""Phase 7.8A - Value-of-Information Contract: VOLATILITY_BREAKOUT_CONFIRMED.

Dopo Phase 7.7A/7.7B (Strategy Lifecycle Registry, Structural Eligibility/
Research Readiness gate, semantica a due assi), VOLATILITY_BREAKOUT_
CONFIRMED resta l'unico candidato con evidenza HOLD_NEEDS_MORE_EVIDENCE
(non refutato, non eseguito il Serious 3Y). La domanda NON e' "sembra
buona?" ma: vale la pena spendere compute/data/research budget per il
Serious 3Y rispetto alle alternative disponibili? Questo modulo
costruisce il contratto decisionale ex-ante PRIMA di eseguire quel test.

Principi non negoziabili (dalla richiesta):
- NESSUN backtest eseguito qui (ne' Serious 3Y ne' altro).
- NESSUN nuovo outcome letto.
- NESSUNA optimization di parametri.
- NESSUNA applicazione di MECH-23.
- NESSUN punteggio numerico VoI inventato (niente 'VoI=82/100') - se
  mancano prior calibrati e una funzione di utilita' esplicita, si
  dichiara NUMERIC_VOI_NOT_IDENTIFIED e si usa un framework ordinale
  trasparente (LOW/MEDIUM/HIGH con rationale), mai un punteggio
  aggregato opaco.
- Tutta l'evidenza e' ricostruita ESCLUSIVAMENTE dagli artifact
  canonici gia' congelati (Strategy Foundry Phase 3, Phase 7.7A/7.7B) -
  nessuna reinterpretazione ottimistica."""
import os
import sys

PHASE78A_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78A_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78A_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "fdab6e73def3fa50665e2d111a5cd8e7ccda48ce"
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"

LIFECYCLE_REGISTRY_PATH = os.path.join(PHASE7_DIR, "phase7_7a", "strategy_lifecycle_registry_v1.json")
GATE_PATH = os.path.join(PHASE7_DIR, "phase7_7b", "strategy_meta_filter_gate_v1.json")
REFINEMENT_PATH = os.path.join(PHASE7_DIR, "phase7_7b", "missing_field_semantics_refinement_v1.json")
FOUNDRY3_PATH = os.path.join(ROOT, "vault", "01-Trading",
                              "NEXUS - Strategy Foundry Phase 3 Volatility Breakout Implementation.md")
FAILURE_MEMORY_PATH = os.path.join(
    ROOT, "vault", "01-Trading",
    "NEXUS - Failure Memory (Registro Pattern di Fallimento Metodologico) (12-09).md",
)


def build():
    lifecycle_doc = load_json(LIFECYCLE_REGISTRY_PATH)
    candidate = lifecycle_doc["payload"]["deep_dive_candidates"][CANDIDATE_ID]
    gate_doc = load_json(GATE_PATH)
    gate_result = gate_doc["payload"]["gate_results_by_candidate"][CANDIDATE_ID]
    refinement_doc = load_json(REFINEMENT_PATH)
    refined_status = refinement_doc["payload"]["per_candidate_field_classifications"][CANDIDATE_ID][
        "refined_structural_status"]

    # ================= 1. Current evidence state (solo da artifact canonici) =================
    current_evidence_state = {
        "lifecycle_completeness": {
            "classification": candidate["classification"],
            "structural_status_current": refined_status,
            "note": "FULL_STRATEGY_SPEC: entry/direction/invalidation/target/timeout tutti espliciti "
                    "(Strategy Foundry Phase 3) - unico candidato del registro con lifecycle interamente "
                    "estratto e verificato.",
        },
        "signal_parity_python_mql5": candidate["evidence_ladder"]["signal_parity_python_vs_mql5"],
        "discovery_result": candidate["evidence_ladder"]["discovery"],
        "internal_validation_result": candidate["evidence_ladder"]["internal_validation"],
        "full_backtest_engine_result": candidate["evidence_ladder"]["full_backtest_engine"],
        "fast_structural_result": candidate["evidence_ladder"]["fast_structural_real_ticks_6mo"],
        "sample_size": {
            "fast_structural": "n=14 (6 mesi, tick reali)",
            "full_backtest_engine": "n=243 trade (intero storico disponibile, non necessariamente a costi "
                                     "realistici - vedi cost_evidence sotto)",
            "raw_events_screening": "n~927 (Phase 2 discovery+validation, conteggio eventi grezzi non "
                                     "gestione one-at-a-time)",
            "assessment": "n=14 e' ben sotto qualunque soglia minima di campione gia' usata altrove nel "
                           "progetto (es. cluster_count_minimum=20, n_nominal_minimum=30, minimum_evidence_"
                           "gates.json) - il campione fast-structural da solo non e' sufficiente per una "
                           "decisione forte in nessuna direzione.",
        },
        "temporal_concentration": {
            "finding": "Il profitto netto dei 6 mesi fast-structural viene quasi interamente da 2 mesi su 5 "
                       "attivi (marzo +$532.40 n=5, agosto +$431.20 n=6 = +$963.60 combinato); "
                       "aprile-giugno uniformemente in perdita, luglio zero segnali.",
            "assessment": "Distribuzione non ancora rassicurante indipendentemente dal campionamento "
                           "specifico - non distinguibile da rumore su un campione di 5 mesi attivi.",
        },
        "direction_asymmetry": {
            "finding": "BUY PF=0.734 (n=9) vs SELL PF=2.236 (n=5) sul fast-structural - marcata ma su "
                       "campioni per-lato troppo piccoli per distinguere pattern strutturale da rumore.",
            "assessment": "Asimmetria aperta, non risolvibile con il campione attuale.",
        },
        "cost_evidence": {
            "full_backtest_engine": "PF=1.20 dichiarato ESPLICITAMENTE 'a costo zero' (Strategy Foundry "
                                     "Phase 3, sez.2) - NON un test di robustezza ai costi su campione ampio.",
            "fast_structural": "Tick reali, costi/broker nativi non alterati (audit di parita', sez.4) - ma "
                                "solo su n=14, insufficiente per una conclusione di robustezza ai costi.",
            "assessment": "Nessun test di robustezza ai costi su un campione sufficientemente ampio esiste "
                           "oggi per questa strategia - un gap reale, indipendente dal segno del PF.",
        },
        "external_evidence": {
            "finding": "Nessuna cross-feed validation (fonte dati diversa da quella gia' usata) mai "
                       "tentata per questo candidato - a differenza di SAR (H015, Dukascopy esterno) o "
                       "H006 (true holdout su un periodo mai visto).",
            "assessment": "Assente - un asse di incertezza (validita' esterna/robustezza alla fonte dati) "
                           "mai testato.",
        },
        "current_meta_filter_gate_status": {
            "structural": refined_status, "readiness": gate_result["meta_filter_research_readiness"],
            "gate_passed": gate_result["meta_filter_ready_gate_passed"],
        },
    }

    # ================= 2. Decision to be informed =================
    decision_to_be_informed = {
        "possible_actions": {
            "A_ABANDON_ARCHIVE": "Il candidato viene archiviato/segnato REFUTED-equivalente - nessun "
                                  "ulteriore investimento di ricerca su questo design.",
            "B_HOLD_NEED_MORE_EVIDENCE": "Stato attuale - nessuna azione, resta in attesa.",
            "C_ADVANCE_TO_NEXT_VALIDATION_GATE": "Promozione allo stage successivo del lifecycle "
                                                  "(tipicamente demo/paper-trading o un ulteriore gate "
                                                  "intermedio) - MAI 'GO LIVE' come conseguenza diretta di "
                                                  "un singolo Serious 3Y, che resta comunque solo un "
                                                  "gate di validazione, non l'ultimo della catena "
                                                  "(EXECUTION_VALIDATION e PORTFOLIO_RISK restano "
                                                  "successivi e indipendenti - vedi pipeline formalizzata "
                                                  "in Phase 7.7A).",
        },
        "explicit_exclusion": "GO_LIVE non e' mai un'azione direttamente sbloccata da questo test - "
                               "richiederebbe comunque EXECUTION_VALIDATION (gia' mostrato critico da "
                               "WICK_SWEEP_RECLAIM - vedi Failure Memory) e una valutazione di portfolio/"
                               "rischio separata.",
        "current_state": "B_HOLD_NEED_MORE_EVIDENCE (stato gia' congelato in Phase 7.7A/7.7B, non "
                          "rivalutato qui).",
    }

    # ================= 3. Serious 3Y information question =================
    uncertainty_axes = {
        "sign_uncertainty": {
            "current_level": "MEDIUM-LOW",
            "rationale": "4 letture concordi e indipendenti nella DIREZIONE positiva (discovery +0.037R, "
                         "validation +0.133R, full-backtest PF=1.20, fast-structural PF=1.165) - il segno "
                         "e' gia' relativamente ben stabilito rispetto ad altri candidati del registro. "
                         "Un Serious 3Y contribuirebbe QUI relativamente poco in termini marginali.",
        },
        "magnitude_uncertainty": {
            "current_level": "HIGH",
            "rationale": "PF oscilla 1.165-1.20 attraverso metodi/campioni diversi, tutti vicini al "
                         "breakeven - la vera magnitudo dell'edge (se esiste) resta poco vincolata.",
        },
        "temporal_stability": {
            "current_level": "HIGH",
            "rationale": "Solo 5 mesi attivi osservati; nessuna osservazione multi-anno/multi-regime.",
        },
        "direction_asymmetry": {
            "current_level": "HIGH",
            "rationale": "BUY/SELL PF marcatamente diversi su campioni troppo piccoli (9/5) per distinguere "
                         "struttura da rumore.",
        },
        "cost_robustness": {
            "current_level": "HIGH",
            "rationale": "Il PF a campione piu' ampio (243 trade) e' esplicitamente 'a costo zero' - MAI "
                         "testato con costi realistici su un campione di quella dimensione.",
        },
        "regime_concentration": {
            "current_level": "HIGH",
            "rationale": "2 mesi su 5 spiegano quasi tutto il profitto fast-structural.",
        },
        "sample_adequacy": {
            "current_level": "HIGH",
            "rationale": "n=14 ben sotto qualunque soglia minima di progetto gia' in uso altrove.",
        },
        "summary": "Il Serious 3Y indirizzerebbe PRINCIPALMENTE magnitude/temporal-stability/cost-"
                   "robustness/regime-concentration/sample-adequacy (tutti HIGH oggi) - MARGINALMENTE il "
                   "sign uncertainty (gia' relativamente basso) - e PARZIALMENTE la direction asymmetry "
                   "(un campione piu' ampio aiuterebbe ma non e' l'unico modo di risolverla, vedi "
                   "alternative sotto).",
    }

    # ================= 4. Alternative experiments (concettuali, nessuno eseguito) =================
    alternatives = {
        "SERIOUS_3Y_FULL_TEST": {
            "description": "Il test sotto valutazione - backtest realistico multi-anno con costi/esecuzione "
                            "realistici sull'intero design gia' congelato (nessuna modifica di spec).",
            "addresses_axes": ["magnitude_uncertainty", "temporal_stability", "cost_robustness",
                                "regime_concentration", "sample_adequacy", "direction_asymmetry (parziale)"],
        },
        "LONGER_CHEAPER_BAR_LEVEL_VALIDATION": {
            "description": "Un'estensione dello screening a livello di evento grezzo (stile Phase 2) su uno "
                            "storico piu' lungo, SENZA il motore di esecuzione realistico completo - piu' "
                            "economico, meno realistico.",
            "addresses_axes": ["sample_adequacy (parziale)", "temporal_stability (parziale)"],
            "does_not_address": ["cost_robustness", "regime_concentration a livello di trade reale"],
        },
        "CROSS_FEED_VALIDATION": {
            "description": "Validazione su una fonte dati indipendente (stesso pattern gia' usato per SAR/"
                            "H015 - Dukascopy esterno via simbolo custom) - testa un asse MAI toccato finora "
                            "per questo candidato: la robustezza alla fonte dati stessa.",
            "addresses_axes": ["external_validity (nuovo asse, non nella lista originale ma reale)"],
            "does_not_address": ["sample_adequacy sullo stesso storico gia' usato",
                                  "cost_robustness a scala"],
        },
        "ADDITIONAL_RECENT_HOLDOUT": {
            "description": "Una finestra fresca e piu' breve (es. i prossimi 3-6 mesi) immediatamente "
                            "successiva alla finestra fast-structural gia' osservata - piu' economico di un "
                            "3Y completo.",
            "addresses_axes": ["temporal_stability (parziale)", "sample_adequacy (incremento piccolo)"],
            "does_not_address": ["cost_robustness a scala", "regime_concentration su piu' anni"],
        },
        "DIRECTION_SPECIFIC_DIAGNOSTIC": {
            "description": "Un test dedicato e PRE-REGISTRATO (non un semplice re-slice dei dati gia' "
                            "raccolti) specificamente sull'asimmetria BUY/SELL, con un campione fresco "
                            "condizionato sulla sola domanda direzionale.",
            "addresses_axes": ["direction_asymmetry (direttamente)"],
            "does_not_address": ["magnitude_uncertainty complessiva", "cost_robustness", "sample_adequacy generale"],
            "warning": "Un re-slice per DIREZIONE sui dati GIA' raccolti (non un campione fresco) sarebbe "
                       "un rescue post-hoc travestito da diagnostica - esplicitamente VIETATO. Solo un "
                       "campione NUOVO, pre-registrato su questa domanda specifica, e' scientificamente "
                       "lecito.",
        },
        "NO_TEST_WAIT_FOR_MORE_DATA": {
            "description": "Accumulare organicamente piu' trade fast-structural nel tempo prima di "
                            "impegnare compute per un test dedicato.",
            "addresses_axes": ["sample_adequacy (lentamente, nel tempo)"],
            "does_not_address": ["nessun asse in tempi brevi - il costo e' il tempo indefinito di attesa, "
                                  "non il compute"],
        },
    }

    # ================= 5. Cost of experiment (ordinale, nessun numero inventato) =================
    cost_matrix = {
        "SERIOUS_3Y_FULL_TEST": {"compute_cost": "HIGH", "data_cost": "MEDIUM", "engineering_cost": "LOW",
                                  "elapsed_time": "HIGH", "contamination_risk": "LOW",
                                  "researcher_degrees_of_freedom_risk": "LOW",
                                  "rationale": "Engineering gia' fatto (parita' Python/MQL5 927/927 gia' "
                                               "verificata, spec congelata) - il costo residuo e' quasi "
                                               "puramente compute/tempo/dati storici, con rischio di "
                                               "contaminazione/gradi di liberta' bassi perche' lo spec e' "
                                               "gia' frozen (nessun parametro da scegliere ora)."},
        "LONGER_CHEAPER_BAR_LEVEL_VALIDATION": {"compute_cost": "LOW", "data_cost": "LOW",
                                                 "engineering_cost": "LOW", "elapsed_time": "LOW",
                                                 "contamination_risk": "MEDIUM",
                                                 "researcher_degrees_of_freedom_risk": "MEDIUM",
                                                 "rationale": "Economico ma il rischio di gradi di liberta' "
                                                              "sale se si comincia a guardare metriche "
                                                              "diverse a livello di evento grezzo senza lo "
                                                              "stesso rigore del motore completo."},
        "CROSS_FEED_VALIDATION": {"compute_cost": "MEDIUM", "data_cost": "MEDIUM", "engineering_cost": "MEDIUM",
                                   "elapsed_time": "MEDIUM", "contamination_risk": "LOW",
                                   "researcher_degrees_of_freedom_risk": "LOW",
                                   "rationale": "Richiede una nuova pipeline di acquisizione dati (come gia' "
                                                "fatto per SAR/H015) - costo di ingegneria reale ma "
                                                "contenuto, pattern gia' esistente da riusare."},
        "ADDITIONAL_RECENT_HOLDOUT": {"compute_cost": "LOW", "data_cost": "LOW", "engineering_cost": "LOW",
                                       "elapsed_time": "LOW", "contamination_risk": "LOW",
                                       "researcher_degrees_of_freedom_risk": "LOW",
                                       "rationale": "Il piu' economico in assoluto, ma l'incremento di "
                                                    "informazione e' proporzionalmente piccolo (pochi mesi "
                                                    "in piu')."},
        "DIRECTION_SPECIFIC_DIAGNOSTIC": {"compute_cost": "LOW", "data_cost": "LOW", "engineering_cost": "LOW",
                                           "elapsed_time": "LOW", "contamination_risk": "HIGH",
                                           "researcher_degrees_of_freedom_risk": "HIGH",
                                           "rationale": "Economico MA rischioso se non genuinamente "
                                                        "pre-registrato su un campione fresco - alto rischio "
                                                        "di diventare un rescue post-hoc travestito."},
        "NO_TEST_WAIT_FOR_MORE_DATA": {"compute_cost": "LOW", "data_cost": "LOW", "engineering_cost": "LOW",
                                        "elapsed_time": "INDEFINITE_NOT_ORDINAL",
                                        "contamination_risk": "LOW",
                                        "researcher_degrees_of_freedom_risk": "LOW",
                                        "rationale": "Nessun costo di ricerca immediato, ma il costo reale e' "
                                                     "il tempo indefinito di attesa - non esprimibile con "
                                                     "LOW/MEDIUM/HIGH in modo comparabile agli altri."},
    }

    # ================= 6. Decision impact (decision tree congelata PRIMA del test) =================
    decision_tree = {
        "strong_negative": {
            "definition": "CI ampiamente sotto breakeven su campione largo, nessun sottogruppo "
                          "materialmente positivo",
            "action": "A_ABANDON_ARCHIVE",
            "note": "Coerente con no_rescue_clause gia' applicato altrove nel progetto (es. H006) - nessun "
                    "tentativo di salvare la candidate cambiando parametri dopo aver visto il risultato.",
        },
        "null_inconclusive": {
            "definition": "CI ampia che include ancora sia breakeven sia valori materialmente positivi "
                          "anche a n grande",
            "action": "B_HOLD_NEED_MORE_EVIDENCE",
            "note": "Innesca la logica di stopping (sez.9) - se anche un campione molto piu' grande resta "
                    "inconclusivo, va valutato se continuare a raccogliere evidenza abbia ancora senso.",
        },
        "positive_but_unstable": {
            "definition": "PF>1 complessivo ma asimmetria direzionale persistente a n grande, o varianza "
                          "elevata fra sotto-periodi/anni",
            "action": "B_HOLD_NEED_MORE_EVIDENCE",
            "note": "MAI un'promozione automatica - richiederebbe un follow-up piu' specifico (es. "
                    "direction-specific diagnostic PRE-REGISTRATO) prima di considerare C.",
        },
        "positive_and_robust": {
            "definition": "PF materialmente >1, CI esclude il breakeven, stabile su sotto-periodi, "
                          "direzione consistente o l'asimmetria e' spiegabile in modo non ad-hoc",
            "action": "C_ADVANCE_TO_NEXT_VALIDATION_GATE",
            "note": "Sblocca il passo successivo nella pipeline (demo/paper-trading) - MAI direttamente "
                    "GO_LIVE.",
        },
    }

    # ================= 7. Formal VoI =================
    formal_voi = {
        "verdict": "NUMERIC_VOI_NOT_IDENTIFIED",
        "missing_prerequisites": [
            "Nessuna prior calibrata su P(edge reale | evidenza attuale) esiste per questo o altri "
            "candidati del progetto.",
            "Nessuna funzione di utilita'/costo esplicita (costo di una falsa promozione vs costo di un "
            "falso rigetto, costo-opportunita' del capitale) e' mai stata dichiarata nel progetto.",
        ],
        "no_invented_pass_probability": True,
        "framework_used_instead": "Confronto qualitativo/ordinale trasparente (sez.4-5-8) - LOW/MEDIUM/HIGH "
                                   "con rationale esplicito per ogni cella, mai un punteggio numerico "
                                   "aggregato.",
    }

    # ================= 8. Expected information utility (matrice trasparente) =================
    utility_matrix = {
        "SERIOUS_3Y_FULL_TEST": {"decision_relevance": "HIGH", "uncertainty_reduction": "HIGH",
                                  "independence_of_evidence": "HIGH", "contamination_risk": "LOW",
                                  "cost": "HIGH", "downstream_unlock_value": "HIGH",
                                  "rationale": "Unico test che indirizza SIMULTANEAMENTE 5 dei 7 assi di "
                                               "incertezza aperti (sez.3) con un campione fresco e "
                                               "indipendente, su un design gia' congelato (basso rischio "
                                               "di contaminazione/gradi di liberta')."},
        "LONGER_CHEAPER_BAR_LEVEL_VALIDATION": {"decision_relevance": "MEDIUM", "uncertainty_reduction": "MEDIUM",
                                                 "independence_of_evidence": "LOW", "contamination_risk": "MEDIUM",
                                                 "cost": "LOW", "downstream_unlock_value": "LOW-MEDIUM",
                                                 "rationale": "Economico ma non affronta cost_robustness ne' "
                                                              "regime_concentration a livello di trade "
                                                              "reale - risultati non direttamente comparabili "
                                                              "al motore completo gia' usato."},
        "CROSS_FEED_VALIDATION": {"decision_relevance": "HIGH", "uncertainty_reduction": "MEDIUM",
                                   "independence_of_evidence": "HIGH", "contamination_risk": "LOW",
                                   "cost": "MEDIUM", "downstream_unlock_value": "MEDIUM",
                                   "rationale": "Affronta un asse REALE mai testato (validita' esterna) ma "
                                                "NON il problema piu' acuto oggi (campione piccolo/"
                                                "concentrazione temporale)."},
        "ADDITIONAL_RECENT_HOLDOUT": {"decision_relevance": "MEDIUM", "uncertainty_reduction": "LOW-MEDIUM",
                                       "independence_of_evidence": "MEDIUM", "contamination_risk": "LOW",
                                       "cost": "LOW", "downstream_unlock_value": "LOW",
                                       "rationale": "Il piu' economico ma l'incremento informativo e' "
                                                    "proporzionalmente piccolo rispetto al gap attuale "
                                                    "(n=14 -> pochi mesi in piu' non risolve sample_adequacy "
                                                    "ne' regime_concentration in modo decisivo)."},
        "DIRECTION_SPECIFIC_DIAGNOSTIC": {"decision_relevance": "HIGH", "uncertainty_reduction": "MEDIUM",
                                           "independence_of_evidence": "LOW", "contamination_risk": "HIGH",
                                           "cost": "LOW", "downstream_unlock_value": "MEDIUM",
                                           "rationale": "Alto rischio di essere un rescue post-hoc travestito "
                                                        "se non genuinamente pre-registrato su un campione "
                                                        "fresco - il beneficio informativo e' reale SOLO se "
                                                        "questa condizione e' rispettata rigorosamente."},
        "NO_TEST_WAIT_FOR_MORE_DATA": {"decision_relevance": "LOW", "uncertainty_reduction": "LOW",
                                        "independence_of_evidence": "N/A", "contamination_risk": "LOW",
                                        "cost": "LOW_BUT_INDEFINITE_TIME", "downstream_unlock_value": "LOW",
                                        "rationale": "Nessun impegno di ricerca, ma nessun progresso "
                                                     "decisionale in tempi prevedibili."},
        "no_arbitrary_numeric_score_computed": True,
    }

    # ================= 9. Stopping logic =================
    stopping_logic = {
        "stop_conditions": [
            {
                "condition": "STRONG_WIDE_SAMPLE_REFUTATION",
                "description": "Un futuro test a campione largo mostra CI chiaramente sotto/al breakeven, "
                                "delta_p materialmente negativo.",
            },
            {
                "condition": "COST_ROBUSTNESS_FAILURE",
                "description": "L'edge scompare quando si applicano costi realistici a scala - ESATTAMENTE "
                                "il pattern gia' documentato per WICK_SWEEP_RECLAIM in Failure Memory "
                                "(SHADOW_EXECUTION_ASSUMPTION: PF shadow=5.80 -> PF reale=0.78-0.80). Se "
                                "questo si ripetesse per VOLATILITY_BREAKOUT_CONFIRMED al Serious 3Y, "
                                "sarebbe un segnale di stop forte, non un problema da 'aggiustare'.",
            },
            {
                "condition": "EXECUTION_INCOMPATIBILITY",
                "description": "Il segnale non puo' essere eseguito realisticamente (non ancora osservato "
                                "per questo candidato - la parita' Python/MQL5 e' gia' confermata 927/927, "
                                "un buon segnale preventivo contro questo esito specifico).",
            },
            {
                "condition": "PERSISTENT_INSUFFICIENT_EFFECTIVE_SAMPLE",
                "description": "Anche un test su 3 anni non raggiunge un campione minimo utile (il setup e' "
                                "semplicemente troppo raro) - indicherebbe che il design non e' validabile "
                                "economicamente con questo approccio, non che l'edge sia falso.",
            },
        ],
    }

    # ================= 10. Serious 3Y eligibility verdict =================
    verdict = {
        "value": "SERIOUS_3Y_IS_NEXT_BEST_EXPERIMENT",
        "rationale": "Il Serious 3Y e' l'UNICO fra le alternative concettualmente lecite che indirizza "
                     "simultaneamente la maggioranza degli assi di incertezza oggi HIGH (magnitude, "
                     "temporal_stability, cost_robustness, regime_concentration, sample_adequacy), con "
                     "rischio di contaminazione/gradi di liberta' BASSO (spec gia' congelata, nessun "
                     "parametro da scegliere ora) e costo di ingegneria residuo BASSO (parita' Python/MQL5 "
                     "gia' verificata). Le alternative piu' economiche (holdout aggiuntivo, validazione "
                     "bar-level) affrontano solo UN sottoinsieme piccolo degli assi aperti; le alternative "
                     "che affrontano un asse specifico con buon rapporto costo/beneficio (cross-feed "
                     "validation, direction-specific diagnostic) non sostituiscono la necessita' di un "
                     "campione ampio a esecuzione realistica.",
        "explicit_caveat": "Questo verdetto e' CONDIZIONALE alla disponibilita' di budget di "
                            "compute/dati/tempo sufficiente per il Serious 3Y - un fatto che questo "
                            "contratto NON puo' verificare (nessun budget di ricerca formale e' dichiarato "
                            "nel progetto, vedi sez.11). Se quel budget non fosse disponibile ORA, "
                            "un'alternativa piu' economica (es. ADDITIONAL_RECENT_HOLDOUT) diventerebbe "
                            "il secondo miglior test praticabile, non perche' scientificamente superiore "
                            "ma per vincolo di risorse - una distinzione che questo contratto rende "
                            "esplicita invece di nasconderla in un punteggio unico.",
        "not_based_on_invented_probability": True,
    }

    # ================= 11. Future numeric VoI prerequisites =================
    future_numeric_voi_prerequisites = {
        "prior_edge_distribution": "Una prior calibrata P(edge reale | pattern di evidenza osservato) - "
                                    "non esiste oggi per nessun candidato del progetto.",
        "candidate_base_rate": "Quanto spesso, storicamente, un candidato NEXUS che raggiunge lo stage "
                                "'fast structural borderline' si rivela poi un edge reale e deployabile? "
                                "Richiederebbe un tracking storico sistematico attraverso TUTTI i candidati "
                                "passati (H006, SAR, ADX_RSI, ecc.) - non ancora costruito.",
        "cost_of_false_promotion": "Perdita di capitale/reputazione se una strategia falsa viene portata "
                                    "live - mai quantificata nel progetto.",
        "cost_of_false_rejection": "Costo-opportunita' di abbandonare un edge reale - mai quantificato.",
        "compute_cost": "Costo reale (tempo/risorse) di un Serious 3Y - non tracciato come voce di budget "
                         "formale in nessun artifact visto finora.",
        "capital_opportunity_cost": "Rendimento atteso del capitale se allocato altrove nel frattempo - "
                                     "mai modellato.",
        "note": "Costruire questi 6 elementi trasformerebbe questo framework qualitativo in un vero EVSI/"
                "EVPI/Expected Utility - un passo futuro esplicitamente NON tentato qui (nessun numero "
                "inventato per riempire il vuoto).",
    }

    payload = {
        "phase": "7.8A", "artifact_role": "VALUE_OF_INFORMATION_CONTRACT",
        "candidate_id": CANDIDATE_ID,
        "scope_note": "Contratto decisionale ex-ante: stabilisce se il Serious 3Y e' il prossimo "
                       "esperimento a maggior valore informativo per questo candidato, PRIMA di eseguirlo. "
                       "Nessun backtest, nessun nuovo outcome, nessuna optimization di parametri, nessuna "
                       "applicazione di MECH-23.",
        "baseline_commit": BASELINE_COMMIT,
        "source_artifacts": {
            "lifecycle_registry": {"file": "server/research_scripts/phase7/phase7_7a/"
                                    "strategy_lifecycle_registry_v1.json",
                                    "canonical_sha256": lifecycle_doc["canonical_sha256"]},
            "gate": {"file": "server/research_scripts/phase7/phase7_7b/strategy_meta_filter_gate_v1.json",
                     "canonical_sha256": gate_doc["canonical_sha256"]},
            "refinement": {"file": "server/research_scripts/phase7/phase7_7b/"
                           "missing_field_semantics_refinement_v1.json",
                           "canonical_sha256": refinement_doc["canonical_sha256"]},
            "strategy_foundry_phase3_vault_note_sha256": file_sha256(FOUNDRY3_PATH),
            "failure_memory_vault_note_sha256": file_sha256(FAILURE_MEMORY_PATH),
            "modified_in_this_phase": False,
        },
        "current_evidence_state": current_evidence_state,
        "decision_to_be_informed": decision_to_be_informed,
        "uncertainty_axes_addressed_by_serious_3y": uncertainty_axes,
        "alternative_experiments": alternatives,
        "cost_of_experiment": cost_matrix,
        "decision_tree_frozen_before_test": decision_tree,
        "formal_voi": formal_voi,
        "expected_information_utility_matrix": utility_matrix,
        "stopping_logic": stopping_logic,
        "serious_3y_eligibility_verdict": verdict,
        "future_numeric_voi_prerequisites": future_numeric_voi_prerequisites,
        "no_serious_3y_executed": True,
        "no_new_outcome_data_accessed": True,
        "no_parameter_optimization_performed": True,
        "no_mech23_applied": True,
        "no_edge_discovery_performed": True,
        "no_retroactive_modification_of_frozen_artifacts": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(
        payload, script="server/research_scripts/phase7/phase7_8a/build_volatility_breakout_voi_contract.py",
    )
    out_path = os.path.join(PHASE78A_DIR, "volatility_breakout_voi_contract_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"verdict: {payload['serious_3y_eligibility_verdict']['value']}")


if __name__ == "__main__":
    main()
