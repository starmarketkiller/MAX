---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, pyramid, debug, risk, portfolio, mql5]
created: 2026-08-28
updated: 2026-08-28
---

# NEXUS EA — Piramidare: debug completo (3 giri) e verdetto sul portafoglio (28/08)

## Punto di partenza

Richiesta esplicita dell'utente: incrementare le posizioni in trend
("vorrei incrementare le posizioni in trend"). Prima di scrivere codice
nuovo, verificato il repo: **il meccanismo esisteva già**, completo e
passato per un audit di sicurezza interno (`NXS_Pyramiding.mqh`, commenti
`AUD0-ADD-005/006/007`) — aggiunge fino a 3 gambe quando una posizione core
è in profitto ≥1 ATR e la velocity concorda, passa dagli stessi controlli
di rischio delle entrate normali. Era solo spento di default
(`InpEnablePyramid=false`), nonostante fosse già agganciato in `OnTick`.

## Tre giri di debug, stesso identico sintomo

Acceso (`InpEnablePyramid=true`) e testato su Tester MT5 a tick reali
(portafoglio completo, Nov 2025-Ago 2026, $1000 USD): **risultato
byte-per-byte identico al baseline senza pyramid**, tre volte di seguito,
dopo tre fix diversi:

1. **Fix 1** (`InpEnablePyramid=true`): nessun effetto.
2. **Fix 2**: il check richiedeva `vel.state == VEL_BULL` esatto, escludendo
   `VEL_BULL_PB` (pullback dentro un trend comunque in corso) che il resto
   del codice tratta come equivalente. Corretto — nessun effetto.
3. **Fix 3** (causa vera, quasi): il velocity gate è **spento globalmente**
   di default (`InpUseVelocity=false`) — con il gate spento
   `NXS_GetVelocity()` ritorna sempre `VEL_NEUTRAL`, quindi nessun check che
   pretenda BULL/BEAR può mai essere vero, qualunque fosse la sintassi.
   Corretto (il check di direzione si applica solo se il gate è attivo,
   stesso trattamento del gate primario) — **ancora nessun effetto**.

A questo punto, invece di continuare a indovinare, richiesta esplicita
dell'utente: costruire una diagnostica dedicata per vedere ESATTAMENTE
dove il funnel si ferma, non un altro giro alla cieca.

## Diagnostica e causa reale

Contatori temporanei + log mirato (poi rimossi) sul Tester MT5 a tick
reali: **939.234 volte "profitto ≥1 ATR raggiunto", zero gambe aperte**,
tutte bloccate da "lotto derivato dal budget (0.0000) sotto il minimo
broker". `NXS_CalcLot()` calcolava correttamente un budget di rischio
valido (verificato nei log: talvolta 0.01 lotti "a rischio maggiorato",
il meccanismo `InpMaxRiskAtMinLotPct` funzionava) — il problema era DOPO:

```
double half = PositionGetDouble(POSITION_VOLUME) * 0.5;
...
double lots = MathMin(half, budgetLots);
```

Su un conto piccolo ($500-1000) le posizioni normali aprono quasi sempre
al lotto minimo (0.01, per il gate RISK_SIZE già noto — vedi nota "SPREAD
e RISK_SIZE"). "Metà del genitore" è allora **0.005**, che arrotondato
per difetto allo step del broker (0.01) diventa **esattamente zero**.
`MathMin(half, budgetLots)` faceva sempre vincere lo zero, a prescindere
dal budget di rischio reale calcolato correttamente. Fix: "metà del
genitore" non scende mai sotto il lotto minimo tradabile
(`MathMax(half, vmin)`); il budget di rischio resta comunque il tetto
vero tramite `MathMin` con `budgetLots` subito dopo.

**Verificato**: 26 gambe pyramid effettivamente inviate (`result=SENT`) in
un solo mese di tick reali, contro zero nei tre tentativi precedenti.

## Il verdetto sul portafoglio: funziona, ma fa male

Con il meccanismo davvero funzionante, backtest completo (10 mesi tick
reali):

| | Baseline (no pyramid) | Con pyramid (funzionante) |
|---|---|---|
| Trade | 195 | 204 |
| Profit Factor | 1.02 | **0.98** |
| Netto | +$31.68 | **-$28.06** |
| Max DD | $340.69 (34%) | $314.20 |

**Il pyramid, anche implementato correttamente, peggiora il portafoglio.**
Stessa lezione del taglio del rischio di sette giorni fa (Monte Carlo:
tagliare il rischio di SAR/EMA_PULLBACK non ha cambiato la rovina 78%→77,5%):
**la gestione non può aggiustare un'entrata senza abbastanza edge** — anzi,
amplificare l'esposizione su strategie con edge già sottile o negativo
(SAR PF0.92, EMA_PULLBACK PF0.55, misurati stanotte) aggrava le perdite
invece di aggiungere profitto.

**Deciso**: `InpEnablePyramid` riportato a `false` di default. Da
riattivare solo quando il PF aggregato del portafoglio è chiaramente e
stabilmente sopra 1 — non prima.

## Lezione di metodo (per la prossima volta)

Il pattern "il meccanismo sembra giusto ma il risultato è identico al
baseline" ha richiesto TRE fix successivi prima di trovare la causa vera,
e i primi due erano comunque bug reali (non sprecati) ma non quello che
bloccava tutto. La diagnostica dedicata (contatori a ogni gate del
funnel, rimossi a fine indagine) ha risolto in un colpo quello che tre
ipotesi plausibili non avevano trovato — vale la pena costruirla SUBITO
quando un risultato è sospettosamente identico, invece di continuare a
ipotizzare.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - WEEKLY_EXP Entry Raffinato M15 e Trailing Strutturale (26-08)]]
[[NEXUS EA - Sei Strategie da TradingView Pine Script (28-08)]]
