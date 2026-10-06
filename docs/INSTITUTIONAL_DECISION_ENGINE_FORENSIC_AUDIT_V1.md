# Institutional Decision Engine — Forensic Audit V1

**Stato:** forensic audit, non committato. Nessuna modifica a codice, nessun backtest, nessun commit/push. Tutto CODE_VERIFIED — letto `NXS_InstitutionalCore.mqh` (completo), `NXS_SignalQuality.mqh` (completo), `NXS_MarketContext.mqh` (sezioni chiave: struct `SNXSContext`, `NXS_Context_Update`, `NXS_Context_DirectionalScore`) e i default dei parametri `Inp*` correlati in `NXS_Inputs.mqh`.

**Verdetto sintetico, prima del dettaglio:** il "Modello Istituzionale v2.1.0" (`InpUseInstitutionalCore`, OFF di default) **contiene già un prototipo funzionante e testato di buona parte dei 4 blocchi del futuro Unified Engine** — grouping, context weighting, conflict handling via netting, e un meccanismo di anti-double-counting esplicito e commentato (`AUD0-INST-010`). Non è il 30-50% stimato dall'utente nel punto di massima ottimisticità, ma è sostanziale: **stima più precisa post-lettura, 35-45% della logica di aggregazione**, concentrata soprattutto su grouping/conflict/eligibility, molto meno su context-weighting (quella parte è legacy/fragile, vedi sotto).

---

## 1. Input

`SNXSSignal all[]` — l'output già prodotto dalle strategie (stesso struct usato ovunque in NEXUS, `s.dir`/`s.score`/`s.stratName`/`s.slPrice`/`s.tpPrice`). **Nessun nuovo tipo di dato di contesto indipendente** — il motore consuma segnali già generati, non il Market State Vector grezzo. Questo è un punto architetturale importante: il Modello Istituzionale opera a valle delle strategie (post-trigger), non a monte come un vero layer di "component evidence" nel senso di `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` §0 — riceve già Signal (ontologia Phase 4), non Event/Setup.

## 2. Signal grouping

`NXS_Institutional_Decide()`: somma gli score per direzione (`buySum`/`sellSum`), sceglie la direzione dominante per somma grezza **solo per decidere il verso**, poi ricalcola con la correzione di famiglia (vedi §5) per la vera conviction netta usata nei gate. Tiene traccia del "top contributor" per direzione (score più alto) e della sua SL strutturale, usata poi per allargare lo stop del gruppo.

## 3. Context weighting

Due livelli distinti, da non confondere:

1. **Pre-aggregazione, per-voto** (`NXS_ApplyContextQuality`, `NXS_SignalQuality.mqh`): veti booleani (regime, MTF, premium/discount, RR/SL) + un bonus/penalità continuo (`NXS_Context_DirectionalScore`) applicato allo score del singolo voto PRIMA del raggruppamento.
2. **Context vector** (`g_ctx`, `NXS_MarketContext.mqh`): 8 dimensioni — `htfBias`, `structTrend`, `bosDir`, `chochDir`, `reactionDir`×`reactionQ`, `sweepDir`, `zoneDir`, `amdActive` — combinate in `NXS_Context_DirectionalScore` con **pesi fissi hard-coded**: HTF=8.0, Struct=5.0, BOS=4.0, CHoCH=4.0, React=10.0 (scalato per qualità), Sweep=6.0, Zone=5.0, AMD=+3.0 bonus, tetto bonus=20.0, tetto penalità=15.0.

**Scoperta rilevante non richiesta ma importante:** questo è **esattamente** l'opzione "weighted evidence" di `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` §4, già implementata — e **nessuno di questi pesi ha una citazione di evidenza/backtest vicina nel codice**, a differenza della quasi totalità degli altri parametri NEXUS (che quasi sempre citano una nota vault/data di verifica). Questo è un segnale concreto che questi pesi sono **stime iniziali mai calibrate**, non un risultato di ricerca — classificazione: **legacy/fragile**, non pericoloso di per sé (è dietro un flag OFF di default) ma da non ereditare come "verità" nel nuovo design.

**Terza rappresentazione di contesto/regime nel progetto, non riconciliata con le altre due:** `g_ctx` è indipendente sia da `market_regime_layer_v1.py` (Phase 4) sia dal classificatore causale di Phase 7.27 (già segnalati come da riconciliare in `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` §2). **Ora sono 3, non 2** — aggiornamento rilevante per quel task.

## 4. Score calculation

Score di ogni voto = score prodotto dalla strategia (già nel range ~55-72 per i 7 componenti già catalogati) + bonus/penalità di contesto (±20/-15 max). Nessuna normalizzazione probabilistica (non Beta-Binomial/Wilson, a differenza del layer `Probability` di `market_ontology.md`) — è un punteggio euristico 0-100, non una stima di probabilità con incertezza dichiarata.

## 5. Direction aggregation + anti-double-counting (il pezzo più importante)

**Questo è il contenuto più direttamente riusabile del motore.** Commento `AUD0-INST-010` nel codice stesso: *"LA CONVICTION NON E' UNA SOMMA... sommare gli score di strategie ALTAMENTE CORRELATE moltiplica la convinzione apparente senza aggiungere informazione"* — **esattamente il problema centrale di `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md` e `COMPONENT_COLLAPSE_HIGH_VALUE_VERIFICATION_V1.md`**, già riconosciuto e mitigato (parzialmente) in produzione.

**Meccanismo:** `_nxs_inst_family(stratName)` — classificatore a 6 bucket per substring match sul nome (**IMBALANCE**: FVG/IFVG/DISP/VOID; **STRUCTURE**: OB/ORDER_BLOCK/BMS/STRUCT; **LIQUIDITY**: LIQ/SWEEP/TURTLE/JUDAS; **MEAN_REVERSION**: REVERSAL/RSI/BOLLINGER/RANGE; **MOMENTUM**: BREAKOUT/BO/MACD/ADX/EMA/SAR; **OTHER**: resto). Dentro ogni famiglia, il primo contributo vale pieno, i successivi pesano 1/2, 1/3, 1/4... (`w = 1/(famCnt+1)`).

**Confronto diretto con la tassonomia di `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md` §6**: i 6 bucket di `_nxs_inst_family` si sovrappongono fortemente alle 10 macro-categorie che avevo proposto (trend/momentum/volatility/liquidity/structure/imbalance/breakout/mean_reversion/location/session) — **ma non sono lo stesso schema**: qui MOMENTUM include anche BREAKOUT (che nel mio schema era una categoria separata "expansion"), e STRUCTURE include BMS (che qui ho classificato come fenomeno di liquidità/state-machine condiviso con LIQ_SWEEP in `COMPONENT_COLLAPSE_HIGH_VALUE_VERIFICATION_V1.md` §4). **Nessuno dei due schemi è "quello giusto" per costruzione — vanno riconciliati, non scelti arbitrariamente.**

**Limite dichiarato onestamente nel codice stesso:** *"E' una correzione grossolana — la matrice di correlazione vera non esiste nel registro — ma e' esplicita e verificabile"*. Classificazione: **concettualmente valido** (il principio — pesare meno i contributi correlati — è esattamente corretto e anticipa `feature_redundancy_audit_v1.md`), **ma l'implementazione è fragile**: substring match sul nome, non sulla relazione di codice reale (non avrebbe mai scoperto, da solo, che ORDER_BLOCK e OB_MIT condividono letteralmente lo stesso stato — li classifica entrambi "STRUCTURE" per nome, arrivando alla stessa diminuzione di peso ma per la ragione sbagliata/più debole).

## 6. Conflict handling

Nessuna risoluzione esplicita di conflitto nel senso di `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` §5 — è **netting puro**: `net = |buyAdj - sellAdj|`. Se buy e sell sono vicini, la conviction netta scende sotto soglia e il motore semplicemente non apre nulla (`InpInstMinConviction=60.0`). Non c'è un concetto di "conflitto rilevato e segnalato" — un conflitto forte e un semplice silenzio del mercato producono lo stesso esito operativo (nessun trade), **indistinguibili nel log della decisione**. Classificazione: **legacy/fragile** per lo scopo di explainability (§8 del design architetturale) — funziona per decidere se tradare, non per spiegare "perché NO_TRADE".

## 7. Threshold/gates

- `InpInstMinConviction=60.0`, `InpInstMinContributors=1` — gate finali post-aggregazione.
- Tutti i veti di `NXS_ApplyContextQuality` (§3) sono gate pre-aggregazione, booleani, ELIGIBILITY_CONTROL per la taxonomy di `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md` §2 — coerente, non MARKET_EVIDENCE.
- **`_nxs_regime_veto`**: liste hardcoded di nomi (mean-reversion: BOLLINGER/BB_SQUEEZE/RANGE_FADE/RSI_DIV/MALAYSIAN_SNR/PIVOT_WICK; trend-follow: ADX_RSI/MACD/SAR/TSI/EMA_PULLBACK/ICHIMOKU/BJORGUM/BREAKOUT_ACC/LONDON_BO) — **è un prototipo rule-based, non statistico, dello stesso principio di `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` §7 (separare habitat da segnale)**. Calcola il regime **fresco sul TF proprio della strategia** (fix documentato nel codice, bug precedente: regime calcolato su M15 sempre, mai sul TF nativo — su 32/32 trade SAR non aveva mai scartato nulla perché guardava il TF sbagliato). Classificazione: **concettualmente valido**, implementazione **legacy/fragile** (liste hardcoded, non derivate dall'evidenza di `TRADING_EDGE_STATUS_RECONCILIATION_V1.md` — es. MALAYSIAN_SNR è in lista mean-reversion qui, ma non è mai stato validato come tale in nessuna decision card).

## 8. Strategy identity / enum usage

**Buona notizia, confermata:** l'intero motore (`_nxs_inst_family`, `_nxs_regime_veto`, la firma `group`) lavora su `stratName` (stringa), **mai** sull'enum `s.strat` — coerente col fatto che `NXS_StratStats.mqh` è anch'esso name-keyed (`STRATEGY_IDENTITY_ATTRIBUTION_PREAUDIT_V1.md` §1). Il motore istituzionale **non eredita** il rischio di attribuzione dell'enum. Il suo OUTPUT (`isig`) viene però taggato `STRAT_STRUCT_REACT` per costruzione — bucket generico, già noto.

## 9. Shared primitive double-counting risk

**Scoperta non richiesta ma concreta e nuova:** `NXS_ApplyContextQuality` applica un veto MTF generico (`g_ctx.htfBias` deve concordare, salvo reversal confermato) **a tutti i contributori**, incluso qualunque voto di ORDER_BLOCK o FVG_CONT. Ma ORDER_BLOCK e FVG_CONT **già applicano lo stesso controllo individualmente dentro la propria funzione** (`g_structH1.trend`, trovato in `UNIFIED_COMPONENT_CATALOG_V1.md`). **Quando il Modello Istituzionale è attivo, questo controllo viene applicato due volte** sulla stessa informazione (una volta dentro la strategia, una volta nel layer di qualità) — non double-counting di *evidenza* nel senso stretto (non gonfia la conviction, è un veto booleano ridondante, non un addendo), ma è uno spreco/duplicazione di logica che vale la pena notare per Codex.

## 10. Timeframe/context dependencies

- `g_ctx` è calcolato una volta per tick (non per-TF), a differenza delle strategie singole che spesso dichiarano il proprio TF (`NXS_Profile_TF`). Questo significa che il Modello Istituzionale valuta il contesto **sempre sullo stesso TF**, indipendentemente dal TF nativo del contributore — **stesso tipo di bug già risolto per il regime veto** (TF sbagliato, fix documentato), ma non verificato qui se `g_ctx` stesso soffra di un problema analogo per i suoi 8 componenti (non approfondito, gap residuo).
- Il tier (`_nxs_inst_tier`) usa un TF derivato dal numero di concetti allineati (0-3 → TF_entry/H1/H4/D1), **un meccanismo di temporal logic indipendente** da quello di `market_ontology.md` — un quarto schema temporale nel progetto, da riconciliare anch'esso.

## 11. Runtime side effects

Nessuno oltre al calcolo della decisione stessa — `NXS_Institutional_Decide` è una funzione pura rispetto allo stato globale (legge `g_ctx`/`g_atr`, non scrive stato persistente). **Non soffre quindi della classe di defect `CROSS_TIMEFRAME_STATE_CONTAMINATION`** (nessuno stato mutato tra chiamate).

## 12. Risk/execution coupling — il punto più delicato per il design futuro

**Qui il motore NON rispetta il confine Market Intelligence / Risk Engine di `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` §9.** `NXS_Institutional_Decide` calcola direttamente `entryRef`, `slPrice`, `tpPrice` (ATR × `InpInstBaseSL/TP` × moltiplicatore di tier, con allargamento condizionale fino a `InpInstMaxSLwiden`×) — **dentro la stessa funzione che aggrega l'evidenza**. Non produce un `Signal` puro (ontologia Phase 4) che poi un Risk Model separato trasforma in Entry/Stop — calcola già SL/TP lui stesso. Il chiamante (`NEXUS_EA_v2.mq5:1448-1462`) poi passa comunque per `NXS_Prot_EntryBlocked()`/`NXS_SpreadOK()` prima di aprire — quindi **il gate di sicurezza finale non è bypassato** — ma il confine concettuale Intelligence/Risk è già sfumato in questo codice legacy. Classificazione: **non pericoloso** (i gate finali esistono comunque), ma **un pattern da non replicare** nel nuovo design — esattamente il motivo per cui §9 dell'architettura insiste sulla separazione netta.

---

## Verdetti espliciti richiesti

**Cosa è concettualmente valido:**
- Il principio di decorrelazione per famiglia prima di sommare (`AUD0-INST-010`) — anticipa correttamente il problema centrale di tutto questo filone di lavoro.
- Il veto di regime per-strategia calcolato sul TF nativo (dopo il fix) — prototipo diretto di habitat-matching.
- La separazione fisica pre-aggregazione (qualità/veti) vs aggregazione (grouping/netting) vs output (decisione) — una buona separazione di stadi, nello spirito (anche se non nella forma esatta) della richiesta anti-circolarità di `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` §12-bis.

**Cosa è legacy/fragile:**
- I pesi di `NXS_Context_DirectionalScore` (hardcoded, nessuna evidenza di calibrazione citata — unico punto del codice NEXUS senza quella disciplina).
- Il classificatore di famiglia per substring-match sul nome (funziona per coincidenza semantica del naming, non per relazione di codice verificata — avrebbe perso ORDER_BLOCK↔OB_MIT come relazione forte).
- Le liste hardcoded di `_nxs_regime_veto` (mai derivate dalle decision card reali di `TRADING_EDGE_STATUS_RECONCILIATION_V1.md`).
- Nessuna distinzione tra "conflitto rilevato" e "silenzio del mercato" (§6) — problema di explainability.

**Cosa è pericoloso:** Nulla di attivo — il motore è `OFF` di default e i gate di sicurezza finali (`NXS_Prot_EntryBlocked`) restano comunque nel percorso. Il coupling Intelligence/Risk (§12) non è pericoloso oggi, ma **sarebbe** un pattern pericoloso da copiare in un sistema futuro con più capitale/autonomia.

**Cosa può essere estratto come primitive riusabile:**
- `_nxs_inst_family` → base di partenza (da sostituire con relazioni verificate da codice, non substring) per la deduplicazione di `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md`.
- Il meccanismo di peso decrescente per contributi correlati (`1/(n+1)`) → un punto di partenza semplice e già testato per l'opzione "weighted evidence" di `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` §4, da NON scartare solo perché "legacy" — è un'euristica onesta, dichiarata come tale.
- `g_ctx` come lista delle 8 dimensioni di contesto effettivamente già calcolate e disponibili live — utile come checklist di cosa esiste già operativamente, anche se va riconciliato con gli altri 2 schemi di regime/contesto del progetto.

**Adattabilità a `market state → components → deduplicated evidence → unified view`:** **Parziale.** Il motore oggi è `signal → grouping (con decorrelazione debole) → decision con SL/TP`, cioè opera un gradino più a valle di dove serve al nuovo design (dopo il Trigger, non al livello di Component/Event). Per riusarlo davvero nel nuovo schema andrebbe: (a) spostare la decorrelazione di famiglia da "nome strategia" a "componente canonico" (usando `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md` invece di `_nxs_inst_family`); (b) separare il calcolo di SL/TP (Risk Model) dalla decisione di direzione/conviction (Decision Layer); (c) riconciliare i 3-4 schemi di contesto/regime/tempo paralleli trovati in questo audit prima di fidarsi di uno qualunque come "il" context vector.

---

## Confronto con i 4 documenti esistenti

| Documento | Relazione |
|---|---|
| `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` | §4 (evidence aggregation): l'opzione "weighted evidence" esiste già in produzione (§3 qui), non calibrata. §9 (safety boundary): il motore viola parzialmente la separazione proposta (§12 qui) — buon argomento a favore di renderla esplicita nel design, non opzionale. §5 (conflict resolution): il motore fa solo netting, non la tipologia a 3 casi proposta — nessuna sovrapposizione diretta, spazio libero per il nuovo design. |
| `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md` | §6 (phenomenon collapse): `_nxs_inst_family` è un secondo schema di macro-fenomeni, parzialmente sovrapposto ma non identico al mio — da riconciliare, non da scegliere arbitrariamente uno dei due. |
| `COMPONENT_COLLAPSE_HIGH_VALUE_VERIFICATION_V1.md` | Il motore istituzionale classifica ORDER_BLOCK e OB_MIT nella stessa famiglia (STRUCTURE) per coincidenza di nome, non perché sappia che condividono stato — stesso esito, motivazione diversa e più debole. |
| `STRATEGY_IDENTITY_ATTRIBUTION_PREAUDIT_V1.md` | Confermato: il motore istituzionale non usa l'enum `strat`, solo `stratName` — non eredita il rischio di attribuzione. Il suo output sì (`STRAT_STRUCT_REACT`), consistente col resto del censimento. |

---

## Gap non risolti in questo audit

- Non verificato se `g_ctx` stesso soffra di un problema di TF analogo a quello già fixato per `_nxs_regime_veto` (calcolato una volta per tick, non per-TF-del-contributore).
- Non verificato se `InpUseInstitutionalCore` sia mai stato attivato in un test reale/demo (il codice è presente e commentato con cura, ma non ho trovato nota vault di un backtest/demo con questo flag ON durante questo audit — non cercato esaustivamente, fuori scope).
- Non quantificato l'impatto pratico del doppio veto MTF ridondante di §9 (probabilmente nullo sul risultato finale, visto che è un AND di condizioni equivalenti, ma non verificato formalmente).

---

## Vincoli rispettati

Nessuna modifica a codice. Nessun backtest. Nessun commit/push.

INSTITUTIONAL_DECISION_ENGINE_FORENSIC_AUDIT_V1_READY_FOR_REVIEW
