---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bug, esecuzione, mt5, sar, macd, rsi-div, adx-rsi]
created: 2026-07-17
updated: 2026-07-17
---

# Caccia al bug di esecuzione + ricerca esterna (17/07)

Richiesta dell'utente: consiglia qualcosa per rendere profittevoli
SAR/MACD/RSI_DIV/ADX_RSI, cerca online come altri usano questi
indicatori, cerca bug/errori/logiche sbagliate nel codice. Durante questo
lavoro sono arrivati i primi 4 risultati REALI di MT5 (sweep isolato
1-37, `results/reports/sweep37/pre-fix-16-07/`) — dati pre-fix (compilati
prima dei fix di oggi) ma preziosissimi: la PRIMA volta che vediamo dati
di esecuzione MT5 reali per queste strategie isolate, non aggregate.

## Scoperta 1 (la più importante): un'anomalia nei dati reali che nessun fix di oggi spiega

Le 4 passate isolate (ADX_RSI, BOLLINGER, MACD, SAR — GOLD M15,
2019-2025, `InpDataCollectionMode`) mostrano tutte lo stesso pattern
sospetto:

| Strategia | Trade decisi | WR% | PF | avg_R_win | avg_R_loss | avg_holding |
|---|---|---|---|---|---|---|
| ADX_RSI | 625 | 31.0 | 0.58 | **+0.230** | **-0.177** | **6.06h** |
| BOLLINGER | 185 | 42.2 | 0.60 | **+0.160** | **-0.195** | **5.47h** |
| MACD | 176 | 20.5 | 0.13 | **+0.216** | **-0.431** | **3.56h** |
| SAR | 242 | 19.4 | 0.18 | **+0.293** | **-0.383** | **4.67h** |

**Il problema**: con SL=1× e TP=4× ATR (config dell'epoca), un vero TP
dovrebbe chiudere a **+4.0R esatto**, un vero SL a **-1.0R esatto** (R è
calcolato sul rischio ORIGINALE, `NXS_StratStats.mqh::_nxs_stats_dealR`,
formula verificata corretta). Invece **ogni singola strategia** — con TF,
SL/TP e logiche completamente diverse — chiude vinte e perse a una
frazione minuscola di R (0.16-0.29 invece di 4.0, -0.18/-0.43 invece di
-1.0), e **il tempo medio in posizione è sempre 3.5-6 ore**,
indipendentemente dal fatto che ADX_RSI/BOLLINGER siano strategie D1
(dovrebbero durare giorni) e MACD/SAR H4.

**Non è compatibile con "il prezzo tocca SL o TP"** — se lo facesse, R
sarebbe vicino a -1.0/+4.0 quasi sempre. Qualcos'altro chiude le
posizioni molto prima, a un P&L parziale, quasi sempre entro poche ore.

## Sospetto principale: il time-exit da 4 ore, non lo scaling per-strategia

`NXS_Management.mqh::NXS_ManageBreakevenAndTrail()` ha un exit forzato a
tempo (P1): `maxHoldSec = InpMaxHoldHours * 3600` (**`InpMaxHoldHours=4`**
— hardcoded, non `input`, letteralmente 4 ORE). Il codice ha un fix
esplicito (commento v2.3.1) per NON applicare questo cap alle strategie
coi profili: se legge il nome strategia dal commento della posizione,
prende `NXS_Profile_TF(nome)` (D1 per ADX_RSI) e scala
`maxHoldSec = PeriodSeconds(TF) * 40` (**40 giorni** per una D1). Il
commento stesso documenta che questo era GIÀ un bug noto in passato: "il
vecchio cap fisso di InpMaxHoldHours (4h) ammazzava le strategie D1/H4
prima del TP".

**Il meccanismo di scaling, letto nel codice, sembra corretto** (verificato
riga per riga: `NXS_ActivateTF`/`NXS_CollectAllSignals` girano
correttamente un passaggio per TF con handle ATR/indicatori dedicati per
D1/H4/H1, quindi anche `g_atr` usato per SL/TP è quello giusto, non quello
M15) — **ma il pattern nei dati reali (holding ~4h uniforme su strategie
D1 e H4) è impossibile da spiegare se lo scaling funzionasse**. O il
parsing del commento fallisce silenziosamente per queste posizioni
(es. formato diverso in `InpDataCollectionMode` rispetto a quello
atteso), o c'è un'altra causa non ancora trovata. **Non sono riuscito a
chiudere il cerchio da codice statico soltanto** — serve una verifica
diretta.

## Bug reale trovato e corretto: log CSV di chiusura sempre vuoto

Durante la caccia, trovato un bug concreto e indipendente: in
`OnTradeTransaction()` (`NEXUS_EA_v2.mq5`), la riga che scrive il log
CSV di ogni chiusura (`NXS_LogTradeCSV("CLOSE", ...)`) veniva chiamata
**PRIMA** che le variabili `strat` (nome strategia) e `reason` (sl/tp/
stop_out/**expert**) fossero calcolate — passava sempre stringhe vuote.
`reason="expert"` è esattamente il segnale di una chiusura FORZATA
dall'EA (`DEAL_REASON_EXPERT`, es. il time-exit sopra) invece che un
vero SL/TP toccato dal prezzo — la distinzione che serve per confermare
o smentire il sospetto sopra. **Spostata la chiamata dopo il calcolo**,
ora il CSV mostra la strategia e il motivo reale di ogni chiusura.

**Prossimo passo concreto per l'altro agente**: nel prossimo sweep (dopo
ricompilazione), controllare `NEXUS_trades.csv` (o il Journal MT5 per la
stringa `[NEXUS] Time-exit`) — se una quota alta di chiusure ha
`reason=expert` invece di `sl`/`tp`, conferma che il time-exit (o un
meccanismo simile) sta tagliando i trade molto prima del previsto, ed è
la causa strutturale della sotto-performance di SAR/MACD/RSI_DIV/ADX_RSI
su MT5 — molto più grande di qualsiasi fix di proxy fatto finora in
questa sessione.

## Ricerca esterna: come i professionisti usano questi indicatori

- **Parabolic SAR + ADX come filtro**: tecnica da manuale (raccomandata
  dallo stesso Wilder, creatore di entrambi gli indicatori). Uno studio
  DailyFX (EUR/USD daily) citato dalla ricerca: aggiungere ADX>25 come
  filtro ha portato il WR dal 47% al 58%, riducendo i segnali del 40% —
  SAR da solo soffre di whipsaw nei mercati laterali perché "è sempre
  acceso" e si inverte anche su rumore minimo. [Combining Parabolic SAR with ADX](https://unofficed.com/courses/entropy/lessons/combining-parabolic-sar-with-adx/) · [Parabolic SAR: The Trailing Stop Indicator for Trend Traders](https://www.tradealgo.com/trading-guides/technical-analysis/parabolic-sar-the-trailing-stop-indicator-for-trend-traders)
- **ADX come filtro universale di forza del trend**: soglia standard
  20-25 (sotto 20 = laterale, sopra 25 = trend forte); i professionisti
  lo usano per decidere SE tradare trend-following, non come segnale a
  sé. Backtest citati mostrano che aggiungere ADX riduce il drawdown
  evitando entrate nei mercati laterali. [ADX Indicator Trading Strategy — Mind Math Money](https://www.mindmathmoney.com/articles/adx-indicator-trading-strategy-the-complete-guide-to-finding-trends-like-a-pro) · [ADX 25+: The One Filter That Kills Bad Trades](https://fxnx.com/en/blog/adx-strategy-efficiency-filter-measure-trend-strength-like)
- **MACD**: la tecnica più citata è il filtro multi-conferma (trend
  HTF + ADX + volume) e il filtro zero-line (solo long sopra zero, solo
  short sotto) — quest'ultimo NEXUS lo applica già. Timeframe più bassi
  producono fino a 3× più falsi segnali di un daily. [MACD Indicator Guide 2025](https://piptrend.com/macd-indicator/) · [Avoiding Whipsaw](https://abovethegreenline.com/whipsaw-trading/)
- **RSI divergence**: il punto più importante — "la divergenza è un
  ALERT, non un segnale d'ingresso". Serve una conferma price-action
  (candela di reversal, rottura di una trendline minore, chiusura sopra/
  sotto una EMA breve) DOPO la divergenza, prima di entrare. Senza
  conferma il WR scende sotto il 40%; con conferma sale al 55-65%. [RSI Divergence Trading Strategy — AlgoAlpha](https://algoalpha.io/blog/rsi-divergence-trading-strategy-how-to-spot-trade-and-avoid-false-signals) · [RSI Divergence Confirmation](https://tradefundrr.com/rsi-divergence-confirmation/)

## Test A/B degli spunti esterni sul motore sito — risultato onesto: non aiutano qui

Implementate e testate le 3 idee più forti (SAR+ADX>25, MACD+ADX>20,
RSI_DIV+conferma price-action via EMA9), sulla config reale di ciascuna
strategia (H4/H1, SL/TP/HTF del profilo):

| Variante | Trade (prima→dopo) | PF (prima→dopo) | DD% (prima→dopo) | Net (prima→dopo) |
|---|---|---|---|---|
| SAR + ADX>25 | 66→37 | 2.01→1.71 | 8.19→**3.94** | 4.233→1.654 |
| MACD + ADX>20 | 77→72 | 1.77→1.50 | 5.85→7.73 | 2.859→1.773 |
| RSI_DIV + conferma EMA9 | 84→11 | 1.34→1.16 | 11.91→**4.90** | 2.275→122 |

**Nessuna delle tre migliora nel complesso** — il DD scende parecchio in
2 casi su 3 (coerente con la letteratura: meno segnali, più selettivi),
ma PF e net peggiorano sempre, e il campione crolla (RSI_DIV+conferma:
84→11 trade, troppo pochi per fidarsi). Per SAR era già stato testato il
15/07 con lo stesso esito ("non aggiungere filtro ADX: testato,
peggiora") — questo lo conferma anche sul TF di produzione vero (H4,
non D1 come il test originale). **Nessuna applicata.**

**Lettura di questo risultato**: tecniche da manuale, validate
esternamente su altri dataset/strumenti, non si trasferiscono
automaticamente a XAUUSD con la logica NEXUS specifica — coerente con
tutto quello che si è visto oggi (un fix valido altrove non è garanzia
qui). Ma soprattutto: se filtri di INGRESSO ben validati non spostano
l'ago, il problema molto probabilmente non è "il trigger si sbaglia
troppo spesso" — è più coerente con l'ipotesi di esecuzione (sezione
sopra) che con un problema di qualità del segnale.

## Conclusione e raccomandazione

1. **Priorità assoluta**: verificare l'ipotesi time-exit/reason=expert
   sul prossimo sweep (ora che il log CSV è riparato). Se confermata, è
   il bug più importante trovato in tutta la sessione — spiegherebbe da
   solo la sotto-performance MT5 di molte più delle 4 strategie
   analizzate oggi (chiunque abbia un profilo D1/H4 sarebbe colpito).
2. Non applicare i filtri ADX/conferma esterni: testati, non aiutano su
   questi dati.
3. Il lavoro di oggi (TP largo+BE, confirm_bars/loss_cooldown) resta
   valido come miglioramento del SEGNALE — ma se il vero collo di
   bottiglia è un'uscita forzata a 4h, nessuno di quei fix può funzionare
   finché non è risolto, perché il trade non arriva mai a vedere il
   TP largo.

## Collegamenti
[[MOC - Trading]] · [[Sar]] · [[Macd]] · [[Rsi Div]] · [[Adx Rsi]] · [[NEXUS EA - Gestione Uscita MFE-MAE (17-07)]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] · [[TODO - Backtest 10Y]]
