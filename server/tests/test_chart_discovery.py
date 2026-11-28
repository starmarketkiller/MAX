"""NEXUS-CHART-MULTISCALE-DISCOVERY-01 — Reverse Discovery Lab V1 (RETROSPECTIVE_DISCOVERY): backend."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import chart_discovery as cd  # noqa: E402
import chart_geometry as cg  # noqa: E402
import test_chart_geometry as tg  # noqa: E402

T0 = 1_760_000_000
H4 = 14400
PIP = {"pip_size": 0.10, "point": 0.01, "tick_size": 0.01}


def anc(t, p):
    return {"t": t, "price": p}


def ev(**kw):
    b = {"name": "Inversione 1", "dataset_id": "DS1", "source": "XM_TEST", "symbol": "gold", "clock_basis": "TERMINAL_CLOCK",
         "timeframe_observation": "H4", "outcome": "REVERSAL", "pivot": dict(anc(T0 + 10 * H4, 2700.0), kind="HIGH"),
         "origin": anc(T0, 2600.0), "destination": anc(T0 + 20 * H4, 2650.0), "units": PIP, "classification": "MAJOR_REVERSAL"}
    b.update(kw)
    return b


@pytest.fixture()
def gs(tmp_path):
    return cg.GeometryStore(str(tmp_path / "d.db"))


@pytest.fixture()
def ds(gs):
    return cd.DiscoveryStore(gs)


@pytest.fixture()
def sid(gs):
    return gs.create_session("alice", "Ricerca 1", "GOLD")["session_id"]


def geom(gs, sid, **kw):
    return gs.create_object("alice", sid, tg.diag(**kw))["geometry_id"]


# ------------------------------------------------------------------ scheda evento e grandezze derivate
def test_event_card_has_required_fields_and_derived_metrics_with_configurable_pips(ds, sid):
    e = ds.create_event("alice", sid, ev())
    for k in ("event_id", "dataset_id", "source", "symbol", "clock_basis", "timeframe_observation", "pivot", "origin", "destination", "discovered_at",
              "author", "revision", "epistemic_mode", "validation_status", "annotations", "hypotheses", "evidence_for", "evidence_against",
              "analog_links", "geometries", "structures", "units", "derived"):
        assert k in e, k
    assert e["symbol"] == "GOLD" and e["author"] == "alice" and e["epistemic_mode"] == "RETROSPECTIVE_DISCOVERY"
    assert e["validation_status"] == "NOT_VALIDATED" and e["output_label"] == "DISCOVERY_ONLY"
    d = e["derived"]
    assert (d["prior_direction"], d["next_direction"]) == ("UP", "DOWN")
    assert d["prior_leg"] == {"direction": "UP", "amplitude_price": 100.0, "amplitude_pips": 1000.0, "duration_s": 10 * H4}
    assert d["next_leg"]["direction"] == "DOWN" and d["next_leg"]["amplitude_price"] == 50.0 and d["next_leg"]["duration_s"] == 10 * H4
    assert e["units"] == PIP                                              # prezzo, pip, point e tick size restano separati
    e2 = ds.update_event("alice", sid, e["event_id"], {"units": {"pip_size": 0.01}}, 1)
    assert e2["derived"]["prior_leg"]["amplitude_pips"] == 10000.0 and e2["units"]["point"] is None


def test_pips_absent_when_pip_size_unknown_and_low_pivot_directions(ds, sid):
    e = ds.create_event("alice", sid, ev(units=None, pivot=dict(anc(T0 + 10 * H4, 2500.0), kind="LOW"), origin=anc(T0, 2600.0), destination=anc(T0 + 20 * H4, 2580.0)))
    assert e["derived"]["prior_leg"]["amplitude_pips"] is None and e["derived"]["prior_direction"] == "DOWN" and e["derived"]["next_direction"] == "UP"


@pytest.mark.parametrize("patch", [
    {"origin": anc(T0 + 11 * H4, 2600.0)},                                        # origine dopo il pivot
    {"destination": anc(T0 + 5 * H4, 2650.0)},                                    # destinazione prima del pivot
    {"origin": anc(T0, 2800.0)},                                                  # per un massimo l'origine deve stare sotto
    {"destination": anc(T0 + 20 * H4, 2800.0)},                                   # dopo un massimo di inversione si scende
    {"pivot": {"t": T0 + 10 * H4, "price": 2700.0, "kind": "MID"}},
    {"timeframe_observation": "H2"}, {"outcome": "MAYBE"}, {"classification": "SUPER"},
])
def test_event_validation_rejects_inconsistent_geometry_but_imposes_no_amplitude_threshold(ds, sid, patch):
    with pytest.raises(cg.GeometryError):
        ds.create_event("alice", sid, ev(**patch))
    tiny = ds.create_event("alice", sid, ev(origin=anc(T0, 2699.99)))          # nessuna soglia di ampiezza
    assert tiny["derived"]["prior_leg"]["amplitude_price"] == pytest.approx(0.01)


@pytest.mark.parametrize("field", ["epistemic_mode", "validation_status", "discovered_at", "author", "revision", "event_id", "imported_by",
                                   "signal", "order", "side", "preregistration_hash", "edge", "p_value", "win_rate"])
def test_server_owned_and_operational_fields_are_not_writable(ds, sid, field):
    with pytest.raises(cg.GeometryError) as e:
        ds.create_event("alice", sid, ev(**{field: "x"}))
    assert e.value.code == "UNKNOWN_FIELD"
    cur = ds.create_event("alice", sid, ev())
    with pytest.raises(cg.GeometryError) as e2:
        ds.update_event("alice", sid, cur["event_id"], {field: "x"}, 1)
    assert e2.value.code == "UNKNOWN_FIELD"


def test_no_reversal_analog_keeps_direction_and_is_a_first_class_event(ds, sid):
    e = ds.create_event("alice", sid, ev(outcome="NO_REVERSAL", destination=anc(T0 + 20 * H4, 2750.0)))
    assert e["derived"]["next_direction"] == e["derived"]["prior_direction"] == "UP" and e["outcome"] == "NO_REVERSAL"


# ------------------------------------------------------------------ geometrie collegate: nessuna retrodatazione
def test_geometry_links_carry_timing_and_never_claim_prior_knowledge(gs, ds, sid):
    gid = geom(gs, sid, semantic={"class": "DIAG_BUY"})
    e = ds.create_event("alice", sid, ev(geometries=[{"geometry_id": gid, "timing": "BEFORE_EVENT_OBSERVABLE", "note": "tre tocchi"}]))
    lk = e["geometries"][0]
    assert lk["timing"] == "BEFORE_EVENT_OBSERVABLE" and lk["causal_knowledge"] == "NOT_ESTABLISHED"
    assert lk["geometry_available_at"] == gs.get_object("alice", sid, gid)["available_at"]
    assert lk["geometry_available_at"] > e["pivot"]["t"]                         # available_at e' il tempo reale di creazione: non retrodatato
    assert lk["geometry"]["semantic_class"] == "DIAG_BUY" and lk["geometry"]["epistemic_mode"] == "RETROSPECTIVE_DISCOVERY"
    assert gs.get_object("alice", sid, gid)["available_at"] == lk["geometry_available_at"]      # il collegamento non modifica la geometria
    for bad in ({"geometry_id": gid, "timing": "KNOWN_BEFORE"}, {"geometry_id": "Gnone", "timing": "DURING_EVENT"}):
        with pytest.raises(cg.GeometryError):
            ds.update_event("alice", sid, e["event_id"], {"geometries": [bad]}, 1)
    forged = ds.update_event("alice", sid, e["event_id"], {"geometries": [{"geometry_id": gid, "timing": "DURING_EVENT", "causal_knowledge": "ESTABLISHED"}]}, 1)
    assert forged["geometries"][0]["causal_knowledge"] == "NOT_ESTABLISHED"          # campo di sola resa: il client non puo' dichiarare conoscenza causale
    again = ds.update_event("alice", sid, e["event_id"], {"geometries": forged["geometries"] + [{"geometry_id": gid, "timing": "RETROSPECTIVELY_RECOGNIZED"}]}, forged["revision"])
    assert [g["timing"] for g in again["geometries"]] == ["DURING_EVENT", "RETROSPECTIVELY_RECOGNIZED"]
    assert again["geometries"][0]["created_at"] == forged["geometries"][0]["created_at"]      # data del collegamento conservata, non riscritta dal client
    sneaky = ds.update_event("alice", sid, e["event_id"], {"geometries": [dict(g, created_at=1) for g in again["geometries"]]}, again["revision"])
    assert [g["created_at"] for g in sneaky["geometries"]] == [g["created_at"] for g in again["geometries"]]


def test_cannot_link_another_users_geometry(gs, ds, sid):
    bsid = gs.create_session("bob", "B")["session_id"]
    bg = gs.create_object("bob", bsid, tg.diag())["geometry_id"]
    with pytest.raises(cg.GeometryError):
        ds.create_event("alice", sid, ev(geometries=[{"geometry_id": bg, "timing": "DURING_EVENT"}]))


# ------------------------------------------------------------------ strutture e scale
def test_structures_support_parent_child_scales_and_derived_origin_amplitude_duration(gs, ds, sid):
    g = geom(gs, sid)
    s = [{"id": "S1", "kind": "IMPULSE", "scale": "MAJOR", "origin": anc(T0, 2600.0), "destination": anc(T0 + 10 * H4, 2700.0)},
         {"id": "S2", "kind": "CORRECTION", "scale": "INTERMEDIATE", "parent_id": "S1", "origin": anc(T0 + 4 * H4, 2660.0), "destination": anc(T0 + 6 * H4, 2640.0), "geometry_ids": [g]},
         {"id": "S3", "kind": "IMPULSE", "scale": "MINOR", "parent_id": "S2", "origin": anc(T0 + 4 * H4, 2660.0), "destination": anc(T0 + 5 * H4, 2650.0)}]
    e = ds.create_event("alice", sid, ev(structures=s))
    by = {x["id"]: x for x in e["structures"]}
    assert by["S2"]["parent_id"] == "S1" and by["S3"]["scale"] == "MINOR" and by["S1"]["derived"]["amplitude_pips"] == 1000.0
    assert by["S2"]["derived"]["direction"] == "DOWN" and by["S2"]["derived"]["duration_s"] == 2 * H4
    assert by["S2"]["geometry_ids"] == [g]
    # i figli non dipendono dal timeframe: nessuna scala e' vincolata a un TF
    assert "timeframe" not in by["S1"]


def test_structure_hierarchy_rejects_cycles_orphans_and_theory_labels(ds, sid):
    base = {"kind": "IMPULSE", "scale": "MAJOR", "origin": anc(T0, 1.0), "destination": anc(T0 + 60, 2.0)}
    for bad in ([dict(base, id="A", parent_id="B"), dict(base, id="B", parent_id="A")], [dict(base, id="A", parent_id="A")], [dict(base, id="A", parent_id="X")],
                [dict(base, id="A", kind="WAVE_3")], [dict(base, id="A", scale="CYCLE")], [dict(base, id="A"), dict(base, id="A")]):
        with pytest.raises(cg.GeometryError):
            ds.create_event("alice", sid, ev(structures=bad))


# ------------------------------------------------------------------ ipotesi, evidenze, analoghi
def test_annotations_hypotheses_evidence_are_stamped_by_the_server_and_never_validated(gs, ds, sid):
    g = geom(gs, sid)
    e = ds.create_event("alice", sid, ev(annotations=[{"text": "spike sul massimo"}], hypotheses=[{"text": "esaurimento", "status": "OPEN"}, {"text": "liquidita'"}],
                                         evidence_for=[{"text": "chiusure congruenti", "geometry_id": g}], evidence_against=[{"text": "nessun retest"}]))
    assert all(x["id"] and x["created_at"] for x in e["annotations"] + e["hypotheses"] + e["evidence_for"] + e["evidence_against"])
    assert [h["status"] for h in e["hypotheses"]] == ["OPEN", "OPEN"]
    with pytest.raises(cg.GeometryError):
        ds.update_event("alice", sid, e["event_id"], {"hypotheses": [{"text": "x", "status": "VALIDATED"}]}, 1)
    with pytest.raises(cg.GeometryError):
        ds.update_event("alice", sid, e["event_id"], {"evidence_for": [{"text": "x", "geometry_id": "Gnone"}]}, 1)
    upd = ds.update_event("alice", sid, e["event_id"], {"hypotheses": [dict(e["hypotheses"][0], status="CONTRADICTED_BY_OBSERVATION", created_at=1)]}, 1)
    assert upd["hypotheses"][0]["created_at"] == e["hypotheses"][0]["created_at"]       # il client non riscrive le date
    assert upd["revision"] == 2 and upd["discovered_at"] == e["discovered_at"]


def test_analog_cases_with_and_without_reversal(ds, sid):
    a = ds.create_event("alice", sid, ev(name="con inversione"))
    b = ds.create_event("alice", sid, ev(name="senza inversione", outcome="NO_REVERSAL", destination=anc(T0 + 20 * H4, 2750.0)))
    u = ds.update_event("alice", sid, a["event_id"], {"analog_links": [{"event_id": b["event_id"], "kind": "ANALOG_NO_REVERSAL", "note": "stessa diagonale"}]}, 1)
    assert u["analog_links"][0]["kind"] == "ANALOG_NO_REVERSAL"
    for bad in ([{"event_id": a["event_id"], "kind": "RELATED"}], [{"event_id": "Enone", "kind": "RELATED"}], [{"event_id": b["event_id"], "kind": "PROVEN_EDGE"}]):
        with pytest.raises(cg.GeometryError):
            ds.update_event("alice", sid, a["event_id"], {"analog_links": bad}, 2)


# ------------------------------------------------------------------ revisioni, isolamento, ricerca
def test_revisions_conflicts_history_archive_and_isolation(gs, ds, sid):
    e = ds.create_event("alice", sid, ev())
    u = ds.update_event("alice", sid, e["event_id"], {"name": "nuovo"}, 1)
    with pytest.raises(cg.GeometryError) as c:
        ds.update_event("alice", sid, e["event_id"], {"name": "stale"}, 1)
    assert c.value.code == "REVISION_CONFLICT"
    arch = ds.set_status("alice", sid, e["event_id"], u["revision"], "ARCHIVED")
    assert ds.list_events("alice", sid) == [] and len(ds.list_events("alice", sid, True)) == 1
    ds.set_status("alice", sid, e["event_id"], arch["revision"], "ACTIVE")
    assert [h["revision"] for h in ds.history("alice", sid, e["event_id"])] == [1, 2, 3, 4]
    assert ds.history("alice", sid, e["event_id"])[0]["name"] == "Inversione 1"
    for call in (lambda: ds.get_event("bob", sid, e["event_id"]), lambda: ds.list_events("bob", sid), lambda: ds.create_event("bob", sid, ev()),
                 lambda: ds.update_event("bob", sid, e["event_id"], {"name": "x"}, 4), lambda: ds.get_research("bob", sid), lambda: ds.history("bob", sid, e["event_id"])):
        with pytest.raises(cg.GeometryError) as x:
            call()
        assert x.value.status == 404


def test_research_state_roundtrip_and_validation(ds, sid):
    assert ds.get_research("alice", sid)["research"] is None
    layout = {"count": 3, "charts": [{"tf": "H4"}, {"tf": "M15", "linked": False}, {"tf": "M5"}], "sync": {"time_range": True, "crosshair": False, "symbol": True}}
    r = ds.put_research("alice", sid, {"name": "Reverse 1", "dataset_id": "DS1", "symbol": "gold", "interval": {"from_t": T0, "to_t": T0 + 5 * H4}, "layout": layout, "units": PIP})
    assert r["research"]["layout"]["charts"][1] == {"tf": "M15", "linked": False} and r["research"]["symbol"] == "GOLD" and r["epistemic_mode"] == "RETROSPECTIVE_DISCOVERY"
    for bad in ({"layout": dict(layout, count=5)}, {"layout": dict(layout, count=2)}, {"interval": {"from_t": T0, "to_t": T0}}, {"holdout": True}, {"layout": {"count": 1, "charts": [{"tf": "H2"}]}}):
        with pytest.raises(cg.GeometryError):
            ds.put_research("alice", sid, bad)


# ------------------------------------------------------------------ export / import
def populate(gs, ds, sid):
    g = geom(gs, sid, semantic={"class": "DIAG_SELL"})
    a = ds.create_event("alice", sid, ev(geometries=[{"geometry_id": g, "timing": "BEFORE_EVENT_OBSERVABLE"}], annotations=[{"text": "n"}],
                                         structures=[{"id": "S1", "kind": "IMPULSE", "scale": "MAJOR", "origin": anc(T0, 2600.0), "destination": anc(T0 + 10 * H4, 2700.0)}]))
    b = ds.create_event("alice", sid, ev(name="analogo", outcome="NO_REVERSAL", destination=anc(T0 + 20 * H4, 2750.0)))
    ds.update_event("alice", sid, a["event_id"], {"analog_links": [{"event_id": b["event_id"], "kind": "ANALOG_NO_REVERSAL"}]}, 1)
    ds.put_research("alice", sid, {"name": "R", "dataset_id": "DS1", "symbol": "GOLD", "units": PIP})


def strip_event(e):
    return {k: e[k] for k in sorted(cd.EVENT_KEYS) if k in e} | {"event_id": e["event_id"], "discovered_at": e["discovered_at"], "author": e["author"],
                                                                 "derived": e["derived"]}


def test_whole_research_export_import_roundtrip_with_author_provenance_kept_separate(gs, ds, sid):
    populate(gs, ds, sid)
    doc = gs.export_session("alice", sid)
    assert len(doc["events"]) == 2 and doc["research"]["name"] == "R"
    meta = gs.import_session("bob", json.loads(json.dumps(doc)), name="import")
    nsid = meta["session_id"]
    ev2 = ds.list_events("bob", nsid)
    assert [strip_event(x)["name"] for x in ev2] == [e["name"] for e in doc["events"]]
    for x, y in zip(ev2, doc["events"]):
        assert strip_event(x)["derived"] == y["derived"] and x["discovered_at"] == y["discovered_at"]       # data di scoperta conservata
        assert x["author"] == "alice" and x["imported_by"] == "bob" and x["author_verified"] is False         # autore DICHIARATO != importatore effettivo
    assert ds.get_research("bob", nsid)["research"]["name"] == "R"
    g2 = gs.list_objects("bob", nsid)[0]
    assert g2["author"] == "alice" and g2["imported_by"] == "bob" and g2["author_verified"] is False
    assert gs.list_objects("alice", sid)[0]["author_verified"] is True
    assert [a["event_id"] for a in ev2[0]["analog_links"]] == [ev2[1]["event_id"]]


def test_import_rejects_tampered_event_and_leaves_nothing(gs, ds, sid):
    populate(gs, ds, sid)
    doc = gs.export_session("alice", sid)
    before = len(gs.list_sessions("bob"))
    t = copy.deepcopy(doc)
    t["events"][0]["pivot"]["price"] += 1
    with pytest.raises(cg.GeometryError) as e:
        gs.import_session("bob", t)
    assert e.value.code == "IMPORT_HASH_MISMATCH"
    bad = copy.deepcopy(doc)
    bad["events"][0]["epistemic_mode"] = "CAUSAL_REPLAY"                         # hash ricalcolato: il contenuto resta inammissibile
    bad["sha256"] = cg.sha256_of({k: v for k, v in bad.items() if k != "sha256"})
    with pytest.raises(cg.GeometryError):
        gs.import_session("bob", bad)
    assert len(gs.list_sessions("bob")) == before


def test_export_with_events_survives_javascript_number_serialization(gs, ds, sid):
    populate(gs, ds, sid)
    doc = gs.export_session("alice", sid)
    assert gs.import_session("bob", tg.js_roundtrip(doc))["name"]


# ------------------------------------------------------------------ confronto
def test_comparison_is_descriptive_and_has_no_statistics(gs, ds, sid):
    populate(gs, ds, sid)
    a, b = ds.list_events("alice", sid)
    c = cd.comparison([a, b])
    assert len(c["events"]) == 2 and "frequenze" in c["disclaimer"]
    flat = json.dumps(c).lower()
    for forbidden in ("p_value", "win_rate", "probability", "percent", "edge"):
        assert forbidden not in flat
    assert c["events"][0]["geometry_by_timing"]["BEFORE_EVENT_OBSERVABLE"] == 1 and c["events"][0]["structures_by_scale"] == {"MAJOR": 1}


# ------------------------------------------------------------------ API reali con due identita'
def test_api_discovery_end_to_end_isolation(tmp_path):
    G, D = "/api/chart/geometry", "/api/chart/discovery"
    body = ev()
    steps = [
        {"m": "GET", "p": D + "/vocabulary", "as": "anon"},                                                       # 0: 401
        {"m": "POST", "p": G + "/sessions", "b": {"name": "R"}, "save": {"sid": "session_id"}},                    # 1
        {"m": "POST", "p": G + "/sessions/{sid}/objects", "b": tg.diag(), "save": {"gid": "geometry_id"}},          # 2
        {"m": "POST", "p": D + "/sessions/{sid}/events", "b": dict(body, geometries=[{"geometry_id": "{gid}", "timing": "BEFORE_EVENT_OBSERVABLE"}]), "save": {"eid": "event_id"}},  # 3
        {"m": "GET", "p": D + "/sessions/{sid}/events"},                                                          # 4
        {"m": "PUT", "p": D + "/sessions/{sid}/events/{eid}", "b": {"name": "mod", "expected_revision": 1}},       # 5
        {"m": "PUT", "p": D + "/sessions/{sid}/events/{eid}", "b": {"name": "stale", "expected_revision": 1}},     # 6: 409
        {"m": "GET", "p": D + "/sessions/{sid}/events", "as": "other"},                                           # 7: 404
        {"m": "GET", "p": D + "/sessions/{sid}/events/{eid}", "as": "other"},                                     # 8: 404
        {"m": "POST", "p": D + "/sessions/{sid}/events", "b": dict(body, epistemic_mode="CAUSAL_REPLAY")},        # 9: 422
        {"m": "PUT", "p": D + "/sessions/{sid}/research", "b": {"name": "r", "units": {"pip_size": 0.1}}},         # 10
        {"m": "GET", "p": D + "/sessions/{sid}/research"},                                                        # 11
        {"m": "POST", "p": D + "/sessions/{sid}/events", "b": dict(body, name="due"), "save": {"eid2": "event_id"}},  # 12
        {"m": "GET", "p": D + "/sessions/{sid}/compare?ids={eid},{eid2}"},                                        # 13
        {"m": "GET", "p": D + "/sessions/{sid}/compare?ids={eid}"},                                               # 14: 422
        {"m": "POST", "p": D + "/sessions/{sid}/events/{eid}/archive", "b": {"expected_revision": 2}},             # 15
        {"m": "GET", "p": G + "/sessions/{sid}/export"},                                                          # 16
    ]
    r = tg.run_api(steps)
    st = [x[0] for x in r]
    assert st[0] == 401 and st[3] == 200 and r[3][1]["geometries"][0]["causal_knowledge"] == "NOT_ESTABLISHED"
    assert st[4] == 200 and len(r[4][1]["events"]) == 1 and st[5] == 200 and st[6] == 409
    assert st[7] == st[8] == 404 and st[9] == 422 and r[9][1]["detail"]["code"] == "UNKNOWN_FIELD"
    assert r[11][1]["research"]["units"]["pip_size"] == 0.1 and st[13] == 200 and st[14] == 422 and st[15] == 200
    assert len(r[13][1]["events"]) == 2 and len(r[16][1]["events"]) == 2


def test_event_window_is_a_validated_user_parameter_persisted_with_the_research(ds, sid):
    r = ds.put_research("alice", sid, {"name": "R", "event_window": {"pre": 120, "post": 0}})
    assert r["research"]["event_window"] == {"pre": 120, "post": 0}
    assert ds.put_research("alice", sid, {"name": "R"})["research"]["event_window"] is None         # nessun valore imposto di default dal server
    for bad in ({"pre": 0, "post": 5}, {"pre": 5, "post": -1}, {"pre": 5000, "post": 5}, {"pre": 1.5, "post": 5}, {"pre": 5}, {"pre": 5, "post": 5, "x": 1}, "70/30"):
        with pytest.raises(cg.GeometryError):
            ds.put_research("alice", sid, {"name": "R", "event_window": bad})


def test_structure_geometry_link_is_validated_and_survives_roundtrip(gs, ds, sid):
    g = geom(gs, sid)
    s = [{"id": "S1", "kind": "GEOMETRY_GROUP", "scale": "MINOR", "origin": anc(T0, 1.0), "destination": anc(T0 + 60, 2.0), "geometry_ids": [g]}]
    e = ds.create_event("alice", sid, ev(structures=s))
    assert e["structures"][0]["geometry_ids"] == [g]
    upd = ds.update_event("alice", sid, e["event_id"], {"structures": [dict(e["structures"][0], geometry_ids=[g, g][:1])]}, 1)
    assert upd["structures"][0]["geometry_ids"] == [g]
    with pytest.raises(cg.GeometryError):
        ds.update_event("alice", sid, e["event_id"], {"structures": [dict(e["structures"][0], geometry_ids=["Gnone"])]}, 2)
