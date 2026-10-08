# NEXUS MASTERPLAN V4 — Reparto Trading

Vedi [NEXUS_MASTERPLAN_V4.md](NEXUS_MASTERPLAN_V4.md) per legenda di stato e provenienza. Fonte: census read-only di questa sessione (fork dedicato), nessun file MQL5/risk/execution toccato.

**Sintesi**: la meccanica di esecuzione (EA, RiskShield, logging) è solida e già forensicamente verificata in una sessione precedente. L'imbuto di validazione strategie è invece quasi vuoto in cima: su 83 strategie nel registro, **0 sono `VALIDATED`**.

## Input
Dati mercati, news/macroeconomia, idee/strategie, feedback performance.

## Processo interno

| # | Step | Stato | Evidenza |
|---|---|---|---|
| 1 | Scouting mercato e setup | IMPLEMENTED | 80+ cartelle fase in `server/research_scripts/`, pipeline fetch storico Dukascopy reale (`NEXUS_DUKASCOPY_DIR`/`NEXUS_DUKASCOPY_AUTOFETCH` in `render.yaml`) |
| 2 | Ricerca e sviluppo strategia | IMPLEMENTED | 80 file `.mqh` in `MQL5/Include/NEXUS_v1/`; 83 strategie tracciate in `contracts/edge-validation-registry.json` |
| 3 | Backtest e validazione | PARTIAL | Esecuzione backtest reale e ripetuta (artefatti `phase7_*`), ma esito debole: `standalone_edge_status` = 65 `UNVALIDATED`, 9 `CANDIDATE`, 4 `BORDERLINE`, 3 `FAILED`, 2 `FORWARD_REQUIRED`, **0 `VALIDATED`**; `defect_status`: 9 `DEFECT_BLOCKED`, 1 `SUSPECT` |
| 4 | Ottimizzazione e stress test | PARTIAL | Script ad hoc per fase (es. cost-calibration rerun), nessun harness riusabile standing |
| 5 | Demo/forward test | PARTIAL / BLOCKED in parte | `forward_validation_status` `UNKNOWN` per 79/83 strategie; 4 con segnale debole (2 `INSUFFICIENT`, 1 `NEGATIVE_INSUFFICIENT`, 1 `COMPLETE_NEGATIVE`). VOLBRK Serious 3Y è esplicitamente `PARTIALLY_BLOCKED` su 3 soglie a decisione umana — gate deliberato, non un gap |
| 6 | Approval live gate | PLANNED/PARTIAL | Nessuna funzione di gate "go-live" codificata; l'approvazione vive nel giudizio umano + nei campi di stato del registro, non in un gate eseguibile |
| 7 | Deployment EA/esecuzione | IMPLEMENTED (meccanica) | EA compila ed esegue; pipeline di 8 gate `NXS_CommonExposurePreflight` verificata end-to-end in audit forense precedente. Quasi nessuna strategia è però promossa live, dato lo stato di step 3/5 |
| 8 | Monitoraggio live | PARTIAL | `NXS_LogTradeCSV`/`NXS_ResearchLogInit` producono log reali; nessun servizio dedicato di monitoraggio live trading oltre questo |
| 9 | Gestione rischio e portafoglio | IMPLEMENTED | `NXS_RiskShield.mqh` v2.0.9: Spread Burst, Equity Breaker, Correlation Cluster, News Tier-3 — verificati cablati su ogni percorso di ingresso in audit precedente |
| 10 | Analisi performance | IMPLEMENTED (nuovo, questa sessione) | `server/mt5_data_v1/analytics.py` + `reports.py` — metriche account/strategy-level, `ACCOUNT_PERFORMANCE_SUMMARY_V1`. Non ancora collegato a un account live |

## Output
Strategie validate (oggi: nessuna), trade eseguiti, PnL, report performance.

## Gate e capability
- Pipeline a 8 gate `NXS_CommonExposurePreflight` (`NXS_Execution.mqh`), incluso RiskShield al passo 5.
- Registro edge-validation con vocabolari di stato espliciti (`status_vocabulary`, `component_value_vocabulary`, `role_vocabulary`).
- `mt5_data_v1` (questa sessione): Account Registry, normalizzazione CSV raw→canonico, verifier a 7 controlli.

## Verificatori
Verifier di qualità dati `mt5_data_v1/verifier.py` (7 controlli); nessun verificatore automatico di "è questa strategia pronta per il live" oltre il giudizio umano sui campi del registro.

## Error handling / retry
A livello EA: outbox durevole per consegne HTTP fallite (`NXS_Outbox.mqh`), intento di esecuzione registrato prima dell'apertura posizione (`NXS_Intent.mqh`). A livello ricerca: nessun retry automatico di un backtest fallito.

## Approvazioni
Umane, non codificate come gate eseguibile (vedi step 6).

## Dipendenze
`mt5_data_v1` per dati canonici; `LocalBridge/nexus_terminal_identity_guard.py` per sicurezza terminale su compile/deploy; MQL5 `NEXUS_v1` include compilati solo dal terminale LIVE (bug noto, vedi project memory).

## Self-improvement locale

| Item | Stato |
|---|---|
| Analisi KPI | IMPLEMENTED (`mt5_data_v1/analytics.py`), non ancora alimentato da dati live |
| Rilevazione errori/opportunità | PARTIAL — `defect_status` è curato manualmente, non un detector automatico |
| Ipotesi di miglioramento / esperimenti sandbox | PLANNED — nessun framework di esperimento dedicato distinto dagli script di ricerca manuali |
| Confronto baseline vs variante | PLANNED — nessuno strumento di confronto riusabile trovato |
| Feedback al consiglio globale | PLANNED — nessuna integrazione con un Global Improvement Council esiste (vedi [proposta cross-reparto](NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md)) |

## Nota di duplicazione (per l'architecture review)
`research_scripts/phase7/` contiene molte varianti quasi identiche per-strategia (es. `phase7_8g/8h/8i` eseguono tutte copie di `collect_immutable_run_manifest.py`) — stesso pattern ripetuto manualmente invece che parametrizzato una volta. Candidato QUICK_WIN di consolidamento, vedi [architecture review](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md).
