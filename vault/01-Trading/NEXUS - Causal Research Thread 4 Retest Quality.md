# NEXUS Causal Research Thread 4 — Retest Quality: HOLD vs FAIL

Segue [[NEXUS - Causal Research Thread 3 Final v3]] (commit `aa8c637`, `NO_PROMISING_HYPOTHESIS` su TRUE_BREAK quality). Non riaperti: TRUE_BREAK quality feature search, penetration/ATR sweep hypothesis, age<1h, source_tf=D1.

Domanda: quando un RETEST è realmente osservato (episodio SH_BMS_RTO con SWEEP→TRUE_BREAK→RETEST causalmente linkato via `episode_sweep_link` v3), esistono feature note entro l'istante del RETEST che predicono HOLD vs FAIL e/o un esito economico favorevole? Nessuna implementazione di strategia.

## 1. Population — required checks

| Check | Esito |
|---|---|
| Orphan (qualunque tipo, TRUE_BREAK/RETEST/INVALIDATE) | **0** |
| Unexplained orphan | **0** |
| Lifecycle post-close | Escluso per costruzione: solo episodi con `closed_by=="RETEST"` (mai un retest tardivo dopo un invalidate precedente) |
| Future leakage | Nessuno: `scan_forward_labels` cammina solo su barre M1 con `time > retest.timestamp`, mai oltre `window_end` |
| **RETEST totali (episodi chiusi DA un retest)** | **88** |

**Nota di trasparenza (non un difetto del linkage v3)**: 60 episodi chiusi da un RETEST valido sono stati **esclusi** dalla population di Thread 4 perché il loro TRUE_BREAK non è mai stato loggato come riga propria — non per lo stesso motivo degli orphan di Phase C.1 (collisione sulla canonicalizzazione SWEEP, già risolta), ma per un meccanismo **diverso**: `_NXS_Struct_IsDuplicate(level_id, event_type, timestamp)` sopprime silenziosamente un evento lifecycle (TRUE_BREAK/RETEST/INVALIDATE) se un evento dello stesso tipo sullo stesso livello e bar è già stato loggato da un episodio precedente nello stesso tick (verificato su un caso concreto: episodio seq=740 logga TRUE_BREAK+RETEST sullo stesso bar; l'episodio seq=741 immediatamente successivo raggiunge WAITING_RETURN ma il suo TRUE_BREAK collide sullo stesso `(level_id, "TRUE_BREAK", timestamp)` già occupato da seq=740 e viene soppresso — il suo RETEST, su un bar diverso, non collide e viene loggato regolarmente). Questi 60 episodi sono **correttamente esclusi** (mancano i campi TRUE_BREAK necessari alle feature congelate), non silenziosamente mal-attribuiti. Estendere la mappa causale `episode_sweep_link` anche al lato lifecycle (non solo SWEEP) per recuperare questi casi è un possibile lavoro futuro, fuori scope qui.

## 2. Observation point

`AT_RETEST`. Tutte le feature sono lette dal rigo RETEST stesso (`retest_source_tf`, `retest_regime_at_event`, `retest_structure_trend_at_event`, `retest_atr_at_event`, `retest_dist_per_atr`) o dai righi TRUE_BREAK/SWEEP che lo precedono causalmente nello stesso episodio — mai dati successivi al retest.

## 3. Sample gate

| | n |
|---|---|
| RETEST totali | 88 |
| HOLD | 30 |
| FAIL | 34 |
| AMBIGUOUS | 24 |
| CENSORED | 0 |
| **RESOLVED (HOLD+FAIL)** | **64** |
| DISCOVERY resolved | 32 |
| VALIDATION resolved | 32 |

64 ≥ 50 → non si applica `HOLD_INSUFFICIENT_RETEST_SAMPLE`. Entrambi gli split hanno 32 ≥ 20 risolti → non si applica `HOLD_RETEST_VALIDATION_SAMPLE_TOO_SMALL`. Promozione di ipotesi **consentita**.

## 4. Target primario — definizione esatta (invariata)

`RETEST_HOLD_OR_FAIL`: **HOLD = PLUS_1R_FIRST**, **FAIL = MINUS_1R_FIRST**, calcolati da `scan_forward_labels(m1, window_end, retest.timestamp, retest.price_at_event, dsign(direction), atr=None)` — R=25 pip fisso, stesso orizzonte (5 giorni) e stessa price reference già usati in tutto il progetto. **Nessuna ridefinizione.** `AMBIGUOUS`/`N/A`/`CENSORED` esclusi dal target primario.

## 5. Target economico secondario

`PLUS_1R_BEFORE_MINUS_1R`, R=25 pip, stesso horizon, stessa price reference. **Verificato riga per riga su tutte le 88 osservazioni**: in questo dataset `HOLD` coincide esattamente con `PLUS_1R_FIRST` e `FAIL` con `MINUS_1R_FIRST` — sono la **stessa identica misura**, non due calcoli indipendenti che potrebbero divergere. Conseguenza diretta per il §11 (coerenza strutturale/economico): in questo dataset è **strutturalmente impossibile** che una feature predica HOLD senza predire anche l'esito economico, perché non sono due variabili distinte. Nessuna feature qui richiede quindi la classificazione `STRUCTURAL_ONLY_HINT`.

## Base rate

| | k/n | rate |
|---|---|---|
| Totale | 30/64 | 46.9% CI95=[35.2%, 58.9%] |
| DISCOVERY | 15/32 | 46.9% |
| VALIDATION | 15/32 | 46.9% |

Ambiguity rate: 24/88 = **27.3%** (inferiore al 38-41% osservato per TRUE_BREAK in Thread 3 — coerente: un retest confermato è per natura un evento più "pulito" di un break grezzo).

## 6-7. Feature set congelato, split invariato

15 feature (vedi task): `direction`, `side`, `retest_source_tf`, `retest_regime_at_event`, `retest_structure_trend_at_event`, `retest_trend_aligned`, `retest_dist_per_atr` (quartili), `tb_source_tf`, `tb_regime_at_event`, `tb_structure_trend_at_event`, `tb_penetration_per_atr` (quartili), `sweep_source_tf`, `sweep_regime_at_event`, `sweep_structure_trend_at_event`, `sweep_penetration_per_atr` (quartili), `regime_changed_sweep_to_break`, `regime_changed_break_to_retest`. Nessuna feature aggiunta dopo aver visto i risultati. Split: DISCOVERY=wA+w0 (n=32), VALIDATION=w1-w4 (n=32), nessun random split.

## 8-10. Discovery, robustness, classificazione

**57 bucket/ipotesi testate.** Classificazione: **NO_SIGNAL=50, WEAK_HINT=7, PROMISING_HYPOTHESIS=0**.

### Top 3 pattern (per |uplift discovery|) — robustness completa

| Feature=Bucket | Class. | DISCOVERY | VALIDATION | 1ª metà | 2ª metà | BUY | SELL | top_mese | top_tag | Dominato |
|---|---|---|---|---|---|---|---|---|---|---|
| `tb_structure_trend_at_event=UP` | WEAK_HINT | 0.400 (n=25) | 0.435 (n=23) | 0.400 (n=25) | 0.435 (n=23) | 0.382 (n=34) | 0.500 (n=14) | 21% | 69% | **SÌ** |
| `side=Asia-Low` | WEAK_HINT | 0.417 (n=24) | 0.438 (n=16) | 0.417 (n=24) | 0.438 (n=16) | 0.425 (n=40) | n/a (n=0) | 25% | 100% | **SÌ** (0 SELL) |
| `retest_structure_trend_at_event=UP` | WEAK_HINT | 0.423 (n=26) | 0.438 (n=16) | 0.423 (n=26) | 0.438 (n=16) | 0.419 (n=31) | 0.455 (n=11) | 26% | 71% | **SÌ** |

Tutti e tre erano già `WEAK_HINT` (effetto sotto soglia di materialità 0.10 in almeno un set) dal gate automatico — nessuno era `PROMISING_HYPOTHESIS`. Il controllo di robustezza aggiuntivo conferma che, comunque, tutti e tre sarebbero respinti per dominanza da un solo fattore (levelTag/direzione unica >60-100%, o uno dei due lati con n<10). **Nessuna promozione.**

## Logistic regression

Feature: `retest_dist_per_atr`, `tb_penetration_per_atr`, `retest_trend_aligned`, `regime_changed_break_to_retest`.
Pesi: `[-0.611, 0.143, -0.104, -0.042]`, bias=-0.148.
Accuracy DISCOVERY: 0.500 — VALIDATION: **0.406** — baseline maggioranza VALIDATION: 0.531.

Il modello **non batte la baseline maggioranza** su VALIDATION (peggio, addirittura).

## Shallow tree (depth≤2)

```
IF retest_dist_per_atr <= 6.066 (n=32, rate=0.469):
  IF regime_changed_break_to_retest <= 0.500 (n=22, rate=0.545):
    LEAF n=10 rate=0.400
  ELSE:
    LEAF n=12 rate=0.667
ELSE:
  LEAF n=10 rate=0.300
```

Verifica su VALIDATION: foglia train=0.300 → VALIDATION n=5 rate=0.400; foglia train=0.400 → VALIDATION n=13 rate=0.538 (invertita!); foglia train=0.667 → VALIDATION n=14 rate=0.429 (dimezzato l'uplift). Nessuna foglia mantiene un edge stabile fuori campione — una addirittura si inverte.

## Verdict

### **NO_PROMISING_HYPOTHESIS**

Con un campione adeguato (64 risolti, entrambi gli split ≥20) e la stessa metodologia pre-registrata usata in Thread 3, nessuna delle 15 feature congelate produce un pattern che superi il gate di robustezza. Il target economico secondario coincide per costruzione con il target primario in questo dataset (§5) — nessuna divergenza strutturale/economica da riportare. Nessuna feature implementata, nessun cutoff cercato, nessuna modifica alla trading logic.

**Commit**: da eseguire subito dopo questo report.
