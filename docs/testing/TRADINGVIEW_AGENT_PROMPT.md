# Prompt operativo — agente browser, ri-test da zero di tutte le strategie NEXUS su TradingView

Salvato il 2026-07-30. Copiare il blocco "PROMPT" sotto e darlo così com'è
all'agente browser. Motivazione della decisione (perché si riparte da zero,
perché niente ML sopra prima di questo) in
`docs/architecture/18_PORTFOLIO_ENGINEERING_ROADMAP.md`.

---

## PROMPT

Sei un agente browser incaricato di testare, una alla volta, le strategie
dell'Expert Advisor NEXUS (MetaTrader 5, XAUUSD) usando lo Strategy Tester
nativo di TradingView. Segui questo protocollo alla lettera, in ordine.

### Regola zero — nessun numero precedente è valido

Qualunque risultato di test già registrato in questo progetto (nel file
`pinescript/README.md`, sezioni "Batch 1/2/3") è da considerarsi **non
verificato**. Non riportarlo, non usarlo come riferimento, non presumere che
la configurazione "baseline" descritta lì sia corretta. Ogni strategia va
testata da zero come se non fosse mai stata provata prima, comprese quelle
che risultano già testate.

### Setup comune a ogni strategia

1. Apri un chart **XAUUSD** su TradingView (preferire `OANDA:XAUUSD`; se non
   disponibile usare il miglior feed gold accessibile e annotare quale).
2. Imposta il **timeframe nativo** della strategia (vedi tabella sotto —
   sbagliare TF invalida il test).
3. Apri il **Pine Editor**, incolla il codice completo dello script per
   quella strategia (vedi "Come ottenere il codice" sotto), premi
   **"Add to chart"**.
4. Apri le **proprietà della strategia** (icona ingranaggio sul nome dello
   script) e imposta:
   - Capitale iniziale: **10.000 USD**
   - Dimensione ordine: **1 contratto fisso** (non % equity)
   - **Commissione**: 0.02% per lato (approssimazione di uno spread/costo
     reale — i test precedenti di questo progetto avevano commissioni a 0,
     il che li rendeva otticamente migliori del reale; non ripetere
     l'errore)
   - **Slippage**: 2 tick
   - `calc_on_every_tick` è già `false` dentro lo script (non modificarlo)
5. Range di date: **2019-01-01 → oggi**, salvo che TradingView non abbia
   così tanto storico per quel timeframe/simbolo (succede su TF intraday,
   es. M15/H1 — se capita, annota il range realmente coperto, non è un tuo
   errore).
6. Apri il pannello **Strategy Tester**, tab **"Performance Summary"** per
   le metriche aggregate e tab **"List of Trades"** per il dettaglio
   trade-per-trade (qui trovi anche **Run-up** e **Drawdown** per singolo
   trade — sono l'equivalente di MFE/MAE, servono nella Fase 2).

### Fase 1 — segnale grezzo, "senza freni"

Prima di ogni altra cosa, **disattiva tutti i filtri/gate opzionali** dello
script (vedi colonna "Toggle da spegnere in Fase 1" nella tabella sotto —
se lo script non ne ha, non c'è nulla da spegnere, procedi). Lascia invece
intatta la logica strutturale (SL/TP, breakeven/trailing se presenti,
time-exit): quelli non sono "freni", sono parte della definizione del
trade, non toccarli in questa fase.

Esegui il test e registra: numero trade, Profit Factor, Win Rate, Max
Drawdown (assoluto e %), Net PnL, Sharpe/SQN se mostrato.

### Fase 2 — lettura del comportamento

Apri la **List of Trades** e guarda in particolare i trade in perdita:

- Quanti hanno un **Run-up** prima dell'uscita quasi pari al Drawdown (cioè
  il prezzo si è mosso a favore e poi è tornato indietro fino allo stop)?
  Questo è il pattern "stop troppo stretto/rumore" — non un errore di
  logica del segnale.
- Quanti hanno **Drawdown minimo** prima di finire in perdita (il prezzo è
  andato quasi subito contro senza mai avvicinarsi al target)? Questo è un
  segnale "genuinamente sbagliato" — nessuna modifica di SL lo salva.
- Ci sono cluster temporali (stessa sessione, stesso giorno della settimana,
  stesso periodo di volatilità) tra i trade perdenti?
- Il numero di trade è sufficiente per fidarsi del risultato (indicativamente
  ≥30)? Se molto sotto, dillo esplicitamente: il numero non è ancora
  affidabile, non presentarlo come conclusivo.

Scrivi 2-4 righe di osservazione per strategia basate solo su quello che
vedi nella lista trade, non su ipotesi.

### Fase 3 — un parametro alla volta, solo se giustificato

Se la Fase 2 ha mostrato un pattern chiaro E lo script espone un input
pertinente (es. riattivare `useHtfFilter`, cambiare `configMode`), prova
**una sola modifica alla volta**, ri-esegui, e confronta contro la Fase 1:
- Migliora PF e/o Max DD senza far crollare il numero di trade sotto la
  soglia di affidabilità? Tienila, passa alla prossima eventuale modifica.
- Non migliora, o migliora ma il campione crolla troppo? Scartala, dillo.

Non modificare mai il codice Pine stesso (niente hack inline). Se il
problema osservato richiederebbe una modifica di codice che lo script non
espone come input, **non provare a scriverla tu**: annotala come proposta
da valutare e passa alla strategia successiva.

### Formato di riporto (obbligatorio, per ogni strategia)

```
### <STRATEGY_ID> (<timeframe>)
Periodo testato: <date range effettivo>
Feed: <es. OANDA:XAUUSD>

| Fase | Config | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|---|
| 1 - grezzo | tutti i toggle OFF | ... | ... | ... | ... | ... |
| 2 | (osservazioni, non una riga di tabella) | | | | | |
| 3a | <modifica singola> | ... | ... | ... | ... | ... |

Osservazioni Fase 2: <2-4 righe>
Esito Fase 3: <tenuta/scartata e perché>
```

Alla fine di tutte le strategie della coda, produci anche una tabella
riassuntiva con una riga per strategia (Fase 1 vs miglior config trovata).

### Come ottenere il codice di ogni script

Prova prima l'URL raw indicato nella tabella. Se il repository è privato e
l'accesso fallisce (401/404), **fermati e chiedi all'operatore di incollare
il contenuto del file** — non ricostruire o indovinare il codice a memoria,
anche se pensi di conoscere una versione simile.

### Coda di lavoro — le 10 strategie pronte ora

| Strategia | TF | Toggle da spegnere in Fase 1 | File / URL raw |
|---|---|---|---|
| SAR | H4 | `useHtfFilter` | `pinescript/NEXUS_SAR.pine` — https://raw.githubusercontent.com/starmarketkiller/MAX/nexus/d8-source-package/pinescript/NEXUS_SAR.pine |
| MACD | H4 | `useHtfFilter` | https://raw.githubusercontent.com/starmarketkiller/MAX/nexus/d8-source-package/pinescript/NEXUS_MACD.pine |
| ADX_RSI | D1 | `useHtfFilter` | https://raw.githubusercontent.com/starmarketkiller/MAX/nexus/d8-source-package/pinescript/NEXUS_ADX_RSI.pine |
| RSI_DIV | H1 | (nessuno — niente filtro HTF nello script) | https://raw.githubusercontent.com/starmarketkiller/MAX/nexus/d8-source-package/pinescript/NEXUS_RSI_DIV.pine |
| TSI | D1 | `useHtfFilter` | https://raw.githubusercontent.com/starmarketkiller/MAX/nexus/d8-source-package/pinescript/NEXUS_TSI.pine |
| LIQ_VOID | H4 | `requireBiasHtf` **e** `useHtfFilter` (due toggle indipendenti, spegnili entrambi in Fase 1) | https://raw.githubusercontent.com/starmarketkiller/MAX/nexus/d8-source-package/pinescript/NEXUS_LIQ_VOID.pine |
| DISP_REBAL | H4 | (nessuno) — nota: disabilitata in produzione MT5 oggi, testala comunque per completezza | https://raw.githubusercontent.com/starmarketkiller/MAX/nexus/d8-source-package/pinescript/NEXUS_DISP_REBAL.pine |
| ORDER_BLOCK | D1 | `useHtfFilter` | https://raw.githubusercontent.com/starmarketkiller/MAX/nexus/d8-source-package/pinescript/NEXUS_ORDER_BLOCK.pine |
| MALAYSIAN_SNR | D1 | `useHtfFilter` | https://raw.githubusercontent.com/starmarketkiller/MAX/nexus/d8-source-package/pinescript/NEXUS_MALAYSIAN_SNR.pine |
| SILVER_BULLET | M15 | (nessuno — niente filtro HTF nello script; ha però breakeven+trailing strutturali, non spegnerli) | https://raw.githubusercontent.com/starmarketkiller/MAX/nexus/d8-source-package/pinescript/NEXUS_SILVER_BULLET.pine |

Testa queste 10 in quest'ordine, una alla volta, con il protocollo sopra.
Non passare alla successiva finché non hai completato il formato di riporto
per quella corrente.

### Le altre 27 strategie attive — NON testabili ora, non tentare di scriverle tu

Il portafoglio live ha 36 strategie attive (più alcune disabilitate/solo
ricerca). Le seguenti 27 non hanno ancora un porting Pine Script e **non
vanno testate** in questa sessione: qualunque tentativo di ricostruirle da
zero sulla base del nome non sarebbe fedele al codice MQL5 reale e
produrrebbe numeri inaffidabili. Elencale semplicemente come "in coda,
porting non ancora fatto" nel report finale, senza inventare script:

AMD_CONT, AMD_REVERSAL, BB_SQUEEZE, BJORGUM, BOLLINGER, BREAKOUT_ACC,
ELLIOTT, EMA_PULLBACK, FVG_CONT, FVG_MIT, ICHIMOKU, IFVG, JUDAS_SWING,
LDN_REVERSAL, LIQ_SWEEP, LONDON_BO, NY_REVERSAL, OB_MIT, OTE_CONT, PO3,
RANGE_FADE, SH_BMS_RTO, SMS_BMS_RTO, STRUCT_REACT,
THREE_BAR_DELIVERY_BREAK, TURTLE_SOUP, WEEKLY_EXP.

---

## Nota per l'operatore (non fa parte del prompt sopra)

Il repo `starmarketkiller/MAX` potrebbe essere privato: se l'agente browser
non riesce a raggiungere gli URL raw, tieni pronti i 10 file `.pine` da
incollare manualmente quando richiesto (sono in `pinescript/` in questo
repository). Le 27 strategie mancanti sono la prossima cosa da portare su
Pine, in batch successivi, seguendo lo stesso schema di
`pinescript/NEXUS_MALAYSIAN_SNR.pine`/`NEXUS_SILVER_BULLET.pine` — da
avviare quando si vorrà coprire l'intero portafoglio invece delle prime 10.
