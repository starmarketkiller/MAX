# Leakage Guard v1 (Phase 5.5 sec.8)

Implementazione: `server/research_scripts/phase5_5/leakage_guard.py`. Controlli statici (grep sul codice sorgente, con esclusione di commenti/docstring) + un controllo dinamico (confronto diretto fra soglie realmente usate e soglie ricalcolate solo-su-discovery). Eseguito qui in modalità **audit retroattivo** su Phase 5 già completata — non ancora integrato come gate bloccante dentro le pipeline stesse (lavoro di follow-up).

## Controlli implementati

1. `center=True` in qualunque `.rolling()`/`.expanding()` — nessuno trovato nel codice reale (i 3 hit iniziali erano falsi positivi su commenti che *spiegano* di non usarlo, corretti escludendo commenti/docstring dalla scansione).
2. `.shift(-N)` (lookup di dati futuri) — nessuno trovato.
3. Script di costruzione feature/eventi che referenziano file di outcome/edge (`build_market_state.py`/`build_events.py` che leggono `outcomes_v1`/`edge_results_v1`) — nessuno trovato.
4. Soglie/statistiche calcolate su `state[...]` senza uno slice esplicito di discovery — verifica euristica statica + **verifica dinamica reale**.

## Risultato: `LEAKAGE_GUARD_FAIL` — 1 problema confermato

**`BASELINE_TERCILES_FIT_ON_FULL_DATASET`** (in `server/research_scripts/phase5/edge_discovery.py`): le soglie di cella per il baseline matching (`vol_terc`, `trend_terc`) e per 3 delle 5 interazioni predefinite (`EFFICIENCY_TOP_TERCILE`, `VOL_BOTTOM_TERCILE`, `TREND_PERSISTENCE_MEDIAN`) sono state calcolate su `state["atr_percentile"].dropna()` — cioè sull'**intero dataset** (discovery + validation), non solo su discovery.

**Verificato dinamicamente** (non solo asserito): la soglia realmente usata (66.67° percentile ATR = 63.89) coincide esattamente con quella calcolabile sull'intero dataset, mentre la soglia calcolabile solo-su-discovery sarebbe stata 66.67 — uno scarto del 4.3%. Stesso ordine di grandezza per la soglia di efficienza direzionale (0.314 vs 0.324, ~3%). La mediana di persistenza di trend è risultata identica (1.0 in entrambi i casi).

**Materialità valutata**: piccola in ampiezza (discovery è già il 70% del campione, quindi la sua distribuzione è molto simile a quella dell'intero dataset) — non ci sono elementi per credere che questo abbia cambiato la classificazione di una qualunque delle 14 ipotesi di Phase 5 (in particolare RECLAIM, il cui test event-alone non dipende da queste soglie di interazione). **Non corretto in questa fase**: farlo richiederebbe ri-eseguire `edge_discovery.py`, quindi ri-validare SWEEP+RECLAIM — esplicitamente vietato dal perimetro di Phase 5.5. Segnalato come difetto reale da correggere nel prossimo ciclo di discovery/validation (calcolare `vol_terc`/`trend_terc`/soglie di interazione SOLO su `state.iloc[:SPLIT_IDX]`).

## Perché conta

Questo è esattamente il tipo di problema che la Phase 5.5 doveva rendere rilevabile automaticamente invece che scoprire per caso: una forma sottile di normalizzazione-sull'intero-dataset che non cambia il risultato headline ma indebolisce la separazione discovery/validation dichiarata come rigorosa. Il fatto che il guardrail l'abbia trovato guardando il proprio codice appena scritto (non un errore di terzi) è la dimostrazione più diretta possibile che il guardrail funziona.
