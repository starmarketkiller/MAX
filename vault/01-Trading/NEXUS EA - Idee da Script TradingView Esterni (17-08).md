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

## Addendum 24/08 (3) - altri 4 script TradingView, 3 testati

L'utente ha condiviso altri 4 script (mentre il porting MQL5 sopra era in
corso). Uno era gia' stato testato:

- **HHLL (HPotter, 4 deviazioni standard reverse breakout)**: identico
  allo script gia' testato il 17/08 sopra ("Breakout su banda estrema 4
  deviazioni standard") - stesso verdetto, bocciata (campione troppo
  sottile/concentrato in una finestra). Non riverificato.

Testati oggi con la stessa pipeline (walk-forward 5 finestre, filtro
regime ER trend soglia 0.045 - entrambi sistemi trend-following per
costruzione, stessa logica di scelta filtro del 16-17/08, conversione a
evento invece di "sempre in mercato" - stessa scelta di MACD+SMA200):

**Hull Suite (InSilico/DashTrader, HMA len=55, segnale=cambio direzione
HULL[0] vs HULL[2])** - `hull_suite_24-08.py`:

| TF | Preset | aggPF | finestre PF>=1 |
|---|---|---|---|
| 4h | retail | 0.98 | 2/5 |
| 4h | ECN | 1.11 | 3/5 |
| 1h | retail | 0.91 | 1/5 |
| 1h | ECN | 1.12 | 4/5 |

**Verdetto**: bocciata. Retail sotto/a pari su entrambi i TF, ECN
marginale (1.11-1.12, mai un plateau pulito). Conferma l'ipotesi gia'
scritta il 17/08 ("rifa concetti gia' presenti nel catalogo, trend-
following via medie come SAR/MACD") - nessun edge aggiuntivo reale.

**ML Adaptive SuperTrend (AlgoAlpha, SuperTrend fattore 3 su ATR10, ma
l'ATR e' sostituito dal centroide di un k-means a 3 cluster - alta/media/
bassa volatilita' - fittato sugli ultimi 100 valori, warm-start dal
centroide del bar precedente come nello script Pine originale)** -
`ml_adaptive_supertrend_24-08.py`:

| TF | Preset | aggPF | finestre PF>=1 |
|---|---|---|---|
| 4h | retail | 1.00 | 2/5 |
| 4h | ECN | 1.12 | 3/5 |
| 1h | retail | 0.88 | 2/5 |
| 1h | ECN | 1.06 | 3/5 |

**Verdetto**: bocciata, stesso pattern di Hull Suite - retail a/sotto
pari, ECN marginale. La sostituzione ATR->centroide k-means non produce un edge misurabile
rispetto a un supertrend con ATR grezzo (mai testato qui per confronto
diretto, ma il livello assoluto del risultato non giustifica il costo di
un k-means online solo per validare quel confronto). Nessun plateau
pulito su 4-5 finestre in nessuno dei due test di oggi.

**KZP - ICT Killzones & Pivots (tradeforopp)** - NON testato,
deliberatamente. E' un `indicator()`, non uno `strategy()`: nessuna
`strategy.entry()`, nessuna direzione, nessuna uscita - solo box di
sessione (Asia/London/NY AM-PM), linee dei massimi/minimi per killzone e
statistiche di hit-rate. Per testarlo avrei dovuto INVENTARE una regola
di ingresso (es. "compra alla rottura del massimo della killzone X") che
lo script stesso non definisce - esattamente il tipo di regola gia'
testata ripetutamente su questo storico con esito negativo (LIQ_SWEEP/
TURTLE_SOUP/CISD_TRUE ancorati a PDH/PDL/Asia, vedi sopra: "livelli
intraday/sessione... usati da tutte le versioni precedenti" contro cui il
pivot di swing maggiore ha appena vinto). Costruire un'altra variante
sessione-ancorata senza una tesi nuova sarebbe il tipo di filtro
aggiunto "perche' suona professionale" che il roadmap vieta esplicitamente
(sezione 12). Se l'utente ha in mente una regola di ingresso specifica
basata su KZP, va testata come ipotesi dichiarata, non dedotta da un
indicatore di visualizzazione.

## Addendum 24/08 (4) - Hull Suite e ML Adaptive SuperTrend: risultato ribaltato con lo sweep

L'utente ha chiesto di riprovare invece di fermarsi al config di default
(erano state bocciate entrambe con i parametri "consigliati dall'autore").
Sweep sistematico (un asse alla volta, cerca di un plateau non di un
picco isolato - regola P4.6/P2.5 del roadmap), poi verifica due-meta'-
storia sul candidato centrale del plateau trovato.

**Hull Suite** (`hull_suite_sweep_24-08.py`) - sweep length 8-200 su 4h e
1h, poi sweep mode (Ehma/Thma) a length 55/200. Trovato un **plateau
reale** su 4h, length 17-45 (Hma), molto diverso dal singolo punto
testato prima (length=55, che sta appena fuori dal bordo positivo):

| length (4h) | retail PF | ECN PF | finestre ECN>=1 |
|---|---|---|---|
| 17 | 1.04 | 1.17 | 5/5 |
| 21 | 1.12 | 1.26 | 5/5 |
| 25 | 1.11 | 1.24 | 4/5 |
| 34 | 0.96 | 1.09 | 4/5 |
| 45 | 1.14 | 1.29 | 5/5 |
| 55 (default autore) | 0.98 | 1.11 | 3/5 |

Non monotono ma consistentemente sopra 1 su ECN in tutto il range 17-45
(34 e' un avvallamento interno, non rompe il plateau). Modalita' Ehma/Thma
non aggiungono nulla di consistente (Thma buono a len 55, pessimo a len
200 - interazione inaffidabile, scartata). Ablation senza filtro di
regime: peggiora ovunque (retail 0.77-0.86) - il filtro resta necessario.

**Verifica due-meta'-storia** (length 25/34/45, 4h): qui la promozione si
ferma. **Stessa firma gia' documentata nel resto dell'indagine** (vedi
[[NEXUS EA - Filtro di Regime e Portafoglio 5 Strategie (16-08)]]) - retail
e' vicino o sotto pari nella prima meta' (2019-2023 circa, PF 0.92-1.02) e
forte solo nella seconda (PF 1.28-1.40, il rally 2023-2026). ECN e' invece
positivo in ENTRAMBE le meta' (1.08-1.16 prima, 1.43-1.55 seconda) per
tutte e 3 le length testate - piu' pulito, non regge il criterio piu'
severo del retail.

**ML Adaptive SuperTrend** (`ml_adaptive_supertrend_sweep_24-08.py`) -
sweep del fattore SuperTrend (1.0-8.0, ATR/training fissi) su 4h e 1h.
Su 4h, **plateau reale a fattore 1.25-2.5** (default autore=3.0 era
appena fuori, sul bordo di discesa):

| factor (4h) | retail PF | ECN PF | finestre ECN>=1 |
|---|---|---|---|
| 1.0 | 0.94 | 1.06 | 3/5 |
| 1.25 | 1.15 | 1.29 | 4/5 |
| 1.5 | 1.14 | 1.27 | 4/5 |
| 1.75 | 1.14 | 1.28 | 4/5 |
| 2.5 | 1.06 | 1.19 | 4/5 |
| 3.0 (default autore) | 1.00 | 1.12 | 3/5 |

Su 1h nessun plateau vero - i valori "buoni" (factor=5, factor=8) sono
picchi isolati su campioni sottili (n=93/47) con finestre a varianza
enorme (0.24-2.98 PF) - scartati come rumore, non un edge.

**Verifica due-meta'-storia** (factor 1.25/1.5/1.75, 4h): **identica firma**
di Hull Suite - retail sotto pari nella prima meta' (PF 0.92-0.95), forte
nella seconda (PF 1.38-1.40); ECN positivo in entrambe (1.03-1.08 prima,
1.53-1.55 seconda).

## Verdetto aggiornato: promozione parziale, non piena

Entrambe passano da "bocciata" a **candidata borderline ECN-only**, stessa
categoria di SAR_ADX20/DONCHIAN_TURTLE nel catalogo esistente ("regge solo
a costi ECN"): il config di default testato la prima volta era
sfortunatamente fuori dal plateau reale per entrambe, ma anche al centro
del plateau il risultato retail dipende dal rally 2023-2026 - lo stesso
problema di fondo mai risolto per l'intero portafoglio (vedi nota 16/08
collegata sopra), non un difetto specifico di questi due script. Non
promosse a Core; da tenere presenti se/quando si affronta il problema di
fondo della dipendenza dal regime storico invece di riprovare varianti
dello stesso sintomo.

Config rappresentativi del plateau (non i picchi assoluti, per evitare di
scegliere il punto piu' fortunato): Hull Suite length=25/Hma/4h; ML
Adaptive SuperTrend factor=1.5/4h.

## Collegamenti
[[MOC - Trading]]
