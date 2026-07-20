#!/usr/bin/env python3
"""M1 — Nexus Automatic Import Engine (deterministico, stdlib only).

Scansiona manifest e artefatti di test (stats CSV, trade CSV snapshot, HTML
report), calcola SHA256, evita import duplicati, conserva run multiple della
stessa strategia (mai sovrascritte), distingue complete/incomplete, aggiorna
automaticamente la knowledge base e registra provenienza e anomalie.

NON modifica mai i file sorgente. Idempotente: rieseguirlo senza nuovi file
non cambia nulla (0 nuovi import).

Output (in knowledge/):
  imports_ledger.json       - ogni evento di import: timestamp, origine, checksum,
                              versione EA, run_id, esito
  runs_database.json        - una entry per run (strategia x passata x file),
                              mai sovrascritta: file nuovi = run nuove
  artifacts_database.json   - ogni artefatto registrato (checksum, tipo, provenienza)
  data_quality_issues.json  - anomalie interrogabili (es. missing_artifact S04)
  strategy_database.json    - aggiornati SOLO i campi di run (ultimo_sweep, trade,
                              PF, WR, expectancy); i campi curati restano intatti
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOW = os.path.join(ROOT, "knowledge")
REPORTS = os.path.join(ROOT, "results", "reports", "sweep37")
MANIFESTS = os.path.join(ROOT, "results", "manifests")

# ---- classificazione deterministica dei round (tabella esplicita) ----------
# cartella -> round_id; per i file top-level decide la data nel nome file.
FOLDER_ROUNDS = {
    "pre-fix-16-07": "sweep37-prefix-r1",
    "pre-fix-16-07-round2": "sweep37-prefix-r2",
    "pre-fix-16-07-round3-gate1pos": "sweep37-gate1pos-r3",
}
BASELINE_CUTOFF = "20260718"           # >= cutoff -> round baseline
ROUND_BASELINE = "sweep37-baseline-e6ce816"
ROUND_POSTFIX12H = "sweep37-postfix12h-killed"
BASELINE_COMMIT = "e6ce816"
EA_VERSION = "2.50"

# M1.1 - versioning della provenienza: con quale versione di schema/importer
# e' stato registrato ogni record. Da incrementare a ogni cambio di formato.
KNOWLEDGE_SCHEMA_VERSION = 2
IMPORT_ENGINE_VERSION = "1.1.0"

# M1.1 - identity check (secondo livello di protezione post incidente
# S01/LIQ_SWEEP): mappa selector index -> strategia attesa, estratta dalle
# chiamate NXS_SelectorAllows(N) nel codice EA (NEXUS_EA_v2.mq5 +
# NXS_Strategies.mqh). Gli alias coprono l'attribution suffix _NXR e il
# rename CISD -> THREE_BAR_DELIVERY_BREAK (i file storici usano il nome
# vecchio, i nuovi quello nuovo: entrambi validi per l'indice 27).
SELECTOR_MAP = {
    1: {"ADX_RSI"}, 2: {"BOLLINGER"}, 3: {"MACD"}, 4: {"SAR"}, 5: {"TSI"},
    6: {"BJORGUM"}, 7: {"LIQ_SWEEP"}, 8: {"FVG_CONT"}, 9: {"BREAKOUT_ACC"},
    10: {"LONDON_BO"}, 11: {"EMA_PULLBACK"}, 12: {"BB_SQUEEZE"},
    13: {"ICHIMOKU"}, 14: {"RSI_DIV"}, 15: {"ORDER_BLOCK"},
    16: {"STRUCT_REACT", "STRUCT_REACT_NXR"},
    17: {"TURTLE_SOUP"}, 18: {"IFVG", "IFVG_NXR"}, 19: {"FVG_MIT", "FVG_MIT_NXR"},
    20: {"OB_MIT", "OB_MIT_NXR"}, 21: {"SH_BMS_RTO"}, 22: {"SMS_BMS_RTO"},
    23: {"SILVER_BULLET"}, 24: {"AMD_REVERSAL"}, 25: {"OTE_CONT"},
    26: {"MALAYSIAN_SNR", "MALAYSIAN_SNR_NXR"},
    27: {"CISD", "THREE_BAR_DELIVERY_BREAK"}, 28: {"AMD_CONT"},
    29: {"JUDAS_SWING"}, 30: {"LDN_REVERSAL"}, 31: {"NY_REVERSAL"},
    32: {"WEEKLY_EXP"}, 33: {"PO3"}, 34: {"LIQ_VOID"}, 35: {"DISP_REBAL"},
    36: {"ELLIOTT"}, 37: {"RANGE_FADE"},
}

# M1.1 - stati del ciclo di vita di un artefatto (enum documentato):
#   discovered -> registrato con checksum, contenuto non ancora estratto
#   imported   -> contenuto caricato ma non ancora interpretato (riservato)
#   parsed     -> contenuto estratto nel database
#   validated  -> parsed + tutti i check (completezza, identita') superati
ARTIFACT_STATUSES = ("discovered", "imported", "parsed", "validated")

STATS_RE = re.compile(r"SWEEP37_S(\d{2})_(\d{8})_(\d{6})_stats\.csv$")


def check_identity(pass_idx: int, strategy: str | None):
    """Ritorna (identity_ok, expected, note). Deterministico.
    identity_ok=None se il check non e' applicabile (strategia non parsata)."""
    expected = SELECTOR_MAP.get(pass_idx)
    if strategy is None:
        return None, sorted(expected) if expected else None, "strategia non parsata: check non applicabile"
    if expected is None:
        return None, None, f"indice {pass_idx} fuori mappa selector: check non applicabile"
    if strategy in expected:
        return True, sorted(expected), None
    return False, sorted(expected), f"il file dichiara '{strategy}' ma l'indice S{pass_idx:02d} atteso e' {sorted(expected)}"


def run_confidence(completed: bool, identity_ok, round_id: str):
    """Classificazione interna della qualita' dell'import (non e' l'Evidence
    Score). Ritorna (confidence, reasons)."""
    reasons = []
    if identity_ok is False:
        return "low", ["identity_mismatch: il contenuto non corrisponde all'indice della passata"]
    if not completed:
        return "low", ["run incompleta: nessuna riga attiva parsabile"]
    reasons.append("run completa, checksum registrato")
    reasons.append("identity check superato" if identity_ok else "identity check non applicabile")
    if round_id == ROUND_BASELINE:
        reasons.append("round baseline post-fix")
        return "high", reasons
    reasons.append("round storico pre-baseline: dati non confrontabili con la baseline")
    return "medium", reasons


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(name: str, default):
    p = os.path.join(KNOW, name)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default


def save(name: str, data):
    with open(os.path.join(KNOW, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def classify_round(path: str, datestr: str) -> str:
    rel = os.path.relpath(path, REPORTS)
    parts = rel.split(os.sep)
    if len(parts) > 1 and parts[0] in FOLDER_ROUNDS:
        return FOLDER_ROUNDS[parts[0]]
    if len(parts) > 1 and parts[0] == "trades_snapshots":
        return ROUND_BASELINE if datestr >= BASELINE_CUTOFF else ROUND_POSTFIX12H
    return ROUND_BASELINE if datestr >= BASELINE_CUTOFF else ROUND_POSTFIX12H


def parse_stats_csv(path: str):
    """Ritorna (strategy_name, metrics, completed, parse_note). Deterministico.
    completed=True se esiste una riga strategia attiva con contatori leggibili."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = [l for l in f.read().splitlines() if l.strip()]
    except OSError as e:
        return None, None, False, f"lettura fallita: {e}"
    if not lines:
        return None, None, False, "file vuoto"
    hdr = lines[0].split(";")
    for line in lines[1:]:
        p = line.split(";")
        if len(p) < 10:
            continue
        try:
            setups, executed = int(p[3]), int(p[5])
        except ValueError:
            continue
        if setups > 0 or executed > 0:
            r = dict(zip(hdr, p))
            try:
                metrics = {
                    "trade_eseguiti": int(r["executed"]),
                    "wins": int(r["wins"]), "losses": int(r["losses"]),
                    "winrate_pct": float(r["winrate_pct"]),
                    "expectancy_R": float(r["expectancy_R"]),
                    "profit_factor": float(r["profit_factor"]),
                    "avg_holding_sec": float(r["avg_holding_sec"]),
                }
            except (KeyError, ValueError) as e:
                return r.get("name"), None, False, f"riga attiva ma metriche illeggibili: {e}"
            return r["name"], metrics, True, None
    return None, None, False, "nessuna riga strategia attiva (setups/executed tutti a 0)"


def main() -> int:
    hdr = {"schema": KNOWLEDGE_SCHEMA_VERSION, "import_engine_version": IMPORT_ENGINE_VERSION}
    ledger = load("imports_ledger.json", {**hdr, "imports": []})
    runs = load("runs_database.json", {**hdr, "runs": []})
    artifacts = load("artifacts_database.json", {**hdr, "artifacts": []})
    issues = load("data_quality_issues.json", {**hdr, "issues": []})
    strategy_db = load("strategy_database.json", None)
    for db in (ledger, runs, artifacts, issues):
        db.update(hdr)

    known_checksums = {a["checksum"] for a in artifacts["artifacts"]}
    known_issue_ids = {i["id"] for i in issues["issues"]}
    run_ids = {r["run_id"] for r in runs["runs"]}
    stats = {"nuovi": 0, "duplicati": 0, "anomalie_nuove": 0}

    def register_artifact(path, atype, run_id=None, note=None, status="discovered"):
        csum = sha256(path)
        rel = os.path.relpath(path, ROOT)
        if csum in known_checksums:
            stats["duplicati"] += 1
            return None, csum
        known_checksums.add(csum)
        aid = f"art-{csum[:16]}"
        artifacts["artifacts"].append({
            "artifact_id": aid, "checksum": csum, "source_path": rel,
            "type": atype, "run_id": run_id, "note": note,
            "status": status,   # M1.1: discovered | imported | parsed | validated
            "provenance": {"imported_at": now_utc(),
                           "import_engine_version": IMPORT_ENGINE_VERSION,
                           "knowledge_schema_version": KNOWLEDGE_SCHEMA_VERSION,
                           "ea_version": EA_VERSION if run_id else None},
        })
        ledger["imports"].append({
            "timestamp": now_utc(), "origine": rel, "checksum": csum,
            "ea_version": EA_VERSION, "run_id": run_id, "esito": "importato", "tipo": atype,
            "import_engine_version": IMPORT_ENGINE_VERSION,
            "knowledge_schema_version": KNOWLEDGE_SCHEMA_VERSION,
        })
        stats["nuovi"] += 1
        return aid, csum

    # ---------------- 1. manifest ----------------
    for mf in sorted(glob.glob(os.path.join(MANIFESTS, "*.json"))):
        register_artifact(mf, "manifest", note="baseline/config di run")

    # ---------------- 2. stats CSV (tutte le cartelle) ----------------
    per_round_passes: dict[str, dict[int, list]] = {}
    for path in sorted(glob.glob(os.path.join(REPORTS, "**", "*_stats.csv"), recursive=True)) + \
                sorted(glob.glob(os.path.join(REPORTS, "*_stats.csv"))):
        m = STATS_RE.search(os.path.basename(path))
        if not m:
            continue
        pass_idx, datestr, timestr = int(m.group(1)), m.group(2), m.group(3)
        round_id = classify_round(path, datestr)
        strategy, metrics, completed, note = parse_stats_csv(path)
        run_id = f"{round_id}__S{pass_idx:02d}__{strategy or 'UNKNOWN'}__{datestr}_{timestr}"
        per_round_passes.setdefault(round_id, {}).setdefault(pass_idx, []).append(run_id)
        if run_id in run_ids:
            stats["duplicati"] += 1
            continue
        # M1.1 - identity check: il contenuto deve corrispondere all'indice.
        identity_ok, expected, id_note = check_identity(pass_idx, strategy)
        confidence, conf_reasons = run_confidence(completed, identity_ok, round_id)
        art_status = "validated" if (completed and identity_ok) else "parsed"
        aid, csum = register_artifact(path, "strategy_stats_csv", run_id=run_id,
                                      status=art_status)
        if aid is None and run_id not in run_ids:
            # artefatto gia' visto ma run non registrata (non dovrebbe accadere): prosegui comunque
            csum = sha256(path)
        run_ids.add(run_id)
        runs["runs"].append({
            "run_id": run_id, "round": round_id, "pass_index": pass_idx,
            "strategy": strategy, "commit": BASELINE_COMMIT if round_id == ROUND_BASELINE else None,
            "ea_version": EA_VERSION, "broker": "XM Global Limited", "symbol": "GOLD",
            "leverage_effettiva": "1:100",
            "period": "2019.07.11-2025.07.11",
            "completed": completed, "parse_note": note,
            "identity_ok": identity_ok, "identity_expected": expected,
            "identity_note": id_note,
            "confidence": confidence, "confidence_reason": conf_reasons,
            "metrics": metrics, "artifact_checksum": csum,
            "source_file": os.path.relpath(path, ROOT),
            "imported_at": now_utc(),
            "import_engine_version": IMPORT_ENGINE_VERSION,
        })
        if identity_ok is False:
            iid = f"dqi-identity-{run_id}"
            if iid not in known_issue_ids:
                known_issue_ids.add(iid)
                stats["anomalie_nuove"] += 1
                issues["issues"].append({
                    "id": iid, "type": "identity_mismatch", "strategy": strategy,
                    "run": run_id, "severity": "high", "status": "open",
                    "expected_artifact": f"stats della strategia attesa {expected} per S{pass_idx:02d}",
                    "actual": f"il file dichiara '{strategy}'",
                    "possible_cause": "tester partito con stato della passata precedente (vedi incidente S01/LIQ_SWEEP)",
                    "detected_at": now_utc(),
                })
        if not completed:
            iid = f"dqi-incomplete-{run_id}"
            if iid not in known_issue_ids:
                known_issue_ids.add(iid)
                stats["anomalie_nuove"] += 1
                issues["issues"].append({
                    "id": iid, "type": "incomplete_run", "strategy": strategy,
                    "run": run_id, "severity": "medium", "status": "open",
                    "expected_artifact": "strategy_stats_csv con riga attiva",
                    "actual": note, "possible_cause": "unknown", "detected_at": now_utc(),
                })

    # ---------------- 3. trade CSV snapshot + HTML (registrati, non parsati) --
    snapdir = os.path.join(REPORTS, "trades_snapshots")
    if os.path.isdir(snapdir):
        for path in sorted(glob.glob(os.path.join(snapdir, "*.csv"))):
            register_artifact(path, "trades_csv_snapshot", note="non ancora parsato (futuro)")
    for path in sorted(glob.glob(os.path.join(REPORTS, "**", "*.htm*"), recursive=True)):
        register_artifact(path, "html_report", note="non ancora parsato (futuro)")

    # ---------------- 4. anomalie: passate mancanti nel round baseline -------
    baseline_passes = per_round_passes.get(ROUND_BASELINE, {})
    if baseline_passes:
        max_idx = max(baseline_passes)
        for idx in range(1, max_idx + 1):
            if idx not in baseline_passes:
                iid = f"dqi-missing-S{idx:02d}-{ROUND_BASELINE}"
                if iid in known_issue_ids:
                    continue
                known_issue_ids.add(iid)
                stats["anomalie_nuove"] += 1
                issues["issues"].append({
                    "id": iid, "type": "missing_artifact",
                    "strategy": "SAR" if idx == 4 else f"selector_index_{idx}",
                    "run": f"{ROUND_BASELINE}__S{idx:02d}", "severity": "medium",
                    "status": "open", "expected_artifact": "strategy_stats_csv",
                    "actual": "missing", "possible_cause": "unknown",
                    "detected_at": now_utc(),
                })

    # ---------------- 5. aggiorna strategy_database (solo campi di run) ------
    if strategy_db:
        best = {}
        for r in runs["runs"]:
            # M1.1: una run con identity_mismatch NON e' mai classificata come
            # run valida - esclusa dalla vetrina di strategy_database.
            if (r["round"] == ROUND_BASELINE and r["strategy"] and r["completed"]
                    and r.get("identity_ok") is not False):
                cur = best.get(r["strategy"])
                if cur is None or r["run_id"] > cur["run_id"]:
                    best[r["strategy"]] = r
        for s in strategy_db["strategie"]:
            r = best.get(s["nome"])
            if not r:
                continue
            s["ultimo_sweep"] = {"run_id": r["run_id"], "round": r["round"],
                                 "passata": f"S{r['pass_index']:02d}", "file": os.path.basename(r["source_file"]),
                                 "completed": r["completed"], **(r["metrics"] or {})}
            s["nota_sweep"] = None
            s["trade"] = r["metrics"]["trade_eseguiti"] if r["metrics"] else None
            s["PF"] = r["metrics"]["profit_factor"] if r["metrics"] else None
            s["WR_pct"] = r["metrics"]["winrate_pct"] if r["metrics"] else None
            s["expectancy_R"] = r["metrics"]["expectancy_R"] if r["metrics"] else None
            s["affidabilita_dati"] = ("run baseline completa (round corrente, leva effettiva 1:100, "
                                      "impatto leva nullo su sweep isolato)")
        strategy_db["aggiornato_da_importer"] = now_utc()
        save("strategy_database.json", strategy_db)

    save("imports_ledger.json", ledger)
    save("runs_database.json", runs)
    save("artifacts_database.json", artifacts)
    save("data_quality_issues.json", issues)

    print(f"import: {stats['nuovi']} nuovi, {stats['duplicati']} duplicati saltati, "
          f"{stats['anomalie_nuove']} anomalie nuove | run totali: {len(runs['runs'])} | "
          f"artefatti: {len(artifacts['artifacts'])} | issue aperte: "
          f"{sum(1 for i in issues['issues'] if i['status'] == 'open')}")
    return 0


def selftest() -> int:
    """Test deterministici delle funzioni M1.1, senza toccare i dati reali."""
    failures = []

    def check(name, cond):
        if not cond:
            failures.append(name)
        print(("PASS" if cond else "FAIL"), "-", name)

    ok, exp, note = check_identity(8, "MACD")
    check("identity mismatch rilevato (S08 con MACD)", ok is False and "FVG_CONT" in exp)
    ok, _, _ = check_identity(8, "FVG_CONT")
    check("identity valido (S08 con FVG_CONT)", ok is True)
    ok, _, _ = check_identity(27, "CISD")
    ok2, _, _ = check_identity(27, "THREE_BAR_DELIVERY_BREAK")
    check("alias rename CISD accettati entrambi", ok is True and ok2 is True)
    ok, _, _ = check_identity(99, "MACD")
    check("indice fuori mappa -> check non applicabile (None)", ok is None)
    ok, _, _ = check_identity(8, None)
    check("strategia non parsata -> check non applicabile (None)", ok is None)

    c, r = run_confidence(True, True, ROUND_BASELINE)
    check("confidence high per run baseline valida", c == "high")
    c, _ = run_confidence(True, True, "sweep37-prefix-r1")
    check("confidence medium per round storico", c == "medium")
    c, r = run_confidence(True, False, ROUND_BASELINE)
    check("confidence low per identity mismatch", c == "low" and "identity_mismatch" in r[0])
    c, _ = run_confidence(False, True, ROUND_BASELINE)
    check("confidence low per run incompleta", c == "low")

    check("mappa selector completa 1..37", set(SELECTOR_MAP) == set(range(1, 38)))
    print(f"\nselftest: {'OK' if not failures else 'FALLITI: ' + ', '.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
