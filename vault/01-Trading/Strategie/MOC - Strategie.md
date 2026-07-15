---
type: moc
domain: trading
status: active
tags: [trading, nexus-ea, strategie, moc]
created: 2026-07-12
updated: 2026-07-15
---

# Strategie — indice per stato di validazione

Le 36 schede di questa cartella, raggruppate per quanto ci si può fidare di
ciascuna **oggi**. Aggiorna questa pagina (spostando i link tra i gruppi) ogni
volta che una scheda cambia stato — è la vista rapida che sostituisce lo
scorrere 36 file per capire a che punto siamo.

**Aggiornamento 15/07**: arrivati 5 anni reali (2019-2023) dal backtest 10y
segmentato v2.5.0 — vedi [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] e
[[NEXUS EA - Hedge nel Tempo]]. I gruppi sotto riflettono questo, non più solo
il singolo test 3 mesi/3 anni di v2.4.8.

## ✅ Validate (1)
Profittevoli confermate su più finestre indipendenti con campione sufficiente.

- [[Turtle Soup]] — confermata anche sui 5 anni (+7.3R, 3/5 anni positivi)

## 🟢 Promettenti — nucleo hedge candidato (2)
Mai un anno negativo o quasi, insieme a Turtle Soup formano un combinato che fa
+14.7R su 5 anni con un solo anno debolmente negativo — vedi
[[NEXUS EA - Hedge nel Tempo]]. Campione ancora sotto i 15 trade/anno, da
confermare ma prioritari per un test isolato.

- [[Breakout Acc]] — +3.9R, 4/5 anni positivi
- [[Cisd]] — +3.5R, 0/5 anni negativi (ma solo 15 trade in 5 anni)

## 🔴 Fallite — confermato su 5 anni, priorità di intervento (3)
Non più "in attesa di validazione": campione ampio (452-838 trade in 5 anni),
il fix HTF di v2.5.0 non ha funzionato. Spiegano ~80% della perdita totale del
portafoglio. Vedi [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] per il
dettaglio codice/screening.

- [[Sar]] — -29.2R, **0/5 anni positivi**, la peggiore in assoluto
- [[Macd]] — -18.5R, era validata su v2.4.8 (PF 1.11) e il "raffinamento" v2.5.0 l'ha peggiorata
- [[Adx Rsi]] — -14.2R, 1/5 anni positivi

## ⏳ In attesa (config v2.5.0, dato ancora ambiguo o negativo minore) (4)
- [[Ema Pullback]] — -1.4R, 3/5 anni positivi ma volatile
- [[Ob Mit]] — -4.5R, 1/5 anni positivi
- [[Tsi]] — -5.8R, 1/5 anni positivi (solo 2023)
- [[Bjorgum]] — -6.6R su 5 anni, 4/5 negativi — **smentisce l'ottimismo precedente** (PF 2.14 su soli 5 trade, vedi [[NEXUS EA - Principi]] #4): il campione più ampio ribalta il segnale

## ❌ Non validate (fallite sui 3 anni / 5 anni) (2)
PF sotto 1.0 con campione sufficiente. Da rivedere o lasciare a rischio minimo.

- [[Fvg Cont]] — -2.3R sui 5 anni, ma 3/5 anni positivi (trascinata da un 2019 pessimo, -5.7)
- [[Rsi Div]] — -7.4R, trascinata da un solo anno pessimo (2022: -9.4)

## 🔬 Campione troppo piccolo (dato insufficiente) (8)
<15 trade sui 3 anni — il PF può sembrare buono ma non è statisticamente affidabile (vedi [[NEXUS EA - Principi]] #4).

- [[Bollinger]]
- [[Liq Sweep]]
- [[London Bo]]
- [[Order Block]]
- [[Sh Bms Rto]]
- [[Malaysian Snr]] — **spostata da "nessun trade"**: nel backtest 10y ha eseguito 10 trade in 5 anni (+0.4R)
- [[Fvg Mit]] — **spostata da "nessun trade"**: 3 trade in 5 anni
- [[Sms Bms Rto]] — **spostata da "nessun trade"**: 3 trade in 5 anni

## 📭 Nessun trade eseguito (4)
0 setup rilevati o segnali sempre bloccati nei 5 anni 2019-2023. Da investigare se dovrebbero generare trade — priorità più bassa di SAR/MACD/ADX_RSI perché qui non c'è nemmeno un segnale da correggere, va capito perché lo strumento non lo trova mai.

- [[Ifvg]]
- [[Liq Void]]
- [[Range Fade]]
- [[Weekly Exp]]

## 🔴 Disabilitate (5)
Spente esplicitamente in NXS_Profile_Enabled dopo test reali negativi.

- [[Bb Squeeze]]
- [[Disp Rebal]]
- [[Ichimoku]]
- [[Ote Cont]]
- [[Struct React]]

## 🔌 Non connesse (sessione/ICT) (7)
Richiedono modellazione intraday che il motore del sito non ha. Da validare isolate direttamente su MT5 (InpStrategySelector).

- [[Amd Cont]]
- [[Amd Reversal]]
- [[Judas Swing]]
- [[Ldn Reversal]]
- [[Ny Reversal]]
- [[Po3]]
- [[Silver Bullet]]

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Principi]] · [[NEXUS EA - Screening Strategie (sito 10y)]]
