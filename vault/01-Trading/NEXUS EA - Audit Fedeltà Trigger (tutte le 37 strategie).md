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
