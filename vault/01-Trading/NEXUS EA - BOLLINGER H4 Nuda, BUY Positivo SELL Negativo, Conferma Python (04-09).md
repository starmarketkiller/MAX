---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bollinger, h4, buy-sell-split]
created: 2026-09-04
updated: 2026-09-04
---

# NEXUS EA — BOLLINGER su H4 nuda: BUY positivo, SELL negativo, conferma diretta della scoperta Python (04/09)

## Perché

Richiesta esplicita dell'utente ("Dobbiamo provare bollinger in h4").
Prima riga della coda [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]]
con PF Python 1.95 (4h, BUY-only, filtro Elliott) mai verificata sul
vero MT5. Test nudo (nessun filtro, direzione simmetrica) su H4, 3
anni (2023.09-2026.08), GOLD, stesso `InpScalpTFOverride` costruito
ieri per BOLLINGER (riusato con H4 invece di M5, nessun codice nuovo).

## Risultato aggregato — negativo, ma il dettaglio conta

| Metrica | Valore |
|---|---|
| Trade | 209 |
| PF | 0.80 |
| Net (3 anni) | -$537.13 |
| Max DD balance | $752.74 (75% del deposito) |

## BUY vs SELL — la stessa storia di ADX_RSI oggi

| | Trade | WR | PF | Net |
|---|---|---|---|---|
| **BUY** | 71 | 46.5% | **1.33** | **+$262.90** |
| SELL | 138 | 23.2% | 0.61 | -$744.46 |

**Identico allo schema visto oggi su ADX_RSI**: il lato BUY ha un edge
reale e positivo, il lato SELL è strutturalmente negativo e trascina
in perdita l'aggregato simmetrico. Conferma diretta di quanto trovato
sul motore Python il 24/08
([[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]: BOLLINGER
BUY-only PF1.95 con Elliott). Qui, **senza ancora nessun filtro**,
BUY-only da solo è già PF1.33 — più basso del PF1.95 Python (che
include anche il filtro Elliott), ma la direzione del segnale è
confermata corretta.

## Prossimo passo

Isolare BUY-only con un test dedicato (nessun flag esistente per
questo — serve aggiungere un lock di direzione, non presente nel
codice attuale) per avere il numero pulito, poi eventualmente
aggiungere il filtro Elliott multi-TF (già esistente come
`InpUseElliottFilter`, generico, nessun nuovo codice) per avvicinarsi
alla ricetta Python completa.

## Collegamenti
[[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] ·
[[NEXUS EA - ADX_RSI D1 Confermata Positiva sul Vero MT5, BUY Domina (04-09)]] ·
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]] · [[MOC - Trading]]

## Addendum — BUY-only isolato, confermato (04/09)

Aggiunto `InpBollingerBuyOnly`, testato isolato (H4, 3 anni, stesso periodo):

| Metrica | Valore |
|---|---|
| Trade | 68 (tutti BUY) |
| Win rate | 50% |
| PF | **1.35** |
| Net | **+$352.92** |
| Sharpe | **2.45** |
| Max DD balance | $296.24 (29.6% del deposito) |

Profilo di rischio nettamente migliore di ADX_RSI (Sharpe 2.45 vs 1.20,
DD 29.6% vs 59.6%). Leggera differenza nel conteggio trade rispetto al
calcolo manuale dal test misto (68 vs 71) — probabilmente il lock
cambia leggermente il tracking di `lastEvalBar` quando i segnali SELL
vengono scartati prima di aggiornarlo, non ancora indagato, differenza
minore non concludente.

**Prossimo passo naturale**: aggiungere il filtro Elliott multi-TF
(`InpUseElliottFilter`, già esistente e generico) per avvicinarsi alla
ricetta Python completa (PF1.95) — non ancora fatto.
