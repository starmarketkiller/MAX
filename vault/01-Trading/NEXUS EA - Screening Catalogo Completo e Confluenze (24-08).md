---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, screening, catalogo, confluenza, macd, fibonacci]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Screening catalogo completo + confluenze (24/08)

## Perché

Richiesta esplicita dell'utente: mettere da parte l'affinamento fine
delle 4 strategie già solide (SAR/MACD/FVG_CONT/Z_SCORE_BREAKOUT) e
usare la ricetta appena scoperta (ER≥0.045 + floor ATR 30° percentile
mobile, vedi [[NEXUS EA - Attacco alla Dipendenza dal Rally 2023-2026 (24-08)]])
per trovare quante più strategie possibile con una baseline
profittevole vera, prima di tornare a raffinare in profondità.

## Parte 1 — Screening a ricetta uniforme su tutto il catalogo (67 strategie)

`full_catalog_screen_24-08.py`: stop ATR generico 1.5/4.0 + ER + floor,
su tutte le strategie compatibili con la firma `(candles, ind, i)`.
Escluse esplicitamente (non per pigrizia): famiglie con stop strutturale
proprio già testate a fondo con il LORO stop nativo il 16-17/08
(CRT/TURTLE_SOUP/SH_BMS_RTO/sweep - uno stop generico le sottostimerebbe),
SCALP_* (scala M15/M30, TF non comparabile), e le 5 già note/portate
(SAR/MACD/FVG_CONT/Z_SCORE_BREAKOUT/LONDON_BO).

**12 candidati emersi** con PF≥1.0 retail o ≥1.20 ECN su campione ≥30
trade, poi verificati due-metà-storia (`meta1`/`meta2`, stesso rigore
usato tutto il giorno) prima di fidarsene:

| Strategia | TF | n | retail PF (agg/meta1/meta2) | ECN PF (agg/meta1/meta2) | Verdetto |
|---|---|---|---|---|---|
| MALAYSIAN_SNR_BREAKOUT | 4h | 94 | 1.58/1.47/1.69 | 1.77/1.68/1.87 | **Robusta** |
| DONCHIAN_TURTLE | 4h | 453 | 1.30/1.28/1.32 | 1.46/1.46/1.46 | **Robusta, quasi identica tra le due metà — il caso migliore di oggi** |
| DARVAS_BOX | 4h | 446 | 1.30/1.24/1.38 | 1.47/1.41/1.52 | **Robusta** |
| ADX_RSI | 4h | 1321 | 1.27/1.35/1.20 | 1.42/1.53/1.31 | **Robusta** (meta1>meta2, non dipende nemmeno dal rally) |
| AMD_CONT | 4h | 164 | 1.42/1.25/1.61 | 1.60/1.43/1.78 | Solida, asimmetria moderata |
| SAR_FLIP | 4h | 106 | 1.40/1.21/1.61 | 1.57/1.38/1.79 | Solida, asimmetria moderata |
| LIQ_VOID | 4h | 503 | 1.30/1.19/1.41 | 1.45/1.36/1.55 | Solida ma **segnale IDENTICO a FVG_CONT** (già Core) — vedi nota sotto |
| EMA_PULLBACK | 4h | 116 | 1.30/1.14/1.48 | 1.47/1.30/1.65 | Solida — **ribalta il verdetto negativo del 16/08** (allora R totale negativo, senza floor) |
| SAR_ADX20 | 4h | 1610 | 1.21/1.07/1.36 | 1.35/1.22/1.50 | Solida, campione enorme |
| BREAKOUT_ACC | 4h | 359 | 1.17/1.09/1.26 | 1.32/1.25/1.39 | Solida |
| OTE_CONT | 4h | 129 | 1.20/1.49/0.96 | 1.34/1.70/1.05 | **Fragile** — pattern INVERTITO (forte su meta1, debole su meta2), il floor ATR non l'ha corretto come per le altre |
| TSI | 4h | 274 | 1.05/0.92/1.19 | 1.18/1.06/1.32 | Debole — meta1 sotto pari, stessa vecchia firma |

Su 1h gli stessi nomi (BREAKOUT_ACC/ICHIMOKU/DARVAS_BOX/DONCHIAN_TURTLE/
LIQ_VOID/SAR_ADX20) mostrano quasi tutti una meta' negativa - **4h resta
il TF giusto**, conferma ancora una volta la conclusione già raggiunta
il 15/08.

**Nota LIQ_VOID**: `bt.STRATEGIES["LIQ_VOID"] = sig_fvg_cont_ext`, la
STESSA funzione segnale di FVG_CONT (già Core), con SL/TP diversi (1.5/
4.0 generico qui vs il profilo ottimizzato di FVG_CONT). Non è una
strategia indipendente per la diversificazione del portafoglio — utile
solo se si vuole lo stesso segnale con un profilo di rischio diverso,
non come "strategia in più" nel conteggio verso i 10-15.

**10 baseline nuove e verificate** (esclusi OTE_CONT/TSI fragili, LIQ_VOID
ridondante): MALAYSIAN_SNR_BREAKOUT, DONCHIAN_TURTLE, DARVAS_BOX, ADX_RSI,
AMD_CONT, SAR_FLIP, EMA_PULLBACK, SAR_ADX20, BREAKOUT_ACC — tutte su 4h,
tutte con la ricetta ER+floor, nessuna ancora portata in MQL5.

## Parte 2 — Confluenze tra strategie/indicatori diversi

Richiesta esplicita dell'utente: uscire dallo schema "una strategia = una
sola logica", provare conferme incrociate (i suoi esempi: MACD per
ADX_RSI, zone Fibonacci per i pullback, Elliott per una lettura a onde -
Elliott non tentato oggi, richiede una logica di conteggio onde troppo
soggettiva per essere codificata bene nel tempo disponibile, idea aperta
non abbandonata). Avvertenza esplicita dell'utente, confermata dai
risultati: **un test può aiutare una strategia e danneggiarne un'altra,
va verificato per ciascuna, non assunto**. `confluence_experiments_24-08.py`.

### MACD come conferma di momentum — funziona su ADX_RSI, non generalizza

ADX_RSI + istogramma MACD (linea-segnale) allineato alla direzione del
trade:

| Config | retail agg/meta1/meta2 | ECN agg/meta1/meta2 | n |
|---|---|---|---|
| baseline | 1.27/1.35/1.20 | 1.42/1.53/1.31 | 1321 |
| + MACD istogramma allineato | 1.41/1.54/1.28 | 1.57/1.75/1.40 | 653 |
| + MACD allineato E stesso lato dello zero (più severo) | **1.48/1.57/1.38** | **1.65/1.79/1.51** | 548 |

Miglioramento reale su entrambe le metà, non solo sull'aggregato — la
versione più severa (istogramma allineato + linea MACD dalla parte
giusta dello zero) è la migliore delle tre. Costo: il campione si dimezza
(1321→548), un compromesso qualità/quantità esplicito, non gratuito.

**Generalizzazione testata, non assunta**: stessa conferma su SAR_FLIP
(marginale: PF1.40→1.45 ma campione già sottile 106→58, meta2 peggiora
1.61→1.38) e su DONCHIAN_TURTLE (**non aiuta**: PF1.30→1.27, meta2
1.32→1.24) — conferma esattamente l'avvertenza dell'utente, un filtro
buono per una strategia può essere neutro o dannoso per un'altra.

### Zona di ritracciamento Fibonacci sui pullback — test inconcludente, non un fallimento della tesi

EMA_PULLBACK + richiesta che il prezzo sia rientrato nella "golden zone"
(38.2%-61.8%) dello swing a 50 barre: campione crolla da 116 a **9 trade**
— troppo pochi per qualunque conclusione (walk-forward non eseguibile).
Stesso collasso su DONCHIAN_TURTLE (453→38, PF0.71 ma su campione
ancora sottile) e SAR_FLIP (106→8, inutilizzabile).

**Diagnosi onesta**: non è la tesi (Fibonacci) ad essere stata
falsificata — è l'implementazione, che impila la zona Fib come QUARTO
filtro simultaneo (segnale strategia + ER + floor ATR + zona Fib) su un
segnale già selettivo, lasciando quasi nessun trade. Da riprovare con un
disegno diverso: zona Fib come innesco primario (non filtro aggiuntivo)
o su un TF/lookback swing diverso, prima di scartare l'idea.

## Prossimi passi aperti

- Le 9 nuove baseline (Parte 1) sono ancora solo Python — nessuna
  portata in MQL5 finora, a differenza di SWING_FALSEBREAK/Z_SCORE_BREAKOUT.
- Confluenza MACD da provare anche sulle altre baseline nuove (AMD_CONT,
  BREAKOUT_ACC, MALAYSIAN_SNR_BREAKOUT) non ancora fatto.
- Zona Fibonacci da riprovare con disegno diverso (innesco primario, non
  filtro impilato) prima di chiuderla come inconcludente per sempre.
- Elliott Wave non tentato — idea aperta, richiede una specifica più
  precisa (conteggio onde, gradi, invalidazione) prima di poter essere
  codificato onestamente.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Attacco alla Dipendenza dal Rally 2023-2026 (24-08)]]
