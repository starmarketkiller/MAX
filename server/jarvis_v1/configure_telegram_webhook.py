#!/usr/bin/env python3
"""Configure Telegram webhook after an explicitly approved deploy.

Reads secrets from environment and never prints them. This script is not run
by application startup, so repository code cannot silently change the bot.
"""
import json
import os
import sys
import urllib.request

token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
secret = os.environ.get("JARVIS_TELEGRAM_WEBHOOK_SECRET", "")
base_url = os.environ.get("NEXUS_PUBLIC_URL", "").rstrip("/")
if not token or not secret or not base_url.startswith("https://"):
    raise SystemExit("TELEGRAM_BOT_TOKEN, JARVIS_TELEGRAM_WEBHOOK_SECRET and HTTPS NEXUS_PUBLIC_URL are required")
payload = json.dumps({"url": f"{base_url}/api/jarvis/telegram/webhook",
                      "secret_token": secret, "allowed_updates": ["message", "callback_query"]}).encode()
request = urllib.request.Request(f"https://api.telegram.org/bot{token}/setWebhook", data=payload,
                                 headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310 - fixed Telegram host
        result = json.loads(response.read())
except Exception as exc:
    raise SystemExit(f"Webhook configuration failed: {type(exc).__name__}")
print(json.dumps({"ok": bool(result.get("ok")), "description": result.get("description")}))
raise SystemExit(0 if result.get("ok") else 1)

