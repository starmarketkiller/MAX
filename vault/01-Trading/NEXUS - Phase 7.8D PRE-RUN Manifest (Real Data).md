# NEXUS - Phase 7.8D PRE-RUN MANIFEST (dati reali)

**Baseline:** `92ec007` (Phase 7.8D, conclusione precedente `PRE_RUN_SEAL_BLOCKED_NO_DATA_ACCESS`). L'utente ha confermato l'accesso reale al terminale MT5 - verificato concretamente e corretto: quella conclusione controllava i sotto-account broker sbagliati. Questa fase produce il **PRE-RUN MANIFEST reale** con date/hash/copertura dati verificati, non fabbricati.

**Conferma esplicita: SERIOUS_VALIDATION_NOT_EXECUTED. NO STRATEGY OUTCOME ACCESSED. NO TRADE RESULTS GENERATED.**

---

## Correzione della conclusione precedente

`volatility_breakout_prerun_seal_status_v1.json` (hash invariato, non modificato) aveva controllato le cache storiche sotto `XMGlobal-MT5 7`/`9` - non l'account REALMENTE connesso di default da questo terminale (`XMGlobal-MT5 10`, login `345277936`, DEMO), il cui storico GOLD risultava sincronizzato fino a pochi giorni prima, non ~2 mesi.

## Come e' stato verificato (azione reale, non solo lettura di file)

1. Scritto **`NXS_VolBrkPrerunCoverageAudit.mq5`** - script READ-ONLY (nessun `OrderSend`, nessun `NEXUS_v1` incluso, nessuna EA/strategia toccata) che sonda la copertura tick/bar di GOLD su 37 mesi + una query wide-range.
2. Compilato con MetaEditor (0 errori), deployato in `MQL5/Scripts` del terminale di ricerca (`C:\MT5-Tester`, cartella dati reale `.../Terminal/7F8EC41F011085EB9C65165AE426B5A6`).
3. Lanciato `terminal64.exe /config:<ini>` con `[StartUp] Script=...` (stesso pattern gia' stabilito nel progetto), atteso il completamento **via marker file reale** (non un poll a iterazioni fisse - lezione gia' in memoria di progetto), confermato dopo ~260s.
4. Terminale chiuso. File di output reali copiati in `raw_coverage_audit/` per provenienza.

## Scoperta onesta: la copertura reale non e' "esattamente 3 anni"

| | |
|---|---|
| Primo tick reale GOLD | **2023-12-20 12:06:50** (191.824.954 tick nella query wide, err=0) |
| Ultimo tick reale GOLD | **2026-09-21 23:58:59** (essenzialmente "ora") |
| Barre H4 storiche | da 2023-09-08 (piu' indietro dei tick reali - cache OHLC indipendente, atteso) |

`TOTAL_TEST_WINDOW` e' quindi vincolato a partire dalla copertura tick REALE (2023-12-20), non da una data nominale di comodo "3 anni fa" - **~2 anni e 9 mesi**, non 3 anni pieni. Un vincolo di dati reale, dichiarato onestamente.

## Finestre temporali (tutte con date reali, non fabbricate)

| Finestra | Start | End | Durata |
|---|---|---|---|
| `TOTAL_TEST_WINDOW` | 2023-12-20 12:06:50 | 2026-09-21 23:58:59 | 1006 giorni |
| `PRIMARY_FRESH_VERDICT_WINDOW` | 2023-12-20 12:06:50 | 2026-03-01 | 801 giorni |
| `PREVIOUSLY_OBSERVED_DIAGNOSTIC_WINDOW` | 2026-03-01 | 2026-09-01 | 184 giorni (fissa, identica al fast-structural gia' fatto) |
| **`NEWLY_ELAPSED_TAIL_SEGMENT`** (scoperta in questa fase) | 2026-09-01 | 2026-09-21 | 20 giorni |

**`NEWLY_ELAPSED_TAIL_SEGMENT`** non era previsto da 7.8B/7.8C: poiche' il tempo reale e' avanzato da quando la finestra `PREVIOUSLY_OBSERVED` fu fissata, esiste ora un piccolo segmento genuinamente mai osservato dopo di essa - troppo corto per un tercile affidabile da solo, riportato come diagnostica di replica separata, **mai fuso silenziosamente nel verdetto primario ne' scartato senza dichiararlo**.

## T1/T2/T3 (tercile cronologico, non "Year 1/2/3")

| | Start | End |
|---|---|---|
| T1 | 2023-12-20 12:06:50 | 2024-09-12 16:04:33 |
| T2 | 2024-09-12 16:04:33 | 2025-06-06 20:02:16 |
| T3 | 2025-06-06 20:02:16 | 2026-03-01 |

Durate: 267 / 267 / 267 giorni. `union_equals_primary_fresh_window=True`, `no_gaps=True`, `no_overlap=True`.

## Correzione al modello tick di 7.8B (annotazione)

7.8B aveva scritto genericamente "Model=1" - verificato contro il precedente reale gia' eseguito in questo progetto (SAR Serious 3Y, validazione Dukascopy indipendente): la convenzione stabilita e' **Model=4 (Every tick based on real ticks)**. Annotato qui, 7.8B non modificato retroattivamente.

## Copertura tick per sotto-periodo (37 probe mensili reali)

33/37 probe con tick reali trovati (`REAL_TICK_RESOLVABLE`), 4/37 senza (`EXECUTION_ORDER_POTENTIALLY_UNRESOLVED`) - **tutti e 4 cadono prima dell'inizio di `TOTAL_TEST_WINDOW`** (gia' vincolato alla copertura reale), quindi nessun trade nella finestra effettivamente usata dal verdetto primario ricade in un mese senza copertura.

## Hash: rappresentazione dichiarata esplicitamente

Non i file binari `.hcc`/`.tkc` (multi-GB, in crescita continua) - il **coverage audit report stesso** (CSV + summary), un fingerprint deterministico e riproducibile di "quali dati erano disponibili al sealing".

## Seal verification (verificata due volte - dal builder E da uno script indipendente)

Tutti e 6 i controlli richiesti: campi popolati, hash validi (ricalcolati, non copiati), ordinamento date valido, FRESH/OBSERVED non sovrapposte, T1/T2/T3 partizionano esattamente FRESH, hash di protocollo corrispondono agli artifact frozen reali, nessun campo di outcome presente. **`verify_volatility_breakout_prerun_manifest.py`** (script separato, ri-deriva tutto dai campi grezzi, non si fida del blocco `seal_verification` del builder) conferma lo stesso verdetto.

## Final status

**`PRE_RUN_SEAL_VERIFIED_READY_TO_RUN`** - il Serious validation resta **non eseguito ed esplicitamente non autorizzato automaticamente** da questo seal (passo separato e successivo).

## Regressione

64/64 PASS su questa suite. **0 regressioni** sulle altre 28 suite Phase 7 (29 totali).

## Deliverables

`volatility_breakout_serious_validation_prerun_manifest_v1.json`, `build_volatility_breakout_prerun_manifest.py`, `verify_volatility_breakout_prerun_manifest.py`, `test_volatility_breakout_prerun_manifest.py`, `raw_coverage_audit/` (CSV/summary/marker reali), `NXS_VolBrkPrerunCoverageAudit.mq5` (script sorgente).

---

**SERIOUS_VALIDATION_NOT_EXECUTED. NO STRATEGY OUTCOME ACCESSED. NO TRADE RESULTS GENERATED.**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
7.8D:
PRE_RUN_SEAL_VERIFIED_READY_TO_RUN ✓
(dati reali, non fabbricati)
PROSSIMO:
autorizzazione esplicita del RUN
```

Il manifest e' su GitHub, verificabile riga per riga. La catena e' completa: hypothesis frozen -> VoI -> decision rules -> execution rules -> data identity -> temporal partitions -> outcomes ancora non visti. Manca solo l'autorizzazione esplicita a eseguire.
