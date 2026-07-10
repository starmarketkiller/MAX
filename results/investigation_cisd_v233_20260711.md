# CISD (v2.3.3) investigation - 2026-07-11

## Question
Coder expected CISD to produce at least one H4 trade; screening consistently
showed `setup=0` across multiple 3-week tests on v2.3.2/v2.3.3.

## Environment bug found along the way
MetaEditor64.exe resolves `#include <NEXUS_v1\...>` (angle-bracket includes)
using the **live terminal's** `MQL5\Include` folder
(`D0E8209F77C8CF37AD8BF550E51FF075`), regardless of which terminal's `.mq5`
is passed to `/compile`. Confirmed by planting a marker string in the test
terminal's own copy of `NXS_Strategies_Institutional.mqh` - it never
appeared in Print() output until the SAME edit was also copied into the
live terminal's copy of the file.

**Practical consequence:** as long as both terminals are kept in sync (the
normal workflow used all session - copy to both, compile both), test
results are valid. But any one-off edit made to only ONE terminal's Include
folder silently has no effect when compiling the OTHER terminal - always
copy changed files to both `D0E8209F77C8CF37AD8BF550E51FF075` and
`7F8EC41F011085EB9C65165AE426B5A6` before compiling either.

## CISD finding (confirmed with instrumented build, then reverted)
Diagnostic added inside `NXS_Strat_CISD()` printed tf/bar/bear3/bull3/c1/hh/ll
on every new bar of the active TF, run on the 3-week window (2026.06.19 -
2026.07.10), multi-TF mode on (D1/H4/H1 passes).

- 83 unique H4 bars in the window.
- The 3-same-color-candle setup (`bear3`/`bull3`) formed on 26 of those 83
  bars (18 bear3, 8 bull3) - a normal, unremarkable formation rate.
- The break confirmation (`c1 > hh` for bear3, `c1 < ll` for bull3) **never
  triggered once** across all 26 setups.

**Conclusion: not a bug.** CISD's logic runs correctly on the intended H4
timeframe (confirmed via NXS_EffTF()/multi-TF pass routing, which is wired
correctly). The setup step is unremarkable-rate; the break-of-extreme
confirmation on the immediate next H4 candle is simply a strict condition
that this specific 3-week GOLD window never satisfied. Longer windows or a
volatility regime with sharper continuation moves would be needed to see it
fire. No code change made - diagnostic fully reverted, `NXS_Strat_CISD()` is
back to the clean v2.3.3 logic.
