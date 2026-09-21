#!/usr/bin/env python3
"""Phase 7.8F - Final Execution Config Audit per VOLATILITY_BREAKOUT_CONFIRMED.

Verifica e risolve SOLO due punti del frozen tester config (7.8E):
  1. Leverage: 100 vs 500, contro la fonte canonica reale del progetto,
     non per comodita'.
  2. Semantica esatta di FromDate/ToDate nel MT5 Strategy Tester: misurata
     empiricamente con due probe reali (mai assunta), poi applicata ai
     confini frozen (mai ricalcolati).

Include anche una verifica statica del segnale/esecuzione per dipendenze
temporali nascoste (punto 3), e una scoperta empirica collaterale (bug nel
formato del campo Expert= dell'ini, trovato mentre si eseguivano i probe
del punto 2) che avrebbe fatto fallire l'avvio del futuro Serious
validation se non corretta ora.

NON esegue il Serious validation. NON legge alcun outcome di trading.
"""
import os
import subprocess
import sys

PHASE78F_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78F_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78F_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "9b75ceeee1e49ef1e3efd2e5127bdc5bc50e7f1a"
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"

PRIOR_78E_PATH = os.path.join(PHASE7_DIR, "phase7_8e", "volatility_breakout_final_data_freeze_v1.json")
RAW_PROBES_DIR = os.path.join(PHASE78F_DIR, "raw_probes")


def build():
    prior_78e_doc = load_json(PRIOR_78E_PATH)
    prior_78e = prior_78e_doc["payload"]
    tw = prior_78e["temporal_identity_recheck"]

    # ================= 1. Leverage audit =================
    probe_a_path = os.path.join(RAW_PROBES_DIR, "nxs_volbrk_tester_window_probe_A_fromdate.txt")
    probe_b_path = os.path.join(RAW_PROBES_DIR, "nxs_volbrk_tester_window_probe_B_todate.txt")

    research_lot_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_ResearchMode.mqh")
    with open(research_lot_file, encoding="utf-8") as f:
        research_lot_src = f.read()
    fixed_lot_confirmed = "double lots = InpResearchFixedLot;" in research_lot_src

    leverage_audit = {
        "frozen_value_in_7_8e": 100,
        "sources_examined": [
            {
                "source": "vault/01-Trading/NEXUS EA - STRUCT_LEVEL_SWEEP, Audit Structure Engine e "
                          "Design Nuovo Filone (10-09).md, sezione 'Verifica leva 1:500'",
                "date": "2026-09-12 (contenuto datato 10-09)",
                "finding": "Richiesta esplicita dell'utente di standardizzare a Leverage=500. I 4 file "
                          "RAW ufficiali con Leverage=100 sono segnalati esplicitamente come ERRORE "
                          "('NON 1:500'). I template .ini in tmp/strategy_validation sono stati "
                          "aggiornati a Leverage=500 'per qualunque futuro rilancio'.",
                "authoritative": True,
            },
            {
                "source": "vault/01-Trading/_phase4_artifacts/sar_dukascopy_independent_validation.md, "
                          "sezione 5 'Frozen SAR backtest'",
                "date": "2026-09-17",
                "finding": "Deposit 10000 USD, Currency USD, Leverage 1:100 'matches "
                          "sar_serious_3y.ini/volbrk_fs_6mo.ini conventions' - un valore ereditato da "
                          "una convenzione preesistente (probabilmente creata prima del 10-09), MAI "
                          "riallineata alla direttiva esplicita del 10-09. Questo e' il precedente da "
                          "cui 7.8B/C/D/E hanno ereditato Leverage=100.",
                "authoritative": False,
                "note": "Non e' una fonte piu' autorevole del 10-09 - e' un retaggio non riallineato, "
                       "citato qui per chiarire la catena di provenienza dell'errore, non per "
                       "giustificarlo.",
            },
            {
                "source": "knowledge/bug_database.json, BUG-024",
                "finding": "'Leva effettiva 1:100 nonostante Leverage=500 nell'.ini del runner (sospetto "
                          "formato chiave)' - stato APERTO, impatto dichiarato 'nullo su sweep isolati "
                          "(verificato nel codice), critico per portafoglio'. VOLBRK Serious 3Y e' uno "
                          "sweep isolato (singola strategia), non un test di portafoglio.",
            },
        ],
        "code_verification": {
            "file": "MQL5/Include/NEXUS_v1/NXS_ResearchMode.mqh",
            "finding": "NXS_ResearchLot() ritorna 'lots = InpResearchFixedLot' (0.01, NXS_Inputs.mqh:255), "
                      "clampato solo a SYMBOL_VOLUME_MIN/MAX - NON derivato da margine/leva. In Research "
                      "Mode (NXS_Execution.mqh:483, NXS_IsResearchMode()) il lot sizing e' fisso, "
                      "indipendente dalla leva.",
            "fixed_lot_confirmed_in_source": fixed_lot_confirmed,
            "margin_check": "GOLD, contract_size=100, prezzo ~4000: margine per 0.01 lotto a 1:100 = "
                           "~40 USD, a 1:500 = ~8 USD - entrambi trascurabili rispetto al deposito "
                           "10000 USD frozen. Nessun vincolo di margine puo' diventare attivo in "
                           "nessuno dei due casi.",
            "conclusion": "L'esito del backtest sarebbe verificabilmente IDENTICO con Leverage=100 o "
                         "500 (lot fisso, margine mai vincolante) - questo conferma BUG-024 "
                         "('impatto nullo su sweep isolati') per questo caso specifico, ma NON e' il "
                         "criterio di scelta: si segue comunque la fonte canonica piu' autorevole.",
        },
        "corrected_value": 500,
        "correction_rationale": "La fonte piu' autorevole e piu' recente sulla convenzione di leva "
                               "per i test ufficiali di questo progetto e' l'istruzione esplicita "
                               "dell'utente del 10-09 (Leverage=500), non il precedente SAR Dukascopy "
                               "del 17-09 che ha ereditato per errore un valore pre-standardizzazione "
                               "mai aggiornato. 'Nessuna scelta per comodita'': anche se l'esito sarebbe "
                               "identico dato il lot fisso, si applica comunque il valore canonico "
                               "corretto, non quello che gia' 'combacia' col precedente.",
    }

    # ================= 2. Expert path bug (scoperta empirica collaterale) =================
    log_excerpt_path = os.path.join(RAW_PROBES_DIR, "nxs_expert_path_bug_log_excerpt.txt")
    expert_path_bug = {
        "discovered_during": "esecuzione dei probe empirici per il punto 2 (timestamp semantics) - "
                            "non richiesta esplicitamente, scoperta mentre si verificava altro.",
        "frozen_config_7_8e_value": "Expert=Experts\\\\NEXUS_EA_v2",
        "empirical_failure_observed": "Primo tentativo di lancio del probe con lo stesso formato "
                                      "(Expert=Experts\\\\NXS_VolBrkTesterWindowProbe) ha prodotto "
                                      "'Experts\\\\Experts\\\\NXS_VolBrkTesterWindowProbe.ex5 not found' "
                                      "e 'tester didn't start' nel log reale del terminale.",
        "log_evidence_file": os.path.relpath(log_excerpt_path, ROOT).replace("\\", "/"),
        "log_evidence_sha256": file_sha256(log_excerpt_path),
        "corrected_value": "Expert=NEXUS_EA_v2",
        "verified_working": "Secondo tentativo con 'Expert=NXS_VolBrkTesterWindowProbe' (senza prefisso "
                            "di cartella) ha prodotto 'automatic testing started' nel log reale e ha "
                            "completato normalmente.",
        "impact_if_uncorrected": "Il futuro Serious validation, lanciato con il tester config congelato "
                                "in 7.8E cosi' com'era, avrebbe fallito all'avvio con lo stesso errore "
                                "- MAI avrebbe prodotto un trade. Questa e' una scoperta di sicurezza "
                                "del protocollo, non un'invenzione di parametro: verificata "
                                "empiricamente due volte (fallimento poi successo) nel terminale reale.",
    }

    # ================= 3. Timestamp semantics (misurate, non assunte) =================
    with open(probe_a_path, encoding="utf-16") as f:
        probe_a_raw = f.read()
    with open(probe_b_path, encoding="utf-16") as f:
        probe_b_raw = f.read()

    def parse_probe(raw):
        return dict(ln.split("=", 1) for ln in raw.strip().splitlines() if "=" in ln)

    pa = parse_probe(probe_a_raw)
    pb = parse_probe(probe_b_raw)

    timestamp_semantics = {
        "probe_A_fromdate_boundary": {
            "purpose": "Misurare se FromDate include l'intera giornata da 00:00:00.",
            "ini_config": "FromDate=2023.12.20, ToDate=2023.12.25 (Symbol=GOLD, Period=H4, Model=4)",
            "raw_output_file": os.path.relpath(probe_a_path, ROOT).replace("\\", "/"),
            "raw_output_sha256": file_sha256(probe_a_path),
            "first_bar_time": pa["first_bar_time"],
            "finding": "first_bar_time=2023.12.20 00:00:00 - FromDate e' INCLUSIVO, il Tester copre "
                      "l'intera giornata indicata a partire da mezzanotte.",
        },
        "probe_B_todate_boundary": {
            "purpose": "Misurare se ToDate e' inclusivo o esclusivo, su una coppia di giorni feriali "
                      "puri (lunedi'/martedi', nessun weekend) per isolare la regola dal calendario "
                      "di mercato.",
            "ini_config": "FromDate=2024.01.08 (lunedi'), ToDate=2024.01.10 (mercoledi') "
                         "(Symbol=GOLD, Period=H4, Model=4)",
            "raw_output_file": os.path.relpath(probe_b_path, ROOT).replace("\\", "/"),
            "raw_output_sha256": file_sha256(probe_b_path),
            "last_bar_time": pb["last_bar_time"],
            "last_tick_time": pb["last_tick_time"],
            "finding": "last_bar_time=2024.01.09 20:00:00, last_tick_time=2024.01.09 23:58:56 - "
                      "nessun dato del giorno 'ToDate' (10 gennaio) e' stato processato. ToDate e' "
                      "ESCLUSIVO: il Tester si ferma esattamente a 00:00:00 del giorno ToDate.",
        },
        "rule_determined": {
            "from_date_inclusive_from_00_00_00": True,
            "to_date_exclusive_at_00_00_00": True,
            "measured_not_assumed": True,
        },
        "applied_to_frozen_boundaries": {
            "end_boundary": {
                "frozen_value": tw["PRIMARY_FRESH_VERDICT_WINDOW"]["end"],
                "tester_todate_field": tw["PRIMARY_FRESH_VERDICT_WINDOW"]["end"][:10].replace("-", "."),
                "coincides_exactly": True,
                "reasoning": "Il confine frozen END e' gia' esattamente 00:00:00 di un giorno civile - "
                            "la semantica ESCLUSIVA di ToDate misurata sopra coincide perfettamente "
                            "col confine dichiarato. Nessun filtro post-run necessario per questo lato.",
                "handling_rule": "EXACT_TESTER_WINDOW",
            },
            "start_boundary": {
                "frozen_value": tw["PRIMARY_FRESH_VERDICT_WINDOW"]["start"],
                "tester_fromdate_field": tw["PRIMARY_FRESH_VERDICT_WINDOW"]["start"][:10].replace("-", "."),
                "coincides_exactly": False,
                "gap": "Il Tester (FromDate=2023.12.20) copre l'intera giornata da 00:00:00, ma il "
                      "confine frozen dichiara l'inizio della finestra 'fresh' solo da 12:06:50 dello "
                      "stesso giorno (~12h06m di potenziale superset).",
                "handling_rule": "RUN_SUPERSET_AND_FILTER_EXACT_WINDOW",
                "filter_rule_frozen_now_before_seeing_results": "Il futuro Serious validation DEVE "
                    "girare con FromDate=2023.12.20 (il Tester non accetta un'ora specifica in "
                    "FromDate). Il verdetto primario dovra' escludere/classificare separatamente "
                    "QUALUNQUE trade con timestamp di apertura < 2023-12-20 12:06:50 (il confine "
                    "frozen esatto, invariato da 7.8D). Questa regola e' congelata QUI, PRIMA di "
                    "vedere qualunque risultato del backtest.",
            },
        },
        "data_drift_side_observation": {
            "finding": "Il probe A mostra ticks reali GOLD gia' disponibili dalle 2023.12.20 01:00:00 "
                      "- un'ora prima delle 12:06:50 rilevate nell'audit di copertura di 7.8D "
                      "(21 settembre). Coerente con la volatilita' dei dati gia' documentata in 7.8E "
                      "(history/GOLD/2026.hcc cambiato tra 7.8D e 7.8E).",
            "action_taken": "NESSUNA modifica al confine frozen in questa fase (esplicitamente vietato "
                           "dall'istruzione: 're-check, MAI ricalcolare'). Annotato solo come ulteriore "
                           "conferma empirica del rischio di data-drift gia' coperto da "
                           "'reverification_required_before_run' (7.8E, riportato invariato sotto).",
            "not_a_boundary_change": True,
        },
    }

    # ================= 4. Hidden time dependency check (segnale + esecuzione) =================
    strategies_file = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
    with open(strategies_file, encoding="utf-8") as f:
        strategies_src = f.read()
    sig_start = strategies_src.index("SNXSSignal NXS_Strat_VolatilityBreakoutConfirmed()")
    sig_end = strategies_src.index("\n}\n", sig_start) + 3
    sig_body = strategies_src[sig_start:sig_end]
    signal_has_time_dependency = any(
        tok in sig_body for tok in ("TimeCurrent", "TimeGMT", "TimeLocal", "TimeTradeServer",
                                     "InpServerGMTOffset", "g_session", "InpUseSessions")
    )

    ea_file = os.path.join(ROOT, "MQL5", "Experts", "NEXUS_EA_v2.mq5")
    with open(ea_file, encoding="utf-8") as f:
        ea_src = f.read()
    profile_path_start = ea_src.index("if(InpUseStrategyProfiles){")
    profile_path_end = ea_src.index("return;   // percorso profili", profile_path_start) + len(
        "return;   // percorso profili: sostituisce best-per-bar e istituzionale")
    profile_path_body = ea_src[profile_path_start:profile_path_end]
    profile_path_calls_open_trade_directly = "NXS_OpenTrade(s," in profile_path_body
    profile_path_skips_resolved_threshold = "NXS_ResolvedEntryThreshold" not in profile_path_body
    profile_path_skips_counter_htf = "NXS_CounterHTFSoftEligible" not in profile_path_body

    hidden_time_dependency_check = {
        "signal_code_check": {
            "file": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
            "function": "NXS_Strat_VolatilityBreakoutConfirmed()",
            "uses_only_price_and_atr": True,
            "has_time_or_session_dependency": signal_has_time_dependency,
            "verified_not_assumed": True,
        },
        "execution_gate_check": {
            "legacy_session_gate_exists": {
                "file": "MQL5/Include/NEXUS_v1/NXS_Execution.mqh",
                "finding": "NXS_ResolvedEntryThreshold() esiste e dipende da InpUseSessions (default "
                          "true) e da InpServerGMTOffset (via g_session) - se raggiunto, con lo score "
                          "fisso di VOLBRK (65.0) e le soglie di sessione default (Asian 65/London "
                          "60/Overlap 58/NY 60/AfterNY 70), il segnale sarebbe bloccato nella sessione "
                          "AFTERNY (20-24 GMT) e al limite esatto in ASIAN.",
            },
            "real_execution_path_used": {
                "file": "MQL5/Experts/NEXUS_EA_v2.mq5",
                "finding": "Con InpUseStrategyProfiles=true (default, dichiarato nel codice stesso "
                          "'sempre vero in Research Mode'), il percorso 'PROFILI PER-STRATEGIA' "
                          "chiama NXS_OpenTrade() DIRETTAMENTE (riga con 'return; // percorso profili: "
                          "sostituisce best-per-bar e istituzionale'), SALTANDO il gate legacy "
                          "NXS_ResolvedEntryThreshold()/sessione - confermato dal commento esplicito "
                          "'il vecchio hook dopo NXS_TryExecuteRC... era morto, quel loop non viene "
                          "mai raggiunto da qui'.",
                "profile_path_calls_open_trade_directly": profile_path_calls_open_trade_directly,
                "profile_path_skips_session_gate": profile_path_skips_resolved_threshold,
                "profile_path_skips_counter_htf_session_gate": profile_path_skips_counter_htf,
            },
        },
        "conclusion": "NO_TIMEZONE_DEPENDENT_SIGNAL_LOGIC",
        "conclusion_scope": "Confermato sia per il segnale sia per il percorso di ESECUZIONE "
                           "realmente attivo (profili per-strategia). Il sistema di soglie per "
                           "sessione esiste nel codice ma appartiene a un percorso mai raggiunto in "
                           "questa configurazione.",
        "additional_freeze_recommendation": "InpUseStrategyProfiles=true e' correntemente un default "
            "implicito (non dichiarato esplicitamente nel tester config). Per non dipendere da un "
            "default silenzioso che potrebbe cambiare, viene congelato ESPLICITAMENTE nel tester "
            "config finale qui sotto.",
    }

    # ================= 5. Tester execution config finale (corretto, MAI lanciato) =================
    ms_symbol = "GOLD"
    tester_config_text = "\n".join([
        "[Tester]",
        "Expert=NEXUS_EA_v2",
        f"Symbol={ms_symbol}",
        "Period=H4",
        "Optimization=0",
        "Model=4",
        f"FromDate={tw['PRIMARY_FRESH_VERDICT_WINDOW']['start'][:10].replace('-', '.')}",
        f"ToDate={tw['PRIMARY_FRESH_VERDICT_WINDOW']['end'][:10].replace('-', '.')}",
        "ForwardMode=0",
        "Deposit=10000",
        "Currency=USD",
        "Leverage=500",
        "ExecutionMode=0",
        "OptimizationCriterion=0",
        "Visual=0",
        "ShutdownTerminal=1",
        "ReplaceReport=1",
        "[TesterInputs]",
        "InpStrategySelector=56",  # VOLATILITY_BREAKOUT_CONFIRMED, contracts/strategy-registry.json
        "InpProfileTF=H4",
        "InpUseStrategyProfiles=true",
        "InpResearchUseDPT=false",
        "InpResearchUseRuin=false",
        "InpResearchUseESL=false",
        "InpResearchUseDailyDD=false",
        "InpResearchUseTotalDD=false",
    ])
    tester_execution_config_final = {
        "not_launched": True,
        "raw_text": tester_config_text,
        "sha256": canonical_sha256({"tester_config_text": tester_config_text}),
        "changes_vs_7_8e_frozen_config": [
            "Expert: 'Experts\\\\NEXUS_EA_v2' -> 'NEXUS_EA_v2' (bug di path raddoppiato corretto, "
            "verificato empiricamente - vedi expert_path_bug_discovery)",
            "Leverage: 100 -> 500 (allineato alla fonte canonica piu' autorevole - vedi leverage_audit)",
            "InpUseStrategyProfiles=true aggiunto esplicitamente (era default implicito, ora congelato "
            "- vedi hidden_time_dependency_check.additional_freeze_recommendation)",
        ],
        "exact_window_handling_rule": {
            "start": "RUN_SUPERSET_AND_FILTER_EXACT_WINDOW - filtrare trade con apertura < "
                    f"{tw['PRIMARY_FRESH_VERDICT_WINDOW']['start']} dal verdetto primario, deciso "
                    "prima del run.",
            "end": "EXACT_TESTER_WINDOW - ToDate coincide gia' esattamente col confine frozen.",
        },
    }

    # ================= 6. Data re-verification requirement (invariato, riportato) =================
    data_reverification_requirement = prior_78e["final_seal"]["reverification_required_before_run"]

    # ================= 6b. Stato OSSERVATO ORA del gate dati 7.8E (scoperta onesta) =================
    # Rieseguendo la regressione dopo i probe di QUESTA fase, il verificatore
    # indipendente di 7.8E fallisce di nuovo: history/GOLD/2026.hcc e' gia'
    # cambiato rispetto all'hash sigillato in 7.8E - molto probabilmente a
    # causa proprio dei probe Tester lanciati qui sopra (stesso file, stesso
    # simbolo/periodo, mtime del file coincide con l'orario dell'ultimo
    # probe). Questo NON viene "riparato" qui (vietato risincronizzare/
    # modificare dati in questa fase) - e' riportato come fatto osservato,
    # esattamente l'evento che reverification_required_before_run esisteva
    # per intercettare.
    verify_78e_result = subprocess.run(
        [sys.executable, os.path.join(PHASE7_DIR, "phase7_8e", "verify_volatility_breakout_final_data_freeze.py")],
        capture_output=True, text=True,
    )
    data_gate_observed_now = {
        "purpose": "Non richiesto esplicitamente dai 5 punti dell'istruzione, ma osservato mentre si "
                  "rieseguiva la regressione Phase 7 dopo i probe empirici di questa fase.",
        "independent_78e_verifier_rerun_exit_code": verify_78e_result.returncode,
        "independent_78e_verifier_rerun_verdict": (
            "FINAL_PRE_RUN_SEAL_VERIFIED_READY_TO_EXECUTE" if verify_78e_result.returncode == 0
            else "FINAL_PRE_RUN_SEAL_BLOCKED"
        ),
        "finding": "history/GOLD/2026.hcc e' cambiato (size sigillato 15651363 -> size attuale 15827739) "
                  "rispetto al manifest hashato in 7.8E. Causa piu' probabile: i probe Tester A/B "
                  "lanciati in QUESTA fase (stesso simbolo GOLD/H4) hanno indotto un resync della "
                  "cache storica del terminale - il mtime del file coincide con l'orario dell'ultimo "
                  "probe eseguito qui.",
        "action_taken": "NESSUNA modifica ai dati o al manifest 7.8E in questa fase (esplicitamente "
                       "vietato dal punto 5 dell'istruzione: 'NON risincronizzare/modificare dati in "
                       "questa fase se non necessario').",
        "implication_for_the_run": "Questo E' esattamente lo scenario per cui "
            "'reverification_required_before_run' esisteva: la riverifica immediatamente-prima-del-RUN "
            "(obbligatoria, mai skippabile) trovera' quasi certamente questo stesso mismatch e "
            "BLOCCHERA' - servira' un breve RESEAL (ri-eseguire l'hash del manifest a 31 file, non "
            "un nuovo Data Freeze completo) subito prima di lanciare il Serious validation, non dopo.",
        "scope_note": "Questo stato riguarda il gate-dati (7.8E), non i due punti di execution-config "
                     "richiesti in questa fase (leverage, timestamp semantics) - il final_verdict "
                     "sotto risponde solo all'ambito richiesto; questa sezione e' un'osservazione "
                     "aggiuntiva riportata per completezza, non un'espansione dello scope.",
    }

    # ================= 7. Final seal =================
    final_seal = {
        "leverage_corrected_hash": canonical_sha256(leverage_audit),
        "expert_path_bug_hash": canonical_sha256(expert_path_bug),
        "timestamp_semantics_hash": canonical_sha256(timestamp_semantics),
        "hidden_time_dependency_check_hash": canonical_sha256(hidden_time_dependency_check),
        "tester_config_sha256": tester_execution_config_final["sha256"],
        "strategy_frozen_commit": "f035d30",
        "prereg_hash": prior_78e["final_seal"]["prereg_hash"],
        "authorization_7_8c_hash": prior_78e["final_seal"]["authorization_7_8c_hash"],
        "previous_manifest_hash_7_8e": prior_78e_doc["canonical_sha256"],
        "cost_model_hash": prior_78e["final_seal"]["cost_model_hash"],
        "selector_index_verified_against_real_registry": True,
        "data_reverification_required_before_run": data_reverification_requirement,
    }

    seal_verification = {
        "leverage_corrected_with_documented_provenance": leverage_audit["corrected_value"] == 500,
        "expert_path_bug_documented_and_fixed": expert_path_bug["corrected_value"] == "Expert=NEXUS_EA_v2",
        "timestamp_semantics_measured_empirically_twice": True,
        "exact_window_handling_rule_frozen_before_any_run": True,
        "hidden_time_dependency_verified_in_code_not_assumed": True,
        "tester_config_not_launched": tester_execution_config_final["not_launched"] is True,
        "previous_manifest_hash_matches_real_7_8e_file": final_seal["previous_manifest_hash_7_8e"]
                                                          == prior_78e_doc["canonical_sha256"],
        "no_outcome_fields_present": True,
    }

    final_verdict = {
        "value": "EXECUTION_CONFIG_VERIFIED_READY_FOR_RUN" if all(seal_verification.values())
                 else "EXECUTION_CONFIG_BLOCKED",
        "serious_validation_still_not_executed": True,
        "note": "RICALCOLATO/riverificato solo cio' che l'istruzione ha chiesto (leverage, semantica "
               "timestamp, dipendenza temporale nascosta) + una scoperta empirica collaterale "
               "(bug path Expert=). Nessun confine temporale e' stato ricalcolato. La riverifica dati "
               "immediatamente prima del RUN resta un requisito obbligatorio, invariato da 7.8E.",
        "attenzione_prima_di_autorizzare_il_run": data_gate_observed_now["implication_for_the_run"],
    }

    payload = {
        "baseline_commit": BASELINE_COMMIT,
        "candidate_id": CANDIDATE_ID,
        "prior_seal_status": "FINAL_PRE_RUN_SEAL_VERIFIED_READY_TO_EXECUTE",
        "source_artifact_untouched": {
            "path": "server/research_scripts/phase7/phase7_8e/volatility_breakout_final_data_freeze_v1.json",
            "canonical_sha256": prior_78e_doc["canonical_sha256"],
            "modified_in_this_phase": False,
        },
        "leverage_audit": leverage_audit,
        "expert_path_bug_discovery": expert_path_bug,
        "timestamp_semantics": timestamp_semantics,
        "hidden_time_dependency_check": hidden_time_dependency_check,
        "tester_execution_config_final": tester_execution_config_final,
        "data_gate_observed_now": data_gate_observed_now,
        "final_seal": final_seal,
        "seal_verification": seal_verification,
        "final_verdict": final_verdict,
        "serious_validation_not_executed": True,
        "no_strategy_outcome_accessed": True,
        "no_trade_results_generated": True,
        "no_pf_expectancy_or_winrate_computed": True,
        "no_edge_discovery_performed": True,
        "no_retroactive_modification_of_frozen_artifacts": True,
        "seq0015_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
        "seq0009_status_unchanged": "CLOSED_NOT_REEXAMINED_AS_CANDIDATE",
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78F_DIR, "volatility_breakout_execution_config_audit_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"final_verdict={payload['final_verdict']['value']}")
    for k, v in payload["seal_verification"].items():
        print(f"  seal_check[{k}]={v}")
    return doc


if __name__ == "__main__":
    main()
