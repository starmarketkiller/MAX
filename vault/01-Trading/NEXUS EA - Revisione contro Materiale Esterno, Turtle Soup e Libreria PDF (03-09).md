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
