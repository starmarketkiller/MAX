"""CHART-REAL-DATA-V1-FIX-02 / FIX01R-01 - l'ammissione di una risposta e' UNA decisione su UN'UNICA revisione dell'autorita'.

Solo fixture sintetiche. Gli aggiornamenti concorrenti dell'autorita' sono iniettati ai CONFINI REALI di lettura (`Guard._snapshot` = lettura dei byte dei metadata, `ChartStore._segment` = lettura di un segmento):
l'hook esegue lo scrittore SUBITO DOPO che il lettore ha acquisito i byte, cioe' nel punto piu' sfavorevole. La sostituzione del file e' sempre atomica (os.replace).
"""
from __future__ import annotations

import json
import random
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import HTTPException

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import chart_api  # noqa: E402
import chart_guard  # noqa: E402
import chart_store  # noqa: E402
from test_chart_fix01_authorization import Env, explicit, utc, write_auth  # noqa: E402

OCT = ("2026-10-01T00:00:00Z", "2026-11-01T00:00:00Z")
NOV = ("2026-11-01T00:00:00Z", "2026-12-01T00:00:00Z")
DEC = ("2026-12-01T00:00:00Z", "2027-01-01T00:00:00Z")


def policy(env, *wins, ds=None, rev=None):
    """Pubblica una revisione dell'autorita' (finestre = unione di `wins`). `rev` rende diversi i byte anche a finestre uguali."""
    d = {(ds or env.dsid): {"kind": "EXPLICIT_WINDOWS", "windows_utc": [list(w) for w in wins]}}
    write_auth_raw(env, d, rev)


def write_auth_raw(env, datasets, rev=None):
    import os
    import time
    tmp = env.auth.with_name(env.auth.name + ".tmp")
    tmp.write_text(json.dumps({"schema": "NEXUS_CHART_AUTHORIZATION_V1", "authorized_by": "owner", "decision_ref": rev or "r", "bound_manifests": {}, "datasets": datasets}), encoding="utf-8")
    for attempt in range(300):
        try:
            os.replace(tmp, env.auth)
            return
        except PermissionError:
            if attempt == 299:
                raise
            time.sleep(0.003)


class Hooks:
    """Esegue azioni dello scrittore dopo la N-esima lettura di metadata (`Guard._snapshot`) e/o dopo la N-esima lettura di segmento."""

    def __init__(self, monkeypatch):
        self.snap_calls = 0
        self.seg_calls = 0
        self.on_snap = {}
        self.on_seg = {}
        self.admitted = []                                    # (revisione, intervalli) di ogni verify_all riuscita
        self.lock = threading.Lock()
        orig_snap = chart_guard.Guard._snapshot
        orig_seg = chart_store.ChartStore._segment
        orig_verify = chart_guard.Guard.verify_all
        h = self

        def snap(guard):
            data = orig_snap(guard)
            with h.lock:
                h.snap_calls += 1
                n = h.snap_calls
            for act in h.on_snap.get(n, []):
                act()
            return data

        def seg(store, m, tf, s):
            blob = orig_seg(store, m, tf, s)
            with h.lock:
                h.seg_calls += 1
                n = h.seg_calls
            for act in h.on_seg.get(n, []):
                act()
            return blob

        def verify(guard, requests):
            s = orig_verify(guard, requests)
            with h.lock:
                h.admitted.append((s, list(requests)))
            return s

        monkeypatch.setattr(chart_guard.Guard, "_snapshot", snap)
        monkeypatch.setattr(chart_store.ChartStore, "_segment", seg)
        monkeypatch.setattr(chart_guard.Guard, "verify_all", verify)


@pytest.fixture
def env(monkeypatch):
    e = Env(monkeypatch)                                       # TEST_DS: M1 sintetici 29/10..3/11 => segmenti mensili di ottobre e novembre
    policy(e, OCT, NOV)
    return e


@pytest.fixture
def hooks(monkeypatch, env):
    return Hooks(monkeypatch)


def admitted_by_single_revision(h):
    """Invariante: ogni risposta ammessa ha TUTTI gli intervalli dentro le finestre dello snapshot restituito da verify_all."""
    for snap, reqs in h.admitted:
        for ds, a, b in reqs:
            snap.check(ds, a, b)


# ---------------------------------------------------------------- riproduzione e scenario inverso
def two_revisions_around_final_validation(env, h, first, second):
    """Dopo la lettura dell'ultimo segmento pubblica la revisione `first`; subito dopo la PRIMA lettura di metadata della verifica finale pubblica `second`
    (cioe' fra il primo e il secondo controllo finale del codice FIX-01: e' esattamente l'interleaving del controesempio FIX01R-01)."""
    def after_last_segment():
        policy(env, *first)
        h.on_snap[h.snap_calls + 1] = [lambda: policy(env, *second)]
    h.on_seg[h.seg_calls + 2] = [after_last_segment]


def test_mixed_revisions_october_revoked_before_final_then_november_revoked_denies_whole_page(env, hooks):
    env.get("H4", 5000)                                         # cache calda
    hooks.snap_calls = hooks.seg_calls = 0
    hooks.admitted.clear()
    two_revisions_around_final_validation(env, hooks, (NOV,), (OCT,))     # R1 = solo novembre, poi R2 = solo ottobre: nessuna ammette la pagina intera
    env.denied(tf="H4", limit=5000)
    assert env.opened.count("2026-10") >= 1 and env.opened.count("2026-11") >= 1     # i dati erano stati letti, ma NON restituiti
    assert hooks.admitted == []


def test_inverse_scenario_october_only_then_november_only_denies(env, hooks):
    hooks.snap_calls = hooks.seg_calls = 0
    two_revisions_around_final_validation(env, hooks, (OCT,), (NOV,))
    env.denied(tf="H4", limit=5000)
    assert hooks.admitted == []


def test_revocation_before_final_validation_denies_whole_page(env, hooks):
    env.get("H4", 5000)
    hooks.snap_calls = hooks.seg_calls = 0
    hooks.admitted.clear()
    hooks.on_seg[2] = [lambda: policy(env, NOV)]                 # ottobre revocato dopo la lettura di tutti i dati, prima della verifica finale
    env.denied(tf="H4", limit=5000)
    assert hooks.admitted == []


def test_second_writer_during_final_validation_still_one_revision(env, hooks):
    """R1 (solo novembre) poi R2 (ottobre+novembre) subito dopo la lettura di R1: la verifica su R1 nega; non si 'recupera' con R2 mescolando esiti."""
    hooks.snap_calls = hooks.seg_calls = 0
    two_revisions_around_final_validation(env, hooks, (NOV,), (OCT, NOV))
    env.denied(tf="H4", limit=5000)                               # decisione sulla revisione S=R1: ottobre negato => risposta negata
    assert hooks.admitted == []
    assert env.get("H4", 5000)["bars"]                            # una NUOVA richiesta (ora R2 stabile) e' ammessa interamente da R2


# ---------------------------------------------------------------- piu' aggiornamenti concorrenti e tre segmenti
@pytest.fixture
def env3(monkeypatch):
    e = Env(monkeypatch, start=utc(2026, 10, 31), days=33)     # ottobre, novembre, dicembre
    policy(e, OCT, NOV, DEC)
    return e


@pytest.mark.parametrize("revisions", [
    [(NOV, DEC), (OCT, NOV)],            # ogni revisione ne ammette solo due su tre, in ordine diverso
    [(OCT, DEC), (NOV,)],
    [(OCT,), (NOV,), (DEC,)],            # tre aggiornamenti in sequenza durante la costruzione
    [(), (OCT, NOV, DEC)],               # revoca totale poi ripristino prima della conferma
])
def test_three_segments_with_two_or_more_concurrent_updates_never_admit_mixed_revisions(monkeypatch, env3, revisions):
    h = Hooks(monkeypatch)
    for i, wins in enumerate(revisions):
        h.on_seg[i + 1] = [lambda w=wins: policy(env3, *w)]
    try:
        r = env3.get("H4", 5000)
        assert r["bars"]
    except HTTPException as e:
        assert e.status_code == 403
    admitted_by_single_revision(h)                              # se ammessa: UNA revisione ammette tutti e tre i segmenti


def test_final_revision_decides_not_earlier_ones(monkeypatch, env3):
    """Durante la lettura la revisione passa da 'tutto' a 'solo ottobre+novembre': la risposta con dicembre e' NEGATA anche se i pre-check (revisione iniziale) passavano."""
    h = Hooks(monkeypatch)
    h.on_seg[3] = [lambda: policy(env3, OCT, NOV)]
    env3.denied(tf="H4", limit=5000)
    assert h.admitted == []


# ---------------------------------------------------------------- confine S -> conferma
def test_update_between_snapshot_and_confirmation_forces_full_reevaluation_on_new_revision(tmp_path):
    p = tmp_path / "a.json"
    write_auth_stub(p, [("X", OCT, NOV)], "A")
    g = chart_guard.Guard(auth_path=p, canon_dir=tmp_path / "none")
    t = utc(2026, 10, 10)
    calls = {"n": 0}
    orig = chart_guard.Guard._snapshot

    def snap(self):
        d = orig(self)
        calls["n"] += 1
        if calls["n"] == 1:                                    # subito dopo lo snapshot S della verifica: nuova revisione B con le stesse finestre ma byte diversi
            write_auth_stub(p, [("X", OCT, NOV)], "B")
        return d
    chart_guard.Guard._snapshot = snap
    try:
        s = g.verify_all([("X", t, t + 60)])
    finally:
        chart_guard.Guard._snapshot = orig
    assert s.revision == g.snapshot().revision                   # ammessa dalla revisione B (ricalcolata), non dalla A
    assert calls["n"] >= 3


def test_update_between_snapshot_and_confirmation_that_revokes_denies(tmp_path):
    p = tmp_path / "a.json"
    write_auth_stub(p, [("X", OCT, NOV)], "A")
    g = chart_guard.Guard(auth_path=p, canon_dir=tmp_path / "none")
    t = utc(2026, 10, 10)
    orig = chart_guard.Guard._snapshot
    state = {"n": 0}

    def snap(self):
        d = orig(self)
        state["n"] += 1
        if state["n"] == 1:
            write_auth_stub(p, [], "B")
        return d
    chart_guard.Guard._snapshot = snap
    try:
        with pytest.raises(chart_guard.PartitionDenied) as e:
            g.verify_all([("X", t, t + 60)])
    finally:
        chart_guard.Guard._snapshot = orig
    assert e.value.code == "DATASET_NOT_AUTHORIZED"              # rivalutazione completa su B: negata


def test_continuous_alternation_is_unstable_and_denied(tmp_path):
    p = tmp_path / "a.json"
    write_auth_stub(p, [("X", OCT, NOV)], "0")
    g = chart_guard.Guard(auth_path=p, canon_dir=tmp_path / "none")
    t = utc(2026, 10, 10)
    orig = chart_guard.Guard._snapshot
    state = {"n": 0}

    def snap(self):
        d = orig(self)
        state["n"] += 1
        write_auth_stub(p, [("X", OCT, NOV)], str(state["n"]))   # ogni lettura e' seguita da una nuova revisione (valida e ammissiva!)
        return d
    chart_guard.Guard._snapshot = snap
    try:
        with pytest.raises(chart_guard.PartitionDenied) as e:
            g.verify_all([("X", t, t + 60)])
    finally:
        chart_guard.Guard._snapshot = orig
    assert e.value.code == "AUTHORITY_UNSTABLE"                  # fail-closed: nessuna stabilita' => nessuna ammissione, nemmeno se ogni revisione ammetterebbe


def write_auth_stub(path, entries, rev):
    """entries: [(dataset, (a, b), ...)] come EXPLICIT_WINDOWS; scrittura atomica."""
    import os
    ds = {}
    for e in entries:
        ds.setdefault(e[0], {"kind": "EXPLICIT_WINDOWS", "windows_utc": []})["windows_utc"].append(list(e[1:] if isinstance(e[1], str) else e[1]))
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"schema": "NEXUS_CHART_AUTHORIZATION_V1", "authorized_by": "owner", "decision_ref": rev, "datasets": ds}), encoding="utf-8")
    os.replace(tmp, path)


def test_verify_all_uses_single_snapshot_for_multiple_datasets(tmp_path):
    p = tmp_path / "a.json"
    write_auth_stub(p, [("A", OCT, NOV), ("B", OCT, NOV)], "r1")
    g = chart_guard.Guard(auth_path=p, canon_dir=tmp_path / "none")
    t = utc(2026, 10, 10)
    orig = chart_guard.Guard._snapshot
    state = {"n": 0}

    def snap(self):
        d = orig(self)
        state["n"] += 1
        if state["n"] == 1:
            write_auth_stub(p, [("A", OCT, NOV)], "r2")           # B revocato subito dopo lo snapshot
        return d
    chart_guard.Guard._snapshot = snap
    try:
        with pytest.raises(chart_guard.PartitionDenied):
            g.verify_all([("A", t, t + 60), ("B", t, t + 60)])   # mai "A secondo r2 + B secondo r1"
    finally:
        chart_guard.Guard._snapshot = orig
    assert g.verify_all([("A", t, t + 60)]).windows("A")           # A da solo e' ammesso dalla revisione corrente


# ---------------------------------------------------------------- metadata invalidi durante la verifica
@pytest.mark.parametrize("bad", ["corrupt", "empty", "delete", "incomplete", "wrong_kind", "bad_dates"])
def test_invalid_metadata_during_verification_denies_whole_response(env, hooks, bad):
    def break_it():
        if bad == "corrupt":
            env.auth.write_text("{not json", encoding="utf-8")
        elif bad == "empty":
            env.auth.write_bytes(b"")
        elif bad == "delete":
            env.auth.unlink()
        elif bad == "incomplete":
            write_auth_raw(env, {env.dsid: {"kind": "EXPLICIT_WINDOWS"}})                  # manca windows_utc
        elif bad == "wrong_kind":
            write_auth_raw(env, {env.dsid: {"kind": "SOMETHING_ELSE"}})
        elif bad == "bad_dates":
            write_auth_raw(env, {env.dsid: {"kind": "EXPLICIT_WINDOWS", "windows_utc": [["not-a-date", "x"]]}})
    hooks.on_seg[2] = [break_it]
    env.denied(tf="H4", limit=5000)
    assert hooks.admitted == []
    policy(env, OCT, NOV)                                         # ripristino: solo un contenuto valido riapre l'accesso
    assert env.get("H4", 5000)["bars"]


# ---------------------------------------------------------------- snapshot immutabile
def test_snapshot_is_immutable_and_independent_of_later_updates(env):
    g = chart_api.get_guard()
    s = g.snapshot()
    t = utc(2026, 10, 10)
    s.check(env.dsid, t, t + 60)
    with pytest.raises(AttributeError):
        s.error = "x"
    with pytest.raises(AttributeError):
        s.revision = "y"
    w = s.windows(env.dsid)
    w.clear()                                                     # modificare la copia non altera lo snapshot
    assert s.windows(env.dsid)
    policy(env)                                                   # revoca totale dopo l'acquisizione
    s.check(env.dsid, t, t + 60)                                  # lo snapshot gia' acquisito non cambia (decide solo per la SUA revisione)
    with pytest.raises(chart_guard.PartitionDenied):
        g.snapshot().check(env.dsid, t, t + 60)                   # uno snapshot nuovo vede la revoca
    assert s.revision != g.snapshot().revision


# ---------------------------------------------------------------- multitimeframe e paginazione con aggiornamento a meta' lettura
@pytest.mark.parametrize("tf", list(chart_store.ALL_TFS))
def test_all_nine_timeframes_denied_when_authority_changes_mid_read(env, hooks, tf):
    hooks.seg_calls = 0
    hooks.on_seg[1] = [lambda: policy(env, NOV)]                  # ottobre revocato subito dopo il primo segmento
    try:
        r = env.get(tf, 5000)
        # ammessa solo se TUTTI i segmenti letti stanno nella revisione finale (es. timeframe con un solo segmento novembre/ottobre coerente)
        admitted_by_single_revision(hooks)
        assert r["bars"]
    except HTTPException as e:
        assert e.status_code == 403
        assert hooks.admitted == []


def test_pagination_pages_are_each_decided_on_one_revision(env, hooks):
    p1 = env.get("H4", 5)
    assert p1["bars"]
    hooks.seg_calls = 0
    hooks.on_seg[1] = [lambda: policy(env, NOV)]                  # ottobre revocato durante la pagina successiva (che scende in ottobre)
    env.denied(tf="H4", limit=5000, before=utc(2026, 11, 2))
    admitted_by_single_revision(hooks)


# ---------------------------------------------------------------- revoca dopo la conferma = finestra residua dichiarata
def test_revocation_after_confirmation_is_the_documented_residual_window(env, monkeypatch):
    """CONTRATTO: ammessa la risposta alla rilettura di conferma, una revoca successiva NON puo' ritirare i byte gia' in memoria; la richiesta SUCCESSIVA e' negata."""
    orig = chart_guard.Guard.verify_all

    def verify_then_revoke(guard, reqs):
        s = orig(guard, reqs)
        policy(env)                                               # revoca subito dopo l'ammissione
        return s
    monkeypatch.setattr(chart_guard.Guard, "verify_all", verify_then_revoke)
    r = env.get("M1", 50)
    assert r["bars"]                                              # finestra residua (documentata): risposta gia' ammessa
    env.denied(tf="M1", limit=50)                                 # ma da qui in poi: negato


# ---------------------------------------------------------------- proprieta' con schedulazioni casuali
def test_random_interleavings_never_admit_a_response_not_covered_by_one_revision(monkeypatch, env3):
    rnd = random.Random(20261127)
    pols = [(OCT, NOV, DEC), (OCT, NOV), (NOV, DEC), (OCT, DEC), (OCT,), (NOV,), (DEC,), ()]
    outcomes = {"admitted": 0, "denied": 0}
    for trial in range(120):
        h = Hooks(monkeypatch)
        for _ in range(rnd.randint(0, 4)):
            when = rnd.randint(1, 9)
            wins = rnd.choice(pols)
            h.on_seg[when] = h.on_seg.get(when, []) + [lambda w=wins: policy(env3, *w, rev=str(rnd.random()))]
            h.on_snap[rnd.randint(1, 14)] = h.on_snap.get(rnd.randint(1, 14), []) + [lambda w=rnd.choice(pols): policy(env3, *w, rev=str(rnd.random()))]
        policy(env3, OCT, NOV, DEC)
        try:
            env3.get("H4", 5000)
            outcomes["admitted"] += 1
        except HTTPException as e:
            assert e.status_code == 403
            outcomes["denied"] += 1
        admitted_by_single_revision(h)
        monkeypatch.undo() if False else None
    assert outcomes["denied"] > 0 and outcomes["admitted"] > 0     # la schedulazione esercita entrambi i rami


# ---------------------------------------------------------------- richieste concorrenti con scrittore continuo
def test_concurrent_requests_with_continuously_toggling_authority_return_only_coherent_pages(monkeypatch, env):
    h = Hooks(monkeypatch)
    stop = threading.Event()
    results = []
    lock = threading.Lock()

    def writer():
        i = 0
        while not stop.is_set():
            i += 1
            policy(env, *( (OCT, NOV) if i % 2 else (NOV,) ), rev=str(i))

    def worker(_):
        try:
            r = env.get("H4", 5000)
            out = ("DATA", [b["time"] for b in r["bars"]])
        except HTTPException as e:
            out = ("DENIED", e.status_code)
        with lock:
            results.append(out)

    t = threading.Thread(target=writer)
    t.start()
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(worker, range(60)))
    finally:
        stop.set()
        t.join()
    assert len(results) == 60
    assert all(o[0] == "DENIED" and o[1] == 403 or o[0] == "DATA" for o in results)
    admitted_by_single_revision(h)                                  # ogni pagina ammessa e' coperta per intero da una singola revisione
    for kind, payload in results:
        if kind == "DATA":
            assert payload == sorted(payload) and len(payload) == len(set(payload))


# ---------------------------------------------------------------- compatibilita' FIX-01: API invariata
def test_guard_public_api_preserved(env):
    g = chart_api.get_guard()
    t = utc(2026, 10, 10)
    g.check(env.dsid, t, t + 60)
    assert g.windows(env.dsid) and g.error is None
    g.recheck(env.dsid, [(t, t + 60)])
    assert g.clamp(env.dsid, t, t + 60) == (t, t + 60)
    policy(env)
    with pytest.raises(chart_guard.PartitionDenied):
        g.recheck(env.dsid, [(t, t + 60)])
