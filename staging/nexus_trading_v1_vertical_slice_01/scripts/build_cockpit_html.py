"""build_cockpit_html.py - injects cockpit_demo/data/cockpit_data.json
(produced by export_cockpit_data.py) into the template, producing a
single self-contained cockpit_demo/index.html. Self-contained on
purpose: embedding the JSON inline avoids fetch()-over-file:// CORS
restrictions some browsers apply, so the demo opens directly as a
local file with no server needed.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = _ROOT / "cockpit_demo" / "template" / "index_template.html"
DATA_JSON = _ROOT / "cockpit_demo" / "data" / "cockpit_data.json"
OUT = _ROOT / "cockpit_demo" / "index.html"

PLACEHOLDER = "__COCKPIT_DATA_JSON__"


def main() -> None:
    template_text = TEMPLATE.read_text(encoding="utf-8")
    data_text = DATA_JSON.read_text(encoding="utf-8")
    if PLACEHOLDER not in template_text:
        raise RuntimeError(f"placeholder {PLACEHOLDER!r} not found in template")
    # JSON never contains "</script>" verbatim in this dataset's field
    # values, but guard anyway so an embedded close tag could never
    # terminate the script block early.
    safe_data_text = data_text.replace("</script>", "<\\/script>")
    out_text = template_text.replace(PLACEHOLDER, safe_data_text)
    OUT.write_text(out_text, encoding="utf-8")
    print(f"wrote {OUT} ({len(out_text)} bytes)")


if __name__ == "__main__":
    main()
