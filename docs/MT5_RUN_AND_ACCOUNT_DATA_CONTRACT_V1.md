# MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1

**Stato:** implementato, test locali verdi, **non committato** (in attesa di review esplicita, come richiesto - "Non commit/push fino a review"). Nessuna modifica a MQL5/trading logic/risk/execution/runtime di produzione, nessun login/password gestito, nessun broker API toccato, nessun tester orchestrator costruito (vedi §Esclusioni di scope rispettate).

Base canonica di partenza: `edb3915b1de9316ea0c584ce9f10f74440ef4f9b` (MT5_TERMINAL_IDENTITY_GUARD_V1).

---

## 1. Census — cosa esiste già (fase obbligatoria, completata prima di ogni design)

Nessuno schema è stato scritto prima di aver verificato byte-per-byte i formati reali. Risultato del census, con verifiche dirette (non solo la relazione del fork iniziale, che aveva un avviso di classificatore di sicurezza non disponibile — ogni affermazione chiave è stata controllata di persona in questa sessione):

| # | Formato | File di esempio verificato | Encoding reale | Colonne reali |
|---|---|---|---|---|
| 1 | **EA_TRADE_LOG** (`NXS_LogTradeCSV`, `MQL5/Include/NEXUS_v1/NXS_Logging.mqh:36`) | `server/research_scripts/phase7/phase7_8i/immutable_run_output/NEXUS_trades_serious_3y_run3.csv` | **UTF-16LE con BOM** (verificato via lettura bytes raw, `FF FE...`) | `time,action,ticket,strategy,price,lots,sl,tp,score_or_pnl,reason,hold_sec,r_multiple,resolved_tf` |
| 2 | **NATIVE_DEAL_EXPORT** (`NXS_DIAG_ExportDeals()`, diagnostica phase7.9H via `HistoryDealGet*`) | `server/research_scripts/phase7/phase7_9h/raw_data/nxs_diag_deals_export_r003.csv` | **ASCII/UTF-8 puro** (verificato — nessun BOM) | `deal_ticket,position_id,order_ticket,time,time_msc,symbol,magic,type,entry,price,volume,sl,tp,profit,swap,commission,comment,reason` (mappa 1:1 su `HistoryDealGetInteger/Double/String(DEAL_*)`) |
| 3 | Export "research-derived" (es. `results/cost_calibration_67_rerun/breakoutacc_maxhist_trades.csv`) | — | **UTF-16LE con BOM, stesso pattern del formato 1** (verificato byte-per-byte: stesso `FF FE`) | Non è un terzo formato — è lo stesso comportamento di `FileOpen(..., FILE_CSV, ...)` di MQL5 (sempre UTF-16LE), solo da un'istanza EA diversa |

**Scoperta reale non ipotetica, fatta durante questa verifica**: `NEXUS_trades_serious_3y_run3.csv` (formato 1) **non ha riga di header** — inizia direttamente con una riga dati. Causa verificata nel codice: `NXS_LogTradeCSV` scrive l'header solo se `FileSize(h)==0` al momento dell'apertura (`NXS_Logging.mqh:38`) — se `Common\Files\NEXUS_trades.csv` esisteva già non vuoto (lo stesso rischio di collisione LIVE/TESTER già documentato in `MT5_TERMINAL_ISOLATION_POLICY_V1`), le righe successive si accodano senza un secondo header. Il parser (`csv_formats.py`) gestisce esplicitamente questo caso reale (`_looks_like_ea_trade_log_data_row`), non lo nasconde.

**Limite reale del formato 1, non un bug del parser**: `ticket` vale sempre `0` sulle righe `action=OPEN` (il ticket di posizione non esiste ancora quando l'EA scrive la riga, prima dell'invio ordine). Il join OPEN→CLOSE per questo formato è quindi **necessariamente euristico**, mai un vero `position_id`. Il formato non contiene nemmeno il `symbol` (un'istanza EA = un simbolo) — va fornito dal chiamante.

**Conflitto reale trovato e riconciliato (non ignorato)**: `server/app.py`, migrazione `010_trade_account_identity` (riga 676), ha un `account_id INTEGER` **grezzo** in chiaro nella tabella `trades` (PK `(account_id, ticket)`), motivato da un bug reale (`AUD0-DB-003`/`NXS-DB-004`: ticket collidenti fra conti diversi sullo stesso backend). Questo è in tensione diretta con lo schema design-only `server/research_scripts/phase7/phase7_19/schemas/runtime_identity_manifest_v1.schema.json`, che richiede esplicitamente `account_id_non_sensitive` ("mai il numero di conto reale in chiaro"). **Riconciliazione scelta** (vedi §3): il nuovo Account Registry usa un alias derivato (`identity.py`), mai il login grezzo; il DB live di `server/app.py` resta **non toccato** e fuori scope — è un sistema diverso (ledger live via LocalBridge, alimentato da eventi EA in tempo reale), con un contesto e una giustificazione propri, già passata in revisione in una fase precedente. I due significati di "account_id" (uno alias qui, uno grezzo lì) coesistono deliberatamente, documentati, non nascosti.

**Toolkit riusato, non duplicato concettualmente** (ma copiato come file, non importato — vedi §4): `server/research_scripts/phase6_6/canonical_utils.py` (hashing/provenance deterministico) e il pattern `IMMUTABLE_RUN_MANIFEST` di `server/research_scripts/phase7/phase7_8g|8h|8i/collect_immutable_run_manifest.py` (raccolta prima di ogni interpretazione, `ea_build_identity.ex5_sha256/source_sha256`).

---

## 2. Architettura RAW / NORMALIZED / DERIVED

```
accounts/<account_id>/
  raw/            copie byte-identiche dei file originali — MAI modificate dopo l'import
  normalized/     Deal / Order / Trade Episode / Account Snapshot canonici (+ provenance)
  derived/        analytics (analytics.py) + report (reports.py)
  runs/<run_id>/  run manifest + artifact per singolo run (Tester o sessione reale/demo)
  account_manifest.json
```

Pipeline: **raw (mai toccato) → csv_formats.py (parser) → normalize.py (canonico + provenance) → verifier.py (giudica, non modifica) → redaction.py (solo su normalized/derived) → manifests.py / analytics.py / reports.py**.

`server/mt5_data_v1/account_package.py` implementa questa struttura di directory (`ensure_layout`, `raw_dir`, `normalized_dir`, `derived_dir`, `run_dir`).

---

## 3. Schemi canonici (`contracts/`)

4 nuovi file, draft-07, stessa convenzione di `contracts/edge-validation-registry.schema.json` (`additionalProperties: false`, `definitions`, `schema_version` const):

- **`mt5-account-registry-v1.schema.json`** — `account_id` = `acct_<sha256(login|broker|server)[:16]>`, mai il login in chiaro. `identity_source` tracciato esplicitamente (`DERIVED_FROM_TRADE_UID`/`DERIVED_FROM_DEAL_EXPORT`/`DECLARED_BY_USER`/`TESTER_SYNTHETIC`).
- **`mt5-trade-history-v1.schema.json`** — `definitions`: `deal` (mappa 1:1 su `HistoryDealGet*`), `order`, `trade_episode` (aggregazione per `position_id`), `account_snapshot`, `provenance` (hash file raw + indice riga), `strategy_attribution` (`VERIFIED`/`PARTIAL`/`UNKNOWN` — mai inferito silenziosamente).
- **`mt5-run-manifest-v1.schema.json`** — generalizza `IMMUTABLE_RUN_MANIFEST`; `artifact_type` enum (`RAW_*`/`NORMALIZED_*`/`DERIVED_*`); `collected_before_any_interpretation`/`no_verdict_computed_here` sempre `true` per costruzione.
- **`mt5-account-manifest-v1.schema.json`** — indice per-account: `runs[]`, `import_log[]` (idempotenza), `data_quality` (`CLEAN`/`WARNINGS`/`FAILED`).

---

## 4. File creati

**Schemi** (4): i file elencati al §3.

**Codice** (`server/mt5_data_v1/`, 12 moduli + `__init__.py`):

| Modulo | Responsabilità |
|---|---|
| `canonical.py` | Hashing/provenance deterministico — stesso pattern di `phase6_6/canonical_utils.py`, **copiato non importato** (quella cartella è ricerca di una fase specifica, non libreria condivisa) |
| `identity.py` | `derive_account_id()` (alias deterministico sha256), mappa privata login→alias (`_private/account_identity_map.json`, **gitignored**) |
| `csv_formats.py` | Sniffing encoding (BOM→UTF-16), detection formato, parser `EA_TRADE_LOG` / `NATIVE_DEAL_EXPORT`, gestione file senza header |
| `normalize.py` | Orchestratore raw→canonico, provenance, `normalize_auto()` |
| `trade_episodes.py` | Ricostruzione posizione da deal (`POSITION_ID_EXACT`) o da EA log (`SEQUENTIAL_HEURISTIC_PER_STRATEGY`, con flag `AMBIGUOUS_FIFO_MULTIPLE_OPEN_PENDING`) |
| `verifier.py` | 7 controlli di qualità dati (duplicati, volume negativo, cronologia, account mismatch, hash corrotto, timestamp mancanti, pairing ambiguo) |
| `redaction.py` | Rimozione del login grezzo da campi testuali liberi su normalized/derived |
| `import_state.py` | `IMPORT_NEW`/`APPEND`/`RESCAN`/`SKIPPED_DUPLICATE` via confronto byte-a-byte con la copia raw salvata |
| `account_package.py` | Struttura directory per account |
| `manifests.py` | Costruzione Run Manifest / Account Manifest |
| `account_registry.py` | CRUD Account Registry (store JSON, come `funding_v1/*_v1.json`) |
| `analytics.py` | Metriche account-level, strategy-level, confronto cross-account normalizzato |
| `reports.py` | `ACCOUNT_PERFORMANCE_SUMMARY_V1`, executive summary multi-account per Jarvis |

**Test** (`server/tests/`, 8 file, 65 test): `test_mt5_data_v1_csv_formats.py`, `test_mt5_data_v1_normalize.py`, `test_mt5_data_v1_trade_episodes.py`, `test_mt5_data_v1_verifier.py`, `test_mt5_data_v1_identity_redaction.py`, `test_mt5_data_v1_import_state.py`, `test_mt5_data_v1_manifests_registry.py`, `test_mt5_data_v1_analytics.py`.

**Esempi reali generati dal codice** (non scritti a mano): `docs/examples/MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1/*.json` (account registry, run manifest, account manifest, trade episodes, deals, performance summary) — prodotti eseguendo la pipeline reale sul file diagnostico `nxs_diag_deals_export_r003.csv`.

## File modificati

- **`.gitignore`**: aggiunta `server/mt5_data_v1/_private/` (mappa privata login→alias, mai committata — stesso pattern di `LocalBridge/*.config.json`).

---

## 5. Esempio reale — Run Manifest

(generato da `manifests.artifact_entry_from_file()` + `manifests.build_run_manifest()` sul file diagnostico reale)

```json
{
  "schema_version": 1,
  "run_id": "phase7_9h_diag_r003",
  "account_id": "acct_9dea2cd40df8c343",
  "terminal_role": "TESTER_TERMINAL",
  "symbol": "GOLD",
  "generated_at": "2026-10-06T17:23:15.839808+00:00",
  "collected_before_any_interpretation": true,
  "no_verdict_computed_here": true,
  "artifacts": [
    {
      "artifact_type": "RAW_DEAL_EXPORT",
      "source_path": "server/research_scripts/phase7/phase7_9h/raw_data/nxs_diag_deals_export_r003.csv",
      "sha256": "93953d93419a20b843e6bac0cb0271a6cf8cf3071ce3d0005d76b1ed353fc534",
      "size_bytes": 16123,
      "row_count": 95,
      "collected_at": "2026-10-06T17:23:15.839773+00:00"
    }
  ]
}
```

## 6. Esempio reale — Account Manifest

```json
{
  "schema_version": 1,
  "account_id": "acct_9dea2cd40df8c343",
  "environment": "REAL",
  "broker": "XMGlobal",
  "server": "XMGlobal-Real7",
  "runs": [{"run_id": "phase7_9h_diag_r003", "artifact_count": 1}],
  "import_log": [{"source_sha256": "9395...fc534", "import_mode": "IMPORT_NEW", "rows_ingested": 95}],
  "data_quality": {
    "status": "CLEAN",
    "checks_passed": ["raw_hash_matches_disk", "no_duplicate_deal_ids", "no_negative_volume",
      "exit_not_before_entry", "account_id_matches_expected", "no_missing_timestamps",
      "no_ambiguous_fifo_pairing"],
    "checks_failed": []
  },
  "redaction_applied": true
}
```

## 7. Esempio reale — Trade Episode normalizzato (da deal reali)

```json
{
  "episode_id": "acct_9dea2cd40df8c343:4",
  "position_id": 4,
  "symbol": "GOLD",
  "strategy_attribution": {"status": "UNKNOWN"},
  "side": "BUY",
  "open_time": "2019-06-21T05:30:00+00:00",
  "close_time": "2019-06-21T09:39:40+00:00",
  "volume_opened": 0.01,
  "volume_closed": 0.01,
  "avg_open_price": 1407.33,
  "avg_close_price": 1390.57,
  "realized_pnl": -16.76,
  "status": "CLOSED",
  "deal_ids": [4, 5],
  "provenance": {
    "raw_source_sha256": "93953d93419a20b843e6bac0cb0271a6cf8cf3071ce3d0005d76b1ed353fc534",
    "pairing_method": "POSITION_ID_EXACT"
  }
}
```

`strategy_attribution.status = "UNKNOWN"` qui non è un bug: il formato `NATIVE_DEAL_EXPORT` reale non porta un nome di strategia nel `comment`/`magic` di questo file diagnostico — nessuna inferenza è stata inventata. Il formato `EA_TRADE_LOG` invece porta `strategy` direttamente → `status: "VERIFIED"` (vedi test `test_ea_trade_log_simple_pairing_not_flagged_ambiguous`).

---

## 8. Verifier — i 7 controlli implementati

`raw_hash_matches_disk`, `no_duplicate_deal_ids`, `no_negative_volume`, `exit_not_before_entry`, `account_id_matches_expected`, `no_missing_timestamps`, `no_ambiguous_fifo_pairing`. Stato: `CLEAN` (0 fallimenti) / `WARNINGS` (1-2) / `FAILED` (3+) — mai un numero nascosto, sempre `checks_passed` + `checks_failed` entrambi visibili.

**Verifica reale, non ipotetica**: sul file `NEXUS_trades_serious_3y_run3.csv` (223 episodi ricostruiti), il verifier ha segnalato correttamente **183 episodi con pairing FIFO ambiguo** (`WARNINGS`) — perché quel run usa il piramidaggio (più posizioni aperte della stessa strategia in parallelo), rendendo il pairing sequenziale genuinamente inaffidabile. Il sistema lo dichiara invece di nasconderlo.

---

## 9. Analytics disponibili

- **Account-level** (`analytics.compute_account_metrics`): `total_trades`, `win_rate`, `profit_factor`, `expectancy`, `total_realized_pnl`, `max_drawdown` (proxy su PnL cumulativo realizzato, **dichiarato esplicitamente non equity reale** — manca balance iniziale/depositi/prelievi fuori-trade).
- **Strategy-level entro account** (`analytics.compute_strategy_metrics`): raggruppa per `strategy_attribution.strategy_name`; gli episodi `UNKNOWN` finiscono in un bucket `__UNKNOWN__` separato, mai mescolati.
- **Cross-account normalizzato** (`analytics.compare_accounts`): mai PnL grezzo — solo `pnl_pct` su `starting_balance`; valuta mista fra conti segnalata (`mixed_currency_warning`); un conto senza balance/currency noti resta `comparable: False`, non escluso silenziosamente.
- **Report**: `reports.build_account_performance_summary()` (`ACCOUNT_PERFORMANCE_SUMMARY_V1`), `reports.build_multi_account_executive_summary()` (per Jarvis, elenca esplicitamente quali account hanno `data_quality.status == FAILED`).

---

## 10. Test — 65 test, 8 file, tutti verdi

Copertura dei 18+ scenari richiesti: import raw (`test_import_raw_file_first_time_is_new`), import duplicato (`test_classify_import_duplicate_when_identical`), CSV malformato (`test_malformed_csv_*`), account mismatch (`test_account_mismatch_detected`), timezone non convertita silenziosamente (`test_time_is_tagged_utc_without_silent_conversion`), ricostruzione deal/episodio (`test_simple_open_close_full_episode`), partial close (`test_partial_close_leaves_status_partially_closed`), deal multipli per posizione (`test_multiple_in_deals_averaged_open_price`), aggregazione commission/swap, attribution known/unknown (`test_ea_trade_log_simple_pairing_not_flagged_ambiguous` / native export UNKNOWN), confronto cross-account (`test_compare_accounts_flags_mixed_currency`), equity/drawdown proxy (`test_max_drawdown_proxy_detects_dip`), artifact corrotto (`test_corrupted_raw_file_hash_mismatch_detected`), redazione segreti (`test_redact_bundle_replaces_login_in_free_text_fields`), preservazione raw (`test_normalize_does_not_modify_raw_file`, `test_import_raw_file_append_detected`), determinismo normalizzato (`test_normalize_native_deal_export_is_deterministic_in_payload`), round-trip manifest (`test_run_manifest_round_trip`, `test_account_manifest_round_trip`).

```
65 passed in 1.16s  (server/tests/test_mt5_data_v1_*.py)
```

**Regressione sulla suite esistente**: eseguita in background subito dopo (vedi riquadro sotto, aggiornato con l'esito reale).

**Regressione sulla suite completa** (`server/tests/`, 913 test totali dopo l'aggiunta dei 65 nuovi):

```
913 passed, 1 skipped, 2 failed in 161.23s
```

I 2 fallimenti sono gli stessi preesistenti già documentati in `MT5_TERMINAL_IDENTITY_GUARD_V1.md` (modulo MACD Phase 1 di Codex, `server/research_scripts/contextual_edge_phase1/` — confermato senza alcun riferimento a `mt5_data_v1`/`LocalBridge`, non causati da questo lavoro).

**Scoperta laterale, non richiesta da questo task ma trovata durante la regressione e corretta**: la prima esecuzione ha mostrato un **terzo fallimento**, `test_command_contract.py::test_single_worker_source_and_manifest_checksums` — `deploy/deployment-manifest.json` conteneva l'hash sha256 di `LocalBridge/nexus_local_worker.py` **da prima** della modifica fatta nella fase `MT5_TERMINAL_IDENTITY_GUARD_V1` (commit `edb3915`, già review-ato e committato): quella fase ha modificato il file reale ma non ha rigenerato il manifest di deployment, lasciando nel commit un hash certificato sbagliato. **Non è un effetto di questo task** (nessun file toccato qui tocca `LocalBridge/` o `deploy/`) — l'ho corretto rieseguendo il generatore canonico già esistente (`python3 contracts/generate_deployment_manifest.py`), che ha prodotto il nuovo hash corretto. **Anche questa correzione resta non committata**, in attesa della stessa review — `deploy/deployment-manifest.json` ha ora un diff di 2 righe (solo l'hash) pronto, separato logicamente da tutto il resto di questo report.

---

## 11. Gap residui (dichiarati, non implementati qui)

- **Order e Account Snapshot**: gli schemi esistono (`mt5-trade-history-v1.schema.json#/definitions/order` e `#/definitions/account_snapshot`) ma **nessun parser reale** li popola — nel census non è stato trovato un file raw di export ordini o di snapshot equity/balance istantaneo verificabile byte-per-byte in questa sessione. Non inventato un parser per un formato non visto.
- **Pairing EA_TRADE_LOG resta euristico per costruzione**: non esiste nel formato un `position_id` reale — qualunque euristica resterà "migliore ipotesi", mai certezza, quando ci sono posizioni piramidate della stessa strategia in parallelo (vedi §8).
- **`max_drawdown` è un proxy sul PnL realizzato cumulato**, non la vera equity curve del conto (serve anche balance iniziale + depositi/prelievi + floating P&L delle posizioni aperte — nessun dato disponibile per questo in nessun formato verificato).
- **Nessun parser per export manuale "History tab" del broker** (locale italiano con migliaia separate da spazio, ipotizzato dal fork del census ma **non trovato un file reale** in questo repo per confermarlo byte-per-byte — non implementato senza un campione reale).
- **Daily/monthly account summary, open positions snapshot, exposure analytics** (sez.20/21/22 della richiesta): non implementati come moduli separati — gli account-level metrics di `analytics.py` sono la base su cui costruirli, ma richiedono Account Snapshot reali (vedi gap sopra) per avere senso.
- **TDR integration**: solo identificatori compatibili riservati (`account_id`, `episode_id`, `deal_ticket` sono già stabili e citabili da un futuro Trade Decision Record) — nessun campo TDR aggiunto, come richiesto.
- **Nessuna pulizia/migrazione dei dati esistenti**: questo contratto non ha importato nessun dato storico reale negli `accounts/` — è pronto per farlo, ma nessun `accounts/` è stato popolato in modo permanente in questa sessione (solo esempi in `docs/examples/`).

---

## 12. Proposta di integrazione con un futuro MT5_AUTOMATED_TESTER_CONTROL_PLANE_V1

Questo contratto è stato progettato perché un futuro control plane lo consumi senza modifiche:

1. **Al termine di un run del Tester**, il control plane chiamerebbe `manifests.artifact_entry_from_file()` per ogni output raw (report HTM, CSV deal/trade log, journal, `.ini`) e `manifests.build_run_manifest()` — stesso pattern già usato manualmente in `collect_immutable_run_manifest.py`, ora a libreria.
2. **Identità account**: il control plane chiamerebbe `identity.register_account_identity()` una volta per account/profilo tester noto, poi userebbe sempre l'`account_id` alias ritornato — mai il login nei suoi log/comandi.
3. **Import**: `import_state.import_raw_file()` darebbe gratis l'idempotenza (ri-eseguire lo stesso run due volte non duplica).
4. **Dopo l'import**: `normalize.normalize_auto()` → `verifier.verify_bundle()` → se `CLEAN`/`WARNINGS`, `redaction.redact_bundle()` → scrittura in `accounts/<account_id>/normalized/`.
5. **Un comando `handle_run_tester` futuro** (non costruito qui, coerente con l'esclusione di scope) potrebbe usare `LocalBridge/nexus_terminal_identity_guard.py` (già esistente, committato in `edb3915`) per il lock/verifica terminale, e DOPO il run chiamare questa pipeline — i due sistemi sono già compatibili per costruzione (nessuna modifica necessaria a nessuno dei due per farli comunicare).
6. Il control plane NON dovrebbe mai scrivere direttamente dentro `accounts/<id>/raw/` — solo tramite `import_state.import_raw_file()`, per mantenere l'idempotenza e la cronologia degli import.

---

## Esclusioni di scope rispettate

Nessun tester orchestrator completo, nessuna modifica a trading/execution/risk MQL5, nessuna modifica al broker/API, nessuna VM/containerizzazione, nessun login automatico, nessun movimento di denaro automatico, nessuna password/token gestito in alcun punto del codice.

---

MT5_RUN_AND_ACCOUNT_DATA_CONTRACT_V1_READY_FOR_REVIEW
