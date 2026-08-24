---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, buy-sell, sistematico, scoperta]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Sweep sistematico BUY/SELL sulle baseline rimaste (24/08)

## Perché

Continuazione del test sistematico di ingredienti. Split BUY/SELL (già
promosso a LIQ_SWEEP e STRUCT_REACT) applicato a tutte le altre 14
baseline del nucleo/cluster/altre solide, stessa config SL/TP nota per
ciascuna. `buysell_sweep_24-08.py`.

## Risultato: pattern quasi universale, ma verificato genuino (non beta)

**13 strategie su 14 migliorano nettamente sul lato BUY**, con entrambe
le metà della storia sopra pareggio. A differenza dei rescue BUY-only
bocciati ieri sera (BJORGUM/FVG_MIT-simmetrica/TSI_EXTREME), qui il
campione BUY è grande (60-1471 trade) e la finestra più vecchia (F0,
quasi tutte partono da 2020-10/11, l'inizio reale del dataset filtrato)
mostra PF già solidamente sopra 1 — non un artefatto del rally 2024-2026.

**Verifica di controllo** (stesso standard usato per la diagnosi di
ieri sera, non solo fidarsi di meta1/meta2): ADX_RSI-BUY, tutte le 5
finestre CON LE DATE:

| Finestra | Periodo | n | PF |
|---|---|---|---|
| F0 | 2020-11 → 2024-05 | 145 | 1.27 |
| F1 | 2024-05 → 2024-12 | 145 | 2.17 |
| F2 | 2024-12 → 2025-04 | 145 | 2.02 |
| F3 | 2025-04 → 2025-10 | 145 | 1.92 |
| F4 | 2025-11 → 2026-05 | 148 | 1.60 |

Campione ampio (145 trade) anche nella finestra più vecchia/laterale,
PF genuinamente sopra pareggio lì — non beta mascherato.

## Tabella completa

| Strategia | Simmetrica | BUY (m1/m2, n) | SELL (m1/m2, n) |
|---|---|---|---|
| TSI | 1.25 | **2.03** (1.97/2.10, n=134) | 0.63 (0.62/0.65, n=137) |
| MALAYSIAN_SNR_BREAKOUT | 1.58 | **1.93** (1.83/2.04, n=75) | troppo pochi (19) |
| ADX_RSI | 1.27 | **1.77** (1.92/1.63, n=728) | 0.80 (0.83/0.77, n=593) |
| SAR_FLIP | 1.40 | **1.78** (1.40/2.27, n=76) | 0.68 (0.80/0.57, n=30) |
| FVG_CONT_V2 | 1.47 | **1.68** (1.34/2.15, n=65) | troppo pochi (4) |
| AMD_CONT | 1.42 | **1.62** (1.26/2.06, n=137) | 0.65 (0.66/0.63, n=27) |
| LONDON_BO | 1.31 | **1.60** (1.71/1.49, n=60) | 0.83 (1.18/0.53, n=32) |
| DARVAS_BOX | 1.30 | **1.58** (1.44/1.73, n=338) | 0.65 (0.78/0.53, n=108) |
| DONCHIAN_TURTLE | 1.30 | **1.56** (1.47/1.67, n=340) | 0.68 (0.74/0.62, n=113) |
| SAR | 1.21 | **1.51** (1.36/1.69, n=1471) | 0.79 (0.72/0.86, n=887) |
| FVG_CONT | 1.30 | **1.51** (1.35/1.69, n=396) | 0.68 (0.79/0.58, n=107) |
| SAR_ADX20 | 1.21 | **1.49** (1.35/1.64, n=1000) | 0.82 (0.72/0.94, n=610) |
| MACD | 1.46 | 1.58 (1.54/1.63, n=1191) | 1.07 (0.78/1.41, n=307) — miglioramento modesto |
| BREAKOUT_ACC | 1.17 | **1.33** (1.19/1.48, n=274) | 0.75 (0.79/0.71, n=85) |

## Interpretazione

Questo è un fenomeno di scala diversa dai singoli rescue di ieri sera:
**praticamente TUTTO il catalogo trend-following su XAUUSD ha un
lato SELL strutturalmente debole**, non solo 2-3 casi isolati. La
spiegazione più plausibile resta la stessa di ieri (tendenza rialzista
strutturale dell'oro su tutto il periodo 2019-2026, non solo il rally
2023-2026) — ma qui il campione è troppo grande e troppo ben
distribuito nel tempo per liquidarlo come puro beta: **730-1470 trade
BUY con PF>1 anche nella finestra più vecchia** è un'evidenza molto più
forte di quella disponibile ieri sera sui casi thin.

**Implicazione per il cluster correlato**: dato che tutte le strategie
del cluster (SAR/MACD/FVG_CONT/DONCHIAN_TURTLE/ADX_RSI/DARVAS_BOX/
SAR_ADX20/BREAKOUT_ACC) migliorano allo stesso modo passando a BUY-only,
la loro correlazione reciproca probabilmente NON cambia (stesso
meccanismo sottostante, solo un lato rimosso) — il problema di
allocazione del portafoglio resta, ma ora con configurazioni
individualmente migliori.

## Verdetto

**13 configurazioni aggiornate a BUY-only** nella tabella master (tutte
tranne MACD, dove il miglioramento è troppo modesto per giustificare la
perdita del lato SELL, che qui rimane marginalmente positivo).

## Prossimi passi aperti

- Aggiornare la tabella master con tutte le nuove config BUY-only.
- Riverificare la matrice di correlazione con le versioni BUY-only (non
  ancora fatto) — potrebbe cambiare leggermente i numeri anche se non la
  sostanza.
- EMA_PULLBACK, OTE_CONT, FVG_MIT (le diversificatrici con D1-align) non
  ancora testate con lo split BUY/SELL.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
[[NEXUS EA - Diagnosi Onesta del BUY-only (24-08)]]
