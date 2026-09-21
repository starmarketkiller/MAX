#!/usr/bin/env python3
"""Phase 7.8B - VOLATILITY_BREAKOUT_CONFIRMED Serious 3Y Preregistration.

Phase 7.8A ha concluso SERIOUS_3Y_IS_NEXT_BEST_EXPERIMENT. Prima di
autorizzare il run, questo modulo pre-registra il protocollo ESATTO:
identita' della strategia, dataset/periodo, execution contract, scenari
di costo, endpoint primario, soglie PASS/BORDERLINE/FAIL, regola di
campione effettivo, diagnostica di direzione/stabilita' temporale,
no-rescue clause, e i result branch (mai GO_LIVE diretto).

Principio guida: OGNI soglia numerica deve dichiarare la propria
provenienza (vedi threshold_policy.json). Dove un valore canonico GIA'
esistente nel progetto si applica (minimum_evidence_gates.json,
cost_model_integration.json, stability_matrix_policy.json,
statistical_methods_policy.json), viene RIUSATO identico - MAI
ri-derivato o approssimato. Dove nessun valore canonico esiste e
inventarne uno costituirebbe un grado di liberta' post-hoc mascherato
da rigore, il campo e' dichiarato ESPLICITAMENTE NOT_YET_JUSTIFIED e
blocca l'autorizzazione del run per quella parte del protocollo - mai
un numero indovinato per compiacenza.

NESSUN backtest eseguito qui. NESSUN nuovo outcome letto. NESSUNA
modifica ai parametri della strategia (frozen dal commit f035d30).
NESSUNA optimization. NESSUNA applicazione di MECH-23."""
import os
import sys

PHASE78B_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78B_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "b8c598f0bbf7693d7f9c9641853e8d7d339bb67f"
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"
STRATEGY_FROZEN_COMMIT = "f035d30"

VOI_CONTRACT_PATH = os.path.join(PHASE7_DIR, "phase7_8a", "volatility_breakout_voi_contract_v1.json")
STRATEGY_REGISTRY_PATH = os.path.join(ROOT, "contracts", "strategy-registry.json")
MIN_EV_GATES_PATH = os.path.join(PHASE7_DIR, "policies", "minimum_evidence_gates.json")
COST_MODEL_PATH = os.path.join(PHASE7_DIR, "policies", "cost_model_integration.json")
STABILITY_MATRIX_PATH = os.path.join(PHASE7_DIR, "policies", "stability_matrix_policy.json")
STATISTICAL_METHODS_PATH = os.path.join(PHASE7_DIR, "policies", "statistical_methods_policy.json")
THRESHOLD_POLICY_PATH = os.path.join(PHASE7_DIR, "policies", "threshold_policy.json")
FOUNDRY3_PATH = os.path.join(ROOT, "vault", "01-Trading",
                              "NEXUS - Strategy Foundry Phase 3 Volatility Breakout Implementation.md")
SAR_MACD_3Y_PATH = os.path.join(ROOT, "vault", "01-Trading",
                                  "NEXUS - First Serious 3Y Validation SAR MACD.md")

NOT_YET_JUSTIFIED = "NOT_YET_JUSTIFIED"


def build():
    voi_doc = load_json(VOI_CONTRACT_PATH)
    voi = voi_doc["payload"]
    strategy_registry = load_json(STRATEGY_REGISTRY_PATH)
    reg_entry = next(s for s in strategy_registry["strategies"] if s["strategy_id"] == CANDIDATE_ID)
    min_ev_gates = load_json(MIN_EV_GATES_PATH)
    cost_model = load_json(COST_MODEL_PATH)
    stability_matrix = load_json(STABILITY_MATRIX_PATH)

    # ================= 1. Evidence-dependence correction (annota 7.8A, non lo modifica) =================
    evidence_dependence_correction = {
        "target_artifact": "server/research_scripts/phase7/phase7_8a/volatility_breakout_voi_contract_v1.json",
        "target_artifact_canonical_sha256_unchanged": voi_doc["canonical_sha256"],
        "modified_in_this_phase": False,
        "correction": {
            "original_framing": "sign_uncertainty = MEDIUM-LOW, motivato da '4 letture concordi e "
                                 "indipendenti' (discovery/validation/full-backtest/fast-structural).",
            "issue": "Le 4 letture NON sono prove statisticamente indipendenti nel senso tecnico - "
                     "condividono la stessa strategia, lo stesso lineage (Phase 2 screening -> Phase 3 "
                     "implementazione) e, in parte, dati/metodologia sovrapposti (il full-backtest e il "
                     "fast-structural condividono porzioni dello stesso storico di mercato).",
            "corrected_framing": {
                "evidence_concordance": "POSITIVE",
                "evidence_independence": "NOT_ESTABLISHED",
            },
            "does_this_change_the_voi_verdict": False,
            "rationale_for_no_change": "La correzione non ribalta SERIOUS_3Y_IS_NEXT_BEST_EXPERIMENT - anzi "
                                        "rafforza la necessita' di un test genuinamente indipendente (il "
                                        "Serious 3Y su un campione fresco, non un'ulteriore rilettura degli "
                                        "stessi dati) esattamente perche' le 4 letture concordi non possono "
                                        "essere sommate come se fossero prove indipendenti nel calcolo "
                                        "informale di confidenza.",
        },
    }

    # ================= 2. Freeze exact strategy identity =================
    strategy_identity = {
        "frozen_commit": STRATEGY_FROZEN_COMMIT,
        "frozen_commit_source": "vault/01-Trading/NEXUS - Strategy Foundry Phase 3 Volatility Breakout "
                                 "Implementation.md, sez. Commit",
        "registry_entry_verified": {
            "strategy_id": reg_entry["strategy_id"], "family": reg_entry["family"],
            "status": reg_entry["status"], "selector_index": reg_entry["selector_index"],
            "live_implementation": reg_entry["live_implementation"],
            "research_implementation": reg_entry["research_implementation"],
            "research_parity": reg_entry["research_parity"],
            "supported_timeframes": reg_entry["supported_timeframes"],
        },
        "detector": "Chiusura barra segnale oltre massimo/minimo di un range di 20 barre [i-21,i-2] "
                    "(offset 2), CONFERMATA da true_range[i] > 1.0 x ATR(14)[i] sulla stessa barra.",
        "entry": "Al prezzo di chiusura della barra segnale (mercato, close[i])",
        "direction": "BUY se rottura sopra il range, SELL se sotto",
        "range_lookback": "N=20 barre, offset [i-21, i-2] (esclude la barra segnale e quella immediatamente "
                            "precedente)",
        "volatility_confirmation": "true_range[i] > 1.0 x ATR(14)[i] - soglia DOMAIN_DEFINED, gia' citata "
                                    "esplicitamente come esempio in threshold_policy.json "
                                    "(allowed_threshold_sources.DOMAIN_DEFINED)",
        "invalidation_stop": "Lato opposto dello stesso range N=20 (minimo per BUY, massimo per SELL)",
        "r_definition": "R = |entry - invalidation| (ampiezza del range al momento dell'entry)",
        "target": "entry ± 1xR (TP=1R, l'unica scelta fedele alla specifica testata in Phase 2 - MAI un "
                  "multiplo diverso)",
        "timeout": "40 barre H4 (~6.7 giorni), uscita a tempo (TIME) al prezzo di chiusura di quella barra "
                   "oltre questo limite - MAI un valore R fisso, il P&L realizzato al timeout dipende dal "
                   "prezzo effettivo in quel momento",
        "management": "Nessun trailing/BE/filtro di sessione o regime - dichiarato esplicitamente fuori "
                       "scope in Fase 3, MAI aggiunto qui",
        "fade_arm": "NON implementato (era NO_EDGE in Phase 2, fuori scope)",
        "no_parameter_may_change_after_this_commit": True,
        "censoring_note": "A differenza dei design MECH-23/SEQ-0014B (Phase 7.6D/7.6E), questa strategia NON "
                           "ha uno stato 'non risolto/censored': ogni trade si chiude o per TP, o per SL, o "
                           "per TIME al prezzo reale di quella barra - il P&L e' SEMPRE definito, nessuna "
                           "ambiguita' di censoring da risolvere qui.",
    }

    # ================= 3. Freeze dataset and period =================
    dataset_and_period = {
        "symbol": "XAUUSD (GOLD)",
        "timeframe": "H4 nativo",
        "data_source": "MT5 Strategy Tester, Model=1 (real ticks quando disponibili) - stesso feed gia' "
                        "usato per il signal-parity audit e il fast-structural test (Strategy Foundry "
                        "Phase 3, sez.4-5). NON il dataset Dukascopy p71 usato per le sequence SEQ-000x "
                        "(popolazione/periodo diversi, mai mescolati).",
        "window_selection_rule": "Ultimo intervallo continuo di 3 anni disponibile che termina alla data "
                                  "corrente di sincronizzazione dello storico MT5 al momento del run - "
                                  "STESSA convenzione gia' usata per SAR/MACD Serious 3Y (vault: 'NEXUS - "
                                  "First Serious 3Y Validation SAR MACD.md', commit e557b22) - non scelta "
                                  "guardando i risultati.",
        "window_selection_rule_exact_dates": "NON dichiarate qui con date assolute - la data di "
                                              "sincronizzazione MT5 corrente non e' verificabile da questa "
                                              "sessione di ricerca (nessun accesso live al terminale MT5). "
                                              "Il RUN deve dichiarare le date esatte (start/end) al momento "
                                              "dell'esecuzione, PRIMA di vedere risultati, seguendo "
                                              "esclusivamente la regola sopra - mai scelte per includere o "
                                              "escludere un sottoperiodo specifico.",
        "timezone": "Broker time (offset da dichiarare al momento del run, stesso principio gia' "
                     "richiesto per WICK_SWEEP_RECLAIM - vedi Failure Memory, pattern TIMEZONE_MISMATCH: "
                     "l'offset va sempre dichiarato e validato su un esempio concreto).",
        "tick_model": "Model=1 (o il piu' alto disponibile per il periodo - dichiarare esplicitamente quale "
                       "modello e' stato usato per OGNI sotto-periodo se cambia nel tempo, mai un default "
                       "silenzioso)",
        "dataset_hash_version": "Da assegnare al momento del fetch/estrazione dati (prima di calcolare "
                                  "qualunque statistica) - non assegnabile ora senza i dati stessi.",
        "previously_observed_vs_fresh": {
            "trailing_6_months_2026_03_2026_09": {
                "status": "PREVIOUSLY_OBSERVED",
                "reason": "Identico alla finestra gia' usata per il signal-parity audit e il fast-"
                          "structural test (Strategy Foundry Phase 3, sez.4-5) - NON puo' essere trattato "
                          "come out-of-sample per questa strategia.",
            },
            "remaining_approx_2_5_years_preceding_the_trailing_segment": {
                "status": "FRESH_FOR_THIS_EXACT_COMBINED_STRATEGY",
                "caveat": "MAI visto con QUESTA esatta combinazione di segnale (breakout 20-barre + "
                          "conferma volatilita' + bracket 1R/1R/40-barre) - MA il mercato sottostante in "
                          "questa finestra e' STATO gia' usato per testare i componenti RAW separati "
                          "(BREAKOUT=H001, VOLATILITY_EXPANSION=H008, entrambi REFUTED in Phase 5.5 su "
                          "dataset 2019-2022 - periodo diverso, non necessariamente sovrapposto a questo, "
                          "da verificare esplicitamente al momento del run). Dichiarato qui come "
                          "FRESH_FOR_THIS_EXACT_COMBINED_STRATEGY, MAI etichettato 'OOS puro' senza questo "
                          "caveat.",
            },
        },
        "primary_verdict_window_rule": "Il verdetto PASS/BORDERLINE/FAIL primario (sez.7) e' calcolato "
                                        "SOLO sulla porzione FRESH (i ~2.5 anni precedenti la finestra gia' "
                                        "osservata) - la porzione PREVIOUSLY_OBSERVED (ultimi 6 mesi) e' "
                                        "riportata SEPARATAMENTE come replica diagnostica di un segmento "
                                        "gia' visto, MAI fusa nel campione del verdetto primario per non "
                                        "gonfiare n con dati non freschi.",
        "no_cherry_picking_of_subperiod": True,
    }

    # ================= 4. Execution contract =================
    execution_contract = {
        "fill_model": "Prezzo di chiusura della barra segnale per l'entry (come da detector) - esecuzione "
                       "reale MT5 tick-driven per SL/TP/TIME (stesso motore gia' usato per il "
                       "signal-parity audit).",
        "spread_commission_slippage": "Nativi del Tester per lo scenario BROKER_BASELINE (sez.5) - nessuna "
                                        "idealizzazione shadow (vedi Failure Memory, pattern "
                                        "SHADOW_EXECUTION_ASSUMPTION - MAI un fill idealizzato al prezzo "
                                        "esatto di trigger).",
        "stop_execution": "SL eseguito al primo tocco del livello di invalidazione (lato opposto del range "
                           "N=20) - stessa regola gia' frozen, nessuna modifica.",
        "target_execution": "TP eseguito al primo tocco di entry±1R.",
        "gap_handling": "Dichiarare al momento del run come il Tester gestisce i gap oltre SL/TP (fill al "
                         "prezzo di apertura post-gap, non al livello nominale) - comportamento nativo del "
                         "motore, non un parametro della strategia.",
        "same_bar_sl_tp_ambiguity_rule": NOT_YET_JUSTIFIED,
        "same_bar_sl_tp_ambiguity_rule_note": "Se SL e TP sono ENTRAMBI teoricamente raggiungibili "
                                               "nell'high-low della stessa barra H4 (possibile dato "
                                               "R=|entry-invalidation| puo' essere piccolo relativo alla "
                                               "volatilita' intrabarra), quale viene eseguito per primo? "
                                               "Il motore MT5 real-tick (Model=1) risolve questo "
                                               "MECCANICAMENTE seguendo l'ordine reale dei tick - nessuna "
                                               "assunzione a livello di barra e' necessaria SE il tick model "
                                               "e' reale. Dichiarato NOT_YET_JUSTIFIED solo per il caso in "
                                               "cui il tick model reale non fosse disponibile per l'intero "
                                               "periodo (vedi tick_model sopra) - in quel caso servirebbe "
                                               "una regola esplicita (es. 'assume SL first', conservativa) "
                                               "MAI scelta dopo aver visto quanti trade sono ambigui.",
        "timeout_execution": "Chiusura a mercato alla barra i+40 (chiusura di quella barra), realizzando "
                              "il P&L effettivo in quel momento - MAI un valore R fisso.",
        "one_position_at_a_time_rule": "Stessa gestione one-at-a-time gia' usata da run_backtest() "
                                        "(Strategy Foundry Phase 3, sez.2) - nessun position stacking, "
                                        "coerente con la definizione originale del segnale.",
        "no_shadow_or_idealized_assumption": True,
    }

    # ================= 5. Cost scenarios (riusati identici da cost_model_integration.json) =================
    cost_scenarios = {
        "source": "server/research_scripts/phase7/policies/cost_model_integration.json (riusato identico, "
                  "non ri-derivato)",
        "source_sha256": file_sha256(COST_MODEL_PATH),
        "scenarios": {
            "ZERO_COST": {"role": "DIAGNOSTIC_ONLY", "note": "Misura l'effetto puro - MAI usato per il "
                          "verdetto PASS/BORDERLINE/FAIL."},
            "BROKER_BASELINE": {"role": "PRIMARY_FOR_VERDICT",
                                  "note": "Scenario di riferimento primario per il verdetto EXECUTABLE, "
                                          "esattamente come dichiarato in cost_model_integration.json - "
                                          "spread_price=0.54 (5.4 pip mediana, 900 campioni live GOLD), "
                                          "commission_r=0.0 (79 deal reali), slippage_price=0.10 pip."},
            "CONSERVATIVE": {"role": "STRESS_DIAGNOSTIC", "multiplier": "x1.5"},
            "STRESS": {"role": "STRESS_DIAGNOSTIC", "multiplier": "x2.0 (esclusa commission, che resta 0.0 "
                       "come misurato)"},
        },
        "primary_scenario_for_verdict": "BROKER_BASELINE",
        "no_new_scenario_created_after_seeing_result": True,
        "reporting_rule_reused": cost_model["reporting_rule"],
    }

    # ================= 6. Primary endpoint =================
    primary_endpoint = {
        "primary_metric": "expectancy_R (media del multiplo-R realizzato per trade, sullo scenario "
                           "BROKER_BASELINE, sulla porzione FRESH del campione)",
        "primary_metric_rationale": "Stessa metrica GIA' usata per costruire l'intera evidenza precedente "
                                      "di questo candidato (Phase 2 screening, full-backtest engine, "
                                      "fast-structural - tutti riportano PF/expectancy_R su trade grezzi, "
                                      "MAI un confronto evento-vs-baseline) e per il precedente SAR/MACD "
                                      "Serious 3Y (stesso set di metriche) - riusata per continuita' "
                                      "metodologica, non scelta ad-hoc per questa fase.",
        "statistical_method": "moving_block_bootstrap (gia' ammesso in statistical_methods_policy.json per "
                               "outcome continui sotto dipendenza seriale - blocco L=ceil(n^(1/3))) "
                               "applicato alla serie ORDINATA TEMPORALMENTE dei multipli-R per trade, per "
                               "ottenere un CI95 sulla media (expectancy_R) - un test one-sample, NON un "
                               "confronto matched event-vs-baseline (questa strategia non ha mai usato "
                               "quel framework nella sua evidenza pregressa).",
        "secondary_diagnostics": ["win_rate (Wilson CI95, gia' ammesso)", "profit_factor",
                                   "payoff_ratio", "max_drawdown_pct", "max_consecutive_losses"],
        "secondary_never_replaces_primary": True,
        "secondary_diagnostics_cannot_override_primary_fail": True,
    }

    # ================= 7. Exact decision thresholds =================
    n_nominal_minimum = min_ev_gates["gates"]["n_nominal_minimum"]["value"]
    effective_n_minimum = min_ev_gates["gates"]["effective_n_minimum"]["value"]
    decision_thresholds = {
        "minimum_nominal_sample": {
            "value": n_nominal_minimum,
            "source": "minimum_evidence_gates.json.n_nominal_minimum (riusato identico)",
            "rule": f"n(trade FRESH, scenario BROKER_BASELINE) < {n_nominal_minimum} => "
                    f"INSUFFICIENT_SAMPLE (stato distinto, non FAIL - stesso principio di H004/H006)",
        },
        "minimum_effective_sample": {
            "value": effective_n_minimum,
            "source": "minimum_evidence_gates.json.effective_n_minimum (riusato identico)",
            "rule": f"Se un ESS e' stimabile (sez.8) e scende sotto {effective_n_minimum} => "
                    f"INSUFFICIENT_SAMPLE indipendentemente da n nominale.",
        },
        "sign_criterion": {
            "rule": "PF > 1.0 AND expectancy_R > 0 (scenario BROKER_BASELINE, porzione FRESH)",
            "source": "DOMAIN_DEFINED - punto di breakeven matematico della metrica stessa (PF=1.0), non "
                      "una soglia di policy inventata.",
        },
        "materiality_threshold_beyond_breakeven": {
            "value": NOT_YET_JUSTIFIED,
            "note": "minimum_material_delta_p_default=0.10 (minimum_evidence_gates.json) e' definito su "
                    "scala PROBABILITA' (delta_p fra evento e baseline) - NON direttamente applicabile a "
                    "expectancy_R (scala R-multiple, nessun confronto a baseline in questo design). "
                    "Nessun valore canonico equivalente per 'quanto sopra 1.0 deve essere il PF perche' sia "
                    "materiale' esiste nel progetto. Dichiarato esplicitamente NOT_YET_JUSTIFIED - "
                    "BLOCCA l'autorizzazione a un verdetto PASS pulito finche' un umano non fissa questo "
                    "valore (o una motivazione di dominio equivalente) PRIMA del run.",
        },
        "uncertainty_requirement": {
            "rule": "Il CI95 (moving_block_bootstrap) di expectancy_R deve escludere 0 interamente.",
            "source": "Adattato da minimum_evidence_gates.json.uncertainty_requirement (struttura "
                      "identica: 'il CI esclude il valore nullo/di breakeven' - qui applicato alla scala "
                      "corretta del primary_endpoint, non ri-derivato da zero).",
        },
        "temporal_stability_criterion": {
            "value": NOT_YET_JUSTIFIED,
            "note": "Nessuna soglia numerica canonica esiste per 'un anno/sotto-periodo materialmente "
                    "negativo' (il precedente SAR/MACD Serious 3Y ha usato un giudizio qualitativo - "
                    "'non materiale rispetto alla scala tipica del trade' - non un numero pre-registrato). "
                    "Dichiarato NOT_YET_JUSTIFIED.",
        },
        "cost_robustness_criterion": {
            "rule": "expectancy_R > 0 anche sotto lo scenario STRESS (x2.0).",
            "source": "DOMAIN_DEFINED - stesso principio gia' applicato a SAR/MACD ('l'edge non collassa in "
                      "nessuno scenario di costo') - qui reso un criterio ESPLICITO invece che una "
                      "descrizione qualitativa post-hoc.",
        },
        "pass_borderline_fail_composite_rule": {
            "PASS": "sign_criterion soddisfatto AND uncertainty_requirement soddisfatto AND "
                    "cost_robustness_criterion soddisfatto AND minimum_nominal/effective_sample "
                    "soddisfatti AND materiality_threshold soddisfatto (BLOCCATO finche' NOT_YET_JUSTIFIED "
                    "non e' risolto) AND direction/temporal stability non mostrano un collasso strutturale "
                    "(sez.9-10).",
            "BORDERLINE": "sign_criterion soddisfatto ma uncertainty_requirement o cost_robustness_"
                          "criterion falliscono di poco, OPPURE asimmetria direzionale/instabilita' "
                          "temporale presente ma non estrema (soglia esatta NOT_YET_JUSTIFIED - vedi sez.9-"
                          "10) - stesso stato usato per SAR nel precedente Serious 3Y.",
            "FAIL": "sign_criterion non soddisfatto, OPPURE almeno 2 criteri falliscono in modo netto "
                    "(stesso principio gia' applicato a MACD: 'due criteri falliscono in modo netto, non "
                    "borderline').",
            "INSUFFICIENT_SAMPLE": "minimum_nominal_sample o minimum_effective_sample non soddisfatti - "
                                     "stato distinto, MAI forzato in FAIL o BORDERLINE.",
        },
        "run_authorization_status": "PARTIALLY_BLOCKED",
        "run_authorization_blockers": ["materiality_threshold_beyond_breakeven (NOT_YET_JUSTIFIED)",
                                        "temporal_stability_criterion (NOT_YET_JUSTIFIED)",
                                        "same_bar_sl_tp_ambiguity_rule (NOT_YET_JUSTIFIED, condizionale al "
                                        "tick model disponibile)"],
        "run_authorization_note": "Il protocollo e' congelabile e il run potrebbe procedere sulla parte gia' "
                                   "giustificata (sample/sign/uncertainty/cost) - MA un verdetto PASS pulito "
                                   "non e' ancora possibile senza risolvere i blocker sopra PRIMA di vedere "
                                   "risultati. Risolverli DOPO aver visto un risultato borderline "
                                   "costituirebbe esattamente il grado di liberta' post-hoc che questa fase "
                                   "esiste per prevenire.",
    }

    # ================= 8. Effective sample =================
    effective_sample = {
        "dependence_sources_to_check": [
            "Trade dependence per gestione one-at-a-time (un trade non puo' aprirsi finche' il precedente "
            "non e' chiuso - possibile serial dependence indotta dalla struttura stessa dell'esecuzione)",
            "Temporal clustering (piu' segnali ravvicinati nello stesso regime di breakout)",
            "Overlap fra la finestra di holding di un trade (fino a 40 barre) e l'innesco del successivo",
        ],
        "method_if_estimable": "Stessa famiglia di metodi gia' ammessa (dependence_diagnostics_v2.py, "
                                "gia' riusata per H006 - n_effective stimato con piu' metodi, riportato "
                                "come range, non un singolo numero falsamente preciso).",
        "fallback_if_not_estimable": "Se un ESS valido non e' stimabile con i metodi gia' ammessi, il "
                                      "fallback e' usare ESCLUSIVAMENTE n nominale con "
                                      "minimum_nominal_sample come gate (nessun ESS inventato) - il "
                                      "verdetto in quel caso porta un flag esplicito "
                                      "'DEPENDENCE_ADJUSTMENT_NOT_APPLIED', mai un ESS presentato come se "
                                      "fosse stato calcolato.",
        "no_invented_ess": True,
    }

    # ================= 9. Direction asymmetry =================
    stability_axes = stability_matrix["axes"]
    direction_asymmetry = {
        "reused_axis_definition": stability_axes["direction"],
        "role": "DIAGNOSTICO PRE-REGISTRATO (stability_matrix_policy.json: 'la stability matrix e' "
                "DIAGNOSTICA - non genera mai automaticamente una promozione di lifecycle')",
        "when_diagnostic_only": "Se il segno di expectancy_R e' concorde su BUY e SELL (entrambi >0 o "
                                 "entrambi <0 in modo coerente col risultato aggregato) - riportato ma non "
                                 "blocca nulla.",
        "when_prevents_pass": "Se un lato (BUY o SELL) e' materialmente negativo mentre l'aggregato e' "
                               "positivo SOLO grazie all'altro lato - precedente diretto: SAR Serious 3Y "
                               "('SELL PF=0.84 su 92 trade, 38% del campione, non pochi trade' -> "
                               "BORDERLINE, non PASS pulito) e MACD ('SELL PF=0.13 nell'IS' -> FAIL). Soglia "
                               "esatta di 'materialmente negativo' per-lato: NOT_YET_JUSTIFIED (stesso gap "
                               "gia' notato in sez.7) - il PRINCIPIO e' pre-registrato, il NUMERO esatto no.",
        "forbidden_action": "overall FAILS -> keep only SELL (o solo BUY) come 'fix' - ESPLICITAMENTE "
                             "VIETATO. Una direzione non puo' essere eliminata post-hoc per salvare il "
                             "verdetto - richiederebbe una NUOVA hypothesis identity in un esperimento "
                             "futuro (stesso principio gia' applicato a H004->H006), mai un rescue "
                             "silenzioso nello stesso test.",
        "direction_is_not_a_declared_part_of_setup_identity": True,
        "note": "VOLATILITY_BREAKOUT_CONFIRMED spara sia BUY sia SELL per costruzione (direzione = lato "
                "della rottura) - non e' una strategia 'BUY-only' dichiarata, quindi il "
                "stability_requirement di minimum_evidence_gates.json ('segno coerente per BUY e SELL, "
                "salvo che la direzione sia parte esplicita del setup') si applica QUI in pieno, non e' "
                "esentabile.",
    }

    # ================= 10. Temporal stability =================
    temporal_stability = {
        "reused_axis_definition": stability_axes["year_or_broad_time_regime"],
        "segmentation_frozen_before_run": "Anno solare (Year 1/2/3 della finestra FRESH) + prima/seconda "
                                            "meta' della finestra FRESH - STESSA segmentazione gia' usata "
                                            "per SAR/MACD Serious 3Y, riusata per continuita', non scelta "
                                            "ad-hoc ora.",
        "stability_criterion": "Almeno 2 dei 3 segmenti annuali non materialmente negativi (soglia esatta "
                                 "di 'materialmente negativo': NOT_YET_JUSTIFIED, stesso gap di sez.7/9).",
        "concentration_criterion": "Il profitto/expectancy netto non deve dipendere ESCLUSIVAMENTE da un "
                                     "singolo segmento (es. 'un solo trimestre spiega piu' del 100% del "
                                     "risultato netto, il resto e' in perdita') - precedente diretto: il "
                                     "fast-structural gia' osservato mostra ESATTAMENTE questo pattern "
                                     "(2 mesi su 5 spiegano quasi tutto il profitto) - un segnale di rischio "
                                     "gia' noto PRIMA del Serious 3Y, non una sorpresa da scoprire.",
        "no_window_change_after_seeing_results": True,
        "oos_check_within_fresh_window": "Split dell'ultimo ~22.5% della finestra FRESH (stessa convenzione "
                                          "gia' usata per SAR/MACD) - riportato come diagnostica aggiuntiva, "
                                          "MAI come sostituto del verdetto sull'intera finestra FRESH.",
    }

    # ================= 11. No-rescue clause =================
    no_rescue_clause = {
        "forbidden_after_seeing_results": [
            "parameter tuning (range_n, ATR multiplier, R multiplier, timeout)",
            "session filter (aggiunta di un filtro orario/sessione mai dichiarato ex-ante)",
            "regime filter (aggiunta di un filtro di volatilita'/trend mai dichiarato ex-ante)",
            "direction deletion (eliminare BUY o SELL per salvare il verdetto aggregato)",
            "stop/target adjustment (cambiare R o il multiplo TP dopo aver visto il risultato)",
            "threshold adjustment (cambiare una qualunque soglia di sez.7/9/10 dopo aver visto il "
            "risultato, incluse quelle NOT_YET_JUSTIFIED - vanno fissate PRIMA, non aggiustate dopo)",
            "post_hoc_subgroup_rescue (isolare un sotto-periodo/sotto-gruppo favorevole non pre-registrato)",
        ],
        "rule": "Un FAIL del design congelato resta FAIL. Un nuovo design (anche minimamente diverso) "
                "richiede una NUOVA identita' di esperimento (nuovo commit, nuovo hypothesis/strategy_id) - "
                "mai una modifica silenziosa del design gia' testato.",
        "precedent": "Stesso principio gia' applicato esplicitamente a MACD nel precedente Serious 3Y "
                     "('Nessuna azione di rescue applicata... Il fallimento e' documentato, non corretto').",
    }

    # ================= 12. Result branches =================
    result_branches = {
        "PASS": {"action": "ADVANCE_TO_NEXT_VALIDATION_GATE"},
        "BORDERLINE": {"action": "HOLD_NEEDS_MORE_EVIDENCE"},
        "FAIL": {"action": "ARCHIVE_CURRENT_DESIGN"},
        "INSUFFICIENT_SAMPLE": {"action": "HOLD_NEEDS_MORE_EVIDENCE",
                                  "note": "Stato distinto da BORDERLINE - il problema e' il campione, non "
                                          "il segnale."},
        "no_branch_leads_directly_to_live": True,
    }

    # ================= 13. Next gate after PASS =================
    next_gate_after_pass = {
        "chosen_next_stage": "EXECUTION_VALIDATION",
        "rationale": "Seguendo la pipeline canonica gia' formalizzata (Phase 7.6E/7.7A: EVENT_RESEARCH -> "
                     "STRATEGY_FORMALIZATION -> STRATEGY_VALIDATION -> META_FILTER_RESEARCH -> "
                     "EXECUTION_VALIDATION -> PORTFOLIO_RISK), un PASS al Serious 3Y completerebbe "
                     "STRATEGY_VALIDATION - lo stage immediatamente successivo e' EXECUTION_VALIDATION "
                     "(verificare che l'edge sopravviva a un'esecuzione reale live/demo, ESATTAMENTE il "
                     "controllo che ha refutato WICK_SWEEP_RECLAIM nonostante un'ipotesi statisticamente "
                     "'STRONGLY SUPPORTED' - vedi Failure Memory) - NON demo/paper diretto (che e' parte di "
                     "EXECUTION_VALIDATION, non uno stage separato scelto ad-hoc) e NON independent "
                     "cross-feed validation (quello indirizzerebbe un asse diverso, la validita' esterna, "
                     "gia' discusso come alternativa in Phase 7.8A ma non scelto come next-best li').",
        "decided_before_seeing_result": True,
        "not_cross_feed_validation_here": "Cross-feed validation resta un'alternativa VALIDA in generale "
                                            "(Phase 7.8A la classificava HIGH su independence_of_evidence) "
                                            "ma non e' 'il prossimo gate' per una strategia gia' "
                                            "PASS-STRUCTURE_VALIDATED - servirebbe come ulteriore evidenza "
                                            "di robustezza, non come gate obbligatorio successivo.",
    }

    payload = {
        "phase": "7.8B", "artifact_role": "SERIOUS_3Y_PREREGISTRATION",
        "candidate_id": CANDIDATE_ID,
        "scope_note": "Pre-registra il protocollo ESATTO del Serious 3Y per VOLATILITY_BREAKOUT_CONFIRMED "
                       "- nessun backtest eseguito, nessun nuovo outcome letto, nessuna modifica ai "
                       "parametri della strategia, nessuna optimization, nessuna applicazione di MECH-23.",
        "baseline_commit": BASELINE_COMMIT,
        "voi_contract_verdict_referenced": voi["serious_3y_eligibility_verdict"]["value"],
        "evidence_dependence_correction": evidence_dependence_correction,
        "strategy_identity_frozen": strategy_identity,
        "dataset_and_period": dataset_and_period,
        "execution_contract": execution_contract,
        "cost_scenarios": cost_scenarios,
        "primary_endpoint": primary_endpoint,
        "decision_thresholds": decision_thresholds,
        "effective_sample": effective_sample,
        "direction_asymmetry_diagnostic": direction_asymmetry,
        "temporal_stability_diagnostic": temporal_stability,
        "no_rescue_clause": no_rescue_clause,
        "result_branches": result_branches,
        "next_gate_after_pass": next_gate_after_pass,
        "serious_3y_not_executed": True,
        "no_new_outcome_data_accessed": True,
        "no_parameter_optimization_performed": True,
        "no_strategy_parameter_modified": True,
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
        payload, script="server/research_scripts/phase7/phase7_8b/build_volatility_breakout_serious_3y_prereg.py",
    )
    out_path = os.path.join(PHASE78B_DIR, "volatility_breakout_serious_3y_prereg_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"run_authorization_status={payload['decision_thresholds']['run_authorization_status']}")
    print(f"blockers={payload['decision_thresholds']['run_authorization_blockers']}")


if __name__ == "__main__":
    main()
