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

_RETRYABLE_HTTP = (502, 503, 504)
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = (3, 6, 12)


def _login(base, user, password, session_factory):
    """One login attempt. Returns (session, headers, auth_mode, failure_or_None)."""
    session = session_factory()
    try:
        login_status, login = session.request_json(
            base+"/api/auth/login", method="POST",
            payload={"username":user,"password":password})
    except urllib.error.HTTPError as exc:
        reason = "LOGIN_REJECTED" if exc.code in (401, 403) else "LOGIN_HTTP_ERROR"
        return None, None, None, {"status":"UNVERIFIED","reason":reason,"http":exc.code}
    except Exception as exc:
        return None, None, None, {"status":"UNVERIFIED","reason":"LOGIN_FAILED",
                                  "error_class":type(exc).__name__}
    if login_status != 200:
        return None, None, None, {"status":"UNVERIFIED","reason":"LOGIN_REJECTED",
                                  "http":login_status}
    # Hardened production auth is cookie-only. A bearer token is accepted only
    # as a compatibility fallback for non-hardened/legacy deployments.
    token = login.get("token")
    cookie_count = session.cookie_count
    if cookie_count == 0 and not token:
        return None, None, None, {"status":"UNVERIFIED","reason":"LOGIN_SESSION_MISSING",
                                  "http":login_status}
    headers = {"Authorization":f"Bearer {token}"} if token else None
    auth_mode = "COOKIE" if cookie_count else "BEARER"
    return session, headers, auth_mode, None


def verify_dispatcher(base, user, password, session_factory=HttpSession, *,
                      max_attempts=DEFAULT_MAX_ATTEMPTS, backoff_seconds=DEFAULT_BACKOFF_SECONDS,
                      sleep=time.sleep):
    """Bounded retry with backoff absorbs a few seconds of Render restart
    noise - it never lowers the bar for success, only gives a transient
    condition room to resolve itself within the SAME fixed budget:
      - network error / 502 / 503 / 504 on the dispatcher call: retried
      - running=False (dispatcher not up yet): retried
      - 401/403 on the dispatcher call: ONE fresh re-login is attempted
        (session/cookie may have rotated with the process), then retried
        once; if still 401/403 after that fresh login, FAIL immediately -
        never silently retried as if it were a transient infra blip
      - login itself rejected/missing session, or running=False that is
        STILL false once the budget is exhausted: unchanged FAIL, exactly
        as strict as before this change
    """
    if not user or not password:
        return ({"status":"UNVERIFIED","reason":"VERIFY_CREDENTIALS_MISSING",
                "attempts":0,"reauth_used":False}, "VERIFY_CREDENTIALS_MISSING")

    session, headers, auth_mode, failure = _login(base, user, password, session_factory)
    if failure:
        failure["attempts"] = 0
        failure["reauth_used"] = False
        return failure, failure["reason"]

    reauth_used = False
    for attempt in range(1, max_attempts + 1):
        try:
            status, dispatcher = session.request_json(
                base+"/api/jarvis/dispatcher/status", headers=headers)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403) and not reauth_used:
                # The session may have rotated with the restarting process -
                # one fresh login, then retry THIS same attempt slot.
                reauth_used = True
                session, headers, auth_mode, failure = _login(base, user, password, session_factory)
                if failure:
                    failure["attempts"] = attempt
                    failure["reauth_used"] = True
                    return failure, failure["reason"]
                continue
            if exc.code not in _RETRYABLE_HTTP or attempt == max_attempts:
                check = {"status":"UNVERIFIED","reason":"DISPATCHER_ENDPOINT_REJECTED",
                        "http":exc.code,"auth_mode":auth_mode,"attempts":attempt,
                        "reauth_used":reauth_used}
                return check, "DISPATCHER_ENDPOINT_REJECTED"
            sleep(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == max_attempts:
                check = {"status":"UNVERIFIED","reason":"DISPATCHER_ENDPOINT_FAILED",
                        "error_class":type(exc).__name__,"auth_mode":auth_mode,
                        "attempts":attempt,"reauth_used":reauth_used}
                return check, "DISPATCHER_ENDPOINT_FAILED"
            sleep(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])
            continue

        running = dispatcher.get("running")
        check = {"http":status,"status":dispatcher.get("status"),"running":running,
                "auth_mode":auth_mode,"attempts":attempt,"reauth_used":reauth_used}
        if running is True:
            return check, None
        if attempt < max_attempts:
            sleep(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])
            continue
        return check, "DISPATCHER_NOT_RUNNING"

    # Defensive only - every branch above returns on its own terminal attempt.
    return ({"status":"UNVERIFIED","reason":"RETRY_EXHAUSTED","attempts":max_attempts,
            "reauth_used":reauth_used}, "RETRY_EXHAUSTED")


def check_ready(base, *, max_attempts=DEFAULT_MAX_ATTEMPTS,
               backoff_seconds=DEFAULT_BACKOFF_SECONDS, sleep=time.sleep):
    """Same bounded retry/backoff discipline as verify_dispatcher(), for the
    same reason: /api/version matching does not guarantee the rest of the
    process has finished settling yet."""
    for attempt in range(1, max_attempts + 1):
        try:
            status, ready = get_json(base+"/api/ready")
        except urllib.error.HTTPError as exc:
            if exc.code not in _RETRYABLE_HTTP or attempt == max_attempts:
                return {"http":exc.code,"attempts":attempt}, False
            sleep(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            if attempt == max_attempts:
                return {"error_class":type(exc).__name__,"attempts":attempt}, False
            sleep(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])
            continue
        check = {"http":status,"body":ready,"attempts":attempt}
        if status == 200 and bool(ready.get("ok")):
            return check, True
        if attempt < max_attempts:
            sleep(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])
            continue
        return check, False
    return {"attempts":max_attempts}, False

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
    version_ok=checks.get("version",{}).get("git_sha")==args.sha

    # A matched /api/version proves the new process answers HTTP requests,
    # not that it has fully settled (dispatcher thread started, etc.) - a
    # short, fixed grace period before the stricter checks below absorbs
    # that without weakening either check's own retry budget.
    stabilization_start = time.monotonic()
    time.sleep(5)
    checks["ready"], ready_ok = check_ready(base)
    user=os.environ.get("NEXUS_DEPLOY_VERIFY_USER"); password=os.environ.get("NEXUS_DEPLOY_VERIFY_PASSWORD")
    checks["dispatcher"], dispatcher_error = verify_dispatcher(base, user, password)
    checks["stabilization_seconds"] = round(time.monotonic() - stabilization_start, 1)
    if not ready_ok: error = "READINESS_FAILED"
    if dispatcher_error: error=dispatcher_error
    dispatcher_ok=checks.get("dispatcher",{}).get("running") is True
    success=version_ok and ready_ok and dispatcher_ok
    ledger={"schema_version":1,"commit":args.sha,"deploy_id":args.deploy_id,"risk":args.risk,
            "start":started,"end":now(),"checks":checks,"result":"VERIFIED" if success else "FAILED",
            "diagnostic":None if success else (error or "POST_DEPLOY_GATE_FAILED"),
            "recovery":"Keep previous healthy deploy; inspect Render logs and prepare explicit rollback." if not success else None}
    Path(args.output).write_text(json.dumps(ledger,indent=2),encoding="utf-8")
    print(json.dumps(ledger,indent=2)); return 0 if success else 1
if __name__=="__main__": raise SystemExit(main())
