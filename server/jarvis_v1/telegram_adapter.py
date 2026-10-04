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
    _STATE_CODES = {"Q": "QUEUED", "R": "RUNNING", "B": "BLOCKED",
                    "E": "ESCALATION_REQUIRED", "A": "WAITING_APPROVAL",
                    "C": "COMPLETED", "F": "FAILED", "X": "CANCELLED",
                    "P": "WAITING_PROVIDER", "D": "WAITING_DEPENDENCY"}
    _STATE_TO_CODE = {value: key for key, value in _STATE_CODES.items()}
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
        if callback and text.startswith("J1|"):
            parts = text.split("|")
            if len(parts) < 3 or any(len(part) > 48 for part in parts):
                raise ValueError("invalid Telegram callback")
            code = parts[1]
            task_actions = {"TS": "TASK_STATUS", "TD": "TECHNICAL_DETAILS",
                            "DG": "DIAGNOSTICS", "LC": "LIFECYCLE",
                            "AP": "APPROVE", "RJ": "REJECT", "RS": "RESUME"}
            agent_actions = {"AD": "AGENT_DETAILS", "AC": "AGENT_CAPABILITIES",
                             "PS": "PROVIDER_STATUS"}
            if code in task_actions:
                metadata.update({"ui_action": task_actions[code], "task_id": parts[2]})
                if code == "LC":
                    metadata["lifecycle_page"] = int(parts[3]) if len(parts) > 3 else 0
                elif len(parts) > 3 and parts[3] in self._STATE_CODES:
                    metadata["expected_state"] = self._STATE_CODES[parts[3]]
                text = f"Telegram action {task_actions[code]} for {parts[2]}"
            elif code in agent_actions:
                metadata.update({"ui_action": agent_actions[code], "agent_id": parts[2]})
                text = f"Telegram action {agent_actions[code]} for {parts[2]}"
            elif code == "Q" and parts[2] in ("STATUS", "TASKS", "AGENTS", "HELP"):
                metadata.update({"ui_action": "QUICK_ACTION", "quick_action": parts[2]})
                text = f"Telegram quick action {parts[2]}"
            else:
                raise ValueError("unsupported Telegram callback")
        elif callback and ":" in text:
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
        payload = {"chat_id": str(chat_id), "text": self.render_response(response),
                   "disable_web_page_preview": True}
        keyboard = self.build_keyboard(response)
        if keyboard:
            payload["reply_markup"] = {"inline_keyboard": keyboard}
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

    @classmethod
    def build_keyboard(cls, response):
        """Build contextual UI only; mutations remain owned by JarvisService."""
        task_id = response.get("task_id")
        status = response.get("status")
        details = response.get("details") or {}
        if task_id and details.get("state"):
            state_code = cls._STATE_TO_CODE.get(status, "")
            suffix = f"|{state_code}" if state_code else ""
            rows = [[
                {"text": "Aggiorna stato", "callback_data": f"J1|TS|{task_id}{suffix}"},
                {"text": "Dettagli tecnici", "callback_data": f"J1|TD|{task_id}{suffix}"},
            ], [
                {"text": "Lifecycle", "callback_data": f"J1|LC|{task_id}|0"},
                {"text": "Diagnostica", "callback_data": f"J1|DG|{task_id}{suffix}"},
            ]]
            recovery = (details.get("recovery") or {}).get("classification")
            if status == "BLOCKED" and recovery == "ORPHANED_RUNNING_AFTER_RESTART":
                rows.append([{"text": "Riprendi", "callback_data": f"J1|RS|{task_id}|B"}])
            if status == "WAITING_APPROVAL":
                rows.append([
                    {"text": "Approva", "callback_data": f"J1|AP|{task_id}|A"},
                    {"text": "Rifiuta", "callback_data": f"J1|RJ|{task_id}|A"},
                ])
            if details.get("view") == "TASK_LIFECYCLE" and details.get("lifecycle_has_more"):
                next_page = int(details.get("lifecycle_page") or 0) + 1
                rows.append([{"text": "Mostra altro", "callback_data": f"J1|LC|{task_id}|{next_page}"}])
            return rows
        if details.get("view") == "AGENT_LIST":
            rows = []
            for agent in (details.get("items") or [])[:8]:
                agent_id = agent.get("agent_id")
                if agent_id:
                    rows.append([{"text": f"Dettagli · {agent_id[:24]}",
                                  "callback_data": f"J1|AD|{agent_id}"}])
            return rows
        if details.get("view") in ("AGENT_DETAIL", "AGENT_CAPABILITIES", "PROVIDER_STATUS"):
            agent_id = (details.get("agent") or {}).get("agent_id")
            if agent_id:
                return [[{"text": "Capabilities", "callback_data": f"J1|AC|{agent_id}"},
                         {"text": "Provider status", "callback_data": f"J1|PS|{agent_id}"}]]
        if response.get("status") == "PARTIAL" or response.get("response_type") == "ERROR":
            return [[{"text": "Stato NEXUS", "callback_data": "J1|Q|STATUS"},
                     {"text": "Le mie task", "callback_data": "J1|Q|TASKS"}],
                    [{"text": "Agenti", "callback_data": "J1|Q|AGENTS"},
                     {"text": "Help", "callback_data": "J1|Q|HELP"}]]
        return []

    @staticmethod
    def _time(value):
        if not value:
            return "—"
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed.astimezone().strftime("%d/%m %H:%M")
        except (TypeError, ValueError):
            return str(value)[:16]

    @classmethod
    def render_response(cls, response):
        """Render structured Jarvis details into one compact Telegram message."""
        summary = str(response.get("summary") or "Jarvis non ha prodotto un riepilogo.").strip()
        details = response.get("details") or {}
        lines = [summary]

        if details.get("view") == "TASK_LIST":
            lines = [summary, ""]
            for item in (details.get("items") or [])[:10]:
                title = str(item.get("title") or "Senza descrizione").strip().replace("\n", " ")
                if len(title) > 70:
                    title = title[:67] + "..."
                lines.append(f"{item.get('task_id', 'TASK_—')} — {item.get('state', 'UNKNOWN')} — {title}")
                lines.append(f"  aggiornata {cls._time(item.get('updated_at'))}")
            counts = details.get("counts") or {}
            if counts:
                order = ("BLOCKED", "QUEUED", "RUNNING", "ESCALATION_REQUIRED",
                         "WAITING_APPROVAL", "COMPLETED", "CANCELLED", "FAILED")
                compact = [f"{counts[state]} {state.lower()}" for state in order if counts.get(state)]
                lines.extend(["", ", ".join(compact) + "."])

        elif details.get("view") == "SYSTEM_STATUS":
            states = details.get("task_states") or {}
            dispatcher = details.get("dispatcher") or {}
            lines.extend(["",
                f"Queued: {states.get('QUEUED', 0)}",
                f"Running: {states.get('RUNNING', 0)}",
                f"Blocked: {states.get('BLOCKED', 0)}",
                f"Escalation: {states.get('ESCALATION_REQUIRED', 0)}",
                f"Waiting approval: {states.get('WAITING_APPROVAL', 0)}",
                f"Completed recenti: {details.get('completed_recent', 0)}",
                f"Dispatcher: {dispatcher.get('status') or 'UNKNOWN'}",
            ])

        elif details.get("view") == "AGENT_LIST":
            lines = [summary, ""]
            for item in (details.get("items") or [])[:10]:
                caps = ", ".join((item.get("capabilities") or [])[:3]) or "—"
                lines.append(f"{item.get('agent_id') or 'UNKNOWN'} · {item.get('status') or 'UNKNOWN'}")
                lines.append(f"  {item.get('role') or 'ruolo —'} · {item.get('provider') or 'provider —'}")
                lines.append(f"  capability: {caps}")

        elif details.get("view") in ("AGENT_DETAIL", "AGENT_CAPABILITIES", "PROVIDER_STATUS"):
            agent = details.get("agent") or {}
            lines.extend(["", f"ID: {agent.get('agent_id') or '—'}",
                          f"Ruolo: {agent.get('role') or '—'}",
                          f"Provider: {agent.get('provider') or '—'}",
                          f"Stato: {agent.get('status') or 'UNKNOWN'}",
                          f"Integrazione: {agent.get('integration_status') or 'UNKNOWN'}"])
            if details.get("view") != "PROVIDER_STATUS":
                lines.extend(["", "Capabilities:", *[f"• {cap}" for cap in (agent.get("capabilities") or [])]])

        elif response.get("task_id") and details.get("state"):
            lines.extend(["", f"Stato: {details.get('state')}"])
            if details.get("title"):
                lines.append(f"Task: {details['title']}")
            lines.append(f"Executor: {details.get('executor') or 'NON ASSEGNATO'}")
            lines.append(f"Retry: {details.get('retry_count') if details.get('retry_count') is not None else '—'}")
            lines.append(f"Dispatcher attempts: {details.get('dispatch_attempts') if details.get('dispatch_attempts') is not None else '—'}")
            if details.get("dispatch_last_error"):
                lines.append(f"Causa: {details['dispatch_last_error']}")
            recovery = details.get("recovery") or {}
            if recovery.get("classification"):
                lines.append(f"Recovery: {recovery['classification']}")
            escalation = details.get("escalation") or {}
            if escalation:
                lines.append(f"Escalation classification: {escalation.get('classification') or '—'}")
                lines.append(f"Escalation target/provider: {escalation.get('target') or '—'}")
            verifier = details.get("verifier") or {}
            if verifier:
                lines.append(f"Verifier: {verifier.get('passed') if verifier.get('passed') is not None else '—'}")
                if verifier.get("failure_class"):
                    lines.append(f"Failure class: {verifier['failure_class']}")
            if details.get("result_decision"):
                lines.append(f"Result decision: {details['result_decision']}")
            lines.append(f"Ultimo aggiornamento: {cls._time(details.get('updated_at'))}")
            if details.get("next_step"):
                lines.extend(["", f"Prossimo passo: {details['next_step']}"])
            lifecycle = details.get("lifecycle") or []
            if lifecycle:
                page = details.get("lifecycle_page")
                heading = "Lifecycle:" if page is None else f"Lifecycle · pagina {int(page) + 1}:"
                lines.extend(["", heading])
                visible = lifecycle[-6:] if page is None else lifecycle
                for event in visible:
                    lines.append(f"• {cls._time(event.get('timestamp'))} {event.get('event_type', 'UNKNOWN')}")
                if details.get("lifecycle_has_more"):
                    lines.append(f"… {details.get('lifecycle_total', 0) - ((int(page or 0) + 1) * 6)} eventi precedenti")

        rendered = "\n".join(lines).strip()
        if len(rendered) > 3900:
            rendered = rendered[:3860].rstrip() + "\n\nDettagli aggiuntivi disponibili nel Control Plane."
        return rendered
