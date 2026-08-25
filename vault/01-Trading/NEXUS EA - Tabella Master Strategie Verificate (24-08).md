---
type: reference
domain: trading
status: active
tags: [trading, nexus-ea, tabella-master, riferimento, baseline]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Tabella master delle strategie verificate (24/08)

Documento di riferimento unico: consolida tutte le configurazioni
"vincenti" trovate/riverificate il 24/08, sparse su ~17 note separate.
Ogni riga è la MIGLIOR configurazione nota per quella strategia oggi,
con la fonte per chi vuole il dettaglio completo. Tutte le PF sono
retail_standard su 4h salvo indicato, con costi scalati sul prezzo
storico. `m1`/`m2` = due metà della storia.

⚠️ **CORREZIONE (vedi [[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]])**:
le config "BUY-only" sotto sono valide come descrizione dell'AGGREGATO
2019-2026, ma isolando la finestra genuinamente laterale (2020-11→
2023-10) il verdetto si RIBALTA — è SELL a vincere lì (es. ADX_RSI: BUY
PF0.23 vs SELL PF2.53 nel laterale). Non è un lato strutturalmente
migliore, è un flip di regime (BUY vince nei trend, SELL nel laterale).
Trattare "BUY-only" come una scommessa sulla continuazione del trend
rialzista, non come un edge di segnale scoperto. **Primo tentativo di
direction-lock condizionato al regime fatto il 24/08 su SAR (il flip
meglio campionato) — non ha funzionato**: il classificatore di regime
macro (D1, ER a 120gg) etichetta correttamente il laterale 2021-2023,
ma il generatore di segnale SAR produce quasi solo BUY anche lì (94.6%
del campione), quindi un gate esterno non ha abbastanza segnali SELL
da raddrizzare. Vedi [[NEXUS EA - Ottimizzazione SAR e Tentativo Direction-Lock (24-08)]].

🌊 **NUOVO INGREDIENTE (25/08) — filtro Elliott Wave multi-timeframe**:
scoperto un filtro (ZigZag + regole Elliott a 5 onde su TF-ingresso
**E** D1, sopprimi il segnale se ANCHE UNO SOLO dei due timeframe è
"esaurito" nella stessa direzione) testato su **tutte le 25 strategie
del catalogo (copertura completa)**: **21 migliorano** (14 in modo
netto), non danneggia altre 2, marginale su 1, peggiora solo
STRUCT_REACT — il tasso di successo più alto di ogni ingrediente
trovato in 2 giorni, incluse 3 strategie (BREAKOUT_ACC,
DONCHIAN_TURTLE, DARVAS_BOX) che avevano resistito al trailing e
**TURTLE_SOUP**, dove risolve proprio la debolezza (finestre
instabili) che la teneva "provvisoria". Le PF sotto NON includono
ancora questo filtro (richiederebbe riverificare tutte le righe, non
ancora fatto). Vedi
[[NEXUS EA - Filtro Elliott Wave Multi-Timeframe, il nuovo ingrediente universale (25-08)]]
per la tabella completa. **Le righe sotto sono già state aggiornate**
con le PF combinate (trailing + Elliott dove entrambi si applicano) —
vedi [[NEXUS EA - Combinazione Trailing + Filtro Elliott, gli effetti si sommano (25-08)]]:
i due ingredienti si sommano quasi ovunque (7/8 casi testati), es.
ADX_RSI 2.20→**2.62**. La configurazione più forte dell'intero
catalogo è ora **FVG_MIT a PF3.24** (D1-align+trailing+Elliott
insieme). Nessuna modifica al codice MQL5 — solo ricerca, su
richiesta esplicita dell'utente.

**Aggiornamento precedente**: split BUY/SELL sistematico (vedi
[[NEXUS EA - Sweep Sistematico BUY-SELL (24-08)]]) — 13 strategie su 14
testate migliorano nettamente passando a BUY-only nell'aggregato, ma
vedi la correzione sopra prima di fidarsene.

## Nucleo storico (5)

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) | Correlazione | MQL5 |
|---|---|---|---|---|---|---|---|
| SAR | 4h | 1.5/4.0, **trailing 2.0×ATR + filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **1.87 (1.44/2.36, n=1370, 5/5)** — trailing da solo 1.64 | Cluster (alta) | No |
| MACD | 4h | 1.5/4.0, **trailing 2.0×ATR + filtro Elliott 4h/D1** | ER+floor 0.3 | simmetrica (BUY-only solo +0.12, non vale la pena) | **1.84 (1.53/2.17, n=1443, 5/5)** — trailing da solo 1.72 | Cluster (alta) | No |
| FVG_CONT | 4h | 1.5/4.0, **trailing 2.0×ATR + filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **1.78 (1.66/1.91, n=379, 4/5)** — trailing da solo 1.63 | Cluster | No |
| LONDON_BO | 4h | 1.0 init, **trailing 2.0×ATR** | ER (no floor) | **BUY-only** | **1.83 (1.38/2.32, n=70, 5/5)** | Bassa | No |
| Z_SCORE_BREAKOUT | 1h | stop M5 strutturale, target 4.0×ATR fisso, **filtro Elliott 1h/D1** | ER+floor 0.3 | simmetrica | **1.38 (1.40/1.35, n=509, 4/5)** — senza Elliott 1.35; il trailing "puro" (1.38-1.40) richiederebbe invece rimuovere il TP fisso, non ancora deciso | Bassa | **Sì — codice live INVARIATO: il trailing richiede rimuovere il TP fisso, verificato 25/08 che altrimenti è inefficace (PF1.32-1.34), decisione non ancora presa. Il filtro Elliott invece è compatibile col TP fisso attuale (agisce solo sull'ingresso), non ancora applicato al codice** |

## Cluster trend-following (5) — correlati 0.45-0.997 tra loro, non sommare ciecamente

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) | Nota |
|---|---|---|---|---|---|---|
| DONCHIAN_TURTLE | 4h | 1.5/4.0, **filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **1.63 (1.45/1.83, n=332, 5/5)** — senza Elliott 1.56 | **Correlata al 99.7% con DARVAS_BOX** — praticamente la stessa; trailing provato e scartato (collassa le finestre 5/5→2/5), Elliott invece aiuta |
| DARVAS_BOX | 4h | 1.5/4.0, **filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **1.65 (1.43/1.89, n=330, 5/5)** — senza Elliott 1.58 | Vedi sopra — tenerne solo una delle due in portafoglio; trailing scartato, Elliott aiuta come per DONCHIAN_TURTLE |
| ADX_RSI | 4h | 1.5 init, **trailing 2.5×ATR + filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **2.62 (2.57/2.66, n=657, 5/5)** — trailing da solo 2.20; terza config più forte del catalogo dopo FVG_MIT (3.24) e STRUCT_REACT (2.65) | Verificato per-data e sulla finestra laterale (flip più netto: BUY0.23/SELL2.53) — il più solido del cluster |
| SAR_ADX20 | 4h | 1.5 init, **trailing 2.0×ATR + filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **1.81 (1.28/2.44, n=936, 5/5)** — trailing da solo 1.61 | Campione enorme, laterale verificata (n=83, PF0.34) |
| BREAKOUT_ACC | 4h | 1.5/4.0, **filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **1.38 (1.24/1.54, n=268, 5/5)** — senza Elliott 1.33 | Miglioramento più modesto del cluster — trailing provato e scartato (peggiora sempre la robustezza), Elliott invece aiuta (finestre 4/5→5/5) |

## Diversificatrici genuine (5) — le più preziose per il portafoglio, bassa/negativa correlazione

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) | Correlazione media |
|---|---|---|---|---|---|---|
| **FVG_MIT** | 4h | 2.0/6.0, **trailing 3.0×ATR + filtro Elliott 4h/D1** | **D1-align (EMA50)** | simmetrica | **3.24 (1.57/5.06, n=74, 5/5)** — senza Elliott 2.72; **la configurazione più forte dell'intero catalogo** | 0.015 |
| **STRUCT_REACT** | 4h | 2.0/6.0 | ER+floor 0.3 | **BUY-only** | **2.65 (2.82/2.48, 5/5)** | **-0.019 (negativa con SAR/SAR_ADX20 — hedge naturale). Unica strategia dove il filtro Elliott PEGGIORA (2.65→2.28) — rimuove i suoi trade migliori, vedi [[NEXUS EA - Perché STRUCT_REACT Peggiora col Filtro Elliott (25-08)]], non applicarlo qui** |
| OTE_CONT | 4h | 1.0/6.0, **filtro Elliott 4h/D1** | **D1-align** | simmetrica (BUY/SELL split non ancora provato) | **2.14 (2.16/2.12, n=214, 5/5)** su config D1-align reale — senza Elliott 1.83 | 0.028 |
| EMA_PULLBACK | 4h **o** D1 | 1.5/4.0 (4h), **filtro Elliott 4h/D1** / 1.5/6.0 (D1) | **D1-align+trailing 3.0×ATR** (4h) / ER, no floor (D1) | simmetrica | **2.13 (1.44/2.83) su 4h, n=223, 5/5** (senza Elliott 1.87, 4/5) · 2.57 (1.69/3.70) su D1, n=39, 5/5 (Elliott non ancora testato su questa variante D1) | -0.012 |
| LIQ_SWEEP | 4h | 1.5/6.0 | ER+floor 0.3 | **BUY-only** | 1.73 (1.73/1.73, 5/5) | 0.084 — filtro Elliott provato, neutro (PF invariato, non aiuta né danneggia qui) |

EMA_PULLBACK aggiornata (24/08, vedi [[NEXUS EA - Ottimizzazione EMA_PULLBACK (24-08)]]):
config principale 4h+D1-align+trailing (campione ampio, PF1.87), D1
nativo SENZA floor come conferma/upside (PF2.57, 5/5 finestre, il floor
ATR era leggermente controproducente qui).

## Nuova (25/08) — riapertura di un verdetto pre-disciplina-laterale

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) | Nota |
|---|---|---|---|---|---|---|
| ML_ADAPTIVE_SUPERTREND | 4h | 1.5/4.0, **filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **2.13 (1.44/3.13, n=117, 4/5)** — senza Elliott 1.94 | Script TradingView esterno (AlgoAlpha), era "bocciata/ECN-only borderline" dal 17-24/08 — riaperta con floor+BUY-SELL+laterale: **flip genuino confermato** (SELL laterale PF1.88 n=11, stessa fascia di SAR/ADX_RSI), non solo beta. Campione ancora sottile, factor SuperTrend=1.5 (k-means su ATR10, training 100), non ancora in MQL5 |
| BOLLINGER (= RANGE_FADE) | 4h | 1.5/4.0, **filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **1.95 (1.91/1.99, n=52, 3/5)** — senza Elliott 1.54, ma finestre 4/5→3/5 (unico costo di robustezza visto con questo filtro) | Era "confermata debole" solo in forma simmetrica — mai testata BUY/SELL. SELL laterale PF3.34 (n=10), flip genuino. Non ancora in MQL5 |
| RSI_DIV | 4h | 1.5/4.0, **filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **1.96 (2.21/1.73, n=48, 4/5)** — senza Elliott 1.65 | Idem — SELL laterale PF1.36 sul campione laterale più ampio verificato oggi (n=21). Non ancora in MQL5 |

## Altre solide (5)

| Strategia | TF | SL/TP | Filtro | Direzione | Retail PF (m1/m2) |
|---|---|---|---|---|---|
| TSI | 4h | 1.0/6.0, **filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **2.25 (2.04/2.46, n=125, 5/5)** — senza Elliott 2.03; il migliore di questo blocco; trailing provato e scartato (peggiora sempre) |
| MALAYSIAN_SNR_BREAKOUT | 4h | 1.5/4.0, **filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **2.14 (1.81/2.51, n=71, 5/5)** — senza Elliott 1.93 |
| SAR_FLIP | 4h | 1.5/4.0, **trailing 2.0×ATR + filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **2.31 (1.54/3.49, n=68, 4/5)** — trailing da solo 1.82 |
| FVG_CONT_V2 | 4h | stop nativo, **trailing 2.0×ATR + filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **2.40 (2.10/2.93, n=61, 5/5)** — trailing da solo 2.03 |
| AMD_CONT | 4h | 1.5/4.0, **filtro Elliott 4h/D1** | ER+floor 0.3 | **BUY-only** | **1.80 (1.43/2.25, n=127, 4/5)** — senza Elliott 1.62; trailing e D1-align provati e scartati (peggiorano sempre), Elliott invece aiuta |

## Confermata con cautela sul campione (riverificata 24-25/08)

| Strategia | TF | SL/TP | Direzione | Retail PF | Nota |
|---|---|---|---|---|---|
| LDN_REVERSAL | 4h | stop strutturale (swing 10 barre), RR 1:3, **filtro Elliott 4h/D1** | simmetrica | **1.36 (1.36/1.37, n=30, 4/5)** — senza Elliott 1.28, ora quasi perfettamente bilanciata | Plateau confermato su griglia 16 combinazioni swing×RR; la config nota è anche il punto più bilanciato della griglia (non scelta per il PF massimo) — promossa da provvisoria, campione assoluto ancora piccolo |

## Ancora provvisoria — riverifica non ha sciolto i dubbi

| Strategia | TF | SL/TP | Direzione | Retail PF | Perché ancora provvisoria |
|---|---|---|---|---|---|
| TURTLE_SOUP | 4h | stop wick sweep + floor 0.3, target 4.0×ATR, **filtro Elliott 4h/D1** | simmetrica | **1.19 (1.06/1.35, n=262, 3/5)** — senza Elliott 1.14 (2/5); migliora proprio la debolezza (finestre instabili) che la teneva "provvisoria" | Plateau confermato sul target (6 valori, PF 1.01-1.18) MA finestre storicamente instabili; asimmetria BUY1.75/SELL0.70 non confermata (lateral BUY n=12, PF0.78, inconcludente). Ancora la più fragile del catalogo, ma il filtro Elliott è un primo passo concreto di miglioramento |

## Rifiutate definitivamente oggi (non riprovare senza nuova ipotesi)

CRT, CRT_MINSTOP_FILTER, BJORGUM (simmetrica e BUY-only, beta mascherato
confermato dalla diagnosi per-data), TSI_EXTREME (BUY-only aggregato
già sotto pareggio, riverificato 25/08), OTE_CONT su D1 (morta
pre-2024), l'intera famiglia sessione/AMD/SCALP_* su M15/M30, LIQ_VOID
(segnale identico a FVG_CONT). ICHIMOKU riverificata 25/08 ma
inconcludente (campioni laterali troppo sottili, n=2-6), non promossa
né definitivamente chiusa.

**Correzioni 25/08**: RSI_DIV e BOLLINGER erano qui per errore — mai
testate BUY/SELL prima di oggi, solo in forma simmetrica. Riaperte con
lo split e la verifica laterale: **entrambe promosse**, vedi
[[NEXUS EA - Riapertura BOLLINGER RSI_DIV ICHIMOKU TSI_EXTREME (25-08)]]
e la sezione "Nuova (25/08)" sopra.

## Bilancio

**19 strategie verificate e pronte** + 2 provvisorie = **21 candidate
totali**, contro le 4 di partenza di stamattina — 13 di queste ora in
versione BUY-only (migliorate rispetto alla forma simmetrica). Solo
**2 sono in MQL5** (SWING_FALSEBREAK, Z_SCORE_BREAKOUT). Il problema di
allocazione del portafoglio (correlazione, budget di rischio) resta
aperto, ora da riverificare con le config BUY-only aggiornate — vedi
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]].

**Ciclo di ottimizzazione individuale completato (24-25/08)**: tutte le
19 strategie verificate sono state passate una per una (verifica
laterale dove applicabile + test trailing/D1-align/altri ingredienti).
**11 su 19 hanno trovato un miglioramento reale** (quasi sempre
trailing 2.0-2.5×ATR): STRUCT_REACT/LIQ_SWEEP/OTE_CONT/FVG_MIT/
EMA_PULLBACK (diversificatrici, fatte prima), SAR_FLIP/FVG_CONT_V2
(altre solide), SAR/MACD/FVG_CONT/LONDON_BO (nucleo storico),
ADX_RSI/SAR_ADX20 (cluster). **8 su 19 nessun miglioramento trovato**
(config invariata, risultato onestamente documentato): TSI/
MALAYSIAN_SNR_BREAKOUT/AMD_CONT (altre solide), BREAKOUT_ACC/
DONCHIAN_TURTLE/DARVAS_BOX (cluster) — pattern comune: il trailing
"collassa" la robustezza delle finestre pur mantenendo il PF
aggregato, quindi non promosso. Un primo tentativo di
"direction-lock per regime" (su SAR) non ha funzionato — vedi
[[NEXUS EA - Ottimizzazione SAR e Tentativo Direction-Lock (24-08)]].
**Le 2 provvisorie sono state riverificate (25/08)**: LDN_REVERSAL
promossa a confermata-con-cautela (plateau su 16 combinazioni
parametriche), TURTLE_SOUP resta provvisoria (finestre instabili,
asimmetria BUY/SELL non spiegata) — vedi
[[NEXUS EA - Riverifica TURTLE_SOUP e LDN_REVERSAL (24-25-08)]]. Bilancio
a quel punto: **20 strategie ragionevolmente solide, 1 (TURTLE_SOUP)
ancora da maneggiare con cautela**.

**Addendum 25/08 — riapertura di verdetti pre-disciplina-laterale**:
diverse strategie erano state scartate PRIMA che lo split BUY/SELL +
verifica sulla finestra laterale diventasse la prassi standard di
oggi — riaperte con gli stessi strumenti usati su tutto il resto.
Risultato: **3 nuove promozioni** (ML_ADAPTIVE_SUPERTREND, BOLLINGER/
RANGE_FADE, RSI_DIV — tutte flip genuini confermati sulla finestra
laterale, non beta mascherato), 2 conferme del rifiuto (Hull Suite,
TSI_EXTREME), 1 inconcludente (ICHIMOKU, campioni troppo sottili). Vedi
[[NEXUS EA - Riverifica Hull Suite e ML Adaptive SuperTrend con BUY-SELL e Laterale (25-08)]]
e [[NEXUS EA - Riapertura BOLLINGER RSI_DIV ICHIMOKU TSI_EXTREME (25-08)]].

**Bilancio finale (25/08)**: **23 strategie ragionevolmente solide**
(20 di ieri + 3 nuove promozioni), 1 (TURTLE_SOUP) ancora da maneggiare
con cautela, 1 (ICHIMOKU) inconcludente. Nessuna modifica al codice
MQL5 live in questo secondo giro — su richiesta esplicita dell'utente,
resta solo ricerca finché non viene chiesto diversamente.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]
[[NEXUS EA - Sweep Sistematico Allineamento D1 (24-08)]]
[[NEXUS EA - Sweep Sistematico BUY-SELL (24-08)]]
