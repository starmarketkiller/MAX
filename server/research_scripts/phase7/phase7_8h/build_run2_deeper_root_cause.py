#!/usr/bin/env python3
"""Phase 7.8H - Root cause analysis PIU' PROFONDA del secondo run (ancora
0 trade nonostante InpStrat_VolBreakoutConfirmed=true). Il sanity gate
preregistrato (punto 8) ha gia' classificato TECHNICAL_EXECUTION_FAILURE_
STRATEGY_NEVER_INITIALIZED (nessuna riga [RESEARCH][INIT] nel journal).
Questo script identifica la causa DI FONDO: l'EX5 deployato nel terminale
precede il commit che introduce VOLATILITY_BREAKOUT_CONFIRMED - il
binario in esecuzione in ENTRAMBI i run (7.8G e 7.8H) non conteneva ne'
il flag, ne' la funzione segnale, ne' l'aggancio del selector=56 al
codice attuale. Nessun valore .ini avrebbe mai potuto risolverlo.
"""
import os
import sys
from datetime import datetime, timezone

PHASE78H_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78H_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78H_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

TERM_DATA = r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6"


def build():
    run2_manifest = load_json(os.path.join(PHASE78H_DIR, "immutable_run_manifest_run2_v1.json"))
    result_doc = load_json(os.path.join(PHASE78H_DIR, "volatility_breakout_serious_3y_result_v1.json"))

    ex5_path = os.path.join(TERM_DATA, "MQL5", "Experts", "NEXUS_EA_v2.ex5")
    ex5_mtime = os.path.getmtime(ex5_path)
    ex5_mtime_iso = datetime.fromtimestamp(ex5_mtime, tz=timezone.utc).isoformat()

    ea_identity = run2_manifest["payload"]["collected_files"]["ea_build_identity"]

    # Ri-scansione del journal (run2, dopo 08:42:22) per il dump automatico
    # MT5 dei parametri Input - prova diretta che il binario NON riconosce
    # la variabile (MT5 stampa fedelmente ogni Input nell'ordine di
    # dichiarazione del sorgente compilato; questa singola riga e' assente
    # fra le due che la circondano nel sorgente attuale).
    journal_entries = run2_manifest["payload"]["collected_files"].get("tester_journal_logs", [])
    journal_path = None
    for e in journal_entries:
        if "20260922" in e["dest_path"]:
            journal_path = os.path.join(ROOT, e["dest_path"])
            break
    dump_evidence = {}
    if journal_path:
        with open(journal_path, encoding="utf-16-le", errors="ignore") as f:
            content = f.read()
        idx_run2_start = content.find("08:42:22.026")
        run2_log = content[idx_run2_start:idx_run2_start + 30000] if idx_run2_start >= 0 else content[:30000]
        pos_bjorgum = run2_log.find("InpStrat_BJORGUM")
        pos_breakout_acc = run2_log.find("InpStrat_BREAKOUT_ACC")
        pos_london_bo = run2_log.find("InpStrat_LONDON_BO")
        pos_volbrk = run2_log.find("InpStrat_VolBreakoutConfirmed")
        dump_evidence = {
            "InpStrat_BJORGUM_position_in_dump": pos_bjorgum,
            "InpStrat_BREAKOUT_ACC_position_in_dump": pos_breakout_acc,
            "InpStrat_LONDON_BO_position_in_dump": pos_london_bo,
            "InpStrat_VolBreakoutConfirmed_position_in_dump": pos_volbrk,
            "gap_between_BREAKOUT_ACC_and_LONDON_BO_chars": pos_london_bo - pos_breakout_acc if pos_london_bo >= 0 and pos_breakout_acc >= 0 else None,
            "InpStrat_VolBreakoutConfirmed_missing_between_the_two_adjacent_flags": (
                pos_bjorgum >= 0 and pos_breakout_acc >= 0 and pos_london_bo >= 0 and pos_volbrk == -1
            ),
            "InpResearchMode_value_logged": "InpResearchMode=false" in run2_log,
        }

    payload = {
        "phase": "7.8H",
        "artifact_role": "RUN2_DEEPER_ROOT_CAUSE_ANALYSIS",
        "candidate_id": "VOLATILITY_BREAKOUT_CONFIRMED",
        "sanity_gate_classification": result_doc["payload"]["sanity_gate"],
        "observed_fact": {
            "run2_total_trades": "0",
            "run2_history_quality": "100% ticks reali",
        },
        "deeper_root_cause": {
            "ex5_path": ex5_path,
            "ex5_mtime_iso_utc": ex5_mtime_iso,
            "ex5_sha256": ea_identity["ex5_sha256"],
            "source_sha256_at_build_time": ea_identity["source_sha256"],
            "last_commit_touching_ea_source": {
                "commit": "f035d30",
                "date": "2026-09-17",
                "message": "Strategy Foundry Phase 3: implement VOLATILITY_BREAKOUT_CONFIRMED, verify parity, HOLD verdict",
            },
            "conclusion": "L'EX5 deployato nel terminale (mtime 2026-09-10) PRECEDE di 7 giorni il commit "
                         "f035d30 (2026-09-17) che introduce VOLATILITY_BREAKOUT_CONFIRMED nel sorgente. "
                         "Il binario compilato in esecuzione in ENTRAMBI i run (7.8G e 7.8H) non conteneva "
                         "ne' la variabile InpStrat_VolBreakoutConfirmed, ne' la funzione segnale "
                         "NXS_Strat_VolatilityBreakoutConfirmed(), ne' l'aggancio del selettore 56 alla "
                         "logica del breakout - la strategia semplicemente non esisteva ancora in quel "
                         "binario. Nessun valore nel tester config .ini avrebbe potuto risolverlo.",
            "why_the_previous_fix_looked_correct_but_was_ineffective": "Il fix di 7.8H "
                "(InpStrat_VolBreakoutConfirmed=true) era corretto IN PRINCIPIO (il nome della variabile "
                "e' quello giusto nel sorgente attuale del repo) ma applicato a un binario che non la "
                "riconosce affatto - MT5 ignora silenziosamente un nome .ini che non corrisponde a "
                "nessun Input del programma compilato in esecuzione, senza errore.",
            "empirical_evidence_from_mt5_native_input_dump": dump_evidence,
            "evidence_interpretation": "MT5 stampa automaticamente OGNI variabile 'input' nell'ordine di "
                "dichiarazione del sorgente compilato all'avvio del Tester. Nel dump reale del run2, "
                "InpStrat_BREAKOUT_ACC e InpStrat_LONDON_BO (che circondano InpStrat_VolBreakoutConfirmed "
                "nel sorgente attuale, righe 543/545) sono presenti; InpStrat_VolBreakoutConfirmed (riga "
                "544) e' assente - coerente con un binario compilato PRIMA che questa riga esistesse.",
            "both_runs_affected": "Il run 7.8G (0 trade, root cause: flag mancante nell'ini) e il run 7.8H "
                "(0 trade, fix applicato ma inefficace) hanno usato ENTRAMBI lo stesso EX5 non aggiornato "
                "- entrambi tecnicamente invalidi per la STESSA causa di fondo, indipendentemente dal "
                "fix del flag gia' applicato in 7.8H.",
        },
        "proposed_fix": {
            "action": "Ricompilare MQL5/Experts/NEXUS_EA_v2.mq5 dal sorgente CORRENTE del repo (HEAD) con "
                      "MetaEditor, verificare che il nuovo EX5 sia piu' recente del commit f035d30 e che "
                      "il dump Input del prossimo run includa InpStrat_VolBreakoutConfirmed, POI rilanciare "
                      "un terzo run con lo stesso tester config gia' corretto in 7.8H (nessun altro campo "
                      "da cambiare).",
            "requires_recompile": True,
            "requires_third_run": True,
            "third_run_cost_estimate": "~2 ore reali (stesso ordine di grandezza dei run precedenti).",
        },
        "recommendation": "FERMARSI qui e attendere conferma esplicita prima di ricompilare l'EX5 e "
                          "lanciare un terzo run - questa scoperta tocca il BINARIO stesso dell'EA "
                          "(non solo un campo .ini), un salto di sostanza tecnica ulteriore rispetto al "
                          "fix gia' applicato in 7.8H.",
        "no_verdict_computed_on_this_run": True,
        "no_serious_validation_result_produced": True,
        "run1_and_run2_both_archived_unmodified": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78H_DIR, "volatility_breakout_run2_deeper_root_cause_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"ex5_mtime={payload['deeper_root_cause']['ex5_mtime_iso_utc']}")
    print(f"last_commit_touching_ea={payload['deeper_root_cause']['last_commit_touching_ea_source']}")
    print(f"evidence={payload['deeper_root_cause']['empirical_evidence_from_mt5_native_input_dump']}")
    return doc


if __name__ == "__main__":
    main()
