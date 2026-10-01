#!/usr/bin/env python3
"""Post-deploy verifier producing a non-secret deploy ledger record."""
from __future__ import annotations
import argparse, http.cookiejar, json, os, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

def now(): return datetime.now(timezone.utc).isoformat()
def get_json(url, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=15) as response:
        return response.status, json.loads(response.read().decode())

class HttpSession:
    """Small urllib session that preserves hardened httpOnly auth cookies."""
    def __init__(self):
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    @property
    def cookie_count(self):
        return len(self.cookies)

    def request_json(self, url, *, method="GET", payload=None, headers=None):
        request_headers = dict(headers or {})
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
        with self.opener.open(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode() or "{}")

def verify_dispatcher(base, user, password, session_factory=HttpSession):
    if not user or not password:
        return ({"status":"UNVERIFIED","reason":"VERIFY_CREDENTIALS_MISSING"},
                "VERIFY_CREDENTIALS_MISSING")

    session = session_factory()
    try:
        login_status, login = session.request_json(
            base+"/api/auth/login", method="POST",
            payload={"username":user,"password":password})
    except urllib.error.HTTPError as exc:
        reason = "LOGIN_REJECTED" if exc.code in (401, 403) else "LOGIN_HTTP_ERROR"
        return ({"status":"UNVERIFIED","reason":reason,"http":exc.code}, reason)
    except Exception as exc:
        reason = "LOGIN_FAILED"
        return ({"status":"UNVERIFIED","reason":reason,
                 "error_class":type(exc).__name__}, reason)

    if login_status != 200:
        return ({"status":"UNVERIFIED","reason":"LOGIN_REJECTED","http":login_status},
                "LOGIN_REJECTED")

    # Hardened production auth is cookie-only. A bearer token is accepted only
    # as a compatibility fallback for non-hardened/legacy deployments.
    token = login.get("token")
    cookie_count = session.cookie_count
    if cookie_count == 0 and not token:
        return ({"status":"UNVERIFIED","reason":"LOGIN_SESSION_MISSING","http":login_status},
                "LOGIN_SESSION_MISSING")
    headers = {"Authorization":f"Bearer {token}"} if token else None
    auth_mode = "COOKIE" if cookie_count else "BEARER"
    try:
        status, dispatcher = session.request_json(
            base+"/api/jarvis/dispatcher/status", headers=headers)
    except urllib.error.HTTPError as exc:
        return ({"status":"UNVERIFIED","reason":"DISPATCHER_ENDPOINT_REJECTED",
                 "http":exc.code,"auth_mode":auth_mode}, "DISPATCHER_ENDPOINT_REJECTED")
    except Exception as exc:
        return ({"status":"UNVERIFIED","reason":"DISPATCHER_ENDPOINT_FAILED",
                 "error_class":type(exc).__name__,"auth_mode":auth_mode},
                "DISPATCHER_ENDPOINT_FAILED")
    return ({"http":status,"status":dispatcher.get("status"),
             "running":dispatcher.get("running"),"auth_mode":auth_mode}, None)

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--base-url", required=True)
    parser.add_argument("--sha", required=True); parser.add_argument("--deploy-id")
    parser.add_argument("--risk", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=int, default=900); args=parser.parse_args(argv)
    base=args.base_url.rstrip("/"); started=now(); checks={}; error=None
    deadline=time.time()+max(30,args.timeout)
    while time.time()<deadline:
        try:
            status, version=get_json(base+"/api/version")
            checks["version"]={"http":status,"git_sha":version.get("git_sha")}
            if status==200 and version.get("git_sha")==args.sha: break
        except Exception as exc: error=type(exc).__name__
        time.sleep(10)
    try:
        status, ready=get_json(base+"/api/ready"); checks["ready"]={"http":status,"body":ready}
    except urllib.error.HTTPError as exc:
        checks["ready"]={"http":exc.code}; error="READINESS_FAILED"
    user=os.environ.get("NEXUS_DEPLOY_VERIFY_USER"); password=os.environ.get("NEXUS_DEPLOY_VERIFY_PASSWORD")
    checks["dispatcher"], dispatcher_error = verify_dispatcher(base, user, password)
    if dispatcher_error: error=dispatcher_error
    version_ok=checks.get("version",{}).get("git_sha")==args.sha
    ready_ok=checks.get("ready",{}).get("http")==200
    dispatcher_ok=checks.get("dispatcher",{}).get("running") is True
    success=version_ok and ready_ok and dispatcher_ok
    ledger={"schema_version":1,"commit":args.sha,"deploy_id":args.deploy_id,"risk":args.risk,
            "start":started,"end":now(),"checks":checks,"result":"VERIFIED" if success else "FAILED",
            "diagnostic":None if success else (error or "POST_DEPLOY_GATE_FAILED"),
            "recovery":"Keep previous healthy deploy; inspect Render logs and prepare explicit rollback." if not success else None}
    Path(args.output).write_text(json.dumps(ledger,indent=2),encoding="utf-8")
    print(json.dumps(ledger,indent=2)); return 0 if success else 1
if __name__=="__main__": raise SystemExit(main())
