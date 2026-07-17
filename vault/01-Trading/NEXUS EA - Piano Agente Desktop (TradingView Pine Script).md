#nexus #trading #multi-agent #pinescript #todo

# Piano di lavoro — Agente Desktop (TradingView)

**Contesto:** l'agente desktop ha accesso a TradingView E accesso commit/push al repository (diverso dall'agente logico, che è solo analisi senza accesso a GitHub). Questo piano è indipendente dal lavoro MT5/EA in corso — nessuna modifica ai file MQL5, nessuna interferenza con lo sweep in corso.

**Obiettivo:** portare le 4 strategie attualmente sotto indagine (SAR, MACD, ADX_RSI, RSI_DIV) su Pine Script, come **terzo motore indipendente** di verifica — non per sostituire MT5/sito, ma per:
1. Cross-check visivo/indipendente della logica reale (un motore diverso, con un suo modello fill/spread diverso, che conferma o smentisce in modo indipendente).
2. Testare rapidamente la variante "TP allargato + breakeven" contro la config reale attuale, usando lo Strategy Tester nativo di Pine (iterazione più veloce di un sweep MT5 completo).

**Confine esplicito (fuori scope):** nessuna delle altre 33 strategie, nessuna modifica a `MQL5/`, nessuna modifica a `server/backtest.py`. Track parallelo e indipendente.

---

## Nota fondamentale sul timing delle barre (leggere PRIMA di portare la logica)

In MQL5, l'EA legge **sempre la barra appena chiusa** (`shift=1`, mai `shift=0`) per calcolare i segnali — è il pattern standard anti-repaint. In Pine, uno `strategy()` di default (senza `calc_on_every_tick=true`) esegue **una volta per chiusura di barra**, e in quel contesto `close` corrisponde già alla barra appena chiusa — è l'equivalente diretto di `close[1]` in MQL5.

**Quindi:** NON aggiungere `[1]` extra in Pine per "simulare" lo shift MQL5 — userebbe la barra sbagliata (due barre indietro). Lasciare gli input come `close`, `ta.rsi(...)`, ecc. al valore corrente di uno script che valuta a chiusura barra, e **non attivare `calc_on_every_tick`** (altrimenti si introduce repaint e il confronto con MT5 diventa invalido).

C'è una particolarità nel codice MQL5 reale da segnalare (non da "correggere silenziosamente" in Pine — riportarla fedelmente o quantomeno documentarla): il filtro HTF (vedi sotto) confronta il prezzo della barra **in formazione** (`iClose(...,0)`, shift 0) contro un EMA200 cache che invece è aggiornato a `shift 1`. È un'asimmetria reale nel codice attuale, probabilmente non voluta ma presente. In Pine è più naturale implementarlo come barra confermata su entrambi i lati (stessa base della entry) — se lo fate così, annotatelo nel file come scelta consapevole, così quando confrontiamo i PF sappiamo da dove viene un'eventuale piccola differenza.

---

## 1. SAR (K4 — Parabolic SAR)

- **TF effettivo:** H4
- **Indicatori:** Parabolic SAR (step=0.02, max=0.2 — stesso default MQL5 `InpSAR_Step`/`InpSAR_Max`), EMA9, EMA21 (close-based), ATR(14) per sizing, EMA200 per filtro HTF.
- **Logica reale (`NXS_Strat_SAR`, `NXS_Strategies.mqh:197-208`):**
  ```
  price = close (barra chiusa)
  BUY  se sar < price AND ema9 > ema21
  SELL se sar > price AND ema9 < ema21
  ```
- **Filtro HTF (profilo richiede `htf=true`):** scarta il segnale se in controtrend rispetto a EMA200 sullo stesso TF (prezzo sotto EMA200 → niente BUY; sopra → niente SELL).
- **Config reale (baseline, da `NXS_StrategyProfiles.mqh`):** SL = 1.5×ATR(14,H4), TP = 4.0×ATR(14,H4), **nessun breakeven**, nessun trailing.
- **Variante da testare:** allargare il TP (proporre 6.0× e 8.0× ATR come primi due punti) + breakeven a 1.0R. Confrontare PF/WR/DD/n.trade contro la baseline 1.5/4.0 senza BE.

## 2. MACD (K3 — MACD Trend)

- **TF effettivo:** H4
- **Indicatori:** MACD(12,26,9) close-based, EMA200, ATR(14).
- **Logica reale (`NXS_Strat_MACD`, `NXS_Strategies.mqh:183-194`):**
  ```
  price = close (barra chiusa)
  BUY  se macd > macdSignal AND macd > 0 AND price > ema200
  SELL se macd < macdSignal AND macd < 0 AND price < ema200
  ```
- **Filtro HTF:** stesso meccanismo di SAR (profilo `htf=true`), scarta segnali controtrend su EMA200.
- **Config reale (baseline):** SL = 2.0×ATR(14,H4), TP = 8.0×ATR(14,H4), **breakeven a 1.0R**.
- **Variante da testare:** TP ancora più largo (proporre 10.0× e 12.0×), verificare comportamento con BE 1.0R confermato come baseline attuale (non è una novità qui, è già la config reale — l'obiettivo è vedere se un TP ancora più largo migliora ulteriormente PF senza far crollare il win rate).

## 3. ADX_RSI (M1 — ADX/RSI Trend)

- **TF effettivo:** D1
- **Indicatori:** ADX(14), RSI(14), EMA50, EMA200 (per filtro HTF), ATR(14).
- **Filtro di forza trend:** se ADX(14) < 20 → nessun segnale (gate primario, prima di tutto il resto).
- **Logica reale (`NXS_Strat_ADXRSI`, `NXS_Strategies.mqh:144-161`):**
  ```
  trendUp = EMA50 > EMA50[1 barra prima]   (EMA50 in salita)
  BUY  se trendUp  AND RSI in (45,65) AND close > EMA50
  SELL se !trendUp AND RSI in (35,55) AND close < EMA50
  ```
- **Filtro HTF:** stesso meccanismo (profilo `htf=true`), su EMA200 D1.
- **Config reale (baseline):** SL = 1.0×ATR(14,D1), TP = 10.0×ATR(14,D1) — già molto largo — **breakeven a 1.5R**.
- **Variante da testare:** qui il "TP largo" è già la config reale, quindi non è la stessa ipotesi delle altre due. Priorità più bassa: testare sensibilità intorno alla baseline (TP 8×/10×/12×, BE 1.0R/1.5R/2.0R) per capire se 10×/1.5R è davvero l'ottimo o solo un punto locale.

## 4. RSI_DIV (H8 — RSI Divergence)

- **TF effettivo:** H1
- **Indicatori:** RSI(14).
- **Logica reale (`NXS_Strat_RSIDiv`, `NXS_Strategies.mqh:409-426`):** divergenza su 8 barre.
  ```
  l1=low[1], l8=low[8], h1=high[1], h8=high[8]  (indici relativi alla barra chiusa)
  rsi1 = RSI barra chiusa, rsi8 = RSI 8 barre prima
  BUY  (div. bullish) se l1 < l8  AND rsi1 > rsi8 AND rsi1 < 40
  SELL (div. bearish) se h1 > h8  AND rsi1 < rsi8 AND rsi1 > 60
  ```
- **Filtro HTF:** NESSUNO (profilo `htf=false` per questa strategia).
- **Config reale (baseline):** SL = 1.0×ATR(14,H1), TP = 4.5×ATR(14,H1), nessun BE, nessun trailing. Nel codice è annotata come "già la migliore trovata anche col proxy corretto" — quindi priorità più bassa rispetto a SAR/MACD/ADX_RSI (che sono quelle sotto indagine attiva sul test MT5 in corso). Utile comunque come quarto punto di conferma indipendente, non urgente.

---

## Deliverable

Proposta di collocazione nel repo (l'agente desktop ha accesso commit, può pushare direttamente):

```
pinescript/
  NEXUS_SAR.pine
  NEXUS_MACD.pine
  NEXUS_ADXRSI.pine
  NEXUS_RSIDIV.pine
  README.md          <- config usate, risultati Strategy Tester (baseline vs varianti TP/BE), note su eventuali scostamenti rispetto a MT5/sito
```

Ogni `.pine` dovrebbe implementare ENTRAMBE le config (baseline reale + variante TP/BE) come input commutabili (es. `input.bool("Usa variante TP allargato")`), così il confronto si fa nello stesso file senza duplicare lo script.

## Cosa fare con i risultati

I risultati Pine sono un **terzo punto di osservazione indipendente**, non un tie-breaker: TradingView ha un suo modello di fill/spread/slippage diverso sia da MT5 sia dal motore Python del sito. Se Pine conferma la stessa direzione (es. "TP largo + BE migliora PF") aumenta la fiducia; se diverge, non significa che uno dei tre sia "sbagliato" — va segnalato e discusso, non usato per sovrascrivere le conclusioni MT5.

Risultati da riportare (per ciascuna delle 4 strategie, baseline vs variante): PF, win rate, drawdown massimo, numero trade, e un commento libero su eventuali differenze di comportamento rispetto a quanto osservato su MT5/sito.
