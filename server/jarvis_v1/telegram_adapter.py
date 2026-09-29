"""Telegram adapter for Jarvis V1. Secrets are read only from environment."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .service import JarvisService, classify


class TelegramAdapter:
    def __init__(self, service: JarvisService, state_path=None, token=None, allowed_users=None,
                 gateway=None):
        self.service = service
        self.gateway = gateway
        self.token = token if token is not None else os.environ.get("TELEGRAM_BOT_TOKEN", "")
        raw_users = allowed_users if allowed_users is not None else os.environ.get("JARVIS_TELEGRAM_ALLOWED_USER_IDS", "")
        self.allowed_users = {str(x).strip() for x in (raw_users.split(",") if isinstance(raw_users, str) else raw_users) if str(x).strip()}
        self.state_path = Path(state_path or os.environ.get("JARVIS_TELEGRAM_STATE_PATH", Path(__file__).with_name("runtime_updates.json")))
        self._rate: dict[str, list[float]] = {}

    @property
    def configured(self):
        return bool(self.token and self.allowed_users)

    def _seen(self):
        try: return set(json.loads(self.state_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, TypeError): return set()

    def _mark_seen(self, update_id):
        seen = self._seen(); seen.add(str(update_id)); self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(sorted(seen)[-2000:]), encoding="utf-8")

    def _allowed_rate(self, user_id):
        now = time.time(); bucket = [x for x in self._rate.get(user_id, []) if now - x < 60]
        if len(bucket) >= 20: return False
        bucket.append(now); self._rate[user_id] = bucket; return True

    def parse_update(self, update):
        callback = update.get("callback_query") or {}
        msg = callback.get("message") or update.get("message") or {}
        user = callback.get("from") or msg.get("from") or {}
        user_id = str(user.get("id", "")); chat_id = str((msg.get("chat") or {}).get("id", ""))
        text = callback.get("data") or msg.get("text")
        if not user_id or not chat_id or not isinstance(text, str): raise ValueError("malformed Telegram update")
        metadata = {"telegram_update_id": update.get("update_id"), "telegram_chat_id": chat_id}
        if callback and ":" in text:
            action, task_id = text.split(":", 1); metadata.update({"approval_action": action, "task_id": task_id})
        return {
            "message_id": f"telegram:{update.get('update_id')}", "user_id": user_id,
            "channel": "TELEGRAM", "conversation_id": f"telegram:{chat_id}",
            "timestamp": datetime.now(timezone.utc).isoformat(), "input_type": "TEXT", "text": text,
            "attachments": [], "reply_to": None, "request_class": classify(text, metadata),
            "priority": "NORMAL", "metadata": metadata,
        }

    def handle_update(self, update):
        update_id = update.get("update_id")
        if update_id is None: raise ValueError("update_id required")
        if str(update_id) in self._seen(): return {"status": "DUPLICATE", "update_id": update_id}
        message = self.parse_update(update); user_id = message["user_id"]
        if user_id not in self.allowed_users: raise PermissionError("unauthorized Telegram user")
        if not self._allowed_rate(user_id): raise RuntimeError("rate limit exceeded")
        response = self.gateway.handle(message) if self.gateway is not None else self.service.handle(message)
        self._mark_seen(update_id)
        return response

    def send(self, chat_id, response):
        if not self.configured: return {"sent": False, "reason": "UNAVAILABLE"}
        body = json.dumps({"chat_id": str(chat_id), "text": response["summary"],
                           "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{self.token}/sendMessage", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as result:  # noqa: S310 - fixed Telegram host
                ok = result.status == 200
        except Exception:  # no secret/error body leakage
            return {"sent": False, "reason": "PROVIDER_UNAVAILABLE"}
        if ok:
            self.service.ledger.append("NOTIFICATION_SENT", response.get("task_id"),
                                       {"channel": "TELEGRAM", "priority": response.get("priority")},
                                       actor="telegram_adapter")
        return {"sent": ok, "reason": None if ok else "PROVIDER_UNAVAILABLE"}
