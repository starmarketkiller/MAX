"""Manual entry point. Every command runs once, on request: no schedule, no daemon,
no network, no model call.

  python -m research_intelligence_v1.cli verify
  python -m research_intelligence_v1.cli ingest-registries
  python -m research_intelligence_v1.cli seed-bl01
  python -m research_intelligence_v1.cli ingest-bl01 RUN_DIR/summary.json
  python -m research_intelligence_v1.cli review EXP-...
  python -m research_intelligence_v1.cli generate-bl01
  python -m research_intelligence_v1.cli queue --available DATASET_ID [...]
  python -m research_intelligence_v1.cli brief FAMILY
  python -m research_intelligence_v1.cli loop-run --available ID --catalog catalog.json [--inbox summary.json]
  python -m research_intelligence_v1.cli loop-status | roles
  python -m research_intelligence_v1.cli checkpoint --note "after review X"

Run from server/research_scripts. --memory selects another file (tests, other projects).
"""
from __future__ import annotations

import argparse
import json
import sys

from . import agents, ingest, lessons, pilot, priority_queue, review
from .memory import DEFAULT_PATH, ResearchMemory


def main(argv=None):
    ap = argparse.ArgumentParser(prog="research_intelligence_v1")
    ap.add_argument("--memory", default=DEFAULT_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify")
    sub.add_parser("ingest-registries")
    sub.add_parser("seed-bl01")
    p = sub.add_parser("ingest-bl01")
    p.add_argument("summary")
    p = sub.add_parser("review")
    p.add_argument("record_id")
    sub.add_parser("generate-bl01")
    p = sub.add_parser("brief")
    p.add_argument("family")
    p = sub.add_parser("loop-run", help="run or resume one research-loop cycle (no schedule)")
    p.add_argument("--available", nargs="*", default=[])
    p.add_argument("--catalog", help="JSON file: data_needed id -> dataset descriptor")
    p.add_argument("--inbox", nargs="*", default=[], help="Behavior Lab summary.json files to ingest")
    p.add_argument("--no-approval-channel", action="store_true",
                   help="refuse APPROVAL_REQUIRED actions instead of queueing them in the orchestrator")
    sub.add_parser("loop-status")
    sub.add_parser("roles")
    p = sub.add_parser("checkpoint")
    p.add_argument("--note", default="")
    p = sub.add_parser("queue")
    p.add_argument("--available", nargs="*", default=[])
    p.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    mem = ResearchMemory(args.memory)
    if args.cmd == "verify":
        out = {"records": len(mem.records), "head": mem.head_hash(), "problems": mem.verify()}
    elif args.cmd == "ingest-registries":
        out = ingest.import_phase7_26(mem)
    elif args.cmd == "seed-bl01":
        out = pilot.seed(mem)
    elif args.cmd == "ingest-bl01":
        rec = ingest.import_behavior_lab_summary(mem, args.summary, "HYP-BL-H4M15-IPC-001",
                                                 prereg_relpath=pilot.PREREG_REF,
                                                 supersedes="EXP-BL-01-DISCOVERY" if mem.get("EXP-BL-01-DISCOVERY")
                                                 else None)
        rev, new, linked = review.review(mem, rec["record_id"])
        out = {"experiment": rec["record_id"], "review": rev["record_id"],
               "findings": [f["check"] for f in rev["body"]["findings"]],
               "new_proposals": [r["record_id"] for r in new], "linked_proposals": linked}
    elif args.cmd == "review":
        rev, new, linked = review.review(mem, args.record_id)
        out = {"review": rev["record_id"], "findings": rev["body"]["findings"],
               "new_proposals": [r["record_id"] for r in new], "linked_proposals": linked}
    elif args.cmd == "brief":
        out = lessons.briefing(mem, args.family)
    elif args.cmd in ("loop-run", "loop-status"):
        from .loop import ResearchLoop
        if args.cmd == "loop-status":
            out = ResearchLoop(mem).status()
        else:
            bridge = None
            if not args.no_approval_channel:
                from .approval_bridge import ApprovalBridge
                bridge = ApprovalBridge()
            catalog = json.load(open(args.catalog, encoding="utf-8")) if args.catalog else {}
            out = ResearchLoop(mem, bridge=bridge, availability={d: True for d in args.available},
                               dataset_catalog=catalog, inbox=args.inbox).run_cycle()
    elif args.cmd == "roles":
        out = {"roles": agents.ROLES, "step_owner": agents.STEP_OWNER, "problems": agents.validate_roles()}
    elif args.cmd == "checkpoint":
        out = mem.checkpoint(args.note)
    elif args.cmd == "generate-bl01":
        out = pilot.generate_alternatives(mem)
    else:
        out = priority_queue.build_queue(mem, {d: True for d in args.available}, write=not args.dry_run)
    json.dump(out, sys.stdout, indent=2, default=str)
    print()
    return 1 if args.cmd == "verify" and out["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
