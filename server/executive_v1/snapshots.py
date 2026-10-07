"""Light executive snapshots + diff for "cosa è cambiato da ieri?".

Only compact facts are stored (statuses, numeric key metrics, alert codes,
approval ids, deployed sha) - never prose, prompts or model output.  At most
one snapshot per `min_interval_seconds`, bounded to `keep` entries.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

TRACKED_METRICS = {
    "system": ("deployed_sha", "ci", "mistral", "dispatcher_running"),
    "tasks": ("running", "blocked", "failed", "waiting_approval", "completed_recently"),
    "revenue": ("prospects", "qualified_leads", "drafts_ready", "sales", "revenue_eur",
                "runner_enabled"),
    "trading": ("strategies_total", "strategies_candidate", "validated", "shadow", "live",
                "account_state"),
    "ai_fashion_agency": ("models_active", "products_found", "store_ready", "content_ready",
                          "awaiting_approval", "revenue", "credits_spent"),
    "social": ("accounts_active", "published"),
}


def compact(state):
    return {"generated_at": state["generated_at"], "overall_status": state["overall_status"],
            "statuses": {d: state[d]["status"] for d in TRACKED_METRICS},
            "metrics": {d: {k: state[d]["key_metrics"].get(k) for k in keys}
                        for d, keys in TRACKED_METRICS.items()},
            "alerts": sorted(a["code"] for a in state["alerts"]),
            "approvals": {a["approval_id"]: a["reason"] for a in state["decisions_required"]}}


class SnapshotStore:
    def __init__(self, path, *, keep=60, min_interval_seconds=3600):
        self.path = Path(path)
        self.keep, self.min_interval = keep, min_interval_seconds
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self, items):
        temp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        temp.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, self.path)

    def record(self, state, *, now=None):
        now = now or datetime.now(timezone.utc)
        with self._lock:
            items = self._load()
            if items:
                last = datetime.fromisoformat(items[-1]["recorded_at"])
                if (now - last).total_seconds() < self.min_interval:
                    return False
            items.append({**compact(state), "recorded_at": now.isoformat()})
            self._save(items[-self.keep:])
            return True

    def baseline(self, *, now=None, hours=24):
        """Snapshot closest to `hours` ago (oldest available if history is shorter)."""
        now = now or datetime.now(timezone.utc)
        items = self._load()
        if not items:
            return None
        target = now - timedelta(hours=hours)
        older = [i for i in items if datetime.fromisoformat(i["recorded_at"]) <= target]
        return older[-1] if older else items[0]


def _fmt(value):
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def diff(previous, current_state):
    """Human-meaningful changes between a stored snapshot and the live state."""
    if previous is None:
        return {"baseline_at": None, "changes": [], "note": "nessuno snapshot precedente"}
    cur = compact(current_state)
    changes = []
    if previous["overall_status"] != cur["overall_status"]:
        changes.append(f"stato generale {previous['overall_status']} → {cur['overall_status']}")
    for domain, status in cur["statuses"].items():
        before = previous["statuses"].get(domain)
        if before and before != status:
            changes.append(f"{domain}: {before} → {status}")
    for domain, metrics in cur["metrics"].items():
        for key, value in metrics.items():
            before = (previous["metrics"].get(domain) or {}).get(key)
            if before != value and before is not None:
                changes.append(f"{domain}.{key}: {_fmt(before)} → {_fmt(value)}")
    new_alerts = sorted(set(cur["alerts"]) - set(previous["alerts"]))
    gone_alerts = sorted(set(previous["alerts"]) - set(cur["alerts"]))
    new_approvals = [r for k, r in cur["approvals"].items() if k not in previous["approvals"]]
    closed_approvals = [r for k, r in previous["approvals"].items() if k not in cur["approvals"]]
    persisting = sorted(set(cur["alerts"]) & set(previous["alerts"]))
    return {"baseline_at": previous["recorded_at"], "changes": changes,
            "new_alerts": new_alerts, "resolved_alerts": gone_alerts,
            "persisting_alerts": persisting, "new_approvals": new_approvals,
            "closed_approvals": closed_approvals}
