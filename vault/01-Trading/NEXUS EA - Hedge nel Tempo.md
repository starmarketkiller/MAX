---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, hedge, correlazione, portafoglio]
created: 2026-07-15
updated: 2026-07-15
---

# Hedge nel tempo tra strategie

Analisi cross-anno (2019-2023, i 5 segmenti affidabili di
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]]) per capire quali strategie
si compensano nel tempo — l'obiettivo non è più "quale strategia è la
migliore" ma "quale **combinazione** dà la curva equity più liscia".

## Matrice R per strategia × anno

| Strategia | 2019 | 2020 | 2021 | 2022 | 2023 | Somma | Anni + | Anni - |
|---|---|---|---|---|---|---|---|---|
| **TURTLE_SOUP** | +2.1 | -1.8 | +4.2 | -0.5 | +3.3 | **+7.3** | 3 | 2 |
| **BREAKOUT_ACC** | +1.2 | +0.7 | -0.5 | +2.0 | +0.5 | **+3.9** | 4 | 1 |
| **CISD** | 0.0 | 0.0 | +0.7 | +1.9 | +0.9 | **+3.5** | 3 | 0 |
| LIQ_SWEEP | +0.2 | -0.2 | -0.0 | +0.3 | +0.1 | +0.4 | 0 | 0 |
| MALAYSIAN_SNR | +0.3 | +0.4 | -0.4 | +0.1 | 0.0 | +0.4 | 1 | 1 |
| EMA_PULLBACK | +0.6 | -2.1 | -3.1 | +2.4 | +0.8 | -1.4 | 3 | 2 |
| ORDER_BLOCK | -0.9 | +0.3 | +0.2 | -0.0 | -1.3 | -1.7 | 0 | 2 |
| FVG_CONT | -5.7 | -1.1 | +1.9 | +1.9 | +0.7 | -2.3 | 3 | 2 |
| OB_MIT | -0.5 | -1.7 | +1.1 | -0.1 | -3.3 | -4.5 | 1 | 3 |
| TSI | -2.3 | -2.1 | -1.3 | -1.2 | +1.1 | -5.8 | 1 | 4 |
| BJORGUM | -3.1 | -0.8 | -2.3 | -2.0 | +1.6 | -6.6 | 1 | 4 |
| RSI_DIV | +1.6 | +1.3 | -2.0 | -9.4 | +1.1 | -7.4 | 3 | 2 |
| ADX_RSI | +0.4 | -3.0 | -3.7 | -4.2 | -3.7 | -14.2 | 1 | 4 |
| MACD | -6.2 | -11.9 | +2.5 | -4.4 | +1.5 | -18.5 | 2 | 3 |
| **SAR** | -10.9 | -14.3 | -1.9 | -1.4 | -0.7 | **-29.2** | **0** | **5** |

## La scoperta: un nucleo di 3 strategie che si coprono a vicenda

**TURTLE_SOUP + BREAKOUT_ACC** sono in controfase in 3 dei 5 anni: quando una
perde (2020, 2021, 2022) l'altra guadagna, e nei 2 anni restanti (2019, 2023)
sono entrambe positive — **non sono mai negative insieme**. Aggiungendo CISD
(mai negativa, 0/5) il combinato è:

| | 2019 | 2020 | 2021 | 2022 | 2023 | Somma |
|---|---|---|---|---|---|---|
| TURTLE_SOUP + BREAKOUT_ACC + CISD | +3.3 | **-1.1** | +4.4 | +3.4 | +4.7 | **+14.7** |

**Un solo anno debolmente negativo (2020: -1.1) su 5**, contro un portafoglio
completo a 20 strategie che nello stesso periodo fa **-78.4R**. Questo è
l'hedge nel tempo che cercavi: non serve una strategia che vince sempre, serve
un piccolo gruppo che non perde mai *nello stesso anno*.

> **Ipotesi da testare**: un profilo che pesa fortemente
> TURTLE_SOUP/BREAKOUT_ACC/CISD (via `NXS_Profile_RiskPct` o
> `InpStrategySelector` isolato) e riduce al minimo o spegne SAR/MACD/ADX_RSI
> finché non sono fixate, dovrebbe avvicinarsi molto di più a un equity curve
> liscio. Da validare con un backtest dedicato (non dedotto solo dalla somma
> algebrica — l'interazione hedge/margine/corsie tra strategie contemporanee
> può cambiare il risultato).

## Chi non si è mai coperto — priorità di intervento

- **SAR**: 0 anni positivi su 5. Non è "una strategia che va male in certi
  regimi", è strutturalmente rotta in ogni condizione di mercato osservata.
  Non è un candidato per l'hedge, è un candidato per lo spegnimento o la
  riscrittura da zero della logica di trigger.
- **ADX_RSI**: 1/5 positivo, e quell'unico anno (2019) è marginale (+0.4).
- **MACD**: 2/5 positivi ma con due anni catastrofici (-6.2, -11.9) che
  dominano — instabile, non solo "in perdita".

Queste tre, insieme, sono l'80% della perdita totale del portafoglio — vedi
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Limiti di questa analisi
- Il calcolo è algebrico (somma di R per strategia), non simula l'interazione
  reale (margine condiviso, `InpMaxConcurrent`, corsie hedge) tra strategie
  attive insieme — è un'ipotesi di prioritizzazione, non una prova finale.
  Il PF di CISD/BREAKOUT_ACC su campioni ancora piccoli (15-73 trade in 5
  anni) — meglio di 3 mesi ma ancora sotto la soglia dei ~15/anno per essere
  pienamente affidabile per singolo anno (vedi [[NEXUS EA - Principi]] #4).
- Servirebbe un backtest isolato solo su questo terzetto per confermare che
  il combinato regge anche eseguito realmente, non solo sommato a tavolino.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[MOC - Strategie]] · [[NEXUS EA - Principi]]
