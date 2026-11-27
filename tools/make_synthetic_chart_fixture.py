"""Fixture SINTETICA per la verifica runtime Docker/CI (nessun dato di mercato reale).

Costruisce con `chart_store.build_store` un dataset chiamato come quello XM autorizzato (stesso dataset_id, cosi' i percorsi e il record coincidono col
deploy) ma con barre M1 sintetiche, e scrive: il manifest di trasferimento (stesso formato di DATA_TRANSFER_MANIFEST.json), il record di autorizzazione
XM-only e i conteggi attesi per timeframe. Serve a provare il PERCORSO (immagine, permessi, restart, revoca, memoria) senza i dati di produzione.
Uso: python tools/make_synthetic_chart_fixture.py <dir_output>
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "server"))
import chart_store  # noqa: E402

DS = "XM-GOLD-2026-11-16-20"


def main(out: str) -> None:
    os.makedirs(out, exist_ok=True)
    store = os.path.join(out, "store")
    t0 = int(dt.datetime(2026, 11, 16, 1, 0, tzinfo=dt.timezone.utc).timestamp())
    rows = []
    end = int(dt.datetime(2026, 11, 20, 22, 0, tzinfo=dt.timezone.utc).timestamp())      # dentro la finestra autorizzata (come l'export XM reale: ultimo minuto 2026-11-20 21:59)
    for i in range(5 * 1440):
        m = i % 1440
        if 1380 <= m < 1440 or t0 + i * 60 >= end:
            continue
        p = 3500.0 + ((i * 37) % 997) * 0.05
        rows.append({"time": t0 + i * 60, "open": round(p, 2), "high": round(p + 0.4, 2), "low": round(p - 0.4, 2), "close": round(p + 0.1, 2)})
    meta = {"dataset_id": DS, "feed_kind": "SYNTHETIC_RUNTIME_FIXTURE", "symbol_actual": "GOLD", "symbol_aliases": ["GOLD", "XAUUSD"], "provenance": "SYNTHETIC - NOT MARKET DATA",
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
    manifest = {"kind": "DATA_TRANSFER_MANIFEST", "synthetic": True, "files": files, "file_count": len(files), "total_bytes": total,
                "dataset": {"dataset_id": DS, "manifest_sha256": hashlib.sha256(open(os.path.join(store, DS, "manifest.json"), "rb").read()).hexdigest()}}
    record = {"schema": "NEXUS_CHART_AUTHORIZATION_V1", "authorized_by": "owner", "decision_ref": "SYNTHETIC RUNTIME FIXTURE", "datasets": {DS: {"kind": "EXPLICIT_WINDOWS", "windows_utc": [["2026-11-16T00:00:00Z", "2026-11-20T22:00:00Z"]]}}}
    json.dump(manifest, open(os.path.join(out, "transfer_manifest.json"), "w"), indent=1)
    json.dump(record, open(os.path.join(out, "authorization_record.json"), "w"), indent=1, sort_keys=True)
    json.dump({"expected_bars": expected, "m1_rows": len(rows)}, open(os.path.join(out, "expected.json"), "w"), indent=1)
    print(json.dumps({"files": len(files), "bytes": total, "expected": expected}))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "chart_fixture")
