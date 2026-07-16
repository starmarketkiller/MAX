---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: JUDAS_SWING
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: JUDAS_SWING

## Tipo
Sessione/ICT (non portabile dal sito)

## Trigger meccanico
Falso movimento di apertura sessione (ICT Judas Swing).

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
🔴 Prima serie di dati mai raccolta (16/07) — non più NOT_CONNECTED, ma il
primo test è negativo su entrambi i timeframe (PF0.74-0.77). Nessun
profilo MT5 esiste ancora, dato preliminare.

## Prima connessione al sito (16/07)
Implementata la vera logica MQL5 (`NXS_Strat_JudasSwing`): finestra di
apertura Londra (7-10 GMT) o NY (12-15 GMT) + sweep del range asiatico
(wick sotto/sopra + chiusura di rientro) + CHoCH (proxy). Vedi [[Amd Cont]]
per il metodo generale.

Test SL1.5/TP3.0 generico, ~2 anni Yahoo intraday:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| 4h | 63 | 0.77 | 13.78 | -927 |
| 1h | 29 | 0.74 | 13.15 | -513 |

Negativa su entrambi i TF testati nel primo giro — non ancora validata su
MT5 (`InpStrategySelector=29`). Da rivedere se i parametri SL/TP generici
(mai tarati) sono la causa, prima di scartarla.

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Amd Cont]]
