---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, ricerca-esterna]
created: 2026-08-17
updated: 2026-08-17
---

# NEXUS EA — Idee da Script TradingView Esterni (17/08)

## Perché

L'utente ha condiviso una decina di script TradingView (indicatori e
strategie) chiedendo di costruire "una visione unica" con NEXUS. Triage
onesto prima di testare: la maggior parte sono strumenti di
visualizzazione o rifanno concetti già presenti nel catalogo (LuxAlgo SMC
= FVG_CONT/ORDER_BLOCK/IFVG già nostri; Hull Suite/MACD+SMA200 = trend-
following via medie come SAR/MACD; ZigZag++ = rilevatore di swing come
quello interno). VWAP ancorato scartato: richiede volume reale, XAUUSD
OTC ha solo tick-volume (stesso limite già segnalato per Wyckoff, vedi
nota Wyckoff in sessione). Due script avevano invece un elemento
genuinamente distinto dal nostro codice esistente, testati qui.

## MACD+SMA200 (ChartArt, 2015)

Diverso dal nostro MACD in 3 punti reali: medie SMA (non EMA) su
fast/slow/verylslow, entrata sull'EVENTO di incrocio dell'istogramma
sopra/sotto zero (non stato persistente come il nostro `sig_macd`), filtro
di trend su SMA200. Replicato fedelmente (SMA-based, evento zero-cross),
entrata a mercato sulla barra successiva (nostra convenzione standard),
stop ATR classico 1.5/4.0, filtro di regime ER, walk-forward 5 finestre.

- **4h**: retail PF 1.39 (4/5 finestre), ECN 1.55 (4/5) — ma solo **34
  trade grezzi** su 7 anni, campione troppo sottile per fidarsi (una
  finestra da 6-7 trade può ribaltare tutto).
- **1h**: retail PF 0.87 (2/5), ECN 1.07 (2/5) — debole.

**Verdetto**: promettente su 4h ma non confermato per la sottigliezza del
campione. Da riverificare su uno storico ancora più ampio se si vuole
insistere, altrimenti accantonare.

## Falso breakout su swing maggiore (ispirato da Bjorgum Key Levels)

Stesso concetto di "Spring"/sweep già chiuso 3 volte (LIQ_SWEEP/
TURTLE_SOUP/CISD_TRUE), ma con un ancoraggio MAI provato: pivot di swing
MAGGIORE (20 barre a sinistra, 15 a destra — quindi confermato solo 15
barre dopo essersi formato, nessun lookahead, stesso principio del
`choch_int` interno ma finestra più larga), zona larga min(prezzo×2%,
0.5×ATR), invece dei livelli intraday/sessione (PDH/PDL/Asia) usati da
tutte le versioni precedenti. Entry a mercato, stop ATR 1.5/4.0, stesso
filtro di regime e walk-forward.

- **4h**: retail PF 1.38 (3/5), 101 trade, ma le finestre 3-4 sono
  negative (0.72, 0.42) — non consistente nel tempo.
- **1h**: retail PF 1.29 (3/5), **234 trade** (il campione migliore tra
  le scoperte di oggi), ECN PF **1.57 su 5/5 finestre** — pulito su ECN,
  borderline su retail (finestre 3-4 vicine/appena sotto pari: 0.89, 0.97).

**Verdetto**: il candidato più interessante dei due — campione
ragionevole, ECN pulitissimo, retail onestamente borderline non
eccellente. La differenza rispetto ai 3 tentativi precedenti conferma che
l'ancoraggio (dove misuri il livello di liquidità) conta quanto il
pattern stesso: sessione/giornaliero non funziona, swing strutturale
maggiore sì (parzialmente). Prima di usarlo: validazione due-metà-storia
(stessa disciplina di [[NEXUS EA - Filtro di Regime e Portafoglio 5 Strategie (16-08)]]),
non ancora fatta qui.

Script: `bjorgum_swing_falsebreak_17-08.py` (ripetibile, non salvato in
file separato il test ChartArt — inline, riproducibile dal comando in
sessione se serve).

## Media adattiva ancorata allo swing (da "Dynamic Swing Anchored VWAP", Zeiierman)

Il VWAP vero non testabile (volume reale assente su XAUUSD OTC). Estratta
la parte indipendente dal volume: una media che si RIANCORA al prezzo a
ogni nuovo swing (finestra 50 barre) invece di un periodo fisso come le
nostre EMA, con velocità di adattamento che si stringe in alta
volatilità. Segnale: incrocio prezzo/media nella direzione dello swing
corrente.

- **4h**: retail PF 1.07 (3/5, una finestra a zero trade), ECN 1.18
  (4/5) — marginale.
- **1h**: retail PF 0.73 (**0/5**), ECN 0.89 (2/5) — negativo.

**Verdetto**: bocciata. L'idea di riancorare la media allo swing non
produce edge reale una volta tolta la ponderazione a volume.

## Breakout su banda estrema 4 deviazioni standard (da "HHLL", HPotter)

Diversa dal nostro BOLLINGER: bande a 4 deviazioni standard (non 2), e
con `reverse=true` (default originale) la rottura fa entrare NELLA
direzione della rottura, non contro — breakout su volatilità estrema con
continuazione, non mean-reversion.

- **4h**: solo 6 trade in 7 anni (soglia troppo estrema, quasi mai
  raggiunta) — campione inutilizzabile.
- **1h**: 59 trade, retail PF 1.09 (3/5, ma la prima finestra da sola
  spiega quasi tutto il profitto), ECN PF 1.32 (3/5) — debole,
  trascinata da una finestra sola.

**Verdetto**: non abbastanza per essere un candidato, campione troppo
sottile e concentrato in una finestra per fidarsene.

## Prossimo passo

Validazione due-metà-storia sul falso-breakout-su-swing-maggiore (1h),
poi eventuale ingresso nel portafoglio insieme a Z_SCORE_BREAKOUT (vedi
[[NEXUS EA - Stop Strutturale M5 su Segnali H1 (16-08)]], addendum 17/08).

## Addendum 24/08 — validazione due-metà-storia: promosso

Eseguita la verifica lasciata aperta (`bjorgum_swing_falsebreak_twohalf_24-08.py`,
stessa logica di segnale del 17/08, nessuna riottimizzazione — solo split
del campione 1h a metà). Nessuna metà negativa in nessuno dei due preset:

| Preset | Aggregato | Prima metà | Seconda metà |
|---|---|---|---|
| retail | PF 1.29, sumR +50.9, n=234 | PF 1.14, n=117 | PF 1.46, n=117 |
| ECN | PF 1.57, sumR +87.4, n=234 | PF 1.42, n=117 | PF 1.74, n=117 |

Retail migliora nella seconda metà invece di degradare (buon segno,
esclude che il risultato aggregato sia trascinato da un singolo periodo
favorevole all'inizio). **Promosso da candidato a strategia validata** —
nome di lavoro `SWING_FALSEBREAK` (1h, stop ATR 1.5/4.0, filtro regime ER
trend ≥0.045). Prossimo passo reale: portare in MQL5 (stesso trattamento
di CRT/FVG_CONT/TSI, vedi commit `145cc71`) e aggiungerlo al pool di
candidati per il portafoglio a 10-15 strategie insieme a Z_SCORE_BREAKOUT,
ICHIMOKU, BB_SQUEEZE (filtro laterale), SAR_ADX20/SAR_FLIP (borderline).

## Addendum 24/08 (2) - porting MQL5 completato

NXS_Strat_SwingFalseBreak() aggiunta a NXS_Strategies_SMC.mqh (bucket
STRAT_STRUCT_REACT, stessa famiglia di TURTLE_SOUP - sweep+rientro, ma
ancorato al pivot di swing maggiore invece di PDH/PDL/Asia). Toccati in
sincrono, seguendo esattamente il precedente TURTLE_SOUP: NXS_Inputs.mqh
(InpStrat_SwingFalseBreak), NEXUS_EA_v2.mq5 (call site, selector_index
41 - primo libero dopo lo scan 1-40 nel codice reale), NXS_StrategyProfiles.mqh
(Get: SL1.5/TP4.0 ATR, stessi moltiplicatori del backtest Python; TF: H1),
NXS_SignalRouter.mqh (FAM_SMC), NXS_Execution.mqh (counter-HTF price-action
list + audit list), NXS_StratStats.mqh (registrazione nome + SetEnabled),
NXS_WebBridge.mqh (toggle dashboard). Registro canonico aggiornato alla
fonte vera (knowledge/strategy_database.json, 37->38 live) e rigenerato
con contracts/generate_registry.py - non editato a mano (validato con
contracts/validate_registry.py: OK).

Gap dichiarato, non nascosto: il filtro di regime (Efficiency Ratio)
usato nella validazione Python NON e' stato portato come gate live - e'
lo stesso gap trovato per l'intero portafoglio SAR/MACD/LONDON_BO/FVG_CONT
(mai deployato live neanche quello). Commento nel codice lo segnala
esplicitamente. Senza quel filtro il comportamento live puo' discostarsi
da quello validato, specialmente in mercati laterali.

Non fatto oggi, deliberatamente fuori scope: nessuna integrazione in
server/backtest.py (STRAT_MAP) - la strategia resta research-only sullo
script dedicato (bjorgum_swing_falsebreak_17-08.py /
_twohalf_24-08.py), non un motore Python condiviso con ind{}. Toccare
quel builder centrale per una sola strategia avrebbe un raggio d'azione
troppo ampio (usato da ogni altro backtest) per uno scope "porta in MQL5".

Non verificato: compilazione MT5 reale - sessione senza MetaEditor
(nessun ambiente Windows/MT5 disponibile qui). Stesso limite dichiarato
nel porting CRT/FVG_CONT/TSI del 13/08 (commit 145cc71). Verifica locale
(compilazione + smoke test isolato con InpStrategySelector=41) richiesta
prima di qualunque uso demo/live.

## Collegamenti
[[MOC - Trading]]
