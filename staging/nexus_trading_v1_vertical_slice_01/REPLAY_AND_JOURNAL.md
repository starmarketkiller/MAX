# REPLAY_AND_JOURNAL — Vertical Slice 01 (H1_A)

## 1. Journal (`journal/journal.py`)

Riusa **verbatim** (import, non copia) lo schema di hash-chaining già
usato da `phase5d_shadow_engine_v1.shadow_mode` per i `DecisionEvent`,
applicato qui a dizionari generici (Decision record, Paper Attempt
record):

```
record = {"prev_hash": <hash della riga precedente o GENESIS_HASH>, "payload": <dict>}
record["record_hash"] = canonical_hash(record)
```

- `append_records()` apre sempre il file in modalità `"a"`
  (append-only) — **mai** `"w"`/`"r+"`, quindi una riga già scritta
  non può essere sovrascritta da questo stesso processo.
- `verify_chain()` ricalcola ogni hash dall'inizio e confronta sia
  `prev_hash` che `record_hash` — rileva qualunque riscrittura,
  riordino o cancellazione di righe intermedie, non solo un controllo
  "il file esiste".
- `read_all()` restituisce solo i `payload` (la parte "utile"),
  usato da `scripts/export_cockpit_data.py` e dai test.

Verificato in `TestJournalIntegrity`:
- `test_hash_chain_detects_tampering` — modifica un `payload` a metà
  file, conferma che `verify_chain()` ritorna `False`.
- `test_journal_is_append_only_never_truncates_existing` — scrive in
  due passate separate, conferma che la prima passata resta intatta e
  la catena resta valida sull'intero file.
- `test_strategy_version_present_on_every_record` — nessun record
  scritto senza `strategy_id`/`strategy_version` espliciti.

## 2. Replay (`replay/replay.py`)

Due funzioni, entrambe pure (nessuno stato di Paper Engine coinvolto):

- `run_decisions_over(bars)` — richiama
  `decision_engine.evaluate_series(bars, lambda: False)`: valuta la
  sequenza di decisioni **assumendo sempre nessun tentativo aperto**
  (`has_open_attempt` sempre `False`). Serve a isolare il
  comportamento del motore decisionale puro dal comportamento di
  deduplicazione del Paper Engine, che è testato separatamente.
- `verify_no_future_leakage(store, as_of_sample_indices)` — per ogni
  indice campione `i`: esegue un run TRONCATO a
  `bars_as_of(full_bars[i].available_at_utc)` e lo confronta,
  campo per campo (`h1a_decision`, `h1a_reason_code`,
  `level_high_observed`, `level_low_observed`, `candidate_detail`),
  con il prefisso corrispondente di un run FULL sull'intero dataset.
  Non è solo un assert "nessun bar futuro nella lista" — è una **prova
  comportamentale**: se un bar futuro avesse mai influenzato una
  decisione passata, i due run divergerebbero e il confronto fallirebbe.

Eseguito realmente sui dati (non solo su fixture sintetiche) in
`TestHistoricalAllowedDataLayer::test_anti_lookahead_replay_passes_on_real_data`:
7 cutoff campionati sull'intero dataset reused, **0 mismatch**,
`passed=True`.

## 3. Esecuzione end-to-end (`scripts/run_full_replay.py`)

Driver che collega `BarStore → decision_engine → paper_engine →
journal` su tutti i 4.808 bar del dataset reused:

1. Per ogni bar, in ordine: avanza un eventuale tentativo aperto
   (`PaperEngine.advance_open_attempt`) **prima** di valutare una
   nuova decisione sullo stesso bar — garantisce che un'uscita sullo
   stesso bar sia registrata prima che un nuovo segnale sullo stesso
   bar possa essere considerato (comunque un solo tentativo alla
   volta in entrambi i casi).
2. Calcola i livelli Donchian N=20 con una finestra scorrevole
   (`collections.deque(maxlen=20)`), aggiornata **dopo** la
   valutazione del bar corrente (mai con il bar corrente incluso nella
   propria finestra — coerente con §2 del contratto).
3. Apre un nuovo tentativo di carta se la decisione è BUY/SELL.
4. A fine ciclo, chiude qualunque tentativo ancora aperto
   (`close_still_open_at_dataset_end`).
5. Scrive entrambi i journal, verifica entrambe le catene hash, scrive
   `logs/run_summary.json` con i conteggi aggregati.

Output dell'ultima esecuzione reale (vedi `TEST_RESULTS.md` per il
dettaglio dei test, questo è solo l'output del driver):

```json
{
  "total_bars_processed": 4808,
  "decision_counts": {"WAIT": 4447, "BUY": 156, "SELL": 205},
  "total_paper_attempts": 361,
  "outcome_counts": {"TP_HIT": 150, "SL_HIT": 211},
  "decisions_log_chain_verified": true,
  "attempts_log_chain_verified": true
}
```

**Nessuna interpretazione economica di questi numeri appartiene a
questo documento** — vedi `LIMITATIONS.md` per la dichiarazione
esplicita "no economic claim" che vale per l'intero run.

## 4. Export per la Cockpit Demo (`scripts/export_cockpit_data.py`)

Legge gli stessi artefatti già prodotti da `run_full_replay.py`
(`logs/decisions.jsonl`, `logs/paper_attempts.jsonl`) più `BarStore`
per i campi OHLC — **non rilancia una nuova simulazione**. Seleziona
una finestra fissa di 260 bar (i primi 260 del dataset, non scelti per
risultato favorevole) e scrive `cockpit_demo/data/cockpit_data.json`,
poi `scripts/build_cockpit_html.py` lo incorpora inline in
`cockpit_demo/index.html` per renderlo autocontenuto (vedi
`cockpit_demo/README` implicito in `FINAL_DECISION_CARD.md` §Cockpit).
