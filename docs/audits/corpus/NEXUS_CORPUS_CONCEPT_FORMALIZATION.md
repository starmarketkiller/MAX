# FORMALIZZAZIONE DEI CONCETTI DAL CORPUS D'ORIGINE

> Prima lettura diretta delle fonti originali. **Documento analitico**: nessun
> file di codice è stato modificato. Nessuna strategia è dichiarata fedele o non
> fedele — dove codice e fonte divergono, la voce è marcata
> `CANDIDATE_DIVERGENCE` e richiede conferma.

| | |
|---|---|
| Data | 2026-07-26 |
| PDF ricevuti | **5 su 13** dichiarati nel blocco A4.2 del Master v18 |
| PDF letti integralmente | 3 (`My Rare SNR Course`, `My Rare SNR Course 2`, `ict-trading`) |
| PDF archiviati e non ancora letti | 2 (`SNR Malaysia` 74 p, `Secret Of 411(1)` 16 p) |
| PDF ancora mancanti | 8 |
| Registro fonti | `docs/sources/SOURCE_MANIFEST.json` |

## Verifica di integrità delle fonti

| File | Pagine reali | A4.2 dichiara | Coincide | Testo nativo |
|---|---:|---:|:---:|---:|
| `My Rare SNR Course.pdf` | 29 | 29 | ✅ | 29/29 (348 car.) |
| `My Rare SNR Course 2.pdf` | 10 | 10 | ✅ | **0/10** |
| `SNR Malaysia.pdf` | 74 | 74 | ✅ | 74/74 (888 car.) |
| `Secret Of 411(1).pdf` | 16 | 16 | ✅ | **0/16** |
| `ict-trading-…pdf` | 91 | 91 | ✅ | 91/91 (58.358 car.) |

**I conteggi pagina di A4.2 sono corretti**, verificati con `pypdf`. I conteggi
di *caratteri* di A4.2 non sono riproducibili con estrazione nativa perché
quell'audit usava OCR supplementare: quattro file su cinque hanno 10 caratteri
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

## ⚠️ Il corpus contiene tre metodologie distinte, non una

La prima cosa che la lettura diretta smentisce è un'assunzione implicita: che i
file "SNR" siano lo stesso corso in più parti.

| Famiglia | File | Autore/origine | Metodo |
|---|---|---|---|
| **SNR / Flipping** | `My Rare SNR Course.pdf` | Price Action Traders, `@iadegboruwa` | livelli SNR dal confine close/open, flipping, GAP_SNR, DOJI_SNR |
| **Trendline "411"** | `My Rare SNR Course 2.pdf` | `liquidityinducementcourses.com`, "by 411" | 6 tipi di trendline, confluenza SNR+TL, XR/QM/666 TL |
| **ICT** | `ict-trading-…pdf` | dipprofit.com (divulgazione del metodo di Michael J. Huddleston) | FVG, OTE, Order Block, Displacement, Silver Bullet |

`My Rare SNR Course 2.pdf` **non è la seconda parte** di `My Rare SNR Course.pdf`:
è un corso di un altro autore su un altro metodo. Il nome del file induce in
errore, e A4.2 li aveva raggruppati come se fossero affini.

**Conseguenza:** la regola §A4.2 "la terminologia duplicata fra corsi non va
trattata come equivalenza semantica senza riconciliazione" non è teorica. Qui
"SNR" significa due cose diverse in due file che si chiamano quasi uguale.

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

**Da confermare:** se un'altra fonte del corpus (8 PDF ancora mancanti) definisca
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

---

# Cosa manca ancora

## PDF non ancora letti (archiviati, hash registrato)

| File | Pagine | Perché serve |
|---|---:|---|
| `SNR Malaysia.pdf` | 74 | è la fonte plausibile di `MALAYSIAN_SNR` (selettore 26), strategia live mai misurata |
| `Secret Of 411(1).pdf` | 16 | famiglia "411", stessa origine del metodo trendline; interamente per immagini |

## PDF ancora mancanti — 8 su 13

`863955768-MSNR-x-SMC-x-ICT-the-Alchemist-Yanu-Emmanuel.pdf` ·
`Sequence.pdf` · `Sequence_1.pdf` · `Sequence_2_unlocked.pdf` ·
`allyouneedtoknow-230110032117-f4fdcdb0.pdf` ·
`candlesticksfibonacciandchartpatterntrading-…pdf` ·
`flippingmarkets1-230503210106-91bd5cfc.pdf` · (+ eventuale duplicato SNR)

**I tre file `Sequence*` restano i più importanti e i più problematici:** A4.2
dichiara che `Sequence_2_unlocked.pdf` ha 119 pagine e **zero** testo estratto.
Sono la famiglia "Sequence / Proprietary Models", cioè il modello proprietario
che il Master raccomanda di isolare.

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
