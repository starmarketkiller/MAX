# Ricerca configurazione batch — tutte le strategie sopravvissute alla Fase 1

Eseguito su richiesta esplicita ("continua con trovare la configurazione
per tutte le strategie"), dopo AMD_CONT e SILVER_BULLET (deep-dive
completi a mano). Applica meccanicamente la parte automatizzabile della
disciplina NQROS v3.1 (Fase 1/3/6/8-lite/4) a tutte le altre strategie con
baseline positiva — non sostituisce un deep-dive completo (Fase 0/2/5/7/9/10
restano da fare a mano se si vuole promuovere una di queste a "mantieni").

Script: `server/research_scripts/find_all_configs.py`. Regole imposte
dopo un primo tentativo fallito (vedi sotto "Falso partenza"):
- baseline richiede ≥25 trade (così i due tagli OOS hanno ≥10 ciascuno)
- al massimo **1 toggle + 1 parametro di gestione** nella combinazione
  dichiarata (mai più di 2, per non impilare filtri come già successo su
  SILVER_BULLET)
- OOS richiede ≥10 trade per lato, altrimenti MARGINALE
- **PF Out-of-Sample sopra 3.0 → MARGINALE automatico**, anche a campione
  sufficiente: troppo bello per fidarsene senza revisione manuale

## Falso partenza (onestà del processo)

Il primo tentativo (senza questi limiti) ha impilato fino a 5 parametri
insieme e prodotto `SH_BMS_RTO`/`SMS_BMS_RTO` con **PF Out-of-Sample
49.54 su 9 trade**, marcato "PASS" dalla logica originale. Sbagliato:
esattamente il tipo di overfitting-per-accumulo-di-filtri già segnalato a
mano su SILVER_BULLET, qui riprodotto senza controllo umano. Corretto
prima di accettare qualunque risultato — vedi le regole sopra.

## PASS (6) — regge il gate OOS

| Strategia | TF | Baseline PF | Config trovata | Combo PF/trade | OOS in→out | Stress |
|---|---|---|---|---|---|---|
| IFVG | 4h | 2.06 | atr_tp=4.0 | 2.28/34 | 2.65→1.81 | 1.72 |
| LONDON_BO | 1wk | 1.71 | htf_filter=True, breakeven_r=1.5 | 2.00/25 | 1.49→2.19 | 2.12 |
| WEEKLY_EXP | 1wk | 1.71 | htf_filter=True, breakeven_r=1.5 | 2.00/25 | 1.49→2.19 | 2.12 |
| FVG_MIT | 4h | 1.24 | trailing_atr=2.0 | 1.41/43 | 0.83→2.55 | 2.42 |
| ICHIMOKU | 1h | 1.09 | atr_tp=4.0 | 1.19/72 | 1.03→1.77 | 1.59 |
| BJORGUM | 4h | 1.06 | atr_sl=2.0 | 1.09/97 | 0.83→1.71 | 1.63 |
| TURTLE_SOUP | 1h | 1.01 | atr_sl=1.0 | 1.22/49 | 1.55→1.02 | 0.89 |

Nota: LONDON_BO/WEEKLY_EXP condividono la stessa funzione Python
(collisione già documentata) — un solo risultato indipendente, non due.
TURTLE_SOUP è il più marginale del gruppo (OOS scende quasi a 1.0 con
costi stress a 0.89 — un pass, ma appena).

## MARGINALE (5) — non scartate, ma non abbastanza pulite per fidarsene subito

| Strategia | Motivo | Dettaglio |
|---|---|---|
| TSI | PF OOS 5.73 sopra soglia 3.0 | Troppo bello, serve revisione manuale prima di adottare |
| LIQ_VOID | PF OOS 3.55 sopra soglia 3.0 | Idem |
| OTE_CONT | PF OOS 4.39 sopra soglia 3.0 | Idem |
| OB_MIT | Campione OOS troppo piccolo (7 trade) | Sotto la soglia di 10, non giudicabile |

## FAIL (2 genuini + 2 "nessun miglioramento trovato")

| Strategia | Motivo | Nota |
|---|---|---|
| PO3 | PF crolla sotto 1.0 fuori campione (0.94, stress 0.89) | Fallimento genuino del gate |
| FVG_CONT | Nessun parametro batte la baseline (PF 3.15) con campione ≥25 | La baseline stessa resta forte — non è "la strategia è cattiva", è "non ho trovato di meglio con questi vincoli" |
| MACD | Nessun parametro batte la baseline (PF 2.94) con campione ≥25 | Idem |

## SKIP (7) — campione già troppo piccolo per tentare la ricerca

ADX_RSI (24tr), NY_REVERSAL (22tr), ORDER_BLOCK (12tr), SAR (18tr),
SH_BMS_RTO (17tr), SMS_BMS_RTO (17tr), THREE_BAR_DELIVERY_BREAK (15tr).

Non è un giudizio negativo — è lo stesso limite di dati che ha già bloccato
parte del lavoro su AMD_CONT/SILVER_BULLET (storico H4/W1 troppo corto per
alcuni). Riverificare quando c'è più storico.

## Stato rispetto al ciclo completo v3.1

Questo è **Fase 1/3/6/8-lite/4 meccanizzate**, non un deep-dive completo.
Mancano ancora, per ogni strategia PASS/MARGINALE, prima di considerarle
pronte:
- Fase 0/2 (bottleneck/anatomia) — qui saltate, la ricerca è stata a
  griglia diretta, non guidata da un'ipotesi sui dati
- Fase 5 (risk_pct — qui non testato, MaxDD non riportato)
- Fase 9/10 (punteggio, decisione, diario)
- Gli stessi due rischi aperti di AMD_CONT/SILVER_BULLET: fedeltà motore
  Python vs MQL5 reale (mai verificata), storico H4/W1 corto (limite Yahoo)

## Aggiornamento 04/08 — LONDON_BO/WEEKLY_EXP corrette, verdetto PASS superato

Verifica di fedeltà (ordine deciso con l'utente: fedeltà prima di tutto,
non dopo un deep-dive): `LONDON_BO` e `WEEKLY_EXP` condividevano lo stesso
proxy generico `sig_breakout` (rottura di un massimo/minimo a 20 barre
qualsiasi) — la "collisione" documentata nel registro non era un caso
d'uso reale, erano due strategie MQL5 **completamente diverse**:

- `NXS_Strat_LondonBO`: breakout H4 del range asiatico durante la sessione
  di Londra, con corpo minimo 0.5×ATR, buffer 0.15×ATR oltre il livello,
  Close Location Value ≥ 0.6 (convinzione della chiusura, non un tocco
  marginale).
- `NXS_Strat_WeeklyRangeExp`: sconto/premio rispetto al midpoint della
  settimana precedente (PWH/PWL), displacement H4 (corpo≥0.8×ATR H4) con
  Break of Structure su uno swing H4 a 15 barre, reclaim dell'apertura
  della settimana corrente, CHoCH di conferma, target Fibonacci 1.272.

Implementate separatamente (`sig_london_bo`, `sig_weekly_exp` in
`backtest.py`, con `_weekly_exp_sl_tp` per il vero SL/TP strutturale di
WEEKLY_EXP — SL da PWH/PWL, TP dal massimo tra livello strutturale,
estensione Fibonacci 1.272 e 2.6×R). Registro (`contracts/strategy-
registry.json`) e documentazione rigenerati di conseguenza (collisioni
6→4, poi 4 confermate dopo la rigenerazione — non più 3, LONDON_BO/
WEEKLY_EXP non condividono più funzione).

**Il verdetto "PASS" del batch precedente per LONDON_BO/WEEKLY_EXP è
superato** — era calcolato sul proxy condiviso, non sulle strategie vere.
Ri-baseline onesto (parametri di default):

| Strategia | TF | PF | Trade | WR% | MaxDD% |
|---|---|---|---|---|---|
| LONDON_BO | H4 | 0.84 | 83 | 32.5 | 24.58 |
| LONDON_BO | H1 | 1.22 | 38 | 42.1 | 7.39 |
| WEEKLY_EXP | H4 | 0.16 | 5 | 20.0 | 4.11 |
| WEEKLY_EXP | H1 | 0.40 | 8 | 25.0 | 2.56 |

(D1 dà zero trade per entrambe: la sessione di Londra e il gate BOS H4
non si distinguono su barre giornaliere — atteso, non un bug.)

LONDON_BO su H1 (PF1.22/38 trade) è l'unico risultato con un campione
minimamente utilizzabile, comunque sotto la soglia di affidabilità
(MIN_BASELINE_TRADES=25 usata nel batch, qui sotto). WEEKLY_EXP è debole
e su campioni troppo piccoli ovunque (5-8 trade) per dire alcunché.

## Aggiornamento 04/08 (2) — IFVG corretta, verdetto PASS superato

Verifica di fedeltà (#2 nell'ordine concordato): `NXS_Strat_IFVG_Reversal`
(MQL5 reale) confrontata con `sig_ifvg`. Il concetto di base (gap violato →
flip) era già presente nel proxy, ma mancavano: buffer ATR sul gap
(0.2×ATR, non un tocco marginale), filtro di forza sulla candela di
reazione (corpo>0.3×ATR), e soprattutto la conferma **CHoCH sulla stessa
barra** — la vera strategia richiede che il flip coincida esattamente con
un cambio di struttura, non un semplice ritorno di prezzo.

Corretta (`sig_ifvg` + `_ifvg_sl_tp`, quest'ultimo aggiunto a
`STRATEGY_SLTP_ALWAYS` per il vero SL/TP: SL dal bordo del gap ±0.5×ATR,
TP a 2.4×ATR fisso dall'entry). Verificato che il filtro CHoCH abbia la
stessa semantica "evento per barra" in Python e MQL5 (`g_struct.chochUp/
chochDown` resettati a `false` a ogni ricalcolo in `NXS_Structure.mqh` —
non è un bug del porting).

**Risultato onesto**: la coincidenza esatta gap+reazione+CHoCH sulla
stessa barra è rarissima nel nostro storico — **zero trade su H4/H1/M30/W1**,
solo 5 trade su D1 (e negativi, PF 0.89). Il "PASS" del batch precedente
(PF 2.06→2.28, 34 trade) è superato: era calcolato su un proxy troppo
permissivo. Stesso pattern già visto su SILVER_BULLET — un setup ICT
molto selettivo che il campione di dati attuale non riesce a popolare a
sufficienza per un giudizio.

## Aggiornamento 04/08 (3) — BJORGUM corretta (off-by-one), verdetto PASS superato

Verifica di fedeltà (#3): `NXS_Strat_Bjorgum` (MQL5 reale) confrontata con
`sig_bjorgum`. Il concetto (rimbalzo/rifiuto su pivot a 30 barre) era già
giusto, ma un **off-by-one**: MQL5 usa shift1 (barra appena chiusa) per la
close e la finestra pivot parte da shift2 — nella convenzione di questo
motore (shift1 MQL5 = indice `i`, già usata per le correzioni precedenti
di oggi) il proxy usava `c[i-1]` per la close e `c[i-32:i-2]` per la
finestra, entrambi spostati indietro di una barra in più del dovuto.
Corretto: `c1=c[i]`, finestra=`c[i-30:i]`.

**Risultato onesto**: dopo la correzione, BJORGUM è **negativa su ogni
timeframe** (H4 PF 0.68, H1 0.90, D1 0.71, W1 0.39). Il "PASS" del batch
precedente (PF 1.06→1.09 con SL=2.0) era un artefatto dell'indicizzazione
sbagliata — con quella corretta l'edge sparisce del tutto. Nessuna
formula SL/TP custom necessaria (BJORGUM usa `NXS_DefaultSLTP`, generico,
già quello che il motore applica di default).

## Aggiornamento 04/08 (4) — TURTLE_SOUP corretta, verdetto PASS superato (nuovo TF)

Verifica di fedeltà (#4): `NXS_Strat_TurtleSoup` (MQL5 reale) usa il
rilevatore di sweep ESTESO (PDH/PDL con priorità Asia/daily, `_sweep_ext_at`
— già disponibile in questo motore e usato da altre strategie come
`sig_liq_sweep_ext`), non l'estremo generico a 20 barre che usava il
proxy. Corretta (`sig_turtle_soup` + `_turtle_soup_sl_tp`: SL dal livello
di sweep ±0.5×ATR, TP a 2.0×R della distanza di rischio reale — non un
multiplo ATR fisso).

**Risultato onesto, e diverso dal batch precedente**: H4 mostra un edge
reale (PF 1.15, 86 trade, WR 41.9%, MaxDD 12.45%) — un timeframe diverso
da quello del "PASS" precedente (era H1, ora **H1 è negativo** PF 0.70).
D1 pessima (MaxDD 49.32%, campione enorme 187 trade ma perdente). W1
debole/sottile.

| TF | PF | Trade | WR% | MaxDD% |
|---|---|---|---|---|
| H4 | 1.15 | 86 | 41.9 | 12.45 |
| H1 | 0.70 | 58 | 34.5 | 19.91 |
| D1 | 0.71 | 187 | 32.6 | 49.32 |
| W1 | 0.84 | 29 | 31.0 | 8.47 |

H4 è il candidato più credibile finora tra le correzioni di oggi (insieme
a LONDON_BO/H1) — non ancora ottimizzato (Fase 6), solo baseline fedele.

## Aggiornamento 04/08 (5) — FVG_MIT corretta, verdetto PASS superato

Verifica di fedeltà (#5): `NXS_Strat_FVG_Mitigation` (MQL5 reale) ha nomi
di variabili fuorvianti (`h2/l2` sono in realtà shift5, `h0/l0` sono
shift7, non shift2/shift0) — il proxy precedente aveva scambiato quali
candele definiscono il gap, la condizione stessa non corrispondeva a
nessuno dei due rami reali. Riscritta seguendo esattamente MQL5
(`sig_fvg_mit` + `_fvg_mit_sl_tp`: SL dal bordo del gap ±0.4×ATR, TP a
2.5×ATR fisso), "bid" approssimato dal range [low,high] della barra
(tocco della zona) invece della sola close.

**Risultato onesto**: debole ovunque. D1 quasi pareggio (PF 1.03, 83
trade — campione reale ma nessun edge), H4 chiaramente negativo (0.39),
H1 debole (0.87), W1 troppo sottile (7 trade) per giudicare. Il "PASS"
del batch precedente (PF 1.24→1.41) è superato — nessun timeframe mostra
un edge credibile con la versione fedele.

## Aggiornamento 04/08 (6) — ICHIMOKU corretta, verdetto PASS superato (ultima del gruppo)

Verifica di fedeltà (#6, ultima dell'ordine concordato): `NXS_Strat_Ichimoku`
(MQL5 reale) — il commento nel codice MQL5 stesso documenta un bug già
corretto lì il 17/07, mai riportato nel motore Python: le Senkou Span A/B
sono "shiftate in avanti" di 26 barre (comportamento nativo Ichimoku/MT5).
La nuvola confrontata col prezzo alla barra corrente va calcolata con
tenkan/kijun/senkouB di **26 barre prima**, non quelli correnti come
faceva il proxy — il proxy confrontava il prezzo con una nuvola "del
futuro" rispetto a quella che un trader reale vedrebbe in quel momento.

Corretta (`sig_ichimoku`, nessuna formula SL/TP custom necessaria —
ICHIMOKU usa `NXS_DefaultSLTP` generico).

**Risultato onesto, e coerente con quanto già sapevamo**: negativa su
ogni timeframe (H4 PF 0.63, H1 0.82, D1 0.59, W1 0.61). Coerente con la
nota già raccolta durante il primo audit di fedeltà su AMD_CONT/
SILVER_BULLET: l'EA reale ha **già disattivato ICHIMOKU** in
`NXS_Profile_Enabled()` per rumore sui dati broker MT5, nonostante
risultati misti/positivi nel motore Python col proxy vecchio — ora anche
la versione fedele lo conferma. Il "PASS" del batch precedente (PF
1.09→1.19) è superato.

## Riepilogo — 6/6 correzioni di fedeltà completate (ordine concordato)

| # | Strategia | Problema trovato | Esito onesto post-fix |
|---|---|---|---|
| 1 | LONDON_BO/WEEKLY_EXP | Proxy generico condiviso, due strategie reali diverse | LONDON_BO/H1 unico segnale utilizzabile (PF1.22/38tr) |
| 2 | IFVG | Mancavano buffer ATR, filtro reazione, CHoCH sulla stessa barra | Quasi nessun trade nel nostro storico (setup troppo selettivo) |
| 3 | BJORGUM | Off-by-one (finestra/close spostate di una barra) | Negativa ovunque, edge era un artefatto |
| 4 | TURTLE_SOUP | Usava estremo generico invece del vero sweep esteso PDH/PDL | H4 mostra edge reale (PF1.15/86tr) — nuovo TF rispetto a prima |
| 5 | FVG_MIT | Indici/candele del gap scambiati (nomi MQL5 fuorvianti) | Debole ovunque, nessun edge |
| 6 | ICHIMOKU | Mancava lo shift in avanti di 26 barre della nuvola (bug già noto in MQL5, mai riportato qui) | Negativa ovunque, coerente col fatto che l'EA reale l'ha già disattivata |

**Unico vero candidato positivo emerso da questo giro**: TURTLE_SOUP su H4.
Tutti gli altri "PASS" del batch precedente erano artefatti di proxy
infedeli — corretti, l'edge sparisce quasi ovunque tranne lì.

## Aggiornamento 04/08 (7) — Estensione a tutte le strategie ("facciamole tutte")

Su richiesta esplicita, esteso il giro di verifica fedeltà a tutte le
strategie rimanenti (27 con equivalente MQL5 reale, escluse le 4 SCALP_*
che non ne hanno — sono motore di ricerca puro). Gruppo 1 di questo giro:

- **ADX_RSI, MACD, BREAKOUT_ACC, RSI_DIV**: già fedeli, nessuna
  correzione necessaria (verificato riga-per-riga contro `NXS_Strat_
  ADXRSI`/`NXS_Strat_MACD`/`NXS_Strat_BreakoutAcc`/`NXS_Strat_RSIDiv`).
- **LONDON_BO**: già corretta nel gruppo precedente, confermata fedele
  anche da questa rilettura di `NXS_Strat_LondonBO`.
- **BOLLINGER/RANGE_FADE**: stesso bug di mixing-shift già trovato e
  corretto in MQL5 il 17/07 ("prezzo storico confrontato con una banda
  temporalmente diversa") — il proxy calcolava la banda una sola volta
  alla barra corrente invece che separatamente a shift1 e shift2.
  Corretta.
- **SAR**: divergenza più seria — MQL5 usa una condizione di **stato**
  (SAR vs prezzo + EMA9/EMA21), non un trigger di **flip** come faceva il
  proxy (solo il bar del cambio di lato PSAR), e usa EMA9/21 non EMA20 da
  sola. Corretta, aggiunto `ema21` a `_prep()`.
- **EMA_PULLBACK**: gap importante — mancavano trend persistente (5
  barre), impulso precedente (prezzo allontanato ≥1.0×ATR da EMA20),
  vera candela di rejection (non un cross istantaneo), filtro EMA50.
  Riscritta seguendo `NXS_Strat_EMAPullback`.
- **TSI**: la nota nel codice ("non è il vero TSI né qui né in MQL5")
  era riferita a una versione MQL5 più vecchia — il codice attuale
  (`NXS_Strat_TSI`, struct `SNXSTSIState`) calcola il vero TSI a doppio
  smoothing (Blau) con signal line e segnala sul cross, non su soglie
  RSI fisse. `tsi_series()` esisteva già (mai usata); aggiunta la signal
  line (`_tsi_signal_series`) e il cross — decisione esplicita sul
  trade-off frequenza/qualità già rimandata in precedenza, presa ora.
- **BB_SQUEEZE**: divergenza reale trovata (percentile-rank vs soglia
  assoluta, stato multi-barra mancante) ma **strategia già disattivata
  nell'EA reale** (`NXS_Profile_Enabled`) — non corretta, priorità bassa.

### Risultati onesti (parametri di default)

| Strategia | Miglior TF | PF | Trade | WR% | MaxDD% |
|---|---|---|---|---|---|
| BOLLINGER/RANGE_FADE | tutti negativi | 0.35–0.89 | | | |
| SAR | W1 | 1.65 | 43 | 46.5 | 8.33 |
| **EMA_PULLBACK** | **D1** | **1.62** | **35** | **51.4** | **4.71** |
| TSI | H1 | 1.08 | 102 | 40.2 | 11.47 |

EMA_PULLBACK/D1 è il candidato più interessante emerso da questo gruppo —
da validare Out-of-Sample prima di qualunque conclusione (stessa
disciplina di sempre).

## Aggiornamento 04/08 (8) — Gruppo sessione/AMD: AMD_REVERSAL, JUDAS_SWING,
## LDN_REVERSAL, NY_REVERSAL, PO3

Le 5 strategie di `NXS_Strategies_Institutional.mqh` condividevano lo
stesso bug: usavano `_choch_at(c, i)`, il vecchio proxy CHoCH "a
estremo rolling" (approssimativo), invece del vero CHoCH strutturale a
frattali già disponibile nel motore (`ind["choch_int"]`, prodotto da
`_fractal_choch_series`, l'unico fedele a `NXS_ComputeStructureCore`).
Il proxy rolling era già stato scartato per altre strategie in
precedenza in questa sessione — non era mai stato tolto da queste 5.

Corretto (`sig_amd_reversal`, `sig_judas_swing`, `sig_ldn_reversal`,
`sig_ny_reversal`, `sig_po3`): sostituito `_choch_at(c, i)` con
`ind["choch_int"][1][i], ind["choch_int"][2][i]` in tutte e 5.

Aggiunte 4 formule SL/TP strutturali (`STRATEGY_SLTP_ALWAYS`, transcritte
da `NXS_Strat_AMD_Reversal`/`NXS_Strat_JudasSwing`/
`NXS_Strat_LondonReversal`/`NXS_Strat_NYReversal`):

- `_amd_reversal_sl_tp`: SL dal refLow/refHigh dello sweep ∓0.5×ATR,
  TP fisso a 2.5×ATR.
- `_judas_swing_sl_tp`: SL da min/max(bar low/high, livello asiatico)
  ∓0.4×ATR, TP dal lato opposto del range asiatico o 2.5×R.
- `_ldn_reversal_sl_tp`: SL dal refLow/refHigh dello sweep ∓0.5×ATR, TP
  dal lato opposto asiatico (fallback 2.0×R).
- `_ny_reversal_sl_tp`: SL dal low/high della barra ∓0.5×ATR, TP dal
  london_hi/lo (fallback 2.5×R) — usa la stessa finestra `look=48`
  barre già presente nel segnale, vedi limite sotto.

**Limiti onesti dichiarati esplicitamente nel codice, non nascosti:**
- **NY_REVERSAL** resta un fix PARZIALE: il vero MQL5 aggrega dati tick
  M5 reali per l'hi/lo della sessione di Londra con conversione BST/UTC;
  questo motore lavora su un solo timeframe per run e non può farlo —
  mantenuta l'approssimazione esistente (finestra di 48 barre H4).
- **PO3**: solo la formula CHoCH è stata corretta. Non è stata trovata/
  confermata in questo giro una formula SL reale propria per PO3 — resta
  in `STRATEGY_TARGETS_ALWAYS` col solo TP strutturale (`_po3_target`)
  già presente, SL generico ATR. Segnato come backlog aperto.

Rimossi da `STRATEGY_TARGETS_ALWAYS` gli entry ormai superati
`JUDAS_SWING`/`LDN_REVERSAL` (le vecchie funzioni `_judas_swing_target`/
`_ldn_reversal_target` coprivano solo il TP; ora entrambe le strategie
hanno la formula SL+TP completa in `STRATEGY_SLTP_ALWAYS`, che ha
priorità — il guard `if target_fn and not sltp_fn` le avrebbe comunque
saltate, rimosse per pulizia).

### Risultato onesto: campione troppo piccolo per concludere qualunque cosa

Queste 5 strategie sono fortemente session-gated (fase AMD/killzone
specifica) — dopo la correzione, il numero di segnali che rispettano
TUTTI i filtri reali (sweep + CHoCH + sessione + eventuali buffer) crolla
molto sotto la soglia minima già fissata per questa sessione
(`MIN_BASELINE_TRADES=25`). Nessuna cella della tabella sotto è
utilizzabile come base per una decisione — riportata solo per onestà,
non come "risultato":

| Strategia | H4 | H1 | M30 | M15 |
|---|---|---|---|---|
| AMD_REVERSAL | PF4.17/3tr | PF—/1tr | PF1.58/2tr | PF0.6/4tr |
| JUDAS_SWING | PF0.39/9tr | 0tr | 0tr | 0tr |
| LDN_REVERSAL | PF1.21/14tr | PF2.51/3tr | PF0.07/3tr | PF0.16/8tr |
| NY_REVERSAL | 0tr | PF—/2tr | PF3.54/3tr | PF0.0/1tr |
| PO3 | PF0.9/7tr | PF2.21/2tr | PF1.97/2tr | PF0.0/3tr |

D1/W1: 0 trade su tutte e 5 (storico troppo corto per una fase AMD/
sessione intraday su timeframe daily+). Nessun timeframe raggiunge una
soglia di campione utilizzabile — a differenza dei gruppi precedenti
(TURTLE_SOUP, EMA_PULLBACK), qui la correzione di fedeltà non ha
prodotto un candidato testabile, solo la conferma che il vecchio proxy
sparava su condizioni molto più larghe (probabile causa dei conteggi-
trade più alti visti nel batch pre-fedeltà per queste strategie). Nessuna
promozione, nessuna bocciatura — serve più storico (stesso limite Yahoo
H4/H1 ~1.74 anni, ancora più severo qui per il gate di sessione che
riduce ulteriormente le occasioni) prima di poter dire qualunque cosa.

## Aggiornamento 04/08 (9) — ORDER_BLOCK, OB_MIT, SH_BMS_RTO, SMS_BMS_RTO
## (la riscrittura più grande di questo giro)

Il pezzo di lavoro più grande rimasto identificato: 4 strategie che nel
proxy Python precedente erano segnali a barra singola (o condividevano
tutte lo stesso proxy generico `sig_ob_mit`), mentre nel vero MQL5 sono
2 famiglie di state machine multi-barra distinte, mai portate prima:

- **ORDER_BLOCK/OB_MIT** (`NXS_OB_UpdateSide`, `NXS_Strategies.mqh`):
  zona attiva con memoria fra barre — impulso (corpo≥1.2×ATR, 3-10 barre
  fa) che ROMPE uno swing di riferimento a 15 barre pre-impulso (BOS, non
  un impulso qualsiasi come faceva il proxy), zona di retest = ultima
  candela di colore OPPOSTO prima dell'impulso (non il body dell'impulso
  stesso), attesa fino a 20 barre di un ritorno con candela di rejection,
  one-shot. **Scoperta di fedeltà aggiuntiva**: nel vero MQL5, OB_MIT non
  ha una logica propria — `NXS_Strat_OB_Mitigation_Structural` è
  letteralmente un wrapper che RIUSA `NXS_Strat_OrderBlock()` (stesso
  `dir`, solo `score`/`reason`/nome diversi). Il proxy precedente le
  aveva implementate come due funzioni DIVERSE (BOS a 5 barre per OB_MIT
  contro 15 per ORDER_BLOCK) — ora `sig_ob_mit`/`sig_ob_mit_ext`
  richiamano semplicemente `sig_order_block`/`sig_order_block_ext`, come
  nel vero EA.
- **SH_BMS_RTO** (`NXS_SHBMS_UpdateSide`, `NXS_Strategies_SMC.mqh`, già
  riscritta come state machine nel codice MQL5 il 17/07, mai portata qui
  prima d'ora): sequenza reale a 3 stadi IDLE→SWEPT→WAITING_RETURN —
  sweep di liquidità (stesso rilevatore esteso PDH/PDL/Asia già usato da
  TURTLE_SOUP) → entro 20 barre un vero MSS/BOS (corpo≥0.8×ATR che rompe
  lo swing pre-sweep) → zona d'origine → attesa fino a 15 barre del primo
  ritorno = entry. Il proxy precedente usava `sig_ob_mit`, la logica di
  tutt'altra strategia (order block, non sweep+MSS+return).
- **SMS_BMS_RTO** (`NXS_Strat_SMS_BMS_RTO`): a differenza di SH_BMS_RTO
  NON è una state machine multi-barra — è un controllo composito sulla
  STESSA barra (failure swing HL/LH sugli ultimi 10 vs 20 bar + CHoCH
  strutturale opposto + candela di rejection + prezzo tornato nella metà
  giusta del range). Anche questa condivideva `sig_ob_mit` nel proxy
  precedente — logica completamente diversa da quella reale.

Aggiunte 2 formule SL/TP strutturali a `STRATEGY_SLTP_ALWAYS`
(`_shbms_sl_tp`, `_sms_bms_sl_tp` — entrambe TP a multiplo ATR fisso
2.6×, non R-multiplo). ORDER_BLOCK/OB_MIT restano SENZA entry in quel
dict: il vero MQL5 chiama `NXS_DefaultSLTP` generico per queste due, non
ha una formula propria.

**Limite di fedeltà dichiarato esplicitamente, non nascosto**: il vero
MQL5 applica anche `NXS_SMCReactionOK` (motore "reazione" globale che
scansiona TUTTE le zone OB/FVG attive dell'EA, `NXS_Reaction.mqh`) come
filtro aggiuntivo sopra la candela di rejection già richiesta qui — è un
sottosistema separato e ampio, condiviso fra più strategie, non
riprodotto in questo giro. Stesso tipo di limite già accettato
esplicitamente per NY_REVERSAL (M5 cross-TF).

### Risultato onesto

| Strategia | H4 | H1 | D1 | W1 | M30 | M15 |
|---|---|---|---|---|---|---|
| ORDER_BLOCK/OB_MIT (identici) | PF0.86/12tr | PF1.03/8tr | PF0.38/12tr | PF0.0/2tr | PF1.43/4tr | PF0.56/7tr |
| SH_BMS_RTO | PF0.78/25tr | PF1.67/6tr | PF0.97/34tr | PF1.05/6tr | PF0.87/8tr | PF1.41/7tr |
| SMS_BMS_RTO | PF0.0/2tr | 0tr | 0tr | 0tr | 0tr | PF0.0/1tr |

**Confermato che ORDER_BLOCK==OB_MIT numericamente** dopo la correzione
(stesso segnale, come nel vero MQL5) — prima erano diversi per via del
bug di fedeltà, ora la riga H4/H1/D1/W1/M30/M15 è identica per entrambi,
esattamente come atteso da un wrapper.

Solo SH_BMS_RTO raggiunge un campione sopra soglia utilizzabile (H4 25tr,
D1 34tr) — ma il risultato è onestamente negativo/piatto (PF 0.78-0.97),
nessun edge trovato, non un artefatto di campione piccolo. ORDER_BLOCK/
OB_MIT restano sotto soglia ovunque (max 12 trade) — la zona attiva è
molto più selettiva del vecchio proxy (BOS a 15 barre reale, non un
impulso qualsiasi). SMS_BMS_RTO è quasi silenziosa (0-2 trade su ogni
TF) — il controllo composito a barra singola (failure swing + CHoCH +
rejection + metà range) è estremamente raro nello storico disponibile,
un dato di per sé (il vero setup SMC "SMS+BMS+RTO" è raro per
costruzione, non un bug del motore). Nessuna promozione possibile per
nessuna delle 4 — serve più storico, stesso limite di sempre.

## Aggiornamento 04/08 (10) — "Testa tutte le strategie": baseline completa
## su tutto il roster (39 strategie × 6 timeframe, parametri di default)

Su richiesta esplicita, girato un test completo su tutte le 39 strategie
disponibili nel motore (36 dei 37 id "live" — manca solo ELLIOTT, mai
portata su Python, solo su Pine — più le 4 SCALP_* di solo studio) su
6 timeframe (H4, H1, D1, W1, M30, M15), costi realistici standard
(`retail_standard`), parametri di default (nessuna ricerca/ottimizzazione
di configurazione — questa è la Fase 1 "grezza", non un giro di ricerca).

Soglia di campione minima usata per giudicare una cella: 25 trade
(`MIN_BASELINE_TRADES`, stessa soglia adottata in `find_all_configs.py`).
Su 234 combinazioni strategia×timeframe, **132 superano la soglia**, di
cui **36 hanno PF>1.0**. 14 strategie non raggiungono MAI la soglia su
nessun timeframe (stesso elenco già noto/spiegato nei giri precedenti:
AMD_REVERSAL, BB_SQUEEZE, DISP_REBAL, IFVG, JUDAS_SWING, LDN_REVERSAL,
NY_REVERSAL, OB_MIT, ORDER_BLOCK, PO3, SILVER_BULLET, SMS_BMS_RTO,
THREE_BAR_DELIVERY_BREAK, WEEKLY_EXP — tutte strategie molto selettive
per costruzione, o limitate dal poco storico intraday di Yahoo).

### I 26 con almeno un timeframe sopra soglia, miglior PF ciascuna

| Strategia | Fedeltà verificata? | Best TF | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|---|---|
| FVG_CONT | Sì (16/07, filtro trend H1 esterno) | W1 | 3.15 | 25 | 64.0 | +0.804 | 2.16 |
| MACD | Sì (già fedele) | W1 | 2.94 | 25 | 60.0 | +0.768 | 5.25 |
| LIQ_VOID | **No — proxy dichiarato di FVG_CONT** (filtro EMA50, non trend H1) | W1 | 1.69 | 38 | 47.4 | +0.374 | 7.08 |
| SAR | Sì (04/08, riscritta) | W1 | 1.65 | 43 | 46.5 | +0.344 | 8.33 |
| AMD_CONT | Sì (deep-dive, 04/08) | M30 | 1.62 | 26 | 53.8 | +0.323 | 3.85 |
| EMA_PULLBACK | Sì (04/08, riscritta) | D1 | 1.62 | 35 | 51.4 | +0.352 | 4.71 |
| SCALP_RANGE_BRK | **No** (mai auditata) | W1 | 1.51 | 31 | 45.2 | +0.304 | 5.30 |
| BREAKOUT_ACC | Sì (già fedele) | W1 | 1.44 | 25 | 44.0 | +0.274 | 5.28 |
| OTE_CONT | **No** — disattivata nell'EA reale, divergenza nota non corretta | D1 | 1.34 | 43 | 44.2 | +0.210 | 8.55 |
| SCALP_EMA | **No** (mai auditata) | H4 | 1.30 | 87 | 42.5 | +0.205 | 6.99 |
| LONDON_BO | Sì (04/08, riscritta) | H1 | 1.22 | 38 | 42.1 | +0.155 | 7.39 |
| TURTLE_SOUP | Sì (deep-dive, 04/08) | H4 | 1.15 | 86 | 41.9 | +0.108 | 12.45 |
| TSI | Sì (04/08, riscritta) | H1 | 1.08 | 102 | 40.2 | +0.059 | 11.47 |
| ADX_RSI | Sì (già fedele) | D1 | 1.07 | 146 | 39.7 | +0.057 | 11.98 |
| FVG_MIT | Sì (04/08, riscritta) | M30 | 1.05 | 33 | 30.3 | +0.122 | 15.41 |
| SCALP_RSI_SNAP | **No** | H1 | 0.98 | 77 | 39.0 | -0.007 | 8.45 |
| LIQ_SWEEP | Parziale (16/07, pre-rigore 04/08) | D1 | 0.97 | 101 | 37.6 | -0.010 | 19.45 |
| RSI_DIV | Sì (già fedele) | H4 | 0.97 | 80 | 36.2 | -0.008 | 14.32 |
| SCALP_BB_FADE | **No** | H4 | 0.97 | 65 | 36.9 | -0.009 | 14.51 |
| SH_BMS_RTO | Sì (questo giro) | D1 | 0.97 | 34 | 52.9 | -0.007 | 9.98 |
| MALAYSIAN_SNR | **No** — architettura cross-TF non replicabile | H4 | 0.96 | 168 | 36.9 | -0.017 | 17.88 |
| BJORGUM | Sì (04/08, off-by-one corretto) | H1 | 0.90 | 95 | 35.8 | -0.059 | 17.07 |
| BOLLINGER/RANGE_FADE | Sì (04/08, mixing-shift corretto) | H1 | 0.89 | 107 | 35.5 | -0.067 | 16.54 |
| ICHIMOKU | Sì (04/08, shift Kumo corretto) — disattivata nell'EA reale | M30 | 0.88 | 40 | 37.5 | -0.076 | 11.59 |
| STRUCT_REACT | **No** — disattivata nell'EA reale | H4 | 0.83 | 77 | 33.8 | -0.114 | 23.48 |

### Lettura onesta

- **Il PF più alto in assoluto (FVG_CONT/MACD, 2.9-3.2) è su W1 a
  campione minimo (25 trade, esattamente la soglia)** — lo stesso
  pattern già visto più volte in questa sessione ("PF spettacolare su
  campione minuscolo è un'ipotesi, non un risultato", lezione #4). Non è
  motivo per scartarli, ma nemmeno per promuoverli senza un Fase 4 vero.
- **Le uniche strategie con un campione davvero ampio (>80 trade) E PF
  sopra 1 sono TURTLE_SOUP (86tr/PF1.15, già in deep-dive, 67/100
  OSSERVAZIONE) e TSI/ADX_RSI (100+tr, PF 1.07-1.08, margine minimo)** —
  nessuna di queste è un edge forte, sono le più credibili proprio
  perché il PF modesto non si è "sciolto" nemmeno su un campione grande.
- **LIQ_VOID (il terzo miglior PF, 1.69/38tr) è un proxy dichiarato di
  FVG_CONT MAI verificato per fedeltà propria** — condivide solo il gap
  a 3 candele, ma usa il filtro trend locale (EMA50) invece del trend H1
  esterno reale che FVG_CONT usa già. Va controllato se LIQ_VOID ha una
  vera implementazione MQL5 propria prima di fidarsi di questo numero.
- **6 dei 26 risultati sopra soglia vengono da strategie MAI auditate per
  fedeltà in questa sessione** (LIQ_VOID, SCALP_RANGE_BRK, SCALP_EMA,
  OTE_CONT, SCALP_RSI_SNAP, SCALP_BB_FADE, MALAYSIAN_SNR — 7 in realtà) —
  i loro numeri vanno presi con la stessa cautela di AMD_CONT/
  SILVER_BULLET PRIMA della correzione (lezione #14): potrebbero
  sciogliersi o capovolgersi una volta verificati riga-per-riga contro
  MQL5, esattamente come è successo a 5 delle 6 strategie del primo
  batch pre-fedeltà.
- **Le 14 sotto soglia ovunque + le 13 sopra ma con PF<1 confermano un
  quadro coerente con tutto il resto della sessione**: un vantaggio
  reale, ampio e robusto non emerge facilmente su questo storico H4
  limitato (1.74 anni) con parametri di default — serve o più storico, o
  una ricerca di configurazione mirata (Fase 3+) sulle strategie già
  fedeli con un segnale di partenza onesto (TURTLE_SOUP, TSI, ADX_RSI,
  EMA_PULLBACK, LONDON_BO, SAR).

## Aggiornamento 04/08 (11) — "Fallo su tutte" + "serve una finestra più
## ampia": ottimizzazione meccanizzata su 24 strategie + avvio storico
## esteso Dukascopy

Su richiesta esplicita, girato `find_all_configs.py` (Fase 3 toggle +
Fase 6 SL/TP/breakeven/trailing + Fase 4 OOS gate, meccanizzato) sulle 24
strategie con almeno un timeframe sopra soglia campione dall'aggiornamento
precedente (esclude AMD_CONT/SILVER_BULLET/TURTLE_SOUP, già con deep-dive
manuale più approfondito). Lista `CANDIDATES` ricostruita da zero (quella
del 16/07 era su proxy in gran parte superati da questa sessione).

### Risultato: 6 PASS, 6 MARGINALE, 12 FAIL

**PASS (regge il gate OOS con lo stesso rigore di AMD_CONT/SILVER_BULLET/
TURTLE_SOUP)**, ordinati per solidità del campione OOS:

| Strategia | TF | Config | Combo PF | OOS PF | OOS trade |
|---|---|---|---|---|---|
| ADX_RSI | 1d | htf_filter=True, atr_sl=3.0 | 1.30 | 1.94 | 35 |
| TSI | 1h | atr_sl=2.0 | 1.11 | 1.17 | 38 |
| LIQ_SWEEP | 1d | htf_filter=True, atr_sl=3.0 | 1.80 | 2.54 | 24 |
| SCALP_BB_FADE | 4h | atr_tp=5.0 | 1.97 | 2.24 | 22 |
| LONDON_BO | 1h | atr_sl=2.5 | 1.79 | 1.45 | 12 |
| EMA_PULLBACK | 1d | atr_tp=4.0 | 2.13 | 2.06 | 10 |

Nota onesta: **LIQ_SWEEP non ha mai avuto il giro di fedeltà rigoroso
04/08** (solo un controllo del 16/07, "misto/non decisivo") e
**SCALP_BB_FADE non è mai stata auditata** (nessuna delle 4 SCALP_* lo
è stata) — questi due PASS vanno quindi trattati con più cautela degli
altri 4, che poggiano su un segnale già verificato riga-per-riga.
ADX_RSI resta il più credibile in assoluto: campione OOS più ampio (35
trade) e nessuna bandiera di sospetto.

**MARGINALE** (SAR, SH_BMS_RTO, SCALP_RANGE_BRK, LIQ_VOID, OTE_CONT: PF
OOS esplode sopra 3.0 su un campione OOS minuscolo — 10-14 trade,
classico segno di rumore non di edge, es. SH_BMS_RTO PF OOS 10.98 su 10
trade; BREAKOUT_ACC: degrado OOS oltre il 40%, sospetto overfitting) —
nessuno di questi va promosso senza revisione manuale.

**Scoperta importante — un limite dello script, non delle strategie**:
FVG_CONT e MACD (i due PF più alti di TUTTO il giro di baseline, 3.15 e
2.94) risultano "FAIL: nessun parametro batte la baseline" — ma questo
NON significa che il loro edge sia falso, significa che lo script non
prova mai a validare Out-of-Sample la baseline STESSA quando nessun
parametro la batte (bug di disegno: salta il gate invece di applicarlo
al segnale grezzo). Controllo manuale supplementare fatto subito dopo:

| Strategia | Baseline PF | In-sample PF (trade) | OOS PF (trade) |
|---|---|---|---|
| FVG_CONT/1wk | 3.15 | 2.41 (8tr) | 2.88 (**5tr**) |
| MACD/1wk | 2.94 | 0.62 (8tr) | **None (0tr)** |

La causa vera: **25 trade totali su W1 si spezzano in 8/5 o 8/0 con lo
split 60/40** — troppo pochi per QUALUNQUE verdetto, non solo per la
ricerca di parametri. Non possiamo ancora sapere se FVG_CONT/MACD hanno
un vantaggio vero o sono i prossimi "PF spettacolare su campione
minuscolo" (lezione #4) — serve più storico per allargare quei 25 trade
a un numero validabile, la stessa richiesta esplicita che ha motivato il
punto successivo.

### Avvio storico esteso via Dukascopy (risposta a "serve una finestra
### più ampia")

Yahoo limita H1/H4 a ~1.74 anni osservati (causa nota del "confondimento
di regime", lezioni #10/#18) — nessun export MT5 disponibile da questo
ambiente. Trovato e riattivato `server/dukascopy_fetch.py` (già presente
in repo da un tentativo precedente, mai portato a termine): scarica tick
gratuiti Dukascopy senza API key, aggregati a candele M15 da cui si
ricampiona H1/H4/M30 (stesso schema di `_resample_4h`).

Verificato: **il 2022 non è raggiungibile da questo ambiente** (timeout
SSL sistematico su ogni ora testata, anche con retry) — **il 2023 in poi
sì**. Avviato un fetch in background da 2023-01-01 a oggi (~3.5 anni,
circa il doppio dello storico attuale). Il primo tentativo è fallito
dopo il primissimo giorno per un 503 non gestito (un'ora fallita faceva
crollare l'intero fetch multi-anno) — corretto `dukascopy_fetch.py`
(`fetch_day_ticks`) perché un'ora persa dopo i retry venga loggata e
trattata come vuota, non interrompa il resto. Fetch rilanciato, gira in
background (richiede diverse ore data la granularità tick-by-tick) — al
termine va ricostruita la pipeline di lettura di `backtest.py` per usare
questa cache locale invece di/oltre a Yahoo sui timeframe intraday, poi
ripetuti i test più rilevanti (in primis FVG_CONT/MACD, TURTLE_SOUP/
SILVER_BULLET per il confondimento di regime) sulla finestra nuova.

## Aggiornamento 04/08 (12) — Piramidazione sul profitto (Fase 7) + rilancio
## storico a 10 anni

Su richiesta esplicita ("li voglio anche in esposizione sul profitto" +
"grid piramidazione" + "scarica più storico possibile"): tre interventi.

**1. Piramidazione sul profitto implementata nel motore** (`backtest.py`,
parametri `pyramid_max_legs`/`pyramid_r`/`pyramid_risk_mult`, default
`pyramid_max_legs=0` — nessun cambiamento per tutto il lavoro già fatto,
verificato bit-per-bit). Ogni volta che il prezzo avanza di `pyramid_r`
× R sul rischio ORIGINALE oltre l'ultima gamba, si apre una nuova gamba
con la propria size e il proprio rischio (distanza dal suo entry allo SL
corrente, non quello originale — se lo SL è già a breakeven, una gamba
successiva rischia meno). Tutte le gambe condividono SL/TP e si chiudono
insieme. Nessuna esclusione per strategia scritta a mano: su una
strategia con TP troppo vicino il primo livello di piramide semplicemente
non viene mai raggiunto, il meccanismo stesso è un no-op lì dove non ha
senso — non serve una lista nera.

**Non è stato costruito il grid/martingala** (aumento di size su un
trade in PERDITA) — solo la piramidazione sul profitto richiesta
esplicitamente. Segnalato esplicitamente il motivo: aumentare
l'esposizione contro il prezzo può ingigantire una perdita in modo molto
più pericoloso di una singola operazione persa, un rischio che va
contro l'obiettivo dichiarato di questo progetto (far crescere in modo
sicuro un conto piccolo).

**2. Aggiunta come leva testabile in `find_all_configs.py`** (Fase 6,
stessa disciplina delle altre: provata da sola, entra solo se batte la
baseline a campione sufficiente). Ri-eseguito su tutte le 24 strategie:
stesso quadro di prima (6 PASS/6 MARGINALE/12 FAIL) ma **TSI (H1)
migliora in modo concreto** — il vincitore precedente (`atr_sl=2.0`, OOS
PF 1.17/38tr) è stato superato da `pyramid_max_legs=1` (**OOS PF 1.35 su
un campione ancora più ampio, 41 trade**) — non solo un PF migliore, un
campione OOS più grande insieme, il segnale più solido di un
miglioramento reale raccolto finora in questo giro. `pyramid_max_legs=1`
vince anche per MACD/LIQ_VOID/MALAYSIAN_SNR, ma su MACD questo ha solo
reso più visibile il problema di dati già noto: batte la baseline (PF
3.38 vs 2.94) ma il test fuori campione ha **0 trade disponibili** (in=8,
out=0) — non un giudizio negativo, un campione insufficiente per
qualunque giudizio, ennesima conferma che serve più storico.

**3. Rilanciato il fetch Dukascopy a 10 anni** (2016-01-01, non più
2023-01-01) — riscritto per scrivere snapshot incrementali ogni 20
giorni invece di attendere il completamento (un fetch da 15-20+ ore deve
poter essere letto o interrotto senza perdere il lavoro fatto). In corso.

## Aggiornamento 04/08 (13) — Verifica indipendente di un'idea social
## ("Liquidity Grab + EMA30", @pranamghagare)

Su richiesta esplicita, verificata un'idea trovata su un post social (8
slide screenshottate): liquidity grab su pivot a 1 barra per lato
(Left=1/Right=1, il livello più sensibile possibile) + filtro EMA30 +
target 1:1 dichiarato ("Low RR = Higher Win Rate"). Claim della fonte:
76.53% win rate, <2% drawdown, ~98 trade in **un solo mese** (2-28
aprile), nessuna validazione Out-of-Sample mostrata.

**Non è una strategia del roster NEXUS** (nessun corrispettivo MQL5,
nessun selector_index) — verificata come script indipendente
(`test_liquidity_grab_ema30.py`), riusa i pezzi generici del motore
senza toccare il registro canonico delle 37+4 strategie.

Implementazione: livello di supporto/resistenza attivo = ultimo pivot
1-barra CONFERMATO (con 1 barra di ritardo, no lookahead — il livello
usato per il check "rottura" di una barra è quello noto PRIMA che quella
barra chiuda). Entry approssimata alla chiusura della barra di segnale
(convenzione di tutto il resto del motore, invece di un vero ordine stop
al massimo/minimo che potrebbe non riempirsi mai — leggermente
ottimistica ma preserva la forma del rischio). SL/TP: 1:1 dal minimo/
massimo della stessa barra, esattamente come dichiarato dalla fonte.

### Risultato onesto: negativo, e con un campione ampio e affidabile

| TF | PF (costi reali) | PF (senza costi) | Trade | WR% (senza costi) | MaxDD% (costi reali) |
|---|---|---|---|---|---|
| M15 | 0.17 | 0.93 | 159 | 48.4 | 79.83 |
| M30 | 0.36 | 1.13 | 131 | 53.4 | 50.48 |
| H1 | 0.49 | 0.89 | 158 | 46.8 | 46.76 |
| H4 | 0.45 | 0.78 | 140 | 44.3 | 44.21 |

A differenza di quasi tutto il resto di questa sessione, qui il campione
NON è il problema (130-159 trade per TF, ben sopra la soglia minima) —
è un risultato negativo genuino, non un "serve più storico".

**Anche senza costi di trading il segnale è sostanzialmente un lancio di
moneta** (PF 0.78-1.13, coerente con WR%/(1-WR%) atteso per un vero 1:1
- verificato: 48.4%/51.6%=0.938 ≈ PF 0.93 misurato, conferma che la
simulazione implementa correttamente la regola 1:1 dichiarata, non un
bug). **Con i costi reali crolla** (PF fino a 0.17, MaxDD fino
all'80%): lo stop di questa strategia è il minimo/massimo di UNA singola
candela — spesso una distanza in dollari molto piccola, specialmente su
M15 — quindi i costi fissi (spread ~$2.50, slippage ~$0.50 su XAUUSD)
mangiano una frazione enorme del rischio dichiarato. Stessa dinamica
"pesa di più sugli stop stretti" già documentata altrove in questa
sessione, qui portata all'estremo dalla scelta di SL a barra singola.

**Perché la fonte mostra 76%/2%**: la finestra di un mese mostrata (2-28
aprile) è visibilmente un trend pulito e continuo nello screenshot —
condizione in cui un filtro di trend semplice funziona quasi sempre.
Nessuna validazione Out-of-Sample, stesso schema già diffidato tutta
questa sessione (lezione #4: "un PF spettacolare su un campione
minuscolo è un'ipotesi, non un risultato").

Nessuna delle nostre strategie esistenti viene adattata a questa logica
— la verifica indipendente non supporta la promessa della fonte.

244 test verdi.
