---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sizing, partial-close, mql5]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — I parziali percentuali sono aritmeticamente impossibili a lotto minimo (03/09)

## Correzione (03/09, dopo commento dell'utente)

Titolo e framing originali dicevano "bug infrastrutturale" — l'utente
ha giustamente corretto: **non è un bug, è un vincolo fisico**. 0.01 è
già il lotto minimo/step del simbolo, non esiste una frazione più
piccola da chiudere; il codice si comporta correttamente rifiutando lo
split invece di mandare un ordine sotto il minimo (che il broker
respingerebbe comunque). Resta comunque un vincolo di test/sizing da
conoscere: vedi sotto la conferma empirica che con lotto sufficiente
(0.02) il meccanismo funziona davvero.

## Perché questa nota è separata (non solo un addendum PIVOT_WICK)

Scoperta durante l'analisi della batteria di test PIVOT_WICK (round
`d1`-`d3`, uscite): a 0.01 lotto (lo standard di quasi tutto lo
screening estivo) nessun parziale percentuale di default può mai
scattare, per **ogni strategia**, non solo PIVOT_WICK — merita una nota
propria per non restare sepolta. Non è integrità del test nel senso di
un bug (P0) — è un limite di sizing da tenere presente quando si
interpretano risultati storici "il parziale non ha cambiato nulla" a
lotto minimo: quel risultato è nullo per costruzione, non una prova che
il parziale non aiuti.

## La scoperta

`d1_atrpartial` (`InpEnableSplit=true`) e `d2_fixedpip`
(`InpUseFixedPipPartial=true`, `InpFixedPipPartialPips=100`) danno
**risultati identici al centesimo alla baseline `c1`** (503 trade,
PF0.79, net -546.74, DD 606.53) — non simili, IDENTICI. Per d1 la causa
immediata è che `InpEnableSplit` ha già default `true` (vedi nota
PIVOT_WICK principale). Per d2 no: `InpUseFixedPipPartial` ha default
`false`, quindi il flag ha davvero cambiato qualcosa di attivo — eppure
zero differenza nel risultato. Tracciata la causa nel codice:

```mql5
// NXS_SplitTrade.mqh:189-190 (FixedPipPartial), stesso pattern per
// ATR P1/P2 (righe 124-125) e VolumePartial (righe ~256-257)
double part = _nxs_split_normalize(g_sym, vol * InpFixedPipPartialPct);
if(part >= minVol && (vol - part) >= minVol){ ... propone il parziale ... }
```

`_nxs_split_normalize` arrotonda per difetto allo step di volume
(`MathFloor(raw/step)*step`, step tipico 0.01). Con `vol=0.01` (lotto
usato in TUTTI questi test, confermato nei deal CSV) e una percentuale
di split <100% (default: ATR-P1=30%, ATR-P2=50% del resto,
FixedPipPartial=50%, VolumePartial=50%):

```
part = floor(0.01 × 0.30 / 0.01) × 0.01 = floor(0.30) × 0.01 = 0
part = floor(0.01 × 0.50 / 0.01) × 0.01 = floor(0.50) × 0.01 = 0
```

`part` è sempre `0`, la condizione `part >= minVol (0.01)` è sempre
falsa → **il parziale non viene MAI proposto, per nessuna percentuale
di default, su nessuno dei 4 meccanismi, a lotto minimo**. Non è un
problema di soglia di prezzo/volume mai raggiunta (quelle si valutano
correttamente) — è aritmetica: a lotto minimo non esiste una frazione
<100% che sopravviva all'arrotondamento allo step.

## Meccanismi coinvolti (tutti in `NXS_SplitTrade.mqh`)

| Meccanismo | Input percentuale | Default | Verificato inerte a lotto min. |
|---|---|---|---|
| ATR split P1 | `InpTP1_Pct` | 30% | Per aritmetica, non ancora testato in isolamento oggi |
| ATR split P2 | `InpTP2_Pct` | 50% del resto | Idem |
| Fixed-pip partial | `InpFixedPipPartialPct` | 50% | **Sì — d2 oggi, risultato identico a c1** |
| Volume-spike partial | `InpVolPartialPct` | 50% | Da confermare (d3 in corso), stessa aritmetica |

## Perché è più grave di un singolo test sprecato

Il lotto fisso minimo (0.01, tipicamente `InpDataCollectionLot` o
lotto naturale su conto piccolo) è **lo standard usato per quasi tutto
lo screening dell'estate** (Data Collection Mode, tutti i test
"nudi"/isolati per strategia). Qualunque conclusione storica del tipo
"il parziale non ha aiutato/non ha cambiato nulla" ottenuta a lotto
0.01 con le percentuali di default **non ha mai davvero testato il
parziale** — non è un risultato negativo, è un risultato nullo
travestito da negativo. Da rivedere quali note storiche si basano su
questo (ricerca futura, non fatta qui — questa nota si limita a
documentare il meccanismo).

## Conferma empirica — a 0.02 lotto il meccanismo funziona davvero (trovata cercando la risposta a "con 0.02/0.05 è stato fatto?")

Due report mai analizzati, già presenti nella cartella del terminal
dal 01-02/09 (prima di questa sessione): `nxs_emapb_step33_lot02_partial`
e `nxs_emapb_step34_lot02_partial_fixed` — EMA_PULLBACK, lotto fisso
`InpEMAPBFixedLot=0.02`, `InpTP1_Pct=0.50` (50% di 0.02 = 0.01, valido:
sopravvive all'arrotondamento). Confermato nei deal CSV: posizioni
0.02 chiuse in due tranche da 0.01 (es. apertura 0.02 alle 16:00,
chiusura parziale 0.01 alle 16:51 a target, poi il resto 0.01 chiuso
più tardi a SL) — il meccanismo scatta davvero a questo lotto.

| | step33 | **step34 (fix ATR-TF)** |
|---|---|---|
| Trade | 198 | 170 |
| PF | 0.90 | **1.22** |
| Net (2023-2026) | -264.85 | **+691.14** |
| Expectancy | -1.34 | **+4.07** |
| Max DD balance | 825.43 | 636.56 |

Stessa identica config tra i due — la differenza è il commit `8c197fe`
("Fix: ATR d'ingresso registrato dal timeframe sbagliato + state mai
riconciliato nel Tester") applicato tra le due passate. Con l'ATR
corretto, EMA_PULLBACK+partial(0.02 lotto) passa da sotto pareggio a
PF1.22 netto positivo su ~3 anni. **Non batte comunque la baseline
nuda già nota di EMA_PULLBACK** (PF1.41 senza filtri, tabella master
24/08) — quindi il partial a 0.02 lotto non è un miglioramento rispetto
al non fare nulla, ma è la prima prova diretta che il meccanismo, di
per sé, è sano quando i numeri gli permettono di scattare.

## Non ancora verificato

- d3 (`InpUseVolumePartial`, PIVOT_WICK a 0.01) ancora in corso —
  previsione: stesso esito nullo del d1/d2, stessa causa aritmetica.
- Non ancora testato PIVOT_WICK a 0.02-0.05 lotto con questi stessi
  meccanismi (i risultati storici trovati sopra sono per EMA_PULLBACK,
  non per PIVOT_WICK) — se si vuole valutare i parziali su PIVOT_WICK
  serve rilanciare `d2`/`d3` con un lotto più alto, non fatto qui.
- Nessuna modifica al codice fatta in questa sessione (solo lettura/
  analisi) — un'eventuale modifica per rendere i parziali utilizzabili
  anche a lotto minimo (es. chiudere l'intera posizione invece di una
  frazione quando la frazione arrotonderebbe a zero) richiede
  discussione esplicita prima di toccare `NXS_SplitTrade.mqh` (vedi
  [[feedback_no_live_mql5_without_asking]]).

## Collegamenti
[[NEXUS EA - PIVOT_WICK step2 e OneShotLevel Analizzati, Nessun Fix (03-09)]] ·
[[NEXUS EA - MASTER ROADMAP v3]] · [[MOC - Trading]]
