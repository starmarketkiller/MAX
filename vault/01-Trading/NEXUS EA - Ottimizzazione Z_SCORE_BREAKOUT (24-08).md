---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, z-score-breakout, mql5, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale Z_SCORE_BREAKOUT (24/08)

## Perché

Una delle sole 2 strategie già portate in MQL5 (`NXS_Strat_ZScoreBreakout`)
— un miglioramento qui ha valore diretto, non solo di ricerca. Config
attuale: H1, stop strutturale M5, target 4.0×ATR fisso, ER+floor0.3,
PF1.29-1.35. `zscore_breakout_optimization_24-08.py`.

## BUY-only sembrava una scoperta pulita — non lo è, verificato subito

BUY-only: PF1.64 (**m1=1.57/m2=1.71**, quasi identiche!), ECN 2.19
(m1=2.18/m2=2.20). Sembrava il caso più pulito di tutta la giornata.
**Verificato subito con la finestra laterale (imparata la lezione di
oggi) — risultato inatteso**: **zero trade BUY nella finestra laterale
2020-11→2023-10**. Non è la stessa trappola "equal-count nasconde la
debolezza" delle altre 6 strategie — qui il segnale BUY letteralmente
non esiste prima del 2024-04-08 (il primo trade BUY assoluto), perché
Z_SCORE_BREAKOUT ha già un filtro di regime PROPRIO nel segnale
(`bull_regime = close > SMA200`) che si combina con l'ER esterno,
escludendo strutturalmente ogni periodo senza un trend rialzista
sostenuto già in corso.

**Conclusione onesta**: BUY-only qui non è validabile come indipendente
dal rally 2024-2026 — è ANCORA PIÙ dipendente dal regime delle altre
6 strategie corrette oggi, non meno (zero campione fuori da quella
finestra, non solo un campione debole). **Non promosso**, stesso
principio della [[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]].

## Miglioramento reale e verificato: trailing

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| Baseline (target fisso 4.0×ATR) | 1.35 (1.37/1.33) | 4/5 | 524 |
| Trailing 2.0×ATR | 1.31 (1.02/1.62) | 4/5 | 526 |
| **Trailing 3.0×ATR** | **1.38 (1.28/1.50)** | 4/5 | 526 |

Miglioramento modesto ma pulito (simmetrico, campione pieno, nessuna
selezione direzionale sospetta) — applicabile a TUTTO lo storico
inclusa la finestra laterale, non solo al rally.

**Soglia z-score**: tutte le varianti provate (1.5/1.75/2.25/2.5)
peggiorano rispetto al default 2.0 — il valore originale del backtest
era già quello giusto, non riottimizzarlo.

## Verdetto

**Z_SCORE_BREAKOUT aggiornata con cautela**: trailing 3.0×ATR al posto
del target fisso (PF1.38, +ECN 1.89) — miglioramento reale ma modesto,
non il salto trovato su FVG_MIT. BUY-only ESPLICITAMENTE NON adottato
nonostante il numero attraente, per lo stesso principio di disciplina
verificato oggi. **Non ancora applicato al codice MQL5 già in
produzione** — richiede una modifica separata e deliberata a
`NXS_Strat_ZScoreBreakout`, non fatta qui senza richiesta esplicita.

## Prossimi passi aperti

- ⚠️ **Aggiornamento 25/08**: verificato che aggiungere solo
  `NXS_Profile_TrailK` **non basta** — il motore live tiene il TP fisso
  come tetto anche con l'overlay trailing attivo (sposta solo lo SL),
  mentre questo test usava un chandelier puro senza TP. Con il TP
  fisso ancora vivo il trailing è piatto/leggermente peggiorativo
  (PF1.32-1.34, non 1.38). Serve rimuovere il TP fisso per replicare
  davvero il miglioramento — una decisione più consequenziale, non
  ancora presa. Vedi [[NEXUS EA - Correzione Trailing Z_SCORE_BREAKOUT, il TP fisso lo annullava (25-08)]].

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
