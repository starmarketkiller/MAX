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

**Aggiornamento 15/07 (segmento 9)**: arrivati 6 anni reali (2019-2024) dal
backtest 10y segmentato v2.5.0 — vedi [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]
e [[NEXUS EA - Hedge nel Tempo]]. Il segmento 9 ha ridimensionato TURTLE_SOUP
(da migliore strategia a quasi-breakeven) e peggiorato RSI_DIV (ora tra le
fallite) — i gruppi sotto riflettono questo aggiornamento, non solo il primo
giro di 5 anni.

## 🟢 Promettenti — nucleo hedge candidato (3)
Il combinato dei tre fa +7.6R su 6 anni (era +14.7R su 5, il 2024 ha tolto
quasi metà del guadagno) — resta comunque nettamente il miglior angolo del
portafoglio, vedi [[NEXUS EA - Hedge nel Tempo]]. BREAKOUT_ACC è l'unica delle
tre a non aver mai avuto un anno chiaramente negativo.

- [[Breakout Acc]] — +4.3R su 6 anni, 5/6 anni positivi — la più stabile del nucleo
- [[Cisd]] — +3.2R su 6 anni, primo anno negativo nel 2024 (-0.3, comunque marginale)
- [[Turtle Soup]] — **ridimensionata**: +0.1R su 6 anni (era +7.3R su 5). Il 2024
  (-7.2R) ha quasi azzerato tutto il guadagno accumulato. Non più "validata"
  senza riserve.

## 🔴 Fallite — confermato su campione ampio, priorità di intervento (5)
Campione ampio (400-1.150 trade su 6 anni), il fix HTF di v2.5.0 non ha
funzionato. Spiegano gran parte della perdita totale del portafoglio. Vedi
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]] per il dettaglio codice/screening.
15/07: fix sperimentali applicati a SAR e ADX_RSI (vedi
[[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]]), non ancora
validati su MT5.

- [[Sar]] — -34.3R, **0/6 anni positivi**, la peggiore in assoluto. Fix testato: vero Parabolic SAR nel proxy sito, PF 1.17→1.28.
- [[Macd]] — -21.1R, era validata su v2.4.8 (PF 1.11) e il "raffinamento" v2.5.0 l'ha peggiorata
- [[Rsi Div]] — -17.5R — **sale in questo gruppo col segmento 9**: il 2024 (-10.1) è il suo anno peggiore in assoluto
- [[Adx Rsi]] — -15.3R, 1/6 anni positivi. Fix applicato: aggiunto vero filtro ADX>20 (mai calcolato prima nonostante il nome).
- [[Tsi]] — -7.9R su 6 anni ma **721 trade** (campione enorme) — riclassificata da "Strat Diag" corretto come CRITICA, non più "in attesa": PF 0.82 è troppo stabilmente negativo per essere ambiguo.

## ⏳ In attesa (config v2.5.0, dato ancora ambiguo o negativo minore) (3)
- [[Fvg Cont]] — -9.3R su 6 anni, 2024 pessimo (-7.0) dopo 3 anni di ripresa
- [[Bjorgum]] — -8.6R su 6 anni (96 trade), 5/6 negativi. 16/07: trovato e
  corretto un bug di proxy sul sito (EMA ribbon invece del vero rimbalzo su
  pivot, stesso tipo di bug di SAR) e applicata una nuova config al profilo
  MQL5 (SL1.5/TP3.0, HTF OFF) — **non ancora validata su MT5**, in attesa
  dello sweep isolato
- [[Ema Pullback]] — -5.5R, volatile, nessun trend chiaro

## ❌ Non validate — negativa ma marginale (1)
PF sotto 1.0, negativa ma non tra le priorità peggiori.

- [[Ob Mit]] — -4.1R su 6 anni, ma 2024 positivo (+0.4) — potrebbe essere in ripresa

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

## 🔌 Prima connessione al sito, mai validate su MT5 (sessione/ICT) (7)
16/07: non erano "non testabili per limite di dati" come si pensava — il
sito scarica già intraday reale, mancava solo il codice. Implementate e
testate per la prima volta (SL1.5/TP3.0 generico, nessun profilo MT5 mai
esistito, ~2 anni di dati Yahoo intraday, non 10). Dati preliminari, da
validare su MT5 isolato prima di qualunque conclusione.

- [[Amd Cont]] — 🟢 il più promettente: PF2.07 su 4h (62 trade, DD5.85%)
- [[Po3]] — 🟢 PF1.29 su 4h (48 trade, DD4.0% — il più basso del gruppo)
- [[Silver Bullet]] — 🟢 PF1.52 su 4h (68 trade) ma negativo su 1h
- [[Amd Reversal]] — ⏳ quasi breakeven su 4h (PF1.10, 57 trade)
- [[Ldn Reversal]] — ⏳ quasi breakeven su 4h (PF1.01, 99 trade — campione più ampio) ma DD alto
- [[Ny Reversal]] — 🔬 PF1.42 su 1h ma solo 20 trade, troppo pochi per giudicare
- [[Judas Swing]] — 🔴 negativo su entrambi i TF testati (PF0.74-0.77)

## ❓ Mai tracciata (1)
Scoperta il 15/07 durante l'audit di fedeltà — la 37ª strategia dell'EA,
mancava da questo indice. Vedi [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]].

- [[Elliott]] — nessun dato ancora raccolto, non è nel motore sito

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Principi]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]
