"""NEXUS Chart — Reverse Discovery Lab V1: modalita' RETROSPECTIVE_DISCOVERY (selezione MANUALE).

Principi (reverse_discovery_lab_contract_v1.json):
  * il futuro e' visibile: queste schede sono DISCOVERY_ONLY e non alimentano mai un replay causale ne' una validazione;
  * associazione geometrica != spiegazione causale != edge predittivo: la scheda registra osservazioni e ipotesi, mai verdetti;
  * `epistemic_mode` (dalla sessione), `validation_status`, `discovered_at`, `author`, `revision` NON sono scrivibili dal client;
  * una geometria presente prima dell'evento non e' per questo conoscenza disponibile prima dell'evento: `available_at` non si
    retrodata e ogni collegamento riporta causal_knowledge = NOT_ESTABLISHED;
  * nessuna soglia sui grandi movimenti: origine, pivot e destinazione sono scelti dall'utente.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import time
from typing import Any, Dict, List, Optional

from chart_geometry import (GeometryError, GeometryStore, ID_RE, MAX_NAME, MAX_TEXT, TIMEFRAMES, _norm, _num, _str, canonical,
                            validate_anchor)

EVENT_SCHEMA = "nexus.chart_discovery_event.v1"
PIVOT_KINDS = ("HIGH", "LOW")
OUTCOMES = ("REVERSAL", "NO_REVERSAL")
GEOM_TIMING = ("BEFORE_EVENT_OBSERVABLE", "DURING_EVENT", "RETROSPECTIVELY_RECOGNIZED")
STRUCT_KINDS = ("IMPULSE", "CORRECTION", "GEOMETRY_GROUP")
SCALES = ("MAJOR", "INTERMEDIATE", "MINOR", "UNCLASSIFIED")
HYP_STATUS = ("OPEN", "SUPPORTED_BY_OBSERVATION", "CONTRADICTED_BY_OBSERVATION", "DISCARDED")
ANALOG_KINDS = ("ANALOG_WITH_REVERSAL", "ANALOG_NO_REVERSAL", "RELATED")
CLASSIFICATIONS = ("UNCLASSIFIED", "MAJOR_REVERSAL", "INTERMEDIATE_REVERSAL", "MINOR_REVERSAL", "FALSE_START", "CONTINUATION")
STATUSES = ("ACTIVE", "ARCHIVED")
VALIDATION_STATUS = "NOT_VALIDATED"          # unico valore ammesso in RETROSPECTIVE_DISCOVERY
EVENT_KEYS = {"name", "dataset_id", "source", "symbol", "clock_basis", "timeframe_observation", "outcome", "pivot", "origin", "destination",
              "units", "classification", "size_class", "geometries", "structures", "annotations", "hypotheses", "evidence_for",
              "evidence_against", "analog_links", "status"}
RESEARCH_KEYS = {"name", "dataset_id", "symbol", "interval", "layout", "units", "focus_event_id"}
RENDER_ONLY = {"geometry", "geometry_available_at", "causal_knowledge", "derived"}   # campi di sola resa: ignorati se il client li rimanda
MAX_EVENTS = 500
MAX_ITEMS = 200

_SQL = """
CREATE TABLE IF NOT EXISTS chart_disc_events(
  owner TEXT NOT NULL, session_id TEXT NOT NULL, event_id TEXT NOT NULL, revision INTEGER NOT NULL,
  created_at REAL NOT NULL, revised_at REAL NOT NULL, author TEXT NOT NULL, imported_by TEXT, body TEXT NOT NULL,
  PRIMARY KEY(owner, session_id, event_id, revision));
CREATE TABLE IF NOT EXISTS chart_disc_research(
  owner TEXT NOT NULL, session_id TEXT NOT NULL, updated_at REAL NOT NULL, body TEXT NOT NULL, PRIMARY KEY(owner, session_id));
"""


def _anchor(a: Any, name: str, *, nullable: bool = False) -> Optional[Dict[str, Any]]:
    if a is None:
        if nullable:
            return None
        raise GeometryError("INVALID_EVENT", f"{name} obbligatorio")
    if not isinstance(a, dict):
        raise GeometryError("INVALID_EVENT", f"{name} deve essere un oggetto")
    a = {k: v for k, v in a.items() if k != "kind"}
    return validate_anchor(a, name, 0)


def _units(u: Any) -> Dict[str, Any]:
    """Prezzo, pip, point e tick size restano grandezze SEPARATE (null se non note)."""
    u = u or {}
    if not isinstance(u, dict) or set(u) - {"pip_size", "point", "tick_size"}:
        raise GeometryError("INVALID_UNITS", "units: ammessi pip_size, point, tick_size")
    out: Dict[str, Any] = {}
    for k in ("pip_size", "point", "tick_size"):
        v = u.get(k)
        if v is None:
            out[k] = None
            continue
        v = _num(v, f"units.{k}")
        if not (0 < v <= 1000):
            raise GeometryError("INVALID_UNITS", f"units.{k} fuori range")
        out[k] = v
    return out


def _stamp(items: Any, old: Optional[List[Dict[str, Any]]], now: float, name: str, fields: set, check) -> List[Dict[str, Any]]:
    """Normalizza una lista di voci: id stabile, created_at server-side (mai dal client), campi ammessi."""
    if items is None:
        return []
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise GeometryError("INVALID_EVENT", f"{name}: lista di massimo {MAX_ITEMS} elementi")
    old_by = {o["id"]: o for o in (old or [])}
    out, seen = [], set()
    for it in items:
        if isinstance(it, dict):
            it = {k: v for k, v in it.items() if k not in RENDER_ONLY}
        if not isinstance(it, dict) or set(it) - (fields | {"id", "created_at"}):
            raise GeometryError("UNKNOWN_FIELD", f"{name}: campi ammessi {sorted(fields | {'id'})}")
        iid = it.get("id")
        if iid is not None and (not isinstance(iid, str) or not ID_RE.match(iid)):
            raise GeometryError("INVALID_ID", f"{name}: id non valido")
        iid = iid or ("I" + secrets.token_hex(5))
        if iid in seen:
            raise GeometryError("INVALID_EVENT", f"{name}: id duplicato {iid}")
        seen.add(iid)
        rec = check({k: v for k, v in it.items() if k not in ("id", "created_at")})
        rec["id"] = iid
        rec["created_at"] = old_by[iid]["created_at"] if iid in old_by else now
        out.append(rec)
    return out


class DiscoveryStore:
    def __init__(self, geo: GeometryStore):
        self.geo = geo
        with geo._c() as c:
            c.executescript(_SQL)

    @staticmethod
    def _now() -> float:
        return round(time.time(), 3)

    # ------------------------------------------------------------------ ricerca (stato della sessione di scoperta)
    def get_research(self, owner: str, sid: str) -> Dict[str, Any]:
        self.geo.get_session_meta(owner, sid)
        with self.geo._c() as c:
            r = c.execute("SELECT * FROM chart_disc_research WHERE owner=? AND session_id=?", (owner, sid)).fetchone()
        base = {"session_id": sid, "epistemic_mode": self.geo.session_mode(owner, sid), "validation_status": VALIDATION_STATUS}
        if not r:
            return {**base, "research": None, "updated_at": None}
        return {**base, "research": json.loads(r["body"]), "updated_at": r["updated_at"]}

    def put_research(self, owner: str, sid: str, body: Any) -> Dict[str, Any]:
        self.geo.get_session_meta(owner, sid)
        if not isinstance(body, dict) or set(body) - RESEARCH_KEYS:
            raise GeometryError("UNKNOWN_FIELD", f"research: campi ammessi {sorted(RESEARCH_KEYS)}")
        out: Dict[str, Any] = {"name": _str(body.get("name", ""), "name", MAX_NAME),
                               "dataset_id": _str(body.get("dataset_id", ""), "dataset_id", 200),
                               "symbol": _str(body.get("symbol", ""), "symbol", 32).upper(),
                               "units": _units(body.get("units")),
                               "focus_event_id": body.get("focus_event_id")}
        if out["focus_event_id"] is not None and not ID_RE.match(str(out["focus_event_id"])):
            raise GeometryError("INVALID_ID", "focus_event_id non valido")
        iv = body.get("interval")
        if iv is not None:
            if not isinstance(iv, dict) or set(iv) - {"from_t", "to_t"}:
                raise GeometryError("INVALID_INTERVAL", "interval: from_t, to_t")
            a, b = iv.get("from_t"), iv.get("to_t")
            for v in (a, b):
                if isinstance(v, bool) or not isinstance(v, int):
                    raise GeometryError("INVALID_INTERVAL", "from_t/to_t interi (epoch secondi)")
            if not a < b:
                raise GeometryError("INVALID_INTERVAL", "from_t deve precedere to_t")
            iv = {"from_t": a, "to_t": b}
        out["interval"] = iv      # selezione dell'utente: NON e' un confine di autorizzazione (la guardia di partizione resta unica)
        lay = body.get("layout") or {"count": 1, "charts": [{"tf": "H4"}], "sync": {"time_range": True, "crosshair": True, "symbol": True}}
        if not isinstance(lay, dict) or set(lay) - {"count", "charts", "sync"}:
            raise GeometryError("INVALID_LAYOUT", "layout: count, charts, sync")
        n = lay.get("count")
        charts = lay.get("charts")
        if isinstance(n, bool) or n not in (1, 2, 3, 4) or not isinstance(charts, list) or len(charts) != n:
            raise GeometryError("INVALID_LAYOUT", "count in 1..4 e charts di pari lunghezza")
        cl = []
        for ch in charts:
            if not isinstance(ch, dict) or set(ch) - {"tf", "linked"} or ch.get("tf") not in TIMEFRAMES:
                raise GeometryError("INVALID_LAYOUT", f"chart: tf in {sorted(TIMEFRAMES)}")
            cl.append({"tf": ch["tf"], "linked": bool(ch.get("linked", True))})
        sy = lay.get("sync") or {}
        if not isinstance(sy, dict) or set(sy) - {"time_range", "crosshair", "symbol"} or any(not isinstance(v, bool) for v in sy.values()):
            raise GeometryError("INVALID_LAYOUT", "sync: time_range, crosshair, symbol booleani")
        out["layout"] = {"count": n, "charts": cl, "sync": {"time_range": sy.get("time_range", True), "crosshair": sy.get("crosshair", True), "symbol": sy.get("symbol", True)}}
        ts = self._now()
        with self.geo._c() as c:
            c.execute("INSERT OR REPLACE INTO chart_disc_research VALUES(?,?,?,?)", (owner, sid, ts, canonical(out)))
        return self.get_research(owner, sid)

    # ------------------------------------------------------------------ validazione evento
    def _validate(self, owner: str, sid: str, body: Dict[str, Any], old: Optional[Dict[str, Any]], *, defer_refs: Optional[set] = None,
                  self_id: Optional[str] = None) -> Dict[str, Any]:
        if not isinstance(body, dict) or set(body) - EVENT_KEYS:
            raise GeometryError("UNKNOWN_FIELD", f"campi non ammessi: {sorted(set(body) - EVENT_KEYS)} (epistemic_mode, validation_status, autore e date sono del server)"
                                if isinstance(body, dict) else "corpo non valido")
        m = {**(old or {}), **body}
        now = self._now()
        pv = m.get("pivot")
        if not isinstance(pv, dict) or pv.get("kind") not in PIVOT_KINDS:
            raise GeometryError("INVALID_EVENT", f"pivot richiede kind in {PIVOT_KINDS}")
        pivot = {**_anchor(pv, "pivot"), "kind": pv["kind"]}
        origin = _anchor(m.get("origin"), "origin", nullable=True)
        dest = _anchor(m.get("destination"), "destination", nullable=True)
        outcome = m.get("outcome", "REVERSAL")
        if outcome not in OUTCOMES:
            raise GeometryError("INVALID_EVENT", f"outcome in {OUTCOMES}")
        if origin and not origin["t"] < pivot["t"]:
            raise GeometryError("INVALID_EVENT", "l'origine deve precedere il pivot")
        if dest and not pivot["t"] < dest["t"]:
            raise GeometryError("INVALID_EVENT", "la destinazione deve seguire il pivot")
        if outcome == "REVERSAL":                              # coerenza geometrica minima, nessuna soglia di ampiezza
            hi = pivot["kind"] == "HIGH"
            if origin and not (origin["price"] < pivot["price"] if hi else origin["price"] > pivot["price"]):
                raise GeometryError("INVALID_EVENT", "origine incoerente con la direzione precedente al pivot")
            if dest and not (dest["price"] < pivot["price"] if hi else dest["price"] > pivot["price"]):
                raise GeometryError("INVALID_EVENT", "destinazione incoerente con un'inversione")
        tf = m.get("timeframe_observation")
        if tf not in TIMEFRAMES:
            raise GeometryError("INVALID_TIMEFRAME", f"timeframe_observation in {sorted(TIMEFRAMES)}")
        cls = m.get("classification", "UNCLASSIFIED")
        sc = m.get("size_class", "UNCLASSIFIED")
        status = m.get("status", "ACTIVE")
        if cls not in CLASSIFICATIONS or sc not in SCALES or status not in STATUSES:
            raise GeometryError("INVALID_EVENT", "classification/size_class/status non validi")
        og = old or {}
        geoms = self._geometries(owner, sid, m.get("geometries"), og.get("geometries"), now)
        structs = self._structures(owner, sid, m.get("structures"), og.get("structures"), now)
        anns = _stamp(m.get("annotations"), og.get("annotations"), now, "annotations", {"text"}, lambda r: {"text": _str(r.get("text", ""), "text", MAX_TEXT, allow_empty=False)})
        def hyp(r: Dict[str, Any]) -> Dict[str, Any]:
            st = r.get("status", "OPEN")
            if st not in HYP_STATUS:
                raise GeometryError("INVALID_EVENT", f"hypothesis.status in {HYP_STATUS}")
            return {"text": _str(r.get("text", ""), "text", MAX_TEXT, allow_empty=False), "status": st}
        hyps = _stamp(m.get("hypotheses"), og.get("hypotheses"), now, "hypotheses", {"text", "status"}, hyp)

        def ev(r: Dict[str, Any]) -> Dict[str, Any]:
            gid = r.get("geometry_id")
            if gid is not None:
                if not ID_RE.match(str(gid)):
                    raise GeometryError("INVALID_ID", "geometry_id non valido")
                self.geo.get_object(owner, sid, gid)
            return {"text": _str(r.get("text", ""), "text", MAX_TEXT, allow_empty=False), "geometry_id": gid}
        ef = _stamp(m.get("evidence_for"), og.get("evidence_for"), now, "evidence_for", {"text", "geometry_id"}, ev)
        ea = _stamp(m.get("evidence_against"), og.get("evidence_against"), now, "evidence_against", {"text", "geometry_id"}, ev)
        known = defer_refs

        def an(r: Dict[str, Any]) -> Dict[str, Any]:
            eid = r.get("event_id")
            if not isinstance(eid, str) or not ID_RE.match(eid) or eid == self_id:
                raise GeometryError("INVALID_EVENT", "analog_links: event_id non valido")
            if r.get("kind") not in ANALOG_KINDS:
                raise GeometryError("INVALID_EVENT", f"analog_links.kind in {ANALOG_KINDS}")
            if known is not None:
                if eid not in known:
                    raise GeometryError("INVALID_EVENT", "analog_links: evento non presente nel documento")
            else:
                self.get_event(owner, sid, eid, render=False)
            return {"event_id": eid, "kind": r["kind"], "note": _str(r.get("note", ""), "note", 500)}
        analogs = _stamp(m.get("analog_links"), og.get("analog_links"), now, "analog_links", {"event_id", "kind", "note"}, an)
        if len({a["event_id"] for a in analogs}) != len(analogs):
            raise GeometryError("INVALID_EVENT", "analog_links: evento ripetuto")
        out = {"name": _str(m.get("name", ""), "name", MAX_NAME), "dataset_id": _str(m.get("dataset_id", ""), "dataset_id", 200),
               "source": _str(m.get("source", ""), "source", 80), "symbol": _str(m.get("symbol", ""), "symbol", 32, allow_empty=False).upper(),
               "clock_basis": _str(m.get("clock_basis", ""), "clock_basis", 120), "timeframe_observation": tf, "outcome": outcome,
               "pivot": pivot, "origin": origin, "destination": dest, "units": _units(m.get("units")), "classification": cls, "size_class": sc,
               "geometries": geoms, "structures": structs, "annotations": anns, "hypotheses": hyps, "evidence_for": ef, "evidence_against": ea,
               "analog_links": analogs, "status": status}
        if len(canonical(out)) > 200_000:
            raise GeometryError("BODY_TOO_LARGE", "scheda evento troppo grande")
        return out

    def _geometries(self, owner, sid, items, old, now):
        def chk(r):
            gid = r.get("geometry_id")
            if not isinstance(gid, str) or not ID_RE.match(gid):
                raise GeometryError("INVALID_ID", "geometries: geometry_id non valido")
            if r.get("timing") not in GEOM_TIMING:
                raise GeometryError("INVALID_EVENT", f"geometries.timing in {GEOM_TIMING}")
            self.geo.get_object(owner, sid, gid)                    # deve esistere nella stessa sessione dello stesso utente
            return {"geometry_id": gid, "timing": r["timing"], "note": _str(r.get("note", ""), "note", 500)}
        out = _stamp(items, old, now, "geometries", {"geometry_id", "timing", "note"}, chk)
        if len({(g["geometry_id"], g["timing"]) for g in out}) != len(out):
            raise GeometryError("INVALID_EVENT", "geometries: collegamento ripetuto")
        return out

    def _structures(self, owner, sid, items, old, now):
        def chk(r):
            if r.get("kind") not in STRUCT_KINDS or r.get("scale", "UNCLASSIFIED") not in SCALES:
                raise GeometryError("INVALID_EVENT", f"structures: kind in {STRUCT_KINDS}, scale in {SCALES}")
            o, d = _anchor(r.get("origin"), "structure.origin"), _anchor(r.get("destination"), "structure.destination")
            if o["t"] == d["t"] and o["price"] == d["price"]:
                raise GeometryError("INVALID_EVENT", "structure: origine e destinazione coincidono")
            gids = r.get("geometry_ids") or []
            if not isinstance(gids, list) or len(gids) > 50 or any(not isinstance(g, str) or not ID_RE.match(g) for g in gids):
                raise GeometryError("INVALID_EVENT", "structure.geometry_ids non valido")
            for g in gids:
                self.geo.get_object(owner, sid, g)
            pid = r.get("parent_id")
            if pid is not None and (not isinstance(pid, str) or not ID_RE.match(pid)):
                raise GeometryError("INVALID_ID", "parent_id non valido")
            return {"kind": r["kind"], "scale": r.get("scale", "UNCLASSIFIED"), "parent_id": pid, "origin": o, "destination": d,
                    "geometry_ids": gids, "note": _str(r.get("note", ""), "note", MAX_TEXT)}
        out = _stamp(items, old, now, "structures", {"kind", "scale", "parent_id", "origin", "destination", "geometry_ids", "note"}, chk)
        ids = {s["id"] for s in out}
        parent = {s["id"]: s["parent_id"] for s in out}
        for s in out:
            if s["parent_id"] is not None and s["parent_id"] not in ids:
                raise GeometryError("INVALID_EVENT", f"structure {s['id']}: parent_id inesistente")
            seen, cur = set(), s["id"]
            while cur is not None:                               # nessun ciclo padre-figlio
                if cur in seen:
                    raise GeometryError("INVALID_EVENT", "structures: ciclo nelle relazioni padre-figlio")
                seen.add(cur)
                cur = parent.get(cur)
        return out

    # ------------------------------------------------------------------ rendering con grandezze derivate (mai scritte dal client)
    @staticmethod
    def _leg(a: Dict[str, Any], b: Dict[str, Any], pip: Optional[float]) -> Dict[str, Any]:
        amp = abs(b["price"] - a["price"])
        return {"direction": "UP" if b["price"] > a["price"] else "DOWN" if b["price"] < a["price"] else "FLAT",
                "amplitude_price": amp, "amplitude_pips": (amp / pip) if pip else None, "duration_s": b["t"] - a["t"]}

    def _render(self, owner: str, sid: str, row: sqlite3.Row, geoms_by_id: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        b = json.loads(row["body"])
        pip = (b.get("units") or {}).get("pip_size")
        pv = b["pivot"]
        derived: Dict[str, Any] = {"prior_direction": "UP" if pv["kind"] == "HIGH" else "DOWN"}
        derived["next_direction"] = ("DOWN" if pv["kind"] == "HIGH" else "UP") if b["outcome"] == "REVERSAL" else derived["prior_direction"]
        derived["prior_leg"] = self._leg(b["origin"], pv, pip) if b.get("origin") else None
        derived["next_leg"] = self._leg(pv, b["destination"], pip) if b.get("destination") else None
        for s in b["structures"]:
            s["derived"] = self._leg(s["origin"], s["destination"], pip)
        if geoms_by_id is None:
            geoms_by_id = {g["geometry_id"]: g for g in self.geo.list_objects(owner, sid, include_archived=True)}
        for lk in b["geometries"]:
            g = geoms_by_id.get(lk["geometry_id"])
            lk["geometry"] = None if not g else {"type": g["type"], "semantic_class": g["semantic"]["class"], "name": g["name"], "anchors": [[a["t"], a["price"]] for a in g["anchors"]],
                                                  "status": g["status"], "epistemic_mode": g["epistemic_mode"]}
            lk["geometry_available_at"] = g["available_at"] if g else None      # istante REALE di creazione: mai retrodatato
            lk["causal_knowledge"] = "NOT_ESTABLISHED"                           # presente nel grafico != conoscibile prima dell'evento
        return {"schema": EVENT_SCHEMA, "event_id": row["event_id"], "session_id": sid, "revision": row["revision"], "discovered_at": row["created_at"],
                "revised_at": row["revised_at"], "author": row["author"], "imported_by": row["imported_by"], "author_verified": row["imported_by"] is None,
                "epistemic_mode": self.geo.session_mode(owner, sid), "validation_status": VALIDATION_STATUS, "memory_domain": "DISCOVERY_NOTES",
                "output_label": "DISCOVERY_ONLY", **b, "derived": derived}

    def _latest(self, c, owner, sid, eid):
        return c.execute("SELECT * FROM chart_disc_events WHERE owner=? AND session_id=? AND event_id=? ORDER BY revision DESC LIMIT 1", (owner, sid, eid)).fetchone()

    # ------------------------------------------------------------------ CRUD
    def create_event(self, owner: str, sid: str, body: Any, *, event_id: Optional[str] = None, preserve: Optional[Dict[str, Any]] = None,
                     defer_refs: Optional[set] = None) -> Dict[str, Any]:
        self.geo.get_session_meta(owner, sid)
        eid = event_id or "E" + secrets.token_hex(7)
        if not ID_RE.match(eid):
            raise GeometryError("INVALID_ID", "event_id non valido")
        clean = self._validate(owner, sid, body, None, defer_refs=defer_refs, self_id=eid)
        with self.geo._c() as c:
            if self._latest(c, owner, sid, eid):
                raise GeometryError("EVENT_EXISTS", "event_id gia' presente", 409)
            if c.execute("SELECT COUNT(DISTINCT event_id) FROM chart_disc_events WHERE owner=? AND session_id=?", (owner, sid)).fetchone()[0] >= MAX_EVENTS:
                raise GeometryError("LIMIT_REACHED", "numero massimo di eventi", 409)
            ts = self._now()
            created, author, imp = ts, owner, None
            if preserve:                                    # import: autore e data di scoperta dichiarati; l'importatore effettivo e' a parte
                created = _num(preserve["discovered_at"], "discovered_at")
                author = _str(preserve["author"], "author", 80, allow_empty=False)
                imp = owner
            c.execute("INSERT INTO chart_disc_events VALUES(?,?,?,?,?,?,?,?,?)", (owner, sid, eid, 1, created, ts, author, imp, canonical(clean)))
            c.execute("UPDATE chart_geo_sessions SET updated_at=? WHERE owner=? AND session_id=?", (ts, owner, sid))
        return self.get_event(owner, sid, eid)

    def get_event(self, owner: str, sid: str, eid: str, *, render: bool = True) -> Dict[str, Any]:
        self.geo.get_session_meta(owner, sid)
        with self.geo._c() as c:
            r = self._latest(c, owner, sid, eid)
        if not r:
            raise GeometryError("EVENT_NOT_FOUND", "evento inesistente", 404)
        return self._render(owner, sid, r) if render else {"event_id": eid}

    def history(self, owner: str, sid: str, eid: str) -> List[Dict[str, Any]]:
        self.geo.get_session_meta(owner, sid)
        with self.geo._c() as c:
            rows = c.execute("SELECT * FROM chart_disc_events WHERE owner=? AND session_id=? AND event_id=? ORDER BY revision", (owner, sid, eid)).fetchall()
        if not rows:
            raise GeometryError("EVENT_NOT_FOUND", "evento inesistente", 404)
        gm = {g["geometry_id"]: g for g in self.geo.list_objects(owner, sid, include_archived=True)}
        return [self._render(owner, sid, r, gm) for r in rows]

    def list_events(self, owner: str, sid: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        self.geo.get_session_meta(owner, sid)
        with self.geo._c() as c:
            ids = [r[0] for r in c.execute("SELECT DISTINCT event_id FROM chart_disc_events WHERE owner=? AND session_id=? ORDER BY event_id", (owner, sid))]
            rows = [self._latest(c, owner, sid, i) for i in ids]
        gm = {g["geometry_id"]: g for g in self.geo.list_objects(owner, sid, include_archived=True)}
        out = [self._render(owner, sid, r, gm) for r in rows]
        out = [e for e in out if include_archived or e["status"] != "ARCHIVED"]
        return sorted(out, key=lambda e: (e["discovered_at"], e["event_id"]))

    def update_event(self, owner: str, sid: str, eid: str, patch: Any, expected_revision: int) -> Dict[str, Any]:
        cur = self.get_event(owner, sid, eid)
        if cur["revision"] != expected_revision:
            raise GeometryError("REVISION_CONFLICT", f"revisione attuale {cur['revision']}, attesa {expected_revision}", 409)
        existing = {k: cur[k] for k in EVENT_KEYS if k in cur}
        clean = self._validate(owner, sid, patch, existing, self_id=eid)
        with self.geo._c() as c:
            try:
                c.execute("INSERT INTO chart_disc_events VALUES(?,?,?,?,?,?,?,?,?)",
                          (owner, sid, eid, cur["revision"] + 1, cur["discovered_at"], self._now(), cur["author"], cur["imported_by"], canonical(clean)))
            except sqlite3.IntegrityError:
                raise GeometryError("REVISION_CONFLICT", "modifica concorrente", 409)
            c.execute("UPDATE chart_geo_sessions SET updated_at=? WHERE owner=? AND session_id=?", (self._now(), owner, sid))
        return self.get_event(owner, sid, eid)

    def set_status(self, owner: str, sid: str, eid: str, expected_revision: int, status: str) -> Dict[str, Any]:
        return self.update_event(owner, sid, eid, {"status": status}, expected_revision)

    # ------------------------------------------------------------------ export / import (parte dello stesso documento con sha256)
    def export_part(self, owner: str, sid: str) -> Dict[str, Any]:
        return {"events": self.list_events(owner, sid, include_archived=True), "research": self.get_research(owner, sid)["research"]}

    def import_part(self, owner: str, sid: str, events: Any, research: Any) -> None:
        if events is not None and not isinstance(events, list):
            raise GeometryError("INVALID_IMPORT", "events non valido")
        events = events or []
        ids = {e.get("event_id") for e in events if isinstance(e, dict)}
        for e in events:
            if not isinstance(e, dict) or e.get("schema") != EVENT_SCHEMA or e.get("epistemic_mode") != "RETROSPECTIVE_DISCOVERY":
                raise GeometryError("INVALID_IMPORT", "evento non riconosciuto o modalita' epistemica non importabile")
            body = {k: e[k] for k in EVENT_KEYS if k in e}
            status = body.get("status", "ACTIVE")
            body["status"] = "ACTIVE"
            body["geometries"] = [{k: v for k, v in g.items() if k in {"geometry_id", "timing", "note", "id", "created_at"}} for g in body.get("geometries", [])]
            self.create_event(owner, sid, body, event_id=e["event_id"], defer_refs=ids,
                              preserve={"discovered_at": e.get("discovered_at"), "author": e.get("author")})
            if status == "ARCHIVED":
                cur = self.get_event(owner, sid, e["event_id"])
                self.set_status(owner, sid, e["event_id"], cur["revision"], "ARCHIVED")
        if research:
            self.put_research(owner, sid, research)


def comparison(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Confronto descrittivo fra schede. NON produce frequenze ne' percentuali: i casi sono scelti a mano e non sono un campione."""
    rows = []
    for e in events:
        d = e["derived"]
        classes: Dict[str, int] = {}
        for lk in e["geometries"]:
            g = lk.get("geometry")
            if g:
                classes[g["semantic_class"]] = classes.get(g["semantic_class"], 0) + 1
        scales: Dict[str, int] = {}
        for s in e["structures"]:
            scales[s["scale"]] = scales.get(s["scale"], 0) + 1
        rows.append({"event_id": e["event_id"], "name": e["name"], "outcome": e["outcome"], "pivot": e["pivot"], "prior_leg": d["prior_leg"], "next_leg": d["next_leg"],
                     "geometry_by_timing": {t: sum(1 for g in e["geometries"] if g["timing"] == t) for t in GEOM_TIMING},
                     "geometry_by_class": classes, "structures_by_scale": scales, "annotations": [a["text"] for a in e["annotations"]],
                     "hypotheses": [{"text": h["text"], "status": h["status"]} for h in e["hypotheses"]],
                     "evidence_for": len(e["evidence_for"]), "evidence_against": len(e["evidence_against"]),
                     "analogs": {k: sum(1 for a in e["analog_links"] if a["kind"] == k) for k in ANALOG_KINDS}})
    return {"events": rows, "disclaimer": "Confronto descrittivo di casi selezionati manualmente: nessuna frequenza, nessun p-value, nessuna validazione. Le frequenze di casi scelti a mano non sono prova statistica."}
