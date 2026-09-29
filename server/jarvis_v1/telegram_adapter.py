"""Telegram adapter for Jarvis V1. Secrets are read only from environment."""
from __future__ import annotations

import json
import hashlib
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

    def configuration_status(self, webhook_secret_configured=False):
        present = sum((bool(self.token), bool(self.allowed_users), bool(webhook_secret_configured)))
        state = "READY" if present == 3 else ("PARTIAL" if present else "NOT_CONFIGURED")
        return {"configuration_state": state, "configured": self.configured,
                "webhook_ready": state == "READY",
                "allowed_user_count": len(self.allowed_users), "token_exposed": False}

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
            action, task_id = text.split(":", 1)
            metadata["task_id"] = task_id
            if action.upper() in ("APPROVE", "REJECT"):
                metadata["approval_action"] = action
            elif action.upper() == "DETAILS":
                text = f"Mostrami i dettagli tecnici della task {task_id}"
                metadata["technical_details"] = True
            elif action.upper() == "CONFIRM_CANCEL":
                text = f"Conferma annullamento task {task_id}"
                metadata["confirm_cancel"] = True
        return {
            "message_id": f"telegram:{update.get('update_id')}", "user_id": user_id,
            "channel": "TELEGRAM", "conversation_id": f"telegram:{chat_id}",
            "timestamp": datetime.now(timezone.utc).isoformat(), "input_type": "TEXT", "text": text,
            "attachments": [], "reply_to": None, "request_class": classify(text, metadata),
            "priority": "NORMAL", "metadata": metadata,
        }

    def handle_update(self, update):
        started = time.perf_counter()
        update_id = update.get("update_id")
        if update_id is None: raise ValueError("update_id required")
        if str(update_id) in self._seen(): return {"status": "DUPLICATE", "update_id": update_id}
        message = self.parse_update(update); user_id = message["user_id"]
        user_ref = hashlib.sha256(user_id.encode()).hexdigest()[:12]
        if user_id not in self.allowed_users:
            self.service.ledger.append("TELEGRAM_ACCESS_DENIED", None,
                {"channel": "telegram", "telegram_update_id": update_id, "authorized": False,
                 "user_ref": user_ref, "failure_class": "UNAUTHORIZED_USER"}, actor="telegram_adapter")
            raise PermissionError("unauthorized Telegram user")
        intent = message["request_class"]
        self.service.ledger.append("TELEGRAM_UPDATE_RECEIVED", None,
            {"channel": "telegram", "telegram_update_id": update_id, "authorized": True,
             "intent": intent, "user_ref": user_ref}, actor="telegram_adapter")
        try:
            if not self._allowed_rate(user_id): raise RuntimeError("rate limit exceeded")
            response = self.gateway.handle(message) if self.gateway is not None else self.service.handle(message)
            self._mark_seen(update_id)
            details = response.get("details") or {}
            self.service.ledger.append("TELEGRAM_UPDATE_COMPLETED", response.get("task_id"),
                {"channel": "telegram", "telegram_update_id": update_id, "authorized": True,
                 "intent": intent, "result": response.get("status"),
                 "premium_calls": details.get("premium_calls", 0),
                 "providers_used": [response.get("generated_by")] if response.get("generated_by") else [],
                 "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                 "failure_class": None}, actor="telegram_adapter")
            return response
        except Exception as exc:
            self.service.ledger.append("TELEGRAM_UPDATE_FAILED", None,
                {"channel": "telegram", "telegram_update_id": update_id, "authorized": True,
                 "intent": intent, "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                 "failure_class": type(exc).__name__}, actor="telegram_adapter")
            raise

    def send(self, chat_id, response):
        if not self.configured: return {"sent": False, "reason": "UNAVAILABLE"}
        payload = {"chat_id": str(chat_id), "text": response["summary"],
                   "disable_web_page_preview": True}
        if response.get("status") == "WAITING_APPROVAL" and response.get("task_id"):
            task_id = response["task_id"]
            payload["reply_markup"] = {"inline_keyboard": [[
                {"text": "APPROVE", "callback_data": f"APPROVE:{task_id}"},
                {"text": "REJECT", "callback_data": f"REJECT:{task_id}"},
                {"text": "DETAILS", "callback_data": f"DETAILS:{task_id}"},
            ]]}
        elif response.get("status") == "CONFIRMATION_REQUIRED" and response.get("task_id"):
            task_id = response["task_id"]
            payload["reply_markup"] = {"inline_keyboard": [[
                {"text": "CONFIRM CANCEL", "callback_data": f"CONFIRM_CANCEL:{task_id}"},
                {"text": "DETAILS", "callback_data": f"DETAILS:{task_id}"},
            ]]}
        body = json.dumps(payload).encode()
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
