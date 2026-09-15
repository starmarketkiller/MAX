# NEXUS Causal Research Thread 3 — FINAL RE-RUN on v3 Causal Population

Segue [[NEXUS - Phase C1 Orphan TRUE_BREAK Audit]] (commit `f6315e3`): il verdict precedente di Thread 3 (`NO_PROMISING_HYPOTHESIS`, ottenuto durante la validazione di Phase C su population v2, 159 risolti) era dichiarato **provvisorio** perché la population cambiava materialmente dopo la chiusura dei 288 orphan TRUE_BREAK. Questo report rilancia la **stessa identica metodologia pre-registrata** (nessuna soglia, feature, o target cambiato) sulla population v3, costruita esclusivamente tramite `episode_sweep_link` (fonte causale).

Nessun risultato precedente è stato riusato come decisione. Nessuna feature nuova aggiunta. Nessuna modifica alla trading logic.

## 0. Cleanup documentale

Corretti i commenti stale in `NXS_StructuralResearchLog.mqh` che riportavano ancora la stima euristica del Round 1 dell'audit (247/288 = 85.8% collision, 41/288 = 14.2% malformed). Sostituiti con la verità causale finale (288/288 = 100% `CANONICAL_DEDUP_EPISODE_COLLISION`, 0 `MALFORMED_SKIPPED` osservato in pratica), con nota esplicita che la stima euristica preliminare è stata superata. Solo commenti — nessuna modifica funzionale, ricompilato per conferma (0 errori).

## 1. Population — required checks

| Check | Esito | Atteso |
|---|---|---|
| Orphan TRUE_BREAK | **0** | 0 ✓ |
| Unexplained orphan | **0** | 0 ✓ |
| Malformed rows | **0** | 0 ✓ |
| Esclusioni post-close/redundant | `{}` | `{}` ✓ |
| Linkage episodio→sweep canonico | valido per tutti i 558 (via `episodes[ep_id]` autoritativo, mai il fragile `sweeps_by_episode` a campo singolo) | — |
| Future leakage | Nessuno per costruzione: `scan_forward_labels` cammina solo su barre M1 con `time > obs_time`, mai oltre `window_end` | — |
| **TRUE_BREAK validi** | **558** | ~558 ✓ |
| **Risolti totali** | **344** | ~344 ✓ |

I conteggi corrispondono esattamente all'atteso — nessuno STOP necessario.

## 2. Observation point — invariato

`AT_TRUE_BREAK`, target primario `PLUS_1R_FIRST` vs `MINUS_1R_FIRST`, R=25 pip, stesso orizzonte (5 giorni), stessa price reference (`price_at_event` del TRUE_BREAK). `AMBIGUOUS_SAME_BAR` esclusi dal target primario, come da metodologia originale. R non modificato.

## 3. Split temporale — invariato

| | n |
|---|---|
| **DISCOVERY** (wA+w0, 2025-05-01→2026-01-01) | **166** |
| **VALIDATION** (w1-w4, 2026-01-01→2026-08-25) | **178** |

Nessun random split, nessun reshuffling.

## 4. Feature set — congelato, invariato

Le 15 feature del Thread 3 precedente, nessuna aggiunta: `direction`, `side`, `tb_source_tf`, `tb_regime_at_event`, `tb_structure_trend_at_event`, `tb_atr_at_event`, `tb_penetration_pips`, `tb_penetration_per_atr`, `sweep_penetration_per_atr`, `sweep_source_tf`, `sweep_regime_at_event`, `sweep_structure_trend_at_event`, `regime_changed_sweep_to_break`, `direction_trend_aligned_at_break`, `regime_category_same_sweep_to_break`. `observed_by`/`observation_count`/RETEST-INVALIDATE futuri restano esclusi.

## 5-6. Discovery e multiple comparisons

**Base rate**: 167/344 = **48.5%** CI95=[43.3%, 53.8%] — DISCOVERY 52.4% (87/166), VALIDATION 44.9% (80/178).

**54 bucket/ipotesi testate** (stesso numero e stessa logica del Thread 3 precedente — 14 feature × bucket/quartili). Soglie invariate: `MIN_EFFECT=0.10`, `MIN_N_TRAIN=30`, `MIN_N_OOS=20`, `MIN_N_TAG_DOMINANCE=0.60`, `MIN_N_MONTH_DOMINANCE=0.60`.

**Classificazione**: `NO_SIGNAL=34`, `WEAK_HINT=20`, **`PROMISING_HYPOTHESIS=0`**.

## 7. Robustness obbligatoria — top 3 pattern (per |uplift discovery|)

| Feature=Bucket | Class. | DISCOVERY | VALIDATION | 1ª metà | 2ª metà | BUY | SELL | top_mese | top_tag | Dominato da un solo fattore |
|---|---|---|---|---|---|---|---|---|---|---|
| `direction=SELL` | WEAK_HINT | 0.429 (n=49) | 0.329 (n=76) | 0.420 (n=50) | 0.333 (n=75) | n/a (n=0) | 0.368 (n=125) | 14% | 35% | **SÌ** (per costruzione, n_BUY=0) |
| `sweep_regime_at_event=RANGING` | WEAK_HINT | 0.433 (n=30) | 0.364 (n=33) | 0.433 (n=30) | 0.364 (n=33) | 0.474 (n=38) | 0.280 (n=25) | 21% | 30% | No |
| `sweep_penetration_per_atr_quartile=Q2` | WEAK_HINT | 0.442 (n=43) | 0.346 (n=26) | 0.468 (n=47) | 0.273 (n=22) | 0.458 (n=48) | 0.286 (n=21) | 19% | **61%** | **SÌ** (>60% da un solo levelTag) |

Nessuno dei tre era già stato classificato `PROMISING_HYPOTHESIS` dal gate automatico (tutti `WEAK_HINT`, effetto sotto soglia di materialità in almeno un set). Il controllo di robustezza aggiuntivo conferma che, anche ipotizzando un abbassamento della soglia, 2 su 3 sarebbero comunque respinti per dominanza da un singolo fattore (direzione unica o singolo levelTag >60%). Nessuna promozione.

## 8. Ambiguity analysis

- Ambiguous: 214/558 = **38.4%** (vs 41.1% in Phase C population v2 — sostanzialmente invariato).
- Sensitivity descrittiva (mai usata per promuovere): worst-case (ambiguous=FAIL) = 0.299, best-case (ambiguous=SUCCESS) = 0.683. Range ampio, coerente con R=25 pip stretto rispetto alla volatilità H4 di GOLD — non usato per alcuna decisione.

## 9. Retest

| | n |
|---|---|
| Osservati | 88 |
| Breakdown | HOLD=30, FAIL=34, AMBIGUOUS=24 |
| **Risolti (HOLD/FAIL)** | **64** |
| Status | **RETEST_SAMPLE_ADEQUATE** (≥50) |

Riportato per trasparenza, **non mischiato** con il target primario né usato per alcuna decisione di promozione.

## Logistic regression (minimale, invariata)

Feature: `tb_penetration_per_atr`, `sweep_penetration_per_atr`, `direction_trend_aligned`, `regime_changed`.
Pesi: `[0.103, -0.060, -0.043, 0.030]`, bias=0.097.
Accuracy DISCOVERY: 0.500 — VALIDATION: 0.399 — baseline maggioranza VALIDATION: 0.551.

Il modello **non batte la baseline maggioranza** su VALIDATION — nessun segnale utile da queste 4 feature linearmente combinate.

## Shallow tree (depth≤2, invariato)

```
IF tb_penetration_per_atr <= 0.903 (n=166, rate=0.524):
  IF tb_penetration_per_atr <= 0.710 (n=141, rate=0.496):
    LEAF n=126 rate=0.532
  ELSE:
    LEAF n=15 rate=0.200
ELSE:
  LEAF n=25 rate=0.680
```

Verifica foglie su VALIDATION: foglia train=0.200 → VALIDATION n=10 rate=0.200 (coerente); foglia train=0.532 → VALIDATION n=140 rate=0.457 (attenuata); foglia train=0.680 → VALIDATION n=28 rate=0.500 (attenuata, quasi dimezzato l'uplift). Nessuna foglia mantiene un edge materiale e stabile fuori campione.

## 10. Decision gate

Nessuna feature soddisfa contemporaneamente tutti i criteri richiesti (effetto materiale in DISCOVERY, stessa direzione in VALIDATION, campione sufficiente, robustezza BUY/SELL, robustezza temporale, non dominata da un solo tag/mese, nessun leakage).

## Verdict

### **NO_PROMISING_HYPOTHESIS**

La population più che raddoppiata (159→344 risolti) grazie alla chiusura corretta degli orphan non ha cambiato la conclusione sostanziale: nessuna delle 15 feature congelate, testata con la stessa metodologia e le stesse soglie pre-registrate, produce un pattern che superi il gate di robustezza. Il Thread 3 è chiuso **non per insufficienza di campione** (come nel verdict precedente `HOLD_INSUFFICIENT_TRUE_BREAK_SAMPLE`) ma per **assenza di segnale materiale e robusto** su un campione ora adeguato — una chiusura più forte e definitiva della precedente.

**Nessuna feature implementata. Nessun cutoff cercato.** Nessuna modifica alla trading logic.

**Commit**: da eseguire subito dopo questo report.
