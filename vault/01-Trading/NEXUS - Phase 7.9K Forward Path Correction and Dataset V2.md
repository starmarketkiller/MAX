# NEXUS - Phase 7.9K — Forward Path Correction e Dataset V2

**Baseline:** `38ee2c4` (Phase 7.9J). Phase 7.9H (V1) e tutti i raw data **preservati e invariati** (verificato via git diff su phase7_9h/7.9i/7.9j). Nessuna optimization, nessuna modifica all'EA, nessuna promozione live.

**Obiettivo**: risolvere il difetto di indicizzazione forward confermato in Phase 7.9J (offset di +1 barra) e misurarne l'impatto, con una nuova versione del dataset derivato (V2).

---

## 0. Correzione post-commit (revisione di `f70500a`)

Dopo il commit iniziale di questa fase, due discrepanze sono state segnalate e verificate direttamente sull'artifact:

**(a) Accounting errato dei 5 eventi "riclassificati".** Verificato che dei 5 eventi con `reclassified=true`, solo **4 sono veri cambi di ESITO** (continuation↔failure, fra eventi in cui **entrambe** le versioni V1/V2 producono una classificazione determinata: 1 CONTINUATION→FAILURE, 3 FAILURE→CONTINUATION) — il quinto è un **cambio di STATO DI COPERTURA** (UNKNOWN→UNKNOWN_CENSORED), concettualmente diverso e non sommabile ai primi quattro. **Corretto**: `build_path_anatomy_v2.py` ora riporta `n_outcome_flips_continuation_vs_failure` (4, su un denominatore esplicito `n_outcome_flips_denominator`=46 eventi comparabili) e `n_coverage_status_changes` (1) come campi **separati**, non più un unico contatore "reclassified"=5.

**(b) Affermazione errata sulla classificazione V1 del censurato.** Il testo originale di questa fase affermava che "la versione precedente lo classificava silenziosamente [come failure]". **Verificato falso**: nell'artifact di confronto, `v1_classification` per l'evento 2026.06.09 era già `UNKNOWN` (non `FAILURE`) — `v1_fwd_return_60d1` era già `None`. Il difetto reale di V1 su questo evento non era una classificazione sbagliata (la classificazione finale a 60 barre era già corretta), ma l'**assenza di un campo di stato esplicito**: MFE/MAE/bars_to_mfe/bars_to_mae venivano comunque calcolati silenziosamente su una finestra incompleta (51 barre), senza dichiararlo. V2 rende questo esplicito con `status: CENSORED_INSUFFICIENT_BARS` e `coverage_bars: 51`. Il vault report e tutti gli artifact che ripetevano l'affermazione errata sono stati corretti.

**(c) Linguaggio sulla non-casualità.** La Decision Card affermava implicitamente che la persistenza del pattern direzionale dopo la correzione fosse una conferma. **Riformulato esplicitamente**: la persistenza del pattern su una correzione metodologica degli *stessi dati* (non un nuovo campione indipendente) dimostra solo che il pattern non era un artefatto puro dell'offset — **non dimostra non-casualità né un edge incrementale rispetto a un benchmark**, entrambi ancora da verificare. Rimossa ogni formulazione "replica indipendente" o equivalente.

**Artifact corretti**: `build_path_anatomy_v2.py` (aggiunta separazione outcome_flip/coverage_status_change + nota precisa sul difetto precedente), `build_decision_card_v2.py` (linguaggio e conteggi), `verify_phase_7_9k.py` (4 nuovi controlli indipendenti), `test_phase_7_9k.py` (5 nuovi test dedicati). Dataset V2, raw, identità e le altre misure numeriche **invariate** — nessun errore distinto trovato altrove.

---

## 1. Contratto temporale

Definiti esplicitamente: timestamp segnale (reale, dal trace live, per tutti i 67 live-observed) vs fill (reale, verificato, solo per i 47 OPENED — identico al timestamp del segnale per costruzione: la strategia invia l'ordine immediatamente); convenzione barre D1 (timestampate all'apertura, feed reale del broker, nessuna barra sintetica per i weekend); **barra parziale d'ingresso** (esclusa sempre — il suo High/Low può contenere prezzo antecedente al fill, non isolabile senza dati intraday verificati per l'intero 2019-2026, che non esistono); **bar 1 = prima barra D1 completa** con apertura ≥ reference_time (mai un estremo precedente al fill, per costruzione); **N barre di mercato ≠ N giorni di calendario** (la sequenza salta nativamente i weekend).

**Copertura dichiarata**: tutti i 47 fill sono intraday (nessuno a mezzanotte esatta) — la misura comincia sempre dal giorno di calendario successivo al fill, mai dal giorno stesso. La porzione del giorno d'ingresso dopo il fill **non è misurata** (limite dichiarato, non colmato — nessuna serie M15 verificata copre l'intero periodo). **1 evento** (2026.06.09, l'ultimo della serie) risulta censurato all'orizzonte di 60 barre (solo 51 disponibili).

## 2. Dataset V2

`breakout_acc_intended_d1_v2_dataset.json` (nuova directory `phase7_9k/`). **Identità preservata**: `dataset_name = "BREAKOUT_ACC_INTENDED_D1_V1"` invariato — cambia solo `dataset_schema_version` (V1→V2). **event_id conservati** identici a V1 (verificato: stesso insieme di 75 id). **Funnel e collegamenti ai fill invariati** (`funnel_terminal_stage`, `entry_fill_price/time`, `realized_pnl` — copiati identici, nessun nuovo difetto trovato lì). Il vecchio `post_entry_path_anatomy` è conservato come `..._V1_SUPERSEDED` per confronto diretto.

## 3. Due misurazioni separate

- **Misurazione A (post-segnale)**: tutti i 75 eventi. Per i 67 live-observed, **timestamp REALE del segnale** (dal trace live — non più un placeholder sintetico come nelle fasi precedenti). Per gli 8 B-only, timestamp **sintetico**, esplicitamente etichettato `SYNTHETIC_NOT_OBSERVED_NOON_PLACEHOLDER` — mai confuso con un tempo osservato. Prezzo = c1 (chiusura pre-segnale, causalmente pulita), uniforme per tutti i 75, **mai il fill**.
- **Misurazione B (post-fill)**: solo i 47 OPENED, fill reale verificato. Tenuta **separata** — mai fusa con A.

Per i 47 OPENED, A e B usano lo stesso timestamp (verificato: segnale=fill) ma prezzi diversi (c1 vs fill reale) — la differenza (movimento intraday fra l'apertura del giorno e il momento della decisione) è ora esplicitamente visibile e non più confusa con slippage.

## 4. Risultati ricalcolati — confronto prima/dopo

**Non neutrale**, come atteso:

| Metrica | V1 (bug) | V2 (corretto) |
|---|---|---|
| BUY continuation (60gg) | 24/36 (66.7%) | 25/36 (69.4%) |
| SELL continuation (60gg) | 1/11 (9.1%) | 2/10 (20.0%, 1 censurato escluso) |
| Veri cambi di esito (continuation↔failure) | — | **4/46 (8.7%)**, denominatore = eventi comparabili |
| Cambi di stato di copertura (UNKNOWN→UNKNOWN_CENSORED) | — | **1** (separato, non un cambio di esito) |
| Eventi censurati a 60gg | 0 (mai segnalato) | **1** |
| BROKER_REJECT fwd60 mediano (controfattuale) | -10.65 | **+12.77** (cambio di segno) |
| BLOCKED fwd60 mediano (controfattuale) | 90.28 | 97.18 (invariato qualitativamente) |

**Il pattern direzionale (BUY≫SELL) resta presente** dopo la correzione — evidenza che non era un artefatto puro dell'offset, **non una replica indipendente** (è una correzione sugli stessi dati, non un nuovo campione). Ma **l'ampiezza si è attenuata per SELL** (raddoppiata dal 9.1% al 20.0%), e la scoperta che l'8.7% delle classificazioni comparabili cambia esito con un fix minore (più separatamente 1 cambio di stato di copertura), più il cambio di segno nel gate diagnostic controfattuale, sono **segnali di fragilità metodologica** che non c'erano stati dichiarati prima con questa precisione. Questa persistenza **non dimostra da sola non-casualità né un edge incrementale** rispetto a un benchmark — entrambi restano da verificare.

## 5. Conclusioni corrette

**EMA100**: precisato che **72/75 eventi sono valutabili** (0 eccezioni, tutti allineati); i **3 non valutabili** (warmup storico insufficiente a inizio 2019) sono **tutti fra gli 8 B-only** — mai contati come allineati o non allineati (UNKNOWN esplicito).

**Allineamento costante ≠ prova di dipendenza**: riformulato esplicitamente — un allineamento del 100% senza eccezioni significa che l'**effetto non è identificabile** in questo campione (nessun gruppo di controllo non-allineato), non che il risultato *dipenda* dall'allineamento. Questo era un errore di interpretazione implicito nelle fasi precedenti, ora corretto.

**Verdetto rivalutato, non ereditato**: il pattern descrittivo (asimmetria BUY/SELL) **resta presente** dopo la correzione (evidenza contro un artefatto puro, non una prova di non-casualità), ma la fragilità aggiuntiva scoperta (8.7% di veri cambi di esito, sign-flip nel gate diagnostic) impedisce di alzare la decisione a `MECHANISM_SUPPORTED`. Nessun elemento emerge per abbassarla a `MECHANISM_NOT_SUPPORTED` o `INSUFFICIENT_EVIDENCE` (il pattern direzionale principale è rimasto nella stessa direzione). **Decisione: `MECHANISM_PARTIALLY_SUPPORTED`** (stessa di Phase 7.9J, ma ri-derivata esplicitamente da zero, non mantenuta per inerzia). Non-casualità ed edge incrementale restano entrambi da verificare.

## 6. Verifiche indipendenti — serie calcolabili a mano

7 test con valori attesi **calcolati manualmente prima di eseguire il codice** (non generati dalla stessa funzione verificata): fill intraday (verifica diretta che l'estremo artificiosamente enorme della barra d'ingresso, H=200, non compaia mai in MFE, che sarebbe 99 invece di 19 corretto); fill esattamente all'apertura D1 (quella barra stessa diventa "bar 1"); weekend/barre mancanti (barra 5 = 3 giorni di calendario dopo la barra 4, nessuna barra sintetica); orizzonte con barre future insufficienti (censura esplicita, mai `FAILURE`); direzione SELL (logica speculare verificata); nessuna barra disponibile (status esplicito). Tutti PASS.

## Report delle limitazioni residue

1. **Porzione infragiornaliera del fill non misurata** — nessun dato intraday verificato per l'intero 2019-2026 (limite dichiarato, non colmato).
2. **1 evento censurato** all'orizzonte di 60 barre (2026.06.09) — escluso dai denominatori, non forzato a FAILURE.
3. **Fragilità metodologica dimostrata**: 8.7% di veri cambi di esito (4/46 eventi comparabili) da un fix minore — qualunque futura analisi a singolo-orizzonte va letta con questa cautela esplicita.
4. **Confondimento trend/direzione invariato** (0/72 non allineati) — la domanda "l'edge dipende dal trend?" resta non testabile con questo dataset.
5. **Un solo regime di mercato** (bull GOLD) — invariato da tutte le fasi precedenti.
6. **Le cautele statistiche di Phase 7.9J sul Natural Horizon** (finestre sovrapposte, dipendenza entro-evento) **restano identiche** — la correzione dell'offset non le risolve.

## Deliverables

`breakout_acc_temporal_contract_v1.json`, `breakout_acc_intended_d1_v2_dataset.json`, `breakout_acc_path_anatomy_v2.json` (+ confronto prima/dopo), `breakout_acc_natural_horizon_v2.json`, `breakout_acc_edge_decomposition_v2.json`, `breakout_acc_gate_diagnostic_v2.json`, `breakout_acc_sensitivity_v2.json`, `breakout_acc_failure_map_v2.json`, `breakout_acc_decision_card_v2.json`, libreria condivisa `nxs_forward_path_v2.py`, 9 builder, verificatore indipendente, 36 test di consistenza (36/36 PASS, incl. 7 serie calcolabili a mano), questo vault report.

## Vincoli preservati

Phase 7.9H, 7.9I, 7.9J e tutti i raw data invariati (verificato via git diff). Nessun file MQL5/Python modificato. Nessuna optimization. Nessuna delle altre 10 strategie DEFECT_CONFIRMED toccata. `VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti.

## Regressione

- **Suite propria 7.9K (pytest, dopo la revisione post-commit)**: 39/39 PASS (36 originali + 3 nuovi dedicati a outcome_flip/coverage_status_change)
- **Suite pytest Phase 7 totale**: **383/383 PASS, 0 fallimenti**
- **4 suite standalone pre-esistenti**, fallimenti noti invariati: `phase7_8e` 68/72, `phase7_8h` 18/21, `phase7_8i` 22/23, `phase7_9b` 31/33.
- Verificato via git diff: 0 modifiche a `phase7_9h/`, `phase7_9i/`, `phase7_9j/`.

I 2 artifact `phase7_9c/breakout_acc_*_event_stream_v1.json` (effetto collaterale noto, hash canonico invariato) ripristinati con `git checkout --` prima del commit.

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.9K: COMPLETATA ✓
FORWARD PATH CORRECTION: offset di +1 barra confermato in 7.9J,
        corretto (bar 1 = prima barra D1 completa, mai un estremo
        precedente al fill). Impatto: 4/46 veri cambi di esito (8.7%,
        separati da 1 cambio di stato di copertura), BROKER_REJECT
        cambia segno - NON neutrale (revisione post-commit inclusa)
DATASET V2: BREAKOUT_ACC_INTENDED_D1_V1 (identita' invariata, schema
        V2, event_id conservati, funnel/fill invariati) - misurazione
        A (post-segnale, timestamp reale) e B (post-fill) separate
EMA100: 72/75 valutabili (100% allineati), 3 non valutabili (B-only) -
        allineamento costante = effetto NON identificabile, non prova
DECISIONE: MECHANISM_PARTIALLY_SUPPORTED (RIVALUTATA da zero, pattern
        direzionale sopravvive in direzione ma fragilita' metodologica
        dimostrata impedisce di alzarla)
PROSSIMO: nessuna nuova ipotesi proposta in questa fase - resta
          TREND_ALIGNMENT_CONDITIONAL_EDGE (7.9I/7.9J), non testabile
          con questo dataset
```
