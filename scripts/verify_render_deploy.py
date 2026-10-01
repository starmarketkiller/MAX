#!/usr/bin/env python3
"""Post-deploy verifier producing a non-secret deploy ledger record."""
from __future__ import annotations
import argparse, json, os, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

def now(): return datetime.now(timezone.utc).isoformat()
def get_json(url, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=15) as response:
        return response.status, json.loads(response.read().decode())
def post_json(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode())

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--base-url", required=True)
    parser.add_argument("--sha", required=True); parser.add_argument("--deploy-id")
    parser.add_argument("--risk", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=int, default=900); args=parser.parse_args(argv)
    base=args.base_url.rstrip("/"); started=now(); checks={}; error=None; token=None
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
    if user and password:
        try: token=post_json(base+"/api/auth/login",{"username":user,"password":password}).get("token")
        except Exception as exc: error=type(exc).__name__
    if token:
        try:
            status, dispatcher=get_json(base+"/api/jarvis/dispatcher/status",{"Authorization":f"Bearer {token}"})
            checks["dispatcher"]={"http":status,"status":dispatcher.get("status"),"running":dispatcher.get("running")}
        except Exception as exc: error=type(exc).__name__
    else: checks["dispatcher"]={"status":"UNVERIFIED","reason":"VERIFY_CREDENTIALS_NOT_CONFIGURED"}
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
