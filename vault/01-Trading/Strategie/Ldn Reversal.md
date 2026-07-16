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
Sostanzialmente breakeven su 4h (PF1.01, 99 trade — il campione più ampio
delle 7), negativa su 1h (PF0.65). Nessun profilo MT5 esiste ancora.

## Prima connessione al sito (16/07)
Implementata la vera logica MQL5 (`NXS_Strat_LondonReversal`): sessione
Londra/Overlap + sweep (Asia High/Low o PDH/PDL) confermato + chiusura di
rientro oltre il livello + CHoCH (proxy). Vedi [[Amd Cont]] per il metodo.

Test SL1.5/TP3.0 generico, ~2 anni Yahoo intraday:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| 4h | 99 | 1.01 | 17.28 | +89 |
| 1h | 52 | 0.65 | 17.02 | -1.202 |

Campione più ampio del gruppo (99 trade su 4h) ma il segnale è debole
(quasi breakeven) e il DD alto su entrambi i TF — non promettente nel
primo giro. Non ancora validata su MT5 (`InpStrategySelector=30`).

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Amd Cont]]
