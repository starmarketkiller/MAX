# Unified Market Intelligence Architecture V1

**Stato:** proposta architetturale concettuale, non ancora committata. Nessun codice, runtime, MQL5 o registry modificato. Nessun peso scelto, nessun parametro da ottimizzare proposto, nessun backtest nuovo. Dove esiste già una primitiva equivalente nel repository, questo documento la cita e la riusa invece di proporne una nuova — coerente con la stessa disciplina di `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` (commit `cfcdef8`).

**Fonti canoniche usate:** `contracts/edge-validation-registry.json`/`.schema.json` (Codex, `3a0906a`), `docs/TRADING_EDGE_STATUS_RECONCILIATION_V1.md` (`364deec`), `docs/CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` (`cfcdef8`), e l'intero arco Phase 4→7.5A (`vault/01-Trading/_phase4_artifacts/`, commit `ad14e97`→`8593f9c`).

---

## 0. La scoperta centrale: la maggior parte dell'architettura richiesta esiste già

Prima di progettare qualunque layer nuovo, ho verificato cosa esiste. Il risultato cambia la forma di questo documento: **l'ontologia e il vocabolario dei layer richiesti dall'utente sono già definiti**, in `market_ontology.md` (Phase 4, 17/09):

```
MARKET STATE -> CONTEXT -> EVENT -> SETUP -> TRIGGER -> SIGNAL -> ENTRY -> FILL
                                                              |
                                                      INVALIDATION / STOP / TARGET -> OUTCOME -> PROBABILITY -> EDGE -> STRATEGY
```

E il `role_vocabulary` già canonico in `contracts/edge-validation-registry.schema.json` (Codex, oggi) copre quasi esattamente i "layer" richiesti: `REGIME_DETECTOR`, `CONTEXT_FEATURE`, `LOCATION_FEATURE`, `MOMENTUM_FEATURE`, `VOLATILITY_FEATURE`, `LIQUIDITY_EVENT`, `ENTRY_TRIGGER`, `CONFIRMATION`, `FILTER`, `RISK_FEATURE`, `EXIT_FEATURE`, `POSITION_MANAGEMENT`. Il registry ha già iniziato a popolare questo per i 6 componenti del task (vedi §2).

**Ciò che genuinamente non esiste ancora, e che è il vero contenuto nuovo di questo documento:** il layer di aggregazione dell'evidenza di più componenti in una vista unificata (§4), la risoluzione dei conflitti tra componenti (§5), e il confine di sicurezza tra questa intelligenza e la decisione operativa (§9 — che in realtà esiste già a un livello diverso, vedi sotto).

---

## 1. Layer del sistema

| Layer richiesto | Esiste già come | Stato |
|---|---|---|
| Market state | `market_state_schema.md` + `market_state_dataset_v1.csv` (4809 barre H4 reali) | **Esiste** |
| Regime | Due implementazioni non riconciliate: `market_regime_layer_v1.py` (5 stati) e il classificatore causale di Phase 7.27 | **Esiste, da riconciliare** (già previsto come pre-step in `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` §2) |
| Structure / Location | `role=LOCATION_FEATURE` (es. `order_block_zone_location`, `fair_value_gap_location` già nel registry) | **Esiste** |
| Liquidity | `role=LIQUIDITY_EVENT` (es. `liquidity_sweep_detection`) | **Esiste** |
| Momentum | `role=MOMENTUM_FEATURE` (es. `adx_trend_strength`, `macd_momentum`) | **Esiste** |
| Volatility | `role=VOLATILITY_FEATURE` (dichiarato nel vocabolario, non ancora popolato per nessuno dei 6 componenti) | **Vocabolario esiste, popolazione no** |
| Event layer | `event_registry_schema.md` (14 famiglie evento, Phase 4) + `role=ENTRY_TRIGGER`/`CONFIRMATION` | **Esiste** |
| Component evidence | `evidence_status` (`UNKNOWN/PROMISING/SUPPORTED/WEAK/REDUNDANT/NOT_EVALUATED`) già nello schema Codex, oggi `NOT_EVALUATED` per tutti | **Esiste come campo, vuoto come contenuto — è esattamente il lavoro di `CONTEXTUAL_EDGE_DISCOVERY_V1` che lo popolerà** |
| Confidence aggregation | Nessuna primitiva equivalente trovata | **Nuovo — vedi §4** |
| Decision layer | Nessuna primitiva equivalente trovata (il più vicino: `draft_action` dell'AI Coach, ma per un dominio diverso) | **Nuovo — vedi §4, §9** |

## 2. Ruolo delle strategie storiche — come smontare le 83 logiche senza perdere conoscenza

**Non è un'idea nuova da progettare: è già iniziato, nel registry canonico.** Il campo `potential_reusable_components` (array di `{component, role, evidence_status, evidence_references}`) è già popolato per i 6 componenti di questo task:

| Strategia | Componenti già estratti | Note |
|---|---|---|
| ADX_RSI | `adx_trend_strength` (REGIME_DETECTOR) · `rsi_momentum_condition` (MOMENTUM_FEATURE) · `adx_rsi_entry_trigger` (ENTRY_TRIGGER) | 3 componenti da 1 strategia — esattamente la decomposizione richiesta |
| FVG_CONT | `fair_value_gap_location` (LOCATION_FEATURE) · `fvg_continuation_trigger` (ENTRY_TRIGGER) | `needs_reimplementation_review=true` (defect SLReclaim, `UNKNOWN_REMEDIATION`) |
| LIQ_SWEEP | `liquidity_sweep_detection` (LIQUIDITY_EVENT) · `sweep_reversal_trigger` (ENTRY_TRIGGER) | — |
| ORDER_BLOCK | `order_block_zone_location` (LOCATION_FEATURE) · `order_block_retest_trigger` (ENTRY_TRIGGER) | `defect_status=REMEDIATED` — usare solo logica post-fix (`17da794`) |
| MACD | `macd_momentum` (MOMENTUM_FEATURE) · `macd_cross_trigger` (ENTRY_TRIGGER, anche se `role_in_system` include anche `CONFIRMATION`) | `standalone_edge_status=FAILED` — è il pilot di Phase 1 |
| **BREAKOUT_ACC** | **nessuno — `role_in_system: []`, `potential_reusable_components: []`** | **Gap reale nel registry, non ancora decomposta. Da segnalare a Codex, non da correggere qui.** |

**Principio di decomposizione** (per le restanti 77 strategie, non eseguito qui): ogni wrapper `NXS_Strat_*` è quasi sempre, per costruzione dell'ontologia (§0), una combinazione fissa di **Context-selection + Event-detection + Trigger**, incollata in un'unica funzione con un solo trigger invece che come Setup riusabile con componenti intercambiabili (`market_ontology.md`, sez. Setup). Smontare significa estrarre ciascun pezzo come `component` indipendente con il proprio `role`, **senza toccare il codice della strategia originale** — additivo, non distruttivo, stessa disciplina del resto del progetto. Il `strategy_id` originale resta nel registry come riferimento (`evidence_references`), mai eliminato.

## 3. Component contract

**Esiste già, quasi completo, in due posti da riconciliare:**

1. `edge_component_schema.md` (Phase 4): `component_id`, `semantic_definition`, `observation_point`, `economic_rationale`, `baseline`, `expected_effect` (ΔP/ΔE), `empirical_evidence` (source/n/result/strength), `confidence` (LOW/MEDIUM/HIGH), `valid_contexts`/`invalid_contexts`, `failure_modes`, `status` (CANDIDATE/SUPPORTED/REFUTED/UNKNOWN).
2. Il `component` object di `contracts/edge-validation-registry.schema.json` (Codex, oggi): `component`, `role`, `evidence_status`, `evidence_references`, `note`.

| Campo richiesto dall'utente | Dove esiste già |
|---|---|
| Input causali | `observation_point` + `valid_contexts` (Phase 4) |
| Output | `expected_effect` (ΔP/ΔE, Phase 4) |
| Confidence | `confidence` (Phase 4, LOW/MEDIUM/HIGH) e `evidence_status` (Codex, UNKNOWN/PROMISING/SUPPORTED/WEAK/REDUNDANT/NOT_EVALUATED) — **due scale parallele, da riconciliare, non da duplicare ulteriormente** |
| Provenance | `evidence_references`/`empirical_evidence` — oggi usato sia per "dove è definito" che "dove è stata misurata l'evidenza", **conflati** |
| Validity status | `status` (Phase 4) / `evidence_status` (Codex) |
| Habitat | `valid_contexts`/`invalid_contexts` (Phase 4) — **non ancora un campo nello schema Codex** |
| Failure modes | `failure_modes` (Phase 4) — **non ancora un campo nello schema Codex** |
| **Timeframe** | **Non esiste esplicitamente in nessuno dei due schemi** — unico campo genuinamente mancante |

**Proposta minimale (non implementata qui):** non un terzo schema. Estendere additivamente il `component` object di Codex con `habitat` (↔ `valid_contexts`/`invalid_contexts`), `failure_modes`, e `timeframe` — i primi due sono letteralmente un rename/riuso di campi Phase 4 già maturi, il terzo è l'unico gap reale.

## 4. Evidence aggregation — opzioni, nessuna scelta

Nessuna primitiva equivalente esiste per questo layer specifico. Quattro opzioni, con il tradeoff esplicito di ciascuna — la scelta resta un passo successivo, non di questo documento:

| Opzione | Come funzionerebbe | Vantaggio | Rischio |
|---|---|---|---|
| **Rule-based deterministico** | Alberi AND/OR/veto espliciti sui `role`/`evidence_status` dei componenti attivi | Massima explainability (§8); stesso stile già usato per i gate di rischio esistenti (`nexus_policy`) | Rigido; non scala bene con molte combinazioni di componenti senza esplosione di regole |
| **Weighted evidence** | Somma/combinazione pesata di `confidence`/`evidence_status` per componente | Flessibile, graduale | **Richiede scegliere pesi — esplicitamente escluso da questo documento** (vincolo utente). Menzionato solo come opzione futura |
| **Probabilistico (Bayesiano)** | Estensione naturale del layer `Probability` già esistente nell'ontologia (Beta-Binomial, Wilson CI) — combinare `P(Target | componente_i, Context)` di più componenti indipendenti | **È l'opzione più "nativa"**: riusa un'infrastruttura già costruita e testata (Phase 5-6), non ne richiede una nuova | Richiede che i componenti combinati siano genuinamente indipendenti — altrimenti §7 (double-counting) corrompe la combinazione |
| **Meta-model** | Un modello (anche semplice) allenato su `evidence_status`/confidence di più componenti → vista unificata | Può catturare interazioni non lineari | **Rischio diretto con la lezione di Phase 7.4A (§0 di `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md`)**: se il meta-model viene allenato/validato sugli stessi dati usati per selezionare quali componenti includere, si ricrea la stessa circolarità che ha prodotto selezione avversa. Richiederebbe la stessa separazione diagnostica/selezione/test già imposta lì. Inoltre riduce drasticamente l'explainability (§8) |
| **Hybrid deterministico/ML** | Gate deterministici di veto (sicurezza, §9) applicati PRIMA; solo nello spazio superstite un aggregatore più soft (probabilistico o meta-model) | Mantiene il confine di sicurezza sempre deterministico | Più complesso da specificare; ma è l'opzione più coerente con come NEXUS già separa Risk Model da Setup (§0, §9) |

Nessuna di queste è scelta qui. L'opzione probabilistica è segnalata come la più coerente con l'infrastruttura esistente, non come raccomandazione definitiva.

## 5. Conflict resolution

Non ancora progettato altrove — tre casi distinti, da non confondere:

1. **Conflitto apparente da ridondanza** (es. due componenti derivati dallo stesso fenomeno sottostante — vedi §7): non è un vero conflitto, è doppio conteggio della stessa informazione con segni opposti per costruzione della formula. **Va deduplicato prima di qualunque risoluzione di conflitto**, usando la stessa metodologia di `feature_redundancy_audit_v1.md` (Pearson/Spearman su feature causali, già applicata con successo — ha già trovato che "trend" e "posizione nel range" sono correlati 0.79-0.95 nel dataset esistente, non due assi indipendenti).
2. **Conflitto genuino tra componenti indipendenti** (es. momentum H4 long vs liquidity event H1 bearish, entrambi genuinamente non ridondanti): non va risolto con una regola arbitraria scelta ora. Due approcci proposti, non scelti: (a) trattare il conflitto stesso come informazione — un segnale di bassa confidenza/NO_TRADE, non un pareggio da rompere; (b) precedenza esplicita e dichiarata per timeframe/role (es. contesto a timeframe maggiore vince su trigger a timeframe minore in caso di contraddizione diretta) — **un'ipotesi da testare con lo stesso rigore di `CONTEXTUAL_EDGE_DISCOVERY_V1`, non un assioma**.
3. **Componenti ridondanti per costruzione del registry** (stesso `role`, stessa famiglia di evento, mai verificato se aggiungono informazione indipendente): da marcare `REDUNDANT` in `evidence_status` (valore già esistente nel vocabolario Codex) prima che entrino in qualunque aggregazione — mai trattarli come due voti indipendenti.

## 6. Temporal logic

**Riuso diretto, non reinvenzione:** la distinzione Event / Trigger / Signal / Invalidation è già formalmente definita e distinta in `market_ontology.md` (§0), con `observation_point` esplicito per ciascuna. Lo stato persistente corrisponde ai campi del Context (Market State Vector); la transizione corrisponde a un cambio di fase in una state machine (es. SWEPT→MSS→RTO).

**Vincolo esplicito derivato dalla saga Phase 7.9-7.14 (CROSS_TIMEFRAME_STATE_CONTAMINATION, già nel registry come classe di defect):** qualunque componente di questo layer che mantenga stato persistente attraverso più pass multi-timeframe deve dichiarare esplicitamente il proprio `observation_point` per ogni pass, esattamente come richiesto dall'ontologia — perché le tre classi di defect già catalogate (`COOLDOWN_STATE_CONTAMINATION`: timing corrotto; `RECURSIVE_VALUE_STATE_CONTAMINATION`: valore corrotto; `STATE_MACHINE_CONTAMINATION`: fase/transizione corrotta) sono esattamente i tre modi in cui questo layer, se implementato senza quella disciplina, fallirebbe nello stesso modo già documentato per ORDER_BLOCK/BREAKOUT_ACC prima del fix.

## 7. No double-counting

**Riuso diretto e diretto ampliamento di `feature_redundancy_audit_v1.md`** (Phase 5.5): metodologia già reale (Pearson+Spearman su 25 feature causali del Market State Vector, non stimata), con 4 classi già operative: `UNIQUE`, `REDUNDANT` (derivazione di formula nota), `HIGHLY_CORRELATED` (associazione empirica), `KEEP_FOR_INTERPRETABILITY`. **Finding già esistente e direttamente rilevante per il rischio citato dall'utente** (MACD/ADX/EMA come 4 evidenze "indipendenti" dello stesso fenomeno): nel dataset Phase 4, `ema_slope` e `position_in_rolling_range` sono correlati 0.79-0.95 — trend e location-nel-range non sono assi indipendenti come spesso assunto.

**Proposta (non eseguita qui, Phase 2+):** estendere la stessa identica metodologia dal livello feature al livello `evidence_status` dei componenti — calcolare correlazione tra i segnali/evidence dei componenti nelle stesse celle di contesto, non solo tra le feature di stato grezze. Nessun nuovo framework statistico da costruire, solo lo stesso audit applicato a un livello più alto.

## 8. Explainability

**Diretta conseguenza della scelta in §4, non un layer separato da progettare ora.** Se l'aggregazione resta rule-based o probabilistica trasparente, "perché NEXUS vede LONG/SHORT/NO TRADE" è rispondibile elencando: quali componenti erano attivi, il loro `role`+`evidence_status`+`confidence`, il loro conditional edge regime-matchato (da `CONTEXTUAL_EDGE_DISCOVERY_V1`), ed eventuali veto/risoluzioni di conflitto (§5) applicate. **Infrastruttura di logging già esistente e riusabile**: lo schema `NEXUS_EVENT_V1` (append-only Activity Ledger, già esteso additivamente molte volte in questo progetto — vedi `contracts/nexus-event.schema.json`) è il posto naturale per nuovi tipi di evento di questo layer (es. `DECISION_LAYER_EVIDENCE_COMBINED`), non un nuovo sistema di log.

Se in futuro si scegliesse l'opzione meta-model di §4, l'explainability si degrada necessariamente — motivo in più per non scegliere quell'opzione per default.

## 9. Safety boundary

**Non è da costruire: esiste già, a un livello diverso, e va solo estesa la stessa disciplina.** Il confine Market Intelligence / Risk Engine / Execution già esiste concettualmente nell'ontologia (Signal → Entry → Fill, §0) e già esiste operativamente nel codice:

- `nexus_policy.HARD_CAPS_HARDENED` — limiti di rischio che nessun input a monte può superare, rifiutati non troncati.
- `NXS_CommonExposurePreflight()`, `NXS_Prot_EntryBlocked()`, ruin freeze — gate deterministici pre-esecuzione, indipendenti da quale logica ha proposto il trade.
- `nexus_policy.build_command()` — target, conferma, motivazione, TTL, chiave di idempotenza per ogni comando.
- **Il precedente più diretto**: l'AI Coach ha già esattamente questo problema risolto — `apply_action` (muta stato live) risponde 403 salvo opt-in esplicito di sviluppo; `draft_action` produce solo proposte, mai esecuzione diretta (`docs/REMEDIATION_STATUS.md`, AUD0-AI-001).

**Principio per il futuro Decision Layer, derivato direttamente da questo precedente:** il suo output è sempre e solo un `Signal` (nel senso dell'ontologia) o l'equivalente di un `draft_action` — mai un comando diretto. Deve attraversare, invariati, lo stesso Risk Model e lo stesso Execution Model che oggi governano ogni altra strategia. Nessun gate nuovo da inventare: il confine è "non lasciare che il nuovo layer salti quelli che esistono già".

## 10. Migration path — nessun big-bang

1. **Fatto**: provenance del registry (`EDGE_VALIDATION_REGISTRY_V1`, `3a0906a`).
2. **In corso (Codex)**: test di valore contestuale di un singolo componente (MACD, Phase 1 di `CONTEXTUAL_EDGE_DISCOVERY_V1`).
3. **Dopo un verdetto su MACD**: estendere lo stesso test, un componente alla volta, mai in ricerca combinatoria, agli altri 5 componenti nominati (e poi, eventualmente, a chi altro nel registry lo merita secondo gli stessi criteri — inclusa la decomposizione mancante di BREAKOUT_ACC, §2).
4. **Solo quando ≥2-3 componenti raggiungono `PROMISING`/`SUPPORTED` con regime riconciliato**: costruire il layer di aggregazione (§4) in modalità **SHADOW**, puramente osservativa — stesso pattern già validato in produzione da `JARVIS_MINISTRAL_ROUTER_V1` (calcola e registra una vista unificata, non agisce mai su di essa, nessun impatto sulla risposta/esecuzione reale).
5. **Solo dopo che la modalità SHADOW ha accumulato evidenza propria** (stessa disciplina TRUE_HOLDOUT di `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` §8): promuovere l'output ad advisory `Signal`/`draft_action`-style, sempre attraverso Risk Model ed Execution Model invariati (§9) — mai un percorso diretto.
6. **Mai**: una sostituzione big-bang delle 83 strategie esistenti. Ogni passo resta additivo e reversibile, nessuna strategia esistente viene disabilitata o eliminata come conseguenza di questo lavoro.

---

## Vincoli rispettati esplicitamente

Nessun backtest nuovo eseguito. Nessun peso scelto (§4 presenta opzioni, non decide). Nessun parametro da ottimizzare proposto. Nessun nuovo framework costruito dove una primitiva equivalente esiste già (§1-§3, §6-§7, §9 sono tutti riuso esplicito, non costruzione). Nessuna modifica a codice, runtime, MQL5 o registry.

UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1_READY_FOR_REVIEW
