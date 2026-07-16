---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: SILVER_BULLET
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: SILVER_BULLET

## Tipo
Sessione/ICT (non portabile dal sito)

## Trigger meccanico
Killzone NY/Londra (ICT). Richiede modellazione di sessione intraday che il motore del sito non ha.

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
Terzo miglior risultato del gruppo su 4h (PF1.52, 68 trade — secondo
campione più ampio). Nessun profilo MT5 esiste ancora, dato preliminare.

## Prima connessione al sito (16/07)
La citazione "richiede modellazione di sessione intraday che il motore
del sito non ha" (sopra) era **il presupposto sbagliato**: il sito scarica
già intraday reale, mancava solo il codice. Implementata la vera logica
MQL5 (`NXS_Strat_SilverBullet`): finestra kill zone Londra (10-11 GMT) o
NY (14-15 GMT) + sweep confermato nella direzione del setup. Orari presi
dalla ricerca esterna già fatta (vedi [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]]).

Test SL1.5/TP3.0 generico, ~2 anni Yahoo intraday:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| **4h** | 68 | **1.52** | 9.56 | +2.085 |
| 1h | 47 | 0.77 | 15.34 | -749 |

Terzo miglior segnale del gruppo su 4h, ma negativo su 1h — coerente con
le fonti che indicano finestre orarie precise più che un timeframe fisso.
Non ancora validata su MT5 (`InpStrategySelector=23`).

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Amd Cont]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]]
