#!/usr/bin/env python3
"""Phase 7.7A - Strategy Lifecycle Registry & Candidate Inventory.

Segue da Phase 7.6E (`082a456`): quell'audit ha dimostrato che le 6
famiglie SEQ-0014B sono detector/eventi direzionali RAW, non strategie
complete - RAW EVENT != STRATEGY. Questo modulo costruisce il primo
inventario CANONICO delle strategie REALMENTE formalizzate nel progetto,
separandole nettamente dai raw event, usando ESCLUSIVAMENTE artifact
gia' esistenti:

- `contracts/strategy-registry.json` (83 strategie, machine-generated da
  contracts/generate_registry.py, fonti: knowledge/strategy_database.json
  + NXS_StrategyProfiles.mqh + server/backtest.py STRAT_MAP) - il
  registro canonico di infrastruttura (implementazione live/research,
  parita').
- `vault/01-Trading/Strategie/MOC - Strategie.md` (37 strategie live EA,
  raggruppate per evidenza empirica: R-multiple/PF su backtest 6 anni
  2019-2024) - trascritto qui manualmente con citazione (contenuto
  Markdown, non parsificabile in modo affidabile).
- Phase 5/5.5/6/6.5/6.6 (H001-H015, H006 decision card v2) - l'unico
  hypothesis testato con il framework statistico rigoroso completo
  (Wilson CI, dependence audit, true holdout).
- `NEXUS - Strategy Foundry Phase 3 Volatility Breakout Implementation.md`
  - VOLATILITY_BREAKOUT_CONFIRMED, l'unica strategia con parita'
  Python/MQL5 verificata bit-per-bit E un lifecycle contract completo
  esplicito.
- `NEXUS - Failure Memory (Registro Pattern di Fallimento Metodologico)`
  - pattern di fallimento a livello di ESECUZIONE (non di statistica),
  scoperti su WICK_SWEEP_RECLAIM.

NESSUNA strategia nuova inventata. NESSUNA modifica a MECH-23. NESSUN
nuovo outcome letto. NESSUN backtest rieseguito. NESSUNA promozione
decisa sulla base di ricordi narrativi - solo su artifact verificati
(hash citati dove applicabile)."""
import os
import sys

PHASE77A_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE77A_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE77A_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "082a456360b9206bceb32b182dcf175e7e84fc63"

STRATEGY_REGISTRY_PATH = os.path.join(ROOT, "contracts", "strategy-registry.json")
STRATEGY_DB_PATH = os.path.join(ROOT, "knowledge", "strategy_database.json")
MOC_PATH = os.path.join(ROOT, "vault", "01-Trading", "Strategie", "MOC - Strategie.md")
FOUNDRY3_PATH = os.path.join(ROOT, "vault", "01-Trading",
                              "NEXUS - Strategy Foundry Phase 3 Volatility Breakout Implementation.md")
FAILURE_MEMORY_PATH = os.path.join(
    ROOT, "vault", "01-Trading",
    "NEXUS - Failure Memory (Registro Pattern di Fallimento Metodologico) (12-09).md",
)
H006_FROZEN_SPEC_PATH = os.path.join(PHASE7_DIR.replace("phase7", "phase6"), "H006_frozen_spec.json")
H006_PRIMARY_RESULT_PATH = os.path.join(PHASE7_DIR.replace("phase7", "phase6"), "h006_primary_result.json")
H006_DECISION_CARD_PATH = os.path.join(PHASE7_DIR.replace("phase7", "phase6_6"), "h006_decision_card_v2.json")
HYPOTHESIS_REGISTRY_PATH = os.path.join(PHASE7_DIR.replace("phase7", "phase5_5"), "hypothesis_registry_v1.json")
PHASE76E_AUDIT_PATH = os.path.join(PHASE7_DIR, "phase7_6e", "seq0014b_native_setup_failure_audit_v1.json")

# ---- Lifecycle classification vocabulary (sec.2 della richiesta) ----
RAW_EVENT = "RAW_EVENT"
PARTIAL_STRATEGY = "PARTIAL_STRATEGY"
FULL_STRATEGY_SPEC = "FULL_STRATEGY_SPEC"
VALIDATED_STRATEGY = "VALIDATED_STRATEGY"
DEPLOYMENT_CANDIDATE = "DEPLOYMENT_CANDIDATE"
ARCHIVED_REFUTED = "ARCHIVED_OR_REFUTED"

# ---- Meta-filter eligibility (sec.7) ----
META_FILTER_ELIGIBLE = "META_FILTER_ELIGIBLE"
META_FILTER_NOT_READY = "META_FILTER_NOT_READY"
META_FILTER_INAPPROPRIATE = "META_FILTER_INAPPROPRIATE"


def build_deep_dive_candidates():
    """Sec.1-4 della richiesta: candidati verificati in PROFONDITA' contro
    l'artifact reale (non solo il registro machine-generated)."""

    # ---- VOLATILITY_BREAKOUT_CONFIRMED (Strategy Foundry Phase 3) ----
    volbrk = {
        "strategy_id": "VOLATILITY_BREAKOUT_CONFIRMED",
        "source_artifact": "vault/01-Trading/NEXUS - Strategy Foundry Phase 3 Volatility Breakout "
                            "Implementation.md (commit f035d30); registrata in contracts/strategy-registry.json "
                            "(family=TREND, status=EXPERIMENTAL, selector_index=56)",
        "not_the_same_as": "Phase 7's raw 'BREAKOUT' o 'VOLATILITY_EXPANSION' detector (build_events_p71.py) - "
                            "nome simile, DEFINIZIONE ed identita' diverse. VOLATILITY_BREAKOUT_CONFIRMED "
                            "combina strutturalmente la logica di ENTRAMBI (rottura di un range 20-barre + "
                            "conferma tramite true range>1.0xATR sulla stessa barra) IN UN'UNICA strategia "
                            "COMPLETA con SL/TP/timeout propri - non va confuso con nessuno dei due raw event "
                            "presi singolarmente.",
        "lifecycle_contract": {
            "entry": "Chiusura della barra segnale close[i], al superamento del massimo/minimo delle 20 barre "
                     "[i-21,i-2] (offset 2), confermata da true_range[i] > 1.0 x ATR(14)[i]",
            "direction": "BUY se rottura sopra il range, SELL se sotto",
            "invalidation_stop": "Lato opposto dello stesso range N=20 (minimo per BUY, massimo per SELL)",
            "target_exit": "entry ± 1R, dove R = |entry - invalidation| (ampiezza del range)",
            "timeout": "40 barre H4 (~6.7 giorni), uscita a tempo (TIME) oltre questo limite",
            "management": "Nessun trailing/BE/filtro di sessione o regime aggiunto (dichiarato esplicitamente "
                          "fuori scope in Fase 3)",
            "risk_sizing": None,
            "trading_costs": "Costi/broker nativi non alterati nell'audit di parita' (dettaglio specifico non "
                              "estratto qui)",
            "timeframe": "H4",
            "instrument": "XAUUSD (GOLD)",
        },
        "classification": FULL_STRATEGY_SPEC,
        "classification_rationale": "Unica strategia del progetto con OGNI campo del lifecycle esplicitamente "
                                     "dichiarato E verificata bit-per-bit identica fra implementazione Python "
                                     "(927/927 eventi grezzi) e MQL5 live (0 SIGNAL_LOGIC_DIFFERENCE su audit "
                                     "di parita' dedicato).",
        "evidence_ladder": {
            "discovery": {"status": "PASS", "detail": "Phase 2 screening: delta_p discovery=+0.037R"},
            "internal_validation": {"status": "PASS", "detail": "Phase 2 screening: delta_p validation=+0.133R, "
                                                                  "n~927 eventi grezzi"},
            "full_backtest_engine": {"status": "PASS", "detail": "run_backtest() completo (gestione one-at-a-"
                                                                   "time): 243 trade, PF=1.20, expectancy=0.068R "
                                                                   "a costo zero"},
            "signal_parity_python_vs_mql5": {"status": "PASS", "detail": "927/927 eventi raw identici; "
                                                                          "SIGNAL_LOGIC_DIFFERENCE=0 su finestra "
                                                                          "comune 2026-03-01/2026-09-01"},
            "fast_structural_real_ticks_6mo": {"status": "BORDERLINE", "detail": "n=14, PF=1.165, win "
                                                "rate=50%, concentrazione temporale forte (2 mesi su 5 attivi "
                                                "spiegano quasi tutto il profitto), asimmetria BUY/SELL "
                                                "(PF 0.734 vs 2.236) non distinguibile da rumore su campione "
                                                "cosi' piccolo"},
            "serious_3y_backtest": {"status": "NOT_RUN", "detail": "Verdetto esplicito: HOLD_NEEDS_MORE_"
                                                                     "EVIDENCE - non promossa"},
            "demo": {"status": "NOT_RUN", "detail": None},
            "live": {"status": "NOT_RUN", "detail": None},
        },
        "evidence_verdict": "HOLD_NEEDS_MORE_EVIDENCE",
        "evidence_verdict_is_not_refuted": True,
        "evidence_verdict_note": "Esplicitamente NON un REJECTED_FAST_STRUCTURAL - nessuna rottura strutturale "
                                  "(parita' confermata, expectancy positiva, nessun leakage) - semplicemente "
                                  "campione ancora troppo piccolo/concentrato per un impegno a un serious 3Y.",
        "failure_memory_links": [],
        "meta_filter_eligibility": META_FILTER_ELIGIBLE,
        "meta_filter_eligibility_rationale": "FULL_STRATEGY_SPEC verificato, lifecycle deterministico, "
                                              "success/failure gia' definiti (barriera R nativa, non "
                                              "sintetica), evidenza sufficiente (non un raw detector) - il "
                                              "candidato piu' maturo del progetto per un futuro test di "
                                              "regime filter, SE/QUANDO accumulera' piu' campione.",
    }

    # ---- H006_LIQUIDITY_SWEEP_RECLAIM (Phase5->6.6, unico hypothesis con framework statistico completo) ----
    h006_decision = load_json(H006_DECISION_CARD_PATH)["payload"]
    h006_primary = load_json(H006_PRIMARY_RESULT_PATH)["primary_result"]
    hyp_registry = load_json(HYPOTHESIS_REGISTRY_PATH)
    h006_hyp_entry = next(h for h in hyp_registry if h["hypothesis_id"] == "H006_LIQUIDITY_SWEEP_RECLAIM_TRUE_HOLDOUT")
    h004_hyp_entry = next(h for h in hyp_registry if h["hypothesis_id"] == "H004_EVENT_RECLAIM")

    h006 = {
        "strategy_id": "H006_LIQUIDITY_SWEEP_RECLAIM",
        "source_artifact": "server/research_scripts/phase6/H006_frozen_spec.json + h006_primary_result.json + "
                            "phase6_6/h006_decision_card_v2.json (parent: phase5_5 H004_EVENT_RECLAIM)",
        "not_the_same_as": "SEQ-0014B's SWEEP/RECLAIM raw events (build_events_p71.py, Phase 7) - stesso "
                            "meccanismo di base (sweep poi reclaim) ma H006 e' un DISEGNO COMPLETO con entry "
                            "alla barra di CONFERMA reclaim, baseline matched, outcome primario ATR-barrier - "
                            "non un raw event isolato.",
        "lifecycle_contract": {
            "entry": "Chiusura della prima barra di conferma reclaim (close oltre il livello swept), non la "
                     "barra dello sweep originale",
            "direction": "+1 se reclaim al rialzo (sweep di un LOW poi ripresa sopra), -1 se al ribasso",
            "invalidation_stop": None,
            "target_exit": "Barriera P(+1.0xATR before -1.0xATR) dalla chiusura di conferma, orizzonte 40 "
                            "barre H4",
            "timeout": "40 barre H4 (implicito nella definizione della barriera)",
            "management": None,
            "risk_sizing": None,
            "trading_costs": None,
            "timeframe": "H4",
            "instrument": "XAUUSD (GOLD)",
        },
        "classification": FULL_STRATEGY_SPEC,
        "classification_rationale": "Entry/direzione/outcome (success/failure via barriera ATR) tutti "
                                     "dichiarati esplicitamente e pre-registrati in H006_frozen_spec.json "
                                     "PRIMA di vedere l'holdout - manca solo un'invalidazione/stop nativa "
                                     "esplicita (l'outcome e' definito come probabilita' di barriera, non "
                                     "come trade con SL separato).",
        "evidence_ladder": {
            "discovery": {"status": "PASS", "detail": f"H004 (Phase 5, event_alone): n_discovery="
                          f"{h004_hyp_entry['result']['n_discovery']}, delta_p="
                          f"{h004_hyp_entry['result']['delta_p_discovery']:.4f}"},
            "internal_validation": {"status": "PASS", "detail": f"H004: n_validation="
                                     f"{h004_hyp_entry['result']['n_validation']}, delta_p="
                                     f"{h004_hyp_entry['result']['delta_p_validation']:.4f}, classificazione "
                                     f"originale={h004_hyp_entry['result']['classification_original']} "
                                     f"(POST_HOC_CANDIDATE - selezionato da un batch di 14, non pre-registrato "
                                     f"come primario)"},
            "true_holdout": {"status": "BORDERLINE", "detail": f"H006 (Phase 6, mai visto prima): "
                              f"n={h006_primary['n_events']}, delta_p={h006_primary['delta_p']:.4f} < soglia "
                              f"materialita' 0.15, CI95 sovrapposte, direzione BUY({h006_primary['buy']['observed_p']:.3f}) "
                              f"vs SELL({h006_primary['sell']['observed_p']:.3f}) non consistente"},
            "dependence_audit": {"status": "PASS_BUT_HIGH_DEPENDENCE", "detail": "Phase 6.5: "
                                  "dependence_flag=HIGH, overlap_rate=0.991 - n effettivo indipendente stimato "
                                  "fra 46 e 115 a seconda del metodo"},
            "external_replication": {"status": "NOT_RUN", "detail": "CROSS_FEED_VALIDATION (E4, fonte dati "
                                       "diversa da Dukascopy) mai tentato"},
            "demo": {"status": "NOT_RUN", "detail": None},
            "live": {"status": "NOT_RUN", "detail": None},
        },
        "evidence_verdict": "RETAIN_E2 (BORDERLINE, non promosso)",
        "evidence_verdict_is_not_refuted": True,
        "evidence_verdict_note": h006_decision["primary_reason"],
        "registry_vocabulary_drift_found": {
            "description": "TRE etichette diverse per LO STESSO risultato in tre artifact diversi dello "
                            "stesso hypothesis: hypothesis_registry_v1.json (Phase 5.5) usa status='WEAK'; "
                            "h006_primary_result.json (Phase 6) usa VERDICT='BORDERLINE'; "
                            "h006_decision_card_v2.json (Phase 6.6) usa current_grade='E2'/decision="
                            "'RETAIN_E2'. Nessuna contraddizione SOSTANZIALE (stesso delta_p=0.0572 citato "
                            "ovunque), ma un drift di VOCABOLARIO fra fasi che rende piu' difficile un "
                            "confronto automatico fra hypothesis - segnalato qui come incoerenza di registro "
                            "(sec.12 della richiesta), non corretto (fuori scope).",
        },
        "failure_memory_links": ["registry_vocabulary_drift (questo stesso record)"],
        "meta_filter_eligibility": META_FILTER_ELIGIBLE,
        "meta_filter_eligibility_rationale": "FULL_STRATEGY_SPEC, lifecycle deterministico, evidenza "
                                              "sufficiente per non essere un raw detector (n=115 true holdout, "
                                              "gia' oltre il minimo nominale) - MA il risultato di validazione "
                                              "e' esso stesso BORDERLINE/non promosso: testare un meta-filter "
                                              "regime su una strategia gia' 'RETAIN_E2' avrebbe basso valore "
                                              "atteso (non c'e' un edge chiaro da filtrare) - eleggibile "
                                              "strutturalmente, ma bassa priorita' pratica.",
    }

    # ---- WICK_SWEEP_RECLAIM (causal experiment lineage - execution-layer failure, non statistico) ----
    wick_sweep = {
        "strategy_id": "WICK_SWEEP_RECLAIM",
        "source_artifact": "vault/01-Trading/NEXUS - Failure Memory (Registro Pattern di Fallimento "
                            "Metodologico) (12-09).md; contracts/strategy-registry.json (status=EXPERIMENTAL, "
                            "live_implementation=true, research_parity=NOT_IMPLEMENTED)",
        "not_the_same_as": "H006_LIQUIDITY_SWEEP_RECLAIM (Phase 5-6.6) - stesso concetto di base (sweep poi "
                            "reclaim) ma lineage/implementazione SEPARATA (causal_experiment_*.py, non "
                            "build_events.py), con un design di entry/timing diverso (vedi 'NEXUS EA - "
                            "WICK_SWEEP Entry Timing Study').",
        "lifecycle_contract": {
            "entry": "Non estratto in dettaglio qui (fuori scope della Failure Memory) - riferito come "
                     "'trigger_price' in un design a due varianti (FILL_ANCHORED / tick-level RECLAIM_TICK / "
                     "RECLAIM_LIMIT_RETEST)",
            "direction": None, "invalidation_stop": None, "target_exit": None, "timeout": None,
            "management": None, "risk_sizing": None, "trading_costs": None,
            "timeframe": None, "instrument": None,
        },
        "classification": PARTIAL_STRATEGY,
        "classification_rationale": "Campi del lifecycle non estratti in dettaglio da questo audit (fuori "
                                     "scope: la fonte primaria e' un registro di pattern di fallimento "
                                     "METODOLOGICO, non uno strategy spec) - classificato PARTIAL non per "
                                     "assenza di formalizzazione ma perche' questo audit non ha approfondito "
                                     "il contratto completo.",
        "evidence_ladder": {
            "shadow_hypothesis_test": {"status": "PASS", "detail": "PF shadow=5.80 (assumendo fill esatto al "
                                        "trigger_price) - titolo del report collegato: 'HYPOTHESIS STRONGLY "
                                        "SUPPORTED'"},
            "fast_smoke_real_execution": {"status": "FAIL", "detail": "PF reale=0.78-0.80, stesso campione, "
                                           "stessa cadenza - l'edge shadow non sopravvive a NESSUNA forma di "
                                           "esecuzione realistica testata (ne' FILL_ANCHORED ne' replay "
                                           "tick-level RECLAIM_TICK/RECLAIM_LIMIT_RETEST)"},
            "demo": {"status": "NOT_RUN", "detail": None},
            "live": {"status": "NOT_RUN", "detail": None},
        },
        "evidence_verdict": "REFUTED_AT_EXECUTION_VALIDATION",
        "evidence_verdict_is_not_refuted": False,
        "evidence_verdict_note": "Distinto esplicitamente da un REFUTED statistico: l'ipotesi era 'STRONGLY "
                                  "SUPPORTED' a livello di outcome shadow - il fallimento e' emerso "
                                  "ESCLUSIVAMENTE al livello di esecuzione reale (assunzione di fill "
                                  "idealizzato), il pattern SHADOW_EXECUTION_ASSUMPTION gia' registrato nella "
                                  "Failure Memory di progetto.",
        "failure_memory_links": ["SHADOW_EXECUTION_ASSUMPTION", "TIMEZONE_MISMATCH", "DATA_COVERAGE_GAP",
                                  "CAUSAL_HOOK_MISMATCH"],
        "meta_filter_eligibility": META_FILTER_INAPPROPRIATE,
        "meta_filter_eligibility_rationale": "Gia' refutato a livello di esecuzione - non ha senso applicare "
                                              "un meta-filter di regime su una strategia la cui base "
                                              "esecutiva e' gia' dimostrata non sopravvivere.",
    }

    # ---- SAR: due identita' correlate ma distinte (H015 python esterno + live MQL5) ----
    hyp_h015 = next(h for h in hyp_registry if h["hypothesis_id"] == "H015_SAR_EXTERNAL_VALIDATION")
    sar_python = {
        "strategy_id": "H015_SAR_EXTERNAL_VALIDATION (SAR_PSAR_EMA_TREND_SIGNAL)",
        "source_artifact": "server/research_scripts/phase5_5/hypothesis_registry_v1.json (H015)",
        "not_the_same_as": "La strategia live MQL5 'SAR' (contracts/strategy-registry.json) - stesso segnale "
                            "concettuale ma un test di validazione ESTERNO e INDIPENDENTE (dataset "
                            "Dukascopy via simbolo custom XAUUSD_DSC, non il motore MQL5 in produzione).",
        "lifecycle_contract": {
            "entry": "Segnale SAR (Parabolic SAR + EMA trend), gia' congelato da fasi precedenti",
            "direction": "BUY/SELL secondo il segnale SAR/EMA",
            "invalidation_stop": "1x ATR (SL1xATR)",
            "target_exit": "6x ATR (TP6xATR)",
            "timeout": None, "management": "RAW (nessuna gestione dinamica dichiarata)", "risk_sizing": None,
            "trading_costs": None, "timeframe": "H4", "instrument": "XAUUSD (custom symbol XAUUSD_DSC)",
        },
        "classification": FULL_STRATEGY_SPEC,
        "classification_rationale": "Entry/direzione/SL/TP tutti dichiarati esplicitamente e pre-registrati "
                                     "(sar_dukascopy_independent_validation.md sec.6) PRIMA di vedere il "
                                     "risultato.",
        "evidence_ladder": {
            "prior_broker_result": {"status": "PASS", "detail": "Broker XM: PF=1.281 (risultato precedente "
                                     "usato come riferimento, non ri-derivato qui)"},
            "prior_python_dukascopy_pre2023": {"status": "BORDERLINE", "detail": "PF=0.93/0.97 (due run "
                                                "precedenti citate come riferimento)"},
            "external_validation_dukascopy": {"status": "FAIL", "detail": f"PF={hyp_h015['result']['PF']}, "
                                               f"n={hyp_h015['result']['n']} - sotto la soglia FAIL<0.95 "
                                               f"pre-registrata (PASS>=1.15/BORDERLINE 0.95-1.15/FAIL<0.95)"},
            "demo": {"status": "NOT_RUN", "detail": None}, "live": {"status": "NOT_RUN", "detail": None},
        },
        "evidence_verdict": "REFUTED",
        "evidence_verdict_is_not_refuted": False,
        "evidence_verdict_note": "SAR_EXTERNAL_CONFIRMATION_FAIL - nessun rescue/filtro applicato dopo aver "
                                  "visto il risultato (stop_condition pre-registrata).",
        "failure_memory_links": [],
        "meta_filter_eligibility": META_FILTER_INAPPROPRIATE,
        "meta_filter_eligibility_rationale": "Gia' refutato - stesso principio di WICK_SWEEP_RECLAIM (non "
                                              "testare un meta-filter su una strategia gia' respinta).",
    }

    sar_live = {
        "strategy_id": "SAR (live MQL5, contracts/strategy-registry.json)",
        "source_artifact": "contracts/strategy-registry.json (family=MOMENTUM, status=ACTIVE, "
                            "live_implementation=true, research_implementation=true, "
                            "research_parity=APPROXIMATE); vault MOC - Strategie.md",
        "not_the_same_as": "H015 (validazione Python esterna sopra) - stesso concetto di segnale, "
                            "implementazione/pipeline di evidenza SEPARATA.",
        "lifecycle_contract": {
            "entry": "Segnale SAR/EMA nel motore MQL5 live (dettaglio esatto non estratto da questo audit - "
                     "vedi NXS_Strategies.mqh)",
            "direction": None, "invalidation_stop": None, "target_exit": None, "timeout": None,
            "management": None, "risk_sizing": None, "trading_costs": None,
            "timeframe": None, "instrument": "XAUUSD (GOLD), live account",
        },
        "classification": FULL_STRATEGY_SPEC,
        "classification_rationale": "live_implementation=true nel registro canonico implica un modulo MQL5 "
                                     "reale con SL/TP/gestione (stesso framework NXS_StrategyProfiles.mqh "
                                     "gia' verificato per VOLATILITY_BREAKOUT_CONFIRMED) - campi esatti non "
                                     "individualmente riverificati in questo audit (STRUCTURALLY_IMPLEMENTED, "
                                     "non VERIFIED riga per riga).",
        "evidence_ladder": {
            "backtest_6y_segmented_2019_2024": {"status": "FAIL", "detail": "MOC - Strategie.md: -34.3R su 6 "
                                                 "anni, 0/6 anni positivi - LA PEGGIORE fra le 37 strategie "
                                                 "tracciate. Fix testato (vero Parabolic SAR nel proxy sito): "
                                                 "PF 1.17->1.28, non ancora validato su MT5."},
            "demo": {"status": "NOT_RUN", "detail": None}, "live": {"status": "NOT_RUN", "detail": None},
        },
        "evidence_verdict": "REFUTED (per evidenza MOC, wide-sample multi-anno)",
        "evidence_verdict_is_not_refuted": False,
        "evidence_verdict_note": "Convergenza indipendente: DUE pipeline di evidenza separate (H015 Python "
                                  "esterno E il backtest MQL5 6-anni) concordano entrambe su un verdetto "
                                  "negativo per il concetto SAR - un segnale di refutazione robusto, non "
                                  "dipendente da un solo metodo.",
        "registry_status_conflict_found": {
            "description": "contracts/strategy-registry.json riporta status='ACTIVE' per SAR nonostante "
                            "l'evidenza empirica (MOC + H015) sia negativa su campione ampio e convergente. "
                            "'ACTIVE' in questo registro descrive la disponibilita'/wiring nel codice, NON "
                            "necessariamente se la strategia sta rischiando capitale reale in questo momento "
                            "(quel controllo separato e' NXS_Profile_Enabled a runtime, MAI verificato in "
                            "questo audit) - ma la giustapposizione merita un flag esplicito, non un "
                            "silenzio.",
            "verified_not_confirmed": "Il flag di runtime NXS_Profile_Enabled per SAR NON e' stato letto in "
                                       "questo audit - non si afferma che capitale reale sia attualmente a "
                                       "rischio, solo che il registro di codice e l'evidenza empirica sono "
                                       "disallineati.",
        },
        "failure_memory_links": [],
        "meta_filter_eligibility": META_FILTER_INAPPROPRIATE,
        "meta_filter_eligibility_rationale": "Refutata su doppia evidenza indipendente.",
    }

    # ---- ADX_RSI (live MQL5) ----
    adx_rsi = {
        "strategy_id": "ADX_RSI",
        "source_artifact": "contracts/strategy-registry.json (family=MOMENTUM, status=ACTIVE, "
                            "live_implementation=true, research_implementation=true, "
                            "research_parity=APPROXIMATE); vault MOC - Strategie.md; "
                            "MQL5/Presets/Research/ADX_RSI_RESEARCH_RAW.set",
        "not_the_same_as": None,
        "lifecycle_contract": {
            "entry": "Segnale ADX+RSI nel motore MQL5 live (dettaglio esatto non estratto - vedi "
                     "NXS_Strategies.mqh/preset RESEARCH_RAW vs RESEARCH_RECIPE)",
            "direction": None, "invalidation_stop": None, "target_exit": None, "timeout": None,
            "management": None, "risk_sizing": None, "trading_costs": None,
            "timeframe": None, "instrument": "XAUUSD (GOLD)",
        },
        "classification": FULL_STRATEGY_SPEC,
        "classification_rationale": "live_implementation=true (STRUCTURALLY_IMPLEMENTED, non "
                                     "individualmente riverificato riga per riga in questo audit).",
        "evidence_ladder": {
            "backtest_6y_segmented_2019_2024": {"status": "FAIL", "detail": "MOC - Strategie.md: -15.3R su 6 "
                                                 "anni, 1/6 anni positivi. Fix applicato: aggiunto vero filtro "
                                                 "ADX>20 (mai calcolato prima nonostante il nome) - non ancora "
                                                 "validato su MT5."},
            "demo": {"status": "NOT_RUN", "detail": None}, "live": {"status": "NOT_RUN", "detail": None},
        },
        "evidence_verdict": "REFUTED (per evidenza MOC, wide-sample multi-anno)",
        "evidence_verdict_is_not_refuted": False,
        "evidence_verdict_note": None,
        "registry_status_conflict_found": {
            "description": "Stesso pattern di SAR: status='ACTIVE' nel registro canonico nonostante evidenza "
                            "MOC negativa su campione ampio.",
            "verified_not_confirmed": "NXS_Profile_Enabled non verificato in questo audit.",
        },
        "failure_memory_links": [],
        "meta_filter_eligibility": META_FILTER_INAPPROPRIATE,
        "meta_filter_eligibility_rationale": "Refutata su evidenza wide-sample.",
    }

    # ---- BREAKOUT_ACC (miglior performer live, da NON confondere con BREAKOUT/VOLATILITY_BREAKOUT_CONFIRMED) ----
    breakout_acc = {
        "strategy_id": "BREAKOUT_ACC",
        "source_artifact": "contracts/strategy-registry.json (family=TREND, status=ACTIVE, "
                            "live_implementation=true, research_implementation=true, "
                            "research_parity=APPROXIMATE); vault MOC - Strategie.md",
        "not_the_same_as": "Ne' il raw event 'BREAKOUT' di Phase 7 (build_events_p71.py), ne' "
                            "'VOLATILITY_BREAKOUT_CONFIRMED' (Strategy Foundry) - tre identita' distinte che "
                            "condividono solo la parola 'breakout' nel nome. Nessuna delle tre va assunta "
                            "equivalente alle altre senza verifica diretta del codice (stesso principio "
                            "guardia gia' applicato in Phase 7.6E).",
        "lifecycle_contract": {
            "entry": "Segnale di accelerazione di breakout nel motore MQL5 live (dettaglio esatto non "
                     "estratto - vedi NXS_Strategies.mqh)",
            "direction": None, "invalidation_stop": None, "target_exit": None, "timeout": None,
            "management": None, "risk_sizing": None, "trading_costs": None,
            "timeframe": None, "instrument": "XAUUSD (GOLD)",
        },
        "classification": FULL_STRATEGY_SPEC,
        "classification_rationale": "live_implementation=true (STRUCTURALLY_IMPLEMENTED, non "
                                     "individualmente riverificato riga per riga in questo audit).",
        "evidence_ladder": {
            "backtest_6y_segmented_2019_2024": {"status": "BORDERLINE_POSITIVE", "detail": "MOC - Strategie."
                                                 "md: +4.3R su 6 anni, 5/6 anni positivi - la piu' stabile del "
                                                 "'nucleo hedge candidato' (mai un anno chiaramente negativo)."},
            "demo": {"status": "NOT_RUN", "detail": None}, "live": {"status": "NOT_RUN", "detail": None},
        },
        "evidence_verdict": "DISCOVERY_SUPPORTED (informale - nessun Wilson CI/dependence-audit applicato)",
        "evidence_verdict_is_not_refuted": True,
        "evidence_verdict_note": "IMPORTANTE (sec.8 della richiesta): 'promettente' su R-multiple/PF grezzo "
                                  "NON equivale a 'validata' nel senso rigoroso di H006/VOLATILITY_BREAKOUT_"
                                  "CONFIRMED (nessun Wilson CI, nessun dependence audit, nessuna separazione "
                                  "discovery/holdout dichiarata per questa metrica) - classificato qui come "
                                  "il miglior candidato INFORMALE del portafoglio EA, non come strategia "
                                  "statisticamente validata.",
        "failure_memory_links": [],
        "meta_filter_eligibility": META_FILTER_NOT_READY,
        "meta_filter_eligibility_rationale": "FULL_STRATEGY_SPEC e il miglior performer del portafoglio live, "
                                              "ma l'evidenza non e' ancora al livello di rigore statistico "
                                              "(Wilson CI/dependence-aware) richiesto per considerarla un "
                                              "candidato meta-filter pienamente maturo - servirebbe prima lo "
                                              "stesso trattamento statistico gia' applicato a H006/"
                                              "VOLATILITY_BREAKOUT_CONFIRMED.",
    }

    return {
        "VOLATILITY_BREAKOUT_CONFIRMED": volbrk,
        "H006_LIQUIDITY_SWEEP_RECLAIM": h006,
        "WICK_SWEEP_RECLAIM": wick_sweep,
        "H015_SAR_EXTERNAL_VALIDATION": sar_python,
        "SAR_LIVE": sar_live,
        "ADX_RSI": adx_rsi,
        "BREAKOUT_ACC": breakout_acc,
    }


# ---- MOC - Strategie.md: trascrizione manuale dei 37 bucket (markdown non parsificabile in modo affidabile,
# contenuto letto e citato direttamente dal file reale) ----
MOC_BUCKETS = {
    "PROMETTENTI_NUCLEO_HEDGE": {
        "note": "+7.6R combinato su 6 anni (era +14.7R su 5 - il 2024 ha tolto quasi meta' del guadagno)",
        "strategies": {
            "Breakout Acc": "+4.3R/6y, 5/6 anni positivi - la piu' stabile",
            "Cisd": "+3.2R/6y, primo anno negativo nel 2024 (-0.3, marginale)",
            "Turtle Soup": "RIDIMENSIONATA: +0.1R/6y (era +7.3R/5y) - il 2024 (-7.2R) ha quasi azzerato tutto",
        },
    },
    "FALLITE_CAMPIONE_AMPIO": {
        "note": "400-1150 trade su 6 anni (aggregato sul gruppo) - confermate su campione ampio, priorita' di "
                "intervento",
        "strategies": {
            "Sar": "-34.3R, 0/6 anni positivi - la peggiore in assoluto",
            "Macd": "-21.1R - era validata su v2.4.8 (PF1.11), il 'raffinamento' v2.5.0 l'ha peggiorata",
            "Rsi Div": "-17.5R - sale in questo gruppo col segmento 9 (2024=-10.1, il peggiore in assoluto)",
            "Adx Rsi": "-15.3R, 1/6 anni positivi",
            "Tsi": "-7.9R su 721 trade (campione enorme) - PF 0.82 troppo stabilmente negativo per essere "
                   "ambiguo",
        },
    },
    "IN_ATTESA": {
        "note": "config v2.5.0, dato ancora ambiguo o negativo minore",
        "strategies": {
            "Fvg Cont": "-9.3R/6y, 2024 pessimo (-7.0) dopo 3 anni di ripresa",
            "Bjorgum": "-8.6R/6y (96 trade), 5/6 negativi",
            "Ema Pullback": "-5.5R, volatile, nessun trend chiaro",
        },
    },
    "NON_VALIDATE_MARGINALI": {
        "note": "PF sotto 1.0, negativa ma non fra le priorita' peggiori",
        "strategies": {"Ob Mit": "-4.1R/6y, ma 2024 positivo (+0.4) - potrebbe essere in ripresa"},
    },
    "CAMPIONE_TROPPO_PICCOLO": {
        "note": "<15 trade sui 3 anni - PF puo' sembrare buono ma non e' statisticamente affidabile",
        "strategies": {
            "Bollinger": None, "Liq Sweep": None, "London Bo": None, "Order Block": None, "Sh Bms Rto": None,
            "Malaysian Snr": "10 trade in 5 anni (+0.4R)",
            "Fvg Mit": "3 trade in 5 anni",
            "Sms Bms Rto": "3 trade in 5 anni",
        },
    },
    "NESSUN_TRADE": {
        "note": "0 setup rilevati o segnali sempre bloccati nei 5 anni 2019-2023",
        "strategies": {"Ifvg": None, "Liq Void": None, "Range Fade": None, "Weekly Exp": None},
    },
    "DISABILITATE": {
        "note": "Spente esplicitamente in NXS_Profile_Enabled dopo test reali negativi",
        "strategies": {"Bb Squeeze": None, "Disp Rebal": None, "Ichimoku": None, "Ote Cont": None,
                        "Struct React": None},
    },
    "PRIMA_CONNESSIONE_SITO_MAI_VALIDATE_MT5": {
        "note": "Dati preliminari (sito intraday, ~2 anni Yahoo, non 10) - da validare su MT5 isolato prima di "
                "qualunque conclusione",
        "strategies": {
            "Amd Cont": "PF2.07 su 4h (62 trade, DD5.85%) - il piu' promettente",
            "Po3": "PF1.51 su 4h con TP dinamico reale (45 trade, DD6.79%)",
            "Silver Bullet": "PF1.52 su 4h (68 trade) ma negativo su 1h",
            "Amd Reversal": "quasi breakeven su 4h (PF1.10, 57 trade)",
            "Ldn Reversal": "quasi breakeven su 4h (PF1.08, 108 trade) ma DD alto",
            "Ny Reversal": "PF1.42 su 1h ma solo 20 trade, troppo pochi per giudicare",
            "Judas Swing": "PF1.4 su 4h con TP dinamico reale (59 trade, DD4.9%)",
        },
    },
    "MAI_TRACCIATA": {
        "note": "Scoperta il 15/07 durante l'audit di fedelta' - mancava dall'indice",
        "strategies": {"Elliott": "nessun dato ancora raccolto, non e' nel motore sito"},
    },
}


def build_moc_to_registry_crossref(strategy_registry):
    """Cross-reference fra i nomi MOC (italiano, Obsidian) e gli strategy_id del registro canonico
    (contracts/strategy-registry.json) - SOLO dove la corrispondenza e' inequivocabile (nome
    normalizzato identico), MAI assunta per somiglianza superficiale (stesso principio guardia di
    Phase 7.6E). Le corrispondenze ambigue sono dichiarate UNRESOLVED, non forzate."""
    by_id = {s["strategy_id"]: s for s in strategy_registry["strategies"]}

    def normalize(name):
        return name.upper().replace(" ", "_")

    confirmed = {}
    unresolved = []
    for bucket_name, bucket in MOC_BUCKETS.items():
        for moc_name in bucket["strategies"].keys():
            norm = normalize(moc_name)
            candidates = [sid for sid in by_id if sid == norm or sid.startswith(norm + "_")]
            # match esatto preferito
            if norm in by_id:
                confirmed[moc_name] = {"registry_strategy_id": norm, "bucket": bucket_name,
                                        "registry_status": by_id[norm]["status"],
                                        "registry_live_implementation": by_id[norm]["live_implementation"]}
            elif len(candidates) == 1:
                confirmed[moc_name] = {"registry_strategy_id": candidates[0], "bucket": bucket_name,
                                        "registry_status": by_id[candidates[0]]["status"],
                                        "registry_live_implementation": by_id[candidates[0]]["live_implementation"],
                                        "note": "match per prefisso, non esatto"}
            else:
                unresolved.append({"moc_name": moc_name, "bucket": bucket_name,
                                    "reason": "nessun match esatto o prefisso univoco in "
                                              "contracts/strategy-registry.json - richiede disambiguazione "
                                              "manuale, non assunta qui"})
    return confirmed, unresolved


def build_prefix_match_implementation_ambiguities(crossref_confirmed):
    """Segnala i cross-reference risolti SOLO per prefisso (non nome esatto) la cui evidenza narrativa
    MOC (trade reali su 6 anni) sembra presupporre un'implementazione live che il registro canonico
    NON conferma (live_implementation=False) - un'ambiguita' diversa dal conflitto ACTIVE-vs-fallita,
    MAI risolta qui (richiede disambiguazione manuale)."""
    ambiguities = []
    for moc_name, info in crossref_confirmed.items():
        if info.get("note") == "match per prefisso, non esatto" and not info["registry_live_implementation"]:
            ambiguities.append({
                "moc_name": moc_name,
                "registry_strategy_id": info["registry_strategy_id"],
                "bucket": info["bucket"],
                "issue": "MOC descrive risultati di backtest/trade reali su piu' anni per questa strategia, "
                         "ma il registro canonico associato (match solo per prefisso, non nome esatto) ha "
                         "live_implementation=False (research_only) - possibile disallineamento fra il nome "
                         "storico usato in MOC e l'attuale strategy_id nel registro (es. rinominazione/"
                         "refactoring non riflesso in questo cross-reference), oppure la MOC potrebbe "
                         "riferirsi a una versione precedente/diversa della strategia. Non disambiguato qui.",
            })
    return ambiguities


def build_active_status_vs_failed_evidence_conflicts(crossref_confirmed):
    """Trova le strategie con evidenza MOC negativa (bucket FALLITE_CAMPIONE_AMPIO) MA status='ACTIVE' nel
    registro canonico - un'incoerenza di governance genuina, MAI risolta qui (fuori scope)."""
    conflicts = []
    for moc_name, info in crossref_confirmed.items():
        if info["bucket"] == "FALLITE_CAMPIONE_AMPIO" and info["registry_status"] == "ACTIVE":
            conflicts.append({
                "moc_name": moc_name,
                "registry_strategy_id": info["registry_strategy_id"],
                "moc_evidence": MOC_BUCKETS["FALLITE_CAMPIONE_AMPIO"]["strategies"][moc_name],
                "registry_status": "ACTIVE",
                "conflict": "Il registro canonico di codice dichiara la strategia ACTIVE nonostante "
                            "l'evidenza empirica di progetto (MOC, backtest 6 anni multi-centinaia di trade) "
                            "la classifichi come confermata fallita.",
                "not_verified_here": "Il flag runtime NXS_Profile_Enabled (che potrebbe gia' avere disattivato "
                                      "la strategia a prescindere da questo status) NON e' stato letto in "
                                      "questo audit - nessuna affermazione fatta su rischio di capitale reale "
                                      "attuale.",
            })
    return conflicts


def build_full_registry_survey():
    """Sec.10-11: classificazione rule-based delle 83 strategie del registro canonico, usando SOLO i
    campi gia' presenti (nessun campo individuale riverificato oltre ai 7 deep-dive candidates sopra)."""
    reg = load_json(STRATEGY_REGISTRY_PATH)
    per_family_status_counts = {}
    classified = []
    for s in reg["strategies"]:
        if s["live_implementation"] or s["research_implementation"]:
            classification = FULL_STRATEGY_SPEC
            confidence = "STRUCTURALLY_IMPLEMENTED_NOT_INDIVIDUALLY_VERIFIED"
        else:
            classification = ARCHIVED_REFUTED
            confidence = "NO_IMPLEMENTATION_FOUND"
        classified.append({
            "strategy_id": s["strategy_id"], "family": s["family"], "status": s["status"],
            "live_implementation": s["live_implementation"], "research_implementation": s["research_implementation"],
            "research_parity": s["research_parity"], "classification": classification, "confidence": confidence,
        })
        key = (s["family"], s["status"])
        per_family_status_counts[f"{s['family']}/{s['status']}"] = per_family_status_counts.get(
            f"{s['family']}/{s['status']}", 0) + 1
    return {
        "source_file": "contracts/strategy-registry.json",
        "source_file_sha256": file_sha256(STRATEGY_REGISTRY_PATH),
        "source_counts": reg["counts"],
        "classification_method": "RULE_BASED da campi gia' presenti nel registro (live_implementation OR "
                                  "research_implementation => FULL_STRATEGY_SPEC strutturale, coerente col "
                                  "framework NXS_StrategyProfiles.mqh/STRAT_MAP gia' verificato per i "
                                  "deep-dive candidates sopra) - NESSUN campo individuale (entry/SL/TP esatti) "
                                  "riverificato per le strategie non incluse nei deep-dive candidates.",
        "per_family_status_counts": per_family_status_counts,
        "strategies": classified,
        "not_individually_verified_count": sum(1 for c in classified if c["confidence"] ==
                                                "STRUCTURALLY_IMPLEMENTED_NOT_INDIVIDUALLY_VERIFIED"),
    }


def build_pipeline_formalization():
    return {
        "stages": ["EVENT_RESEARCH", "STRATEGY_FORMALIZATION", "STRATEGY_VALIDATION", "META_FILTER_RESEARCH",
                   "EXECUTION_VALIDATION", "PORTFOLIO_RISK"],
        "stage_definitions": {
            "EVENT_RESEARCH": "Trova fenomeni/eventi (es. build_events.py/build_events_p71.py, i 9 raw event "
                               "families di Phase 5/7) - NESSUN lifecycle di trade richiesto a questo livello.",
            "STRATEGY_FORMALIZATION": "entry+invalidazione+target+timeout espliciti, deterministici (es. "
                                       "VOLATILITY_BREAKOUT_CONFIRMED, H006, i moduli MQL5 live).",
            "STRATEGY_VALIDATION": "Stabilisce se esiste un edge - stesso gate rigoroso gia' usato per "
                                    "H006/SEQ-0009/SEQ-0015 (Wilson CI, dependence audit, true holdout) o, "
                                    "quantomeno, un backtest a campione ampio su piu' anni (MOC).",
            "META_FILTER_RESEARCH": "MECH-23-style: quando NON usare una strategia GIA' validata (o "
                                     "quantomeno gia' FULL_STRATEGY_SPEC con evidenza sufficiente) - MAI "
                                     "applicato a un raw event o a una strategia gia' refutata.",
            "EXECUTION_VALIDATION": "Verifica che l'edge sopravviva a un'esecuzione REALE (fill/slippage/gate) "
                                     "- scoperta diretta in WICK_SWEEP_RECLAIM (PF shadow 5.80 -> PF reale "
                                     "0.78-0.80, pattern SHADOW_EXECUTION_ASSUMPTION).",
            "PORTFOLIO_RISK": "Sizing/rischio di portafoglio - non trattato in questo registro.",
        },
        "contract_only_not_new_infrastructure": True,
        "company_control_plane_note": "Il futuro Company Control Plane dovrebbe consumare questo registro "
                                       "come output ufficiale del reparto Quant Research (VALIDATED_STRATEGY_"
                                       "SPEC) e input del reparto Execution - contratto fra reparti, non "
                                       "implementato qui.",
    }


def build():
    strategy_registry = load_json(STRATEGY_REGISTRY_PATH)
    deep_dive = build_deep_dive_candidates()
    crossref_confirmed, crossref_unresolved = build_moc_to_registry_crossref(strategy_registry)
    active_conflicts = build_active_status_vs_failed_evidence_conflicts(crossref_confirmed)
    prefix_ambiguities = build_prefix_match_implementation_ambiguities(crossref_confirmed)
    full_survey = build_full_registry_survey()
    pipeline = build_pipeline_formalization()
    phase76e_audit = load_json(PHASE76E_AUDIT_PATH)["payload"]

    lifecycle_registry_payload = {
        "phase": "7.7A", "artifact_role": "STRATEGY_LIFECYCLE_REGISTRY",
        "scope_note": "Primo inventario canonico delle strategie realmente formalizzate, separato dai raw "
                       "event. Nessuna strategia nuova inventata, nessuna modifica a MECH-23, nessun nuovo "
                       "outcome letto, nessun backtest rieseguito.",
        "baseline_commit": BASELINE_COMMIT,
        "raw_event_reference": {
            "note": "Le 6 famiglie SEQ-0014B (0 FULL_NATIVE_SETUP, 2 PARTIAL_SETUP, 4 DIRECTIONAL_EVENT_ONLY) "
                    "restano classificate come in Phase 7.6E - non riclassificate qui.",
            "reference_artifact": "server/research_scripts/phase7/phase7_6e/seq0014b_native_setup_failure_"
                                   "audit_v1.json",
            "reference_hash": file_sha256(PHASE76E_AUDIT_PATH),
            "family_classification_summary": phase76e_audit["family_classification"]["summary"],
        },
        "deep_dive_candidates": deep_dive,
        "full_registry_survey": full_survey,
        "moc_evidence_buckets": MOC_BUCKETS,
        "moc_to_registry_crossref_confirmed": crossref_confirmed,
        "moc_to_registry_crossref_unresolved": crossref_unresolved,
        "pipeline_formalization": pipeline,
        "no_new_strategy_invented": True,
        "no_mech23_modified": True,
        "no_new_outcome_data_accessed": True,
        "no_new_backtest_executed": True,
        "no_edge_discovery_performed": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }

    evidence_matrix_payload = {
        "phase": "7.7A", "artifact_role": "STRATEGY_EVIDENCE_MATRIX",
        "baseline_commit": BASELINE_COMMIT,
        "scope_note": "Separazione esplicita fra completezza del lifecycle ed evidenza empirica (sec.4/8 "
                       "della richiesta) - una strategia puo' essere FULL_STRATEGY_SPEC e REFUTED "
                       "contemporaneamente, senza contraddizione.",
        "evidence_ladders_by_candidate": {k: v["evidence_ladder"] for k, v in deep_dive.items()},
        "evidence_verdicts_by_candidate": {k: {
            "verdict": v["evidence_verdict"], "is_refuted": not v["evidence_verdict_is_not_refuted"],
            "note": v.get("evidence_verdict_note"),
        } for k, v in deep_dive.items()},
        "registry_status_vs_evidence_conflicts": active_conflicts,
        "prefix_match_implementation_ambiguities": prefix_ambiguities,
        "registry_vocabulary_drift_examples": [
            deep_dive["H006_LIQUIDITY_SWEEP_RECLAIM"]["registry_vocabulary_drift_found"],
        ],
        "failure_memory_reference": {
            "note": "Registro di pattern di fallimento METODOLOGICO (non specifico di una strategia) gia' "
                    "esistente e riusato, non duplicato qui.",
            "reference_artifact": "vault/01-Trading/NEXUS - Failure Memory (Registro Pattern di Fallimento "
                                   "Metodologico) (12-09).md",
            "patterns_cataloged": ["SHADOW_EXECUTION_ASSUMPTION", "TIMEZONE_MISMATCH", "DATA_COVERAGE_GAP",
                                    "CAUSAL_HOOK_MISMATCH"],
        },
        "convergent_evidence_examples": [
            "SAR: due pipeline di evidenza indipendenti (H015 Python esterno PF=0.61; MOC MQL5 6-anni "
            "-34.3R) concordano su REFUTED - segnale di refutazione robusto.",
        ],
        "no_new_outcome_data_accessed": True,
        "no_new_backtest_executed": True,
    }

    meta_filter_payload = {
        "phase": "7.7A", "artifact_role": "STRATEGY_META_FILTER_ELIGIBILITY",
        "baseline_commit": BASELINE_COMMIT,
        "scope_note": "Eleggibilita' CONCETTUALE (sec.7 della richiesta) - il filtro MECH-23 non e' applicato "
                       "qui, solo classificato quali candidati sarebbero strutturalmente appropriati in "
                       "futuro.",
        "requisiti_minimi": ["FULL_STRATEGY_SPEC", "lifecycle deterministico", "success/failure definiti",
                              "execution semantics definite", "evidenza almeno sufficiente per non essere un "
                              "raw detector"],
        "eligibility_by_candidate": {k: {
            "eligibility": v["meta_filter_eligibility"], "rationale": v["meta_filter_eligibility_rationale"],
        } for k, v in deep_dive.items()},
        "pooled_across_strategies_note": "Concettualmente, un 'failure_F' comune per STRATEGIA (analogo a "
                                          "'failure_F' per FAMIGLIA gia' discusso in Phase 7.6E) sarebbe piu' "
                                          "fedele di un pooling ingenuo - MA non implementato qui (nessuna "
                                          "inferenza pooled costruita, per istruzione esplicita).",
        "pipeline_formalization": pipeline,
        "not_applying_filter_yet": True,
    }

    return lifecycle_registry_payload, evidence_matrix_payload, meta_filter_payload


def main():
    lifecycle_payload, evidence_payload, meta_payload = build()

    lifecycle_doc = wrap_with_provenance(
        lifecycle_payload,
        script="server/research_scripts/phase7/phase7_7a/build_strategy_lifecycle_registry.py",
    )
    evidence_doc = wrap_with_provenance(
        evidence_payload,
        script="server/research_scripts/phase7/phase7_7a/build_strategy_lifecycle_registry.py",
    )
    meta_doc = wrap_with_provenance(
        meta_payload,
        script="server/research_scripts/phase7/phase7_7a/build_strategy_lifecycle_registry.py",
    )

    save_json(os.path.join(PHASE77A_DIR, "strategy_lifecycle_registry_v1.json"), lifecycle_doc)
    save_json(os.path.join(PHASE77A_DIR, "strategy_evidence_matrix_v1.json"), evidence_doc)
    save_json(os.path.join(PHASE77A_DIR, "strategy_meta_filter_eligibility_v1.json"), meta_doc)

    print("Written strategy_lifecycle_registry_v1.json, strategy_evidence_matrix_v1.json, "
          "strategy_meta_filter_eligibility_v1.json")
    print(f"lifecycle canonical_sha256={lifecycle_doc['canonical_sha256']}")
    print(f"evidence canonical_sha256={evidence_doc['canonical_sha256']}")
    print(f"meta_filter canonical_sha256={meta_doc['canonical_sha256']}")


if __name__ == "__main__":
    main()
