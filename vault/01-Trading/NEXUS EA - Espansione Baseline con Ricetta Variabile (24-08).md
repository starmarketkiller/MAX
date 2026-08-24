---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, baseline, sl-tp, stop-nativo, screening]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Espansione baseline con ricetta variabile per strategia (24/08)

## Perché

Richiesta esplicita dell'utente dopo lo screening a ricetta uniforme
(vedi [[NEXUS EA - Screening Catalogo Completo e Confluenze (24-08)]]):
non fermarsi a un solo SL/TP fisso per tutte, non escludere ingredienti.
`baseline_expansion_24-08.py`, tre fasi, tutte con ER≥0.045 + floor ATR
30° percentile (l'ingrediente nuovo di oggi) come base comune:

- **Fase 1**: griglia di 6 combinazioni SL/TP (1.0/3.0, 1.0/4.5, 1.0/6.0,
  1.5/3.0, 1.5/6.0, 2.0/6.0) sulle strategie a stop generico bocciate o
  fragili ieri con il solo 1.5/4.0.
- **Fase 2a**: strategie con stop+target GIÀ precalcolati nel motore
  (CRT/FVG_CONT_V2/FVG_MIT_WINDOW/ORDER_BLOCK_V2/OTE_CONT_V2/
  SILVER_BULLET_V2/SH_BMS_RTO_V2) — il floor ATR non era mai stato
  provato SOPRA il loro stop nativo.
- **Fase 2b**: famiglia sweep (TURTLE_SOUP\*/SH_BMS_RTO/SMS_BMS_RTO\*/
  NY_REVERSAL_CHOCH_WINDOW/IFVG_CHOCH_WINDOW) — stop dal wick dello sweep
  (stesse funzioni del motore reale), target 4.0×ATR, stesso principio.

**Limite dichiarato**: la fase 1 sceglie il MIGLIORE dei 6 SL/TP per
ciascuna strategia (non una media, non un valore fissato a priori) — un
rischio reale di selezione fortunata su un solo giro di griglia, non
ancora un plateau verificato come per Hull Suite/ML SuperTrend. Riportato
comunque `meta1`/`meta2` per ogni candidato, cosi' il rischio è visibile
subito, non nascosto.

## Risultati — 4 candidati forti, 3 borderline, resto confermato debole

### Forti (entrambe le metà positive, campione ≥69 trade)

| Strategia | Config | retail PF (m1/m2) | ECN PF (m1/m2) | n | Note |
|---|---|---|---|---|---|
| **OTE_CONT** | SL1.0/TP6.0, 4h | 1.61 (1.69/1.52) | 1.83 (1.98/1.69, 5/5) | 129 | Il migliore della giornata — il verdetto "fragile" di ieri (con SL1.5/TP4.0) era un problema di SL/TP, non di segnale |
| **FVG_CONT_V2** | stop nativo precalcolato, 4h | 1.47 (1.33/1.64) | 1.73 (1.62/1.85, 5/5) | 69 | Robusta, campione più sottile |
| **TSI** | SL1.0/TP6.0, 4h | 1.25 (1.22/1.28) | 1.44 (1.43/1.45, 5/5) | 271 | Le due metà quasi identiche — molto più solida della TSI "fragile" trovata ieri (SL1.5/TP4.0, m1=0.92) |
| **TURTLE_SOUP** | stop wick sweep + floor, 4h | 1.14 (1.04/1.25) | 1.33 (1.25/1.42) | 271 | **Ribalta 3+ rifiuti precedenti** (17/08: nessuno stop provato l'aveva salvata) — l'ingrediente che mancava era il floor ATR, mai provato prima sopra lo stop nativo. Da riverificare con un secondo test prima di fidarsene del tutto, vista la storia di rifiuti |

### Borderline (una metà appena sopra/sotto pari)

| Strategia | Config | retail PF (m1/m2) | Note |
|---|---|---|---|
| STRUCT_REACT | SL2.0/TP6.0, 4h | 1.07 (1.01/1.12) | Modesta ma genuina, entrambe le metà ≥1 |
| LIQ_SWEEP | SL1.5/TP6.0, 4h (stop generico, non nativo) | 1.07 (1.03/1.11) | Genuina inversione — stop generico largo batte lo stop nativo (sweep) sempre bocciato finora |
| BOLLINGER = RANGE_FADE | SL1.0/TP6.0, 4h | 1.22 (1.00/1.47) | Prima metà esattamente a pareggio — non pulita come le altre |

### Confermate deboli anche con la griglia estesa

BJORGUM, RSI_DIV, FVG_MIT, LDN_REVERSAL (campione troppo sottile e
invertito), TSI_EXTREME, ICHIMOKU-4h (pattern invertito con questo
SL/TP). CRT/CRT_MINSTOP_FILTER **confermate definitivamente rotte**
anche con il floor (retail PF 0.24-0.48 su entrambi i TF) — non è un
problema di filtro di regime, la saga costi-dominanti di CRT resta
irrisolta con ogni ingrediente provato finora. FVG_MIT_WINDOW,
SH_BMS_RTO_V2, TURTLE_SOUP_CHOCH* (pattern invertito), SH_BMS_RTO/
SMS_BMS_RTO*/NY_REVERSAL_CHOCH_WINDOW (campioni troppo sottili per
giudicare).

## Bilancio della giornata: baseline totali trovate

Sommando tutti gli screening di oggi (Parte 1 di ieri + questa
espansione): **13 nuove baseline verificate due-metà-storia** oltre alle
4 già solide (SAR/MACD/FVG_CONT/Z_SCORE_BREAKOUT) e a LONDON_BO:

DONCHIAN_TURTLE, ADX_RSI, MALAYSIAN_SNR_BREAKOUT, DARVAS_BOX, AMD_CONT,
SAR_FLIP, EMA_PULLBACK, SAR_ADX20, BREAKOUT_ACC, OTE_CONT, FVG_CONT_V2,
TSI, TURTLE_SOUP (quest'ultima da riverificare per la storia di rifiuti
precedenti). Nessuna ancora portata in MQL5.

## Prossimi passi aperti

- Nessun plateau-check ancora fatto sulla fase 1 (best-of-6 SL/TP) — a
  differenza di Hull Suite/ML SuperTrend, il rischio di scelta fortunata
  non è stato ancora escluso per OTE_CONT/TSI/STRUCT_REACT/LIQ_SWEEP.
- TURTLE_SOUP merita una riverifica dedicata prima di fidarsene, vista la
  storia di 3+ rifiuti con altri stop.
- Non ancora tentato: griglia SL/TP anche sulla famiglia sweep (fase 2b
  ha usato solo target=4.0xATR fisso, mai variato).
- Su richiesta dell'utente, il prossimo passo è tornare indietro su
  TUTTE le baseline trovate (13 nuove + 4 note) una per una con test
  "meno ovvi": confluenze cross-strategia (MACD esteso oltre ADX_RSI),
  Fibonacci come gestione di uscita/reverse (non filtro di ingresso),
  Elliott Wave come lettura di posizionamento — non ancora iniziato
  sistematicamente, solo il primo giro (MACD su ADX_RSI/SAR_FLIP/
  DONCHIAN_TURTLE) fatto ieri.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Screening Catalogo Completo e Confluenze (24-08)]]
[[NEXUS EA - Attacco alla Dipendenza dal Rally 2023-2026 (24-08)]]
