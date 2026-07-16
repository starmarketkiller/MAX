---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: ORDER_BLOCK
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: ORDER_BLOCK

## Tipo
SMC/order block

## Trigger meccanico
Impulso (body>1.2 ATR) 3-10 barre fa + retest del blocco con rifiuto (chiusura oltre il midpoint). Da v2.4.2: richiede conferma reazione (structure+react engine).

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.0× ATR · **TP**: 3.0× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 563 setup, 3W/3L/1BE, WR 50.0%, expR +0.068, **PF 1.97**
- **3 anni**: 130 setup, 3W/5L/0BE, WR 37.5%, expR -0.202, **PF 0.24**

## Stato
❌ NON VALIDATA — confermato su campione ampio: **96 trade reali su 8
segmenti** (2016+2019-2025). Solo 2 anni OK (2021, 2024), il resto
CRITICA/DEBOLE/POCHI_DATI. Non più "campione piccolo": il pattern base
(impulso + retest) non ha un edge stabile su XAUUSD D1 in questa forma.

## Fix reale 16/07: aggiunta struttura esterna (g_structH1, prima mai letta)
Stesso trigger di base di OB_MIT (che lo richiama internamente). Applicata
la teoria interna/esterna dell'utente ([[NEXUS EA - Struttura Interna vs Esterna — Framework]]):
l'impulso+retest ora richiede anche che il trend **esterno** (H1,
`g_structH1` — calcolata ogni tick ma mai letta da nessuna strategia prima
d'ora) confermi la direzione. Test A/B sul sito con la config reale
(D1+HTF): **PF 1.50→1.77, DD 5.85%→3.94%**, campione dimezzato (80→36
trade) — miglioramento di qualità consistente su quasi ogni TF/config
provato, non un caso isolato. Applicato sia al sito che a MQL5
(`NXS_Strat_OrderBlock`). **Non ancora validato su MT5 reale.**

Nota di fedeltà: sul sito il test verificava il trend esterno al momento
dell'impulso (serie storica); in MQL5 `g_structH1` è solo lo stato
corrente, quindi il controllo reale è "il trend H1 conferma ORA la
direzione del retest" — stessa idea, punto di verifica leggermente
diverso per limite strutturale di MQL5 (nessuno storico per barra).

Resta candidato Tier 1 per il framework Setup Buy-Sell (le "5 tipologie
di Engulfing" di Secret of 4.11) per un refactor più profondo in futuro.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Ob Mit]] · [[NEXUS EA - Fonte Secret of 4111 (Ali Yusoff)]]
