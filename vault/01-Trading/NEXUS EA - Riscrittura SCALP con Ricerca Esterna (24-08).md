---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, scalp, ricerca-esterna, costi-dominanti, verdetto-finale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Riscrittura SCALP con ricerca esterna (24/08)

## Perché

Su richiesta esplicita dell'utente dopo il verdetto negativo di prima
("riscriviamole per l'edge, cerca anche online"): non un altro filtro
sul segnale esistente, ma una riscrittura del segnale stesso informata
da ricerca reale.

## Ricerca

Due ricerche web (contenuto per lo più promozionale/blog, nessun
backtest rigoroso pubblico trovato — i numeri di win-rate citati NON
sono presi per buoni, solo il meccanismo strutturale, confermato da
fonti indipendenti tra loro):
- L'overlap London-New York (12:00-16:00 UTC) è la finestra di massima
  liquidità per l'oro — spread più stretti, volume più alto.
- "Liquidity Sweep Reversal" durante l'overlap è il pattern citato più
  spesso come edge di scalping strutturale (non un indicatore, uno
  sweep di livello + rientro).
- Una fonte nota esplicitamente che un segnale che funziona
  nell'overlap si comporta diversamente in sessione asiatica — la
  sessione conta, non è dettaglio.

Fonti: [mql5.com/en/blogs/post/770488](https://www.mql5.com/en/blogs/post/770488),
[fxnx.com/en/blog/session-session-scalping-your-precision-guide](https://fxnx.com/en/blog/session-session-scalping-your-precision-guide),
[zayecapitalmarkets.com/london-new-york-overlap-session-2](https://zayecapitalmarkets.com/london-new-york-overlap-session-2/)

## Test 1 — restringere le SCALP_* esistenti all'overlap (non riscrittura, controllo)

`scalp_session_rewrite_24-08.py`. La restrizione aiuta in modo
misurabile e consistente (es. SCALP_RANGE_BRK retail 0.31→0.42, ECN
0.66→0.78) ma **resta sempre sotto pareggio** — conferma che il
problema è il segnale sottostante, non (solo) la finestra oraria.

## Test 2 — riscrittura vera: liquidity sweep reversal a scala M15, ristretta all'overlap

`scalp_liquidity_sweep_rewrite_24-08.py`. Segnale NUOVO (non una
variante di RSI/EMA/Bollinger): sweep di uno swing a 15-30 barre M15
(non i 20/15 barre H1 di SWING_FALSEBREAK, scalati alla granularità
giusta) + rientro, stop oltre il wick, target R:R 1:2, ristretto
all'overlap. **Risultato: peggiore delle SCALP_* originali**, PF
0.15-0.61 su tutte le combinazioni provate (3 ampiezze di swing × 2
finestre orarie).

**Diagnosi quantitativa, non solo il verdetto**: isolato il caso
migliore (swing 30/10, overlap) — risk_dist mediano **$3.45**, costo
tipico retail **$2.37** (il 69% dello stop!), win rate grezzo
**32.3%** contro il 33.3% di pareggio per un R:R 1:2 — **il segnale
non ha edge nemmeno prima dei costi**, e i costi lo affondano
ulteriormente. Due problemi che si sommano, non uno.

## Verdetto finale

**Rewrite genuino tentato, non solo un altro filtro — anche questo
fallisce**, con una causa quantificata: a M15 su XAUUSD con questa
struttura di costi (spread+slippage retail ~$2.4), qualunque stop
strutturale ancorato a uno swing di poche ore produce un rapporto
costo/rischio troppo sfavorevole per essere economico, indipendentemente
da quanto sia buona l'idea di mercato dietro (qui: liquidity sweep,
un concetto reale e usato professionalmente a scale più larghe — vedi
SWING_FALSEBREAK su H1, che INVECE funziona, PF1.29). **La differenza
non è l'idea, è la scala**: lo stesso meccanismo di sweep+rientro
funziona su H1 (stop di alcuni dollari, ore di durata) e non su M15
(stop di pochi dollari, minuti di durata) per lo stesso motivo per cui
CRT (stop ancorato al wick di una candela) ha sempre avuto la stessa
saga di costi dominanti.

**Chiuso definitivamente**: 7 tentativi indipendenti su due sessioni
(TF, ampiezza stop ×2 direzioni, timing di uscita, regime-filter ×2
scale, restrizione di sessione, riscrittura completa del segnale) -
nessuno produce edge sfruttabile per XAUUSD scalping a M15 con questo
motore di costi. Non un problema di ricetta ma di struttura: i costi
retail fissi non permettono economia a questa scala temporale su
questo strumento.

## Addendum 24/08 (2) — "allarghiamo lo stop?" verificato con una griglia completa

Domanda diretta dell'utente dopo il verdetto, testata con una griglia
SL 1.5→8.0×ATR (TP sempre 2× lo SL) sulle 4 SCALP_* originali, 24h e
overlap:

| SL/TP | SCALP_RANGE_BRK retail (24h) | ECN (24h) |
|---|---|---|
| 1.5/3.0 | 0.40 | 0.72 |
| 2.0/4.0 | 0.51 | 0.80 |
| 3.0/6.0 | 0.66 | 0.89 |
| **4.0/8.0** | **0.73** | **0.92** |
| 5.0/10.0 | 0.74 (m2=**1.03**) | **0.90** |
| 6.0/12.0 | 0.73 | 0.86 |
| 8.0/16.0 | 0.66 | 0.75 |

**Sì, allargare aiuta molto — fino a un punto**: plateau netto a
SL4.0-5.0×ATR/TP8.0-10.0×ATR (non un picco isolato, tre configurazioni
vicine danno risultati simili), poi la curva si inverte e peggiora di
nuovo oltre SL6. Al plateau, ECN sfiora il pareggio (0.90-0.92) e la
seconda metà della storia lo supera persino (m2=1.03) — ma il **retail
non lo raggiunge mai** (0.73-0.74 il massimo).

**Il problema di fondo**: a quella larghezza di stop (4-5×ATR M15, tipicamente
$15-25 su XAUUSD), il trade non è più uno scalp — è un trade che può
restare aperto ore o giorni aspettando un target 8-10×ATR, con un
trigger di ingresso a scala M15 ma una gestione a scala swing. A quel
punto conviene usare una strategia PROGETTATA per quella scala
(DONCHIAN_TURTLE/BREAKOUT_ACC/ecc., già in catalogo, già validate a
livelli PF 1.3-1.8) invece di allargare artificialmente lo stop di un
segnale nato per essere veloce.

**Risposta diretta**: allargare lo stop è la leva giusta in direzione,
ma non basta da sola a rendere le SCALP_* profittevoli sui costi retail
— aiuta a metà strada, non fino in fondo, e nel farlo trasforma la
strategia in qualcosa che non è più "scalping".

## Prossimi passi aperti

- Se si vuole riprendere lo scalping, servirebbe uno strumento con
  spread assoluto molto più piccolo rispetto ai movimenti tipici a M15
  (es. un cross forex maggiore, non oro) — fuori scope oggi (nessun
  dato Dukascopy reale per altri simboli, solo XAUUSD in cache).
- Alternativa: scalare la stessa idea (liquidity sweep) a M30/H1 con
  stop più ampi — ma a quel punto è SWING_FALSEBREAK, già in catalogo
  e già validata.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Verdetto Finale SCALP (24-08)]]
