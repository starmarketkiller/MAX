#!/usr/bin/env python3
"""M2 — Strategy Timeline (deterministico, stdlib only).

Ricostruisce la storia tecnica di ogni strategia come sequenza cronologica
di FATTI documentati nei database del Knowledge Engine (bug, run, issue,
redesign, rename) e nelle date reali dei commit git.

Regole: nessun evento inventato; cronologia incerta -> confidence=medium;
cronologia non determinabile -> NESSUN evento (registrato come gap);
niente statistiche, ranking, confronti o raccomandazioni.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOW = os.path.join(ROOT, "knowledge")

TIMELINE_SCHEMA_VERSION = 1
TIMELINE_ENGINE_VERSION = "1.0.0"

# alias storici -> nome canonico in strategy_database
ALIASES = {"CISD": "THREE_BAR_DELIVERY_BREAK"}


def load(name):
    with open(os.path.join(KNOW, name), encoding="utf-8") as f:
        return json.load(f)


def commit_date(sha: str) -> str | None:
    """Data (YYYY-MM-DD) di un commit dal repo. Deterministica. None se non esiste."""
    if not sha or not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        return None
    try:
        out = subprocess.run(["git", "-C", ROOT, "show", "-s", "--format=%as", sha],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None
    except Exception:
        return None


def event_id(strategy: str, etype: str, date: str, title: str) -> str:
    h = hashlib.sha1(f"{strategy}|{etype}|{date}|{title}".encode()).hexdigest()[:12]
    return f"evt-{h}"


def parse_it_date(s: str) -> str | None:
    """'17/07: ...' -> '2026-07-17' (anno noto dal contesto progetto: 2026).
    '16/07' -> 2026-07-16. Nessuna data -> None."""
    m = re.match(r"(\d{2})/(\d{2})", s.strip())
    if m:
        return f"2026-{m.group(2)}-{m.group(1)}"
    return None


def run_timestamp(run: dict) -> str | None:
    """Dal run_id ...__YYYYMMDD_HHMMSS -> ISO. Deterministico."""
    m = re.search(r"__(\d{8})_(\d{6})$", run["run_id"])
    if not m:
        return None
    d, t = m.group(1), m.group(2)
    return f"{d[:4]}-{d[4:6]}-{d[6:]}T{t[:2]}:{t[2:4]}:{t[4:]}Z"


def canon(name: str) -> str:
    return ALIASES.get(name, name)


def main() -> int:
    strat_db = load("strategy_database.json")
    bug_db = load("bug_database.json")
    runs_db = load("runs_database.json")
    issues_db = load("data_quality_issues.json")

    names = [s["nome"] for s in strat_db["strategie"]]
    nameset = set(names)
    by_name = {s["nome"]: s for s in strat_db["strategie"]}
    run_ids = {r["run_id"] for r in runs_db["runs"]}
    bug_ids = {b["id"] for b in bug_db["bug"]}

    events: dict[str, list] = {n: [] for n in names}
    gaps: list[str] = []
    assumptions = [
        "date italiane 'GG/MM' nei campi curati interpretate come anno 2026 (contesto documentato del progetto)",
        "alias CISD -> THREE_BAR_DELIVERY_BREAK applicato agli eventi storici",
        "eventi 'implementation' iniziali NON creati: la data di prima implementazione delle strategie precede la storia tracciata e non e' determinabile dalle fonti (registrata come gap, regola 'do not invent')",
    ]

    def add(strategy, etype, date, title, description, source_document,
            confidence, source_checksum=None, related_commit=None, related_run_id=None):
        if not date:
            return False
        ev = {
            "event_id": event_id(strategy, etype, date, title),
            "strategy_id": strategy, "timestamp": date, "event_type": etype,
            "title": title, "description": description,
            "source_document": source_document, "source_checksum": source_checksum,
            "related_commit": related_commit, "related_run_id": related_run_id,
            "confidence": confidence,
        }
        if any(e["event_id"] == ev["event_id"] for e in events[strategy]):
            return False
        events[strategy].append(ev)
        return True

    # ---------- 1. bug scoperti / fixati (bug_database) ----------
    vague_skipped = set()
    for b in bug_db["bug"]:
        raw = b["strategie_coinvolte"]
        if raw.strip().lower().startswith("tutte"):
            targets = list(names)
        else:
            targets = []
            for tok in raw.split(","):
                t = canon(tok.strip())
                if t in nameset:
                    targets.append(t)
                elif t and not t.startswith(("~", "-")):
                    vague_skipped.add(f"{b['id']}: '{tok.strip()}' non mappabile a una strategia")
        if not targets:
            gaps.append(f"{b['id']}: strategie coinvolte non attribuibili ('{raw}') - nessun evento per-strategia")
            continue
        cdate = commit_date(b.get("commit_fix", "") or "")
        for t in targets:
            add(t, "bug_discovered", b["data"], f"Bug scoperto: {b['id']}",
                b["descrizione"], "knowledge/bug_database.json", "high")
            if b["stato"].lower().startswith("risolto"):
                add(t, "bug_fixed", cdate or b["data"], f"Bug risolto: {b['id']}",
                    f"Fix: {b.get('commit_fix') or 'vedi descrizione'}",
                    "knowledge/bug_database.json",
                    "high" if cdate else "medium",
                    related_commit=b.get("commit_fix") if cdate else None)

    # ---------- 2. redesign / modifiche logica (strategy_database, campi curati) ----------
    for s in strat_db["strategie"]:
        for r in s.get("redesign_effettuati") or []:
            d = parse_it_date(r)
            if not d:
                gaps.append(f"{s['nome']}: redesign senza data determinabile ('{r[:60]}...')")
                continue
            add(s["nome"], "redesign", d, "Redesign", r, "knowledge/strategy_database.json", "high")
        for f in s.get("fix_applicati") or []:
            d = parse_it_date(f)
            m = re.search(r"\(([0-9a-f]{7})\)", f)
            sha = m.group(1) if m else None
            cd = commit_date(sha) if sha else None
            if cd:
                add(s["nome"], "logic_modification", cd, "Modifica di logica/parametri", f,
                    "knowledge/strategy_database.json", "high", related_commit=sha)
            elif d:
                add(s["nome"], "parameter_change", d, "Modifica parametri", f,
                    "knowledge/strategy_database.json", "medium")
            # senza data ne' commit: coperto quasi sempre dai bug event; non inventare

    # ---------- 3. rename (fatto documentato) ----------
    rd = commit_date("1bb167a")
    if rd:
        add("THREE_BAR_DELIVERY_BREAK", "renamed_strategy", rd,
            "Rinominata da CISD a THREE_BAR_DELIVERY_BREAK",
            "Rename onesto (la logica non e' un vero CISD canonico); logica invariata, toggle .set invariato",
            "knowledge/decision_database.json (DEC-005)", "high", related_commit="1bb167a")

    # ---------- 4. sweep eseguiti + baseline (runs_database) ----------
    for r in runs_db["runs"]:
        strat = canon(r["strategy"] or "")
        if strat not in nameset:
            continue
        ts = run_timestamp(r)
        if not ts:
            gaps.append(f"{r['run_id']}: timestamp non determinabile")
            continue
        add(strat, "sweep_executed", ts,
            f"Sweep {r['round']} S{r['pass_index']:02d}",
            f"trade={r['metrics']['trade_eseguiti'] if r['metrics'] else 'n/d'}, "
            f"PF={r['metrics']['profit_factor'] if r['metrics'] else 'n/d'}, "
            f"completed={r['completed']}, identity_ok={r.get('identity_ok')}, "
            f"confidence_import={r.get('confidence')}",
            "knowledge/runs_database.json", "high",
            source_checksum=r.get("artifact_checksum"), related_run_id=r["run_id"])
        if (r["round"].startswith("sweep37-baseline") and r["completed"]
                and r.get("identity_ok") is not False):
            add(strat, "baseline_reached", ts,
                "Prima run baseline valida (post-fix, e6ce816)",
                f"run_id={r['run_id']}", "knowledge/runs_database.json", "high",
                related_run_id=r["run_id"])

    # ---------- 5. issue rilevate (data_quality_issues) ----------
    for i in issues_db["issues"]:
        strat = canon(i.get("strategy") or "")
        if strat not in nameset:
            continue
        d = (i.get("detected_at") or "")[:10]
        add(strat, "issue_detected", d or None,
            f"Issue: {i['type']} ({i['id']})",
            f"severity={i['severity']}, status={i['status']}, actual={i.get('actual')}",
            "knowledge/data_quality_issues.json", "high")

    # ---------- ordina, valida, classifica ----------
    for n in names:
        events[n].sort(key=lambda e: (e["timestamp"], e["event_type"]))

    all_events = [e for n in names for e in events[n]]
    errors = []
    ids_seen = set()
    for e in all_events:
        if e["event_id"] in ids_seen:
            errors.append(f"evento duplicato: {e['event_id']}")
        ids_seen.add(e["event_id"])
        if e["strategy_id"] not in nameset:
            errors.append(f"evento con strategia inesistente: {e['event_id']}")
        if e["related_run_id"] and e["related_run_id"] not in run_ids:
            errors.append(f"run inesistente: {e['related_run_id']}")
        m = re.match(r"Bug (?:scoperto|risolto): (BUG-\d+)", e["title"])
        if m and m.group(1) not in bug_ids:
            errors.append(f"bug inesistente: {m.group(1)}")
    if errors:
        print("VALIDAZIONE FALLITA:", *errors[:10], sep="\n  ")
        return 1

    complete, partial = [], []
    for n in names:
        srcs = {e["source_document"] for e in events[n]}
        has_baseline = any(e["event_type"] == "baseline_reached" for e in events[n])
        (complete if len(srcs) >= 2 and has_baseline else partial).append(n)

    out = {
        "schema": TIMELINE_SCHEMA_VERSION, "timeline_engine_version": TIMELINE_ENGINE_VERSION,
        "regole": "solo fatti documentati; cronologia non determinabile = nessun evento; nessuna statistica/ranking/confronto",
        "totale_eventi": len(all_events),
        "strategie_storia_completa": complete, "strategie_storia_parziale": partial,
        "gap_cronologici": sorted(set(gaps + list(vague_skipped))),
        "assunzioni": assumptions,
        "timelines": {n: {"strategy_id": n,
                          "stato_corrente": by_name[n].get("decisione_corrente") or by_name[n].get("stato"),
                          "eventi": events[n]} for n in names},
    }
    with open(os.path.join(KNOW, "strategy_timelines.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ---------- indice umano ----------
    lines = ["# Nexus — Strategy Timeline (indice)", "",
             f"Generato da timeline_engine.py v{TIMELINE_ENGINE_VERSION} · "
             f"{len(all_events)} eventi · {len(complete)} strategie con storia completa, "
             f"{len(partial)} parziale", "",
             "Solo ricostruzione cronologica di fatti documentati — nessuna statistica, "
             "nessun ranking, nessuna raccomandazione.", ""]
    for n in names:
        evs = events[n]
        lines.append(f"## {n}  ({'storia completa' if n in complete else 'storia parziale'})")
        if not evs:
            lines.append("- (nessun evento databile nelle fonti)")
        for e in evs:
            extra = []
            if e["related_commit"]:
                extra.append(f"commit `{e['related_commit']}`")
            if e["related_run_id"]:
                extra.append(f"run `{e['related_run_id']}`")
            lines.append(f"- **{e['timestamp'][:10]}** · {e['event_type']} · {e['title']}"
                         + (f" ({', '.join(extra)})" if extra else "")
                         + (f" · confidence={e['confidence']}" if e['confidence'] != 'high' else ""))
        stato = by_name[n].get("decisione_corrente") or by_name[n].get("stato") or "-"
        lines.append(f"- **Stato attuale**: {stato}")
        lines.append("")
    if gaps or vague_skipped:
        lines.append("## Gap cronologici (nessun evento creato, regola 'do not invent')")
        for g in sorted(set(gaps + list(vague_skipped))):
            lines.append(f"- {g}")
    with open(os.path.join(KNOW, "timeline_index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"eventi totali: {len(all_events)} | complete: {len(complete)} | "
          f"parziali: {len(partial)} | gap: {len(set(gaps + list(vague_skipped)))} | validazione: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
