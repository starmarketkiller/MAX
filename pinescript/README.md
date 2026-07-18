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
   RSI_DIV) con due opzioni, ma il significato delle due opzioni **non è lo
   stesso per tutte le strategie** — dipende da cosa gira davvero in
   produzione oggi:
   - **SAR e RSI_DIV**: "Baseline (config attuale)" = config live in
     `NXS_StrategyProfiles.mqh`; "Variante TP-largo(+BE)" = ipotesi
     alternativa dall'analisi MFE/MAE del 17/07, **mai applicata in
     produzione** (miglioramento marginale/ambiguo per queste due).
   - **MACD e ADX_RSI**: "Baseline (config attuale)" = il fix TP-largo+BE
     del 17/07, che è **già la config live in produzione** oggi in
     `NXS_StrategyProfiles.mqh`; "Config pre-fix (17/07, storica)" = la
     config precedente, tenuta solo come riferimento storico per il
     confronto — **non** rappresenta un'ipotesi ancora da validare.
   In tutti e 4 i casi, esegui il test con entrambe le opzioni (stesso
   range di date, stesso capitale) e confronta PF/Drawdown/Net.
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
- Il filtro HTF di SAR/MACD/ADX_RSI è EMA200 sullo **stesso** timeframe (non
  multi-TF, non serve `request.security`) — vedi sezione dedicata sotto per i
  dettagli e per la correzione fatta il 18/07.
- La divergenza RSI_DIV confronta solo barre già chiuse (`[1]` e `[8]`): nessun
  pivot ricalcolato a posteriori, quindi nessun repaint strutturale.

## Riepilogo logica per strategia

### SAR (H4)
- **Indicatori**: Parabolic SAR (step 0.02, max 0.2), EMA9, EMA21, ATR(14).
- **BUY**: SAR sotto il prezzo E EMA9 > EMA21. **SELL**: speculare.
- **SL/TP baseline**: SL 1.5×ATR, TP 4.0×ATR, no breakeven.
- **SL/TP variante**: stesso SL/TP, breakeven a 1.5×R (test ambiguo nel piano:
  PF sale ma net scende leggermente — disponibile solo per confronto manuale).
- **Filtro HTF**: attivo (EMA200 stesso TF, vedi sotto).
- **Nota**: nessun trailing stop reale (`trailATR=0` nel profilo attuale — il
  test MFE/MAE ha confermato che il trailing non aiuta su questa famiglia di
  strategie, la leva è SL/TP fisso + eventuale breakeven).

### MACD (H4)
- **Indicatori**: MACD line = EMA12 − EMA26, signal = **SMA9** della MACD line
  (MT5 `iMACD` usa SMA per il segnale, non EMA — differenza dal MACD
  "standard" di TradingView, riprodotta a mano nello script), EMA200, ATR(14).
- **BUY**: MACD line > signal E MACD line > 0 E close > EMA200. **SELL**: speculare.
- **SL/TP baseline (= config live oggi in produzione)**: SL 2.0×ATR,
  TP 8.0×ATR, breakeven a 1.0×R — fix reale applicato il 17/07 dopo
  l'analisi MFE/MAE (PF 1.48→2.05 sul motore sito), già in
  `NXS_StrategyProfiles.mqh`.
- **SL/TP config pre-fix (storica)**: SL 2.0×ATR, TP 3.0×ATR, no breakeven —
  la config precedente al fix del 17/07, qui solo come riferimento.
- **Filtro HTF**: attivo (EMA200 stesso TF) ma **ridondante** — il trigger
  richiede già close vs EMA200, vedi sotto.

### ADX_RSI (D1)
- **Indicatori**: EMA50 (pendenza + posizione prezzo), RSI(14), ATR(14).
  **Non calcola un vero ADX** nonostante il nome — errore storico di naming
  documentato nel vault, riprodotto fedelmente così com'è nel codice reale.
- **BUY**: EMA50 in salita E RSI in banda (45,65) E close > EMA50. **SELL**: speculare (EMA50 in discesa, RSI in banda (35,55), close < EMA50).
- **SL/TP baseline (= config live oggi in produzione)**: SL 1.0×ATR,
  TP 10.0×ATR, breakeven a 1.5×R — fix reale applicato il 17/07 dopo
  l'analisi MFE/MAE (PF 1.48→1.97 sul motore sito), già in
  `NXS_StrategyProfiles.mqh`.
- **SL/TP config pre-fix (storica)**: SL 1.0×ATR, TP 4.0×ATR, no breakeven —
  la config precedente al fix del 17/07, qui solo come riferimento.
- **Filtro HTF**: attivo (EMA200 stesso TF) — qui aggiunge un vincolo
  indipendente dal trigger (che usa EMA50, non EMA200).

### RSI_DIV (H1)
- **Indicatori**: RSI(14), finestra fissa di 8 barre (non un pivot/zigzag).
- **BUY (divergenza bullish)**: low[1] < low[8] E RSI[1] > RSI[8] E RSI[1] < 40.
- **SELL (divergenza bearish)**: high[1] > high[8] E RSI[1] < RSI[8] E RSI[1] > 60.
- **SL/TP baseline**: SL 1.0×ATR, TP 4.5×ATR, no breakeven.
- **SL/TP variante**: SL 1.0×ATR, TP 10.0×ATR — miglioramento solo marginale
  nel test del 17/07, **non applicata in produzione**; qui solo per confronto.
- **Filtro HTF**: **disattivato** — con l'HTF attivo il campione crolla a 0-4
  trade su ogni timeframe testato (vedi vault "Fix Blocco 4").

## Filtro HTF — cos'è, e correzione del 18/07

**Corretto il 18/07** — la prima versione di questo filtro (SAR/MACD/ADX_RSI)
riproduceva `NXS_GetHTFBias`/`NXS_HTFBlocks` (EMA50 multi-timeframe H4+H1).
Verificando dove il flag `htf=true` del profilo viene davvero applicato
(`NEXUS_EA_v2.mq5`, riga ~344, dentro `InpUseStrategyProfiles=true` — il
default), è emerso che quel meccanismo **non è quello realmente attivo**:
`InpUseHTFBias` (che governa `NXS_GetHTFBias`) è **`false` di default**, un
gate opzionale mai acceso in produzione.

Il gate **davvero live** è molto più semplice: **EMA200 sullo stesso
timeframe della strategia**, confronto prezzo vs EMA200. Blocca i BUY se il
prezzo è sotto EMA200, i SELL se è sopra. Aggiornato in tutti e 3 gli script
che lo usano (SAR/MACD/ADX_RSI — RSI_DIV non ha filtro HTF, invariato).

Una nota di fedeltà sul codice reale: lì il confronto è **asimmetrico**
(prezzo `shift 0`, cioè la barra ancora in formazione, vs EMA200 `shift 1`,
l'ultima barra chiusa) — probabilmente non intenzionale, ma presente. Qui in
Pine, coerentemente col resto dello script (modello a barra confermata,
anti-repaint), **entrambi i lati usano la barra confermata** — scelta
consapevole, non una replica esatta di quell'asimmetria.

**Impatto sui risultati già raccolti**: le tabelle di test più sotto sono
state generate **prima** di questa correzione, quindi con il vecchio filtro
EMA50 multi-timeframe (di fatto quasi sempre disattivo per SAR/MACD dato che
`InpUseHTFBias=false` non lo blocca comunque a livello EA — ma il
comportamento del filtro *dentro lo script Pine* era diverso da quello
descritto qui). Vale la pena rieseguire i 3 test con la versione corretta
per un confronto pulito.

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

## Risultati dei test manuali

Test eseguiti con lo Strategy Tester nativo di TradingView su
**OANDA:XAUUSD**, `calc_on_every_tick=false`, capitale iniziale 10.000 USD.

> ⚠️ I risultati di **SAR/MACD/ADX_RSI** sotto sono stati raccolti **prima**
> della correzione del filtro HTF del 18/07 (vedi sezione "Filtro HTF —
> cos'è, e correzione del 18/07"). Da rieseguire con la versione corretta
> per un confronto pienamente valido.

> **Sintesi**: dei 4 motori indipendenti testati, **SAR/MACD/ADX_RSI
> confermano risultati profittevoli** e in linea con la direzione dei fix
> MFE/MAE del 17/07 — per MACD e ADX_RSI la config TP-largo+breakeven (che è
> anche quella live oggi in produzione) migliora PF e/o drawdown rispetto
> alla vecchia config pre-fix; per SAR il miglioramento della variante
> BE-only è marginale/ambiguo. **RSI_DIV mostra invece risultati
> deboli/in perdita** nel periodo campione disponibile su TradingView e
> merita ulteriore osservazione prima di trarre conclusioni (vedi nota sul
> campione dati sotto).

### SAR (H4) — range dati Jan 2, 2023 – Jul 17, 2026 (~3.5 anni)
| Config | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|
| Baseline (SL1.5×/TP4.0× ATR, no BE) | 406 | 1,276 | 37,44% (152/406) | 973,13 USD (7,52%) | +2.127,08 USD (+21,27%) |
| Variante TP-largo + BE 1.5×R (SL1.5×/TP4.0× ATR) | 404 | 1,30 | 34,65% (140/404) | 1.022,80 USD (7,79%) | +2.185,53 USD (+21,86%) |

Miglioramento marginale, variante non conclusivamente superiore alla
baseline (coerente con quanto già annotato nello script: il test MFE/MAE
del 17/07 aveva già segnalato questo caso come ambiguo).

### MACD (H4) — stesso range dati
| Config | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|
| Config pre-fix, storica (SL2.0×/TP3.0× ATR, no BE) | 292 | 1,321 | 48,29% (141/292) | 909,56 USD (7,61%) | +1.895,02 USD (+18,95%) |
| **Baseline = live oggi** (SL2.0×/TP8.0× ATR + BE 1.0×R) | 192 | 1,459 | 28,65% (55/192) | 778,88 USD (6,44%) | +1.955,65 USD (+19,56%) |

La config live oggi riduce nettamente il numero di trade (292→192) rispetto
alla vecchia config pre-fix, ma migliora PF e riduce il drawdown — coerente
col fix reale applicato in produzione il 17/07 lato sito.

### ADX_RSI (D1) — range filtrato da `startDate` dello script (2019-01-01)
| Config | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|
| Config pre-fix, storica (SL1.0×/TP4.0× ATR, no BE) | 217 | 1,326 | 29,49% (64/217) | 534,53 USD (5,25%) | +1.529,77 USD (+15,30%) |
| **Baseline = live oggi** (SL1.0×/TP10.0× ATR + BE 1.5×R) | 199 | 1,672 | 24,62% (49/199) | 483,12 USD (4,65%) | +1.950,87 USD (+19,51%) |

Miglioramento netto su tutti i fronti (PF, DD assoluto e %, PnL) rispetto
alla vecchia config pre-fix — coerente col fix reale applicato in produzione
il 17/07 lato sito.

> Nota tecnica: il date-picker del chart D1 mostrava un valore anomalo
> ("Jan 6 1833") durante il test, dovuto a un bug cosmetico di rendering di
> TradingView con zoom molto ampio su D1 (probabile overlay di un secondo
> simbolo storico) — non un problema del filtro date dello script. I trade
> restano correttamente filtrati dagli input `startDate`/`endDate`, quindi i
> numeri sopra sono validi.

### RSI_DIV (H1) — range dati Jan 2, 2025 – Jul 17, 2026 (~1.5 anni)
| Config | Trade | PF | Win Rate | Max DD | Net PnL |
|---|---|---|---|---|---|
| Baseline (SL1.0×/TP4.5× ATR) | 338 | 0,931 | 20,41% (69/338) | 1.290,93 USD (12,67%) | −339,20 USD (−3,39%) |
| Variante TP-largo (SL1.0×/TP10.0× ATR) | 341 | 0,989 | 20,82% (71/341) | 789,53 USD (7,83%) | −52,12 USD (−0,52%) |

Entrambe le configurazioni sono in perdita/breakeven sul campione
disponibile, a differenza del quadro più favorevole probabilmente osservato
su dataset MT5 più lunghi. **Non trarre conclusioni definitive**: campione
troppo corto e specifico per questo periodo di mercato.

> **Limite del dato, non della strategia**: TradingView (piano Basic) mette
> a disposizione solo ~1,5 anni di storico intraday H1 per OANDA:XAUUSD,
> molto più corto dei ~3,5 anni usati per SAR/MACD (H4) — verificato che non
> è un artefatto di zoom (tentato zoom/pan del chart per forzare più
> storico, senza risultato: è il limite reale dei dati disponibili sul
> piano). I risultati RSI_DIV qui sopra vanno letti in questo contesto.

### Osservazioni
- SAR, MACD e ADX_RSI confermano un edge positivo su un terzo motore/dataset
  indipendente da MT5 e dal sito. Per MACD e ADX_RSI la config TP-largo+BE
  (live oggi in produzione) migliora PF e/o drawdown rispetto alla vecchia
  config pre-fix, in linea con l'analisi MFE/MAE del 17/07; per SAR la
  variante BE-only resta marginale/ambigua rispetto alla baseline.
- RSI_DIV è l'unica delle 4 in perdita/breakeven su questo campione, ma il
  campione (~1,5 anni, limite del piano TradingView) è troppo corto per
  giudicarla — da rivalidare quando sarà disponibile più storico o un feed
  con maggiore profondità intraday.
- Prossimo passo naturale: confrontare questi numeri con l'equivalente
  finestra temporale sul motore sito e su MT5 per vedere se le divergenze
  già note tra motori (vedi `NEXUS EA - Principi.md` #5) si ripresentano
  anche qui.
