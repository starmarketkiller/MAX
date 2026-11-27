"""Verifiche HTTP del runtime Chart (usate da docker_runtime_verify.sh, ma eseguibili contro qualunque istanza di STAGING/locale con credenziali di prova).

NON usare contro la produzione. Le credenziali arrivano da variabili d'ambiente (CO_TEST_USER / CO_TEST_PASS), mai da file.
Uso: python tools/docker_runtime_http.py <base_url> <expected.json> [--phase NAME] [--out FILE]
Stampa un JSON {checks:[{name,status,detail}], summary}. Exit 0 solo se tutti PASS.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.request

DS = "XM-GOLD-2026-11-16-20"


def call(base, path, tok=None, body=None, timeout=60):
    h = {"Content-Type": "application/json"}
    if tok:
        h["Authorization"] = "Bearer " + tok
    r = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=h, method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:                                                  # noqa: BLE001
            return e.code, {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("expected")
    ap.add_argument("--phase", default="run")
    ap.add_argument("--out", default="")
    ap.add_argument("--expect-denied", action="store_true", help="atteso: autorita' revocata/fail-closed (403 su ohlc)")
    a = ap.parse_args()
    exp = json.load(open(a.expected))["expected_bars"]
    checks = []

    def chk(name, ok, detail=""):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:300]})

    s, j = call(a.base, "/api/health")
    chk("health_200", s == 200, j.get("version"))
    s, _ = call(a.base, "/api/ready")
    chk("ready_200", s == 200, s)
    user, pw = os.environ.get("CO_TEST_USER", ""), os.environ.get("CO_TEST_PASS", "")
    s, j = call(a.base, "/api/auth/login", body={"email": user, "password": pw})
    tok = j.get("token") if s == 200 else None
    chk("login", bool(tok), s)
    chk("anonymous_ohlc_401", call(a.base, "/api/chart/ohlc?symbol=GOLD&tf=M15")[0] == 401)
    chk("anonymous_sources_401", call(a.base, "/api/chart/sources")[0] == 401)
    chk("demo_disabled_403", call(a.base, "/api/chart/ohlc?source=SYNTHETIC_DEMO&symbol=GOLD&tf=M15", tok)[0] == 403)
    url = "/api/chart/ohlc?source=%s&symbol=GOLD&tf=%s&limit=%d"
    if a.expect_denied:
        s, j = call(a.base, url % (DS, "M15", 5000), tok)
        chk("ohlc_denied_403_without_bars", s == 403 and not j.get("bars"), "%s %s" % (s, j.get("detail")))
        s, j = call(a.base, "/api/chart/sources", tok)
        chk("sources_not_authorized", s == 200 and all(not x.get("authorized") for x in j.get("sources", [])), s)
    else:
        s, j = call(a.base, "/api/chart/sources", tok)
        src = [x for x in j.get("sources", []) if x.get("dataset_id") == DS]
        chk("sources_dataset_authorized", s == 200 and len(j.get("sources", [])) == 1 and bool(src) and src[0].get("authorized") is True, s)
        # DOC-SMOKE-01: limite predefinito = 300 barre; con limit=5000 il totale atteso
        s, j = call(a.base, "/api/chart/ohlc?source=%s&symbol=GOLD&tf=M15" % DS, tok)
        want_default = min(300, exp["M15"])
        chk("ohlc_default_limit_%d_bars" % want_default, s == 200 and len(j.get("bars", [])) == want_default and j.get("has_more") == (exp["M15"] > 300), "%s n=%s" % (s, len(j.get("bars", []))))
        s, j = call(a.base, url % (DS, "M15", 5000), tok)
        chk("ohlc_m15_limit5000_%d_bars" % exp["M15"], s == 200 and len(j.get("bars", [])) == exp["M15"] and j.get("has_more") is False and j.get("provenance") == "REAL_HISTORICAL", "%s n=%s" % (s, len(j.get("bars", []))))
        for tf, n in exp.items():
            got, before, ok, last = 0, None, True, None
            while True:
                s, j = call(a.base, url % (DS, tf, 1000) + ("&before=%d" % before if before else ""), tok)
                if s != 200:
                    ok = False
                    break
                ts = [b["time"] for b in j["bars"]]
                if ts != sorted(ts) or (last is not None and ts and ts[-1] >= last):
                    ok = False
                    break
                got += len(ts)
                if ts:
                    last = ts[0]
                if not j["has_more"]:
                    break
                before = j["next_before"]
            chk("paginate_%s_total_%d" % (tf, n), ok and got == n, "got=%s" % got)

        def one(i):
            tf = ("M1", "M5", "M15", "H1")[i % 4]
            s, j = call(a.base, url % (DS, tf, 5000), tok)
            return s, len(j.get("bars", []))
        t = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            res = list(pool.map(one, range(120)))
        chk("concurrent_120x8_all_200", all(s == 200 and n > 0 for s, n in res), "%.1fs" % (time.time() - t))
    out = {"phase": a.phase, "checks": checks, "summary": {"pass": sum(c["status"] == "PASS" for c in checks), "fail": sum(c["status"] == "FAIL" for c in checks)}}
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))
    return 0 if out["summary"]["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
