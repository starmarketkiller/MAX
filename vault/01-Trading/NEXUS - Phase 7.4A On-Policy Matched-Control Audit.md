# NEXUS - Phase 7.4A On-Policy Matched-Control Simulation Audit

**Baseline:** `704ce38` (Phase 7.4A Dependence-Aware Inference Redesign). Audit mirato: il precedente stress test `control_reuse_small_pool` violava la frozen policy reale — questa fase lo corregge usando realmente `ControlReuseLedger` per l'assegnazione. **Nessun nuovo metodo inferenziale progettato, nessun dato NEXUS letto, nessuna Phase 7.4B, nessuna frozen_spec_v5.**

**Conferma esplicita: NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.**

---

## 1. Violazione confermata

Il vecchio generatore `control_reuse_small_pool` usava `reuse_pool_size=10` per `30 eventi × 5 controlli = 150 assegnazioni` → **~15 usi medi per controllo**, contro la frozen policy `max_control_reuse_per_run=5` enforced da `ControlReuseLedger`. **Confermato**: quello scenario è `OFF_POLICY_STRESS` e non rappresenta un regime che la pipeline reale possa produrre. Il valore riportato in precedenza (Type-I=0.223) resta nel record ma **non può più essere usato come blocker specifico per la policy congelata**.

## 2-3. Simulazione on-policy + feasibility accounting

`on_policy_matched_control_simulation.py` usa **realmente** `ControlReuseLedger(max_control_reuse_per_run=5)` per filtrare il pool disponibile ad ogni assegnazione — enforcement meccanico, non statistico "in media". Minimo teorico per `n_events=30, k=5, max_reuse=5`: **30 controlli unici** (confermato: `30×5/5=30`).

**Scoperta laterale rilevante**: con selezione **uniforme casuale** fra i candidati disponibili, l'assegnazione fallisce per "packing" (candidati disponibili < k nonostante capacità aggregata sufficiente) nell'**86% delle repliche** al pool minimo esatto. Corretto con una selezione "meno-usato-per-primo" (pareggio casuale, il ledger resta l'unica autorità di enforcement) — **0% di fallimenti** su 300+ repliche verificate. Un vero motore di matching non ignorerebbe l'informazione di utilizzo residuo già nota, quindi questa è una correzione realistica, non un aggiustamento per far tornare i conti.

| Pool size (max_reuse=5) | max reuse osservato | reuse medio | Type-I@.05 |
|---|---|---|---|
| 30 (minimo) | 5 | 5.00 | 0.077-0.098 |
| 45 (1.5×) | 4 | 3.33 | 0.058-0.071 |
| 60 (2×) | 3 | 2.50 | 0.051-0.059 |
| 150 (ampio) | 1 | 1.00 | 0.030-0.033 |

## 4. Reuse cap sweep (pool minimo per ciascun livello — condizione di stress più severa per quel tetto)

| max_reuse | pool minimo | reuse osservato | Type-I@.05 |
|---|---|---|---|
| 1 | 150 | 1 | 0.026-0.036 |
| 2 | 75 | 2 | 0.037-0.050 |
| 3 | 50 | 3 | 0.056-0.062 |
| **5 (policy NEXUS)** | **30** | **5** | **0.087-0.098** |

Relazione monotona attesa: più il tetto è permissivo, più il Type-I sale — ma **anche al tetto congelato di 5, isolato, resta sotto la soglia di esplosione 2× (0.10)**.

## 5. Audit di `overlapping_control_sets`

**Confermato**: il vecchio generatore (nessun ledger, nessun tracciamento di identità) produce **max_reuse_observed=8** (11 indici oltre il tetto di 5) — anch'esso `OFF_POLICY`. Ricostruito on-policy: Type-I@.05=**0.095**, anch'esso borderline ma sotto soglia di esplosione.

## 6. Matrice temporal-overlap × identity-reuse — il risultato decisivo

| | Bassa sovrapposizione temporale | Alta sovrapposizione temporale |
|---|---|---|
| **max_reuse=1** (pool=150) | 0.028-0.039 | 0.060-0.065 |
| **max_reuse=5** (pool=30, policy NEXUS) | 0.092-0.094 | **0.229** |

**Il riuso al tetto consentito, DA SOLO, è borderline (sotto 2×). Ma COMBINATO con alta sovrapposizione temporale dei controlli riusati, produce un'esplosione reale (4.6× il nominale).** Il ledger limita *quante volte* un controllo è riusato, ma non impedisce che i controlli riusati siano anche vicini nel tempo/regime — la policy attuale non esclude questa combinazione.

## 7. Metodo B non modificato

`studentized_block_bootstrap_p` usato identico, invariato, su tutti gli scenari on-policy — nessuna modifica al metodo, come richiesto (l'obiettivo era isolare l'effetto della correzione del simulatore, non ri-progettare l'inferenza).

## 8-9. Correzione del record scientifico + decisione

Il vecchio risultato (`control_reuse_small_pool`, Type-I=0.223) resta nel record **marcato esplicitamente `OFF_POLICY_STRESS`**, non cancellato, non più utilizzabile come blocker specifico per la pipeline reale.

## **Verdetto control-reuse: `ON_POLICY_CONTROL_REUSE_RISK_CONFIRMED`**

Non per il motivo originariamente ipotizzato (riuso isolato catastrofico — smentito, era artefatto off-policy), ma per un motivo **diverso e più preciso**: l'**interazione fra riuso al tetto consentito e sovrapposizione temporale dei controlli riusati**, non esclusa dalla sola policy `max_control_reuse_per_run=5`.

## Verdetto complessivo — invariato

## **PRIMARY INFERENCE METHOD NOT YET VALIDATED**

Confermato **indipendente**: il blocker di dipendenza seriale forte (φ=0.7, Type-I@.05 Metodo B = 0.112-0.136 su n=20-100, esplosione 2.2-2.7× stabile e non risolvibile con più dati) resta invariato da questa patch e da solo basterebbe a non validare alcun metodo.

## Implicazioni per un futuro redesign

Ora sappiamo che ci sono **due problemi reali distinti**, non uno:
1. **Dipendenza seriale forte** (φ≥0.5-0.7) — confermato, indipendente, non affetto da questo audit.
2. **Interazione riuso-identità × sovrapposizione temporale** — confermato ora, più mirato di quanto ipotizzato: non basta gestire l'autocorrelazione nel tempo, serve anche una correzione che tenga conto di QUANDO i controlli condivisi sono stati "attivi" (non solo quante volte sono stati riusati). Questo restringe significativamente lo spazio di un futuro redesign (es. blocco/clustering che consideri congiuntamente posizione temporale e identità del controllo condiviso), evitando di costruire un'architettura completa "tempo × identità" quando il problema di identità pura, isolato, è già borderline-gestibile dalla policy attuale.

## Regression tests — 21/21 PASS

Copre: formula del minimo teorico, conferma violazione del vecchio generatore (entrambi gli scenari), enforcement del ledger mai superato su 150+ repliche on-policy, pool insufficiente correttamente rifiutato, selezione meno-usato-per-primo verificata a 0 fallimenti di packing, struttura e coerenza interna del verdetto nell'artefatto, blocker φ=0.7 ancora referenziato invariato, tutti i file congelati (detector, v1-v4) intatti, nessuna v5 creata. Nessuna regressione sulla suite precedente (24/24 ancora PASS).

## File prodotti

`server/research_scripts/phase7/phase7_4/`: `on_policy_matched_control_simulation.py`, `run_on_policy_matched_control_audit.py`, `phase7_4_on_policy_matched_control_audit_v1.json`, `test_phase7_4a_on_policy_control_reuse_audit.py`.

Nessun file del motore congelato modificato.

---

**NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.**

**Commit/push eseguiti. Verdetto complessivo: PRIMARY INFERENCE METHOD NOT YET VALIDATED (φ=0.7 resta il blocker primario indipendente; il rischio di control-reuse è ora meglio circoscritto: interazione con la sovrapposizione temporale, non riuso isolato). Nessuna Phase 7.4B. Nessuna frozen_spec_v5. Un futuro redesign mirato richiederà una nuova, separata autorizzazione.**
