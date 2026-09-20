# NEXUS - Phase 7.4A Final Gate Calibration / End-to-End Inference Validation

**Baseline:** `b825012` (Phase 7.4A Dependence Validity Gate). Validazione sintetica end-to-end della pipeline **già congelata** - nessuna discovery eseguita, nessun dato NEXUS letto, **nessuna modifica** a detector/soglia/episode rule/matched baseline/gate thresholds/BH policy.

**Conferma esplicita: NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.**

---

## Verdetto

## **BLOCKED — GATE REQUIRES REDESIGN**

La domanda decisiva posta dall'utente ("fra il sottoinsieme che il gate lascia `INFERENCE_VALID`, quante volte il test rigetta H0 erroneamente?") ha risposta **negativa**: il sottoinsieme superstite **non è affidabile**, e in diversi regimi è **peggio calibrato** del tasso grezzo non condizionato.

## Definition of Pass (congelata prima dell'interpretazione, sec.8)

| # | Criterio | Esito |
|---|---|---|
| 1 | FDR di famiglia (21 celle, null globale) ≤ q + tolleranza MC | ✅ PASS |
| 2 | **Type-I condizionato su `INFERENCE_VALID` non materialmente anti-conservativo** (≤max(1.5×α, α+3SE), α=.05) | ❌ **FAIL (decisivo)** |
| 3 | Nessuna instabilità catastrofica al variare di n | ❌ **FAIL (strutturale, non risolvibile con n)** |
| 4 | Skew/asimmetria non materialmente anti-conservativo | ✅ PASS |

Un solo criterio fallito bloccherebbe la validazione; qui ne falliscono due, e il criterio 2 è esplicitamente quello identificato come "il controllo più importante della task".

## 1. Conditional calibration - la tabella decisiva (n=30, 2000 repliche/φ)

| φ | n_VALID | n_SENSITIVE | n_INVALID | raw rej@.05 | **cond. rej@.05 su VALID** | gated rej@.05 (overall) |
|---|---|---|---|---|---|---|
| 0.0 | 1321 (66.1%) | - | - | ~.048 | **0.034** | 0.023 |
| 0.1 | 1298 (64.9%) | - | - | ~.05 | **0.057** | 0.037 |
| 0.2 | 1038 (51.9%) | - | - | ~.06 | **0.080** | 0.042 |
| 0.3 | 690 (34.5%) | - | - | ~.062 | **0.097** | 0.034 |
| 0.5 | 205 (10.2%) | 913 (45.6%) | 882 (44.1%) | ~.096 | **0.239** | 0.025 |
| 0.7 | 32 (1.6%) | - | - | ~.155 | **0.4375** | 0.007 |

**Il tasso di rigetto condizionato su `INFERENCE_VALID` è sistematicamente PEGGIORE del tasso grezzo non condizionato per φ≥0.2** - a φ=0.5 è quasi 2.5× il tasso grezzo (0.239 vs ~0.096); a φ=0.7 il piccolissimo sottoinsieme superstite (1.6%) rigetta quasi la metà delle volte (0.4375) contro un nominale del 5%.

## Root cause (perché succede)

Il gate seleziona le celle usando una diagnostica (ACF/Ljung-Box/ESS) calcolata **sullo stesso campione** `d_i` usato dal test. Condizionare su questa diagnostica **distorce** la distribuzione campionaria del p-value fra le repliche sopravvissute: sotto AR(1) con φ elevato, le realizzazioni in cui una forte deviazione campionaria coincide, per puro caso, con una stima locale di autocorrelazione bassa sono **esattamente quelle più probabili a superare il gate** - il meccanismo di selezione premia proprio i falsi positivi più eclatanti. La "protezione" osservata a livello di famiglia BH a 21 celle (FDR molto sotto q, sez. 3) è quasi interamente dovuta al fatto che il gate **scarta la stragrande maggioranza** delle celle problematiche (fino al 98%+ a φ=0.7), non al fatto che le celle superstiti siano affidabili.

## 3. Full BH-FDR simulation (21 celle, 300 repliche/scenario)

| Scenario | P(any rejection) | Empirical FDR | Power | mean n gated a p=1 |
|---|---|---|---|---|
| Global null, 21 celle iid | 0.0067 | 0.0067 | - | 7.1/21 |
| Global null, dipendenza mista (6 iid + 5×φ.2 + 5×φ.5 + 5×φ.7) | 0.0100 | 0.0100 | - | 14.0/21 |
| Misto: 14 null + 7 effetti veri (iid, δ=0.8) | 0.7133 | 0.0252 | **0.394** | 7.3/21 |

FDR ben sotto q=0.10 in tutti gli scenari (criterio 1 PASS) - ma **potenza solo 39.4%** anche per effetti forti e puliti (iid), a causa del ~33% di celle scartate per "falso allarme" di dipendenza anche su dati veramente iid, più la conservatività intrinseca del test. Costo reale, non solo teorico, della postura fail-closed.

## 5. Sample-size sensitivity - il problema è strutturale

| n | φ=0.5 % INFERENCE_VALID | φ=0.5 cond. rej@.05 |
|---|---|---|
| 20 | 19.3% | 0.197 |
| 30 | 8.7% | 0.310 |
| 50 | 4.5% | 0.222 |
| 100 | 0.4% | 0.250 |

Il tasso condizionato **non migliora** aumentando n da 20 a 100 (resta fra 0.20 e 0.31, sempre 4-6× il nominale) - **non è un artefatto di campione piccolo**. Man mano che n cresce, il gate diventa più severo (meno celle sopravvivono, dallo 0.19 allo 0.004%), ma le pochissime che sopravvivono restano male calibrate: aumentare `n_nominal_minimum` non risolverebbe il problema.

## 6. Skew/asimmetria - nessun problema nella stessa direzione

| Scenario | asymmetry_sensitive rate | cond. Type-I su VALID @.05 |
|---|---|---|
| Gaussiana simmetrica | 5.6% | 0.045 |
| Skew lieve (gamma) | 37.3% | **0.0** |
| Skew forte (esponenziale) | 89.6% | **0.0** |
| Code pesanti simmetriche (t3) | 43.5% | 0.052 |
| Code pesanti asimmetriche (t3) | 56.8% | **0.0** |

Direzione **opposta** al problema di autocorrelazione: sotto skew il sottoinsieme superstite è fortemente **conservativo/powerless** (mai anti-conservativo), e il flag `ASYMMETRY_SENSITIVE` si attiva correttamente in proporzione alla gravità dello skew. Lasciarlo come puro diagnostico (non gating) è **empiricamente sicuro** - non contribuisce al blocco.

## 7. Gate-selection bias

Confermato esplicitamente: `P(reject | INFERENCE_VALID, H0)` **si allontana dal nominale proprio dove serve di più** (φ crescente) - non un effetto marginale, ma la causa radice del blocco.

## Conclusione

Il gate fa esattamente ciò che il report precedente sosteneva a livello di **frequenza di classificazione** (φ alto → più raramente `INFERENCE_VALID`), ma questo **non implica** che le celle classificate `INFERENCE_VALID` producano p-value affidabili - anzi, il meccanismo di selezione le rende **meno** affidabili nel regime intermedio-alto di dipendenza (φ 0.2-0.7). La policy congelata in `b825012` **non può** essere usata come garanzia di validità statistica per BH-FDR nella sua forma attuale.

**Nessuna modifica automatica alle soglie o al design del gate è stata effettuata** - come richiesto, ci si è fermati a riportare il blocco. Nessuna `phase7_4_seq0015_frozen_spec_v5.json` creata (per esplicita istruzione, invariata in caso di fallimento).

## File prodotti

`server/research_scripts/phase7/phase7_4/`: `dependence_gated_inference_validation.py` (sezioni 1/3/5/6, eseguibili singolarmente via CLI arg), `evaluate_dependence_gated_inference_validation.py` (Definition of Pass congelata + verdetto calcolato deterministicamente), `phase7_4_dependence_gated_inference_validation_v1.json` (artefatto completo: tutte le sezioni + findings + verdetto).

Nessun file del motore o delle frozen spec (v1-v4) è stato modificato.

---

**NO REAL NEXUS OUTCOME DATA ACCESSED. NO SEQUENCE DISCOVERY EXECUTED.**

**Commit/push eseguiti. Verdetto: BLOCKED — GATE REQUIRES REDESIGN. Nessuna Phase 7.4B. Il redesign del gate (probabilmente: un approccio che non condizioni la selezione sulla stessa statistica usata per il test, es. un correttore di varianza non-selettivo, o un criterio di validità basato su informazione strutturale del run invece che su un test post-hoc sullo stesso campione) richiederà una nuova, separata autorizzazione.**
