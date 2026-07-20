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

STATS_RE = re.compile(r"SWEEP37_S(\d{2})_(\d{8})_(\d{6})_stats\.csv$")


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
    ledger = load("imports_ledger.json", {"schema": 1, "imports": []})
    runs = load("runs_database.json", {"schema": 1, "runs": []})
    artifacts = load("artifacts_database.json", {"schema": 1, "artifacts": []})
    issues = load("data_quality_issues.json", {"schema": 1, "issues": []})
    strategy_db = load("strategy_database.json", None)

    known_checksums = {a["checksum"] for a in artifacts["artifacts"]}
    known_issue_ids = {i["id"] for i in issues["issues"]}
    run_ids = {r["run_id"] for r in runs["runs"]}
    stats = {"nuovi": 0, "duplicati": 0, "anomalie_nuove": 0}

    def register_artifact(path, atype, run_id=None, note=None):
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
            "provenance": {"imported_at": now_utc(), "importer": "import_engine.py v1",
                           "ea_version": EA_VERSION if run_id else None},
        })
        ledger["imports"].append({
            "timestamp": now_utc(), "origine": rel, "checksum": csum,
            "ea_version": EA_VERSION, "run_id": run_id, "esito": "importato", "tipo": atype,
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
        aid, csum = register_artifact(path, "strategy_stats_csv", run_id=run_id)
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
            "metrics": metrics, "artifact_checksum": csum,
            "source_file": os.path.relpath(path, ROOT),
            "imported_at": now_utc(),
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
            if r["round"] == ROUND_BASELINE and r["strategy"] and r["completed"]:
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


if __name__ == "__main__":
    sys.exit(main())
