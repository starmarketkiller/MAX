# Edge Definition, Conditional Edge, Interaction Research, Survival, High-Probability Setup — metodologia v1

## 8. Edge Definition (operativa)

Edge ≠ risultato positivo. Edge = miglioramento condizionale rispetto a un baseline appropriato e comparabile.

```
ΔP = P(Target | Setup, State) − P(Target | Baseline, State comparabile)
ΔE = E[R | Setup, State] − E[R | Baseline, State comparabile]
```

Requisiti per dichiarare edge:
1. Il baseline deve condividere lo stesso State (o uno State comparabile dichiarato ex-ante) — non un baseline generico "buy&hold" o "random entry senza condizionamento sul contesto", salvo che sia esplicitamente quello il confronto voluto.
2. ΔP e ΔE vanno riportati ENTRAMBI con la loro incertezza (schema probability), non solo il segno.
3. Un Setup con risultato assoluto positivo ma ΔP≤0 e ΔE≤0 NON ha edge dimostrato — il risultato positivo è spiegabile dal comportamento generico del mercato in quello State, non dal Setup.
4. Baseline candidato di default per NEXUS: "stesso Context (State comparabile), stessa finestra temporale, entrata random/uniforme nel tempo entro il Context, stesso Stop/Target usati dal Setup" — questo isola il contributo dell'Event/Trigger dal contributo del solo Context.

## 9. Conditional Edge — piano di modellazione

Obiettivo: stimare P(Outcome | Setup, Market State) e E[R | Setup, Market State] con modelli INTERPRETABILI, in quest'ordine di complessità crescente:

1. **Logistic regression** — P(target raggiunto) in funzione di un piccolo numero di feature di Market State dichiarate ex-ante (no feature selection post-hoc su centinaia di variabili — quello è data-mining). Coefficienti devono essere leggibili e economicamente plausibili.
2. **Shallow decision tree** (profondità 2-3) — utile per scoprire interazioni non lineari in modo ancora ispezionabile a occhio.
3. **Modelli Bayesiani/gerarchici** — per stimare probabilità per sotto-gruppo (es. per regime, per direzione) con shrinkage verso la media generale quando il sotto-campione è piccolo — evita di sovra-interpretare un sotto-gruppo con n=8.
4. **GAM (eventuale)** — solo se un effetto è chiaramente non lineare ma ancora monotono/interpretabile in un grafico.

Esplicitamente VIETATO in questa fase: reti neurali o modelli black-box. Il criterio di accettazione di un modello non è l'accuratezza massima, è l'interpretabilità + plausibilità economica dei coefficienti/split trovati.

Split dei dati: la stima "di validazione" deve usare un campione disgiunto da quello di "scoperta" (stesso principio già imposto nello schema probability, campo `discovery_sample_disjoint_from_validation_sample`).

## 10. Interaction Research — regole

L'edge può risiedere nell'interazione fra due componenti (A da solo debole, B da solo debole, A+B forte), ma la ricerca di interazioni è vincolata:

- Le interazioni da testare devono essere PREDEFINITE prima di guardare i risultati, con una motivazione economica scritta (es. "Sweep da solo può essere rumore in un mercato senza direzione; Sweep dentro un trend attivo elimina i falsi sweep di un range laterale" — motivazione plausibile, non "abbiamo provato e ha funzionato").
- È VIETATA la ricerca combinatoria esaustiva (provare tutte le coppie/triple di feature/eventi e tenere quelle che risultano significative) — è overfitting mascherato da "ricerca sistematica".
- Ogni interazione approvata va validata separatamente con il proprio schema probability/outcome, non riciclando il campione usato per formulare l'ipotesi.
- Lista iniziale di interazioni economicamente plausibili da testare per prime (non esaustiva, punto di partenza): `TREND_STATE × SWEEP`, `VOLATILITY_EXPANSION × SESSION_STATE`, `COMPRESSION × BREAKOUT_DIRECTION`, `DISPLACEMENT × TREND_PERSISTENCE`.

## 11. Survival / Edge Decay

Per ogni Setup validato, oltre alla Outcome Surface statica, studiare l'andamento nel tempo:

- **Probability of target vs bars elapsed**: P(target raggiunto | non ancora raggiunto ne stoppato dopo k barre) — una curva, non un singolo numero.
- **Hazard of invalidation**: tasso istantaneo di invalidazione condizionato alla sopravvivenza fino a quella barra.
- **Expectancy decay**: E[R rimanente | posizione ancora aperta dopo k barre] — se decresce marcatamente, è evidenza empirica (non assunta) di un time-stop naturale.
- **Probability that an event becomes stale**: quanto un Setup/segnale perde di significato se non agito entro N barre dalla sua formazione (rilevante per Setup con trigger ritardato, es. retest).

Un TIME_STOP va introdotto SOLO se emerge da questa analisi (hazard/expectancy decay osservati), mai aggiunto a priori "perché sembra prudente" — coerente con l'istruzione originale di non introdurlo artificialmente.

## 15. High-Probability Setup — formalizzazione

`HIGH_PROBABILITY_SETUP` richiede TUTTI i seguenti requisiti, nessuno da solo è sufficiente:

1. **Ex-ante definition**: Context/Event/Preconditions congelati PRIMA di osservare l'outcome (stesso principio di FROZEN_SIGNAL_SPEC_V1).
2. **Causal observation**: nessuna feature usata nella definizione include informazione futura rispetto all'observation point.
3. **Sufficient sample**: n minimo dichiarato ex-ante per la soglia R di interesse (es. n≥30 per una stima grezza, n≥100 per una stima da usare in produzione — valori indicativi, da tarare per asset/TF; MAI dichiarare "alta probabilità" con n<15 salvo dichiararlo esplicitamente come segnale preliminare/low-confidence).
4. **Meaningful edge vs baseline**: ΔP e ΔE positivi e non spiegabili dal solo Context (sezione 8).
5. **Independent validation**: replicata su un campione disgiunto da quello di scoperta (temporale out-of-sample, o simbolo/periodo diverso se disponibile).
6. **Uncertainty quantified**: intervallo di confidenza/credibile riportato sempre, mai solo la media.
7. **Stability assessment**: l'edge non sparisce/inverte in sottoperiodi ragionevoli (es. per anno, per regime) — un edge presente solo in un sottoperiodo va segnalato come regime-dipendente, non "alta probabilità" incondizionata.
8. **No pathological outlier dependence**: rimuovendo il singolo trade migliore (o i 2 migliori), edge e significatività non devono collassare — se collassano, il risultato dipende da un outlier, non da un pattern robusto.

Il solo win rate NON è mai sufficiente da solo per nessuno di questi requisiti.
