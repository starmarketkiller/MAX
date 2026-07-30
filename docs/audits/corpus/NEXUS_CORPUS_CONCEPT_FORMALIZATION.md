# FORMALIZZAZIONE DEI CONCETTI DAL CORPUS D'ORIGINE

> Prima lettura diretta delle fonti originali. **Documento analitico**: nessun
> file di codice è stato modificato. Nessuna strategia è dichiarata fedele o non
> fedele — dove codice e fonte divergono, la voce è marcata
> `CANDIDATE_DIVERGENCE` e richiede conferma.

| | |
|---|---|
| Data | 2026-07-26 · aggiornato 2026-07-30 (PARTE 7, `Sequence_2.pdf`) |
| PDF ricevuti | **9 su 13** dichiarati in A4.2, **+1 fuori elenco** (`CANDLE_RANGE_THEORY`) |
| PDF letti integralmente | 6 (`My Rare SNR Course`, `My Rare SNR Course 2`, `ict-trading`, `Yanu Emmanuel`, `CANDLE_RANGE_THEORY`, `Sequence_2`) |
| PDF letti parzialmente | 1 (`Sequence` — 20 pagine su 76) |
| PDF archiviati e non ancora letti | 3 (`SNR Malaysia` 74 p, `Secret Of 411(1)` 16 p, `Sequence_1` 74 p) |
| Conferme incrociate della primitiva open/close | **6 fonti indipendenti** (S-01, A-05, A-06, M-01, Q-03, Q-08) |
| PDF ancora mancanti | **4** |
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

# PARTE 7 — Sequence_2.pdf (il file 9/13, ora recuperato)

Fonte: `Sequence_2.pdf`, 119 pagine, lette integralmente via rendering
multimodale (zero testo nativo, confermato da A4.2 e da questa verifica).
Bilingue inglese/indonesiano, autore `@abayforex`, stessa firma di
`Sequence.pdf`. **È la fonte più densa e più precisamente quantificata
dell'intero corpus.**

A differenza di `Sequence.pdf` (framework Alchemist a livello di composizione),
questo file entra nel dettaglio operativo di singoli concetti — spesso con
numeri esatti dove le altre fonti si fermavano a una descrizione qualitativa.
Dove un concetto qui **ri-conferma** una voce già formalizzata (es. A-03, A-04,
A-05), lo segnalo esplicitamente invece di duplicare il predicato.

## Q-01 · Fresh / Unfresh / Flipped — `EXPLICIT`, specifica completa

Ri-conferma e **completa** M-03 (Yanu Emmanuel), che aveva già la macchina a
stati ma non i numeri. Qui la fonte li dà:

> "A zone is considered fresh if it has never been touched." · "If touched by a
> wick → unfresh." · "If broken through by a full body candle → the zone
> becomes fresh again." · "A zone can only be used a maximum of **2 times**."
> "Exception: if it was previously a daily gap that produced a strong reaction,
> then the zone can be reused without following the 2-use limit."

**Predicato deterministico completo:**

```text
stato(livello) = FRESH        se mai toccato da wick o corpo
stato(livello) = UNFRESH      se toccato da un wick (non rotto a corpo pieno)
stato(livello) = FRESH        se rotto da una candela a CORPO PIENO (si "flippa")
usi_massimi(livello) = 2
  eccezione: livello nato da un daily gap con reazione forte pregressa
             → nessun limite di utilizzo
```

Rispetto a M-03 (che aveva la transizione qualitativa) questo predicato
aggiunge due elementi **quantitativi e testabili**: il numero massimo di usi
(2) e l'eccezione del daily gap. È lo stesso identico discriminante corpo/ombra
già visto in S-04, M-03, M-05 — quinta conferma indipendente.

## Q-02 · Checklist di validazione SNR — `EXPLICIT`, tre condizioni congiunte

> "To confirm whether an SNR level is tradable, make sure: 1. Price has tapped
> the wick/shadow. 2. Liquidity has been collected (liquidity sweep). 3. Price
> is located in a congestion or reaction zone. If all three conditions are met,
> the level is considered valid for buying or selling."

```text
valido(livello) = tocco_wick(livello) AND liquidity_sweep(livello) AND zona_congestione(livello)
```

È una versione più operativa di M-04 (livello → confluenze → rifiuto →
allineamento HTF): qui le "confluenze" sono ridotte a tre condizioni
enumerate e congiunte, non una lista aperta.

## Q-03 · RBS / SBR — `EXPLICIT`, ri-conferma di A-03 con esempio numerico

Stessa definizione di A-03 (Break → Retest → Continue), qui con un esempio
concreto e quantificato:

> "If XAU/USD breaks above the $2,400 resistance level and then retests that
> level while showing bullish rejection candles, the level now acts as RBS.
> Traders may look for long entries around $2,400 with stop-losses placed
> slightly below the zone."

Nota aggiuntiva della fonte, non presente in A-03: *"Higher timeframes (such as
H4 or Daily) give stronger and more reliable RBS/SBR levels."* — un requisito
di timeframe minimo che le altre fonti non davano.

## Q-04 · QM / Quasimodo — `EXPLICIT`, sequenza a 4 passi per entrambe le direzioni

Estende A-04 con la sequenza completa e simmetrica (A-04 aveva solo la versione
ribassista):

```text
QM ribassista (Sell Setup):
  1. il prezzo sale  → forma un Higher High (HH)
  2. pullback        → forma un Higher Low (HL)
  3. il prezzo risale ma con momentum più debole, poi rompe sotto l'HL
     → la struttura inizia a rompersi
  4. il prezzo ritraccia sulla stessa area → QUELLO è l'entry SELL

QM rialzista (Buy Setup):
  1. il prezzo scende → forma un Lower Low (LL)
  2. pullback         → forma un Lower High (LH)
  3. il prezzo riscende ma fallisce un nuovo LL, poi rompe sopra l'LH
     → la struttura inizia a spostarsi
  4. il prezzo ritraccia sulla stessa area → QUELLO è l'entry BUY
```

> "Price seems to still follow the previous direction, but suddenly the
> structure breaks and the direction changes." · "QM is a trap area — where the
> market intentionally lures the majority of traders into entering in the
> wrong direction."

## Q-05 · QMM — Quasimodo Manipulation — `EXPLICIT`, concetto nuovo

Non presente in nessun'altra fonte del corpus. Un sotto-pattern di QM:

> "QMM (Quasimodo Manipulation) is the phase where the market pretends to break
> a key level (QML) to trap most traders, before eventually moving back in the
> true direction." · "Price fakes a break above or below the QML, making it
> look like a valid breakout. Then price returns back inside the range and
> continues in the original direction."

```text
QMM: rottura FALSA del livello QM → il prezzo rientra nel range
     → si muove nella direzione ORIGINALE (opposta alla falsa rottura)
```

`MISSING`: nessuna soglia su quanto la falsa rottura debba estendersi oltre il
livello prima di essere considerata QMM invece di una rottura vera.

## Q-06 · QMC — Quasimodo Continuation — `EXPLICIT`, concetto nuovo

Complementare a QMM: qui la falsa mossa precede una **continuazione**, non
un'inversione.

```text
Uptrend:
  1. il mercato forma un Higher High (HH)
  2. ritraccia formando un Higher Low (HL)
  3. risale a formare un FALSO HH (liquidity grab / fake wick)
  4. rompe e chiude sotto l'HL → segnale di cambio struttura

Downtrend: sequenza speculare (LL → LH → falso LL → rottura sopra l'LH)
```

> "QMC = a fake continuation move + a clean retest entry." · "Waiting for the
> break + retest offers a far safer and more reliable entry than chasing
> normal support or resistance levels."

## Q-07 · QMX — QM + Trendline Crossing — `EXPLICIT`, completa A-07

A-07 (da `Sequence.pdf`) aveva i diagrammi ma nessuna regola quantitativa
("MISSING: la fonte non definisce la tolleranza dell'intersezione né i criteri
di validità della candela engulfing"). Questa fonte la completa:

```text
QMX = rottura di struttura QM  +  incrocio fra trendline e area QM/SNR
segnale di conferma: candela ENGULFING nel punto di incrocio
```

> "QMX is a combination of two major market elements: 1. QM (Quasimodo / Change
> of Character) 2. Trendline Crossing (X) — the intersection between the
> trendline and the QM/SNR area. This combination creates a high-probability
> reversal signal because two strong confirmations appear at the same time."

`MISSING` resta: nessuna tolleranza numerica di prezzo/tempo per definire
"stesso punto" fra i due elementi. Ma la logica dei tre requisiti congiunti
(rottura QM + incrocio trendline + candela engulfing) è ora esplicita, dove
prima era solo un diagramma.

## Q-08 · OCL — Open-Close Level — `EXPLICIT`, ri-conferma A-05/M-01 con peso di sessione

Stessa primitiva di A-05, S-01, M-01 (**sesta conferma indipendente** della
primitiva close/open), con un elemento nuovo: la sessione in cui si forma
influenza l'affidabilità.

> "An OCL formed during the New York or London sessions often gives us
> stronger zones and better momentum compared to the Asian session. If the OCL
> is created during the London/New York overlap, it tends to be more reliable
> with a lower chance of being fake-broken."

```text
forza(OCL) = alta   se formata in sessione Londra/NY (specialmente overlap)
forza(OCL) = bassa  se formata in sessione Asia
```

Nessuna delle altre cinque fonti che parlano della stessa primitiva
(open/close level) menziona un peso legato alla sessione di formazione.

## Q-09 · Candle Equilibrium (CE) — `EXPLICIT`, concetto nuovo, zona quantificata

Non presente altrove nel corpus. Definizione precisa:

> "CE (Candle Equilibrium) is the balance point of a candle — the exact area
> where buying and selling pressure are equalized." · "The most commonly used
> area is the **45%-50% zone of the candle's range** (high to low, including
> wicks)." · "Why this range? 1. Price naturally gravitates toward the midpoint
> to rebalance orders. 2. It filters noise from very long wicks. 3. It provides
> a more accurate equilibrium than the exact 50%."

**Predicato deterministico:**

```text
range_candela = high[i] - low[i]                (include le ombre)
CE_zona = [low[i] + 0.45 * range_candela ,  low[i] + 0.50 * range_candela]   (candela bearish, misurato da high)
CE_zona = [high[i] - 0.50 * range_candela , high[i] - 0.45 * range_candela]  (per simmetria, versione bullish da open/low)
```

Uso operativo dichiarato: si aspetta il ritorno del prezzo in questa zona dopo
una candela impulsiva, con conferma di rigetto (wick, BOS, sweep di liquidità)
prima di entrare nella direzione dell'impulso originale.

## Q-10 · Regole di tocco trendline (MSNR Trendlines) — `EXPLICIT`, completa A-08/T-01

Aggiunge due regole quantitative assenti in A-08 e T-01:

> "Touches must be equally spaced — this creates a strong trendline." · "Touches
> must occur above or below SNR. If price is above SNR → strong trend (bullish
> bias). If price is below SNR → weak trend (bearish bias)." · "Never force a
> line the market doesn't show you — don't try to make it fit."

```text
trendline_valida = tocchi equidistanti (non forzati)
bias = bullish  se prezzo sopra SNR
bias = bearish  se prezzo sotto SNR
```

`MISSING`: nessuna tolleranza numerica per "equidistanti".

## Q-11 · Confluenza / [X] Factor — `EXPLICIT`, ri-conferma A-09 con una regola operativa in più

Stessa definizione di A-09 (2-3 elementi che convergono nello stesso punto),
con un'aggiunta pratica assente altrove:

> "You don't need to wait for a perfect candle confirmation, because when
> everything aligns, the plan itself already tells you to act." · "This is
> trading based on 'confirmation through the plan,' not confirmation through
> emotion."

Cioè: quando **trendline + SNR + liquidity** (o altre 2-3 fonti indipendenti)
convergono nello stesso punto, la fonte dichiara esplicitamente che **non serve
un'ulteriore candela di conferma**. È in tensione con M-06 (che richiede una
candela di rifiuto con corpo spesso) — due fonti diverse, non riconciliate qui.

## Q-12 · SMT Divergence — `EXPLICIT`, concetto nuovo, con coppie nominate

Non presente altrove nel corpus.

> "SMT stands for Smart Money Technique. Divergence simply means a difference
> in movement. In simple terms, SMT Divergence is used to spot when two assets
> that normally move together... start moving differently."

**Tabella degli scenari, completa e deterministica:**

```text
Gold (XAU) scende, Silver (XAG) NON scende  → il calo di Gold è probabile fake  → segui Silver, aspettati reversal rialzista
Silver (XAG) scende, Gold (XAU) NON scende  → il calo di Silver è probabile fake → segui Gold, aspettati reversal rialzista
Gold (XAU) sale, Silver (XAG) NON sale      → il rialzo di Gold è probabile fake → segui Silver, aspettati reversal ribassista
Silver (XAG) sale, Gold (XAU) NON sale      → il rialzo di Silver è probabile fake → segui Gold, aspettati reversal ribassista
```

Coppie correlate dichiarate esplicitamente per l'applicazione dello stesso
principio: **EURUSD ⇌ GBPUSD**, **USDCAD ⇌ USDCHF**, **AUDUSD ⇌ NZDUSD**, oltre
a Gold-Silver. Condizioni di conferma richieste (non basta la divergenza sola):
struttura di mercato chiara (SMT vicino a fine trend, non a metà), sweep di
liquidità sul lato "fake", e una reazione/BOS sul lato che non ha fatto la
mossa fake, prima di entrare.

## Q-13 · Quarterly Theory (QT) — `EXPLICIT`, AMD multi-timeframe con orari

Il modello è **Accumulation → Manipulation → Distribution → Reversal/Continuation
(Q1→Q2→Q3→Q4)**, applicato in modo **frattale** su cinque livelli temporali
annidati: annuale, mensile, settimanale, giornaliero, intraday (finestre di 90
minuti).

**Tabella oraria giornaliera dichiarata (GMT+7):**

```text
Q1 Asia        00:00–06:00   Accumulation
Q2 London      06:00–12:00   Manipulation
Q3 New York AM 12:00–18:00   Distribution
Q4 New York PM 18:00–00:00   Reversal / Continuation
```

Più una tabella intraday dettagliata (finestre da 90 minuti dentro ogni
sessione, con orari Asia KZ/London Open/New York/PM per ciascun quarto) e una
struttura annuale/mensile/settimanale con la stessa logica Q1-Q4 applicata a
anno, mese e settimana.

> "The market does not move randomly. Every period follows the same rhythm:
> Accumulation → Manipulation → True Direction Revealed → Continuation or
> Reversal."

`ATTENZIONE`: la fonte etichetta la tabella "GMT+7" ma non chiarisce se sia il
fuso del broker dell'autore o un riferimento assoluto; non l'ho potuto
verificare con una fonte esterna come fatto per D-01/F-02. Va trattata come
`CANDIDATE`, non presa alla lettera per un confronto orario diretto.

## Q-14 · Daily Bias Cheat Sheet — `EXPLICIT`, checklist a 5 concetti

> "I use the following five core concepts to define my daily bias."

```text
1. Internal & External Range Liquidity (IRL/ERL) — il prezzo si muove da ERL a IRL o viceversa?
2. Candle Body Close (PDH/L & PWH/L)             — il close ha superato l'high/low del giorno precedente?
3. Institutional Order Flow                       — la struttura è bullish o bearish? il prezzo rispetta i PD Arrays?
4. SMT Divergence                                 — c'è divergenza con un mercato correlato?
5. Weekly Profiles                                 — è confermato l'high o il low della settimana?

Conclusione: c'è un Draw on Liquidity chiaro? Se no → restare neutrali è la decisione corretta.
```

## Q-15 · IRL / ERL — Internal / External Range Liquidity — `EXPLICIT`, concetto nuovo

> "External Range Liquidity (ERL) is defined by Swing Highs and Swing Lows,
> where the accumulation of liquidity tends to reside." · "Internal Range
> Liquidity (IRL) is defined by imbalances (FVG/Fair Value Gaps)." · "After
> price takes ERL, the draw on liquidity shifts toward IRL. After price moves
> into IRL, liquidity will move back toward ERL."

```text
ERL = ai livelli di Swing High/Swing Low
IRL = agli squilibri (FVG) dentro il range
il prezzo alterna la destinazione fra ERL e IRL
```

## Q-16 · Institutional Order Flow — STH/ITH/LTH — `EXPLICIT`, concetto nuovo

Gerarchia a tre livelli per i punti di struttura, con criterio di validazione:

```text
STH/STL (Short-Term High/Low)        = high/low fra due candele successive di direzione opposta
ITH/ITL (Intermediate-Term High/Low) = STH/STL fra due Short-Term High/Low sul lato opposto
LTH/LTL (Long-Term High/Low)         = formato da un livello di timeframe superiore
```

> "Once an ITH is confirmed, it is expected to remain intact until price
> reaches an opposing higher-timeframe draw on liquidity."

## Q-17 · Weekly Profiles — `EXPLICIT`, quattro pattern nominati

```text
Classic Expansion (bullish)   — consolidamento Lun-Mer, espansione Gio-Ven
Midweek Reversal (bearish)    — Lun/Mar salgono, Mer inverte
Consolidation + Thursday Reversal (bullish) — range Lun-Mer, Gio rompe HTF discount, Ven espande
TGIF Friday (bearish)         — espansione Lun-Gio, Ven ritraccia nel range settimanale
```

`MISSING`: nessuna soglia quantitativa su cosa distingue un "consolidamento"
da un "range" o un'"espansione".

## Q-18 · Daily Profiles — `EXPLICIT`, cinque pattern con orari sessione

Cinque profili giornalieri nominati, ciascuno con orari di sessione dichiarati
esplicitamente (tutti nello stesso formato ET-like usato dalla fonte, non
GMT+7 come in Q-13 — le due tabelle orarie della stessa fonte usano
**convenzioni diverse**, mai riconciliate esplicitamente nel testo):

```text
1. London Reversal, NY Continuation — Londra inverte, NY continua la direzione vera
   Forex 07:00-10:00, Indici 08:30-11:00 (orario non specificato se ET o altro)

2. NY Reversal — Londra fallisce ad espandersi, NY forma il vero high/low del giorno

3. NY Manipulation & Expansion — Londra accumula/consolida, manipolazione e
   espansione avvengono entrambe a New York (esempio esplicito di AMD/Power of 3)

4. NY Judas — falsa direzione a Londra ("Judas Swing"), inversione e
   espansione vera a New York

5. Seek and Destroy — nessun bias direzionale chiaro, il prezzo prende
   liquidità su entrambi i lati prima di mostrare l'intento reale
```

Ogni profilo specifica anche il comportamento atteso di High/Low of the Day
(fasce orarie in cui tipicamente si formano) e l'uso opzionale di SMT
Divergence come conferma aggiuntiva (mai obbligatoria).

`MISSING`: la fonte non chiarisce se gli orari "07:00-10:00" ecc. siano ET,
GMT o server time — diversamente da I-07 (PDF ICT) che specifica "ET" in modo
esplicito.

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
| `QM` (Quasimodo) | POI | **esiste** (`NXS_Quasimodo_Detect`, `NXS_BjorgumZones.mqh:113-146`) ma **nessuna strategia la consulta** — vedi F-06 |
| **`OCL` (Open Close Levels)** | POI | **nessuna** |
| **`CLASSIC V` / `CLASSIC A`** | POI | **nessuna** |
| **`BPR`** | AOI | **nessuna** |
| **`BREAKER BLOCK`** | AOI | **nessuna** |
| **`QMX`** | composito | **nessuna** |
| **trendline (3 tipi + confluenza)** | POI | **nessuna** |

**Sei primitive su undici non hanno alcun codice.** Fra queste c'è `OCL`, che è
la stessa cosa del livello SNR di MSNR (A-05) — la primitiva più fondamentale
dell'intero corpus. `QM` è un caso a parte: il codice esiste (rilevatore
visivo) ma nessuna strategia lo consulta per decidere un ingresso — vedi F-06.
È lo stesso pattern già visto per BOS/CHOCH in F-04: capacità presente, non
usata.

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

## D-11 · `QM` (Quasimodo) esiste nel codice, ma solo per il disegno · `CANDIDATE_MATCH` sulla struttura, `DIVERGENTE` sull'uso

**Fonte** (Q-04): sequenza a 4 passi (HH→HL→rottura debole→retest = entry
sell, e speculare per buy), usata per generare un **segnale di ingresso**.

**Codice** (`NXS_BjorgumZones.mqh:105-146`):

```cpp
// Quasimodo detector (HH then deeper LL then HL above prior LH) - pure visual
struct SNXSQuasimodo { bool detected; int direction; double anchorPrice; datetime anchorTime; };
SNXSQuasimodo NXS_Quasimodo_Detect(...)
```

Il commento nel codice stesso dice **"pure visual"**. Verificato: l'unico altro
punto del codice che referenzia `NXS_Quasimodo_Detect` o `SNXSQuasimodo` è
`NEXUS_VisualSuite_v2.mq5:381-390`, che lo disegna sul grafico
(`NXS_VS_DrawQuasimodo`). **Nessuna delle 37 strategie live lo consulta.** È
verificato per ricerca esaustiva del simbolo in tutto `MQL5/Include/` e
`MQL5/Experts/`.

La struttura di rilevamento (`hs[0]<hs[1]>hs[2]` con condizioni sui minimi) è
concettualmente compatibile con la sequenza HH→HL→LH→LL della fonte — non ho
verificato riga per riga la corrispondenza esatta dei quattro passi, quindi la
marco `CANDIDATE_MATCH` sulla logica interna. Ma sull'**uso** il verdetto è
netto: `DIVERGENTE`, perché la fonte prescrive QM come base per un ingresso e
nel codice è **solo un layer visivo dell'indicatore**, esattamente come BOS/CHOCH
in F-04 — capacità presente, mai collegata a una decisione di trading.

## D-12 · `AMD` / Quarterly Theory · `PARZIALE` — struttura presente, nesting multi-timeframe assente

**Fonte** (Q-13): Q1 Accumulation → Q2 Manipulation → Q3 Distribution → Q4
Reversal/Continuation, applicato in modo **frattale** su 5 livelli temporali
(anno, mese, settimana, giorno, intraday 90 min).

**Codice** (`NXS_AMDModel.mqh:7-119`): una macchina a stati con esattamente
quattro fasi — `AMD_ACCUMULATION`, `AMD_MANIPULATION`,
`AMD_CONTINUATION_DISTRIBUTION`, `AMD_REVERSAL_DISTRIBUTION` — che replica
concettualmente Q1→Q4: dentro il range asiatico = accumulation; prima chiusura
oltre il range = manipulation; 2+ chiusure oltre lo stesso lato = distribution
di continuazione; chiusura di rientro nel range dopo una manipolazione =
distribution di reversal. **Struttura a quattro fasi confermata, verificata
riga per riga.**

Due divergenze, non una:

1. **Nessun nesting multi-timeframe.** Il codice applica AMD **solo al livello
   giornaliero** (reset una volta al giorno, `g_amdSessionDay`). La fonte
   applica lo stesso ciclo Q1-Q4 anche ad anno, mese e settimana. Assente.
2. **Orari non confrontabili con certezza.** Il default del codice
   (`InpAsianStartHour=0`, `InpAsianEndHour=7`, in GMT) e la tabella oraria di
   Q-13 (Asia 00:00-06:00 **GMT+7**) non sono nella stessa unità e la fonte
   stessa non chiarisce se "GMT+7" sia un riferimento assoluto o il fuso del
   broker dell'autore — la stessa riserva già segnata in Q-13. **Non marco
   questo punto come divergenza confermata**, a differenza di D-01/F-02 dove
   avevo conferma esterna: qui servirebbe verificare l'intento dell'autore
   prima di trarre conclusioni sull'orario.

## D-13 · CE, OCL, SMT Divergence, IRL/ERL — nessuna implementazione · `EXPLICIT`

Ricerca esaustiva nel codice (`MQL5/Include/NEXUS_v1/*.mqh`,
`MQL5/Experts/*.mq5`, `MQL5/Indicators/*.mq5`) per ciascun concetto:

| Concetto | Fonte | Trovato nel codice |
|---|---|---|
| Candle Equilibrium (CE), zona 45-50% | Q-09 | **nessuno** |
| OCL — Open Close Level | Q-08 / A-05 / M-01 | **nessuno** (già in D-06) |
| SMT Divergence | Q-12 | **nessuno** |
| IRL / ERL | Q-15 | **nessuno** |
| STH / ITH / LTH (Institutional Order Flow) | Q-16 | **nessuno** |
| Weekly / Daily Profiles nominati | Q-17, Q-18 | **nessuno** |

Sei concetti, tutti quantificati con precisione dalla fonte, **zero
implementazioni**. A differenza di QM (D-11) o della struttura BOS/CHOCH
(F-01/F-04), qui non c'è nemmeno una capacità inutilizzata: il codice non ha
alcun riferimento, nemmeno visivo, a nessuno di questi sei concetti.

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

## PDF ancora mancanti — 4 su 13

`Malaysian SNR Emperor.pdf` (distinto da `SNR Malaysia.pdf`, già ricevuto —
sono due file diversi in A4.2, prima confusi in una singola voce di questo
elenco) · `allyouneedtoknow-230110032117-f4fdcdb0.pdf` ·
`candlesticksfibonacciandchartpatterntrading-forexfactorypdfdrive-210313181656.pdf`
· `flippingmarkets1-230503210106-91bd5cfc.pdf`

`Sequence_2_unlocked.pdf` (ricevuto come `Sequence_2.pdf`, PARTE 7) e
`863955768-MSNR-x-SMC-x-ICT-the-Alchemist-Yanu-Emmanuel.pdf` (ricevuto, PARTE 5)
erano ancora in questo elenco per una svista di aggiornamento: entrambi sono
già formalizzati altrove in questo documento. Rimossi qui.

Con tutti e tre i file `Sequence*` ora in mano (`Sequence.pdf` parziale,
`Sequence_1.pdf` non ancora letto, `Sequence_2.pdf` integrale) sappiamo che la
famiglia **è** Alchemist, cioè il framework di composizione — non un modello
proprietario oscuro. `Sequence_2.pdf` era il "caso peggiore" per zero testo
estraibile: ora letto per intero via rendering multimodale.

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
