"""CHART-GEOMETRY-01 — test backend: validazione, memoria persistente, isolamento, export/import, API reali."""
import copy
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER))
import chart_geometry as cg  # noqa: E402

T0 = 1_760_000_000


def anchor(t=T0, p=2650.5, ref=None):
    a = {"t": t, "price": p}
    if ref:
        a["ref"] = ref
    return a


def diag(**kw):
    b = {"type": "trendline", "symbol": "xauusd", "timeframe_origin": "M15", "dataset_id": "DS1", "source": "XM_TEST",
         "anchors": [anchor(T0, 2650.5), anchor(T0 + 3600, 2661.25)], "name": "d1"}
    b.update(kw)
    return b


@pytest.fixture()
def store(tmp_path):
    return cg.GeometryStore(str(tmp_path / "geo.db"))


@pytest.fixture()
def sess(store):
    return store.create_session("alice", "Analisi 1", "XAUUSD")["session_id"]


# ---------------------------------------------------------------- validazione
def test_all_types_accepted_with_correct_anchor_count(store, sess):
    shapes = {
        "hline": [anchor()], "vline": [anchor()], "trendline": [anchor(), anchor(T0 + 60, 2651)],
        "ray": [anchor(), anchor(T0 + 60, 2651)], "extended_line": [anchor(), anchor(T0 + 60, 2651)],
        "rectangle": [anchor(), anchor(T0 + 60, 2655)], "price_band": [anchor(), anchor(T0 + 60, 2655)],
        "text": [anchor()], "fib_retracement": [anchor(), anchor(T0 + 60, 2655)],
        "fib_extension": [anchor(), anchor(T0 + 60, 2655), anchor(T0 + 120, 2652)],
        "ruler": [anchor(), anchor(T0 + 60, 2655)],
    }
    assert set(shapes) == set(cg.VOCAB["types"])
    for t, an in shapes.items():
        extra = {"text": "nota"} if t == "text" else {}
        o = store.create_object("alice", sess, diag(type=t, anchors=an, **extra))
        assert o["type"] == t and o["revision"] == 1 and o["origin"] == "MANUAL" and o["memory_domain"] == "GRAPHICAL"


@pytest.mark.parametrize("anchors", [[anchor()], [anchor(), anchor(T0 + 1, 2), anchor(T0 + 2, 3)], []])
def test_diagonal_requires_exactly_two_anchors(store, sess, anchors):
    with pytest.raises(cg.GeometryError) as e:
        store.create_object("alice", sess, diag(anchors=anchors))
    assert e.value.code == "INVALID_ANCHOR_COUNT"


@pytest.mark.parametrize("bad,code", [
    ({"t": "x", "price": 1}, "INVALID_ANCHOR_TIME"), ({"t": T0 + 0.5, "price": 1}, "INVALID_ANCHOR_TIME"),
    ({"t": 5, "price": 1}, "INVALID_ANCHOR_TIME"), ({"t": T0, "price": float("nan")}, "INVALID_NUMBER"),
    ({"t": T0, "price": "2650"}, "INVALID_NUMBER"), ({"t": T0, "price": 1e12}, "INVALID_ANCHOR_PRICE"),
    ({"t": T0, "price": 1, "px": 33}, "UNKNOWN_FIELD"),
    ({"t": T0, "price": 1, "ref": {"kind": "CANDLE", "bar_t": T0, "field": "mid"}}, "INVALID_ANCHOR_REF"),
    ({"t": T0, "price": 1, "ref": {"kind": "CANDLE", "field": "high"}}, "INVALID_ANCHOR_REF"),
    ({"t": T0, "price": 1, "ref": {"kind": "FREE", "projection_id": "P3"}}, "PROJECTION_NOT_DEFINED"),
])
def test_anchor_validation(store, sess, bad, code):
    with pytest.raises(cg.GeometryError) as e:
        store.create_object("alice", sess, diag(anchors=[bad, anchor(T0 + 60, 2)]))
    assert e.value.code == code


def test_degenerate_and_unknown_fields_rejected(store, sess):
    with pytest.raises(cg.GeometryError) as e:
        store.create_object("alice", sess, diag(anchors=[anchor(T0, 1), anchor(T0, 2)]))
    assert e.value.code == "DEGENERATE_GEOMETRY"
    for field in ("order", "signal", "lots", "sl", "tp", "origin", "author", "created_at", "available_at", "revision", "owner"):
        with pytest.raises(cg.GeometryError) as e:
            store.create_object("alice", sess, diag(**{field: "x"}))
        assert e.value.code == "UNKNOWN_FIELD", field


def test_candle_anchor_records_snap_reference_without_projection(store, sess):
    a = anchor(T0, 2650.5, ref={"kind": "CANDLE", "bar_t": T0, "field": "high"})
    o = store.create_object("alice", sess, diag(anchors=[a, anchor(T0 + 60, 2651)]))
    assert o["anchors"][0]["ref"] == {"kind": "CANDLE", "projection_id": None, "bar_t": T0, "field": "high"}
    assert o["anchors"][1]["ref"] == {"kind": "FREE", "projection_id": None}


def test_semantic_is_separate_from_shape_and_never_a_signal(store, sess):
    o = store.create_object("alice", sess, diag(semantic={"class": "DIAG_BUY", "note": "tre tocchi"}))
    assert o["type"] == "trendline" and o["semantic"] == {"class": "DIAG_BUY", "set_by": "USER", "note": "tre tocchi"}
    o2 = store.create_object("alice", sess, diag(name="senza"))
    assert o2["semantic"]["class"] == "NONE"
    for k in ("signal", "order", "side", "action"):
        assert k not in o and k not in o2
    mism = [("DIAG_BUY", "rectangle"), ("ZONE_BUY_TO_SELL", "trendline"), ("KEY_LEVEL_CLOSES", "rectangle")]
    for cls, shape in mism:
        an = [anchor()] if shape == "hline" else [anchor(), anchor(T0 + 60, 2660)]
        with pytest.raises(cg.GeometryError) as e:
            store.create_object("alice", sess, diag(type=shape, anchors=an, semantic={"class": cls}))
        assert e.value.code == "SEMANTIC_SHAPE_MISMATCH"
    with pytest.raises(cg.GeometryError):
        store.create_object("alice", sess, diag(semantic={"class": "BUY_NOW"}))
    with pytest.raises(cg.GeometryError):
        store.create_object("alice", sess, diag(semantic={"class": "DIAG_BUY", "set_by": "ENGINE"}))


def test_all_nexus_semantic_classes_are_assignable(store, sess):
    ok = {"DIAG_BUY": ("trendline", 2), "DIAG_SELL": ("ray", 2), "KEY_LEVEL_CLOSES": ("hline", 1), "LIQUIDITY_SPIKES": ("hline", 1),
          "ZONE_BUY_TO_SELL": ("rectangle", 2), "ZONE_SELL_TO_BUY": ("rectangle", 2), "INNER_SPACE": ("rectangle", 2),
          "REACTION_ZONE": ("rectangle", 2), "CONTINUATION_ZONE": ("price_band", 2)}
    assert set(ok) | {"NONE"} == set(cg.VOCAB["semantic_classes"])
    for cls, (shape, n) in ok.items():
        an = [anchor(T0, 2650)] if n == 1 else [anchor(T0, 2650), anchor(T0 + 600, 2660)]
        assert store.create_object("alice", sess, diag(type=shape, anchors=an, semantic={"class": cls}))["semantic"]["class"] == cls


def test_style_validation(store, sess):
    for bad in ({"color": "red"}, {"width": 99}, {"dash": "zigzag"}, {"visible": "yes"}, {"layer": "../x"}, {"zzz": 1}, {"fill_opacity": 2}):
        with pytest.raises(cg.GeometryError) as e:
            store.create_object("alice", sess, diag(style=bad))
        assert e.value.code == "INVALID_STYLE"
    o = store.create_object("alice", sess, diag(style={"color": "#ff0000", "width": 3, "dash": "dashed", "extend": "right"}))
    assert o["style"]["color"] == "#ff0000" and o["style"]["extend"] == "right" and o["style"]["layer"] == "default"


def test_fib_levels_are_user_parameters(store, sess):
    a = [anchor(T0, 2650), anchor(T0 + 600, 2670)]
    o = store.create_object("alice", sess, diag(type="fib_retracement", anchors=a))
    assert o["fib_levels"] == cg.VOCAB["fib_defaults"]["fib_retracement"]
    o2 = store.create_object("alice", sess, diag(type="fib_retracement", anchors=a, fib_levels=[0, 0.3, 1]))
    assert o2["fib_levels"] == [0, 0.3, 1]
    with pytest.raises(cg.GeometryError):
        store.create_object("alice", sess, diag(type="fib_retracement", anchors=a, fib_levels=["x"]))


def test_text_requires_text_and_limits(store, sess):
    with pytest.raises(cg.GeometryError):
        store.create_object("alice", sess, diag(type="text", anchors=[anchor()]))
    with pytest.raises(cg.GeometryError):
        store.create_object("alice", sess, diag(name="x" * 500))


# ---------------------------------------------------------------- memoria e revisioni
def test_persistence_fields_and_exact_roundtrip_across_store_instances(tmp_path):
    db = str(tmp_path / "p.db")
    s1 = cg.GeometryStore(db)
    sid = s1.create_session("alice", "S", "XAUUSD")["session_id"]
    created = s1.create_object("alice", sid, diag(semantic={"class": "DIAG_SELL"}, description="d", links=[], evidence=["E1"]))
    for k in ("geometry_id", "dataset_id", "source", "symbol", "timeframe_origin", "type", "anchors", "author", "origin",
              "created_at", "available_at", "revision", "status", "style", "description", "links", "memory_domain"):
        assert k in created, k
    assert created["symbol"] == "XAUUSD" and created["author"] == "alice" and created["available_at"] >= created["created_at"]
    s2 = cg.GeometryStore(db)                                            # "chiusura e riapertura"
    again = s2.get_object("alice", sid, created["geometry_id"])
    assert again == created
    assert again["anchors"][0]["t"] == T0 and again["anchors"][1]["price"] == 2661.25


def test_update_creates_revision_history_and_conflict_detection(store, sess):
    o = store.create_object("alice", sess, diag())
    gid = o["geometry_id"]
    o2 = store.update_object("alice", sess, gid, {"anchors": [anchor(T0, 2640), anchor(T0 + 3600, 2661.25)]}, 1)
    assert o2["revision"] == 2 and o2["anchors"][0]["price"] == 2640 and o2["created_at"] == o["created_at"]
    with pytest.raises(cg.GeometryError) as e:
        store.update_object("alice", sess, gid, {"name": "x"}, 1)
    assert e.value.code == "REVISION_CONFLICT" and e.value.status == 409
    hist = store.history("alice", sess, gid)
    assert [h["revision"] for h in hist] == [1, 2] and hist[0]["anchors"][0]["price"] == 2650.5   # la storia non si perde
    with pytest.raises(cg.GeometryError) as e:
        store.update_object("alice", sess, gid, {"type": "ray"}, 2)
    assert e.value.code == "TYPE_IMMUTABLE"


def test_extend_line_does_not_alter_origins(store, sess):
    o = store.create_object("alice", sess, diag())
    o2 = store.update_object("alice", sess, o["geometry_id"], {"style": {"extend": "both"}}, 1)
    assert o2["anchors"] == o["anchors"] and o2["style"]["extend"] == "both"


def test_archive_is_reversible_and_never_deletes(store, sess):
    o = store.create_object("alice", sess, diag())
    a = store.archive_object("alice", sess, o["geometry_id"], 1)
    assert a["status"] == "ARCHIVED" and store.list_objects("alice", sess) == []
    assert len(store.list_objects("alice", sess, include_archived=True)) == 1
    r = store.restore_object("alice", sess, o["geometry_id"], a["revision"])
    assert r["status"] == "ACTIVE" and r["anchors"] == o["anchors"] and len(store.history("alice", sess, o["geometry_id"])) == 3


def test_lock_blocks_edit_and_delete_but_allows_unlock(store, sess):
    o = store.create_object("alice", sess, diag(style={"locked": True}))
    gid = o["geometry_id"]
    for patch in ({"name": "n"}, {"anchors": [anchor(T0, 1), anchor(T0 + 60, 2)]}, {"style": {"color": "#000000"}}):
        with pytest.raises(cg.GeometryError) as e:
            store.update_object("alice", sess, gid, patch, 1)
        assert e.value.code == "OBJECT_LOCKED"
    with pytest.raises(cg.GeometryError) as e:
        store.archive_object("alice", sess, gid, 1)
    assert e.value.code == "OBJECT_LOCKED"
    u = store.update_object("alice", sess, gid, {"style": {"locked": False}}, 1)
    assert u["style"]["locked"] is False
    assert store.update_object("alice", sess, gid, {"name": "n"}, 2)["name"] == "n"


def test_lock_allows_full_style_patch_that_changes_only_lock_or_visibility(store, sess):
    """Regressione trovata nel browser reale: redo di uno sblocco rimanda l'intero stile; non e' una modifica."""
    o = store.create_object("alice", sess, diag(style={"locked": True, "width": 3}))
    full_unlock = dict(o["style"], locked=False)
    u = store.update_object("alice", sess, o["geometry_id"], {"style": full_unlock, "name": o["name"]}, 1)
    assert u["style"]["locked"] is False
    relock = store.update_object("alice", sess, o["geometry_id"], {"style": dict(u["style"], locked=True)}, 2)
    with pytest.raises(cg.GeometryError) as e:
        store.update_object("alice", sess, o["geometry_id"], {"style": dict(relock["style"], width=5)}, 3)
    assert e.value.code == "OBJECT_LOCKED"


def test_links_between_geometries_and_relation_vocabulary(store, sess):
    a = store.create_object("alice", sess, diag(name="a"))
    b = store.create_object("alice", sess, diag(name="b", links=[{"geometry_id": a["geometry_id"], "relation": "PAIRED_WITH"}]))
    assert b["links"] == [{"geometry_id": a["geometry_id"], "relation": "PAIRED_WITH"}]
    with pytest.raises(cg.GeometryError):
        store.create_object("alice", sess, diag(links=[{"geometry_id": "x", "relation": "BUYS"}]))


def test_layers_visibility_lock_and_unknown_layer(store, sess):
    layers = store.upsert_layer("alice", sess, "zone", {"name": "Zone", "visible": False, "locked": True, "position": 2})
    assert any(l["layer_id"] == "zone" and l["visible"] is False and l["locked"] is True for l in layers)
    o = store.create_object("alice", sess, diag(style={"layer": "zone"}))
    assert o["style"]["layer"] == "zone"
    with pytest.raises(cg.GeometryError) as e:
        store.create_object("alice", sess, diag(style={"layer": "nolayer"}))
    assert e.value.code == "LAYER_NOT_FOUND"
    with pytest.raises(cg.GeometryError):
        store.upsert_layer("alice", sess, "zone", {"owner": "bob"})


# ---------------------------------------------------------------- isolamento
def test_owner_isolation_everywhere(store):
    sa = store.create_session("alice", "A")["session_id"]
    sb = store.create_session("bob", "B")["session_id"]
    ga = store.create_object("alice", sa, diag())["geometry_id"]
    assert [s["session_id"] for s in store.list_sessions("bob")] == [sb]
    calls = [
        lambda: store.get_session_meta("bob", sa), lambda: store.list_objects("bob", sa), lambda: store.get_object("bob", sa, ga),
        lambda: store.history("bob", sa, ga), lambda: store.export_session("bob", sa),
        lambda: store.create_object("bob", sa, diag()), lambda: store.update_object("bob", sa, ga, {"name": "x"}, 1),
        lambda: store.archive_object("bob", sa, ga, 1), lambda: store.upsert_layer("bob", sa, "default", {"name": "x"}),
        lambda: store.rename_session("bob", sa, "x"),
    ]
    for c in calls:
        with pytest.raises(cg.GeometryError) as e:
            c()
        assert e.value.status == 404 and e.value.code == "SESSION_NOT_FOUND"      # 404 identico: non rivela l'esistenza
    # lo stesso geometry_id puo' esistere in un'altra sessione/utente senza collisioni o fughe
    store.create_object("bob", sb, diag(name="mia"), geometry_id=ga)
    assert store.get_object("alice", sa, ga)["name"] == "d1" and store.get_object("bob", sb, ga)["name"] == "mia"


# ---------------------------------------------------------------- export / import
def _populate(store, sid):
    store.upsert_layer("alice", sid, "zone", {"name": "Zone", "position": 1})
    a = store.create_object("alice", sid, diag(semantic={"class": "DIAG_BUY"}, anchors=[
        anchor(T0, 2650.5, {"kind": "CANDLE", "bar_t": T0, "field": "low"}), anchor(T0 + 3600, 2661.25)]))
    store.create_object("alice", sid, diag(type="hline", anchors=[anchor(T0 + 10, 2655.125)], semantic={"class": "KEY_LEVEL_CLOSES"}, name="kl"))
    z = store.create_object("alice", sid, diag(type="rectangle", anchors=[anchor(T0, 2640), anchor(T0 + 7200, 2648)],
                                               semantic={"class": "ZONE_BUY_TO_SELL"}, style={"layer": "zone", "color": "#00aa00"},
                                               links=[{"geometry_id": a["geometry_id"], "relation": "RELATED"}]))
    gone = store.create_object("alice", sid, diag(name="eliminata"))
    store.archive_object("alice", sid, gone["geometry_id"], 1)
    store.update_object("alice", sid, z["geometry_id"], {"description": "rev2"}, 1)


def test_export_import_roundtrip_identical_hash_and_geometry(store, sess):
    _populate(store, sess)
    exp = store.export_session("alice", sess)
    assert exp["schema"] == cg.SCHEMA and exp["sha256"] == cg.sha256_of({k: v for k, v in exp.items() if k != "sha256"})
    meta = store.import_session("alice", json.loads(json.dumps(exp)), name="copia")
    exp2 = store.export_session("alice", meta["session_id"])
    # stesse geometrie, stessi ancoraggi, stessi timestamp di creazione e disponibilita'
    assert cg.comparable(exp["geometries"]) == cg.comparable(exp2["geometries"])
    for g1, g2 in zip(sorted(exp["geometries"], key=lambda g: g["geometry_id"]), sorted(exp2["geometries"], key=lambda g: g["geometry_id"])):
        assert (g1["created_at"], g1["available_at"], g1["author"], g1["anchors"]) == (g2["created_at"], g2["available_at"], g2["author"], g2["anchors"])
    assert exp2["layers"] == exp["layers"]
    # ri-esportando due volte lo stesso stato si ottiene lo stesso hash
    assert store.export_session("alice", meta["session_id"])["sha256"] == exp2["sha256"]


def test_import_rejects_tampered_files_and_leaves_no_residue(store, sess):
    _populate(store, sess)
    exp = store.export_session("alice", sess)
    before = len(store.list_sessions("alice"))
    t = copy.deepcopy(exp)
    t["geometries"][0]["anchors"][0]["price"] += 1
    with pytest.raises(cg.GeometryError) as e:
        store.import_session("alice", t)
    assert e.value.code == "IMPORT_HASH_MISMATCH"
    # file con hash ricalcolato ma contenuto non valido (es. campo ordine) -> rifiutato e import atomico
    bad = copy.deepcopy(exp)
    bad["geometries"][1]["order"] = "BUY"
    payload = {k: v for k, v in bad.items() if k != "sha256"}
    bad["sha256"] = cg.sha256_of(payload)
    # 'order' e' ignorato dal filtro TOP_KEYS: nessun campo operativo entra mai nel corpo importato
    meta = store.import_session("alice", bad)
    assert all("order" not in g for g in store.list_objects("alice", meta["session_id"]))
    bad2 = copy.deepcopy(exp)
    bad2["geometries"][0]["origin"] = "ENGINE"
    bad2["sha256"] = cg.sha256_of({k: v for k, v in bad2.items() if k != "sha256"})
    n = len(store.list_sessions("alice"))
    with pytest.raises(cg.GeometryError):
        store.import_session("alice", bad2)
    assert len(store.list_sessions("alice")) == n and before + 1 == n
    with pytest.raises(cg.GeometryError):
        store.import_session("alice", {"schema": "x"})


def js_roundtrip(doc):
    """Simula il passaggio dal browser: JSON.parse/stringify serializza 2.0 come 2."""
    def fix(o):
        if isinstance(o, float) and o.is_integer():
            return int(o)
        if isinstance(o, dict):
            return {k: fix(v) for k, v in o.items()}
        if isinstance(o, list):
            return [fix(v) for v in o]
        return o
    return fix(doc)


def test_export_hash_survives_javascript_number_serialization(store, sess):
    """Regressione trovata nel browser reale: width 2.0 -> 2 cambiava lo sha256 e l'import veniva rifiutato."""
    store.create_object("alice", sess, diag(style={"width": 2, "fill_opacity": 0}))
    store.create_object("alice", sess, diag(type="fib_retracement", anchors=[anchor(T0, 2650), anchor(T0 + 600, 2670)], fib_levels=[0, 0.5, 1]))
    exp = store.export_session("alice", sess)
    assert cg.sha256_of({k: v for k, v in js_roundtrip(exp).items() if k != "sha256"}) == exp["sha256"]
    meta = store.import_session("alice", js_roundtrip(exp), name="via browser")
    assert cg.comparable(store.export_session("alice", meta["session_id"])["geometries"]) == cg.comparable(exp["geometries"])


def test_import_into_other_owner_is_isolated(store, sess):
    _populate(store, sess)
    exp = store.export_session("alice", sess)
    m = store.import_session("bob", exp)
    assert len(store.list_objects("bob", m["session_id"])) == len(store.list_objects("alice", sess))
    store.update_object("bob", m["session_id"], store.list_objects("bob", m["session_id"])[0]["geometry_id"], {"name": "solo-bob"}, 1)
    assert all(g["name"] != "solo-bob" for g in store.list_objects("alice", sess))


def test_limits(store, sess, monkeypatch):
    monkeypatch.setattr(cg, "MAX_GEOMETRIES_PER_SESSION", 3)
    for i in range(3):
        store.create_object("alice", sess, diag(name=str(i)))
    with pytest.raises(cg.GeometryError) as e:
        store.create_object("alice", sess, diag())
    assert e.value.code == "LIMIT_REACHED"


# ---------------------------------------------------------------- API reali (sottoprocesso)
API_SCRIPT = r"""
import json, os
from fastapi.testclient import TestClient
import app as server
c = TestClient(server.app)
steps = json.loads(os.environ["STEPS"])
r = c.post("/api/auth/login", json={"email": os.environ["NEXUS_ADMIN_USER"], "password": os.environ["NEXUS_ADMIN_PASSWORD"]})
tok_admin = r.json().get("token")
tok_other, _ = server.make_jwt("other-user@local")
c.cookies.clear()        # solo Bearer: il cookie del login non deve autenticare le richieste 'anon' o 'other'
out = []
vars_ = {}
def sub(x):
    if isinstance(x, str):
        for k, v in vars_.items(): x = x.replace("{" + k + "}", str(v))
        return x
    if isinstance(x, list): return [sub(i) for i in x]
    if isinstance(x, dict): return {k: sub(v) for k, v in x.items()}
    return x
for st in steps:
    who = st.get("as", "admin")
    h = {"Authorization": "Bearer " + (tok_admin if who == "admin" else tok_other if who == "other" else "bad"), "Origin": "http://localhost:3000"}
    if who == "anon": h = {}
    m, p, b = st["m"], sub(st["p"]), sub(st.get("b"))
    r = c.request(m, p, json=b, headers=h)
    try: body = r.json()
    except Exception: body = None
    for name, path in (st.get("save") or {}).items():
        v = body
        for part in path.split("."): v = v[int(part)] if part.isdigit() else v[part]
        vars_[name] = v
    out.append([r.status_code, body])
print("RESULT" + json.dumps(out, default=str))
"""


def run_api(steps):
    env = os.environ.copy()
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "NEXUS_ENV": "DEV", "NEXUS_COOKIE_SECURE": "false", "NEXUS_DUKASCOPY_AUTOFETCH": "false",
                "NEXUS_SEED_ON_START": "false", "NEXUS_QUEUE_DISPATCHER_ENABLED": "false",
                "NEXUS_DB_PATH": str(Path(tempfile.mkdtemp(prefix="geo_api_")) / "t.db"), "NEXUS_ADMIN_USER": "geo-test@local",
                "NEXUS_ADMIN_PASSWORD": "geo-test-local-only", "STEPS": json.dumps(steps)})
    for k in ("NEXUS_CHART_STORE_ROOT", "NEXUS_CHART_AUTH_FILE", "NEXUS_CHART_DEMO"):
        env.pop(k, None)
    r = subprocess.run([sys.executable, "-B", "-c", API_SCRIPT], cwd=str(SERVER), env=env, capture_output=True, text=True, timeout=240)
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("RESULT")]
    assert line, (r.stderr or r.stdout)[-2000:]
    return json.loads(line[-1][6:])


def test_api_end_to_end_isolation_and_errors():
    B = "/api/chart/geometry"
    body = diag()
    steps = [
        {"m": "GET", "p": B + "/vocabulary", "as": "anon"},                                                       # 0: 401
        {"m": "POST", "p": B + "/sessions", "b": {"name": "A1", "symbol": "XAUUSD"}, "save": {"sid": "session_id"}},  # 1
        {"m": "POST", "p": B + "/sessions/{sid}/objects", "b": body, "save": {"gid": "geometry_id"}},               # 2
        {"m": "GET", "p": B + "/sessions/{sid}"},                                                                  # 3
        {"m": "PUT", "p": B + "/sessions/{sid}/objects/{gid}", "b": {"name": "mod", "expected_revision": 1}},       # 4
        {"m": "PUT", "p": B + "/sessions/{sid}/objects/{gid}", "b": {"name": "stale", "expected_revision": 1}},     # 5: 409
        {"m": "PUT", "p": B + "/sessions/{sid}/objects/{gid}", "b": {"name": "x"}},                                 # 6: 422
        {"m": "GET", "p": B + "/sessions/{sid}", "as": "other"},                                                    # 7: 404
        {"m": "GET", "p": B + "/sessions/{sid}/objects/{gid}", "as": "other"},                                      # 8: 404
        {"m": "PUT", "p": B + "/sessions/{sid}/objects/{gid}", "b": {"name": "hack", "expected_revision": 2}, "as": "other"},  # 9: 404
        {"m": "GET", "p": B + "/sessions", "as": "other"},                                                          # 10: vuota
        {"m": "POST", "p": B + "/sessions/{sid}/objects", "b": dict(body, order="BUY"), },                          # 11: 422
        {"m": "POST", "p": B + "/sessions/{sid}/objects/{gid}/archive", "b": {"expected_revision": 2}},             # 12
        {"m": "GET", "p": B + "/sessions/{sid}"},                                                                   # 13: nessun oggetto attivo
        {"m": "POST", "p": B + "/sessions/{sid}/objects/{gid}/restore", "b": {"expected_revision": 3}},             # 14
        {"m": "GET", "p": B + "/sessions/{sid}/export"},                                                            # 15
        {"m": "POST", "p": B + "/sessions", "b": {"name": ""}},                                                     # 16: 422
        {"m": "POST", "p": B + "/sessions/{sid}/objects/{gid}/delete", "b": {"expected_revision": 4}},              # 17: 404 azione
        {"m": "POST", "p": B + "/sessions", "b": {"name": "x"}, "as": "bad"},                                       # 18: 401
    ]
    r = run_api(steps)
    st = [x[0] for x in r]
    assert st[0] == 401 and st[1] == 200 and st[2] == 200 and st[3] == 200 and st[4] == 200
    assert st[5] == 409 and r[5][1]["detail"]["code"] == "REVISION_CONFLICT"
    assert st[6] == 422 and st[7] == st[8] == st[9] == 404 and r[10][1]["sessions"] == []
    assert st[11] == 422 and r[11][1]["detail"]["code"] == "UNKNOWN_FIELD"
    assert st[12] == 200 and r[13][1]["geometries"] == [] and st[14] == 200
    exp = r[15][1]
    assert [(a["t"], a["price"]) for a in exp["geometries"][0]["anchors"]] == [(a["t"], a["price"]) for a in body["anchors"]]
    assert exp["geometries"][0]["revision"] == 4
    assert st[16] == 422 and st[17] == 404 and st[18] == 401
    assert r[3][1]["geometries"][0]["anchors"][1] == {"t": T0 + 3600, "price": 2661.25, "ref": {"kind": "FREE", "projection_id": None}}


def test_api_export_import_roundtrip_and_tamper():
    B = "/api/chart/geometry"
    steps = [
        {"m": "POST", "p": B + "/sessions", "b": {"name": "A1"}, "save": {"sid": "session_id"}},
        {"m": "POST", "p": B + "/sessions/{sid}/objects", "b": diag(semantic={"class": "DIAG_BUY"})},
        {"m": "POST", "p": B + "/sessions/{sid}/objects", "b": diag(type="rectangle", name="z", anchors=[anchor(T0, 2640), anchor(T0 + 600, 2650)],
                                                                    semantic={"class": "ZONE_SELL_TO_BUY"})},
        {"m": "GET", "p": B + "/sessions/{sid}/export"},
    ]
    exp = run_api(steps)[3][1]
    tampered = copy.deepcopy(exp)
    tampered["geometries"][0]["anchors"][0]["price"] = 1.0
    steps2 = steps + [
        {"m": "POST", "p": B + "/import", "b": exp},
        {"m": "POST", "p": B + "/import", "b": tampered},
        {"m": "POST", "p": B + "/import", "b": exp, "as": "other"},
    ]
    r = run_api(steps2)
    assert r[4][0] == 200 and r[5][0] == 422 and r[5][1]["detail"]["code"] == "IMPORT_HASH_MISMATCH" and r[6][0] == 200


# ---------------------------------------------------------------- FASE 07: contesto futuro riservato, memoria separata
FUTURE = json.loads((SERVER / "chart_geometry_future_context_v1.json").read_text(encoding="utf-8"))


def test_future_context_contract_is_reserved_not_implemented_and_separate():
    assert FUTURE["status"] == "CONTRACT_ONLY_NOT_IMPLEMENTED"
    assert FUTURE["memory_domains"]["EMPIRICAL"].startswith("eventi osservati") and cg.VOCAB["memory_domain"] == "GRAPHICAL"
    assert FUTURE["geometric_scales"]["status"] == "NOT_DEFINED" and FUTURE["candle_projections"]["status"] == "NOT_DEFINED_BY_OWNER"
    # nessun campo riservato e' un campo scrivibile della geometria; gli eventi hanno un proprio registro
    reserved = set(FUTURE["rejected_geometry_fields"])
    assert not (reserved & cg.TOP_KEYS)
    assert set(FUTURE["contact_events"]["event_types"]) >= {"CONTACT", "PENETRATION", "BREAK", "RETEST", "ROLE_CHANGED"}
    assert "PROJECTION_OF" in cg.VOCAB["link_relations"]                       # collegamento multiscala gia' disponibile


@pytest.mark.parametrize("field", FUTURE["rejected_geometry_fields"])
def test_api_rejects_future_and_operational_fields(store, sess, field):
    with pytest.raises(cg.GeometryError) as e:
        store.create_object("alice", sess, diag(**{field: {"x": 1}}))
    assert e.value.code == "UNKNOWN_FIELD"
    o = store.create_object("alice", sess, diag())
    with pytest.raises(cg.GeometryError) as e2:
        store.update_object("alice", sess, o["geometry_id"], {field: "x"}, 1)
    assert e2.value.code == "UNKNOWN_FIELD"


def test_stored_geometry_carries_the_causal_and_provenance_fields_the_future_replay_needs(store, sess):
    o = store.create_object("alice", sess, diag())
    for k in ("created_at", "available_at", "revision", "timeframe_origin", "dataset_id", "clock_basis", "links", "evidence", "origin", "author"):
        assert k in o
    assert o["anchors"][0]["ref"]["projection_id"] is None
