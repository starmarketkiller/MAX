# Missing Data Policy v1 (Phase 5.5 sec.10)

Regole esplicite, vincolanti per ogni dataset di ricerca futuro. **Vietato**: forward-fill indiscriminato, zero-fill silenzioso, drop di righe senza reporting.

## Regole per tipo di gap

| Tipo di gap | Politica | Motivazione |
|---|---|---|
| **Barre mancanti** (buco nella serie OHLC) | Riportare come `bar_gap` esplicito con timestamp; NON interpolare il prezzo; se un evento/feature attraversa il buco, marcarlo `data_gap_suspect=true` (stesso principio già usato in Phase 4, failure pattern `DATA_COVERAGE_GAP`) | Un prezzo interpolato è inventato, non osservato — inquinerebbe qualunque outcome R/ATR |
| **Tick mancanti** | Già coperto dall'integrity audit Dukascopy (Phase 4): ore vuote legittime (weekend/festivi) vs ore vuote sospette sono distinte esplicitamente, mai confuse | Un'ora vuota per festività è normale; un'ora vuota su un giorno feriale va segnalata |
| **Dati cross-market non disponibili** (DXY, yields, ecc.) | Il record di stato NON include il campo finché la fonte non è integrata (nessun placeholder 0/NaN silenzioso mescolato a dati reali) — vedi Cross-Market Data Interface (sec.13): il campo `availability` dichiara esplicitamente "NOT_YET_INTEGRATED" | Un campo NaN indistinguibile da un NaN di warmup nasconderebbe la vera ragione dell'assenza |
| **NaN iniziali da lookback** (warmup) | Riportati esplicitamente per colonna (vedi tabella sotto), MAI droppati dal dataset (le righe restano, solo quella colonna è NaN) | Droppare le righe sposterebbe l'indice temporale e romperebbe il join con eventi/altre feature che non hanno bisogno di quella finestra |
| **Festività di mercato** | Nessuna barra viene generata per ore/giorni di chiusura reale (Dukascopy non produce tick in quelle ore) — non è "missing", è correttamente assente. Distinto esplicitamente dalle ore vuote sospette nell'integrity audit di Phase 4 | Confondere "mercato chiuso" con "dato mancante" è il tipo di errore già catalogato (Phase 4 audit iniziale, poi corretto) |
| **Sessioni parziali** | Se una barra H4 contiene meno tick del previsto per via di una sessione parziale (es. giorno di chiusura anticipata), il campo `n_ticks` di `xauusd_h4_bars.csv` lo rende visibile per barra — nessuna barra viene scartata, ma un consumatore può filtrare su `n_ticks` basso se rilevante | Trasparenza senza perdita di dati |
| **Source gaps** (l'intera fonte dati non copre un periodo) | Dichiarato nel `dataset_id`/versioning (sec.14) come limite noto della finestra, non riempito con un'altra fonte senza dichiararlo esplicitamente (vedi Failure Memory, `ENVIRONMENT_TICK_DATA_BOUNDARY`) | Mescolare fonti diverse senza dichiararlo introduce il rischio già catalogato di feed-mismatch |

## Missingness reale — market_state_dataset_v1 (Phase 5)

Calcolato direttamente dal dataset (4809 barre H4, 2019-02-03→2022-02-03):

- **Tutte le colonne con NaN sono confinate ai primi 75 bar (2019-02-03 → 2019-02-19), il periodo di warmup delle finestre più lunghe (percentile ATR a 252 barre).** Nessun gap a metà serie.
- Colonna con più NaN: `atr_percentile` (75 righe, 1.56% del dataset).
- Colonna con meno NaN: `return_direction` (1 riga, 0.02% — la primissima barra, nessun ritorno calcolabile).
- Nessuna riga è stata droppata dal dataset per via di questi NaN — tutte le 4809 righe sono presenti, la mancanza è esplicita colonna-per-colonna.

**Policy applicata**: warmup NaN lasciato esplicito (non forward-filled, non zero-filled) — coerente con la policy sopra. Qualunque detector/test che usi una colonna con NaN nella finestra di warmup salta naturalmente quelle righe (già il comportamento di `build_events.py`, che controlla `np.isnan(atr[i])` prima di procedere).

## Requisito di reporting per ogni dataset futuro

Ogni dataset deve riportare, come parte del proprio `dataset_id` (sec.14): missingness rate per colonna, periodi affetti (date), e la policy scelta — esattamente nel formato di questo documento, non come nota sparsa nel codice.
