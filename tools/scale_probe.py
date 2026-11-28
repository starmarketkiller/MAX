"""Sonda di scala del backend Chart: tempi di risposta, dimensione delle risposte, paginazione e concorrenza su uno store storico. Solo HTTP (nessun accesso diretto ai dati).

  python tools/scale_probe.py --base http://127.0.0.1:8860 --user U --password P --source DUKASCOPY_XAUUSD_PHASE7 --symbol XAUUSD [--pid 1234 | --rss-file /proc/1/status] --report out.json

Misura: H4 completo in una richiesta (limite 5000), paginazione M1 all'indietro (pagine da 1000), concorrenza (8 client), ripetizione. Se e' noto il PID (o un file stile /proc/<pid>/status)
registra l'RSS del processo backend prima/dopo/picco osservato (campionato): e' la RAM del BACKEND, distinta da quella del browser. Nessuna credenziale viene scritta nel rapporto.
"""
import argparse, concurrent.futures as cf, http.cookiejar, json, statistics, subprocess, sys, threading, time, urllib.error, urllib.request


class Client:
    def __init__(self, base, user, password):
        self.base = base.rstrip("/")
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.get("/api/ready")
        data = json.dumps({"email": user, "password": password}).encode()
        req = urllib.request.Request(self.base + "/api/auth/login", data=data, method="POST", headers={"Content-Type": "application/json", "Origin": self.base})
        with self.op.open(req, timeout=30) as r:
            if r.status != 200:
                raise SystemExit("login fallito")

    def get(self, path):
        t0 = time.perf_counter()
        try:
            with self.op.open(self.base + path, timeout=120) as r:
                raw = r.read()
                return r.status, len(raw), (time.perf_counter() - t0) * 1000, json.loads(raw) if raw[:1] in b"{[" else None
        except urllib.error.HTTPError as e:
            return e.code, 0, (time.perf_counter() - t0) * 1000, None


def pct(xs, p):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * p))], 1) if xs else None


def rss_mb(pid=None, rss_file=None):
    try:
        if rss_file:
            for ln in open(rss_file):
                if ln.startswith("VmRSS"):
                    return round(int(ln.split()[1]) / 1024, 1)
        if pid:
            if sys.platform.startswith("win"):
                out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-Process -Id %d).WorkingSet64" % pid], capture_output=True, text=True).stdout.strip()
                return round(int(out) / 1048576, 1)
            for ln in open("/proc/%d/status" % pid):
                if ln.startswith("VmRSS"):
                    return round(int(ln.split()[1]) / 1024, 1)
    except Exception:
        return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--user", required=True); ap.add_argument("--password", required=True)
    ap.add_argument("--source", required=True); ap.add_argument("--symbol", required=True)
    ap.add_argument("--pid", type=int); ap.add_argument("--rss-file"); ap.add_argument("--pages", type=int, default=25); ap.add_argument("--report", required=True)
    a = ap.parse_args()
    c = Client(a.base, a.user, a.password)
    peak = {"v": rss_mb(a.pid, a.rss_file)}
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            v = rss_mb(a.pid, a.rss_file)
            if v and (peak["v"] is None or v > peak["v"]):
                peak["v"] = v
            time.sleep(0.25)
    th = threading.Thread(target=sampler, daemon=True); th.start()
    rep = {"base_rss_mb": rss_mb(a.pid, a.rss_file), "steps": {}}
    q = lambda tf, limit, before=None: "/api/chart/ohlc?source=%s&symbol=%s&tf=%s&limit=%d%s" % (a.source, a.symbol, tf, limit, "&before=%d" % before if before else "")
    for tf in ("H4", "D1"):
        s, n, ms, d = c.get(q(tf, 5000))
        rep["steps"]["full_" + tf] = {"status": s, "bytes": n, "ms": round(ms, 1), "bars": len(d["bars"]) if d else None, "has_more": d.get("has_more") if d else None}
    rows, before = [], None
    s, n, ms, d = c.get(q("M1", 1500)); rows.append((n, ms, len(d["bars"]) if d else 0)); before = d.get("next_before") if d else None
    for _ in range(a.pages):
        if not before:
            break
        s, n, ms, d = c.get(q("M1", 1000, before))
        if s != 200:
            break
        rows.append((n, ms, len(d["bars"]))); before = d.get("next_before")
    rep["steps"]["m1_paging"] = {"pages": len(rows), "bars_total": sum(r[2] for r in rows), "ms_p50": pct([r[1] for r in rows], 0.5), "ms_p95": pct([r[1] for r in rows], 0.95), "ms_max": round(max(r[1] for r in rows), 1),
                                 "bytes_per_page_max": max(r[0] for r in rows), "bytes_total": sum(r[0] for r in rows)}
    # concorrenza: 8 client, ciascuno 12 pagine M5/M15 da punti diversi
    anchors = []
    s, n, ms, d = c.get(q("H4", 5000))
    if d and d["bars"]:
        bs = d["bars"]; anchors = [bs[int(len(bs) * f)]["time"] for f in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.9)]

    def worker(t):
        cl = Client(a.base, a.user, a.password)
        out = []
        for tf in ("M15", "M5", "M15", "M5", "H1", "M15", "M5", "H1", "M15", "M5", "M15", "H1"):
            s, n, ms, _ = cl.get(q(tf, 1000, t))
            out.append((s, n, ms))
        return out
    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        res = [x for r in ex.map(worker, anchors) for x in r]
    el = time.perf_counter() - t0
    rep["steps"]["concurrency_8x12"] = {"requests": len(res), "ok": sum(1 for r in res if r[0] == 200), "elapsed_s": round(el, 2), "req_per_s": round(len(res) / el, 1), "ms_p50": pct([r[2] for r in res], 0.5), "ms_p95": pct([r[2] for r in res], 0.95), "bytes_max": max(r[1] for r in res)}
    stop.set(); th.join(timeout=2)
    rep["rss_mb"] = {"before": rep["base_rss_mb"], "peak_observed": peak["v"], "after": rss_mb(a.pid, a.rss_file)}
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
