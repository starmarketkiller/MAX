# DATA_PROVENANCE

## Sorgente riusata, non ricostruita

`server/research_scripts/phase5e_causal_replay_v1/dataset.py`
(canonico, mai modificato — solo importato) — già verificato in una
missione precedente, qui riusato byte-per-byte:

- **Symbol**: XAUUSD. **Timeframe**: H4. **Price side**: BID.
- **Copertura**: 2019-02-03T20:00:00Z → 2022-02-03T16:00:00Z
  (4.808 barre, dopo l'esclusione dell'ultima barra di confine —
  vedi sotto).
- **Classificazione**: `DISCOVERY_REUSE` — esplicitamente **non un
  vero holdout** (`server/research_datasets/market_state_v1/README.md`).
- **File sorgente**: `server/research_datasets/market_state_v1/xauusd_h4_bars.csv`
  + `market_state_dataset_v1.csv`, con hash SHA-256 pinnati in
  `dataset.PINNED_SHA256` e verificati fail-closed ad ogni caricamento
  (`dataset.verify_file_hashes()` — se un file cambia, il caricamento
  solleva `IntegrityError`, non procede silenziosamente).

## Perché NON è una cache con holdout filtrata in memoria

Il mandato vieta esplicitamente "leggere una cache contenente holdout
per poi filtrarla in memoria". Questa sorgente non lo fa:

1. Il file CSV stesso **non contiene** la finestra sigillata — la
   copertura del file termina al 2022-02-03, la sealed FINAL_HOLDOUT
   del progetto (2026-02-04→2026-09-16, vedi
   `server/research_scripts/phase7/final_holdout_seal_v1.json`) è un
   periodo completamente diverso e successivo, non presente in questo
   file in nessuna forma.
2. C'è un secondo holdout storico, più vecchio e distinto
   (`DATASET-P6-H006-HOLDOUT-20220204-20230203`), il cui **primo
   istante** (2022-02-04T00:00:00Z) coincide esattamente con la
   chiusura dell'ultima barra teoricamente presente nel file
   (bar_epoch 1643918400, apertura 2022-02-03T20:00:00Z). `dataset.py`
   **esclude quella barra per intero** (`LAST_SAFE_BAR_EPOCH_EXCLUSIVE`),
   non la filtra dopo averla letta — è la sorgente stessa, già
   pre-tagliata, verificabile leggendo il codice.

## Timestamp di disponibilità (as_of / available_at)

Ogni barra riporta `available_at_utc = bar_open_utc + 4h` (vedi
`data_layer/bar_store.py`) — l'istante in cui quella barra è
realmente chiusa e quindi conoscibile. Il metodo `BarStore.bars_as_of(t)`
restituisce solo barre con `available_at_utc <= t`, **mai** una barra
ancora in formazione. Verificato con un test diretto (0 violazioni su
un campione, vedi `TEST_RESULTS.md`).

## Sessioni e timezone

Tutte le barre sono in UTC (`bar_boundaries_utc: [0,4,8,12,16,20]`,
dal manifest del dataset) — nessuna conversione di fuso orario
applicata o necessaria in questa versione. Nessun concetto di
sessione (Asia/London/NY) è usato dal motore H1-A (fuori scope
dichiarato nel contratto).

## MID vs BID/ASK

Il dataset è **solo BID** — non esiste una serie ASK separata in
questa sorgente. **DESIGN_ASSUMPTION_V1 dichiarata nel contratto**:
questa versione non sintetizza un prezzo MID, usa BID come unico
riferimento per livello/sweep/reclaim/entry, e modella il costo di
esecuzione separatamente mediante `avg_spread` (colonna reale del
dataset, non un numero inventato) — vedi `PAPER_ENGINE` e
`STRATEGY_CONTRACT_H1_A.md` §7.

## Manifest della sorgente (riferimento, non duplicato)

`server/research_datasets/market_state_v1/manifest.json` —
`dataset_id=MARKET_STATE_V1_436265d450475aaa`,
`validation_integrity=DISCOVERY_REUSE`. Hash dei 2 CSV verificati
corrispondenti in questa sessione (vedi log di test). Nessuna
modifica a questo manifest o ai CSV sorgente.
