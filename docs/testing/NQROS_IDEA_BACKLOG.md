# NQROS v3.1 — Backlog idee

Idee emerse durante i cicli di ricerca ma non ancora testate (mancava
tempo, dati, o serviva prima chiudere il ciclo in corso). Ogni voce indica
da quale strategia/fase è emersa. Da riprendere quando si sceglie la
prossima strategia da approfondire o quando si torna su una già chiusa.

## Aperte

- **Riscrivere `sig_silver_bullet` con la vera state machine MQL5**
  (urgente, da verifica fedeltà 04/08) — sweep confermato in killzone →
  candela di displacement con BOS → formazione FVG → ritorno nel FVG →
  SOLO ALLORA segnale. Il proxy attuale spara al solo sweep, saltando 3
  stadi di conferma interi. Tutto il deep-dive SILVER_BULLET fatto finora
  va rifatto da capo su questa base.

- **Riscrivere il retest di `sig_amd_cont` (low, non close) e implementare
  la vera formula SL/TP** (da verifica fedeltà 04/08) — MQL5 usa
  `l1 <= asianHigh+atr*0.6` per il retest (non la close) e
  `SL=min(asianHigh-0.3×ATR, mid)` / `TP=entry+2.4×R` (non un multiplo ATR
  libero). La Fase 6 di AMD_CONT (SL2.5/TP4.0) va rifatta su una versione
  che implementi questa formula, non sul generico ATR-multiple.

- **Verificare fedeltà motore-vs-MQL5 per OGNI prossima strategia SUBITO
  dopo la Fase 1** (lezione #11, non aspettare fino a dopo un deep-dive
  completo come successo per AMD_CONT/SILVER_BULLET) — se il proxy manca
  un meccanismo intero (come successo con SILVER_BULLET), le fasi 2-8 fatte
  prima di scoprirlo sono lavoro sprecato.

- **Verificare se altre strategie hanno una formula SL/TP propria in MQL5
  non coperta da `STRATEGY_TARGETS_ALWAYS`/`STRATEGY_TARGETS_OPTIN`**
  (lezione #12) — prima di fidarsi di qualunque risultato Fase 6 su quelle
  strategie (rischio di ottimizzare un parametro che nell'EA reale non
  esiste, come successo con AMD_CONT).

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

- **SILVER_BULLET, isolamento killzone London (10-11 GMT)** (da
  SILVER_BULLET, Fase 4) — PF 6.42 out-of-sample ma su soli 9 trade,
  scartato per campione troppo piccolo. Riverificare quando c'è più
  storico H4 (stesso limite Yahoo di AMD_CONT).

- **SILVER_BULLET, pass condizionato di Fase 4** (da SILVER_BULLET) — sia
  con che senza `htf_filter` il PF esplode nella seconda metà dello
  storico H4 disponibile: sospetto forte cambio di regime di mercato
  nell'oro in quel periodo, non (solo) un effetto del filtro. Da
  ricontrollare con più storico per capire se è un effetto di periodo che
  sparisce o una caratteristica reale del setup.
