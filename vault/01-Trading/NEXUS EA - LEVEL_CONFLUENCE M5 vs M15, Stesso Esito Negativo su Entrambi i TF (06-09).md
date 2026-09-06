---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, level-confluence, negativo, htf, m5, m15]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — LEVEL_CONFLUENCE: M5 vs M15, stesso esito negativo su entrambi i TF (06/09)

## Il test

Stessa logica (livelli solo H1/H4/D1, conferma 2 barre), stessa
finestra 3 mesi, stesso rischio 5% — unica variabile cambiata:
**timeframe di esecuzione**. M15 già testato ([[NEXUS EA - Conferma 2 Barre e Livelli HTF, Migliora il Rapporto ma Resta Negativo (06-09)]]),
qui il confronto diretto con M5.

## Risultato

| Metrica | M15 (conferma 2, H1/H4/D1) | M5 (stessa logica) |
|---|---|---|
| Trade | 295 | 346 |
| Profit factor | 0.83 | 0.78 |
| Net profit | -$837.33 | -$894.47 |
| Win rate | 35.3% (BUY) / 35.0% (SELL) | 36.9% (BUY) / 39.9% (SELL) |
| Vincita media | +$32.33 | +$24.40 |
| Perdita media | -$27.28 | -$19.23 |
| Durata media vincite | 3.9h | 1.1h |
| Durata media perdite | 2.5h | 0.7h |
| Soglia di pareggio (WR) | ~45.7% | ~44.1% |
| Gap dalla soglia | -10.7 punti | -6.2 punti (BUY) / -4.2 (SELL) |

## Interpretazione

**M5 non è meglio, è leggermente peggio in assoluto** (PF 0.78 vs
0.83, net -$894 vs -$837) nonostante un win rate più alto (36.9-39.9%
vs 35%) e un gap dalla soglia di pareggio più piccolo. La ragione: su
M5 il rapporto vincita/perdita si comprime (1.27 vs 1.19 su M15 — in
realtà leggermente migliore in rapporto, ma) **le vincite e le perdite
sono entrambe più piccole in valore assoluto e durano un terzo del
tempo** (1.1h vs 3.9h) — l'esecuzione più fine cattura meno del
movimento reale del prezzo, quindi anche quando il trigger "funziona"
di più (WR più alto), il P&L per trade non compensa.

**Verdetto**: entrambi i timeframe falliscono per la stessa ragione di
fondo — il trigger (tocco/sweep di un livello H1/H4/D1 con conferma 2
barre) non seleziona punti con abbastanza vantaggio statistico, a
prescindere dal TF su cui viene eseguito. Questo è un'ulteriore
conferma (non un'eccezione) rispetto alla nota precedente: il problema
è nella selezione del punto d'ingresso, non nella granularità
dell'esecuzione. Eseguire su M5 non "ripara" un trigger debole,
semplicemente applica la stessa selezione debole con un'unità di
misura più piccola.

## Cosa resta da provare prima di chiudere LEVEL_CONFLUENCE

- `InpLevelConfRequireConfluence=true` (mandatorio 2+ TF alte
  d'accordo sullo stesso livello) — non ancora testato, unica ipotesi
  rimasta che cambia la SELEZIONE del punto invece del solo
  timing/TF d'esecuzione.
- Se anche la confluenza obbligatoria non alza il win rate sopra
  soglia, la conclusione onesta è che "tocco di livello + conferma"
  non è di per sé un segnale sufficiente su GOLD in questa finestra,
  indipendentemente da TF, conferma-barre o fonte dei livelli — da
  chiudere come le altre chiuse negative (PIVOT_WICK, BOLLINGER M5
  scalp).

## Collegamenti
[[NEXUS EA - LEVEL_CONFLUENCE Primo Risultato Vero, Negativo su Entrambi i Lati (06-09)]] · [[NEXUS EA - LEVEL_CONFLUENCE 3 Anni Conferma il Negativo (06-09)]] · [[NEXUS EA - Conferma 2 Barre e Livelli HTF, Migliora il Rapporto ma Resta Negativo (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
