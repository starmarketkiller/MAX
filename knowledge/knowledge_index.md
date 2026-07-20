# Nexus Knowledge Engine v1 — Indice della conoscenza

Generato: 19/07/2026 · Baseline: `e6ce816` (branch `baseline-post-infra-audit`, EA 2.50) · Solo lettura: nessun codice, configurazione o dato originale modificato.

Base dati per il futuro **Nexus Core**. Ogni valore riporta la fonte; nessuna interpretazione aggiunta oltre a quanto già documentato nei sorgenti citati.

---

## I 4 database

| File | Contenuto | Voci |
|---|---|---|
| [strategy_database.json](strategy_database.json) | Le 37 strategie: stato, redesign, bug storici, fix, risultati ultimo sweep (parsati dai CSV reali), affidabilità, decisione corrente | 37 |
| [bug_database.json](bug_database.json) | Bug con id, commit di fix, impatto, stato (24 risolti, 7 aperti) | 31 |
| [backtest_database.json](backtest_database.json) | Campagne di backtest: broker, periodo, leva, qualità dati, esito, report associato | 10 |
| [decision_database.json](decision_database.json) | Decisioni vincolanti del progetto con motivo, evidenze, conseguenze | 13 |

## Fonti primarie (dove verificare ogni valore)

### Codice e configurazione
- `MQL5/Experts/NEXUS_EA_v2.mq5` + `MQL5/Include/NEXUS_v1/*.mqh` (61 include) — l'EA
- `MQL5/Include/NEXUS_v1/NXS_StrategyProfiles.mqh` — profili SL/TP/HTF/BE per strategia (source of truth)
- `results/sets/` — file .set (template sweep: `SWEEP_37_DataCollectionMode.set`)
- `results/manifests/baseline_manifest.json` — identità completa della baseline (P0.1)

### Dati di test
- `results/reports/sweep37/` — stats CSV per passata; round corrente = file `20260718`/`20260719`; round storici nelle sottocartelle `pre-fix-*`
- `results/reports/sweep37/trades_snapshots/` — snapshot `NEXUS_trades.csv` (trade-level)
- `pinescript/README.md` — risultati TradingView (terzo motore)

### Vault (conoscenza e decisioni)
- `NEXUS EA - MASTER ROADMAP v3.md` — la roadmap P0-P5
- `NEXUS EA - Roadmap verso il Live.md` — le 7 fasi con stato corrente
- `NEXUS EA - Principi.md` — le 9 regole nate da errori reali
- `Decisions/DEC - Baseline tecnica corrente.md` — decisione baseline
- `NEXUS EA - Caccia al Bug Esecuzione (17-07).md` — cronaca completa dei 16 aggiornamenti della sessione fix
- `NEXUS EA - Audit Fedeltà Trigger` / `Audit Livello A` — gli audit di coerenza
- `NEXUS EA - Confronto 3 Motori` — MT5 vs TradingView vs sito
- `NEXUS EA - Lezione Overfitting 3Y.md` · `NEXUS EA - Hedge nel Tempo.md` · `TODO/TODO - Backtest 10Y.md`

## Stato del progetto in 5 righe (al 19/07)

1. **Sweep baseline in corso**: S01-S08 completate su 37 — primo dataset pulito del progetto (leva effettiva 1:100, BUG-024, impatto nullo documentato).
2. Primi PF isolati (lotto fisso, trigger post-fix): ADX_RSI 0.82 · BOLLINGER 0.79 · MACD 0.79 · TSI 0.76 · BJORGUM 0.68 · LIQ_SWEEP 1.04 · FVG_CONT 0.96 — misurano il **trigger nudo** senza gestione di portafoglio; il confronto vero arriva a sweep completo.
3. Fase 0 (esecuzione) quasi chiusa; Fase 1 (coerenza logica) al ~90%: 37/37 auditate, ~20 fix implementati, 3 spec pronte in attesa di approvazione (CHOCH timestamp, AMD_REVERSAL, PO3) + rename ELLIOTT.
4. Hold implementativo attivo (DEC-012): nessuna modifica a codice fino a fine sweep + approvazione.
5. Prossimi gate verso il live: fine sweep → analisi C-level pulita → P0.2/P0.3 → fix leva (BUG-024) → test portafoglio 1:500 con protezioni ON → realismo esecuzione → demo 4-8 settimane.

## Convenzioni di lettura

- **Ogni numero ha fonte e orizzonte** (DEC-013): "PF 1.5" senza contesto non è un dato.
- I risultati **pre-18/07 non sono confrontabili** con la baseline (DEC-008): gate posizione mancante + trigger poi riscritti.
- PF/WR del round corrente = strategia **isolata a lotto fisso**: comportamento del trigger, non P&L di portafoglio.
- Sito/TradingView = ipotesi da validare su MT5, mai conclusive (Principi 5-6, DEC-011).
