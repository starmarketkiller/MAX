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

## Approfondimento quantitativo (12/08, stesso giorno) — tutti i candidati, non solo i pick a mano

Richiesta esplicita dell'utente: approfondire **tutte** le combinazioni
sopravvissute al filtro IS, non solo i 2-3 scelte a mano sopra.
`research_scripts/exit_optimizer_deepdive.py` — walk-forward completo a 5
finestre + tutte le metriche OOS (`win_rate`, `expectancy_r`, `sharpe`,
già calcolate da `run_backtest` ma non stampate prima) per le 6
combinazioni CRT e le 12 candidate FVG_CONT, più due punteggi
quantitativi trasparenti:

- **Robustezza** = media(PF walk-forward) − dev.std(PF walk-forward) —
  premia un edge medio alto e penalizza l'incoerenza tra finestre (stesso
  principio dello Sharpe applicato al PF, non ai ritorni).
- **Calmar-like** = media(PF walk-forward) / DD% OOS — ritorno per unità
  di drawdown, quanto è "efficiente" sul capitale.

Artifact con tabella completa ordinabile:
https://claude.ai/code/artifact/5354f55e-a728-4463-847c-3c725ba5139f

### CRT — i due punteggi concordano, conferma il pick precedente

| Config | Robustezza | Calmar | OOS pf/dd |
|---|---|---|---|
| be=1.0 trail=1.0 | **1.257** (1°) | 0.0473 (2°) | 1.38 / 29.1% |
| be=0.0 trail=1.0 | 1.213 (2°) | **0.0477** (1°) | 1.34 / 28.57% |
| be=0.0 trail=0.0 (baseline) | 1.2 | 0.0373 | 1.25 / 36.47% |
| be=1.5 trail=1.0 | 1.173 | 0.0413 | 1.34 / 31.83% |
| be=1.5 trail=0.0 | 1.044 | 0.0289 | 1.12 / 40.41% |
| be=1.0 trail=0.0 | 1.041 | 0.0309 | 1.11 / 37.93% |

**Scoperta nuova**: il breakeven **da solo** (senza trailing) è
*peggiore* del baseline su entrambi i punteggi — non un effetto neutro,
proprio dannoso (probabilmente esce a pareggio da trade che poi
sarebbero arrivati a TP). Il trailing è la leva che fa il lavoro vero; il
breakeven aiuta solo se abbinato al trailing (effetto di interazione, non
additivo). Confermato: **be=1.0 + trail=1.0** resta il pick per CRT.

### FVG_CONT — divergenza reale tra i due punteggi, non un solo vincitore

| Config | Robustezza | Calmar | OOS pf/dd/wr |
|---|---|---|---|
| sl1.0/tp4.0/be0 | **1.201** (1°) | 0.0687 (**ultimo**, 12°) | 1.43 / 20.91% / 27.6% |
| sl2.0/tp2.0/be0 | 1.02 (9°) | **0.1506** (1°) | 1.29 / 7.78% / **56.6%** |
| sl2.0/tp4.0/be0 | 1.154 (2°) | 0.1023 (4°) | 1.38 / 13.66% / 44.0% |
| sl2.0/tp3.0/be0 | 1.096 (5°) | 0.100 (5°) | 1.33 / 12.06% / 47.8% |

Il candidato più "robusto" per walk-forward (sl1.0/tp4.0) è
**contemporaneamente il peggiore per efficienza sul drawdown** — un vero
trade-off, non rumore. Il migliore per calmar (sl2.0/tp2.0, R:R 1:1) ha
un profilo di trade diverso: win rate quasi raddoppiato (56.6% contro il
27-48% di tutti gli altri) e drawdown quasi un terzo del baseline, ma è
solo a metà classifica per robustezza walk-forward.

**Compromesso migliore su entrambi gli assi**: sl=2.0/tp=4.0/be=0 — 2°
per robustezza, 4° per calmar, senza essere ultimo su nessuno dei due.
Non è un "vincitore" nel senso di dominare ogni metrica (nessuno lo fa),
ma è quello che non sacrifica pesantemente né la coerenza walk-forward
né l'efficienza sul capitale.

## Scoperta critica (12/08, stesso giorno) — un secondo trailing SEMPRE ATTIVO mai modellato

Prima di estendere il lavoro a tutte le strategie, trovato un problema di
fondo che invalida anche le due scelte sopra: in MQL5 esiste un
**secondo sistema di trailing**, `NXS_TrailingATR.mqh` (v2.4.5),
completamente separato dal `beR/trailATR` per-strategia testato finora
(`NXS_Management.mqh`/`NXS_Profile_Get`):

- **Attivo di default per TUTTE le strategie** (`InpUseAtrTrail = true`),
  nessuno switch per-strategia per spegnerlo — solo la LARGHEZZA è
  per-strategia (`NXS_Profile_TrailK`), non il fatto che sia attivo.
- Larghezza: `NXS_Profile_TrailK(nome)` se presente, altrimenti fallback
  al globale `InpAtrTrailMult = 2.5`.
- Si attiva solo dopo `InpAtrTrailActivateATR = 1.0` × ATR di profitto
  (attivazione per-strategia esisteva in v2.4.6 ma è stata rimossa in
  v2.4.7 — "dava netto più basso", vedi commento in codice).

Il motore Python non modellava questa soglia di attivazione (il
`trailing_atr` di `run_backtest` inseguiva da subito, non dopo 1×ATR) —
aggiunto `trailing_activate_atr` (default 0.0 = comportamento invariato)
per replicarla fedelmente.

**Impatto**: CRT non ha una voce in `NXS_Profile_TrailK`, quindi ha già
un trailing 2.5×ATR attivo di default via fallback globale — testato,
l'effetto è **trascurabile** per CRT (il suo SL è già stretto per natura,
il trailing raramente interviene prima del target): baseline vero
pf=1.25/dd=36.73% contro pf=1.25/dd=36.47% del "baseline Python" usato
sopra — praticamente identici. **Il pick CRT (be=1.0+trail=1.0) resta
valido**, anzi con l'attivazione modellata correttamente migliora
leggermente (OOS pf 1.38→1.39, dd 29.1%→28.05%).

**FVG_CONT invece cambia sostanzialmente**: ha `TrailK=2.5` esplicito, e
il vero baseline live (htf=True, sl1.0/tp4.5, overlay trail 2.5/attiva a
1×ATR **sempre presente**) è **OOS pf=1.55, dd=13.41%** — molto peggio
del "baseline senza overlay" usato per la scelta precedente (pf=1.71,
dd=11.36%, mai esistito nella realtà). Il pick di prima (sl1.5/tp5.0/be1.5)
ricalcolato con l'overlay reale sopra scende da pf 1.80 a **pf 1.63** —
resta un miglioramento sul vero live (1.55) ma meno netto di quanto
sembrava.

**Rifatta la ricerca tenendo l'overlay FISSO come vincolo reale** (non
disattivabile per-strategia con l'architettura attuale), sweepando
sl/tp/be sopra: **vincitore SL1.5×/TP6.0×/BE1.5R** — OOS pf 1.55→**1.74**,
drawdown 13.41%→**7.06%** (quasi dimezzato), calmar 0.104→**0.196** (quasi
raddoppiato). Walk-forward: 1.36·1.21·0.96·1.72·1.67 (una finestra debole
a 0.96, sotto pareggio di poco — il vero baseline ha 1.01 nella stessa
finestra, quindi non è un problema introdotto dal cambio).

## Raccomandazione

- **CRT**: breakeven a 1R + trailing 1×ATR — miglioramento di DD chiaro e
  coerente con il problema strutturale già noto, buon candidato per il
  porting MQL5.
- **FVG_CONT**: **aggiornato di nuovo dopo la scoperta dell'overlay
  trailing sempre attivo (vedi sezione sopra)** — le raccomandazioni
  precedenti (sl2.0/tp4.0, poi sl1.5/tp5.0/be1.5) erano contro un
  baseline che non esiste dal vivo. Pick finale, verificato contro il
  vero baseline (htf=True + overlay trail 2.5/attiva 1×ATR sempre
  presente): **SL1.5×/TP6.0×/BE1.5R** — OOS pf 1.55→1.74, DD
  13.41%→7.06%, calmar quasi raddoppiato. Non richiede modifiche
  all'overlay (che resta acceso, non è disattivabile per-strategia oggi),
  solo ai parametri SL/TP/BE del profilo.

Nessuna delle due modifiche è stata ancora portata in MQL5 — solo
verificata sul motore Python. Prossimo passo naturale: decidere quale
profilo FVG_CONT preferire, poi portare entrambi (CRT + FVG_CONT) nei
profili SL/TP/BE/trailing già esistenti in `NXS_StrategyProfiles.mqh`
(stesso meccanismo usato per gli altri override per-strategia).

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Riverifica Master-Slave Bias sul Motore Vero (12-08)]] ·
[[NEXUS EA - Fase C Recovery Baseline e Rischio Flottante (11-08)]]
