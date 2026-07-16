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
🟡 Prima serie di dati mai raccolta (16/07) — non più NOT_CONNECTED. Il
primo test (TP fisso generico) era negativo; corretto lo stesso giorno
(vedi sotto) implementando il vero TP dinamico MQL5 — ora PF1.4 su 4h.
Nessun profilo MT5 esiste ancora, dato preliminare, non validato su MT5
reale.

## Prima connessione al sito (16/07)
Implementata la vera logica MQL5 (`NXS_Strat_JudasSwing`): finestra di
apertura Londra (7-10 GMT) o NY (12-15 GMT) + sweep del range asiatico
(wick sotto/sopra + chiusura di rientro) + CHoCH (proxy). Vedi [[Amd Cont]]
per il metodo generale.

Primo test SL1.5/TP3.0 generico (fisso), ~2 anni Yahoo intraday:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| 4h | 63 | 0.77 | 13.78 | -927 |
| 1h | 29 | 0.74 | 13.15 | -513 |

## Fix reale 16/07 (sera): TP dinamico mancante nella prima implementazione
Il primo porting delle 7 strategie a sessione (16/07) aveva usato per
tutte un TP generico ATR fisso — ma il vero `NXS_Strat_JudasSwing` MQL5
calcola già un **target dinamico** (`MathMax`/`MathMin` tra il multiplo R
fisso e l'estremo del range asiatico, cioè liquidità reale, non un
multiplo arbitrario). Questo era stato omesso per errore nel primo passo,
non una scelta — i numeri sopra sottostimavano la vera fedeltà. Aggiunta
`_judas_swing_target()` (fedele al calcolo MQL5) e resa **sempre attiva**
(non opt-in, è comportamento reale non un'ipotesi):

| TF | TP | Trade | PF | DD% | Net |
|---|---|---|---|---|---|---|
| 4h | fisso (bug) | 61 | 1.37 | 4.93 | +1.388 |
| **4h** | **dinamico (reale)** | **59** | **1.4** | **4.9** | **+1.546** |

Nota: anche la versione "fisso" di questo confronto è già molto meglio del
primo test (PF0.77→1.37) — differenza attribuibile alla finestra dati
Yahoo che si è spostata nel tempo reale della sessione di lavoro (dati
"ultime N barre" via Yahoo, non uno storico congelato), non un cambio di
codice tra le due righe. Il salto di fedeltà vero è fisso→dinamico
(+PF0.03, DD invariato, stesso ordine di grandezza di trade). Applicato
solo al sito (`STRATEGY_TARGETS_ALWAYS`) — la logica MQL5 la aveva già
correttamente, nessun cambio lato EA. **Non ancora validato su MT5
reale.**

Negativa su entrambi i TF testati nel primo giro — non ancora validata su
MT5 (`InpStrategySelector=29`). Da rivedere se i parametri SL/TP generici
(mai tarati) sono la causa, prima di scartarla.

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Amd Cont]]
