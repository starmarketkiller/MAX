---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, drawdown, sizing, martingale, scalp]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Drawdown per strategia e sizing dinamico in drawdown (24/08)

## Perché

Tre domande dirette dell'utente: (1) qual è il drawdown massimo per
strategia, non solo a livello di portafoglio? (2) ha senso aumentare la
size quando una strategia è in drawdown contenuto? (3) perché lo stesso
non salverebbe le SCALP_*? `drawdown_and_sizing_24-08.py`.

## 1. Drawdown massimo per strategia (in R, size fissa, sequenza reale dei trade)

| Strategia | n trade | PF retail | maxDD (R) |
|---|---|---|---|
| STRUCT_REACT (BUY-only) | 50 | 2.65 | **7.5R** |
| LIQ_SWEEP (BUY-only) | 89 | 1.73 | **7.8R** |
| DONCHIAN_TURTLE (BUY-only) | 340 | 1.56 | 29.5R |
| ADX_RSI (BUY-only) | 728 | 1.77 | 62.3R |
| SAR (BUY-only) | 1471 | 1.51 | 98.3R |

**Il drawdown in R scala con la frequenza dei trade, non solo con la
qualità (PF)** — SAR ha il PF più basso del gruppo ma il drawdown più
alto in assoluto, semplicemente perché fa 30 volte più trade di
STRUCT_REACT. Implicazione pratica: le strategie ad alta frequenza
(SAR/ADX_RSI/SAR_ADX20/DONCHIAN_TURTLE, il "cluster" già identificato)
richiedono un rischio per trade più PICCOLO in euro per mantenere lo
stesso drawdown in valuta reale delle diversificatrici a bassa
frequenza — un'informazione diretta per il sizing del portafoglio,
non ancora applicata.

## 2. Aumentare la size in drawdown contenuto — funziona sulle strategie buone

Meccanismo testato: size normale (1×R); se il drawdown corrente dal
picco è SOTTO una soglia "contenuta" (3R o 5R), il trade successivo
rischia 1.5×-2.0×R invece di 1×.

| Strategia | Baseline | +1.5x se DD<3R | +2.0x se DD<3R | +1.5x se DD<5R |
|---|---|---|---|---|
| STRUCT_REACT | +45.1R (DD 7.5R) | **+63.4R** (DD 8.5R) | **+70.1R** (DD 9.6R) | +67.0R (DD 9.6R) |
| LIQ_SWEEP | +48.9R (DD 7.8R) | **+58.3R** (DD 9.0R) | +48.1R (DD 10.1R) — **peggiora** | +62.5R (DD 9.7R) |

**Funziona, con cautela**: su STRUCT_REACT ogni combinazione migliora
(fino a +55% di rendimento con un aumento di drawdown modesto, 7.5R→
9.6R). Su LIQ_SWEEP il moltiplicatore 2.0x PEGGIORA il risultato
rispetto a 1.5x — la leva non è "più è meglio", va calibrata per
strategia, stessa disciplina di tutto il resto di oggi. Meccanismo
distinto dal bucket a slot condivisi del portafoglio (qui si aumenta
il RISCHIO PER TRADE su una singola strategia, non gli slot
concorrenti) — coerente con la richiesta dell'utente di "non rubare
slot ad altre strategie".

## 3. Perché NON salverebbe le SCALP_* — dimostrato, non solo spiegato

Stesso identico meccanismo su SCALP_RANGE_BRK (config migliore trovata
ieri, SL4.0/TP8.0 overlap, PF0.71 — **sotto 1, aspettativa negativa**):

| Config | Risultato |
|---|---|
| Baseline 1x | **-691.2R** (DD 758.7R) |
| +1.5x se DD<3R | -683.5R (DD 759.8R) |
| +2.0x se DD<3R | -674.8R (DD 760.9R) |
| +1.5x se DD<5R | -684.9R (DD 760.9R) |

**Il sizing non cambia quasi nulla** — la perdita resta enorme e il
drawdown resta enorme in ogni variante. La ragione è matematica, non
un'opinione: il sizing (dinamico o fisso) scala l'AMPIEZZA di ogni
trade, ma non cambia l'aspettativa per trade. Se ogni trade ha valore
atteso negativo (PF<1), aumentare la size su ALCUNI trade non "recupera"
nulla — moltiplica proporzionalmente le stesse perdite sistematiche.
Il sizing dinamico funziona SOLO quando c'è un edge reale sottostante da
amplificare (STRUCT_REACT/LIQ_SWEEP, PF>1) — su un sistema a valore
atteso negativo è matematicamente equivalente ad aumentare la posta su
un gioco già perdente, non una protezione.

**Nota su "chiudere veloce e proteggerci"**: un'uscita più rapida
(stop più stretto, time-stop più corto) NON risolve il problema di
fondo per le SCALP_* - è esattamente quello che è già stato provato
(vedi [[NEXUS EA - Verdetto Finale SCALP (24-08)]] e [[NEXUS EA - Riscrittura SCALP con Ricerca Esterna (24-08)]]):
stop più stretti PEGGIORANO il PF (i costi fissi pesano di più su
rischio più piccolo), non lo migliorano. La "protezione" giusta per un
sistema senza edge non è un'uscita più veloce o un sizing più
intelligente — è non tradarlo.

## Prossimi passi aperti

- Applicare il sizing dinamico (drawdown contenuto → size maggiore)
  alle altre diversificatrici buone (OTE_CONT, FVG_MIT, EMA_PULLBACK,
  DONCHIAN_TURTLE) — testato solo su 2 finora.
- Usare il drawdown-in-R per strategia per calibrare il rischio per
  trade in euro nel portafoglio (le strategie ad alta frequenza
  meritano un rischio per trade più piccolo) - non ancora fatto.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Portafoglio a 20 Strategie (24-08)]]
[[NEXUS EA - Verdetto Finale SCALP (24-08)]]
