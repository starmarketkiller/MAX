# NEXUS - Phase 7.12 — Coverage Matrix, Lacune e Coda delle Priorità

**Baseline:** `8e405e5` (Phase 7.9K). Phase 7.10, 7.11 e tutti i raw data **preservati e invariati** (verificato via git diff). Lavoro concorrente di Codex su Product Platform/census/freshness **non toccato** — questa fase opera esclusivamente in `server/research_scripts/phase7/phase7_12/` e in un nuovo vault report. Nessuna correzione a EA/registry/strategie, nessuna campagna di backtest, nessuna optimization o promozione live.

**Obiettivo**: usare il census completo (Phase 7.11, 83 identità) per stabilire la copertura reale dell'audit già svolto (Phase 7.10, 20 candidate stateful) e scegliere UNA sola prossima strategia su cui intervenire.

---

## 1. Riconciliazione census × audit

Il census 7.11 **già incorpora** la riconciliazione con l'audit 7.10 nel campo `known_implementation_defects` (60 `NOT_AUDITED_IN_PHASE_7_10`, 10 `DEFECT_CONFIRMED`, 7 `SAFE`, 5 `SUSPECT`, 1 `DEFECT_CONFIRMED_FIXED_IN_7_9G` — totale 23, combaciante con `stateful=True`). La matrice di copertura di questa fase (`strategy_coverage_matrix_v1.json`, 83 righe) espande questo con: implementazioni Python/MQL5, raggiungibilità dal router live, presenza di registry gap, e — punto centrale — **due correzioni verificate direttamente sul codice** al campo `stateful` del census, risultato errato per due identità.

**Principi applicati esplicitamente su tutte le 83 righe**: "non auditata" ≠ SAFE (60 righe marcate `not_audited_does_not_mean_safe=True`); SAFE rispetto al pattern CROSS_TIMEFRAME_STATE_CONTAMINATION ≠ validata complessivamente (7 righe SAFE marcate con la nota esplicita).

## 2. Lacune di copertura — 2 nuove scoperte verificate

**FVG_MIT_WINDOW** (census: `stateful=False` — **errato**): possiede un pool persistente di zone FVG (`g_fvgMitWBull[]`/`g_fvgMitWBear[]`, `g_fvgMitWLastBar`), mutato da `NXS_FvgMitWindow_Update()` usando `NXS_EffTF()` dinamico, **senza guardia TF**. Escluso dall'audit 7.10 perché le variabili non seguono la convenzione di naming `*State g_*` cercata dal grep originale. Un commento nel codice (righe 275-278) suggerisce un modello mentale a singolo timeframe — la stessa ambiguità intento/difetto già risolta per BREAKOUT_ACC con adjudication dedicata (Phase 7.9F), qui **non ripetuta**. Classificato **SUSPECT** (non DEFECT_CONFIRMED: manca l'adjudication documentale).

**OB_MIT** (census: `stateful=False` — **errato**): `NXS_Strat_OB_Mitigation_Structural()` chiama **direttamente** `NXS_Strat_OrderBlock()` come wrapper — eredita l'intera mutazione di stato `g_obBuy`/`g_obSell` già `DEFECT_CONFIRMED` per ORDER_BLOCK. Evidenza **diretta** (fatto del grafo delle chiamate, non analogia strutturale). Classificato **DEFECT_CONFIRMED**.

**Controllo negativo eseguito**: CRT verificato **stateless** (nessuna struct/static/globale nel corpo della funzione) — corretamente esclusa dal pattern, resta soggetta solo a `UNKNOWN_STRATEGY_REGISTRY_GAP` (pattern diverso, Phase 7.11).

**Limite dichiarato**: la scansione non ha riletto riga-per-riga tutte le 71+60 funzioni Python/MQL5 per pattern diversi da CROSS_TIMEFRAME_STATE_CONTAMINATION — copertura mirata, non esaustiva.

## 3. Coda delle priorità — 7 criteri espliciti, mai PF

**`ORDER_BLOCK` in testa** (non TSI, non BAR_UPDN — giustificato):
- Default **abilitata** (`InpStrat_ORDER_BLOCK=true`), selettore 15.
- Propaga direttamente a **OB_MIT** (stessa funzione eseguita) — un solo test diagnostico chiarisce due identità.
- Valida la sotto-classe `STATE_MACHINE_CONTAMINATION` (mai testata empiricamente, distinta dal `COOLDOWN` già validato su BREAKOUT_ACC) e informa l'intera famiglia SMC (`SH_BMS_RTO`, `SH_BMS_RTO_V2`, `SILVER_BULLET`, `RANGE_FADE`).
- Costo diagnostico basso-medio: metodologia **direttamente riutilizzabile** da Phase 7.9E-G.

**TSI** al #2 — non ignorata, ma non prima: severità teorica massima e **unica con evidenza storica documentata** (sweep37, 839 trade), ma costo diagnostico più alto (stato continuo ricorsivo, non binario — richiede esportare un'intera traiettoria numerica, non un conteggio di eventi) e nessuna doppia-identità da chiarire.

**BAR_UPDN esplicitamente NON in testa**, nonostante il costo diagnostico più basso del gruppo: disabilitata di default (bassa raggiungibilità) e la sua sotto-classe (cooldown) è **già validata** empiricamente da BREAKOUT_ACC — un test qui confermerebbe un meccanismo già provato, non aggiungerebbe conoscenza su nuove sotto-classi.

**Registry gap trattati separatamente** (CRT, FVG_MIT_WINDOW): correggere `NXS_StrategyKnown()` è un intervento diverso (rende eseguibile codice bloccato, non corregge stato contaminato). Nota di attenzione: se il gap di FVG_MIT_WINDOW venisse corretto senza chiarire il suo stato SUSPECT, si rischierebbe di attivare silenziosamente un secondo difetto mai testato.

## 4. Protocollo diagnostico — ORDER_BLOCK (unica prossima task, non eseguita)

Ipotesi precisa (nessuna guardia TF prima di `NXS_OB_UpdateSide()`, verificata riga-per-riga), config di riferimento (stesso fingerprint Research Mode di BREAKOUT_ACC, selettore 15), confronto controllato (stream A live multi-TF vs stream B offline D1-isolato, stesso schema di Phase 7.9C-E), metriche (funnel GENERATED/BLOCKED/OPENED via trace esistente + nuove metriche di zona per lo stream offline), criteri di conferma/smentita **e gestione esplicita del caso ambiguo** (`NOT_ENOUGH_EVIDENCE_AFTER_EXPERIMENT`, mai forzata), criteri di accettazione del fix che **separano** verifica implementazione / validità evidenza / redditività (quest'ultima esplicitamente **non presunta**), dipendenze e blocker (autorizzazione utente per modifica EA, scelta fra EA diagnostico standalone vs guardia di prova, dipendenze esterne `g_atr`/`g_structH1.trend`).

---

## Deliverables

`strategy_coverage_matrix_v1.json` (83 righe), `coverage_gaps_and_new_candidates_v1.json`, `strategy_priority_queue_v1.json`, `diagnostic_protocol_order_block_v1.json`, 4 builder, verificatore indipendente (ri-deriva ogni artifact e ri-verifica FVG_MIT_WINDOW/OB_MIT/CRT/ORDER_BLOCK direttamente sul codice sorgente attuale + tutti i flag di abilitazione citati), 30 test di consistenza (30/30 PASS), questo vault report.

## Vincoli preservati

Phase 7.10, 7.11 e raw data invariati (verificato via git diff). Nessun file MQL5/Python modificato. Nessuna optimization, nessuna campagna di backtest, nessuna correzione EA/registry/strategie, nessuna promozione live. Artifact BREAKOUT_ACC (Phase 7.9H-K) non toccati.

## Regressione

(compilata dopo l'esecuzione della suite completa)

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.12: COMPLETATA ✓
COVERAGE MATRIX: 83 identita' riconciliate (23 auditate in 7.10, 60
        non auditate - MAI equiparate a SAFE)
NUOVE SCOPERTE: FVG_MIT_WINDOW (SUSPECT, pool FVG mai controllato dal
        grep 7.10 per naming) e OB_MIT (DEFECT_CONFIRMED diretto -
        wrapper letterale di ORDER_BLOCK) - census 7.11 corretto qui
        (stateful=False errato per entrambi)
PRIORITA': ORDER_BLOCK in testa (default enabled, propaga a OB_MIT,
        valida sotto-classe mai testata) - TSI #2, BAR_UPDN
        esplicitamente NON in testa (giustificato)
PROSSIMO: protocollo diagnostico ORDER_BLOCK pronto, NON eseguito -
          richiede autorizzazione dedicata per qualunque test EA
```
