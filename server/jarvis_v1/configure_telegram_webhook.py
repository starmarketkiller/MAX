#!/usr/bin/env python3
"""Set or verify the approved Telegram webhook without exposing secrets."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request


def _config():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    secret = os.environ.get("JARVIS_TELEGRAM_WEBHOOK_SECRET", "")
    base_url = os.environ.get("NEXUS_PUBLIC_URL", "").rstrip("/")
    if not token or not secret or not base_url.startswith("https://"):
        raise SystemExit(
            "TELEGRAM_BOT_TOKEN, JARVIS_TELEGRAM_WEBHOOK_SECRET and HTTPS NEXUS_PUBLIC_URL are required")
    return token, secret, f"{base_url}/api/jarvis/telegram/webhook"


def _telegram(token, method, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}", data=data,
        headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - fixed Telegram host
            return json.loads(response.read())
    except Exception as exc:
        raise SystemExit(f"Telegram webhook operation failed: {type(exc).__name__}") from None


def set_webhook(token, secret, webhook_url):
    return _telegram(token, "setWebhook", {
        "url": webhook_url, "secret_token": secret,
        "allowed_updates": ["message", "callback_query"],
    })


def verify_webhook(token, webhook_url):
    result = _telegram(token, "getWebhookInfo")
    info = result.get("result") or {}
    matches = bool(result.get("ok") and info.get("url") == webhook_url)
    return {"ok": matches, "url_matches": matches, "secret_locally_configured": True,
            "pending_update_count": info.get("pending_update_count"),
            "last_error_date": info.get("last_error_date"),
            "last_error_message": info.get("last_error_message")}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("set", "verify"), nargs="?", default="set")
    args = parser.parse_args(argv)
    token, secret, webhook_url = _config()
    if args.action == "set":
        result = set_webhook(token, secret, webhook_url)
        output = {"ok": bool(result.get("ok")), "description": result.get("description"),
                  "webhook_url": webhook_url}
    else:
        output = verify_webhook(token, webhook_url)
        output["webhook_url"] = webhook_url
    print(json.dumps(output))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
