---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, master-slave, bias, riverifica, motore-vero]
created: 2026-08-12
updated: 2026-08-12
---

# Riverifica "Pipeline Gerarchica Master/Slave" sul motore vero (12/08)

## Perché questa riverifica

Il piano proposto dall'utente cita: *"usare BREAKOUT_ACC come 'Master' per
dettare il bias direzionale ha aiutato strategie come SAR, FVG_CONT, TSI e
MACD"*, basato sui "tuoi test precedenti" — cioè `phase3c_bias_pipeline.py`
(10/08, Metodo 2 in [[NEXUS EA - Ricerca Combinazioni Multi-Strategia (10-08)]]).

Controllato lo script: usa un **simulatore proprio** (`_simulate()`), non
`run_backtest`, con SL/TP piatto hardcoded (1.5×/3.0× ATR) per OGNI slave,
ignorando il profilo/SL/TP reale di ciascuna strategia. Stessa categoria di
problema già trovata e corretta per `ensemble_engine_search.py` e
`msnr_retest_gates.py` — e sono esattamente i 5 filtri di regime che, una
volta riverificati sul motore vero, sono risultati TUTTI inaffidabili
(vedi [[NEXUS EA - Riverifica su Storico Ampliato (11-08)]], §2). Il
Master/Slave non era mai stato riverificato dopo quella scoperta.

## Metodo

Aggiunto `master_bias=` a `run_backtest()` (`server/backtest.py`), stesso
principio già usato per `regime_filter`: precompute di un bias persistente
(l'ultimo segnale non-zero del master resta valido finché non si inverte),
poi gate su `_find_signal()` — **ogni slave gira col proprio SL/TP/profilo
reale**, non un ATR fisso per tutte. Stesso TF=4h master+slave dello script
originale (per testare la stessa identica claim, non una versione diversa).
XAUUSD, IS(60%)/OOS(40%) + walk-forward a 5 finestre, baseline vs biased.

Smoke test di validazione del meccanismo: SAR+bias riduce i trade
(700→593) e sposta il PF in modo plausibile prima di lanciare la
riverifica completa — meccanismo confermato funzionante.

## Risultati

| Strategia | | IS PF/n/dd | OOS PF/n/dd | Walk-forward (PF/n × 5 finestre) |
|---|---|---|---|---|
| SAR | baseline | 1.07/422/30.95% | 1.22/276/12.4% | 1.27/136 · 0.91/142 · 1.10/140 · 1.35/135 · 1.14/140 |
| SAR | +bias | **1.13**/350/**21.02%** | **1.26**/241/16.6% | **1.39**/110 · **1.03**/106 · 1.10/130 · 1.29/118 · **1.17**/122 |
| FVG_CONT | baseline | 1.16/297/16.72% | 1.29/198/13.48% | 1.35/95 · 1.21/95 · 0.95/93 · 1.35/86 · 1.17/103 |
| FVG_CONT | +bias | **1.34**/192/**10.57%** | **1.43**/148/10.49% | **1.53**/63 · **1.34**/64 · **1.18**/56 · **1.50**/67 · **1.34**/73 |
| TSI | baseline | 1.00/253/39.38% | 1.24/169/11.09% | 2.11/79 · 0.80/86 · 0.66/85 · 1.29/81 · 1.13/86 |
| TSI | +bias | 0.90/145/25.13% | **1.35**/89/8.68% | 1.70/39 · 0.72/49 · 0.69/54 · 1.27/41 · 1.40/46 |
| MACD | baseline | 1.16/295/21.74% | 1.65/205/10.57% | 1.48/90 · 0.87/95 · 1.27/85 · 1.70/94 · 1.62/100 |
| MACD | +bias | 1.12/258/18.22% | 1.64/182/14.02% | 1.50/78 · 0.88/75 · 1.06/83 · 1.52/85 · 1.78/87 |

(grassetto = migliora rispetto al baseline sulla stessa metrica)

## Lettura onesta — risultato MISTO, non un fallimento totale come i regime filter

A differenza dei 5 filtri di regime (falliti TUTTI senza eccezioni), qui il
quadro è diviso:

- **FVG_CONT — miglioramento reale e coerente.** Ogni singola finestra
  walk-forward migliora col bias attivo (5/5 finestre sopra 1.0, contro
  4/5 del baseline), IS e OOS migliorano insieme, drawdown IS quasi
  dimezzato (16.7%→10.6%). Il fatto che il miglioramento sia sistematico
  su OGNI finestra (non solo in media) è il segnale più convincente
  raccolto finora per un vettore "extra-strategia" in questa sessione.
- **SAR — miglioramento reale ma più modesto.** IS e OOS migliorano
  entrambi, drawdown IS scende (31.0%→21.0%) ma quello OOS sale
  (12.4%→16.6%). Walk-forward passa da 4/5 a 5/5 finestre profittevoli.
  Coerente con un vero effetto, non rumore, ma meno netto di FVG_CONT.
- **TSI — nessun beneficio reale.** IS peggiora (1.00→0.90, sotto
  pareggio), il pattern walk-forward resta instabile in modo identico
  (3/5 finestre sopra 1.0 in entrambi i casi, con gli stessi minimi
  intorno a 0.7). L'OOS migliora ma non basta a bilanciare un IS peggiore
  e una walk-forward che non cambia struttura.
- **MACD — sostanzialmente neutro.** OOS invariato (1.65→1.64), IS
  leggermente peggiore, walk-forward 4/5 in entrambi i casi. Nessun
  beneficio misurabile. Da ricordare inoltre che MACD è già segnalata
  **CRITICA sull'esecuzione reale MT5** (vedi tier di rischio in
  `NXS_Profile_Risk()`) indipendentemente da questo test — un bias di
  Master non risolve quel problema.

**Avvertenza sul calo di campione**: il filtro di bias taglia il 30-45%
dei trade (naturale, è un gate aggiuntivo che scarta i segnali
controtrend). Per FVG_CONT questo non inficia la lettura — il
miglioramento è coerente su ogni finestra, non un effetto media su un
campione ridotto. Per TSI/MACD invece il campione più piccolo rende il
quadro già debole ancora meno conclusivo.

## Conclusione

La claim del piano ("ha aiutato SAR, FVG_CONT, TSI e MACD") **non regge
per tutte e 4** come genericamente affermato: FVG_CONT e SAR mostrano un
miglioramento reale e riproducibile sul motore vero; TSI e MACD no. Prima
di costruire infrastruttura Master/Slave nell'EA, ha senso limitare
l'ambito a FVG_CONT (+ eventualmente SAR) come slave, non a tutte e
quattro come nel piano originale. Resta comunque un lavoro architetturale
non banale: il master (BREAKOUT_ACC) dovrebbe girare continuamente in
background nell'EA anche quando non genera un proprio segnale operativo,
solo per alimentare il bias — un componente nuovo, non presente
nell'attuale `NEXUS_EA_v2.mq5`.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Ricerca Combinazioni Multi-Strategia (10-08)]] ·
[[NEXUS EA - Riverifica su Storico Ampliato (11-08)]]
