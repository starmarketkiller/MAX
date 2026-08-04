# NQROS v3.1 — Backlog idee

Idee emerse durante i cicli di ricerca ma non ancora testate (mancava
tempo, dati, o serviva prima chiudere il ciclo in corso). Ogni voce indica
da quale strategia/fase è emersa. Da riprendere quando si sceglie la
prossima strategia da approfondire o quando si torna su una già chiusa.

## Aperte

- **Fedeltà motore Python vs MQL5 reale** (da AMD_CONT, Fase 9) — confronto
  riga-per-riga tra `_session_amd_series`/`sig_amd_cont` (Python) e
  `NXS_AMDModel.mqh` (MQL5 reale). Blocca la promozione di AMD_CONT a
  "mantieni". Probabilmente utile anche per le altre strategie a sessione
  (SILVER_BULLET, JUDAS_SWING, ecc.) che condividono la stessa
  infrastruttura `_session_amd_series`.

- **Storico H4/H1 più lungo per la validazione** (da AMD_CONT, Fase 9) —
  Yahoo limita H4/H1 a ~2 anni. Serve un export MT5 (quando l'utente è al
  PC) per un test 10 anni vero, o accettare il limite attuale e trattare
  ogni verdetto come provvisorio.

- **Fase 7 (pyramiding/grid/recovery) — capacità di motore mancante**
  (da AMD_CONT) — il motore Python è a posizione singola. Se si decide che
  vale la pena, va costruita: supporto multi-posizione concorrente per
  simbolo/strategia, non un test rapido.

- **Segmentazione per sessione su altre strategie a sessione** (da
  AMD_CONT, Fase 8-9) — SILVER_BULLET, JUDAS_SWING, LDN_REVERSAL,
  NY_REVERSAL, AMD_REVERSAL, PO3 condividono lo stesso gate a sessione:
  vale la pena ripetere lo stesso check economico (segmentare i trade per
  sessione, vedere se una tira giù la media) prima di approfondirle una
  alla volta.

- **M30 per AMD_CONT resta un "forse"** (da AMD_CONT, Fase 9) — PF 1.71 su
  14 trade, sotto la soglia di affidabilità e non validabile OOS col
  campione attuale. Da riverificare se/quando arriva più storico intraday.

- **Walk-forward multi-finestra** (da AMD_CONT, Fase 4/9) — oggi un solo
  split 60/40 in-sample/out-of-sample. Con più storico si potrebbe fare un
  vero walk-forward a più finestre, molto più convincente di un singolo
  taglio temporale.

## Chiuse / rispose da un test già fatto

- ~~AMD_CONT "nessun TF pulito, da escludere"~~ — smentito dalla Fase 1
  multi-timeframe (04/08): H4 funziona bene, il gate a sessione non
  richiede granularità intrabar fine.
