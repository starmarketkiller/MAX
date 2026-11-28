"""Costruzione ESTESA e verificata dello store Dukascopy (partizione `development_discovery`). Sola lettura delle sorgenti; scrive solo in --out e --report.

  python tools/build_historical_store.py --root <.../phase7/data_cache_new_period/decoded> --data-manifest <.../data_cache_new_period/manifest.json> \
         --out <store> --from 2023-02-04 --to 2024-08-03 --report <build_report.json>

Regole di sicurezza (invariate rispetto a tools/build_chart_store.py):
  * PRIMA di aprire il file di un giorno si interroga la guardia di partizione con [00:00, 24:00) UTC del giorno: un giorno non autorizzato (sigillato, consumato, validazione bloccata,
    fuori da una finestra esplicita, manifest cambiati) interrompe la costruzione SENZA aprire il file. Nessuna deduzione "per data".
  * Nessun tick entra nello store: solo barre M1 (bid) e le aggregazioni; la riconciliazione per giorno e' scritta nel rapporto, non nello store.
Controlli per giorno: conteggio righe = n_ticks del manifest dati, timestamp monotoni non decrescenti, tick duplicati consecutivi (stesso ms e stesso bid), prezzi non positivi / fuori banda,
tick fuori dal giorno (errore). Dopo la costruzione: analisi dei buchi (weekend, pausa giornaliera, altri). UTC e calendario NON sono dichiarati verificati.
"""
import argparse, csv, datetime as dt, gzip, hashlib, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "server"))
import chart_guard, chart_store

DATASET_ID = "DUKASCOPY_XAUUSD_PHASE7"
PRICE_BAND = (500.0, 5000.0)            # banda di plausibilita' per XAUUSD USD/oz (segnala, non scarta)
GAP_MIN = 10                            # minuti: soglia per l'analisi dei buchi


def read_day(path, t0):
    """Legge un giorno gia' autorizzato. Ritorna (minute_bars{minuto: [o,h,l,c]}, stats)."""
    st = {"rows": 0, "skipped": 0, "non_monotonic": 0, "duplicates": 0, "out_of_band": 0, "nonpositive": 0, "first_ms": None, "last_ms": None, "min_bid": None, "max_bid": None}
    bars, prev_ms, prev_bid = {}, None, None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for row in csv.reader(f):
            try:
                ms, bid = int(row[0]), float(row[1])
            except (ValueError, IndexError):
                st["skipped"] += 1                        # intestazione o riga non numerica
                continue
            if not t0 * 1000 <= ms < (t0 + 86400) * 1000:
                raise SystemExit("tick fuori dal giorno del file: %s (%d)" % (path, ms))
            st["rows"] += 1
            if prev_ms is not None:
                if ms < prev_ms:
                    st["non_monotonic"] += 1
                elif ms == prev_ms and bid == prev_bid:
                    st["duplicates"] += 1
            prev_ms, prev_bid = ms, bid
            if bid <= 0:
                st["nonpositive"] += 1
                continue
            if not PRICE_BAND[0] <= bid <= PRICE_BAND[1]:
                st["out_of_band"] += 1
            st["min_bid"] = bid if st["min_bid"] is None else min(st["min_bid"], bid)
            st["max_bid"] = bid if st["max_bid"] is None else max(st["max_bid"], bid)
            if st["first_ms"] is None:
                st["first_ms"] = ms
            st["last_ms"] = ms
            k = ms // 60000 * 60
            b = bars.get(k)
            if b is None:
                bars[k] = [bid, bid, bid, bid]
            else:
                b[1] = max(b[1], bid); b[2] = min(b[2], bid); b[3] = bid
    return bars, st


def analyse_gaps(rows):
    """Buchi >= GAP_MIN minuti tra M1 consecutive, classificati in modo descrittivo (non e' un calendario verificato)."""
    out = {"n": 0, "minutes": 0, "weekend": 0, "daily_break": 0, "other": [], "break_start_minutes_utc": {}}
    for a, b in zip(rows, rows[1:]):
        miss = (b["time"] - a["time"]) // 60 - 1
        if miss < GAP_MIN:
            continue
        s = a["time"] + 60
        d = dt.datetime.fromtimestamp(s, dt.timezone.utc)
        out["n"] += 1; out["minutes"] += miss
        if miss >= 24 * 60:                                # ~un giorno o piu': chiusura di fine settimana o festivo
            out["weekend"] += 1
        elif miss <= 120 and d.hour in (20, 21, 22, 23):    # pausa giornaliera di fine sessione
            out["daily_break"] += 1
            key = "%02d:%02d" % (d.hour, d.minute)
            out["break_start_minutes_utc"][key] = out["break_start_minutes_utc"].get(key, 0) + 1
        else:
            if len(out["other"]) < 200:
                out["other"].append({"start_utc": d.isoformat(), "minutes": miss, "weekday": d.strftime("%a")})
    out["other_total"] = out["n"] - out["weekend"] - out["daily_break"]
    return out


def build(root, data_manifest_path, out, d0, d1, report_path, guard=None, quiet=False):
    t_start = time.time()
    guard = guard or chart_guard.Guard()
    if getattr(guard, "error", None):
        raise SystemExit("AUTORIZZAZIONE NON DISPONIBILE (fail-closed): " + guard.error)
    data_man = json.load(open(data_manifest_path, encoding="utf-8"))
    man_sha = hashlib.sha256(open(data_manifest_path, "rb").read()).hexdigest()
    day, last = dt.date.fromisoformat(d0), dt.date.fromisoformat(d1)
    bars, files, per_day, mism = {}, [], [], []
    while day <= last:
        t0 = int(dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc).timestamp())
        guard.check(DATASET_ID, t0, t0 + 86400)            # PRIMA di aprire il file
        p = os.path.join(root, str(day.year), day.isoformat() + ".csv.gz")
        entry = data_man.get(day.isoformat())
        if os.path.isfile(p):
            files.append(os.path.basename(p))
            mb, st = read_day(p, t0)
            for k, v in mb.items():
                b = bars.get(k)
                if b is None:
                    bars[k] = v
                else:
                    b[1] = max(b[1], v[1]); b[2] = min(b[2], v[2]); b[3] = v[3]
            exp = entry.get("n_ticks") if entry else None
            st.update({"date": day.isoformat(), "manifest_n_ticks": exp, "count_match": exp == st["rows"], "weekday": day.weekday(), "minutes": len(mb)})
            if exp is not None and exp != st["rows"]:
                mism.append({"date": day.isoformat(), "file_rows": st["rows"], "manifest_n_ticks": exp})
            per_day.append({k: st[k] for k in ("date", "rows", "manifest_n_ticks", "count_match", "weekday", "minutes", "non_monotonic", "duplicates", "out_of_band", "nonpositive", "skipped", "min_bid", "max_bid")})
        else:
            per_day.append({"date": day.isoformat(), "rows": None, "manifest_n_ticks": entry.get("n_ticks") if entry else None, "file_missing": True})
        day += dt.timedelta(days=1)
    rows = [{"time": k, "open": v[0], "high": v[1], "low": v[2], "close": v[3]} for k, v in sorted(bars.items())]
    if not rows:
        raise SystemExit("nessuna barra costruita")
    meta = {"dataset_id": DATASET_ID, "label": "Dukascopy XAUUSD (Phase 7, partizione development_discovery %s..%s)" % (d0, d1), "feed_kind": "DUKASCOPY", "broker_server": None,
            "symbol_actual": "XAUUSD", "symbol_aliases": ["XAUUSD"],
            "provenance": "Dukascopy tick decoded (bid) %s..%s, %d file; NON e' il feed MT5 del broker; data manifest sha256=%s" % (d0, d1, len(files), man_sha),
            "source_sha256": hashlib.sha256(",".join(files).encode()).hexdigest(), "clock_basis": "UTC (timestamp epoch del downloader; non verificato in modo indipendente)",
            "purpose": "RESEARCH_DISCOVERY_PARTITION", "quality_verdict": "PASS_WITH_NOTES (new_dataset_integrity_report_v1)", "instrument_spec": {"price_unit": "USD per troy ounce", "digits": 3},
            "authorization": {"record": "server/chart_authorization.json"}}
    m = chart_store.build_store(rows, out, meta, None, 1000)
    gaps = analyse_gaps(rows)
    tot_rows = sum(d["rows"] or 0 for d in per_day)
    report = {
        "schema": "NEXUS_HISTORICAL_STORE_BUILD_REPORT_V1", "dataset_id": DATASET_ID, "window": {"from": d0, "to": d1}, "built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "elapsed_s": round(time.time() - t_start, 1), "data_manifest_sha256": man_sha, "days": len(per_day), "files": len(files), "files_missing": [d["date"] for d in per_day if d.get("file_missing")],
        "ticks_total": tot_rows, "count_mismatches": mism, "non_monotonic_total": sum(d.get("non_monotonic", 0) for d in per_day), "duplicate_ticks_total": sum(d.get("duplicates", 0) for d in per_day),
        "out_of_band_total": sum(d.get("out_of_band", 0) for d in per_day), "nonpositive_total": sum(d.get("nonpositive", 0) for d in per_day), "skipped_rows_total": sum(d.get("skipped", 0) for d in per_day),
        "zero_tick_weekdays": [d["date"] for d in per_day if d.get("rows") == 0 and d["weekday"] < 5], "price_min": min((d["min_bid"] for d in per_day if d.get("min_bid")), default=None),
        "price_max": max((d["max_bid"] for d in per_day if d.get("max_bid")), default=None), "n_m1": len(rows), "coverage": m["coverage"], "calendar": m["calendar"],
        "completeness_counts": m["completeness_counts"], "bars_per_timeframe": {tf: sum(s["n"] for s in segs) for tf, segs in m["segments"].items()}, "gaps": gaps,
        "store_bytes": sum(s["bytes"] for segs in m["segments"].values() for s in segs), "per_day": per_day,
        "limitations": ["UTC non verificato in modo indipendente (timestamp epoch del downloader)", "calendario di mercato candidato/non verificato: le barre che attraversano le pause sono PARTIAL, i buchi non spiegati GAP",
                        "barre costruite dal solo prezzo BID; nessun ask, nessun volume", "feed Dukascopy: NON equivalente al feed MT5 XM"]}
    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
    json.dump(report, open(report_path, "w", encoding="utf-8"), indent=1)
    if not quiet:
        print(json.dumps({k: report[k] for k in ("days", "files", "ticks_total", "n_m1", "elapsed_s", "store_bytes", "bars_per_timeframe")}, indent=1))
        print("mismatches:", len(mism), "non_monotonic:", report["non_monotonic_total"], "duplicates:", report["duplicate_ticks_total"], "zero-tick weekdays:", report["zero_tick_weekdays"])
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True); ap.add_argument("--data-manifest", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--from", dest="d0", required=True); ap.add_argument("--to", dest="d1", required=True); ap.add_argument("--report", required=True)
    a = ap.parse_args()
    try:
        build(a.root, a.data_manifest, a.out, a.d0, a.d1, a.report)
    except chart_guard.PartitionDenied as ex:
        raise SystemExit("PARTIZIONE NON AUTORIZZATA, costruzione interrotta senza aprire il file: " + str(ex))
