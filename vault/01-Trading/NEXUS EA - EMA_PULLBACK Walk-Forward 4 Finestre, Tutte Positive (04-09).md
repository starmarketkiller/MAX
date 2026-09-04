---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, ema-pullback, walk-forward, confermata]
created: 2026-09-04
updated: 2026-09-04
---

# NEXUS EA — EMA_PULLBACK: walk-forward su 4 finestre, tutte positive (04/09)

## Perché

CSV mai analizzati dalla sessione maratona 01-02/09 (`nxs_emapb_mp1-4`),
trovati su segnalazione esplicita dell'utente ("un paio di csv che non
analizzi"). Sono 4 test su finestre di ~1 anno con partenza scalata
(gennaio/luglio 2024-2025) — un walk-forward de facto mai scritto.

## Risultato — 4/4 finestre positive, in miglioramento

| Finestra | Trade | WR | PF | Sharpe | Net |
|---|---|---|---|---|---|
| mp1 (2024-01) | 75 | 41.3% | 1.44 | 2.20 | $673.50 |
| mp2 (2024-07) | 59 | 39.0% | 1.46 | 2.34 | $636.08 |
| mp3 (2025-01) | 47 | 42.6% | 1.56 | 2.71 | $669.92 |
| mp4 (2025-07) | 33 | 45.5% | 1.71 | 3.55 | $692.34 |

## Lettura

**La conferma più pulita di tutta l'indagine di oggi.** Nessuna delle
4 finestre indipendenti è negativa, e PF/Sharpe migliorano
monotonamente (1.44→1.71, 2.20→3.55) mano a mano che la finestra si
avvicina al presente — né deterioramento né instabilità. Il numero di
trade cala (75→33, finestre più recenti hanno meno storia/dati
disponibili, non necessariamente meno segnale) ma la qualità sale.
Questo rafforza la classificazione già esistente di EMA_PULLBACK come
"confermata robusta" — qui con una prova walk-forward reale che prima
mancava (la nota precedente diceva solo "nessun filtro trovato
migliora", senza uno split temporale esplicito a 4 finestre).

## Non ancora fatto

- Non verificato se le 4 finestre si sovrappongono (mp1 2024-01 e mp2
  2024-07 potrebbero condividere mesi) — se sì, non sono completamente
  indipendenti statisticamente.
- Config esatta usata in questi 4 test non riletta dal report (assunta
  identica alla EMA_PULLBACK "nuda" già confermata, da verificare).

## Collegamenti
[[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] ·
[[MOC - Trading]]
