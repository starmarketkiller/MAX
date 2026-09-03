---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bollinger, scalp, m5, mean-reversion, rsi, candlestick]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — BOLLINGER: filtro RSI e candela testati, nessuno alza il win rate (03/09)

## Perché

Step 3 del piano [[NEXUS EA - Ricerca Scalp BAR_UPDN e BREAKOUT_ACC, Piano BOLLINGER+RSI (02-09)]]:
dopo la baseline nuda M5 (306 trade, PF0.83, WR28.1%, payoff ~2.15:1 —
vedi [[NEXUS EA - BOLLINGER M5 Nuda, Primo Risultato Vero dopo Fix Selector (03-09)]]),
implementato e testato isolatamente il filtro RSI(14) "divergenza"
(scarta il tocco se RSI CONFERMA l'estremo) e il filtro candela di
inversione (hammer/engulfing sul supporto, shooting star/engulfing
sulla resistenza), più la combinazione dei due.

## Risultato — 4 varianti, stesso periodo (M5, 2026.06.01-2026.08.26)

| Variante | Trade | WR | Avg win | Avg loss | PF | Net |
|---|---|---|---|---|---|---|
| Solo gate barra (baseline) | 306 | 28.1% | $10.99 | -$5.10 | 0.83 | -$186.23 |
| + Filtro RSI | 250 (-18%) | 27.2% | $9.98 | -$5.00 | **0.74** | -$236.17 |
| + Filtro candela | 54 (-82%) | 25.9% | $11.29 | -$5.08 | 0.77 | -$46.01 |
| + Entrambi | 41 (-87%) | 26.8% | $10.88 | -$4.75 | 0.83 | -$23.78 |

## Diagnosi onesta

**Nessuno dei due filtri sposta il win rate** (resta 25.9-28.1% in
tutte e 4 le varianti, differenze nel rumore statistico su campioni
sempre più piccoli). Il filtro RSI addirittura **peggiora il PF**
(0.83→0.74) — l'ipotesi "l'estremo senza conferma RSI è momentum in
esaurimento/divergenza" **non regge sui dati**, va scartata così
com'è. Il filtro candela riduce il campione dell'82% senza guadagno di
qualità — stesso schema già visto ripetutamente su PIVOT_WICK
(OneShotLevel, veto di regime): un filtro che taglia volume senza
toccare l'edge sottostante.

Combinare i due riporta il PF esattamente al livello baseline (0.83)
ma con l'87% dei trade in meno — nessun beneficio, solo rumore
statistico su un campione di 41 trade.

## Conclusione

Il problema di BOLLINGER su M5 non è "troppi falsi segnali filtrabili
con RSI/candela" come ipotizzato nel piano del 02/09 — è più probabile
un problema strutturale del trigger stesso (rientro nudo dalla banda,
senza contesto di trend/regime) che non ha edge direzionale su questo
timeframe, indipendentemente da quale conferma extra gli si affianca.
Stessa lezione di PIVOT_WICK: quando NESSUN filtro isolato sposta il
win rate, il problema è a monte (il trigger), non a valle (i filtri).

## Non ancora fatto

- BUY vs SELL non ancora separato — possibile che uno dei due lati
  regga meglio (pattern visto più volte in questa indagine, es. SAR/
  ADX_RSI dipendenti da regime BUY/SELL).
- Non testato su timeframe diverso da M5 con questi due filtri (la
  baseline D1 originale, PF1.17, non ha mai avuto RSI/candela — non
  sappiamo se lì aiuterebbero).
- Nessuna soglia RSI diversa da 30/70 provata.

## Collegamenti
[[NEXUS EA - Ricerca Scalp BAR_UPDN e BREAKOUT_ACC, Piano BOLLINGER+RSI (02-09)]] ·
[[NEXUS EA - BOLLINGER M5 Nuda, Primo Risultato Vero dopo Fix Selector (03-09)]] ·
[[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]] ·
[[MOC - Trading]]
