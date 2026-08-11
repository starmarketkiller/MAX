---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, malaysian-snr, msnr, smc, ict, porting, specifica-tecnica]
strategia: MALAYSIAN_SNR
created: 2026-08-10
updated: 2026-08-10
---

# MALAYSIAN_SNR — Specifica tecnica per il porting Tier 1

Documento di progettazione, non codice. Obiettivo: ridisegnare
`MALAYSIAN_SNR` per riflettere davvero la fonte
[[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]] invece della
semplificazione attuale ("Support/resistance con storyline
fresh/flipped" — vedi [[Malaysian Snr]]), che cattura solo una
frazione della metodologia e soffre di una quasi-tautologia
strutturale (vedi sezione "Perché ora").

## Stato di partenza

- **`NXS_Strat_MalaysianSNR_Rejection`** (MQL5, `NXS_Strategies_SMC.mqh:520`)
  e **`sig_malaysian_snr`/`_malaysian_snr_series`** (Python,
  `server/backtest.py:1480`) sono fedeli tra loro (verificato riga-per-riga
  il 06/08), ma implementano solo: livelli H4 a 12 barre su chiusura,
  conferma W1 a 8 barre, filtro storyline H4+D1, esclusione sessione
  ASIAN. Restano **entrambi la baseline attiva** — questo documento
  descrive una v2 sperimentale, non una sostituzione immediata.
- **`MALAYSIAN_SNR_BREAKOUT`** (solo Python, sperimentale, registrata
  separatamente) inverte "tocco" in "chiusura oltre il livello" — un
  primo tentativo di rompere la tautologia, non la ricostruzione
  completa della fonte. Vedi risultati diagnostici nella sessione del
  10/08 (30m: PF 1.17/18 trade a periodo intero, non ancora incrociato
  IS/OOS per limiti di finestra dati).

## Perché ora

La versione "rejection" richiede *simultaneamente*: (a) il prezzo è
all'estremo delle ultime 12 barre H4, e (b) l'H4 recente (4 barre)
mostra già un'inversione di momentum nella direzione opposta. Le due
condizioni tendono a **contraddirsi**: se sei all'estremo del range a
12 barre, di norma le ultime 4 non stanno ancora "recuperando",
altrimenti non saresti più all'estremo. Risultato empirico coerente:
0-3 trade su ogni timeframe testato (vedi Fase 4 della sessione,
matrix a 5 TF). Il libro risolve esattamente questo separando la
**zona** (tocco HTF con rifiuto) dal **trigger** (breakout su un TF
più basso, con pullback) — due eventi in sequenza, non una condizione
sola.

## Architettura dati necessaria (il cambio più grande)

Il codice attuale è **stateless a livello di segnale** (una funzione
`sig_*(c, ind, i)` pura, tutta la storia serve solo per calcolare
soglie). La fonte richiede invece una **memoria persistente fra
barre**: un livello SNR identificato oggi resta vivo (fresh → unfresh
→ eventualmente flip) per settimane, e un tocco HTF apre una finestra
di attesa multi-barra per il trigger LTF. Serve lo stesso pattern già
usato in questo codebase per zone con memoria — vedi `_ob_series`
(`server/backtest.py:2516`, un registro di zone attive con stato
`{active, lo, hi, bars_waited}` per direzione, consumate one-shot al
retest o scadute dopo `MAX_WAIT` barre) e `_silver_bullet_series`.
Il porting Tier 1 generalizza quel pattern da "una zona attiva per
direzione" a **un registro di livelli SNR**, ciascuno con il proprio
stato.

Struttura dati proposta (uno per timeframe HTF tracciato, es. H4 e D1):

```
level = {
    "price": float,          # il close-pivot, non un range
    "role": "support" | "resistance",
    "status": "fresh" | "unfresh" | "flipped",
    "created_i": int,        # barra di formazione
    "last_touch_i": int | None,
    "touch_count": int,      # per il filtro MISS (sezione 4)
}
registry = {"support": [...], "resistance": [...]}  # o lista unica con "role"
```

Pruning necessario per costo computazionale: mantenere solo gli ultimi
N livelli per ruolo (es. 20) e scartare quelli mai ritoccati dopo M
barre (es. 200) — altrimenti il registro cresce senza limite su
storici lunghi e ogni barra deve scansionarlo tutto.

## Pilastro 1 — SNR close-to-open (V/A shape), non high/low

**Fonte**: si traccia la linea che collega CLOSE di una candela e OPEN
della successiva, ignorando gli stoppini. Resistenza = candela
rialzista (close>open) seguita da un'apertura più bassa del close
(forma "A" — picco). Supporto = candela ribassista seguita da
un'apertura più alta del close (forma "V" — valle).

**Algoritmo preciso** (sostituisce `max/min delle chiusure H4 a 12
barre`):

```
per ogni barra i (su un dato TF HTF, es H4):
    bull_i = close[i] > open[i]
    bear_i = close[i] < open[i]
    gap_down = open[i+1] < close[i]
    gap_up   = open[i+1] > close[i]
    if bull_i and gap_down:
        nuovo livello RESISTENZA a prezzo = close[i]
    if bear_i and gap_up:
        nuovo livello SUPPORTO a prezzo = close[i]
```

Nota: qui "gap" non è necessariamente uno spread giorno-notte — su
timeframe intraday indica solo che l'apertura successiva non replica
esattamente la chiusura precedente (quasi sempre vero salvo close
identico a open). Va deciso un valore di soglia minima (es.
`|open[i+1]-close[i]| > 0.05×ATR`) per evitare di generare un livello
a ogni singola barra — non specificato esplicitamente nella fonte,
prima incognita aperta da testare empiricamente.

## Pilastro 2 — Fresh / Unfresh / Flip

**Fonte**:
- Fresh: mai toccato da wick o body.
- Unfresh: già toccato (anche solo dal wick) — "liquidità già
  raccolta", livello più debole.
- Flip (RBS/SBR): un livello unfresh rotto da una **chiusura di corpo
  intera** inverte ruolo (supporto→resistenza o viceversa). Se poi
  ri-toccato **solo da un wick** (senza richiudere oltre), torna
  "fresh" nella nuova direzione — il livello più forte da tradare.

**State machine per livello** (eseguita ogni barra su ogni livello nel
registry):

```
per ogni livello L attivo, alla barra i:
    toccato_wick = (low[i] <= L.price <= high[i])
    rotto_corpo  = (L.role=="support"  and close[i] < L.price) or
                   (L.role=="resistance" and close[i] > L.price)
    if L.status == "fresh" and toccato_wick:
        L.status = "unfresh"; L.touch_count += 1; L.last_touch_i = i
    elif L.status == "unfresh" and rotto_corpo:
        L.role = "resistance" if L.role=="support" else "support"
        L.status = "flipped"
    elif L.status == "flipped" and toccato_wick and not rotto_corpo_nella_nuova_direzione:
        L.status = "fresh"   # ri-testato solo da wick dopo il flip -> livello piu' forte
```

## Pilastro 3 — "2 TF's Confirmation Rule" (il vero fix della tautologia)

**Fonte**: (1) il prezzo tocca un livello HTF fresh con un rifiuto
(wick, non chiusura oltre); (2) si scende di **due timeframe** per
cercare un breakout di struttura (BOS, chiusura di corpo piena oltre
uno swing) — qui il livello LTF *non* deve essere fresh; (3) Weekly
Setup → conferma su H4, Daily Setup → conferma su H1 (quindi anche
H4→M15 per coerenza con la granularità di questo EA); (4) al breakout
LTF, **aspettare il pullback** (spalla destra / livello QML) prima di
entrare.

**State machine di ingresso** (per ogni direzione, sostituisce il
trigger a condizione singola):

```
stato ∈ {IDLE, ATTESA_BOS_LTF, ATTESA_PULLBACK}

IDLE:
    se rifiuto su livello HTF fresh (wick tocca L, corpo chiude
    lontano da L nella direzione "giusta") e storyline concorde:
        stato = ATTESA_BOS_LTF; scadenza = i + MAX_WAIT_BOS (es. 12 barre LTF)

ATTESA_BOS_LTF:
    se scaduto: stato = IDLE
    se chiusura di corpo piena oltre uno swing LTF (stessa direzione):
        stato = ATTESA_PULLBACK; livello_bos = swing rotto
        scadenza = i + MAX_WAIT_PULLBACK (es. 8 barre LTF)

ATTESA_PULLBACK:
    se scaduto: stato = IDLE
    se prezzo ritorna verso livello_bos senza richiudere oltre (pullback):
        → SEGNALE, stato = IDLE
```

`MAX_WAIT_BOS`/`MAX_WAIT_PULLBACK` non sono specificati nella fonte —
seconda incognita aperta, da tarare empiricamente (stesso spirito di
`InpOB_MaxWaitBars=20` già usato per `_ob_series`).

## Pilastro 4 — Filtro "MISS" (spazio prima del retest)

**Fonte**: un livello va tradato solo se, tra la sua formazione e il
retest attuale, non ci sono stati micro-tocchi prematuri ("MISS" =
spazio pulito). Si traduce direttamente nel campo `touch_count` del
registro (Pilastro 2): richiedere `touch_count == 0` (o sotto una
soglia bassa, es. ≤1) al momento del rifiuto che apre la state machine
del Pilastro 3 — un livello già toccato più volte prima del setup
attuale viene scartato, non tradato.

## Pilastro 5 — Killzone Londra/NY

Il codice attuale esclude solo `session == "ASIAN"`; la fonte chiede
esplicitamente Londra/NY come **finestre di espansione**. Cambio
minimo (a differenza degli altri 4 pilastri, quasi pronto): la
sessione è già calcolata con granularità `ASIAN/LONDON/NY/OVERLAP`
(vedi altre strategie in `backtest.py`, es. riga 2127/2258/2308) — il
filtro va stretto a `session[i] in ("LONDON", "NY", "OVERLAP")`
esplicitamente, invece di limitarsi a escludere l'Asia.

## SL/TP — nota separata, non un pilastro strutturale

Gli esempi del libro mostrano RR molto ampi (1:20+), TP verso la
prossima struttura HTF, non un multiplo fisso di ATR. Coerente col
pattern già documentato nello screening del sito (TP largo batte quasi
sempre TP corto). Per la v2: SL sotto/sopra il livello di struttura
appena confermato (non un multiplo ATR fisso come oggi), TP al
prossimo livello SNR HTF opposto nel registro — non uno scalare, un
lookup nella stessa struttura dati del Pilastro 2. Va deciso un
fallback (multiplo ATR) per quando il registro non ha ancora un
livello opposto valido.

## Concetti citati ma non implementabili subito

- **QM/QML (Quasimodo Level)**: citato come riferimento d'entrata ma
  mai definito esplicitamente nella fonte letta finora. Serve altro
  materiale prima di poterlo specificare — per ora il pullback del
  Pilastro 3 usa lo swing rotto come riferimento, non un vero QML.
- **CRT (Candle Range Theory)**: range del giorno precedente, si
  osserva se la candela corrente chiude dentro quel range. Vicino
  concettualmente a `RANGE_FADE`/`DISP_REBAL` già nel codice — da
  valutare se è un filtro aggiuntivo qui o una strategia a sé, non
  deciso in questo documento.

## Piano di implementazione consigliato (ordine, non tutto insieme)

1. ✅ **Pilastro 1 isolato — fatto il 10/08** (`MALAYSIAN_SNR_V2_STAGE1`
   in `server/backtest.py`). Ipotesi di frequenza **confermata**: 24
   trade su 30m contro 3 della baseline, stesso ordine di grandezza su
   ogni TF (15m 22 vs 6, 1h 23 vs 4, 4h 10 vs 1, 1d 2 vs 0). Ma la
   profittabilità non segue automaticamente — split IS/OOS onesto su
   30m (l'unico TF con PF>1 a periodo intero): IS PF 1.36/15 trade
   (OK), OOS PF 1.05/9 trade (DEBOLE, campione al limite). 15m e 1h
   collassano sotto 1 in OOS. **Conclusione**: la sola identificazione
   dei livelli non basta a produrre edge — coerente con l'ipotesi che
   sia la "2 TF's Confirmation Rule" (Pilastro 3) a fare il lavoro
   vero, non il Pilastro 1 da solo. Non un fallimento dello stadio: è
   esattamente la domanda che doveva rispondere.
   
   Scoperto en passant durante questo stadio, corretto separatamente
   nella stessa sessione: `_malaysian_snr_series` (la baseline fedele
   all'MQL5) aveva un gate su `w1_idx<8` che bloccava l'intera
   funzione per ~1512 barre di lookback — nel vero MQL5 il livello W1
   è solo un bonus di score, mai un blocco. Rimosso: la baseline stessa
   ora produce 2-3× più trade a parità di logica.

2. ⏭️ **Pilastro 2 (Fresh/Unfresh/Flip) saltato per ora** — su
   richiesta esplicita, si è passati direttamente al Pilastro 3
   (vedi sotto), quello che la diagnosi indicava come decisivo. Resta
   nel piano per una fase successiva.

3. ✅ **Pilastro 3 — fatto il 10/08** (`MALAYSIAN_SNR_V2_STAGE3`).
   State machine per direzione (IDLE → ATTESA_BOS → ATTESA_PULLBACK →
   segnale, `SWING_LOOKBACK=15`, `MAX_WAIT_BOS=12`,
   `MAX_WAIT_PULLBACK=8`), costruita sopra i livelli close-to-open
   dello Stadio 1. Semplificazione dichiarata: "scendere di due
   timeframe" diventa qui H4 (livello) → serie base del test
   (BOS/pullback), non una camminata letterale sulla scala
   D1/H4/H1/M30.

   **Primo test (campione stretto, ~52 giorni per un bug di cap
   scoperto dopo)**: sembrava il risultato più "a forma di libro di
   testo" della sessione — 30m IS PF 1.8/11 trade, OOS PF 2.41/5
   trade, entrambi positivi. **Smentito dal retest con lo storico
   pieno** (~3,9 anni, dopo il fix del bug sotto): 15m IS PF 1.22/166
   trade (OK) → OOS PF 0.77/97 trade (CRITICA); 30m IS PF 0.74/70
   (CRITICA) → OOS PF 1.03/55 (DEBOLE); 1h IS PF 1.16/33 (OK) → OOS PF
   0.20/23 (CRITICA, WR 4.3%). **Nessun timeframe regge con un
   campione vero.** Il risultato incoraggiante di prima era esso
   stesso un miraggio da campione minuscolo — la stessa lezione
   ribadita un'altra volta, stavolta sulla propria diagnosi.

   **Bug scoperto ripetendo il test**: `_fetch_dukascopy` ignorava
   completamente il parametro `bars`, tagliando sempre alle ultime
   2500 barre indipendentemente dallo storico su disco — su 15m/30m
   questo e' un tetto di calendario di 26-52 giorni. Corretto
   (`server/backtest.py`, 10/08): ora rispetta `max(bars,
   _REAL_BARS_CAP)`. **Portata**: ha limitato silenziosamente OGNI
   test 15m/30m/1h di oggi che non passava `bars` esplicitamente (di
   fatto tutti).

## Ri-verifica di tutti i test 15m/30m/1h del 10/08 (dopo il fix)

Rieseguiti con `bars=60000` (storico Dukascopy pieno, ~3,9 anni,
campioni finalmente a 3-4 cifre invece di 5-30 trade):

- **Fase 4b (OTE_CONT/RSI_DIV)**: il risultato "più solido della
  serie" (RSI_DIV IS PF 1.36/OOS PF 1.16) **non regge** — con 432 IS
  e 302 OOS trade veri, PF 0.94/1.07 (CRITICA/DEBOLE), sostanzialmente
  breakeven. OTE_CONT confermato negativo come nella diagnosi
  originale (PF 0.77-0.99).
- **Fase 4 (9 strategie, TF naturali)**: tutte passano da POCHI_DATI
  (campione troppo piccolo per giudicare) a verdetti veri con
  campioni di 16-70 trade — e nessuna mostra edge robusto. Il meglio
  e' DEBOLE (WEEKLY_EXP, LDN_REVERSAL), il resto CRITICA. Chiusura
  onesta, non piu' "forse con altri dati": con dati veri, no.
- **Fase 3b — la scoperta piu' importante di questo giro, MA con una
  causa identificata che ne ridimensiona la portata**: il
  direction-lock BUY-only su 4h, con campioni ora enormi (54-114
  trade per lato), regge su **tutte e tre** MACD/TURTLE_SOUP/
  BREAKOUT_ACC, sempre FORTE sia IS che OOS, sempre meglio del
  proprio baseline senza lock (MACD 1.58→1.72, TURTLE_SOUP 1.96→2.60,
  BREAKOUT_ACC 1.75→2.74).

  **Approfondimento 10/08 (3) — perche': l'oro nella finestra testata
  e' salito del +160% (1.666→4.343 $, sia IS +76% sia OOS +48%
  fortemente rialzisti)**. SELL-only nello stesso periodo e'
  sistematicamente piu' debole di BUY-only su tutte e tre (es.
  TURTLE_SOUP SELL-only IS PF 0.47, BREAKOUT_ACC SELL-only OOS PF
  0.76) - la firma di un mercato in trend, non di un'asimmetria
  strutturale della logica. **Verifica decisiva**: isolato l'unico
  tratto davvero ribassista dentro il dataset (ultimi ~5 mesi, oro
  -16,2%, 5.187→4.343) e il pattern si INVERTE su tutte e tre -
  SELL-only diventa il lato piu' forte (MACD SELL PF 1.59 vs BUY
  troppo magro per giudicare; TURTLE_SOUP SELL PF 3.46 vs BUY 1.99;
  BREAKOUT_ACC SELL PF 1.70 vs BUY 0.99, appena sopra breakeven).

  **Conclusione onesta**: non e' un'edge BUY-only strutturale, e'
  un'edge "con il trend" - queste strategie catturano meglio la
  direzione dominante, qualunque essa sia, non il rialzo in se'.
  Il BUY-only ha funzionato finora perche' il trend e' stato quasi
  sempre rialzista in questi ~3,9 anni, non perche' l'oro "sale
  meglio di quanto scenda" nella logica delle strategie. Implicazione
  operativa: un filtro di direzione **dinamico legato al regime/trend
  in corso** (non un BUY-only statico) e' l'ipotesi piu' difendibile
  da testare dopo - riprende l'idea di "cambio di strategia per
  regime" gia' esplorata prima nella sessione (allora inconcludente
  per campione troppo piccolo), ora con un meccanismo molto meglio
  identificato (allineamento direzione/trend) e un vero tratto
  ribassista su cui verificarla, anche se corto (~5 mesi). Non ancora
  implementato ne' portato in MQL5.
- **Stadio 1 di MALAYSIAN_SNR**: confermato invariato nella sostanza
  - nessun TF mostra edge consistente IS+OOS anche con campioni di
    100-280 trade. La sola identificazione dei livelli non basta,
    come gia' concluso, ora su base statistica molto piu' solida.
2. **Pilastro 2 + registro**: aggiungere fresh/unfresh/flip come
   struttura dati, ancora senza il Pilastro 3 — verificare che il
   registro non esploda in dimensione su uno storico lungo (pruning).
3. **Pilastro 3** (il pezzo che risolve la tautologia): la state
   machine a 2 TF, la parte più delicata da testare in isolamento
   prima di comporla con gli altri pilastri.
4. **Pilastro 4 e 5** per ultimi: filtri che riducono frequenza, più
   facili da validare quando i pilastri 1-3 già producono un flusso di
   segnali misurabile.

Registrare ogni stadio come strategia Python separata (come già fatto
per `MALAYSIAN_SNR_BREAKOUT`), mai sovrascrivere la baseline fedele
all'MQL5 attuale — permette di confrontare ogni stadio contro quella e
contro lo stadio precedente.

## Criteri di validazione

Stesso schema usato in tutta la sessione del 09-10/08: split
in-sample (60%)/out-of-sample (40%), parametri (soglie di
`MAX_WAIT_*`, tolleranze ATR) scelti **solo** su IS, verdetto letto
**solo** su OOS, minimo 8 trade per considerare un verdetto (sotto
quella soglia: POCHI_DATI, non un giudizio). Dato il costo
computazionale più alto (registro di livelli + state machine multi-TF
invece di una funzione stateless), preferire test su un singolo TF
alla volta invece di scansionare 5 TF × 4 stadi in un colpo solo.

## Variante RETEST (11/08) — quarto pattern, descritto dall'utente da trader manuale

L'utente usa questa strategia manualmente da tempo e ha descritto il
proprio modello mentale: rottura di un key level (massimo/minimo o
struttura) + breve ritracciamento **sulla stessa linea rotta** (ora
S/R capovolta) + continuazione. Confrontato con le 3 varianti già
testate, **non corrisponde a nessuna**:

- **MALAYSIAN_SNR (rejection)**: il livello non si rompe mai, si
  rimbalza sull'estremo H4 intatto — l'opposto.
- **MALAYSIAN_SNR_BREAKOUT**: entra SUBITO alla rottura, nessuna attesa
  del ritracciamento.
- **Stadio 3 (2 TF's Rule)**: parte da un RIMBALZO (non una rottura),
  poi cerca uno swing SEPARATO formatosi dopo — il pullback è su quello
  swing, non sul livello H4 originale.

Implementata come quarta variante, `MALAYSIAN_SNR_V2_RETEST`
(`server/backtest.py`, `_malaysian_snr_v2_retest_series`): rottura
fresca del livello H4 (stesso evento di `snr_brk_signal`, sulla
candela H4) → stato `ATTESA_RETEST` (max 12 barre) → segnale quando il
prezzo rientra nella **zona** del livello rotto con una candela di
reazione nella direzione della continuazione, invalidato se richiude
oltre la zona dalla parte sbagliata (il breakout fallisce/viene
riassorbito).

**Zona, non linea**: l'utente ha segnalato che il prezzo raramente
ritraccia esattamente sul prezzo del livello — trattata come una
piccola zona (~50 pip XAUUSD). **Assunzione da confermare**:
`ZONE_WIDTH_PRICE = $5.0`, convenzione MT5 "punti" per l'oro
(quotazione a 2 decimali, es. 2650.32) dove 50 pip ≈ $5.00. Se la
convenzione dell'utente è diversa (es. 1 pip = $0.01 → $0.50, dieci
volte più stretta), i risultati sotto cambiano e vanno rifatti.

### Risultati diagnostici (XAUUSD, storico Dukascopy pieno, IS 60%/OOS 40%)

| TF | IS PF / n | OOS PF / n |
|---|---|---|
| 4h | 1.31 / 22 | 0.35 / **5** (troppo pochi per giudicare) |
| 1h | 1.23 / 137 | **0.81** / 35 (campione credibile, negativo) |
| 30m | 1.06 / 284 | **1.24** / 103 (campione credibile, positivo ma modesto) |

**Non conclusivo, misto tra timeframe**: a 1h l'OOS è sott'acqua
(campione grande, quindi non un caso di rumore da pochi trade), a 30m
è leggermente positivo su un campione ancora più grande. Nessun walk-
forward multi-finestra ancora fatto (a differenza di BREAKOUT_ACC+
regime) — prima di trarre conclusioni serve lo stesso trattamento.
Nessuna controparte MQL5, stesso status delle altre varianti "_v2"
(EXPERIMENTAL, `research_implementation=True`, `live_implementation=
False`, registrata in `contracts/strategy-registry.json`).

### Caratterizzazione delle zone OC (11/08) — perché il retest è fondato

Richiesta di seguito dall'utente: prima di validare ulteriormente
RETEST, capire empiricamente cosa succede davvero sui livelli OC quando
il prezzo li ritocca (`server/research_scripts/msnr_oc_zone_diagnostic.py`,
storico Dukascopy pieno, 4h).

**Frequenza** (638 livelli OC formati, 97% ritoccati entro 60 barre):
- **60% TENGONO** (rimbalzo/rifiuto) — l'inversione è il comportamento
  più comune sui livelli OC, più della rottura.
- **40% si ROMPONO** (continuazione) — di questi, **91% fa retest entro
  12 barre**. Conferma indipendente e su campione ampio che aspettare il
  retest dopo una rottura (il pattern che l'utente ha descritto da
  trader manuale) è statisticamente ben fondato, non un caso raro.

**P&L della continuazione immediata** (rottura del livello OC, entra
subito, NESSUNA attesa di retest — il pezzo che ancora mancava:
`MALAYSIAN_SNR_BREAKOUT` usa i livelli VECCHI a 12 barre, non questi
OC): IS 37 trade PF 0.74 (in perdita), OOS 32 trade PF 1.88. **Non
affidabile** — con la disciplina IS-blind di tutta la sessione questa
configurazione non verrebbe nemmeno scelta (il numero attraente è solo
sull'OOS, l'IS dice il contrario). Entrare subito alla rottura non paga
in modo consistente; aspettare il retest resta l'ipotesi più solida.

### Walk-forward su MALAYSIAN_SNR_V2_RETEST (11/08) — mai netto come BREAKOUT_ACC/SAR

5 finestre sequenziali, 1h e 30m (`msnr_retest_walkforward.py`):

| Finestra | 1h PF/n | 30m PF/n |
|---|---|---|
| 1/5 | 1.26/47 | 1.17/98 |
| 2/5 | 0.87/56 | 1.04/108 |
| 3/5 | 1.88/35 | 1.00/79 |
| 4/5 | 1.10/23 | 1.85/67 |
| 5/5 | 0.43/12 | 0.66/36 |

**Misto su entrambi i TF, nessun pattern pulito**: 3/5 finestre sopra 1
su entrambi, ma senza la coerenza vista con BREAKOUT_ACC+regime (vince
3/5 con motivazione strutturale) o SAR+WEAK_TREND (vince 5/5 su 5).
Oscilla troppo per essere già un candidato — non smentito, ma nemmeno
confermato. La caratterizzazione delle zone OC sopra (91% retest dopo
rottura) resta un fondamento statistico solido per il PATTERN in
generale; il P&L specifico di questa implementazione (SL/TP/zona
scelti) non lo è ancora altrettanto.

### Gate/confluenze aggiuntivi (11/08) — un gate "fuori range" aiuta, gli altri due no

⚠️ **Correzione 11/08 (2)**: il gate sotto chiamato "CRT" **non è la vera
Candle Range Theory**. L'utente ha caricato il PDF fonte (Suven Raj,
"Candle Range Theory") e la vera CRT è un pattern preciso a 3 candele
(range → sweep con chiusura dentro il range → entrata nella direzione
opposta, target il lato opposto del range) — vedi sezione dedicata più
sotto. Quello testato qui era solo "prezzo fuori dal range del giorno
precedente", una mia semplificazione con lo stesso nome per errore.
Ridenominato **"gate fuori-range"** per non confonderlo con la CRT vera
(che invece, testata correttamente, non ha mostrato nessun edge — vedi
sotto).

Su richiesta esplicita dell'utente ("proviamo più versioni, non solo la
fonte, basta che ci sia motivazione e prova"): tre gate testati su
RETEST con selezione IS-blind + verifica OOS (`msnr_retest_gates.py`),
ciascuno con una motivazione precisa, non a caso.

- **Regime STRONG_TREND** (ipotesi: RETEST è un pattern di
  continuazione, come BREAKOUT_ACC): **non regge** — peggiora l'IS su
  entrambi i TF, scartato dalla selezione disciplinata su entrambi.
- **Confluenza LIQ_SWEEP** (idea dell'utente: un segnale RETEST è più
  forte se coincide con un vero sweep di liquidità entro poche barre,
  stesso principio del Marriage Concept ma con liquidità invece di
  trendline): campione troppo sottile dopo il filtro su entrambi i TF
  (1h: 1 trade OOS con PF "inf" — scartato subito come inutilizzabile).
  Ipotesi non verificabile con questi dati, non smentita.
- **Gate fuori-range** (prezzo fuori dal range max/min del giorno
  precedente — NON la vera CRT, vedi correzione sopra): **aiuta a
  30m**, scelto dalla selezione IS-blind, confermato su OOS (PF
  1.12→1.22, campione 103→58 trade) e su walk-forward a 5 finestre
  (**vince 4 finestre su 5**, perde solo la prima di poco). Non aiuta a
  1h (non scelto dalla selezione IS-blind lì).

**Conclusione onesta**: delle tre idee "fuori dallo schema" testate,
una regge (gate fuori-range a 30m), una non regge (regime), una resta indecisa per
campione insufficiente (confluenza liquidità).

### Vera Candle Range Theory (11/08) — registrata come strategia, forte su oro, non su BTC

Dal PDF fonte caricato dall'utente ("Candle Range Theory" di Suven Raj):
pattern preciso a 3 candele **consecutive** sullo stesso timeframe
(qualunque - Daily/H4/H1/M1, non fisso):
1. Candela 1 = **Range** → CRH/CRL (high/low di quella candela).
2. Candela 2 = **Sweep** → stoppino oltre CRH (o CRL) ma **chiusura
   dentro** il range (se chiude oltre, il setup è invalido — il mercato
   sta continuando, non invertendo).
3. Candela 3 = **Entrata** → direzione opposta allo sweep, target il
   lato opposto del range.

**Tre versioni prima di arrivare a quella giusta** (`crt_diagnostic.py`,
poi registrata in `backtest.py` come `CRT`):

- **v1**: 3 candele distinte come vuole la fonte, ma simulava l'entrata
  all'APERTURA della candela 3 — numeri vistosi (4h OOS PF 1.63/442,
  30m walk-forward 5/5) ma non corrispondenti a come esegue davvero
  `run_backtest` (`px = candles[i]["close"]` — entra sempre alla
  CHIUSURA della barra del segnale, mai alla sua apertura).
- **v2**: "corretta" fondendo sweep+entrata nella stessa candela per
  allinearsi alla chiusura del motore — ma così lo stop (estremo della
  candela sweep) finiva innaturalmente vicino alla chiusura di quella
  STESSA candela, tradendo la fonte (candela 3 dev'essere nuova e
  separata). Risultato: nessun edge su nessun TF (falso negativo).
- **v3 (quella giusta)**: 3 candele distinte come in v1, ma segnale
  registrato SULLA candela 3 così che il motore esegua alla sua
  chiusura (non alla sua apertura come in v1, né fusa con lo sweep
  come in v2) — sintesi corretta fonte+motore.

**Risultato v3, verificato attraverso `run_backtest` (non solo lo
script standalone) — walk-forward a 5 finestre**:

| TF | Finestre PF | Walk-forward |
|---|---|---|
| 4h | 1.04, 1.31, 1.01, 2.01, 1.11 | **5/5 sopra 1** |
| 1h | 1.06, 1.72, 0.85, 1.15, 1.30 | 4/5 sopra 1 |
| 30m | 1.17, 1.37, 1.21, 1.48, 1.23 | **5/5 sopra 1, range strettissimo** |

Campioni enormi (210-1470 trade a finestra) — il risultato più solido
di tutta la sessione, walk-forward più pulito persino di BREAKOUT_ACC+
regime (che vinceva 3/5) o SAR+WEAK_TREND (5/5 ma campioni di 40-80).

**Non confermata su BTC** (1d/4h/1h, OOS PF 0.87-1.09, IS 0.92-1.19 —
nessun edge chiaro) — stessa storia di LIQ_SWEEP+regime e del gate
fuori-range oggi: probabilmente un pattern legato alla struttura di
sessione dei mercati come oro/forex (liquidità che si forma e viene
"cacciata" agli estremi di sessione), non un edge universale su un
mercato 24/7 come BTC.

**Registrata come `CRT`** in `backtest.py`/`contracts/strategy-registry.json`
(EXPERIMENTAL, `research_implementation=True`, `live_implementation=
False`, nessuna controparte MQL5).

**Lezione di metodo**: un risultato eccezionale merita PRIMA una
verifica di coerenza con la convenzione di esecuzione del motore, non
solo un walk-forward — sia v1 (falso positivo) sia v2 (falso negativo)
avrebbero superato un walk-forward "pulito" sui propri termini, solo
il confronto diretto con `run_backtest` ha rivelato quale delle due
correzioni fosse quella giusta.

## Cosa NON tocca questo documento

- Nessun cambio al MQL5 live (`NXS_Strat_MalaysianSNR_Rejection`
  resta la strategia in produzione finché la v2 non è validata in
  Python, stesso principio già seguito per ogni altro porting di
  questa sessione).
- Nessuna implementazione di codice — solo architettura. Il prossimo
  passo esecutivo è il punto 1 del piano sopra.

## Collegamenti
[[MOC - Trading]] · [[Malaysian Snr]] ·
[[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]] ·
[[NEXUS EA - Setup Buy-Sell — Framework]] ·
[[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]
