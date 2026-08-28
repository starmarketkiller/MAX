---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, pine-script, tradingview, mql5, sar, ema-pullback]
created: 2026-08-28
updated: 2026-08-28
---

# NEXUS EA — Sei strategie portate da script Pine Script TradingView pubblici (28/08)

## Perché

Backtest reale MT5 di stanotte: **SAR (PF0.92, netto -$118.95) ed
EMA_PULLBACK (PF0.55, netto -$170.48) sono negative** sul motore vero, a
tick reali, indipendentemente dal rischio (vedi nota SAR/EMA_PULLBACK di
stanotte). L'utente ha condiviso 6 script Pine Script pubblici trovati su
TradingView, chiedendo di provarli come possibili sostituti/aggiunte.
Prima di scartarli, verificato che non fossero vittime dello stesso
fenomeno di backtest-ottimistico già diagnosticato su SAR/EMA_PULLBACK
(vedi sotto, "repaint").

## Il controllo repaint (prima di portare qualunque script)

Uno degli script (Ichimoku+HullMA+MACD) è stato scartato di getto per una
nota di rilascio 2016 che ammetteva repaint ("set SL low to reduce
repaint"). Verifica più attenta: la revisione **2020** dello stesso script
corregge il problema (`barmerge.lookahead_off` su ogni `security()`,
commissione+slippage aggiunti) — riabilitato dopo la correzione.
**Lezione**: controllare sempre `barmerge.lookahead_off` nelle chiamate
`security()` prima di scartare o accettare uno script per repaint, non
fidarsi della sola nota di rilascio più vecchia trovata.

## Le 6 strategie portate (tutte disattivate di default, mai verificate su MT5)

Tutte seguono lo stesso trattamento cauto: `Inp*=false`, tier di rischio
0.5%, registrate nel registro canonico (`contracts/generate_registry.py`),
in attesa di backtest isolato reale prima di qualunque attivazione.

| Selector | Nome | TF | Meccanismo | Novità vs strategie esistenti |
|---|---|---|---|---|
| 43 | BAR_UPDN | M15 | Barra verde+apre sopra chiusura precedente (price-action puro, nessun indicatore) | Nessuna sovrapposizione |
| 44 | PMAX | H1 | SuperTrend ATR-adattivo, stop-and-reverse (ATR(10)×3.0, EMA(10)) | **Candidato mirato a sostituire SAR** — ATR-adattivo invece di step/max fissi del Parabolic SAR classico |
| 45 | MACD_SMA200 | H4 | MACD su SMA (non EMA) + filtro trend SMA200 | Il nostro MACD nativo (K3) è EMA-based |
| 46 | RSI_DIV_PINE | H1 | Divergenza su pivot RSI veri (lbL=1,lbR=3, range 5-60 barre) | Il nostro RSI_DIV nativo usa finestra fissa 8 barre (già forte, PF1.21 reale — questo è un secondo meccanismo da confrontare, non un sostituto) |
| 47 | ICHIMOKU_HULL_MACD | H4 | 5 filtri in AND: Hull MA in salita, trend D1, prezzo vs Hull MA, cloud Ichimoku, MACD-su-Hull-MA | Costruita **Hull MA vera** (NXS_HMAv, WMA di una serie derivata) — non approssimata con EMA. Segnale probabilmente molto raro (5 condizioni simultanee) |
| 48 | 3COMMAS_BOT | H1 | Incrocio EMA21/50 + stop su swing(5)+ATR(14) + target R:R 1:1 | Simile a SAR (incrocio EMA) ma stop/target strutturati invece di ATR generico |

## Nuovi helper riutilizzabili aggiunti

- `NXS_SMAv(period, tf, shift)` — media mobile semplice per-TF, stesso
  pattern cache di `NXS_EMAv`.
- `NXS_WMAv(period, tf, shift)` — media mobile ponderata per-TF.
- `NXS_HMAv(period, tf, shift)` — Hull MA vera: `WMA(2×WMA(n/2)-WMA(n),
  round(sqrt(n)))`, calcolata a mano sulla serie derivata (non esiste un
  indicatore nativo MT5 per l'Hull MA).

## Semplificazioni dichiarate (onestà, non fedeltà cieca)

- **ICHIMOKU_HULL_MACD**: la signal line del MACD-su-Hull-MA
  (`hma(MACD,9)` nell'originale) è approssimata con una media semplice
  sulle ultime `round(sqrt(9))=3` barre, per non annidare una seconda Hull
  MA dentro la prima (costo di calcolo altrimenti eccessivo per un
  segnale già probabilmente rarissimo).
- **3COMMAS_BOT**: replicata solo la variante EMA/EMA (default script);
  le altre opzioni di MA (HEMA/SMA/HMA/WMA/DEMA/VWMA/VWAP/T3)
  dell'originale non sono state portate.

## Prossimo passo

Backtest isolati MT5 a tick reali per ciascuna (stesso protocollo di
stanotte: `InpStrategySelector` dedicato, 10 mesi, $1000 USD) — priorità a
**PMAX** (candidato diretto a sostituire SAR). Il primo test PMax è in
corso mentre questa nota viene scritta.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Piramidare, Debug Completo e Verdetto sul Portafoglio (28-08)]]
