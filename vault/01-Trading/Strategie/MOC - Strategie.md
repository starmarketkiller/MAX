---
type: moc
domain: trading
status: active
tags: [trading, nexus-ea, strategie, moc]
created: 2026-07-12
updated: 2026-07-12
---

# Strategie — indice per stato di validazione

Le 36 schede di questa cartella, raggruppate per quanto ci si può fidare di
ciascuna **oggi**. Aggiorna questa pagina (spostando i link tra i gruppi) ogni
volta che una scheda cambia stato — è la vista rapida che sostituisce lo
scorrere 36 file per capire a che punto siamo.

## ✅ Validate (1)
Profittevoli confermate su almeno 15 trade sui 3 anni. Le uniche su cui ci si può appoggiare oggi.

- [[Turtle Soup]]

## ⏳ In attesa di validazione (config cambiata in v2.5.0) (7)
La config è stata appena cambiata sulla base dello screening sito. Aggiornare qui appena arriva il risultato della validazione 3M+3Y in corso.

- [[Adx Rsi]]
- [[Breakout Acc]]
- [[Ema Pullback]]
- [[Macd]]
- [[Ob Mit]]
- [[Sar]]
- [[Tsi]]

## ❌ Non validate (fallite sui 3 anni) (2)
PF sotto 1.0 sui 3 anni con campione sufficiente. Da rivedere o lasciare a rischio minimo.

- [[Fvg Cont]]
- [[Rsi Div]]

## 🔬 Campione troppo piccolo (dato insufficiente) (7)
<15 trade sui 3 anni — il PF può sembrare buono ma non è statisticamente affidabile (vedi [[NEXUS EA - Principi]] #4).

- [[Bjorgum]]
- [[Bollinger]]
- [[Cisd]]
- [[Liq Sweep]]
- [[London Bo]]
- [[Order Block]]
- [[Sh Bms Rto]]

## 📭 Nessun trade eseguito (7)
O 0 setup rilevati o segnali sempre bloccati. Da investigare se dovrebbero generare trade.

- [[Fvg Mit]]
- [[Ifvg]]
- [[Liq Void]]
- [[Malaysian Snr]]
- [[Range Fade]]
- [[Sms Bms Rto]]
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
