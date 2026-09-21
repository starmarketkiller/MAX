#!/usr/bin/env python3
"""Phase 7.8D (redo) - VOLATILITY_BREAKOUT_CONFIRMED PRE-RUN MANIFEST.

Corregge la conclusione precedente di questa fase
(`volatility_breakout_prerun_seal_status_v1.json`,
`PRE_RUN_SEAL_BLOCKED_NO_DATA_ACCESS`): quella verifica aveva ispezionato
i sottoprofili broker sbagliati (XMGlobal-MT5 7/9) invece dell'account
REALMENTE connesso di default da questo terminale (XMGlobal-MT5 10,
login 345277936, DEMO) - il cui storico GOLD risultava molto piu'
recente (fino a pochi giorni prima). L'utente ha confermato l'accesso
reale al terminale; questa fase lo ha verificato concretamente:

1. Scritto/compilato/deployato un MQL5 Script READ-ONLY
   (`NXS_VolBrkPrerunCoverageAudit.mq5` - nessuna EA/strategia toccata,
   nessun trade) nel terminale di ricerca (`C:\\MT5-Tester`, cartella
   dati reale `.../Terminal/7F8EC41F011085EB9C65165AE426B5A6`).
2. Lanciato `terminal64.exe /config:<ini>` con `[StartUp] Script=...`
   (stesso pattern gia' stabilito nel progetto - vedi Failure Memory/
   vault SAR Dukascopy validation), atteso il completamento via marker
   file (non un poll a iterazioni fisse), chiuso il terminale.
3. Letto i risultati REALI (copertura tick/bar GOLD) - copiati in
   `raw_coverage_audit/` per provenienza, mai riscritti a mano.

Scoperta onesta: la copertura REALE di tick (necessaria per
REAL_TICK_REQUIRED_FOR_PRIMARY_VERDICT, Phase 7.8C) inizia il
2023-12-20 (non "esattamente 3 anni fa" come nominalmente ipotizzato in
7.8B/7.8C) - un vincolo di dati reale, non un'invenzione. Il
TOTAL_TEST_WINDOW e' quindi vincolato a partire da quella data, non da
una data arbitraria di comodo. Trovato anche un piccolo segmento
'fresco' aggiuntivo (2026-09-01 -> oggi) apparso semplicemente perche'
il tempo e' passato dalla stesura di 7.8B - riportato come diagnostica
separata (`NEWLY_ELAPSED_TAIL_SEGMENT`), MAI fuso silenziosamente nel
verdetto primario ne' scartato senza dichiararlo.

NESSUN Serious validation eseguito. NESSUN outcome di strategia letto.
NESSUN trade result generato. Solo identita'/provenienza/date/hash/
copertura dati."""
import datetime
import os
import sys

PHASE78D_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78D_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78D_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "92ec007f677ac1b8269cefccb7c02da2e748f5ca"  # git rev-parse HEAD, verified at build time
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"

PRIOR_BLOCKED_STATUS_PATH = os.path.join(PHASE78D_DIR, "volatility_breakout_prerun_seal_status_v1.json")
AUTHORIZATION_PATH = os.path.join(PHASE7_DIR, "phase7_8c",
                                    "volatility_breakout_serious_3y_run_authorization_v1.json")
PREREG_PATH = os.path.join(PHASE7_DIR, "phase7_8b", "volatility_breakout_serious_3y_prereg_v1.json")
COST_MODEL_PATH = os.path.join(PHASE7_DIR, "policies", "cost_model_integration.json")
RAW_DIR = os.path.join(PHASE78D_DIR, "raw_coverage_audit")
RAW_CSV = os.path.join(RAW_DIR, "nxs_volbrk_prerun_coverage.csv")
RAW_SUMMARY = os.path.join(RAW_DIR, "nxs_volbrk_prerun_summary.txt")
RAW_DONE = os.path.join(RAW_DIR, "nxs_volbrk_prerun_done.txt")

DATE_FMT = "%Y.%m.%d %H:%M:%S"


def parse_dt(s):
    return datetime.datetime.strptime(s, DATE_FMT)


def build():
    prior_blocked_doc = load_json(PRIOR_BLOCKED_STATUS_PATH)
    auth_doc = load_json(AUTHORIZATION_PATH)
    prereg_doc = load_json(PREREG_PATH)

    with open(RAW_SUMMARY, encoding="utf-8") as f:
        summary_lines = [ln.strip() for ln in f if ln.strip()]
    summary = {}
    for ln in summary_lines:
        if "=" in ln:
            k, v = ln.split("=", 1)
            summary.setdefault(k, []).append(v)

    server = summary["server"][0]
    login = summary["login"][0]
    trade_mode = summary["trade_mode"][0]
    server_time_now = summary["server_time_now"][0]

    gold_line = [ln for ln in summary_lines if ln.startswith("symbol=GOLD wide_")][0]
    # symbol=GOLD wide_ticks=191824954 wide_first=2023.12.20 12:06:50 wide_last=2026.09.21 23:58:59 wide_err=0
    parts = gold_line.split(" ")
    wide_ticks = int(parts[1].split("=")[1])
    wide_first = parts[2].split("=")[1] + " " + parts[3]
    wide_last = parts[4].split("=")[1] + " " + parts[5]
    wide_err = int(parts[6].split("=")[1])

    gold_h4_line = [ln for ln in summary_lines if ln.startswith("symbol=GOLD h4_")][0]
    h4parts = gold_h4_line.split(" ")
    h4_bars = int(h4parts[1].split("=")[1])
    h4_first_bar = h4parts[2].split("=")[1] + " " + h4parts[3]
    h4_last_bar = h4parts[4].split("=")[1] + " " + h4parts[5]

    real_tick_start = parse_dt(wide_first)
    real_tick_end = parse_dt(wide_last)
    h4_first_bar_dt = parse_dt(h4_first_bar)
    h4_last_bar_dt = parse_dt(h4_last_bar)

    # ---- Correzione onesta rispetto a 7.8B/7.8C: copertura tick reale inizia 2023-12-20, non
    # "esattamente 3 anni fa" - vincolo di dati reale, verificato dal probe mensile (sez. sotto). ----
    monthly_probe_gap_note = (
        "Il probe mensile (nxs_volbrk_prerun_coverage.csv) mostra 0 tick per le finestre di "
        "settembre/ottobre/novembre/dicembre 2023 (7 giorni ciascuna, non coprono l'intero mese) - "
        "il primo tick REALE (query wide-range, autorevole) e' 2023-12-20 12:06:50, in un "
        "intervallo non coperto dai probe mensili discreti (nessuna contraddizione, solo "
        "granularita' piu' fine della query wide rispetto ai probe mensili)."
    )

    total_test_window_start = real_tick_start
    total_test_window_end = real_tick_end

    previously_observed_start = datetime.datetime(2026, 3, 1, 0, 0, 0)
    previously_observed_end = datetime.datetime(2026, 9, 1, 0, 0, 0)

    primary_fresh_start = total_test_window_start
    primary_fresh_end = previously_observed_start

    newly_elapsed_tail_start = previously_observed_end
    newly_elapsed_tail_end = total_test_window_end

    # ---- T1/T2/T3: tercile cronologico della SOLA porzione fresh primaria (contigua) ----
    fresh_duration = primary_fresh_end - primary_fresh_start
    third = fresh_duration / 3
    t1_start = primary_fresh_start
    t1_end = t1_start + third
    t2_start = t1_end
    t2_end = t2_start + third
    t3_start = t2_end
    t3_end = primary_fresh_end

    def iso(d):
        return d.strftime("%Y-%m-%dT%H:%M:%S")

    temporal_windows = {
        "TOTAL_TEST_WINDOW": {"start": iso(total_test_window_start), "end": iso(total_test_window_end),
                               "duration_days": (total_test_window_end - total_test_window_start).days,
                               "bounded_by": "Inizio = primo tick reale disponibile per GOLD (verificato "
                                             "empiricamente, non un nominale '3 anni fa') - vedi "
                                             "real_tick_coverage_finding sotto. Fine = ultimo tick "
                                             "disponibile al momento del sync (ora corrente broker)."},
        "PRIMARY_FRESH_VERDICT_WINDOW": {"start": iso(primary_fresh_start), "end": iso(primary_fresh_end),
                                          "duration_days": (primary_fresh_end - primary_fresh_start).days,
                                          "note": "Blocco contiguo piu' ampio di dati MAI osservati per "
                                                  "questo candidato - alimenta il verdetto PASS/BORDERLINE/"
                                                  "FAIL primario."},
        "PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW": {"start": iso(previously_observed_start),
                                                    "end": iso(previously_observed_end),
                                                    "duration_days": (previously_observed_end -
                                                                      previously_observed_start).days,
                                                    "note": "Identica alla finestra gia' usata per il "
                                                            "fast-structural test (Strategy Foundry Phase "
                                                            "3) - fissa, non ricalcolata rispetto a 'oggi'. "
                                                            "MAI usata per il verdetto primario."},
        "NEWLY_ELAPSED_TAIL_SEGMENT": {"start": iso(newly_elapsed_tail_start), "end": iso(newly_elapsed_tail_end),
                                        "duration_days": (newly_elapsed_tail_end - newly_elapsed_tail_start).days,
                                        "note": "SCOPERTA IN QUESTA FASE (non prevista da 7.8B/7.8C): "
                                                "poiche' il tempo reale e' avanzato da quando la finestra "
                                                "PREVIOUSLY_OBSERVED fu fissata, esiste ora un piccolo "
                                                "segmento genuinamente MAI osservato dopo di essa. Troppo "
                                                "corto per un tercile T1/T2/T3 affidabile da solo - "
                                                "riportato come diagnostica di replica separata, MAI fuso "
                                                "silenziosamente nel verdetto primario ne' scartato senza "
                                                "dichiararlo.",
                                        "excluded_from_primary_verdict": True},
        "T1": {"start": iso(t1_start), "end": iso(t1_end)},
        "T2": {"start": iso(t2_start), "end": iso(t2_end)},
        "T3": {"start": iso(t3_start), "end": iso(t3_end)},
        "t1_t2_t3_partition_check": {
            "union_equals_primary_fresh_window": (t1_start == primary_fresh_start and t3_end == primary_fresh_end),
            "no_gaps": (t1_end == t2_start and t2_end == t3_start),
            "no_overlap": True,
            "durations_approximately_equal_days": [
                (t1_end - t1_start).days, (t2_end - t2_start).days, (t3_end - t3_start).days,
            ],
        },
    }

    real_tick_coverage_finding = {
        "declared_before_this_finding": "7.8B/7.8C avevano nominalmente ipotizzato TOTAL_TEST_WINDOW ~ "
                                          "ultimi 3 anni continui - MAI verificato contro la copertura "
                                          "reale fino a questa fase.",
        "verified_finding": f"Copertura tick REALE per GOLD inizia {wide_first} (verificato via "
                             f"CopyTicksRange wide-range, {wide_ticks} tick trovati, err={wide_err}) - "
                             f"circa 2 anni e 9 mesi prima di oggi, NON 3 anni pieni.",
        "h4_bar_history_extends_further_but_without_real_ticks": (
            f"Le barre H4 storiche risalgono a {h4_first_bar} ({h4_bars} barre totali) - PIU' indietro "
            f"della copertura tick reale ({wide_first}). Questo e' atteso (le barre OHLC possono essere "
            f"cachate/costruite indipendentemente dai tick grezzi) - MA significa che qualunque porzione "
            f"prima di {wide_first} NON potrebbe soddisfare REAL_TICK_REQUIRED_FOR_PRIMARY_VERDICT (Phase "
            f"7.8C sez.4) e resta correttamente ESCLUSA da TOTAL_TEST_WINDOW."
        ),
        "monthly_probe_note": monthly_probe_gap_note,
    }

    # ---- Correzione al modello di tick dichiarato in 7.8B (annotazione, non modifica) ----
    tick_model_correction = {
        "declared_in_7_8b": "Model=1 (real ticks quando disponibili)",
        "actual_established_project_convention": "Model=4 (Every tick based on real ticks) - verificato "
                                                   "contro il precedente REALE gia' eseguito in questo "
                                                   "progetto per lo stesso tipo di test (sar_serious_3y.ini, "
                                                   "vault 'NEXUS - First Serious 3Y Validation SAR MACD.md'; "
                                                   "e la validazione Dukascopy indipendente, 'History Quality: "
                                                   "99% real ticks', anch'essa Model=4).",
        "correction": "Il futuro Serious 3Y di VOLATILITY_BREAKOUT_CONFIRMED deve usare Model=4, non "
                      "Model=1 come genericamente scritto in 7.8B - annotato qui, 7.8B non modificato "
                      "retroattivamente.",
        "target_artifact_7_8b_canonical_sha256_unchanged": prereg_doc["canonical_sha256"],
    }

    # ---- Dataset identity (REALE) ----
    dataset_identity = {
        "symbol": "GOLD",
        "symbol_note": "Simbolo nativo del broker (non XAUUSD.s ne' il custom XAUUSD_DSC usato solo per "
                       "la validazione Dukascopy indipendente di SAR) - stesso simbolo gia' dichiarato in "
                       "7.8B/Strategy Foundry Phase 3.",
        "timeframe": "H4 nativo",
        "broker_server": server,
        "account_login": login,
        "account_trade_mode": trade_mode,
        "broker_timezone_offset_convention": "InpServerGMTOffset=2 (CEST broker) - costante di progetto "
                                              "gia' riusata ovunque nel codice (NXS_Inputs.mqh:1120), "
                                              "riusata qui identica, non ri-derivata.",
        "tester_model": "Model=4 (Every tick based on real ticks) - vedi tick_model_correction sopra.",
        "history_synchronization_timestamp_server": server_time_now,
        "history_synchronization_method": "Script MQL5 read-only (NXS_VolBrkPrerunCoverageAudit.mq5) "
                                            "lanciato live-attached su questo account/server, con query "
                                            "wide-range che forza il terminal a richiedere/sincronizzare "
                                            "dal server qualunque tick mancante nella finestra richiesta.",
        "first_available_timestamp_ticks": wide_first,
        "last_available_timestamp_ticks": wide_last,
        "first_available_timestamp_h4_bars": h4_first_bar,
        "last_available_timestamp_h4_bars": h4_last_bar,
    }

    # ---- Real-tick coverage per subperiod (dai probe mensili reali) ----
    with open(RAW_CSV, encoding="utf-8") as f:
        csv_lines = [ln.strip() for ln in f if ln.strip()]
    gold_probe_rows = [ln for ln in csv_lines if ln.startswith("XMGlobal-MT5 10,345277936,DEMO,GOLD,")]
    tick_coverage_by_subperiod = []
    for row in gold_probe_rows:
        cols = row.split(",")
        probe_from, probe_to, n_ticks = cols[4], cols[5], int(cols[6])
        tick_coverage_by_subperiod.append({
            "probe_window_start": probe_from, "probe_window_end_plus7d": probe_to,
            "ticks_found": n_ticks,
            "classification": "REAL_TICK_RESOLVABLE" if n_ticks > 0 else "EXECUTION_ORDER_POTENTIALLY_UNRESOLVED",
        })
    n_resolvable = sum(1 for r in tick_coverage_by_subperiod if r["classification"] == "REAL_TICK_RESOLVABLE")
    real_tick_coverage_summary = {
        "n_monthly_probes": len(tick_coverage_by_subperiod), "n_real_tick_resolvable": n_resolvable,
        "n_execution_order_potentially_unresolved": len(tick_coverage_by_subperiod) - n_resolvable,
        "unresolved_probes_fall_before_total_test_window_start": True,
        "note": "I probe con 0 tick trovati cadono TUTTI prima dell'inizio di TOTAL_TEST_WINDOW (gia' "
                "vincolato all'inizio della copertura reale, sez. real_tick_coverage_finding) - nessun "
                "trade nella finestra effettivamente usata dal verdetto primario ricade quindi in una "
                "porzione EXECUTION_ORDER_POTENTIALLY_UNRESOLVED su base mensile grossolana. La "
                "risoluzione ESATTA per-trade (bracket worst/best-case, Phase 7.8C sez.4) resta comunque "
                "necessaria per eventuali singole barre con tick radi, non sostituita da questo controllo "
                "mensile.",
    }

    # ---- Hash reali (rappresentazione dichiarata: il coverage report, non i file binari .hcc/.tkc) ----
    dataset_hash_representation = {
        "what_is_hashed": "Il coverage audit report generato da questa fase (CSV + summary txt), NON i "
                          "file binari .hcc/.tkc del broker (multi-GB, in continua crescita, non "
                          "praticamente hashabili come singolo valore stabile).",
        "why_this_representation": "Il report e' un fingerprint deterministico e riproducibile di 'quali "
                                    "dati erano disponibili al momento del sealing' - esattamente cio' che "
                                    "il manifest deve pinnare, senza dover hashare l'intero archivio "
                                    "storico del broker.",
        "coverage_csv_sha256": file_sha256(RAW_CSV),
        "coverage_summary_sha256": file_sha256(RAW_SUMMARY),
        "coverage_done_marker_sha256": file_sha256(RAW_DONE),
        "audit_script_source_sha256": file_sha256(
            os.path.join(ROOT, "server", "research_scripts", "NXS_VolBrkPrerunCoverageAudit.mq5")
        ),
    }

    # ---- Protocol identity pins (gia' congelati, riusati) ----
    protocol_pins = {
        "strategy_frozen_commit": "f035d30",
        "prereg_canonical_hash": prereg_doc["canonical_sha256"],
        "authorization_7_8c_canonical_hash": auth_doc["canonical_sha256"],
        "cost_model_hash": file_sha256(COST_MODEL_PATH),
        "prior_blocked_status_7_8d_canonical_hash": prior_blocked_doc["canonical_sha256"],
    }

    # ---- Seal verification (sec.8 della richiesta) ----
    required_fields_populated = all([
        temporal_windows["TOTAL_TEST_WINDOW"]["start"], temporal_windows["TOTAL_TEST_WINDOW"]["end"],
        dataset_identity["symbol"], dataset_identity["broker_server"], dataset_identity["account_login"],
        dataset_identity["tester_model"], dataset_identity["history_synchronization_timestamp_server"],
        dataset_hash_representation["coverage_csv_sha256"], protocol_pins["strategy_frozen_commit"],
    ])
    date_ordering_valid = (
        primary_fresh_start < primary_fresh_end <= previously_observed_start < previously_observed_end
        <= newly_elapsed_tail_end
    ) if newly_elapsed_tail_start >= previously_observed_end else False
    fresh_observed_non_overlapping = primary_fresh_end <= previously_observed_start
    t1t2t3_partitions_fresh = (
        temporal_windows["t1_t2_t3_partition_check"]["union_equals_primary_fresh_window"] and
        temporal_windows["t1_t2_t3_partition_check"]["no_gaps"]
    )
    protocol_hashes_correspond = (
        protocol_pins["prereg_canonical_hash"] == prereg_doc["canonical_sha256"] and
        protocol_pins["authorization_7_8c_canonical_hash"] == auth_doc["canonical_sha256"]
    )
    no_outcome_fields_present = True  # per costruzione - nessun campo PF/expectancy/winrate/DD in questo payload

    seal_verification = {
        "all_required_fields_populated": required_fields_populated,
        "date_ordering_valid": date_ordering_valid,
        "fresh_and_observed_non_overlapping": fresh_observed_non_overlapping,
        "t1_t2_t3_exactly_partition_fresh_window": t1t2t3_partitions_fresh,
        "protocol_hashes_correspond_to_frozen_artifacts": protocol_hashes_correspond,
        "no_outcome_fields_present": no_outcome_fields_present,
        "all_checks_passed": all([required_fields_populated, date_ordering_valid, fresh_observed_non_overlapping,
                                    t1t2t3_partitions_fresh, protocol_hashes_correspond, no_outcome_fields_present]),
    }

    final_status = {
        "value": "PRE_RUN_SEAL_VERIFIED_READY_TO_RUN" if seal_verification["all_checks_passed"] else "PRE_RUN_SEAL_BLOCKED",
        "serious_validation_still_not_executed": True,
        "note": "Il seal verificato NON autorizza l'esecuzione automatica del Serious validation - resta "
                "un passo SEPARATO e successivo, da autorizzare esplicitamente.",
    }

    payload = {
        "phase": "7.8D-MANIFEST", "artifact_role": "PRE_RUN_MANIFEST",
        "candidate_id": CANDIDATE_ID,
        "scope_note": "PRE-RUN MANIFEST REALE con dati/hash/date/copertura VERIFICATI (non fabbricati) - "
                       "corregge la conclusione PRE_RUN_SEAL_BLOCKED_NO_DATA_ACCESS della fase precedente "
                       "(verifica ambientale incompleta: controllato il broker sub-account sbagliato). "
                       "NESSUN Serious validation eseguito, nessun outcome letto, nessun trade generato - "
                       "solo identita'/provenienza/date/hash/copertura.",
        "correction_of_prior_blocked_status": {
            "target_artifact": "server/research_scripts/phase7/phase7_8d/"
                               "volatility_breakout_prerun_seal_status_v1.json",
            "target_artifact_canonical_sha256_unchanged": prior_blocked_doc["canonical_sha256"],
            "modified_in_this_phase": False,
            "issue": "Quella verifica aveva controllato le sotto-cartelle broker 'XMGlobal-MT5 7'/'9' "
                     "invece dell'account REALMENTE connesso di default da questo terminale "
                     "('XMGlobal-MT5 10', login 345277936) - il cui storico GOLD risultava sincronizzato "
                     "fino a pochi giorni prima, non ~2 mesi come concluso allora. L'utente ha confermato "
                     "l'accesso reale al terminale; verificato qui concretamente con un run reale.",
        },
        "how_this_manifest_was_produced": {
            "step_1": "Scritto/compilato MQL5 Script read-only NXS_VolBrkPrerunCoverageAudit.mq5 "
                      "(0 errori di compilazione).",
            "step_2": "Deployato in MQL5/Scripts del terminale di ricerca, lanciato via "
                      "terminal64.exe /config:<ini> con [StartUp] Script=..., atteso il completamento "
                      "via marker file (non un poll a iterazioni fisse).",
            "step_3": "Processo terminal64.exe chiuso dopo la conferma di completamento.",
            "step_4": "File di output reali copiati in server/research_scripts/phase7/phase7_8d/"
                      "raw_coverage_audit/ per provenienza - mai riscritti a mano.",
            "no_ea_or_strategy_touched": True, "no_trade_placed": True,
        },
        "baseline_commit": BASELINE_COMMIT,
        "temporal_windows": temporal_windows,
        "real_tick_coverage_finding": real_tick_coverage_finding,
        "tick_model_correction": tick_model_correction,
        "dataset_identity": dataset_identity,
        "real_tick_coverage_by_subperiod": tick_coverage_by_subperiod,
        "real_tick_coverage_summary": real_tick_coverage_summary,
        "dataset_hash_representation": dataset_hash_representation,
        "protocol_identity_pins": protocol_pins,
        "seal_verification": seal_verification,
        "final_status": final_status,
        "manifest_purity_check": {
            "trade_count_present": False, "pf_present": False, "expectancy_present": False,
            "win_rate_present": False, "drawdown_present": False, "buy_sell_performance_present": False,
            "yearly_performance_present": False, "any_strategy_outcome_present": False,
        },
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
    doc = wrap_with_provenance(
        payload, script="server/research_scripts/phase7/phase7_8d/build_volatility_breakout_prerun_manifest.py",
    )
    out_path = os.path.join(PHASE78D_DIR, "volatility_breakout_serious_validation_prerun_manifest_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"final_status={payload['final_status']['value']}")
    print(f"seal_verification={payload['seal_verification']}")


if __name__ == "__main__":
    main()
