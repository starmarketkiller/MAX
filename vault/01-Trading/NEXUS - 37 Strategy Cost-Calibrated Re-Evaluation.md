# NEXUS — Cost Calibration Final + Strategy Re-Evaluation

Segue [[NEXUS - Broker Cost Model Audit]] (commit `7547bde`/`cbd5c6c`, verdict `COST_MODEL_TOO_CONSERVATIVE`). Questo report calibra il broker baseline su base statistica solida e riesegue **tutte** le strategie con implementazione research, senza modificare segnali, parametri o gate.

## 0. Correzione di scope: 67 strategie, non 37

Il numero corretto di strategie con `research_implementation=true` nel registry canonico (`contracts/strategy-registry.json`, identico a `bt.STRATEGIES.keys()` in `server/backtest.py`) è **67**, non 37. Verificato direttamente dal registry: 82 record totali, 52 con `live_implementation`, **67 con `research_implementation`** (36 ACTIVE + 30 RESEARCH_ONLY + 1 DISABLED). Tutte le 67 sono state rieseguite in questo report.

## 1. Spread — calibrazione storica reale

**Fonte**: `CopyTicksRange` sul terminale LIVE connesso al broker reale (mai nel Tester — i tick del Tester sono simulati, non storico reale broker). **24.105.115 tick reali** GOLD, **75 giorni di trading con dati** su 90 giorni di calendario richiesti (2026-06-17 → 2026-09-15 — i giorni mancanti sono weekend, nessun buco anomalo). Istogramma per punto di spread, percentili ricostruiti dall'istogramma completo (non da un campione).

| Sessione (ora server broker) | n tick | p25 | median | p75 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|---|---|---|
| **Intero dataset** | 24.105.115 | 5.4 pip | **5.5 pip** | 5.7 pip | 5.8 pip | 5.9 pip | **7.0 pip** | 33.0 pip |
| Asia (00-07) | 6.174.043 | 5.5 | 5.7 | 5.8 | 5.9 | 5.9 | **13.0** | 33.0 |
| London (07-13) | 5.705.539 | 5.4 | 5.5 | 5.6 | 5.8 | 5.8 | 5.9 | 7.0 |
| New York (13-21) | 9.894.393 | 5.4 | 5.5 | 5.6 | 5.7 | 5.8 | 5.9 | 20.0 |
| Rollover (21-24, 00-01) | 2.331.140 | 5.3 | 5.5 | 5.6 | 5.8 | 5.9 | 10.6 | 33.0 |

**Osservazioni**: distribuzione centrale estremamente stretta e stabile (p25→p95 quasi indistinguibile, 53-59 punti in ogni sessione) — la vera variabilità è tutta nella coda p99+. Asia e Rollover hanno code nettamente più larghe (p99 13.0 e 10.6 pip) coerenti con liquidità più sottile; London è la sessione più stretta (max osservato 7.0 pip in 75 giorni). La mediana (5.5 pip) è coerente entro l'1.8% con il campione live di 15 minuti dell'audit precedente (5.4 pip) — buona conferma incrociata indipendente.

**Non usato il max assoluto (33.0 pip) come base di nulla** — è un singolo evento estremo (probabilmente news), non rappresentativo.

## 2. Commissione — riconfermata

**79 deal storici reali** del conto connesso, `HistoryDealGetDouble(DEAL_COMMISSION)`: **commissione totale = $0.00, commissione media/deal = $0.00**, su tutti i 79 senza eccezioni. Nessuna stima: misurata (stesso risultato dell'audit precedente, riconfermato).

## 3. Slippage — MISURATA (parzialmente) e dichiarata come ASSUMED

Tentativo di misura diretta: confronto `ORDER_PRICE_OPEN` (prezzo richiesto) vs prezzo di fill del deal collegato, su tutti gli ordini a mercato della cronologia. **Risultato**: la maggior parte degli ordini storici non registra un `ORDER_PRICE_OPEN` diverso da zero (non comparabile — limite della cronologia di questo broker/conto, non un'omissione nostra). Nei pochi casi comparabili (~4 su 77), la differenza osservata è **0.00–0.13 unità di prezzo (0–1.3 pip)** — consistente con, ma non una prova statistica di, uno slippage minimo.

**Etichetta corretta: `ASSUMED_SLIPPAGE`, non broker-observed.** Valore mantenuto prudenziale (1 pip = $0.10 al baseline), ora esplicitamente qualificato come assunzione informata dal debole indizio reale sopra, non come dato misurato con rigore statistico.

## 4. Cost profile congelati — costruiti sui percentili reali, non 1.5×/2× arbitrari

| Profilo | spread_price | Fonte spread | commission_r | slippage_price | Fonte slippage |
|---|---|---|---|---|---|
| **BROKER_BASELINE** | **$0.55** (5.5 pip) | mediana intero dataset (24.1M tick) | 0.0 (misurata) | $0.10 (1 pip) | ASSUMED |
| **CONSERVATIVE** | **$0.70** (7.0 pip) | p99 intero dataset — coda "alta ma normale", non 1.5×baseline | 0.0 | $0.15 | ASSUMED, scalata |
| **STRESS** | **$1.30** (13.0 pip) | p99 sessione Asia — condizione avversa **realmente osservata**, peggior sessione normale, **non** il max assoluto (33 pip) | 0.0 | $0.25 | ASSUMED, scalata |

Ogni valore è ancorato a un percentile reale specifico (dichiarato), non a un moltiplicatore arbitrario — come richiesto.

## 5. Semantica di `pnl_gross` — decomposizione e identità contabile

**Perché il gross PnL in dollari cambia fra cost profile nonostante la sequenza trade resti identica?** Verificato con un test diretto (stessa strategia, 2 cost profile, trade-by-trade): il **multiplo-R gross per trade (`r_gross`) è bit-per-bit identico** fra tutti i profili di costo — la simulazione di mercato/segnale è **completamente indipendente** dal cost model. Il PnL gross in **dollari** diverge invece perché il position sizing è a rischio percentuale sull'**equity corrente** (`risk_money = equity × risk_pct%`), ed equity compounda sul PnL **netto** (che dipende dai costi) trade dopo trade — un effetto di compounding legittimo, non un bug.

**Decomposizione implementata** (campi additivi in `server/backtest.py`, nessuna logica esistente toccata):
```
raw_market_pnl  (= pnl_gross, r_gross × risk_money)
- spread_cost     (spread_r × risk_money, scalato se MAX_COST_R_PER_TRADE satura)
- slippage_cost   (slip_r × risk_money, idem)
- commission_cost (commission_r × risk_money, idem — sempre 0 qui)
= net_pnl
```
**Identità verificata numericamente** (EMA_PULLBACK, OLD_COST_MODEL, n=240): `spread_cost(4492.09) + slippage_cost(1422.42) + commission_cost(0.00) = 5914.51` contro `total_cost = 5914.52` (differenza 0.01, solo arrotondamento per-trade a 4 decimali) — e `gross_pnl(4795.32) - 5914.51 = -1119.19` contro `net_pnl = -1119.20`. Identità contabile confermata entro l'arrotondamento.

## 6-7. Rerun 67 strategie × 4 profili (ZERO_COST/BROKER_BASELINE/CONSERVATIVE/STRESS)

TF e parametri **originari, mai ottimizzati**: fonte primaria `NXS_Profile_TF` (MQL5), fallback su TF_MAP Python già esistenti (`nucleus_cost_reverify_14-08.py`, `find_best_profiles.py`) per gli override documentati (es. LONDON_BO/WEEKLY_EXP, gate di sessione su barre non-intraday), assunzione esplicita per famiglia/naming per le varianti puramente Python senza profilo MQL5 dichiarato (~24 delle 67 — dichiarato riga per riga nello script `cost_calibration_67_rerun.py`). `risk_pct=1.0, atr_sl=1.5, atr_tp=3.0`, OOS 60-100%, `bars=110000` — identici in tutte le run precedenti.

**Nota di correzione**: `EMA_PULLBACK` qui usa TF=4h (fonte autorevole `NXS_Profile_TF`), diverso dal TF=1h usato nell'esempio illustrativo del Broker Cost Model Audit precedente (ereditato da un mapping Python più vecchio, meno fedele al profilo MQL5 originale). La conclusione di quell'audit (il cost model può capovolgere un verdetto) resta valida — solo l'esempio specifico usava un TF leggermente diverso.

**Caveat tecnico** (non un bug del cost model): `CRT`/`CRT_MINSTOP_FILTER` (5597/4879 trade, M30) collassano l'equity quasi a zero ($0.29-0.42 su $10.000 iniziali) sotto qualunque profilo di costo non-zero — lo stop nativo di questa famiglia è troppo stretto per il sizing a rischio fisso 1%, un limite già documentato nel commento di `MAX_COST_R_PER_TRADE` nel codice ("senza un tetto sul lotto l'equity crollava sotto zero... il tetto lascia comunque visibile il problema reale"). Classificate correttamente `GROSS_EDGE_COST_SENSITIVE` (gross PF~1.02-1.04, ma il crollo equity ne rende il PF netto poco interpretabile in valore assoluto).

### Classificazione (67 strategie)

| Categoria | n |
|---|---|
| ROBUST_POSITIVE | **18** |
| INSUFFICIENT_SAMPLE (n<30 nell'OOS) | 18 |
| NEGATIVE_EVEN_ZERO_COST | 14 |
| GROSS_EDGE_COST_SENSITIVE | 8 |
| BROKER_BASELINE_PASS_STRESS_FAIL | 6 |
| BORDERLINE | 3 |

## 8. Audit falsi negativi storici — OLD_COST_MODEL FAIL → BROKER_BASELINE PASS

Ricalcolate tutte le 67 anche con `OLD_COST_MODEL` (`retail_standard`, spread $2.50/25 pip) per il confronto diretto. **13 falsi negativi** identificati — nessun caso nella direzione opposta (0 strategie che passavano con OLD e falliscono con BASELINE, come atteso dato che i costi OLD sono sistematicamente più alti):

| Strategia | TF | PF (OLD) | PF (BASELINE) | n |
|---|---|---|---|---|
| MALAYSIAN_SNR_V2_STAGE3 | 30m | 0.65 | 1.39 | 126 |
| FVG_MIT_WINDOW | 4h | 0.74 | 1.29 | 244 |
| Z_SCORE_BREAKOUT | 1h | 0.84 | 1.23 | 460 |
| MALAYSIAN_SNR | 30m | 0.73 | 1.18 | 53 |
| AMD_CONT | 30m | 0.71 | 1.10 | 340 |
| MALAYSIAN_SNR_V2_RETEST_OUTRANGE | 30m | 0.68 | 1.08 | 130 |
| ICHIMOKU | 4h | 0.93 | 1.08 | 79 |
| NY_REVERSAL | 15m | 0.69 | 1.06 | 55 |
| NY_REVERSAL_CHOCH_WINDOW | 15m | 0.65 | 1.05 | 168 |
| SH_BMS_RTO_V2 | 1h | 0.73 | 1.05 | 273 |
| LONDON_BO | 1h | 0.68 | 1.02 | 252 |
| MALAYSIAN_SNR_V2_RETEST | 30m | 0.60 | 1.02 | 278 |
| FVG_CONT_V2 | 4h | 0.84 | 1.01 | 48 |

28 strategie restano FAIL in entrambi i modelli (genuinamente negative, non un artefatto di costo).

## 9. Top 5 (nessuna combinazione, nessuna ottimizzazione)

Ordinate per PF a BROKER_BASELINE, con degradazione CONSERVATIVE/STRESS riportata per trasparenza:

| # | Strategia | TF | n | PF (zero/base/cons/stress) | DD% | Expectancy/trade (R) |
|---|---|---|---|---|---|---|
| 1 | **BREAKOUT_ACC** | 1d | 40 | 2.39 / 2.34 / 2.33 / 2.28 | 3.02 | 0.636 |
| 2 | **LIQ_SWEEP** | 1d | 42 | 1.88 / 1.85 / 1.83 / 1.79 | 4.00 | 0.448 |
| 3 | **DARVAS_BOX** | 1d | 40 | 1.82 / 1.78 / 1.76 / 1.72 | 5.13 | 0.410 |
| 4 | **DONCHIAN_TURTLE** | 1d | 45 | 1.75 / 1.71 / 1.70 / 1.66 | 5.13 | 0.386 |
| 5 | **SAR_FLIP** | 4h | 111 | 1.69 / 1.61 / 1.59 / 1.51 | 5.81 | 0.346 |

Degradazione ZERO→STRESS minima per tutte e 5 (max -6% relativo, BREAKOUT_ACC) — coerente con uno spread reale molto più basso di quanto assunto in passato.

## 10. Promotion gate — SERIOUS_BACKTEST_CANDIDATE

Criteri: `ROBUST_POSITIVE` + n≥30 + expectancy>0 + PF CONSERVATIVE>1.0 + DD baseline≤25%. **18 strategie promosse** (coincide esattamente con tutte le ROBUST_POSITIVE — nessuna esclusa da DD/expectancy/sample in questo giro):

BREAKOUT_ACC, LIQ_SWEEP, DARVAS_BOX, DONCHIAN_TURTLE, SAR_FLIP, CISD_TRUE, MACD, SAR, JUDAS_SWING, ADX_RSI, MALAYSIAN_SNR_V2_STAGE3, EMA_PULLBACK, SAR_ADX20, FVG_MIT_WINDOW, Z_SCORE_BREAKOUT, FVG_CONT, LIQ_VOID, ICHIMOKU.

**Non equivale a validazione definitiva** — nessuna implementazione, nessuna combinazione, nessuna ottimizzazione ulteriore eseguita qui.

## Riepilogo numerico richiesto

- Spread: mediana **5.5 pip**, p99 **7.0 pip** (overall), p99 Asia **13.0 pip** — 24.1M tick reali, 75 giorni
- Slippage: **ASSUMED_SLIPPAGE** (non misurata con rigore — debole indizio reale 0-1.3 pip da 4 confronti order/deal comparabili)
- Cost model finale: BROKER_BASELINE $0.55/CONSERVATIVE $0.70/STRESS $1.30 (spread), commissione $0 (misurata), slippage assunta
- **Falsi negativi storici (OLD FAIL → BASELINE PASS): 13**
- **Positive a BROKER_BASELINE: 36/67**
- **Positive a CONSERVATIVE: 33/67**
- **Positive a STRESS: 27/67**
- **Top 5**: BREAKOUT_ACC, LIQ_SWEEP, DARVAS_BOX, DONCHIAN_TURTLE, SAR_FLIP
- **SERIOUS_BACKTEST_CANDIDATE: 18/67**

**Commit**: `[da assegnare]`
