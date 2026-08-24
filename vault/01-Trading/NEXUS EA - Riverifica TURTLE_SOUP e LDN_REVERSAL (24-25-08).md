---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, turtle-soup, ldn-reversal, riverifica, plateau-check]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Riverifica delle 2 provvisorie: TURTLE_SOUP e LDN_REVERSAL (24-25/08)

## Perché

Ultime due voci del catalogo — entrambe marcate "provvisoria, riverifica
raccomandata" nella tabella master. Nessuna delle due era mai stata
sottoposta a un **plateau-check** (sensibilità ai parametri) prima
d'ora — il test che ha già salvato Hull Suite/ML SuperTrend da un
overfitting nascosto in altre occasioni. Metodo: ricreare esattamente
la ricetta originale (stessa funzione dell'engine), riprodurre il
numero noto per escludere derive di script, poi variare il parametro
chiave su una griglia per vedere se il risultato è un plateau o una
cella isolata fortunata.

## LDN_REVERSAL — promossa da provvisoria a confermata (con cautela sul campione)

Ricetta nota: stop strutturale (swing 10 barre) + floor 0.3×ATR sul
rischio minimo, target RR fisso. Riprodotto esattamente: **PF1.28
(m1=1.31/m2=1.25), n=31, 4/5 finestre** — identico al numero registrato,
nessuna deriva di script.

**Griglia swing_N × RR** (16 combinazioni):

| RR\\swing | 7 | 10 | 14 | 20 |
|---|---|---|---|---|
| 2.0 | 0.83 (0.90/0.75) | 0.93 (0.79/1.09) | 1.06 (0.90/1.24) | 1.02 (0.73/1.40) |
| 2.5 | 1.04 (1.15/0.95) | 1.17 (0.99/1.37) | 1.21 (0.91/1.56) | 1.16 (0.68/1.76) |
| **3.0** | 1.26 (1.39/1.14) | **1.28 (1.31/1.25)** | 1.46 (1.09/1.88) | 1.39 (0.82/2.11) |
| 3.5 | 1.21 (1.35/1.07) | 1.20 (1.23/1.17) | 1.20 (0.58/2.05) | 1.27 (0.64/2.06) |

Due segnali incoraggianti: (1) **plateau chiaro per RR≥2.5** su tutti e
4 gli swing — non è una cella isolata, RR2.0 è sistematicamente debole
ovunque (coerente con un win-rate reale intorno al 30-35%, la stessa
matematica breakeven vista tutto il giorno sulle SCALP); (2) **la
config originale (swing10/RR3.0) è anche il punto più bilanciato di
tutta la griglia** (m1=1.31/m2=1.25, quasi identiche) — swing14/RR3.0
ha un PF aggregato più alto (1.46) ma è molto più sbilanciato
(0.58-1.09 contro 1.56-2.11), segno che lì il PF è trainato dalla
seconda metà, non un miglioramento pulito. Non è stata scelta a
posteriori per il PF massimo, il che riduce il sospetto di overfitting.

BUY/SELL (campione minuscolo, solo indicativo): BUY n=14 PF2.59, SELL
n=17 PF0.59 — un'asimmetria reale ma il campione è troppo piccolo
(7-8 trade per metà) per applicare la verifica laterale standard di
oggi, quindi non testata separatamente.

**Verdetto**: promossa da "provvisoria" a **confermata con cautela sul
campione** — il plateau attraverso 16 combinazioni e il fatto che il
punto scelto sia anche il più bilanciato (non il più alto) sono buoni
segnali. Resta comunque un campione assoluto piccolo (n=31) rispetto
alle altre 18 baseline di oggi — da tenere d'occhio mentre si
accumulano dati, non ancora al livello di fiducia di ADX_RSI o SAR.

## TURTLE_SOUP — resta provvisoria, nuovi dubbi emersi

Ricetta nota: stop dal wick dello sweep (`_turtle_soup_sl_tp`, stessa
funzione del motore reale) + floor 0.3×ATR, target 4.0×ATR fisso,
simmetrica. Riprodotto esattamente: **PF1.14 (m1=1.04/m2=1.25), n=271**
— identico al numero registrato.

**Griglia target ATR** (6 valori):

| TP×ATR | 3.0 | 3.5 | 4.0 | 4.5 | 5.0 | 6.0 |
|---|---|---|---|---|---|---|
| PF (m1/m2) | 1.01 (0.90/1.15) | 1.14 (1.02/1.26) | **1.14 (1.04/1.25)** | 1.18 (1.06/1.32) | 1.12 (1.02/1.23) | 1.15 (1.10/1.20) |
| Finestre | 2/5 | 4/5 | 2/5 | 3/5 | 3/5 | 3/5 |

Il plateau in PF aggregato (1.01-1.18 su 6 target) è di per sé
rassicurante — non è un valore isolato — **ma la robustezza per
finestra è debole ovunque**: mai 5/5, quasi sempre 2-3/5. Guardando le
5 finestre della config nota (TP4.0) singolarmente: **1.27, 0.68, 0.99,
0.94, 2.19** — 3 finestre su 5 sono flat-o-negative, e il PF aggregato
positivo è largamente trainato dall'ultima finestra (2.19, la più
recente).

**Asimmetria BUY/SELL non ancora spiegata**: BUY n=127 PF1.75, SELL
n=144 PF0.70 — un'asimmetria reale e con campioni ampi stavolta (non
sottili). Verifica laterale sul BUY: n=12, PF0.78, sumR=-2.4 — leggermente
negativo ma non un crollo drammatico come nei flip netti di oggi
(SAR/ADX_RSI), campione comunque troppo sottile per un verdetto.

**Verdetto**: **resta provvisoria** — il plateau sul target conferma
che non è overfitting sul singolo TP, ma la fragilità per-finestra (3/5
sotto pari) e l'asimmetria BUY/SELL non confermata sono due segnali di
cautela nuovi, non c'erano nella nota di ieri. Non promuoverla oltre,
non darle priorità nel backlog di porting MQL5 finché non emergono più
dati o un ingrediente che risolva l'instabilità per-finestra.

## Bilancio

Con questa riverifica si chiude la revisione di **tutte le 21
strategie candidate** del 24-25/08 (19 verificate + le 2 provvisorie
appena riesaminate). LDN_REVERSAL passa a "confermata con cautela",
TURTLE_SOUP resta "provvisoria" — 20 strategie ora ragionevolmente
solide, 1 ancora da maneggiare con attenzione.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Espansione Baseline con Ricetta Variabile (24-08)]]
[[NEXUS EA - Nuovi Ingredienti (Stop Struttura, Allineamento D1, Giorno) 24-08]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
