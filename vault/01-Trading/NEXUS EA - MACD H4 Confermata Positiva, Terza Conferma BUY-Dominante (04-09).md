---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, macd, h4, buy-sell-split]
created: 2026-09-04
updated: 2026-09-04
---

# NEXUS EA — MACD (H4) confermata positiva, terza conferma BUY-dominante di oggi (04/09)

## Perché

Terzo elemento della coda prioritaria (dopo ADX_RSI PF2.04 e BOLLINGER
H4 BUY-only PF1.35). Test nudo su config di produzione attuale (H4,
`NXS_SelectorAllows(3)` verificato, già abilitata di default), 3 anni.

## Risultato

| Metrica | Valore |
|---|---|
| Trade | 199 |
| PF | **1.53** |
| Net (3 anni) | +$1975.49 |
| Sharpe | 1.28 |
| Max DD balance | $492.46 (49.2% del deposito) |

## BUY vs SELL — terza conferma dello stesso schema

| | Trade | WR | Net |
|---|---|---|---|
| BUY | 129 | 37.2% | **+$2272.65** |
| SELL | 70 | 18.6% | +$162.17 (rumore, praticamente pareggio) |

Identico a ADX_RSI e BOLLINGER oggi: tutto l'edge è nel lato BUY, SELL
è irrilevante. Terza conferma dello stesso giorno dello stesso
fenomeno — rafforza l'ipotesi (vedi discussione con l'utente) che gran
parte di questo "edge" rifletta il rally secolare dell'oro (+125% nel
periodo 2023-09→2026-08, dato verificato su Dukascopy) più che un vero
segnale predittivo indipendente dal trend.

## Discrepanza con una nota storica nel codice

`NXS_Profile_Risk` (riga ~380 di `NXS_StrategyProfiles.mqh`) ha un
commento: *"CRITICA storica su MT5 (PF1.10 al limite, mai chiarita)"*.
Il test di oggi dà PF1.53, nettamente sopra quel numero. Non
verificato se la config sia cambiata da allora o se quel numero si
riferisse a un periodo/dataset diverso — segnalato, non risolto.

## Non ancora fatto

- BUY-only non isolato esplicitamente con un test dedicato (richiede
  aggiungere un lock di direzione come già fatto per BOLLINGER — non
  ancora fatto qui).
- Trailing/Elliott (ricetta Python, PF1.84) non ancora provati.
- Nessuna verifica walk-forward/finestre separate.

## Collegamenti
[[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] ·
[[NEXUS EA - ADX_RSI D1 Confermata Positiva sul Vero MT5, BUY Domina (04-09)]] ·
[[NEXUS EA - BOLLINGER H4 Nuda, BUY Positivo SELL Negativo, Conferma Python (04-09)]] ·
[[MOC - Trading]]
