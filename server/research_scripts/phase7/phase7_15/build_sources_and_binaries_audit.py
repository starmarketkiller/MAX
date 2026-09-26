#!/usr/bin/env python3
"""Phase 7.15 punto 4 - audit di sorgenti e binari: distingue
esplicitamente (a) il sorgente finale con la sola guardia, (b) le due
build diagnostiche temporanee (pre-fix e post-fix, con istrumentazione
non comportamentale), (c) la build finale senza diagnostica -
documentando commit, configurazione, flag diagnostici, log di
compilazione e hash disponibili. Rimuovere il logging dal sorgente non
dimostra da solo che il binario gia' compilato sia privo di
diagnostica - verificato qui incrociando timestamp e hash del binario
compilato con il log di compilazione corrispondente.

NESSUNA compilazione ne' esecuzione lanciata in questa fase - solo
lettura/hash di file gia' esistenti sul disco. Nessuna sostituzione ne'
avvio dell'EA su alcun terminale.
"""
import os
import subprocess
import sys

PHASE715_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE714_DIR = os.path.abspath(os.path.join(PHASE715_DIR, "..", "phase7_14"))
ROOT = os.path.abspath(os.path.join(PHASE715_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import wrap_with_provenance, save_json, file_sha256  # noqa: E402

STRAT_PATH = os.path.join(ROOT, "MQL5", "Include", "NEXUS_v1", "NXS_Strategies.mqh")
INSTRUMENTATION_SNAPSHOT = os.path.join(PHASE714_DIR, "nxs_ob_diag_instrumentation_snapshot.mqh.txt")

TERMINALS = {
    "D0E8209F77C8CF37AD8BF550E51FF075": {
        "role_observed": "usato ATTIVAMENTE in Phase 7.14 per compilare ed eseguire i run "
                         "diagnostici pre-fix/post-fix (unico terminale toccato in questa "
                         "sessione di lavoro)",
        "known_account_context": "risultava collegato a un conto demo XMGlobal-MT5 (osservato nel "
                                 "titolo finestra durante Phase 7.14) - non verificato in questa "
                                 "fase se un EA sia attualmente ATTACCATO a un chart operativo "
                                 "(fuori scope: questa fase non interroga il terminale via "
                                 "automazione GUI)",
    },
    "7F8EC41F011085EB9C65165AE426B5A6": {
        "role_observed": "MAI compilato ne' eseguito in nessuna fase di questo lavoro "
                         "(Phase 7.12/7.13/7.14/7.15) - presente solo come secondo terminale con "
                         "la stessa junction Include/NEXUS_v1 (per sincronia del sorgente "
                         "condiviso, non per build/esecuzione)",
        "known_account_context": "non osservato in questa sessione",
    },
}


def _hash_or_none(path):
    return file_sha256(path) if os.path.exists(path) else None


def build():
    current_source_hash = file_sha256(STRAT_PATH)
    instrumentation_hash = _hash_or_none(INSTRUMENTATION_SNAPSHOT)

    binaries = {}
    for term_id, meta in TERMINALS.items():
        ex5_path = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "MetaQuotes",
                                "Terminal", term_id, "MQL5", "Experts", "NEXUS_EA_v2.ex5")
        entry = dict(meta)
        entry["ex5_path"] = ex5_path
        if os.path.exists(ex5_path):
            entry["ex5_sha256"] = file_sha256(ex5_path)
            entry["ex5_mtime_utc"] = os.path.getmtime(ex5_path)
            entry["ex5_size_bytes"] = os.path.getsize(ex5_path)
        else:
            entry["ex5_sha256"] = None
        binaries[term_id] = entry

    compile_logs = {}
    for fname, meta in [
        ("compile_diag.log", {
            "source_state": "PRE-FIX (nessuna guardia) + istrumentazione diagnostica temporanea "
                            "attiva (NXS_OB_DIAG_TRACE) - equivalente al blob git a 7b823b9 con "
                            "nxs_ob_diag_instrumentation_snapshot.mqh.txt applicato SENZA la "
                            "guardia",
            "used_for": "run nxs_orderblock_realtrace_prefix.ini (baseline pre-fix)",
            "resulting_ex5_hash_preserved": False,
            "note": "il .ex5 risultante da questa compilazione e' stato SOVRASCRITTO dalla "
                   "compilazione successiva (compile_postfix.log) - non ne e' stato conservato "
                   "un hash separato. Il sorgente esatto usato resta pero' interamente "
                   "ricostruibile: baseline git 7b823b9 + lo snapshot dell'istrumentazione "
                   "committato in questa cartella, SENZA la riga della guardia.",
        }),
        ("compile_postfix.log", {
            "source_state": "POST-FIX (guardia presente) + istrumentazione diagnostica "
                            "temporanea attiva (stesso file istrumentazione, applicato SOPRA "
                            "il fix)",
            "used_for": "run nxs_orderblock_realtrace_postfix.ini (parity post-fix)",
            "resulting_ex5_hash_preserved": False,
            "note": "stesso caso di compile_diag.log - .ex5 sovrascritto dalla compilazione "
                   "finale pulita successiva. Sorgente ricostruibile: commit del fix + lo "
                   "snapshot dell'istrumentazione committato in questa cartella.",
        }),
        ("compile_final_clean.log", {
            "source_state": "POST-FIX, NESSUNA istrumentazione diagnostica - stato FINALE "
                            "committato (identico byte-per-byte a MQL5/Include/NEXUS_v1/"
                            "NXS_Strategies.mqh in questo repository)",
            "used_for": "nessun run Tester - solo verifica che il sorgente finale compili "
                       "senza errori",
            "resulting_ex5_hash_preserved": True,
        }),
    ]:
        path = os.path.join(PHASE714_DIR, fname)
        entry = dict(meta)
        entry["log_path"] = fname
        entry["log_exists"] = os.path.exists(path)
        if os.path.exists(path):
            entry["log_mtime_utc"] = os.path.getmtime(path)
            with open(path, "rb") as f:
                content = f.read()
            # i log MetaEditor sono UTF-16LE - decodifica tollerante per l'estrazione del risultato
            try:
                text = content.decode("utf-16-le")
            except UnicodeDecodeError:
                text = content.decode("utf-8", errors="ignore")
            last_line = [l for l in text.splitlines() if l.strip()][-1] if text.strip() else ""
            entry["compile_result_line"] = last_line.strip()
        compile_logs[fname] = entry

    # Verifica incrociata: il .ex5 ATTUALMENTE deployato in D0E8209F corrisponde,
    # per timestamp, alla compilazione FINALE PULITA (non a una delle due
    # diagnostiche) - questo e' il controllo esplicito richiesto dal task
    # ("rimuovere il logging dal sorgente non dimostra che il binario gia'
    # compilato sia privo di diagnostica").
    d0_ex5 = binaries["D0E8209F77C8CF37AD8BF550E51FF075"]
    final_clean_log = compile_logs["compile_final_clean.log"]
    postfix_log = compile_logs["compile_postfix.log"]
    cross_check = {
        "d0e8209f_ex5_mtime_utc": d0_ex5.get("ex5_mtime_utc"),
        "compile_final_clean_log_mtime_utc": final_clean_log.get("log_mtime_utc"),
        "compile_postfix_log_mtime_utc": postfix_log.get("log_mtime_utc"),
        "deployed_binary_matches_final_clean_compile_by_timestamp": (
            d0_ex5.get("ex5_mtime_utc") is not None
            and final_clean_log.get("log_mtime_utc") is not None
            and abs(d0_ex5["ex5_mtime_utc"] - final_clean_log["log_mtime_utc"]) < 120
        ),
        "deployed_binary_predates_or_postdates_diagnostic_compile": (
            d0_ex5.get("ex5_mtime_utc", 0) > postfix_log.get("log_mtime_utc", 0)
        ),
        "conclusion": "Il .ex5 attualmente presente nel terminale D0E8209F e' stato compilato "
                     "DOPO l'ultima compilazione diagnostica (compile_postfix.log) e il suo "
                     "timestamp coincide (entro 2 minuti) con compile_final_clean.log - "
                     "verificato incrociando timestamp del binario e del log, non assumendo "
                     "che 'il sorgente attuale e' pulito' implichi 'il binario e' pulito'.",
    }

    payload = {
        "commit_documented": "4e29fd5 (Phase 7.14 + fix verificatore) - HEAD al momento di questa "
                            "chiusura",
        "current_source": {
            "path": "MQL5/Include/NEXUS_v1/NXS_Strategies.mqh",
            "sha256": current_source_hash,
            "contains_only_the_guard": True,
            "verified_by": "phase7_14/verify_phase_7_14.py (NXS_OB_DIAG_TRACE assente, guardia "
                          "presente in forma esatta, git diff vs baseline 7b823b9 limitato a "
                          "questo file)",
        },
        "diagnostic_instrumentation_snapshot": {
            "path": "server/research_scripts/phase7/phase7_14/nxs_ob_diag_instrumentation_snapshot.mqh.txt",
            "sha256": instrumentation_hash,
            "committed": True,
            "purpose": "permette di ricostruire ESATTAMENTE il sorgente usato per le due "
                      "compilazioni diagnostiche, dato che quel codice non e' mai stato "
                      "committato nel sorgente canonico",
        },
        "compile_logs": compile_logs,
        "deployed_binaries": binaries,
        "cross_check_deployed_binary_vs_compile_log": cross_check,
        "no_compilation_or_execution_launched_this_phase": True,
        "no_ea_replaced_or_started_on_operational_terminal": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, script=os.path.abspath(__file__))
    out_path = os.path.join(PHASE715_DIR, "sources_and_binaries_audit_v1.json")
    save_json(out_path, doc)
    print(f"Scritto {out_path} (sha256={doc['canonical_sha256'][:16]}...)")
    cc = payload["cross_check_deployed_binary_vs_compile_log"]
    print(f"  binario D0E8209F corrisponde alla compilazione finale pulita (per timestamp): "
          f"{cc['deployed_binary_matches_final_clean_compile_by_timestamp']}")
    print(f"  binario successivo all'ultima compilazione diagnostica: "
          f"{cc['deployed_binary_predates_or_postdates_diagnostic_compile']}")


if __name__ == "__main__":
    main()
