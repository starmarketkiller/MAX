---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: AMD_REVERSAL
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: AMD_REVERSAL

## Tipo
Sessione/ICT (non portabile dal sito)

## Trigger meccanico
Accumulation-Manipulation-Distribution, ramo reversal.

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
⏳ Prima serie di dati mai raccolta (16/07) — non più NOT_CONNECTED. Debole
sul sito (PF1.10 su 4h, 57 trade — sostanzialmente breakeven; PF0.68 su 1h,
negativo). Nessun profilo MT5 esiste ancora, dato preliminare.

## Prima connessione al sito (16/07)
Implementata la vera logica MQL5 (`NXS_Strat_AMD_Reversal`): fase AMD
"reversal_distribution" (manipolazione fallita, prezzo rientra nel range
asiatico) + sweep Asia High/Low + CHoCH (proxy failure-swing). Stesso
lavoro fatto per le altre 6 strategie a sessione — vedi [[Amd Cont]] per il
dettaglio del metodo.

Test SL1.5/TP3.0 generico (nessun profilo MT5 mai tarato), ~2 anni Yahoo
intraday:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| 4h | 57 | 1.10 | 5.15 | +336 |
| 1h | 20 | 0.68 | 6.3 | -443 |

Non ancora validata su MT5 (`InpStrategySelector=24`). Meno promettente di
AMD_CONT nello stesso primo test, ma il campione è ancora piccolo.

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Amd Cont]]
