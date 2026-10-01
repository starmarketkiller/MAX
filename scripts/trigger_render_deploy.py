#!/usr/bin/env python3
"""Trigger one exact Render commit without ever printing the secret hook URL."""
import json, os, urllib.parse, urllib.request

def build_url(hook, sha):
    parts = urllib.parse.urlsplit(hook)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query.append(("ref", sha))
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path,
                                   urllib.parse.urlencode(query), parts.fragment))

def main(opener=urllib.request.urlopen):
    hook = os.environ.get("RENDER_DEPLOY_HOOK_URL", "")
    sha = os.environ.get("DEPLOY_COMMIT_SHA", "")
    if not hook or not sha:
        raise SystemExit("RENDER_DEPLOY_HOOK_URL and DEPLOY_COMMIT_SHA are required")
    try:
        with opener(urllib.request.Request(build_url(hook, sha), method="POST"), timeout=30) as response:
            body = json.loads(response.read().decode() or "{}")
            if response.status not in (200, 202): raise RuntimeError("deploy trigger rejected")
    except Exception as exc:
        raise SystemExit(f"Render deploy trigger failed: {type(exc).__name__}") from None
    print(json.dumps({"accepted": True, "deploy_id": body.get("id"), "commit": sha}))

if __name__ == "__main__": main()
