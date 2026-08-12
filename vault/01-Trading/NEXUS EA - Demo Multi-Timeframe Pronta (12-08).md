---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, demo, multi-timeframe]
created: 2026-08-12
updated: 2026-08-12
---

# Demo multi-timeframe — stato e checklist (12/08)

Richiesta dell'utente: moltiplicatore da streak spento per ora, testare
in demo su tutti i timeframe.

## Moltiplicatore da streak: già spento

`InpUseLossStreakScaling = false` è il default in `NXS_Inputs.mqh` —
nessuna modifica necessaria. Va acceso solo esplicitamente, dopo aver
osservato il comportamento in demo per un ciclo.

## Multi-timeframe: è già il comportamento di default, non serve un .set

Verificato leggendo la catena reale (non presunta) di gate in MQL5:

1. `InpUseStrategyProfiles = true` (default) attiva sia i profili
   SL/TP/BE/rischio per-strategia SIA il TF dedicato per-strategia
   (`NXS_Profile_TF`) — ogni strategia cerca il suo trigger sul SUO
   timeframe naturale, non su un unico TF globale.
2. `NXS_Profile_Enabled()` è il gate che decide chi può APRIRE davvero
   (in `NXS_Execution.mqh`: `if(InpUseStrategyProfiles &&
   !NXS_Profile_Enabled(sig.stratName)) return OPEN_FAIL_PREFLIGHT;`) —
   elenca esattamente le 16 del nucleo. Le altre generano comunque un
   segnale "grezzo" (i toggle `InpStrat_*` classici sono quasi tutti
   `true` di default) ma vengono sempre bloccate qui, quindi non aprono.
3. Tutti i toggle individuali (`InpStrat_ADX_RSI`, `InpStrat_MACD`,
   `InpStrat_SAR`, `InpStrat_TSI`, `InpStrat_LIQ_SWEEP`,
   `InpStrat_FVG_CONT`, `InpStrat_BREAKOUT_ACC`, `InpStrat_LONDON_BO`,
   `InpStrat_EMA_PULLBACK`, `InpStrat_TurtleSoup`, `InpStrat_FVG_Mit`,
   `InpUseStrat_AMD_Cont`, `InpUseStrat_LdnReversal`,
   `InpStrat_AMD_Reversal`, `InpUseStrat_CRT`) sono già `true` di default.

**Conclusione**: un compile pulito con gli input di default, attaccato
al grafico XAUUSD, fa già esattamente quello che l'utente ha chiesto —
15 strategie (vedi sotto) attive simultaneamente, ognuna sul proprio TF
(15m → 1d), rischio a 5 fasce, nessun martingale.

## Scoperta collaterale: THREE_BAR_DELIVERY_BREAK non esiste in MQL5

`NXS_Profile_Enabled()` elenca 16 nomi, ma cercando
`NXS_Strat_ThreeBar*`/`Delivery` in tutto `NEXUS_EA_v2.mq5` non c'è
nessuna implementazione — la strategia esiste solo lato Python
(`backtest.py`), non ha mai avuto una controparte MQL5. Il suo profilo
in `NXS_Profile_Get`/`NXS_Profile_Risk` è quindi inerte oggi: **il
nucleo realmente tradabile in demo è di 15 strategie, non 16.** Non
blocca nulla (le altre 15 funzionano), ma è un gap da colmare se si
vuole davvero le 16 previste — non affrontato qui, fuori scope di
questa richiesta.

## Le 15 strategie del nucleo demo, per timeframe

| TF | Strategie |
|---|---|
| 15m | LDN_REVERSAL, AMD_REVERSAL |
| 30m | AMD_CONT, CRT |
| 1h | TURTLE_SOUP, EMA_PULLBACK |
| 4h | SAR, MACD, FVG_CONT, FVG_MIT, LONDON_BO, THREE_BAR_DELIVERY_BREAK¹ |
| 1d | TSI, ADX_RSI, BREAKOUT_ACC, LIQ_SWEEP |

¹ presente nel profilo ma non tradabile (vedi sopra).

## Checklist prima di andare in demo

Niente di quanto scritto in questa sessione remota è stato compilato o
eseguito (nessun accesso a MT5/MetaEditor qui). Prima di attaccare l'EA
a un conto demo:

1. **Compilare in MetaEditor** — `NEXUS_EA_v2.mq5`, zero errori/warning
   nuovi. Il modulo `NXS_StreakRisk.mqh` deve essere incluso PRIMA di
   `NXS_Risk.mqh` (ordine già sistemato nel sorgente, verificare che la
   compilazione non lo contraddica).
2. **Storico**: caricare abbastanza storico XAUUSD nel terminal per
   coprire tutti i TF usati (1d compreso, per ADX_RSI/TSI/BREAKOUT_ACC/
   LIQ_SWEEP che hanno bisogno di indicatori "caldi").
3. **Osservare i log all'avvio**: `[NEXUS SRISK]` non deve MAI comparire
   (martingale spento) — se compare, `InpUseLossStreakScaling` non è
   false come atteso.
4. **Verificare il floating drawdown di CRT** in particolare (è la
   strategia con la riserva di rischio nota più alta) — non solo il
   drawdown a trade chiuso.
5. **Controllare il lotto minimo sul conto demo**: se il demo è
   impostato con un saldo realistico (~200-300€), verificare che
   `InpMaxRiskAtMinLotPct=8` produca lotti sensati e non lotti sempre
   al minimo assoluto per ogni strategia.

## File di convenienza
`MQL5/Demo/NEXUS_Demo_MultiTF_12-08.set` — non cambia nulla rispetto ai
default compilati, rende solo esplicita/riproducibile la configurazione
per chi carica il file invece di fidarsi a memoria dei default.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Rischio a Livelli e Moltiplicatore da Streak (12-08)]]
