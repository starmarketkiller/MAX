---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar, python-engine, debug, mt5, auto-close]
created: 2026-08-29
updated: 2026-08-29
---

# NEXUS EA — Debug del motore Python "real-tick" su SAR: tre bug trovati e corretti (29/08)

## Perché

Il nuovo motore Python "come MT5 vero" (`nxs_real_engine_29-08.py`, vedi
[[NEXUS EA - Diff Python vs MQL5 su SAR-EMA_PULLBACK, Limite Strutturale del Motore Ricerca (28-08)]])
al primo test su SAR **non convergeva** col Tester MT5 reale di stanotte:

| | Prima versione (v1, entry+SL/TP statico) | MT5 reale |
|---|---|---|
| Trade | 55 | 175 |
| PF | 1.65 | 0.92 |
| Netto | +$1427.70 | -$118.95 |

Segno del risultato SBAGLIATO (vincente in Python, perdente nel motore
vero) — inaccettabile. L'utente ha rifiutato esplicitamente di accettare
questo come punto di arrivo ("fai il debug e sistema già il codice...
correggi e capisci perché"), quindi non ci si è fermati al primo tentativo.

## Bug #1: mancava tutta la gestione intraday (v1 → v2)

v1 modellava solo entry + SL/TP nativo statico, controllato sulle sole
barre H4. Analisi empirica dei 175 trade reali (`nexus_sel_sar_realtick_
report_deals.csv`): **zero trade su 175 chiudono per target** (TP nativo
mai raggiunto), 66% chiudono "sl" (ma a un livello diverso da quello
nativo — è il trailing), 23% "NXS:RISK", 11% "NXS:TIME". Durata mediana
2.59h — molto meno di una barra H4 (4h): la gestione è intraday, serve
granularità M15. Esportate le barre M15 reali via una nuova EA
(`NXS_ExportM15.mq5`, `CopyRates` in `OnInit`) e riscritta la simulazione
per camminare barra per barra dentro ogni posizione, applicando trailing
ATR + max-loss-per-posizione + timeout.

## Bug #2: ATR calcolato con media mobile semplice, non Wilder

`atr_series()` e `ema_series()` nella prima riscrittura erano state
scritte da zero invece di riusare le versioni già validate riga-per-riga
in `backtest.py`. Risultato: EMA seedata sul primo valore grezzo (non
SMA(n)) e ATR come media mobile semplice su finestra, invece del vero
smoothing di Wilder (`a = (a*(n-1)+tr)/n`) che `iATR` di MT5 usa
davvero. Sostituite con un porting esatto delle funzioni di `backtest.py`.
Inoltre `NXS_Profile_TrailK("SAR")` ha un override specifico (**2.0**),
non il trailing globale (2.5) usato per sbaglio.

## Bug #3 (il più grande): "NXS:TIME" non è un timer per-posizione

Assunzione iniziale: max-hold ~4h per posizione (calibrata "a occhio"
sulla durata mediana osservata). **Sbagliata.** Verificato riga per riga
sul CSV reale: OGNI singola chiusura "NXS:TIME" cade esattamente alle
**23:43:0x server time**, in qualunque giorno del test, indipendentemente
da quando la posizione era stata aperta:

```
2025.11.04 23:43:00  buy out  NXS:TIME   (entry 20:00 → hold 3h43m)
2025.11.05 23:43:01  buy out  NXS:TIME   (entry 18:45 → hold 4h58m)
2025.11.07 23:43:00  sell out NXS:TIME
2026.05.14 23:43:00  buy out  NXS:TIME
... (ogni singola occorrenza, stesso orario esatto)
```

Causa reale: `NXS_Prot_CheckAutoClose()` (`NXS_Protections.mqh:411`) —
un **flatten-all giornaliero** prima della chiusura di sessione del
broker per GOLD (`InpAutoCloseMin=15` minuti prima dell'orario di
chiusura sessione; su tick reali la prima posizione ancora aperta in
quella finestra viene chiusa quasi subito, da cui il pattern "23:43:0x"
identico ogni volta). **Non c'entra affatto** `NXS_MaxHold_LimitSec()`
(il percorso 4h/160h) per SAR: quella funzione, avendo un profilo
risolvibile (SAR/H4), marca `holdResolved=true` e la generica
`NXS_Prot_CheckMaxHold()` la salta del tutto — competenza di
`NXS_Management.mqh`, non del timer generico. La ricerca precedente di
un "~4h" empirico era un artefatto statistico (molte posizioni chiuse
vicino a fine giornata per puro caso dell'orario di apertura), non la
causa vera. Sostituito il timer relativo con un deadline **giornaliero
fisso** (23:43).

## Bug #4 (quello che ha davvero sbloccato il conteggio): entry solo al bar H4 successivo

Anche dopo i fix #2/#3 il conteggio restava 2x quello reale (350 contro
175), col mix sl/risk/time ormai corretto ma il volume totale ancora
sbagliato. Analisi dei gap reali tra una chiusura e la rientrata
successiva (`nexus_sel_sar_realtick_report_deals.csv`): gap da **0.0h**
a diverse ore, mediana 1.7h — **non allineati ai boundary H4**. La v2
apriva solo "alla barra H4 successiva a quella del segnale", un'
approssimazione discreta che non riflette come MT5 valuta davvero la
condizione: **su ogni tick**, usando l'ultima barra H4 chiusa
(`iClose(...,1)`), quindi può rientrare in qualunque momento non appena
una posizione si libera, non solo all'apertura della barra H4
successiva. Riscritto l'intero motore come **un unico event loop M15
continuo** (non più un ciclo per indice H4): ad ogni barra M15 si
avanza il cursore "ultima H4 chiusa" e, se nessuna posizione è aperta,
si valuta il segnale su quella barra. Risultato: 350 → **139 trade**
(reale 175), PF **0.47** (reale 0.92 — segno finalmente corretto, entrambi
sotto 1.0 = strategia in perdita), bucket "time" **20** (reale 19 — quasi
esatto).

## Stato finale (non perfetto, onesto)

| | Python v3 (finale) | MT5 reale |
|---|---|---|
| Trade | 139 | 175 |
| PF | 0.47 | 0.92 |
| Netto | -$749.59 | -$118.95 |
| Motivi | risk 57 / sl 62 / time 20 | RISK 40 / sl 116 / TIME 19 |

Segno e ordine di grandezza corretti (da 3x/segno-sbagliato a ~20% sotto
col motivo "time" quasi esatto). Gap residuo: il rapporto risk:sl è più
alto nel mio modello del reale (quasi 1:1 contro quasi 1:3) — sospetto
principale per il prossimo giro: il check max-loss-per-posizione (2%)
scatta più spesso nel mio modello sui trade a lotto minimo con rischio
maggiorato di quanto scatti nel motore vero. Non ancora investigato oltre
— lo script (`sar_real_engine_validate_29-08.py`) documenta questo gap
esplicitamente per la prossima sessione.

## Lezione di metodo

Quando un motore di simulazione diverge dal reale su PIÙ assi (segno del
risultato E conteggio trade E mix dei motivi di chiusura), non fermarsi
al primo fix plausibile: ogni bug trovato qui era reale e necessario, ma
nessuno da solo bastava. Il debug efficace è stato guidato SEMPRE dai
dati reali (il CSV dei 175 trade), non da assunzioni sul codice lette a
occhio — la scoperta del bug #3 (auto-close giornaliero, non timer
relativo) è arrivata SOLO notando che tutte le chiusure NXS:TIME
cadevano allo stesso identico orario, un pattern impossibile da vedere
leggendo solo il codice sorgente.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Diff Python vs MQL5 su SAR-EMA_PULLBACK, Limite Strutturale del Motore Ricerca (28-08)]]
[[NEXUS EA - Piramidare, Debug Completo e Verdetto sul Portafoglio (28-08)]]
[[NEXUS EA - Sei Strategie da TradingView Pine Script (28-08)]]
