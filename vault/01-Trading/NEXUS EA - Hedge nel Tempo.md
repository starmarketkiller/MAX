---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, hedge, correlazione, portafoglio]
created: 2026-07-15
updated: 2026-07-15
---

# Hedge nel tempo tra strategie

Analisi cross-anno (2019-2024, i 6 segmenti affidabili di
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]]) per capire quali strategie
si compensano nel tempo — l'obiettivo non è più "quale strategia è la
migliore" ma "quale **combinazione** dà la curva equity più liscia".

**Aggiornamento 15/07 (segmento 9, 2024-2025)**: la scoperta sotto è stata
scritta prima che arrivasse questo segmento. Il 2024 ha rotto due degli
streak citati (TURTLE_SOUP e CISD, entrambe negative per la prima volta) —
la sezione "scoperta" è stata aggiornata di conseguenza, non riscritta da
zero, per lasciare tracciabile cosa è cambiato.

## Matrice R per strategia × anno

| Strategia | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | Somma | Anni + | Anni - |
|---|---|---|---|---|---|---|---|---|---|
| **BREAKOUT_ACC** | +1.2 | +0.7 | -0.5 | +2.0 | +0.5 | +0.4 | **+4.3** | 5 | 1 |
| **CISD** | 0.0 | 0.0 | +0.7 | +1.9 | +0.9 | -0.3 | **+3.2** | 3 | 1 |
| MALAYSIAN_SNR | +0.3 | +0.4 | -0.4 | +0.1 | 0.0 | +0.3 | +0.7 | 2 | 1 |
| LIQ_SWEEP | +0.2 | -0.2 | -0.0 | +0.3 | +0.1 | -0.2 | +0.2 | 0 | 0 |
| **TURTLE_SOUP** | +2.1 | -1.8 | +4.2 | -0.5 | +3.3 | **-7.2** | **+0.1** | 3 | 3 |
| ORDER_BLOCK | -0.9 | +0.3 | +0.2 | -0.0 | -1.3 | +0.2 | -1.5 | 1 | 2 |
| EMA_PULLBACK | +0.6 | -2.1 | -3.1 | +2.4 | +0.8 | -4.1 | -5.5 | 3 | 3 |
| FVG_CONT | -5.7 | -1.1 | +1.9 | +1.9 | +0.7 | -7.0 | -9.3 | 3 | 3 |
| OB_MIT | -0.5 | -1.7 | +1.1 | -0.1 | -3.3 | +0.4 | -4.1 | 2 | 3 |
| TSI | -2.3 | -2.1 | -1.3 | -1.2 | +1.1 | -2.1 | -7.9 | 1 | 5 |
| BJORGUM | -3.1 | -0.8 | -2.3 | -2.0 | +1.6 | -2.0 | -8.6 | 1 | 5 |
| RSI_DIV | +1.6 | +1.3 | -2.0 | -9.4 | +1.1 | **-10.1** | -17.5 | 3 | 3 |
| ADX_RSI | +0.4 | -3.0 | -3.7 | -4.2 | -3.7 | -1.1 | -15.3 | 1 | 5 |
| MACD | -6.2 | -11.9 | +2.5 | -4.4 | +1.5 | -2.6 | -21.1 | 2 | 4 |
| **SAR** | -10.9 | -14.3 | -1.9 | -1.4 | -0.7 | -5.1 | **-34.3** | **0** | **6** |

## La scoperta (aggiornata col 2024): il nucleo tiene, ma non è più "mai negativo"

**TURTLE_SOUP + BREAKOUT_ACC** erano in controfase in 3 dei primi 5 anni
(quando una perdeva l'altra guadagnava), e per 5 anni il terzetto con CISD non
aveva mai chiuso un anno insieme in negativo di più di -1.1R. **Il 2024 rompe
questo pattern**: TURTLE_SOUP -7.2 e CISD -0.3 sono entrambe negative nello
stesso anno, mentre solo BREAKOUT_ACC regge (+0.4). Il combinato:

| | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | Somma |
|---|---|---|---|---|---|---|---|
| TURTLE_SOUP + BREAKOUT_ACC + CISD | +3.3 | -1.1 | +4.4 | +3.4 | +4.7 | **-7.1** | **+7.6** |

**2 anni negativi su 6** invece di 1, e il secondo (2024) è il peggiore di
tutti (-7.1, contro -1.1 del 2020). Il nucleo resta nettamente il migliore
angolo del portafoglio (+7.6R contro **-118.1R** del portafoglio completo a 20
strategie), ma la frase "non sono mai negative insieme" **non è più vera** —
va corretta a "raramente, e quando succede può essere severo quanto un anno
buono". BREAKOUT_ACC è l'unica delle tre a non aver mai chiuso un anno in
territorio chiaramente negativo (peggior anno: -0.5).

> **Ipotesi rivista**: BREAKOUT_ACC sembra la componente più stabile del
> nucleo; TURTLE_SOUP e CISD aggiungono rendimento ma anche più varianza di
> quanto stimato coi primi 5 anni. Un profilo che pesa BREAKOUT_ACC come base
> e TURTLE_SOUP/CISD come satelliti a rischio ridotto (non paritario) potrebbe
> essere più robusto della versione "pesa tutte e tre allo stesso modo"
> proposta prima del segmento 9. Da testare, non ancora confermato.

## Chi non si è mai coperto — priorità di intervento

- **SAR**: 0 anni positivi su 6, ora ancora più netto. Non è "una strategia
  che va male in certi regimi", è strutturalmente rotta in ogni condizione di
  mercato osservata finora. Non è un candidato per l'hedge, è un candidato per
  lo spegnimento o la riscrittura da zero della logica di trigger.
- **MACD**: 2/6 positivi ma con due anni catastrofici (-6.2, -11.9) che
  dominano — instabile, non solo "in perdita".
- **RSI_DIV**: sale in questa lista col segmento 9 — il 2024 (-10.1) è il suo
  anno peggiore in assoluto, peggio del 2022. 3/6 anni positivi ma i 3
  negativi sono sempre più gravi dei positivi.
- **ADX_RSI**: 1/6 positivo, e quell'unico anno (2019) è marginale (+0.4).

Queste quattro, insieme, sono circa il 75% della perdita totale del
portafoglio — vedi [[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Limiti di questa analisi
- Il calcolo è algebrico (somma di R per strategia), non simula l'interazione
  reale (margine condiviso, `InpMaxConcurrent`, corsie hedge) tra strategie
  attive insieme — è un'ipotesi di prioritizzazione, non una prova finale.
- Il campione di CISD/BREAKOUT_ACC resta piccolo (15-73 trade in 5 anni,
  aggiornare col conteggio 2024) — sotto la soglia dei ~15/anno per essere
  pienamente affidabile per singolo anno (vedi [[NEXUS EA - Principi]] #4).
- **Lezione diretta di questo aggiornamento**: anche 5 anni di dati (non solo
  3 mesi) possono nascondere un singolo anno che ribalta la conclusione.
  Aspettarsi che anche il segmento 10 possa spostare ancora qualche numero.
- Servirebbe un backtest isolato solo su questo terzetto per confermare che
  il combinato regge anche eseguito realmente, non solo sommato a tavolino.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[MOC - Strategie]] · [[NEXUS EA - Principi]]
