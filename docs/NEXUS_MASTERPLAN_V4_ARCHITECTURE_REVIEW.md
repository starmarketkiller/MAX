# NEXUS MASTERPLAN V4 — Architecture Optimization Review

Revisione critica, non una conferma. Ogni Improvement Card è ancorata a un'evidenza reale trovata nei census di reparto/infrastruttura di questa sessione — nessuna percentuale di beneficio inventata, nessun problema ipotizzato senza citazione.

## Metodo

Cercato attivamente (come richiesto): colli di bottiglia, componenti duplicati, passaggi non necessari, processi seriali parallelizzabili, rischi di affidabilità, rischi di crescita incontrollata degli agenti, costi evitabili, limiti del PC locale, dipendenze tra reparti, automazioni inutilmente complesse, migliorie a Fast/Deep Path, opportunità di riuso.

**Risultato principale della ricerca**: il sistema NON soffre di duplicazione incontrollata di agenti (temuta nella richiesta) — ogni census ha confermato zero nuovi agenti creati per reparto, riuso sistematico dell'Orchestrator esistente. Il rischio reale trovato è l'opposto: **gap di coordinamento (nessun Council, nessun Reviewer) e un collo di bottiglia di decisione umana non ancora codificato (Trading step 6)**, non proliferazione incontrollata.

---

## Top 10 — classificate e ordinate per impatto/fattibilità combinati

### 1. [HIGH_IMPACT] Codificare il gate "go-live" per le strategie di Trading

- **Problema verificato**: su 83 strategie nel registro, 0 sono `VALIDATED`; lo step "Approval live gate" è PLANNED/PARTIAL — nessuna funzione di gate eseguibile esiste, l'approvazione vive solo nel giudizio umano sui campi di stato.
- **Evidenza**: `contracts/edge-validation-registry.json` (65 UNVALIDATED, 9 CANDIDATE, 4 BORDERLINE, 3 FAILED, 2 FORWARD_REQUIRED su 83); nessuna funzione `can_go_live()` o equivalente trovata in `NXS_v1`/`mt5_data_v1`.
- **Soluzione proposta**: una funzione deterministica (non un modello) che legge `standalone_edge_status`+`forward_validation_status`+`defect_status` dal registro e produce `GO`/`NO_GO`/`NEEDS_HUMAN_DECISION` — mai un bypass, solo la codifica esplicita di criteri che oggi sono impliciti nella testa dell'operatore.
- **Alternativa reuse-first**: estendere `contracts/edge-validation-registry.schema.json` con un campo derivato invece di un nuovo servizio — zero nuova infrastruttura.
- **Beneficio atteso**: rende visibile (non più implicito) perché 0/83 strategie sono live — oggi questo fatto è vero ma nessun componente del sistema lo "sa" esplicitamente.
- **Costo e complessità**: basso — una funzione pura sopra dati già esistenti.
- **Rischi**: nessuno se resta un gate di visibilità/suggerimento, non un trigger di esecuzione automatica (va mantenuto `NEEDS_HUMAN_DECISION` come stato di default, mai `GO` implicito).
- **Priorità**: alta — sblocca la comprensione dello stato reale del reparto più centrale alla missione.
- **Test di accettazione**: dato un sottoinsieme di strategie con stati noti del registro, la funzione produce il verdetto atteso per ciascuna, incluso il caso BLOCKED esplicito (VOLBRK Serious 3Y).

### 2. [STRUCTURAL] Global Improvement Council — implementazione minima

- **Problema verificato**: zero integrazione con un Council in qualunque reparto, confermato indipendentemente da tutti e 7 i census.
- **Evidenza**: ricerca esplicita in ogni fork di census — nessun hit.
- **Soluzione proposta**: vedi [NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md](NEXUS_MASTERPLAN_V4_SELF_IMPROVEMENT_AND_COUNCIL.md) — estensione di `executive_v1/` (una sezione aggiuntiva), 4 nuovi tipi di evento additivi.
- **Alternativa reuse-first**: già la proposta stessa — nessun nuovo processo/servizio.
- **Beneficio atteso**: sblocca la Fase 3 della roadmap (ottimizzazione/scaling) — oggi non iniziabile in modo coordinato.
- **Costo e complessità**: medio — richiede un reparto pilota prima dell'estensione a tutti.
- **Rischi**: se implementato come revisore sincrono invece che coordinatore asincrono, ricrea il collo di bottiglia umano che deve evitare — il design lo previene esplicitamente.
- **Priorità**: alta, ma dipende dall'item 3 (Reviewer) per essere azionabile.
- **Test di accettazione**: un esperimento simulato in un reparto pilota genera i 4 eventi nell'ordine corretto, leggibili da `executive_v1`.

### 3. [STRUCTURAL] Revisore Indipendente — implementazione minima

- **Problema verificato**: nessun meccanismo che confronti baseline-vs-variante con soglia pre-registrata esiste in nessun reparto.
- **Evidenza**: `review_pipeline_v1`/`finalization_gate.py` esistono ma verificano segreti/finalizzazione di singoli task, non esperimenti di miglioramento.
- **Soluzione proposta**: vedi [NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md](NEXUS_MASTERPLAN_V4_INDEPENDENT_REVIEWER_MODEL.md) — funzione deterministica, soglia dichiarata in anticipo, mai post-hoc.
- **Alternativa reuse-first**: riusa `core/result_packet.py`'s concetto `verifier:{ran,passed,errors}` già esistente, esteso al confronto baseline/variante.
- **Beneficio atteso**: previene l'errore di selezione post-hoc che il resto del progetto tratta già come non negoziabile in Trading (preregistrazioni), applicato a tutti i reparti.
- **Costo e complessità**: basso-medio.
- **Rischi**: soglie scelte male per reparti con poca metrica storica — mitigato dal verdict `INCONCLUSIVE` esplicito invece di forzare un verdetto.
- **Priorità**: alta, prerequisito dell'item 2.
- **Test di accettazione**: dato baseline/variante sintetici con differenza nota, il revisore produce il verdict atteso (POSITIVE/NEGATIVE/INCONCLUSIVE) nei 3 casi.

### 4. [HIGH_IMPACT] Aggregatore Finance & Cost cross-reparto

- **Problema verificato**: Finance & Cost non esiste come reparto coeso — solo frammenti sparsi (`premium_model_cost_usd` in Jarvis, margine in Revenue, ROI nell'Agency).
- **Evidenza**: census Finance & Cost — 6/8 step PLANNED, `financial_risk` hardcoded a `"NONE"` su ogni task (`jarvis_v1/service.py:947`).
- **Soluzione proposta**: una `finance_section` reale in `executive_v1/sections.py` che legge i 3 frammenti già esistenti — stesso pattern delle altre 9 sezioni, nessuna nuova fonte dati.
- **Alternativa reuse-first**: questa È l'alternativa reuse-first — nessun modulo Finance nuovo, solo un aggregatore.
- **Beneficio atteso**: prima vista reale, anche se parziale, di costo totale vs ricavo totale — oggi impossibile da vedere in un unico posto.
- **Costo e complessità**: basso — i dati esistono già, serve solo l'aggregazione.
- **Rischi**: minimo — sola lettura.
- **Priorità**: alta, costo basso la rende anche un quick win mascherato da high-impact.
- **Test di accettazione**: la sezione mostra correttamente i 3 numeri sorgente quando popolati, `UNAVAILABLE` esplicito quando mancanti (mai zero fabbricato, stesso principio già usato altrove).

### 5. [QUICK_WIN] Riconciliare la terminologia priorità P0-P4 vs URGENT/HIGH/NORMAL/LOW

- **Problema verificato**: l'infografica/masterplan usa P0-P4, il codice reale (`task_queue.py`) usa `URGENT/HIGH/NORMAL/LOW` — nessuna mappatura esplicita esiste.
- **Evidenza**: census infrastruttura (Queue Manager).
- **Soluzione proposta**: documentare la mappatura esplicita (es. P0=URGENT, P1-P2=HIGH, P3=NORMAL, P4=LOW) in un unico posto canonico, oppure estendere lo schema in modo additivo se la granularità P0-P4 serve davvero.
- **Alternativa reuse-first**: la mappatura documentale è già la via più economica — nessun codice da cambiare se la granularità a 4 livelli basta.
- **Beneficio atteso**: elimina un'ambiguità che altrimenti si propaga in ogni documento di reparto di questo set.
- **Costo e complessità**: minimo.
- **Rischi**: nessuno.
- **Priorità**: bassa urgenza ma a costo quasi zero — va fatta presto.
- **Test di accettazione**: un documento canonico definisce la mappatura; nessun documento di questo set la contraddice (già verificato: questo set usa sempre "P0-P4 vedi nota terminologica").

### 6. [QUICK_WIN] Popolare un'istanza reale del Capability Registry

- **Problema verificato**: `contracts/agent-capability-registry.schema.json` esiste, **nessuna istanza popolata trovata nel repo**.
- **Evidenza**: census infrastruttura — ricerca esplicita di `agent-capability-registry*.json` non schema, zero risultati.
- **Soluzione proposta**: eseguire `build_agent_capability_registry.py` (già esistente) e committare l'output.
- **Alternativa reuse-first**: lo script generatore già esiste — questa è la via reuse-first per definizione.
- **Beneficio atteso**: primo passo verso un routing capability-aware invece di solo tier-based (TIER1-4).
- **Costo e complessità**: minimo — eseguire uno script già scritto.
- **Rischi**: nessuno, è un artefatto di sola lettura.
- **Priorità**: bassa complessità, abilita lavoro futuro (item 8 e il modello responsabili).
- **Test di accettazione**: il file generato valida contro il proprio schema (`validate_registry.py`).

### 7. [QUICK_WIN] Consolidare la duplicazione in `research_scripts/phase7`

- **Problema verificato**: più cartelle fase (es. `phase7_8g/8h/8i`) eseguono copie quasi identiche di `collect_immutable_run_manifest.py`.
- **Evidenza**: census Trading.
- **Soluzione proposta**: parametrizzare in un unico script — **direttamente riusabile**: `server/mt5_data_v1/manifests.py` (costruito in questa sessione) già generalizza esattamente questo pattern (`build_run_manifest()`, `artifact_entry_from_file()`).
- **Alternativa reuse-first**: questa È l'alternativa — nessun nuovo codice da scrivere, solo migrare le fasi esistenti a `mt5_data_v1`.
- **Beneficio atteso**: meno codice da mantenere, meno rischio di divergenza silenziosa tra copie.
- **Costo e complessità**: basso-medio (richiede toccare script di fasi passate, va fatto con cura per non alterare artefatti storici già usati come evidenza).
- **Rischi**: se fatto male, potrebbe invalidare la provenienza di artefatti di ricerca già citati come evidenza altrove — fare SOLO per fasi future, mai riscrivere artefatti storici.
- **Priorità**: bassa urgenza, alta a lungo termine.
- **Test di accettazione**: un nuovo run di fase produce lo stesso schema di manifest delle copie precedenti, verificato contro `contracts/mt5-run-manifest-v1.schema.json`.

### 8. [HIGH_IMPACT] Un template Ministral bounded write-capable

- **Problema verificato**: un solo template esiste (`REPO_INSPECTION_V1`), esplicitamente read-only — il sistema non può ancora "scrivere" codice tramite il modello locale in modo bounded, solo tramite `FreeCodingWorkerHandler` (percorso diverso, non il compiler Ministral).
- **Evidenza**: census System & Development.
- **Soluzione proposta**: un secondo template che riusa il pattern già sicuro di `FreeCodingWorkerHandler` (workspace isolato, `files_allowed`/`files_forbidden` fail-closed) ma instradato tramite `ministral_task_compiler.py`.
- **Alternativa reuse-first**: riusare `FreeCodingWorkerHandler`'s meccanismo di bounding invece di inventarne uno nuovo per il compiler.
- **Beneficio atteso**: amplia cosa il modello locale (gratuito) può fare in autonomia prima di richiedere un provider premium.
- **Costo e complessità**: medio — richiede lo stesso livello di cura di sicurezza di `FreeCodingWorkerHandler`.
- **Rischi**: un template write-capable mal bounded è il rischio di sicurezza più alto in questa lista — richiede lo stesso rigore già dimostrato nell'esistente (fail-closed su `files_allowed` vuoto).
- **Priorità**: alta ma va fatta con calma, non affrettata.
- **Test di accettazione**: lo stesso set di test di sicurezza già esistente per `FreeCodingWorkerHandler` (fail-closed, path traversal, file forbidden) applicato al nuovo template.

### 9. [STRUCTURAL] Riconciliare i due meccanismi di audit log

- **Problema verificato**: `EventLedger` generico (nessuna hash chain) vs `trade_events` (hash chain reale + trigger di immutabilità) — postura di sicurezza non uniforme tra tipi di dato.
- **Evidenza**: census infrastruttura — `app.py:781-785` per `trade_events`; nessun equivalente trovato per `EventLedger`.
- **Soluzione proposta**: NON implementare qui — decisione per l'utente se l'asimmetria è intenzionale (dati finanziari meritano garanzie più forti) o va estesa anche a `EventLedger`.
- **Alternativa reuse-first**: documentare la scelta invece di cambiare codice, se l'asimmetria è già accettabile.
- **Beneficio atteso**: chiarezza esplicita su quale garanzia di integrità esiste dove, invece di un'inconsistenza silenziosa.
- **Costo e complessità**: alto se si decide di estendere la hash chain a `EventLedger` (tocca codice condiviso, territorio di Codex) — minimo se si decide solo di documentare.
- **Rischi**: toccare `EventLedger` rischia di interferire con il lavoro concorrente di Codex — da NON fare senza coordinamento esplicito.
- **Priorità**: bassa azione immediata, alta visibilità — va presentata come proposta, non eseguita.
- **Test di accettazione**: N/A finché non c'è una decisione — questo item è una domanda per l'utente, non un'implementazione.

### 10. [FUTURE] Dipendenza da un singolo PC locale

- **Problema verificato**: l'intero percorso Ollama/Ministral dipende da una singola macchina Windows; se spenta, `/mistral` fallisce (con diagnostica chiara, non un crash — già verificato in LOCAL_INFERENCE_CONNECTIVITY_V1).
- **Evidenza**: sessione LOCAL_INFERENCE_CONNECTIVITY_V1 di questa stessa giornata — tempi di cold-start di ~49s, nessuna ridondanza.
- **Soluzione proposta**: nessuna azione ora — il degrado è già gestito con grazia (messaggio diagnostico chiaro in italiano, mai un crash). Un percorso di ridondanza (es. un secondo modello cloud economico come fallback) è un investimento futuro, non un gap urgente oggi con un solo operatore.
- **Alternativa reuse-first**: nessuna — questo è esplicitamente un item FUTURE, non un'azione.
- **Beneficio atteso**: non quantificabile ora — dipende da quanto l'uptime diventa critico in futuro.
- **Costo e complessità**: alto se implementato (richiederebbe un secondo provider configurato).
- **Rischi**: nessuno nel non agire ora.
- **Priorità**: bassa oggi, da rivalutare se l'uso di `/mistral` diventa centrale all'operatività quotidiana.
- **Test di accettazione**: N/A, item di sola osservazione.

---

## Trovato ma NON nella top 10 (per completezza, priorità più bassa)

- **Estrazione di un `ContentAgent`/`SocialAgent` generico** da AI Fashion Agency — il codice è già a forma di adapter, ma con un solo consumatore oggi non è un investimento prioritario (vedi [Social/Content](NEXUS_MASTERPLAN_V4_SOCIAL_CONTENT.md)).
- **Dashboard KPI unificata cross-reparto** — dipende dall'esistenza di item 4 (Finance aggregator) e beneficerebbe dal Council (item 2) per avere dati di miglioramento da mostrare — prematura prima di quelli.
- **Tuning del Fast/Deep Path** (`is_complex_mistral_request()`) — candidato naturale come primo esperimento pilota una volta che Council+Reviewer (item 2+3) esistono, non un'azione indipendente.
- **RBAC granulare oltre il singolo ruolo admin** — non urgente con un solo operatore umano oggi; da rivalutare se più persone useranno NEXUS.

---

## Roadmap tecnica con dipendenze (dei soli item di questa lista)

```
5 (terminologia) ──────────────────────────────────┐
6 (capability registry) ────────────────────────────┤
                                                     ├──> nessuna dipendenza, eseguibili subito
7 (consolidamento phase7) ──────────────────────────┘

3 (Reviewer) ──> 2 (Council) ──> tuning Fast/Deep Path (non in top 10)
                              └─> promozione sicura di qualunque esperimento futuro

4 (Finance aggregator) ──> Dashboard KPI unificata (non in top 10)

1 (gate go-live Trading) ─── indipendente, alta priorità propria

8 (template Ministral write-capable) ─── indipendente, richiede rigore di sicurezza proprio

9 (audit log) ─── richiede decisione utente prima di qualunque azione, coordinamento con Codex
```
