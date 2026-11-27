"""Costruzione (lato PC) dello store di barre del Chart. Sola lettura delle sorgenti; scrive solo in --out.

  python tools/build_chart_store.py xm --src <cartella gold con m1.jsonl+manifest.json> --out <store>
  python tools/build_chart_store.py dukascopy --root <.../decoded> --out <store> --from 2023-02-06 --to 2023-02-28

Dukascopy: PRIMA di aprire il file di un giorno si interroga la guardia (chart_guard) con l'intervallo [00:00, 24:00) UTC del giorno; un giorno non autorizzato (sigillato, consumato,
validazione bloccata, fuori da una finestra esplicita, manifest cambiati) interrompe la costruzione SENZA aprire il file. Nessuna deduzione "per data".
XM: l'export M1 e' verificato per sha256 contro il suo manifest; la finestra e' quella del manifest.
"""
import argparse, csv, datetime as dt, gzip, hashlib, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "server"))
import chart_guard, chart_store


def xm(src, out):
    man = json.load(open(os.path.join(src, "manifest.json"), encoding="utf-8"))
    raw = open(os.path.join(src, "m1.jsonl"), "rb").read()
    if hashlib.sha256(raw).hexdigest() != man["m1_sha256"]:
        raise SystemExit("HASH DATASET XM NON COINCIDE: costruzione annullata")
    rows = [{"time": b["t"] // 1000, "open": b["o"], "high": b["h"], "low": b["l"], "close": b["c"]} for b in map(json.loads, raw.decode().splitlines())]
    scale = 100  # digits=2 nel manifest
    for r in rows:
        for k in ("open", "high", "low", "close"):
            if abs(r[k] * scale - round(r[k] * scale)) > 1e-6:
                raise SystemExit("precisione prezzo oltre le cifre dichiarate")
    meta = {"dataset_id": man["dataset_id"], "label": "XM GOLD 16-20 Nov 2026 (MT5 ticks, bid)", "feed_kind": "MT5_BROKER_EXPORT", "broker_server": "XMGlobal-MT5 10 (dichiarato dall'export; non riverificato)",
            "symbol_actual": man["symbol"], "symbol_aliases": ["GOLD", "XAUUSD"], "provenance": "NEXUS_CHART_INT_03 export, bar_construction=%s, n_ticks=%d, tick_sha256=%s (tick non presenti su disco)" % (man["bar_construction"], man["n_ticks"], man["tick_sha256"]),
            "source_sha256": man["m1_sha256"], "clock_basis": "TERMINAL_CLOCK (offset broker non verificato; osservato terminale-UTC = %d ms)" % (man["tick_time_msc"] - man["utc_now_ms"]), "purpose": man.get("purpose"),
            "quality_verdict": "PASS (CHART-INT-03 quality.json)", "instrument_spec": {"digits": man["digits"], "point": man["point"], "tick_size": man["trade_tick_size"], "price_unit": "USD per troy ounce"},
            "authorization": {"record": "server/chart_authorization.json"}}
    m = chart_store.build_store(rows, out, meta, None, scale)
    print(json.dumps({"dataset_id": m["dataset_id"], "n_m1": m["n_m1"], "calendar": m["calendar"], "counts": m["completeness_counts"]}, indent=1))


def _day_ticks(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for row in csv.reader(f):
            try:
                yield int(row[0]), float(row[1])
            except (ValueError, IndexError):
                continue                                   # intestazione o riga non numerica


def dukascopy(root, out, d0, d1):
    guard = chart_guard.Guard()
    if guard.error:
        raise SystemExit("AUTORIZZAZIONE NON DISPONIBILE (fail-closed): " + guard.error)
    day = dt.date.fromisoformat(d0)
    last = dt.date.fromisoformat(d1)
    bars, files = {}, []
    while day <= last:
        t0 = int(dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc).timestamp())
        guard.check("DUKASCOPY_XAUUSD_PHASE7", t0, t0 + 86400)       # PRIMA di aprire il file
        p = os.path.join(root, str(day.year), day.isoformat() + ".csv.gz")
        if os.path.isfile(p):
            files.append(os.path.basename(p))
            for ms, bid in _day_ticks(p):
                if not t0 * 1000 <= ms < (t0 + 86400) * 1000:
                    raise SystemExit("tick fuori dal giorno del file: " + p)
                k = ms // 60000 * 60
                b = bars.get(k)
                if b is None:
                    bars[k] = [bid, bid, bid, bid]
                else:
                    b[1] = max(b[1], bid); b[2] = min(b[2], bid); b[3] = bid
        day += dt.timedelta(days=1)
    rows = [{"time": k, "open": v[0], "high": v[1], "low": v[2], "close": v[3]} for k, v in sorted(bars.items())]
    if not rows:
        raise SystemExit("nessuna barra costruita")
    meta = {"dataset_id": "DUKASCOPY_XAUUSD_PHASE7", "label": "Dukascopy XAUUSD (Phase 7, partizione development_discovery)", "feed_kind": "DUKASCOPY", "broker_server": None, "symbol_actual": "XAUUSD", "symbol_aliases": ["XAUUSD"],
            "provenance": "Dukascopy tick decoded (bid) %s..%s, %d file; NON e' il feed MT5 del broker" % (d0, d1, len(files)), "source_sha256": hashlib.sha256(",".join(files).encode()).hexdigest(), "clock_basis": "UTC (timestamp epoch del downloader)",
            "purpose": "RESEARCH_DISCOVERY_PARTITION", "quality_verdict": "PASS_WITH_NOTES (new_dataset_integrity_report_v1)", "instrument_spec": {"price_unit": "USD per troy ounce", "digits": 3}, "authorization": {"record": "server/chart_authorization.json"}}
    m = chart_store.build_store(rows, out, meta, None, 1000)
    print(json.dumps({"dataset_id": m["dataset_id"], "n_m1": m["n_m1"], "days": len(files), "calendar_rules": len(m["calendar"]["rules"]), "counts": m["completeness_counts"]}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("xm"); a.add_argument("--src", required=True); a.add_argument("--out", required=True)
    b = sub.add_parser("dukascopy"); b.add_argument("--root", required=True); b.add_argument("--out", required=True); b.add_argument("--from", dest="d0", required=True); b.add_argument("--to", dest="d1", required=True)
    args = ap.parse_args()
    if args.cmd == "xm":
        xm(args.src, args.out)
    else:
        try:
            dukascopy(args.root, args.out, args.d0, args.d1)
        except chart_guard.PartitionDenied as ex:
            raise SystemExit("PARTIZIONE NON AUTORIZZATA, costruzione interrotta senza aprire il file: " + str(ex))
