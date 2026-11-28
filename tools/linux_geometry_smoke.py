"""Smoke test API delle geometrie e del Reverse Discovery Lab, pensato per il container Linux/Docker del candidato.

Non modifica l'infrastruttura approvata: e' uno script ADDITIVO da eseguire dopo `docker run` (stessa immagine, stesso volume /data).
  fase 1:  python tools/linux_geometry_smoke.py write  --base http://127.0.0.1:8080 --user U --password P --state /tmp/geo_state.json
  (riavvio del container: `docker restart` e, separatamente, ridistribuzione della stessa immagine sullo stesso volume)
  fase 2:  python tools/linux_geometry_smoke.py verify --base ... --state /tmp/geo_state.json
Esito: JSON con PASS/FAIL per controllo; exit code 1 se un controllo fallisce. Nessuna credenziale e' scritta su disco.
"""
import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.request

T0 = 1_760_000_000


class Client:
    def __init__(self, base, user, password):
        self.base = base.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = None
        self.origin = self.base
        r = self.call("POST", "/api/auth/login", {"email": user, "password": password})
        if r[0] != 200:
            raise SystemExit(f"login fallito: {r[0]}")
        for c in self.jar:
            if c.name == "nexus_csrf":
                self.csrf = c.value

    def call(self, method, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Origin", self.origin)
        if self.csrf and method not in ("GET", "HEAD"):
            req.add_header("X-Nexus-Csrf", self.csrf)
        try:
            with self.op.open(req, timeout=30) as resp:
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, None


def geom(name="g"):
    return {"type": "trendline", "symbol": "GOLD", "timeframe_origin": "H4", "dataset_id": "SMOKE", "source": "SMOKE", "clock_basis": "TERMINAL_CLOCK", "name": name,
            "anchors": [{"t": T0, "price": 3600.5}, {"t": T0 + 14400 * 6, "price": 3712.25}], "semantic": {"class": "DIAG_SELL"}}


def event(gid):
    return {"name": "smoke", "dataset_id": "SMOKE", "source": "SMOKE", "symbol": "GOLD", "clock_basis": "TERMINAL_CLOCK", "timeframe_observation": "H4", "outcome": "REVERSAL",
            "pivot": {"t": T0 + 14400 * 6, "price": 3712.25, "kind": "HIGH"}, "origin": {"t": T0, "price": 3600.5}, "destination": {"t": T0 + 14400 * 10, "price": 3650.0},
            "units": {"pip_size": 0.1, "point": None, "tick_size": None}, "geometries": [{"geometry_id": gid, "timing": "BEFORE_EVENT_OBSERVABLE"}],
            "hypotheses": [{"text": "ipotesi alternativa", "status": "OPEN"}]}


def run(args):
    c = Client(args.base, args.user, args.password)
    res = []

    def chk(name, ok, detail=""):
        res.append({"name": name, "ok": bool(ok), "detail": str(detail)[:200]})

    G, D = "/api/chart/geometry", "/api/chart/discovery"
    if args.mode == "write":
        s, sess = c.call("POST", G + "/sessions", {"name": "linux-smoke", "symbol": "GOLD"})
        chk("sessione creata", s == 200, s)
        sid = sess["session_id"]
        s, g = c.call("POST", f"{G}/sessions/{sid}/objects", geom())
        chk("geometria creata (due ancoraggi)", s == 200 and g["revision"] == 1 and g["epistemic_mode"] == "RETROSPECTIVE_DISCOVERY", s)
        s, e = c.call("POST", f"{D}/sessions/{sid}/events", event(g["geometry_id"]))
        chk("scheda evento creata con pip e geometria collegata", s == 200 and abs(e["derived"]["prior_leg"]["amplitude_pips"] - 1117.5) < 1e-6 and e["geometries"][0]["causal_knowledge"] == "NOT_ESTABLISHED", s)
        s, _ = c.call("POST", f"{D}/sessions/{sid}/events", dict(event(g["geometry_id"]), epistemic_mode="CAUSAL_REPLAY"))
        chk("campo epistemic_mode rifiutato", s == 422, s)
        s, _ = c.call("PUT", f"{D}/sessions/{sid}/research", {"name": "r", "dataset_id": "SMOKE", "symbol": "GOLD", "units": {"pip_size": 0.1}})
        chk("stato della ricerca salvato", s == 200, s)
        s, exp = c.call("GET", f"{G}/sessions/{sid}/export")
        chk("export con sha256 e scheda", s == 200 and len(exp["sha256"]) == 64 and len(exp["events"]) == 1, s)
        state = {"sid": sid, "gid": g["geometry_id"], "eid": e["event_id"], "geometry": {k: g[k] for k in ("anchors", "created_at", "available_at", "revision")}, "event_name": e["name"], "event_rev": e["revision"], "sha": exp["sha256"]}
        json.dump(state, open(args.state, "w"))
    else:
        st = json.load(open(args.state))
        sid = st["sid"]
        s, g = c.call("GET", f"{G}/sessions/{sid}/objects/{st['gid']}")
        chk("geometria persistita senza variazioni dopo il riavvio", s == 200 and all(g[k] == v for k, v in st["geometry"].items()), s)
        s, e = c.call("GET", f"{D}/sessions/{sid}/events/{st['eid']}")
        chk("scheda evento persistita dopo il riavvio", s == 200 and e["name"] == st["event_name"] and e["revision"] == st["event_rev"] and e["validation_status"] == "NOT_VALIDATED", s)
        s, exp = c.call("GET", f"{G}/sessions/{sid}/export")
        chk("export identico (stesso sha256) dopo il riavvio", s == 200 and exp["sha256"] == st["sha"], s)
        s, r = c.call("GET", f"{D}/sessions/{sid}/research")
        chk("stato della ricerca persistito", s == 200 and r["research"] and r["research"]["units"]["pip_size"] == 0.1, s)
        s, _ = c.call("GET", f"{G}/sessions/Snonexistent")
        chk("sessione inesistente = 404 uniforme", s == 404, s)
    print(json.dumps({"mode": args.mode, "checks": res, "pass": sum(r["ok"] for r in res), "total": len(res)}, indent=1))
    return 0 if all(r["ok"] for r in res) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["write", "verify"])
    ap.add_argument("--base", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--state", required=True)
    sys.exit(run(ap.parse_args()))
