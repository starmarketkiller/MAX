---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, setup, buy-sell, framework, metodologia]
created: 2026-07-15
updated: 2026-07-15
---

# Framework: setup Buy e Sell indipendenti per ogni strategia

Richiesta esplicita dell'utente (15/07), a correzione di un mio errore
precedente (vedi [[NEXUS EA - Principi]] #9): **non si taglia una direzione
per "risolvere" una strategia**. Ogni strategia del portafoglio deve restare
tradabile sia in buy che in sell, ma trigger d'ingresso, timeframe ed
eventualmente combinazione di parametri vanno **costruiti e validati
indipendentemente per ciascuna direzione**. Una strategia con ~37 nomi
genera quindi fino a ~2 setup ciascuna (buy + sell) da trattare come unità
separate di lavoro — non tutte avranno bisogno di logiche realmente diverse
(alcune saranno legittimamente simmetriche), ma vanno **verificate** una per
una, non assunte simmetriche.

## Schema di una scheda "Setup"
Ogni setup (es. `MALAYSIAN_SNR — BUY`) va documentato con:
- **Trigger d'ingresso**: condizione meccanica precisa, in termini di prezzo/
  candele/struttura — non solo "il contrario del sell".
- **Timeframe**: quello di analisi/bias (HTF) e quello di refine/entry (LTF),
  possono differire da BUY a SELL della stessa strategia.
- **Conferme/filtri richiesti**: es. fresh/unfresh, numero di tocchi,
  sessione, trend HTF.
- **SL/TP**: origine del livello (struttura vs ATR) e rapporto.
- **Fonte**: da quale documento/backtest/osservazione deriva questa regola.
- **Stato di validazione**: ipotesi da fonte esterna / testata sul sito /
  testata su MT5 / confermata su dati reali multi-anno.

## Esempio completo: MALAYSIAN_SNR (BUY e SELL da [[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]])

Questo è il primo setup ricostruito interamente da fonte esterna, come
dimostrazione del metodo. La strategia attuale in `NXS_StrategyProfiles.mqh`
implementa solo una frazione di questa logica (vedi [[Malaysian Snr]]) — è
il candidato più maturo per un refactor guidato dalla fonte, perché il nome
stesso della strategia deriva da questo libro.

### MALAYSIAN_SNR — SETUP BUY (supporto)
1. **Bias HTF**: Weekly/Daily in storyline rialzista (prezzo che si muove da
   supporto a resistenza sulla HTF). Se Weekly rialzista ma Daily
   ribassista, **aspettare** che la storyline Daily ribassista si esaurisca
   prima di cercare entrate long (regola gerarchica delle HTF).
2. **Livello**: un supporto SNR **fresh** (identificato per close-to-open,
   non high/low) sulla HTF di riferimento, oppure un supporto flippato
   (RBS — Resistance Become Support) ri-testato solo dal wick dopo il flip.
3. **Conferma "2 TF"**: il prezzo tocca il supporto HTF con un rifiuto
   (wick). Si scende di due timeframe (es. Daily → H1) per cercare un
   **breakout rialzista** con chiusura di corpo piena — qui il livello LTF
   non deve essere per forza fresh.
4. **Entrata**: dopo il breakout LTF, **aspettare il pullback** (spalla
   destra / QML) e entrare long lì, idealmente in confluenza con una
   trendline rialzista tracciata su close/open ("marriage concept" — se
   trendline e SNR coincidono nello stesso punto, priorità massima).
5. **Sessione**: preferire entrate durante Londra/New York.
6. **SL/TP**: SL sotto il livello di struttura appena confermato (non un
   multiplo fisso di ATR); TP verso la prossima resistenza HTF — spesso
   molto ampio (gli esempi del libro mostrano RR 1:20+).

### MALAYSIAN_SNR — SETUP SELL (resistenza)
Speculare ma non identico — parametri di sessione/conferma possono differire:
1. **Bias HTF**: Weekly/Daily in storyline ribassista.
2. **Livello**: una resistenza SNR **fresh**, oppure una resistenza flippata
   (SBR — Support Become Resistance) ri-testata solo dal wick dopo il flip.
3. **Conferma "2 TF"**: rifiuto (wick) sulla resistenza HTF → due timeframe
   più in basso, breakout ribassista con corpo pieno.
4. **Entrata**: pullback dopo il breakout LTF, in confluenza con trendline
   ribassista (marriage concept).
5. **Sessione**: Londra/New York.
6. **SL/TP**: SL sopra il livello di struttura; TP verso il prossimo
   supporto HTF, RR ampio.

### Stato: ipotesi da fonte esterna, non ancora testata
Questo è un punto di partenza per un **refactor guidato dalla fonte**, non
una config pronta per il codice — va prima verificato che i concetti
(fresh/unfresh close-to-open, flip SBR/RBS, 2-TF confirmation, trendline
marriage) siano implementabili nel motore MQL5/sito con ragionevole sforzo,
poi testato isolato prima di sostituire la logica attuale.

## Priorità di ricostruzione per le altre strategie

Non tutte le 37 hanno fonti esterne dirette ancora raccolte. Ordine
consigliato, per rapporto sforzo/beneficio:

**Tier 1 — fonte diretta già disponibile, da fare per prime**
- [[Malaysian Snr]] — fatto sopra, da implementare.
- `TURTLE_SOUP`, `LIQ_SWEEP`, `SH_BMS_RTO`, `SMS_BMS_RTO` — il ciclo ZIKIR
  (breakout+pullback+entry) di [[NEXUS EA - Fonte Secret of 4111 (Ali Yusoff)]]
  e il pattern "stop-hunt + BOS" del libro MSNR si applicano direttamente.
- `ORDER_BLOCK`, `OB_MIT`, `FVG_CONT`, `FVG_MIT`, `IFVG` — le "5 tipologie di
  Engulfing" (ISL/HSL) di Secret of 4.11 sono un candidato diretto per
  ridefinire come si marcano questi pattern SMC.
- `CISD`, `BJORGUM` — legate al concetto di BOS/trendline marriage.

**Tier 2 — priorità alta per impatto economico, fonte da cercare**
- `SAR`, `MACD`, `RSI_DIV`, `ADX_RSI` — le 4 peggiori del portafoglio
  ([[NEXUS EA - Backtest 10Y Segmentato - Analisi]]). Nessuna fonte esterna
  diretta ancora raccolta (sono indicatori classici, non concetti SMC/ICT) —
  qui la ricostruzione buy/sell dovrà venire dall'analisi trade-level
  (vedi [[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]]) più eventuali
  nuove fonti che l'utente fornirà.

**Tier 3 — sessione/ICT specifiche, serve materiale non ancora fornito**
- `SILVER_BULLET`, `JUDAS_SWING`, `LDN_REVERSAL`, `NY_REVERSAL`, `AMD_CONT`,
  `AMD_REVERSAL`, `PO3`, `OTE_CONT` — modelli ICT legati a orari/sessioni
  specifiche, solo accennati nel materiale letto finora (kill zone
  Londra/NY). Servirà altro materiale per ricostruirle correttamente — in
  attesa delle prossime chat/fonti che l'utente fornirà.

**Tier 4 — resto del portafoglio**
Tutte le altre, da affrontare mano a mano che arrivano fonti o mentre si
accumula più dato trade-level.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Principi]] · [[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]] · [[NEXUS EA - Fonte Secret of 4111 (Ali Yusoff)]] · [[Malaysian Snr]] · [[TODO - Backtest 10Y]]
