---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: PO3
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: PO3

## Tipo
Sessione/ICT (non portabile dal sito)

## Trigger meccanico
Power of Three (ICT: accumulo/manipolazione/espansione sul range giornaliero).

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
🟢 Prima serie di dati mai raccolta (16/07) — non più NOT_CONNECTED.
Secondo miglior risultato del gruppo su 4h (PF1.29, 48 trade, DD4.0% — il
più basso delle 7). Nessun profilo MT5 esiste ancora, dato preliminare.

## Prima connessione al sito (16/07)
Implementata la vera logica MQL5 (`NXS_Strat_PO3`): range asiatico
(Accumulation) + sweep oltre il range (Manipulation) + candela di
distribuzione con corpo forte (>0.6×ATR) nella direzione del rientro +
CHoCH (proxy) — il ciclo ACC-MAN-DIST completo. Vedi [[Amd Cont]] per il
metodo.

Test SL1.5/TP3.0 generico, ~2 anni Yahoo intraday:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| **4h** | 48 | **1.29** | **4.0** | +885 |
| 1h | 14 | 0.84 | 4.34 | -147 |

Su 4h è il secondo risultato più incoraggiante del gruppo dopo AMD_CONT,
con il drawdown più basso delle 7. Non ancora validata su MT5
(`InpStrategySelector=33`).

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Amd Cont]]
