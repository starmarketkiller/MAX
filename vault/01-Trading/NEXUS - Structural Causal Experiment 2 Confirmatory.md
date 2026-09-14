# NEXUS Causal Research Thread 2 — Structural Causal Experiment 2: Confirmatory Test

Segue [[NEXUS - Structural Causal Experiment 1]] (commit `853b1a4`, verdict `NO_PROMISING_HYPOTHESIS`, 3 `WEAK_HINT`). Test confermativo, non discovery: nessuna nuova feature, nessuna combinazione, nessuna soglia ricalcolata. Testati **solo** i 3 hint congelati.

## Soglie congelate (da Experiment 1, mai ricalcolate)

| Hint | Soglia congelata |
|---|---|
| `penetration_per_atr` Q4 | `> 0.058713928652578955` — ricomputato deterministicamente dal TRAIN di Experiment 1 (w1+w2+parte w3, n=642), stesso identico valore che produceva il quartile top nel report originale |
| `age_seconds` | `< 3600` (fisso, per istruzione) |
| `source_tf` | `== "PERIOD_D1"` (fisso, per istruzione) |

Nessun trattamento missing/outlier diverso da Experiment 1: righe con `penetration_per_atr` non definibile (ATR≤0) escluse dal solo test di quel hint, non dagli altri due.

## 1. Periodo indipendente

**w0: 2025-09-01 → 2026-01-01** (4 mesi) — interamente precedente a w1 (2026-01-01), zero overlap con w1-w4 (2026-01-01→2026-08-25). Stessa configurazione di raccolta di w1-w4 (GOLD H4, Model=1, Research Mode, selettore SH_BMS_RTO=21, `InpStructuralResearchEventLog=true`).

## 2. Stessa population logic

Riusato **direttamente** `assign_episodes()`/`build_episode_lifecycle_index()` da `build_structural_dataset_v1.py` (stesso detector fix `9b77f83`, stesso episode linkage per `(window_id, event_id)`, stessa policy di esclusione) — nessuna riscrittura della logica di popolazione.

| | n |
|---|---|
| Episodi SH_BMS_RTO totali (w0) | 1157 |
| Esclusi `NO_LIFECYCLE_OBSERVED` | 198 |
| Esclusi (esito da evento redundant-after-close/true-break-after-close) | 18 |
| Orphan (dovrebbero essere 0 per costruzione) | **0** |
| **Population valida** | **941** |

## 3. Base rate (w0)

**94/941 = 10.0%** CI95=[8.2%, 12.1%] — coerente con Experiment 1 (8.2% su w1-w4), nessuna deriva macroscopica fra i due periodi.

## 4. Risultati per hint

| Hint | n_group | rate | uplift assoluto | uplift relativo | CI95 | 1ª metà | 2ª metà | BUY | SELL |
|---|---|---|---|---|---|---|---|---|---|
| `penetration_per_atr` Q4 | 221 | 21.3% | **+11.3pp** | +112.9% | [16.4%,27.1%] | n=123, +12.4pp | n=98, +9.1pp | n=111, +12.8pp | n=110, +9.2pp |
| `age_seconds<1h` | 95 | 28.4% | +18.4pp | +184.5% | [20.3%,38.2%] | n=52, +27.6pp | n=43, +6.7pp | n=64, +29.7pp | n=31, **−8.0pp** |
| `source_tf=D1` | 100 | 28.0% | +18.0pp | +180.3% | [20.1%,37.5%] | n=55, +27.2pp | n=45, +6.1pp | n=65, +30.6pp | n=35, **−8.0pp** |

Tutti e tre superano nominalmente la soglia meccanica di 0.10 assoluto e la significatività statistica (p<0.0001 su tutti). **Ma un'ispezione più a fondo, richiesta esplicitamente dal punto 4 (BUY/SELL robustness), rivela un problema sostanziale per due dei tre.**

## 5. Scoperta critica: confondimento fra `age_seconds<1h` e `source_tf=D1`

Verificato esplicitamente (non richiesto come "interazione" — è un controllo di validità sui due gruppi già definiti, non una nuova ipotesi):

- **Overlap fra i due gruppi: 87/95 (91.6%) e 87/100 (87.0%)** — sono in pratica lo stesso insieme di episodi, non due conferme indipendenti.
- **Composizione di `age_seconds<1h`: 100% sweep Asia** (64 Asia-Low, 31 Asia-High, zero Daily/Weekly/Monthly/Equal). Causa meccanica: `created_time` per i livelli Asia è ancorato a `iTime(g_sym, PERIOD_D1, 0)` (mezzanotte di OGGI), mentre per Daily/Weekly/Monthly è ancorato al periodo PRECEDENTE — un'osservazione durante un pass D1 di uno sweep Asia produce quindi quasi sempre `age≈0` per costruzione della formula, non perché il livello sia realmente "più fresco" in un senso causale generale.
- **`source_tf=D1`**: 87/100 sono lo stesso sottoinsieme Asia; i restanti 13 (Weekly/Monthly) mostrano quasi sempre `INVALIDATED_NO_BREAK` (12/13).
- **Asimmetria BUY/SELL, causa radice trovata**: `sweptAsiaHigh` implica sempre `direction=SELL`, `sweptAsiaLow` implica sempre `direction=BUY` (hardcoded nel detector) — un mapping deterministico 1:1, non una correlazione statistica. Nel gruppo `age_seconds<1h`: **Asia-High/SELL = 0/31 TRUE_BREAK_OBSERVED (0.0%)**, **Asia-Low/BUY = 27/64 TRUE_BREAK_OBSERVED (42.2%)**. L'intero uplift riportato per entrambi gli hint è generato **esclusivamente** dal sottoinsieme Asia-Low/BUY — Asia-High/SELL non porta alcun segnale (anzi, un tasso nullo).

**Conclusione**: `age_seconds<1h` e `source_tf=D1`, così come definiti, non misurano "livelli giovani" o "timeframe D1" in senso generale — misurano quasi esclusivamente "sweep Asia-Low" per un artefatto della formula di `created_time`, e l'intero effetto è concentrato nel solo lato BUY. La soglia numerica meccanica di inversione distruttiva (`SELL uplift < −0.10`) non è scattata per un margine stretto (−0.080), ma la sostanza — 0.0% contro 42.2% sullo stesso hint — è esattamente il tipo di inversione distruttiva che il punto 5 del task chiede di verificare. **Non viene proposta qui una nuova ipotesi "Asia-Low predice" — sarebbe nuova discovery, esplicitamente vietata in questo esperimento.** I due hint restano semplicemente non confermabili come formulati.

`penetration_per_atr` Q4 non condivide questo problema: distribuito su **9 levelTag diversi** (Asia-Low, Asia-High, Equal-Low, Daily-High, Daily-Low, Equal-High, Weekly-High, Monthly-High, Weekly-Low), **entrambe le direzioni con campione bilanciato** (BUY n=111, SELL n=110) **ed entrambe con uplift positivo** (+12.8pp, +9.2pp) — nessuna inversione, nessun singolo tag a dominare il risultato.

## 6. Classificazione finale

| Hint | Gate meccanico | Revisione sostanziale | Classificazione finale |
|---|---|---|---|
| `penetration_per_atr` Q4 | CONFIRMED | Nessun problema trovato: multi-tag, BUY/SELL bilanciato ed entrambi positivi, coerente in entrambe le metà temporali | **CONFIRMED** |
| `age_seconds<1h` | CONFIRMED | **Declassato**: 100% artefatto Asia (formula `created_time`), effetto interamente concentrato in Asia-Low/BUY, SELL a tasso nullo | **INCONCLUSIVE_FINAL** |
| `source_tf=D1` | CONFIRMED | **Declassato**: 87-92% overlap con `age_seconds<1h`, stessa causa, stesso pattern SELL nullo | **INCONCLUSIVE_FINAL** |

## 7. Verdict finale

### **STRUCTURAL_HYPOTHESIS_CONFIRMED**

Un solo hint (`penetration_per_atr` Q4) supera il gate sia meccanicamente sia dopo revisione sostanziale — sufficiente per il verdict complessivo (soglia: almeno uno su tre). Gli altri due, pur superando nominalmente le soglie numeriche dichiarate, sono stati declassati a `INCONCLUSIVE_FINAL` per un confondimento reale scoperto dal controllo di robustezza BUY/SELL richiesto dal task stesso — non un artefatto ignorato, ma la ragione stessa per cui quel controllo esiste.

**Nessuna strategia implementata.** `penetration_per_atr` alto al momento dello sweep resta un'ipotesi meritevole di un'eventuale, separata validazione futura (es. su un quarto periodo indipendente) prima di qualunque implementazione — non eseguita qui.
