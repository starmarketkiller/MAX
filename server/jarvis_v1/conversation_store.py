"""Small durable conversation index for Jarvis.

This is conversational context only, never canonical task state. Canonical task
facts remain in TaskQueue/EventLedger and are re-read for every response.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class ConversationStore:
    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._save({})

    def _load(self):
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self, value):
        temp = self.path.with_name(f"{self.path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        temp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, self.path)

    def get(self, conversation_id):
        with self._lock:
            return dict(self._load().get(conversation_id) or {})

    def update(self, conversation_id, **fields):
        with self._lock:
            data = self._load()
            current = dict(data.get(conversation_id) or {})
            current.update(fields)
            current["updated_at"] = _now_iso()
            data[conversation_id] = current
            self._save(data)
            return dict(current)

    def clear_pending(self, conversation_id):
        with self._lock:
            data = self._load()
            current = dict(data.get(conversation_id) or {})
            current.pop("pending_action", None)
            current["updated_at"] = _now_iso()
            data[conversation_id] = current
            self._save(data)
            return dict(current)
