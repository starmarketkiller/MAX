---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, ict, smc, turtle-soup, sh-bms-rto, pdf-library, revisione]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — Revisione contro materiale esterno: Turtle Soup, SH+BMS+RTO, catalogo PDF (03/09)

## Perché

L'utente ha mandato sul PC ~34 PDF di trading (tutti insieme, sync da
telefono in `Downloads\Mobile Devices\`) e ha chiesto di analizzarli
concentrandomi su logiche a immagini, metodi di ingresso, mindset,
gestione — parte della Fase 3 del
[[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]].
Molti di questi PDF sono immagine-pura (poco testo estraibile), quindi
letti pagina per pagina come slide, non come testo.

## Nota tecnica: come leggerli

Il tool nativo di lettura PDF di Claude Code dipende da `pdftoppm`
(poppler), **non installato su questa macchina** — fallisce su ogni PDF.
Soluzione: `pymupdf` (pacchetto Python, presente ma installato per
Python 3.12, non per l'alias `python3`/3.14 di default — usare
`C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe`
esplicitamente) per estrarre testo E per renderizzare le pagine come
PNG (`page.get_pixmap(dpi=110).save(...)`), poi leggere i PNG. Utile
saperlo per la prossima volta invece di riscoprirlo.

## Primo PDF letto: "All You Need To Know" (WADE_FX_SETUPS, 153 pagine)

Quasi tutto immagini (21.691 caratteri di testo su 153 pagine — un
deck di slide, non un libro). Indice: Basics (expansion/retracement,
BMS, failure swing), Market Structure, Liquidity (BSL/SSL, stop hunt),
Order Blocks, Daily Range Price Action (sessioni, AMD), **Powerful
Setups** (Turtle Soup, SH+BMS+RTO, SMS+BMS+RTO, AMD), Confluence +
HTF/LTF, Marked Up Charts.

**Il contenuto è quasi interamente ICT/SMC classico — la stessa base
concettuale su cui è già costruita gran parte del motore NEXUS**
(TURTLE_SOUP, SH_BMS_RTO, SMS_BMS_RTO, AMD_*, PO3, liquidity sweep sono
già implementate). Quindi il valore maggiore qui non è "scoprire
concetti nuovi" ma **verificare che l'implementazione rispetti la
definizione originale** — ed è emerso subito un gap concreto:

### Trovato: TURTLE_SOUP non verifica la profondità dello sweep

Definizione del libro (pag. 85, "Turtle Soup Long"): il prezzo deve
superare un minimo di riferimento (PDL, LOD, vecchio minimo, minimi
uguali) di **5-20 pip** — non di più, non di meno. Uno sweep troppo
grande non è più manipolazione, è un vero breakout; SL minimo fisso a
10 pip.

`NXS_Strat_TurtleSoup` (`NXS_Strategies_SMC.mqh:24`) invece: controlla
solo `sw.sweptPDH/EQH/PDL/EQL` (booleano, dal rilevatore di sweep) +
corpo candela ≥0.4×ATR + chiusura oltre il livello — **nessun controllo
sulla PROFONDITÀ dello sweep**. Uno sweep di 2 pip e uno sweep di 80 pip
passano allo stesso modo, mentre per il libro solo il primo è un vero
setup Turtle Soup (l'altro è probabilmente un breakout reale, il
contrario esatto della tesi "manipolazione poi ritorno").

**Non ancora corretto nel codice** — è una modifica a una strategia
attiva, e "5-20 pip" è un'unità forex-centrica che va tradotta per
GOLD (probabile equivalente: una banda in ATR, es. 0.1-0.5×ATR, da
calibrare — NON applicare il numero forex alla lettera). Proposta per
la prossima sessione: aggiungere un controllo
`sweepDepth = |closePrice - refLevel|` limitato a una banda ATR-relativa,
testare isolato su MT5 prima/dopo per vedere se filtra i falsi
positivi (sweep troppo ampi che sono breakout veri, non trappole).

### Confermato: SH_BMS_RTO è già fedele alla definizione del libro

Definizione del libro (pag. 89): sweep di un minimo (X) → rottura di
struttura (BMS, chiusura oltre lo swing precedente) → ritorno in una
zona "origine" (l'ultima candela di colore opposto prima
dell'impulso) → entrata lì, stop sotto la zona, primo target il livello
di BMS.

`NXS_SHBMS_UpdateSide` (`NXS_Strategies_SMC.mqh:402`) implementa
esattamente questo: stato SWEPT → verifica MSS (chiusura oltre
`st.swingRef` con corpo ≥`InpSHBMS_DispBodyATR`×ATR) → zona origine
= "ultima candela di colore opposto prima del displacement" (loop
`k=2..6` cercando `oppositeColor`) → stato WAITING_RETURN. Corrispondenza
1:1 con il diagramma. Nessuna azione richiesta, solo confermato per
la prima volta contro la fonte.

### Framework di confluenza (sez. 7, per Fase 2 del piano)

"HTF key levels" (Order Block, Liquidity Pool, Market Structure sul
timeframe alto) usati per raffinare gli ingressi sul timeframe basso —
esplicitamente **non tutti i livelli HTF vanno raffinati**, è un filtro
opzionale caso per caso, non una regola fissa. Rilevante per la Fase 2
del piano d'azione (conferme/correlazioni tra strategie) — NEXUS ha
già un concetto simile (`InpUseInstitutionalCore`/HTF bias) ma non è
mai stato collegato al percorso a profili usato in tutti i test di
questa sessione (stesso pattern del veto di regime, mai agganciato).

## Catalogo completo dei 34 PDF (per tracciare cosa resta da leggere)

Tutti in `C:\Users\User\Downloads\Mobile Devices\`. Stato: ✅ letto,
🔶 letto parzialmente, ⬜ non ancora aperto.

**Generali / non-ICT specifici (priorità alta — meno probabile che sia già coperto)**
- 🔶 `allyouneedtoknow...pdf` (153p, ICT/SMC) — sez. 1-5, 8 non ancora lette
- ⬜ `candlesticksfibonacciandchartpatterntrading-forexfactory...pdf` (273p, **l'unico con testo estraibile vero** — 360K caratteri, probabilmente un libro classico su candele/Fibonacci/pattern grafici — priorità alta, si presta a lettura testuale invece che immagine per immagine)
- ⬜ `797807669-trading-book.pdf` (51p, quasi tutto immagini)
- ⬜ `643335252-Simple-Trading-Book-Trading-Smart.pdf` (26MB, non ancora aperto)
- ⬜ `flippingmarkets1-...pdf` (59p)
- ⬜ `technicalanalysisinforexprinciplessupportresistancekey-...pdf` (12p, breve — supporti/resistenze)
- ⬜ `820178565-Top-10-Most-Profitable-Trading-Strategies...pdf`
- ⬜ `755214418-BinaryPatterns.pdf`
- ⬜ `541324475-Support-and-Resistance-Trading-Strategy.pdf`
- ⬜ `692042405-100-SCREENSHOT-SETUP-SNR-CONTINUATION.pdf`

**ICT/SMC specifici (priorità media — verificare implementazione come per Turtle Soup sopra)**
- ⬜ `inversefairvaluegapifvginicttradingstrategiesguide-...pdf`
- ⬜ `whatisthesmartmoneyconcept-...pdf`
- ⬜ `icttradingstyleabbreviationsandterminologiesfvgsobspo3mmxm-...pdf`
- ⬜ `ict-trading-250828073107-...pdf`

**CRT (Candle Range Theory) — già una nota vault dedicata dall'11/08, priorità bassa salvo dettagli nuovi**
- ⬜ `754092222-CRT.pdf`, `889821823-CRT-TBS-ebook.pdf`, `942591252-CRT-SECRETS-SERIES.pdf`,
  `951747974-The-CRT-Enigma...pdf`, `796237872-Romeo-Written-CRT-Unlocked.pdf`,
  `878992448-Mastering-CRT-by-Maher-Only.pdf`

**SNR Malaysia (già implementata come MALAYSIAN_SNR, priorità bassa salvo dettagli nuovi)**
- ⬜ `Malaysian SNR Emperor.pdf`, `SNR Malaysia.pdf` (+dup), `My Rare SNR Course.pdf` (+2, +dup)

**Sequence / Secret Of 411 / Alchemist (non ancora chiaro il contenuto)**
- ⬜ `Sequence.pdf`, `Sequence_1.pdf`, `Sequence_2_unlocked.pdf` (+dup)
- ⬜ `Secret Of 411(1).pdf`
- ⬜ `863955768-MSNR-x-SMC-x-ICT-the-Alchemist-Yanu-Emmanuel.pdf` (+dup)
- ⬜ `994417437-Alchemist-Concepts-in-Forex-Trading-Msnr-Overview.pdf`
- ⬜ `978173780-isc-10-eng-shrinked.pdf`

## Secondo PDF letto: "Candlesticks, Fibonacci, and Chart Pattern Trading Tools" (Fischer & Fischer, Wiley 2003, 273p)

A differenza del primo, questo è un libro vero (360K caratteri di testo
estraibile) — letto sia a testo che le figure delle pagine chiave (il
testo da solo perde le figure, controllato esplicitamente su richiesta
dell'utente).

### Mindset (Cap. 1 — risponde direttamente alla richiesta "mindset")

13 regole, le più rilevanti per NEXUS/gestione (il tema "80% gestione"
sollevato dall'utente):
- **Mai raddoppiare le perdite** — quasi tutti i grandi fallimenti nel
  trading vengono da posizioni perdenti raddoppiate sperando di
  recuperare con più leva
- **Vivere con le perdite fa parte del sistema** — chiudere in pari una
  posizione che era arrivata al +100% è una perdita reale quanto una
  posizione chiusa sotto al prezzo d'ingresso (rilevante: è esattamente
  il fenomeno "giveback" trovato stanotte su SAR/PIVOT_WICK/BAR_UPDN)
- **La disciplina conta più di ogni strategia** — una strategia
  efficace non deve essere complicata, ma va eseguita anche dopo una
  serie di perdite
- **Conoscere il proprio "pain level"** prima di eseguire una
  strategia, e non cambiarla senza una ragione sufficiente solo perché
  il sentiment di breve termine cambia
- **Diversificare** produce una equity curve più stabile, anche se
  probabilmente un rendimento medio più basso di un singolo prodotto
  molto redditizio

### Candele — regole quantitative precise (risponde a "quali candele danno segnali da sole")

| Pattern | Regola quantitativa | Conferma |
|---|---|---|
| Hammer / Hanging Man | ombra ≈**3× il corpo**, corpo vicino all'estremo opposto della barra | chiusura oltre l'estremo della barra nei giorni seguenti (più sicuro: chiusura, non solo tocco) |
| Belt-hold | nessuna ombra da un lato, corpo pieno | forza ∝ dimensione del corpo |
| Harami | corpo piccolo **interamente dentro** il corpo grande del giorno prima | più forte a fine trend + colore opposto al corpo precedente |
| Harami Cross | harami con corpo di oggi quasi zero (quasi-doji) | — |
| Doji | apertura≈chiusura, ombra lunga da un lato | conta di più a fine trend lungo, ancora di più se seguito da un engulfing il giorno dopo |
| **Piercing / Dark-Cloud Cover** | il corpo di oggi copre **almeno il 50%** del corpo di ieri (soglia quantificata!) | più copre, più forte il segnale |
| Morning/Evening Star | corpo piccolo **separato da un gap** dal corpo del giorno prima (3 candele) | — |

**Confronto diretto con NEXUS**: la soglia "50% di copertura del corpo
precedente" per Piercing/Dark-Cloud è molto più precisa del criterio
attuale di `NXS_Strat_BarUpDn` (semplice relazione OHLC tra due barre,
nessuna soglia di copertura) o del wick-ratio di PIVOT_WICK (1.5× come
soglia arbitraria, mai validata contro una fonte). Idea concreta per la
prossima sessione: implementare Piercing/Dark-Cloud/Harami come
condizione di rigetto alternativa al wick-ratio attuale in PIVOT_WICK,
usando la soglia 50% invece di un rapporto inventato — più
verificabile perché viene da una fonte con criterio esplicito, non da
un numero scelto a caso.

Non ancora letta: la parte propria di Fibonacci/PHI-ellisse (strumento
proprietario brevettato dagli autori, difficile da verificare
indipendentemente — priorità bassa) e il capitolo 4 "Candlestick Chart
Patterns" applicato (pattern grafici a 3 punti per inversioni di trend,
p.88 del libro) — da fare se si vuole approfondire oltre le definizioni
di base.

## Terzo giro: IFVG confermata, "Secret of 4.11" (S/R + zone fresh/non-fresh)

### IFVG (Inverse Fair Value Gap) — confermata fedele

Da `inversefairvaluegapifvginicttradingstrategiesguide.pdf` (guida
breve, 8p, editore "TradingFinder"): un FVG che viene invalidato
(rotto nella direzione opposta) cambia ruolo — un FVG ribassista rotto
verso l'alto diventa zona di domanda (bullish IFVG), un FVG rialzista
rotto verso il basso diventa zona di offerta (bearish IFVG). Confrontato
con `NXS_Strat_IFVG_Reversal` (`NXS_Strategies_SMC.mqh:163`): **corretto
e persino più rigoroso della fonte** — richiede chiusura oltre il
livello, candela di reazione (corpo ≥0.3×ATR) E conferma di rottura di
struttura (`chochUp/chochDown`), mentre la guida non menziona la CHoCH
esplicitamente. Nessuna azione richiesta.

### "Secret of 4.11" (Ali Yusoff, 16p) — framework Breakout-Pullback-Entry, TROVATO CONCETTO NUOVO

Diverso da tutto il resto letto finora — non ICT/SMC, un framework
compatto proprio dell'autore ("ZIKIR": Breakout → Pullback → Entry).
Rilevante per NEXUS su due punti concreti:

1. **Criterio di validità del livello: "rottura 2 volte"** — un livello
   S/R non è tradabile finché non è stato toccato/rotto **due volte**
   (mostrato con 4 mini-diagrammi breakout/no-breakout). Nessuna
   strategia NEXUS attuale ha questo criterio — sia PIVOT_WICK che
   MALAYSIAN_SNR tradano al primo tocco.

2. **Zona "Fresh" vs "Non-Fresh" — un livello si consuma dopo un uso**:
   una volta completata la sequenza Breakout→Pullback→Entry su una
   zona, quella zona è "usata" (non fresh) e **non va ritradata**,
   indipendentemente dal tempo passato. Questo è concettualmente più
   pulito del raffreddamento a tempo (N barre) usato in PIVOT_WICK/
   BAR_UPDN/BREAKOUT_ACC per lo stesso problema (inseguimento):
   invece di "aspetta N barre poi ritrada pure lo stesso livello", dice
   "quel livello è bruciato, punto" — un livello diverso può tradare
   subito dopo, un livello riusato mai. Idea concreta per la prossima
   sessione: aggiungere un flag "used" per-livello nel pool di
   PIVOT_WICK (accanto ai livelli stessi), invece di (o in aggiunta a)
   il cooldown a tempo attuale.

Introduce anche ISL (Intermediate Significant Level, breakout di
prezzo corrente) vs HSL (Historical Significant Level, livello di
timeframe più alto) — stessa idea del pool multi-TF già implementato
in PIVOT_WICK, nomenclatura diversa.

### Pattern riconosciuto: molti PDF sono dello stesso publisher/corso

- `technicalanalysisinforexprinciplessupportresistancekey.pdf` e
  `icttradingstyleabbreviationsandterminologiesfvgsobspo3mmxm.pdf`
  sono entrambi articoli generici brandizzati "TradingFinder" — tabelle
  comparative superficiali (TA vs Fundamentale, TA classica vs ICT),
  glossario di abbreviazioni. **Basso valore aggiunto**, contenuto già
  coperto meglio altrove nel motore. Non approfondire ulteriormente
  salvo bisogno specifico di un termine.
- `Sequence.pdf`, `994417437-Alchemist-Concepts...pdf`,
  `863955768-MSNR-x-SMC-x-ICT-the-Alchemist-Yanu-Emmanuel.pdf` sono
  **lo stesso corso** ("Smart Money ABAY FX — Alchemist", combina
  MSNR+SMC+LIT+ICT in un unico sistema) — trattarli come un corpus
  unico, non come 3 fonti indipendenti, quando si approfondirà.

## Quarto documento: "Support and Resistance Trading Strategy — The Advanced Guide" (Rayner Teo, TradingwithRayner, 26p)

**Il documento più direttamente utile trovato finora per PIVOT_WICK.**
Educatore riconosciuto (non un corso anonimo), guida compatta e ben
argomentata, letta per intero (testo estraibile pulito).

### 5 punti concreti, tutti applicabili a PIVOT_WICK

1. **"Più volte un livello viene testato, PIÙ SI INDEBOLISCE"** (non il
   contrario) — un livello S/R esiste perché ci sono ordini in attesa
   lì (istituzionali/smart money); ogni test consuma parte di quegli
   ordini. **Conferma indipendente del concetto "fresh/non-fresh" di
   Secret of 4.11**: due fonti diverse arrivano alla stessa conclusione
   — un livello va scontato/rimosso dopo l'uso, non ritradato
   all'infinito. PIVOT_WICK attualmente non ha alcun decadimento per
   numero di tocchi — i livelli restano validi indefinitamente nel pool
   (8 slot, nessun contatore di utilizzo).

2. **SR sono AREE, non linee** — "undershoot" (il prezzo si avvicina ma
   non tocca esattamente, il trade viene perso ad aspettare il livello
   preciso) e "overshoot" (il prezzo supera leggermente il livello, lo
   si crede rotto, non lo è). PIVOT_WICK usa già una tolleranza
   (`InpPivotWickTouchTolATR`) — coerente con questo principio, nessuna
   azione necessaria.

3. **SR è il PEGGIOR posto per lo stop loss — "viene cacciato"**. Due
   soluzioni concrete offerte: (a) stop a distanza ATR dal livello
   (esattamente quello che fa già `NXS_DefaultSLTP` — validato); (b)
   **aspettare la CHIUSURA della candela oltre il livello**, non basarsi
   sul semplice tocco intrabar (wick), per confermare che il livello sia
   davvero rotto. **Risposta diretta e con fonte alla domanda iniziale
   dell'utente** ("i trade a volte prendono stop e invertono dopo
   poco") — PIVOT_WICK valuta il tocco sul massimo/minimo della barra
   (wick), non sulla chiusura: uno stop hunt intrabar seguito da
   inversione è esattamente il pattern che l'attesa della chiusura
   evita.

4. **Filtro "buildup"**: se il prezzo si consolida (candele piccole, in
   range stretto) PROPRIO sul livello prima del tocco, è un segnale di
   DEBOLEZZA — il livello ha più probabilità di ROMPERSI che di
   reggere. Un filtro che PIVOT_WICK non ha: attualmente tratta ogni
   tocco allo stesso modo, che sia un tocco pulito e diretto o un
   consolidamento prolungato proprio sul livello (che secondo questa
   fonte va evitato per un trade di rigetto, non cercato).

5. **Strategia completa in 5 passi** (per confronto architetturale):
   segna le aree SR → aspetta un movimento direzionale VERSO l'area →
   aspetta il rigetto → **entra sulla candela SUCCESSIVA al rigetto**
   (non sulla stessa) con stop oltre lo swing → target sullo swing
   opposto. PIVOT_WICK entra potenzialmente sulla stessa barra del
   tocco — un ritardo di conferma di una barra è una variante
   facilmente testabile.

### Tre miglioramenti concreti e testabili per PIVOT_WICK (prossima sessione)

1. Contatore di utilizzo per livello — un livello usato (ciclo
   completo trade) esce dal pool, non viene ritradato (combina i punti
   1 di questa fonte + Secret of 4.11)
2. Conferma su CHIUSURA invece che su wick per il tocco — potrebbe
   ridurre gli stop prematuri seguiti da inversione lamentati
   dall'utente
3. Filtro anti-buildup — scartare tocchi preceduti da consolidamento
   stretto sul livello (calcolabile come range delle ultime N barre
   vs ATR)

## Quinto/sesto/settimo documento: Simple Trading Book (basso valore), trading-book.pdf (pattern grafici classici), Flipping Markets (conferma #3)

- `643335252-Simple-Trading-Book-Trading-Smart.pdf` (60p) — **basso
  valore**, contenuto da principiante assoluto ("cos'è una candela"),
  niente di nuovo. Non approfondire oltre.

- `797807669-trading-book.pdf` (51p, account "@5trader"/"trading_book1")
  — **enciclopedia di pattern grafici classici con regole quantificate
  di entry/SL/TP**: Doppio Massimo/Minimo (entry al retest della
  neckline, TP = altezza pattern proiettata), Rettangolo (**minimo 3
  tocchi** per validare il range), Testa e Spalle (regolare e
  invertita, TP = altezza testa-neckline), Cuneo ascendente/discendente,
  Diamante. **Nessuna di queste è implementata in NEXUS oggi** (nessuna
  strategia STRUCT_REACT copre doppio massimo/minimo o testa-spalle
  esplicitamente) — famiglia di pattern completamente nuova, con regole
  di target già quantificate (misura del pattern proiettata dal
  breakout), candidata per una futura strategia "Classic Chart
  Patterns" se si vuole ampliare oltre ICT/SMC.

- `flippingmarkets1-...pdf` (59p, "Flipping Markets") — consiglio di
  disciplina: scegliere UNA sola coppia/strumento e UNA sola sessione,
  padroneggiarla col backtest, non disperdersi su 4-5 strumenti insieme
  (coerente col principio "qualità non quantità" ripetuto
  dall'utente). Contenuto tecnico: stesso framework ICT (supply/demand,
  mitigazione, inefficienza/FVG) già coperto. **Ma conferma per la
  TERZA volta, da un autore indipendente**, il principio "zona non
  ancora testata = più forte" — qui chiamata "**UNMITIGATED** supply/
  demand" (una zona mai ritestata è un obiettivo di prezzo più forte di
  una già testata). **Tre fonti indipendenti (Secret of 4.11, Rayner
  Teo, Flipping Markets) convergono sulla stessa conclusione** — non è
  l'opinione di una persona sola, è un principio consolidato nella
  letteratura di trading. Rafforza ulteriormente la priorità del
  miglioramento #1 già proposto per PIVOT_WICK (contatore di utilizzo
  per livello, rimozione dal pool dopo un ciclo completo).

## Corpus Alchemist, CRT, Malaysian SNR — sintesi (sample mirati, non lettura integrale)

### Alchemist (While Srp — diverso dall'"ABAY FX" di Sequence.pdf, due corsi omonimi distinti)

- **OCL (Open Close Level)**: livello definito dall'apertura della
  candela subito dopo un impulso forte — concettualmente vicino alla
  "zona origine" già usata in `NXS_SHBMS_UpdateSide` (ultima candela di
  colore opposto prima del displacement), nomenclatura diversa, stessa
  idea di fondo.
- **"4 Key Trendline"**: linea dinamica tracciata tra due pivot nella
  stessa direzione (1→2), estesa in avanti, **ingresso al terzo tocco
  (punto 3)**. Geometria diagonale — **PIVOT_WICK non ha nulla di
  simile** (solo livelli orizzontali da pivot frattali). Idea per una
  strategia companion (trendline dinamica invece di livello
  orizzontale), non ancora esplorata nel motore in questa forma.

### CRT (6 PDF, sample rapido — la nota vault CRT esistente già copre l'essenziale)

Confermato: la teoria è compatta (candela 1 definisce il range, candela
2 dentro, candela 3 rompe) e **combinata esplicitamente con Turtle
Soup** in almeno una fonte (`754092222-CRT.pdf`, Romeo): "1. CRT per il
range. 2. Aspetta un turtle soup. 3. Aspetta model #1 ed entra su LTF."
**Idea concreta non ancora testata**: NEXUS ha sia CRT che TURTLE_SOUP
come strategie indipendenti — non sono mai state provate in
combinazione/confluenza (segnale solo quando entrambe concordano sulla
stessa zona), che è esattamente come le fonti esterne le descrivono
usate insieme, non separatamente.

### Malaysian SNR Emperor (KORORFX, 67p) — cascata di conferma multi-TF non presente in NEXUS

Confermato l'impianto di base (zone da massimo/minimo di CHIUSURA
W1/D1, "Weekly to Weekly", "Daily to Daily" — stesso principio di
`NXS_Strat_MalaysianSNR_Rejection` che usa H4/W1). **Ma trovato un
livello di sofisticazione in più**: "Setup 2(B) Medium Risk" descrive
una **cascata di conferma a doppio timeframe** — rigetto sul TF alto
(es. Daily) seguito dall'attesa di un **breakout di conferma su un TF
più basso** (H1) prima di entrare, invece di entrare direttamente al
tocco sul TF alto. `NXS_Strat_MalaysianSNR_Rejection` oggi entra
direttamente alla chiusura H4 che rispetta le condizioni — **nessun
passaggio di raffinamento su TF più basso**. Miglioramento concreto e
testabile per una prossima sessione, simile nello spirito al
"raffinamento HTF→LTF" già notato nella sezione Confluence del primo
PDF letto.

`My Rare SNR Course.pdf` non ancora aperto in profondità — stesso
autore/scuola presumibilmente, priorità bassa vista la sovrapposizione
già confermata con KORORFX.

## Stato onesto e prossimi passi

Letti in profondità 4 PDF su 34 (allyouneedtoknow parziale,
candlestick book parziale, IFVG guide completa, Secret of 4.11
parziale), più una decina scansionati per la copertina/struttura per
capire cosa contengono. **Non è realistico finire tutti e 34 con
questa profondità in una sola sessione** — alcuni superano le 270
pagine. Rimasti da leggere con priorità:

**Alta priorità (probabile contenuto nuovo, non ICT/SMC generico)**
- `541324475-Support-and-Resistance-Trading-Strategy.pdf` (26p)
- `692042405-100-SCREENSHOT-SETUP-SNR-CONTINUATION.pdf` (102p — banco
  di esempi reali per validare MALAYSIAN_SNR)
- Resto di `Secret Of 411(1).pdf` (pagine 7-16, ne mancano 10)
- `643335252-Simple-Trading-Book-Trading-Smart.pdf` (60p, non ancora aperto)
- `797807669-trading-book.pdf` (51p, quasi tutto immagini)
- `flippingmarkets1-...pdf` (59p)

**Media priorità (corpus Alchemist unificato, MSNR/CRT già in vault)**
- `Sequence.pdf`/`Sequence_1.pdf`/`Sequence_2_unlocked.pdf` (76p+)
- `994417437-Alchemist-Concepts...pdf`, `863955768-MSNR-x-SMC-x-ICT...pdf`
- `978173780-isc-10-eng-shrinked.pdf`
- I 6 PDF CRT (probabile sovrapposizione con la nota CRT esistente)
- I 4 PDF SNR Malaysia/My Rare SNR (probabile sovrapposizione con MALAYSIAN_SNR)

**Bassa priorità (già letti/campionati, basso valore aggiunto)**
- `technicalanalysisinforexprinciplessupportresistancekey.pdf` ✅
- `icttradingstyleabbreviationsandterminologiesfvgsobspo3mmxm.pdf` ✅ (solo glossario)
- `inversefairvaluegapifvginicttradingstrategiesguide.pdf` ✅ (confermato, nessuna azione)
- `whatisthesmartmoneyconcept.pdf` (non ancora aperto ma stesso publisher dei due sopra, probabile stesso valore basso)

## Prossimi passi

1. Leggere `candlesticksfibonacciandchartpatterntrading` per primo (testo
   vero, 273p ma processabile a blocchi — copre esattamente "quali
   candele danno segnali da sole" chiesto dall'utente)
2. Finire le sezioni 1-5 e 8 di `allyouneedtoknow` (market structure di
   base, sessioni, grafici annotati)
3. Applicare lo stesso metodo di audit (confronta diagramma del libro
   vs codice reale) alle altre strategie SMC via via che emergono
   definizioni precise nei PDF ICT-specifici
4. Decidere e testare il fix della profondità sweep su TURTLE_SOUP
