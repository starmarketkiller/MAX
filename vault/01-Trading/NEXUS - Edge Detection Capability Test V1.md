---
type: note
domain: trading
status: active
tags: [trading, nexus-research, power, calibration, methodology]
created: 2026-10-18
updated: 2026-10-18
---

# NEXUS - Edge Detection Capability Test V1 (18-10)

Test sintetico della pipeline di validazione: un edge noto viene aggiunto a
copie in memoria degli esiti (prezzi e dataset invariati) per misurare
falsi positivi, potenza, bias e copertura. Nessun holdout, nessun backtest.

**Verdetto: `PIPELINE_UNDERPOWERED`**, più un difetto di calibrazione
circoscritto: il bootstrap IID (usato in 7.21/7.25/7.27) dà 17-29% di falsi
positivi quando gli eventi sono raggruppati; i metodi a blocchi
dell'engine restano calibrati.

- Con 47 trade la potenza è 12-34% per edge di 0,2-0,3R; per 0,3R servono
  ~180-500 trade, per 0,2R ~400-1.100.
- Il 7.27 aveva potenza ≤ ~0,2: il suo esito è non informativo, non una prova
  che i profitti siano solo trend dell'oro.
- Proposta di power gate (da approvare separatamente).

Dettaglio, tabelle e riproduzione: `docs/NEXUS_EDGE_DETECTION_CAPABILITY_V1.md`.
Artifact e manifest: `server/research_scripts/edge_detection_capability_v1/`.

## Collegamenti
[[NEXUS - Phase 7.27 GOLD BUY-Dominance Benchmark Test]] · [[NEXUS - Phase 7.21 BREAKOUT_ACC Edge Validation V1]] · [[NEXUS - Phase 7.25 LIQ_SWEEP Edge Validation V1]] · [[MOC - Trading]]
