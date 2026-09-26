# NEXUS - Phase 7.9H BREAKOUT_ACC_INTENDED_D1_V1 — Canonical Dataset

**Baseline:** `8fab0dd` (Phase 7.11 - Complete Strategy Census). Nessuna optimization, nessuna ricerca di edge, nessun P&L usato per decidere la metodologia. Nessuna nuova modifica alla logica di trading dell'EA in questa fase (verificato: 0 diff su `MQL5/` e `server/backtest.py`).

**Obiettivo**: costruire il dataset canonico event-level `BREAKOUT_ACC_INTENDED_D1_V1`, ora che identità, implementazione e signal parity sono state sufficientemente ristabilite (Phase 7.9E→7.9G→7.10→7.11). Popolazione = **eventi**, non solo trade aperti; funnel intero preservato; nessuna selection bias.

---

## 1. Prezzo di fill reale — il gap trovato e colmato senza toccare l'EA live

Verificato sul codice: `NEXUS_trades.csv` (log CSV esistente) logga in apertura il **prezzo di riferimento del segnale** (`refP`, calcolato prima dell'invio ordine), non il fill reale — mentre in chiusura usa correttamente `tc.vwap_out` (fill reale via `HistoryDealGetDouble`). Per l'apertura, il fill reale (`PositionGetDouble(POSITION_PRICE_OPEN)`) viene risolto nello stesso blocco ma **mai loggato**.

Su tua indicazione esplicita (non usare `refP` come proxy del fill se il fill reale è recuperabile): costruito **`NXS_BreakoutAccDealExportDiagnostic.mq5`**, copia byte-identica di `NEXUS_EA_v2.mq5` (stesso `#include`, **zero righe di logica di trading toccate**) con un'unica aggiunta — `NXS_DIAG_ExportDeals()`, chiamata solo a fine `OnTester()`, sola lettura, che esporta **ogni deal reale** della history del Tester via `HistoryDealGetDouble(DEAL_PRICE)`. `NEXUS_EA_v2.mq5` stesso resta non modificato (verificato via `git status`).

**Run diagnostico**: stessa configurazione canonica congelata di 7.9G (`GOLD, D1, sel=9, RAW, lot=0.01, lev=500, tutte le protezioni opt-in disattivate, 2019.02.03→2026.08.15`). Funnel identico byte-per-byte al certificato originale: **generated=67, blocked=11, opened=47, broker_reject=9** — riproducibilità confermata. 95 deal reali esportati (1 balance iniziale + 94 deal di trading = 47 posizioni × 2).

**Ostacolo ambientale risolto (non di logica)**: il Tester headless risolve i binari `.ex5` dalla cartella Experts del **terminale roaming** (`7F8EC41F...\MQL5\Experts`), non da `C:\MT5-Tester\MQL5\Experts` dove veniva compilato — root cause di 5 fallimenti "not found" prima di individuare la cartella corretta. Nessun impatto sulla logica o sui dati.

## 2. Segnale vs fill — distinzione esplicita, slippage osservato zero

Ogni evento aperto ha ora **tre campi separati**: `signal_price` (da `NEXUS_trades.csv`, join per time+sl+tp), `entry_fill_price` (da `HistoryDealGetDouble`, verificato), `signal_to_fill_slippage_price_units`. **Risultato empirico**: slippage = 0.0 su tutti i 47 eventi — coerente con esecuzione a mercato in Research Mode/RAW senza modello di slippage broker in questo run diagnostico (non generalizzabile a condizioni broker reali, esplicitamente documentato come tale — riferimento diretto alla Failure Memory WICK_SWEEP sulla distinzione prezzo-segnale/prezzo-fill).

## 3. Popolazione event-level completa — 75 eventi, nessuna selection bias

| Stage | N | Fonte |
|---|---|---|
| OPENED | 47 | trace live reale + fill reale + path anatomy |
| BLOCKED | 11 | trace live reale, nessun fill (NOT_APPLICABLE esplicito) |
| BROKER_REJECT | 9 | trace live reale, nessun fill |
| NEVER_OBSERVED_IN_LIVE_TRACE (B-only) | 8 | solo ricostruzione offline, **ritenuti non eliminati** |

Blocked e broker_reject **restano nel dataset** con tutti i campi di fill/path esplicitamente `NOT_APPLICABLE` — mai eliminati, mai riempiti con valori inventati.

## 4. event_id causale e stabile

`event_id = sha256(strategia|direzione|data_barra_D1)[:16]` — deterministico, indipendente da ticket/position_id (che possono cambiare fra run identici). Testato: unicità su 75 eventi, stabilità (ricalcolo ⇒ stesso id), sensibilità a direzione e data (cambiare uno dei due cambia l'id).

## 5. Post-entry path anatomy — orizzonti preregistrati, non TP/SL

MFE/MAE/tempo-a-MFE/tempo-a-MAE + forward return a **7 orizzonti preregistrati** (1/3/5/10/20/40/60 barre D1, definiti nel builder PRIMA di guardare risultati) per tutti i 47 eventi OPENED, calcolati da barre D1 reali (`CopyRates`, stessa fonte prezzi del backtest, esportate con un secondo EA diagnostico read-only). **Non basati su TP/SL della strategia stessa.**

## 6. Gli 8 eventi B-only — causalmente classificati, non eliminati

Verificato che il meccanismo originale (**CROSS_TIMEFRAME_STATE_CONTAMINATION**) è **strutturalmente impossibile** per tutti e 8 post-fix (la guardia TF precede ora ogni accesso allo stato, verificato sul codice attuale). Verificato anche che nessuno degli 8 appare come BLOCKED/BROKER_REJECT nel trace live (escludendo suppression da execution gates) — sono **completamente assenti** dal trace, non soppressi dopo essere stati generati.

**Cross-riferimento prezioso**: 3 di questi 8 erano già stati analizzati in Phase 7.9E come eventi mancanti **pre-fix**. Il fix 7.9G ne ha risolto **1/3** (2019.06.21, ora un trade reale) ma **non gli altri 2/3** (2019.04.18, 2019.05.15) — prova diretta che per questi 2 (e presumibilmente per gli altri 6, mai analizzati prima) serve un meccanismo **diverso** da quello già corretto.

**2 meccanismi candidati** identificati (nessuno confermato sperimentalmente in questa fase, onestamente dichiarato): differenza di timing intrabarra (dati OHLC live vs ricostruzione offline post-hoc) e gap nel gate di attivazione D1 (ipotesi originale 7.9E sui 10 indicatori ausiliari). `causal_status = PARTIALLY_EXPLAINED_NOT_ENOUGH_EVIDENCE_FOR_EXACT_MECHANISM` per tutti e 8 — nessuna certezza fabbricata. Follow-up dedicato raccomandato, non eseguito qui (fuori scope di questa fase).

## 7. Python come terza implementazione, mai ground truth

Le tre parity restano **separate**, riferite direttamente dagli artifact 7.9G già congelati (nessuna doppia fonte di verità): same-feed A-vs-B (matched=67, only_a=0, only_b=8), cross-feed A-vs-C e B-vs-C (feed Dukascopy vs broker). Il dataset event-level (fill/path anatomy) è costruito **solo** dal trace/deal MQL5 reale — Python resta un confronto di parity a livello di segnale, non fuso nei campi per-evento (feed diverso, nessun fill reale disponibile lato Python).

## 8. Validazione — 10/10 controlli passati

Unicità/stabilità event_id, funnel coerente col certificato reale, nessun fill fabbricato per eventi non-OPENED, tutti gli OPENED con fill verificato, signal/fill price come campi distinti, path anatomy con orizzonti preregistrati, B-only ritenuti e classificati onestamente — **tutti PASS**.

## 9. Decisione finale

**`CANONICAL_DATASET_READY_FOR_MECHANISM_RESEARCH`** (unico verdetto ammesso oltre a `CANONICAL_DATASET_NOT_READY` — **mai** un verdetto di profittabilità).

## 10. Azioni di optimization esplicitamente vietate e rispettate

Nessun parameter tuning su SL/TP/cooldown, nessuna selezione di orizzonti dopo aver visto i risultati (preregistrati nel builder), nessun filtro su P&L, nessuna nuova modifica EA, nessuna promozione a verdetto di profittabilità, nessuna eliminazione degli 8 eventi B-only.

---

## Deliverables

`breakout_acc_intended_d1_v1_dataset.json` (75 eventi), `b_only_residual_classification_v1.json`, `phase_7_9h_validation_and_decision_v1.json`, 3 builder, verificatore indipendente, 32 test di consistenza (32/32 PASS), 2 EA diagnostici read-only (`NXS_BreakoutAccDealExportDiagnostic.mq5`, `NXS_ExportD1_Phase79H.mq5` — mai toccato `NEXUS_EA_v2.mq5`), dati grezzi (`nxs_diag_deals_export_r003.csv`, `nxs_d1_gold_phase79h.csv`), questo vault report.

## Vincoli preservati

`VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti. `HISTORICAL_VOLUME_CONTRACT_WALLS` resta backlog. Le 10 strategie DEFECT_CONFIRMED rimanenti (oltre BREAKOUT_ACC) e i pattern `UNKNOWN_STRATEGY_REGISTRY_GAP`/`CROSS_STRATEGY_STATE_SHARING` da Phase 7.11 restano non corretti/non prioritari.

## Prossimo passo (non iniziato)

Edge Decomposition → Path Anatomy aggregata → Natural Horizon → Mechanism Discovery — richiede una nuova istruzione dedicata dell'utente.

## Regressione

- **Suite propria 7.9H (pytest)**: 32/32 PASS
- **Suite pytest Phase 7 totale**: **286/286 PASS, 0 fallimenti** (254 precedenti + 32 nuovi)
- **4 suite standalone pre-esistenti**, fallimenti noti invariati (stesse cause di Phase 7.10/7.11, nessuna regressione nuova):
  - `phase7_8e`: 68/72 PASS
  - `phase7_8h`: 18/21 PASS
  - `phase7_8i`: 22/23 PASS
  - `phase7_9b`: 31/33 PASS

I 2 artifact `phase7_9c/breakout_acc_*_event_stream_v1.json` (effetto collaterale noto: `generated_at` toccato dall'esecuzione suite, hash canonico invariato) ripristinati con `git checkout --` prima del commit.

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.9H: COMPLETATA ✓
DATASET CANONICO: BREAKOUT_ACC_INTENDED_D1_V1 - 75 eventi (47 OPENED
        con fill reale verificato + path anatomy, 11 BLOCKED, 9
        BROKER_REJECT, 8 B-only ritenuti e classificati causalmente)
FILL PRICE: gap trovato (refP != fill reale) e colmato con un EA
        diagnostico read-only dedicato, NEXUS_EA_v2.mq5 mai toccato -
        slippage osservato 0.0 su tutti i 47 trade
8 EVENTI B-ONLY: CROSS_TF_CONTAMINATION esclusa strutturalmente per
        tutti; 2/8 gia' noti pre-fix, il fix ne ha risolto 1/2 - serve
        un meccanismo diverso per gli altri, non ancora isolato
DECISIONE FINALE: CANONICAL_DATASET_READY_FOR_MECHANISM_RESEARCH
PROSSIMO: Edge Decomposition -> Path Anatomy -> Natural Horizon ->
          Mechanism Discovery (nuova istruzione richiesta)
```
