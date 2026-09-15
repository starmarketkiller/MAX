# NEXUS — Broker Cost Model Audit

Prima di qualsiasi nuovo backtest strategico o research thread: verifica se il motore Python (`server/backtest.py`) ha usato spread/commissioni superiori a quelli reali del broker, facendo fallire strategie ai gate di robustezza per costi artificialmente elevati. Nessuna strategia modificata, nessun parametro ottimizzato, nessun gate abbassato.

## 1. Tutti i cost model trovati nel repo

**Un solo modello canonico**: `COST_PRESETS` + `scaled_cost_for_price()` in `server/backtest.py` (righe 36-110), applicato dentro `run_backtest()` (righe ~5109-5119 e ~5253-5259, due engine paths — singola posizione e multi-posizione — identici nella logica di costo). **Tutti** gli 80+ script in `server/research_scripts/` che modellano costi importano `backtest.COST_PRESETS`/`scaled_cost_for_price` — nessuna reimplementazione parallela trovata, nessun secondo motore costi divergente. `server/app.py` non referenzia il cost model direttamente (i default restano spread=0/commission=0/slippage=0, "none", se non passati esplicitamente).

## 2. Old cost model — valori esatti usati

```python
COST_PRESETS = {
    "none":            {"spread_price": 0.00, "commission_r": 0.0, "slippage_price": 0.00},
    "retail_standard": {"spread_price": 2.50, "commission_r": 0.0, "slippage_price": 0.50},
    "ecn":             {"spread_price": 0.90, "commission_r": 0.0, "slippage_price": 0.15},
    "stress":          {"spread_price": 4.00, "commission_r": 0.0, "slippage_price": 1.00},
}
MAX_COST_R_PER_TRADE = 5.0   # tetto per trade, safety net non punitivo
```

| Preset | spread ($ = unità prezzo) | spread (pip, 1 pip=0.10) | commissione/side | commissione round-turn | slippage ($) |
|---|---|---|---|---|---|
| none | 0.00 | 0 | 0 | 0 | 0.00 |
| retail_standard | **2.50** | **25** | 0 | 0 | 0.50 |
| ecn | 0.90 | 9 | 0 | 0 | 0.15 |
| stress | 4.00 | 40 | 0 | 0 | 1.00 |

**Dove vengono sottratti dal PnL** (`run_backtest`, entrambi gli engine path):
```python
spread_r = (spread_price / rd) if spread_price > 0 else 0.0   # rd = risk_dist del trade/gamba
slip_r = 0.0
if slippage_price > 0:
    slip_r = slippage_price / rd                                # sempre (entry, sempre a mercato)
    if reason in ("SL", "TIME", "FLIP"):
        slip_r += slippage_price / rd                            # +1x SOLO su uscite a mercato (mai su TP)
cost_r = min(spread_r + commission_r + slip_r, MAX_COST_R_PER_TRADE)
r_mult_net = r_mult - cost_r
```
`commission_r` è sempre 0 in **ogni** preset — nessuna commissione è mai stata modellata, nemmeno per "ecn" (il commento nel codice lo dichiara esplicitamente: il preset "ecn" **sottostima** il costo reale ECN di quella parte, "risultati un limite superiore ottimistico").

## 3. Audit double-counting / scaling — nessun bug trovato

Controllati esplicitamente tutti i punti richiesti:

| Check | Esito |
|---|---|
| Pip vs point ×10 | **OK** — `spread_price=$2.50` → 25 pip a 1 pip=$0.10, coerente col commento "spread retail 20-50 pip" |
| Spread già incluso in BID/ASK e sottratto di nuovo | **OK** — `_open_position` usa `candles[i]["close"]` (prezzo grezzo unico, mai bid/ask), lo spread è sottratto **una sola volta** a chiusura |
| Commissione round-turn applicata due volte | **N/A** — `commission_r=0` in ogni preset, nessuna doppia applicazione possibile perché non applicata affatto |
| Commissione per-side duplicata come round-turn | **N/A** — stesso motivo |
| Slippage applicato a entry+exit in modo errato | **Verificato corretto**: 1× su ogni trade (entry, sempre a mercato) + 1× aggiuntivo SOLO se uscita SL/TIME/FLIP (mercato) — **mai** su TP (limite, prassi broker reale) — design dichiarato nei commenti, non un bug |
| Tick value / contract size errati | **OK** — motore lavora in R-multipli astratti (`risk_money`/`risk_dist`), non simula lotti/nozionale — nessun tick_value/contract_size da validare in questo motore |

**Prova indipendente di assenza di double-counting**: aggiunto un campo puramente diagnostico (`pnl_gross` per trade, mai esposto prima — vedi §10) e verificato che `gross_profit_factor` ricalcolato da questo campo **coincide esattamente** con un run indipendente a costo zero (preset "none"): BREAKOUT_ACC PF_none=2.39 (run diretto) == gross_profit_factor=2.39 (ricavato dai trade con costi applicati). Se ci fosse stato un doppio conteggio, i due numeri sarebbero divergenti.

**Verdict di questa sezione: nessuno scaling bug, nessun double-counting.** Il problema, se esiste, è nei **valori** dei preset, non nella loro applicazione.

## 4. Dati reali dal broker collegato

Terminale LIVE connesso, conto **DEMO** (`ACCOUNT_TRADE_MODE=0`) — le specifiche di uno strumento CFD su un conto demo replicano quasi sempre quelle del conto reale corrispondente presso lo stesso broker (stessa infrastruttura di pricing), ma è un limite dichiarato, non un conto "reale" in senso stretto.

**Symbol info (GOLD)**:
| Campo | Valore |
|---|---|
| SYMBOL_POINT | 0.01 |
| SYMBOL_DIGITS | 2 |
| SYMBOL_TRADE_TICK_SIZE | 0.01 |
| SYMBOL_TRADE_TICK_VALUE | $1.00 |
| SYMBOL_TRADE_CONTRACT_SIZE | 100 |
| SYMBOL_SWAP_LONG / SHORT | -84.84 / +18.59 |
| Account currency / leverage | EUR / 1:500 |

**Spread — campione temporale reale** (900 campioni, 15 minuti, 2026-09-15 19:33–19:48, sessione NY, `SYMBOL_SPREAD`/bid-ask letti dal vivo ogni secondo — non una singola lettura):

| | punti | $ | pip (1 pip=0.10) |
|---|---|---|---|
| Mediana | 54 | 0.54 | **5.4** |
| p75 | 55 | 0.55 | 5.5 |
| p90 | 55 | 0.55 | 5.5 |
| Max osservato | 58 | 0.58 | 5.8 |
| Min osservato | 51 | 0.51 | 5.1 |

Spread estremamente stabile in questa finestra (51-58 punti) — nessuna coda pesante osservata in questo specifico intervallo. **Limite dichiarato**: 15 minuti in un'unica sessione (NY) non copre variazioni Asia/rollover/news — trattato di conseguenza nei profili di costo (§5).

**Commissioni — da deal history reale del conto** (79 deal storici, `HistorySelect`/`HistoryDealGetDouble`, intero storico disponibile su questo conto): **commission = $0.0000 su tutti i 79 deal, senza eccezioni.** Non stimata: misurata. Swap non-zero osservato su alcuni deal overnight (es. -4.16, -3.33), coerente con SYMBOL_SWAP_LONG/SHORT.

**Slippage**: **non misurabile** dalla sola deal history (logga il prezzo di fill, non il prezzo richiesto all'invio ordine) — dichiarato esplicitamente, non inventato. Nei profili sotto uso una stima esplicita e etichettata come tale (1 pip), non una misura.

## 5. Tre cost profile

| Profilo | spread_price | commission_r | slippage_price | Fonte |
|---|---|---|---|---|
| **OLD_COST_MODEL** | 2.50 | 0.0 | 0.50 | preset `retail_standard` esistente, quello usato per il gate SURVIVAL in `nucleus_cost_reverify_14-08.py` |
| **BROKER_BASELINE** | **0.54** | **0.0** | 0.10 (stima, non misurata) | mediana spread live + commissione misurata da deal history |
| **CONSERVATIVE** (~1.5×) | 0.81 | 0.0 | 0.15 | |
| **STRESS** (~2×) | 1.08 | 0.0 | 0.20 | sopra il max osservato (0.58) — non è una ripetizione del baseline |

## 6-7. Impact test — 3 strategie storiche rappresentative

Selezionate da un run **reale e non modificato** di `nucleus_cost_reverify_14-08.py` (nessun segnale/parametro toccato), GOLD, OOS 60-100%, `bars=110000`:

| Strategia | Ruolo | Cost profile | n | PF (net) | PF (gross) | Net PnL | Gross PnL | Costo totale | Costo/trade | DD% | cost_drag |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **BREAKOUT_ACC** (1d) | positiva | OLD_COST_MODEL | 40 | 2.18 | 2.39 | 2585.40 | 2860.15 | 274.75 | 6.87 | 3.20 | 9.6% |
| | | BROKER_BASELINE | 40 | **2.34** | 2.39 | 2833.67 | 2892.58 | 58.91 | 1.47 | 3.02 | 2.1% |
| | | CONSERVATIVE | 40 | 2.32 | 2.39 | 2799.92 | 2888.17 | 88.25 | 2.21 | 3.04 | 3.1% |
| | | STRESS | 40 | 2.30 | 2.39 | 2766.20 | 2883.78 | 117.58 | 2.94 | 3.07 | 4.1% |
| **EMA_PULLBACK** (1h) | **borderline** | OLD_COST_MODEL | 240 | **0.93 (FAIL)** | 1.40 | -1119.20 | 4795.32 | 5914.52 | 24.64 | 25.80 | 123.3% |
| | | BROKER_BASELINE | 240 | **1.28 (PASS)** | 1.39 | 5023.91 | 6656.41 | 1632.50 | 6.80 | 11.49 | 34.0% |
| | | CONSERVATIVE | 240 | 1.23 (PASS) | 1.39 | 3998.53 | 6358.86 | 2360.33 | 9.83 | 12.40 | 49.2% |
| | | STRESS | 240 | 1.18 (PASS) | 1.39 | 3042.81 | 6077.44 | 3034.63 | 12.64 | 13.31 | 63.3% |
| **THREE_BAR_DELIVERY_BREAK** (4h) | negativa | OLD_COST_MODEL | 28 | 0.66 | 0.82 | -732.87 | -334.10 | 398.77 | 14.24 | 10.83 | -119.4% |
| | | BROKER_BASELINE | 28 | 0.78 | 0.82 | -421.41 | -335.59 | 85.82 | 3.06 | 7.91 | -25.7% |
| | | CONSERVATIVE | 28 | 0.76 | 0.82 | -463.80 | -335.39 | 128.41 | 4.59 | 8.31 | -38.4% |
| | | STRESS | 28 | 0.74 | 0.82 | -506.06 | -335.19 | 170.87 | 6.10 | 8.71 | -51.1% |

**Numero e sequenza dei trade identici in tutti i 4 profili per tutte e 3 le strategie (40/240/28)** — conferma che il cost model è puramente contabile, nessun effetto sul path di simulazione (position sizing scala con l'equity ma non altera segnali/trigger SL-TP).

**Risultato chiave — EMA_PULLBACK**: il verdetto **cambia letteralmente** (FAIL→PASS) passando da OLD_COST_MODEL a BROKER_BASELINE. Il vecchio modello mangiava il 123% del gross edge (più dell'intero vantaggio lordo, rendendo la strategia artificialmente in perdita netta); con i costi realmente osservati sul broker ne mangia il 34%, lasciando un PF netto di 1.28.

Per le altre due, il verdetto **non cambia** (BREAKOUT_ACC resta chiaramente positiva, THREE_BAR_DELIVERY_BREAK resta negativa anche a costo zero — `PF_gross=0.82<1`) — solo l'entità del costo è sovrastimata.

## 8. Audit storico — classificazione

**A. Causal structural research (Thread 1-4, WICK Sweep, Structural Dataset, episode_sweep_link, ecc.)**: **UNAFFECTED**, categoricamente. Questi thread non hanno mai usato `server/backtest.py`/`COST_PRESETS` — girano sul motore MQL5 reale (Strategy Tester, spread/commissione del simbolo broker) o su analisi puramente di eventi strutturali (SWEEP/TRUE_BREAK/RETEST), senza P&L in dollari calcolato dal motore Python. Nessuna invalidazione dovuta a questo audit.

**B. Strategy profitability / robustness / cost-stress backtest** (tutti gli script in `server/research_scripts/` che chiamano `run_backtest` con un preset di costo): popolazione stimata 37 strategie/varianti (nucleo + catalogo esteso), **non tutte ri-testate qui** (esplicitamente richiesto di non farlo automaticamente). Framework di classificazione applicato ai 3 casi verificati, da estendere alle altre quando si deciderà di ri-verificarle:

| Categoria | Criterio | Esempio verificato |
|---|---|---|
| **DEFINITELY_AFFECTED** | Verdetto (PASS/FAIL) cambia tra OLD_COST_MODEL e BROKER_BASELINE | **EMA_PULLBACK** (0.93→1.28) |
| **POTENTIALLY_AFFECTED** | Stesso verdetto ma margine PF ridotto sostanzialmente (es. PF netto <1.3 sotto OLD_COST_MODEL, quindi vicino al punto di flip) — richiede riverifica caso per caso | Non verificato oltre i 3 casi — qualunque strategia del nucleo/catalogo con PF_retail storico nel range ~0.85-1.15 (vedi output parziale di `nucleus_cost_reverify_14-08.py`: es. FVG_MIT_WINDOW PF_none=1.60→PF_retail=0.74, DD 11.86%→49.91% — candidato fortissimo, da riverificare) |
| **UNAFFECTED** | Verdetto invariato con ampio margine in entrambe le direzioni | **BREAKOUT_ACC** (sempre PF>2.0), **THREE_BAR_DELIVERY_BREAK** (sempre PF<1, gia' negativa a costo zero) |

**Nota aggiuntiva, non nuova ma rilevante**: un secondo fattore, già noto e già parzialmente corretto nel codice (`scaled_cost_for_price()`, aggiunto il 16/08), aggrava ulteriormente la sovrastima per i walk-forward su periodi storici a prezzo dell'oro molto più basso (es. 2019, ~$1300 vs ~$2500 di riferimento): un costo fisso in $ tassa proporzionalmente di più le epoche a prezzo basso. `nucleus_cost_reverify_14-08.py` (14/08, precede la fix) usa il preset flat, non scalato — quindi potenzialmente doppiamente affetto per le sue finestre più vecchie. Non ri-verificato qui.

## 9. Verdict

### **COST_MODEL_TOO_CONSERVATIVE**

Nessun bug di scaling, nessun double-counting (§3, dimostrato con verifica indipendente gross/net). Il modello applica i costi correttamente **una volta sola**, in modo matematicamente coerente. Il problema è nei **valori assunti**: `retail_standard` (25 pip) è **~4.6×** lo spread mediano realmente osservato su questo broker (5.4 pip); anche `ecn` (9 pip) resta **~1.7×** troppo alto. La commissione (0 in ogni preset) è invece confermata corretta per questo broker (misurata, non stimata: $0.00 su 79 deal reali). L'effetto pratico è dimostrato concretamente su EMA_PULLBACK: un flip di verdetto FAIL→PASS.

## 10. Nessuna correzione silenziosa

**Nessuna modifica ai valori di `COST_PRESETS`, a nessuna strategia, a nessun gate.** L'unica modifica al codice è **additiva e diagnostica**: un campo `pnl_gross` per trade (già calcolato internamente come `total_gross_pnl`, mai esposto prima) e 4 chiavi aggiuntive nel dizionario di ritorno di `_metrics()` (`gross_pnl`, `gross_profit_factor`, `total_cost`, `avg_cost_per_trade`) — nessun campo esistente toccato, nessun impatto su trade/equity/PF/gate esistenti (verificato via smoke test: stessi identici `trades`/`profit_factor`/`net_pnl` di prima della modifica). Questo report è la documentazione richiesta; l'eventuale correzione dei valori di `COST_PRESETS` (es. aggiungere un preset `broker_baseline`) è una decisione successiva, non presa qui.

**Nessuna delle 37 strategie è stata ri-eseguita automaticamente** oltre ai 3 casi rappresentativi richiesti.

**Commit**: `7547bde` (pushato su `origin/main`) — modifiche: `server/backtest.py` (campi diagnostici additivi), `server/research_scripts/cost_model_audit_impact.py` (nuovo), `results/cost_model_audit/impact_test_results.json` (nuovo), questo report.
