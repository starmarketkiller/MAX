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
"vincenti" trovate/riverificate il 24/08, sparse su ~17 note separate.
Ogni riga è la MIGLIOR configurazione nota per quella strategia oggi,
con la fonte per chi vuole il dettaglio completo. Tutte le PF sono
retail_standard su 4h salvo indicato, con costi scalati sul prezzo
storico. `m1`/`m2` = due metà della storia.

**Aggiornamento più recente**: split BUY/SELL sistematico (vedi
[[NEXUS EA - Sweep Sistematico BUY-SELL (24-08)]]) — 13 strategie su 14
testate migliorano nettamente passando a BUY-only, verificato con
campioni ampi (60-1471 trade) e finestra più vecchia genuinamente sopra
pareggio (non beta mascherato come i casi bocciati ieri sera).

## Nucleo storico (5)

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) | Correlazione | MQL5 |
|---|---|---|---|---|---|---|---|
| SAR | 4h | 1.5/4.0 | ER+floor 0.3 | **BUY-only** | **1.51 (1.36/1.69)** | Cluster (alta) | No |
| MACD | 4h | 1.5/4.0 | ER+floor 0.3 | simmetrica (BUY-only solo +0.12, non vale la pena) | 1.46 (1.39/1.54) | Cluster (alta) | No |
| FVG_CONT | 4h | 1.5/4.0 | ER+floor 0.3 | **BUY-only** | **1.51 (1.35/1.69)** | Cluster | No |
| LONDON_BO | 4h | 1.0/4.5 | ER (no floor) | **BUY-only** | **1.60 (1.71/1.49)** | Bassa | No |
| Z_SCORE_BREAKOUT | 1h | stop M5 strutturale, target 4.0×ATR | ER+floor 0.3 | simmetrica | 1.29 (1.20/1.38) | Bassa | **Sì** |

## Cluster trend-following (5) — correlati 0.45-0.997 tra loro, non sommare ciecamente

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) | Nota |
|---|---|---|---|---|---|---|
| DONCHIAN_TURTLE | 4h | 1.5/4.0 | ER+floor 0.3 | **BUY-only** | **1.56 (1.47/1.67)** | **Correlata al 99.7% con DARVAS_BOX** — praticamente la stessa |
| DARVAS_BOX | 4h | 1.5/4.0 | ER+floor 0.3 | **BUY-only** | **1.58 (1.44/1.73)** | Vedi sopra — tenerne solo una delle due in portafoglio |
| ADX_RSI | 4h | 1.5/4.0 | ER+floor 0.3 | **BUY-only** | **1.77 (1.92/1.63, n=728)** | Verificato per-data (F0 2020-2024 n=145 PF1.27) — il più solido del cluster |
| SAR_ADX20 | 4h | 1.5/4.0 | ER+floor 0.3 | **BUY-only** | **1.49 (1.35/1.64, n=1000)** | Campione enorme |
| BREAKOUT_ACC | 4h | 1.5/4.0 | ER+floor 0.3 | **BUY-only** | **1.33 (1.19/1.48)** | Miglioramento più modesto del cluster |

## Diversificatrici genuine (5) — le più preziose per il portafoglio, bassa/negativa correlazione

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) | Correlazione media |
|---|---|---|---|---|---|---|
| **STRUCT_REACT** | 4h | 2.0/6.0 | ER+floor 0.3 | **BUY-only** | **2.65 (2.82/2.48, 5/5)** | **-0.019 (negativa con SAR/SAR_ADX20 — hedge naturale)** |
| LIQ_SWEEP | 4h | 1.5/6.0 | ER+floor 0.3 | **BUY-only** | 1.73 (1.73/1.73, 5/5) | 0.084 |
| OTE_CONT | 4h | 1.0/6.0 | **D1-align** | simmetrica (BUY/SELL split non ancora provato) | 1.83 (1.89/1.77, 5/5) | 0.028 |
| FVG_MIT | 4h | 2.0/6.0 | **D1-align** | simmetrica (BUY/SELL split non ancora provato) | 1.48 (1.33/1.64, 5/5) | 0.015 |
| EMA_PULLBACK | 4h **o** D1 | 1.5/4.0 (4h) / 1.5/6.0 (D1) | **D1-align** (4h) / ER+floor0.2 (D1) | simmetrica (BUY/SELL split non ancora provato) | 1.42 (1.15/1.74) su 4h, n=241 · **2.53 (2.88/2.23) su D1, n=32** | -0.012 |

EMA_PULLBACK ha due varianti valide con trade-off opposto: 4h+D1-align
(campione ampio, PF più modesto) o D1 nativo (PF eccezionale ma solo 32
trade). Usare la versione 4h come baseline principale, la D1 come
conferma/upside.

## Altre solide (5)

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) |
|---|---|---|---|---|---|
| TSI | 4h | 1.0/6.0 | ER+floor 0.3 | **BUY-only** | **2.03 (1.97/2.10, n=134)** — il migliore di questo blocco |
| MALAYSIAN_SNR_BREAKOUT | 4h | 1.5/4.0 | ER+floor 0.3 | **BUY-only** | **1.93 (1.83/2.04, n=75)** |
| SAR_FLIP | 4h | 1.5/4.0 | ER+floor 0.3 | **BUY-only** | **1.78 (1.40/2.27, n=76)** |
| FVG_CONT_V2 | 4h | stop nativo precalcolato | ER+floor 0.3 | **BUY-only** | **1.68 (1.34/2.15, n=65)** |
| AMD_CONT | 4h | 1.5/4.0 | ER+floor 0.3 | **BUY-only** | **1.62 (1.26/2.06, n=137)** |

## Provvisorie — riverifica raccomandata prima di fidarsene

| Strategia | TF | SL/TP | Direzione | Retail PF | Perché provvisoria |
|---|---|---|---|---|---|
| TURTLE_SOUP | 4h | stop wick sweep + floor 0.3, target 4.0×ATR | simmetrica | 1.14 (1.04/1.25) | Ribalta 3+ rifiuti precedenti |
| LDN_REVERSAL | 4h | stop strutturale (swing 10 barre), RR 1:3 | simmetrica | 1.28 (1.31/1.25) | Campione sottile (n=31) |

## Rifiutate definitivamente oggi (non riprovare senza nuova ipotesi)

CRT, CRT_MINSTOP_FILTER, BJORGUM (simmetrica e BUY-only, beta mascherato
confermato dalla diagnosi per-data), RSI_DIV, TSI_EXTREME, OTE_CONT su
D1 (morta pre-2024), BOLLINGER (solo "watch"), l'intera famiglia
sessione/AMD/SCALP_* su M15/M30, LIQ_VOID (segnale identico a FVG_CONT).

## Bilancio

**19 strategie verificate e pronte** + 2 provvisorie = **21 candidate
totali**, contro le 4 di partenza di stamattina — 13 di queste ora in
versione BUY-only (migliorate rispetto alla forma simmetrica). Solo
**2 sono in MQL5** (SWING_FALSEBREAK, Z_SCORE_BREAKOUT). Il problema di
allocazione del portafoglio (correlazione, budget di rischio) resta
aperto, ora da riverificare con le config BUY-only aggiornate — vedi
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]].

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]
[[NEXUS EA - Sweep Sistematico Allineamento D1 (24-08)]]
[[NEXUS EA - Sweep Sistematico BUY-SELL (24-08)]]
