---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, level-confluence, negativo]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — LEVEL_CONFLUENCE su 3 anni: conferma il negativo (versione touch originale) (06/09)

## Risultato

Stessa logica del primo test (touch al primo contatto, livelli M15/M30,
nessuna conferma), ma sui 3 anni completi e rischio normale (0.5%,
non il 5% della finestra breve):

| Metrica | Valore |
|---|---|
| Trade | 1958 (1153 BUY, 805 SELL) |
| Profit factor | 0.81 |
| Net profit | -$974.82 |
| Win rate | 30.8% (603/1958) |
| Sharpe | -4.92 |
| Max DD equity | $982.91 |

Conferma su scala molto più ampia (quasi 2000 trade contro i 424 del
test breve) lo stesso verdetto: il trigger "touch" grezzo senza
conferma non ha edge, entrando su una scommessa di reversal immediata
che il più delle volte non regge (vedi
[[NEXUS EA - LEVEL_CONFLUENCE Primo Risultato Vero, Negativo su Entrambi i Lati (06-09)]]).

Questo era il test AVVIATO PRIMA del fix di conferma (2 barre) e del
cambio dei livelli a H1/H4/D1 richiesti dall'utente — resta come
baseline "prima" per il confronto diretto con i risultati successivi
(confirm2 + livelli HTF), attualmente in coda.

## Collegamenti
[[NEXUS EA - LEVEL_CONFLUENCE Primo Risultato Vero, Negativo su Entrambi i Lati (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
