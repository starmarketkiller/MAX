#!/usr/bin/env python3
"""Compare local/origin/production build identity without changing state."""
import json
import subprocess
import sys
import urllib.error
import urllib.request


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def check(base_url):
    local = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/version", timeout=15) as response:
            version = json.loads(response.read())
        production = version.get("git_sha") or "UNKNOWN"
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        version, production = None, "UNKNOWN"
    if production == "UNKNOWN": status = "PRODUCTION_UNKNOWN"
    elif production == origin: status = "PRODUCTION_ALIGNED"
    else:
        try: origin_contains = subprocess.run(["git", "merge-base", "--is-ancestor", production, origin]).returncode == 0
        except OSError: origin_contains = False
        status = "PRODUCTION_BEHIND" if origin_contains else "PRODUCTION_AHEAD"
    return {"local_head": local, "origin_main": origin, "production_sha": production,
            "status": status, "version": version}


if __name__ == "__main__":
    if len(sys.argv) != 2: raise SystemExit("usage: check_production_alignment.py https://service.example")
    print(json.dumps(check(sys.argv[1]), indent=2))

