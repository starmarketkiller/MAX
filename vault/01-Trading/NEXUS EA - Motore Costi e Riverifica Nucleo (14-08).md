---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, backtest-engine, costi, crt, turtle-soup, nucleo]
created: 2026-08-14
updated: 2026-08-14
---

# NEXUS EA — Motore Costi e Riverifica Nucleo (14/08)

## Il buco trovato: nessun test della sessione aveva mai applicato costi realistici

Partendo dalla validazione a 12 gate su SH_BMS_RTO_V2 (framework fornito
dall'utente), è emerso che **nessun test fatto in questa sessione — nè oggi
nè nei giorni precedenti — aveva mai applicato spread/slippage/commissione
realistici**. Tutti i verdetti "SOLIDA"/"promettente" del nucleo (CRT
compresa) erano su `cost_preset="none"`.

## Bug reale trovato e corretto nel motore

Applicando `retail_standard` (spread $2.50 + slippage $0.50 in R) su CRT,
l'equity crollava a valori negativi con trade successivi a "$0.00 fantasma"
— root cause: `spread_r = spread_price / risk_dist`, e CRT (stop ancorato al
wick, a volte pochi centesimi) genera `cost_r` fino a 50R+ su un singolo
trade, corrompendo tutta la size a seguire. **Fix approvato esplicitamente
dall'utente**: `MAX_COST_R_PER_TRADE = 5.0`, cap sul costo-in-R a chiusura
(non un cap sul lot size, scartato perché costo/rischio è scala-invariante
— nessuna size fix il problema, solo allargare davvero lo stop lo farebbe).
Applicato in `server/backtest.py`, entrambi i punti di calcolo costi.

## CRT — revisione più approfondita possibile, chiusa in modo definitivo

Su richiesta esplicita di non passare oltre finché CRT non fosse risolta.
Testate TUTTE le combinazioni ragionevoli su dati Dukascopy ampi
(bars=110000, XAUUSD, OOS 60-100%):

| Variante | Costi | PF | DD | Esito |
|---|---|---|---|---|
| floor MinStopATR 0/0.3/0.5/0.8 | none | 0.84-1.21 | 23-86% | edge grezzo reale ma sottile |
| stesso floor | retail | **0.08-0.25** | **100%** | conto azzerato su OGNI floor |
| + skip-filter invece di widen | retail | nessun miglioramento | — | |
| + breakeven 1R + trailing 1.0× (ricetta completa da `NXS_Profile_Get`) | none | 0.45-1.05 | 39-99% | **peggiora**, non migliora |
| stessa ricetta completa | retail | **0.02-0.11** | **100%** | invariato |

Nessuna combinazione di parametri salva CRT sotto costi realistici — il
problema non è il floor, è che il costo per trade è troppo grande rispetto
allo stop naturale, a qualunque frequenza di migliaia di trade. **CRT
disattivata in `NXS_Profile_Enabled` (NXS_StrategyProfiles.mqh), compilata
pulita (0 errori).**

Riconciliazione con analisi esterna parallela (Grok): il loro verdetto
"SOLIDA" (OOS PF~1.24) è lo stesso dato costless che avevamo anche noi prima
di oggi — il loro stesso documento walk-forward segnala "MT5 isolato: non
fatto (gap critico)". Nessuna vera contraddizione: due fasi dello stesso
processo, la seconda (costi) chiusa oggi qui.

## Riverifica nucleo-wide: prima flat, poi ricetta corretta (errore trovato e fissato)

Primo batch (16 strategie nucleo, SL/TP flat 1.5×/3.0×): 5 sopravvivono
a `PF_retail≥1.0, n≥30`. **Errore metodologico scoperto dopo**: SL/TP flat
non è la "ricetta ufficiale" per-strategia (`NXS_Profile_Get`), stesso
errore imputato a Grok su CRT. Rifatto con la ricetta vera di ciascuna
(slMult/tpMult/htf/beR reali dal codice):

| Strategia | TF | Ricetta | PF retail | n | DD retail | Esito |
|---|---|---|---|---|---|---|
| MACD | 4h | sl2.0/tp8.0/htf/be1.0 | **1.82** | 66 | 6.5% | ✅ migliorato vs flat (1.42) |
| SAR | 4h | sl1.5/tp4.0/htf | **1.38** | 129 | 10.2% | ✅ confermato |
| FVG_CONT | 4h | sl1.5/tp6.0/htf/be1.5 | **1.35** | 62 | 8.7% | ✅ migliorato vs flat (1.08) |
| LONDON_BO | 4h | sl1.0/tp4.5/htf | **1.50** | 43 | 11.7% | ✅ n più sottile della stima flat |
| EMA_PULLBACK | 1h | sl1.5/tp4.0/htf | **1.15** | 118 | 11.5% | ✅ stabile |
| TURTLE_SOUP | 1h | sl1.0/tp4.5/htf | 0.74 | 88 | 22.4% | ❌ migliora vs flat (0.55/63%DD) ma resta sotto 1 |
| AMD_CONT | 30m | sl1.5/tp3.0 | 0.81 | 164 | 28.1% | ❌ |
| LDN_REVERSAL | 15m | sl1.5/tp3.0 | 0.60 | 82 | 32.6% | ❌ |
| AMD_REVERSAL | 15m | sl1.5/tp3.0 | 0.96 | 64 | 15.4% | ❌ appena sotto |
| THREE_BAR_DELIVERY_BREAK | 4h | sl1.5/tp3.0/htf | 0.59 | 8 | — | ❌ campione troppo piccolo per giudicare comunque |
| ADX_RSI, BREAKOUT_ACC, LIQ_SWEEP | 1d | — | 2.0-4.0 | 12-19 | — | ⚠️ campione troppo piccolo, non dimostra nulla |

Sopravvissuti confermati con metodo corretto: **stessi 5** del batch flat
(SAR, LONDON_BO, MACD, EMA_PULLBACK, FVG_CONT) — la correzione ha cambiato i
numeri (a volte di molto: MACD/FVG_CONT migliorano, LONDON_BO peggiora) ma
non la lista finale. TURTLE_SOUP confermata sotto pareggio anche con la sua
vera ricetta (0.74, non più 0.55, ma comunque <1 su n=88 solido).

**Correzione (16/08, trovata durante un audit bug strategia-per-strategia)**:
la spiegazione sopra per TURTLE_SOUP era imprecisa. `TURTLE_SOUP` è in
`STRATEGY_SLTP_ALWAYS` (`_turtle_soup_sl_tp`, riga ~1806): il suo SL/TP è
SEMPRE strutturale (buffer 0.5×ATR sul refLow/refHigh dello sweep + target
fisso 2.0×rischio), i parametri `atr_sl`/`atr_tp` passati a `run_backtest`
sono ignorati per questa strategia (come già noto per CRT). Il
miglioramento PF 0.55→0.74 tra il batch flat e quello "a ricetta corretta"
NON viene quindi dal cambio di SL/TP (identico in entrambi i test) — viene
dall'unico altro parametro diverso tra i due giri: `htf_filter=True`. La
conclusione resta invariata (TURTLE_SOUP sotto pareggio, giustamente
disattivata), ma l'attribuzione del "perché" era sbagliata. Stesso discorso
vale per AMD_CONT/LDN_REVERSAL/AMD_REVERSAL/SH_BMS_RTO (anche loro in
`STRATEGY_SLTP_ALWAYS`), ma lì la ricetta "corretta" coincideva già con i
parametri flat usati nel primo batch, quindi nessuna discrepanza pratica
nei numeri, solo per TURTLE_SOUP la differenza era attribuita alla causa
sbagliata.

## Fase 0 eseguita: 4 strategie disattivate nel codice

`NXS_Profile_Enabled` (NXS_StrategyProfiles.mqh) — CRT, TURTLE_SOUP,
SH_BMS_RTO_V2, FVG_MIT_WINDOW → `false`, con commenti datati che linkano
l'evidenza. Sincronizzato nella cartella dati MT5 (robocopy additivo) e
ricompilato: **0 errori, 2 warning preesistenti non collegati**. Il nucleo
demo passa da 16 a 12 strategie attive.

## Varianti SAR testate (protocollo A/B, un cambio alla volta, costi retail)

| Variante | PF retail | n | DD retail | Verdetto |
|---|---|---|---|---|
| SAR base (sl1.5/tp4.0/htf) | 1.38 | 129 | 10.2% | baseline |
| + ADX≥20 gate | **1.11** | 107 | **14.1%** | ❌ peggiora tutto (PF giù, DD su) — archiviata |
| + cooldown 2/3 barre | 1.35/1.30 | 118/114 | 12.0%/11.8% | neutro-leggero negativo |
| **flip-only** (entry solo al cambio lato PSAR, non ogni barra di stato) | **1.96** | 48 | **4.2%** | ✅ promettente — PF e DD nettamente migliori, ma n più sottile (simile a LONDON_BO) |

`SAR_ADX20` e `SAR_FLIP` aggiunte come strategie EXPERIMENTAL in
`backtest.py`/`strategy-registry.json`, non ancora portate in MQL5.

## Addendum 16/08 — ultimo tentativo (multi-timeframe) testato e chiuso

Su richiesta esplicita dell'utente ("CRT è formidabile, bisogna saperla
usare — range su TF alto, trigger di entry su M1/M5"): costruita una
versione multi-timeframe vera (range/sweep su 4h come sempre, ma entry
rifinita sui dati M5 reali 2021-2026, unica finestra con dati M5
disponibili). Percorso (con gli errori trovati e corretti in diretta):

1. Entry al minimo/massimo M5 raggiunto dentro la barra 4h: **PF 1.07-2.42**
   con costi reali — primo PF>1 dell'intera indagine. Sembrava la svolta.
2. Debug strutturale (invarianti + determinismo, framework fornito
   dall'utente): trovato che il 12% dei segnali aveva il TP dal lato
   SBAGLIATO rispetto all'entry M5 (il prezzo dentro la barra a volte
   supera già il target prima che si possa "entrare" lì). Tolti quei
   segnali: PF sale ancora, fino a **8.87** — troppo alto per essere vero.
3. Causa di fondo trovata: scegliere il punto estremo di TUTTA la barra
   4h per l'entry è **hindsight bias** — nella realtà non sai in anticipo
   quale candela M5 dará il prezzo migliore, un limite va piazzato PRIMA
   con dati già chiusi, non scelto a posteriori.
4. Ricostruito con un vero ordine a limite (prezzo deciso da dati della
   sola candela di sweep GIA' chiusa, riempito solo se M5 lo tocca
   scorrendo in avanti, altrimenti trade non eseguito): **PF torna a
   0.55/0.70** (retail/ECN), sotto pareggio come ogni altra variante. Il
   breakeven a +0.5R peggiora ulteriormente (0.23/0.41) invece di aiutare.

**Verdetto finale**: l'idea multi-timeframe, l'unica mai rimasta non
testata, è stata implementata e testata onestamente (dopo due falsi
positivi dovuti a bias di misurazione, non di strategia) — fallisce come
tutte le altre. Nessuna variante di CRT testata in tre giorni (single-TF,
floor 0/0.3/0.5/0.8, skip-filter, breakeven+trailing, multi-TF con e
senza limite reale) sopravvive a costi realistici. Chiusura considerata
definitiva. Lezione di metodo per il futuro: qualunque tecnica di
"raffinamento dell'entry" che guarda dentro una finestra di dati per
scegliere il prezzo migliore va sempre verificata per hindsight bias
prima di fidarsi del PF, indipendentemente da quanto il numero sembri
buono — anzi, PIÙ il numero sembra buono, più va sospettato.

## Addendum 16/08 (2) — pacchetto composito finale (bias+sessione+sweep+TP50%)

Ultimo pacchetto ragionato (ricerca esterna su varianti CRT pubbliche:
bias HTF, killzone di sessione, sweep minimo in ATR, TP a metà range),
testato per intero su 7 anni, entry OPEN (fedele alla fonte originale del
pattern, vedi commento storico in `_crt_series` — v1 usava l'apertura
della candela 3, cambiato a chiusura solo per la convenzione del motore,
non perché sbagliato), costi scalati sul prezzo storico (fix 15/08):

| Configurazione | PF retail | PF ECN | n |
|---|---|---|---|
| Baseline (solo OPEN + costi scalati) | 0.210 | 0.688 | ~20750 |
| Solo filtro sessione (London/Overlap/NY) | 0.277 | **0.810** | 12114 |
| Sessione + sweep minimo 0.15×ATR | 0.173 | 0.605 | 7267 |
| Bias HTF+sessione+sweep+floor (TP pieno) | 0.191 | 0.698 | 3401 |
| Pacchetto completo (+ TP a 50% del range) | 0.042 | 0.296 | 2770 |

Il filtro sessione da solo è il **miglior risultato dell'intera indagine
di 3 giorni** (PF 0.81 ECN) — ma resta sotto pareggio. TP a metà range
(anziché il lato opposto) è il singolo cambiamento più dannoso trovato
(taglia il rapporto rischio/rendimento più di quanto il win rate
migliori). Combinare filtri non aiuta mai: ogni filtro aggiuntivo taglia
campione senza guadagno proporzionale.

**Chiusura definitiva**: nessun angolo ragionevole rimasto — pattern
base, floor (4 valori), skip-filter, breakeven+trailing, multi-TF con e
senza hindsight bias, entry OPEN vs CLOSE, segnale invertito, slippage di
apertura, costi scalati sul prezzo storico, bias HTF, killzone di
sessione, sweep minimo, TP a metà range, tutte le combinazioni — tutto
testato onestamente in tre giorni, nessuna variante supera PF 1 con costi
realistici. Il pattern grezzo (senza costi) ha un edge reale (~PF 1.2),
ma è strutturalmente troppo sottile per la sua frequenza di trade e la
strettezza naturale dello stop.

## Addendum 16/08 (3) — filtro posizione candela di range (pivot), primo PF>1 ma non stabile

Domanda dell'utente: la candela di RANGE (k-2) va presa ovunque capiti
nella serie, o dovrebbe essere in una posizione significativa (vicino a
un pivot/livello di liquidità)? Verificato: il codice base (`_crt_series`)
**non ha mai avuto nessun filtro del genere** — controlla letteralmente
ogni tripletta di 3 candele consecutive.

Testate due ipotesi dell'utente separatamente:
- **Forma della candela di range** (spike sopra E sotto ≥0.1×ATR): non
  aiuta (ECN 0.688→0.664, leggermente peggio).
- **Posizione vicino a un pivot** (entro 0.3×ATR da un massimo/minimo
  swing a 20 barre, calcolato solo su dati precedenti la candela di
  range - nessun look-ahead): **PF ECN 0.688→1.081**, n=4787 — primo PF
  sopra 1 con costi realistici in tutta l'indagine.

Verificato subito su walk-forward 5 finestre (stesso standard usato il
15/08 per le altre strategie) prima di fidarsene:

| Finestra | PF ECN | PF retail |
|---|---|---|
| 0 (2019-2020) | 0.99 | 0.37 |
| 1 (2020-2022) | 1.09 | 0.44 |
| 2 (2022-2023) | 0.54 | 0.10 |
| 3 (2023-2025) | 0.43 | 0.08 |
| 4 (2025-2026) | 2.66 | 1.43 |

**Non stabile** — il PF aggregato 1.08 è quasi interamente trainato dalla
finestra 4 (il rally recente). Nelle finestre 2-3 il filtro va molto
peggio del baseline stesso (0.10/0.08 a costi retail). Stesso fenomeno di
dipendenza dal regime già trovato il 15/08 su SAR/MACD/LONDON_BO/
EMA_PULLBACK/FVG_CONT — non un edge stabile, il mercato recente rende
bene qualunque cosa assomigli a trend-following.

Vicino a PDH/PDL (massimo/minimo del giorno prima) invece non aiuta
affatto (ECN 0.51, n=2048) — il pivot a 20 barre "generico" funziona
meglio (quando funziona) del livello specifico PDH/PDL.

**Conclusione**: anche l'ultima idea con segnali genuinamente promettenti
in aggregato non supera il test di stabilità. Chiusura di CRT confermata
su ogni fronte misurabile, incluso questo ultimo filtro.

## Prossimi passi aperti
- SAR_FLIP: verificare stabilità su walk-forward (n=48 è sottile) prima di
  considerarla per il porting MQL5.
- Dossier Gate 2-11 del Validator Framework non necessario per SH_BMS_RTO_V2
  (già chiuso a Gate 1 con dati sufficienti: PF 0.75-0.89 su n=140).
- Foglio S0 (struct audit) di LONDON_BO/MACD ancora da fare.
- Cap sul lot size in research (non solo cap-R) resta in backlog — non
  urgente con CRT chiusa, utile solo se si riapre in futuro.

Vedi anche [[NEXUS EA - Rischio a Livelli e Moltiplicatore da Streak (12-08)]]
(i tier di rischio ora vanno aggiornati per riflettere queste disattivazioni),
[[NEXUS EA - Fase C Recovery Baseline e Rischio Flottante (11-08)]] (origine
del floating DD 107% di CRT), [[NEXUS EA - 50 Maestri del Trading, Sintesi e
Confronto col Nucleo (14-08)]].

## Collegamenti
[[MOC - Trading]]
