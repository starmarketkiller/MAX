# Event Dataset v1 e Baseline Matching — metodologia (Phase 5.C/E)

Dati reali: `server/research_scripts/phase5/data/events_v1.csv` (8618 eventi) + `events_v1.meta.json`. Costruito da `server/research_scripts/phase5/build_events.py`, regole dichiarate EX-ANTE (prima di calcolare qualunque outcome).

## Conteggi per famiglia (su 4809 barre H4, 2019-02-03→2022-02-03)

| Famiglia | n | % barre | Note |
|---|---|---|---|
| PULLBACK | 3988 | 83.0% | **Calibrazione fallita** — vedi Limitazioni sotto |
| VOLATILITY_EXPANSION | 1784 | 37.1% | soglia 1.0×ATR (stessa di FROZEN_SIGNAL_SPEC_V1) |
| BREAKOUT | 724 | 15.1% | range N=20, offset [i-21,i-2] |
| SWEEP | 500 | 10.4% | estremo rolling N=20 |
| COMPRESSION_RELEASE | 482 | 10.0% | compressione ≥5 barre sotto il 20° percentile poi espansione |
| RETEST | 337 | 7.0% | entro 10 barre da un BREAKOUT |
| FAILED_BREAKOUT | 315 | 6.5% | 43% dei BREAKOUT falliscono entro 5 barre — plausibile |
| RECLAIM | 300 | 6.2% | entro 10 barre da uno SWEEP |
| DISPLACEMENT | 188 | 3.9% | soglia 1.5×ATR sul corpo (più stringente di vol-expansion) |

## Schema evento

`event_id, event_family, row_index, timestamp, direction, magnitude, observation_point, detector_provenance, confirmed_at_row_index[, level, swept_side, trend_context, breakout_row, sweep_row]`. Eventi a risoluzione ritardata (FAILED_BREAKOUT, RETEST, RECLAIM) portano `confirmed_at_row_index` distinto da `row_index` — l'osservazione iniziale e la conferma sono istanti diversi, mai confusi.

## Limitazioni/calibrazione trovate (onestà richiesta dal progetto)

1. **PULLBACK degenerato**: la soglia (ritracciamento ≥0.5×ATR contro un trend stabilito su 20 barre) si attiva sull'83% delle barre — troppo permissiva per essere un "evento" distintivo. Trattato nei risultati come nota di qualità, non come detector affidabile; il suo test event-alone (NO_EDGE) va letto con questo caveat, non come evidenza forte contro l'idea di pullback in generale.
2. **BREAKOUT_x_TREND_PERSISTENCE degenere**: la condizione (trend EMA allineato + persistenza ≥ mediana) è risultata vera per 724/724 BREAKOUT (100%) — nessuna capacità discriminante residua, l'interazione collassa esattamente sull'evento base. Segnala che "trend già allineato" è quasi tautologico per un breakout con questa definizione, non un condizionamento informativo.

## Baseline matching (metodologia E)

Per ogni evento/interazione: si individua la cella `(terzile_volatilità, terzile_trend, anno)` della barra evento (terzili calcolati UNA VOLTA sull'intero dataset, non per-evento). Il baseline è il pool di barre della STESSA famiglia-evento assenti (es. "non-BREAKOUT" per testare BREAKOUT) che condividono almeno una cella richiesta, valutate nella stessa direzione dell'evento con cui sono accoppiate. Non è un confronto con barre casuali indiscriminate.

**Valuta comune di confronto**: tutti i confronti evento-vs-baseline (anche per le 4 famiglie R-based: BREAKOUT/SWEEP/RECLAIM/RETEST) usano outcome ATR-normalizzati (non gli R-outcome nativi di `outcomes_v1.csv`), perché una barra di baseline non ha un "livello" naturale di rischio con cui costruire R — dichiarato esplicitamente per evitare di confrontare mele con pere.

**Caveat di indipendenza**: le osservazioni di baseline non sono pienamente indipendenti fra loro (barre adiacenti condividono percorsi di prezzo sovrapposti; una barra può comparire sia nel pool BUY sia nel pool SELL se rientra nelle celle richieste per entrambe le direzioni) — gli intervalli di confidenza Wilson/Beta-Binomial vanno quindi letti come indicativi, non come stima esatta di un campione i.i.d.; il segnale principale (RECLAIM, sezione K) è comunque così ampio (51% vs 75-81%, mai sovrapposto) da restare solido anche con questa cautela.
