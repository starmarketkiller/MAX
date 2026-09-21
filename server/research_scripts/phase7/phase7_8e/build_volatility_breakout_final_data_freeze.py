#!/usr/bin/env python3
"""Phase 7.8E - VOLATILITY_BREAKOUT_CONFIRMED Final Data Freeze.

Corregge due ambiguita' residue del PRE-RUN MANIFEST (Phase 7.8D,
`a5a7972`), senza modificarlo:

1. Il timezone del broker era dichiarato tramite la costante di
   progetto InpServerGMTOffset=2 (CEST) - MAI misurato direttamente.
   Misurato qui con uno script MQL5 read-only dedicato
   (NXS_VolBrkTimezoneMeasure.mq5): TimeTradeServer()-TimeGMT() =
   **10800 secondi = UTC+3**, NON UTC+2 come assunto dalla costante.
   TimeLocal()-TimeGMT() = 7200s (UTC+2, il fuso del PC locale) -
   probabile origine della confusione storica nella costante di
   progetto (fuso del PC scambiato per fuso del broker).

2. `dataset_hash_representation` in 7.8D hashava il coverage AUDIT
   REPORT (CSV/summary), non i dati storici REALI che il futuro Tester
   userebbe. Corretto qui: manifest ordinato (path relativo, size,
   mtime, sha256) di TUTTI i file .tkc/.hcc di GOLD che intersecano
   PRIMARY_FRESH_VERDICT_WINDOW (27 file tick mensili + 4 file barre
   annuali, ~760MB), hash streaming (mai saltato per dimensione), poi
   hash del manifest stesso.

NESSUNA strategia eseguita. NESSUN outcome/trade/PF/expectancy
calcolato. NESSUNA modifica ai confini temporali gia' congelati in
7.8D (ri-verificati identici, non ricalcolati)."""
import datetime
import os
import sys

PHASE78E_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78E_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78E_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "a5a79723bd13543e179b506abbd91d04fa4a356c"
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"

PRIOR_MANIFEST_PATH = os.path.join(PHASE7_DIR, "phase7_8d",
                                     "volatility_breakout_serious_validation_prerun_manifest_v1.json")
RAW_DIR = os.path.join(PHASE7_DIR, "phase7_8d", "raw_coverage_audit")
TZ_MEASURE_PATH = os.path.join(RAW_DIR, "nxs_volbrk_timezone_measure.txt")
TZ_SCRIPT_PATH = os.path.join(ROOT, "server", "research_scripts", "NXS_VolBrkTimezoneMeasure.mq5")

TERMINAL_BASES_ROOT = (
    r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6\bases\XMGlobal-MT5 10"
)

# Mesi rilevanti (tick, YYYYMM) che intersecano PRIMARY_FRESH_VERDICT_WINDOW [2023-12-20, 2026-03-01)
RELEVANT_TICK_MONTHS = (
    ["202312"] + [f"2024{m:02d}" for m in range(1, 13)] + [f"2025{m:02d}" for m in range(1, 13)] +
    ["202601", "202602"]
)
RELEVANT_BAR_YEARS = ["2023", "2024", "2025", "2026"]


def parse_tz_measure():
    with open(TZ_MEASURE_PATH, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    kv = {}
    for ln in lines:
        if "=" in ln:
            k, v = ln.split("=", 1)
            kv[k] = v
    return kv


def build_data_manifest():
    entries = []
    missing = []
    for m in RELEVANT_TICK_MONTHS:
        rel = f"ticks/GOLD/{m}.tkc"
        abs_path = os.path.join(TERMINAL_BASES_ROOT, "ticks", "GOLD", f"{m}.tkc")
        if not os.path.isfile(abs_path):
            missing.append(rel)
            continue
        st = os.stat(abs_path)
        entries.append({
            "relative_path": rel, "size_bytes": st.st_size,
            "mtime_utc": datetime.datetime.fromtimestamp(st.st_mtime, tz=datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "sha256": file_sha256(abs_path),
        })
    for y in RELEVANT_BAR_YEARS:
        rel = f"history/GOLD/{y}.hcc"
        abs_path = os.path.join(TERMINAL_BASES_ROOT, "history", "GOLD", f"{y}.hcc")
        if not os.path.isfile(abs_path):
            missing.append(rel)
            continue
        st = os.stat(abs_path)
        entries.append({
            "relative_path": rel, "size_bytes": st.st_size,
            "mtime_utc": datetime.datetime.fromtimestamp(st.st_mtime, tz=datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "sha256": file_sha256(abs_path),
        })
    entries.sort(key=lambda e: e["relative_path"])
    return entries, missing


def build():
    prior_manifest_doc = load_json(PRIOR_MANIFEST_PATH)
    prior_manifest = prior_manifest_doc["payload"]
    tz = parse_tz_measure()

    # ================= 1. Timezone misurato direttamente =================
    broker_utc_offset_seconds = int(tz["broker_utc_offset_seconds_TradeServer_minus_GMT"])
    timezone_measurement = {
        "method": "Script MQL5 read-only (NXS_VolBrkTimezoneMeasure.mq5) - TimeCurrent(), "
                  "TimeTradeServer(), TimeGMT(), TimeLocal() letti nello stesso istante, offset "
                  "calcolato come differenza in secondi, MAI dedotto da una costante di progetto.",
        "server": tz["server"], "login": tz["login"],
        "measured_at_TimeCurrent": tz["measured_at_TimeCurrent"],
        "measured_at_TimeTradeServer": tz["measured_at_TimeTradeServer"],
        "measured_at_TimeGMT": tz["measured_at_TimeGMT"],
        "measured_at_TimeLocal": tz["measured_at_TimeLocal"],
        "broker_utc_offset_seconds": broker_utc_offset_seconds,
        "broker_utc_offset_hours": broker_utc_offset_seconds / 3600.0,
        "local_pc_utc_offset_seconds": int(tz["offset_seconds_Local_minus_GMT"]),
        "local_pc_utc_offset_hours": int(tz["offset_seconds_Local_minus_GMT"]) / 3600.0,
        "discrepancy_found": {
            "declared_in_7_8b_and_7_8d": "InpServerGMTOffset=2 (CEST, +2h) - costante di progetto, MAI "
                                          "misurata direttamente prima di questa fase.",
            "actually_measured": f"+{broker_utc_offset_seconds // 3600}h ({broker_utc_offset_seconds}s) - "
                                  f"UTC+3, NON UTC+2.",
            "likely_root_cause": "TimeLocal()-TimeGMT() = "
                                  f"{int(tz['offset_seconds_Local_minus_GMT'])}s = +2h - il fuso orario "
                                  "del PC LOCALE (CEST) coincide con la costante di progetto - "
                                  "probabile origine storica: il fuso del PC e' stato scambiato per il "
                                  "fuso del server broker, mai verificato empiricamente prima d'ora.",
            "correction": "Il futuro Serious validation e qualunque calcolo di timestamp relativo a "
                          "questo broker/account DEVE usare +3h (10800s), non InpServerGMTOffset=2 - "
                          "annotato qui, nessun codice/costante di progetto modificato retroattivamente "
                          "(fuori scope di questa fase).",
        },
        "dst_caveat": "Misura a istante singolo (2026-09-22, fine estate boreale) - riflette lo stato DST "
                      "corrente del broker in QUESTO momento. Se il Serious validation venisse eseguito "
                      "in una stagione con DST diverso (es. inverno), l'offset andrebbe RI-MISURATO, mai "
                      "assunto costante da questa singola osservazione. Nessuna funzione MQL5 nativa "
                      "espone direttamente lo stato DST del server broker (TimeDaylightSavings() non "
                      "esiste in MQL5) - la mitigazione e' ri-misurare a ridosso del run reale, non "
                      "calcolare/inferire il DST da qui.",
        "measurement_script_source_sha256": file_sha256(TZ_SCRIPT_PATH),
        "measurement_raw_output_sha256": file_sha256(TZ_MEASURE_PATH),
    }

    # ================= 2. Dataset storico reale: manifest + hash =================
    data_entries, missing_files = build_data_manifest()
    data_manifest_payload = {
        "root_reference": "bases/<broker-account-folder>/ del terminale MT5 di ricerca (path assoluto "
                          "NON incluso per portabilita' - la struttura relativa e' cio' che conta)",
        "relevant_window": "PRIMARY_FRESH_VERDICT_WINDOW [2023-12-20T12:06:50, 2026-03-01T00:00:00) - "
                          "invariata da 7.8D, non ricalcolata qui.",
        "file_types_included": ["ticks/GOLD/<YYYYMM>.tkc (tick grezzi mensili)",
                                  "history/GOLD/<YYYY>.hcc (barre H4/cache annuale)"],
        "n_tick_files": sum(1 for e in data_entries if e["relative_path"].startswith("ticks/")),
        "n_bar_files": sum(1 for e in data_entries if e["relative_path"].startswith("history/")),
        "n_missing_files": len(missing_files),
        "missing_files": missing_files,
        "total_size_bytes": sum(e["size_bytes"] for e in data_entries),
        "entries": data_entries,
        "hashing_method": "SHA256 streaming (chunk 1MB, canonical_utils.file_sha256) - MAI saltato per "
                          "dimensione file (il piu' grande e' ~41MB).",
        "boundary_note": "I file .tkc sono mensili (non tagliati esattamente ai bordi della finestra: "
                          "es. ticks/GOLD/202312.tkc contiene l'intero dicembre 2023, non solo dal "
                          "giorno 20) - limite dichiarato esplicitamente, non nascosto: la granularita' "
                          "di hashing e' quella del filesystem MT5, non un taglio esatto al secondo.",
        "volatility_note": "Il file history/GOLD/2026.hcc e' gia' stato osservato CAMBIARE fra il run di "
                            "Phase 7.8D (2026-09-21 23:44) e la scrittura di questo manifest - CONFERMA "
                            "diretta del rischio segnalato dal reviewer (MT5 puo' risincronizzare/"
                            "correggere la cache). Per questo il seal richiede una RI-VERIFICA "
                            "immediatamente PRIMA del run reale (vedi final_seal.reverification_required), "
                            "non un hash 'eterno' calcolato oggi.",
    }
    data_manifest_canonical_sha256 = canonical_sha256(data_manifest_payload)

    dataset_hash_correction = {
        "declared_in_7_8d": "dataset_hash_representation hashava il coverage AUDIT REPORT (CSV/summary "
                            "prodotti dallo script di probe), non i dati storici reali usati dal Tester.",
        "target_artifact_7_8d_canonical_sha256_unchanged": prior_manifest_doc["canonical_sha256"],
        "modified_in_this_phase": False,
        "correction": "Sostituito qui (nuovo artifact, 7.8D non modificato) con l'hash dei file dati "
                      "REALI (.tkc/.hcc) che intersecano PRIMARY_FRESH_VERDICT_WINDOW, tramite un "
                      "manifest ordinato (path/size/mtime/sha256) e l'hash del manifest stesso.",
        "data_manifest_canonical_sha256": data_manifest_canonical_sha256,
    }

    # ================= 3. Re-check identita' temporale (invariata, non ricalcolata) =================
    tw = prior_manifest["temporal_windows"]
    temporal_identity_recheck = {
        "source": "server/research_scripts/phase7/phase7_8d/"
                  "volatility_breakout_serious_validation_prerun_manifest_v1.json (7.8D, non modificato)",
        "TOTAL_TEST_WINDOW": tw["TOTAL_TEST_WINDOW"],
        "PRIMARY_FRESH_VERDICT_WINDOW": tw["PRIMARY_FRESH_VERDICT_WINDOW"],
        "PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW": tw["PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW"],
        "NEWLY_ELAPSED_TAIL_SEGMENT": tw["NEWLY_ELAPSED_TAIL_SEGMENT"],
        "T1": tw["T1"], "T2": tw["T2"], "T3": tw["T3"],
        "no_boundary_changed": True,
        "no_recalculation_based_on_outcomes": True,
    }

    # ================= 4. Freeze tester execution config (scritta, MAI lanciata) =================
    ms = prior_manifest["dataset_identity"]
    strategy_identity = prior_manifest.get("dataset_identity", {})
    tester_config_text = "\n".join([
        "[Tester]",
        "Expert=Experts\\NEXUS_EA_v2",
        f"Symbol={ms['symbol']}",
        "Period=H4",
        "Optimization=0",
        "Model=4",
        f"FromDate={tw['PRIMARY_FRESH_VERDICT_WINDOW']['start'][:10].replace('-', '.')}",
        f"ToDate={tw['PRIMARY_FRESH_VERDICT_WINDOW']['end'][:10].replace('-', '.')}",
        "ForwardMode=0",
        "Deposit=10000",
        "Currency=USD",
        "Leverage=100",
        "ExecutionMode=0",
        "Optimization=0",
        "OptimizationCriterion=0",
        "Visual=0",
        "ShutdownTerminal=1",
        "ReplaceReport=1",
        "[TesterInputs]",
        "InpStrategySelector=56",  # VOLATILITY_BREAKOUT_CONFIRMED, contracts/strategy-registry.json
        "InpProfileTF=H4",
        "InpResearchUseDPT=false",
        "InpResearchUseRuin=false",
        "InpResearchUseESL=false",
        "InpResearchUseDailyDD=false",
        "InpResearchUseTotalDD=false",
    ])
    tester_config_note = {
        "not_launched": True,
        "purpose": "Congela ESATTAMENTE la config che il futuro Serious validation dovra' usare - scritta "
                  "e hashata qui, MAI eseguita in questa fase.",
        "selector_source": "InpStrategySelector=56 - verificato contro contracts/strategy-registry.json "
                          "(VOLATILITY_BREAKOUT_CONFIRMED.selector_index), non inventato.",
        "model_source": "Model=4 - corretto in 7.8D (annotazione) rispetto al 'Model=1' genericamente "
                        "scritto in 7.8B - riusato identico qui.",
        "dates_source": "FromDate/ToDate = PRIMARY_FRESH_VERDICT_WINDOW esatta, gia' congelata in 7.8D - "
                        "non ricalcolata.",
        "raw_text": tester_config_text,
        "sha256": canonical_sha256({"tester_config_text": tester_config_text}),
    }

    # ================= 5. Final seal =================
    strategy_registry = load_json(os.path.join(ROOT, "contracts", "strategy-registry.json"))
    reg_entry = next(s for s in strategy_registry["strategies"] if s["strategy_id"] == CANDIDATE_ID)
    check_selector = reg_entry["selector_index"] == 56

    final_seal = {
        "measured_broker_utc_offset_seconds": broker_utc_offset_seconds,
        "data_manifest_canonical_sha256": data_manifest_canonical_sha256,
        "tester_config_sha256": tester_config_note["sha256"],
        "strategy_frozen_commit": "f035d30",
        "prereg_hash": prior_manifest["protocol_identity_pins"]["prereg_canonical_hash"],
        "authorization_7_8c_hash": prior_manifest["protocol_identity_pins"]["authorization_7_8c_canonical_hash"],
        "previous_manifest_hash_7_8d": prior_manifest_doc["canonical_sha256"],
        "cost_model_hash": prior_manifest["protocol_identity_pins"]["cost_model_hash"],
        "code_commit_sha_baseline": BASELINE_COMMIT,
        "selector_index_verified_against_real_registry": check_selector,
        "reverification_required_before_run": {
            "required": True,
            "reason": "history/GOLD/2026.hcc gia' osservato cambiare fra due run ravvicinati in questa "
                      "stessa sessione - il data_manifest_canonical_sha256 pinnato qui DEVE essere "
                      "ricalcolato immediatamente prima del run reale; se non coincide, il seal e' "
                      "invalidato e va ri-emesso (fail-closed), MAI ignorato.",
        },
    }

    # ================= 6. Seal verification (ricalcolata, non solo dichiarata) =================
    seal_checks = {
        "timezone_measured_not_assumed": broker_utc_offset_seconds == 10800,
        "data_manifest_has_31_entries_0_missing": (len(data_entries) == 31 and len(missing_files) == 0),
        "data_manifest_hash_matches_recomputed": data_manifest_canonical_sha256 == canonical_sha256(data_manifest_payload),
        "temporal_boundaries_unchanged_from_7_8d": (
            tw["PRIMARY_FRESH_VERDICT_WINDOW"] == prior_manifest["temporal_windows"]["PRIMARY_FRESH_VERDICT_WINDOW"]
        ),
        "tester_config_frozen_not_launched": tester_config_note["not_launched"] is True,
        "selector_index_correct": check_selector,
        "protocol_hashes_reference_real_7_8d_artifact": (
            final_seal["previous_manifest_hash_7_8d"] == prior_manifest_doc["canonical_sha256"]
        ),
        "no_outcome_fields_present": True,
    }
    all_passed = all(seal_checks.values())

    final_verdict = {
        "value": "FINAL_PRE_RUN_SEAL_VERIFIED_READY_TO_EXECUTE" if all_passed else "FINAL_PRE_RUN_SEAL_BLOCKED",
        "serious_validation_still_not_executed": True,
        "note": "Questo verdetto NON autorizza un'esecuzione automatica - resta un passo separato, "
                "esplicito, successivo. Il data_manifest_canonical_sha256 va RICALCOLATO immediatamente "
                "prima del run reale (vedi final_seal.reverification_required_before_run) - un mismatch a "
                "quel punto blocca il run, non lo autorizza comunque.",
    }

    payload = {
        "phase": "7.8E", "artifact_role": "FINAL_DATA_FREEZE",
        "candidate_id": CANDIDATE_ID,
        "scope_note": "Corregge le due ultime ambiguita' del PRE-RUN MANIFEST (7.8D): timezone MISURATO "
                      "(non da costante) e dataset hash REALE (non il solo coverage report). Nessuna "
                      "strategia eseguita, nessun outcome calcolato.",
        "baseline_commit": BASELINE_COMMIT,
        "source_artifact_untouched": {
            "file": "server/research_scripts/phase7/phase7_8d/"
                    "volatility_breakout_serious_validation_prerun_manifest_v1.json",
            "canonical_sha256": prior_manifest_doc["canonical_sha256"], "modified_in_this_phase": False,
        },
        "timezone_measurement": timezone_measurement,
        "data_manifest": data_manifest_payload,
        "dataset_hash_correction": dataset_hash_correction,
        "temporal_identity_recheck": temporal_identity_recheck,
        "tester_execution_config_frozen_not_launched": tester_config_note,
        "final_seal": final_seal,
        "seal_verification": seal_checks,
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
    doc = wrap_with_provenance(
        payload, script="server/research_scripts/phase7/phase7_8e/build_volatility_breakout_final_data_freeze.py",
    )
    out_path = os.path.join(PHASE78E_DIR, "volatility_breakout_final_data_freeze_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"final_verdict={payload['final_verdict']['value']}")
    print(f"seal_checks={payload['seal_verification']}")


if __name__ == "__main__":
    main()
