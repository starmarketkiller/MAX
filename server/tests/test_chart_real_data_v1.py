"""CHART-REAL-DATA-V1 - test dello store, della guardia di partizione e delle API del Chart.
Dati: serie M1 sintetiche COSTRUITE NEL TEST (per verificare la meccanica: duplicati, buchi, cache, RAM) + l'export XM reale gia' autorizzato (SKIP se assente).
Le chiamate HTTP girano in un sottoprocesso (l'app e' importata una sola volta per processo e legge l'ambiente all'import)."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tracemalloc
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
import chart_guard  # noqa: E402
import chart_store  # noqa: E402

T0 = int(dt.datetime(2026, 11, 16, 0, 0, tzinfo=dt.timezone.utc).timestamp())        # lunedi'
XM_DIR = os.environ.get("NEXUS_CHART_TEST_XM_DIR", r"C:\Users\User\ClaudeWork\NEXUS_CHART_INT_03\runtime\gold")


def mk_rows(n_days=3, start=T0, break_start_min=1380, break_len=60, holes=(), price=3000.0):
    """M1 sintetici: 24 h al giorno con una pausa giornaliera ricorrente; `holes` = minuti (dall'inizio) rimossi in modo NON ricorrente."""
    rows = []
    for i in range(n_days * 1440):
        m = i % 1440
        if break_start_min <= m < break_start_min + break_len or i in holes:
            continue
        p = price + (i % 97) * 0.01
        rows.append({"time": start + i * 60, "open": p, "high": p + 0.30, "low": p - 0.30, "close": p + 0.10})
    return rows


def meta(dsid="TEST_DS", **extra):
    m = {"dataset_id": dsid, "feed_kind": "TEST", "symbol_actual": "GOLD", "symbol_aliases": ["GOLD", "XAUUSD"], "provenance": "unit test", "clock_basis": "TERMINAL_CLOCK", "instrument_spec": {"digits": 2}}
    m.update(extra)
    return m


def tmpdir(prefix="chart_t_"):
    return Path(tempfile.mkdtemp(prefix=prefix))


def auth_file(d: Path, dsid="TEST_DS", windows=None):
    p = d / "auth.json"
    p.write_text(json.dumps({"schema": "NEXUS_CHART_AUTHORIZATION_V1", "authorized_by": "owner", "decision_ref": "test", "bound_manifests": {},
                             "datasets": {dsid: {"kind": "EXPLICIT_WINDOWS", "windows_utc": windows or [["2026-11-01T00:00:00Z", "2026-12-31T00:00:00Z"]]}}}), encoding="utf-8")
    return p


# ============================================================ store: costruzione e completezza
def test_duplicate_or_unaligned_m1_rejected():
    rows = mk_rows(1)
    with pytest.raises(chart_store.StoreError) as e:
        chart_store.build_store(rows + [rows[-1]], tmpdir(), meta())
    assert e.value.code == "M1_DUPLICATE_OR_UNORDERED"
    with pytest.raises(chart_store.StoreError) as e:
        chart_store.build_store([dict(rows[0], time=rows[0]["time"] + 7)], tmpdir(), meta())
    assert e.value.code == "M1_NOT_ALIGNED"
    bad = [dict(rows[0], high=rows[0]["low"] - 1)]
    with pytest.raises(chart_store.StoreError) as e:
        chart_store.build_store(bad, tmpdir(), meta())
    assert e.value.code == "M1_OHLC_INCOHERENT"


def test_completeness_classes_complete_partial_gap_not_dropped():
    holes = {5 * 60 + 17, 5 * 60 + 18, 5 * 60 + 19}                       # buco di 3 minuti NON ricorrente (05:17-05:19)
    rows = mk_rows(5, holes=holes)
    root = tmpdir()
    m = chart_store.build_store(rows, root, meta(), None, 100)
    assert m["calendar"]["status"] == "UNVERIFIED" and m["calendar"]["rules"] == [{"dow": None, "start_min": 1380, "duration_min": 60}]
    st = chart_store.ChartStore(root)
    h1 = {b["time"]: b for b in st.read("TEST_DS", "H1", 5000)["bars"]}
    assert len(h1) == len({chart_store.bucket(r["time"], "H1")[0] for r in rows})            # nessuna barra scartata
    hole_bar = T0 + 5 * 3600
    assert h1[hole_bar]["completeness"] == "GAP" and "UNEXPLAINED_MISSING_MINUTES" in h1[hole_bar]["reason"] and h1[hole_bar]["minutes_missing"] == 3
    break_bar = T0 + 23 * 3600
    assert break_bar not in h1                                                       # nessuna barra inventata dove non esistono minuti
    h4 = {b["time"]: b for b in st.read("TEST_DS", "H4", 5000)["bars"]}
    assert h4[T0 + 20 * 3600]["completeness"] == "PARTIAL" and "CANDIDATE_CALENDAR_UNVERIFIED" in h4[T0 + 20 * 3600]["reason"]   # pausa ricorrente ma calendario NON verificato
    assert h4[T0 + 4 * 3600]["completeness"] == "GAP"                                                                             # contiene il buco di 3 minuti
    assert all(b["completeness"] in ("COMPLETE", "PARTIAL", "GAP") for b in h4.values())


def test_verified_calendar_makes_break_bars_complete_but_not_edges():
    rows = mk_rows(3)
    cal = {"status": "VERIFIED", "rules": [{"dow": None, "start_min": 1380, "duration_min": 60}]}
    root = tmpdir()
    chart_store.build_store(rows, root, meta(), cal, 100)
    h4 = {b["time"]: b for b in chart_store.ChartStore(root).read("TEST_DS", "H4", 5000)["bars"]}
    assert h4[T0 + 20 * 3600]["completeness"] == "COMPLETE" and "CALENDAR_VERIFIED_CLOSURE" in h4[T0 + 20 * 3600]["reason"]
    d1 = {b["time"]: b for b in chart_store.ChartStore(root).read("TEST_DS", "D1", 5000)["bars"]}
    assert d1[T0 + 86400]["completeness"] == "COMPLETE"
    w1 = chart_store.ChartStore(root).read("TEST_DS", "W1", 10)["bars"]
    assert w1[0]["completeness"] == "PARTIAL" and "COVERAGE_EDGE" in w1[0]["reason"]                # la settimana esce dalla copertura: mai COMPLETE


def test_open_bar_only_for_live_datasets():
    rows = mk_rows(1)
    root = tmpdir()
    m = chart_store.build_store(rows, root, meta(), None, 100)
    st = chart_store.ChartStore(root)
    last_end = m["coverage"]["last_end_t"]
    assert all(b["completeness"] != "OPEN" for b in st.read("TEST_DS", "H1", 100, now=T0 + 3600)["bars"])      # storico: mai OPEN
    mf = root / "TEST_DS" / "manifest.json"
    mm = json.loads(mf.read_text()); mm["live"] = True; mf.write_text(json.dumps(mm))
    bars = st.read("TEST_DS", "H1", 100, now=last_end - 1800)["bars"]
    assert bars[-1]["completeness"] == "OPEN" and bars[0]["completeness"] != "OPEN"


# ============================================================ store: lettura, paginazione, integrita'
def test_pagination_has_more_and_no_overlap():
    rows = mk_rows(40)
    root = tmpdir()
    chart_store.build_store(rows, root, meta(), None, 100)
    st = chart_store.ChartStore(root)
    seen, before, pages = [], None, 0
    while True:
        r = st.read("TEST_DS", "H1", 100, before)
        pages += 1
        seen = [b["time"] for b in r["bars"]] + seen
        if not r["has_more"]:
            break
        assert r["next_before"] == r["bars"][0]["time"]
        before = r["next_before"]
    assert seen == sorted(set(seen)) and len(seen) == len({chart_store.bucket(x["time"], "H1")[0] for x in rows}) and pages > 5


def test_timeframe_and_limit_validation():
    root = tmpdir()
    chart_store.build_store(mk_rows(2), root, meta(), None, 100)
    st = chart_store.ChartStore(root)
    for tf, code in (("M7", "TIMEFRAME_UNSUPPORTED"), ("", "TIMEFRAME_UNSUPPORTED")):
        with pytest.raises(chart_store.StoreError) as e:
            st.read("TEST_DS", tf, 10)
        assert e.value.code == code
    for lim in (0, -1, chart_store.MAX_LIMIT + 1):
        with pytest.raises(chart_store.StoreError) as e:
            st.read("TEST_DS", "M1", lim)
        assert e.value.code == "LIMIT_INVALID"
    with pytest.raises(chart_store.StoreError) as e:
        st.manifest("../etc")
    assert e.value.code == "DATASET_ID_INVALID"


def test_contaminated_cache_or_segment_is_never_served():
    root = tmpdir()
    chart_store.build_store(mk_rows(3), root, meta(), None, 100)
    seg = next((root / "TEST_DS" / "H1").glob("*.bin"))
    good = seg.read_bytes()
    seg.write_bytes(good[:-1] + bytes([good[-1] ^ 1]))                                  # un bit alterato
    with pytest.raises(chart_store.StoreError) as e:
        chart_store.ChartStore(root).read("TEST_DS", "H1", 50)
    assert e.value.code == "SEGMENT_HASH_MISMATCH"
    seg.write_bytes(good + b"\0")                                                       # lunghezza diversa
    with pytest.raises(chart_store.StoreError):
        chart_store.ChartStore(root).read("TEST_DS", "H1", 50)
    other = tmpdir()
    chart_store.build_store(mk_rows(3, price=1000.0), other, meta(), None, 100)       # segmento valido ma di un ALTRO dataset copiato qui
    seg.write_bytes(next((other / "TEST_DS" / "H1").glob("*.bin")).read_bytes())
    with pytest.raises(chart_store.StoreError) as e:
        chart_store.ChartStore(root).read("TEST_DS", "H1", 50)
    assert e.value.code == "SEGMENT_HASH_MISMATCH"
    mf = root / "TEST_DS" / "manifest.json"
    mm = json.loads(mf.read_text()); mm["dataset_id"] = "OTHER"; mf.write_text(json.dumps(mm))
    with pytest.raises(chart_store.StoreError) as e:
        chart_store.ChartStore(root).manifest("TEST_DS")
    assert e.value.code == "MANIFEST_INVALID"


def test_pc_disconnection_gives_unreachable_not_data():
    root = tmpdir()
    chart_store.build_store(mk_rows(3), root, meta(), None, 100)
    st = chart_store.ChartStore(root)
    next((root / "TEST_DS" / "M5").glob("*.bin")).unlink()                              # segmento sparito (disco/sync interrotti)
    with pytest.raises(chart_store.StoreError) as e:
        st.read("TEST_DS", "M5", 50)
    assert e.value.code == "STORE_UNREACHABLE"
    shutil.rmtree(root)
    with pytest.raises(chart_store.StoreError) as e:
        st.manifest("TEST_DS")
    assert e.value.code == "STORE_UNREACHABLE"
    assert st.datasets() == []


def test_read_memory_is_bounded_and_independent_of_dataset_size():
    small, large = tmpdir(), tmpdir()
    chart_store.build_store(mk_rows(14), small, meta(), None, 100)                      # ~19k M1
    chart_store.build_store(mk_rows(300), large, meta(), None, 100)                     # ~414k M1 (~9 mesi)
    peaks = []
    for root in (small, large):
        st = chart_store.ChartStore(root)
        tracemalloc.start()
        r = st.read("TEST_DS", "M5", 5000)
        peaks.append(tracemalloc.get_traced_memory()[1])
        tracemalloc.stop()
        assert len(r["bars"]) == 5000 or r["has_more"] is False
    assert peaks[1] < 40 * 1024 * 1024, peaks
    assert peaks[1] < peaks[0] * 3 + 4 * 1024 * 1024, peaks                              # non cresce con la dimensione del dataset


# ============================================================ guardia: fail-closed
def test_guard_denies_everything_by_default_and_on_errors():
    d = tmpdir()
    g = chart_guard.Guard(auth_path=d / "missing.json")
    assert g.error and g.windows("X") == []
    with pytest.raises(chart_guard.PartitionDenied) as e:
        g.check("X", 0, 1)
    assert e.value.code == "AUTHORIZATION_UNAVAILABLE"
    (d / "bad.json").write_text("{not json")
    assert chart_guard.Guard(auth_path=d / "bad.json").error
    p = auth_file(d, "A", [["2026-11-16T00:00:00Z", "2026-11-17T00:00:00Z"]])
    g = chart_guard.Guard(auth_path=p)
    assert g.error is None
    t = int(dt.datetime(2026, 11, 16, tzinfo=dt.timezone.utc).timestamp())
    g.check("A", t, t + 86400)
    for args in (("A", t - 60, t + 60), ("A", t, t + 86401), ("B", t, t + 60)):                    # fuori finestra, a cavallo, dataset non autorizzato
        with pytest.raises(chart_guard.PartitionDenied):
            g.check(*args)


def _real_guard():
    return chart_guard.Guard()


def test_canonical_authorization_phase7_only_discovery_and_nothing_sealed():
    g = _real_guard()
    assert g.error is None, g.error
    ds = "DUKASCOPY_XAUUSD_PHASE7"
    wins = g.windows(ds)
    assert wins == [(int(dt.datetime(2023, 2, 4, tzinfo=dt.timezone.utc).timestamp()), int(dt.datetime(2024, 8, 4, tzinfo=dt.timezone.utc).timestamp()))]

    def day(y, m, d):
        t = int(dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp())
        return t, t + 86400
    g.check(ds, *day(2023, 2, 6))
    g.check(ds, *day(2024, 8, 3))
    for y, m, d in ((2024, 8, 4), (2024, 9, 1), (2025, 5, 3), (2025, 6, 1), (2026, 2, 3), (2026, 2, 4), (2026, 3, 1), (2026, 9, 16), (2023, 2, 3), (2022, 6, 1), (2021, 1, 4)):
        with pytest.raises(chart_guard.PartitionDenied):
            g.check(ds, *day(y, m, d))                                                           # internal_validation, locked, sealed, consumed: tutti negati
    with pytest.raises(chart_guard.PartitionDenied):
        g.check(ds, int(dt.datetime(2024, 8, 3, 12, tzinfo=dt.timezone.utc).timestamp()), int(dt.datetime(2024, 8, 4, 12, tzinfo=dt.timezone.utc).timestamp()))   # a cavallo del confine
    xm = "XM-GOLD-2026-11-16-20"
    with pytest.raises(chart_guard.PartitionDenied):
        g.check(xm, *day(2023, 2, 6))                                                             # le fonti restano separate
    with pytest.raises(chart_guard.PartitionDenied):
        g.check(ds, *day(2026, 11, 17))


def test_authorization_cannot_name_sealed_segments_or_changed_manifests():
    d = tmpdir()
    canon = d / "canon"
    shutil.copytree(SERVER / "research_scripts" / "phase7", canon, ignore=shutil.ignore_patterns("*"))
    canon.mkdir(exist_ok=True)
    for f in chart_guard.CANON_FILES:
        shutil.copy(SERVER / "research_scripts" / "phase7" / f, canon / f)
    base = json.loads((SERVER / "chart_authorization.json").read_text(encoding="utf-8"))
    assert chart_guard.Guard(auth_path=SERVER / "chart_authorization.json", canon_dir=canon).error is None
    for seg in ("final_holdout", "locked_validation", "nome_inesistente"):
        rec = copy.deepcopy(base)
        rec["datasets"]["DUKASCOPY_XAUUSD_PHASE7"]["allowed_segment_names"] = [seg]
        (d / "a.json").write_text(json.dumps(rec))
        g = chart_guard.Guard(auth_path=d / "a.json", canon_dir=canon)
        assert g.error and g.windows("DUKASCOPY_XAUUSD_PHASE7") == [], seg
    (canon / "partition_manifest_v1.json").write_bytes((canon / "partition_manifest_v1.json").read_bytes() + b" ")   # manifest canonico alterato
    g = chart_guard.Guard(auth_path=SERVER / "chart_authorization.json", canon_dir=canon)
    assert g.error and "CANONICAL_MANIFEST_MISSING_OR_CHANGED" in g.error and g.windows("XM-GOLD-2026-11-16-20") == []     # fail-closed per TUTTI i dataset
    shutil.rmtree(canon / "x", ignore_errors=True)


def test_store_checks_guard_before_opening_any_segment():
    """Segmenti in finestra sigillata: la lettura deve fallire con PartitionDenied PRIMA di toccare il file (lo cancelliamo: se venisse aperto vedremmo STORE_UNREACHABLE)."""
    d = tmpdir()
    start = int(dt.datetime(2026, 3, 2, tzinfo=dt.timezone.utc).timestamp())          # dentro il final_holdout
    rows = mk_rows(2, start=start)
    root = d / "store"
    chart_store.build_store(rows, root, meta("DUKASCOPY_XAUUSD_PHASE7"), None, 100)
    for f in (root / "DUKASCOPY_XAUUSD_PHASE7").rglob("*.bin"):
        f.unlink()
    g = _real_guard()
    for tf in ("M1", "H1", "D1", "W1", "MN1"):                                         # nessuna aggregazione multitimeframe aggira la guardia
        with pytest.raises(chart_guard.PartitionDenied):
            chart_store.ChartStore(root).read("DUKASCOPY_XAUUSD_PHASE7", tf, 100, guard=g)
    with pytest.raises(chart_guard.PartitionDenied):
        chart_store.ChartStore(root).read("DUKASCOPY_XAUUSD_PHASE7", "M5", 100, before=start + 10 ** 6, guard=g)       # nemmeno via paginazione


def test_pagination_cannot_cross_into_unauthorized_window():
    d = tmpdir()
    base = int(dt.datetime(2026, 10, 29, tzinfo=dt.timezone.utc).timestamp())
    rows = mk_rows(6, start=base)                                                     # 29 ott .. 3 nov: due segmenti mensili
    root = d / "store"
    chart_store.build_store(rows, root, meta("TEST_DS"), None, 100)
    g = chart_guard.Guard(auth_path=auth_file(d, "TEST_DS", [["2026-11-01T00:00:00Z", "2026-12-01T00:00:00Z"]]))      # autorizzato solo novembre
    st = chart_store.ChartStore(root)
    r = st.read("TEST_DS", "H4", 5, guard=g)                                         # ultime 5 barre: tutte di novembre
    assert r["bars"][0]["time"] >= int(dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc).timestamp())
    with pytest.raises(chart_guard.PartitionDenied):
        st.read("TEST_DS", "H4", 5000, guard=g)                                      # la pagina attraverserebbe ottobre: negata, nessun dato parziale
    with pytest.raises(chart_guard.PartitionDenied):
        st.read("TEST_DS", "H4", 5, before=int(dt.datetime(2026, 11, 1, 1, tzinfo=dt.timezone.utc).timestamp()), guard=g)  # nemmeno scorrendo all'indietro oltre il confine


# ============================================================ API (sottoprocesso)
API_SCRIPT = r"""
import json, os, sys
from fastapi.testclient import TestClient
import app as server
c = TestClient(server.app)
reqs = json.loads(os.environ["REQS"])
out = []
tok = None
if os.environ.get("DO_LOGIN") == "1":
    r = c.post("/api/auth/login", json={"email": os.environ["NEXUS_ADMIN_USER"], "password": os.environ["NEXUS_ADMIN_PASSWORD"]})
    tok = r.json().get("token")
h = {"Authorization": "Bearer " + tok} if tok else {}
for p in reqs:
    r = c.get(p, headers=h)
    try: body = r.json()
    except Exception: body = None
    out.append([r.status_code, body])
print("RESULT" + json.dumps(out, default=str))
"""


def api(reqs, store=None, login=True, **env_extra):
    env = os.environ.copy()
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "NEXUS_ENV": "DEV", "NEXUS_COOKIE_SECURE": "false", "NEXUS_DUKASCOPY_AUTOFETCH": "false", "NEXUS_SEED_ON_START": "false", "NEXUS_QUEUE_DISPATCHER_ENABLED": "false",
                "NEXUS_DB_PATH": str(tmpdir("chart_db_") / "t.db"), "NEXUS_ADMIN_USER": "chart-test@local", "NEXUS_ADMIN_PASSWORD": "chart-test-local-only", "REQS": json.dumps(reqs), "DO_LOGIN": "1" if login else "0"})
    for k in ("NEXUS_CHART_STORE_ROOT", "NEXUS_CHART_DEFAULT_SOURCE", "NEXUS_CHART_DEMO", "NEXUS_CHART_AUTH_FILE", "NEXUS_CHART_PARTITION_DIR"):
        env.pop(k, None)
    if store:
        env["NEXUS_CHART_STORE_ROOT"] = str(store)
    env.update({k: str(v) for k, v in env_extra.items()})
    r = subprocess.run([sys.executable, "-B", "-c", API_SCRIPT], cwd=SERVER, env=env, capture_output=True, text=True, timeout=240)
    line = [ln for ln in r.stdout.splitlines() if ln.startswith("RESULT")]
    assert line, (r.stderr or r.stdout)[-1500:]
    return json.loads(line[-1][6:])


@pytest.fixture(scope="module")
def api_env():
    d = tmpdir("chart_api_")
    store = d / "store"
    rows = mk_rows(5)
    chart_store.build_store(rows, store, meta("TEST_DS"), None, 100)
    return {"dir": d, "store": store, "auth": auth_file(d, "TEST_DS", [["2026-11-01T00:00:00Z", "2026-12-31T00:00:00Z"]]), "rows": rows}


def test_api_requires_authentication(api_env):
    out = api(["/api/chart/ohlc?symbol=GOLD&tf=M15", "/api/chart/sources", "/api/chart/markers?symbol=GOLD"], store=api_env["store"], login=False, NEXUS_CHART_AUTH_FILE=api_env["auth"])
    assert [o[0] for o in out] == [401, 401, 401]


def test_api_real_data_contract_and_errors(api_env):
    q = "/api/chart/ohlc?source=TEST_DS&symbol=GOLD&tf=%s&limit=%d"
    out = api([q % ("H1", 50), q % ("M7", 50), q % ("H1", 0), q % ("H1", 5001), q % ("H1", 10) + "&before=-5", "/api/chart/ohlc?source=TEST_DS&symbol=EURUSD&tf=H1&limit=5",
               "/api/chart/ohlc?source=NOPE&symbol=GOLD&tf=H1&limit=5", "/api/chart/sources"], store=api_env["store"], NEXUS_CHART_AUTH_FILE=api_env["auth"])
    ok, bad_tf, lim0, lim_big, bad_before, bad_sym, nope, srcs = out
    assert ok[0] == 200 and ok[1]["status"] == "AVAILABLE_OFFLINE" and ok[1]["source"] == "REAL_HISTORICAL" and ok[1]["demo"] is False
    b = ok[1]
    for k in ("dataset_id", "feed_kind", "symbol_requested", "symbol_actual", "timeframe", "available_range", "last_update_at", "dataset_version", "quality", "limitations", "has_more", "bars", "calendar_status", "instrument_spec"):
        assert k in b, k
    assert b["timeframe"] == "H1" and len(b["bars"]) == 50 and all(x["completeness"] in ("COMPLETE", "PARTIAL", "GAP", "OPEN") for x in b["bars"])
    steps = {b["bars"][i + 1]["time"] - b["bars"][i]["time"] for i in range(len(b["bars"]) - 1)}
    assert steps <= {3600, 7200}                                                                      # il timeframe E' rispettato (non 900 s)
    assert any("BROKER_CALENDAR_UNVERIFIED" in x for x in b["limitations"]) and any("CLOCK_OFFSET_UNVERIFIED" in x for x in b["limitations"])
    assert bad_tf[0] == 422 and lim0[0] == 422 and lim_big[0] == 422 and bad_before[0] == 422 and bad_sym[0] == 422
    assert nope[0] == 200 and nope[1]["status"] == "UNAVAILABLE" and nope[1]["bars"] == [] and nope[1]["demo"] is False
    spec = srcs[1]["sources"][0]["instrument_spec"]
    assert spec["pip_convention"]["pip_price_usd_per_oz"] == 0.10 and spec["tick_value"] == "NOT_RECORDED" and spec["contract_size"] == "NOT_RECORDED" and spec["account_currency"] == "NOT_RECORDED"
    assert spec["digits"] == 2 and spec["price_change"].startswith("absolute")


def test_api_no_silent_synthetic_fallback_and_demo_is_separate(api_env):
    out = api(["/api/chart/ohlc?symbol=XAUUSD&tf=M15", "/api/chart/ohlc?source=SYNTHETIC_DEMO&symbol=XAUUSD&tf=M5&limit=20", "/api/chart/sources"])      # nessuno store configurato
    assert out[0][0] == 200 and out[0][1]["status"] == "UNAVAILABLE" and out[0][1]["reason"] == "CHART_STORE_NOT_CONFIGURED" and out[0][1]["bars"] == [] and out[0][1]["source"] != "SYNTHETIC_DATA"
    assert out[1][0] == 403 and out[1][1]["detail"]["code"] == "DEMO_DISABLED"
    assert out[2][1]["status"] == "UNAVAILABLE"
    demo = api(["/api/chart/ohlc?source=SYNTHETIC_DEMO&symbol=XAUUSD&tf=M5&limit=20"], NEXUS_CHART_DEMO="1")[0][1]
    assert demo["demo"] is True and demo["source"] == "SYNTHETIC_DATA" and demo["dataset_id"] == "SYNTHETIC_DEMO" and {demo["bars"][i + 1]["time"] - demo["bars"][i]["time"] for i in range(19)} == {300}


def test_api_denies_unauthorized_partitions_and_disconnection(api_env):
    d = tmpdir("chart_api2_")
    store = d / "store"
    start = int(dt.datetime(2026, 3, 2, tzinfo=dt.timezone.utc).timestamp())                    # finestra sigillata
    chart_store.build_store(mk_rows(2, start=start), store, meta("DUKASCOPY_XAUUSD_PHASE7", symbol_aliases=["XAUUSD"], symbol_actual="XAUUSD"), None, 100)
    out = api(["/api/chart/ohlc?source=DUKASCOPY_XAUUSD_PHASE7&symbol=XAUUSD&tf=H1&limit=10", "/api/chart/ohlc?source=DUKASCOPY_XAUUSD_PHASE7&symbol=XAUUSD&tf=M1&limit=10&before=%d" % (start + 100000),
              "/api/chart/ohlc?symbol=XAUUSD&tf=D1&limit=10"], store=store)
    assert [o[0] for o in out] == [403, 403, 403] and all(o[1]["detail"]["code"] == "PARTITION_NOT_AUTHORIZED" for o in out) and not any("bars" in (o[1] or {}) for o in out)
    gone = d / "gone"
    out = api(["/api/chart/ohlc?source=TEST_DS&symbol=GOLD&tf=H1&limit=5", "/api/chart/sources"], store=gone, NEXUS_CHART_AUTH_FILE=api_env["auth"])
    assert out[0][1]["status"] == "UNAVAILABLE" and out[0][1]["reason"] == "SOURCE_UNREACHABLE" and out[1][1]["status"] == "UNAVAILABLE"            # PC/archivio non raggiungibile
    seg = next((api_env["store"] / "TEST_DS" / "H1").glob("*.bin"))
    keep = seg.read_bytes()
    try:
        seg.write_bytes(keep[:-1] + b"\x00" if keep[-1] else keep[:-1] + b"\x01")
        out = api(["/api/chart/ohlc?source=TEST_DS&symbol=GOLD&tf=H1&limit=5000"], store=api_env["store"], NEXUS_CHART_AUTH_FILE=api_env["auth"])
        assert out[0][0] == 503 and out[0][1]["detail"]["code"] == "SEGMENT_HASH_MISMATCH"
    finally:
        seg.write_bytes(keep)


def test_api_response_size_is_bounded(api_env):
    out = api(["/api/chart/ohlc?source=TEST_DS&symbol=GOLD&tf=M1&limit=5000"], store=api_env["store"], NEXUS_CHART_AUTH_FILE=api_env["auth"])
    assert out[0][0] == 200 and len(out[0][1]["bars"]) == 5000
    assert len(json.dumps(out[0][1])) < 3_000_000


def test_markers_expose_closetime_and_alias(api_env):
    out = api(["/api/chart/markers?symbol=XAUUSD"], store=api_env["store"], NEXUS_CHART_AUTH_FILE=api_env["auth"])
    assert out[0][0] == 200 and out[0][1]["visuals"] == [] and isinstance(out[0][1]["markers"], list) and out[0][1]["open"] == [] and out[0][1]["shadows"] == []   # nessun marker inventato


# ============================================================ OHLC contro la fonte reale originale
def _xm_rows():
    p = Path(XM_DIR)
    if not (p / "m1.jsonl").is_file():
        pytest.skip("BLOCKED: export XM non presente")
    man = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
    raw = (p / "m1.jsonl").read_bytes()
    if hashlib.sha256(raw).hexdigest() != man["m1_sha256"]:
        pytest.skip("BLOCKED: hash dell'export XM non coincide")
    return man, [json.loads(x) for x in raw.decode().splitlines() if x]


def _ref_aggregate(rows, tf):
    out = {}
    for r in rows:
        s, _ = chart_store.bucket(r["t"] // 1000, tf)
        b = out.get(s)
        if b is None:
            out[s] = [r["o"], r["h"], r["l"], r["c"]]
        else:
            b[1] = max(b[1], r["h"]); b[2] = min(b[2], r["l"]); b[3] = r["c"]
    return out


def test_real_xm_store_matches_original_export_ohlc_all_timeframes():
    man, orig = _xm_rows()
    root = tmpdir()
    d = tmpdir()
    chart_store.build_store([{"time": r["t"] // 1000, "open": r["o"], "high": r["h"], "low": r["l"], "close": r["c"]} for r in orig], root, meta("XM-GOLD-2026-11-16-20", instrument_spec={"digits": 2}), None, 100)
    st = chart_store.ChartStore(root)
    g = chart_guard.Guard()
    total = 0
    for tf in chart_store.ALL_TFS:
        ref = _ref_aggregate(orig, tf)
        got = {}
        before = None
        while True:
            r = st.read("XM-GOLD-2026-11-16-20", tf, 5000, before, guard=g)
            for b in r["bars"]:
                got[b["time"]] = [b["open"], b["high"], b["low"], b["close"]]
            if not r["has_more"]:
                break
            before = r["next_before"]
        assert set(got) == set(ref), tf                                                       # nessuna barra persa o inventata
        for k, v in ref.items():
            assert all(abs(a - b) < 1e-9 for a, b in zip(got[k], v)), (tf, k)                  # OHLC identico alla fonte originale
        total += len(ref)
    assert total > 2000
    assert d.exists()
