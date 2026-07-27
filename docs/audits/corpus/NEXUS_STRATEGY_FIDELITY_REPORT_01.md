# RAPPORTO DI FEDELTÀ 01 — SMC / SNR contro le fonti d'origine

> Prima verifica di fedeltà eseguita contro le fonti originali, ora disponibili.
> **Nessun file di codice è stato modificato.** Questo documento constata; non
> corregge.

| | |
|---|---|
| Data | 2026-07-27 |
| Fonti primarie usate | `docs/sources/corpus/` (9 PDF archiviati con hash) |
| Formalizzazione di riferimento | `docs/audits/corpus/NEXUS_CORPUS_CONCEPT_FORMALIZATION.md` |
| Codice esaminato | `NXS_Structure.mqh`, `NXS_Strategies_SMC.mqh` (baseline `main` = `4465873`) |
| Esiti | 1 fedele · 1 divergenza confermata · 1 divergenza strutturale · 9 strategie con copertura di gate insufficiente |

## Livelli di giudizio

| | Significato |
|---|---|
| `FEDELE` | il codice implementa ciò che la fonte prescrive, verificato riga per riga |
| `DIVERGENTE` | fonte e codice dicono cose diverse, entrambe citate |
| `PARZIALE` | implementa una parte della prescrizione e ne omette altre |
| `NON VERIFICATO` | non esaminato in questa consegna |

**Cosa questo rapporto non fa.** Non dice che una strategia sia buona o cattiva:
la fedeltà a una fonte non è un edge. Una strategia può essere perfettamente
fedele e perdere denaro, e viceversa. Non ho misurato nulla qui.

---

## F-01 · Break of Structure — `FEDELE` ✅

**Fonte** (M-05, Yanu Emmanuel):

> "Break of market structure occurs when price **closes** above a swing
> high/low… A break of structure is only considered valid when price closes
> above the higher high **with a full body**; when price closes above the swing
> high **with a wick**, this is not considered as a break of structure."

**Codice** (`NXS_Structure.mqh:239-252`):

```cpp
double c1 = iClose(sym, tf, 1);
if(st.lastSwingHigh > 0 && c1 > st.lastSwingHigh){
   if(trendBefore == -1) st.chochUp = true;
   else                  st.bosUp   = true;
}
if(st.lastSwingLow > 0 && c1 < st.lastSwingLow){
   if(trendBefore == 1) st.chochDown = true;
   else                 st.bosDown   = true;
}
```

Il confronto è su `iClose`, non su `iHigh`/`iLow`. Una candela che perfora lo
swing con l'ombra ma chiude sotto **non** produce un BOS. È esattamente la
regola della fonte.

**In più, non richiesto dalla fonte ma corretto:** la separazione BOS/CHOCH è
mutuamente esclusiva e dipende dal trend *precedente* alla rottura. La fonte
parla solo di BOS; il codice distingue continuazione da inversione. È
un'estensione coerente, non una divergenza.

**Nota residua:** gli swing point sono individuati con `iHigh`/`iLow` (ombre).
La fonte non prescrive nulla in merito, e usare gli estremi per *individuare*
uno swing è convenzionale. Non è una divergenza; lo segnalo perché è l'unico
punto dove il codice usa l'ombra in questo percorso.

---

## F-02 · `SILVER_BULLET` — `DIVERGENTE` 🔴

**Fonte primaria** (I-07, PDF ICT):

> "The strategy works best when the market is busy, usually between **10 am–11
> am ET or 3 am–4 am ET**."

**Fonti esterne consultate** (marcate come tali: non fanno parte del corpus):
le tre finestre Silver Bullet sono London Open **03:00–04:00 ET**, AM Session
**10:00–11:00 ET**, PM Session **14:00–15:00 ET**; la London Open Killzone è
02:00–05:00 ET e la New York Open Killzone 08:30–11:00 ET. Le fonti esterne
**confermano** il PDF del corpus e aggiungono la terza finestra.

**Codice** (`NXS_Strategies_SMC.mqh:404-412`):

```cpp
datetime gmtNow = (datetime)((long)TimeCurrent() - (long)InpServerGMTOffset * 3600);
MqlDateTime mt; TimeToStruct(gmtNow, mt);
int h = mt.hour;
bool killzoneLO = (h >= 10 && h < 11);   // London KZ 10-11 GMT
bool killzoneNY = (h >= 14 && h < 15);   // NY KZ 14-15 GMT
```

### Conversione, con e senza ora legale americana

| Finestra della fonte | GMT in EST (inverno) | GMT in EDT (estate) |
|---|---|---|
| 03:00–04:00 ET (London Open SB) | 08:00–09:00 | 07:00–08:00 |
| 10:00–11:00 ET (AM SB) | 15:00–16:00 | 14:00–15:00 |
| 14:00–15:00 ET (PM SB) | 19:00–20:00 | 18:00–19:00 |

| Finestra del codice | Corrisponde in EST | Corrisponde in EDT |
|---|---|---|
| 10:00–11:00 GMT ("London KZ") | 05:00–06:00 ET → **nessuna finestra** | 06:00–07:00 ET → **nessuna finestra** |
| 14:00–15:00 GMT ("NY KZ") | 09:00–10:00 ET → **un'ora in anticipo** | 10:00–11:00 ET → **corretta** |

### Tre constatazioni distinte

1. **La finestra "London" non corrisponde a nulla.** 10:00–11:00 GMT è
   05:00–06:00 ET d'inverno e 06:00–07:00 ET d'estate. Non è la Silver Bullet
   di London Open (03:00–04:00 ET), e cade **fuori** anche dalla London Open
   Killzone (02:00–05:00 ET) in entrambi i regimi.
2. **La finestra "NY" è corretta solo sei mesi l'anno.** Coincide con
   10:00–11:00 ET durante l'ora legale americana; durante l'ora solare parte
   un'ora prima. Il codice converte l'ora del server in GMT tramite
   `InpServerGMTOffset`, ma **GMT non segue il DST americano**: lo sfasamento è
   strutturale, non un parametro da tarare.
3. **La terza finestra non esiste nel codice.** La PM Session (14:00–15:00 ET)
   non è implementata.

**Conseguenza pratica.** La strategia opera per metà del tempo in una finestra
che nessuna fonte indica, e nell'altra metà in una finestra corretta solo
d'estate. `SILVER_BULLET` non ha dati di sweep: qualsiasi misura futura senza
correggere questo misurerebbe una strategia diversa da quella che dichiara di
essere.

---

## F-03 · `MALAYSIAN_SNR` — `PARZIALE`

È la strategia con più materiale d'origine disponibile: un capitolo intero del
PDF Yanu Emmanuel. Confronto punto per punto.

### Cosa il codice fa bene ✅

| Prescrizione della fonte | Codice |
|---|---|
| M-01 — livelli sui prezzi di **chiusura**, ignorare le ombre | `iHighest(..., MODE_CLOSE, ...)`, `iClose(...)`; il commento dice esplicitamente *"Body-based levels (close, not wick)"* |
| M-06 — candela di rifiuto con corpo spesso | `bodyAbs = MathAbs(c1-o1)`; richiede `bodyAbs > atr*0.5` |
| M-06 — la candela chiude nella direzione del rifiuto | `c1 > o1` per il buy al supporto, `c1 < o1` per il sell alla resistenza |
| Cap. 3 — *storyline* come bias direzionale | `storyBull`/`storyBear` da chiusure H4 e D1 |
| Confluenza multi-timeframe | bonus di punteggio se il livello H4 coincide con un livello W1 |
| M-08 — evitare le ore a bassa volatilità | esclude la sessione asiatica |

Il commento nel codice — *"Body-based levels (close, not wick)"* — dimostra che
chi l'ha scritto conosceva la regola. Su questo punto la fedeltà è
**intenzionale**, non accidentale.

### Dove diverge 🔴

**1. Il livello non è la primitiva della fonte.**

> Fonte (M-01): *"You draw a line across the first candlestick's close to join
> the next candlestick's open."*

Il livello SNR è il **confine fra due candele adiacenti**: la chiusura di una e
l'apertura della successiva. Il codice invece calcola:

```cpp
int idxH4Hi = iHighest(g_sym, InpTFHigh, MODE_CLOSE, 12, 1);
double h4Hi = iClose(g_sym, InpTFHigh, idxH4Hi);
```

cioè **la chiusura più alta delle ultime 12 barre H4**. È un massimo su finestra
mobile, non una giunzione close/open. Entrambi sono "body-based", ma sono
oggetti diversi: la fonte produce **molti** livelli (uno per ogni coppia di
candele qualificata), il codice ne produce **due** (un massimo e un minimo di
finestra).

Questa è la divergenza più importante del rapporto, perché riguarda la
primitiva su cui tutte e quattro le fonti concordano.

**2. "Fresh" ha una definizione diversa, e non è un gate.**

> Fonte (M-03): *"A fresh SNR level is one that hasn't been touched or broken by
> the candle's wick or body."* — mai toccato, in assoluto.

```cpp
for(int i = 1; i <= 20; i++){
   if(hh >= h4Hi - atrH4*0.3 && hh <= h4Hi + atrH4*0.3 && i > 3) freshHi = false;
   ...
}
s.score = 68.0 + (freshHi ? 5.0 : 0.0);
```

Tre differenze:
- finestra di **20 barre**, non "mai";
- tolleranza di ±0.3 ATR attorno al livello, mentre la fonte parla di contatto;
- `i > 3` **esclude le ultime 3 barre**: un livello toccato due barre fa risulta
  ancora fresh.

E soprattutto: nella fonte fresh/unfresh determina **se il livello è
affidabile**; nel codice vale **+5 punti di score**. Un livello unfresh opera
comunque.

**3. La macchina a stati del flip è assente.**

M-03 descrive il ciclo `FRESH → UNFRESH → FLIPPED (SBR/RBS) → FRESH nella
direzione invertita`. In questa funzione non c'è: nessun tracciamento dello
stato del livello, nessuna inversione di ruolo. È il meccanismo centrale del
metodo, ed è il motivo per cui il corso si intitola *flipping*.

**4. L'allineamento con la struttura non usa la struttura.**

M-04 richiede allineamento con *"higher timeframe order flow, directional bias,
prevailing trend, or overall market structure"*. Il codice usa:

```cpp
bool storyBull = (h4C1 > h4C4 && d1C1 >= d1C2);
```

due confronti fra chiusure. `g_struct.trend`, `bosUp`, `chochUp` — che il
progetto calcola già correttamente (F-01) — **non sono consultati**.

**5. Le killzone non sono applicate.**

M-08: *"we mainly focus on trading the London and NY killzones"*. Il codice
esclude solo l'Asia, quindi ammette tutte le altre ore, non le due killzone.

---

## F-04 · Copertura dei gate nelle 12 funzioni SMC

Scansione automatica dei corpi delle funzioni `SNXSSignal` in
`NXS_Strategies_SMC.mqh`, per verificare **la presenza** dei gate che la fonte
prescrive (M-04: livello → confluenze → rifiuto → allineamento HTF).

| Strategia | struttura/BOS | sessione | fresh | candela rifiuto | bias HTF | gate |
|---|:---:|:---:|:---:|:---:|:---:|---:|
| `MALAYSIAN_SNR` | — | ✅ | ✅ | ✅ | ✅ | **4** |
| `SILVER_BULLET` | — | ✅ | — | ✅ | — | 2 |
| `IFVG` | ✅ | — | — | ✅ | — | 2 |
| `SMS_BMS_RTO` | ✅ | — | — | ✅ | — | 2 |
| `OTE_CONT` | ✅ | — | — | ✅ | — | 2 |
| `AMD_REVERSAL` | ✅ | — | — | — | — | 1 |
| `SH_BMS_RTO` | — | — | — | ✅ | — | 1 |
| `TURTLE_SOUP` | — | — | — | ✅ | — | 1 |
| `FVG_MIT` | — | — | — | ✅ | — | 1 |
| `OB_MIT` | — | — | — | — | — | **0** |

> La scansione rileva la **presenza** di un riferimento, non la sua correttezza.
> Un ✅ significa "il gate esiste", non "il gate è giusto" — `MALAYSIAN_SNR` ha
> quattro gate su cinque e resta `PARZIALE` per i motivi in F-03.

### Cosa dice questa tabella

**Nessuna strategia applica tutti e cinque i gate.** La migliore, `MALAYSIAN_SNR`,
ne ha quattro e non consulta la struttura. `OB_MIT` non ne ha nessuno: opera
sull'evento del livello, che è precisamente ciò che la fonte vieta —

> *"We do not blindly execute trades simply because price has reached an SNR
> level."*

**Il filtro di sessione esiste in 2 strategie su 10**, mentre le fonti
attribuiscono alle killzone un ruolo centrale (ICT le assegna esplicitamente il
ruolo di *timing* nella composizione Alchemist: `ICT : KILL ZONES`).

**Il riferimento alla struttura esiste in 4 su 10**, benché il progetto calcoli
BOS e CHOCH correttamente in un modulo dedicato. È capacità presente e non
usata.

---

## Sintesi

| Verifica | Esito |
|---|---|
| F-01 Break of Structure | **FEDELE** — usa la chiusura, come la fonte |
| F-02 `SILVER_BULLET` killzone | **DIVERGENTE** — una finestra inesistente, una corretta solo d'estate, una mancante |
| F-03 `MALAYSIAN_SNR` | **PARZIALE** — primitiva del livello diversa, fresh degradato a bonus, flip assente, struttura non consultata |
| F-04 copertura dei gate | 0 strategie su 10 applicano la cascata completa; `OB_MIT` non applica alcun gate |

### Il quadro che ne esce

Il progetto **conosce** le regole giuste — il commento *"Body-based levels
(close, not wick)"*, il BOS su chiusura, il concetto di fresh, la storyline
sono tutti presenti e corretti nell'intenzione. Ciò che manca è la
**composizione**: le condizioni che la fonte prescrive in cascata sono
implementate a macchia di leopardo, una qui e una là, e mai tutte insieme.

Questo è coerente con l'osservazione strutturale già registrata (D-07): il
corpus descrive una pipeline dove il segnale nasce dalla convergenza; l'EA
implementa strategie parallele dove ciascuna decide da sola con i gate che le
sono capitati.

**Non concludo che sia questa la causa dell'assenza di edge.** Non l'ho
misurato, e sarebbe una spiegazione comoda. Ma è la prima ipotesi che ora ha
sotto delle constatazioni verificate invece che un'impressione.

---

## Cosa NON è stato verificato

- Le strategie non-SMC (momentum, volatilità, trend): 25 su 37.
- La correttezza *interna* dei gate rilevati da F-04: la scansione vede la
  presenza di un riferimento, non la sua logica.
- `FVG_CONT`, `ORDER_BLOCK`, `DISP_REBAL`, `LIQ_VOID` contro I-01/I-05/I-06.
- CRT (C-03) contro `THREE_BAR_DELIVERY_BREAK`, `TURTLE_SOUP`, `LIQ_SWEEP`.
- Qualunque cosa richieda esecuzione: **il codice MQL5 non è mai stato
  compilato**, in questa fase come in tutte le precedenti.

## Fonti esterne consultate

Usate solo per **corroborare** il PDF del corpus sugli orari delle killzone,
mai come fonte primaria. Marcate `EXTERNAL_REFERENCE` in questo rapporto.

- [ICT Silver Bullet Trading Strategy: The 1-Hour Killzones Setup](https://forexbee.co/ict-silver-bullet-trading-strategy/)
- [ICT Silver Bullet & Killzones — The Complete 2026 Trading Guide](https://chartwhisperer.ca/blog/ict-silver-bullet-killzones-trading-guide)
- [ICT Kill Zones: Complete Guide to Trading Sessions](https://www.ictkillzone.com/ict-kill-zones)
- [ICT Killzones — All 4 Session Times](https://innercircletrader.net/tutorials/master-ict-kill-zones/)

## Collegamenti

`docs/audits/corpus/NEXUS_CORPUS_CONCEPT_FORMALIZATION.md` ·
`docs/sources/SOURCE_MANIFEST.json` ·
`docs/audits/master/NEXUS_MASTER_GAPS.md`
