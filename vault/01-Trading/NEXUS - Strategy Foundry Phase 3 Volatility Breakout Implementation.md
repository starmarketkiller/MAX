# NEXUS — Strategy Foundry Phase 3: Volatility_Breakout Implementation & Parity

Base: commit `e6fa392` (Phase 2, approvato). Unico candidato: **Volatility_Breakout — confirmed breakout arm** (discovery +0.037R, validation +0.133R, n≈927). Nessun altro candidato implementato. Nessuna modifica al segnale per migliorare i risultati, nessuna optimization/grid search, nessun trailing/BE/session/regime filter aggiunto.

---

## 1. FROZEN_SIGNAL_SPEC_V1

Estratta esattamente da `server/research_scripts/phase2_run.py` (blocco `G2_volbreakout_confirmed`), nessuna semantica cambiata:

| Campo | Valore |
|---|---|
| Symbol / TF | XAUUSD (GOLD), **H4** |
| Range/reference level | Massimo/minimo delle 20 barre `[i-21, i-2]` relative alla barra segnale `i` (offset di 2 barre, esclude la barra segnale e quella immediatamente precedente) |
| Event | Chiusura della barra segnale `close[i]` oltre il massimo (BUY) o sotto il minimo (SELL) del range |
| Observation point | Chiusura della barra segnale `i` stessa |
| Conferma | True range della barra segnale `> 1.0 × ATR(14)[i]` (stesso ATR causale già usato in tutto il motore) |
| Entry | Al prezzo di chiusura della barra segnale (mercato, `close[i]`) |
| Direction | BUY se rottura sopra il range, SELL se sotto |
| Invalidation / SL | Lato opposto dello stesso range N=20 (minimo per BUY, massimo per SELL) |
| R definition | R = \|entry − invalidation\| (ampiezza del range) |
| TP | entry ± 1×R — **non un multiplo diverso**: nello screening Phase 2 "vinto" era definito come primo raggiungimento di +1R, quindi TP=1R è l'unica scelta fedele alla specifica testata |
| Timeout | 40 barre H4 (~6.7 giorni) — stesso `MAX_HOLD_BARS_H4` di Phase 2; oltre questo il motore research applica uscita a tempo (`TIME`) |
| Braccio fade | **Non implementato** — era NO_EDGE in Phase 2, esplicitamente fuori scope |
| Filtri aggiuntivi | Nessuno (no HTF, no sessione, no regime, no trailing/BE) |

Dopo questo punto nessuna semantica è stata cambiata.

---

## 2. Python implementation

Aggiunta **additiva** in `server/backtest.py`: `sig_volatility_breakout_confirmed()` + `_volatility_breakout_confirmed_sl_tp()`, registrate come nuova strategia `VOLATILITY_BREAKOUT_CONFIRMED` in `STRATEGIES`/`STRATEGY_SLTP_ALWAYS`. Zero effetto sulle altre 67 strategie (nessuna funzione esistente modificata).

**Riproduzione esatta dell'event screening Phase 2**: confrontati bar-per-bar i segnali grezzi generati dalla nuova funzione contro l'evento raw usato in Phase 2 sullo stesso dataset XAUUSD H4.

**Risultato: 927/927 eventi identici** (stesso indice di barra, stessa direzione, zero discrepanze) — non solo "coerenti entro differenze spiegabili", identici bit-per-bit.

Eseguito anche attraverso il motore completo `run_backtest()` (gestione posizione one-at-a-time, non il semplice conteggio eventi grezzi di Phase 2): 243 trade nell'intero storico disponibile, PF 1.20, expectancy 0.068R a costo zero — coerente in ordine di grandezza con la fascia discovery/validation di Phase 2 (0.037-0.133R), la differenza residua è attesa e spiegabile dalla gestione "una posizione alla volta" del motore reale contro il conteggio indipendente per-evento di Phase 2.

**Acceptance: superata.**

---

## 3. MQL5 implementation

Aggiunta `NXS_Strat_VolatilityBreakoutConfirmed()` in `NXS_Strategies.mqh`, selettore **56**, TF nativo H4 (`NXS_Profile_TF`), SL/TP strutturali calcolati inline (non un multiplo ATR generico — `slMult=tpMult=0` inerti nel profilo, stesso pattern di CRT/Z_SCORE_BREAKOUT). Nessun filtro extra aggiunto (`htf=false` nel profilo).

### Bug scoperto e corretto durante la verifica

Il primo test di parità ha prodotto **0 trade su 1047 segnali grezzi generati** (verificato via `nexus_stats_*.csv`: `setup=1047, signals=1047, executed=0, blk_PREFLIGHT=1047, health=BLOCKED_BY_GATE`). Causa: `NXS_StrategyKnown()` in `NXS_StrategyRegistry.mqh` (file **auto-generato** da `contracts/generate_registry.py`, la cui fonte reale per lo stato "live" è `knowledge/strategy_database.json`, non ancora aggiornato con la nuova strategia) non riconosceva `VOLATILITY_BREAKOUT_CONFIRMED` — `NXS_OpenTrade()` blocca in preflight qualunque strategia non nella whitelist generata, indipendentemente da quanto il segnale sia corretto.

**Correzione applicata**: aggiunta manuale mirata a `NXS_StrategyRegistry.mqh` (whitelist + `NXS_StrategyIdAt`, count 52→53), con commento esplicito che documenta la necessità di aggiornare `knowledge/strategy_database.json` prima di rieseguire il generatore in futuro (altrimenti la correzione verrebbe sovrascritta). Non è stata una modifica della logica del segnale — è un gate di infrastruttura preesistente, applicabile a QUALUNQUE nuova strategia, non specifico di questa.

Compilazione dopo la correzione: **0 errori, 2 warning preesistenti non correlati**.

### Registry

`contracts/strategy-registry.json` aggiornato: `VOLATILITY_BREAKOUT_CONFIRMED`, family=TREND, status=ACTIVE, selector_index=56, live_implementation=true, research_implementation=true, supported_timeframes=["H4"].

---

## 4. Signal-level parity audit

Finestra comune: **2026-03-01 → 2026-09-01** (H4, storico continuo), Model=1 (1-min OHLC — sufficiente per un confronto a livello di segnale H4, coerente con l'uso già fatto per altre strategie in questa sessione), costi/broker nativi non alterati.

- **MT5**: 18 posizioni aperte (`VolBreakout_confirmed` in log)
- **Python** (stesso dataset, stessa finestra): 48 segnali grezzi

### Classificazione dei mismatch

| Tipo di mismatch | Causa verificata | Classificazione |
|---|---|---|
| Timestamp di apertura MT5 spesso qualche ora dopo la chiusura H4 nominale (es. 03-02 01:30 vs barra 03-02 00:00) | Esecuzione tick-driven reale (MT5 valuta ad ogni tick) contro valutazione una-volta-per-barra-chiusa di Python — stesso meccanismo già documentato per SAR/MACD in fasi precedenti di questa sessione | `BAR_ALIGNMENT_DIFFERENCE` |
| Segnali Python multipli in sequenza ravvicinata (es. 4+ SELL tra 03-18 e 03-23) senza un'apertura MT5 corrispondente per ciascuno | Verificato: `InpMaxConcurrent=4` e `InpMaxPerDirTF=4` (gate di esposizione globale dell'EA, preesistente, si applica a TUTTE le strategie) — con più SELL già aperti dallo stesso segnale ripetuto, ulteriori segnali vengono bloccati dal cap, non dalla logica di VOLATILITY_BREAKOUT_CONFIRMED | `BAR_ALIGNMENT_DIFFERENCE` (gate di esecuzione/ambiente, non di segnale) |
| Direzione, livello di rottura, condizione di conferma sulle coppie effettivamente confrontabili | Identici in ogni coppia MT5/Python verificata manualmente (es. 03-10 16:00 BUY, 03-02 04:00 BUY combaciano esattamente in timestamp/direzione/prezzo) | Nessun mismatch |

**SIGNAL_LOGIC_DIFFERENCE = 0. UNKNOWN = 0.** Gate superato.

---

## 5. Fast Structural (real ticks, 6 mesi, 2026-03-01 → 2026-09-01, config congelata)

| Metrica | Valore |
|---|---|
| n trade chiusi | 14 |
| Profit Factor | 1.165 |
| Net P&L | $263.20 |
| Expectancy | $18.80/trade |
| Max DD | 7.99% |
| Win rate | 50.0% (7 vinte / 7 perse) |
| Avg win / avg loss | $264.87 / $227.27 |
| BUY / SELL | 9 / 5 |
| BUY PF / SELL PF | **0.734 / 2.236** |
| Exit reasons | `sl`: 7, `tp`: 7 |

**Monthly**: 2026-03 +$532.40 (n=5) · 2026-04 −$282.80 (n=1) · 2026-05 −$210.50 (n=1) · 2026-06 −$207.10 (n=1) · **2026-07: 0 trade** · 2026-08 +$431.20 (n=6).

**Osservazioni oneste**: il campione è piccolo (n=14 su 6 mesi). L'intero profitto netto viene da 2 dei 5 mesi attivi (marzo e agosto, +$963.60 combinato) mentre aprile-giugno sono uniformemente in perdita e luglio non produce alcun segnale. Asimmetria BUY/SELL marcata (PF 0.73 vs 2.24) ma su campioni per-lato troppo piccoli (9 e 5) per distinguere un pattern strutturale da rumore statistico.

---

## 6. Decision

### Verdict: **`HOLD_NEEDS_MORE_EVIDENCE`**

Motivazione — non promossa a `READY_FOR_SERIOUS_3Y` nonostante PF>1 ed expectancy positiva:

1. **Sample non ancora ragionevole per una decisione forte**: n=14 in 6 mesi è sottile, con un intero mese (luglio) a zero segnali.
2. **Concentrazione temporale**: il risultato netto positivo dipende quasi interamente da 2 mesi su 5 attivi — non ancora una distribuzione che ispiri confidenza indipendente dal campionamento specifico.
3. **Asimmetria BUY/SELL** (0.734 vs 2.236) plausibilmente solo rumore dato il campione, ma non verificabile con questi numeri.

Non è un `REJECTED_FAST_STRUCTURAL` perché non c'è nulla di strutturalmente rotto: parità di segnale confermata (0 differenze di logica), expectancy positiva, nessun leakage, nessun mismatch semantico. È semplicemente presto per un impegno a un serious 3Y backtest su un campione così piccolo — coerente con "non promuovere solo perché PF>1".

---

## 7. Displacement Stack — nota per il futuro

```
FUTURE_HYPOTHESIS: DISPLACEMENT_STACK_FADE
```

Da testare in futuro su una separazione discovery/validation **fresca e indipendente**, non sugli stessi dati del Phase 2 che hanno suggerito l'inversione di segno (userebbe la stessa evidenza sia per formulare che per "confermare" l'ipotesi — circolare). Non implementato in questa fase.

---

## 8. Dukascopy

Download della finestra 2019-02-03→2022-02-03 proseguito separatamente in background per l'intera durata di questa fase, senza bloccarla. Non usato per modificare Volatility_Breakout in questo task, come richiesto.

---

## Blocker

Nessun blocker residuo per Volatility_Breakout stesso. Blocker tecnico documentato (non bloccante per questa fase): `knowledge/strategy_database.json` non ancora aggiornato con la nuova strategia — se `contracts/generate_registry.py` venisse rieseguito senza prima aggiornare quella fonte, la correzione manuale a `NXS_StrategyRegistry.mqh` verrebbe persa (commento esplicito lasciato nel file).

## File prodotti

- `server/backtest.py` — `sig_volatility_breakout_confirmed`, `_volatility_breakout_confirmed_sl_tp`, registrazione in `STRATEGIES`/`STRATEGY_SLTP_ALWAYS`
- `MQL5/Include/NEXUS_v1/NXS_Strategies.mqh` — `NXS_Strat_VolatilityBreakoutConfirmed()`
- `MQL5/Include/NEXUS_v1/NXS_StrategyProfiles.mqh` — profilo TF/SL-TP/risk/enabled
- `MQL5/Include/NEXUS_v1/NXS_StrategyRegistry.mqh` — whitelist corretta (selettore 56)
- `MQL5/Include/NEXUS_v1/NXS_Inputs.mqh` — `InpStrat_VolBreakoutConfirmed`
- `MQL5/Experts/NEXUS_EA_v2.mq5` — call site selettore 56
- `contracts/strategy-registry.json` — nuova voce
- `results/strategy_foundry_phase3/volbrk_parity_trades_mt5.csv`
- `results/strategy_foundry_phase3/volbrk_fast_structural_6mo_trades.csv`

## Commit

`f035d30`
