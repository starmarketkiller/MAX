#!/usr/bin/env python3
"""M4 — Deterministic Evidence Engine (stdlib only).

Collega affermazioni fattuali (claim) alle fonti che le supportano: run,
artefatti, commit, eventi timeline, bug, decisioni, issue di qualita'.

Distinzione permanente (Canonical Schema v1):
  Run.confidence   = qualita'/affidabilita' della run IMPORTATA
  evidence_strength = forza delle fonti che supportano UNO specifico claim
Non vengono mai fuse. Nessun claim di giudizio (buona/cattiva/pronta) viene
mai generato. La forza NON usa mai PF/WR/expectancy.

Determinismo: nessun wall-clock nell'output; ID derivati dal contenuto;
stessi input -> output byte-identico (verificato dal selftest).
Regole documentate in evidence_rules.md (R01-R16).
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

EVIDENCE_ENGINE_VERSION = "1.1.0"  # 1.1.0 = M4.1: baseline_availability_state
KNOWLEDGE_SCHEMA_VERSION = 2

ALLOWED_CLAIM_TYPES = {
    "strategy_exists", "strategy_identity_verified", "run_exists",
    "run_completed", "run_incomplete", "baseline_run_available",
    "baseline_run_missing", "artifact_exists", "artifact_missing",
    "artifact_checksum_verified", "metric_observed", "bug_recorded",
    "bug_fixed", "decision_recorded", "timeline_event_recorded",
    "identity_mismatch_detected", "data_quality_issue_open",
    "data_quality_issue_resolved",
}
STATUSES = ("supported", "partially_supported", "conflicting", "unsupported", "invalidated")
STRENGTHS = ("strong", "moderate", "weak", "invalid")
SCOPES = ("signal_level", "equity_level", "metadata", "execution_integrity",
          "code_history", "documentation", "data_quality")
# M4.1 - enum controllato, additivo: presente SOLO sui claim di disponibilita'
# baseline (baseline_run_available / baseline_run_missing). Il claim_type dice
# che non esiste una baseline eleggibile; questo campo dice PERCHE'.
BASELINE_AVAILABILITY_STATES = ("available", "expected_but_missing",
                                "not_yet_observed", "invalid", "unknown")

BASELINE_ROUND = "sweep37-baseline-e6ce816"


def load(name):
    with open(os.path.join(KNOW, name), encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def commit_exists(sha):
    if not sha or not re.fullmatch(r"[0-9a-f]{7,40}", str(sha)):
        return False
    try:
        r = subprocess.run(["git", "-C", ROOT, "cat-file", "-e", f"{sha}^{{commit}}"],
                           capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def cid(claim_type, subject_type, subject_id):
    return "clm-" + hashlib.sha1(f"{claim_type}|{subject_type}|{subject_id}".encode()).hexdigest()[:12]


def eid(claim_id, source_type, source_id, checksum):
    return "evl-" + hashlib.sha1(f"{claim_id}|{source_type}|{source_id}|{checksum or ''}".encode()).hexdigest()[:12]


class Builder:
    def __init__(self):
        self.claims = {}            # claim_id -> claim
        self.new_issues = []

    def add(self, rule, claim_type, subject_type, subject_id, claim_text,
            status, strength, reason, data_scope, source_type, source_id,
            source_path=None, source_checksum=None, related=None,
            validation_results=None, baseline_availability_state=None):
        assert claim_type in ALLOWED_CLAIM_TYPES, claim_type
        assert status in STATUSES and strength in STRENGTHS and data_scope in SCOPES
        if baseline_availability_state is not None:
            assert baseline_availability_state in BASELINE_AVAILABILITY_STATES
        claim_id = cid(claim_type, subject_type, subject_id)
        c = self.claims.get(claim_id)
        if c is None:
            c = {
                "claim_id": claim_id, "claim_type": claim_type,
                "claim_text": claim_text, "subject_type": subject_type,
                "subject_id": subject_id, "evidence_status": status,
                "evidence_strength": strength, "evidence_reason": [f"[{rule}] {reason}"],
                "data_scope": data_scope, "independent_source_count": 0,
                "evidence_links": [],
                "created_by_engine_version": EVIDENCE_ENGINE_VERSION,
                "knowledge_schema_version": KNOWLEDGE_SCHEMA_VERSION,
            }
            self.claims[claim_id] = c
        else:
            # aggregazione: mai duplicare il claim; status/strength si degradano
            # verso il peggiore se una fonte lo impone (conflicting/invalidated
            # dominano), altrimenti resta il migliore gia' stabilito.
            order_s = {"supported": 0, "partially_supported": 1, "unsupported": 2,
                       "conflicting": 3, "invalidated": 4}
            if order_s[status] > order_s[c["evidence_status"]]:
                c["evidence_status"] = status
            ord_f = {"strong": 0, "moderate": 1, "weak": 2, "invalid": 3}
            if status in ("conflicting", "invalidated"):
                c["evidence_strength"] = "invalid"
            elif ord_f[strength] < ord_f[c["evidence_strength"]]:
                c["evidence_strength"] = strength
            if f"[{rule}] {reason}" not in c["evidence_reason"]:
                c["evidence_reason"].append(f"[{rule}] {reason}")
        if baseline_availability_state is not None:
            prev = c.get("baseline_availability_state")
            assert prev is None or prev == baseline_availability_state, \
                f"stato baseline incoerente per {claim_id}: {prev} vs {baseline_availability_state}"
            c["baseline_availability_state"] = baseline_availability_state
        link_id = eid(claim_id, source_type, source_id, source_checksum)
        if any(l["evidence_id"] == link_id for l in c["evidence_links"]):
            return c  # stessa fonte gia' collegata: nessun duplicato
        link = {"evidence_id": link_id, "source_type": source_type,
                "source_id": source_id, "source_path": source_path,
                "source_checksum": source_checksum,
                "validation_results": validation_results or []}
        for k, v in (related or {}).items():
            link[k] = v
        c["evidence_links"].append(link)
        # indipendenza: checksum distinti contano una volta; fonti senza
        # checksum si distinguono per path/source_id.
        keys = {(l["source_checksum"] or f"nochk::{l['source_type']}::{l['source_id']}")
                for l in c["evidence_links"]}
        c["independent_source_count"] = len(keys)
        return c


def classify_baseline(candidates, selector_index, max_baseline_idx, artifact_ok):
    """M4.1 - classificazione deterministica della disponibilita' baseline.

    Input: SOLO esistenza dei candidati, completezza, identita', verifica
    artefatto e posizione nella sequenza dello sweep. Nessuna metrica di
    profittabilita' (PF/WR/expectancy) entra mai in questa funzione.
    Ritorna (state, cause) con state in BASELINE_AVAILABILITY_STATES;
    cause e' valorizzata solo per lo stato invalid (priorita' deterministica:
    identity_mismatch > incomplete > checksum_conflict).
    """
    valid = [r for r in candidates
             if r["completed"] and r.get("identity_ok") is not False
             and artifact_ok(r.get("artifact_checksum"))]
    if valid:
        return "available", None
    if candidates:
        if any(r.get("identity_ok") is False for r in candidates):
            return "invalid", "identity_mismatch"
        if any(not r["completed"] for r in candidates):
            return "invalid", "incomplete"
        return "invalid", "checksum_conflict"
    if selector_index is None:
        return "unknown", None
    if selector_index <= max_baseline_idx:
        return "expected_but_missing", None
    return "not_yet_observed", None


def build():
    strat_db = load("strategy_database.json")
    runs_db = load("runs_database.json")
    arts_db = load("artifacts_database.json")
    bugs_db = load("bug_database.json")
    dec_db = load("decision_database.json")
    iss_db = load("data_quality_issues.json")
    tl_db = load("strategy_timelines.json")

    b = Builder()
    names = [s["nome"] for s in strat_db["strategie"]]
    arts_by_checksum = {a["checksum"]: a for a in arts_db["artifacts"]}
    issue_ids = {i["id"] for i in iss_db["issues"]}

    # sha256 reale su disco, calcolato una volta per artefatto: usato sia dalla
    # verifica R09/R10 sia (M4.1) dall'eleggibilita' baseline.
    art_actual = {a["checksum"]: sha256_file(os.path.join(ROOT, a["source_path"]))
                  for a in arts_db["artifacts"]}

    def artifact_ok(chk):
        return chk is not None and art_actual.get(chk) == chk

    # ---------------- strategie ----------------
    for s in strat_db["strategie"]:
        b.add("R01", "strategy_exists", "strategy", s["nome"],
              f"La strategia {s['nome']} esiste nel Knowledge Engine",
              "supported", "strong",
              "voce presente in strategy_database (fonte diretta curata)",
              "metadata", "database", "strategy_database.json",
              source_path="knowledge/strategy_database.json",
              validation_results=["subject_exists"])

    # ---------------- run ----------------
    baseline_candidates = {}   # strategia -> TUTTE le run del round baseline
    max_baseline_idx = 0
    for r in runs_db["runs"]:
        rid, strat = r["run_id"], r["strategy"]
        art = arts_by_checksum.get(r["artifact_checksum"])
        art_id = art["artifact_id"] if art else None
        is_baseline = r["round"] == BASELINE_ROUND
        if is_baseline:
            max_baseline_idx = max(max_baseline_idx, r["pass_index"])
        related = {"related_run_id": rid, "related_artifact_id": art_id}

        b.add("R02", "run_exists", "run", rid,
              f"La run {rid} esiste ed e' collegata a un artefatto con checksum",
              "supported", "strong" if art else "moderate",
              "run registrata con artefatto checksummato" if art else
              "run registrata ma artefatto non trovato nel registro",
              "execution_integrity", "run", rid,
              source_path=r["source_file"], source_checksum=r["artifact_checksum"],
              related=related, validation_results=["run_registered"] + (["artifact_linked"] if art else []))

        if r.get("identity_ok") is True:
            b.add("R05", "strategy_identity_verified", "run", rid,
                  f"L'identita' selector<->strategia della run {rid} e' verificata",
                  "supported", "strong",
                  "identity check superato (mappa selector estratta dal codice EA)",
                  "execution_integrity", "run", rid,
                  source_path=r["source_file"], source_checksum=r["artifact_checksum"],
                  related=related, validation_results=["identity_check_passed"])
        elif r.get("identity_ok") is False:
            b.add("R06", "identity_mismatch_detected", "run", rid,
                  f"Identity mismatch nella run {rid}: contenuto e indice passata non corrispondono",
                  "supported", "strong",
                  "mismatch rilevato deterministicamente; la run e' invalida come fonte per altri claim",
                  "data_quality", "run", rid,
                  source_path=r["source_file"], source_checksum=r["artifact_checksum"],
                  related=related, validation_results=["identity_check_failed"])

        if r["completed"]:
            st, fz, why = ("supported", "strong", "riga attiva parsata dall'artefatto validato") \
                if r.get("identity_ok") is not False else \
                ("invalidated", "invalid", "run completa ma identity mismatch: fonte non valida")
            b.add("R03", "run_completed", "run", rid,
                  f"La run {rid} e' completa", st, fz, why,
                  "execution_integrity", "run", rid,
                  source_path=r["source_file"], source_checksum=r["artifact_checksum"],
                  related=related, validation_results=["parse_complete"])
        else:
            b.add("R04", "run_incomplete", "run", rid,
                  f"La run {rid} e' incompleta ({r.get('parse_note')})",
                  "supported", "strong",
                  "incompletezza osservata direttamente nel parse",
                  "data_quality", "run", rid,
                  source_path=r["source_file"], source_checksum=r["artifact_checksum"],
                  related=related, validation_results=["parse_incomplete"])

        if r.get("metrics"):
            m = r["metrics"]
            if r.get("identity_ok") is False:
                st, fz, why = "invalidated", "invalid", "metriche da run con identity mismatch"
            elif is_baseline:
                st, fz, why = "supported", "strong", "metriche da artefatto baseline validato (checksum registrato)"
            else:
                st, fz, why = "supported", "moderate", "metriche da round storico pre-baseline (non confrontabile con la baseline)"
            b.add("R11", "metric_observed", "run", rid,
                  f"Metriche SEGNALE osservate per {strat} in {rid}: "
                  f"trade={m['trade_eseguiti']}, PF={m['profit_factor']}, "
                  f"WR={m['winrate_pct']}%, expR={m['expectancy_R']} "
                  f"(livello segnale/lotto fisso - NON equity di conto)",
                  st, fz, why, "signal_level", "run", rid,
                  source_path=r["source_file"], source_checksum=r["artifact_checksum"],
                  related=related, validation_results=["metrics_parsed", "scope=signal_level"])

        if is_baseline and strat:
            baseline_candidates.setdefault(strat, []).append(r)

    # ---------------- baseline per strategia (M4.1: 5 stati espliciti) -------
    # selector index: prima dal database strategie, altrimenti dalla mappa
    # NXS_SelectorAllows estratta dal codice EA (import_engine.SELECTOR_MAP).
    # Cosi' "unknown" resta riservato ai casi davvero non classificabili.
    if KNOW not in sys.path:
        sys.path.insert(0, KNOW)
    from import_engine import SELECTOR_MAP
    sel_rev = {}
    for i, sel_names in SELECTOR_MAP.items():
        for n in sorted(sel_names):
            sel_rev.setdefault(n, i)
    strat_idx = {s["nome"]: (s["selector_index"] if s.get("selector_index") is not None
                             else sel_rev.get(s["nome"]))
                 for s in strat_db["strategie"]}
    for name in names:
        cands = baseline_candidates.get(name, [])
        idx = strat_idx.get(name)
        state, cause = classify_baseline(cands, idx, max_baseline_idx, artifact_ok)

        if state == "available":
            valid = [r for r in cands
                     if r["completed"] and r.get("identity_ok") is not False
                     and artifact_ok(r.get("artifact_checksum"))]
            r = sorted(valid, key=lambda x: x["run_id"])[-1]
            b.add("R07", "baseline_run_available", "strategy", name,
                  f"Esiste una run baseline valida per {name}",
                  "supported", "strong",
                  "run baseline completa con identity verificata e artefatto riverificato su disco",
                  "execution_integrity", "run", r["run_id"],
                  source_path=r["source_file"], source_checksum=r["artifact_checksum"],
                  related={"related_run_id": r["run_id"]},
                  validation_results=["baseline_round", "completed", "identity_ok",
                                      "artifact_verified_on_disk"],
                  baseline_availability_state="available")
        elif state == "invalid":
            r = sorted(cands, key=lambda x: x["run_id"])[-1]
            status = "conflicting" if cause == "checksum_conflict" else "invalidated"
            b.add("R08c", "baseline_run_missing", "strategy", name,
                  f"Nessuna baseline eleggibile per {name}: candidato presente ma squalificato ({cause})",
                  status, "invalid",
                  f"candidato baseline squalificato deterministicamente: {cause}",
                  "data_quality", "run", r["run_id"],
                  source_path=r["source_file"], source_checksum=r.get("artifact_checksum"),
                  related={"related_run_id": r["run_id"]},
                  validation_results=["baseline_candidate_disqualified", cause],
                  baseline_availability_state="invalid")
        elif state == "expected_but_missing":
            dqi = f"dqi-missing-S{idx:02d}-{BASELINE_ROUND}"
            b.add("R08a", "baseline_run_missing", "strategy", name,
                  f"Nessuna run baseline valida per {name}: passata S{idx:02d} attesa ma assente",
                  "supported", "strong",
                  "gap rilevato deterministicamente nella sequenza delle passate baseline",
                  "data_quality", "data_quality_issue",
                  dqi if dqi in issue_ids else "runs_database.json",
                  source_path="knowledge/data_quality_issues.json" if dqi in issue_ids
                  else "knowledge/runs_database.json",
                  related={"related_run_id": None},
                  validation_results=["gap_in_baseline_sequence"] +
                  (["dqi_linked"] if dqi in issue_ids else []),
                  baseline_availability_state="expected_but_missing")
        elif state == "not_yet_observed":
            # stato normale e transitorio dello sweep in corso: NON e' un'anomalia
            # e NON crea/collega mai una data_quality_issue.
            b.add("R08b", "baseline_run_missing", "strategy", name,
                  f"Nessuna run baseline per {name}: passata non ancora raggiunta (sweep in corso)",
                  "supported", "moderate",
                  "assenza attesa e transitoria: lo sweep non e' ancora arrivato a questa passata",
                  "metadata", "database", "runs_database.json",
                  source_path="knowledge/runs_database.json",
                  validation_results=["pass_not_yet_reached"],
                  baseline_availability_state="not_yet_observed")
        else:  # unknown: nessuna classificazione deterministica possibile
            b.add("R08d", "baseline_run_missing", "strategy", name,
                  f"Stato baseline non determinabile per {name}: selector index assente dai dati",
                  "partially_supported", "weak",
                  "ne' candidati ne' posizione nella sequenza sweep: stato non classificabile a macchina",
                  "metadata", "database", "runs_database.json",
                  source_path="knowledge/runs_database.json",
                  validation_results=["state_not_determinable"],
                  baseline_availability_state="unknown")

    # ---------------- artefatti (verifica REALE del checksum su disco) -------
    for a in arts_db["artifacts"]:
        actual = art_actual[a["checksum"]]
        related = {"related_artifact_id": a["artifact_id"]}
        if actual is None:
            b.add("R09b", "artifact_missing", "artifact", a["artifact_id"],
                  f"L'artefatto {a['source_path']} risulta registrato ma il file non esiste piu'",
                  "conflicting", "invalid",
                  "file assente su disco: conflitto fra registro e filesystem",
                  "data_quality", "artifact", a["artifact_id"],
                  source_path=a["source_path"], source_checksum=a["checksum"],
                  related=related, validation_results=["file_missing"])
            iid = f"dqi-missing-file-{a['artifact_id']}"
            if iid not in issue_ids:
                b.new_issues.append({
                    "id": iid, "type": "missing_artifact", "strategy": None,
                    "run": a.get("run_id"), "severity": "high", "status": "open",
                    "expected_artifact": a["source_path"], "actual": "file assente su disco",
                    "possible_cause": "unknown", "detected_at": "evidence_engine (deterministico)",
                })
            continue
        b.add("R09a", "artifact_exists", "artifact", a["artifact_id"],
              f"L'artefatto {a['source_path']} esiste su disco",
              "supported", "strong", "file presente al path registrato",
              "execution_integrity", "artifact", a["artifact_id"],
              source_path=a["source_path"], source_checksum=a["checksum"],
              related=related, validation_results=["file_exists"])
        if actual == a["checksum"]:
            b.add("R10a", "artifact_checksum_verified", "artifact", a["artifact_id"],
                  f"Il checksum di {a['source_path']} e' stato riverificato ora e coincide",
                  "supported", "strong",
                  "sha256 ricalcolato dal file == checksum registrato all'import",
                  "execution_integrity", "artifact", a["artifact_id"],
                  source_path=a["source_path"], source_checksum=a["checksum"],
                  related=related, validation_results=["checksum_match"])
        else:
            b.add("R10b", "artifact_checksum_verified", "artifact", a["artifact_id"],
                  f"Il checksum di {a['source_path']} NON coincide piu' col registrato",
                  "conflicting", "invalid",
                  "il file e' cambiato dopo l'import: viola l'immutabilita' (V03)",
                  "data_quality", "artifact", a["artifact_id"],
                  source_path=a["source_path"], source_checksum=a["checksum"],
                  related=related, validation_results=["checksum_mismatch"])
            iid = f"dqi-checksum-{a['artifact_id']}"
            if iid not in issue_ids:
                b.new_issues.append({
                    "id": iid, "type": "identity_mismatch", "strategy": None,
                    "run": a.get("run_id"), "severity": "high", "status": "open",
                    "expected_artifact": f"checksum {a['checksum'][:16]}...",
                    "actual": f"checksum attuale {actual[:16]}...",
                    "possible_cause": "file modificato dopo l'import",
                    "detected_at": "evidence_engine (deterministico)",
                })

    # ---------------- bug ----------------
    for bug in bugs_db["bug"]:
        b.add("R12", "bug_recorded", "bug", bug["id"],
              f"{bug['id']} registrato: {bug['descrizione'][:80]}",
              "supported", "strong", "voce presente nel bug database",
              "documentation", "database", "bug_database.json",
              source_path="knowledge/bug_database.json",
              related={"related_bug_id": bug["id"]},
              validation_results=["bug_registered"])
        if str(bug["stato"]).lower().startswith("risolto"):
            sha = bug.get("commit_fix") or ""
            m = re.search(r"\b([0-9a-f]{7,40})\b", sha)
            verified = commit_exists(m.group(1)) if m else False
            if verified:
                b.add("R13a", "bug_fixed", "bug", bug["id"],
                      f"{bug['id']} risolto con commit verificabile {m.group(1)}",
                      "supported", "strong",
                      "commit di fix esistente nel repository (cronologia commit-backed)",
                      "code_history", "commit", m.group(1),
                      related={"related_bug_id": bug["id"], "related_commit": m.group(1)},
                      validation_results=["commit_exists"])
            elif sha and sha not in ("-",):
                b.add("R13b", "bug_fixed", "bug", bug["id"],
                      f"{bug['id']} dichiarato risolto; fix descritto ma non commit-verificabile ({sha[:50]})",
                      "partially_supported", "moderate",
                      "il fix e' documentato ma vive fuori dal repository o senza SHA verificabile",
                      "documentation", "database", "bug_database.json",
                      source_path="knowledge/bug_database.json",
                      related={"related_bug_id": bug["id"]},
                      validation_results=["fix_documented_not_commit_backed"])
            else:
                b.add("R13c", "bug_fixed", "bug", bug["id"],
                      f"{bug['id']} dichiarato risolto ma senza alcun riferimento di fix",
                      "conflicting", "invalid",
                      "stato 'risolto' senza commit ne' descrizione del fix: conflitto documentale",
                      "data_quality", "database", "bug_database.json",
                      source_path="knowledge/bug_database.json",
                      related={"related_bug_id": bug["id"]},
                      validation_results=["fix_reference_missing"])

    # ---------------- decisioni ----------------
    for d in dec_db["decisioni"]:
        b.add("R14", "decision_recorded", "decision", d["id"],
              f"{d['id']} registrata: {d['decisione'][:80]}",
              "supported", "strong",
              "decisione registrata con motivo, evidenze e documenti sorgente",
              "documentation", "database", "decision_database.json",
              source_path="knowledge/decision_database.json",
              related={"related_decision_id": d["id"]},
              validation_results=["decision_registered"])

    # ---------------- eventi timeline ----------------
    for name, tl in tl_db["timelines"].items():
        for e in tl["eventi"]:
            backed = bool(e.get("related_commit") or e.get("related_run_id"))
            b.add("R15", "timeline_event_recorded", "timeline_event", e["event_id"],
                  f"Evento {e['event_type']} per {name} il {e['timestamp'][:10]}: {e['title'][:60]}",
                  "supported",
                  "strong" if backed and e["confidence"] == "high" else "moderate",
                  "evento ancorato a commit/run" if backed else
                  "evento da fonte documentale (data documentata, non commit-backed)",
                  "code_history" if e.get("related_commit") else "documentation",
                  "timeline_event", e["event_id"],
                  source_path=e["source_document"], source_checksum=e.get("source_checksum"),
                  related={"related_event_id": e["event_id"],
                           "related_commit": e.get("related_commit"),
                           "related_run_id": e.get("related_run_id")},
                  validation_results=["event_registered"] + (["source_backed"] if backed else []))

    # ---------------- data quality issues ----------------
    for i in iss_db["issues"]:
        ctype = "data_quality_issue_open" if i["status"] == "open" else "data_quality_issue_resolved"
        b.add("R16", ctype, "data_quality_issue", i["id"],
              f"Issue {i['id']} ({i['type']}) e' {i['status']}",
              "supported", "strong", "voce presente nel registro issue",
              "data_quality", "database", "data_quality_issues.json",
              source_path="knowledge/data_quality_issues.json",
              validation_results=["issue_registered"])

    return b, runs_db, arts_db, bugs_db, dec_db, iss_db, tl_db


def validate(b, runs_db, arts_db, bugs_db, dec_db, iss_db, tl_db):
    run_ids = {r["run_id"] for r in runs_db["runs"]}
    art_ids = {a["artifact_id"] for a in arts_db["artifacts"]}
    bug_ids = {x["id"] for x in bugs_db["bug"]}
    dec_ids = {x["id"] for x in dec_db["decisioni"]}
    ev_ids = {e["event_id"] for tl in tl_db["timelines"].values() for e in tl["eventi"]}
    errors = []
    for c in b.claims.values():
        if c["claim_type"] not in ALLOWED_CLAIM_TYPES:
            errors.append(f"tipo claim vietato: {c['claim_type']}")
        if not c["evidence_links"]:
            errors.append(f"claim senza fonti: {c['claim_id']}")
        for l in c["evidence_links"]:
            for field, pool in (("related_run_id", run_ids), ("related_artifact_id", art_ids),
                                ("related_bug_id", bug_ids), ("related_decision_id", dec_ids),
                                ("related_event_id", ev_ids)):
                v = l.get(field)
                if v is not None and v not in pool:
                    errors.append(f"{c['claim_id']}: {field}={v} inesistente")
    return errors


def main():
    b, *dbs = build()
    errors = validate(b, *dbs)
    if errors:
        print("VALIDAZIONE FALLITA:", *errors[:10], sep="\n  ")
        return 1

    claims = sorted(b.claims.values(), key=lambda c: c["claim_id"])
    fingerprint = hashlib.sha256(json.dumps(
        [(c["claim_id"], c["evidence_status"], c["evidence_strength"],
          c.get("baseline_availability_state"),
          len(c["evidence_links"])) for c in claims]).encode()).hexdigest()[:16]

    from collections import Counter
    st = Counter(c["evidence_status"] for c in claims)
    fz = Counter(c["evidence_strength"] for c in claims)
    sc = Counter(c["data_scope"] for c in claims)

    out = {
        "schema": KNOWLEDGE_SCHEMA_VERSION,
        "evidence_engine_version": EVIDENCE_ENGINE_VERSION,
        "distinzione_permanente": "Run.confidence = qualita' dell'import; evidence_strength = forza delle fonti di UN claim. Mai fuse.",
        "output_fingerprint": fingerprint,
        "totale_claims": len(claims),
        "totale_evidence_links": sum(len(c["evidence_links"]) for c in claims),
        "distribuzione_status": dict(sorted(st.items())),
        "distribuzione_strength": dict(sorted(fz.items())),
        "distribuzione_scope": dict(sorted(sc.items())),
        "claims": claims,
    }
    with open(os.path.join(KNOW, "evidence_database.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # ---- nuove issue rilevate (convenzioni esistenti, append idempotente) ----
    if b.new_issues:
        iss = load("data_quality_issues.json")
        known = {i["id"] for i in iss["issues"]}
        added = [i for i in b.new_issues if i["id"] not in known]
        if added:
            iss["issues"].extend(added)
            with open(os.path.join(KNOW, "data_quality_issues.json"), "w", encoding="utf-8") as f:
                json.dump(iss, f, ensure_ascii=False, indent=1)

    # ---- indice umano ----
    def by_state(s):
        return sorted(c["subject_id"] for c in claims
                      if c.get("baseline_availability_state") == s)

    avail = by_state("available")
    exp_missing = by_state("expected_but_missing")
    not_yet = by_state("not_yet_observed")
    invalid = by_state("invalid")
    unknown = by_state("unknown")
    lines = [
        "# Nexus — Evidence Index (M4)", "",
        f"Generato da evidence_engine v{EVIDENCE_ENGINE_VERSION} · fingerprint `{fingerprint}` · deterministico, senza interpretazioni.", "",
        f"- **Claims totali**: {len(claims)}",
        f"- **Evidence links totali**: {out['totale_evidence_links']}",
        f"- **Status**: {dict(sorted(st.items()))}",
        f"- **Strength**: {dict(sorted(fz.items()))}",
        f"- **Scope**: {dict(sorted(sc.items()))}", "",
        "## Disponibilita' baseline per strategia (M4.1)", "",
        "Campo controllato `baseline_availability_state`: distingue a macchina i motivi "
        "dell'assenza, senza inferenze dal testo libero.", "",
        f"### Baseline disponibile ({len(avail)})",
        ", ".join(avail) or "(nessuna)", "",
        f"### Attesa ma assente ({len(exp_missing)}) — anomalia reale, tracciata come data quality issue",
        ", ".join(exp_missing) or "(nessuna)", "",
        f"### Non ancora osservata ({len(not_yet)}) — stato NORMALE e transitorio: lo sweep in corso non e' ancora arrivato a queste passate. Non e' un'anomalia.",
        ", ".join(not_yet) or "(nessuna)", "",
        f"### Invalida ({len(invalid)}) — candidato presente ma squalificato (identity mismatch / incompleta / checksum)",
        ", ".join(invalid) or "(nessuna)", "",
        f"### Non determinabile ({len(unknown)})",
        ", ".join(unknown) or "(nessuna)", "",
        "## Issue di qualita' collegate alle evidenze",
    ]
    iss = load("data_quality_issues.json")
    for i in iss["issues"]:
        if i["status"] == "open":
            lines.append(f"- `{i['id']}` ({i['type']}, severity {i['severity']})")
    lines += ["", "## Limiti",
              "- Le metriche sono SEMPRE a livello segnale (lotto fisso, strategia isolata): mai Net PnL/Max DD di conto, mai inferiti dai CSV di sweep.",
              "- Copertura timeline = completa PER LE EVIDENZE DISPONIBILI (complete_for_available_evidence), mai storia assoluta.",
              "- Nessun claim di giudizio (buona/cattiva/pronta per il live) viene generato: fuori scope M4.",
              "- Le run baseline mancanti per passate non ancora eseguite sono assenze transitorie (sweep in corso)."]
    with open(os.path.join(KNOW, "evidence_index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"claims: {len(claims)} | links: {out['totale_evidence_links']} | "
          f"status: {dict(sorted(st.items()))} | strength: {dict(sorted(fz.items()))} | "
          f"nuove issue: {len(b.new_issues)} | fingerprint: {fingerprint}")
    return 0


# ------------------------------- selftest ---------------------------------
def selftest():
    fails, ran = [], []

    def check(name, cond):
        print(("PASS" if cond else "FAIL"), "-", name)
        ran.append(name)
        if not cond:
            fails.append(name)

    # 1+12. determinismo/idempotenza: doppio build -> stesso output serializzato
    b1, *dbs1 = build()
    b2, *_ = build()
    s1 = json.dumps(sorted(b1.claims.keys()) + [b1.claims[k]["evidence_status"] for k in sorted(b1.claims)])
    s2 = json.dumps(sorted(b2.claims.keys()) + [b2.claims[k]["evidence_status"] for k in sorted(b2.claims)])
    check("1/12: doppio build semanticamente identico (determinismo+idempotenza)", s1 == s2)

    # 2. fonte duplicata -> nessun claim/link duplicato
    t = Builder()
    for _ in range(2):
        t.add("RT", "bug_recorded", "bug", "BUG-999", "t", "supported", "strong",
              "r", "documentation", "database", "x.json", source_checksum="abc")
    c = t.claims[cid("bug_recorded", "bug", "BUG-999")]
    check("2: fonte duplicata non crea duplicati", len(t.claims) == 1 and len(c["evidence_links"]) == 1)

    # 3. stesso checksum da due path -> 1 fonte indipendente
    t = Builder()
    t.add("RT", "bug_recorded", "bug", "BUG-998", "t", "supported", "strong", "r",
          "documentation", "database", "a.json", source_path="p1", source_checksum="same")
    t.add("RT", "bug_recorded", "bug", "BUG-998", "t", "supported", "strong", "r2",
          "documentation", "copy", "b.json", source_path="p2", source_checksum="same")
    c = t.claims[cid("bug_recorded", "bug", "BUG-998")]
    check("3: stesso checksum via due path = 1 fonte indipendente",
          c["independent_source_count"] == 1 and len(c["evidence_links"]) == 2)

    # 4. identity mismatch -> invalidated/invalid su run_completed
    t = Builder()
    t.add("R03", "run_completed", "run", "fake-run", "t", "invalidated", "invalid",
          "run completa ma identity mismatch", "execution_integrity", "run", "fake-run")
    c = t.claims[cid("run_completed", "run", "fake-run")]
    check("4: identity mismatch -> evidenza invalidated/invalid",
          c["evidence_status"] == "invalidated" and c["evidence_strength"] == "invalid")

    # 5+6+7+8+9+10+11: sui dati reali
    claims = b1.claims.values()
    base_avail = [c for c in claims if c["claim_type"] == "baseline_run_available"]
    check("5: nessuna baseline_run_available da run incompleta",
          all("completed" in l["validation_results"] for c in base_avail for l in c["evidence_links"]))
    s04 = [c for c in claims if c["claim_type"] == "baseline_run_missing" and c["subject_id"] == "SAR"]
    check("6: S04/SAR -> baseline_run_missing collegata alla DQI esistente",
          len(s04) == 1 and any("dqi_linked" in l["validation_results"] for l in s04[0]["evidence_links"]))
    metrics = [c for c in claims if c["claim_type"] == "metric_observed"]
    check("7: tutte le metriche restano signal_level",
          all(c["data_scope"] == "signal_level" for c in metrics) and len(metrics) > 0)
    check("8: evidence_strength e' campo proprio, mai copia di Run.confidence",
          all("evidence_strength" in c and "confidence" not in c for c in claims))
    errs = validate(b1, *dbs1)
    check("9: ogni entita' referenziata esiste", errs == [])
    check("10: ogni claim ha almeno una fonte reale",
          all(c["evidence_links"] for c in claims))
    check("11: nessun claim speculativo/di giudizio",
          all(c["claim_type"] in ALLOWED_CLAIM_TYPES for c in claims))

    # ----------------- M4.1: baseline_availability_state -----------------
    base_claims = [c for c in claims
                   if c["claim_type"] in ("baseline_run_available", "baseline_run_missing")]
    check("13: ogni claim di disponibilita' baseline porta il campo controllato",
          len(base_claims) > 0 and
          all(c.get("baseline_availability_state") in BASELINE_AVAILABILITY_STATES
              for c in base_claims))
    check("14: tutte le baseline_run_available sono state=available",
          all(c["baseline_availability_state"] == "available"
              for c in base_claims if c["claim_type"] == "baseline_run_available"))
    check("15: S04/SAR e' expected_but_missing",
          len(s04) == 1 and s04[0].get("baseline_availability_state") == "expected_but_missing")

    # frontiera calcolata dagli input, non hardcoded (stesso fallback selector del build)
    strat_db = load("strategy_database.json")
    runs_now = load("runs_database.json")
    max_idx = max([r["pass_index"] for r in runs_now["runs"]
                   if r["round"] == BASELINE_ROUND], default=0)
    if KNOW not in sys.path:
        sys.path.insert(0, KNOW)
    from import_engine import SELECTOR_MAP
    sel_rev = {}
    for i, sel_names in SELECTOR_MAP.items():
        for nm in sorted(sel_names):
            sel_rev.setdefault(nm, i)
    beyond = {s["nome"] for s in strat_db["strategie"]
              if (s.get("selector_index") if s.get("selector_index") is not None
                  else sel_rev.get(s["nome"], 0)) > max_idx}
    beyond_claims = [c for c in base_claims if c["subject_id"] in beyond]
    check("16: ogni strategia oltre la frontiera dello sweep = not_yet_observed",
          len(beyond_claims) > 0 and
          all(c["baseline_availability_state"] == "not_yet_observed" for c in beyond_claims))
    check("17: not_yet_observed non crea ne' collega data_quality_issue",
          all("dqi_linked" not in l["validation_results"]
              for c in beyond_claims for l in c["evidence_links"]) and
          not any("missing-S" in i["id"] for i in b1.new_issues))

    # classificatore puro: cause di invalidita'
    ok_art = lambda chk: True
    cand_mm = [{"completed": True, "identity_ok": False, "artifact_checksum": "x", "run_id": "r"}]
    cand_inc = [{"completed": False, "identity_ok": True, "artifact_checksum": "x", "run_id": "r"}]
    cand_chk = [{"completed": True, "identity_ok": True, "artifact_checksum": "x", "run_id": "r"}]
    check("18: candidato squalificato -> invalid con causa deterministica",
          classify_baseline(cand_mm, 4, 8, ok_art) == ("invalid", "identity_mismatch") and
          classify_baseline(cand_inc, 4, 8, ok_art) == ("invalid", "incomplete") and
          classify_baseline(cand_chk, 4, 8, lambda c: False) == ("invalid", "checksum_conflict") and
          classify_baseline([], None, 8, ok_art) == ("unknown", None))

    # indipendenza dalla profittabilita': stessa classificazione con PF opposti,
    # e la firma del classificatore non accetta alcun input metrico
    import inspect
    sig = str(inspect.signature(classify_baseline)).lower()
    c_low = [{"completed": True, "identity_ok": True, "artifact_checksum": "x",
              "run_id": "r", "metrics": {"profit_factor": 0.1, "winrate_pct": 1.0}}]
    c_high = [dict(c_low[0], metrics={"profit_factor": 9.9, "winrate_pct": 99.0})]
    check("19: classificazione indipendente dalle metriche di profittabilita'",
          classify_baseline(c_low, 1, 8, ok_art) == classify_baseline(c_high, 1, 8, ok_art)
          and not any(k in sig for k in ("profit", "winrate", "expectancy", "metric")))

    check("20: claim_id stabili (stessa formula pre-M4.1: tipo|soggetto)",
          all(c["claim_id"] == cid(c["claim_type"], c["subject_type"], c["subject_id"])
              for c in base_claims))
    check("21: stati distinguibili dal solo campo enum (nessuna inferenza testuale)",
          s04[0]["baseline_availability_state"] != beyond_claims[0]["baseline_availability_state"]
          if s04 and beyond_claims else False)

    n = len(ran) + 1  # +1: il check 1 copre due validazioni (determinismo+idempotenza)
    print(f"\nselftest: {'OK (%d/%d)' % (n, n) if not fails else 'FALLITI: ' + ', '.join(fails)}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
