---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fvg-cont, bug, entry-score, gate-mode, metodo]
created: 2026-09-08
updated: 2026-09-08
---

# NEXUS EA — Step7 ancora identico: la vera causa è NXS_ResolvedEntryThreshold, non un `input` mancante (08/09)

## Il test

Dopo il fix di `InpMinEntryScore` (08/09, `input` aggiunto,
ricompilato 01:33:50 — vedi
[[NEXUS EA - Step6 Ancora Identico, Bug Indipendente su InpMinEntryScore (08-09)]]),
rilanciato `nexus_fvgcont_step7_regimescore75_minscorefixed_3y`
(PID reale 7928, 01:36:31→~04:3x). L'.ex5 usato è confermato
post-fix (timestamp 01:33:50, coerente col compile).

## Risultato: identico al centesimo, per la QUARTA volta

168 trade, net $2635.26, PF 1.92, DD 12.42%/22.79% — bit-identico a
step2/4/5/6. Ogni singolo trade FVG_CONT (168/168) mostra ancora
punteggio 70.0 nel commento.

## Causa reale: non un `input` mancante, ma una formula di soglia con leniency di sessione

Stavolta il fix di `InpMinEntryScore` **ha funzionato** — il valore
75 arriva davvero a `g_run_MinEntryScore`. Il problema è a valle:
`NXS_ResolvedEntryThreshold()` (`NXS_Execution.mqh:696-703`) non usa
mai direttamente `g_run_MinEntryScore` come soglia finale:

```cpp
double NXS_ResolvedEntryThreshold(){
   double globalTh = (double)g_run_MinEntryScore;
   double sessionTh = InpUseSessions ? NXS_SessionMinScore(g_session) : globalTh;
   if(InpGateMode <= 0) return MathMax(globalTh, sessionTh);
   if(InpGateMode == 1) return MathMax(sessionTh, globalTh - 5.0);   // <- questo è il path attivo
   if(InpGateMode == 2) return MathMin(globalTh, sessionTh);
   return MathMax(40.0, MathMin(globalTh, sessionTh) - 10.0);
}
```

Con `InpGateMode=1` (default "Balanced", commento nel codice: "session
may lower it by at most 5 points") la soglia effettiva è
`max(sessionTh, globalTh - 5.0)`. Con `globalTh=75`:
`75 - 5.0 = 70.0`. Le soglie di sessione (`InpAsianScoreMin=65`,
`InpLondonScoreMin=60`, `InpOverlapScoreMin=58`, `InpNYScoreMin=60`,
`InpAfterNYScoreMin=70`) sono **tutte ≤70**, quindi
`max(sessionTh, 70.0) = 70.0` **in ogni sessione, sempre**. FVG_CONT
scora sempre esattamente 70.0 → **passa sempre**, qualunque sia
`InpMinEntryScore` da 55 in su (finché `globalTh - 5 ≤ 70`, cioè
`globalTh ≤ 75`). A `InpMinEntryScore=75` la soglia effettiva è
*esattamente* 70.0, sul filo — non abbastanza per scartare un
segnale che scora esattamente 70.0.

**In altre parole**: voto75 non è mai stato un test valido per
FVG_CONT con `InpGateMode=1` attivo — servirebbe `InpMinEntryScore≥76`
per superare anche solo di un punto la soglia effettiva, oppure
disattivare la leniency di sessione (`InpGateMode=0`, "Conservative":
`max(globalTh, sessionTh)`, che con `globalTh=75` darebbe soglia
effettiva **75 netta** — e **zero trade** per FVG_CONT, dato che il
suo punteggio è fisso a 70.0).

## Bonus: `InpGateMode` è ANCHE un quinto caso della stessa classe di bug

`NXS_Inputs.mqh:749`: `int InpGateMode = 1;` — **non `input`**. Già
segnalato nell'audit esterno di stanotte
([[NEXUS EA - Audit Esterno Cartella MQL5, Verificato Punto per Punto (08-09)]])
come una delle 5 variabili non-`input` trovate incrociando gli `.ini`.
Nessuno dei nostri `.ini` FVG_CONT ha mai provato a impostarlo — quindi
non è la causa del risultato identico di oggi (il default 1 è
comunque quello attivo), ma **serve fixarlo comunque** se si vuole
testare `InpGateMode=0` per isolare l'effetto della leniency di
sessione.

## Cosa dice davvero questo per FVG_CONT

Il punteggio del segnale FVG_CONT è **fisso a 70.0**, non un valore
graduato — probabilmente un punteggio "base" della strategia senza
componenti variabili (o con componenti che sommano sempre a zero in
questo campione). Questo significa:
- Con la formula GateMode=1 attuale, qualunque `InpMinEntryScore` da
  50 a 75 produce **esattamente lo stesso risultato** per FVG_CONT —
  il voto-entrata semplicemente non è una leva che fa nulla per
  questa strategia, in questa configurazione.
- Se si vuole davvero un gate a 75 netto (GateMode=0), il risultato
  atteso è **zero trade** — non "un filtro migliore", una chiusura
  totale del segnale.
- Il vero modo per far leva sul "voto" per FVG_CONT sarebbe rendere il
  suo punteggio realmente variabile (aggiungere componenti allo score
  che dipendano da condizioni di mercato/regime), non alzare una
  soglia contro un numero costante.

## Prossimo passo (da decidere, non ancora fatto)

1. Aggiungere `input` a `InpGateMode` (quinta istanza della stessa
   classe di bug, coerente con l'audit esterno).
2. Rilanciare come step8 con `InpGateMode=0` esplicito nell'.ini,
   aspettandosi **zero trade** — se conferma, il "voto75" per FVG_CONT
   è definitivamente chiuso come leva (il punteggio non arriva mai a
   75), e l'attenzione si sposta sul regime fix multi-TF preso da
   solo (senza cambiare il voto), o su come rendere lo score
   effettivamente variabile.

Non applicato — in attesa di conferma esplicita, come da regola del
progetto.

## Collegamenti
[[NEXUS EA - Step6 Ancora Identico, Bug Indipendente su InpMinEntryScore (08-09)]] · [[NEXUS EA - Step5 Ancora Bacato, InpRiskProfile Non e' un Vero Input MQL5 (07-09)]] · [[NEXUS EA - Audit Esterno Cartella MQL5, Verificato Punto per Punto (08-09)]] · [[MOC - Trading]]
