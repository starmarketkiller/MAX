---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, amd-cont, ldn-reversal, mql5, ricerca-da-zero, rifiutata, bug-scoperto]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — AMD_CONT e LDN_REVERSAL live: segnali reali testati da zero e disattivati (25/08)

## Perché

Continuazione della verifica strategia-per-strategia richiesta
dall'utente. Come TURTLE_SOUP, entrambe usano stop nativi e dipendono
dalla state machine `NXS_GetAMD()` (`NXS_AMDModel.mqh`) e/o
`NXS_DetectSweepExt()`/struttura CHOCH (`NXS_MarketAnalysis.mqh`,
`NXS_Structure.mqh`) — mai testate prima con questa disciplina.

## Bug scoperto nella state machine AMD (indipendente dall'esito del test)

`NXS_GetAMD()` viene chiamata ad OGNI TICK dentro `OnTick()`, non una
volta per barra. La fase MANIPULATION incrementa `g_amdBeyondCount` a
ogni chiamata finché il prezzo resta oltre il range — su un simbolo
liquido come XAUUSD (più tick al secondo) la fase MANIPULATION dura
1-2 tick (millisecondi) prima di collassare in
CONTINUATION_DISTRIBUTION. In pratica qualunque strategia che legge
`amd.phase` vede quasi sempre CONTINUATION_DISTRIBUTION dal primo tick
utile dopo la chiusura oltre il range, non dopo 2 chiusure come
suggerisce il commento nel codice. Non è stato corretto in questa
sessione (richiederebbe un gate "solo su nuova barra" su
`NXS_GetAMD()`, che tocca anche AMD_REVERSAL e JUDAS_SWING) — segnalato
qui per una valutazione futura. Il test sotto replica il comportamento
REALE (collasso immediato), coerente con la disciplina "cosa fa
davvero il codice in live", non cosa dovrebbe fare.

## Risultato: mai profittevole, su nessun TF/direzione

`amd_cont_ldn_reversal_live_signal_25-08.py` (ricetta live esatta) +
`amd_cont_ldn_reversal_tf_scan_25-08.py` (TF alternativi):

**AMD_CONT** (fase AMD_CONTINUATION_DISTRIBUTION + retest Asia High/Low
± 0.6×ATR, stop nativo, RR2.4, sessione London+Overlap+NY):

| TF | Direzione | n | PF (m1/m2) | Finestre |
|---|---|---|---|---|
| M30 (live) | simmetrica | 3483 | 0.64 (0.55/0.74) | 1/5 |
| M30 (live) | BUY-only | 1885 | 0.70 (0.54/0.90) | 1/5 |
| M30 (live) | SELL-only | 1598 | 0.58 (0.57/0.59) | 0/5 |
| M15 | simmetrica | 6313 | 0.60 (0.53/0.69) | 0/5 |
| M15 | BUY-only | 3390 | 0.67 (0.52/0.84) | 1/5 |
| H1 | simmetrica | 2091 | 0.67 (0.58/0.78) | 1/5 |
| H1 | BUY-only | 1148 | 0.71 (0.57/0.87) | 1/5 |

**LDN_REVERSAL** (sweep AsiaHigh/PDH/EQH + CHOCH, stop nativo, target
Asia opposto, sessione London+Overlap):

| TF | Direzione | n | PF (m1/m2) | Finestre |
|---|---|---|---|---|
| M15 (live) | simmetrica | 833 | 0.38 (0.38/0.37) | 0/5 |
| M15 (live) | BUY-only | 360 | 0.40 (0.40/0.41) | 0/5 |
| M30 | simmetrica | 353 | 0.53 (0.55/0.52) | 0/5 |
| H1 | simmetrica | 131 | 0.71 (0.66/0.77) | 1/5 |
| H1 | SELL-only | 73 | 0.78 (0.68/0.89) | 0/5 |

Nessuna configurazione (TF o direzione) avvicina il pareggio in modo
robusto. LDN_REVERSAL è particolarmente debole nella sua ricetta live
esatta (M15, PF0.38).

## Verdetto

**Entrambe disattivate**: `InpUseStrat_AMD_Cont = false`,
`InpUseStrat_LdnReversal = false`. Compilato pulito (0 errori, 2
warning pre-esistenti non correlati), sincronizzato su entrambi i
terminali MT5.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - TURTLE_SOUP Live, Segnale Reale Testato e Disattivato (25-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
