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
