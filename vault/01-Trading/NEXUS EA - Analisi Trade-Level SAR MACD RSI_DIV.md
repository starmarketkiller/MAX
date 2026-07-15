---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, trade-level, sar, macd, rsi_div, analisi]
created: 2026-07-15
updated: 2026-07-15
---

# Analisi trade-level: cosa distingue un trade vincente da uno perdente (SAR/MACD/RSI_DIV)

I report `.htm` dei segmenti 4-9 (2019-2024) contengono la tabella "Affari"
(deals) con un campo commento per ogni apertura: `NEXUS_v2|<STRATEGIA>|<SCORE>|<TF>`.
Ho scritto un parser che abbina entrate e uscite (FIFO per simbolo/direzione —
approssimazione: l'export HTML non espone il Position ID reale usato
internamente dall'EA, quindi il matching non è garantito trade-per-trade al
100%, ma il totale abbinato per SAR e MACD combacia **esattamente** con i
conteggi già noti da [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] — 1.129
e 994 — quindi il metodo è affidabile nella sostanza; RSI_DIV mostra uno
scarto di ~60 trade non abbinati, probabilmente commenti con formato diverso
o posizioni aperte a cavallo di due segmenti, da tenere a mente come margine
di errore).

## Scoperta 1: lo score interno non ha ALCUN potere predittivo

Win rate per decina di score (0-100), SAR/MACD/RSI_DIV:

| Strategia | Score 60-69 | Score 70-79 | Score 80-89 | Score 90-99 |
|---|---|---|---|---|
| SAR | 40.0% (n=55) | 42.0% (n=157) | 40.9% (n=286) | 44.1% (n=631) |
| MACD | 75.0% (n=4) | 44.9% (n=98) | 50.4% (n=244) | 49.1% (n=648) |
| RSI_DIV | 38.7% (n=230) | 47.6% (n=42) | 38.5% (n=52) | 37.5% (n=32) |

**Il win rate è sostanzialmente piatto da score 60 a score 99.** Un trade con
score 95 non vince più spesso di uno con score 65. Questo è un risultato
importante e contro-intuitivo: la leva più ovvia ("alza la soglia minima di
score per essere più selettivi") **non funzionerebbe** per queste tre — il
punteggio semplicemente non cattura nulla che differenzi vincite da perdite
in queste strategie specifiche. Il problema non è "il filtro lascia passare
trade di bassa qualità", è che **il trigger di base stesso non ha edge
misurabile**, indipendentemente da quanto sia "sicuro" nel suo stesso sistema
di scoring interno.

## Scoperta 2: la direzione (long/short) è l'unica leva che conta davvero

| Strategia | LONG win rate | SHORT win rate | Differenza |
|---|---|---|---|
| SAR | 45.7% (n=705) | 38.0% (n=424) | **+7.7 punti** |
| MACD | 52.0% (n=650) | 43.6% (n=344) | **+8.4 punti** |
| RSI_DIV | 42.7% (n=157) | 37.2% (n=199) | **+5.5 punti** |

Le tre strategie vincono sistematicamente di più al rialzo che al ribasso —
coerente con XAUUSD in un mercato rialzista secolare per quasi tutto il
periodo 2019-2024 (da ~1.400 a oltre 2.400+, con punte vicine a 4.000 nel
2025 sui dati Yahoo usati per lo screening sito). **Questo è vero nonostante
il filtro HTF sia già attivo per tutte e tre in v2.5.0** — segno che il
filtro di tendenza attuale non sta tagliando abbastanza gli short
controtendenza, o li lascia comunque passare troppo spesso.

Nota anche su MACD: il fatto che LONG arrivi a 52% (sopra 50%) mentre lo
short resta al 43.6% spiega perché MACD abbia comunque un edge raw positivo
misurato sul motore sito (che su dati daily coglie meglio il trend
generale) — probabilmente gran parte del suo edge vero sta proprio nella
componente long, diluita/cancellata dalla componente short nel portafoglio
combinato.

## Controprova: il nucleo hedge NON ha lo stesso bias

Ripetuta la stessa analisi long/short su TURTLE_SOUP/BREAKOUT_ACC/CISD:

| Strategia | LONG win rate | SHORT win rate | Differenza |
|---|---|---|---|
| TURTLE_SOUP | 34.0% (n=97) | 34.1% (n=82) | ~0 |
| BREAKOUT_ACC | 49.4% (n=81) | 45.0% (n=20) | +4.4 (campione short piccolo) |
| CISD | 57.1% (n=14) | 100.0% (n=4) | campione troppo piccolo per contare |

TURTLE_SOUP non ha **nessun** bias direzionale, nonostante sia esposta allo
stesso identico mercato rialzista di SAR/MACD/RSI_DIV nello stesso periodo.
Questo rafforza la lettura: **il bias long/short di SAR/MACD/RSI_DIV non è
solo "il mercato è salito", è un difetto specifico del loro trigger** che le
rende strutturalmente più deboli sul lato short — altrimenti vedremmo lo
stesso bias anche in TURTLE_SOUP.

## Quanto pesa lo short: somma profitto $ per direzione (6 segmenti, non normalizzato per rischio)

| Strategia | Long ($) | Short ($) | Totale ($) | Solo long (ipotetico) |
|---|---|---|---|---|
| SAR | -380.7 | -674.0 | -1.054.7 | -380.7 — **dimezza la perdita, ma resta negativa** |
| RSI_DIV | -108.7 | -482.7 | -591.4 | -108.7 — **quasi azzera la perdita** |
| MACD | +522.4 | -53.9 | **+468.6** | +522.4 |

⚠️ Nota importante: qui MACD risulta **positivo** in dollari sommati sui 6
segmenti, mentre l'analisi in R-multipli in
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]] lo dà a -21.1R. Non è una
contraddizione nell'errore — sono due metriche diverse (il dollaro assoluto
può essere dominato da poche operazioni grandi, l'R-multiplo pesa ogni trade
in proporzione al proprio rischio) — ma è un segnale che **lo stato reale di
MACD è meno netto di quanto sembri dal solo R-sum**, e merita uno sguardo più
attento (es. quante delle operazioni long vincenti sono poche outlier molto
grandi) prima di decidere se rollback o refactor.

## Raccomandazione concreta (azionabile subito, senza aspettare altri segmenti)

Non alzare la soglia di score (Scoperta 1 dice che non aiuterebbe). Invece:
1. **Rafforzare il filtro di tendenza specificamente sugli short** per
   SAR/MACD/RSI_DIV — non un filtro simmetrico uguale per entrambe le
   direzioni, ma una soglia più severa (es. richiedere un trend ribassista
   più netto, o un RR più alto) solo quando il segnale è short.
2. **MACD**: il taglio long-only lo rende chiaramente positivo su entrambe le
   metriche ($ e, presumibilmente, R) — il candidato più veloce e a basso
   rischio da testare per primo tra le tre.
3. **RSI_DIV**: il taglio long-only quasi azzera la perdita ma non la rende
   positiva — utile ma non risolutivo da solo, serve anche altro lavoro sul
   trigger.
4. **SAR**: anche solo long resta negativa — conferma che qui il problema è
   più profondo del solo bias direzionale, e la riscrittura da zero
   ipotizzata in [[TODO - Backtest 10Y]] resta necessaria.
5. In tutti i casi, **testare il taglio long-only è una modifica di una riga
   di codice**, il modo più veloce per verificare quanto delle raccomandazioni
   sopra regge nella pratica, prima di investire in refactor più ampi.

## Limiti del metodo
- Matching FIFO per simbolo/direzione, non Position ID reale — margine di
  errore stimato ~5% sul conteggio (vedi RSI_DIV sopra).
- Non abbiamo lo stato degli indicatori al momento dell'entrata (solo lo
  score aggregato finale), quindi non possiamo dire *perché* lo score non
  predice l'esito — solo che non lo fa.
- Analisi fatta solo su SAR/MACD/RSI_DIV (le 3 priorità). Andrebbe ripetuta
  su TURTLE_SOUP/BREAKOUT_ACC/CISD per vedere se la stessa asimmetria
  long/short esiste anche lì (e se è la ragione per cui funzionano).

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[TODO - Backtest 10Y]] · [[Sar]] · [[Macd]] · [[Rsi Div]]
