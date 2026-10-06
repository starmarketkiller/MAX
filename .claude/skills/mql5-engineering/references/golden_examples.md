# Golden Examples — NEXUS MQL5

Real, already-applied, correct patterns from this codebase — imitate these, don't re-derive them from first principles.

## TF-scoped guard before persistent state (the fix pattern)

`NXS_Strategies.mqh:1535-1552` (`NXS_Strat_BreakoutAcc`, post-fix `651d3a2`):

```mql5
SNXSSignal NXS_Strat_BreakoutAcc(){
   SNXSSignal s; ZeroMemory(s); s.strat = STRAT_BREAKOUT_ACC; s.stratName = "BREAKOUT_ACC";
   if(!InpStrat_BREAKOUT_ACC || !NXS_SelectorAllows(9)) return s;
   ENUM_TIMEFRAMES tf = NXS_EffTF();
   // guardia precoce: nessuna lettura/scrittura dello stato se il pass corrente
   // non e' il timeframe dichiarato della strategia
   if(tf != NXS_Profile_TF("BREAKOUT_ACC")) return s;
   datetime curBar0 = iTime(g_sym, tf, 0);
   if(g_breakoutAccState.lastBarTime == curBar0) return s;   // same-bar guard, separate concern
   g_breakoutAccState.lastBarTime = curBar0;
   ...
}
```

Two guards, two different problems: the TF guard (§3 of SKILL.md) protects against cross-pass contamination; the same-bar guard protects against re-firing within one still-open bar. Both are needed, neither substitutes for the other.

## Indicator handle caching per timeframe

`NXS_SignalQuality.mqh:33-51` (`NXS_ADXv`) — see SKILL.md §1 for the full snippet. Reuse this exact caching shape for any new per-TF indicator read instead of calling `iADX`/`iRSI`/etc. fresh every time.

## Deriving execution parameters from the order's own symbol, not the chart's

`NXS_Globals.mqh` — `NXS_FillingForSymbol(sym)`/`NXS_DeviationForSymbol(sym)`, called with the **order's** symbol inside `NXS_DoBuy`/`NXS_DoSell`/`NXS_DoClose`/`NXS_Prot_ClosePositionWithReason` — not the chart symbol. Fixed under `AUD0-RAW-003`/`AUD0-RAW-004`/`NXS-PROT-003`.

## Recovering strategy attribution from the opening deal, not the closing one

`NXS_RiskShield.mqh:279-310` (`NXS_RS_Breaker_Update`) — builds a `position_id → strategy` map from **opening** deals (`DEAL_ENTRY_IN`, never rewritten by the broker) before scanning closing deals, instead of trusting the closing deal's comment (which MT5 overwrites with `"sl ..."`/`"tp ..."` on native stop/target exits).

## Causal, re-derivable regime check instead of reusing a stale tick-global

`NXS_SignalQuality.mqh:19-67` (`NXS_ADXv`/`NXS_DetectRegimeTF`) — explicitly recomputes ADX/ATR fresh **on the strategy's own profile TF** via a small per-TF cache, specifically because the shared tick-global `g_regime` is computed once per tick on the currently-active collector-pass TF, which is wrong for a check meant to apply to a different strategy's TF (this exact bug made the regime veto silently never fire for `SAR`, confirmed on 32/32 real trades, before the fix documented in the same file's comments).

## One invariant, many callers, no parallel fast path

`NXS_Execution.mqh:63-213` (`NXS_CommonExposurePreflight`) called from `NXS_Execution.mqh:548`, `NXS_GridRecovery.mqh:86`, `NXS_InstManage.mqh:195`, `NXS_ProfitReclaim.mqh:107`, `NXS_Pyramiding.mqh:166`, `NXS_SLReclaim.mqh:214` — six call sites, zero duplicated gate logic. This is the shape any new exposure-creating mechanism should match: call the existing invariant, don't write a new one.
