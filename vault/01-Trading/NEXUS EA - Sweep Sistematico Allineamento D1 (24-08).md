---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, multi-timeframe, sistematico, ottimizzazione]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Sweep sistematico dell'allineamento D1 (24/08)

## Perché

L'allineamento D1 (sostituisce il filtro ER, non si somma) aveva vinto
2 volte su 2 (FVG_MIT, OTE_CONT) con lo stesso pattern pulito. Prima di
continuare a scegliere strategie a caso, testato sistematicamente
sulle altre 14 baseline non ancora provate con questo ingrediente, stessa
config SL/TP nota per ciascuna. `d1_alignment_sweep_24-08.py`.

## Risultato: NON generalizza — 3/14, non 14/14

| Migliorano (3) | retail ER → D1-align | Non migliorano (11) |
|---|---|---|
| LONDON_BO | 1.31 → 1.40 | SAR, MACD, FVG_CONT, DONCHIAN_TURTLE, ADX_RSI, MALAYSIAN_SNR_BREAKOUT, DARVAS_BOX, AMD_CONT, SAR_FLIP, SAR_ADX20, BREAKOUT_ACC |
| TSI | 1.25 → 1.36 | |
| EMA_PULLBACK | 1.30 → 1.42 | |

**Pattern chiaro**: D1-alignment aiuta le strategie il cui filtro ER era
GIÀ debole/borderline (LONDON_BO, TSI, EMA_PULLBACK — tutte con finestre
3-4/5, non 5/5). Per le strategie già forti con ER (SAR, MACD, FVG_CONT,
DONCHIAN_TURTLE, ADX_RSI, tutte 5/5 o 4/5 pulite), D1-alignment
**peggiora sistematicamente** — il campione quasi raddoppia (filtro più
permissivo) ma la qualità cala (m1 crolla quasi ovunque: SAR 1.09→0.87,
MACD 1.39→0.82, DONCHIAN_TURTLE 1.28→0.75), segno che il filtro D1 lascia
passare più segnali di bassa qualità di quanti ne scarti l'ER già ben
calibrato.

## Conclusione

**Non è un ingrediente universale, è uno strumento di salvataggio** per
strategie dove il filtro standard non basta — stessa lezione del floor
ATR (utile per alcune, dannoso o inutile per altre) e della soglia ER
adattiva. Quarta o quinta conferma dello stesso principio oggi:
verificare per strategia, mai assumere.

## Configurazione aggiornata (sostituisce ER solo dove serve)

Usa allineamento D1: **FVG_MIT, OTE_CONT, LONDON_BO, TSI, EMA_PULLBACK**
(5 strategie). Resta su ER standard: tutte le altre (SAR, MACD,
FVG_CONT, DONCHIAN_TURTLE, ADX_RSI, MALAYSIAN_SNR_BREAKOUT, DARVAS_BOX,
AMD_CONT, SAR_FLIP, SAR_ADX20, BREAKOUT_ACC, STRUCT_REACT, LIQ_SWEEP).

## Prossimi passi aperti

- Non ancora provato: allineamento D1 su FVG_CONT_V2 e Z_SCORE_BREAKOUT
  (stop nativi, richiedono adattare il test).
- La lista di configurazioni "vincenti" per strategia sta diventando
  numerosa e sparsa tra molte note — utile consolidare in un'unica
  tabella di riferimento prima di continuare con altre singole
  ottimizzazioni.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Ottimizzazione OTE_CONT (24-08)]]
[[NEXUS EA - Ottimizzazione LIQ_SWEEP (24-08)]]
