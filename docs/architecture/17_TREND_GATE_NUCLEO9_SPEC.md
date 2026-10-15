# 17. TREND_GATE + Nucleo 9 — specifica per l'implementazione MQL5

Evidence labels come da [README](README.md). Questo documento è **Proposed**
nella sua interezza: descrive un'architettura validata solo in un prototipo
Python (`server/research_scripts/trend_gate_core.py`, `institutional_core_test.py`),
mai eseguita nel vero MT5 Strategy Tester. I numeri citati sono un'ipotesi da
verificare, non una garanzia.

## 0. Stato dei dati — leggere prima di tutto

I risultati citati sotto vengono da un motore Python che riusa dati storici
XAUUSD **1d** (Yahoo, ~10 anni disponibili, nessun problema di finestra corta
su questo timeframe). Il Nucleo 9 descritto qui è quindi **dati-solido**: non
dipende dal fetch storico Dukascopy intraday ancora in corso.

**Esplicitamente ESCLUSI da questa spec** perché dipendono da dati 1h/4h non
ancora confermati sullo storico pieno:
- `LONDON_BO` standalone sotto TREND_GATE (4h, PF 4.08/20 trade nel test Python)
- `OTE_CONT` Short-Only, state machine sperimentale (1h, PF 2.11/23 trade)

Questi due vanno aggiunti in un secondo tempo, dopo la riconferma sui dati
Dukascopy pluriennali (`GET /api/dukascopy_status` sul servizio Render,
`ready_for_intraday_reconfirm: true` quando pronto).

## 1. Cosa esiste già in MQL5 (non va reinventato)

| Componente | File | Stato |
|---|---|---|
| Structure engine (trend/BOS/CHoCH, per-TF, refresh a chiusura barra) | `NXS_Structure.mqh` | **Observed**, in uso |
| Modello Istituzionale (fusione segnali per direzione, peso decrescente per famiglia correlata) | `NXS_InstitutionalCore.mqh` | **Observed**, `InpUseInstitutionalCore` oggi OFF di default |
| Market Context (6 componenti per il tier: structTrend/bosDir/htfBias/sweepDir/zoneDir/reactionDir) | `NXS_MarketContext.mqh` | **Observed** |
| `rect_engine` (rilevatore di range/rottura a box N barre) | — | **Non esiste**, va scritto da zero |

Punto importante: il prototipo Python usa un tier ridotto a 3 componenti
(structTrend/htfBias/sweepDir) perché non ha accesso a bosDir/zoneDir/
reactionDir. **La vera implementazione MQL5 ha già tutti e 6** via `g_ctx` —
va usato `_nxs_inst_tier()` così com'è, senza la riduzione che il Python ha
dovuto fare per limiti propri. Il vero MQL5 può quindi essere più preciso di
quanto misurato in Python, non meno.

## 2. Nucleo 9 — le strategie esatte

### 2.1 Gruppo BUY-only (5) — nessun SELL mai eseguito

| Strategia | Score reale MQL5 | Fonte | Implementazione MQL5 |
|---|---|---|---|
| `SAR` | 60.0 | `NXS_Strategies.mqh:259/261` | ✅ esiste |
| `BREAKOUT_ACC` | 68.0 | `NXS_Strategies.mqh:~445/447` | ✅ esiste |
| `LIQ_VOID` | 73.0 | `NXS_Strategies_Institutional.mqh` (`NXS_Strat_LiquidityVoid`) | ✅ esiste |
| `SCALP_EMA` | — | — | ❌ **NON esiste in MQL5** — solo Python/research |
| `SCALP_RANGE_BRK` | — | — | ❌ **NON esiste in MQL5** — solo Python/research |

**Gap da colmare prima dell'implementazione**: `SCALP_EMA` e
`SCALP_RANGE_BRK` sono `RESEARCH_ONLY` nel registro canonico
(`contracts/strategy-registry.json`, `live_implementation: false`) — non
hanno mai avuto una controparte MQL5. Vanno implementate da zero in MQL5
prima di poter far parte del nucleo reale, oppure il nucleo va scoperto a 3
(SAR/BREAKOUT_ACC/LIQ_VOID) come primo passo. Logica di riferimento per la
riscrittura: `server/backtest.py::sig_scalp_ema`/`sig_scalp_range_brk`.

### 2.2 Gruppo bidirezionale (4) — contribuiscono in entrambe le direzioni

| Strategia | Score reale MQL5 | Fonte |
|---|---|---|
| `TSI` | 66.0 | `NXS_Strategies.mqh:331/333` |
| `SH_BMS_RTO` | 74.0 | `NXS_Strategies_SMC.mqh` (`NXS_SHBMS_UpdateSide`) |
| `FVG_CONT` | 70.0 | `NXS_Strategies.mqh:416/418` |
| `LIQ_SWEEP` | 72.0 | `NXS_Strategies.mqh:388/390` |

Tutte e 4 hanno già implementazione MQL5 completa — nessun gap.

### 2.3 Classificazione famiglia (per il peso di conviction, già in `_nxs_inst_family`)

`SAR`/`BREAKOUT_ACC`/`SCALP_EMA` → `MOMENTUM` · `LIQ_VOID`/`FVG_CONT` →
`IMBALANCE` · `SCALP_RANGE_BRK` → `MEAN_REVERSION` · `SH_BMS_RTO` →
`STRUCTURE` · `LIQ_SWEEP` → `LIQUIDITY` · `TSI` → `OTHER` (nessuna parola
chiave in `_nxs_inst_family` la intercetta — verificare se sia il
comportamento voluto o se vada aggiunta esplicitamente).

## 3. `rect_engine` — nuovo modulo, specifica

```
Input:  N = 20 barre (chiuse, non la corrente)
        confirm_body_atr = 0.3

Per ogni barra i chiusa:
  box_hi = max(high) delle N barre precedenti (i-N .. i-1)
  box_lo = min(low)  delle N barre precedenti
  body   = |close[i] - open[i]|

  se close[i] > box_hi E body >= confirm_body_atr * ATR[i]:
      stato = BROKEN_UP
  altrimenti se close[i] < box_lo E body >= confirm_body_atr * ATR[i]:
      stato = BROKEN_DOWN
  altrimenti:
      stato = RANGING
```

Nessun look-ahead (il box usa solo barre già chiuse prima di quella
corrente). Stesso principio di conferma già usato da `LONDON_BO` (niente
breakout a tocco marginale).

Verificato in Python: il Range Fade naive ai bordi del box (comprare/vendere
sul wick oltre il bordo) è **dannoso** (PF 0.66 isolato) — NON implementarlo,
questa spec copre solo il gate di trend (Fase 2 "Trend Pulito").

## 4. Integrazione: TREND_GATE sopra il Modello Istituzionale

Punto di innesto: `NEXUS_EA_v2.mq5`, ramo `InpUseInstitutionalCore` (dove
oggi c'è `if(dec.valid && NXS_Inst_OpenPositionsInDir(dec.dir) == 0 && ...)`).

Aggiungere una condizione ulteriore, PRIMA di aprire:

```
SNXS_RectState rect = NXS_RectEngine_Update(g_sym, tf_nucleo);  // nuovo

bool trendGateOk =
    (rect.state == BROKEN_UP   && dec.dir == DIR_BUY) ||
    (rect.state == BROKEN_DOWN && dec.dir == DIR_SELL);

if(dec.valid && trendGateOk && NXS_Inst_OpenPositionsInDir(dec.dir) == 0
   && !NXS_Prot_EntryBlocked() && NXS_SpreadOK()){
    // ... apertura esistente, invariata
}
```

Nessuna altra modifica a `NXS_Institutional_Decide()` — la conviction, i
pesi di famiglia, `InpInstMinConviction=60`/`InpInstBaseSL=2.0`/
`InpInstBaseTP=4.0` restano esattamente come sono oggi (default reali, non
il proxy Python).

## 5. Filtro BUY-only per il gruppo 2.1

`NXS_Institutional_Decide()` raccoglie tutti i segnali senza distinzione.
Per replicare `direction_lock=BUY` sulle 5 strategie del gruppo 2.1, filtrare
PRIMA dell'aggregazione (in `NXS_CollectAllSignals()` o subito dopo): se
`stratName` è nel gruppo BUY-only e `dir == DIR_SELL`, scartare il segnale
(`dir = DIR_NONE`) prima che entri nel calcolo di conviction — non dopo.

## 6. Cosa NON è coperto da questa spec

- News Filter (`NXS_NewsFilter.mqh`) — esiste, non integrato qui.
- `NXS_SMCReactionOK` (conferma di reazione sui livelli) — esiste
  (`NXS_Reaction.mqh`), oggi collegato solo a ORDER_BLOCK/OB_MIT, non
  incluso nel Nucleo 9.
- Range/Sessione (Gruppi A/B della sperimentazione di oggi) — nessuno dei
  due ha prodotto un risultato solido, non fanno parte di questa spec.
- LONDON_BO e OTE_CONT Short-Only — vedi §0, in attesa di dati.

## 7. Prima di eseguire in demo/live

- Validare su MT5 Strategy Tester con tick reali — i numeri Python (PF 2.28,
  39 trade su ~10 anni 1d) sono un'ipotesi, non una garanzia in esecuzione
  reale (spread variabile, slippage, modello "every tick").
- Implementare `SCALP_EMA`/`SCALP_RANGE_BRK` in MQL5 (§2.1) o partire dal
  nucleo a 3 già completo.
- `rect_engine` da scrivere e testare in isolamento prima di collegarlo al
  Modello Istituzionale.
