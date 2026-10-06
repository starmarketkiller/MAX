#!/usr/bin/env python3
"""NEXUS MQL5 Engineering Skill - static verifier (heuristic, not authoritative).

Mechanical, grep-level checks for a subset of the checklist in SKILL.md §18.
This is advisory only: it cannot see the real call graph across files, cannot
compile, and cannot tell a legitimate deliberate pattern (EC-05 in
eval/eval_cases.md) from a mistake. Every finding is a prompt for a human/
model reviewer to check manually against SKILL.md and references/, not an
automatic pass/fail. No MQL5 file is modified by this script.

Usage:
    python verifier.py <path/to/file.mqh or .mq5>
    python verifier.py <path/to/directory>   # recurses over *.mqh/*.mq5
"""
import re
import sys
from pathlib import Path

ORDER_SEND_PATTERN = re.compile(r"\b(OrderSend|NXS_DoBuy|NXS_DoSell)\s*\(")
PREFLIGHT_MARKERS = re.compile(r"\b(NXS_CommonExposurePreflight|NXS_OpenTrade)\s*\(")
STRAT_ENUM_COMPARE = re.compile(r"\.\s*strat\s*(==|!=)")
PROFILE_TF_MARKER = re.compile(r"NXS_Profile_TF\s*\(")
STATIC_OR_GLOBAL_STATE = re.compile(r"^\s*(static\s+\w|g_\w+\s*\[|struct\s+SNXS\w*State)", re.MULTILINE)
RAW_GATE_LOG = re.compile(r'Print(Format)?\s*\(\s*"[^"]*\b(GATE|BLOCK(ED)?)\b', re.IGNORECASE)
GATE_TELEMETRY_MARKER = re.compile(r"NXS_GateTelemetry\s*\(")
HARDCODED_THRESHOLD_HINT = re.compile(
    r"\b(Sharpe|PF|ProfitFactor)\b\s*[<>]=?\s*[0-9.]+", re.IGNORECASE
)
INPUT_DECL = re.compile(r"^\s*input\b")


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    findings = []

    if ORDER_SEND_PATTERN.search(text) and not PREFLIGHT_MARKERS.search(text):
        findings.append(
            "[CHECK SKILL.md 11 / EC-03] File calls OrderSend/NXS_DoBuy/NXS_DoSell but contains "
            "no call to NXS_CommonExposurePreflight or NXS_OpenTrade in this same file. "
            "If this is a new exposure-creating path, it must route through the common "
            "invariant (directly or via a caller) - verify the actual call graph manually, "
            "this check cannot see across files."
        )

    if STRAT_ENUM_COMPARE.search(text):
        findings.append(
            "[CHECK SKILL.md 8 / EC-04] Found a comparison against `.strat` (the enum). The "
            "enum is not a reliable per-strategy identity (34 strategies share "
            "STRAT_STRUCT_REACT as of 2026-10-06). Use `.stratName` for attribution-sensitive "
            "logic instead, unless this is genuinely about the attribution *bucket* itself."
        )

    if STATIC_OR_GLOBAL_STATE.search(text) and not PROFILE_TF_MARKER.search(text):
        findings.append(
            "[CHECK SKILL.md 3 / EC-01 / EC-02] File declares static/global state (or a "
            "*State struct) but contains no call to NXS_Profile_TF(...). If any strategy "
            "function in this file is called once per collector pass (the normal case) and "
            "reads/writes that state, it needs a TF-scoped guard "
            "(`if(tf != NXS_Profile_TF(\"NAME\")) return;`) before touching it - see "
            "CROSS_TIMEFRAME_STATE_CONTAMINATION in references/."
        )

    gate_logs = RAW_GATE_LOG.findall(text)
    if gate_logs and not GATE_TELEMETRY_MARKER.search(text):
        findings.append(
            "[CHECK SKILL.md 10] Found an ad hoc Print/PrintFormat that looks like a gate log "
            "(contains GATE/BLOCK) but no NXS_GateTelemetry call in this file. New gates "
            "inside the exposure-creation path should use the structured convention."
        )

    for m in HARDCODED_THRESHOLD_HINT.finditer(text):
        line_no = text.count("\n", 0, m.start()) + 1
        line = text.splitlines()[line_no - 1]
        if not INPUT_DECL.match(line):
            findings.append(
                f"[CHECK SKILL.md 16-3 / EC-06] Line {line_no}: possible hardcoded performance "
                f"threshold not declared as `input`: {line.strip()!r}. If this is meant to be a "
                "universal requirement rather than a configurable default, reconsider - see "
                "forbidden pattern 3."
            )

    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1
    target = Path(argv[1])
    files = []
    if target.is_dir():
        files = sorted(target.rglob("*.mqh")) + sorted(target.rglob("*.mq5"))
    elif target.is_file():
        files = [target]
    else:
        print(f"Not found: {target}")
        return 1

    total_findings = 0
    for f in files:
        findings = check_file(f)
        if findings:
            print(f"\n=== {f} ===")
            for finding in findings:
                print(f"  - {finding}")
            total_findings += len(findings)

    print(f"\n{len(files)} file(s) scanned, {total_findings} advisory finding(s). "
          "Heuristic only - review manually against SKILL.md before acting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
