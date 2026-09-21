# NEXUS - Phase 7.7A Strategy Lifecycle Registry & Candidate Inventory

**Baseline:** `082a456` (Phase 7.6E: RAW EVENT != STRATEGY, dimostrato sulle 6 famiglie SEQ-0014B). Primo inventario canonico delle strategie REALMENTE formalizzate nel progetto, separate dai raw event. Nessuna strategia nuova, nessuna modifica a MECH-23, nessun nuovo outcome letto, nessun backtest rieseguito.

**Conferma esplicita: NO NEW OUTCOME DATA ACCESSED. NO NEW BACKTEST EXECUTED. NO EDGE DISCOVERY PERFORMED.**

---

## Fonti usate (tutte gia' esistenti, nessuna inventata)

- `contracts/strategy-registry.json` - **83 strategie**, generato da codice (`knowledge/strategy_database.json` + `NXS_StrategyProfiles.mqh` + `server/backtest.py`) - il registro canonico di infrastruttura.
- `vault/01-Trading/Strategie/MOC - Strategie.md` - **37 strategie live EA** raggruppate per evidenza empirica (R-multiple/PF su backtest 6 anni 2019-2024).
- Phase 5/5.5/6/6.5/6.6 (H001-H015) - l'unico hypothesis con framework statistico rigoroso completo (Wilson CI, dependence audit, true holdout).
- `NEXUS - Strategy Foundry Phase 3 Volatility Breakout Implementation.md` - VOLATILITY_BREAKOUT_CONFIRMED, parita' Python/MQL5 verificata bit-per-bit.
- `NEXUS - Failure Memory (Registro Pattern di Fallimento Metodologico)` - pattern di fallimento a livello di ESECUZIONE.

## Deep-dive candidates (verificati in profondita' contro l'artifact reale)

| Candidato | Classificazione | Evidenza | Meta-filter eligibility |
|---|---|---|---|
| **VOLATILITY_BREAKOUT_CONFIRMED** | `FULL_STRATEGY_SPEC` (entry/direction/SL/TP/timeout tutti espliciti, parita' Python/MQL5 927/927 identici) | `HOLD_NEEDS_MORE_EVIDENCE` (PF=1.165, n=14/6mesi - non refutata, solo campione piccolo) | `META_FILTER_ELIGIBLE` |
| **H006_LIQUIDITY_SWEEP_RECLAIM** | `FULL_STRATEGY_SPEC` | `RETAIN_E2` / `BORDERLINE` (delta_p=0.057<0.15, CI95 sovrapposte, direzione BUY/SELL inconsistente) | `META_FILTER_ELIGIBLE` (bassa priorita' pratica) |
| **WICK_SWEEP_RECLAIM** | `PARTIAL_STRATEGY` | `REFUTED_AT_EXECUTION_VALIDATION` (shadow PF=5.80 -> reale PF=0.78-0.80) | `META_FILTER_INAPPROPRIATE` |
| **H015_SAR_EXTERNAL_VALIDATION** | `FULL_STRATEGY_SPEC` | `REFUTED` (PF=0.61, soglia FAIL<0.95) | `META_FILTER_INAPPROPRIATE` |
| **SAR (live MQL5)** | `FULL_STRATEGY_SPEC` (strutturale) | `REFUTED` (-34.3R/6y, 0/6 anni positivi) | `META_FILTER_INAPPROPRIATE` |
| **ADX_RSI** | `FULL_STRATEGY_SPEC` (strutturale) | `REFUTED` (-15.3R/6y, 1/6 positivi) | `META_FILTER_INAPPROPRIATE` |
| **BREAKOUT_ACC** | `FULL_STRATEGY_SPEC` (strutturale) | `DISCOVERY_SUPPORTED` informale (+4.3R/6y, 5/6 positivi - MA nessun Wilson CI/dependence-audit) | `META_FILTER_NOT_READY` |

**SAR** ha due identita' correlate-ma-distinte (H015 validazione Python esterna vs strategia live MQL5) - **entrambe convergono indipendentemente su REFUTED**, un segnale di refutazione robusto non dipendente da un solo metodo.

**BREAKOUT_ACC vs raw BREAKOUT vs VOLATILITY_BREAKOUT_CONFIRMED**: tre identita' distinte che condividono solo la parola "breakout" - disambiguate esplicitamente, mai assunte equivalenti (stesso principio guardia di Phase 7.6E).

## Le 6 famiglie SEQ-0014B (invariate, riferimento a Phase 7.6E)

0 `FULL_NATIVE_SETUP`, 2 `PARTIAL_SETUP` (BREAKOUT, SWEEP), 4 `DIRECTIONAL_EVENT_ONLY` - non riclassificate qui.

## Inventario completo (83 strategie, rule-based da `contracts/strategy-registry.json`)

Tutte e 83 hanno `live_implementation` e/o `research_implementation` → classificate `FULL_STRATEGY_SPEC` a livello strutturale (framework `NXS_StrategyProfiles.mqh`/`STRAT_MAP` gia' verificato per i deep-dive), ma **non individualmente riverificate** oltre ai 7 candidati sopra + le 6 famiglie Phase 7.6E - dichiarato esplicitamente come `STRUCTURALLY_IMPLEMENTED_NOT_INDIVIDUALLY_VERIFIED`.

## Incoerenze trovate nei registry esistenti (sec.12)

### 1. Status `ACTIVE` nonostante evidenza confermata negativa (finding principale)

**5 strategie** (`SAR`, `MACD`, `RSI_DIV`, `ADX_RSI`, `TSI`) hanno `status=ACTIVE` in `contracts/strategy-registry.json` **nonostante** il MOC le classifichi "Fallite - confermato su campione ampio" (400-1150 trade su 6 anni, tutte con R-multiple marcatamente negativi, TSI addirittura su 721 trade). Verificato programmaticamente (non narrato). **Non affermato**: se capitale reale sia attualmente a rischio - il flag runtime `NXS_Profile_Enabled` (che potrebbe gia' avere disattivato queste strategie a prescindere da questo registro) non e' stato letto in questo audit.

### 2. Drift di vocabolario su H006 (stesso risultato, tre etichette)

`hypothesis_registry_v1.json` (Phase 5.5) usa `status='WEAK'`; `h006_primary_result.json` (Phase 6) usa `VERDICT='BORDERLINE'`; `h006_decision_card_v2.json` (Phase 6.6) usa `current_grade='E2'`/`decision='RETAIN_E2'` - stesso `delta_p=0.0572` citato ovunque, nessuna contraddizione sostanziale, ma un vero drift di vocabolario fra fasi.

### 3. Ambiguita' di mappatura "Cisd"

MOC descrive "Cisd" come strategia 🟢 promettente con trade reali su 6 anni (+3.2R), ma il match piu' vicino nel registro canonico (`CISD_TRUE`) ha `live_implementation=False` (research-only) - possibile rinominazione/refactoring non riflesso, non disambiguato qui.

## Pipeline formalizzata (contratto, nessuna nuova infrastruttura)

```
EVENT RESEARCH → STRATEGY FORMALIZATION → STRATEGY VALIDATION → META-FILTER RESEARCH → EXECUTION VALIDATION → PORTFOLIO/RISK
```

MECH-23 appartiene a META-FILTER RESEARCH, applicabile solo a candidati gia' FULL_STRATEGY_SPEC con evidenza sufficiente (VOLATILITY_BREAKOUT_CONFIRMED, H006) - mai a raw event o a strategie gia' refutate.

## Regressione

79/79 PASS su questa suite. **0 regressioni** sulle altre 20 suite Phase 7 (21 totali).

## Deliverables

`strategy_lifecycle_registry_v1.json`, `strategy_evidence_matrix_v1.json`, `strategy_meta_filter_eligibility_v1.json`, `build_strategy_lifecycle_registry.py`, `test_strategy_lifecycle_registry.py` - tutti in `server/research_scripts/phase7/phase7_7a/`. Nessuna modifica agli artifact frozen precedenti.

---

**NO NEW OUTCOME DATA ACCESSED. NO NEW BACKTEST EXECUTED. NO EDGE DISCOVERY PERFORMED.** Nessuna strategia nuova inventata, MECH-23 non modificato. SEQ-0015 e SEQ-0009 restano chiuse.

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
FASE ATTUALE:
Strategy Lifecycle Registry costruito -
VOLATILITY_BREAKOUT_CONFIRMED e H006
sono i candidati piu' maturi (entrambi
non refutati, entrambi bisognosi di
piu' evidenza)
PROSSIMO SBLOCCO:
accumulare evidenza su un candidato
META_FILTER_ELIGIBLE prima di applicare
un regime filter come MECH-23
```

Il 68% resta fermo: struttura concettuale enormemente migliorata (mappa completa lifecycle/evidenza, incoerenze di governance reali portate alla luce), ma nessuna nuova evidenza deployable prodotta.
