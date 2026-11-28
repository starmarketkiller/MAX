"""NEXUS Chart — geometrie manuali e memoria grafica persistente (GATE 04/05).

Principi (vedi GEOMETRY_CONTRACT di CHART-MASTER-01):
  * ancoraggi in coordinate di dato (t epoch-secondi, price): MAI pixel;
  * forma (`type`) distinta dal significato attribuito dall'utente (`semantic.class`);
  * una geometria NON e' un segnale operativo: nessun campo ordine/segnale e' accettato;
  * append-only per revisioni: modifica = nuova revisione, eliminazione = revisione ARCHIVED (reversibile);
  * ogni query e' filtrata per `owner` (isolamento fra utenti);
  * memoria GRAFICA separata dalla futura memoria EMPIRICA delle reazioni (campo `memory_domain`).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SCHEMA = "nexus.chart_geometry_session.v1"
GEOMETRY_SCHEMA = "nexus.chart_geometry_object.v1"
VOCAB_PATH = Path(__file__).resolve().parent / "chart_geometry_vocabulary.json"
VOCAB: Dict[str, Any] = json.loads(VOCAB_PATH.read_text(encoding="utf-8"))

MAX_GEOMETRIES_PER_SESSION = 2000
MAX_SESSIONS_PER_OWNER = 200
MAX_TEXT = 2000
MAX_NAME = 120
T_MIN, T_MAX = 946684800, 4102444800          # 2000-01-01 .. 2100-01-01 (epoch secondi)
PRICE_ABS_MAX = 1e9
ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
OHLC = tuple(VOCAB["anchor_fields"])
LINE_SHAPES = {"trendline", "ray", "extended_line"}
SEMANTIC_SHAPES = {
    "DIAG_BUY": LINE_SHAPES, "DIAG_SELL": LINE_SHAPES,
    "KEY_LEVEL_CLOSES": {"hline", "price_band"}, "LIQUIDITY_SPIKES": {"hline", "price_band"},
    "ZONE_BUY_TO_SELL": {"rectangle", "price_band"}, "ZONE_SELL_TO_BUY": {"rectangle", "price_band"},
    "INNER_SPACE": {"rectangle", "price_band"}, "REACTION_ZONE": {"rectangle", "price_band"},
    "CONTINUATION_ZONE": {"rectangle", "price_band"},
}
TOP_KEYS = {"type", "symbol", "dataset_id", "source", "clock_basis", "timeframe_origin", "anchors", "semantic", "name",
            "description", "style", "text", "links", "evidence", "status", "fib_levels"}
STYLE_KEYS = {"color", "width", "dash", "visible", "locked", "layer", "fill_opacity", "extend", "show_labels"}
DEFAULT_STYLE = {"color": "#2962ff", "width": 2, "dash": "solid", "visible": True, "locked": False,
                 "layer": "default", "fill_opacity": 0.15, "extend": "none", "show_labels": True}
TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"}


class GeometryError(Exception):
    def __init__(self, code: str, message: str = "", status: int = 422):
        super().__init__(f"{code}: {message}")
        self.code, self.message, self.status = code, message, status


def _norm(o: Any) -> Any:
    """Forma numerica canonica: un float di valore intero e' un intero (Python serializza 2.0, JavaScript 2).
    Senza questo, un export che passa dal browser non rispetta piu' lo sha256 calcolato dal server."""
    if isinstance(o, float) and o.is_integer() and abs(o) < 2 ** 53:
        return int(o)
    if isinstance(o, dict):
        return {k: _norm(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_norm(v) for v in o]
    return o


def canonical(obj: Any) -> str:
    return json.dumps(_norm(obj), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_of(obj: Any) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def _num(v: Any, name: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise GeometryError("INVALID_NUMBER", f"{name} deve essere un numero finito")
    return float(v)


def _str(v: Any, name: str, maxlen: int, allow_empty: bool = True) -> str:
    if not isinstance(v, str):
        raise GeometryError("INVALID_TEXT", f"{name} deve essere testo")
    if len(v) > maxlen or (not allow_empty and not v.strip()):
        raise GeometryError("INVALID_TEXT", f"{name} vuoto o piu' lungo di {maxlen}")
    return v


def validate_anchor(a: Any, ttype: str, i: int) -> Dict[str, Any]:
    if not isinstance(a, dict):
        raise GeometryError("INVALID_ANCHOR", f"ancoraggio {i} non e' un oggetto")
    extra = set(a) - {"t", "price", "ref"}
    if extra:
        raise GeometryError("UNKNOWN_FIELD", f"ancoraggio {i}: campi non ammessi {sorted(extra)}")
    t = a.get("t")
    if isinstance(t, bool) or not isinstance(t, int) or not (T_MIN <= t <= T_MAX):
        raise GeometryError("INVALID_ANCHOR_TIME", f"ancoraggio {i}: t deve essere epoch-secondi interi (2000..2100)")
    price = _num(a.get("price"), f"ancoraggio {i}.price")
    if abs(price) > PRICE_ABS_MAX:
        raise GeometryError("INVALID_ANCHOR_PRICE", f"ancoraggio {i}: prezzo fuori range")
    ref = a.get("ref") or {"kind": "FREE"}
    if not isinstance(ref, dict) or ref.get("kind") not in VOCAB["anchor_ref_kinds"]:
        raise GeometryError("INVALID_ANCHOR_REF", f"ancoraggio {i}: ref.kind deve essere FREE o CANDLE")
    if set(ref) - {"kind", "bar_t", "field", "projection_id"}:
        raise GeometryError("UNKNOWN_FIELD", f"ancoraggio {i}: ref con campi non ammessi")
    if ref.get("projection_id") is not None:
        raise GeometryError("PROJECTION_NOT_DEFINED",
                            "le sei proiezioni delle candele non sono definite: projection_id deve restare null")
    out_ref: Dict[str, Any] = {"kind": ref["kind"], "projection_id": None}
    if ref["kind"] == "CANDLE":
        bt = ref.get("bar_t")
        if isinstance(bt, bool) or not isinstance(bt, int) or not (T_MIN <= bt <= T_MAX):
            raise GeometryError("INVALID_ANCHOR_REF", f"ancoraggio {i}: CANDLE richiede bar_t intero")
        if ref.get("field") not in OHLC:
            raise GeometryError("INVALID_ANCHOR_REF", f"ancoraggio {i}: field deve essere uno di {OHLC}")
        out_ref.update({"bar_t": bt, "field": ref["field"]})
    return {"t": t, "price": price, "ref": out_ref}


def validate_style(style: Any) -> Dict[str, Any]:
    out = dict(DEFAULT_STYLE)
    if style is None:
        return out
    if not isinstance(style, dict) or set(style) - STYLE_KEYS:
        raise GeometryError("INVALID_STYLE", f"style: campi ammessi {sorted(STYLE_KEYS)}")
    for k, v in style.items():
        if k == "color":
            if not isinstance(v, str) or not COLOR_RE.match(v):
                raise GeometryError("INVALID_STYLE", "color deve essere #rrggbb")
        elif k == "width":
            v = _num(v, "style.width")
            if not (0.5 <= v <= 8):
                raise GeometryError("INVALID_STYLE", "width fra 0.5 e 8")
        elif k == "dash":
            if v not in VOCAB["dashes"]:
                raise GeometryError("INVALID_STYLE", f"dash in {VOCAB['dashes']}")
        elif k in ("visible", "locked", "show_labels"):
            if not isinstance(v, bool):
                raise GeometryError("INVALID_STYLE", f"{k} deve essere booleano")
        elif k == "layer":
            if not isinstance(v, str) or not ID_RE.match(v):
                raise GeometryError("INVALID_STYLE", "layer: identificatore non valido")
        elif k == "fill_opacity":
            v = _num(v, "style.fill_opacity")
            if not (0 <= v <= 1):
                raise GeometryError("INVALID_STYLE", "fill_opacity fra 0 e 1")
        elif k == "extend":
            if v not in ("none", "right", "left", "both"):
                raise GeometryError("INVALID_STYLE", "extend in none/right/left/both")
        out[k] = v
    return out


def validate_body(body: Any, *, existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Valida un corpo di geometria e ne restituisce la forma canonica (senza campi di sistema)."""
    if not isinstance(body, dict):
        raise GeometryError("INVALID_BODY", "il corpo deve essere un oggetto")
    extra = set(body) - TOP_KEYS
    if extra:
        raise GeometryError("UNKNOWN_FIELD", f"campi non ammessi: {sorted(extra)} (nessun campo ordine/segnale e' previsto)")
    merged = dict(existing or {})
    merged.update(body)
    ttype = merged.get("type")
    spec = VOCAB["types"].get(ttype)
    if not spec:
        raise GeometryError("INVALID_TYPE", f"tipo non ammesso: {ttype!r}")
    if existing and body.get("type") not in (None, existing.get("type")):
        raise GeometryError("TYPE_IMMUTABLE", "il tipo non e' modificabile: creare una nuova geometria")
    anchors = merged.get("anchors")
    if not isinstance(anchors, list) or len(anchors) != spec["anchors"]:
        raise GeometryError("INVALID_ANCHOR_COUNT", f"{ttype} richiede esattamente {spec['anchors']} ancoraggi")
    anchors = [validate_anchor(a, ttype, i) for i, a in enumerate(anchors)]
    if spec["anchors"] >= 2 and ttype not in ("price_band",):
        if len({(a["t"], a["price"]) for a in anchors}) < spec["anchors"]:
            raise GeometryError("DEGENERATE_GEOMETRY", "gli ancoraggi devono essere distinti")
    if ttype in ("trendline", "ray", "extended_line", "rectangle", "fib_retracement", "ruler") and anchors[0]["t"] == anchors[1]["t"]:
        raise GeometryError("DEGENERATE_GEOMETRY", "una diagonale/rettangolo richiede due istanti diversi")
    if ttype == "price_band" and anchors[0]["price"] == anchors[1]["price"]:
        raise GeometryError("DEGENERATE_GEOMETRY", "la fascia richiede due prezzi diversi")
    sem = merged.get("semantic") or {"class": "NONE"}
    if not isinstance(sem, dict) or set(sem) - {"class", "note", "set_by"} or sem.get("set_by", "USER") != "USER":
        raise GeometryError("INVALID_SEMANTIC", "semantic: ammessi solo class e note (set_by e' sempre USER)")
    cls = sem.get("class", "NONE")
    if cls not in VOCAB["semantic_classes"]:
        raise GeometryError("INVALID_SEMANTIC", f"classe semantica sconosciuta: {cls!r}")
    if cls != "NONE" and ttype not in SEMANTIC_SHAPES[cls]:
        raise GeometryError("SEMANTIC_SHAPE_MISMATCH",
                            f"il significato {cls} non e' attribuibile alla forma {ttype} (ammesse: {sorted(SEMANTIC_SHAPES[cls])})")
    out_sem = {"class": cls, "set_by": "USER"}
    if sem.get("note"):
        out_sem["note"] = _str(sem["note"], "semantic.note", MAX_TEXT)
    symbol = _str(merged.get("symbol", ""), "symbol", 32, allow_empty=False)
    tf = merged.get("timeframe_origin")
    if tf not in TIMEFRAMES:
        raise GeometryError("INVALID_TIMEFRAME", f"timeframe_origin in {sorted(TIMEFRAMES)}")
    links = merged.get("links") or []
    if not isinstance(links, list) or len(links) > 50:
        raise GeometryError("INVALID_LINKS", "links: lista di massimo 50 elementi")
    out_links = []
    for ln in links:
        if (not isinstance(ln, dict) or set(ln) - {"geometry_id", "relation"} or not ID_RE.match(str(ln.get("geometry_id", "")))
                or ln.get("relation") not in VOCAB["link_relations"]):
            raise GeometryError("INVALID_LINKS", f"link non valido; relation in {VOCAB['link_relations']}")
        out_links.append({"geometry_id": ln["geometry_id"], "relation": ln["relation"]})
    ev = merged.get("evidence") or []
    if not isinstance(ev, list) or len(ev) > 50 or any(not isinstance(e, str) or len(e) > 200 for e in ev):
        raise GeometryError("INVALID_EVIDENCE", "evidence: lista di stringhe brevi")
    status = merged.get("status", "ACTIVE")
    if status not in VOCAB["statuses"]:
        raise GeometryError("INVALID_STATUS", f"status in {VOCAB['statuses']}")
    out: Dict[str, Any] = {
        "type": ttype, "symbol": symbol.upper(), "timeframe_origin": tf, "anchors": anchors, "semantic": out_sem,
        "dataset_id": _str(merged.get("dataset_id", ""), "dataset_id", 200),
        "source": _str(merged.get("source", ""), "source", 80),
        "clock_basis": _str(merged.get("clock_basis", ""), "clock_basis", 120),     # orologio degli orari originali degli ancoraggi
        "name": _str(merged.get("name", ""), "name", MAX_NAME),
        "description": _str(merged.get("description", ""), "description", MAX_TEXT),
        "style": validate_style(merged.get("style")),
        "links": out_links, "evidence": list(ev), "status": status,
    }
    if ttype == "text":
        out["text"] = _str(merged.get("text", ""), "text", MAX_TEXT, allow_empty=False)
    if ttype in ("fib_retracement", "fib_extension"):
        lv = merged.get("fib_levels", VOCAB["fib_defaults"][ttype])
        if not isinstance(lv, list) or not (1 <= len(lv) <= 20):
            raise GeometryError("INVALID_FIB_LEVELS", "fib_levels: da 1 a 20 valori numerici")
        out["fib_levels"] = [_num(x, "fib_levels") for x in lv]
        if any(abs(x) > 100 for x in out["fib_levels"]):
            raise GeometryError("INVALID_FIB_LEVELS", "livello fuori range (|x| <= 100)")
    if len(canonical(out)) > 16384:
        raise GeometryError("BODY_TOO_LARGE", "geometria oltre 16 KiB")
    return out


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS chart_geo_sessions(
  owner TEXT NOT NULL, session_id TEXT NOT NULL, name TEXT NOT NULL, symbol TEXT NOT NULL DEFAULT '',
  created_at REAL NOT NULL, updated_at REAL NOT NULL, PRIMARY KEY(owner, session_id));
CREATE TABLE IF NOT EXISTS chart_geo_layers(
  owner TEXT NOT NULL, session_id TEXT NOT NULL, layer_id TEXT NOT NULL, name TEXT NOT NULL,
  visible INTEGER NOT NULL DEFAULT 1, locked INTEGER NOT NULL DEFAULT 0, position INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(owner, session_id, layer_id));
CREATE TABLE IF NOT EXISTS chart_geo_revisions(
  owner TEXT NOT NULL, session_id TEXT NOT NULL, geometry_id TEXT NOT NULL, revision INTEGER NOT NULL,
  created_at REAL NOT NULL, available_at REAL NOT NULL, origin TEXT NOT NULL, author TEXT NOT NULL,
  body TEXT NOT NULL, PRIMARY KEY(owner, session_id, geometry_id, revision));
"""


class GeometryStore:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        with self._c() as c:
            c.executescript(_SCHEMA_SQL)

    def _c(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path, timeout=15)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA busy_timeout=15000")
        return c

    @staticmethod
    def _now() -> float:
        return round(time.time(), 3)

    # ---- sessioni ----
    def create_session(self, owner: str, name: str, symbol: str = "", session_id: Optional[str] = None) -> Dict[str, Any]:
        name = _str(name, "name", MAX_NAME, allow_empty=False)
        sid = session_id or "S" + secrets.token_hex(6)
        if not ID_RE.match(sid):
            raise GeometryError("INVALID_ID", "session_id non valido")
        with self._c() as c:
            n = c.execute("SELECT COUNT(*) FROM chart_geo_sessions WHERE owner=?", (owner,)).fetchone()[0]
            if n >= MAX_SESSIONS_PER_OWNER:
                raise GeometryError("LIMIT_REACHED", "numero massimo di sessioni raggiunto", 409)
            ts = self._now()
            try:
                c.execute("INSERT INTO chart_geo_sessions VALUES(?,?,?,?,?,?)", (owner, sid, name, symbol.upper()[:32], ts, ts))
            except sqlite3.IntegrityError:
                raise GeometryError("SESSION_EXISTS", "sessione gia' esistente", 409)
            c.execute("INSERT INTO chart_geo_layers VALUES(?,?,?,?,1,0,0)", (owner, sid, "default", "Livello 1"))
        return self.get_session_meta(owner, sid)

    def list_sessions(self, owner: str) -> List[Dict[str, Any]]:
        with self._c() as c:
            rows = c.execute("SELECT * FROM chart_geo_sessions WHERE owner=? ORDER BY updated_at DESC", (owner,)).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                d.pop("owner")
                d["object_count"] = self._count_active(c, owner, r["session_id"])
                out.append(d)
            return out

    def get_session_meta(self, owner: str, sid: str) -> Dict[str, Any]:
        with self._c() as c:
            r = c.execute("SELECT * FROM chart_geo_sessions WHERE owner=? AND session_id=?", (owner, sid)).fetchone()
        if not r:
            raise GeometryError("SESSION_NOT_FOUND", "sessione inesistente", 404)   # stesso errore per 'non tua' e 'non esiste'
        d = dict(r)
        d.pop("owner")
        return d

    def rename_session(self, owner: str, sid: str, name: str) -> Dict[str, Any]:
        self.get_session_meta(owner, sid)
        name = _str(name, "name", MAX_NAME, allow_empty=False)
        with self._c() as c:
            c.execute("UPDATE chart_geo_sessions SET name=?, updated_at=? WHERE owner=? AND session_id=?", (name, self._now(), owner, sid))
        return self.get_session_meta(owner, sid)

    @staticmethod
    def _count_active(c: sqlite3.Connection, owner: str, sid: str) -> int:
        n = 0
        for (b,) in c.execute(
                "SELECT r.body FROM chart_geo_revisions r JOIN (SELECT geometry_id, MAX(revision) m FROM chart_geo_revisions "
                "WHERE owner=? AND session_id=? GROUP BY geometry_id) l ON r.geometry_id=l.geometry_id AND r.revision=l.m "
                "WHERE r.owner=? AND r.session_id=?", (owner, sid, owner, sid)):
            if json.loads(b).get("status") != "ARCHIVED":
                n += 1
        return n

    # ---- layer ----
    def list_layers(self, owner: str, sid: str) -> List[Dict[str, Any]]:
        self.get_session_meta(owner, sid)
        with self._c() as c:
            rows = c.execute("SELECT layer_id,name,visible,locked,position FROM chart_geo_layers WHERE owner=? AND session_id=? "
                             "ORDER BY position, layer_id", (owner, sid)).fetchall()
        return [{"layer_id": r["layer_id"], "name": r["name"], "visible": bool(r["visible"]),
                 "locked": bool(r["locked"]), "position": r["position"]} for r in rows]

    def upsert_layer(self, owner: str, sid: str, layer_id: str, patch: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.get_session_meta(owner, sid)
        if not ID_RE.match(layer_id):
            raise GeometryError("INVALID_ID", "layer_id non valido")
        if set(patch) - {"name", "visible", "locked", "position"}:
            raise GeometryError("UNKNOWN_FIELD", "layer: ammessi name, visible, locked, position")
        cur = next((l for l in self.list_layers(owner, sid) if l["layer_id"] == layer_id), None)
        new = dict(cur or {"layer_id": layer_id, "name": layer_id, "visible": True, "locked": False, "position": 99})
        for k, v in patch.items():
            if k == "name":
                v = _str(v, "name", 60, allow_empty=False)
            elif k in ("visible", "locked"):
                if not isinstance(v, bool):
                    raise GeometryError("INVALID_LAYER", f"{k} booleano")
            elif k == "position":
                if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v <= 999):
                    raise GeometryError("INVALID_LAYER", "position 0..999")
            new[k] = v
        with self._c() as c:
            if not cur and len(self.list_layers(owner, sid)) >= 30:
                raise GeometryError("LIMIT_REACHED", "massimo 30 livelli", 409)
            c.execute("INSERT OR REPLACE INTO chart_geo_layers VALUES(?,?,?,?,?,?,?)",
                      (owner, sid, layer_id, new["name"], int(new["visible"]), int(new["locked"]), new["position"]))
            c.execute("UPDATE chart_geo_sessions SET updated_at=? WHERE owner=? AND session_id=?", (self._now(), owner, sid))
        return self.list_layers(owner, sid)

    # ---- geometrie ----
    @staticmethod
    def _row_to_obj(r: sqlite3.Row, sid: str, gid: str) -> Dict[str, Any]:
        body = json.loads(r["body"])
        return {"schema": GEOMETRY_SCHEMA, "geometry_id": gid, "session_id": sid, "revision": r["revision"],
                "created_at": r["created_at"], "available_at": r["available_at"], "origin": r["origin"],
                "author": r["author"], "memory_domain": "GRAPHICAL", **body}

    def _latest(self, c: sqlite3.Connection, owner: str, sid: str, gid: str) -> Optional[sqlite3.Row]:
        return c.execute("SELECT * FROM chart_geo_revisions WHERE owner=? AND session_id=? AND geometry_id=? "
                         "ORDER BY revision DESC LIMIT 1", (owner, sid, gid)).fetchone()

    def list_objects(self, owner: str, sid: str, include_archived: bool = False) -> List[Dict[str, Any]]:
        self.get_session_meta(owner, sid)
        with self._c() as c:
            ids = [r[0] for r in c.execute("SELECT DISTINCT geometry_id FROM chart_geo_revisions WHERE owner=? AND session_id=? "
                                           "ORDER BY geometry_id", (owner, sid))]
            out = []
            for gid in ids:
                o = self._row_to_obj(self._latest(c, owner, sid, gid), sid, gid)
                if include_archived or o["status"] != "ARCHIVED":
                    out.append(o)
        return sorted(out, key=lambda o: (o["created_at"], o["geometry_id"]))

    def get_object(self, owner: str, sid: str, gid: str) -> Dict[str, Any]:
        self.get_session_meta(owner, sid)
        with self._c() as c:
            r = self._latest(c, owner, sid, gid)
        if not r:
            raise GeometryError("GEOMETRY_NOT_FOUND", "geometria inesistente", 404)
        return self._row_to_obj(r, sid, gid)

    def history(self, owner: str, sid: str, gid: str) -> List[Dict[str, Any]]:
        self.get_session_meta(owner, sid)
        with self._c() as c:
            rows = c.execute("SELECT * FROM chart_geo_revisions WHERE owner=? AND session_id=? AND geometry_id=? ORDER BY revision",
                             (owner, sid, gid)).fetchall()
        if not rows:
            raise GeometryError("GEOMETRY_NOT_FOUND", "geometria inesistente", 404)
        return [self._row_to_obj(r, sid, gid) for r in rows]

    def _insert(self, c: sqlite3.Connection, owner: str, sid: str, gid: str, rev: int, body: Dict[str, Any],
                created_at: float, available_at: float, origin: str, author: str) -> None:
        try:
            c.execute("INSERT INTO chart_geo_revisions VALUES(?,?,?,?,?,?,?,?,?)",
                      (owner, sid, gid, rev, created_at, available_at, origin, author, canonical(body)))
        except sqlite3.IntegrityError:
            raise GeometryError("REVISION_CONFLICT", "revisione gia' esistente (modifica concorrente)", 409)
        c.execute("UPDATE chart_geo_sessions SET updated_at=? WHERE owner=? AND session_id=?", (self._now(), owner, sid))

    def _ensure_layer(self, owner: str, sid: str, layer: str) -> None:
        if not any(l["layer_id"] == layer for l in self.list_layers(owner, sid)):
            raise GeometryError("LAYER_NOT_FOUND", f"livello inesistente: {layer}", 404)

    def create_object(self, owner: str, sid: str, body: Dict[str, Any], *, geometry_id: Optional[str] = None,
                      preserve: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.get_session_meta(owner, sid)
        clean = validate_body(body)
        self._ensure_layer(owner, sid, clean["style"]["layer"])
        gid = geometry_id or "G" + secrets.token_hex(8)
        if not ID_RE.match(gid):
            raise GeometryError("INVALID_ID", "geometry_id non valido")
        with self._c() as c:
            if self._latest(c, owner, sid, gid):
                raise GeometryError("GEOMETRY_EXISTS", "geometry_id gia' presente", 409)
            if len(self.list_objects(owner, sid, include_archived=True)) >= MAX_GEOMETRIES_PER_SESSION:
                raise GeometryError("LIMIT_REACHED", "numero massimo di geometrie nella sessione", 409)
            ts = self._now()
            created, avail, author = ts, ts, owner          # autore = utente autenticato, mai dal client
            if preserve:                                    # solo import verificato da hash: conserva la provenienza originale
                created = _num(preserve["created_at"], "created_at")
                avail = _num(preserve["available_at"], "available_at")
                author = _str(preserve["author"], "author", 80, allow_empty=False)
            self._insert(c, owner, sid, gid, 1, clean, created, avail, "MANUAL", author)
        return self.get_object(owner, sid, gid)

    def update_object(self, owner: str, sid: str, gid: str, patch: Dict[str, Any], expected_revision: int) -> Dict[str, Any]:
        cur = self.get_object(owner, sid, gid)
        if cur["revision"] != expected_revision:
            raise GeometryError("REVISION_CONFLICT", f"revisione attuale {cur['revision']}, attesa {expected_revision}", 409)
        existing = {k: cur[k] for k in TOP_KEYS if k in cur}
        # un oggetto bloccato accetta solo lo sblocco (style.locked=false) e cambi di stato/visibilita'
        if cur["style"].get("locked") and cur["status"] != "ARCHIVED":
            # conta solo cio' che cambia davvero: un patch completo che ripete i valori attuali (undo/redo) non e' una modifica
            changed = {k for k, v in patch.items() if k != "style" and _norm(cur.get(k)) != _norm(v)}
            ps = patch.get("style") or {}
            if not isinstance(ps, dict):
                raise GeometryError("INVALID_STYLE", "style deve essere un oggetto")
            changed |= {"style." + k for k, v in ps.items() if _norm(cur["style"].get(k)) != _norm(v)}
            if changed - {"style.locked", "style.visible"}:
                raise GeometryError("OBJECT_LOCKED", "oggetto bloccato: sbloccarlo prima di modificarlo", 423)
        merged_style = dict(cur["style"])
        if "style" in patch:
            if not isinstance(patch["style"], dict):
                raise GeometryError("INVALID_STYLE", "style deve essere un oggetto")
            merged_style.update(patch["style"])
        body = dict(patch)
        body["style"] = merged_style
        clean = validate_body(body, existing=existing)
        self._ensure_layer(owner, sid, clean["style"]["layer"])
        with self._c() as c:
            self._insert(c, owner, sid, gid, cur["revision"] + 1, clean, cur["created_at"], cur["available_at"], cur["origin"], cur["author"])
        return self.get_object(owner, sid, gid)

    def archive_object(self, owner: str, sid: str, gid: str, expected_revision: int) -> Dict[str, Any]:
        return self._set_status(owner, sid, gid, expected_revision, "ARCHIVED")

    def restore_object(self, owner: str, sid: str, gid: str, expected_revision: int) -> Dict[str, Any]:
        return self._set_status(owner, sid, gid, expected_revision, "ACTIVE")

    def _set_status(self, owner: str, sid: str, gid: str, expected_revision: int, status: str) -> Dict[str, Any]:
        cur = self.get_object(owner, sid, gid)
        if cur["revision"] != expected_revision:
            raise GeometryError("REVISION_CONFLICT", f"revisione attuale {cur['revision']}, attesa {expected_revision}", 409)
        if cur["style"].get("locked") and status == "ARCHIVED":
            raise GeometryError("OBJECT_LOCKED", "oggetto bloccato: non eliminabile", 423)
        body = {k: cur[k] for k in TOP_KEYS if k in cur}
        body["status"] = status
        with self._c() as c:
            self._insert(c, owner, sid, gid, cur["revision"] + 1, validate_body(body), cur["created_at"], cur["available_at"], cur["origin"], cur["author"])
        return self.get_object(owner, sid, gid)

    # ---- esportazione / importazione ----
    def export_session(self, owner: str, sid: str) -> Dict[str, Any]:
        meta = self.get_session_meta(owner, sid)
        payload = {"schema": SCHEMA, "session": {"session_id": sid, "name": meta["name"], "symbol": meta["symbol"], "created_at": meta["created_at"]},
                   "layers": self.list_layers(owner, sid),
                   "geometries": self.list_objects(owner, sid, include_archived=True)}
        return {**payload, "sha256": sha256_of(payload)}

    def import_session(self, owner: str, doc: Any, *, name: Optional[str] = None) -> Dict[str, Any]:
        if not isinstance(doc, dict) or doc.get("schema") != SCHEMA or not isinstance(doc.get("sha256"), str):
            raise GeometryError("INVALID_IMPORT", "documento non riconosciuto")
        payload = {k: v for k, v in doc.items() if k != "sha256"}
        if sha256_of(payload) != doc["sha256"]:
            raise GeometryError("IMPORT_HASH_MISMATCH", "hash non coincidente: file modificato o corrotto")
        if set(payload) - {"schema", "session", "layers", "geometries"}:
            raise GeometryError("INVALID_IMPORT", "campi non ammessi nel documento")
        geoms = payload.get("geometries")
        if not isinstance(geoms, list) or len(geoms) > MAX_GEOMETRIES_PER_SESSION:
            raise GeometryError("INVALID_IMPORT", "geometries non valido")
        s = payload.get("session") or {}
        new = self.create_session(owner, name or s.get("name") or "Sessione importata", s.get("symbol", ""))
        sid = new["session_id"]
        try:
            for lay in payload.get("layers") or []:
                self.upsert_layer(owner, sid, lay["layer_id"], {k: lay[k] for k in ("name", "visible", "locked", "position") if k in lay})
            for g in geoms:
                body = {k: g[k] for k in TOP_KEYS if k in g}
                status = body.get("status", "ACTIVE")
                body["status"] = "ACTIVE"
                if g.get("origin") != "MANUAL":
                    raise GeometryError("INVALID_IMPORT", "sono importabili solo geometrie MANUAL")
                created = self.create_object(owner, sid, body, geometry_id=g.get("geometry_id"),
                                             preserve={k: g.get(k) for k in ("created_at", "available_at", "author")})
                if status == "ARCHIVED":
                    self.archive_object(owner, sid, created["geometry_id"], created["revision"])
        except GeometryError:
            with self._c() as c:                           # import atomico: in caso di errore nulla resta
                for t in ("chart_geo_revisions", "chart_geo_layers", "chart_geo_sessions"):
                    c.execute(f"DELETE FROM {t} WHERE owner=? AND session_id=?", (owner, sid))
            raise
        return self.get_session_meta(owner, sid)


def comparable(geometries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Proiezione stabile per confrontare 'prima/dopo' ignorando i campi di sistema che cambiano (session_id, revision, timestamp)."""
    keep = ("geometry_id", *sorted(TOP_KEYS))
    return [{k: g[k] for k in keep if k in g} for g in sorted(geometries, key=lambda g: g["geometry_id"])]
