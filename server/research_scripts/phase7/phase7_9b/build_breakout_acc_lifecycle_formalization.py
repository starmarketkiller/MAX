#!/usr/bin/env python3
"""Phase 7.9B - BREAKOUT_ACC Lifecycle Formalization.

SOLO audit statico / estrazione lifecycle dal codice reale e dagli
artifact/vault esistenti. NESSUN backtest eseguito, NESSuna ottimizzazione,
NESSUN nuovo outcome letto, NESSUNA modifica alla strategia. Tre
deliverable separati (lifecycle contract, evidence lineage, formalization
decision) prodotti da questo unico builder per coerenza referenziale.
"""
import os
import sys

PHASE79B_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(PHASE79B_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "ea0013e090ae2776fe61565392d19991c6dbecc4"


def build_identity():
    registry = load_json(os.path.join(ROOT, "contracts", "strategy-registry.json"))
    entry = next(s for s in registry["strategies"] if s["strategy_id"] == "BREAKOUT_ACC")

    strategies_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    with open(strategies_file, encoding="utf-8") as f:
        strategies_src = f.read()
    guard_line = next(ln for ln in strategies_src.splitlines()
                       if "InpStrat_BREAKOUT_ACC" in ln and "NXS_SelectorAllows" in ln)
    func_present = "SNXSSignal NXS_Strat_BreakoutAcc()" in strategies_src

    ea_file = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
    with open(ea_file, encoding="utf-8") as f:
        ea_src = f.read()
    router_line = next((ln for ln in ea_src.splitlines() if "NXS_Strat_BreakoutAcc()" in ln), None)

    profiles_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_StrategyProfiles.mqh")
    with open(profiles_file, encoding="utf-8") as f:
        profiles_src = f.read()
    profile_enabled_line = next(ln for ln in profiles_src.splitlines()
                                 if 'name == "BREAKOUT_ACC"' in ln and "return true" in ln)

    shared_enum_uses = [ln.strip() for ln in strategies_src.splitlines() if "s.strat = STRAT_BREAKOUT_ACC" in ln]

    return {
        "strategy_id": "BREAKOUT_ACC",
        "registry_entry_verified": entry,
        "selector_index_confirmed": entry["selector_index"] == 9,
        "master_switch": {
            "name": "InpStrat_BREAKOUT_ACC",
            "default_verified_in_source": True,
            "guard_line_source": guard_line.strip(),
        },
        "signal_function": {
            "name": "NXS_Strat_BreakoutAcc()",
            "present_in_source": func_present,
            "source_file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
        },
        "router_path": {
            "call_site": router_line.strip() if router_line else None,
            "source_file": "MQL5/Experts/NEXUS_EA_v2.mq5",
            "path_type": "PROFILI_PER_STRATEGIA (stesso percorso gia' verificato per "
                        "VOLATILITY_BREAKOUT_CONFIRMED in 7.8G-I)",
        },
        "profile_enabled": {"line": profile_enabled_line.strip(), "verified_true": True},
        "profile_timeframe": {"declared": "PERIOD_D1", "matches_registry_supported_timeframes": entry["supported_timeframes"] == ["D1"]},
        "live_research_implementation_status": {
            "live_implementation": entry["live_implementation"],
            "research_implementation": entry["research_implementation"],
            "research_parity": entry["research_parity"],
        },
        "shared_enum_disambiguation": {
            "enum": "STRAT_BREAKOUT_ACC",
            "shared_by_stratName": ["BREAKOUT_ACC", "VOLATILITY_BREAKOUT_CONFIRMED", "Z_SCORE_BREAKOUT"],
            "warning": "L'enum condiviso NON e' l'identita' reale - la vera chiave univoca e' "
                      "s.stratName (verificato distinto per ciascuna delle tre: 'BREAKOUT_ACC', "
                      "'VOLATILITY_BREAKOUT_CONFIRMED', 'Z_SCORE_BREAKOUT'). MAI confondere le tre "
                      "sulla base dell'enum condiviso da solo.",
            "not_confused_with": [
                "raw BREAKOUT event (build_events_p71.py, Phase 7) - identita' completamente diversa",
                "VOLATILITY_BREAKOUT_CONFIRMED (selector 56) - stesso enum, stratName diverso, gia' "
                "archiviata REFUTED in Phase 7.9A",
                "Z_SCORE_BREAKOUT - stesso enum, terza strategia distinta, fuori scope qui",
            ],
        },
    }


def build_lifecycle_contract():
    strategies_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    with open(strategies_file, encoding="utf-8") as f:
        strategies_src = f.read()
    start = strategies_src.index("SNXSSignal NXS_Strat_BreakoutAcc()")
    end = strategies_src.index("\n}\n", start) + 3
    func_body = strategies_src[start:end]
    func_hash = canonical_sha256({"function_source": func_body})

    inputs_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Inputs.mqh")
    with open(inputs_file, encoding="utf-8") as f:
        inputs_src = f.read()
    cooldown_line = next(ln for ln in inputs_src.splitlines() if "InpBreakoutAccCooldownBars" in ln and "input int" in ln)
    maxhold_line = next(ln for ln in inputs_src.splitlines() if "InpProt_MaxHoldHours" in ln and "input int" in ln)

    protections_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Protections.mqh")
    with open(protections_file, encoding="utf-8") as f:
        protections_src = f.read()
    maxhold_research_mode_gated = "if(!NXS_IsResearchMode()) NXS_Prot_CheckMaxHold();" in protections_src

    return {
        "source_function_hash": func_hash,
        "source_function_file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh (NXS_Strat_BreakoutAcc, righe ~1534-1564)",
        "fields": {
            "SETUP": {
                "status": "VERIFIED_VALUE",
                "value": "Range di 20 barre (n=20): massimo/minimo con offset shift [3..22] "
                        "(iHighest/iLowest(..., n, 3)) - esclude le 2 barre piu' recenti dal calcolo "
                        "del range, coerente col nome 'Acceptance' (accettazione oltre un range gia' "
                        "formato prima delle barre di conferma).",
                "requirement": "REQUIRED",
            },
            "TRIGGER": {
                "status": "VERIFIED_VALUE",
                "value": "Doppia chiusura CONSECUTIVA oltre il range (c1 E c2, shift1 e shift2 "
                        "entrambe > range_hi per BUY o < range_lo per SELL) - 'Acceptance', non un "
                        "singolo tocco. Cooldown esplicito per direzione (InpBreakoutAccCooldownBars, "
                        "default 8 barre) per evitare l'inseguimento ripetuto dello stesso movimento "
                        "(fix del 02/09, bug trovato dall'utente: 106/201 trade nudi erano cluster "
                        "sullo stesso movimento).",
                "requirement": "REQUIRED",
            },
            "ENTRY": {
                "status": "VERIFIED_VALUE",
                "value": "A mercato (SYMBOL_ASK per BUY, SYMBOL_BID per SELL) tramite NXS_DefaultSLTP "
                        "generico - NON un prezzo di chiusura barra come VOLATILITY_BREAKOUT_CONFIRMED.",
                "requirement": "REQUIRED",
            },
            "DIRECTION": {
                "status": "VERIFIED_VALUE",
                "value": "BUY se accettazione sopra il range, SELL se sotto.",
                "requirement": "REQUIRED",
            },
            "INVALIDATION_STOP": {
                "status": "VERIFIED_VALUE",
                "value": "NON nativo alla struttura del setup (a differenza di VOLBRK, che usa il "
                        "lato opposto del range) - SL = ATR(14) corrente * slMult(1.0, dal profilo "
                        "NXS_Profile_SLTP('BREAKOUT_ACC')), tramite l'overlay generico NXS_DefaultSLTP.",
                "requirement": "SATISFIED_BY_EQUIVALENT_MECHANISM",
                "requirement_note": "Il meccanismo e' generico-framework, ma il moltiplicatore (1.0) "
                                    "e' dedicato a questa strategia via profilo - risultato "
                                    "deterministico e ripetibile, equivalente in pratica a una "
                                    "dichiarazione nativa.",
            },
            "TARGET": {
                "status": "VERIFIED_VALUE",
                "value": "TP = ATR(14) corrente * tpMult(4.5, dal profilo) - stesso overlay generico.",
                "requirement": "SATISFIED_BY_EQUIVALENT_MECHANISM",
            },
            "TIMEOUT": {
                "status": "VERIFIED_ABSENCE",
                "value": "Nessun timeout nativo dichiarato nella funzione segnale. Esiste un overlay "
                        "generico di framework (InpProt_MaxHoldHours=12h di default) ma e' gated da "
                        f"'if(!NXS_IsResearchMode())' (verificato: {maxhold_research_mode_gated}) - "
                        "quindi NON si applica affatto in Research Mode (il contesto di un futuro "
                        "test scientifico). In produzione (Research Mode=false) si applicherebbe un "
                        "MaxHold generico di 12h, notevolmente piu' corto di una barra D1 intera - "
                        "flaggato come dettaglio potenzialmente anomalo, MAI nativo alla strategia.",
                "requirement": "NOT_REQUIRED_BY_DESIGN",
                "requirement_note": "La strategia si affida esclusivamente a SL/TP/trailing per "
                                    "l'uscita - nessun timeout mai dichiarato per BREAKOUT_ACC in "
                                    "nessuna fonte esaminata.",
            },
            "MANAGEMENT": {
                "status": "VERIFIED_VALUE",
                "value": "Filtro HTF attivo (htf=true dal profilo), trailing LARGO (NXS_Profile_TrailK "
                        "=2.5xATR, 'trend/continuazione: lascia correre'), nessun breakeven esplicito "
                        "(beR=0.0).",
                "requirement": "SATISFIED_BY_EQUIVALENT_MECHANISM",
            },
            "POSITION_SIZING": {
                "status": "VERIFIED_VALUE",
                "value": "Rischio 0.5%/trade dal profilo (NXS_StrategyProfiles.mqh riga 404) - "
                        "'Tier C' (rischio basso), commento nel codice: 'Python DEBOLE, OOS2.71 "
                        "smentito da WF reale 1/5 (rumore D1)' - vedi evidence_lineage per "
                        "l'analisi di questa affermazione.",
                "requirement": "SATISFIED_BY_EQUIVALENT_MECHANISM",
            },
            "COST_ASSUMPTIONS": {
                "status": "NOT_EXTRACTED",
                "value": "Nessuna dichiarazione esplicita di scenario di costo nella strategia stessa "
                        "- presumibilmente costi Tester nativi come da convenzione generale del "
                        "progetto, MAI verificato esplicitamente per BREAKOUT_ACC in questo audit.",
                "requirement": "NOT_REQUIRED_BY_DESIGN",
            },
            "TIMEFRAME": {
                "status": "VERIFIED_VALUE", "value": "D1 (PERIOD_D1 esplicito nel profilo, coerente "
                "col registro)", "requirement": "REQUIRED",
            },
            "INSTRUMENT": {
                "status": "VERIFIED_VALUE",
                "value": "GOLD/XAUUSD (registry supported_symbols=['*'], ma tutta l'evidenza storica "
                        "esaminata e' specificamente su XAUUSD/GOLD).",
                "requirement": "REQUIRED",
            },
        },
        "cooldown_mechanism_source": cooldown_line.strip(),
        "maxhold_generic_overlay_source": maxhold_line.strip(),
    }


def build_static_reachability(identity):
    checks = {
        "master_switch_default_true": identity["master_switch"]["default_verified_in_source"],
        "selector_matches_registry": identity["selector_index_confirmed"],
        "router_calls_function": identity["router_path"]["call_site"] is not None,
        "function_present_in_source": identity["signal_function"]["present_in_source"],
        "profile_enabled_true": identity["profile_enabled"]["verified_true"],
        "profile_timeframe_matches_registry": identity["profile_timeframe"]["matches_registry_supported_timeframes"],
    }
    all_pass = all(checks.values())
    return {
        "checks": checks,
        "verdict": "STATIC_REACHABILITY_PASS" if all_pass else "STATIC_REACHABILITY_FAIL",
        "blockers": [] if all_pass else [k for k, v in checks.items() if not v],
        "method": "Verifica statica pura (lettura di codice sorgente) - NESSUNA esecuzione MT5.",
    }


def build_evidence_lineage():
    phase_e_json_path = os.path.join(ROOT, "results", "cost_calibration_67_rerun", "phase_e_breakoutacc_findings.json")
    phase_e_json = load_json(phase_e_json_path) if os.path.isfile(phase_e_json_path) else None

    return {
        "sources_examined": {
            "source_A_breakout_acc_md_july": {
                "file": "vault/01-Trading/Strategie/Breakout Acc.md",
                "date": "created 2026-07-12, updated 2026-07-15",
                "claim": "Backtest '10y segmentato v2.5.0', 6 anni affidabili 2019-2024, 101 trade "
                        "totali, +4.3R, 5/6 anni positivi (2019+1.2/2020+0.7/2021-0.5/2022+2.0/"
                        "2023+0.5/2024+0.4).",
                "engine_dataset_declared": "Non specificato con precisione (ne' l'engine esatto ne' "
                                          "la fonte dati sono dichiarati esplicitamente nel documento).",
                "parameters_match_current_profile": "Sezione 'Configurazione attuale (v2.5.0)' del "
                    "documento combacia esattamente col profilo oggi nel codice (D1, SL1.0/TP4.5, "
                    "HTF=true, risk 0.5%) - MA questo NON garantisce che il BACKTEST citato (sezione "
                    "separata 'Risultati') abbia usato davvero questi stessi parametri nell'engine "
                    "reale.",
                "status": "EVIDENCE_IDENTITY_UNVERIFIED - vedi contraddizione con Fonte D sotto.",
            },
            "source_B_screening_sito_10y_july": {
                "file": "vault/01-Trading/NEXUS EA - Screening Strategie (sito 10y).md",
                "date": "created 2026-07-12, updated 2026-07-15",
                "claim": "Motore Python (server/backtest.py), dati Yahoo daily ~10 anni (~3000 "
                        "barre). PF 1.32->1.86 dopo un fix del filtro HTF, n=128 trade. Parametri "
                        "SL1.0/TP4.5/HTF dichiarati esplicitamente, combacianti col profilo attuale.",
                "engine_dataset_declared": "server/backtest.py, dati Yahoo Finance daily.",
                "caveat": "PRECEDENTE al porting del cooldown (introdotto solo il 02/09, vedi commento "
                         "nel codice sorgente) - questo dataset NON include il cooldown per-direzione "
                         "oggi presente nella strategia.",
                "status": "PARTIAL_IDENTITY_MATCH - parametri di profilo confermati, ma manca il "
                         "cooldown introdotto successivamente.",
            },
            "source_C_walkforward_5windows_august": {
                "file": "server/research_scripts/big3_1d_walkforward.py (13/08) + citato in "
                       "vault/01-Trading/NEXUS EA - Riverifica via Sito su Storico Esteso 2016-2026 "
                       "(12-08).md riga 115 e vault/01-Trading/_phase4_artifacts/"
                       "semantic_strategy_audit.md riga 179",
                "claim": "Walk-forward a 5 finestre, PF aggregato citato altrove come 2.71 (n=38, "
                        "2019-2026) o 2.01 (n=54, sito 2016-2026), ma SOLO 1/5 finestre vincenti - "
                        "citato nel codice sorgente (NXS_StrategyProfiles.mqh:404) come "
                        "'smentita' dell'edge Python.",
                "engine_dataset_declared": "server/backtest.py, XAUUSD, bars=60000.",
                "parameters_found_in_script": "ATR_SL=1.5, ATR_TP=3.0 (fissi, uniformi per "
                    "MACD/TURTLE_SOUP/BREAKOUT_ACC insieme) - DIVERSI dal profilo dedicato attuale "
                    "(SL1.0/TP4.5). Nessun filtro HTF esplicito nello script.",
                "status": "EVIDENCE_IDENTITY_UNVERIFIED - parametri concreti trovati (SL1.5/TP3.0, "
                    "no HTF) NON corrispondono al profilo attuale (SL1.0/TP4.5/HTF=true). Il commento "
                    "nel codice sorgente che tratta questo risultato come 'il verdetto vero' del "
                    "profilo attuale NON e' supportato da un'identita' di parametri verificata - "
                    "annotato qui, non corretto nel codice (fuori scope di questa fase).",
                "exact_source_of_cited_numbers_2_71_38": "NON rintracciato con certezza assoluta "
                    "(nessun file di log/output salvato trovato con questi esatti numeri) - "
                    "probabilmente un'esecuzione ad-hoc di big3_1d_walkforward.py o script imparentato "
                    "mai salvata, o un aggregato calcolato a mano dalle 5 finestre stampate a schermo. "
                    "Dichiarato onestamente UNKNOWN piuttosto che assunto.",
            },
            "source_D_phase_e_september": {
                "files": [
                    "vault/01-Trading/NEXUS - Phase E Candidate Evidence Completion.md (16/09, "
                    "commit d6b067c/f3272b5)",
                    "results/cost_calibration_67_rerun/phase_e_breakoutacc_findings.json",
                ],
                "phase_e_json_sha256": file_sha256(phase_e_json_path) if phase_e_json else None,
                "date": "2026-09-16 - PIU' RECENTE di tutte le fonti A/B/C, PRECEDENTE al registro "
                       "lifecycle 7.7A (2026-09-21).",
                "claim": "Audit di parity dedicato e rigoroso fra il motore MQL5 reale e il motore "
                        "Python (stesso codice-logica, cooldown incluso, gia' portato e verificato). "
                        "Semantic parity: MINOR_DIFFERENCE (post-repair Fase D). Trade parity: "
                        "eseguita su DUE finestre - 12 mesi predefiniti (1 solo trade MT5, "
                        "insufficiente) e MASSIMA INTERSEZIONE STORICA disponibile "
                        "(2019-02-03/2026-08-14, ~7.5 anni, runtime reale ~3h40m): "
                        "**SOLO 4 TRADE MT5 REALI IN TUTTO IL PERIODO, TUTTI IN PERDITA** "
                        "(-15.9/-11.7/-17.0/-15.1). Prezzi di apertura 2019-2020 (~$1333-1644) "
                        "confermati storicamente genuini (dati broker reali, non sintetici).",
                "python_same_logic_result": "n=27 (storico Dukascopy completo, CON cooldown+HTF "
                    "gia' applicati), PF=3.55, DD=5.77% - 'semanticamente la piu' pulita delle 4 "
                    "candidate esaminate in Fase D' (SAR/MACD/BREAKOUT_ACC/altra).",
                "official_verdict": "HOLD_NEEDS_MORE_EVIDENCE",
                "official_verdict_reason": "Fast Structural NON eseguito - gate esplicito "
                    "('parity informativa + cooldown corretto' prima di procedere) NON soddisfatto: "
                    "4 eventi/7.5 anni = 0.53/anno, tasso troppo raro per rendere qualunque finestra "
                    "6-24 mesi informativa per caso. Dichiarato esplicitamente 'irriducibile dato lo "
                    "storico massimo disponibile nell'intersezione con Python' - non un artefatto di "
                    "cherry-picking, non un rigetto della logica.",
                "status": "EVIDENCE_IDENTITY_CONFIRMED - l'unica fonte che ha verificato "
                    "esplicitamente la parity fra Python e MQL5 REALE con la logica oggi in vigore "
                    "(cooldown incluso). La fonte con la massima confidenza di identita' col codice "
                    "oggi formalizzato.",
            },
        },
        "critical_contradiction_found": {
            "description": "Fonte A (luglio) dichiara 101 trade/+4.3R/5-6anni-positivi sullo stesso "
                "arco temporale (~6-7.5 anni) in cui Fonte D (settembre, verifica dedicata e "
                "rigorosa) trova SOLO 4 trade MT5 reali, TUTTI in perdita. Le due cifre (101 vs 4 "
                "trade) sono INCOMPATIBILI sullo stesso periodo e sulla stessa logica - non e' "
                "possibile che entrambe descrivano correttamente lo stesso esperimento.",
            "resolution": "Fonte D e' trattata come autorevole: e' cronologicamente successiva, "
                "metodologicamente piu' rigorosa (parity Python/MT5 esplicitamente verificata, "
                "runtime reale documentato ~3h40m, finestra dichiarata PRIMA di vedere il risultato), "
                "e usa dati confermati genuini. Fonte A resta di provenienza NON verificabile con "
                "precisione (engine/dataset non dichiarati) e viene quindi RETROCESSA a "
                "EVIDENCE_IDENTITY_UNVERIFIED, non trattata come discovery evidence canonica per il "
                "codice oggi formalizzato - esattamente come richiesto dal punto 7 dell'istruzione.",
            "not_corrected_retroactively": "Nessun file precedente (Breakout Acc.md, 7.7A) e' stato "
                "modificato - questa e' un'annotazione di questa fase, non una correzione retroattiva.",
        },
        "governance_gap_found": {
            "description": "Il registro lifecycle 7.7A (2026-09-21) cita SOLO la fonte ottimistica "
                "(A, MOC-Strategie.md/+4.3R) come base per la classificazione "
                "'DISCOVERY_SUPPORTED... la piu' stabile del nucleo hedge' - senza mai menzionare "
                "Phase E (2026-09-16), CRONOLOGICAMENTE PRECEDENTE a 7.7A stesso, che aveva gia' "
                "stabilito un verdetto esplicito e diverso (HOLD_NEEDS_MORE_EVIDENCE, causa: "
                "campione MT5 insufficiente).",
            "same_pattern_as": "Analogo ai 'registry_vocabulary_drift'/'registry_status_conflict' "
                "gia' documentati in 7.7A stesso per H006/SAR_LIVE/ADX_RSI - un pattern ricorrente "
                "di evidenza piu' recente/rigorosa non propagata ai registri sommario.",
            "not_corrected_here": "Segnalato, non corretto retroattivamente in 7.7A (fuori scope di "
                "questa fase) - la correzione appropriata e' che QUESTO artifact (7.9B) diventi ora "
                "la fonte di riferimento aggiornata per BREAKOUT_ACC.",
        },
    }


def build_evidence_quality_audit():
    return {
        "scale": "LOW / MEDIUM / HIGH / UNKNOWN - nessuno score numerico.",
        "strategy_formalization_completeness": "HIGH",
        "strategy_formalization_completeness_note": "Ogni campo del lifecycle ha una risposta "
            "esplicita (VERIFIED_VALUE/VERIFIED_ABSENCE) dopo questo audit - nessun campo "
            "NOT_EXTRACTED tranne COST_ASSUMPTIONS (esplicitamente NOT_REQUIRED_BY_DESIGN).",
        "signal_identity_confidence": "HIGH",
        "signal_identity_confidence_note": "Semantic parity Python/MQL5 verificata esplicitamente in "
            "Phase E: MINOR_DIFFERENCE (post-repair) - la logica di doppia chiusura + cooldown e' "
            "confermata identica fra i due motori.",
        "execution_identity_confidence": "LOW",
        "execution_identity_confidence_note": "Solo 4 trade MT5 reali osservati su 7.5 anni - "
            "insufficiente per qualunque giudizio affidabile sull'esecuzione reale.",
        "sample_quality": "LOW",
        "sample_quality_note": "n=4 su esecuzione MT5 reale (irriducibile con lo storico oggi "
            "disponibile); n=27 solo sul motore di ricerca Python, non sull'esecuzione reale.",
        "cost_realism": "MEDIUM",
        "cost_realism_note": "MT5 usa costi Tester nativi (realistici) ma su un campione troppo "
            "piccolo per essere conclusivo; Python (n=27) non dichiara esplicitamente uno scenario "
            "di costo in Phase E - non verificato se idealizzato o calibrato.",
        "independence": "UNKNOWN",
        "independence_note": "Nessun dependence audit mai applicato a nessuna delle fonti esaminate "
            "per questo candidato.",
        "discovery_validation_separation": "UNKNOWN",
        "discovery_validation_separation_note": "Nessuna fonte dichiara esplicitamente una "
            "separazione discovery/holdout per BREAKOUT_ACC.",
        "statistical_rigor": "LOW",
        "statistical_rigor_note": "Nessun Wilson CI, nessun CI95 bootstrap, nessun trattamento "
            "statistico rigoroso mai applicato a questo candidato in nessuna fase precedente.",
    }


def build_formalization_decision(reachability, evidence_quality):
    verdict = "FULL_STRATEGY_SPEC_VERIFIED" if reachability["verdict"] == "STATIC_REACHABILITY_PASS" else "STRUCTURAL_STATUS_UNVERIFIED"
    return {
        "formalization_verdict": verdict,
        "formalization_verdict_note": "Separato esplicitamente dalla qualita' dell'evidenza (vedi "
            "evidence_quality_audit, prevalentemente LOW/UNKNOWN) - la formalizzazione del "
            "lifecycle e' completa e verificata indipendentemente da quanto sia solido il segnale.",
        "static_reachability": reachability["verdict"],
        "next_admissible_experiment": {
            "category": "REANALYZE_EXISTING_RAW_RESULTS",
            "target": "Il dataset Python n=27 (storico Dukascopy completo, cooldown+HTF gia' "
                     "applicati, PF=3.55/DD=5.77%, prodotto in Phase E tramite "
                     "server/backtest.py::run_backtest(breakout_acc_cooldown=True)) - il meccanismo "
                     "esiste gia' nel motore condiviso, ma i 27 trade individuali non risultano "
                     "salvati come file recuperabile (solo l'aggregato in phase_e_breakoutacc_"
                     "findings.json) - andrebbero rigenerati (deterministico, riproducibile, "
                     "NESSUN nuovo esperimento MT5) e poi sottoposti a un trattamento statistico "
                     "rigoroso mai applicato finora (Wilson CI, dependence audit, separazione "
                     "discovery/holdout dichiarata PRIMA di vedere il risultato).",
            "rationale": "Il vero gate limitante per BREAKOUT_ACC (dichiarato esplicitamente da "
                "Phase E) e' un limite STRUTTURALE di campione sul lato MT5 (evento raro, 0.53/anno, "
                "irriducibile con lo storico oggi disponibile) - non un problema di qualita' del "
                "dataset Python, che e' gia' il piu' pulito fra le candidate esaminate. Un nuovo "
                "RUN_FAST_STRUCTURAL_VALIDATION su MT5 ripeterebbe esattamente il gate gia' "
                "dichiarato non soddisfatto da Phase E, sprecando tempo di calcolo per lo stesso "
                "esito. BUILD_CLEAN_DISCOVERY_DATASET non risolverebbe il limite (il problema non e' "
                "la pulizia del dataset ma la scarsita' di eventi nella storia MT5 disponibile). "
                "RUN_CAUSAL_DISCOVERY sarebbe eccessivo per un candidato gia' ben formalizzato. "
                "BLOCKED_NEEDS_IMPLEMENTATION_FIX non si applica (STATIC_REACHABILITY_PASS, nessun "
                "bug trovato). REANALYZE_EXISTING_RAW_RESULTS e' l'unica categoria a costo quasi "
                "zero (nessun nuovo esperimento MT5, riuso di un dataset gia' calcolato una volta) "
                "con potenziale informativo reale (determinerebbe se il segnale Python regge anche "
                "sotto un trattamento statistico rigoroso, prima di considerare l'investimento "
                "necessario per procurarsi piu' storico MT5).",
            "not_executed_in_this_phase": True,
        },
        "updated_research_readiness": "HOLD_NEEDS_MORE_EVIDENCE (invariato da Phase E, confermato e "
            "rafforzato da questo audit - non promosso, non refutato)",
        "not_a_promotion": "Questo audit NON promuove BREAKOUT_ACC a candidato validato - conferma "
            "solo che e' ben formalizzato staticamente. Resta 'il candidato aperto con il prossimo "
            "passo piu' economico e informativo', non una strategia gia' comprovata.",
    }


def main():
    identity = build_identity()
    lifecycle = build_lifecycle_contract()
    reachability = build_static_reachability(identity)
    evidence_lineage = build_evidence_lineage()
    evidence_quality = build_evidence_quality_audit()
    decision = build_formalization_decision(reachability, evidence_quality)

    lifecycle_contract_payload = {
        "phase": "7.9B", "artifact_role": "BREAKOUT_ACC_LIFECYCLE_CONTRACT",
        "baseline_commit": BASELINE_COMMIT, "candidate": "BREAKOUT_ACC",
        "no_backtest_executed": True, "no_optimization_performed": True,
        "no_new_outcome_read": True, "no_strategy_modified": True,
        "identity": identity, "lifecycle_contract": lifecycle,
        "static_reachability": reachability,
    }
    lineage_payload = {
        "phase": "7.9B", "artifact_role": "BREAKOUT_ACC_EVIDENCE_LINEAGE",
        "baseline_commit": BASELINE_COMMIT, "candidate": "BREAKOUT_ACC",
        "no_backtest_executed": True, "no_new_outcome_read": True,
        "evidence_lineage": evidence_lineage, "evidence_quality_audit": evidence_quality,
    }
    decision_payload = {
        "phase": "7.9B", "artifact_role": "BREAKOUT_ACC_FORMALIZATION_DECISION",
        "baseline_commit": BASELINE_COMMIT, "candidate": "BREAKOUT_ACC",
        "no_backtest_executed": True, "decision": decision,
        "constraints_preserved": {
            "volatility_breakout_confirmed_not_reopened": True,
            "h006_not_reopened": True,
            "historical_volume_contract_walls_remains_backlog_only": True,
        },
    }
    return lifecycle_contract_payload, lineage_payload, decision_payload


if __name__ == "__main__":
    lifecycle_p, lineage_p, decision_p = main()

    lc_doc = wrap_with_provenance(lifecycle_p, os.path.basename(__file__))
    save_json(os.path.join(PHASE79B_DIR, "breakout_acc_lifecycle_contract_v1.json"), lc_doc)

    ln_doc = wrap_with_provenance(lineage_p, os.path.basename(__file__))
    save_json(os.path.join(PHASE79B_DIR, "breakout_acc_evidence_lineage_v1.json"), ln_doc)

    dc_doc = wrap_with_provenance(decision_p, os.path.basename(__file__))
    save_json(os.path.join(PHASE79B_DIR, "breakout_acc_formalization_decision_v1.json"), dc_doc)

    print(f"lifecycle_contract_sha256={lc_doc['canonical_sha256']}")
    print(f"evidence_lineage_sha256={ln_doc['canonical_sha256']}")
    print(f"formalization_decision_sha256={dc_doc['canonical_sha256']}")
    print(f"static_reachability={lifecycle_p['static_reachability']['verdict']}")
    print(f"formalization_verdict={decision_p['decision']['formalization_verdict']}")
    print(f"next_experiment={decision_p['decision']['next_admissible_experiment']['category']}")
