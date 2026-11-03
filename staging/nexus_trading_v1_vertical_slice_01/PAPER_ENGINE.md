# PAPER_ENGINE — Vertical Slice 01 (H1_A)

`paper_engine/simulator.py::PaperEngine`. Esecuzione **PAPER-ONLY**,
deterministica, su una lista di bar già caricata in memoria — nessun
feed live, nessun broker, nessuna chiamata di rete. Verificato da un
test statico sul testo sorgente
(`tests/test_h1a_vertical_slice.py::TestBrokerSeparation::test_simulator_source_has_no_network_or_mt5_import`),
che cerca token proibiti (`socket`, `requests`, `MetaTrader5`,
`OrderSend`, `urllib`, `http.client`) nel file stesso.

## 1. Cosa riusa (non reinventato)

Da `server/research_execution_model_v1.py` (import diretto):

- `rem.fill_price(...)` con policy `NEXT_OPEN_V1` — prezzo di
  riempimento = apertura del bar **successivo** al bar di segnale,
  mai il close del bar di segnale stesso (vedi `STRATEGY_CONTRACT_H1_A.md` §8).
- `rem.resolve_bar_exit(...)` con policy `INTRABAR_POLICY = "STOP_FIRST"`
  — quando sia SL che TP cadono nel range high/low dello stesso bar,
  si assume che lo stop venga toccato per primo. **DESIGN_ASSUMPTION_V1**:
  scelta conservativa dichiarata, non derivata da dati tick reali (il
  dataset reused è OHLC H4, non tick-level — non è possibile sapere
  l'ordine reale intrabar da questi dati).
- `rem.SyntheticBar` — wrapper OHLC comune, stesso tipo usato altrove
  nel codebase per questo genere di risoluzione.

## 2. Un solo tentativo alla volta (vincolo esplicito del mandato)

`PaperEngine._open_attempt` è un singolo slot, non una lista.
`open_from_candidate()` solleva `RuntimeError` se chiamato mentre uno
slot è già occupato — ma questo non dovrebbe mai accadere nel
percorso normale, perché `decision_engine/engine.py` ha già vetato
("WAIT"/`DUPLICATE_SUPPRESSED_OPEN_ATTEMPT_EXISTS`) qualunque nuovo
candidato mentre un tentativo è aperto, **prima** che arrivi al
Paper Engine. Il `RuntimeError` è quindi un controllo difensivo di
secondo livello, non il meccanismo primario di deduplicazione —
testato esplicitamente in
`TestMandatoryStopAndCosts::test_no_grid_pyramid_recovery_martingale_single_attempt_enforced`.
Nessun grid, nessun pyramiding, nessun recovery, nessun martingale —
per costruzione, non per convenzione.

## 3. Calcolo di stop, target, volume

```
stop_LONG  = candidate.sweep_extreme - signal_bar.avg_spread
stop_SHORT = candidate.sweep_extreme + signal_bar.avg_spread
risk_distance = abs(fill_price - stop)
target_LONG   = fill_price + 2 * risk_distance
target_SHORT  = fill_price - 2 * risk_distance
risk_amount   = equity_corrente * risk_pct   # default 1%
volume        = risk_amount / risk_distance
```

Lo stop è ancorato all'estremo del sweep già calcolato dal detector
(`candidate_detail.sweep_extreme`), **non ricalcolato** qui — unica
fonte di verità per quel numero. Il volume assume **1 unità = 1
oncia**, nessun modello di margine o dimensione di contratto reale —
DESIGN_ASSUMPTION_V1 dichiarata, non una specifica broker.

## 4. Costi espliciti, mai impliciti

- `SLIPPAGE_PRICE_UNITS = 0.05` applicato sia all'entrata che
  all'uscita (contro il trader: peggiora sempre il prezzo ottenuto).
- `spread_price_units_at_signal_bar` registrato nel `cost_breakdown`
  per trasparenza, anche se già consumato nel calcolo dello stop.
- Nessun costo "a sorpresa": ogni test in
  `TestMandatoryStopAndCosts::test_slippage_and_spread_are_explicit_and_applied`
  verifica che questi campi siano popolati e non-zero quando
  applicabili.

## 5. `FILL_UNCERTAIN` — mai un prezzo inventato

Due condizioni distinte, entrambe registrate come tentativo chiuso
con `outcome="FILL_UNCERTAIN"` **invece di** essere silenziosamente
scartate:

- `fill_uncertain_reason = "NO_NEXT_BAR_AVAILABLE_FOR_FILL"` — il bar
  di segnale è l'ultimo del dataset, non esiste un bar successivo su
  cui riempire.
- `fill_uncertain_reason = "NON_POSITIVE_RISK_DISTANCE"` — stop e
  prezzo di riempimento coincidono o sono invertiti (può succedere
  con spread/slippage estremi vicino al livello) — mai un `volume`
  o un `risk_distance` negativo/zero propagato a valle.

Testato in `TestMissingData::test_no_next_bar_registers_fill_uncertain_not_invented_fill`.

## 6. Chiusura a fine dataset

`close_still_open_at_dataset_end()` chiude qualunque tentativo ancora
aperto all'ultimo bar disponibile, con `outcome="DATASET_ENDED_STILL_OPEN"`
e `exit_price = last_bar.close` — mai un tentativo "dimenticato" fuori
dal journal. Chiamato esplicitamente da `scripts/run_full_replay.py`
dopo il ciclo principale.

## 7. Cosa questo motore NON fa (dichiarato)

- Nessuna gestione dinamica dello stop (trailing, break-even) — uscita
  binaria SL/TP fissata al momento del fill.
- Nessun position sizing oltre al rischio percentuale fisso per
  tentativo.
- Nessun conto di margine, leva o requisito di capitale minimo.
- Nessun invio reale — per costruzione (vedi §0 sopra).
