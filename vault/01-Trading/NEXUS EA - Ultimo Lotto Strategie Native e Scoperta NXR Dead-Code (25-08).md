---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, mql5, ricerca-da-zero, dead-code, nxr, choch]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — ultimo lotto strategie a stop nativo + scoperta NXR dead-code (25/08)

## Bug metodologico corretto: allineamento CHOCH M15 → H4/D1

`g_struct.chochUp/chochDown` (NXS_Structure.mqh) viene azzerato e
ricalcolato a OGNI barra M15 (InpTFEntry) — resta vero solo per la
singola barra M15 in cui il break scatta, non in modo persistente. Una
strategia con EffTF piu' alto (H4/D1) pero' viene rivalutata a ogni tick
per l'intero periodo: se il CHOCH scatta in un qualsiasi istante M15
dentro quel periodo, prima o poi un tick lo trova true. Il primo test di
SMS_BMS_RTO (allineamento puntuale al solo M15 di chiusura) dava
`choch_up` **sempre falso** su 486 candidati — corretto con un OR su
tutte le barre M15 comprese nel periodo H4/D1
(`choch_any_in_period` in `remaining_institutional_smc_live_signal_25-08.py`).
Dopo la correzione: IFVG n=14→60, SMS_BMS_RTO n=0→117, WEEKLY_EXP n=6→16.

## Risultati (ricetta live esatta, stop nativi, TF proprio di ciascuna)

| Strategia | TF | n | PF | Finestre | Verdetto |
|---|---|---|---|---|---|
| RANGE_FADE | D1 | 6 | 0.00 | 0/0 | **Disattivata** (troppo rara per contare, non un verdetto di profittabilita' solido) |
| DISP_REBAL | H4 | 69 | 0.86 | 2/5 | Invariata (borderline, non conclusivo) |
| IFVG | H4 | 60 | 0.66 | 2/5 | Disattivata — **ma vedi sotto: era gia' morta per un altro motivo** |
| SH_BMS_RTO (v1) | D1 | 25 | 1.49 | 3/5 | Invariata (il piu' promettente, campione ancora modesto) |
| SMS_BMS_RTO | D1 | 117 | 0.92 | 3/5 | Invariata (vicino al pareggio, non conclusivo) |
| WEEKLY_EXP | H4 | 16 | 1.18 | 0/0 | Invariata (troppo rara per concludere) |

Nota tecnica SH_BMS_RTO: essendo EffTF=D1, `h1/l1/c1` di
`NXS_DetectSweepExt` (letti su `NXS_EffTF()`) coincidono ESATTAMENTE con
`pdh/pdl` (sempre D1 shift1, fissi) — lo sweep PDH/PDL e' quindi
strutturalmente impossibile (`h1>pdh` diventa `pdh>pdh`), non solo per
questa strategia ma per QUALUNQUE strategia EffTF=D1 che consumasse
`sw.sweptPDH/sweptPDL`. Solo Asia ed EQH/EQL restano vivi come sorgente
di sweep. Non e' un bug da correggere isolatamente — e' cosi' che il
motore funziona per costruzione su D1 — ma va tenuto a mente.

## Scoperta maggiore: IFVG, FVG_MIT, OB_MIT sono dead-code per un motivo completamente diverso

Il disattivamento di IFVG sopra (basato sul backtest PF0.66) era **per
il motivo sbagliato**. `NXS_ReusePerformancePack.mqh` (incluso per
ultimo, righe ~2364-2366) fa una redirezione macro incondizionata:

```mql5
#define NXS_Strat_IFVG_Reversal              NXR_Strat_IFVG_Reversal
#define NXS_Strat_FVG_Mitigation             NXR_Strat_FVG_Mitigation
#define NXS_Strat_OB_Mitigation_Structural   NXR_Strat_OB_Mitigation
```

Ogni chiamata (incluso il loop segnali principale dell'EA) invoca quindi
sempre la variante `NXR_*`, mai la funzione che ho letto e backtestato.
Le tre `NXR_Strat_*` sono per design (audit 17/07: "converge on NXR as
sole source of truth", **nessun fallback** sulla logica legacy)
alimentate SOLO da `g_nxrTrigger`, che diventa valido solo se
`InpNXR_Enable=true`. Ma `InpNXR_Enable` e' **hardcoded false** (non e'
nemmeno un `input`, serve ricompilare per cambiarlo). Risultato: le tre
strategie ritornano sempre segnale vuoto, indipendentemente dal loro
toggle (`InpStrat_IFVG`/`InpStrat_FVG_Mit`/`InpStrat_OB_Mit`) e
indipendentemente da qualunque backtest — sono morte per costruzione,
stesso schema di CRT/LIQ_VOID.

**Verificato che NON sono affette**: `NXR_Strat_MalaysianSNR` e
`NXR_Strat_StructureReaction` sono anch'esse rediretta via macro, ma
chiamano SEMPRE prima la funzione base originale
(`NXS_Strat_MalaysianSNR_Rejection`/`NXS_Strat_StructureReaction`) e la
ritornano se il trigger NXR non e' valido (sempre il caso oggi) — quindi
il lavoro di oggi su STRUCT_REACT (TF H4, direction lock, SL/TP) e'
pienamente live e non tocca alcun percorso morto.

### Azione

- `InpStrat_IFVG=false` (era gia' cosi', motivazione corretta nel commento)
- `InpStrat_FVG_Mit=false` (era `true`, dead code silenzioso — disattivata)
- `InpStrat_OB_Mit=false` (era `true`, dead code silenzioso — disattivata)
- `InpStrat_FVG_MIT_WINDOW` **non toccata** — nome diverso, non rediretta dal blocco NXR, verificata viva.
- `InpNXR_Enable` **non toccato** — riattivarlo significherebbe accendere un intero sottosistema (zone SMC con motore di trigger proprio) mai validato in questa sessione; richiede una ricerca dedicata separata, non una decisione da prendere di riflesso stasera.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - AMD_CONT e LDN_REVERSAL Live, Segnali Reali Testati e Disattivati (25-08)]]
[[NEXUS EA - TURTLE_SOUP Live, Segnale Reale Testato e Disattivato (25-08)]]
