# NEXUS - Phase 7.4A Dependence-Aware Inference Redesign

**Baseline:** `44ff5a2` (Phase 7.4A End-to-End Inference Validation, verdetto BLOCKED accettato). Elimina l'architettura "diagnostica sugli stessi d_i → selezione → test sugli stessi d_i" (dimostrata soggetta a selection bias avverso) e valuta 3 metodi che incorporano la dipendenza **nel test stesso**, senza gating selettivo. **Nessuna discovery eseguita, nessun dato NEXUS letto, nessuna modifica** a detector/P90/252/direction/episode/embargo/matched baseline/control reuse/outcome definitions (verificato).

**Conferma esplicita: NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.**

---

## Verdetto

## **PRIMARY INFERENCE METHOD NOT YET VALIDATED**

Nessuno dei 3 metodi candidati soddisfa **tutti** i 4 criteri della Decision Rule congelata *prima* dell'interpretazione finale. **Nessuna `phase7_4_seq0015_frozen_spec_v5.json` creata** (per esplicita istruzione in caso di non validazione).

## Decision Rule (congelata, sec.9)

1. Type-I@.05 ≤ .075 in tutti gli scenari core (griglia 6φ a n=30)
2. Nessuna esplosione >2× nominale, su tutta la griglia 6φ×4n + 8 scenari distribuzionali + 5 scenari matched-control
3. Nessuna instabilità catastrofica al variare di n=20→100 (φ=0.5)
4. FDR 21-cell (global null) ≤ q + tolleranza MC (3σ)

## Metodi confrontati

| Metodo | Descrizione | Costo/replica |
|---|---|---|
| **A** | null-centered moving block bootstrap: centra `d` sulla propria media osservata (H0 vera per costruzione), ricampiona blocchi | ~13ms |
| **B** | studentized block bootstrap: `T=mean(d)/SE_block(d)`, SE ricalcolato per ogni replica bootstrap | ~40-70ms |
| **C** | HAC/Newey-West: `mean(d)/HAC_SE`, bandwidth=ceil(n^(1/3)) strutturale, kernel Bartlett, p da t(n-1) | ~0.2ms (forma chiusa) |

**Nota sul budget**: uno screening preliminare (6φ, n=30, 800 repliche) ha mostrato B nettamente più calibrato di A e C in ogni scenario — budget di calcolo allocato asimmetricamente (più repliche per B), dichiarato esplicitamente in `dependence_aware_inference_calibration.py`. A e C restano comunque testati sull'intera griglia richiesta.

## Type-I per metodo/φ/n (α=.05, griglia core n=30)

| φ | A | B | C |
|---|---|---|---|
| 0.0 | 0.072 | **0.029** | 0.095 |
| 0.1 | 0.090 | **0.038** | 0.096 |
| 0.2 | 0.100 | **0.043** | 0.108 |
| 0.3 | 0.115 | **0.041** | 0.130 |
| 0.5 | 0.175 | **0.070** | 0.167 |
| 0.7 | 0.295 | **0.112** | 0.239 |

B è sistematicamente il migliore, ma **fallisce comunque** il criterio 1 a φ=0.7 (0.112 > 0.075) e il criterio 2 (esplosione 2.2-2.7× a φ=0.7, **a tutti gli n testati 20-100** — non risolvibile aumentando il campione).

## Stress distribuzionale (8 scenari, n=30, α=.05)

Gaussiana, Student-t3, skew lieve/forte, volatility clustering (GARCH), regime-switching, AR(1) φ=0.4, ARMA(1,1): **B supera tutti** (0.020-0.069, tutti ≤0.075). A e C falliscono già sulla gaussiana pura (A=0.108, C=0.096) — un metodo che non supera nemmeno il caso base non richiede ulteriore discussione.

## Matched-control stress (5 scenari) — la scoperta decisiva

| Scenario | A | B | C |
|---|---|---|---|
| Riuso pool piccolo condiviso | **0.348** | **0.223** | **0.362** |
| Control set sovrapposti | 0.146 | 0.063 | 0.157 |
| Shock di regime condiviso | 0.100 | 0.043 | 0.087 |
| k eterogeneo | 0.083 | 0.025 | 0.089 |
| Controlli occasionalmente mancanti | 0.104 | 0.037 | 0.096 |

**Tutti e 3 i metodi falliscono catastroficamente** sotto riuso di un pool piccolo di controlli condivisi (B: 4.46× il nominale, il migliore dei tre ma comunque inaccettabile). **Root cause**: A/B/C sono costruiti attorno alla dipendenza **seriale/temporale** (blocchi contigui nel tempo, lag HAC) — nessuno modella la correlazione che nasce quando più eventi condividono **lo stesso controllo** nel pool matched, indipendentemente dalla posizione temporale. È una lacuna strutturale **distinta** dal problema di autocorrelazione, non risolta da nessuno dei 3 candidati.

## Power (φ=0.0, n=30, α=.05)

| δ | A | B | C |
|---|---|---|---|
| 0.0 | 0.081 | 0.026 | 0.097 |
| 0.2 | 0.252 | 0.122 | 0.256 |
| 0.4 | 0.616 | 0.350 | 0.637 |
| 0.8 | 0.995 | **0.893** | 0.991 |

B paga un costo di potenza reale per la sua migliore calibrazione (0.893 vs ~0.99 di A/C a δ=0.8) — atteso e accettabile, ma non l'unico ostacolo alla validazione.

## FDR a 21 celle (senza gating — tutte le 21 celle restano nella famiglia)

| Scenario | A (FDR) | B (FDR) | C (FDR) |
|---|---|---|---|
| Global null, 21 iid | **0.337** | 0.060 | **0.273** |
| Global null, dipendenza mista | **0.697** | 0.130 | **0.743** |
| Misto 14 null + 7 effetti (power) | 0.114 (power=0.991) | 0.031 (power=**0.761**) | 0.129 (power=0.986) |

Solo **B** controlla l'FDR di famiglia entro la tolleranza in entrambi gli scenari di null globale; A e C esplodono clamorosamente (fino a 0.743, quasi 7.5× q=0.10) — conseguenza diretta e attesa dell'assenza di gating quando il metodo per-cella non è calibrato. B recupera anche molta più potenza (0.761) rispetto all'architettura gated abbandonata (0.394 per lo stesso scenario, Phase 7.4A precedente) — un beneficio concreto dell'aver eliminato il gating.

## Perché nessun metodo è validato

**A e C**: falliscono già sotto iid pura (dist. gaussiana) e catastroficamente sotto dipendenza (φ≥0.5) e riuso di controlli. Nessuna ambiguità.

**B**: nettamente il migliore, supera tutti gli 8 scenari distribuzionali e 4 dei 5 scenari matched-control, ha un FDR di famiglia ben controllato — ma fallisce **due criteri distinti e genuini**: (1) esplosione >2× a φ=0.7, stabile/non-migliorabile con n; (2) fallimento catastrofico (4.46×) sotto riuso di pool di controlli condivisi, una struttura di dipendenza **combinatoria** che il suo design a blocchi temporali non è pensato per catturare.

## Metodo più promettente (informativo, non validato)

**B (studentized block bootstrap)** — base solida per un futuro redesign mirato, es. un termine di correzione cluster-robust addizionale per l'identità del controllo condiviso (oltre al blocco temporale), o una combinazione a due vie (tempo × identità-controllo).

## Regression tests — 24/24 PASS

`test_phase7_4a_dependence_aware_redesign.py`: tutti e 3 i metodi rispondono correttamente a H0 vera/falsa, la famiglia ungated non scarta mai una cella né forza p=1 artificialmente, nessuna reintroduzione dell'architettura di gating abbandonata, verdetto ricalcolato dai 4 criteri coincide con quello dichiarato, tutti i file congelati (detector, v1-v4, moduli del gate abbandonato) risultano intatti.

## File prodotti

`server/research_scripts/phase7/engine/`: `dependence_aware_mean_tests.py` (metodi A/B/C), `ungated_bh_family.py`.
`server/research_scripts/phase7/phase7_4/`: `dependence_aware_inference_calibration.py`, `ungated_21cell_bh_simulation.py`, `evaluate_dependence_aware_method_selection.py`, `phase7_4_dependence_aware_inference_calibration_v1.json`, `phase7_4_dependence_aware_method_selection_v1.json`, `test_phase7_4a_dependence_aware_redesign.py`.

Nessun file del motore congelato (detector, frozen spec v1-v4, moduli del Dependence Validity Gate abbandonato) è stato modificato.

---

**NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.**

**Commit/push eseguiti. Verdetto: PRIMARY INFERENCE METHOD NOT YET VALIDATED. Nessuna Phase 7.4B. Nessuna frozen_spec_v5. Un futuro tentativo di redesign (es. correzione cluster-robust per identità del controllo condiviso, combinata con block bootstrap temporale) richiederà una nuova, separata autorizzazione.**
