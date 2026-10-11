"""Pre-registration loading and the 'no silent parameter change' rule."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWED_SPLITS = ("discovery", "internal_validation")


class PreregViolation(Exception):
    pass


def canonical_sha256(obj):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load(path):
    with open(path, encoding="utf-8") as handle:
        prereg = json.load(handle)
    declared = prereg.get("params_sha256")
    actual = canonical_sha256(prereg["params"])
    if declared != actual:
        raise PreregViolation(f"params_sha256 {declared} does not match params ({actual}): "
                              "the parameters changed after pre-registration")
    return prereg


def split_window(prereg, split):
    if split not in ALLOWED_SPLITS:
        raise PreregViolation(f"split '{split}' is not available to this runner")
    s = prereg["splits"][split]
    return (int(datetime.fromisoformat(s["start_utc"]).timestamp()),
            int(datetime.fromisoformat(s["end_utc"]).timestamp()),
            int(datetime.fromisoformat(s["warmup_start_utc"]).timestamp()))


def check_hypothesis_registry(registry_path, prereg):
    """One hypothesis id, one parameter set. Returns the registry to update."""
    registry = {}
    if os.path.exists(registry_path):
        with open(registry_path, encoding="utf-8") as handle:
            registry = json.load(handle)
    known = registry.get(prereg["hypothesis_id"])
    if known and known["params_sha256"] != prereg["params_sha256"]:
        raise PreregViolation(f"{prereg['hypothesis_id']} already ran with params "
                              f"{known['params_sha256']}; a new parameter set needs a new hypothesis_id")
    registry.setdefault(prereg["hypothesis_id"], {"params_sha256": prereg["params_sha256"], "runs": []})
    return registry


def freeze(path):
    """Write params_sha256 into a draft pre-registration. Refuses to overwrite a frozen hash."""
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
