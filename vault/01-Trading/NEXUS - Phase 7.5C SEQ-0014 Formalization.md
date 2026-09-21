# NEXUS - Phase 7.5C SEQ-0014 (MECH-23 LOW_INFORMATION_STATE) Minimal State-to-Event Formalization

**Baseline:** `f7559ee` (SEQ-0015 e SEQ-0009 chiuse). Primo test del gate su una family che e' uno **STATO**, non un evento puntuale. **Questo e' il FORMALIZATION COMMIT** - congela la trasformazione STATE→EVENT, direction, episode/horizon/embargo/matching_spec PRIMA di eseguire il gate.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED. NO STATISTICAL CONTRACT BUILT.**

---

## 1. Il problema centrale

SEQ-0014 non e' un evento puntuale (come SWEEP o MOMENTUM_BURST) ma una classificazione continua di regime ("choppy/low-information"). Se ogni barra con lo stato attivo diventasse un evento, N barre consecutive nello stesso regime produrrebbero N osservazioni **false**, non N osservazioni indipendenti. Formalizzata la trasformazione:

```
STATE (in_state[t], per-barra)  ->  STATE-ENTRY EVENT (event_a = prima barra della transizione False->True)
```

## 2. Feature ispezionate (nessuna nuova)

| Feature | Ruolo | Causal safety |
|---|---|---|
| `directional_efficiency` (Kaufman Efficiency Ratio, lookback=20) | **STATE-DEFINING** (detector) | CAUSAL_SAFE, LOW leakage |
| `atr_percentile` | **MATCHING/CONTEXT** (asse distinto: livello di volatilita', non efficienza) | CAUSAL_SAFE, LOW leakage |
| `variance_ratio_proxy` | Considerata, **non usata** - concettualmente sovrapposta a `directional_efficiency`, impilarle avrebbe stretto arbitrariamente la definizione senza giustificazione causale distinta | CAUSAL_SAFE |

Nessuna feature nuova inventata. **Evitamento tautologia (sec.8):** la feature che definisce lo stato (`directional_efficiency`) e' diversa dalla feature di matching (`atr_percentile`) - verificato esplicitamente, non solo dichiarato.

## 3. Definizione di stato e state-entry event

`LOW_INFORMATION_STATE`: `directional_efficiency[t]` nel terzile **LOW** della propria distribuzione, terzili fittati **esclusivamente** su `development_discovery` (cutpoints: `q1=0.160, q2=0.335`) - non una soglia fissa scelta guardando risultati.

`event_a` = prima barra della transizione `in_state[t-1]=False → in_state[t]=True`. Una corsa di N barre consecutive produce **un solo evento** (verificato dal detector self-test: corsa di 5 barre → 1 evento, non 5). Le uscite non sono eventi. **Reset/re-entry:** nessuna finestra di reset separata - il flicker vicino al confine del terzile e' gestito dal secondo livello gia' esistente (`episode_gap_rule`), decisione esplicita per non duplicare la stessa funzione.

## 4. Direction, episode, horizon, embargo

- `event_direction_policy = NON_DIRECTIONAL` (congelato - MECH-23 non e' un candidato direzionale).
- `episode_gap_rule = 5`: derivato dal lookback di `directional_efficiency` (20 barre) - un gap ≤5 (25% del lookback) condivide ancora >75% della stessa finestra sottostante, quasi certamente rumore di misura. **Non copiato** da SEQ-0009 (gap=2) ne' SEQ-0015 (gap=3).
- `proposed_natural_horizon = 20`: simmetrico al lookback di detection (20 barre) - "cosa succede in una finestra futura della stessa ampiezza di quella che ha rilevato il regime". **Deliberatamente diverso** dal default 40 usato per SEQ-0009/SEQ-0015 (meccanismi di rigetto/rottura, non applicabile qui).
- `embargo = 19` (= horizon-1, formula vincolata).

## 5. Matching spec

`match_dimensions=["volatility_state_pre_entry"]` (terzile di `atr_percentile` a **t-1**, fit su discovery), `k=5`, `minimum_control_count=20`, `max_control_reuse_per_run=5` (convenzioni generali di progetto, `baseline_contract_v4.json`). `control_pool_construction_policy`: stesso split, esclusi evento stesso + `|r-t|<=20` + stesso episode_id.

## 6. Detector - nuovo, minimale

Nessun detector MECH-23/SEQ-0014 preesisteva in Phase 5/7.1 (confermato). Scritto `seq0014_state_entry_detector.py` (nuovo, v1) - due funzioni pure: `compute_in_state` (tercile threshold) e `compute_state_entry_rows` (transizione 0→1). 5/5 self-test PASS (incl. "corsa di 5 barre → 1 evento, mai 5").

## 7. No-rescue clause

Nessuno di questi parametri sara' modificato dopo aver visto il risultato del gate.

## 8. Regressione - 30/30 PASS

`test_seq0014_frozen_spec.py`: coerenza interna, evitamento tautologia detector-vs-matching, episode/horizon non copiati da altre family, confini di split contigui, terzili crescenti, tutti i flag `no_*` presenti.

## 9. File

`server/research_scripts/phase7/phase7_5c/seq0014_state_entry_detector.py`, `build_seq0014_frozen_spec.py`, `seq0014_frozen_structural_spec_v1.json`, `test_seq0014_frozen_spec.py`.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED. NO STATISTICAL CONTRACT BUILT.** SEQ-0015 e SEQ-0009 restano chiuse, non riesaminate.

**Prossimo passo (commit separato):** eseguire il Sequence Structural Feasibility Gate su questo spec congelato, outcome-blind, sulla sola partition `development_discovery`.
