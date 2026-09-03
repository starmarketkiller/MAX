---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, adx-rsi, d1, confermata]
created: 2026-09-04
updated: 2026-09-04
---

# NEXUS EA — ADX_RSI (D1) confermata positiva sul vero MT5, BUY domina (04/09)

## Perché

Primo elemento della coda prioritaria del
[[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]]
(dopo aver rinunciato a FVG_MIT per complessità architetturale — vive
nel sistema di zone condiviso "NXR", non nel pattern semplice usato
da ADX_RSI/BOLLINGER). Test nudo sulla config di produzione attuale
(D1, `NXS_SelectorAllows(1)` verificato nel codice, nessun override),
3 anni (2023.09-2026.08), GOLD.

## Risultato — primo esito chiaramente positivo di oggi

| Metrica | Valore |
|---|---|
| Trade | 51 |
| Win rate | 29.4% |
| Avg win | $253.02 |
| Avg loss | -$40.51 |
| Payoff ratio | ~6.25:1 |
| PF | **2.04** |
| Net (3 anni, $1000 deposito) | **+$1675.65** |
| Sharpe | 1.20 |
| Max DD balance | $596.09 (59.6% del deposito — alto) |

## BUY vs SELL — conferma diretta della scoperta Python del 24/08

| | Trade | Net | WR |
|---|---|---|---|
| BUY | 44 | +$2308.89 | 31.8% (14/44) |
| SELL | 7 | +$28.06 | 14.3% (1/7) |

SELL è rumore puro (7 trade, praticamente a pareggio). Questo conferma
esattamente quanto trovato sul motore Python il 24/08
([[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]: ADX_RSI
BUY-only PF2.62 vs simmetrica) — **prima conferma vera su MT5** di un
pattern BUY/SELL trovato su Python.

## Lettura

Payoff ratio molto alto (~6.25:1, TP a 10×ATR + breakeven a 1.5R)
compensa un win rate basso (29.4%, ben sopra il pareggio teorico
~13.8% a questo payoff). Il DD (59.6% del deposito) è però severo per
un conto piccolo — da tenere presente prima di qualunque conclusione
su "pronta per demo/live", questa nota valuta solo l'edge, non il
risk management completo.

## Non ancora fatto

- BUY-only non ancora isolato esplicitamente (solo osservato dai dati
  misti) — prossimo passo naturale, rimuovere le 7 SELL dovrebbe
  lasciare PF e net quasi invariati ma è da confermare con un test
  dedicato (disabilitare SELL nel codice o via filtro).
- Trailing 2.5×ATR e filtro Elliott multi-TF (la ricetta Python
  completa, PF2.62) non ancora aggiunti — `InpUseAtrTrail` e
  `InpUseElliottFilter` esistono già come flag generici, non
  richiedono nuovo codice, solo test.
- Nessuna verifica walk-forward/finestre separate ancora fatta su
  questo dataset specifico (solo aggregato 3 anni).

## Collegamenti
[[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] ·
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]] · [[MOC - Trading]]
