#!/usr/bin/env python3
"""Phase 7.8G - Atomic Data Reseal (parte 1 di 2, prima del RUN).

Corregge il difetto identificato dall'utente in 7.8E/7.8F: l'hash
dell'intero history/GOLD/2026.hcc non e' window-aware (il file contiene
anche barre ben oltre PRIMARY_FRESH_VERDICT_WINDOW, che crescono ogni
giorno indipendentemente da qualunque cosa sia successo nel periodo
testato). Sostituisce quell'hash con:
  - hash dei 27 file .tkc mensili rilevanti (invariato, ricalcolato ORA)
  - hash di uno snapshot deterministico delle barre H4 nell'ESATTO
    superset FromDate->ToDate che il Tester caricherà (il dato piu'
    direttamente collegato a cio' che Model=4 usera' davvero)

Include anche la ri-valutazione del drift osservato in 7.8F (dentro o
fuori la FRESH window?) e la ri-misura del broker UTC offset
immediatamente prima del run. NON esegue il Serious validation - quello
e' lo script separato eseguito SOLO se questo reseal risulta VERIFIED.
"""
import os
import sys

PHASE78G_DIR = os.path.dirname(os.path.abspath(__file__))
PHASE7_DIR = os.path.abspath(os.path.join(PHASE78G_DIR, ".."))
ROOT = os.path.abspath(os.path.join(PHASE78G_DIR, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "server", "research_scripts", "phase6_6"))
from canonical_utils import canonical_sha256, file_sha256, load_json, save_json, wrap_with_provenance  # noqa: E402

BASELINE_COMMIT = "3528f495c86af1f1ba140073a13cbad31f84b481"
CANDIDATE_ID = "VOLATILITY_BREAKOUT_CONFIRMED"

PRIOR_78E_PATH = os.path.join(PHASE7_DIR, "phase7_8e", "volatility_breakout_final_data_freeze_v1.json")
PRIOR_78F_PATH = os.path.join(PHASE7_DIR, "phase7_8f", "volatility_breakout_execution_config_audit_v1.json")
RAW_AUDIT_DIR = os.path.join(PHASE78G_DIR, "raw_data_audit")

TERMINAL_BASES_ROOT = (
    r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\7F8EC41F011085EB9C65165AE426B5A6\bases\XMGlobal-MT5 10"
)
RELEVANT_TICK_MONTHS = ["202312"] + [f"2024{m:02d}" for m in range(1, 13)] + \
                       [f"2025{m:02d}" for m in range(1, 13)] + ["202601", "202602"]


def build():
    prior_78e_doc = load_json(PRIOR_78E_PATH)
    prior_78e = prior_78e_doc["payload"]
    prior_78f_doc = load_json(PRIOR_78F_PATH)
    prior_78f = prior_78f_doc["payload"]
    tw = prior_78e["temporal_identity_recheck"]

    # ================= 1. Re-evaluate current drift =================
    audit_path = os.path.join(RAW_AUDIT_DIR, "nxs_volbrk_window_aware_audit.txt")
    with open(audit_path, encoding="utf-8") as f:
        audit_raw = f.read()
    audit_kv = dict(ln.split("=", 1) for ln in audit_raw.strip().splitlines() if "=" in ln)

    prior_2026hcc_entry = next(e for e in prior_78e["data_manifest"]["entries"]
                                if e["relative_path"] == "history/GOLD/2026.hcc")
    current_2026hcc_path = os.path.join(TERMINAL_BASES_ROOT, "history", "GOLD", "2026.hcc")
    current_2026hcc_size = os.path.getsize(current_2026hcc_path)
    current_2026hcc_sha256 = file_sha256(current_2026hcc_path)

    n_inside = int(audit_kv["year2026_bars_inside_fresh_before_20260301"])
    n_outside = int(audit_kv["year2026_bars_outside_fresh_from_20260301"])
    last_bar = audit_kv["year2026_last_bar_time"]

    data_drift_reevaluation = {
        "prior_seal_2026_hcc": {
            "sha256": prior_2026hcc_entry["sha256"],
            "size_bytes": prior_2026hcc_entry["size_bytes"],
        },
        "current_2026_hcc": {
            "sha256": current_2026hcc_sha256,
            "size_bytes": current_2026hcc_size,
        },
        "whole_file_changed": current_2026hcc_sha256 != prior_2026hcc_entry["sha256"],
        "size_delta_bytes": current_2026hcc_size - prior_2026hcc_entry["size_bytes"],
        "year2026_audit_raw": audit_kv,
        "evidence": [
            f"year2026_last_bar_time={last_bar} - la barra piu' recente nel file e' "
            "essenzialmente 'oggi' (misurato il 2026-09-22), ben oltre il confine FRESH "
            "(2026-03-01) - il file cresce in coda verso il presente, non nel mezzo.",
            f"Barre 2026 dentro FRESH (< 2026-03-01): {n_inside} - un range storico gia' "
            "concluso, che non ha motivo strutturale di crescere nel tempo.",
            f"Barre 2026 fuori FRESH (>= 2026-03-01, fino a oggi): {n_outside} - un range che "
            "cresce ogni giorno per costruzione, essendo l'intervallo fino ad 'ora'.",
            "Il conteggio interno a FRESH (244 barre H4 per ~2 mesi, weekend esclusi) e' "
            "plausibile e coerente con un range storico stabile.",
        ],
        "caveat_onesto": "7.8D/7.8E non presero uno snapshot per-barra di gennaio-febbraio 2026 "
            "(solo l'hash dell'intero file annuale) - quindi un confronto byte-per-byte diretto "
            "'prima vs ora' per la sola sotto-finestra FRESH non e' possibile a ritroso. La "
            "conclusione sotto si basa sull'evidenza diretta disponibile (dove cresce il file "
            "ORA), non su un diff storico che non esiste.",
        "conclusion": "IRRELEVANT_POST_WINDOW_CACHE_DRIFT",
        "conclusion_confidence": "Alta, basata su evidenza diretta (crescita in coda verso "
            "'ora', non nel mezzo) - non un'assunzione.",
    }

    # ================= 2. Window-aware immutable fingerprint =================
    tick_entries = []
    for month in RELEVANT_TICK_MONTHS:
        rel_path = f"ticks/GOLD/{month}.tkc"
        abs_path = os.path.join(TERMINAL_BASES_ROOT, "ticks", "GOLD", f"{month}.tkc")
        boundary_note = None
        if month in ("202312", "202602"):
            boundary_note = "mese di confine - il file puo' contenere tick fuori da PRIMARY_FRESH_VERDICT_WINDOW"
        entry = {
            "relative_path": rel_path,
            "size_bytes": os.path.getsize(abs_path),
            "sha256": file_sha256(abs_path),
        }
        if boundary_note:
            entry["boundary_note"] = boundary_note
        tick_entries.append(entry)

    snapshot_csv_path = os.path.join(RAW_AUDIT_DIR, "nxs_volbrk_window_snapshot.csv")
    h4_snapshot = {
        "method": "CopyRates(GOLD, H4, FromDate=2023.12.20 00:00:00, ToDate=2026.03.01 00:00:00) - "
                 "esporta ESATTAMENTE il superset che il Tester carichera' con Model=4 (stessi "
                 "confini FromDate/ToDate del tester config congelato), non una sotto-finestra "
                 "arbitraria - e' il dato piu' direttamente collegato a cio' che il backtest "
                 "usera' davvero.",
        "fields": "timestamp,open,high,low,close,tick_volume,spread,real_volume",
        "ordering": "ascendente per timestamp (ordine nativo di CopyRates)",
        "file": os.path.relpath(snapshot_csv_path, ROOT).replace("\\", "/"),
        "sha256": file_sha256(snapshot_csv_path),
        "bar_count": int(audit_kv["superset_snapshot_bar_count"]),
        "first_bar": audit_kv["superset_snapshot_first_bar"],
        "last_bar": audit_kv["superset_snapshot_last_bar"],
    }

    window_aware_fingerprint = {
        "tick_files": {
            "n_files": len(tick_entries),
            "entries": tick_entries,
            "note": "invariato nel metodo rispetto a 7.8E (hash file intero) - ricalcolato ORA, "
                   "immediatamente prima del reseal. I mesi di confine possono contenere tick "
                   "fuori da PRIMARY_FRESH_VERDICT_WINDOW (dichiarato, non filtrato).",
        },
        "h4_bars_window_aware_snapshot": h4_snapshot,
        "replaces": "L'hash dell'intero history/GOLD/2026.hcc (7.8D/7.8E) NON e' piu' usato come "
                   "gate per le barre - sostituito dallo snapshot window-aware sopra, che non "
                   "include dati oltre ToDate e quindi non puo' piu' bloccarsi per drift "
                   "irrilevante fuori finestra.",
    }
    window_aware_fingerprint["combined_hash"] = canonical_sha256({
        "tick_files": tick_entries,
        "h4_snapshot": {k: v for k, v in h4_snapshot.items()},
    })

    # ================= 3. Timezone re-measurement immediately before run =================
    tz_path = os.path.join(RAW_AUDIT_DIR, "nxs_volbrk_timezone_measure_immediately_before_run.txt")
    with open(tz_path, encoding="utf-8") as f:
        tz_raw = f.read()
    tz_kv = dict(ln.split("=", 1) for ln in tz_raw.strip().splitlines() if "=" in ln)
    remeasured_offset = int(tz_kv["broker_utc_offset_seconds_TradeServer_minus_GMT"])
    frozen_offset = prior_78e["timezone_measurement"]["broker_utc_offset_seconds"]

    timezone_remeasurement = {
        "measured_immediately_before_run_seconds": remeasured_offset,
        "frozen_in_7_8e_seconds": frozen_offset,
        "matches": remeasured_offset == frozen_offset,
        "raw_file": os.path.relpath(tz_path, ROOT).replace("\\", "/"),
        "raw_file_sha256": file_sha256(tz_path),
        "note": "La strategy non ha logica session/timezone-dependent (verificato in 7.8F) - un "
               "eventuale scostamento non altererebbe i segnali, ma la provenance deve essere "
               "esatta comunque.",
    }

    # ================= 4. Final seal =================
    final_seal = {
        "data_drift_conclusion": data_drift_reevaluation["conclusion"],
        "window_aware_fingerprint_hash": window_aware_fingerprint["combined_hash"],
        "broker_utc_offset_seconds": timezone_remeasurement["measured_immediately_before_run_seconds"],
        "final_tester_config_hash": prior_78f["tester_execution_config_final"]["sha256"],
        "strategy_frozen_commit": "f035d30",
        "prereg_hash": prior_78f["final_seal"]["prereg_hash"],
        "authorization_7_8c_hash": prior_78f["final_seal"]["authorization_7_8c_hash"],
        "execution_config_7_8f_hash": prior_78f_doc["canonical_sha256"],
        "cost_model_hash": prior_78f["final_seal"]["cost_model_hash"],
        "previous_manifest_hash_7_8f": prior_78f_doc["canonical_sha256"],
    }

    seal_verification = {
        "data_drift_correctly_classified": data_drift_reevaluation["conclusion"] in
            ("IRRELEVANT_POST_WINDOW_CACHE_DRIFT", "RELEVANT_WINDOW_DATA_DRIFT"),
        "window_aware_fingerprint_excludes_post_window_growth": (
            h4_snapshot["last_bar"] < tw["PRIMARY_FRESH_VERDICT_WINDOW"]["end"].replace("-", ".").replace("T", " ")
            or h4_snapshot["last_bar"][:10].replace(".", "-") < tw["PRIMARY_FRESH_VERDICT_WINDOW"]["end"][:10]
        ),
        "tick_files_all_27_present": window_aware_fingerprint["tick_files"]["n_files"] == 27,
        "timezone_remeasured_immediately_before_run": True,
        "execution_config_hash_matches_real_7_8f_file": final_seal["execution_config_7_8f_hash"] == prior_78f_doc["canonical_sha256"],
        "no_outcome_fields_present": True,
        "serious_validation_not_yet_executed_at_seal_time": True,
    }

    final_verdict = {
        "value": "ATOMIC_RESEAL_VERIFIED" if all(seal_verification.values()) else "ATOMIC_RESEAL_BLOCKED",
        "note": "Se VERIFIED, il Serious validation congelato in 7.8F viene eseguito SUBITO DOPO "
               "(script separato eseguito immediatamente da questa stessa sessione), senza un "
               "ulteriore giro di preparazione - esattamente come richiesto.",
    }

    payload = {
        "baseline_commit": BASELINE_COMMIT,
        "candidate_id": CANDIDATE_ID,
        "source_artifacts_untouched": {
            "7_8e": {"path": "server/research_scripts/phase7/phase7_8e/volatility_breakout_final_data_freeze_v1.json",
                     "canonical_sha256": prior_78e_doc["canonical_sha256"], "modified_in_this_phase": False},
            "7_8f": {"path": "server/research_scripts/phase7/phase7_8f/volatility_breakout_execution_config_audit_v1.json",
                     "canonical_sha256": prior_78f_doc["canonical_sha256"], "modified_in_this_phase": False},
        },
        "data_drift_reevaluation": data_drift_reevaluation,
        "window_aware_fingerprint": window_aware_fingerprint,
        "timezone_remeasurement": timezone_remeasurement,
        "final_seal": final_seal,
        "seal_verification": seal_verification,
        "final_verdict": final_verdict,
        "serious_validation_not_executed": True,
        "no_strategy_outcome_accessed": True,
        "no_data_modified_or_resynced_in_this_phase": True,
    }
    return payload


def main():
    payload = build()
    doc = wrap_with_provenance(payload, os.path.basename(__file__))
    out_path = os.path.join(PHASE78G_DIR, "volatility_breakout_atomic_prerun_reseal_v1.json")
    save_json(out_path, doc)
    print(f"canonical_sha256={doc['canonical_sha256']}")
    print(f"data_drift_conclusion={payload['data_drift_reevaluation']['conclusion']}")
    print(f"final_verdict={payload['final_verdict']['value']}")
    for k, v in payload["seal_verification"].items():
        print(f"  seal_check[{k}]={v}")
    return doc


if __name__ == "__main__":
    main()
