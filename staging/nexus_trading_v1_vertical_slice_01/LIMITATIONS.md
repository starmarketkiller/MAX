# LIMITATIONS — Vertical Slice 01 (H1_A)

## 0. La dichiarazione più importante di questo documento

Il run completo sull'intero dataset reused (4.808 bar H4, XAUUSD,
2019-02-03→2022-02-03) produce:

```
starting_equity = 10,000.00
final_equity    = 23,462.51   (+134.6%)
total_paper_attempts = 361
outcome_counts: {"TP_HIT": 150, "SL_HIT": 211}
```

**Questo numero NON è evidenza di un edge di trading.** È un
sottoprodotto di parametri congelati ma **non ciechi** (2R fisso,
N=20, buffer=avg_spread, stop ancorato all'estremo del sweep) testati
su **una singola finestra storica**, senza alcun test statistico
(nessun bootstrap, nessun confronto con un controllo negativo, nessun
intervallo di confidenza), e — punto più importante — **il codice è
stato scritto, debuggato e iterato guardando ripetutamente l'output su
questo stesso dataset**. Non è un test fuori-campione, non è stato
mai valutato alla cieca, e il 58.4% win-rate implicito (150/361 TP)
non è stato confrontato con nessuna baseline casuale o nessun'altra
strategia. Qualunque lettura di questo numero come "la strategia
funziona" sarebbe un errore metodologico, non una conclusione di
questa missione.

Lo scopo dichiarato di questa slice (vedi mandato originale, sezione
Vertical Slice 01) è dimostrare che l'intera catena
osserva→riconosce→decide→simula→gestisce→registra→spiega funziona
end-to-end in modo **causale, deterministico e verificabile** — non
produrre o validare un'ipotesi di trading. Questo documento esiste
per impedire che il numero sopra venga mai riportato senza questa
cornice.

## 1. Limiti dei dati

- **BID-only**: nessuna serie ASK separata nel dataset reused —
  nessuna sintesi MID tentata, lo spread/costo è modellato tramite
  `avg_spread` (reale, per-bar) più uno slippage fisso dichiarato
  (`SLIPPAGE_PRICE_UNITS=0.05`), non un vero book bid/ask.
- **Una sola finestra storica**: 2019-02-03→2022-02-03 (~3 anni). Nessun
  test su altri regimi di mercato (es. 2008, 2020 covid-crash, 2022-2024
  rialzo dei tassi) — questa slice non fa alcuna affermazione sulla
  generalizzazione ad altri periodi.
- **Nessun accesso all'holdout sigillato**: FINAL_HOLDOUT
  (2026-02-04→2026-09-16) non è mai stato letto da questa slice — per
  costruzione, non solo per policy (vedi `DATA_PROVENANCE.md`,
  `BarStore` non espone nemmeno la possibilità di caricarlo).

## 2. Limiti del Decision Engine

- **PREEXISTING_LEVEL**, **soglia sweep** (zero buffer) e
  **R-multiple fisso (2R)** sono tutti DESIGN_ASSUMPTION_V1 — scelte
  dichiarate per permettere l'esecuzione end-to-end, **non** derivate
  da un'analisi quantitativa delle fonti Telegram (che non forniscono
  mai questi numeri, confermato ripetutamente nelle missioni 02-04).
- **Nessun filtro HTF, nessun filtro di sessione** — ogni bar H4
  valido nel periodo è valutato 24/7, anche se le fonti Telegram
  osservate menzionano spesso contesto multi-timeframe e finestre
  orarie specifiche (vedi `nexus_telegram_trading_intelligence_02`).
- **RECLAIM valutato solo sullo stesso bar** del sweep — non cattura
  pattern "sweep su un bar, reclaim/struttura sui bar successivi",
  esplicitamente visti nelle immagini ispezionate nella missione 03.
- **Nessuna ricostruzione del "Draw On Liquidity"** — il target fisso
  2R non rappresenta il concetto di target dinamico osservato nei
  canali; dichiarato esplicitamente nel contratto (§8), ripetuto qui.

## 3. Limiti del Paper Engine

- **`STOP_FIRST` come policy intrabar** quando sia SL che TP cadono
  nello stesso bar H4 — assunzione conservativa dichiarata, non
  verificabile con dati OHLC (servirebbe il tick stream reale per
  sapere l'ordine esatto).
- **Nessun modello di margine/leva/dimensione di contratto reale** —
  volume calcolato come `risk_amount / risk_distance` con 1 unità = 1
  oncia, una semplificazione dichiarata.
- **Nessuna gestione dinamica della posizione** (trailing stop,
  break-even, chiusura parziale) — uscita binaria SL/TP fissata al
  fill.

## 4. Limiti della Cockpit Demo

- Finestra fissa di 260 bar (i primi del dataset, non selezionati per
  risultato favorevole) — non l'intero dataset, per restare leggera e
  veloce nel browser.
- La vista "D1" è **puramente un'aggregazione di visualizzazione**
  (raggruppamento OHLC per data UTC) — non esiste alcuna logica
  decisionale D1 in questa slice; livelli, sweep e marker di decisione
  sono mostrati solo nella vista H4 nativa, per evitare di far
  intendere una capacità multi-timeframe che non esiste.
- Nessun controllo visivo automatizzato tramite browser reale è stato
  incluso nella suite pytest (vedi `TEST_RESULTS.md` §1,
  classificazione VISUAL non eseguita come test pytest) — la demo è
  stata verificata manualmente con un driver CDP headless separato
  durante lo sviluppo, non come parte della suite di regressione.

## 5. Limiti di processo

- **Nessuna revisione indipendente** (Codex o altro reviewer) di
  questo codice prima di questo documento — il mandato originale non
  la richiedeva esplicitamente per questa slice, ma è un limite reale
  da dichiarare.
- **Nessuna modifica al codice MQL5/EA canonico** — questa slice è
  interamente isolata in `staging/nexus_trading_v1_vertical_slice_01/`,
  non tocca `MQL5/` né richiede l'esecuzione di MetaTrader/MetaEditor.
