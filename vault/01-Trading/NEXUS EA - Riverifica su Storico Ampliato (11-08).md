---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, riverifica, dukascopy, walk-forward]
created: 2026-08-11
updated: 2026-08-11
---

# Riverifica di tutte le scoperte "buone" su storico ampliato (11/08)

Richiesta esplicita dell'utente: "ho paura che abbiamo insistito su
strategie che erano già ottimali" — riverifica sistematica di ogni
scoperta positiva della sessione 10-11/08, prima di decidere cosa
portare nel codice.

## Cache Dukascopy aggiornata
Locale ferma a 63.245 candele M15 (dal 2022-03-04, 1.618 giorni). In
produzione erano già disponibili **105.304 candele, dal 2019-05-20**
(2.636 giorni, +63%). Copiata nella cache locale prima di ririflottare
qualsiasi cosa — script: `wide_window_reverify.py`, `BARS=110000` per
usare tutto il nuovo storico (i vecchi script erano tarati su
60000/70000, insufficienti ora).

## 1. Le tre "buone confermate" — reggono, non perfette

| Strategia | OOS PF (nuovo) | OOS PF (vecchio) | Walk-forward |
|---|---|---|---|
| MACD | 1.65 (n=205) | 1.63 | 4/5 |
| TURTLE_SOUP | 1.45 (n=161) | 1.66 | 3/5 |
| BREAKOUT_ACC | 1.48 (n=165) | 1.71 | 3/5 |

Tutte e tre confermate positive, ma **nessuna è perfetta** al
walk-forward su più dati — utile ricordarlo prima di trattarle come
"blindate". TURTLE_SOUP e BREAKOUT_ACC scendono leggermente rispetto
al vecchio storico, resta comunque un edge reale.

## 2. Filtri di regime — tutti e 5 confermati, alcuni migliorano

| Filtro | OOS filtrato (nuovo) | OOS baseline (nuovo) | OOS filtrato (vecchio) |
|---|---|---|---|
| BREAKOUT_ACC+STRONG_TREND | 1.59 | 1.48 | 1.84 |
| LIQ_SWEEP+STRONG_TREND | 1.84 | 1.33 | 2.17 |
| SAR+WEAK_TREND | 1.29 | 1.21 | 1.47 |
| TSI+WEAK_TREND | **1.82** | 1.26 | 1.02 (marginale prima) |
| FVG_CONT+STRONG/WEAK_TREND | 1.39 | 1.29 | 1.32 |

Tutti e 5 continuano ad aiutare rispetto al proprio baseline —
robustezza confermata su dati quasi doppi. TSI+WEAK_TREND migliora
molto (era il più marginale, ora il più forte del gruppo).

## 3. MALAYSIAN_SNR_V2_RETEST — si indebolisce parecchio

| TF | OOS PF (nuovo, senza gate) | OOS PF (vecchio) | Walk-forward (nuovo) | Walk-forward (vecchio) |
|---|---|---|---|---|
| 1h | 0.91 | 0.81 | 2/5 | — |
| 30m | 1.04 | 1.24 | **2/5** | 3/5 |

**Questo è il caso che l'utente temeva**: con più dati, RETEST (senza
il gate fuori-range) si avvicina al pareggio su entrambi i TF, e il
walk-forward a 30m peggiora da 3/5 a 2/5. Non era un errore tenerla
nella ricerca — era comunque un'ipotesi motivata (91% di retest dopo
rottura, verificato) — ma **non è pronta per il demo**: il segnale
grezzo non regge quanto sembrava sul campione più piccolo. Il gate
fuori-range specifico non è stato riverificato qui (richiederebbe
rifare `msnr_retest_gates.py` sul nuovo storico) — da fare se si vuole
ancora considerarla.

## 4. CRT — confermata in modo schiacciante, la più solida di sempre

| TF | OOS PF | n totale IS+OOS | Walk-forward |
|---|---|---|---|
| 4h | 1.25 | 1.889 | **5/5** |
| 1h | 1.16 | 5.761 | **5/5** |
| 30m | 1.25 | 11.710 | **5/5** |

**15/15 finestre positive su tre timeframe**, su quasi 20.000 trade
totali. Non è più "promettente" — è la scoperta più statisticamente
solida di tutta la sessione, confermata due volte (storico vecchio e
nuovo) con lo stesso esito. Nessun altro test di questa sessione si
avvicina a questo livello di conferma.

## 5. MALAYSIAN_SNR_V2_STAGE1/STAGE3 — confermato: nessun edge

STAGE1: OOS PF 0.76 (n=36). STAGE3: OOS PF 0.45 (n=17). Campioni ancora
piccoli anche con più storico (la rarità è strutturale, non un limite
di dati) — invariato rispetto alla diagnosi precedente.

## Conclusione — cosa ha retto, cosa no

**Confermato solido**: le tre buone, i 5 filtri di regime, **CRT
(soprattutto)**.
**Ridimensionato**: MALAYSIAN_SNR_V2_RETEST — non pronta per il demo
senza ulteriore lavoro (il gate fuori-range specifico non ancora
riverificato su questo storico).
**Confermato negativo**: STAGE1/STAGE3.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]] ·
[[NEXUS EA - Config Demo 15 Strategie (10-08)]] ·
[[NEXUS EA - Ricerca Combinazioni Multi-Strategia (10-08)]]
