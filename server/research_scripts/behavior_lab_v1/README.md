# Behavior Lab V1: H4 impulse → pullback → M15 confirmation

Ipotesi pre-registrata: `prereg_BL-H4M15-IPC-001.json` (parametri congelati, hash `7c66d51c…`). Una sola famiglia di eventi, nessuna ricerca di strategie.

## Dove sono i dati

I tick Dukascopy Phase 7 (2023-02-04 → 2026-09-16, 226 M tick, bid/ask) stanno **solo sul PC di ricerca**:

- `server/research_scripts/phase7/data_cache_new_period/decoded/YYYY/YYYY-MM-DD.csv.gz`
- manifest `phase7/data_cache_new_period/manifest.json`, sha256 atteso `605249c6…` (`phase7/dataset_version_registry_v2.json`)
- warmup del periodo di scoperta: `phase6/data_cache_holdout/decoded/` (2022-11-04 → 2023-02-03)

Sono gitignored. Il container cloud non ne ha una copia e non può raggiungere Dukascopy. Non serve scaricare nulla: la pipeline legge i file esistenti.

## Pipeline

| Passo | Modulo | Regola |
|---|---|---|
| Tick e controlli | `ticks.py` | conta crossed (ask<bid), prezzi ≤0, timestamp all'indietro, duplicati esatti, spread oltre soglia. Non scarta nulla |
| Barre M15 e H4 | `bars.py` | stessa regola di `phase7_1/build_h4_bars_p71.py` (OHLC BID, griglia UTC, tie sul timestamp alla riga successiva), più ask OHLC e spread |
| Allineamento | `bars.check_alignment` | ogni H4 deve coincidere con l'aggregazione delle sue M15; `compare_with_reference_h4` confronta con le H4 Phase 7.1 se presenti |
| Sessioni, DST, buchi | `sessions.py` | sessioni calcolate sull'ora locale di Tokyo, Londra e New York; ora di Roma; buchi classificati WEEKEND, DAILY_BREAK, OTHER; firma DST: l'ora più quieta deve spostarsi di 1 ora tra ora legale e solare USA |
| Impulso H4 | `events.detect_impulses` | corpo ≥ 1,5 × ATR della barra **precedente** e corpo/range ≥ 0,6 |
| Pullback H4 | `events.detect_pullbacks` | primo close entro 6 barre con ritracciamento ≥ 38,2% della gamba; un minimo sotto l'origine dell'impulso annulla. Evento noto alla chiusura della barra |
| Conferma M15 | `events.confirm_m15` | solo barre M15 che iniziano dopo la chiusura H4; conferma alla prima chiusura oltre gli estremi delle barre precedenti della finestra (≥2 barre, finestra 4 ore) |
| Ingresso e outcome | `events.simulate_outcome` | ingresso all'apertura M15 successiva (long su ask, short su bid), stop sotto/sopra gli estremi già stampati, +2R contro −1R, orizzonte 24 ore, stop prima del target nella stessa barra, censura al confine dello split |
| Confronto | `events.run_family` (CONTROL) | stessa regola M15 alle altre chiusure H4, senza contesto impulso/pullback |
| Statistiche | `stats.py` | Wilson, aspettativa netta e prima dello spread, costo dello spread in R, MFE/MAE, bootstrap a blocchi mensili, trimestri, direzione, sessione, salute dei detector con `phase7/engine/event_firing_rate_guard.py` |

## Come eseguirlo sul PC

Dalla cartella `server/research_scripts`, con `pip install -r ../requirements-dev.txt` (scipy, tzdata):

```bash
# 1. prova sui primi 10 giorni: niente statistiche, solo lettura, barre, allineamento
python -m behavior_lab_v1.run_experiment --split discovery --smoke-days 10
# 2. se tick_audit non è FAIL e alignment_mismatches è 0: periodo di scoperta completo
python -m behavior_lab_v1.run_experiment --split discovery
```

Output in `behavior_lab_v1/data/runs/<run_id>/` (gitignored): `summary.json` (hash del codice, della pre-registrazione e del manifest, controlli dati, funnel, statistiche) ed `events.csv`.

`--split internal_validation` scrive l'accesso nel ledger persistente `data/validation_access_log.json` (massimo 3 letture, policy Phase 7). `locked_validation` e `final_holdout` sono rifiutati. Uno stesso `hypothesis_id` non può girare con parametri diversi.

## Regole di evidenza

- Si itera solo su `discovery`. `internal_validation` si legge dopo aver deciso, senza cambiare parametri.
- Le finestre 2025-05 → 2026-09 sono già state attraversate dagli studi MT5 su BREAKOUT_ACC, ORDER_BLOCK e LIQ_SWEEP: per questa famiglia non sono un holdout indipendente (vedi `exposure_statement` nella pre-registrazione). L'indipendenza dovrà venire da dati successivi al 2026-09-17.
- Le soglie e il target non si scelgono guardando MFE o risultati di validazione: un cambio richiede un nuovo `hypothesis_id`.

## Test

`server/tests/test_behavior_lab_v1.py` (in CI), su campioni **sintetici**: niente in quei test descrive l'oro. Include la parità con il builder H4 Phase 7.1 eseguito sugli stessi tick, i test di causalità (barre future e barre M15 precedenti non cambiano l'evento) e una prova end-to-end del runner su file tick finti.
