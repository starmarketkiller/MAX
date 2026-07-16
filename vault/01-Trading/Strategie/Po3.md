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
Secondo miglior risultato del gruppo su 4h, migliorato lo stesso giorno
col vero TP dinamico MQL5: **PF1.51, 45 trade, DD6.8%**. Nessun profilo
MT5 esiste ancora, dato preliminare, non validato su MT5 reale.

## Prima connessione al sito (16/07)
Implementata la vera logica MQL5 (`NXS_Strat_PO3`): range asiatico
(Accumulation) + sweep oltre il range (Manipulation) + candela di
distribuzione con corpo forte (>0.6×ATR) nella direzione del rientro +
CHoCH (proxy) — il ciclo ACC-MAN-DIST completo. Vedi [[Amd Cont]] per il
metodo.

Primo test SL1.5/TP3.0 generico (fisso), ~2 anni Yahoo intraday:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| **4h** | 48 | **1.29** | **4.0** | +885 |
| 1h | 14 | 0.84 | 4.34 | -147 |

Su 4h è il secondo risultato più incoraggiante del gruppo dopo AMD_CONT,
con il drawdown più basso delle 7. Non ancora validata su MT5
(`InpStrategySelector=33`).

## Fix reale 16/07 (sera): TP dinamico mancante nella prima implementazione
Stesso bug di [[Judas Swing]] e [[Ldn Reversal]]: il primo porting aveva
usato un TP ATR fisso generico, omettendo che `NXS_Strat_PO3` calcola già
un target dinamico (`MathMax`/`MathMin` tra multiplo R fisso e liquidità
reale del range asiatico). Aggiunta `_po3_target()` e resa sempre attiva:

| TF | TP | Trade | PF | DD% | Net |
|---|---|---|---|---|---|---|
| 4h | fisso (bug) | 47 | 1.39 | 8.02 | +1.094 |
| **4h** | **dinamico (reale)** | **45** | **1.51** | **6.79** | **+1.413** |

Miglioramento netto su ogni metrica (PF, DD e net) — insieme a JUDAS_SWING
il caso più chiaro di beneficio dal target dinamico tra le 3 strategie
interessate. Il numero "fisso" qui sopra è già diverso dal primo test
della mattina (PF1.29→1.39) per lo stesso motivo di finestra dati Yahoo
mobile spiegato in [[Judas Swing]] — non un cambio di codice. Applicato
per fedeltà al vero comportamento MQL5 (`STRATEGY_TARGETS_ALWAYS`).
**Non ancora validato su MT5 reale.**

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Amd Cont]]
