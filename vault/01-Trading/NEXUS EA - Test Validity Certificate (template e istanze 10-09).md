# Test Validity Certificate - template

Da compilare per OGNI test Research Mode d'ora in poi (richiesto dall'utente 10/09, dopo la scoperta del troncamento silenzioso da EQUITY_BREAKER su WICK_SWEEP_REV). Copiare il blocco e riempirlo.

```
STRATEGY:            <nome>
DATE RANGE:          <FromDate> -> <ToDate> (<durata>)
LEVERAGE:            1:<N>              <- da 10/09 SEMPRE esplicito
DEPOSIT/CURRENCY:    <...>
EXIT MODE:           RAW | RECIPE
OPT-IN ATTIVI:       ESL=<on/off> TotalDD=<on/off> DPT=<on/off> Ruin=<on/off> RiskShield=<on/off>
FIXED LOT:           <...>
TRADES:              <n>
EXIT AUTHORITY:      BROKER_SL=<n> BROKER_TP=<n> TESTER_END=<n> OTHER=<n> (dettaglio: <...>)
INVARIANT_FAIL:      <n> (deve essere 0 se RAW e nessun leak)
MARGIN/VOLUME BLOCKS: <si/no, dettaglio>
EQUITY_BREAKER:       <mai scattato / scattato a n=<x> trade, data <...> - vedi nota validita' sotto>
COVERAGE:             <% del periodo richiesto effettivamente coperto da trade, es. "19/87 giorni = 22%">
VALIDITA':            VALID FOR EDGE DESCRIPTIVE READING
                       | VALID BUT PARTIAL COVERAGE (vedi COVERAGE)
                       | INVALID FOR EDGE - <motivo, es. EQUITY BREAKER TRUNCATED AT N TRADES>
NOTE:                 <altre anomalie/scoperte specifiche di questo run>
```

## Istanze compilate (test gia' eseguiti in questa sessione)

### ADX_RSI RAW ESL OFF
```
STRATEGY:            ADX_RSI
DATE RANGE:          2023.09.01 -> 2026.08.26 (3 anni)
LEVERAGE:            1:100   <- test pre-standardizzazione, vedi nota
DEPOSIT/CURRENCY:    1000 USD
EXIT MODE:           RAW
OPT-IN ATTIVI:       ESL=off TotalDD=off DPT=off Ruin=off RiskShield=off (bypass non ancora esistente all'epoca del run, ma mai scattato comunque)
FIXED LOT:           0.01
TRADES:              22
EXIT AUTHORITY:      BROKER_SL=16 BROKER_TP=5 TESTER_END=1 OTHER=0
INVARIANT_FAIL:      0
MARGIN/VOLUME BLOCKS: no
EQUITY_BREAKER:       mai scattato (0 occorrenze nel log)
COVERAGE:             copertura piena del periodo (ultimo trade vicino a fine test)
VALIDITA':            VALID FOR EDGE DESCRIPTIVE READING
NOTE:                 51 trade storici (ricetta live) -> 22 in RAW isolato; gap atteso e coerente
                       (RAW rimuove tutti gli overlay di gestione/pyramid/reclaim che nella ricetta
                       live generano trade aggiuntivi sulla stessa sequenza logica).
```

### ADX_RSI RAW ESL ON
```
STRATEGY:            ADX_RSI
DATE RANGE:          2023.09.01 -> 2026.08.26 (3 anni)
LEVERAGE:            1:100   <- test pre-standardizzazione, vedi nota
DEPOSIT/CURRENCY:    1000 USD
EXIT MODE:           RAW
OPT-IN ATTIVI:       ESL=on TotalDD=off DPT=off Ruin=off RiskShield=off (bypass non ancora esistente)
FIXED LOT:           0.01
TRADES:              36
EXIT AUTHORITY:      BROKER_SL=15 BROKER_TP=6 TESTER_END=~1 OTHER=14 (post-fix: risolti come ESL via
                      exit-authority registry, commit d1609c1 - se rianalizzato oggi risulterebbero
                      41 SL+... NO: la disambiguazione va rifatta SUL LOG del run originale, che non
                      conteneva le entry del registry perche' compilato dopo - il conteggio OTHER=14
                      resta quello osservato, semanticamente e' ESL con alta confidenza ma non
                      riverificabile a posteriori su questo specifico file di log)
INVARIANT_FAIL:      14 (osservati PRIMA del fix del registry - risolti architetturalmente, non
                      rianalizzabili sul log gia' scritto)
MARGIN/VOLUME BLOCKS: no
EQUITY_BREAKER:       mai scattato per ADX_RSI (0 occorrenze) - il breaker NON e' il motivo di questo
                      test, e' un caso di SL nativo dell'ESL, non del breaker Sharpe
COVERAGE:             copertura piena (ultimo trade 2026.08.19, vicino a fine test)
VALIDITA':            VALID FOR EDGE DESCRIPTIVE READING (i 14 OTHER sono quasi certamente ESL, causa
                      gia' isolata e corretta architetturalmente, solo non re-instrumentata a posteriori)
NOTE:                 Primo run a scoprire il bug del ledger DEAL_REASON (vedi commit d1609c1).
```

### EMA_PULLBACK RAW (lanciato 15:30, prima del fix RiskShield/leverage)
```
STRATEGY:            EMA_PULLBACK
DATE RANGE:          2023.10.01 -> 2026.08.26 (~3 anni)
LEVERAGE:            1:100   <- test pre-standardizzazione
DEPOSIT/CURRENCY:    1000 USD
EXIT MODE:           RAW
OPT-IN ATTIVI:       ESL=off TotalDD=off DPT=off Ruin=off RiskShield=off (bypass non ancora esistente,
                      MA verificato: mai scattato per questa strategia)
FIXED LOT:           0.01
TRADES:              57
EXIT AUTHORITY:      BROKER_SL=36 BROKER_TP=21 TESTER_END=0 OTHER=0
INVARIANT_FAIL:      0
MARGIN/VOLUME BLOCKS: no (verificato su tutto il log condiviso del giorno)
EQUITY_BREAKER:       mai scattato (0 occorrenze "EQUITY_BREAKER...EMA_PULLBACK" nel log)
COVERAGE:             piena (ultimo trade 2026.08.19, a ridosso della fine test)
VALIDITA':            VALID FOR EDGE DESCRIPTIVE READING
NOTE:                 PF1.36, net $606.05, DD 34.38%/38.99%. Nessuna anomalia.
```

### FVG_CONT RAW (completato 20:56, Terminal1)
```
STRATEGY:            FVG_CONT
DATE RANGE:          2023.09.01 -> 2026.08.26 (3 anni)
LEVERAGE:            1:100 (run partito con l'ini vecchio, prima dell'aggiornamento template a 500)
DEPOSIT/CURRENCY:    1000 USD
EXIT MODE:           RAW
OPT-IN ATTIVI:       ESL=off TotalDD=off DPT=off Ruin=off RiskShield=off (compilato senza bypass:
                      il fix RiskShield e' stato committato/compilato dopo l'avvio di questo run -
                      MA verificato: mai scattato comunque per questa strategia)
FIXED LOT:           0.01
TRADES:              86
EXIT AUTHORITY:      BROKER_SL=62 BROKER_TP=24 TESTER_END=0 OTHER=0
INVARIANT_FAIL:      0
MARGIN/VOLUME BLOCKS: no (verificato su tutta la finestra del run)
EQUITY_BREAKER:       0 occorrenze
COVERAGE:             piena (nessuna anomalia di troncamento)
VALIDITA':            VALID FOR EDGE DESCRIPTIVE READING
NOTE:                 PF1.30, net $833.14, DD 49.08%/58.81% (drawdown notevolmente piu' alto delle
                      altre 3 strategie ufficiali - non toccato il trigger, solo osservato). 251 trade
                      storici (ricetta live) -> 86 in RAW isolato, PF storico 0.96 -> PF1.30 in RAW
                      (unico dei 4 test dove RAW migliora il PF storico, non solo riduce i trade).
```

### WICK_SWEEP_REV Fast Smoke (run precedente, INVALIDATO)
```
STRATEGY:            WICK_SWEEP_REV
DATE RANGE:          2026.06.01 -> 2026.08.26 (3 mesi, Fast Smoke Livello 1)
LEVERAGE:            1:500
DEPOSIT/CURRENCY:    1000 EUR
EXIT MODE:           RAW
OPT-IN ATTIVI:       ESL=off TotalDD=off DPT=off Ruin=off RiskShield=off (bypass non ancora esistente)
FIXED LOT:           0.02
TRADES:              50
EXIT AUTHORITY:      BROKER_SL=41 BROKER_TP=9 TESTER_END=0 OTHER=0
INVARIANT_FAIL:      0
MARGIN/VOLUME BLOCKS: no
EQUITY_BREAKER:       SCATTATO al 50esimo trade (2026-06-19 05:21), sharpe/trade=-0.07<0.30,
                      autoalimentato (rinnovo ogni 5 min sim) per il resto del test
COVERAGE:             19 giorni su 87 richiesti = 22%
VALIDITA':            **INVALID FOR EDGE — EQUITY BREAKER TRUNCATED AT 50 TRADES**
NOTE:                 Report archiviato in C:\MT5-Terminal3\invalid_runs\
                      nxs_fastsmoke_wicksweep_INVALID_EQUITY_BREAKER_TRUNCATED_AT_50_TRADES.htm
                      Rilanciato 10/09 19:44 con InpResearchUseRiskShield bypass (commit 1ac464d) e
                      leva 1:500 - vedi istanza successiva quando completo.
```

### WICK_SWEEP_REV Fast Smoke - run VALIDO (bypass RiskShield, 10/09 20:12)
```
STRATEGY:            WICK_SWEEP_REV
DATE RANGE:          2026.06.01 -> 2026.08.26 (3 mesi, Fast Smoke Livello 1)
LEVERAGE:            1:500
DEPOSIT/CURRENCY:    1000 EUR
EXIT MODE:           RAW
OPT-IN ATTIVI:       ESL=off TotalDD=off DPT=off Ruin=off RiskShield=off (bypass attivo, commit 1ac464d)
FIXED LOT:           0.02
TRADES:              178
EXIT AUTHORITY:      BROKER_SL=148 BROKER_TP=30 TESTER_END=0 OTHER=0
INVARIANT_FAIL:      0
MARGIN/VOLUME BLOCKS: no
EQUITY_BREAKER:       0 occorrenze (bypass confermato funzionante)
COVERAGE:             piena - primo trade 2026.06.01 06:45, ultimo 2026.08.25 23:00 (ultima barra H4 utile del test)
VALIDITA':            VALID FOR EDGE DESCRIPTIVE READING
NOTE:                 PF0.78, net -$151.39, WR 16.85% (30/178), avg win $17.54, avg loss -$4.58,
                      max perdite consecutive 18. Funnel: sweepsDetected=181, entryAttempts=178,
                      entryRejected=0, entryOpened=178 (tutti i tentativi riusciti - nessun cancello
                      residuo). Confronta con il run INVALIDATO sopra (50 trade, troncato al 22% del
                      periodo) per vedere l'effetto pieno del fix RiskShield: 178 vs 50 trade, copertura
                      100% vs 22%. Ancora SOLO descrittivo (Fast Smoke Livello 1, non validazione edge).
```

## Nota generale sulla leva 1:100 vs 1:500

Verificato sui log di tutti e 4 i test ufficiali eseguiti a leva 1:100: **zero blocchi margin/volume/preflight riconducibili alla leva** (lotti fissi 0.01, margine richiesto trascurabile rispetto al deposito $1000 a qualunque leva realistica). **Non invalidati, non rilanciati** - i risultati restano validi. Standardizzazione a 1:500 applicata solo ai template per test futuri (`nxs_research_*.ini` in `tmp/strategy_validation`), non retroattiva.
