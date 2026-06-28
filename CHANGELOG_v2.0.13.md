# NEXUS EA v2.0.13 — AGGRESSIVE + STRATEGY CHAIN

**Data:** Feb 2026
**Linea base:** v2.0.12_GATES_OFF

## Cosa cambia

### 🆕 Strategy Chain & Smart Continuation (P0)
Nuovo modulo `NXS_StrategyChain.mqh`:
- **Smart Continuation**: dopo che un trade chiude in PROFITTO, l'EA riconosce un pullback
  ATR ≥ 0.3 e riapre nella stessa direzione con lotto ridotto (default 0.6×). Solo per
  strategie compatibili (bridges configurabili dal dashboard).
- **Smart Close & Reverse**: quando arriva un segnale opposto con reaction ≥ 75 AND HTF
  concorde, abbassa la soglia di chiusura (default 70 → 55 nel caso forte) per fare
  close+inverti in modo aggressivo. Configurabile via `/api/strategy_chain/config`.
- **Strategy Bridges**: matrice strategia → strategie compatibili per continuazione
  (es. dopo `ADX_RSI` in profitto, `EMA_PULLBACK` o `BREAKOUT_ACC` possono aprire).
- **Max continuazioni**: cap configurabile (default 3) per evitare chain infinite.
- **Extremum tracking**: durante posizione aperta, max/min prezzo viene memorizzato
  per riconoscere il pullback dopo close.

### 🐞 Fix
- **DPT (Daily Profit Target)** disabilitato di default — non blocca più il trading
  per tutta la giornata. Set `InpUseDPT=true` per riattivare.
- **MinScoreReverse** abbassato 75 → 70 (Smart Reverse può abbassare ulteriormente).
- **Strategy name nella close**: ora estratta dal comment del deal (`NEXUS_v2|STRAT|score`),
  prima era vuota → analytics ora distingue per strategia.

### ☁️ Cloud Bridge (P0)
- Nuovo worker Python `nexus_local_worker.py` per controllo MT5 dal cloud
  (compile EA, restart MT5, deploy files, apply template).
- Dashboard `/local-bridge`: monitora il worker + invia comandi.

### 📊 UX
- Empty state Journal migliorato con diagnostica WebRequest whitelist.
- Velocity check nel "Why no trade" nasconde se `UseVelocityGate=false`.

## File modificati / aggiunti

```
MQL5/
├── Experts/NEXUS_EA_v2.mq5                       [MOD]
├── Include/NEXUS_v1/
│   ├── NXS_Inputs.mqh                             [MOD: DPT off, MinScoreReverse 70, chain inputs]
│   ├── NXS_Execution.mqh                          [MOD: Smart Close & Reverse]
│   ├── NXS_StrategyChain.mqh                      [NEW]
└── LocalBridge/
    ├── nexus_local_worker.py                      [NEW]
    └── README_LOCAL_WORKER_IT.md                  [NEW]
```

## Backend nuovo

- `POST /api/local_bridge/enqueue` (JWT) — dashboard accoda comando
- `GET  /api/local_bridge/poll` (X-Nexus-Token) — worker polling
- `POST /api/local_bridge/ack` (X-Nexus-Token) — worker reporta esito
- `POST /api/local_bridge/heartbeat` (X-Nexus-Token) — worker keep-alive
- `GET  /api/local_bridge/status` (JWT) — dashboard fetch status worker
- `GET  /api/strategy_chain/config` (JWT) — dashboard CRUD chain config
- `PUT  /api/strategy_chain/config` (JWT)
- `GET  /api/strategy_chain/config_for_ea` (X-Nexus-Token) — EA polls config

## Installazione

1. **Decomprimi** `NEXUS_v2.0.13_AGGRESSIVE.zip` nella tua cartella MQL5 (sovrascrivi).
2. **Compila** `NEXUS_EA_v2.mq5` in MetaEditor (oppure dal dashboard via Local Bridge).
3. **Restart** MT5 (oppure remove+riattacca EA al chart).
4. **Whitelist** URL backend in MT5 → Strumenti → Opzioni → Expert Advisors.
5. **(Opzionale)** Avvia il worker Python per controllo remoto.

## Default parameters (v2.0.13)

```
InpUseDPT                       = false   (was true → spegne DPT)
InpMinScoreReverse              = 70.0    (was 75.0)
InpChainEnableContinuation      = true
InpChainEnableSmartReverse      = true
InpChainContinuationWindowSec   = 1800    (30 min)
InpChainContinuationLotMult     = 0.6
InpChainMaxContinuations        = 3
```
