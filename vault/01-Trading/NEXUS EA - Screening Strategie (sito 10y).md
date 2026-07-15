---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, screening, riferimento]
created: 2026-07-12
updated: 2026-07-15
---

# Screening strategie — motore sito, ~10 anni XAUUSD

Dopo la scoperta dell'overfitting ([[NEXUS EA - Lezione Overfitting 3Y]]), sweep
sistematico di ogni strategia su `server/backtest.py` (dati Yahoo daily, ~3000
barre ≈ 10 anni) per trovare una regola generalizzabile invece di un parametro
tarato su una finestra corta.

## Scoperta principale: il filtro HTF è un booster universale
**8 config vincenti su 10** hanno il filtro HTF (allineamento al trend del
timeframe superiore) **acceso**. Non è un parametro fortunato per una strategia:
è una regola che alza l'edge su quasi tutto il portafoglio, su un orizzonte lungo.
Secondo pattern: **TP largo (4.0-4.5× ATR)** batte quasi sempre TP corto.

## Tabella di riferimento (baseline → miglior config trovata)

| Strategia | PF base → best | net (10y) | trade | Config vincente |
|---|---|---|---|---|
| BREAKOUT_ACC | 1.32 → **1.86** | +10.422 | 128 | SL1.0 · TP4.5 · **HTF✓** |
| OB_MIT | 1.45 → **1.80** | +3.048 | 70 | SL1.5 · TP4.0 · Trail2.5 |
| FVG_CONT | 1.24 → **1.66** | +10.848 | 208 | SL1.0 · TP4.5 · **HTF✓** · Trail2.5 |
| ORDER_BLOCK | 1.22 → **1.66** | +3.644 | 83 | SL1.0 · TP3.0 · **HTF✓** · Trail2.5 |
| MACD | 1.38 → **1.63** | +1.846 | 57 | SL2.0 · TP3.0 · **HTF✓** |
| TSI | 1.32 → **1.62** | +7.634 | 174 | SL1.5 · TP4.5 · **HTF✓** |
| ICHIMOKU | 1.21 → **1.54** | +2.794 | 72 | SL1.5 · TP4.5 |
| EMA_PULLBACK | 1.17 → **1.52** | +2.233 | 86 | SL1.5 · TP4.0 · **HTF✓** · Trail2.5 |
| ADX_RSI | 1.26 → **1.48** | +10.555 | 253 | SL1.0 · TP4.0 · **HTF✓** · Trail2.5 |
| BJORGUM | 2.47 (baseline) | — | <50 | campione troppo piccolo per sweep affidabile |
| RSI_DIV | 0.85 → **1.09** | +673 | 79 | SL1.0 · TP4.5 · HTF off — aggiunta 15/07, debole |
| CISD | mai >1.0 | -18 (best) | 18 | mai profittevole sul sito in nessuna config — aggiunta 15/07 |
| TURTLE_SOUP | mai >1.0 | -716 (best) | 63 | mai profittevole sul sito in nessuna config — aggiunta 15/07, conferma [[NEXUS EA - Principi]] #5 |
| ~~SAR~~ | ~~1.17 → 1.50~~ | — | — | ⚠️ **DATO INVALIDO** — il proxy `sig_sar()` del sito è identico a `sig_ema_pullback()` (verificato trade-per-trade), non testa Parabolic SAR. Vedi [[NEXUS EA - Motore Sito: Audit e Confronto 10Y]] |

Campioni più affidabili per numerosità: **ADX_RSI (253 trade)**, **FVG_CONT (208)**,
**TSI (174)**, **BREAKOUT_ACC (128)**.

## Applicato in v2.5.0
Divario trovato: ADX_RSI, EMA_PULLBACK, MACD, SAR avevano l'HTF filter **spento**
sull'EA mentre il sito lo vuole acceso. Corretto in v2.5.0 — vedi
[[NEXUS EA - Log Versioni]] per il dettaglio dei cambi e lo stato della validazione.

⚠️ **Aggiornamento 15/07**: il fix su SAR era basato su un test che, di fatto,
non testava mai la vera logica Parabolic SAR (bug del proxy sito, vedi sopra).
Il fix su MACD, ADX_RSI, EMA_PULLBACK resta valido come test (segnali reali),
ma solo MACD ha un edge raw confermato anche in esecuzione diretta 10y
(PF 1.38) — eppure fallisce su MT5 (-21.1R), quindi il problema lì è
probabilmente nell'esecuzione, non nel segnale. Dettaglio completo:
[[NEXUS EA - Motore Sito: Audit e Confronto 10Y]].

## Limite di questo screening (da tenere a mente)
Il motore del sito usa dati Yahoo daily e una logica semplificata rispetto
all'esecuzione reale su MT5 (broker, timeframe multipli, gestione posizioni).
Un edge trovato qui è un'**ipotesi da validare**, non una certezza — esattamente
come lo era il record dei 3 mesi. Il test che conferma o smentisce è sempre lo
stesso: MT5, 3 mesi **e** 3 anni, entrambi positivi.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Sito Backtest Lab - Note Tecniche]]
