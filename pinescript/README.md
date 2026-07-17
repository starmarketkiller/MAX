# NEXUS EA — Pine Script (terzo motore di verifica, TradingView)

Questa cartella contiene 4 strategie NEXUS portate su Pine Script v6, come
**terzo motore di verifica indipendente** da MT5 (l'EA reale) e dal backtest
lab interno (`server/backtest.py`, motore Python su dati Yahoo). Scopo: capire
se il segnale di queste 4 strategie regge anche su un terzo dataset/motore
(dati e matching-engine di TradingView), non sostituire gli altri due.

Strategie incluse — le 4 peggiori del portafoglio sui 6 anni MT5 segmentati
(vedi `vault/01-Trading/NEXUS EA - Backtest 10Y Segmentato - Analisi.md`),
nessuna fonte esterna diretta ancora trovata per loro (sono indicatori
classici, non concetti SMC/ICT):

| File | Strategia | Timeframe | Tipo |
|---|---|---|---|
| `NEXUS_SAR.pine` | SAR | H4 | Trend-following (Parabolic SAR + EMA9/21) |
| `NEXUS_MACD.pine` | MACD | H4 | Trend-following (MACD 12/26/9 + EMA200) |
| `NEXUS_ADX_RSI.pine` | ADX_RSI | D1 | Trend-following (EMA50 + banda RSI — **non usa un vero ADX**, vedi sotto) |
| `NEXUS_RSI_DIV.pine` | RSI_DIV | H1 | Reversal/divergenza (RSI vs prezzo, finestra 8 barre) |

Scope di questo lavoro: solo queste 4 strategie. Nessuna modifica a `MQL5/`
o `server/backtest.py`.

## Come usarle nello Strategy Tester di TradingView

1. Apri un chart **XAUUSD** (o il ticker gold del tuo broker/feed su
   TradingView) sul **timeframe nativo della strategia** (vedi tabella sopra —
   H4 per SAR/MACD, D1 per ADX_RSI, H1 per RSI_DIV). Ogni script mostra un
   avviso a schermo se il chart è su un TF diverso da quello previsto.
2. Apri il **Pine Editor**, incolla il contenuto del file `.pine`, premi
   "Add to chart".
3. Apri il pannello **Strategy Tester** (in basso) per vedere Net Profit,
   Profit Factor, Win Rate, Max Drawdown e la lista trade — le stesse metriche
   usate nelle analisi MT5/sito nel vault, così i numeri sono confrontabili
   direttamente.
4. Ogni script ha un input **"Configurazione SL/TP/BE"** (o "SL/TP" per
   RSI_DIV) con due opzioni:
   - **Baseline (config attuale)** — la config oggi in produzione su MT5.
   - **Variante TP-largo (+ Breakeven dove applicabile)** — la gestione
     alternativa emersa dall'analisi MFE/MAE del 17/07 (vedi
     `vault/01-Trading/NEXUS EA - Gestione Uscita MFE-MAE (17-07).md`).
   Esegui il test con entrambe le opzioni (stesso range di date, stesso
   capitale) e confronta PF/Drawdown/Net — è esattamente il confronto
   baseline-vs-variante richiesto.
5. Range di date di default: 2019-01-01 → oggi, per allinearsi alla finestra
   dei 6 anni "affidabili" usata nel backtest 10Y segmentato MT5. Modificabile
   dagli input in cima allo script.
6. Quantità fissa a 1 contratto per tutte e 4 (non è calibrata sul lot sizing
   MT5): l'obiettivo qui è confrontare PF/Win Rate/Drawdown% (metriche a
   rapporto, insensibili alla size) trade per trade, non riprodurre l'equity
   in $ dell'EA reale. Commissioni e slippage sono a 0 di default — aggiungili
   dalle proprietà della strategia se vuoi un test più realistico.

## Regola anti-repaint (importante, applicata in tutti e 4 gli script)

- `calc_on_every_tick = false` in ogni `strategy()`: le condizioni d'ingresso
  sono valutate sulla **barra chiusa** e l'ordine si riempie all'apertura
  della barra successiva. È lo stesso modello di MQL5, che legge
  SAR/EMA/MACD/RSI con `shift=1` (ultima barra chiusa) e apre a mercato subito
  dopo — mai sulla barra "live"/in formazione.
- Dove serve un dato multi-timeframe (filtro HTF di SAR/MACD/ADX_RSI), la
  chiamata usa `request.security(..., lookahead=barmerge.lookahead_off)` **più
  un offset `[1]`** sul valore richiesto — il pattern standard per evitare che
  il valore dell'ultima barra HTF "in corso" venga riletto retroattivamente
  (il classico repaint del multi-timeframe in Pine).
- La divergenza RSI_DIV confronta solo barre già chiuse (`[1]` e `[8]`): nessun
  pivot ricalcolato a posteriori, quindi nessun repaint strutturale.

## Riepilogo logica per strategia

### SAR (H4)
- **Indicatori**: Parabolic SAR (step 0.02, max 0.2), EMA9, EMA21, ATR(14).
- **BUY**: SAR sotto il prezzo E EMA9 > EMA21. **SELL**: speculare.
- **SL/TP baseline**: SL 1.5×ATR, TP 4.0×ATR, no breakeven.
- **SL/TP variante**: stesso SL/TP, breakeven a 1.5×R (test ambiguo nel piano:
  PF sale ma net scende leggermente — disponibile solo per confronto manuale).
- **Filtro HTF**: attivo (EMA50 H4 + EMA50 H1, vedi sotto).
- **Nota**: nessun trailing stop reale (`trailATR=0` nel profilo attuale — il
  test MFE/MAE ha confermato che il trailing non aiuta su questa famiglia di
  strategie, la leva è SL/TP fisso + eventuale breakeven).

### MACD (H4)
- **Indicatori**: MACD line = EMA12 − EMA26, signal = **SMA9** della MACD line
  (MT5 `iMACD` usa SMA per il segnale, non EMA — differenza dal MACD
  "standard" di TradingView, riprodotta a mano nello script), EMA200, ATR(14).
- **BUY**: MACD line > signal E MACD line > 0 E close > EMA200. **SELL**: speculare.
- **SL/TP baseline**: SL 2.0×ATR, TP 3.0×ATR, no breakeven.
- **SL/TP variante**: SL 2.0×ATR, TP 8.0×ATR, breakeven a 1.0×R — fix reale
  applicato il 17/07 in produzione (PF 1.48→2.05 sul motore sito).
- **Filtro HTF**: attivo.

### ADX_RSI (D1)
- **Indicatori**: EMA50 (pendenza + posizione prezzo), RSI(14), ATR(14).
  **Non calcola un vero ADX** nonostante il nome — errore storico di naming
  documentato nel vault, riprodotto fedelmente così com'è nel codice reale.
- **BUY**: EMA50 in salita E RSI in banda (45,65) E close > EMA50. **SELL**: speculare (EMA50 in discesa, RSI in banda (35,55), close < EMA50).
- **SL/TP baseline**: SL 1.0×ATR, TP 4.0×ATR, no breakeven.
- **SL/TP variante**: SL 1.0×ATR, TP 10.0×ATR, breakeven a 1.5×R — fix reale
  applicato il 17/07 in produzione (PF 1.48→1.97 sul motore sito).
- **Filtro HTF**: attivo.

### RSI_DIV (H1)
- **Indicatori**: RSI(14), finestra fissa di 8 barre (non un pivot/zigzag).
- **BUY (divergenza bullish)**: low[1] < low[8] E RSI[1] > RSI[8] E RSI[1] < 40.
- **SELL (divergenza bearish)**: high[1] > high[8] E RSI[1] < RSI[8] E RSI[1] > 60.
- **SL/TP baseline**: SL 1.0×ATR, TP 4.5×ATR, no breakeven.
- **SL/TP variante**: SL 1.0×ATR, TP 10.0×ATR — miglioramento solo marginale
  nel test del 17/07, **non applicata in produzione**; qui solo per confronto.
- **Filtro HTF**: **disattivato** — con l'HTF attivo il campione crolla a 0-4
  trade su ogni timeframe testato (vedi vault "Fix Blocco 4").

## Filtro HTF — cos'è e semplificazioni note

Riproduce `NXS_GetHTFBias`/`NXS_HTFBlocks` (MQL5): bias rialzista se
close(H4) > EMA50(H4) **e** EMA50(H1) > EMA50(H4); bias ribassista se
l'opposto. Con bias ribassista i BUY sono bloccati, con bias rialzista sono
bloccati i SELL; se il bias è neutro il filtro non blocca nulla.

Semplificazioni rispetto al codice MQL5 (documentate qui per trasparenza, non
nascoste):
- **Non riproduce l'eccezione "reversal vicino a PDH/PDL"**: in MQL5, se il
  prezzo è vicino al massimo/minimo del giorno precedente, un trade
  controtrend è comunque permesso. Qui quell'eccezione è omessa — il filtro
  Pine è quindi leggermente più restrittivo (blocca qualche trade in più
  rispetto a MT5 in quei casi specifici).
- Non riproduce `InpGateMode`/`InpEnableCounterHTFSoft` (gate a livello di
  portafoglio, non applicabili a una singola strategia isolata come questa).

## Gestione uscita comune a tutti e 4

- SL/TP calcolati una sola volta all'apertura del trade, come multiplo
  dell'ATR(14) **al momento dell'ingresso** (non ricalcolato durante la vita
  del trade) — identico a `NXS_DefaultSLTP` in MQL5.
- Breakeven (dove beR > 0): quando il profitto flottante raggiunge `beR × R`
  (R = distanza SL iniziale), lo stop si sposta esattamente al prezzo
  d'ingresso — identico a `NXS_ManageBreakevenAndTrail`.
- **Time-exit a 40 barre**: se né SL né TP vengono toccati entro 40 barre dal
  timeframe della strategia, la posizione viene chiusa a mercato — replica il
  "time-based forced exit" reale di MQL5 (`~40 barre del TF della strategia`),
  che è anche l'orizzonte usato nell'analisi MFE/MAE del vault.
- Nessun trailing stop: tutte e 4 le strategie hanno `trailATR=0` nel profilo
  MQL5 attuale, confermato inefficace dal test MFE/MAE del 17/07.

## Risultati dei test manuali (da compilare)

Spazio per incollare i risultati dello Strategy Tester dopo i test manuali —
un blocco per strategia × configurazione (baseline / variante), stesso range
di date per tutte, per un confronto pulito.

### SAR
| Config | Periodo | Trade | PF | Win Rate | Max DD % | Net |
|---|---|---|---|---|---|---|
| Baseline | | | | | | |
| Variante BE | | | | | | |

### MACD
| Config | Periodo | Trade | PF | Win Rate | Max DD % | Net |
|---|---|---|---|---|---|---|
| Baseline | | | | | | |
| Variante TP+BE | | | | | | |

### ADX_RSI
| Config | Periodo | Trade | PF | Win Rate | Max DD % | Net |
|---|---|---|---|---|---|---|
| Baseline | | | | | | |
| Variante TP+BE | | | | | | |

### RSI_DIV
| Config | Periodo | Trade | PF | Win Rate | Max DD % | Net |
|---|---|---|---|---|---|---|
| Baseline | | | | | | |
| Variante TP-largo | | | | | | |

### Osservazioni
_(da compilare — es. concordanza/divergenza con MT5 e col motore sito, sorprese, anomalie)_
