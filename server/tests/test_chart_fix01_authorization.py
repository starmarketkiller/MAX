"""CHART-REAL-DATA-V1-FIX-01 / CRDV1R-01 - l'autorita' di accesso e' rivalidata a ogni lettura (nessuna autorizzazione obsoleta riutilizzabile).

Solo fixture sintetiche e copie dei metadata canonici: NESSUNA partizione sigillata reale viene aperta.
Il contatore `_segment` conta le aperture reali di file di dati: dopo una revoca deve restare invariato.
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import shutil
import sys
import threading
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import HTTPException

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
import chart_api  # noqa: E402
import chart_guard  # noqa: E402
import chart_store  # noqa: E402

PHASE7 = "DUKASCOPY_XAUUSD_PHASE7"


def utc(y, m, d, h=0):
    return int(dt.datetime(y, m, d, h, tzinfo=dt.timezone.utc).timestamp())


def mk_rows(n_days, start):
    rows = []
    for i in range(n_days * 1440):
        if i % 1440 >= 1380:
            continue
        p = 3000.0 + (i % 97) * 0.01
        rows.append({"time": start + i * 60, "open": p, "high": p + 0.3, "low": p - 0.3, "close": p + 0.1})
    return rows


def meta(dsid):
    return {"dataset_id": dsid, "feed_kind": "TEST", "symbol_actual": "GOLD", "symbol_aliases": ["GOLD", "XAUUSD"], "provenance": "unit test", "clock_basis": "TERMINAL_CLOCK", "instrument_spec": {"digits": 2}}


def write_auth(path: Path, datasets: dict, bound=None):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps({"schema": "NEXUS_CHART_AUTHORIZATION_V1", "authorized_by": "owner", "decision_ref": "fix01", "bound_manifests": bound or {}, "datasets": datasets}), encoding="utf-8")
    for attempt in range(200):                                              # sostituzione atomica, come farebbe un deploy (su Windows fallisce se un lettore ha il file aperto)
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 199:
                raise
            time.sleep(0.005)


def explicit(a, b):
    return {"kind": "EXPLICIT_WINDOWS", "windows_utc": [[a, b]]}


class Env:
    """Ambiente isolato: store sintetico + record di autorizzazione + conteggio delle aperture di segmento."""

    def __init__(self, monkeypatch, start=utc(2026, 10, 29), days=6, dsid="TEST_DS", extra_ds=()):
        self.dir = Path(tempfile.mkdtemp(prefix="fix01_"))
        self.root = self.dir / "store"
        for d in (dsid,) + tuple(extra_ds):
            chart_store.build_store(mk_rows(days, start), self.root, meta(d), None, 100)
        self.auth = self.dir / "auth.json"
        self.dsid = dsid
        self.reads = 0
        self.opened: list[str] = []
        self._lock = threading.Lock()
        orig = chart_store.ChartStore._segment
        env = self

        def counted(store, m, tf, seg):
            with env._lock:
                env.reads += 1
                env.opened.append(seg["month"])
            return orig(store, m, tf, seg)
        monkeypatch.setattr(chart_store.ChartStore, "_segment", counted)
        monkeypatch.setenv("NEXUS_CHART_STORE_ROOT", str(self.root))
        monkeypatch.setenv("NEXUS_CHART_AUTH_FILE", str(self.auth))
        monkeypatch.delenv("NEXUS_CHART_PARTITION_DIR", raising=False)
        chart_api.reset_caches()

    def get(self, tf="H4", limit=50, before=None, source=None):
        return chart_api.ohlc(source or self.dsid, "GOLD", tf, limit, before)

    def denied(self, **kw) -> HTTPException:
        with pytest.raises(HTTPException) as e:
            self.get(**kw)
        assert e.value.status_code == 403, e.value.detail
        return e.value


@pytest.fixture
def env(monkeypatch):
    e = Env(monkeypatch)
    write_auth(e.auth, {e.dsid: explicit("2026-10-01T00:00:00Z", "2026-12-31T00:00:00Z")})
    return e


# ---------------------------------------------------------------- scenario obbligatorio 1-7
def test_revocation_after_warm_cache_denies_identical_request_without_reading_or_returning_data(env):
    first = env.get("M5")                                                   # 1-2: autorizzato, cache calda (guardia + store popolati)
    assert first["status"] == "AVAILABLE_OFFLINE" and first["bars"]
    reads_after_warm = env.reads
    assert reads_after_warm > 0
    write_auth(env.auth, {})                                                # 3: revoca (stesso percorso, stesso processo)
    err = env.denied(tf="M5")                                               # 4-5: richiesta identica negata
    assert env.reads == reads_after_warm                                    # 6: nessuna nuova apertura di segmento
    assert "bars" not in json.dumps(err.detail) and "3000" not in json.dumps(err.detail)   # 7: nessun contenuto precedente nella risposta


def test_revocation_denies_all_nine_timeframes_zero_reads(env):
    for tf in chart_store.ALL_TFS:
        env.get(tf, limit=200)
    warm = env.reads
    write_auth(env.auth, {})
    for tf in chart_store.ALL_TFS:                                          # aggregazioni multitimeframe: nessuna aggira la revoca
        env.denied(tf=tf, limit=200)
    assert env.reads == warm


def test_sources_listing_reflects_revocation_immediately(env):
    assert chart_api.sources()["sources"][0]["authorized"] is True
    write_auth(env.auth, {})
    s = chart_api.sources()["sources"][0]
    assert s["authorized"] is False and s["authorized_windows"] == []


# ---------------------------------------------------------------- metadata mancanti, corrotti, non verificabili, sostituiti
@pytest.mark.parametrize("how", ["delete", "corrupt", "empty", "wrong_schema", "not_owner", "directory"])
def test_missing_corrupt_or_unverifiable_authorization_fails_closed_even_with_warm_cache(env, how):
    env.get("H1")
    warm = env.reads
    if how == "delete":
        env.auth.unlink()
    elif how == "corrupt":
        env.auth.write_text("{not json", encoding="utf-8")
    elif how == "empty":
        env.auth.write_bytes(b"")
    elif how == "wrong_schema":
        env.auth.write_text(json.dumps({"schema": "OTHER", "authorized_by": "owner", "datasets": {env.dsid: explicit("2026-01-01T00:00:00Z", "2027-01-01T00:00:00Z")}}))
    elif how == "not_owner":
        env.auth.write_text(json.dumps({"schema": "NEXUS_CHART_AUTHORIZATION_V1", "authorized_by": "someone", "datasets": {env.dsid: explicit("2026-01-01T00:00:00Z", "2027-01-01T00:00:00Z")}}))
    elif how == "directory":                                                # illeggibile (non assente)
        env.auth.unlink()
        env.auth.mkdir()
    env.denied(tf="H1")
    assert env.reads == warm


def test_restoring_the_exact_authorization_reauthorizes_only_by_content(env):
    env.get("H1")
    good = env.auth.read_bytes()
    write_auth(env.auth, {})
    env.denied(tf="H1")
    env.auth.write_bytes(good)                                              # il ripristino del contenuto valido e' l'unico modo di riottenere l'accesso
    assert env.get("H1")["bars"]


def test_atomic_replacement_with_narrower_window_applies_to_next_request(env):
    assert env.get("H4", 5000)["bars"]                                      # ottobre + novembre
    write_auth(env.auth, {env.dsid: explicit("2026-11-01T00:00:00Z", "2026-12-31T00:00:00Z")})
    env.denied(tf="H4", limit=5000)                                         # attraverserebbe ottobre: ora fuori finestra
    assert env.get("H4", 5)["bars"]                                         # l'intervallo ancora autorizzato resta leggibile (nessun falso negativo)


def test_pagination_is_reauthorized_per_page_after_window_change(env):
    page1 = env.get("H4", 5)
    assert page1["has_more"] is False or page1["next_before"]
    write_auth(env.auth, {env.dsid: explicit("2026-11-01T00:00:00Z", "2026-12-31T00:00:00Z")})
    before = utc(2026, 11, 1, 1)
    env.opened.clear()
    env.denied(tf="H4", limit=5, before=before)                             # la pagina successiva scende in ottobre: negata dopo il restringimento
    env.denied(tf="H4", limit=5, before=before)
    assert "2026-10" not in env.opened                                      # il segmento non piu' autorizzato non viene mai aperto


def test_dataset_authorizations_are_independent_across_sources(monkeypatch):
    e = Env(monkeypatch, extra_ds=("OTHER_DS",))
    write_auth(e.auth, {"TEST_DS": explicit("2026-10-01T00:00:00Z", "2026-12-31T00:00:00Z"), "OTHER_DS": explicit("2026-10-01T00:00:00Z", "2026-12-31T00:00:00Z")})
    assert e.get("H1")["bars"] and e.get("H1", source="OTHER_DS")["bars"]
    write_auth(e.auth, {"OTHER_DS": explicit("2026-10-01T00:00:00Z", "2026-12-31T00:00:00Z")})      # revoca solo TEST_DS
    e.denied(tf="H1")
    assert e.get("H1", source="OTHER_DS")["bars"]
    write_auth(e.auth, {"TEST_DS": explicit("2026-10-01T00:00:00Z", "2026-12-31T00:00:00Z")})
    e.denied(tf="H1", source="OTHER_DS")                                    # l'autorizzazione di un dataset non vale per un altro


# ---------------------------------------------------------------- concorrenza
def test_concurrent_requests_never_return_data_started_after_revocation(env):
    env.get("M1", 100)
    revoked = threading.Event()
    results = []
    lock = threading.Lock()

    def worker(i):
        started_after = revoked.is_set()
        try:
            r = env.get("M5" if i % 2 else "M1", 100)
            outcome = ("DATA", len(r["bars"]))
        except HTTPException as ex:
            outcome = ("DENIED", ex.status_code)
        with lock:
            results.append((started_after, outcome))

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(worker, i) for i in range(60)]
        write_auth(env.auth, {})
        revoked.set()
        futs += [pool.submit(worker, i) for i in range(60, 160)]
        for f in futs:
            f.result()
    assert len(results) == 160
    assert all(o == ("DENIED", 403) for started_after, o in results if started_after), "una richiesta avviata dopo la revoca ha ricevuto dati"
    assert all(o[0] in ("DATA", "DENIED") for _, o in results)             # nessun errore inatteso (500, eccezioni non gestite)


def test_revocation_during_a_read_prevents_returning_data(monkeypatch):
    """TOCTOU: la revoca avviene tra il controllo del segmento e la fine della lettura -> il ricontrollo finale nega e non restituisce nulla."""
    e = Env(monkeypatch)
    write_auth(e.auth, {e.dsid: explicit("2026-10-01T00:00:00Z", "2026-12-31T00:00:00Z")})
    inner = chart_store.ChartStore._segment

    def revoking(store, m, tf, seg):
        blob = inner(store, m, tf, seg)
        write_auth(e.auth, {})
        return blob
    monkeypatch.setattr(chart_store.ChartStore, "_segment", revoking)
    e.denied(tf="H1")


def test_guard_revalidates_by_content_not_by_time_or_mtime(tmp_path):
    p = tmp_path / "a.json"
    write_auth(p, {"A": explicit("2026-11-01T00:00:00Z", "2026-12-01T00:00:00Z")})
    g = chart_guard.Guard(auth_path=p, canon_dir=tmp_path / "none")
    g.check("A", utc(2026, 11, 2), utc(2026, 11, 3))
    n = g.reloads
    for _ in range(50):
        g.check("A", utc(2026, 11, 2), utc(2026, 11, 3))
    assert g.reloads == n                                                   # nessun ricalcolo se il contenuto non cambia
    st = p.stat()
    new = p.read_text(encoding="utf-8").replace("2026-12-01", "2026-11-02")  # stessa lunghezza (stesso size), contenuto diverso
    assert len(new) == len(p.read_text(encoding="utf-8"))
    p.write_text(new, encoding="utf-8")
    os.utime(p, ns=(st.st_atime_ns, st.st_mtime_ns))                        # mtime ripristinato: un controllo basato su mtime/TTL non se ne accorgerebbe
    with pytest.raises(chart_guard.PartitionDenied):
        g.check("A", utc(2026, 11, 2), utc(2026, 11, 3))
    assert g.reloads == n + 1


# ---------------------------------------------------------------- metadata canonici (partizioni Phase 7) e classificazione
@pytest.fixture
def canon_env(monkeypatch):
    e = Env(monkeypatch, start=utc(2023, 2, 6), days=6, dsid=PHASE7)
    canon = e.dir / "canon"
    canon.mkdir()
    for f in chart_guard.CANON_FILES:
        shutil.copy(SERVER / "research_scripts" / "phase7" / f, canon / f)
    rec = json.loads((SERVER / "chart_authorization.json").read_text(encoding="utf-8"))
    rec["datasets"] = {PHASE7: rec["datasets"][PHASE7]}
    e.rec = rec
    e.canon = canon
    e.auth.write_text(json.dumps(rec), encoding="utf-8")
    monkeypatch.setenv("NEXUS_CHART_PARTITION_DIR", str(canon))
    chart_api.reset_caches()
    return e


def test_canonical_manifest_change_after_warm_cache_closes_access(canon_env):
    e = canon_env
    assert e.get("H4")["bars"]                                              # autorizzato dal record legato per hash ai manifest canonici
    warm = e.reads
    f = e.canon / chart_guard.CANON_FILES[0]
    original = f.read_bytes()
    f.write_bytes(original + b" ")                                          # modifica dei metadata canonici, stesso percorso
    err = e.denied(tf="H4")
    assert err.detail["code"] == "AUTHORIZATION_UNAVAILABLE"
    assert e.reads == warm
    f.write_bytes(original)                                                 # ripristino del contenuto canonico = ripristino dell'autorita'
    assert e.get("H4")["bars"]


@pytest.mark.parametrize("which", range(3))
def test_canonical_manifest_removed_or_unreadable_fails_closed(canon_env, which):
    e = canon_env
    e.get("H4")
    warm = e.reads
    f = e.canon / chart_guard.CANON_FILES[which]
    f.unlink()
    e.denied(tf="H4")
    f.mkdir()                                                               # presente ma non leggibile come file
    e.denied(tf="H4")
    assert e.reads == warm


def test_classification_change_to_sealed_segment_is_denied(canon_env):
    e = canon_env
    e.get("H4")
    warm = e.reads
    for seg in ("final_holdout", "locked_validation", "internal_validation"):
        rec = copy.deepcopy(e.rec)
        rec["datasets"][PHASE7]["allowed_segment_names"] = [seg]
        e.auth.write_text(json.dumps(rec), encoding="utf-8")
        e.denied(tf="H4")                                                   # riclassificazione verso partizioni sigillate / non autorizzate
    assert e.reads == warm
    e.auth.write_text(json.dumps(e.rec), encoding="utf-8")
    assert e.get("H4")["bars"]


def test_canonical_manifest_replacement_changing_segment_dates_is_denied(canon_env):
    """Il manifest canonico viene sostituito con uno che sposta le date: l'hash legato non coincide piu' -> nessuna finestra, per qualunque dataset."""
    e = canon_env
    e.get("H4")
    f = e.canon / "partition_manifest_v1.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    data["payload"]["segments"][0]["declared_end"] = "2030-01-01"
    f.write_text(json.dumps(data), encoding="utf-8")
    e.denied(tf="H4")
    assert chart_api.get_guard().windows(PHASE7) == []
