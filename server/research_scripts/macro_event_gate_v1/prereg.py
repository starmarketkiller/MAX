"""Pre-registration loading and the 'no silent parameter change' rule."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWED_SPLITS = ("discovery_a", "discovery_b", "combined_discoveries", "internal_validation")
EXCLUDED_SPLIT_KEYS = ("excluded_consumed_holdout_2022", "excluded_phase7_sealed_holdout")


class PreregViolation(Exception):
    pass


def canonical_sha256(obj):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load(path=None):
    path = path or os.path.join(HERE, "prereg_MEG-NFP-CPI-FOMC-001.json")
    with open(path, encoding="utf-8") as handle:
        prereg = json.load(handle)
    declared = prereg.get("params_sha256")
    actual = canonical_sha256(prereg["params"])
    if declared != actual:
        raise PreregViolation(
            f"params_sha256 {declared} does not match params ({actual}): "
            "the parameters changed after pre-registration"
        )
    return prereg


def _parse_utc(text):
    return datetime.fromisoformat(text).astimezone(timezone.utc)


def split_window(prereg, split):
    """Return (start_ts, end_ts) epoch seconds for an allowed split.

    combined_discoveries unions discovery_a start with discovery_b end.
    """
    if split not in ALLOWED_SPLITS:
        raise PreregViolation(f"split '{split}' is not available to this runner")
    if split == "combined_discoveries":
        a = prereg["splits"]["discovery_a"]
        b = prereg["splits"]["discovery_b"]
        return (int(_parse_utc(a["start_utc"]).timestamp()),
                int(_parse_utc(b["end_utc"]).timestamp()))
    s = prereg["splits"][split]
    return (int(_parse_utc(s["start_utc"]).timestamp()),
            int(_parse_utc(s["end_utc"]).timestamp()))


def excluded_intervals(prereg):
    out = []
    for key in EXCLUDED_SPLIT_KEYS:
        s = prereg["splits"][key]
        out.append((int(_parse_utc(s["start_utc"]).timestamp()),
                    int(_parse_utc(s["end_utc"]).timestamp()),
                    key))
    return out


def assert_split_avoids_exclusions(prereg, split):
    start, end = split_window(prereg, split)
    for ex_start, ex_end, name in excluded_intervals(prereg):
        if start < ex_end and end > ex_start:
            raise PreregViolation(
                f"split '{split}' overlaps excluded window '{name}' "
                f"[{ex_start}, {ex_end}]; refuse"
            )


def window_hits_exclusion(start_ts, end_ts, prereg):
    for ex_start, ex_end, name in excluded_intervals(prereg):
        if start_ts < ex_end and end_ts > ex_start:
            return name
    return None


def day_in_exclusion(day_ts, prereg):
    for ex_start, ex_end, name in excluded_intervals(prereg):
        if ex_start <= day_ts <= ex_end:
            return name
    return None


def check_hypothesis_registry(registry_path, prereg):
    registry = {}
    if os.path.exists(registry_path):
        with open(registry_path, encoding="utf-8") as handle:
            registry = json.load(handle)
    known = registry.get(prereg["hypothesis_id"])
    if known and known["params_sha256"] != prereg["params_sha256"]:
        raise PreregViolation(
            f"{prereg['hypothesis_id']} already ran with params "
            f"{known['params_sha256']}; a new parameter set needs a new hypothesis_id"
        )
    registry.setdefault(
        prereg["hypothesis_id"],
        {"params_sha256": prereg["params_sha256"], "runs": []},
    )
    return registry


def freeze(path):
    with open(path, encoding="utf-8") as handle:
        prereg = json.load(handle)
    if prereg.get("params_sha256") not in (None, "COMPUTED_BY_prereg.py"):
        raise PreregViolation("already frozen; create a new hypothesis_id instead")
    prereg["params_sha256"] = canonical_sha256(prereg["params"])
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(prereg, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return prereg["params_sha256"]


if __name__ == "__main__":
    import sys
    print(freeze(sys.argv[1]))
