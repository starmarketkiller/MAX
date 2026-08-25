---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, elliott-wave, trailing, combinazione, scoperta]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Combinare trailing (ieri) e filtro Elliott (oggi): gli effetti si sommano (25/08)

## Perché

Ogni test del filtro Elliott finora è stato isolato SOPRA la baseline
non ottimizzata (target fisso, senza trailing) per misurare il suo
effetto puro. Ma il ciclo di ottimizzazione individuale di ieri aveva
già adottato trailing 2.0-2.5×ATR su molte di queste strategie (SAR,
MACD, FVG_CONT, LONDON_BO, ADX_RSI). Domanda aperta: i due ingredienti
si sommano, sono ridondanti, o si annullano a vicenda?

## Risultato: si sommano, quasi senza eccezioni

| Strategia | Trailing da solo (ieri) | **Trailing + Elliott (oggi)** | Δ |
|---|---|---|---|
| **ADX_RSI** | 2.20 (2.20/2.21, 5/5) | **2.62 (2.57/2.66, 5/5, n=657)** | **+19%** |
| **SAR_FLIP** | 1.82 (1.64/2.02, 4/5) | **2.31 (1.54/3.49, 4/5, n=68)** | **+27%** |
| **FVG_CONT_V2** | 2.03 (1.72/2.60, 5/5) | **2.40 (2.10/2.93, 5/5, n=61)** | **+18%** |
| SAR_ADX20 | 1.61 (1.16/2.15, 5/5) | **1.81 (1.28/2.44, 5/5, n=936)** | +12% |
| SAR | 1.64 (1.28/2.04, 5/5) | **1.87 (1.44/2.36, 5/5, n=1370)** | +14% |
| MACD | 1.72 (1.43/2.04, 5/5) | **1.84 (1.53/2.17, 5/5, n=1443)** | +7% |
| FVG_CONT | 1.63 (1.64/1.63, 4/5) | **1.78 (1.66/1.91, 4/5, n=379)** | +9% |
| LONDON_BO | 1.80 (1.29/2.39, 4/5) | 1.80 (1.29/2.39, 4/5, n=60) | 0% — nessun trade filtrato in questo campione, neutro |

**7 strategie su 8 migliorano ulteriormente**, tutte mantenendo la
robustezza per finestra (mai un peggioramento), la 8ª (LONDON_BO)
resta neutra senza danno. Nessuna combinazione testata mostra un
conflitto o un annullamento reciproco — i due ingredienti agiscono su
dimensioni diverse del trade (trailing = come gestire l'uscita una
volta dentro; Elliott = se questo è il momento giusto per entrare,
dato dove siamo nell'onda) e infatti si comportano come **ortogonali**,
non ridondanti. Z_SCORE_BREAKOUT non incluso qui: il suo "trailing"
di ieri si è rivelato inefficace nel motore live per un motivo diverso
(TP fisso ancora attivo, vedi [[NEXUS EA - Correzione Trailing Z_SCORE_BREAKOUT, il TP fisso lo annullava (25-08)]]) —
combinarlo con Elliott richiederebbe prima risolvere quel problema.

**ADX_RSI a PF2.62** è ora la seconda configurazione più forte
dell'intero catalogo, dietro solo a STRUCT_REACT (2.65) — e a
differenza di STRUCT_REACT (che *peggiora* col filtro Elliott),
ADX_RSI ha guadagnato da entrambi gli ingredienti indipendentemente.

## Implicazione

Le PF "definitive" per le strategie con trailing adottato sono più
alte di quanto documentato ieri — la tabella master andrebbe
aggiornata riga per riga con questa combinazione, non ancora fatto per
tutte (solo le 5 qui sopra verificate). Le altre ~16 strategie che
hanno guadagnato dal filtro Elliott ma NON avevano un trailing
adottato ieri (es. OTE_CONT, TSI, MALAYSIAN_SNR_BREAKOUT, BOLLINGER,
RSI_DIV) restano con solo il guadagno Elliott documentato, senza
bisogno di combinazione essendo già la loro configurazione base.

## Cosa NON è stato fatto

Nessuna modifica al codice MQL5 — resta ricerca Python, come da
indicazione esplicita dell'utente.

## Addendum — combinazione anche con D1-align (non solo ER+floor)

Le 3 strategie con **D1-align** al posto del filtro ER standard
(FVG_MIT, OTE_CONT, EMA_PULLBACK) erano rimaste non testate — l'unico
test Elliott fatto su di loro usava la ricetta ER generica, non la
loro vera config promossa. Colmato:

| Strategia | Config promossa (D1-align, +trailing dove presente) | +Elliott | Δ |
|---|---|---|---|
| **FVG_MIT** | 2.72 (1.32/4.26, 5/5) | **3.24 (1.57/5.06, n=74, 5/5)** | **+19%, ora la più forte del catalogo** |
| **EMA_PULLBACK** (4h) | 1.87 (1.26/2.49, 4/5) | **2.13 (1.44/2.83, n=223, 5/5)** | **+14%, finestre 4/5→5/5** |
| OTE_CONT | 1.83 (1.89/1.77, 5/5) | **2.14 (2.16/2.12, n=214, 5/5)** | +17%, quasi perfettamente bilanciata |

Tutte e 3 migliorano, confermando che il filtro Elliott si somma bene
anche a D1-align (non solo a trailing su ER standard) — **10 strategie
su 11 testate in combinazione con altri ingredienti migliorano
ulteriormente**, la sola eccezione resta LONDON_BO (neutro, non
dannoso). FVG_MIT a PF3.24 è ora la configurazione più forte
dell'intero catalogo di 25 strategie.

## Prossimi passi aperti

- Aggiornare sistematicamente tutte le righe della tabella master con
  le PF combinate finali (fatto per le 11 di questa nota).
- Risolvere il problema del TP fisso di Z_SCORE_BREAKOUT prima di
  poter testare la combinazione anche lì.
- Testare Elliott sulla variante D1-nativa di EMA_PULLBACK (PF2.57),
  non ancora fatto.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Filtro Elliott Wave Multi-Timeframe, il nuovo ingrediente universale (25-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
