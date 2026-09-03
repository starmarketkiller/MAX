---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, pivot-wick, backtest, mt5, research]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — PIVOT_WICK: step2 (tpMult=1.0) e OneShotLevel analizzati, nessun fix (03/09)

## Perché questa nota

Sessione in background dopo `/clear`, ripartita da
[[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]]
(Fase 0, punto 1: "PIVOT_WICK step2 in coda, aspettare il risultato").
Trovati nel frattempo **tre report Tester MT5 non ancora analizzati** in
`Terminal/D0E8209F.../`: `nxs_pivotwick_step2_tp1.htm`,
`nxs_pivotwick_c1_baseline3m.htm`, `nxs_pivotwick_c2_oneshot.htm` — gli
ultimi due successivi alla nota post-maratona (16:41 e 17:02 del 03/09,
probabilmente prodotti da un'altra sessione/agente desktop in
parallelo). Parsati con `server/research_scripts/parse_mt5_tester_report.py`
+ analisi manuale dei deal CSV grezzi (livelli entrata/uscita, motivo
chiusura, side, streak).

## Risultato 1 — step2 (tpMult 2.2→1.0): ancora negativo

Periodo M15 2025-11-01→2026-08-26 (10 mesi), `InpPivotWickRequireWick=false`.

| Metrica | Valore |
|---|---|
| Trade | 1538 |
| PF | **0.90** |
| Net | **-843.96** |
| Max DD balance | 929.02 |
| Sharpe | -3.81 |

Confermato: abbassare `tpMult` da 2.2 a 1.0 (target più vicino, deciso
dopo l'analisi MFE della sessione precedente) **non basta da solo** —
resta sotto pareggio su campione ampio (1538 trade, non un artefatto di
campione piccolo).

## Risultato 2 — c1 (baseline pulita) vs c2 (OneShotLevel=true)

Stesso periodo per entrambi (M15 2026-06-01→2026-08-26, 3 mesi, per
confronto pulito), stessa build (commit `755f3e4`, che ha aggiunto
`InpPivotWickOneShotLevel`/`InpPivotWickRequireCloseConfirm`/
`InpPivotWickAvoidBuildup`, di default tutti `false`). c2 attiva **solo**
`InpPivotWickOneShotLevel=true` (ogni livello pivot tradabile una sola
volta, la "zona fresh/non-fresh"), gli altri due restano `false`.

| | c1 baseline | c2 OneShotLevel=true | Δ |
|---|---|---|---|
| Trade | 503 | 362 | -28% |
| Win rate | 44.9% | 45.0% | ≈uguale |
| PF | 0.79 | 0.77 | leggero peggioramento |
| Net | -546.74 | -431.07 | meno negativo (meno trade) |
| Avg win | $8.88 | $8.81 | ≈uguale |
| Avg loss | -$9.19 | -$9.36 | leggero peggioramento |
| Max consec losses | 11 | 11 | uguale |
| Buy vs Sell | entrambi negativi, nessun bias direzionale | entrambi negativi | uguale |
| Uscite | 275 SL / 225 TP | 198 SL / 161 TP | proporzione uguale |

**Diagnosi onesta**: OneShotLevel filtra un sottoinsieme dei segnali
(-28% trade) ma **non cambia la qualità** del sottoinsieme che resta —
win rate, avg win/loss e proporzione SL/TP sono statisticamente
identici a c1. Il net loss si riduce solo perché si tradano meno volte
lo stesso edge negativo, non perché l'edge migliori. Coerente con lo
schema già visto altre volte in questa indagine (floor ATR, D1-alignment,
ecc.): **un filtro che riduce il volume non è automaticamente un fix**,
va verificato che cambi PF/expectancy, non solo il net.

## Perché è probabilmente un problema di logica, non di tuning

Win rate 44.9-45.0% con avg win ≈ avg loss (payoff ratio ~0.94-0.96,
cioè target e stop quasi alla pari in valore atteso per trade, coerente
con `tpMult=1.0` cioè R:R ≈1:1) è matematicamente sotto pareggio: a
R:R 1:1 servirebbe WR >50% per essere profittevoli, qui è sotto. Nessun
filtro provato finora (tpMult, wick richiesto flag di default off,
OneShotLevel) ha spostato il win rate — solo il volume. Per la
[[NEXUS EA - MASTER ROADMAP v3]] (§P2.4, punto 1: "trigger base senza
filtri" va verificato PRIMA di ottimizzare le uscite) questo è il
segnale che manca ancora un passaggio: **verificare se il trigger
pivot+wick ha davvero un edge predittivo di direzione**, indipendente da
SL/TP, prima di continuare a girare la manopola dei filtri. Non ancora
fatto: un check diretto (es. % di volte che il prezzo si muove nella
direzione del segnale entro N barre, senza SL/TP fissi — MFE/MAE puro)
per separare "il pattern non predice nulla" da "il pattern predice ma
l'uscita/il timing lo vanifica".

## Non ancora verificato

- Se il flag `InpPivotWickRequireWick=true` (pianificato in Fase 0 punto
  2 della nota post-maratona) cambia il quadro — non testato in questi
  tre report, tutti con `RequireWick=false`.
- `RequireCloseConfirm` e `AvoidBuildup` (gli altri due flag del commit
  `755f3e4`) — presenti nel `.set` di c1/c2 ma entrambi `false` in
  entrambi i test, quindi non isolati singolarmente ancora.
- Analisi MFE/MAE pura (senza SL/TP) per capire se il trigger ha edge
  direzionale grezzo — prossimo passo naturale prima di provare altri
  filtri di uscita.

## Prossima azione consigliata

Prima di un altro giro di tuning uscite: isolare `RequireWick=true` da
solo (stesso periodo 3 mesi, stessa baseline c1) — se anche questo non
sposta WR/payoff, la conclusione onesta è che PIVOT_WICK come concepito
(pivot frattale + wick di rigetto, senza altro contesto) **non ha edge
su M15 GOLD in questo periodo**, e la strada utile diventa il
"filtro candela + re-entry" già pianificato (Fase 0 punto 2) o
l'archiviazione della strategia come `Rejected` (§10 Master Roadmap) se
anche quello fallisce. Richiede l'agente desktop (MetaEditor/MT5) per
lanciare il prossimo Tester run — questa sessione (background) ha solo
analizzato i report già prodotti, nessuna modifica al codice MQL5 fatta
qui (per [[feedback_no_live_mql5_without_asking]]).

## Collegamenti
[[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]] ·
[[NEXUS EA - MASTER ROADMAP v3]] · [[MOC - Trading]]
