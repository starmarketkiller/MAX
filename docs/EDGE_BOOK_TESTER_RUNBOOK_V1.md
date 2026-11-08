# Edge Book — Strategy Tester runbook (smoke)

Credit-safe book only. Not a confirmatory edge claim. Production remains NO-GO.

## Artifacts

| File | Role |
|---|---|
| `MQL5/Profiles/NEXUS_EDGE_SHORTLIST_GOLD.set` | Chart / properties shortlist |
| `MQL5/Profiles/NEXUS_EDGE_SHORTLIST_GOLD_SMOKE.ini` | Tester `/config` smoke 2026.10.01–2026.10.19 GOLD H4 |
| `scripts/edge_book_set_check.py` | Static completeness of the `.set` |

## Constraints

- Do **not** kill existing `metatester64` processes (project standing rule).
- Do **not** launch `/config` against a live terminal data folder (skill §13).
- Prefer a dedicated tester terminal / portable copy with its own `MQL5` tree synced to this branch.
- Sync `Include\NEXUS_v1` before compile (skill §12).
- **Junction gotcha:** `C:\MT5-Tester\MQL5\Include\NEXUS_v1` currently junctions to `ClaudeWork\MAX\...`, **not** agent worktrees. Compiling Edge Book for a worktree requires retargeting that junction temporarily **or** an isolated `/portable` MetaEditor tree (see `docs/EDGE_BOOK_COMPILE_EVIDENCE_V1.md`). Do not retarget while metatester is mid-run.

## Manual smoke steps

1. Checkout `cursor/edge-book-mode-v1-b2b8` into the tester `MQL5` tree.
2. Compile `Experts\NEXUS_EA_v2.mq5` (0 errors).
3. Copy `NEXUS_EDGE_SHORTLIST_GOLD_SMOKE.ini` into the tester config path.
4. Launch tester `/config` on that ini only.
5. Accept only if: Expert loads, Journal shows `[EDGE_BOOK] mode=EDGE_SHORTLIST`, and any opens (if any) are shortlist `stratName` only.

Zero opens in the short window is allowed — the smoke proves configuration, not edge.

## Deterministic checks (no Tester)

```
python scripts/edge_freeze_check.py
python scripts/edge_book_set_check.py
python -m pytest server/tests/test_edge_freeze_check_v1.py server/tests/test_edge_book_matrix_v1.py server/tests/test_edge_book_set_v1.py -q
```
