---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, exit-management, breakeven, trailing, crt, fvg-cont]
created: 2026-08-12
updated: 2026-08-12
---

# Ottimizzazione uscite strutturali — CRT e FVG_CONT (12/08)

Richiesta esplicita dell'utente: griglia SL/TP × breakeven × trailing su
CRT (volume) e FVG_CONT (drawdown), passi larghi non micro-tuning,
`research_scripts/exit_optimizer_grid.py`. L'utente ha fornito uno script
architetturale di riferimento da adattare.

## Correzioni fatte rispetto allo script di riferimento

1. **Firma del motore**: `run_backtest()` non prende `df`/`params={}` — va
   chiamato con `symbol=/timeframe=/bars=/bar_range=` (fetch dati interno)
   e `atr_sl=/atr_tp=/breakeven_r=/trailing_atr=` come kwargs diretti, già
   esistenti. Non esiste `data_loader.load_dukascopy_data`.
2. **Chiavi risultato vere**: `profit_factor`/`trades`/`max_dd_pct`, non
   `total_trades`/`max_drawdown`.
3. **CRT: il vettore SL/TP è inerte.** Verificato in `_open_position()` /
   `STRATEGY_SLTP_ALWAYS["CRT"] = _crt_sl_tp` prima di lanciare la griglia:
   la SL/TP di CRT è **sempre** quella ancorata al wick/sweep, `atr_sl`/
   `atr_tp` non la toccano mai. Sweepare comunque 3×3 valori avrebbe dato 9
   risultati identici, sprecando tempo macchina — per CRT si sweepano solo
   `breakeven_r × trailing_atr` (6 combinazioni, non 18).
4. **`trailing_atr` ≠ "trailing_stop_R"**: non è un trigger a R (attivato
   dopo 1R come nello script di riferimento) — è una distanza di trailing
   in multipli di ATR, **sempre attiva dalla prima barra** della posizione
   quando >0. Stesso concetto, meccanica diversa — i numeri sotto vanno
   letti con questa semantica.
5. **Dataset locale (2019-2026), non l'endpoint del sito**: CRT a 30m con
   migliaia di trade per finestra avrebbe quasi certamente ripetuto i 502
   già documentati su Render per richieste pesanti a bassa TF (vedi
   [[NEXUS EA - Riverifica via Sito su Storico Esteso 2016-2026 (12-08)]]).
   Il campione locale è già enorme per questo scopo (~4700 trade OOS CRT).
6. **Filtro anti-overfitting mantenuto**: IS pf>1.10 e n>50 prima di
   spendere una chiamata OOS, come nello script originale — corretto e
   utile.

## Risultati — CRT (30m)

Baseline OOS: pf **1.25**, n=4711, dd **36.47%**.

| sl | tp* | be | trail | IS pf/n | OOS pf/n/dd |
|---|---|---|---|---|---|
| 1.5 | 3.0 | 0.0 | 1.0 | 1.54/7307 | 1.34/4921/28.57% |
| 1.5 | 3.0 | 1.0 | 0.0 | 1.43/7447 | 1.11/4979/37.93% |
| 1.5 | 3.0 | **1.0** | **1.0** | **1.58/7631** | **1.38/5101/29.1%** |
| 1.5 | 3.0 | 1.5 | 0.0 | 1.41/7228 | 1.12/4834/40.41% |
| 1.5 | 3.0 | 1.5 | 1.0 | 1.57/7467 | 1.34/5007/31.83% |

(*sl/tp fissati e inerti per CRT, vedi punto 3 sopra)

**Vincitore: breakeven a 1R + trailing 1×ATR insieme.** OOS pf 1.25→1.38,
drawdown 36.47%→29.1% — un miglioramento reale sulla debolezza strutturale
già nota di CRT (stop ancorato al wick, drawdown flottante alto, vedi
[[NEXUS EA - Fase C Recovery Baseline e Rischio Flottante (11-08)]]).
Walk-forward (5 finestre):

- Candidato: 1.21/2542 · 1.38/2560 · 1.58/2521 · 1.33/2588 · 1.38/2510
- Baseline: 1.22/2337 · 1.47/2334 · 1.63/2320 · 1.24/2373 · 1.25/2335

**Lettura onesta**: non è un dominio totale finestra-per-finestra (baseline
vince 3/5, candidato 2/5), ma il candidato è più stabile (min 1.21 contro
un range 1.22-1.63 più ampio del baseline) e il DD aggregato scende in modo
consistente. Coerente con un vero effetto di protezione del capitale, non
un artefatto di una singola finestra.

## Risultati — FVG_CONT (4h)

Baseline OOS: pf **1.29**, n=198, dd **13.48%**.

Il mio script, così come quello di riferimento, sceglieva il candidato con
il **PF OOS più alto senza guardare il drawdown** — lo stesso limite dello
script originale, e in contrasto con l'obiettivo dichiarato per FVG_CONT
("abbattere il drawdown"). Ho quindi verificato separatamente anche i
candidati che migliorano **entrambe** le metriche insieme:

| Profilo | sl | tp | be | OOS pf | OOS n | OOS dd |
|---|---|---|---|---|---|---|
| **Solo-PF** (scelto dallo script) | 1.0 | 4.0 | 0.0 | **1.43** | 196 | 20.91% |
| Dual sl2.0/tp4.0/be1.0 | 2.0 | 4.0 | 1.0 | 1.39 | 174 | 12.27% |
| Dual sl1.5/tp4.0/be1.5 | 1.5 | 4.0 | 1.5 | 1.38 | 189 | 12.58% |
| **Dual sl2.0/tp3.0** (consigliato) | 2.0 | 3.0 | 0.0 | 1.33 | 178 | **12.06%** |

Walk-forward a confronto (5 finestre):

- Baseline: 1.35/95 · 1.21/95 · **0.95**/93 · 1.35/86 · 1.17/103 (1 finestra sotto pareggio)
- Solo-PF (1.0/4.0): 1.86/90 · 1.32/93 · 1.2/94 · 1.29/92 · 1.51/95 (5/5 sopra pareggio, PF aggregato più alto, **ma DD quasi raddoppiato**)
- Dual sl2.0/tp4.0/be1.0: 1.71/83 · 1.06/80 · **0.98**/85 · 1.34/82 · 1.28/86 (1 finestra ancora sotto pareggio)
- Dual sl1.5/tp4.0/be1.5: 1.62/88 · 1.08/89 · **0.83**/94 · 1.5/85 · 1.19/96 (peggio del baseline nella finestra debole)
- **Dual sl2.0/tp3.0**: 1.27/85 · 1.16/81 · **1.04**/82 · 1.37/82 · 1.19/89 (**5/5 sopra pareggio, mai sotto — unico profilo senza finestre perdenti**)

**Conclusione — trade-off reale, non un vincitore unico**:
- Se l'obiettivo è il **PF più alto**: sl=1.0/tp=4.0/be=0 (R:R 4:1, stop
  stretto) — walk-forward molto forte in conteggio finestre vincenti, ma
  drawdown OOS quasi doppio del baseline (20.91% vs 13.48%), coerente con
  uno stop più stretto che produce più stop-out prima dei trade vincenti
  grandi.
- Se l'obiettivo è **abbattere il drawdown senza perdere edge** (l'obiettivo
  dichiarato per FVG_CONT in questo giro): **sl=2.0/tp=3.0/be=0/trail=0** —
  PF OOS 1.29→1.33 (modesto ma reale), drawdown 13.48%→12.06%, e **unica
  combinazione la cui walk-forward non scende mai sotto pareggio** (contro
  1 finestra fallita nel baseline stesso). Meno spettacolare in aggregato,
  più solido come profilo strutturale.

## Raccomandazione

- **CRT**: breakeven a 1R + trailing 1×ATR — miglioramento di DD chiaro e
  coerente con il problema strutturale già noto, buon candidato per il
  porting MQL5.
- **FVG_CONT**: **sl=2.0×ATR / tp=3.0×ATR** (stop più largo, target
  invariato, niente BE/trailing) come primo candidato — coerente con
  l'obiettivo dichiarato di ridurre il drawdown; sl=1.0/tp=4.0 resta
  un'alternativa legittima se si preferisce PF più alto accettando più
  drawdown, da valutare esplicitamente con l'utente prima di sceglierla.

Nessuna delle due modifiche è stata ancora portata in MQL5 — solo
verificata sul motore Python. Prossimo passo naturale: decidere quale
profilo FVG_CONT preferire, poi portare entrambi (CRT + FVG_CONT) nei
profili SL/TP/BE/trailing già esistenti in `NXS_StrategyProfiles.mqh`
(stesso meccanismo usato per gli altri override per-strategia).

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Riverifica Master-Slave Bias sul Motore Vero (12-08)]] ·
[[NEXUS EA - Fase C Recovery Baseline e Rischio Flottante (11-08)]]
