---
type: reference
domain: trading
status: active
tags: [trading, nexus-ea, tabella-master, riferimento, baseline]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Tabella master delle strategie verificate (24/08)

Documento di riferimento unico: consolida tutte le configurazioni
"vincenti" trovate/riverificate il 24/08, sparse fino ad ora su ~15 note
separate. Ogni riga è la MIGLIOR configurazione nota per quella
strategia oggi, con la fonte per chi vuole il dettaglio completo. Tutte
le PF sono retail_standard su 4h salvo indicato, con costi scalati sul
prezzo storico. `m1`/`m2` = due metà della storia (o `Fn` = finestra
specifica dove rilevante).

## Nucleo storico (5) — già solidi prima di oggi, ora con floor dove serve

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) | Correlazione | MQL5 |
|---|---|---|---|---|---|---|---|
| SAR | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.21 (1.09/1.33) | Cluster (0.31, alta) | No |
| MACD | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.46 (1.39/1.54) | Cluster (0.30, alta) | No |
| FVG_CONT | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.30 (1.19/1.41) | Cluster (0.26) | No |
| LONDON_BO | 4h | 1.0/4.5 | **D1-align** (no floor) | simmetrica | 1.40 (0.70/2.36*) | Bassa (0.14) | No |
| Z_SCORE_BREAKOUT | 1h | stop M5 strutturale, target 4.0×ATR | ER+floor 0.3 | simmetrica | 1.29 (1.20/1.38) | Bassa (0.14) | **Sì** |

\* LONDON_BO con D1-align ha un divario ampio (0.70/2.36) — migliora
l'aggregato ma non è "pulita" come le altre D1-align; verificare per-data
prima di fidarsene quanto FVG_MIT/OTE_CONT.

## Cluster trend-following (7) — correlati 0.45-0.997 tra loro, non sommare ciecamente in portafoglio

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) | Nota |
|---|---|---|---|---|---|---|
| DONCHIAN_TURTLE | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.30 (1.28/1.32) | **Correlata al 99.7% con DARVAS_BOX** — praticamente la stessa |
| DARVAS_BOX | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.30 (1.24/1.38) | Vedi sopra — tenerne solo una delle due in portafoglio |
| ADX_RSI | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.27 (1.35/1.20) | Non dipende dal rally (m1>m2) |
| SAR_ADX20 | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.21 (1.07/1.36) | Campione enorme (1610) |
| BREAKOUT_ACC | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.17 (1.09/1.26) | |

## Diversificatrici genuine (5) — le più preziose per il portafoglio, bassa/negativa correlazione

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) | Correlazione media |
|---|---|---|---|---|---|---|
| **STRUCT_REACT** | 4h | 2.0/6.0 | ER+floor 0.3 | **BUY-only** | **2.65 (2.82/2.48, 5/5)** | **-0.019 (negativa con SAR/SAR_ADX20 — hedge naturale)** |
| LIQ_SWEEP | 4h | 1.5/6.0 | ER+floor 0.3 | **BUY-only** | 1.73 (1.73/1.73, 5/5) | 0.084 |
| OTE_CONT | 4h | 1.0/6.0 | **D1-align** | simmetrica | 1.83 (1.89/1.77, 5/5) | 0.028 |
| FVG_MIT | 4h | 2.0/6.0 | **D1-align** | simmetrica | 1.48 (1.33/1.64, 5/5) | 0.015 |
| EMA_PULLBACK | 4h **o** D1 | 1.5/4.0 (4h) / 1.5/6.0 (D1) | **D1-align** (4h) / ER+floor0.2 (D1) | simmetrica | 1.42 (1.15/1.74) su 4h, n=241 · **2.53 (2.88/2.23) su D1, n=32** | -0.012 |

EMA_PULLBACK ha due varianti valide con trade-off opposto: 4h+D1-align
(campione ampio, PF più modesto) o D1 nativo (PF eccezionale ma solo 32
trade, troppo pochi per grande fiducia). Usare la versione 4h come
baseline principale, la D1 come conferma/upside.

## Altre solide, correlazione moderata (3)

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) |
|---|---|---|---|---|---|
| MALAYSIAN_SNR_BREAKOUT | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.58 (1.47/1.69) |
| AMD_CONT | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.42 (1.25/1.61) |
| SAR_FLIP | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica | 1.40 (1.21/1.61) |
| FVG_CONT_V2 | 4h | stop nativo precalcolato | ER+floor 0.3 | simmetrica | 1.47 (1.33/1.64) |
| TSI | 4h | 1.0/6.0 | **D1-align** | simmetrica | 1.36 (1.16/1.58) |

## Provvisorie — non ancora piene, riverifica raccomandata prima di fidarsene

| Strategia | TF | SL/TP | Direzione | Retail PF | Perché provvisoria |
|---|---|---|---|---|---|
| TURTLE_SOUP | 4h | stop wick sweep + floor 0.3, target 4.0×ATR | simmetrica | 1.14 (1.04/1.25) | Ribalta 3+ rifiuti precedenti — mai successo prima con nessun altro stop |
| LDN_REVERSAL | 4h | stop strutturale (swing 10 barre), RR 1:3 | simmetrica | 1.28 (1.31/1.25) | Campione sottile (n=31) |

## Rifiutate definitivamente oggi (non riprovare senza nuova ipotesi)

CRT, CRT_MINSTOP_FILTER (costi dominanti confermati anche col floor),
BJORGUM (simmetrica e BUY-only, beta mascherato confermato dalla
diagnosi per-data), RSI_DIV, TSI_EXTREME, FVG_MIT-simmetrica (superata
dalla variante D1-align), OTE_CONT su D1 (morta pre-2024), BOLLINGER
(solo "watch", non promossa), l'intera famiglia sessione/AMD/SCALP_* su
M15/M30 (JUDAS_SWING, SILVER_BULLET*, NY_REVERSAL*, AMD_REVERSAL, PO3,
WEEKLY_EXP, SCALP_BB_FADE/EMA/RANGE_BRK/RSI_SNAP), LIQ_VOID (segnale
identico a FVG_CONT, non conta come strategia in più).

## Bilancio

**19 strategie verificate e pronte** (esclude le 2 provvisorie) + 2
provvisorie = **21 candidate totali**, contro le 4 di partenza di
stamattina. Solo **2 sono in MQL5** (SWING_FALSEBREAK, Z_SCORE_BREAKOUT
— SWING_FALSEBREAK non compare sopra perché già portata ieri, resta
valida come da nota originale). Il problema di allocazione del
portafoglio (correlazione, budget di rischio) resta aperto — vedi
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]].

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]
[[NEXUS EA - Sweep Sistematico Allineamento D1 (24-08)]]
