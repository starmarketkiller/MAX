"""Small durable conversation index for Jarvis.

This is conversational context only, never canonical task state. Canonical task
facts remain in TaskQueue/EventLedger and are re-read for every response.

NATURAL_CONVERSATION_V3: bounded, not arbitrary memory - a fixed set of
operational fields (last_task_id, last_agent, last_provider, last_result,
last_action, last_view, pending_action, pending_confirmation,
premium_allowed, preferred_provider, notification_mode) plus a clear TTL.
Nothing here grows unbounded and nothing here is ever treated as canonical -
every caller that resolves a task_id from this store still re-reads the real
record from TaskQueue before acting on it.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_TTL_SECONDS = 24 * 3600  # a day of silence and the context is stale


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class ConversationStore:
    def __init__(self, path, ttl_seconds=DEFAULT_TTL_SECONDS):
        self.path = Path(path)
        self._lock = threading.RLock()
        self.ttl_seconds = max(60, int(ttl_seconds))
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

    def _is_stale(self, entry):
        updated_at = entry.get("updated_at")
        if not updated_at:
            return False
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(updated_at)).total_seconds()
        except ValueError:
            return False
        return age > self.ttl_seconds

    def get(self, conversation_id):
        """Fail-closed on staleness: an entry older than ttl_seconds is
        returned as empty, never as a stale task_id/preference a caller
        might otherwise act on."""
        with self._lock:
            entry = self._load().get(conversation_id) or {}
            return {} if self._is_stale(entry) else dict(entry)

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
            current.pop("pending_confirmation", None)
            current["updated_at"] = _now_iso()
            data[conversation_id] = current
            self._save(data)
            return dict(current)

    def reset(self, conversation_id):
        """Drop only ephemeral conversation context, never task or ledger data."""
        with self._lock:
            data = self._load()
            existed = conversation_id in data
            data.pop(conversation_id, None)
            self._save(data)
            return existed

    def purge_stale(self):
        """Explicit, bounded-memory cleanup - removes every conversation
        entry older than ttl_seconds. Returns how many were purged."""
        with self._lock:
            data = self._load()
            kept = {cid: entry for cid, entry in data.items() if not self._is_stale(entry)}
            purged = len(data) - len(kept)
            if purged:
                self._save(kept)
            return purged
