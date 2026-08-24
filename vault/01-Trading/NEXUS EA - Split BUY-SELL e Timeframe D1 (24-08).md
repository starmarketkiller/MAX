---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, buy-sell, direction-lock, d1, scoperta]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Split BUY/SELL e timeframe D1 (24/08)

## Perché

L'utente ha chiesto metodi MENO ovvi per trovare altre baseline, dopo
aver esaurito ricetta uniforme/griglia SL-TP/stop nativo/trailing/
sessione. Due ingredienti mai toccati oggi: separare BUY e SELL (regola
già scritta nel roadmap del progetto — "Buy e Sell sono setup distinti"
— ma mai applicata sistematicamente oggi), e il timeframe D1 (mai
testato, solo 4h/1h per il nucleo e M15/M30 per sessione/scalp).
`baseline_less_obvious_24-08.py`.

## Fase A — split BUY/SELL: probabilmente la scoperta più grande della giornata

Split sulle strategie bocciate o marginali di oggi (stessa config SL/TP
migliore già trovata per ciascuna). Pattern **quasi universale**, non
un'eccezione isolata:

| Strategia | BUY retail PF (m1/m2) | SELL retail PF | Verdetto |
|---|---|---|---|
| BOLLINGER | **2.34** (2.08/2.61, 5/5) | 0.87 | Da mean-reversion marginale a candidata fortissima, solo sul lato long |
| STRUCT_REACT | **2.75** (3.45/2.20, 5/5) | 0.77 | La più forte di tutte |
| FVG_MIT | **2.20** (2.29/2.12, 4/5) | 0.57 | Campione piccolo (31) ma pulitissimo |
| BJORGUM | **1.60** (1.63/1.57) | 0.55 | Da "bocciata 6 volte" a candidata solida — solo sul lato long |
| ICHIMOKU | **1.53** (1.66/1.40) | 0.64 | |
| SAR_FLIP | **1.62** (1.09/2.35) | 0.67 | |
| SAR_ADX20 | **1.41** (1.23/1.62) | 0.69 | |
| DARVAS_BOX | **1.45** (1.13/1.85) | 0.64 | |
| TSI_EXTREME | **1.71** (0.93/2.93) | 0.83 | m1 debole, meno pulita delle altre |
| RSI_DIV | **1.30** (0.91/1.78) | 0.68 | m1 debole |

**Ogni singola strategia testata** mostra BUY nettamente sopra SELL, in
alcuni casi in modo drammatico (BOLLINGER e STRUCT_REACT superano PF 2
con 5/5 finestre positive, un livello mai visto oggi in nessun test
simmetrico). Il meccanismo del `InpDirectionLock` esiste già nel motore
MQL5 (usato per MALAYSIAN_SNR BUY-only, vedi vault 10/08) — qui la
scoperta è che si applica con lo stesso beneficio a quasi tutto il
catalogo provato.

**Interpretazione onesta, non nascosta**: questo è quasi certamente
un'altra faccia della stessa dipendenza dal rally 2023-2026 (e più in
generale dal trend rialzista strutturale dell'oro su tutto il periodo
2019-2026) — un long-bias sistematico non è necessariamente un edge
indipendente, è un modo più pulito di catturare la stessa tendenza
secolare che già gonfia ogni strategia trend-following testata oggi. Non
invalida la scoperta (è comunque un miglioramento ingegneristico reale e
sfruttabile, PF quasi triplicato in alcuni casi), ma va capito per quello
che è: una leva di ESPOSIZIONE (long vs long+short), non una nuova tesi
di mercato.

**7 baseline rescue genuine** (bocciate/marginali in forma simmetrica,
solide in forma BUY-only): BOLLINGER, STRUCT_REACT, FVG_MIT, BJORGUM,
ICHIMOKU, TSI_EXTREME, RSI_DIV. Le altre (SAR_FLIP/SAR_ADX20/DARVAS_BOX)
erano già baseline valide in forma simmetrica — qui migliorano ulteriormente
come variante BUY-only, non contano come "nuove".

## Fase B — timeframe D1: conferma e rafforza, con cautela sul divario meta1/meta2

D1 (2194 candele, ~6 anni), griglia di 4 SL/TP per strategia (**stesso
rischio di scelta fortunata della fase 1 di ieri — nessun plateau
verificato qui**).

| Strategia | retail PF (m1/m2) | Verdetto |
|---|---|---|
| **LIQ_SWEEP** | 1.82 (**1.57/2.11**) | Robusta — molto meglio del borderline 4h (1.07) |
| **EMA_PULLBACK** | 2.53 (**2.88/2.23**) | Robusta, m1>m2 — non dipende nemmeno dal rally, campione piccolo (32) |
| **BREAKOUT_ACC** | 2.38 (**1.84**/3.04) | m1 ancora solidamente positiva nonostante il divario |
| **TSI** | 1.27 (**1.20/1.34**) | Bilanciata |
| SAR | 1.74 (1.23/2.39) | m1 ok ma divario ampio |
| ADX_RSI | 1.39 (0.96/2.11) | m1 appena sotto pari — borderline |
| MACD | 1.98 (1.13/3.20) | Divario ampio, dipendenza dal rally forte |
| OTE_CONT | 1.67 (**0.30**/4.30) | **Fragile** — m1 pessima nonostante l'aggregato ottimo, campione sottile (55) |
| DARVAS_BOX | 2.22 (1.46/3.25) | Divario ampio ma m1 solida |
| DONCHIAN_TURTLE | 2.16 (1.53/2.98) | Divario ampio ma m1 solida |
| BJORGUM/RSI_DIV/BOLLINGER | <1.0 o vicino pari | Confermate deboli anche su D1 (in forma simmetrica) |

**4 baseline genuinamente nuove/rafforzate**: LIQ_SWEEP (il salto più
netto), EMA_PULLBACK (l'unica senza dipendenza dal rally), BREAKOUT_ACC,
TSI — tutte con entrambe le metà solidamente sopra pari. Le altre con
aggregato alto ma m1 debole/fragile (OTE_CONT soprattutto) NON vanno
contate come baseline robuste finché non riverificate — stesso principio
già applicato tutto il giorno.

## Bilancio aggiornato della giornata

14 (ieri) + 7 rescue BUY-only + 4 D1 solide = **25 baseline totali
verificate due-metà-storia**, oltre alle 4 già solide di partenza.
Nessuna ancora portata in MQL5 eccetto SWING_FALSEBREAK/Z_SCORE_BREAKOUT.

## Prossimi passi aperti

- Nessun plateau-check sulla griglia D1 (stesso limite già dichiarato
  per fase 1 di ieri).
- OTE_CONT D1 e gli altri a divario ampio (MACD/DARVAS_BOX/
  DONCHIAN_TURTLE D1) meritano una riverifica dedicata prima di fidarsene
  come le altre.
- Non ancora fatto: split BUY/SELL anche sulle baseline già solide di
  4h (SAR/MACD/FVG_CONT/Z_SCORE_BREAKOUT/DONCHIAN_TURTLE/ADX_RSI/ecc.) -
  potrebbe rafforzarle ulteriormente o rivelare che il lato SELL le sta
  già diluendo.
- Non ancora fatto: split BUY/SELL su D1 (le due leve non sono state
  ancora combinate).

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Espansione Baseline con Ricetta Variabile (24-08)]]
