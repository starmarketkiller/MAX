# Edge Book — isolated MetaEditor compile evidence

Date: 2026-11-08 (Europe/Rome)

## Method

Portable MetaEditor tree under `_mt5_edge_compile/` (gitignored):

- Copied worktree `MQL5/Experts/NEXUS_EA_v2.mq5` + `MQL5/Include/NEXUS_v1/**`
- `MetaEditor64.exe /portable /compile:... /log:...`
- Did **not** retarget `C:\MT5-Tester\MQL5\Include\NEXUS_v1` (still junctions to `ClaudeWork\MAX`, not this worktree)
- Did **not** touch live terminal data folders
- Did **not** kill/stop `metatester64` PIDs 5380 / 15776

## Result

```
Result: 0 errors, 2 warnings, 28517 ms elapsed, cpu='X64 Regular'
```

Warnings are pre-existing (`NXS_MAX_SIGNALS` redefinition; `ulong`→`long` conversion) and unrelated to Edge Book.

Log confirms include of `NXS_EdgeBook.mqh`.

## Artifact digest (local only, not committed)

| File | SHA256 | Bytes | mtime (Europe/Rome) |
|---|---|---|---|
| `_mt5_edge_compile/MQL5/Experts/NEXUS_EA_v2.ex5` | `5BFA03FA734902302CCD798082E4B57C4244D66FCF7369AF94B1488C5D2CE772` | 811284 | 2026-11-08 20:41:11 |

## Tester smoke status

Still blocked on this machine while existing `metatester64` jobs own the Tester install. Use `docs/EDGE_BOOK_TESTER_RUNBOOK_V1.md` on a free Tester slot. Not a confirmatory edge claim.
