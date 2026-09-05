---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, p0, benchmark, buy-hold, metodologia]
created: 2026-09-05
updated: 2026-09-05
---

# NEXUS EA — il vero benchmark è buy&hold, e quasi tutto quello confermato oggi lo perde (05/09)

## Perché — obiezione dell'utente, corretta

Tutti i test di oggi (MACD, BOLLINGER, STRUCT_REACT, ADX_RSI, FVG_CONT)
sono **BUY-only o BUY-dominanti**, su una finestra in cui GOLD è salito
del **+125.5%** (da $1939.31 il 01/09/2023 a $4373.78 al 14/08/2026,
dato Dukascopy M15). L'obiezione: se una strategia fa solo BUY in un
mercato che sale sempre, un PF>1 non dimostra nessun edge — dimostra
solo che era esposta al trend. Il benchmark giusto non è "PF sopra 1",
è **quanto avrebbe reso restare semplicemente investiti (buy&hold)
sullo stesso periodo, con lo stesso lotto**.

## Calcolo

Buy&hold 0.01 lot GOLD, 01/09/2023 → 14/08/2026 (limite dei dati
cache, 12 giorni prima del ToDate reale dei test):

- Prezzo: $1939.31 → $4373.78 (+2434.47 punti = **+$2434.47** a $1/punto/0.01 lot, rapporto confermato empiricamente sui CSV di oggi)
- **Max drawdown lungo il percorso: $1628.41** (dal picco $5586.02 al minimo $3957.61, intorno al 30/06/2026) — anche solo stare fermi non era senza rischio
- Calmar (net/maxDD) del buy&hold: **1.49**

## Confronto con tutto quello testato oggi

| Strategia | Net | % del Buy&Hold | Max DD | Calmar | Risk-adjusted vs B&H |
|---|---|---|---|---|---|
| **Buy & Hold** | $2434.47 | 100% | $1628.41 | 1.49 | — |
| FVG_CONT H4 nudo | $2655 | **109%** | n/d | n/d | probabile meglio (unico che batte anche in assoluto) |
| MACD H4 Overlap-only | $2088.06 | 86% | $584.22 | **3.57** | **MEGLIO** — stesso ~86% del rendimento con 1/3 del rischio |
| MACD H4 nudo | $1975.49 | 81% | n/d | n/d | — |
| ADX_RSI D1 nudo | $1676.00 | 69% | n/d | n/d | — |
| STRUCT_REACT H4 nudo | $1560.22 | 64% | $1109.18 | 1.41 | leggermente peggio |
| BOLLINGER H4 BuyOnly nudo | $352.92 | **14%** | $343.96 | 1.03 | peggio |
| BOLLINGER H4 BuyOnly+Overlap | $68.01 | **3%** | $153.40 | 0.44 | molto peggio |

## Interpretazione

- **FVG_CONT** resta l'unico caso pulito: batte il buy&hold anche in
  valore assoluto, quindi ha probabilmente un vero contributo oltre
  al trend (da confermare con un DD preciso, non ancora calcolato).
- **MACD Overlap-only** è il secondo caso onesto: cattura "solo"
  l'86% del rendimento disponibile ma con **un terzo del drawdown**
  del semplice stare fermi — qui la gestione del rischio (SL, uscita
  a 40 barre, filtro sessione) aggiunge davvero valore anche se il
  PF da solo non lo diceva. Coerente con
  [[NEXUS EA - Il Filtro Sessione Era su un Percorso di Esecuzione Diverso (04-09)]].
- **STRUCT_REACT** è nella media-bassa: leggermente peggio del
  buy&hold anche risk-adjusted — "confermata positiva" era vero alla
  lettera (PF1.29>1) ma fuorviante come giudizio di qualità.
- **BOLLINGER** è il caso più netto: cattura solo il 3-14% del
  rendimento disponibile. Le etichette "confermata (H4 solo)" e
  "miglior Sharpe di tutta l'indagine" scritte in precedenza restano
  vere sulle LORO metriche interne, ma **non reggono il confronto con
  il fare niente**. Da ripensare se vale la pena tenerla nel nucleo
  demo così com'è.

## Correzione di metodo per tutti i test futuri

D'ora in poi, ogni strategia BUY-only o BUY-dominante testata va
confrontata con il buy&hold dello stesso identico periodo (net e
Calmar), non solo con PF/Sharpe/Recovery Factor calcolati in
isolamento. Un PF>1 non è più sufficiente per etichettare un
risultato "confermato positivo" — serve superare (o almeno avvicinare
risk-adjusted) il benchmark passivo.

## Non ancora fatto

- Max DD non calcolato per ADX_RSI D1, MACD H4 nudo, FVG_CONT H4 —
  servirebbe per completare la tabella Calmar.
- Non applicato lo stesso confronto alle strategie confermate PRIMA
  di oggi (SAR, EMA_PULLBACK) — probabile che vada rifatto anche lì.
- Benchmark calcolato solo su GOLD/XAUUSD con i dati M15 disponibili
  fino al 14/08 (12 giorni prima del vero ToDate 26/08) — differenza
  minima, non ricalcolata con dati più recenti.

## Collegamenti
[[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[NEXUS EA - MASTER ROADMAP v3]] · [[MOC - Trading]]
