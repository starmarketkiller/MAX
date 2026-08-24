---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, hull-suite, ml-adaptive-supertrend, buy-sell, regime, riverifica]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Riapertura di Hull Suite e ML Adaptive SuperTrend con gli ingredienti di oggi (25/08)

## Perché

Le due strategie erano rimaste "candidate borderline ECN-only, non
promosse" dal 17-24/08 (vedi [[NEXUS EA - Idee da Script TradingView Esterni (17-08)]]),
con una firma sospetta mai indagata fino in fondo: retail debole nella
prima metà storica (PF 0.92-1.02), forte nella seconda (rally 2023-2026)
— esattamente il pattern che oggi si è rivelato essere quasi sempre
rally-beta mascherato da un filtro simmetrico. Due ingredienti mai
applicati a queste due: (1) il **floor ATR** (introdotto lo stesso
24/08 ma dopo i test originali di Hull/ML SuperTrend), (2) lo **split
BUY/SELL con verifica sulla finestra laterale calendario** (2020-11→
2023-10), il protocollo diventato standard oggi per ogni caso simile.

## Hull Suite (length=25/Hma/4h) — pattern debole, non promossa

Con floor ATR aggiunto: simmetrica PF1.11 (m1=1.01/m2=1.22, 2/5
finestre) — leggero miglioramento dal floor ma resta debole.
BUY-only: **PF1.82** (m1=1.52/m2=2.17, n=147, 4/5 finestre) — sembra
un salto enorme, la stessa illusione vista tutto il giorno.

**Verifica laterale**: BUY n=12, PF**0.44**; SELL n=13, PF**0.99**.
Pattern debole su entrambi i lati — SELL non è chiaramente forte come
nei flip genuini di oggi (SAR SELL1.66, ADX_RSI SELL2.53), è solo
vicino al pareggio. **Non abbastanza per promuoverla**: il salto
BUY-only nell'aggregato resta presumibilmente rally-beta, non un
segnale nuovo genuino. Verdetto invariato: **non promossa**.

## ML Adaptive SuperTrend (factor=1.5/4h) — flip genuino, promossa a BUY-only

Con floor ATR: simmetrica PF1.14 (m1=0.93/m2=1.38, 3/5). BUY-only:
**PF1.94** (m1=1.33/m2=2.79, n=123, 4/5 finestre).

**Verifica laterale — qui il pattern è diverso e più convincente**:
BUY n=10, PF**0.24** (debole, come atteso); **SELL n=11, PF1.88** —
non vicino al pareggio come Hull Suite, ma **forte quanto i flip
genuini confermati oggi** (stessa fascia di SAR SELL1.66/ADX_RSI
SELL2.53/LIQ_SWEEP SELL4.07). Stesso criterio usato per promuovere
STRUCT_REACT come "flip genuino, non solo beta mascherato" — qui il
lato SELL non è debole nel laterale, è competitivo.

## Verdetto

**ML Adaptive SuperTrend promossa** a nuova baseline candidata
(BUY-only, 4h, factor=1.5, ER+floor 0.3, PF1.94 n=123) — stesso
livello di fiducia delle altre diversificatrici a campione sottile
(LIQ_SWEEP/STRUCT_REACT all'inizio), da confermare con più dati ma non
scartabile come le altre BUY-only rally-dipendenti. **Hull Suite resta
non promossa** — il pattern SELL-laterale è troppo debole (vicino al
pareggio, non chiaramente forte) per distinguerla da un semplice beta
mascherato.

Bilancio: primo caso in cui riaprire un verdetto "chiuso" prima
dell'inizio della disciplina laterale di oggi ha prodotto una vera
promozione, non solo una conferma del rifiuto — vale la pena
riconsiderare anche altri candidati "borderline ECN-only" archiviati
in precedenza con la stessa firma sospetta (debole 1ª metà, forte 2ª).

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Idee da Script TradingView Esterni (17-08)]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
