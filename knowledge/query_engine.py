#!/usr/bin/env python3
"""Nexus Core - M5 Deterministic Query Engine (v1.0.0).

Risponde a domande strutturate usando SOLO la base di conoscenza canonica
(knowledge/*.json). Nessuna ricerca semantica, nessun embedding, nessun LLM,
nessun riassunto in linguaggio naturale: solo filtri esatti e attraversamento
deterministico delle relazioni. Ogni risultato resta tracciabile alle entita'
sottostanti (id + fonti). Stessa query => output byte-identico.

Uso:
    python3 knowledge/query_engine.py <query_type> [chiave=valore ...]
    python3 knowledge/query_engine.py --list
    python3 knowledge/query_engine.py --validate
    python3 knowledge/query_engine.py --selftest

Documentazione: query_reference.md, query_examples.md, query_tests.md.
"""
from __future__ import annotations

import json
import os
import sys

QUERY_ENGINE_VERSION = "1.0.0"
KNOWLEDGE_SCHEMA_VERSION = 2
KNOW = os.path.dirname(os.path.abspath(__file__))
BASELINE_ROUND = "sweep37-baseline-e6ce816"

COVERAGES = ("complete_for_available_evidence", "partial_for_available_evidence")
BASELINE_STATES = ("available", "expected_but_missing", "not_yet_observed",
                   "invalid", "unknown")
ISSUE_STATUSES = ("open", "resolved")
TRAVERSE_MAX_DEPTH = 4


def _load(name):
    with open(os.path.join(KNOW, name), encoding="utf-8") as f:
        return json.load(f)


class KB:
    """Base di conoscenza indicizzata, caricata una volta, sola lettura."""

    def __init__(self):
        self.strategies = {s["nome"]: s for s in _load("strategy_database.json")["strategie"]}
        self.runs = {r["run_id"]: r for r in _load("runs_database.json")["runs"]}
        self.artifacts_by_id = {}
        self.artifacts_by_checksum = {}
        for a in _load("artifacts_database.json")["artifacts"]:
            self.artifacts_by_id[a["artifact_id"]] = a
            self.artifacts_by_checksum[a["checksum"]] = a
        self.bugs = {b["id"]: b for b in _load("bug_database.json")["bug"]}
        self.decisions = {d["id"]: d for d in _load("decision_database.json")["decisioni"]}
        self.issues = {i["id"]: i for i in _load("data_quality_issues.json")["issues"]}
        tl = _load("strategy_timelines.json")
        self.timelines = tl["timelines"]
        self.events = {e["event_id"]: e
                       for t in tl["timelines"].values() for e in t["eventi"]}
        ev = _load("evidence_database.json")
        self.claims = {c["claim_id"]: c for c in ev["claims"]}

        # indici di relazione (tutti ordinati => attraversamento deterministico)
        self.runs_by_strategy = {}
        self.runs_by_round = {}
        for rid in sorted(self.runs):
            r = self.runs[rid]
            if r.get("strategy"):
                self.runs_by_strategy.setdefault(r["strategy"], []).append(rid)
            self.runs_by_round.setdefault(r["round"], []).append(rid)
        self.events_by_strategy = {
            n: [e["event_id"] for e in sorted(t["eventi"],
                                              key=lambda e: (e["timestamp"], e["event_id"]))]
            for n, t in sorted(self.timelines.items())}
        self.events_by_run = {}
        for eid in sorted(self.events):
            rid = self.events[eid].get("related_run_id")
            if rid:
                self.events_by_run.setdefault(rid, []).append(eid)
        self.claims_by_subject = {}
        for cid in sorted(self.claims):
            c = self.claims[cid]
            self.claims_by_subject.setdefault(
                (c["subject_type"], c["subject_id"]), []).append(cid)

    def claims_for(self, subject_type, subject_id):
        return self.claims_by_subject.get((subject_type, subject_id), [])

    def bugs_of_strategy(self, name):
        # match deterministico sul testo strategie_coinvolte (campo v1 libero)
        return [bid for bid in sorted(self.bugs)
                if name in (self.bugs[bid].get("strategie_coinvolte") or "")]


# --------------------------- costruzione entita' ---------------------------
def _ent(entity_type, entity_id, matched_fields, source_ids, links,
         confidence=None):
    e = {"entity_type": entity_type, "entity_id": entity_id,
         "matched_fields": matched_fields,
         "source_ids": sorted(set(filter(None, source_ids)))}
    if confidence is not None:
        e["confidence"] = confidence
    e["links"] = {k: v for k, v in sorted(links.items()) if v}
    return e


def ent_strategy(kb, name):
    s = kb.strategies[name]
    return _ent("strategy", name,
                {k: s.get(k) for k in ("nome", "selector_index", "stato",
                                       "implementata", "decisione_corrente")},
                ["strategy_database.json"],
                {"runs": kb.runs_by_strategy.get(name, []),
                 "timeline_events": kb.events_by_strategy.get(name, []),
                 "claims": kb.claims_for("strategy", name),
                 "bugs": kb.bugs_of_strategy(name)},
                confidence=s.get("affidabilita_dati"))


def ent_run(kb, rid):
    r = kb.runs[rid]
    art = kb.artifacts_by_checksum.get(r.get("artifact_checksum"))
    return _ent("run", rid,
                {k: r.get(k) for k in ("round", "pass_index", "strategy",
                                       "completed", "identity_ok", "metrics")},
                [r.get("source_file"), "runs_database.json"],
                {"strategy": [r["strategy"]] if r.get("strategy") else [],
                 "artifact": [art["artifact_id"]] if art else [],
                 "claims": kb.claims_for("run", rid),
                 "timeline_events": kb.events_by_run.get(rid, [])},
                confidence=r.get("confidence"))


def ent_artifact(kb, aid):
    a = kb.artifacts_by_id[aid]
    return _ent("artifact", aid,
                {k: a.get(k) for k in ("checksum", "source_path", "type", "status")},
                [a.get("source_path"), "artifacts_database.json"],
                {"run": [a["run_id"]] if a.get("run_id") else [],
                 "claims": kb.claims_for("artifact", aid)})


def ent_bug(kb, bid):
    b = kb.bugs[bid]
    return _ent("bug", bid,
                {k: b.get(k) for k in ("descrizione", "strategie_coinvolte",
                                       "commit_fix", "stato")},
                ["bug_database.json"],
                {"claims": kb.claims_for("bug", bid)})


def ent_decision(kb, did):
    d = kb.decisions[did]
    docs = d.get("documenti_sorgente") or []
    if isinstance(docs, str):
        docs = [docs]
    return _ent("decision", did,
                {k: d.get(k) for k in ("data", "decisione", "documenti_sorgente")},
                ["decision_database.json"] + list(docs),
                {"claims": kb.claims_for("decision", did)})


def ent_event(kb, eid):
    e = kb.events[eid]
    return _ent("timeline_event", eid,
                {k: e.get(k) for k in ("strategy_id", "timestamp", "event_type",
                                       "title")},
                [e.get("source_document"), "strategy_timelines.json"],
                {"strategy": [e["strategy_id"]],
                 "run": [e["related_run_id"]] if e.get("related_run_id") else [],
                 "commit": [e["related_commit"]] if e.get("related_commit") else [],
                 "document": [e["source_document"]] if e.get("source_document") else [],
                 "claims": kb.claims_for("timeline_event", eid)},
                confidence=e.get("confidence"))


def ent_claim(kb, cid):
    c = kb.claims[cid]
    m = {k: c.get(k) for k in ("claim_type", "claim_text", "subject_type",
                               "subject_id", "evidence_status",
                               "evidence_strength", "data_scope",
                               "independent_source_count")}
    if "baseline_availability_state" in c:
        m["baseline_availability_state"] = c["baseline_availability_state"]
    links = {"subject": [f"{c['subject_type']}::{c['subject_id']}"],
             "evidence_links": sorted(l["evidence_id"] for l in c["evidence_links"])}
    for key in ("related_run_id", "related_artifact_id", "related_bug_id",
                "related_decision_id", "related_event_id", "related_commit"):
        vals = sorted({l[key] for l in c["evidence_links"] if l.get(key)})
        if vals:
            links[key.replace("related_", "")] = vals
    return _ent("evidence_claim", cid, m,
                [l.get("source_path") or "evidence_database.json"
                 for l in c["evidence_links"]],
                links,
                confidence={"evidence_status": c["evidence_status"],
                            "evidence_strength": c["evidence_strength"]})


def ent_issue(kb, iid):
    i = kb.issues[iid]
    return _ent("data_quality_issue", iid,
                {k: i.get(k) for k in ("type", "strategy", "run", "severity",
                                       "status", "expected_artifact")},
                ["data_quality_issues.json"],
                {"strategy": [i["strategy"]] if i.get("strategy") else [],
                 "run": [i["run"]] if i.get("run") else [],
                 "claims": kb.claims_for("data_quality_issue", iid)})


ENTITY_BUILDERS = {
    "strategy": (lambda kb: kb.strategies, ent_strategy),
    "run": (lambda kb: kb.runs, ent_run),
    "artifact": (lambda kb: kb.artifacts_by_id, ent_artifact),
    "bug": (lambda kb: kb.bugs, ent_bug),
    "decision": (lambda kb: kb.decisions, ent_decision),
    "timeline_event": (lambda kb: kb.events, ent_event),
    "evidence_claim": (lambda kb: kb.claims, ent_claim),
    "data_quality_issue": (lambda kb: kb.issues, ent_issue),
}


# ------------------------------ risposte ------------------------------------
def _envelope(qtype, params, status, results=None, error=None):
    out = {"query_engine_version": QUERY_ENGINE_VERSION,
           "knowledge_schema_version": KNOWLEDGE_SCHEMA_VERSION,
           "query": {"type": qtype, "params": dict(sorted(params.items()))},
           "status": status,
           "result_count": len(results or [])}
    if error is not None:
        out["error"] = error
    out["results"] = results or []
    return out


def _err(qtype, params, code, message, extra=None):
    e = {"code": code, "message": message}
    if extra:
        e.update(extra)
    return _envelope(qtype, params, "error", error=e)


def _found(qtype, params, results):
    return _envelope(qtype, params, "ok" if results else "empty", results)


def _sorted_results(entities):
    return sorted(entities, key=lambda e: (e["entity_type"], e["entity_id"]))


def _lookup(kb, qtype, params, key, table_name, builder_key):
    ident = params.get(key)
    if not ident:
        return _err(qtype, params, "invalid_filter", f"parametro obbligatorio: {key}")
    table, builder = ENTITY_BUILDERS[builder_key]
    if ident not in table(kb):
        return _err(qtype, params, "unknown_id",
                    f"{builder_key} '{ident}' inesistente in {table_name}")
    return _found(qtype, params, [builder(kb, ident)])


# ------------------------------ query handler -------------------------------
def q_strategy_by_id(kb, p):
    return _lookup(kb, "strategy_by_id", p, "strategy_id",
                   "strategy_database.json", "strategy")


def q_run_by_id(kb, p):
    return _lookup(kb, "run_by_id", p, "run_id", "runs_database.json", "run")


def q_artifact_by_checksum(kb, p):
    chk = p.get("checksum")
    if not chk:
        return _err("artifact_by_checksum", p, "invalid_filter",
                    "parametro obbligatorio: checksum")
    a = kb.artifacts_by_checksum.get(chk)
    if not a:
        return _err("artifact_by_checksum", p, "unknown_id",
                    f"nessun artefatto con checksum '{chk}'")
    return _found("artifact_by_checksum", p, [ent_artifact(kb, a["artifact_id"])])


def q_bug_by_id(kb, p):
    return _lookup(kb, "bug_by_id", p, "bug_id", "bug_database.json", "bug")


def q_decision_by_id(kb, p):
    return _lookup(kb, "decision_by_id", p, "decision_id",
                   "decision_database.json", "decision")


def q_timeline_of_strategy(kb, p):
    name = p.get("strategy_id")
    if not name:
        return _err("timeline_of_strategy", p, "invalid_filter",
                    "parametro obbligatorio: strategy_id")
    if name not in kb.strategies:
        return _err("timeline_of_strategy", p, "unknown_id",
                    f"strategy '{name}' inesistente")
    # ordine cronologico (timestamp, event_id): NON riordinato alfabeticamente
    return _found("timeline_of_strategy", p,
                  [ent_event(kb, eid) for eid in kb.events_by_strategy.get(name, [])])


def q_evidence_for_claim(kb, p):
    return _lookup(kb, "evidence_for_claim", p, "claim_id",
                   "evidence_database.json", "evidence_claim")


def q_evidence_for_subject(kb, p):
    st, sid = p.get("subject_type"), p.get("subject_id")
    if not st or not sid:
        return _err("evidence_for_subject", p, "invalid_filter",
                    "parametri obbligatori: subject_type, subject_id")
    cids = kb.claims_for(st, sid)
    return _found("evidence_for_subject", p,
                  _sorted_results([ent_claim(kb, c) for c in cids]))


def q_data_quality_issues(kb, p):
    status = p.get("status")
    if status is not None and status not in ISSUE_STATUSES:
        return _err("data_quality_issues", p, "invalid_filter",
                    f"status ammessi: {list(ISSUE_STATUSES)}")
    ids = [i for i in sorted(kb.issues)
           if status is None or kb.issues[i]["status"] == status]
    return _found("data_quality_issues", p, [ent_issue(kb, i) for i in ids])


def q_baseline_availability(kb, p):
    state = p.get("state")
    name = p.get("strategy_id")
    if state is not None and state not in BASELINE_STATES:
        return _err("baseline_availability", p, "invalid_filter",
                    f"state ammessi: {list(BASELINE_STATES)}")
    if name is not None and name not in kb.strategies:
        return _err("baseline_availability", p, "unknown_id",
                    f"strategy '{name}' inesistente")
    res = []
    for cid in sorted(kb.claims):
        c = kb.claims[cid]
        if "baseline_availability_state" not in c:
            continue
        if state is not None and c["baseline_availability_state"] != state:
            continue
        if name is not None and c["subject_id"] != name:
            continue
        res.append(ent_claim(kb, cid))
    return _found("baseline_availability", p, _sorted_results(res))


def q_strategies_by_timeline_coverage(kb, p):
    cov = p.get("coverage")
    if cov is not None and cov not in COVERAGES:
        return _err("strategies_by_timeline_coverage", p, "invalid_filter",
                    f"coverage ammessi: {list(COVERAGES)}")
    res = []
    for name in sorted(kb.timelines):
        tc = kb.timelines[name].get("timeline_coverage")
        if cov is None or tc == cov:
            e = ent_strategy(kb, name)
            e["matched_fields"]["timeline_coverage"] = tc
            res.append(e)
    return _found("strategies_by_timeline_coverage", p, res)


def q_runs_by_round(kb, p):
    rnd = p.get("round")
    if not rnd:
        return _err("runs_by_round", p, "invalid_filter",
                    "parametro obbligatorio: round")
    if rnd not in kb.runs_by_round:
        return _err("runs_by_round", p, "unknown_id",
                    f"round '{rnd}' inesistente",
                    {"rounds_esistenti": sorted(kb.runs_by_round)})
    return _found("runs_by_round", p,
                  [ent_run(kb, r) for r in kb.runs_by_round[rnd]])


def q_artifacts_by_type(kb, p):
    t = p.get("artifact_type")
    types = sorted({a["type"] for a in kb.artifacts_by_id.values()})
    if not t:
        return _err("artifacts_by_type", p, "invalid_filter",
                    "parametro obbligatorio: artifact_type",
                    {"tipi_esistenti": types})
    if t not in types:
        return _err("artifacts_by_type", p, "invalid_filter",
                    f"artifact_type '{t}' inesistente", {"tipi_esistenti": types})
    return _found("artifacts_by_type", p,
                  [ent_artifact(kb, a) for a in sorted(kb.artifacts_by_id)
                   if kb.artifacts_by_id[a]["type"] == t])


def _bug_is_resolved(bug):
    return str(bug.get("stato", "")).lower().startswith("risolto")


def q_open_bugs(kb, p):
    return _found("open_bugs", p,
                  [ent_bug(kb, b) for b in sorted(kb.bugs)
                   if not _bug_is_resolved(kb.bugs[b])])


def q_resolved_bugs(kb, p):
    return _found("resolved_bugs", p,
                  [ent_bug(kb, b) for b in sorted(kb.bugs)
                   if _bug_is_resolved(kb.bugs[b])])


def q_identity_mismatches(kb, p):
    res = [ent_run(kb, r) for r in sorted(kb.runs)
           if kb.runs[r].get("identity_ok") is False]
    res += [ent_issue(kb, i) for i in sorted(kb.issues)
            if kb.issues[i]["type"] == "identity_mismatch"]
    res += [ent_claim(kb, c) for c in sorted(kb.claims)
            if kb.claims[c]["claim_type"] == "identity_mismatch_detected"]
    return _found("identity_mismatches", p, _sorted_results(res))


def q_incomplete_runs(kb, p):
    return _found("incomplete_runs", p,
                  [ent_run(kb, r) for r in sorted(kb.runs)
                   if not kb.runs[r]["completed"]])


def q_missing_artifacts(kb, p):
    res = [ent_issue(kb, i) for i in sorted(kb.issues)
           if kb.issues[i]["type"] == "missing_artifact"]
    res += [ent_claim(kb, c) for c in sorted(kb.claims)
            if kb.claims[c]["claim_type"] == "artifact_missing"]
    return _found("missing_artifacts", p, _sorted_results(res))


def q_documentation_of_strategy(kb, p):
    name = p.get("strategy_id")
    if not name:
        return _err("documentation_of_strategy", p, "invalid_filter",
                    "parametro obbligatorio: strategy_id")
    if name not in kb.strategies:
        return _err("documentation_of_strategy", p, "unknown_id",
                    f"strategy '{name}' inesistente")
    docs = {}
    for eid in kb.events_by_strategy.get(name, []):
        doc = kb.events[eid].get("source_document")
        if doc:
            docs.setdefault(doc, []).append(eid)
    res = [_ent("document", doc, {"referenced_by_events": len(eids)},
                [doc], {"timeline_events": eids, "strategy": [name]})
           for doc, eids in sorted(docs.items())]
    return _found("documentation_of_strategy", p, res)


def q_commit_history_of_strategy(kb, p):
    name = p.get("strategy_id")
    if not name:
        return _err("commit_history_of_strategy", p, "invalid_filter",
                    "parametro obbligatorio: strategy_id")
    if name not in kb.strategies:
        return _err("commit_history_of_strategy", p, "unknown_id",
                    f"strategy '{name}' inesistente")
    commits = {}
    for eid in kb.events_by_strategy.get(name, []):
        e = kb.events[eid]
        if e.get("related_commit"):
            c = commits.setdefault(e["related_commit"],
                                   {"events": [], "timestamps": []})
            c["events"].append(eid)
            c["timestamps"].append(e["timestamp"])
    for bid in kb.bugs_of_strategy(name):
        fix = kb.bugs[bid].get("commit_fix")
        if fix and fix != "-":
            commits.setdefault(fix, {"events": [], "timestamps": []}) \
                .setdefault("bugs", []).append(bid)
    # ordine cronologico per primo timestamp documentato, poi per sha
    def first_ts(item):
        return (min(item[1]["timestamps"]) if item[1]["timestamps"] else "9999",
                item[0])
    res = []
    for sha, info in sorted(commits.items(), key=first_ts):
        res.append(_ent("commit", sha,
                        {"first_documented": min(info["timestamps"])
                         if info["timestamps"] else None},
                        ["strategy_timelines.json", "bug_database.json"],
                        {"timeline_events": info["events"],
                         "bugs": info.get("bugs", []),
                         "strategy": [name]}))
    return _found("commit_history_of_strategy", p, res)


# --------------------------- attraversamento --------------------------------
def _neighbors(kb, etype, eid):
    """Vicini diretti (tipo, id) di un nodo, in ordine deterministico."""
    out = []
    if etype in ENTITY_BUILDERS:
        table, builder = ENTITY_BUILDERS[etype]
        if eid in table(kb):
            links = builder(kb, eid)["links"]
            typemap = {"runs": "run", "run": "run", "artifact": "artifact",
                       "claims": "evidence_claim", "evidence_links": None,
                       "timeline_events": "timeline_event", "bugs": "bug",
                       "strategy": "strategy", "commit": "commit",
                       "document": "document", "subject": None,
                       "bug": "bug", "decision": "decision",
                       "event": "timeline_event"}
            for key in sorted(links):
                ntype = typemap.get(key)
                if ntype is None:
                    continue
                for nid in links[key]:
                    out.append((ntype, nid))
    return sorted(set(out))


def q_traverse(kb, p):
    st, sid = p.get("start_type"), p.get("start_id")
    try:
        depth = int(p.get("depth", 2))
    except (TypeError, ValueError):
        return _err("traverse", p, "invalid_filter", "depth deve essere un intero")
    if depth < 1 or depth > TRAVERSE_MAX_DEPTH:
        return _err("traverse", p, "invalid_filter",
                    f"depth ammessa: 1..{TRAVERSE_MAX_DEPTH}")
    if st not in ENTITY_BUILDERS:
        return _err("traverse", p, "invalid_filter",
                    f"start_type ammessi: {sorted(ENTITY_BUILDERS)}")
    table, builder = ENTITY_BUILDERS[st]
    if sid not in table(kb):
        return _err("traverse", p, "unknown_id", f"{st} '{sid}' inesistente")

    visited = {(st, sid)}          # guardia anti-cicli: ogni nodo una sola volta
    frontier = [(st, sid)]
    edges, broken = [], []
    for _ in range(depth):
        nxt = []
        for etype, eid in frontier:
            for ntype, nid in _neighbors(kb, etype, eid):
                if ntype in ENTITY_BUILDERS and nid not in ENTITY_BUILDERS[ntype][0](kb):
                    broken.append(f"{etype}::{eid} -> {ntype}::{nid}")
                    continue
                edges.append([f"{etype}::{eid}", f"{ntype}::{nid}"])
                if (ntype, nid) not in visited:
                    visited.add((ntype, nid))
                    nxt.append((ntype, nid))
        frontier = sorted(set(nxt))
    nodes = []
    for etype, eid in sorted(visited):
        if etype in ENTITY_BUILDERS:
            nodes.append(ENTITY_BUILDERS[etype][1](kb, eid))
        else:  # nodi terminali senza tabella propria (commit, document)
            nodes.append(_ent(etype, eid, {}, [], {}))
    env = _found("traverse", p, _sorted_results(nodes))
    env["edges"] = sorted(edges)
    if broken:
        env["broken_references"] = sorted(set(broken))
    return env


QUERIES = {
    "strategy_by_id": q_strategy_by_id,
    "run_by_id": q_run_by_id,
    "artifact_by_checksum": q_artifact_by_checksum,
    "bug_by_id": q_bug_by_id,
    "decision_by_id": q_decision_by_id,
    "timeline_of_strategy": q_timeline_of_strategy,
    "evidence_for_claim": q_evidence_for_claim,
    "evidence_for_subject": q_evidence_for_subject,
    "data_quality_issues": q_data_quality_issues,
    "baseline_availability": q_baseline_availability,
    "strategies_by_timeline_coverage": q_strategies_by_timeline_coverage,
    "runs_by_round": q_runs_by_round,
    "artifacts_by_type": q_artifacts_by_type,
    "open_bugs": q_open_bugs,
    "resolved_bugs": q_resolved_bugs,
    "identity_mismatches": q_identity_mismatches,
    "incomplete_runs": q_incomplete_runs,
    "missing_artifacts": q_missing_artifacts,
    "documentation_of_strategy": q_documentation_of_strategy,
    "commit_history_of_strategy": q_commit_history_of_strategy,
    "traverse": q_traverse,
}


def run_query(kb, qtype, params):
    if qtype not in QUERIES:
        return _err(qtype, params, "unknown_query_type",
                    f"query type '{qtype}' non supportato",
                    {"supported": sorted(QUERIES)})
    return QUERIES[qtype](kb, params)


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1)


# ------------------------------ validazione ---------------------------------
def validate(kb):
    """Integrita' referenziale dell'intera base + assenza cicli + ordinamento."""
    errors = []
    for rid, r in kb.runs.items():
        chk = r.get("artifact_checksum")
        if chk and chk not in kb.artifacts_by_checksum:
            errors.append(f"run {rid}: artifact_checksum non risolvibile")
        if r.get("strategy") and r["strategy"] not in kb.strategies:
            errors.append(f"run {rid}: strategy '{r['strategy']}' non risolvibile")
    for aid, a in kb.artifacts_by_id.items():
        if a.get("run_id") and a["run_id"] not in kb.runs:
            errors.append(f"artifact {aid}: run_id non risolvibile")
    for eid, e in kb.events.items():
        if e["strategy_id"] not in kb.strategies:
            errors.append(f"event {eid}: strategy non risolvibile")
        if e.get("related_run_id") and e["related_run_id"] not in kb.runs:
            errors.append(f"event {eid}: related_run_id non risolvibile")
    for cid, c in kb.claims.items():
        for l in c["evidence_links"]:
            for field, pool in (("related_run_id", kb.runs),
                                ("related_artifact_id", kb.artifacts_by_id),
                                ("related_bug_id", kb.bugs),
                                ("related_decision_id", kb.decisions),
                                ("related_event_id", kb.events)):
                v = l.get(field)
                if v is not None and v not in pool:
                    errors.append(f"claim {cid}: {field}={v} non risolvibile")
    for iid, i in kb.issues.items():
        if i.get("strategy") and i["strategy"] not in kb.strategies:
            errors.append(f"issue {iid}: strategy non risolvibile")

    # nessun ciclo: traverse a profondita' massima termina e non duplica nodi
    for name in sorted(kb.strategies)[:3]:
        env = q_traverse(kb, {"start_type": "strategy", "start_id": name,
                              "depth": TRAVERSE_MAX_DEPTH})
        ids = [(n["entity_type"], n["entity_id"]) for n in env["results"]]
        if len(ids) != len(set(ids)):
            errors.append(f"traverse {name}: nodi duplicati (ciclo non gestito)")

    # stesso query => output byte-identico, ordinamento stabile
    for qtype, params in (("open_bugs", {}), ("baseline_availability", {}),
                          ("runs_by_round", {"round": BASELINE_ROUND})):
        a = dumps(run_query(kb, qtype, dict(params)))
        bq = dumps(run_query(kb, qtype, dict(params)))
        if a != bq:
            errors.append(f"{qtype}: output non byte-identico")
    return errors


# ------------------------------- selftest -----------------------------------
def selftest():
    kb = KB()
    fails = []

    def check(name, cond):
        print(("PASS" if cond else "FAIL"), "-", name)
        if not cond:
            fails.append(name)

    r = run_query(kb, "strategy_by_id", {"strategy_id": "MACD"})
    check("1: lookup entita' (strategy_by_id MACD)",
          r["status"] == "ok" and r["results"][0]["entity_id"] == "MACD"
          and r["results"][0]["links"]["runs"])

    rid = sorted(kb.runs)[0]
    r = run_query(kb, "run_by_id", {"run_id": rid})
    check("2: run_by_id risolve run reale con confidence e artefatto",
          r["status"] == "ok" and "confidence" in r["results"][0])

    a = kb.artifacts_by_id[sorted(kb.artifacts_by_id)[0]]
    r = run_query(kb, "artifact_by_checksum", {"checksum": a["checksum"]})
    check("3: artifact_by_checksum roundtrip",
          r["status"] == "ok" and r["results"][0]["entity_id"] == a["artifact_id"])

    ro = run_query(kb, "open_bugs", {})
    rr = run_query(kb, "resolved_bugs", {})
    check("4: open+resolved bugs = totale bug database",
          ro["result_count"] + rr["result_count"] == len(kb.bugs))

    r = run_query(kb, "baseline_availability", {})
    states = {}
    for e in r["results"]:
        s = e["matched_fields"]["baseline_availability_state"]
        states[s] = states.get(s, 0) + 1
    sar = run_query(kb, "baseline_availability", {"strategy_id": "SAR"})
    check("5: baseline_availability copre le 37 strategie e SAR=expected_but_missing",
          sum(states.values()) == len(kb.strategies) and
          sar["results"][0]["matched_fields"]["baseline_availability_state"]
          == "expected_but_missing")

    r = run_query(kb, "timeline_of_strategy", {"strategy_id": "MACD"})
    ts = [e["matched_fields"]["timestamp"] for e in r["results"]]
    check("6: timeline in ordine cronologico, conteggio = timelines JSON",
          ts == sorted(ts) and
          r["result_count"] == len(kb.timelines["MACD"]["eventi"]))

    cid = sorted(kb.claims)[0]
    r = run_query(kb, "evidence_for_claim", {"claim_id": cid})
    check("7: evidence_for_claim con status/strength e link alle fonti",
          r["status"] == "ok" and
          r["results"][0]["confidence"]["evidence_strength"] in
          ("strong", "moderate", "weak", "invalid") and
          r["results"][0]["links"]["evidence_links"])

    r = run_query(kb, "traverse",
                  {"start_type": "strategy", "start_id": "MACD", "depth": 2})
    kinds = {n["entity_type"] for n in r["results"]}
    ids = [(n["entity_type"], n["entity_id"]) for n in r["results"]]
    check("8: traverse strategy->run->artifact/evidenze senza nodi duplicati",
          {"strategy", "run", "evidence_claim"} <= kinds and
          len(ids) == len(set(ids)) and r["edges"] == sorted(r["edges"]))

    r1 = run_query(kb, "strategy_by_id", {"strategy_id": "NON_ESISTE"})
    r2 = run_query(kb, "tipo_inventato", {})
    r3 = run_query(kb, "baseline_availability", {"state": "stato_inventato"})
    r4 = run_query(kb, "runs_by_round", {"round": BASELINE_ROUND + "-x"})
    check("9: errori deterministici (unknown_id/unknown_query_type/invalid_filter)",
          r1["error"]["code"] == "unknown_id" and
          r2["error"]["code"] == "unknown_query_type" and
          "supported" in r2["error"] and
          r3["error"]["code"] == "invalid_filter" and
          r4["error"]["code"] == "unknown_id")

    stable = True
    for qtype in sorted(QUERIES):
        params = {"strategy_by_id": {"strategy_id": "SAR"},
                  "run_by_id": {"run_id": rid},
                  "artifact_by_checksum": {"checksum": a["checksum"]},
                  "bug_by_id": {"bug_id": "BUG-024"},
                  "decision_by_id": {"decision_id": "DEC-009"},
                  "timeline_of_strategy": {"strategy_id": "SAR"},
                  "evidence_for_claim": {"claim_id": cid},
                  "evidence_for_subject": {"subject_type": "strategy",
                                           "subject_id": "SAR"},
                  "runs_by_round": {"round": BASELINE_ROUND},
                  "artifacts_by_type": {"artifact_type": "strategy_stats_csv"},
                  "documentation_of_strategy": {"strategy_id": "MACD"},
                  "commit_history_of_strategy": {"strategy_id": "MACD"},
                  "traverse": {"start_type": "run", "start_id": rid, "depth": 2},
                  }.get(qtype, {})
        if dumps(run_query(kb, qtype, dict(params))) != \
           dumps(run_query(kb, qtype, dict(params))):
            stable = False
    check("10: ogni query type e' idempotente e byte-identico su doppia esecuzione",
          stable)

    r = run_query(kb, "incomplete_runs", {})
    check("11: incomplete_runs coerente con runs_database",
          r["result_count"] == sum(1 for x in kb.runs.values() if not x["completed"]))

    errs = validate(kb)
    check("12: validazione completa (riferimenti, cicli, ordinamento)", errs == [])
    if errs:
        print("  errori:", errs[:5])

    r = run_query(kb, "strategies_by_timeline_coverage",
                  {"coverage": "complete_for_available_evidence"})
    check("13: strategies_by_timeline_coverage usa il campo canonico M4.1",
          r["status"] == "ok" and
          all(e["matched_fields"]["timeline_coverage"]
              == "complete_for_available_evidence" for e in r["results"]))

    r = run_query(kb, "missing_artifacts", {})
    check("14: missing_artifacts include la DQI S04 e il claim collegato",
          any(e["entity_id"].startswith("dqi-missing-S04") for e in r["results"]))

    n = len(fails)
    total = 14
    print(f"\nselftest: {'OK (%d/%d)' % (total, total) if not n else 'FALLITI: ' + ', '.join(fails)}")
    return 0 if not n else 1


# --------------------------------- CLI --------------------------------------
def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--validate" in argv:
        kb = KB()
        errs = validate(kb)
        print(dumps({"query_engine_version": QUERY_ENGINE_VERSION,
                     "validation": "ok" if not errs else "failed",
                     "errors": errs}))
        return 0 if not errs else 1
    if "--list" in argv or not argv:
        print(dumps({"query_engine_version": QUERY_ENGINE_VERSION,
                     "supported_queries": sorted(QUERIES)}))
        return 0
    qtype, params = argv[0], {}
    for tok in argv[1:]:
        if "=" not in tok:
            print(dumps(_err(qtype, {}, "invalid_filter",
                             f"parametro non valido: '{tok}' (atteso chiave=valore)")))
            return 1
        k, v = tok.split("=", 1)
        params[k] = v
    print(dumps(run_query(KB(), qtype, params)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
