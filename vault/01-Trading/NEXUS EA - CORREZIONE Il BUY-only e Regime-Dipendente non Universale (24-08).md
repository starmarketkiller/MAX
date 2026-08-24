---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, buy-sell, regime, correzione, metodologia]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — CORREZIONE: il "BUY-only" è regime-dipendente, non universale (24/08)

## Perché

L'utente ha rimesso in dubbio, giustamente, lo sweep sistematico BUY/SELL
appena riportato come "13/14 migliorano": se il dataset è in gran parte
un rally, un lato BUY vincente non è un dato convincente da solo — va
testato su altre finestre o altri mercati prima di fidarsene. Niente
altro mercato con dati Dukascopy reali di qualità comparabile è
disponibile (solo XAUUSD è cache locale; BTCUSD/EURUSD via Yahoo danno
solo ~2 anni, 2024-2026, che è ESSO STESSO dentro la finestra "rally" —
non un test indipendente utile, onestamente scartato). La verifica
migliore possibile con i dati disponibili: isolare la finestra
**genuinamente laterale già classificata il 15/08** (2020-11→2023-10,
oro +4.4%/+1.2% nei due sotto-periodi, "quasi 3 anni... hanno affondato
tutte le strategie trend-following") e guardare SOLO lì, non
nell'aggregato.

## Risultato: la finestra laterale RIBALTA il verdetto — è SELL a vincere lì

| Strategia | BUY nella finestra laterale | SELL nella finestra laterale |
|---|---|---|
| ADX_RSI | PF **0.23** (n=63) | PF **2.53** (n=70) |
| SAR | PF **0.55** (n=111) | PF **1.66** (n=110) |
| TSI | PF **0.39** (n=13) | PF **1.73** (n=15) |
| DONCHIAN_TURTLE | PF **0.59** (n=24) | PF **1.90** (n=11) |
| LIQ_SWEEP | PF **0.68** (n=12) | PF **4.07** (n=11) |
| STRUCT_REACT | PF **0.87** (n=4) | PF **2.62** (n=10) |

**Pattern universale e opposto** a quello trovato nell'aggregato: nella
finestra laterale, SELL domina su TUTTE le 6 strategie controllate,
spesso in modo drammatico (ADX_RSI: PF0.23 vs PF2.53). Il verdetto "13/14
migliorano con BUY-only" del messaggio precedente era vero
nell'AGGREGATO 2019-2026 (a maggioranza rialzista) ma **nascondeva un
flip di regime reale**: BUY vince nei trend rialzisti (2019-2020,
2023-2026), SELL vince nel laterale (2020-2023) — non è che SELL sia
"rotto", è che il campione aggregato lo annega nella parte rialzista
più numerosa.

## Perché il controllo precedente (F0 equal-count) non l'aveva visto

Il controllo di prima su ADX_RSI-BUY (F0 = 2020-11→2024-05, n=145,
PF1.27) usava una finestra a CONTEGGIO uguale, che mescolava insieme la
finestra laterale (dove BUY perde, PF0.23) con l'inizio del rally 2023-
2024 (dove BUY vince forte) — la media dei due nascondeva la debolezza
vera. **Stessa identica trappola già diagnosticata ieri sera per
BJORGUM/FVG_MIT/TSI_EXTREME**, qui riapparsa in una forma più subdola
perché il campione era abbastanza grande da sembrare convincente.
Lezione rinforzata: le finestre equal-count non equal-calendario
possono ingannare anche con centinaia di trade, non solo con manciate.

## Cosa significa per il resto della giornata

- Le config "BUY-only" della tabella master (13 strategie) restano
  valide come descrizione dell'AGGREGATO 2019-2026, ma **non sono la
  scoperta di un "lato buono" strutturale** — sono un modo di catturare
  meglio l'esposizione al trend rialzista dominante nel periodo
  disponibile, esattamente il sospetto originale dell'utente.
- STRUCT_REACT resta il caso meglio caratterizzato: era già stato
  descritto onestamente come "flip di regime", non come edge
  unidirezionale — la nuova verifica lo conferma pienamente (SELL
  2.62 nel laterale, coerente con quanto già scritto).
- **L'opportunità reale non è BUY-only statico, è un direction-lock
  CONDIZIONATO al regime**: BUY quando il mercato è in trend (ER alto),
  SELL quando è laterale (ER basso) — non ancora costruito/testato,
  ma è la conclusione naturale di questa verifica.

## Addendum 24/08 (2) — OTE_CONT/FVG_MIT/EMA_PULLBACK: stessa direzione, campione troppo sottile per confermare

Split BUY/SELL con verifica laterale immediata (non rimandata) sulle 3
diversificatrici rimaste:

| Strategia | BUY aggregato | BUY laterale | SELL laterale |
|---|---|---|---|
| OTE_CONT | PF2.13 (n=85) | PF0.00 (n=**10**) | PF19.31 (n=**5**) |
| FVG_MIT | PF2.27 (n=24) | PF0.00 (n=**1**) | PF1.32 (n=**6**) |
| EMA_PULLBACK | PF1.56 (n=77) | PF0.00 (n=**4**) | PF1.32 (n=**8**) |

Stessa direzione delle altre 6 (SELL relativamente più forte nel
laterale) ma campioni troppo sottili (1-10 trade) per confermare o
smentire con fiducia — a differenza di ADX_RSI (63-728 trade nella
stessa finestra). **Non contate come conferma né come smentita** — la
config BUY-only per queste 3 resta quella che era: valida
nell'aggregato 2019-2026, di natura incerta rispetto al regime, senza
prova né a favore né contro sulla dipendenza dal rally per mancanza di
campione.

## Prossimi passi aperti

- Costruire e testare un direction-lock regime-condizionato (BUY se
  ER≥soglia trend, SELL se ER<soglia laterale) su ADX_RSI/SAR/TSI/
  DONCHIAN_TURTLE/LIQ_SWEEP — non ancora fatto, è il test naturale dopo
  questa scoperta.
- Riverificare TUTTE le 13 configurazioni BUY-only della tabella master
  con lo stesso isolamento a finestra laterale prima di considerarle
  definitive — fatto solo per 6 finora.
- Il tentativo di verifica su altro mercato è rimasto inconcludente per
  mancanza di dati di qualità comparabile (solo 2 anni via Yahoo per
  BTCUSD/EURUSD) — non un test vero, onestamente scartato, non riprovato
  finché non c'è una fonte dati migliore.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
[[NEXUS EA - Sweep Sistematico BUY-SELL (24-08)]]
[[NEXUS EA - Riverifica Walk-Forward 5 Finestre e Dipendenza da Regime (15-08)]]
