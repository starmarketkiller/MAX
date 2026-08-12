---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, rischio, sizing, mql5, conto-piccolo]
created: 2026-08-12
updated: 2026-08-12
---

# Rischio a livelli per-strategia + moltiplicatore da perdite consecutive (12/08)

Richiesta esplicita dell'utente: conto di partenza ~200-300 EUR, 0.5% flat
è troppo poco per crescere in tempi ragionevoli (e sotto il lotto minimo
XAUUSD quasi sempre — l'EA di fatto non tradava). Vuole rischiare di più
(fino al 5%) sulle strategie che vanno bene, scalare giù su quelle così
così, e un moltiplicatore che aumenti il rischio dopo una serie di perdite
per recuperare più in fretta.

## Il problema di fondo: il floor sul lotto minimo

Su un conto piccolo, il lotto minimo (0.01 XAUUSD) rischia quasi sempre più
del budget nominale a rischio% basso. `InpMaxRiskAtMinLotPct` (già scritto
in sessione precedente, mai verificato) risolve questo: se il lotto minimo
supera il budget calcolato, viene comunque eseguito ma solo se il rischio
effettivo resta sotto un tetto esplicito (mai un clamp silenzioso — sempre
loggato come `RISCHIO MAGGIORATO`). **Alzato da 0.0 (disattivo) a 8.0** —
prima di questo, aumentare i rischio% per-strategia non avrebbe risolto
nulla su un conto così piccolo, il lotto minimo avrebbe comunque bloccato
la maggior parte dei segnali.

## Il moltiplicatore da perdite consecutive: un martingale, dichiarato come tale

Prima di costruirlo, verificato col numero: con RR ampi come in questo EA
(TP spesso 3-4.5×ATR contro SL 1-1.5×ATR), il win rate è spesso 35-45% —
una serie di 3-4 perdite consecutive non è un evento raro, è normale
amministrazione. Un moltiplicatore senza tetto applicato lì è
strutturalmente un martingale: non "se" spazza un conto piccolo, ma
"quando". L'utente ha confermato di volerlo comunque (recupero più
aggressivo dopo le perdite, non solo dentro lo stesso trade), a patto di
guardrail espliciti concordati insieme:

- **Scatta dopo 3 perdite consecutive** sulla stessa strategia
  (`InpSRisk_LossesToScale`), ripetuto ogni 3 (alla 6a, 9a... fino al
  tetto).
- **+30% per step** (`InpSRisk_ScaleStep=1.3`), non un raddoppio — un
  martingale puro con step di 3 perdite arriverebbe a 8x il rischio base
  dopo solo 3 serie; con lo step 1.3x servono **9 perdite consecutive
  sulla stessa strategia** per arrivare al tetto.
- **Tetto assoluto 2.0x** (`InpSRisk_MaxMult`) — mai oltre, indipendente da
  quante perdite si accumulano oltre la 9a.
- **Reset alla prima vincita**, non serve tornare a zero perdite.
- **Per-strategia, non globale**: se il mercato va storto per TUTTE le
  strategie insieme (capita, è correlazione non anomalia), non scattano
  tutti i moltiplicatori insieme a sommarsi nel cap aggregato.
- **Resta sempre dentro** `InpMaxRiskAtMinLotPct` e `InpMaxAggregateRiskPct`
  — il moltiplicatore non può mai bypassarli, sono il vero limite di
  sopravvivenza del conto.
- **Default OFF** (`InpUseLossStreakScaling=false`) — l'utente lo abilita
  esplicitamente sul proprio conto live, non un comportamento silenzioso
  ereditato da chiunque altro usi questo EA.

### Scoperta durante la costruzione: due meccanismi esistenti fanno l'OPPOSTO

Nel codice esistevano già due leve di sizing basate su streak, entrambe OFF
di default:
- `NXS_AntiBleedMultiplier` (`InpUseAntiBleed`) — **riduce** il rischio
  dopo 1/2/3+ perdite consecutive (0.7x/0.7x/0.4x), un meccanismo
  difensivo.
- `g_streakLotMult` (`InpUseStreakSizing`) — sale dopo N **vittorie**
  consecutive, scende dopo N perdite — "cavalca la mano calda".

Il nuovo modulo (`NXS_StreakRisk.mqh`) fa l'esatto contrario per
costruzione. Non abilitare i due gruppi insieme sulla stessa strategia —
si moltiplicano in `NXS_CalcLotRisk` e l'effetto netto non sarebbe
auditabile. Commentato esplicitamente nel codice per chi la userà in
futuro.

### Implementazione

- **`NXS_StreakRisk.mqh`** (nuovo file): registro per-nome (stesso pattern
  di `NXS_StratStats.mqh`), `consecLosses` + `mult` per strategia,
  `NXS_StreakRisk_Mult(name)` (letto in sizing) e
  `NXS_StreakRisk_OnTradeClosed(name, pnl)` (aggiornato alla chiusura).
- **`NXS_CalcLotRisk`**: nuovo parametro opzionale `stratName` (default
  `""`, retrocompatibile — `NXS_CalcLot` globale non lo passa e resta
  invariato), applica `NXS_StreakRisk_Mult` allo stesso punto di
  AntiBleed/AccountLotMult.
- **`NXS_Execution.mqh`**: `NXS_OpenTrade` passa `sig.stratName` a
  `NXS_CalcLotRisk`.
- **`NEXUS_EA_v2.mq5`**: `NXS_StreakRisk_OnTradeClosed` agganciata
  esattamente allo stesso punto di `NXS_OnTradeClosed`
  (`NXS_EA_OnLogicalClose`) — una volta per trade LOGICO (aggregato), non
  per deal parziale, stessa disciplina già in uso per anti-revenge/
  anti-bleed.
- **`NXS_State.mqh`**: persistenza attraverso i riavvii (schema v4→v5) —
  senza, un riavvio a metà serie di perdite azzererebbe il moltiplicatore
  in silenzio.
- **Percorso NON toccato**: il path "NXR" (`NXS_ReusePerformancePack.mqh`,
  `InpNXR_Enable=false` di default) calcola il lotto in modo indipendente
  (`NXR_CalcRawVolume`, usa il rischio% GLOBALE non quello per-strategia) e
  non passa attraverso `NXS_CalcLotRisk` — è dormiente oggi, ma se in
  futuro venisse abilitato non erediterebbe né i tier per-strategia né
  questo moltiplicatore senza un cablaggio separato.
- **Percorso NON toccato**: le gambe di grid/pyramid (`NXS_GridRecovery.mqh`/
  `NXS_Pyramiding.mqh`) usano `NXS_CalcLot` (globale, nessun nome) — fuori
  scope, sono comunque disattivate di default (`InpEnableGrid=false`) e
  appartengono al progetto "Fase C" separato (vedi [[NEXUS EA - Fase C Recovery Baseline e Rischio Flottante (11-08)]]).

## Rischio % per-strategia: 5 fasce, non più flat

Riscritta `NXS_Profile_Risk()` per le 16 strategie del nucleo attivo
(demo/live), incrociando **due evidenze indipendenti** — non una sola:
1. PF reale su MT5 dove esiste una storia (la più affidabile: comprende
   slippage/spread/esecuzione vera, non un backtest).
2. OOS + walk-forward Python sullo storico Dukascopy ampio 2019-2026
   (census e giro veloce dell'11/08).

Le red flag di esecuzione reale note (MACD, FVG_CONT — CRITICA su MT5 pur
con backtest Python forte) **sovrascrivono** un buon numero Python:
eseguire male dal vivo conta più di un backtest pulito.

| Tier | % | Strategie | Perché |
|---|---|---|---|
| **S** | 5.0 | EMA_PULLBACK, SAR, TURTLE_SOUP | Doppia conferma forte (reale MT5 positivo E Python WF pulito), nessuna red flag. TURTLE_SOUP: il PF2.04 reale è con la ricetta ufficiale attiva (SL1.0/TP4.5/HTF), coerente col Python (0.96→1.15 con la stessa ricetta) |
| **A** | 2.5 | LONDON_BO, AMD_CONT, ADX_RSI, CRT | Terreno vergine su MT5 ma Python solido/campione ampio, o singola conferma con riserva nota. CRT: l'evidenza Python più forte di sessione (WF5/5, ~20k trade) ma nessuna storia reale + riserva strutturale sullo stop (vedi sotto) — tier A non S finché non c'è conferma live col floor |
| **B** | 1.2 | LDN_REVERSAL, AMD_REVERSAL | Terreno vergine, Python più modesto o meno pulito (WF 3/5) |
| **C** | 0.5 | MACD, FVG_CONT, BREAKOUT_ACC, LIQ_SWEEP, THREE_BAR_DELIVERY_BREAK, FVG_MIT | Red flag di esecuzione reale nota, o debolezza Python conclamata (DEBOLE/IS negativo/WF incoerente) — vive ma a size minima |
| **D** | 0.3 | TSI | Problema aperto confermato, nessuna soluzione trovata dopo 2 tentativi, unica del nucleo sotto pareggio in OOS |

Rapporto tra tier S e tier D: ~16.7x — riflette la richiesta di
differenziare parecchio, non una scala piatta. Le altre ~20 strategie
fuori dal nucleo attivo restano ai valori precedenti (fuori scope, nessuna
nuova evidenza raccolta su quelle in questo giro) — con un'eccezione:
**BJORGUM corretta da 2.5% a 0.4%**, il commento precedente ("PF 1.90
reale") era stale, superato dalla chiusura negativa dell'11/08 (-8.6R
reali, 5/6 anni negativi — trovato per caso rileggendo il file, BJORGUM
non è comunque nel nucleo attivo oggi).

### Il floor sullo stop di CRT

Tier A alza il rischio nominale di CRT rispetto a prima (0.6%→2.5%) — ma
CRT ha una riserva strutturale nota (vedi [[NEXUS EA - Fase C Recovery Baseline e Rischio Flottante (11-08)]]):
lo stop è ancorato al wick della candela di sweep, non a un multiplo ATR.
Quando il wick è minimo il rischio flottante durante il trade può
esplodere (107% osservato in una finestra) prima che il trade chiuda
correttamente a -1R. Aggiunto `InpCRT_MinStopATR` (default 0.3): se la
distanza wick-based scende sotto 0.3×ATR, lo stop viene esteso (mai
stretto) fino al floor. Allarga solo il rischio nominale dichiarato per
quel trade, non tocca la logica del target.

## Cap di rischio aggregato ricalibrato

`InpMaxAggregateRiskPct`: **15.0 → 25.0**. Con i tier ora fino al 5%
(prima 3% massimo), 15% avrebbe bloccato l'operatività normale già con 3
strategie tier S aperte insieme. Il caso limite teorico — tutte e 16 le
strategie del nucleo aperte insieme sulla stessa barra — sommerebbe
~30.7% (3×5.0 + 4×2.5 + 2×1.2 + 6×0.5 + 1×0.3): 25% resta un freno reale
anche in quello scenario estremo, non un cap simbolico.

## Cosa NON è stato fatto (serve verifica su MT5, non fattibile da qui)

Questa sessione è remota, Linux, senza MT5 — tutto il codice sopra è
scritto ma **non compilato né testato dal vivo**. Prima di usarlo su un
conto reale:
1. Compilare in MetaEditor (nessuna riga di `MQL5/` risulta mai compilata
   in questa sessione, stesso avvertimento di ogni altro TODO "agente
   desktop").
2. Verificare `InpUseLossStreakScaling=false` (default) non cambia nulla
   rispetto a prima — poi abilitarlo esplicitamente e osservare il log
   `[NEXUS SRISK]` su un conto demo per qualche settimana prima del conto
   reale da 200-300 EUR.
3. Verificare `InpMaxRiskAtMinLotPct=8.0` produce `RISCHIO MAGGIORATO` nel
   Journal quando atteso, non silenziosamente.
4. Verificare il floor sullo stop di CRT (`InpCRT_MinStopATR=0.3`) non
   altera i trade dove il wick era già sopra il floor (deve essere un
   no-op nella maggioranza dei casi).

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Fase C Recovery Baseline e Rischio Flottante (11-08)]] ·
[[NEXUS EA - Config Demo 15 Strategie (10-08)]] ·
[[TODO - Agente Desktop (validazione MT5 post-Dukascopy, 09-08)]]
