---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, portafoglio, correlazione, concorrenza, drawdown]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Portafoglio a 20 strategie (24/08)

## Perché

Su richiesta dell'utente: unire tutte le baseline trovate/riverificate
oggi in un unico portafoglio in euro reali, stessa disciplina del 16/08
(`portfolio_regime_sim_16-08.py`, da cui `simulate_portfolio_capped` è
riusato quasi verbatim): rischio fisso €10/trade, tetto lotti 0.10,
tetto diretto €40 sul rischio per trade, max 2 posizioni concorrenti.
`portfolio_expanded_24-08.py`, 20 strategie (le 5 già solide + 15
trovate/riverificate oggi con la migliore config verificata per
ciascuna), escluse deliberatamente TURTLE_SOUP (ribalta 3+ rifiuti, da
riverificare) e LDN_REVERSAL (campione troppo sottile).

## Risultato headline: positivo, ma trainato da una sola strategia

Conto €1000, max 2 posizioni concorrenti:

| | Retail | ECN |
|---|---|---|
| Trade eseguiti (su 11.264 candidati) | 743 | 743 |
| Net PnL | **+€2.725** | **+€4.383** |
| Drawdown massimo | 35.9% | 26.0% |

Numero grosso e positivo — ma **6-4 strategie su 16-20 sono NETTE
PERDENTI dentro il portafoglio**, pur essendo profittevoli in isolamento
oggi: LIQ_SWEEP è la peggiore in assoluto (-€207 retail, -€183 ECN,
nonostante fosse "doppiamente confermata" da sola), poi DONCHIAN_TURTLE
(-€130/-€111), DARVAS_BOX (-€79/-€73), EMA_PULLBACK (-€72/-€63). **SAR da
sola contribuisce più del netPnL totale del portafoglio** (+€1642 retail,
+€2195 ECN) — il risultato positivo non è un vero effetto di
diversificazione, è SAR che trascina tutto.

## Diagnosi: 8.426 trade scartati per "bucket pieno" su 11.264 candidati (75%)

Il meccanismo a 2 slot FIFO (chi arriva prima prende lo slot) funzionava
bene il 16/08 con 4-5 strategie di frequenza comparabile. Con 20
strategie di frequenza MOLTO diversa (SAR 2.606 segnali grezzi contro
EMA_PULLBACK 28, STRUCT_REACT 57), le strategie ad alta frequenza
(SAR/SAR_ADX20/MACD/ADX_RSI, tutte >1.400 segnali) occupano quasi sempre
i 2 slot per primi, lasciando alle strategie più selettive pochissime
occasioni reali di contribuire — e quando ci riescono, non è detto siano
i loro trade migliori (selezione per ordine di arrivo, non per qualità).

## Sweep di max_concorrenti: più slot = più profitto MA drawdown esplosivo

| max_concorrenti | netPnL retail | maxDD retail | strategie negative |
|---|---|---|---|
| 2 | +€2.725 | 35.9% | 6/16 |
| 4 | +€5.620 | 42.6% | 6/20 |
| 6 | +€8.241 | **57.0%** | 4/20 |
| 10 | +€10.999 | **93.2%** | 3/20 |
| 20 (nessun tetto) | **-€1.005** | **100.1%** | 9/18 |

Il profitto nominale sale con più slot, ma il drawdown sale MOLTO più
velocemente (non lineare) — e a 20 slot (nessun limite reale) il
portafoglio **esplode e va in perdita netta**, DD 100%. Questo è il
segnale più chiaro di tutta la giornata che molte delle 20 strategie
NON sono indipendenti: sono varianti dello stesso tipo di scommessa
direzionale (trend-following su XAUUSD 4h), e quando il tetto di
concorrenza si allenta abbastanza da farle sparare tutte insieme, il
rischio si somma invece di diversificarsi — la stessa identica lezione
della "correlazione/concentrazione delle perdite" già scritta nel
roadmap del progetto (P4.4), ora osservata con i numeri.

## Conclusione

Il portafoglio a 2 slot è ancora il più prudente (DD 35.9%/26.0%,
accettabile), ma **"più strategie buone in isolamento" non ha prodotto
un portafoglio più diversificato** — ha prodotto un portafoglio dominato
da una sola strategia (SAR) con diverse altre che si danneggiano a
vicenda competendo per gli stessi 2 slot. Il problema non è più "quali
strategie sono buone" (risolto oggi, 20 baseline verificate) — è
**come allocare il rischio tra loro**, un problema di correlazione e
priorità, non di parametri.

## Prossimi passi aperti

- **Analisi di correlazione vera** tra le 20 strategie (non solo
  guardare chi vince/perde nel bucket) — quali coppie si muovono
  insieme, quali sono genuinamente indipendenti. Non ancora fatta.
- **Criterio di priorità nel bucket** invece di FIFO puro (già segnalato
  come "non ancora testato" nella nota 16/08, mai affrontato da allora)
  — es. dare la precedenza al segnale con ER più alto, o a rotazione tra
  strategie invece che per ordine di arrivo.
- **Budget di rischio separato per strategia** (non un pool condiviso a
  2 slot) — architettura alternativa, ogni strategia ha la sua fetta di
  rischio indipendentemente dalle altre, mai provata.
- Rimuovere/ridurre il peso delle strategie ridondanti prima di
  aggiungerne altre (es. SAR_ADX20/SAR_FLIP sono varianti di SAR - quanto
  si sovrappongono davvero?).
- TURTLE_SOUP e LDN_REVERSAL non ancora inclusi (in attesa di
  riverifica) — andrebbero aggiunti dopo, non prima, di risolvere il
  problema di allocazione.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Filtro di Regime e Portafoglio 5 Strategie (16-08)]]
