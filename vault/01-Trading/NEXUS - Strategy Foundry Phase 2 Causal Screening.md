# NEXUS — Strategy Foundry Phase 2: Causal Edge Screening

Base: commit `23db29c` (Phase 1, approvato). Nessun EA completo scritto, nessuna ottimizzazione, nessuna grid search, nessuna combinazione di strategie. Dati: XAUUSD, motore Python esistente (`server/backtest.py`), H4 per le ipotesi 1/2/4/F/G2, M15 (cache locale Dukascopy) per l'ipotesi 3/G1/G3. Finestra dati disponibile: 2019-02 → 2026-08.

**Metodologia comune** (dichiarata prima di ogni risultato): per ogni evento, R = |entry_price − invalidation_price| definito UNA VOLTA al momento dell'evento; cammino in avanti fino a `MAX_HOLD_BARS` (40 barre H4 ≈ 6.7 giorni; per l'ipotesi 3/G1/G3 orizzonti in barre M15 dichiarati per esperimento) senza alcuna gestione dinamica (nessun trailing/BE); primo tra +1R e −1R determina `first_outcome` (PLUS_1R_FIRST/MINUS_1R_FIRST/AMBIGUOUS_SAME_BAR/CENSORED); expectancy in R = (vinte−perse)/n (ambigue/censurate contate ne' vinte ne' perse, conservativo). Split discovery/validation: **70/30 cronologico**, deciso prima di guardare i risultati, nessun cambio di definizione dopo.

---

## 1. Failed Breakout Fade

Soglie dichiarate ex-ante: N=20 (range lookback, stessa convenzione BREAKOUT_ACC), K≤3 barre per la conferma di fallimento, TF=H4.

| | n | Win rate | Expectancy R | Mean MFE_R | Mean MAE_R |
|---|---|---|---|---|---|
| Discovery | 194 | 57.3% | **+0.134** | 1.30 | 1.10 |
| Validation | 84 | 38.8% | **−0.214** | 0.91 | 1.20 |
| Baseline (breakout non fallito, continuazione) Discovery | 644 | 56.1% | +0.059 | 0.61 | 0.54 |
| Baseline Validation | 276 | 62.2% | +0.120 | 0.66 | 0.55 |

**L'effetto si inverte da discovery a validation** (+0.134R → −0.214R). Il baseline di continuazione (breakout che NON falliscono) è invece consistente e positivo in entrambi i segmenti, e nel validation supera nettamente la versione "fade". Nessun supporto per l'ipotesi.

**Verdict: `NO_EDGE`**

---

## 2. Volatility Compression Percentile Breakout

Soglie dichiarate ex-ante: finestra percentile=100 barre, soglia=20°, persistenza M=5 barre, espansione=TR>1.5×ATR, TF=H4.

| | n | Win rate | Expectancy R | Mean MFE_R | Mean MAE_R |
|---|---|---|---|---|---|
| Discovery | 137 | 44.9% | **−0.095** | 0.79 | 0.89 |
| Validation | 59 | 48.1% | **−0.034** | 0.79 | 0.75 |
| Baseline (espansione SENZA compressione) Discovery | 311 | 51.7% | +0.029 | 0.79 | 0.76 |
| Baseline Validation | 134 | 58.1% | +0.142 | 0.80 | 0.69 |

Direzione **consistente ma negativa** in entrambi i segmenti — la compressione precedente non solo non aggiunge edge, ma il baseline SENZA compressione fa costantemente meglio. Risultato onesto: la precondizione di compressione sembra **controproducente**, non neutra.

**Verdict: `NO_EDGE`**

---

## 3. Session Compression → London Open Expansion

Soglie dichiarate ex-ante: finestra percentile storico=60 sessioni asiatiche, soglia=25°, finestra di rottura Londra 07:00-09:00 UTC, corpo minimo=50% del range, orizzonte 4 giorni di calendario in barre M15.

| | n | Win rate | Expectancy R | Mean MFE_R | Mean MAE_R |
|---|---|---|---|---|---|
| Discovery | 150 | 45.0% | **−0.100** | 0.84 | 0.99 |
| Validation | 65 | 69.2% | **+0.385** | 0.98 | 0.69 |
| Baseline (rottura Londra senza compressione asiatica) Discovery | 215 | 54.5% | +0.088 | 0.81 | 0.78 |
| Baseline Validation | 93 | 57.8% | +0.151 | 0.82 | 0.71 |

**L'effetto si inverte** (−0.100R → +0.385R). Il baseline è invece consistente in entrambi i segmenti. Il salto in validation (n=65) è vistoso ma non accompagnato da coerenza nel discovery — esattamente il pattern che il gate "coerenza discovery→validation" è disegnato per intercettare.

**Verdict: `NO_EDGE`** (nonostante il validation isolato sembri forte, l'incoerenza con discovery e il confronto sfavorevole col baseline nel discovery escludono la promozione)

---

## 4. Displacement Continuation via Imbalance Stack

Soglie dichiarate ex-ante: gap 3-barre stile `sig_fvg_cont_ext`, stack≥2 gap consecutivi stessa direzione senza gap opposto nel mezzo, conferma alla barra successiva all'ultimo gap.

| | n | Win rate | Expectancy R | Mean MFE_R | Mean MAE_R |
|---|---|---|---|---|---|
| Discovery | 47 | 28.2% | **−0.362** | 0.47 | 1.05 |
| Validation | 21 | 23.1% | **−0.333** | 0.40 | 0.86 |
| Baseline (gap singolo isolato) Discovery | 330 | 52.1% | +0.039 | 1.02 | 0.86 |
| Baseline Validation | 142 | 53.7% | +0.070 | 0.83 | 0.81 |

**Trovata una direzione CONSISTENTE ma OPPOSTA all'ipotesi**: lo stack di gap nella stessa direzione predice sistematicamente il FALLIMENTO della continuazione (expectancy fortemente negativa, stabile discovery→validation), mentre il gap singolo isolato (baseline) è mite ma positivo e consistente. Campione piccolo (47+21=68).

**Nota metodologica onesta**: questo è un risultato non pianificato (l'ipotesi originale prevedeva continuazione, non fade) — invertire il segno ora e dichiararlo "confermato" sarebbe circolare, dato che userebbe lo stesso split discovery/validation già osservato per formulare la nuova ipotesi. Non promosso; segnalato come pista per un **nuovo** esperimento con un proprio split discovery/validation fresco.

**Verdict: `NO_EDGE`** (per l'ipotesi originale di continuazione) — **con nota di ricerca per un futuro esperimento sul fade dello stack**, non promosso ora.

---

## F. Regime-Conditional Momentum Persistence (diagnostico)

Domanda unica: *il regime TRENDING (ADX≥20, STRONG_TREND o WEAK_TREND da `_regime_series` esistente) aumenta materialmente probabilità/expectancy di continuazione rispetto allo stesso segnale ROC fuori da quel regime?* Soglie: ROC(10)>1%, stop 1×ATR uguale per entrambi i bracci.

| | n | Expectancy R |
|---|---|---|
| TRENDING — Discovery | 2132 | +0.008 |
| TRENDING — Validation | 915 | +0.058 |
| NON-TRENDING — Discovery | 667 | −0.040 |
| NON-TRENDING — Validation | 286 | **+0.073** |

Il regime TRENDING mostra un'expectancy quasi nulla in entrambi i segmenti (+0.008/+0.058) — non materialmente diversa, e nel validation il gruppo NON-TRENDING la supera (+0.073 contro +0.058). Il gruppo non-trending non è nemmeno consistente in segno tra i due segmenti.

**Risposta alla domanda: NO.** Il regime TRENDING non aumenta materialmente l'expectancy del segnale momentum rispetto al fuori-regime.

**Verdict: ipotesi chiusa**, come da istruzione esplicita ("se no, chiudi l'ipotesi"). Non trattata come strategia, come richiesto.

---

## G. Open-Source Track — segnale minimo, separato da risk/execution

### G1. Asian Range Breakout EA — fade minimo

Soglie dell'autore non ritarate: range asiatico 10-100 pip, fade su richiusura dentro il range dopo rottura.

| | n | Win rate | Expectancy R |
|---|---|---|
| Discovery | 445 | 50.3% | +0.007 |
| Validation | 191 | 51.6% | +0.031 |

Direzione **consistente** ma economicamente **trascurabile** (~0.01-0.03R, ordine di grandezza sotto qualunque costo di trading reale — spread/slippage lo cancellerebbero).

**Verdict: `NO_EDGE`** (segno coerente ma non economicamente significativo)

### G2. Volatility_Breakout — segnale dual-mode minimo

Soglie: range N=20 barre (stessa convenzione ipotesi 1), dispatch: TR>1.0×ATR alla barra di rottura → braccio "confermato" (continuazione); altrimenti → braccio "fade".

| | n | Expectancy R | Mean MFE_R | Mean MAE_R |
|---|---|---|---|---|
| Confermato — Discovery | 648 | **+0.037** | 0.62 | 0.56 |
| Confermato — Validation | 279 | **+0.133** | 0.65 | 0.53 |
| Fade — Discovery | 600 | −0.007 | 5.58 | **22.98** |
| Fade — Validation | 258 | −0.147 | 4.20 | 3.48 |

**Braccio confermato**: direzione consistente e **in crescita** discovery→validation (+0.037→+0.133R), campione ampio (927 totali), MFE/MAE in range normale — nessun segnale di dipendenza da outlier.

**Failure mode scoperto (braccio fade)**: MAE_R medio di 22.98 nel discovery è un artefatto — verificato che alcuni eventi hanno R quasi-zero (min osservato 0.0015) perché l'invalidation del braccio fade è definita sul bordo stesso del range appena rotto, che a volte coincide quasi esattamente col prezzo di entrata quando la rottura è marginale. Non è leakage (nessun dato futuro), è una debolezza di specifica che gonfia artificialmente le statistiche di escursione per un piccolo numero di eventi degeneri — dichiarato esplicitamente, non nascosto. Il verdetto negativo del braccio fade resta ma con confidenza ridotta a causa di questo artefatto.

**Verdict braccio confermato: `PROMOTE_TO_IMPLEMENTATION`**
**Verdict braccio fade: `NO_EDGE`** (con failure mode dichiarato)

### G3. Weekly Day Reversal EA — segnale minimo (lunedì fa fade di venerdì)

Scelta dichiarata ex-ante (non scelta dopo aver visto i risultati, e non un grid-search su tutti i giorni): lunedì, braccio reversal (non continuazione) della direzione di venerdì, coerente col folklore di mercato citato in Phase 1.

| | n | Win rate | Expectancy R |
|---|---|---|
| Discovery | 35 | 61.8% | +0.229 |
| Validation | 15 | 41.7% | **−0.133** |

Direzione si inverte, e il campione di validation (n=15) è troppo piccolo per qualunque conclusione — esattamente il caso per cui esiste il verdetto dedicato.

**Verdict: `INSUFFICIENT_SAMPLE`**

### COT1 e BAKOME/Sophisticated-Bot

Come da istruzione: COT1 resta sospeso (nessuna pipeline dati COT pulita disponibile), BAKOME/Sophisticated-Bot resta solo nella track risk/execution della Fase 1, non valutato qui come strategia.

---

## Riepilogo verdetti

| Ipotesi | n (disc+val) | Direzione coerente? | Verdict |
|---|---|---|---|
| 1. Failed Breakout Fade | 278 | No (si inverte) | `NO_EDGE` |
| 2. Volatility Compression Breakout | 196 | Sì, ma negativa | `NO_EDGE` |
| 3. Session Compression → London Expansion | 215 | No (si inverte) | `NO_EDGE` |
| 4. Displacement Imbalance Stack | 68 | Sì, ma segno opposto all'ipotesi | `NO_EDGE` (nota di ricerca per fade) |
| F. Regime-Conditional Momentum (diagnostico) | 3047+953 | No, e differenza non materiale | Chiusa (non una strategia) |
| G1. Asian Range Fade (open-source) | 636 | Sì, ma trascurabile | `NO_EDGE` |
| **G2. Volatility_Breakout — confermato** | 927 | **Sì, in crescita** | **`PROMOTE_TO_IMPLEMENTATION`** |
| G2. Volatility_Breakout — fade | 858 | Sì, ma con failure mode nelle statistiche | `NO_EDGE` |
| G3. Weekly Day Reversal | 50 | No, e campione minimo insufficiente | `INSUFFICIENT_SAMPLE` |

**Promosse a implementazione: 1 (Volatility_Breakout, braccio confermato)** — entro il tetto di 3, non forzato al massimo. Nessuna delle 4 ipotesi native supera il gate minimo così come formalizzate in Phase 1; l'unico segnale promuovibile viene dalla track open-source (una regola di conferma ATR su un breakout, concettualmente vicina ma non identica a BREAKOUT_ACC).

---

## Failure modes riscontrati (dichiarati esplicitamente)

1. **Inversione di segno discovery→validation** in 3 delle 4 ipotesi native (1, 3) e in 2 (2 è negativa in entrambi, quindi coerente ma sbagliata) — il pattern dominante di questa fase è che gli effetti "sembrano esserci" nel discovery ma non sopravvivono al validation, esattamente il tipo di falso positivo che lo split è disegnato per catturare. Nessuna ipotesi nativa così come specificata in Phase 1 supera questo filtro.
2. **R degenere nel braccio fade di G2**: invalidation definita sul bordo del range rotto produce R quasi-zero per rotture marginali, gonfiando MAE_R medio. Non leakage, ma un limite di specifica da correggere se questo braccio venisse mai ripreso in futuro.
3. **Displacement stack**: l'unico risultato realmente consistente (oltre a G2-confermato) ha il segno OPPOSTO a quanto ipotizzato in Phase 1 — un buon esempio di perché "prima evento poi strategia" è la sequenza giusta: se si fosse implementato direttamente l'EA sulla base della sola intuizione economica, si sarebbe costruita una strategia con l'edge nella direzione sbagliata.

## Nessun leakage riscontrato

Tutte le detection usano solo barre strettamente precedenti alla barra di valutazione per le soglie/percentili/range; gli outcome camminano solo in avanti da `entry_i+1`; nessuna feature ricalcolata con hindsight.

---

## File prodotti

- `server/research_scripts/phase2_causal_screening.py` — detector delle 4 ipotesi native + baseline + walk-forward R-outcome
- `server/research_scripts/phase2_run.py` — orchestrazione, regime experiment, 3 estrazioni open-source, split discovery/validation
- `results/phase2_causal_screening/phase2_results.json` — risultati completi per ogni ipotesi/baseline/segmento

## Commit

`[da assegnare]`
