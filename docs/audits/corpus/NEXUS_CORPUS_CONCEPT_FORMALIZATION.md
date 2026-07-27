# FORMALIZZAZIONE DEI CONCETTI DAL CORPUS D'ORIGINE

> Prima lettura diretta delle fonti originali. **Documento analitico**: nessun
> file di codice è stato modificato. Nessuna strategia è dichiarata fedele o non
> fedele — dove codice e fonte divergono, la voce è marcata
> `CANDIDATE_DIVERGENCE` e richiede conferma.

| | |
|---|---|
| Data | 2026-07-26 |
| PDF ricevuti | **8 su 13** dichiarati in A4.2, **+1 fuori elenco** (`CANDLE_RANGE_THEORY`) |
| PDF letti integralmente | 5 (`My Rare SNR Course`, `My Rare SNR Course 2`, `ict-trading`, `Yanu Emmanuel`, `CANDLE_RANGE_THEORY`) |
| PDF letti parzialmente | 1 (`Sequence` — 20 pagine su 76) |
| PDF archiviati e non ancora letti | 3 (`SNR Malaysia` 74 p, `Secret Of 411(1)` 16 p, `Sequence_1` 74 p) |
| Conferme incrociate della primitiva open/close | **4 fonti indipendenti** |
| PDF ancora mancanti | **5** |
| Registro fonti | `docs/sources/SOURCE_MANIFEST.json` |

## Verifica di integrità delle fonti

| File | Pagine reali | A4.2 dichiara | Coincide | Testo nativo |
|---|---:|---:|:---:|---:|
| `My Rare SNR Course.pdf` | 29 | 29 | ✅ | 29/29 (348 car.) |
| `My Rare SNR Course 2.pdf` | 10 | 10 | ✅ | **0/10** |
| `SNR Malaysia.pdf` | 74 | 74 | ✅ | 74/74 (888 car.) |
| `Secret Of 411(1).pdf` | 16 | 16 | ✅ | **0/16** |
| `ict-trading-…pdf` | 91 | 91 | ✅ | 91/91 (58.358 car.) |
| `Sequence.pdf` | 76 | 76 | ✅ | **0/76** |
| `Sequence_1.pdf` | 74 | 74 | ✅ | **0/74** |
| `…the-Alchemist-Yanu-Emmanuel.pdf` | 51 | 51 | ✅ | 39/51 (24.685 car.) |
| `CANDLE_RANGE_THEORY.pdf` | 12 | — | n/d | 12/12 (3.247 car.) |

**I conteggi pagina di A4.2 sono corretti su tutti e otto i file dichiarati**, verificati
con `pypdf`. I conteggi di *caratteri* non sono riproducibili con estrazione
nativa perché quell'audit usava OCR supplementare: **sei file su otto** hanno 10 caratteri
per pagina o meno — cioè solo il numero di pagina. **Sono corsi visivi.** La
lettura utile richiede rendering delle pagine, non estrazione di testo.

## Legenda

| Sigla | Significato |
|---|---|
| `EXPLICIT` | affermato testualmente o graficamente nella fonte |
| `INFERRED` | deduzione da testo esplicito; **non è un requisito** |
| `MISSING` | la fonte non lo dice |
| `CANDIDATE_DIVERGENCE` | codice e fonte sembrano dire cose diverse — **da confermare**, non è un verdetto |
| `CANDIDATE_MATCH` | codice e fonte sembrano coincidere — **da confermare** |

---

## ⚠️ Il corpus non è una raccolta di metodi separati: ha un framework che li compone

> **Correzione a una versione precedente di questo documento.** Dopo la lettura
> dei primi tre PDF avevo scritto che il corpus conteneva "tre metodologie
> distinte, non una". Al livello dei singoli file è vero. Ma `Sequence.pdf`,
> letto dopo, mostra che esiste un **framework di integrazione dichiarato** che
> le compone con ruoli espliciti. L'affermazione precedente era incompleta e va
> letta con questa sezione.

`Sequence.pdf` si intitola **"SMART MONEY ABAY FX — ALCHEMIST"** e definisce
Alchemist così (p. 1–2, `EXPLICIT`):

> "ALCHEMIST SENDIRI ADALAH SATU KE SATUAN ATAU GABUNGAN DARI BERBAGAI METODE
> YANG MENJADI SATU"
> "Alchemist is a method that mixes several other methods to form a unified whole
> to analyze a market."

Con un diagramma di flusso e un'assegnazione di **ruoli**:

```text
MSNR  →  SMC  →  LIT  →  ICT

MSNR : ENTRY POI
ICT  : KILL ZONES
SMC  : STRUCTURE
LIT  : LIQUIDITY / STRUCTURE
```

**Questo è il pezzo che mancava.** I singoli corsi non sono alternative fra cui
scegliere: sono **componenti con funzioni diverse dentro una sola pipeline**. La
struttura viene da SMC, la liquidità da LIT, il timing da ICT, il punto di
ingresso da MSNR.

### Le tre famiglie, riviste

| Famiglia | File | Origine | Ruolo in Alchemist |
|---|---|---|---|
| **ALCHEMIST** | `Sequence.pdf`, `Sequence_1.pdf` | Smart Money Abay FX | **framework di composizione** |
| **MSNR / SNR-Flipping** | `My Rare SNR Course.pdf` | Price Action Traders | ENTRY POI |
| **Trendline "411"** | `My Rare SNR Course 2.pdf` | liquidityinducementcourses.com | parte di MSNR (confluenza SNR+TL) |
| **ICT** | `ict-trading-…pdf` | dipprofit.com (metodo Huddleston) | KILL ZONES + AOI |

Resta vero che `My Rare SNR Course 2.pdf` **non è la seconda parte** di
`My Rare SNR Course.pdf` — è un altro autore. Ma non è nemmeno un metodo
estraneo: Alchemist usa la confluenza SNR+trendline come costruttore di POI, e
`Sequence.pdf` p. 10 la chiama **"THE [X] FACTOR OF TRENDLINE"** con la stessa
definizione di confluenza del corso 411.

**Conseguenza per la regola §A4.2** ("la terminologia duplicata fra corsi non va
trattata come equivalenza semantica senza riconciliazione"): la riconciliazione
non solo è necessaria — è **possibile**, perché Alchemist la fornisce.

---

# PARTE 1 — Metodo SNR / Flipping

Fonte: `My Rare SNR Course.pdf`, 29 pagine, letto integralmente.

## S-01 · Come si forma un livello SNR — `EXPLICIT`

> "First candle CLOSES lower which is the SUPPORT, and the other candle OPENS at
> the support level." (p. 1)
> "First candle (white) CLOSES higher and this becomes the RESISTANCE, while the
> second candle (black) OPENS at the resistance level." (p. 2)

**Predicato deterministico:**

```text
livello_SNR(i) = close[i]
tipo = SUPPORT     se close[i] < open[i]   (candela ribassista)
tipo = RESISTANCE  se close[i] > open[i]   (candela rialzista)
```

**Nota della fonte, importante:** "It does not matter if the second candle opens
higher or lower than the first candle's close. Our attention is to mark the
first candle's close across the open of second candle." (p. 2)

Cioè il livello è **il confine close/open fra due candele consecutive**, e non
richiede alcun gap. È una definizione codificabile senza ambiguità.

## S-02 · Tre tipi di SNR — `EXPLICIT`

```text
CLASSIC SNR  → classic support | classic resistance
GAP SNR      → bearish gap | bullish gap
DOJI SNR     → bullish doji SNR | bearish doji SNR
```

## S-03 · Flipping (SBR / RBS) — `EXPLICIT`

> "when a market force of support line is breached … it is an indication change
> of power from broken support to a new resistance — *Support becomes new
> Resistance (SBR)*" (p. 7)
> "the broken resistance is automatically transferred into a new support …
> *Resistance becomes new Support (RBS)*"

**FLIPZONE** = la candela che rompe il livello. Definita a p. 8:
> "FLIPZONE is the bearish candlestick that takes out a weak support and this
> becomes a strong resistance (SBR) on the other side of breakout."

## S-04 · Validità e invalidazione — `EXPLICIT`, e discriminante preciso

> "An SNR level which has been used several times in the past would still be
> valid for use recently if it is broken through with a **body** of candlestick."
> (p. 5)

**Rottura = corpo, non ombra.** È il tipo di discriminante che rende una regola
testabile invece che interpretabile.

> "How long an SNR level travels or gets used does not matter as long as it
> turned FRESH level in its present state it can be used again." (p. 4)

> "AS LONG AS PRICES DO NOT CLOSE BELOW THE BROKEN RESISTANCE LEVEL, THIS MEANS
> PRICE MOVING IN CONTINUATION OF AN ORIGINAL TREND" (p. 4)

## S-05 · GAP_SNR: limiti e invalidazione — `EXPLICIT`

```text
UL = gap's upper limit
LL = gap's lower limit

GAP ribassista (SNR support → fresh resistance):
  vendita valida sul reject della fresh resistance
  FINCHÉ nessun prezzo CHIUDE sopra UL

GAP rialzista (SNR resistance → fresh support):
  acquisto valido sul reject del fresh support
  FINCHÉ nessun prezzo CHIUDE sotto LL
```

Regola di invalidazione esplicita, con condizione su **chiusura**. (p. 8–9)

## S-06 · Sequenza di ingresso su FLIPZONE — `EXPLICIT`

```text
1 = SNR ORIGIN (support/resistance)
2 = 1° REJECT (livello debole)
3 = 2° REJECT (livello debole)
4 = REJECT del livello forte → usato per DIRECT ENTRY

DIRECT ENTRY       = candela subito dopo il breakout dell'SNR
CONFIRMATORY ENTRY = sul retest successivo
```

## S-07 · DOJI_SNR — `EXPLICIT`, pattern a tre candele

> "BULLISH DOJI_SNR: A Bullish candlestick with strong momentum. Followed by a
> 'Doji' or a candlestick with narrow-range body. And finally, a bullish
> candlestick with strong momentum that breaks and CLOSES ABOVE the Doji
> candlestick. IMPLICATIONS: Buying pressure resumes!" (p. 18)

```text
candela[i-2]: rialzista, momentum forte
candela[i-1]: doji o corpo di range stretto
candela[i]:   rialzista, momentum forte, chiude SOPRA la doji
```

`MISSING`: la fonte non quantifica "strong momentum" né "narrow-range".

## S-08 · Catena di raffinamento multi-timeframe — `EXPLICIT`

```text
SELL: DAILY  → 4-HOUR → 1-HOUR
BUY:  WEEKLY → DAILY   → 4-HOUR
```

> "A HTF momentum candle when refined gives a LTF #GAP_SNR. That means, if we
> have two opposing momentum candles (bullish & bearish impulses) the current
> candle is the flipped #GAP_SNR in LTFs." (p. 7)

## S-09 · Hidden / Internal GAP_SNR — `EXPLICIT`, regola sui target

> "When a momentum candle breaks through an SNR level, REFINE the candle to see
> a hidden GAPS within the entire range. And price would come back, after
> breakout, to RETEST the INTERNAL GAPS (they stand as **roadblocks** to market
> direction)." (p. 21)

> "A MOMENTUM CANDLE THAT BREAKS OUT OR ENGULFS AN SNR USUALLY POSSESS A GAP SNR
> WITHIN"

**È una regola di selezione del target**, non di ingresso: i gap interni sono
ostacoli fra prezzo e obiettivo.

## S-10 · Rischio e rendimento — `EXPLICIT` ma aneddotico

| Esempio | SL | TP | R:R |
|---|---|---|---|
| GBPUSD 4H (p. 13) | 7 pips | 35 pips | 1:5 |
| EURUSD 1H (p. 23) | 3 pips | 77 pips | 1:5.2 |
| Gold 4H (p. 23) | 44 pips | 1143 pips | 1:26 |
| EURUSD 1H (p. 23) | 1 pip | 95 pips | — |

`AMBIGUOUS`: sono **esempi selezionati**, non una regola di dimensionamento. La
fonte non definisce dove va lo stop in generale, né un R:R obbligatorio. Non
vanno usati come parametri.

## S-11 · Killzone — `EXPLICIT` come etichetta, `MISSING` come definizione

I grafici a p. 14 e 15 marcano `LONDON KILLZONE` e `NEW YORK KILLZONE`. **La
fonte non dichiara mai gli orari.** Vanno letti dai grafici o presi da un'altra
fonte.

## S-12 · Buco dichiarato dalla fonte stessa — `MISSING`

Tre volte nel documento (p. 15, 22, 23):

> "The CHART REFINEMENT skill is exposed to the members of SNR Inner Circle
> (VIP). To have access, DM me on @iadegboruwa"

**Il corso trattiene deliberatamente la parte di raffinamento del grafico.** Non
è una lacuna dell'archiviazione: è assente dal materiale. Qualunque
implementazione che dichiari fedeltà al "chart refinement" non è verificabile
contro questa fonte.

---

# PARTE 2 — Metodo Trendline "411"

Fonte: `My Rare SNR Course 2.pdf`, 10 pagine, letto integralmente.

## T-01 · Costruzione della trendline — `EXPLICIT`

```text
Impostazione: RAY RIGHT
1° punto TL = 1° punto
3° punto TL = 2° punto      ← si salta il secondo swing

HOOKING METHOD (ancoraggio):
  Resistance → Body Bullish
  Support    → Body Bearish
```

> "Please pay attention to the location of the TL POINT on the **BODY**."

Ancoraggio sul **corpo**, non sull'estremo. Come S-04, è un discriminante
codificabile.

## T-02 · Confluenza — `EXPLICIT`

> "CONFLUENCE — Two points of convergence that result in the same decision."

```text
Punto 1 = SNR
Punto 2 = TL
→ convergenza → DECISION
```

## T-03 · Sei tipi di trendline — `EXPLICIT` (grafici), `MISSING` (definizioni testuali)

```text
TYPE 1, TYPE 2, TYPE 3, QM TL, 666 TL, XR TL
XR TL:  X = price action formata da 2 TL
        R = rotazione della TL per trovare l'angolo appropriato
BOOM POINT = intersezione di due tipi diversi di TL
```

> "2 TRENDLINE (R+S) are used in this method to identify: 1. Trend and direction
> in the short or long term. 2. The possibility of price momentum."
> "HIGH MOMENTUM = Less PIPS · LOW MOMENTUM = More PIPS"
> "*This is the trade secret that I employ on a daily basis."

## T-04 · Rischio — `EXPLICIT`

```text
RISK : REWARDS = 1 : 5
esempio: STOP LOSS 40 pips, TAKE PROFIT 200 pips
```

## T-05 · Nessuna strategia dell'EA implementa questo metodo — `EXPLICIT`

Nessuna delle 37 strategie live è basata su trendline. Il registro canonico non
contiene alcun identificatore riconducibile a `TRENDLINE`, `TL`, `QM`, `XR` o
`666`. **Questa intera famiglia metodologica è presente nel corpus e assente
dall'implementazione.**

---

# PARTE 3 — Metodo ICT

Fonte: `ict-trading-250828073107-caca0de9.pdf`, 91 pagine, testo nativo completo.

## I-01 · Fair Value Gap — `EXPLICIT`, definizione esatta

> "The fair value gap is a three-candle pattern that hides a gap between the
> first and third candle **shadows**."

```text
FVG rialzista (BISI — buy side imbalance / sell side inefficiency):
  high[i-2] < low[i]        ← nessuna sovrapposizione fra ombra sup. di 1 e inf. di 3

FVG ribassista (SIBI — sell side imbalance / buy side inefficiency):
  low[i-2] > high[i]

CONSEQUENT ENCROACHMENT = punto medio del gap (ritracciamento 50%)
```

> "Fair value gaps can be used as zones of support and resistance … pay attention
> to how price reacts to fair value gap limits and the consequent encroachment
> line."
> "The ideal scenario is to see price reacting to the upper limit of the fair
> value gap, meaning piercing it and closing above it."

**Il segnale è la reazione al gap, non la sua formazione.**

## I-02 · FVG Inversion — `EXPLICIT`

> "Price can disrespect the fair value gap and test it on the other side. In ICT
> trading terms this is called a fair value gap inversion."

FVG rialzista invalidato → movimento ribassista, e viceversa.

## I-03 · Discount / Premium — `EXPLICIT`

```text
range = da swing low a swing high (o viceversa)
metà superiore = PREMIUM
metà inferiore = DISCOUNT
long  → si entra in DISCOUNT
short → si entra in PREMIUM
```

## I-04 · Optimal Trade Entry (OTE) — `EXPLICIT`, numeri precisi

> "The OTE is a specific Fibonacci retracement zone that will fall in the
> discount zone for a long trade entry and in the premium zone for a short trade
> entry. This specific Fibonacci zone is **from 0.62% to 0.79%**. The midpoint of
> this zone which is **0.705** is also highlighted."

## I-05 · Order Block — `EXPLICIT`

```text
ALTA PROBABILITÀ (corpo grande):
  bullish OB = candela ribassista a corpo grande che spazza SSL,
               seguita da rottura del massimo precedente (BOS)
               → OB all'APERTURA di quella candela
  bearish OB = candela rialzista a corpo grande che spazza BSL,
               seguita da rottura del minimo precedente (BOS)
               → OB all'APERTURA di quella candela
  formazione: pivot espansivo (lower low → higher high, o viceversa)

BASSA PROBABILITÀ (corpo piccolo, ombre prominenti, in mezzo al movimento):
  bullish = candela ribassista a corpo piccolo dentro un movimento rialzista
            → OB nello spazio fra HIGH e OPEN di quella candela
  bearish = candela rialzista a corpo piccolo dentro un movimento ribassista
            → OB nello spazio fra LOW e OPEN
```

Ordine obbligatorio: **prima lo sweep di liquidità, poi il BOS**, poi il retest.

## I-06 · Displacement — `EXPLICIT` come concetto, `MISSING` come soglia

> "Displacement happens when the price makes a strong and abrupt move … a bunch
> of long candles in a row, all heading in the same direction with very short
> wicks. … Displacement often leads to two important things: a change in Market
> Structure and a gap between the current price and its Fair Value."

`MISSING`: nessuna soglia numerica per "long candles" o "short wicks".

## I-07 · Silver Bullet — `EXPLICIT`, con orari

> "The strategy works best when the market is busy, usually between **10 am–11 am
> ET or 3 am–4 am ET**. Once you know the timing, you look for certain conditions
> to align. You're waiting for the price to break either the highest or lowest
> point of the **last hour's candle**. When that happens, you're aiming to trade
> back within that candle's range. The method takes the ICT concept of daily bias
> as its trading method."

## I-08 · Provenienza della fonte ICT — da tenere presente

Il PDF è di `dipprofit.com` ed è una **divulgazione di terze parti** del metodo
di Michael J. Huddleston, non materiale originale ICT. È evidenza utile, non
autorità finale.

---

# PARTE 4 — Framework ALCHEMIST

Fonte: `Sequence.pdf`, 76 pagine, lette le prime 20. Documento bilingue
indonesiano/inglese, interamente per immagini.

## A-01 · Composizione e ruoli — `EXPLICIT`

Vedi la sezione iniziale. `MSNR → SMC → LIT → ICT`, con ruoli assegnati.

## A-02 · Tassonomia POI / AOI — `EXPLICIT`

La distinzione più utile del documento, perché separa **livelli** da **zone**:

```text
POI — Point of Interest   (un LIVELLO, prezzo singolo)
  esempi: QM, RBS, SBR, OCL
  SNR POI:  support = CLASSIC V   ·   resistance = CLASSIC A

AOI — Area of Interest    (una ZONA, intervallo di prezzo)
  esempi: FVG, BPR, IFVG, BISI, ORDER BLOCK, BREAKER BLOCK
```

## A-03 · RBS / SBR — `EXPLICIT`, con sequenza operativa

```text
RBS = Resistance Becomes Support
      pattern: Break → Retest → Continue Up      (bias rialzista, area di acquisto)

SBR = Support Becomes Resistance
      pattern: Break → Retest → Continue Down    (bias ribassista, area di vendita)
```

È la stessa nozione di *flipping* di S-03, con la sequenza in tre tempi resa
esplicita. **Due fonti indipendenti concordano** — è il primo concetto del
corpus con doppia conferma.

## A-04 · QM / Quasimodo — `EXPLICIT`, struttura precisa

> "Quasimodo is a reversal pattern that forms after a market structure break,
> marking the Smart Money reversal zone."

```text
QM ribassista:  Higher High → Higher Low → Lower High → Lower Low
QM rialzista:   Lower Low  → Lower High → Higher Low  → Higher High

Sequenza operativa (versione ribassista, dal testo indonesiano):
  1. il mercato fa un Higher High (HH)
  2. poi fa un Lower Low (LL)  → la struttura inizia a indebolirsi
  3. quando il prezzo ritraccia e forma un Lower High (LH) nell'area
     precedente — il QM Level — quella è la zona di ingresso short
```

## A-05 · OCL — Open Close Levels — `EXPLICIT`

```text
OCL           livello chiave dall'HTF          → zona base
Candela HTF   definisce l'area di reazione     → zona di setup
Struttura LTF fornisce la conferma d'ingresso  → zona di entry
Buying/Selling Model  determina la direzione   → fase di esecuzione
```

**OCL è lo stesso oggetto di S-01**: un livello definito dal confine
open/close. Due fonti indipendenti, stessa primitiva, nomi diversi
(`SNR level` in MSNR, `OCL` in Alchemist). È esattamente il tipo di
riconciliazione terminologica che §A4.2 richiede.

## A-06 · Classic V / Classic A — `EXPLICIT`

```text
CLASSIC V (supporto):
  il prezzo scende su un'area di supporto e rimbalza formando una "V"
  rifiuto rapido dalla zona di supporto
  una candela rialzista si forma SUBITO DOPO che una ribassista tocca il livello
  → uso: ingressi di acquisto sul supporto

CLASSIC A (resistenza):
  il prezzo sale su un'area di resistenza e ricade formando una "A"
  una candela ribassista compare subito dopo che una rialzista tocca il livello
  → uso: ingressi di vendita sulla resistenza
```

Il diagramma mostra candela ribassista seguita da rialzista al supporto:
**è la stessa costruzione di S-01**. Terza conferma incrociata della primitiva
close/open.

## A-07 · QMX — `EXPLICIT` (diagrammi), `MISSING` (regole quantitative)

> "QMX — Comprises of QM + Trendline crossing (X)"

I diagrammi (p. 11–12) mostrano, per la versione di vendita: livello SNR toccato
tre volte (1, 2, 3), trendline ascendente che lo interseca al terzo tocco, e una
candela **ENGULF** al punto di incrocio. Il POI è il punto di intersezione fra
SNR e trendline.

`MISSING`: la fonte non definisce la tolleranza dell'intersezione né i criteri
di validità della candela engulfing.

## A-08 · Tipi di trendline in MSNR — `EXPLICIT`

```text
Regular Trendline   → supporto/resistenza dinamici; ingresso sul retest
Breakout Trendline  → rottura della TL = possibile cambio di struttura;
                      si attende il retest per confermare la nuova direzione
Trendline Divergence → prezzo e angolo della TL divergono
                      (es. il prezzo fa higher high ma la TL si appiattisce)
                      → debolezza del trend, potenziale reversal
```

## A-09 · Confluenza / [X] Factor — `EXPLICIT`

> "Two or three points of convergence that result in the same direction. These
> points could be: SNR + Trendline, or two SNR levels converging at the same
> point to give a sell or buy signal."

Il POI operativo è il punto dove **due o tre elementi indipendenti convergono**.
Nei grafici XAUUSD (p. 13–20) il POI è l'intersezione di due trendline con un
livello orizzontale.

---

# PARTE 5 — Malaysian SNR (Yanu Emmanuel)

Fonte: `863955768-MSNR-x-SMC-x-ICT-the-Alchemist-Yanu-Emmanuel.pdf`, 51 pagine,
testo nativo 39/51 (24.685 caratteri). **È il documento più completo del
corpus**: ha indice, capitoli e prosa, non solo diagrammi.

Struttura: Introduzione → Malaysian SNR → Storyline (bias MTF) → Confluenze
(trendline, sessioni/killzone) → Action Plans (chart refinement, esempi, risk
management, backtesting).

## M-01 · Identificazione del livello SNR — `EXPLICIT`, quarta conferma

> "To identify the SNR level, your focus is on the close and open prices. You
> draw a line across the first candlestick's close to join the next
> candlestick's open. **Ignore the wicks**."
> "For resistance level, you draw line from the bullish candle's close to join
> the next bearish candle's open… You'll identify this as **'A' shape** on line
> chart."
> "On support level, you draw a line across bearish candle's close to join next
> bullish candle's open. This can be identified on a line chart as **'V' shape**."

**Quarta fonte indipendente, stessa primitiva.** E risolve un'ambiguità: i nomi
`CLASSIC V` e `CLASSIC A` di Alchemist (A-06) sono **le forme che il livello
assume su un grafico a linee** — perché la linea unisce le chiusure, e ignorare
le ombre produce una V al supporto e una A alla resistenza.

| Fonte | Nome della primitiva |
|---|---|
| `My Rare SNR Course` | livello SNR (S-01) |
| `Sequence.pdf` (Alchemist) | OCL — Open Close Levels (A-05) |
| `Sequence.pdf` (Alchemist) | Classic V / Classic A (A-06) |
| `Yanu Emmanuel` | SNR level, forme V e A su line chart (M-01) |

## M-02 · Perché la primitiva è il confine open/close — `EXPLICIT`

> "1. If price is to move UP, it must first move DOWN. 2. If price is to move
> DOWN, it must first move UP. Why this is so? Because the essence of every
> major player in the financial markets is to MANIPULATE prices to his own
> advantage. They trade off the liquidity (bulk orders) at each level of support
> and resistance (SnR)."

È il razionale del metodo, non una regola operativa. Lo riporto perché è
l'unica giustificazione esplicita che il corpus offre per la scelta della
primitiva.

## M-03 · Stato di un livello: fresh / unfresh / flipped — `EXPLICIT`

La regola più operativa dell'intero corpus. È una **macchina a stati**:

```text
FRESH     livello mai toccato dal prezzo — né da ombra né da corpo
          "untouched snow"; forte e affidabile
          motivo: conserva liquidità non raccolta

  ── ombra tocca il livello ──▶

UNFRESH   già toccato o rotto; più debole, "usato"

  ── una candela CHIUDE OLTRE con corpo pieno (non solo ombra) ──▶

FLIPPED   il ruolo si inverte: supporto → resistenza (SBR),
          resistenza → supporto (RBS)

  ── il prezzo torna e lo TOCCA solo con l'ombra, senza romperlo ──▶

FRESH di nuovo, ma nella direzione invertita
          "the level has essentially been cleansed and reborn with a new role"
```

Il discriminante **corpo vs ombra** compare per la terza volta nel corpus
(S-04, M-03, M-05): è la regola più ripetuta e più codificabile che le fonti
esprimano.

## M-04 · Il livello NON è un segnale — `EXPLICIT`, ed è vincolante

> "we treat these key levels **not as automatic trade signals**, but as
> potential zones of interest. These levels become actionable **only after all
> other confluences have been confirmed** — such as candlestick patterns,
> momentum indicators, or liquidity sweeps — and we observe a clear rejection
> from that zone. This rejection must align with the higher timeframe order
> flow, directional bias, prevailing trend, or overall market structure."
> "**We do not blindly execute trades simply because price has reached an SNR
> level.**"

**Questa è la frase più importante che ho letto in tutto il corpus.** La fonte
dichiara esplicitamente che il livello da solo non genera un ingresso. Servono,
nell'ordine: confluenze confermate, rifiuto osservato dalla zona, allineamento
con l'order flow del timeframe superiore.

## M-05 · Break of Market Structure — `EXPLICIT`

> "Break of market structure occurs when price **closes** above a swing
> high/low… A break of structure is only considered valid when price closes
> above the higher high **with a full body**; when price closes above the swing
> high **with a wick**, this is not considered as a break of structure."
> "After break of structure, always wait for retracement."
> "Always trade in the direction of the BOS."

Tre regole distinte e tutte codificabili: validità (corpo), attesa
(ritracciamento), direzione (concorde al BOS).

## M-06 · Candela di rifiuto — `EXPLICIT`, `MISSING` sulle soglie

> "The rejection candle… The anatomy and concept is similar to the classic 'Pin
> Bar'. Rejection candles communicate denial of higher or lower prices… This
> denial leaves a very distinct feature: a long lower or upper wick. **The
> better quality rejection candles pack thicker candle bodies** (closing in the
> direction of the rejection)."

`MISSING`: "long wick" e "thicker body" non sono quantificati.

## M-07 · GAP SNR come zona nascosta HTF — `EXPLICIT`

> "Gap is usually a 'Hidden Zone' in a higher timeframe (HTF) but when refined
> in a lower timeframe turns a Breakout (Flipped SNR)."

Coincide con S-09 (`Hidden / Internal GAP_SNR`) di un'altra fonte: il gap HTF si
risolve in un livello flipped sul timeframe inferiore.

## M-08 · Sessioni e killzone — `EXPLICIT` sull'uso, `MISSING` sugli orari

> "Kill zones refers to the hot trading hours… based on the four primary
> sessions: Sydney, Tokyo, London and New York."
> "With the Malaysian SNR, we **mainly focus on trading the London and NY
> killzones**, since they have the most volatility throughout the whole day."

**Gli orari non sono dichiarati nemmeno qui.** Terza fonte che nomina le
killzone senza definirle. L'unica fonte del corpus che dà orari resta il PDF
ICT (I-07: 10–11 ET e 3–4 ET).

---

# PARTE 6 — Candle Range Theory (CRT)

Fonte: `CANDLE_RANGE_THEORY.pdf`, 12 pagine, di Suven Raj, testo nativo
completo. **Non è fra i 13 PDF dichiarati in A4.2**: è una fonte aggiuntiva.

È il metodo **più precisamente codificabile dell'intero corpus**.

## C-01 · Primitiva — `EXPLICIT`

> "candle range theory or crt is a trading concept that focuses on the price
> range high or low of a single candlestick on the chart… each candle
> represents a trading range. If you break this down into lower timeframe
> candle, you will notice that high and low of the candle often act as turning
> point on the lower timeframe. These points form the most important liquidity
> level because that is the highest and lowest price traded during previous
> trading period."

```text
CRH = Candle Range High = high[i]   (livello di liquidità superiore)
CRL = Candle Range Low  = low[i]    (livello di liquidità inferiore)
```

> "PERIOD: CAN BE A DAILY, H4, H1 … M1" — vale su qualunque timeframe.

## C-02 · Modello a tre candele con ruoli — `EXPLICIT`

```text
prima candela   definisce il range   (CRH, CRL)
seconda candela crea lo sweep
terza candela   fornisce l'ingresso
```

## C-03 · Regola completa, con invalidazione — `EXPLICIT`

Setup ribassista (speculare per il rialzista):

> "if the second candle attacks the liquidity above the CRH and immediately
> reverses, there is high probability that next target will be the liquidity
> below the Candle Range Low."
> "If instead, we see the second candle **close above the CRH**, then the
> potential Candle Range Theory setup becomes **invalid**… it's more likely
> that the market will continue pushing upward."
> "if the criteria are met, and the second candle **fails to close above** the
> Candle Range High, we can then look to the third candle for a potential short
> setup with our target being the Candle Range Low."

**Predicato deterministico completo:**

```text
CRH = high[i-2]
CRL = low[i-2]

sweep        :  high[i-1] >  CRH            la seconda candela attacca la liquidità
validità     :  close[i-1] <= CRH           NON chiude oltre → setup valido
invalidazione:  close[i-1] >  CRH           → setup ANNULLATO

se valido:  ingresso SHORT sulla terza candela, target = CRL
```

Ingresso, invalidazione e target sono tutti espressi in termini di OHLC. **Non
richiede alcuna interpretazione.** È l'unico blocco del corpus che si può
scrivere in codice leggendolo una volta sola.

## C-04 · Limite dichiarato dalla fonte — `MISSING`

L'indice elenca cinque sezioni, quattro delle quali marcate `CLASS`:
`RULES & STEPS`, `CRT + MARKET DIRECTION`, `CRT MISTAKES`, `REAL CHART EXAMPLE`.
Il documento si chiude con:

> "THE REST WILL BE TAUGHT IN THE UPCOMING CLASS."

**Questo PDF contiene solo l'introduzione.** Regole operative complete,
direzione di mercato, errori tipici ed esempi reali non ci sono.

### Un tratto ricorrente del corpus, che vale la pena dichiarare

Terza fonte su sette che trattiene deliberatamente la parte operativa:

| Fonte | Cosa trattiene | Dove |
|---|---|---|
| `My Rare SNR Course` | "CHART REFINEMENT" | S-12, riservato ai membri VIP |
| `My Rare SNR Course 2` | "trade secret that I employ on a daily basis" (XR TL) | T-03 |
| `CANDLE_RANGE_THEORY` | regole, direzione, errori, esempi | C-04, "upcoming class" |

Non è un problema di archiviazione: **i materiali gratuiti sono strutturati per
introdurre e rimandare**. Va messo in conto nella pianificazione: acquisire più
PDF gratuiti non garantisce di ottenere più regole operative.

---

# Confronto preliminare con l'implementazione

**Nessuna di queste voci è un verdetto.** Sono confronti fra una fonte e una
riga di codice, entrambi citati, da confermare con lettura completa del modulo.

## D-01 · `SILVER_BULLET` — orari delle killzone · `CANDIDATE_DIVERGENCE` 🔴

**Fonte** (I-07): 10:00–11:00 ET **e** 03:00–04:00 ET.

**Codice** (`MQL5/Include/NEXUS_v1/NXS_Strategies_SMC.mqh:409-410`):

```cpp
bool killzoneLO = (h >= 10 && h < 11);   // London KZ 10-11 GMT
bool killzoneNY = (h >= 14 && h < 15);   // NY KZ 14-15 GMT
```

| Finestra fonte | In GMT (EST, inverno) | In GMT (EDT, estate) | Finestra codice |
|---|---|---|---|
| 10–11 ET | 15:00–16:00 | 14:00–15:00 | 14:00–15:00 ✅ solo in estate |
| 03–04 ET | 08:00–09:00 | 07:00–08:00 | 10:00–11:00 ❌ né l'una né l'altra |

Due osservazioni distinte:

1. la finestra "NY" del codice coincide con 10–11 ET **solo durante l'ora legale
   americana**; in inverno è spostata di un'ora. Il codice converte da server a
   GMT (`InpServerGMTOffset`) ma **GMT non segue il DST americano**, quindi lo
   sfasamento è strutturale, non un errore di configurazione;
2. la finestra "London 10–11 GMT" corrisponde a 05:00–06:00 ET e non compare in
   questa fonte.

**Da confermare:** se un'altra fonte del corpus (6 PDF ancora mancanti) definisca
una killzone di Londra, oppure se la finestra sia una scelta di progetto non
derivata dal corso.

## D-02 · `OTE_CONT` — zona Fibonacci · `CANDIDATE_MATCH` ✅

**Fonte** (I-04): 0.62–0.79, punto medio 0.705, discount per long, premium per short.

**Codice** (`NXS_Strategies_SMC.mqh:449, 495, 502`):

```
// Entry on OTE retrace (0.62-0.79) of the dominant leg
s.reason = "OTE 0.62-0.79 disc+trend+BOS"
s.reason = "OTE 0.62-0.79 prem+trend+BOS"
```

Zona, direzione e uso di discount/premium coincidono con la fonte. **Da
confermare:** se il codice usi anche il punto medio 0.705, che la fonte
sottolinea ("especially the midpoint").

## D-03 · `FVG_CONT` — momento del segnale · coerente con un bug già registrato

**Fonte** (I-01): il segnale è la **reazione** al gap (limite o consequent
encroachment), non la formazione.

Il knowledge base registra per `FVG_CONT` il bug storico: *"entra alla formazione
del gap, non sul retest (audit: lifecycle in coda)"*. La fonte **conferma che il
retest è il comportamento corretto**. Il bug era già noto; ora ha un riferimento
d'origine.

## D-04 · `DISP_REBAL`, `ORDER_BLOCK`, `OB_MIT`, `IFVG` — `da verificare`

Le definizioni I-02, I-05 e I-06 sono ora disponibili in forma codificabile. Il
confronto con il codice non è stato eseguito in questa consegna.

## D-05 · Metodo trendline — nessuna implementazione

Vedi T-05. Non è una divergenza: è un'assenza.

## D-06 · Primitive di Alchemist assenti dall'EA · `EXPLICIT`

Confronto fra la tassonomia POI/AOI (A-02) e i 37 identificatori del registro
canonico:

| Primitiva Alchemist | Tipo | Strategia EA corrispondente |
|---|---|---|
| `FVG` / `BISI` | AOI | `FVG_CONT`, `FVG_MIT` ✅ |
| `IFVG` | AOI | `IFVG` ✅ |
| `ORDER BLOCK` | AOI | `ORDER_BLOCK`, `OB_MIT` ✅ |
| `RBS` / `SBR` | POI | `SH_BMS_RTO`, `SMS_BMS_RTO` — **da verificare** |
| **`QM` (Quasimodo)** | POI | **nessuna** |
| **`OCL` (Open Close Levels)** | POI | **nessuna** |
| **`CLASSIC V` / `CLASSIC A`** | POI | **nessuna** |
| **`BPR`** | AOI | **nessuna** |
| **`BREAKER BLOCK`** | AOI | **nessuna** |
| **`QMX`** | composito | **nessuna** |
| **trendline (3 tipi + confluenza)** | POI | **nessuna** |

**Sette primitive su undici non hanno alcuna implementazione.** Fra queste c'è
`OCL`, che è la stessa cosa del livello SNR di MSNR (A-05) — la primitiva più
fondamentale dell'intero corpus.

## D-08 · Il livello da solo non è un segnale · `EXPLICIT` nella fonte

Questa **non** è una mia inferenza: è una frase della fonte (M-04).

> "We do not blindly execute trades simply because price has reached an SNR
> level. These levels become actionable only after all other confluences have
> been confirmed… and we observe a clear rejection from that zone. This
> rejection must align with the higher timeframe order flow."

Il metodo prescrive tre condizioni **in cascata** prima di un ingresso:

```text
1. livello raggiunto              (condizione necessaria, non sufficiente)
2. confluenze confermate          (pattern, momentum, sweep di liquidità)
3. rifiuto osservato dalla zona
4. allineamento con l'order flow del timeframe superiore
```

**Da verificare sull'implementazione:** quante delle strategie SMC/SNR dell'EA
richiedano tutte e quattro le condizioni, e quante generino un segnale al solo
tocco del livello. Non l'ho verificato in questa consegna. È il controllo di
fedeltà a più alto rendimento fra quelli ora possibili, perché la fonte è
esplicita e la condizione è binaria.

## D-09 · Corpo contro ombra: la regola più ripetuta del corpus · `EXPLICIT`

Tre fonti indipendenti usano lo stesso discriminante:

| Fonte | Regola |
|---|---|
| `My Rare SNR Course` (S-04) | un livello è rotto solo da un **corpo** di candela |
| `Yanu Emmanuel` (M-03) | un livello diventa flipped solo se una candela **chiude oltre con corpo pieno**, non con l'ombra |
| `Yanu Emmanuel` (M-05) | il BOS è valido solo con **corpo pieno**; con l'ombra non è un BOS |

**Da verificare sull'implementazione:** se le rotture di livello e i BOS nel
codice usino il corpo o l'estremo della candela. È un controllo puntuale, e una
divergenza qui cambierebbe il comportamento di ogni strategia strutturale.

## D-10 · CRT non ha una strategia dedicata, ma tre candidate · `da verificare`

Il modello a tre candele di C-03 (range → sweep → ingresso, con invalidazione su
chiusura) somiglia a tre strategie dell'EA:

| Strategia EA | Selettore | Perché candidata |
|---|---|---|
| `THREE_BAR_DELIVERY_BREAK` | 27 | modello a **tre barre**, come CRT |
| `TURTLE_SOUP` | 17 | archetipo dello sweep di liquidità fallito |
| `LIQ_SWEEP` | 7 | sweep esplicito, ed è la sola strategia misurata con PF > 1 (1.04) |

Nessun confronto eseguito. Ma CRT fornisce una **regola di invalidazione
esatta** (`close[i-1] > CRH` annulla il setup) che è il tipo di condizione che
distingue uno sweep vero da una rottura: vale la pena verificare se una delle
tre la implementi.

## D-07 · L'architettura del corpus e quella dell'EA non coincidono · `INFERRED`

**Questa è una lettura mia, non un'affermazione della fonte.** La segnalo perché
riguarda il modo in cui l'intero progetto è impostato.

> Aggiornamento dopo la lettura di Yanu Emmanuel: D-08 rafforza questa lettura,
> ma **non la dimostra**. D-08 è esplicito nella fonte e riguarda una singola
> strategia (Malaysian SNR); D-07 resta una mia generalizzazione all'intera
> architettura.

| | Corpus (Alchemist) | EA NEXUS |
|---|---|---|
| Forma | **una pipeline** con ruoli: struttura → liquidità → killzone → POI d'ingresso | **37 strategie parallele e indipendenti** |
| Decisione | un POI si forma quando 2–3 elementi **convergono** | ogni strategia produce un segnale per conto proprio |
| Composizione | dichiarata e ordinata (`MSNR → SMC → LIT → ICT`) | somma di score, con conviction (oggi disattivata) |

Nel corpus, `FVG`, `ORDER BLOCK` e `SNR` **non sono strategie**: sono
*primitive* che il metodo compone. Nell'EA sono diventate 37 strategie che
votano in parallelo.

Non concludo che questo spieghi l'assenza di edge — sarebbe una spiegazione
comoda e non l'ho misurata. Ma è un'ipotesi **testabile**, ed è la prima
ipotesi strutturale che il corpus permette di formulare. Va messa fra le
decisioni del proprietario, non applicata.

---

# Cosa manca ancora

## PDF non ancora letti (archiviati, hash registrato)

| File | Pagine | Perché serve |
|---|---:|---|
| `Sequence.pdf` (p. 21–76) | 56 | resto del framework Alchemist: 20 pagine su 76 lette |
| `Sequence_1.pdf` | 74 | seconda parte di Alchemist; A4.2 le attribuisce 55.488 caratteri OCR, la densità testuale più alta della famiglia |
| `SNR Malaysia.pdf` | 74 | è la fonte plausibile di `MALAYSIAN_SNR` (selettore 26), strategia live mai misurata |
| `Secret Of 411(1).pdf` | 16 | famiglia "411", stessa origine del metodo trendline; interamente per immagini |

## PDF ancora mancanti — 6 su 13

`863955768-MSNR-x-SMC-x-ICT-the-Alchemist-Yanu-Emmanuel.pdf` ·
`Sequence_2_unlocked.pdf` ·
`allyouneedtoknow-230110032117-f4fdcdb0.pdf` ·
`candlesticksfibonacciandchartpatterntrading-…pdf` ·
`flippingmarkets1-230503210106-91bd5cfc.pdf` · `My Rare SNR Course 2.pdf`
(voce distinta in A4.2 con 10 pagine — ricevuta)

Il primo della lista merita attenzione: il titolo
`MSNR-x-SMC-x-ICT-the-Alchemist` contiene **la stessa composizione** che
`Sequence.pdf` dichiara (`MSNR → SMC → LIT → ICT`). È verosimilmente una
seconda esposizione dello stesso framework, di un altro autore.

**`Sequence_2_unlocked.pdf` resta il caso peggiore:** A4.2 gli attribuisce 119
pagine e **zero** testo estratto. Con i due file ricevuti ora sappiamo che la
famiglia "Sequence" **è** Alchemist, cioè il framework di composizione — non un
modello proprietario oscuro. Il terzo file resta l'unico non recuperabile con
l'estrazione, e va letto a vista come gli altri.

## Informazioni che nessuno dei file letti fornisce

- **Orari delle killzone SNR** (S-11): marcate sui grafici, mai dichiarate.
- **Soglie di "momentum"** (S-07, I-06): "strong momentum", "long candles",
  "short wicks" non sono mai quantificati in nessuna delle tre fonti.
- **Regola di stop loss generale** (S-10): solo esempi, mai una regola.
- **Chart refinement** (S-12): trattenuto dall'autore, dietro accesso a pagamento.

---

## Collegamenti

`docs/sources/corpus/` · `docs/sources/SOURCE_MANIFEST.json` ·
`docs/audits/master/NEXUS_MASTER_GAPS.md` ·
`docs/audits/master/NEXUS_MASTER_PROJECT_v18_ANALYSIS.md`
