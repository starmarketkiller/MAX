# Phase 7.32 — FVG_CONT isolation diagnostic (Windows / PC-MT5)

Hypothesis: `FVG-CONT-MT5-ISOLATION-DIAG-001` (committed before launch)  
Parent: Phase 7.31 `ISOLATION_READY`  
Window: **2023.10.02 → 2026.06.30** · GOLD · H4 · selector **8** · lot 0.01 · ResearchMode

This is a **density / recipe-R diagnostic**, not an edge claim and not live/prop.

## On PC-MT5 (PowerShell, repo root on branch)

```powershell
cd C:\Users\User\ClaudeWork\MAX
git pull origin cursor/edge-freeze-credit-safe-loop-5198
python server\research_scripts\phase7\phase7_32_fvg_cont_isolation_diagnostic\launch_diagnostic_run.py
```

Wait until Strategy Tester Journal shows **successfully finished**.

```powershell
python server\research_scripts\phase7\phase7_32_fvg_cont_isolation_diagnostic\collect_diagnostic_run.py
python server\research_scripts\phase7\phase7_32_fvg_cont_isolation_diagnostic\analyze_diagnostic_run.py
git add server\research_scripts\phase7\phase7_32_fvg_cont_isolation_diagnostic
git commit -m "research(phase7.32): FVG_CONT isolation diagnostic result"
git push origin cursor/edge-freeze-credit-safe-loop-5198
```

## Decisions (frozen)

| Label | Meaning |
|---|---|
| `INSUFFICIENT_SAMPLE` | n_closed < 30 |
| `SAMPLE_READY_FOR_EDGE_PREREG` | n≥30 — unlocks a *new* habitat prereg only |
| `HARNESS_OR_IDENTITY_PROBLEM` | foreign stratNames / recon fail |
| `MIXED` | else; no promotion |

Keep worker PowerShell open if using Cursor My Machines (`PC-MT5`).
