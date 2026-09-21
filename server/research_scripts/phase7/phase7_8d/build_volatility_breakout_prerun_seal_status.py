#!/usr/bin/env python3
"""Phase 7.8D - PRE-RUN DATA SEAL (status + temporal segmentation fix).

Due compiti distinti:

1. Correzione della segmentazione temporale (Phase 7.8C, `a0fe99e`):
   PRIMARY_FRESH_VERDICT_WINDOW (~2.5 anni) NON garantisce tre anni
   solari completi e comparabili - usare implicitamente "Year 1/2/3"
   introdurrebbe segmenti di durata diseguale (es. 2 anni pieni + un
   pezzo), rendendo il criterio '2 dei 3 segmenti non negativi'
   dipendente dalla posizione delle date nel calendario. Corretto qui
   (annotazione, 7.8C non modificato) con una regola DETERMINISTICA:
   split cronologico in 3 blocchi contigui di durata il piu' possibile
   uguale (T1/T2/T3), MAI 'anni solari' nominali. Nessun outcome letto
   per definire questa regola - e' puramente strutturale.

2. Verifica ONESTA dell'accesso ai dati storici reali richiesti dal
   PRE-RUN MANIFEST (Phase 7.8C sez.5). Questa sessione di ricerca e'
   un processo Bash/PowerShell in background, SENZA terminale MT5 in
   esecuzione e SENZA alcuno strumento per pilotare l'apertura di MT5,
   la sincronizzazione dello storico o l'esecuzione dello Strategy
   Tester. Verificato concretamente (non assunto):
   - nessun processo terminal64/terminal in esecuzione (Get-Process)
   - LocalBridge/nexus_local_worker.py (l'UNICO ponte automation
     esistente nel progetto verso MT5) ha una whitelist di azioni che
     NON include alcuna sincronizzazione storico ne' esecuzione di
     backtest (solo ping/compile_ea/restart_mt5/deploy_files/
     open_chart/apply_template)
   - una cache storica GOLD PREESISTENTE esiste su disco (piu'
     terminali), ma e' STALE (ultimo file 2026.hcc modificato
     2026-07-21, ~2 mesi prima della data odierna 2026-09-21) e la sua
     provenienza/coerenza con un vero run di Strategy Tester non e'
     verificabile da questa sessione - usarla equivarrebbe a inventare
     un 'sync' che non e' mai avvenuto in questa fase.

Conclusione: PRE_RUN_SEAL_BLOCKED_NO_DATA_ACCESS - NESSUNA data/hash/
tick-coverage fabbricata. NESSUN Serious validation eseguito. NESSUN
outcome di strategia letto o calcolato."""
import os
import subprocess
import sys

PHASE78D_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78D_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78D_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "a0fe99eb88ff8b21d26bacbaae69003c49eeec32"
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"

AUTHORIZATION_PATH = os.path.join(PHASE7_DIR, "phase7_8c",
                                    "volatility_breakout_serious_3y_run_authorization_v1.json")
LOCAL_BRIDGE_WORKER_PATH = os.path.join(ROOT, "LocalBridge", "nexus_local_worker.py")

TODAY_DECLARED = "2026-09-21"  # data odierna dichiarata dall'ambiente di questa sessione (system prompt)


def check_mt5_process_running():
    """Verifica REALE (non assunta) - nessun terminal64/terminal.exe in esecuzione al momento del
    build. Fatto puntuale (potrebbe cambiare in futuro), riportato con il metodo di verifica
    esplicito, mai affermato senza controllo."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-Process -Name 'terminal64','terminal' -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=15,
        )
        running_pids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return len(running_pids) > 0, running_pids
    except Exception as e:
        return None, str(e)


def check_local_bridge_whitelist():
    """Verifica REALE contro il file sorgente - quali azioni il ponte di automation esistente
    supporta davvero, non assunte dalla sola descrizione nel README."""
    with open(LOCAL_BRIDGE_WORKER_PATH, encoding="utf-8") as f:
        src = f.read()
    import re
    handlers = sorted(set(re.findall(r"def handle_(\w+)\(", src)))
    data_sync_or_backtest_action_present = any(
        kw in src.lower() for kw in ("sync_history", "run_backtest", "run_tester", "start_tester",
                                       "history_sync", "download_history")
    )
    return handlers, data_sync_or_backtest_action_present


def check_existing_gold_history_cache():
    """Elenca i file di cache storica GOLD REALMENTE presenti su disco (percorsi/dimensioni/mtime
    verificati), SENZA usarli per fabbricare un 'sync' - solo come evidenza del perche' non
    soddisfano il requisito di sincronizzazione fresca al momento del run."""
    candidate_dirs = [
        r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6\bases"
        r"\XMGlobal-MT5 7\history\GOLD",
        r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\bases"
        r"\XMGlobal-MT5 9\history\GOLD",
    ]
    found = []
    for d in candidate_dirs:
        if os.path.isdir(d):
            entries = sorted(e for e in os.listdir(d) if e.endswith(".hcc"))
            if entries:
                latest = entries[-1]
                latest_path = os.path.join(d, latest)
                mtime = os.path.getmtime(latest_path)
                import datetime
                mtime_str = datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ")
                found.append({
                    "directory": d, "n_year_files": len(entries),
                    "latest_file": latest, "latest_file_mtime_utc": mtime_str,
                })
    return found


def build():
    auth_doc = load_json(AUTHORIZATION_PATH)

    # ================= 1. Temporal segmentation correction (annotazione, 7.8C non modificato) =================
    temporal_segmentation_correction = {
        "target_artifact": "server/research_scripts/phase7/phase7_8c/"
                           "volatility_breakout_serious_3y_run_authorization_v1.json",
        "target_artifact_canonical_sha256_unchanged": auth_doc["canonical_sha256"],
        "modified_in_this_phase": False,
        "issue": "7.8C usa implicitamente 'Year 1/2/3' per il criterio di stabilita' temporale "
                 "(ereditato dal precedente SAR/MACD Serious 3Y, che aveva una finestra di 3 anni "
                 "solari pieni). PRIMARY_FRESH_VERDICT_WINDOW (~2.5 anni) NON garantisce tre segmenti "
                 "annuali completi e comparabili - userebbe implicitamente segmenti di durata "
                 "diseguale (es. due anni pieni + una porzione), rendendo il criterio '2 dei 3 "
                 "segmenti non negativi' dipendente dalla posizione calendariale delle date, non "
                 "dalla struttura del test.",
        "correction_rule": {
            "definition": "T1/T2/T3 = split cronologico della PRIMARY_FRESH_VERDICT_WINDOW in TRE "
                          "blocchi contigui di durata il piu' possibile uguale (tercile temporale, "
                          "NON anni solari nominali).",
            "constraints": ["T1 unione T2 unione T3 = l'intera PRIMARY_FRESH_VERDICT_WINDOW",
                             "nessuna sovrapposizione (no overlap)", "nessun buco (no gaps)",
                             "durate approssimativamente uguali (tercile cronologico, non calendariale)"],
            "boundaries_frozen_before_outcomes": True,
            "no_outcome_read_to_construct_segments": True,
        },
        "criteria_unchanged_in_substance": {
            "criterion_1": "Almeno 2 dei 3 segmenti (T1/T2/T3, non piu' 'Year 1/2/3') con "
                            "expectancy_R >= 0.",
            "criterion_2": "Nessun singolo segmento (T1, T2 o T3) spiega piu' del 100% del risultato "
                            "netto aggregato mentre gli altri due combinati sono negativi.",
            "same_T1_T2_T3_used_for_concentration_rule": True,
        },
        "status": "RESOLVED",
    }

    # ================= 2. Data access verification (onesta, verificata concretamente) =================
    mt5_running, mt5_running_detail = check_mt5_process_running()
    handlers, has_sync_action = check_local_bridge_whitelist()
    gold_cache = check_existing_gold_history_cache()

    data_access_verification = {
        "verification_method": "Controlli eseguiti DAVVERO al momento del build di questo artifact "
                                "(non assunti) - vedi funzioni check_mt5_process_running/"
                                "check_local_bridge_whitelist/check_existing_gold_history_cache nello "
                                "script sorgente.",
        "mt5_process_check": {
            "method": "PowerShell Get-Process -Name terminal64,terminal",
            "result": "NESSUN processo MT5 in esecuzione al momento del build" if mt5_running is False
                      else ("processo trovato" if mt5_running else f"controllo fallito: {mt5_running_detail}"),
            "running_pids_found": mt5_running_detail if mt5_running else [],
        },
        "local_bridge_capability_check": {
            "file_checked": "LocalBridge/nexus_local_worker.py",
            "file_sha256": file_sha256(LOCAL_BRIDGE_WORKER_PATH),
            "handlers_found_in_source": handlers,
            "has_history_sync_or_backtest_action": has_sync_action,
            "conclusion": "L'UNICO ponte di automation MT5 esistente nel progetto NON espone alcuna "
                          "azione di sincronizzazione storico o esecuzione Strategy Tester - solo "
                          "ping/compile_ea/restart_mt5/deploy_files/open_chart/apply_template.",
        },
        "existing_gold_history_cache_found": gold_cache,
        "existing_cache_does_not_satisfy_requirement": {
            "reason": "La cache storica GOLD preesistente su disco e' STALE rispetto alla data "
                      "dichiarata di questa sessione (" + TODAY_DECLARED + ") - l'ultimo file annuale "
                      "risulta modificato prima di tale data, e la sua provenienza/coerenza con un "
                      "vero run di Strategy Tester NON e' verificabile da questa sessione (nessun "
                      "accesso al terminale che l'ha generata, nessuna garanzia che rifletta lo stesso "
                      "feed/simbolo/broker gia' usato per l'evidenza pregressa di questo candidato). "
                      "Usarla per costruire il manifest equivarrebbe a dichiarare un 'sync' mai "
                      "realmente avvenuto in questa fase - esplicitamente vietato.",
        },
        "no_dates_hashes_or_tick_coverage_fabricated": True,
    }

    # ================= 3-8: bloccati per assenza di accesso dati (nessun valore fabbricato) =================
    blocked_sections = {
        "exact_windows": "NON risolvibile - richiede la data di sincronizzazione storica reale, non "
                        "disponibile in questa sessione.",
        "dataset_identity": "NON registrabile - symbol/timeframe/broker/timezone/tester_model/history "
                            "sync timestamp/dataset hash richiedono un run MT5 reale.",
        "real_tick_coverage": "NON verificabile - richiede l'esecuzione (o quantomeno l'ispezione "
                              "tramite Strategy Tester) dello storico reale per il periodo FRESH.",
        "protocol_identity_pins": "Gli hash dei protocolli GIA' congelati (prereg, 7.8C authorization, "
                                  "cost model, commit di codice) SONO disponibili e riportati sotto "
                                  "(sez. pinnable_protocol_hashes) - solo gli elementi che richiedono "
                                  "dati storici reali restano bloccati.",
    }

    pinnable_protocol_hashes = {
        "strategy_frozen_commit": "f035d30",
        "prereg_canonical_hash": load_json(
            os.path.join(PHASE7_DIR, "phase7_8b", "volatility_breakout_serious_3y_prereg_v1.json")
        )["canonical_sha256"],
        "authorization_7_8c_canonical_hash": auth_doc["canonical_sha256"],
        "cost_model_hash": file_sha256(os.path.join(PHASE7_DIR, "policies", "cost_model_integration.json")),
        "code_commit_sha_baseline": BASELINE_COMMIT,
        "note": "Questi hash sono gia' pinnabili ORA (non richiedono dati storici) - andranno "
                "riportati nel PRE-RUN MANIFEST reale quando i dati saranno sincronizzabili, insieme "
                "ai campi bloccati sopra.",
    }

    # ================= 9. Final status =================
    final_status = {
        "value": "PRE_RUN_SEAL_BLOCKED",
        "reason": "PRE_RUN_SEAL_BLOCKED_NO_DATA_ACCESS - questa sessione di ricerca non ha un "
                  "terminale MT5 in esecuzione, ne' uno strumento (LocalBridge o altro) capace di "
                  "sincronizzare storico reale o eseguire lo Strategy Tester. La cache storica "
                  "preesistente su disco e' stale e la sua provenienza non e' verificabile da qui - "
                  "usarla equivarrebbe a fabbricare un sync mai avvenuto.",
        "not_a_conceptual_blocker": "Diversamente dai 3 blocker di Phase 7.8B/7.8C (gia' tutti "
                                     "RESOLVED), questo e' un blocco di ACCESSO/AMBIENTE, non "
                                     "metodologico - il protocollo stesso resta interamente valido e "
                                     "pronto (vedi pinnable_protocol_hashes).",
        "what_would_unblock_this": "L'esecuzione di questa fase da una sessione/ambiente con accesso "
                                    "reale a un terminale MT5 collegato al broker (sincronizzazione "
                                    "storico dal vivo), oppure un'estensione del LocalBridge worker con "
                                    "un'azione dedicata di sync/tester - nessuna delle due disponibile "
                                    "qui.",
    }

    payload = {
        "phase": "7.8D", "artifact_role": "PRE_RUN_SEAL_STATUS",
        "candidate_id": CANDIDATE_ID,
        "scope_note": "Corregge la segmentazione temporale di 7.8C (T1/T2/T3 cronologici, non 'Year "
                       "1/2/3') e verifica ONESTAMENTE l'accesso ai dati storici reali richiesti dal "
                       "PRE-RUN MANIFEST - nessun Serious validation eseguito, nessun outcome letto, "
                       "nessun valore fabbricato.",
        "baseline_commit": BASELINE_COMMIT,
        "source_artifact_untouched": {
            "file": "server/research_scripts/phase7/phase7_8c/"
                    "volatility_breakout_serious_3y_run_authorization_v1.json",
            "canonical_sha256": auth_doc["canonical_sha256"], "modified_in_this_phase": False,
        },
        "temporal_segmentation_correction": temporal_segmentation_correction,
        "data_access_verification": data_access_verification,
        "blocked_sections_pending_real_data_access": blocked_sections,
        "pinnable_protocol_hashes": pinnable_protocol_hashes,
        "final_status": final_status,
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
        payload, script="server/research_scripts/phase7/phase7_8d/build_volatility_breakout_prerun_seal_status.py",
    )
    out_path = os.path.join(PHASE78D_DIR, "volatility_breakout_prerun_seal_status_v1.json")
    save_json(out_path, doc)
    print(f"Written {out_path}")
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"final_status={payload['final_status']['value']}")


if __name__ == "__main__":
    main()
