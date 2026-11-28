# Inventario dei dati storici — CHART-HISTORICAL-EXPANSION-01 (Fase 01)

Metodo: solo elenchi di directory, dimensioni, manifest e rapporti di governance (metadati). **Nessun contenuto di finestre sigillate è stato letto**; MetaTrader non è stato avviato; nessuna autorizzazione è stata modificata; nessun download.
Nota di trasparenza: durante l'ispezione dei metadati di `server/data_cache_m5/` è stato stampato per errore l'inizio (le prime 3 candele, 2021-11-29) di `dukascopy_xauusd_m5.json`; è un periodo precedente a ogni finestra sigillata e non è stato usato.

Quattro livelli, **distinti** (un dato può esistere ma non essere utilizzabile):
**Esiste** = presente su disco · **Accessibile** = leggibile senza MetaTrader e senza nuovo download · **Autorizzato** = coperto da `server/chart_authorization.json` (decisione D2) · **Utilizzabile dal Lab** = oggi presente nello store e servito dal Chart.

| # | Dataset | Esiste (copertura, dimensione) | Accessibile | Autorizzato per il Chart | Utilizzabile dal Lab oggi |
|---|---|---|---|---|---|
| 1a | **Dukascopy Phase 7 — `development_discovery`** (tick bid/ask) | 2023-02-04 → 2024-08-03 · 547 giorni · **61.404.484 tick** · file `decoded/{2023,2024}/*.csv.gz` | sì (CSV gz) | **SÌ** (`allowed_segment_names: ["development_discovery"]`) | **SÌ — store esteso costruito in questa missione** (H4 2.393 barre, M1 530.331) |
| 1b | Dukascopy Phase 7 — `development_internal_validation` | 2024-08-04 → 2025-05-03 · 273 giorni · 50.636.469 tick | sì | **NO** (dichiarato DEVELOPMENT ma esplicitamente non elencato dalla decisione D2) | NO |
| 1c | Dukascopy Phase 7 — `locked_validation` | 2025-05-04 → 2026-02-03 · 276 giorni · 58.428.170 tick | — | **mai autorizzabile** (un solo passaggio confirmatorio) | NO — **non letto** |
| 1d | Dukascopy Phase 7 — `final_holdout` (SIGILLATO) | 2026-02-04 → 2026-09-16 · 225 giorni · 56.013.167 tick | — | **mai autorizzabile** | NO — **non letto** |
| 2 | Archivio Dukascopy Phase 5 (`server/data_cache/dukascopy_phaseH`) | 2019-02-03 → 2022-02-03 · 1.097 giorni · 148.097.525 tick · 1.587 MB | sì | NO (nessun record) · finestre "SPESE" (Phase 5/H004, contaminate) | NO |
| 3 | Archivio Dukascopy Phase 6 (`phase6/data_cache_holdout`) | 2022-02-04 → 2023-02-03 · 365 giorni · 53.486.174 tick · 598 MB | — | NO · **era un holdout (H006), speso** | NO — **non letto** |
| 4 | Cache M5 JSON (`server/data_cache_m5`, 60 MB) | candele M5 dal 2021-11-29 al 2026-08-14 (progresso 1.720/3.651 giorni, 224.683 candele, **recupero incompleto**) | sì | NO · **attraversa finestre sigillate** | NO |
| 5 | MARKET_STATE_V1 (`research_datasets/market_state_v1`, 2,5 MB) | 2 CSV di feature derivate, classificazione `DISCOVERY_REUSE` | sì | NO (non è OHLC) | NO |
| 6 | Storici MetaTrader `.hcc`/`.tkc` (broker XM e altri) | 3 terminali / 8 basi (server di broker): GOLD M1 `.hcc` dal 2001/2008/2014 al 2026 (6–26 file per base, 9–257 MB); tick `.tkc` dal 2022-01 / 2023-09 / 2023-12 al 2026 (fino a 1.255 MB per base) | **NO** (formato proprietario; serve MetaTrader o un export; nessun terminale avviato) | NO · orologio del terminale non verificato | NO |
| 7 | Export XM 16–20/11/2026 (`NEXUS_CHART_INT_03/runtime/gold`) | 6.776 barre M1 bid · 2.123.243 tick (non su disco) · hash `f57f306c…` | sì | **SÌ** (finestra esplicita) | **SÌ** (store XM, 5 giorni: H4 = 30 barre) |
| 8 | Store già costruiti | `NEXUS_CHART_REAL_DATA_V1/store`: XM + **campione Dukascopy di 12 giorni** (0,8 MB); nuovo `NEXUS_CHART_HISTORICAL_EXPANSION_01/store`: XM + Dukascopy 547 giorni (20,4 MB) | sì | come righe 1a e 7 | sì |
| 9 | Statistiche MQL5 (`MQL5/Files/NEXUS/nexus_stats_GOLD_PERIOD_M15.csv`, 6 KB) | statistiche, non OHLC | sì | NO | NO |

Totale tick Phase 7: 226.482.290 in 1.321 file giornalieri (1,64 GB compressi; il "≈2,5 GB" dei documenti precedenti era una stima). Spazio libero sul PC: 158 GB — **non** è lo spazio di Render.

## Provenienza, orologio, continuità, timeframe
* **Dukascopy**: tick `epoch_ms,bid,ask,bid_vol,ask_vol`; costruzione barre dal solo **bid**. Orologio: "UTC per costruzione" dichiarato dal downloader; il rapporto d'integrità (`PASS_WITH_NOTES`) lo dice *non da scansione*. **Non è il feed MT5 del broker XM e non va mescolato con esso.**
* **Continuità (rapporto d'integrità, 1.321 giorni)**: nessuna data mancante, 0 timestamp non monotoni, 0 tick duplicati, 0 prezzi impossibili, 0 anomalie di spread; 4 giorni feriali a zero tick (2023-04-07, 2024-03-29, 2025-04-18, 2026-04-03: Venerdì Santo). Nella finestra autorizzata: 2023-04-07 e 2024-03-29.
* **XM**: orologio del terminale ≠ UTC (+7.200.307 ms osservati), calendario del broker non verificato.
* **Timeframe**: dai tick o dall'M1 si ottengono tutti i 9 (M1, M5, M15, M30, H1, H4, D1, W1, MN1); lo store li contiene tutti.
* **Finestre sigillate**: `final_holdout_seal_v1.json` (2026-02-04 → 2026-09-16) e `locked_validation`; la guardia di partizione le nega per costruzione (verificato: il giorno 2024-08-04 e il 2023-02-03 sono rifiutati).

## Conclusione
Esistono ≈428 milioni di tick Dukascopy (Phase 5 + 6 + 7) e storici MT5 pluriennali, ma **l'unico storico lungo già autorizzato e immediatamente utilizzabile è la partizione `development_discovery` del Phase 7 (18 mesi)**. Gli storici MT5 non sono accessibili senza un export autorizzato; i dati sigillati o spesi restano esclusi.
