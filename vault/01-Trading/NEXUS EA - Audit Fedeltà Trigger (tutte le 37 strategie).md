---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, audit, fedelta, trigger, bug]
created: 2026-07-15
updated: 2026-07-15
---

# Audit di fedeltà: ogni strategia usa davvero il trigger del suo nome?

Richiesta diretta dell'utente dopo la scoperta di SAR/ADX_RSI (15/07): non
fidarsi che il resto sia a posto solo perché quei due erano rotti — leggere
**ogni singola strategia** (37 su MQL5, dove gira davvero il denaro, più il
corrispondente sul motore sito) e verificare che il trigger d'ingresso
appartenga davvero al nome che porta. Letto per intero:
`NXS_Strategies.mqh` (16), `NXS_Strategies_Institutional.mqh` (10),
`NXS_Strategies_SMC.mqh` (10), `NXS_Strategies_Elliott.mqh` (1) = 37 su
MQL5, più tutte le `sig_*` in `server/backtest.py`.

## Risultato: la maggior parte è a posto. 3 casi reali trovati (2 già corretti)

| Strategia | MQL5 | Sito | Verdetto |
|---|---|---|---|
| **SAR** | ✅ `iSAR()` reale (`g_hSAR`, `NEXUS_EA_v2.mq5:88`) | 🔴 **era identico a EMA_PULLBACK** | Sito corretto oggi |
| **ADX_RSI** | 🔴 **non leggeva mai `g_adx`** nonostante il nome | 🔴 **non calcolava mai ADX** | Entrambi corretti oggi (soglia 20) |
| **TSI** | ⚠️ **dichiarato nel commento "simplified RSI/EMA proxy"**, non vero TSI (William Blau, doppio smoothing EMA del momentum) | ⚠️ stesso proxy | **Non ancora corretto — vedi decisione da prendere sotto** |
| Tutte le altre 34 | ✅ trigger coerente col nome (verificato leggendo il codice) | Vedi nota sui proxy dichiarati sotto | OK |

## Round 2 (16/07): la domanda che doveva essere fatta subito — "ne mancano altre?"

Dopo aver trovato BJORGUM (proxy EMA ribbon invece di pivot-bounce), MACD
(incrocio zero invece di MACD/signal+EMA200) e RSI_DIV (rientro RSI invece
di vera divergenza) — **tre bug in più dello stesso tipo di SAR**, non
trovati nel primo giro — l'utente ha chiesto direttamente se altre
strategie avessero lo stesso problema. Ripassato sistematicamente ogni
`sig_*` "reale" (non tra i 6 proxy già dichiarati sotto) contro la sua
`NXS_Strat_*` MQL5:

| Strategia | Esito |
|---|---|
| BOLLINGER | ✅ fedele (rientro banda su close, nessun filtro extra — combacia esattamente) |
| EMA_PULLBACK | ✅ fedele (trend EMA20/50 + pullback — combacia) |
| CISD | ✅ fedele (già verificato nel Blocco 3) |
| **BREAKOUT_ACC** | 🔴 **bug trovato**: sito chiedeva 1 sola chiusura oltre il range, la vera "Acceptance" ne richiede 2 consecutive. **Corretto** — a differenza degli altri, qui il fix **migliora** il risultato (PF1.88→2.15), non lo smentisce: la strategia era già solida. |
| BB_SQUEEZE | ⚠️ gap minore trovato: definizione di "squeeze" diversa (MQL5: width vs ATR fisso; sito: percentile sulle ultime 40 barre) e breakout misurato su riferimenti diversi. **Non corretto** — strategia disabilitata (`NXS_Profile_Enabled`), priorità bassa. |
| ICHIMOKU | ⚠️ gap minore trovato: il sito calcola Tenkan/Kijun/Span senza lo sfasamento in avanti (displacement) standard della nuvola Ichimoku. **Non corretto** — strategia disabilitata, priorità bassa. |
| OB_MIT / ORDER_BLOCK | ⚠️ gap minore: manca sul sito il filtro opzionale `InpUseSMCReactionGate` (conferma reazione aggiuntiva su MT5). Logica di base comunque fedele. Non corretto — filtro secondario, non il trigger centrale. |
| MALAYSIAN_SNR | Nessun bug nuovo — la semplificazione multi-TF era già nota (vedi sotto), non un bug nascosto. |

**In totale: 5 bug reali trovati finora** (SAR, BJORGUM, MACD, RSI_DIV,
BREAKOUT_ACC), tutti corretti sul sito. Le strategie disabilitate
(BB_SQUEEZE, ICHIMOKU, DISP_REBAL, OTE_CONT, STRUCT_REACT) non sono state
riverificate a fondo — priorità bassa finché restano spente in produzione.

## E le strategie "non connesse" (AMD_*, JUDAS_SWING, LDN/NY_REVERSAL, PO3, SILVER_BULLET)?

Risposta diretta alla seconda domanda dell'utente: **non manca qualcosa di
strutturalmente impossibile da ottenere**. Il motore sito PUÒ scaricare
dati intraday reali con timestamp veri via Yahoo (`_fetch_real`, già usato
per lo sweep multi-TF di TURTLE_SOUP: H1/H4 fino a 2 anni di storico, M15
fino a 60 giorni) — le candele hanno un campo `time` con ora reale
(`HH:MM`), sufficiente per calcolare le sessioni Londra/NY/Asia che queste
7 strategie richiedono. **Il pezzo mancante non è il dato, è che nessuna
di queste 7 è mai stata collegata nel dizionario `STRATEGIES` del sito** —
zero righe di codice scritte per loro finora, non un limite dei dati.
Con gli orari già trovati in ricerca (Silver Bullet 3-4/10-11/14-15 ET,
Judas Swing 2-5 EST) sarebbe possibile implementarle e testarle davvero,
anche se con uno storico più corto (2 anni, non 10) di quello disponibile
su D1. Non ancora fatto — proposta per un prossimo blocco, da confermare
con l'utente prima di investirci tempo.

## TSI: il terzo caso, con un trade-off da decidere (non ancora corretto)

Implementato il vero TSI (doppio smoothing EMA(25)/EMA(13) del momentum,
crossing dello zero) e testato A/B sul motore sito (funzione `tsi_series()`
già scritta in `backtest.py`, non ancora collegata al trigger):

| Versione | Trade (10y sito) | PF | DD% |
|---|---|---|---|
| Proxy attuale (RSI/EMA) | 245 | 1.35 | 10.57 |
| **TSI vero** | **67** | **1.42** | **4.99** |

Il vero TSI è **qualitativamente migliore** (PF più alto, drawdown quasi
azzerato) ma genera **il 73% di trade in meno**. Su MT5, dove il proxy fa
oggi 721 trade in 6 anni (il campione più grande dopo SAR e MACD), un taglio
proporzionale porterebbe TSI a circa 190-200 trade in 6 anni — ancora un
campione utilizzabile, ma una riduzione drastica di frequenza.

**Non ho sostituito il trigger** (né sito né MQL5) perché questo non è un
fix "gratis" come SAR/ADX_RSI: è un compromesso esplicito
frequenza-vs-qualità che tocca anche quanto TSI contribuisce alla
diversificazione nel tempo del portafoglio (vedi
[[NEXUS EA - Hedge nel Tempo]]) — merita una decisione tua, non
un'assunzione mia. Il codice per farlo è pronto (`tsi_series()` in
`backtest.py`), è un cambio di poche righe quando deciderai.

## Correzione a una mia nota precedente: MALAYSIAN_SNR è meno debole di quanto scritto

In [[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]] avevo scritto che il
trigger attuale "cattura solo una frazione minima" del libro. **Rileggendo
`NXS_Strat_MalaysianSNR_Rejection()` per intero, non è così minimale**: usa
già livelli S/R basati su chiusura (non wick, come richiede il libro),
un controllo di freschezza a 20 barre H4, una storyline H4+D1, e richiede
una candela di rifiuto con corpo forte. Mancano ancora: la regola di
conferma a "2 timeframe", il "marriage concept" con le trendline, e il
filtro sessione Londra/NY esplicito — ma la base è più solida di quanto
avevo detto. Corretto qui per onestà, non ignorato.

## Nota sui "proxy dichiarati" del motore sito (non bug, ma da ricordare)

Il dizionario `STRATEGIES` in `backtest.py` dichiara esplicitamente 6
strategie come proxy di un'altra, perché il sito (dati daily, no sessioni
intraday) non può testarle per davvero:
`LONDON_BO→sig_breakout`, `RANGE_FADE→sig_bollinger`,
`WEEKLY_EXP→sig_breakout`, `LIQ_VOID→sig_fvg_cont`,
`SH_BMS_RTO→sig_ob_mit`, `SMS_BMS_RTO→sig_ob_mit`. Non sono un bug (sono
etichettati come tali nel codice), ma significano che **lo screening sito
per queste 6 non dice nulla sulla loro vera logica** — solo su un cugino
approssimativo. Su MT5 invece tutte e 6 hanno la loro vera implementazione
(verificato: usano sessione/sweep/struttura reali, non un proxy).

## Scoperta collaterale: ELLIOTT (la 37ª strategia) non era tracciata nel vault

`NXS_Strategies_Elliott.mqh` implementa un vero conteggio meccanico delle
onde di Elliott (pivot alternati, ritracciamento Fibonacci, onda 2→3, onda
4→5, reversal di onda 5) — sofisticato e coerente col nome. **Non compare
in [[MOC - Strategie]] né ha una scheda propria** — probabilmente perché non
è nella lista storica di 36 usata come riferimento. Da aggiungere al
tracking (non è nel motore sito, quindi va validata solo su MT5 isolata).

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] · [[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]] · [[Adx Rsi]] · [[Sar]] · [[Tsi]] · [[TODO - Backtest 10Y]]
