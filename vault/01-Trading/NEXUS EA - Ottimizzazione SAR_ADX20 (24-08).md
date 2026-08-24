---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar-adx20, ottimizzazione-individuale]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Ottimizzazione individuale SAR_ADX20 (24-25/08)

## Perché

Diciassettesima ottimizzazione — cluster trend-following, campione
enorme (BUY-only PF1.49, n=1000). Mai verificata sulla laterale né
spinta con trailing.

## Verifica laterale — campione ampio, conferma solida

BUY-only laterale: n=**83**, PF0.34, sumR=-54.3 — uno dei campioni
laterali più grandi verificati oggi (secondo solo a SAR stessa,
n=111), stessa direzione di tutte le altre. Perdita aggregata
significativa (-54.3R) in quella finestra da sola.

## Trailing: miglioramento modesto, robusto

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| BUY-only, target fisso 1.5/4.0 (nota) | 1.49 (1.35/1.64) | 5/5 | 1000 |
| **BUY + trailing 2.0×ATR** | **1.61 (1.16/2.15)** | 5/5 | 1000 |
| BUY + trailing 2.5×ATR | 1.52 (1.21/1.87) | 5/5 | 1000 |
| BUY + trailing 3.0×ATR | 1.57 (1.08/2.11) | 4/5 | 1000 |

2.0×ATR è la scelta migliore: PF più alto (+8%), 5/5 finestre come il
baseline. Sbilancia un po' verso la seconda metà (m1 1.35→1.16, m2
1.64→2.15) ma resta positivo su entrambe.

## Verdetto

**Adottato trailing 2.0×ATR** — miglioramento modesto ma pulito sul
terzo campione più grande testato oggi (n=1000). Correlata al cluster
(SAR/MACD/ecc.), da non sommare ciecamente in portafoglio. Non ancora
in MQL5.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
