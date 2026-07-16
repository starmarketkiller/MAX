---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: LDN_REVERSAL
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: LDN_REVERSAL

## Tipo
Sessione/ICT (non portabile dal sito)

## Trigger meccanico
Reversal di sessione Londra.

## Configurazione attuale (v2.5.0)
- **Timeframe**: N/D — non connessa al collector segnali
- **SL**: N/D — non connessa al collector segnali× ATR · **TP**: N/D — non connessa al collector segnali× ATR
- **Filtro HTF**: N/D — non connessa al collector segnali
- **Trailing**: N/D — non connessa al collector segnali
- **Rischio per trade**: N/D — non connessa al collector segnali%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build.
- **3 anni**: 0 trade eseguiti in questo build.

## Stato
⏳ Prima serie di dati mai raccolta (16/07) — non più NOT_CONNECTED.
Sostanzialmente breakeven su 4h (PF1.08, 108 trade — il campione più ampio
delle 7), DD alto (9.9%). Corretto lo stesso giorno con il vero TP
dinamico MQL5 (miglioramento marginale). Nessun profilo MT5 esiste
ancora, dato preliminare, non validato su MT5 reale.

## Prima connessione al sito (16/07)
Implementata la vera logica MQL5 (`NXS_Strat_LondonReversal`): sessione
Londra/Overlap + sweep (Asia High/Low o PDH/PDL) confermato + chiusura di
rientro oltre il livello + CHoCH (proxy). Vedi [[Amd Cont]] per il metodo.

Primo test SL1.5/TP3.0 generico (fisso), ~2 anni Yahoo intraday:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| 4h | 99 | 1.01 | 17.28 | +89 |
| 1h | 52 | 0.65 | 17.02 | -1.202 |

Campione più ampio del gruppo (99 trade su 4h) ma il segnale è debole
(quasi breakeven) e il DD alto su entrambi i TF — non promettente nel
primo giro. Non ancora validata su MT5 (`InpStrategySelector=30`).

## Fix reale 16/07 (sera): TP dinamico mancante nella prima implementazione
Stesso bug di [[Judas Swing]] e [[Po3]]: il primo porting aveva usato un
TP ATR fisso generico per tutte le 7 strategie a sessione, omettendo che
`NXS_Strat_LondonReversal` calcola già un target dinamico
(`MathMax`/`MathMin` tra multiplo R fisso e liquidità reale). Aggiunta
`_ldn_reversal_target()` e resa sempre attiva:

| TF | TP | Trade | PF | DD% | Net |
|---|---|---|---|---|---|---|
| 4h | fisso (bug) | 108 | 1.08 | 9.92 | +573 |
| **4h** | **dinamico (reale)** | **108** | **1.08** | **9.92** | **+593** |

A differenza di JUDAS_SWING e PO3, qui il target dinamico quasi non
cambia (stesso PF/DD, net leggermente migliore) — il livello ATR fisso e
quello dinamico coincidono quasi sempre in questa strategia sui dati
testati. Applicato comunque per fedeltà al vero comportamento MQL5
(`STRATEGY_TARGETS_ALWAYS`), non è un'ipotesi. **Non ancora validato su
MT5 reale.**

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Amd Cont]]
