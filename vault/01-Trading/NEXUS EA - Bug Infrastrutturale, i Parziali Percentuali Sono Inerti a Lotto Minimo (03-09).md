---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bug, infra, p0, partial-close, mql5]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — Bug infrastrutturale: TUTTI i parziali percentuali sono inerti a lotto minimo (03/09)

## Perché questa nota è separata (non solo un addendum PIVOT_WICK)

Scoperta durante l'analisi della batteria di test PIVOT_WICK (round
`d1`-`d3`, uscite), ma il bug è in `NXS_SplitTrade.mqh` e riguarda
**ogni strategia testata a lotto minimo (0.01)**, non solo PIVOT_WICK —
merita una nota propria per non restare sepolta. Classificazione
Master Roadmap: **P0** (integrità del test), non P4 (edge) — il
problema non è "il parziale non aiuta", è "il parziale non è mai stato
davvero testato".

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

## Non ancora verificato

- d3 (`InpUseVolumePartial`) ancora in corso — previsione: stesso esito
  nullo, stessa causa aritmetica. Da confermare quando finisce.
- Se un conto con lotto naturale più alto (es. 0.05-0.10, come nei test
  SAR "lotto naturale" già confermati) rende i parziali percentuali
  effettivamente operativi — plausibile (0.03 lotto ÷ P1 30% = 0.009 →
  arrotonda comunque a 0 con step 0.01; serve un lotto per cui
  `lotto × pct` superi almeno 0.005 per arrotondare a 0.01, quindi
  serve un lotto ≥ ~0.03-0.05 a seconda della percentuale) — non
  ricontrollato sui test SAR storici che menzionano parziali riusciti
  (`NXS_ManageVolumePartial`, commit 3bd6d82, era per SAR — lì il lotto
  potrebbe essere stato diverso da 0.01, da verificare).
- Nessuna modifica al codice fatta qui (solo lettura/analisi) — un fix
  plausibile (alzare a `MathCeil` invece di `MathFloor` quando il
  risultato sarebbe altrimenti sotto lo step minimo, o un floor sul
  volume minimo assoluto invece che sulla percentuale) richiede
  discussione esplicita prima di toccare `NXS_SplitTrade.mqh` (vedi
  [[feedback_no_live_mql5_without_asking]]).

## Collegamenti
[[NEXUS EA - PIVOT_WICK step2 e OneShotLevel Analizzati, Nessun Fix (03-09)]] ·
[[NEXUS EA - MASTER ROADMAP v3]] · [[MOC - Trading]]
