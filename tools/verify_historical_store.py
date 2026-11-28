"""Verifica INDIPENDENTE dello store storico (non riusa le funzioni di aggregazione dello store).

  python tools/verify_historical_store.py --store <store> --dataset DUKASCOPY_XAUUSD_PHASE7 [--raw-root <decoded> --samples 12 --seed 7] --report <verify_report.json>

Controlli: hash e dimensione di ogni segmento; ordine/allineamento/duplicati; coerenza OHLC; riconciliazione dei conteggi (n_m1, segmenti); ri-aggregazione COMPLETA da M1 per tutti i timeframe
(open/high/low/close/minuti presenti) confrontata barra per barra; bilancio dei minuti (presenti + mancanti + bordo = durata del bucket); copertura; nessun dato fuori dalla finestra dichiarata;
(opzionale) ri-derivazione di giorni campione direttamente dai tick, interrogando la guardia PRIMA di aprire ogni file.
"""
import argparse, datetime as dt, hashlib, json, os, random, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "server"))
REC = struct.Struct("<qiiiiHHBB")           # formato dichiarato nel manifest: lo verifico contro manifest["record"]
SEC = {"M1": 60, "M5": 300, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400, "D1": 86400}
ALL = ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1")


def bucket(t, tf):
    """Implementazione indipendente degli intervalli di barra (UTC)."""
    if tf in SEC:
        s = t - t % SEC[tf]
        return s, s + SEC[tf]
    d = dt.datetime.fromtimestamp(t, dt.timezone.utc)
    if tf == "W1":
        s = (d - dt.timedelta(days=d.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return int(s.timestamp()), int((s + dt.timedelta(days=7)).timestamp())
    s = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    e = dt.datetime(s.year + (s.month == 12), s.month % 12 + 1, 1, tzinfo=dt.timezone.utc)
    return int(s.timestamp()), int(e.timestamp())


def load(store, man, tf, fails):
    recs = []
    for seg in man["segments"].get(tf, []):
        p = os.path.join(store, man["dataset_id"], tf, seg["month"] + ".bin")
        blob = open(p, "rb").read()
        if len(blob) != seg["bytes"] or hashlib.sha256(blob).hexdigest() != seg["sha256"]:
            fails.append("%s/%s: hash o dimensione non coincidono" % (tf, seg["month"]))
        if len(blob) % REC.size or len(blob) // REC.size != seg["n"]:
            fails.append("%s/%s: numero di record non coincide" % (tf, seg["month"]))
        recs += [REC.unpack_from(blob, i * REC.size) for i in range(len(blob) // REC.size)]
    return recs


def verify(store, dataset_id, window=None, raw_root=None, samples=0, seed=7, guard=None):
    man = json.load(open(os.path.join(store, dataset_id, "manifest.json"), encoding="utf-8"))
    checks = []
    def chk(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:300]})
    chk("schema e formato del record", man.get("schema") == "NEXUS_CHART_STORE_V1" and man.get("record") == "<qiiiiHHBB", man.get("record"))
    series, fails = {}, []
    for tf in ALL:
        series[tf] = load(store, man, tf, fails)
    chk("hash/dimensioni/numero di record di tutti i segmenti", not fails, fails[:3])
    chk("timeframe presenti = dichiarati", [tf for tf in ALL if series[tf]] == man["tf_available"], man["tf_available"])
    m1 = series["M1"]
    chk("riconciliazione conteggio M1 (manifest = record)", man["n_m1"] == len(m1), (man["n_m1"], len(m1)))
    # ordine, allineamento, duplicati, coerenza OHLC
    bad_order = bad_align = bad_ohlc = bad_bal = 0
    scale = man["price_scale"]
    for tf, recs in series.items():
        prev = None
        for (t, o, h, l, c, pres, miss, comp, why) in recs:
            if prev is not None and t <= prev:
                bad_order += 1
            prev = t
            if bucket(t, tf)[0] != t:
                bad_align += 1
            if not (0 < l <= min(o, c) <= max(o, c) <= h):
                bad_ohlc += 1
            if comp not in (0, 1, 2) or pres < 1:
                bad_bal += 1
    chk("ordine strettamente crescente e nessun duplicato (tutti i timeframe)", bad_order == 0, bad_order)
    chk("ogni barra e' allineata all'inizio del proprio bucket UTC", bad_align == 0, bad_align)
    chk("OHLC coerente (0 < low <= min(o,c) <= max(o,c) <= high) in tutte le barre", bad_ohlc == 0, bad_ohlc)
    chk("codici di completezza validi e minuti presenti >= 1", bad_bal == 0, bad_bal)
    # ri-aggregazione completa da M1
    mism, bal = {}, 0
    cov0, cov1 = man["coverage"]["first_t"], man["coverage"]["last_end_t"]
    chk("copertura = primo M1 e ultimo M1 + 60 s", m1 and m1[0][0] == cov0 and m1[-1][0] + 60 == cov1, (m1[0][0] if m1 else None, m1[-1][0] if m1 else None, cov0, cov1))
    for tf in ALL[1:]:
        g = {}
        for (t, o, h, l, c, *_r) in m1:
            s, e = bucket(t, tf)
            x = g.get(s)
            if x is None:
                g[s] = [o, h, l, c, 1, e]
            else:
                x[1] = max(x[1], h); x[2] = min(x[2], l); x[3] = c; x[4] += 1
        exp = [(s, v[0], v[1], v[2], v[3], v[4]) for s, v in sorted(g.items())]
        got = [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in series[tf]]
        if exp != got:
            mism[tf] = sum(1 for a, b in zip(exp, got) if a != b) + abs(len(exp) - len(got))
        for r in series[tf]:                                            # bilancio dei minuti del bucket
            s, e = bucket(r[0], tf)
            total = (e - s) // 60
            lo, hi = max(s, cov0), min(e, cov1)
            edge = total - (hi - lo) // 60 if hi > lo else total
            if r[5] + r[6] + edge != total:
                bal += 1
    chk("ri-aggregazione da M1 identica barra per barra (M5, M15, M30, H1, H4, D1, W1, MN1: open/high/low/close/minuti presenti)", not mism, mism)
    chk("bilancio dei minuti: presenti + mancanti + bordo = durata del bucket", bal == 0, bal)
    bars_per_tf = {tf: len(series[tf]) for tf in ALL}
    if window:
        w0 = int(dt.datetime.fromisoformat(window[0]).replace(tzinfo=dt.timezone.utc).timestamp()); w1 = int(dt.datetime.fromisoformat(window[1]).replace(tzinfo=dt.timezone.utc).timestamp()) + 86400
        chk("nessun minuto fuori dalla finestra dichiarata", m1 and m1[0][0] >= w0 and m1[-1][0] + 60 <= w1, (window,))
    # ri-derivazione di giorni campione dai tick
    if raw_root and samples:
        import chart_guard
        import build_historical_store as bhs
        guard = guard or chart_guard.Guard()
        d0 = dt.datetime.fromtimestamp(cov0, dt.timezone.utc).date(); d1 = dt.datetime.fromtimestamp(cov1 - 1, dt.timezone.utc).date()
        days = [d0 + dt.timedelta(n) for n in range((d1 - d0).days + 1)]
        rnd = random.Random(seed)
        pick = sorted({days[0], days[-1], *rnd.sample(days, min(samples, len(days)))})
        by_t = {r[0]: r for r in m1}
        ok_days, bad = 0, []
        for d in pick:
            t0 = int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())
            guard.check(dataset_id, t0, t0 + 86400)                    # PRIMA di aprire il file
            p = os.path.join(raw_root, str(d.year), d.isoformat() + ".csv.gz")
            if not os.path.isfile(p):
                continue
            mb, _st = bhs.read_day(p, t0)
            exp_t = {k for k in mb}
            got_t = {t for t in by_t if t0 <= t < t0 + 86400}
            same = exp_t == got_t and all(tuple(int(round(x * scale)) for x in mb[k]) == tuple(by_t[k][1:5]) for k in exp_t)
            if same:
                ok_days += 1
            else:
                bad.append(d.isoformat())
        chk("ri-derivazione dai tick di %d giorni campione (incl. primo e ultimo): M1 identici (minuti e OHLC)" % len(pick), not bad and ok_days > 0, {"giorni_ok": ok_days, "diversi": bad})
    ok = all(c["ok"] for c in checks)
    return {"schema": "NEXUS_HISTORICAL_STORE_VERIFY_REPORT_V1", "dataset_id": dataset_id, "verdict": "PASS" if ok else "FAIL", "checks": checks, "bars_per_timeframe": bars_per_tf,
            "completeness_counts": man["completeness_counts"], "store_bytes": sum(s["bytes"] for segs in man["segments"].values() for s in segs), "coverage": man["coverage"], "calendar_status": man["calendar"]["status"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True); ap.add_argument("--dataset", required=True); ap.add_argument("--raw-root"); ap.add_argument("--samples", type=int, default=0)
    ap.add_argument("--seed", type=int, default=7); ap.add_argument("--window", nargs=2, metavar=("FROM", "TO")); ap.add_argument("--report", required=True)
    a = ap.parse_args()
    rep = verify(a.store, a.dataset, tuple(a.window) if a.window else None, a.raw_root, a.samples, a.seed)
    os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
    json.dump(rep, open(a.report, "w", encoding="utf-8"), indent=1)
    for c in rep["checks"]:
        print("PASS" if c["ok"] else "FAIL", c["name"], c["detail"] if not c["ok"] else "")
    print("VERDICT", rep["verdict"])
    sys.exit(0 if rep["verdict"] == "PASS" else 1)
