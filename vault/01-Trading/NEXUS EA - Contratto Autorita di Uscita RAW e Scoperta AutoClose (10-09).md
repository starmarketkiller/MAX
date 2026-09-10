---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, mql5, research-mode, protezioni, autoclose, maxhold]
created: 2026-09-10
updated: 2026-09-10
---

# Contratto autorità di uscita RAW + scoperta AutoClose (10/09)

## Perché questa nota

Il primo giro di Research Mode RAW (ADX_RSI/EMA_PULLBACK/FVG_CONT, mattina
del 10/09) non era davvero RAW: ho trovato che 60-64% delle chiusure in
**tutti e 4** i test venivano da `NXS_Prot_CheckMaxHold`/`MaxLossPerPos`,
non dallo SL/TP nativo della strategia. Analizzando più a fondo (richiesto
dall'utente prima di rilanciare i test), la causa dominante non era nemmeno
quella ipotizzata — vedi sotto.

## Ricerca globale delle exit authority

Ogni chiusura/modifica di posizione nel codice passa da UNO di questi tre
percorsi primitivi (verificato via ricerca globale, nessun `PositionClose`/
`OrderSend` di chiusura esiste fuori da questi tre):

1. `NXS_DoClose`/`NXS_DoClosePartial`/`NXS_DoModify` (`NXS_Globals.mqh`) — il
   percorso "standard", usato dal coordinatore posizioni (`NXS_PM_ApplyCycle`)
   e da due punti diretti in `NXS_Execution.mqh`.
2. `NXS_Prot_ClosePositionWithReason` (`NXS_Protections.mqh`) — un
   `OrderSend` **completamente separato e diretto**, non passa dal
   coordinatore. Tagga sempre il commento della deal con un codice
   `NXS:XXX` — è la fonte di ogni tag che si vede nei report.
3. `_nxs_ruin_flatten` (`NXS_Risk.mqh`) — chiama `NXS_DoClose` direttamente,
   **nessun commento**, terzo percorso indipendente dai primi due.

### Tabella completa

| Module | Function | Close/Modify | Active in RAW (10/09, dopo il fix)? | Active in RECIPE? | Active in LIVE? |
|---|---|---|---|---|---|
| NXS_Protections.mqh | `NXS_Prot_CheckESL` → FlattenAll | CLOSE ALL | Opt-in (`InpResearchUseESL`, default OFF) | Opt-in, stesso flag | Sì (`InpUseESL`, default true) |
| NXS_Protections.mqh | `NXS_Prot_CheckMaxTotalDD` → FlattenAll | CLOSE ALL | Opt-in (`InpResearchUseTotalDD`, default OFF) | Opt-in, stesso flag | Sì (`InpUseMaxTotalDD`) |
| NXS_Protections.mqh | `NXS_Prot_CheckDPT` → FlattenAll | CLOSE ALL | Opt-in (`InpResearchUseDPT`, default OFF, **nuovo**) | Opt-in, stesso flag | Sì (`InpUseDPT`, default false) |
| NXS_Protections.mqh | `NXS_Prot_CheckMaxHold` → ClosePositionWithReason | CLOSE per-posizione | **NO, sempre** (nuovo gate) | **NO, sempre** | Sì (`InpUseMaxHold`, default true) |
| NXS_Protections.mqh | `NXS_Prot_CheckMaxLossPerPos` → ClosePositionWithReason | CLOSE per-posizione | **NO, sempre** (nuovo gate) | **NO, sempre** | Sì (`InpUseMaxLossPos`, default true) |
| NXS_Protections.mqh | `NXS_Prot_CheckAutoClose` → FlattenAll | CLOSE ALL | **NO, sempre** (nuovo gate) | **NO, sempre** | Sì (`InpUseAutoClose`, default true) — **vedi scoperta sotto** |
| NXS_Risk.mqh | `_nxs_ruin_flatten` via `NXS_Ruin_OnTick` | CLOSE ALL, nessun tag | Opt-in (`InpResearchUseRuin`, default OFF, **nuovo**) | Opt-in, stesso flag | Sì (`InpRuinEnable` — **plain bool, non input**, sempre true a meno di ricompilare) |
| NXS_Execution.mqh | `NXS_SmartCloseOppositeIfBetter` (CLOSE_REVERSE) | CLOSE diretto | **NO, sempre** (nuovo gate) | **NO, sempre** | Sì (`InpEnableCloseReverse` — **plain bool, non input**, sempre true) |
| NXS_Management.mqh | `NXS_ManageFixedBE` → PM (FIXED_BE) | MODIFY | NO (`InpUseFixedBE` irrilevante, funzione mai chiamata) | NO | Sì (`InpUseFixedBE`, default false) |
| NXS_Management.mqh | `NXS_ManageBreakevenAndTrail` → PM (PROFILE_BREAKEVEN/PROFILE_TRAIL) | MODIFY | NO (funzione mai chiamata) | **Sì** (questo è il punto di RECIPE) | Sì |
| NXS_Management.mqh | `NXS_ManageBreakevenAndTrail` → PM (CLASSIC_TIME_STOP) | CLOSE per-posizione | **NO, sempre** (nuovo gate interno alla funzione) | **NO, sempre** | Sì |
| NXS_Management.mqh | `NXS_ManageBreakevenAndTrail` → PM (GLOBAL_BREAKEVEN/CLASSIC_TRAIL) | MODIFY | NO (funzione mai chiamata) | Sì se la strategia non ha profilo risolto (raro nei nostri test) | Sì |
| NXS_TrailingATR.mqh | `NXS_TrailATR` → PM (ATR_TRAILING) | MODIFY | NO | NO | Sì (`InpUseAtrTrail`, default true) |
| NXS_SplitTrade.mqh | `NXS_ManageSplit`/`FixedPipPartial`/`VolumePartial` → PM | PARTIAL | NO | NO (nessun meccanismo "Split è nella ricetta" ancora implementato — vedi nota sotto) | Sì |
| NXS_PipSequence.mqh | `NXS_ManagePipSequence` → PM (PIPSEQ_STAGE1/2) | MODIFY+PARTIAL | NO | NO | Sì (`InpUsePipSeq`, default false) |
| NXS_SLReclaim.mqh | `NXS_ManageSLReclaim` → nuova apertura (non chiude una esistente) | N/A (riapre) | NO | NO | Sì (`InpUseSLReclaim`, default false) |
| NXS_ProfitReclaim.mqh | `NXS_ManageProfitReclaim` → PM (PROFITRECLAIM) | CLOSE (poi riapre) | NO | NO | Sì (`InpUseProfitReclaim`, default false) |
| NXS_InstManage.mqh | `NXS_InstManage_OnTick` (INST_TIME_STOP + modify) | CLOSE+MODIFY | NO (`InpUseInstitutionalCore` bloccato fatal in preflight Research) | NO | Sì se `InpUseInstitutionalCore=true` (default false) |
| NXS_WeeklyExpManage.mqh | `NXS_WeeklyExpManage` → PM (WEXP_BE/WEXP_TRAIL) | MODIFY | Tecnicamente chiamata sempre, ma scoped a WEEKLY_EXP — irrilevante per le 4 strategie testate | Idem | Sì |
| NXS_WebBridge.mqh | comandi dashboard remoti (`close`/`close_partial`/`flatten_all`) | CLOSE/PARTIAL | Inerte in Tester (dietro `MQL_TESTER`/rete) | Idem | Sì (live only) |

**Non toccati** (per esplicita richiesta): hard stop broker (SL/TP nativi
sempre inviati all'ordine), broker preflight, margin safety, state
integrity (`NXS_State_ReconcileBroker`).

## Scoperta: non era MaxHold, era AutoClose

Controllando l'orario esatto delle chiusure "NXS:TIME" nel primo giro RAW,
**tutte** cadevano alla stessa identica ora del giorno (23:43 circa, con
variazione di 1-3 secondi) — non a durate diverse come farebbe MaxHold
(che dipende da quando ciascuna posizione è stata aperta). Questo è il
comportamento di `NXS_Prot_CheckAutoClose()` (flatten prima della chiusura
di sessione giornaliera), che **riusava lo stesso tag `NXS:TIME` di
MaxHold** — indistinguibili a posteriori dal solo commento della deal.
Corretto: AutoClose ora usa `NXS:AUTOCLOSE`, tag proprio.

Effetto pratico: ADX_RSI/EMA_PULLBACK/FVG_CONT (pensate per durare più
barre H4/D1) venivano flattenate OGNI SERA, indipendentemente dal loro
stop/target nativo — poi, se la condizione STATE del trigger era ancora
vera il giorno dopo, si riapriva una posizione quasi identica. Questo
gonfiava il conteggio trade (5x per ADX_RSI) molto più di quanto MaxHold da
solo avrebbe fatto.

## Fix applicato (commit separato dal futuro fix Max Total DD)

- `InpResearchExitMode` (enum RAW=0/RECIPE=1) sostituisce il vecchio bool
  `InpResearchUseProfileExit`.
- MaxHold, MaxLossPerPos, AutoClose, Close&Reverse: disattivati SEMPRE in
  Research Mode (RAW e RECIPE), indipendentemente dal `.set` — nessuno dei
  quattro è "parte della ricetta dichiarata" di una strategia.
- ESL/Total DD/DPT/Ruin: layer separato, opt-in esplicito, mai riattivato
  implicitamente da RECIPE (nuovi `InpResearchUseDPT`/`InpResearchUseRuin`).
- Telemetria `[RESEARCH][EXIT]` ora include `position=`/`exit_authority=`;
  `[RESEARCH][INVARIANT_FAIL]` se in RAW compare un'autorità diversa da
  BROKER_SL/BROKER_TP/TESTER_END.

## Collegamenti
[[MOC - Trading]]
[[Verifica Protezione Max Total DD, Zero Trigger Nonostante DD 22.83% (10-09)]]
