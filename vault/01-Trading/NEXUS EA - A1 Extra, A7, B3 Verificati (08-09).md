---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, audit, alert, htfbias, verifica]
created: 2026-09-08
updated: 2026-09-08
---

# NEXUS EA — A1 extra, A7, B3 verificati (08/09)

## A1 extra — Alert() su preset che scarta valori custom

Testato con un backtest FVG_CONT breve (2 mesi H4, `InpRiskProfile`
lasciato al default BALANCED, `InpMinEntryScore=75` e altri valori
custom impostati esplicitamente nell'.ini per forzare lo scarto).
Log, 10:02:14:

```
Alert: [NEXUS PRESET] BALANCED sta scartando valori custom impostati
esplicitamente: InpMaxTradesPerDay(999999->12) InpMaxDailyDDPct(100.00->5.00)
InpMinEntryScore(75->70) - usa InpRiskProfile=0 (Custom) se questi
valori erano intenzionali.
```

Elenca correttamente tutti e tre i valori scartati con vecchio/nuovo
valore. **Confermato funzionante** — questo è l'identico avviso che ci
avrebbe risparmiato 3 tentativi falliti sul voto75 di FVG_CONT
(step4/5/6) se fosse esistito prima.

## B3 — nessun falso allarme HTFBias

Stesso test: **zero** occorrenze di `[NEXUS HTFBIAS]` nel log — nessun
handle rotto, il filtro HTF ha funzionato normalmente. Conferma anche
che i test FVG_CONT fatti finora oggi non erano silenziosamente
compromessi da questo problema specifico (non prova che non accada mai,
solo che non è successo in questo campione).

## A7 — ConsecLossBrake marcato, non toccato

Nessun test dedicato necessario: è codice morto per costruzione (nessun
`#include`), la modifica era solo documentale (banner nel file).

## Stato complessivo dopo oggi

| Fix | Stato |
|---|---|
| A1 (InpRiskProfile input) | ✅ Applicato e verificato (07/09) |
| A1 extra (Alert su scarto) | ✅ Applicato e verificato (questa nota) |
| A2 (ProfitReclaim gate) | ✅ Applicato e verificato con test di regressione (401+15 blocchi) |
| A3 (SLReclaim gate pieno) | ✅ Applicato e verificato con test di regressione |
| A4 (magic number reclaim) | ✅ Applicato (verifica indiretta: i blocchi A2/A3 avvengono prima del punto in cui il magic verrebbe assegnato) |
| A5 (licenza fail-open 4xx) | ⏳ Non applicato — verificato solo staticamente |
| A6 (WebPush in OnTick) | ⏳ Non applicato — irrilevante per i backtest (`MQL_TESTER` esclude il path), rilevante solo per demo/live |
| A7 (ConsecLossBrake) | ✅ Marcato come inattivo, non riattivato |
| B1 (StructureMultiLayer) | ⏳ Non ancora verificato se FVG_CONT/SAR lo usano |
| B3 (HTFBias log) | ✅ Applicato e verificato |
| B2, B4, B5, B6 | ⏳ Non iniziati |
| Resto Fase C/D/E/F del piano | Non iniziato |

## Collegamenti
[[NEXUS EA - A2+A3+A4 Verificati con Test di Regressione, Storia Completa (08-09)]] · [[NEXUS EA - Audit Esterno Cartella MQL5, Verificato Punto per Punto (08-09)]] · [[MOC - Trading]]
