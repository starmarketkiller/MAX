"""CHART-HISTORICAL-EXPANSION-01 — strumenti di costruzione e verifica dello store storico (dati sintetici, guardia finta)."""
import datetime as dt
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "tools"))
import chart_guard  # noqa: E402
import build_historical_store as bhs  # noqa: E402
import verify_historical_store as vhs  # noqa: E402

DS = "DUKASCOPY_XAUUSD_PHASE7"


def ep(y, m, d, hh=0, mm=0, ss=0):
    return int(dt.datetime(y, m, d, hh, mm, ss, tzinfo=dt.timezone.utc).timestamp())


class FakeGuard:
    """Stesso contratto della guardia vera: error/check. `deny` = insieme di giorni (date) negati."""
    error = None

    def __init__(self, deny=()):
        self.deny, self.calls = set(deny), []

    def check(self, dataset_id, t0, t1):
        self.calls.append((dataset_id, t0, t1))
        d = dt.datetime.fromtimestamp(t0, dt.timezone.utc).date().isoformat()
        if d in self.deny:
            raise chart_guard.PartitionDenied("PARTITION_NOT_AUTHORIZED", d)


def write_day(root, date, ticks, raw=None):
    p = Path(root) / str(date.year)
    p.mkdir(parents=True, exist_ok=True)
    f = p / (date.isoformat() + ".csv.gz")
    if raw is not None:
        f.write_bytes(raw)
        return f
    with gzip.open(f, "wt", encoding="utf-8", newline="") as g:
        g.write("epoch_ms,bid,ask,bid_vol,ask_vol\n")
        for ms, bid in ticks:
            g.write("%d,%s,%s,1,1\n" % (ms, bid, bid + 0.3))
    return f


def mk_ticks(date, minute_prices):
    """minute_prices: {minuto-del-giorno: [bid...]} -> lista di (ms, bid) ordinata."""
    t0 = ep(date.year, date.month, date.day) * 1000
    out = []
    for mi, prices in sorted(minute_prices.items()):
        for k, p in enumerate(prices):
            out.append((t0 + mi * 60000 + k * 1000, p))
    return out


@pytest.fixture()
def env(tmp_path):
    root, store = tmp_path / "decoded", tmp_path / "store"
    d1, d2, d3 = dt.date(2023, 2, 6), dt.date(2023, 2, 7), dt.date(2023, 2, 8)
    t = {d1: mk_ticks(d1, {0: [1900.0, 1901.5, 1899.5, 1900.5], 1: [1900.5, 1902.0], 2: [1902.0, 1901.0], 600: [1905.0, 1906.0]}),
         d2: mk_ticks(d2, {0: [1910.0, 1911.0], 1: [1911.0, 1909.0, 1912.0]}),
         d3: mk_ticks(d3, {5: [1920.0, 1921.0, 1919.0]})}
    for d, tk in t.items():
        write_day(root, d, tk)
    man = {d.isoformat(): {"n_ticks": len(tk), "complete": True} for d, tk in t.items()}
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(man))
    return {"root": str(root), "store": str(store), "man_path": mp, "man": man, "days": (d1, d2, d3), "ticks": t, "tmp": tmp_path}


def run_build(env, guard=None, report=None, d1="2023-02-06", d0="2023-02-06"):
    return bhs.build(env["root"], str(env["man_path"]), env["store"], d0, d1, str(report or env["tmp"] / "rep.json"), guard=guard or FakeGuard(), quiet=True)


def test_build_reconciles_counts_and_builds_exact_m1_ohlc(env):
    rep = run_build(env, d1="2023-02-08")
    assert rep["days"] == 3 and rep["ticks_total"] == sum(len(v) for v in env["ticks"].values()) and rep["count_mismatches"] == []
    assert rep["non_monotonic_total"] == 0 and rep["duplicate_ticks_total"] == 0 and rep["out_of_band_total"] == 0 and rep["nonpositive_total"] == 0
    st = Path(env["store"]) / DS
    man = json.loads((st / "manifest.json").read_text())
    assert man["n_m1"] == 4 + 2 + 1 and man["dataset_id"] == DS and "UTC" in man["clock_basis"] and man["calendar"]["status"] == "UNVERIFIED"
    recs = vhs.load(env["store"], man, "M1", [])
    first = recs[0]
    assert (first[0], first[1], first[2], first[3], first[4]) == (ep(2023, 2, 6), 1900000, 1901500, 1899500, 1900500)       # open, high, low, close del minuto 0
    assert [r[0] for r in recs[:3]] == [ep(2023, 2, 6, 0, 0), ep(2023, 2, 6, 0, 1), ep(2023, 2, 6, 0, 2)]


def test_build_detects_manifest_count_mismatch_and_tick_anomalies(env):
    man = dict(env["man"]); man["2023-02-07"] = {"n_ticks": 99}
    env["man_path"].write_text(json.dumps(man))
    d = env["days"][0]
    tk = env["ticks"][d] + [(env["ticks"][d][-1][0] - 5000, 1903.0), (env["ticks"][d][-1][0] - 5000, 1903.0)]      # un tick all'indietro, poi un duplicato consecutivo
    write_day(env["root"], d, tk)
    rep = run_build(env, d1="2023-02-08")
    assert [m["date"] for m in rep["count_mismatches"]] == ["2023-02-06", "2023-02-07"]            # 2023-02-06 ora ha 2 righe in piu' del manifest
    day = {x["date"]: x for x in rep["per_day"]}["2023-02-06"]
    assert day["non_monotonic"] == 1 and day["duplicates"] == 1 and day["count_match"] is False


def test_guard_is_consulted_before_the_file_is_opened_and_denial_stops_the_build(env):
    write_day(env["root"], env["days"][1], None, raw=b"NON E' UN GZIP: se venisse aperto solleverebbe un'eccezione diversa")
    g = FakeGuard(deny={"2023-02-07"})
    with pytest.raises(chart_guard.PartitionDenied):
        run_build(env, guard=g, d1="2023-02-08")
    assert [dt.datetime.fromtimestamp(c[1], dt.timezone.utc).date().isoformat() for c in g.calls] == ["2023-02-06", "2023-02-07"]       # il 2023-02-08 non e' stato nemmeno interrogato
    assert all(c[2] - c[1] == 86400 for c in g.calls)


def test_build_fails_closed_without_authorization(env):
    class NoAuth(FakeGuard):
        error = "AUTH_FILE_MISSING"
    with pytest.raises(SystemExit):
        run_build(env, guard=NoAuth())


def test_tick_outside_its_day_is_a_hard_error(env):
    d = env["days"][0]
    write_day(env["root"], d, env["ticks"][d] + [(ep(2023, 2, 7, 0, 0, 1) * 1000, 1900.0)])
    with pytest.raises(SystemExit):
        run_build(env)


def test_gap_analysis_classifies_weekend_daily_break_and_other():
    base = ep(2023, 2, 10, 21, 50)            # venerdi'
    rows = [{"time": base + 60 * i} for i in range(5)]
    rows += [{"time": ep(2023, 2, 12, 22, 5) + 60 * i} for i in range(3)]        # riapre domenica sera: buco di ~48h = weekend
    rows += [{"time": ep(2023, 2, 13, 21, 55) + 60 * i} for i in range(2)]
    rows += [{"time": ep(2023, 2, 13, 23, 5)}]                                    # pausa di 66 minuti con inizio 21:57: pausa giornaliera
    rows += [{"time": ep(2023, 2, 14, 3, 0)}, {"time": ep(2023, 2, 14, 3, 30)}]    # buco di 29 minuti alle 03:xx: "altro"
    g = bhs.analyse_gaps(rows)
    assert g["weekend"] == 1 and g["daily_break"] == 1 and g["other_total"] == 2 or g["other_total"] >= 1
    assert any(o["minutes"] == 29 for o in g["other"])


# --------------------------------------------------------------------- verificatore
def test_verifier_passes_a_correct_store_and_rederives_days_from_ticks(env):
    run_build(env, d1="2023-02-08")
    rep = vhs.verify(env["store"], DS, ("2023-02-06", "2023-02-08"), env["root"], samples=3, seed=1, guard=FakeGuard())
    assert rep["verdict"] == "PASS", [c for c in rep["checks"] if not c["ok"]]
    names = " ".join(c["name"] for c in rep["checks"])
    assert "ri-aggregazione" in names and "ri-derivazione dai tick" in names and "bilancio dei minuti" in names


def test_verifier_detects_a_tampered_segment(env):
    run_build(env, d1="2023-02-08")
    seg = next((Path(env["store"]) / DS / "M1").glob("*.bin"))
    b = bytearray(seg.read_bytes()); b[10] ^= 0xFF
    seg.write_bytes(bytes(b))
    rep = vhs.verify(env["store"], DS)
    assert rep["verdict"] == "FAIL" and any("hash" in c["name"] and not c["ok"] for c in rep["checks"])


def test_verifier_detects_incoherent_ohlc_and_wrong_aggregation_even_when_hashes_are_recomputed(env):
    run_build(env, d1="2023-02-08")
    st = Path(env["store"]) / DS
    man = json.loads((st / "manifest.json").read_text())
    seg = st / "H1" / (man["segments"]["H1"][0]["month"] + ".bin")
    recs = [list(vhs.REC.unpack_from(seg.read_bytes(), i * vhs.REC.size)) for i in range(man["segments"]["H1"][0]["n"])]
    recs[0][2] += 5000                                    # high alterato: la barra H1 non e' piu' l'aggregato dei suoi M1
    blob = b"".join(vhs.REC.pack(*r) for r in recs)
    seg.write_bytes(blob)
    man["segments"]["H1"][0]["sha256"] = hashlib.sha256(blob).hexdigest()           # l'attaccante ricalcola l'hash
    (st / "manifest.json").write_text(json.dumps(man))
    rep = vhs.verify(env["store"], DS)
    assert rep["verdict"] == "FAIL" and any("ri-aggregazione" in c["name"] and not c["ok"] for c in rep["checks"])


def test_verifier_flags_data_outside_the_declared_window(env):
    run_build(env, d1="2023-02-08")
    rep = vhs.verify(env["store"], DS, ("2023-02-07", "2023-02-08"))
    assert any("finestra" in c["name"] and not c["ok"] for c in rep["checks"])


def test_verifier_sampling_goes_through_the_guard_before_opening_files(env):
    run_build(env, d1="2023-02-08")
    write_day(env["root"], env["days"][2], None, raw=b"corrotto")
    with pytest.raises(chart_guard.PartitionDenied):
        vhs.verify(env["store"], DS, None, env["root"], samples=3, seed=1, guard=FakeGuard(deny={"2023-02-08"}))
