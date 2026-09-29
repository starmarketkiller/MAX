"""Configurable notification policy; low-value INFO stays ledger-only."""
from __future__ import annotations

LEVELS = {"INFO": 0, "IMPORTANT": 1, "HIGH": 2, "URGENT": 3}


class NotificationEngine:
    def __init__(self, service, telegram, minimum_telegram="IMPORTANT"):
        self.service = service; self.telegram = telegram
        self.minimum_telegram = minimum_telegram if minimum_telegram in LEVELS else "IMPORTANT"

    def notify(self, level, chat_id, response):
        if level not in LEVELS: raise ValueError("invalid notification level")
        if LEVELS[level] < LEVELS[self.minimum_telegram]:
            self.service.ledger.append("NOTIFICATION_SENT", response.get("task_id"),
                                       {"channel": "LEDGER", "priority": level}, actor="notification_engine")
            return {"sent": True, "channel": "LEDGER", "aggregated": True}
        delivered = self.telegram.send(chat_id, {**response, "priority": level})
        return {**delivered, "channel": "TELEGRAM", "aggregated": False}

