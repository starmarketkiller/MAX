"""Fixture SINTETICA DI SCALA per la verifica Linux/Docker (nessun dato di mercato reale, nessun dato Dukascopy: i dati reali non lasciano il PC).

Stessi file e stesso dataset_id della fixture approvata (tools/make_synthetic_chart_fixture.py), ma con ~DAYS giorni di M1 sintetici (default 547 = durata della partizione
development_discovery) con pause giornaliere e weekend, cosi' da avere un volume di barre/segmenti paragonabile allo store storico reale (~530k M1) e misurare RAM, tempi e
dimensioni delle risposte con i limiti Render (512 MiB). Uso: python tools/make_scale_fixture.py <dir_output> [giorni]
Poi: REAL_STORE_DIR=<out>/store REAL_TRANSFER_MANIFEST=<out>/transfer_manifest.json REAL_EXPECTED=<out>/expected.json REAL_RECORD=<out>/authorization_record.json bash tools/docker_runtime_verify.sh
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "server"))
import chart_store  # noqa: E402

DS = "XM-GOLD-2026-11-16-20"           # stesso id della fixture approvata: percorsi e record coincidono col deploy


def build_rows(days: int, end: dt.datetime):
    rnd = random.Random(20261128)          # deterministico
    t = int((end - dt.timedelta(days=days)).timestamp()) // 60 * 60
    t_end = int(end.timestamp())
    p, rows = 2000.0, []
    while t < t_end:
        d = dt.datetime.fromtimestamp(t, dt.timezone.utc)
        wd, mi = d.weekday(), d.hour * 60 + d.minute
        closed = wd == 5 or (wd == 4 and mi >= 1320) or (wd == 6 and mi < 1320) or 1320 <= mi < 1380      # weekend e pausa giornaliera 22:00-23:00
        if not closed:
            p = max(100.0, p + rnd.uniform(-0.35, 0.35))
            o = round(p, 2); c = round(p + rnd.uniform(-0.2, 0.2), 2)
            rows.append({"time": t, "open": o, "high": round(max(o, c) + rnd.uniform(0, 0.3), 2), "low": round(min(o, c) - rnd.uniform(0, 0.3), 2), "close": c})
        t += 60
    return rows


def main(out: str, days: int = 547) -> None:
    os.makedirs(out, exist_ok=True)
    store = os.path.join(out, "store")
    end = dt.datetime(2026, 11, 20, 22, 0, tzinfo=dt.timezone.utc)
    rows = build_rows(days, end)
    meta = {"dataset_id": DS, "feed_kind": "SYNTHETIC_SCALE_FIXTURE", "symbol_actual": "GOLD", "symbol_aliases": ["GOLD", "XAUUSD"], "provenance": "SYNTHETIC - NOT MARKET DATA (scale test only)",
            "clock_basis": "TERMINAL_CLOCK", "instrument_spec": {"digits": 2}}
    chart_store.build_store(rows, store, meta, None, 100)
    files, total = [], 0
    for b, _, fs in os.walk(os.path.join(store, DS)):
        for f in sorted(fs):
            p = os.path.join(b, f)
            d = open(p, "rb").read()
            files.append({"source_relative": os.path.relpath(p, store).replace("\\", "/"), "bytes": len(d), "sha256": hashlib.sha256(d).hexdigest()})
            total += len(d)
    files.sort(key=lambda x: x["source_relative"])
    st = chart_store.ChartStore(store)
    expected = {}
    for tf in chart_store.ALL_TFS:
        n, before = 0, None
        while True:
            r = st.read(DS, tf, 5000, before)
            n += len(r["bars"])
            if not r["has_more"]:
                break
            before = r["next_before"]
        expected[tf] = n
    first = dt.datetime.fromtimestamp(rows[0]["time"], dt.timezone.utc).strftime("%Y-%m-%dT00:00:00Z")
    manifest = {"kind": "DATA_TRANSFER_MANIFEST", "synthetic": True, "scale_fixture": True, "files": files, "file_count": len(files), "total_bytes": total,
                "dataset": {"dataset_id": DS, "manifest_sha256": hashlib.sha256(open(os.path.join(store, DS, "manifest.json"), "rb").read()).hexdigest()}}
    record = {"schema": "NEXUS_CHART_AUTHORIZATION_V1", "authorized_by": "owner", "decision_ref": "SYNTHETIC SCALE FIXTURE", "datasets": {DS: {"kind": "EXPLICIT_WINDOWS", "windows_utc": [[first, "2026-11-20T22:00:00Z"]]}}}
    json.dump(manifest, open(os.path.join(out, "transfer_manifest.json"), "w"), indent=1)
    json.dump(record, open(os.path.join(out, "authorization_record.json"), "w"), indent=1, sort_keys=True)
    json.dump({"expected_bars": expected, "m1_rows": len(rows)}, open(os.path.join(out, "expected.json"), "w"), indent=1)
    print(json.dumps({"files": len(files), "bytes": total, "m1_rows": len(rows), "expected": expected}))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "chart_scale_fixture", int(sys.argv[2]) if len(sys.argv) > 2 else 547)
