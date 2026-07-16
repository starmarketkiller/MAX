---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: AMD_CONT
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: AMD_CONT

## Tipo
Sessione/ICT (non portabile dal sito)

## Trigger meccanico
Accumulation-Manipulation-Distribution, ramo continuation.

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
🟢 Prima serie di dati mai raccolta (16/07) — non più NOT_CONNECTED sul
sito. **PF2.07 su 4h (62 trade, DD5.85%)** — il risultato più incoraggiante
delle 7 strategie a sessione appena collegate. Nessun profilo MT5 esiste
ancora (mai configurata), serve validazione su dati reali prima di
qualunque conclusione.

## Prima connessione al sito (16/07) — sessioni/AMD implementate per davvero
Il motore sito non aveva MAI testato questa strategia (0 chiamate,
NOT_CONNECTED) — si pensava per limite strutturale (nessun dato di
sessione). In realtà `_fetch_real()` scarica già candele intraday con
timestamp GMT reali; il pezzo mancante era il codice. Implementata la
vera logica MQL5 (`NXS_Strat_AMD_Continuation`): range asiatico
giornaliero + state machine AMD (accumulation→manipulation→continuation)
+ filtro sessione Londra/Overlap/NY + bias HTF. Il CHoCH usa un proxy
failure-swing (non il vero `g_struct` fractal-based di MQL5).

Test con SL1.5/TP3.0 generico (nessun profilo MT5 esiste per questa
strategia, mai tarata prima) su ~2 anni di dati Yahoo intraday (limite
Yahoo, non i 10 anni di MT5):

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| **4h** | 62 | **2.07** | 5.85 | +3.677 |
| 1h | 31 | 1.00 | 8.68 | -10 |

**Non ancora validata su MT5** — è un primo segnale sul sito, non una
conferma. Prossimo passo: test isolato MT5 (`InpStrategySelector`, indice
28) per vedere se regge su dati broker reali.

## Note

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]
