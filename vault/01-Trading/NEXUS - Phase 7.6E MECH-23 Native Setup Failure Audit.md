# NEXUS - Phase 7.6E MECH-23 Native Setup Failure Audit

**Baseline:** `67282de` (Phase 7.6D Outcome-Horizon Contract, bloccato su `DESIGN_V2_BLOCKED_ON_OUTCOME_HORIZON_CONTRACT`). Audit **semantico**, non un rescue: nessun outcome letto, nessuna barrier magnitude/horizon scelti, nessuna geometry/preflight eseguita, nessun DESIGN_V2 creato, nessuna modifica ai frozen artifact precedenti.

**Conferma esplicita: NO NEXUS OUTCOME DATA ACCESSED. NO STRUCTURAL PREFLIGHT EXECUTED. NO EDGE DISCOVERY PERFORMED.**

---

## Il problema trovato dal reviewer

Phase 7.6D aveva assunto che una doppia barriera ATR (`P(+X ATR before -1 ATR)`) potesse rappresentare "il fallimento del setup" per le 6 famiglie SEQ-0014B. Ma queste 6 famiglie sono detector/eventi direzionali RAW (`build_events_p71.py`), non necessariamente strategie complete con entry+invalidazione+stop+target+timeout. Imporre una barriera ATR sintetica rischia di misurare "comportamento direzionale del prezzo dopo un evento raw" invece di "successo/fallimento di un setup" - la stessa confusione claim-su-setup vs claim-su-prezzo gia' trovata (e corretta) fra SEQ-0014A e SEQ-0014B in Phase 7.6A, qui riemersa ad un livello piu' fine.

## 1-2. Audit e classificazione delle 6 famiglie (solo definizioni gia' esistenti)

| Famiglia | Native invalidation | Native target | Classificazione |
|---|---|---|---|
| VOLATILITY_EXPANSION | Nessuna | Nessuno | `DIRECTIONAL_EVENT_ONLY` |
| DISPLACEMENT | Nessuna | Nessuno | `DIRECTIONAL_EVENT_ONLY` |
| **BREAKOUT** | **FAILED_BREAKOUT** (chiusura oltre livello rotto entro 5 barre - gia' etichettato "outcome failure di BREAKOUT" in Phase 7.6B) | Nessuno (RETEST e' un diagnostico di tenuta, non un target) | `PARTIAL_SETUP` |
| **SWEEP** | **RECLAIM** (chiusura oltre livello swept entro 10 barre - gia' etichettato "outcome failure/non-risoluzione di SWEEP" in Phase 7.6B, ma con doppio uso ambiguo: lo stesso trigger genera anche un nuovo evento tradabile) | Nessuno | `PARTIAL_SETUP` |
| COMPRESSION_RELEASE | Nessuna | Nessuno | `DIRECTIONAL_EVENT_ONLY` |
| PULLBACK | Nessuna | Nessuno | `DIRECTIONAL_EVENT_ONLY` |

**0/6 FULL_NATIVE_SETUP, 2/6 PARTIAL_SETUP, 4/6 DIRECTIONAL_EVENT_ONLY.** Nessuna famiglia possiede un lifecycle di trade completo - anche BREAKOUT/SWEEP hanno solo il lato invalidazione, mai un target/successo nativo.

## 3. Status semantico della doppia barriera ATR

| Famiglia | Status |
|---|---|
| BREAKOUT | **`SEMANTICALLY_MISALIGNED`** - esiste GIA' un'invalidazione strutturale nativa (FAILED_BREAKOUT), la barriera ATR la ignora completamente |
| SWEEP | **`SEMANTICALLY_MISALIGNED`** - stessa logica (RECLAIM gia' nativo, ignorato) |
| Altre 4 | `COMPATIBLE_BUT_SYNTHETIC` - nessuna definizione nativa con cui confliggere, ma comunque inventata |

**Nessuna famiglia classificata `NATIVE`.**

## 4. Guardia contro la falsa equivalenza

Due assunzioni esplicitamente respinte (non postulate): "detector direzionale raw = setup tradabile completo" e "mancato +X ATR = fallimento del setup" - nessuna delle due verificata equivalente contro le definizioni pre-esistenti.

## 5. Correzione del censoring

Punto matematico del reviewer confermato: `1 - P(success)` e' una probabilita' di fallimento **solo se** il caso non risolto (censored) e' stato esplicitamente collassato in FAILURE da una policy ex-ante. Senza quella policy, la formulazione corretta e' `P(SUCCESS) + P(FAILURE) + P(UNRESOLVED) = 1`. Corregge una frase di Phase 7.6D (`primary_outcome_decision`) **senza modificare l'artifact originale** (annotazione in audit separato, stessa disciplina di `f6b0859`).

## 6. Identita' del claim: A vs B

- **A:** "CHOPPY peggiora la performance di setup/trade realmente definiti."
- **B:** "CHOPPY modifica il comportamento direzionale futuro del prezzo dopo eventi detector raw."

**Attualmente operazionalizzata: B.** Il design gia' testato (`DESIGN_V1`) e la classe di outcome proposta in Phase 7.6D stavano costruendo B vestita col linguaggio di A ("filter utility", "fallimento del setup") - dichiarato qui esplicitamente, non lasciato implicito.

## 7. Conseguenza sul pooled design

Un `failure_F` per famiglia (concettualmente piu' fedele) non e' implementabile oggi in modo uniforme: solo 2/6 famiglie hanno anche solo un lato (invalidazione), le altre 4 nulla. Un contratto di outcome pooled unico sulle 6 famiglie e' prematuro **indipendentemente** dalla magnitudo di barriera - il problema precede la scelta dei parametri di Phase 7.6D.

## 8. Decisione

**Verdetto: `PARTIALLY_AVAILABLE_REQUIRES_SETUP_FORMALIZATION`.** Non il caso piu' severo (2 famiglie hanno gia' un componente nativo su cui costruire), ma non disponibile (quel componente e' incompleto, e le altre 4 non hanno nulla).

## 9. Prossimo requisito (nessuno stop/target inventato)

Riorganizzazione di pipeline proposta (non implementata):

```
EVENT RESEARCH → STRATEGY FORMALIZATION → STRATEGY VALIDATION → META-FILTER RESEARCH
```

MECH-23 andrebbe applicato solo a strategie che hanno gia' superato il proprio gate di validazione, non alle 6 famiglie raw nella loro forma attuale - evita di testare un filtro su idee gia' refutate/incomplete con il rischio di "salvarne" una per caso (data mining involontario su 3 hypothesis sovrapposte: detector + execution rule sintetica + regime filter).

## Regressione

64/64 PASS su questa suite. **0 regressioni** sulle altre 19 suite Phase 7 (20 totali). Verificato: tutti i frozen artifact precedenti (`fb52168`, `6c0d3f6`, `80e7cbc`, `f6b0859`, `67282de`) invariati (hash verificati).

## Deliverables

`seq0014b_native_setup_failure_audit_v1.json`, `build_seq0014b_native_setup_failure_audit.py`, `test_seq0014b_native_setup_failure_audit.py` - tutti in `server/research_scripts/phase7/phase7_6e/`. Nessuna modifica agli artifact frozen precedenti.

---

**NO NEXUS OUTCOME DATA ACCESSED. NO STRUCTURAL PREFLIGHT EXECUTED. NO EDGE DISCOVERY PERFORMED.** Nessuna scelta di primary outcome. Nessuno stop/target/invalidazione inventato. SEQ-0015 e SEQ-0009 restano chiuse.

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
FASE ATTUALE:
identita' nativa del "setup failure" verificata:
2/6 PARTIAL_SETUP, 4/6 DIRECTIONAL_EVENT_ONLY
PROSSIMO SBLOCCO:
formalizzare strategie direzionali reali
prima di testare MECH-23 come meta-filter
```

Come scritto dal reviewer: se manca la semantica nativa di strategia non e' un problema, e' una scoperta architetturale - separare nettamente event discovery, strategy construction e meta-filtering rende l'intero impianto di ricerca piu' pulito e piu' difficile da ingannare.
