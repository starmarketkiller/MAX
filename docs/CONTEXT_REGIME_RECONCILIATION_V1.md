# Context/Regime Reconciliation V1

**Stato:** riconciliazione concettuale, non committata. Nessuna modifica a codice, nessun backtest di performance, nessun commit/push. Tutto CODE_VERIFIED: letto `server/research_scripts/phase5_5/build_regime_layer.py` (Phase 4/5.5, completo), `server/research_scripts/phase7/phase7_27/nxs_regime_classifier.py` (Phase 7.27, completo), `MQL5/Include/NEXUS_v1/NXS_MarketContext.mqh` (completo, struct `SNXSContext` + `NXS_Context_Update` + `NXS_Context_DirectionalScore`), più la definizione di `g_struct.trend` (`NXS_Structure.mqh`/`NXS_StructureMultiLayer.mqh`).

## 0. Correzione concettuale necessaria prima della matrice

**`g_ctx` non è un classificatore di regime nello stesso senso degli altri due.** Phase 4/5.5 e Phase 7.27 producono entrambi un'**etichetta categorica descrittiva, indipendente da qualunque direzione di trade candidata** ("che tipo di mercato è questo, a prescindere da cosa vorrei fare"). `g_ctx`/`NXS_Context_DirectionalScore` produce invece un **punteggio continuo, segnato per una direzione specifica già proposta da una strategia** ("quanto il mercato attuale confirma QUESTA direzione"). Non sono tre implementazioni della stessa cosa — sono due classificatori di regime (da riconciliare tra loro) più un aggregatore di confluenza direzionale che **consuma** alcuni ingredienti regime-simili (`htfBias`, `structTrend`) insieme a evidenza di evento/componente (sweep, zone, reazione) in un unico score, senza separare i due livelli. Questa conflazione è di per sé un gap architetturale rilevante per il punto 2 della sequenza data dall'utente (Canonical Component Identity), non solo per questo task.

## 1. Matrice CANONICAL_DIMENSION → Phase4/5.5 → Phase7.27 → g_ctx

| Dimensione canonica | Phase 4/5.5 | Phase 7.27 | g_ctx (runtime) |
|---|---|---|---|
| **Trend/direzione** | `directional_efficiency` (tercile) — parte della definizione di regime, non isolata | `sma50_slope` (UP/DOWN/FLAT, soglia ±0.1% su 5 barre) — classificazione indipendente | `structTrend` (`g_struct.trend`, break-of-structure su swing high/low, +1/-1/0) |
| **Volatilità** | `atr_percentile` (tercile, priorità massima: HIGH_VOL/LOW_VOL dominano sempre) | `atr14` (tercile LOW/MED/HIGH) | **Assente come dimensione propria** — `g_atr` usato solo per tolleranze/SL, non come stato di contesto |
| **"Freschezza" del trend** | `trend_persistence_bars` (soglia ≤2 barre → TRANSITION, priorità sopra TRENDING/RANGING) | Assente | Assente |
| **Bias di lungo periodo (HTF)** | Assente come dimensione propria (solo implicito in directional_efficiency) | `price_above_htf_sma200` (bool, SMA200) | `htfBias` (da un modulo HTF separato, non letto in questo task — presumibilmente simile) |
| **Struttura (BOS/CHoCH)** | Assente | Assente | `bosDir`, `chochDir` (da `g_struct`, stesso modulo swing di `structTrend`) |
| **Liquidity event (sweep)** | Assente (è un Event, non un Context, nell'ontologia Phase 4) | Assente | `sweepDir` (solo se confermato) |
| **Location (zona FVG/OB attiva)** | Assente | Assente | `zoneDir` (prossimità ATR-scalata) |
| **Reazione/confluenza** | Assente | Assente | `reactionDir` × `reactionQ` |
| **AMD (manipulation/distribution)** | Assente | Assente | `amdActive` (bool, non direzionale) |
| **Sessione/ora** | `hour_utc`, `day_of_week` presenti nel Market State Vector (Phase 4) ma **non usati nella classificazione di regime** — solo "KEEP_FOR_INTERPRETABILITY" (`feature_redundancy_audit_v1.md`) | Esplicitamente `NOT_APPLICABLE` (serie D1, nessun concetto di sessione infra-day) | Assente come dimensione esplicita (nessun campo sessione in `SNXSContext`) |
| **Anno/periodo calendariale** | Assente dalla classificazione di regime (presente come colonna nel dataset, non nel regime) | `year` — esplicitamente escluso dalla chiave di matching stretto, riportato solo come covariata descrittiva | Assente |
| **Timeframe operativo** | H4 (4809 barre, Dukascopy) | D1 (serie giornaliera) | Tick-by-tick, ricalcolato ogni `OnTick`, non ancorato a un singolo TF dichiarato |
| **Output** | 1 variabile categorica, 5 stati, **priorità dichiarata esplicitamente** (non assi ortogonali) | 2 variabili categoriche indipendenti (trend × vol_tercile), combinate in una chiave di matching | 1 score continuo per direzione, somma pesata di 8 contributi |
| **Causal safety** | Dichiarata esplicitamente: soglie calibrate SOLO su finestra discovery, observation point = bar_close | Dichiarata esplicitamente: valore causale punto-per-punto, bordi tercile su intera distribuzione (limite dichiarato, non leakage sul prezzo) | Non dichiarata esplicitamente nel codice — non verificato in questo task se `g_ctx` soffra di leakage, solo verificato che non soffre dello stesso bug di TF-sbagliato già fixato per `_nxs_regime_veto` (non verificato nemmeno questo, gap residuo) |
| **Uso dichiarato** | **Esplicitamente NON un segnale di trading** (`is_a_trading_signal: false`) — solo stratificazione descrittiva per il Probability Engine | Covariata di matching per un benchmark causale (Phase 7.27, BUY-dominance) — research, non runtime | **È** direttamente un moltiplicatore di score usato per decidere se aprire un trade — runtime, non research |
| **Pesi hardcoded** | Nessuno (soglie da tercili calcolati sui dati, non scelte a mano) | Nessuno (terzili calcolati sui dati) | **Sì** — `InpCtxW_*` (HTF=8.0, Struct=5.0, BOS=4.0, CHoCH=4.0, React=10.0, Sweep=6.0, Zone=5.0, AMD=3.0), nessuna provenance sperimentale trovata (`INSTITUTIONAL_DECISION_ENGINE_FORENSIC_AUDIT_V1.md` §3) |

## 2. Equivalenze trovate (stesso concetto, formula diversa — non ancora verificate come numericamente equivalenti)

- **Trend/direzione**: 3 metodologie genuinamente diverse per lo stesso concetto — pendenza SMA50 (Phase 7.27), efficienza direzionale/tercile (Phase 4/5.5), rottura di struttura su swing (g_ctx). **Nessuna delle tre è ridondante per costruzione** — sono approcci metodologicamente distinti (moving-average-based vs efficiency-based vs price-structure-based), non la stessa formula rinominata. Si aggiunge ai 3 proxy già trovati a livello di STRATEGIA in `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md` (ADX_RSI/MACD/SAR) — **ora sono 6 implementazioni indipendenti del concetto "trend" nel progetto, su 2 livelli diversi (strategia e contesto)**, mai confrontate tra loro.
- **Bias di lungo periodo**: `price_above_htf_sma200` (Phase 7.27) concettualmente identico a `ema200_trend_filter` trovato dentro `NXS_Strat_MACD` (`UNIFIED_COMPONENT_CATALOG_V1.md`) e probabilmente a `htfBias` di g_ctx (modulo non letto in questo task, verifica da fare). **Il candidato più forte di vera ridondanza** tra i tre sistemi — stesso identico test (prezzo vs media mobile di lungo periodo), implementato almeno 2-3 volte indipendentemente.
- **Volatilità**: ATR su finestre diverse (14 vs implicito in Phase 4's ATR percentile) — stesso indicatore di base, timeframe diverso (D1 vs H4), non verificato se producono classificazioni coerenti sulle stesse date.

## 3. Contraddizioni

**Nessuna contraddizione logica diretta trovata** — i tre sistemi non fanno mai affermazioni opposte sulla stessa barra nello stesso momento, perché operano su timeframe diversi (H4 vs D1 vs tick-live) e nessuno è mai stato eseguito sullo stesso dataset per un confronto diretto. **Questo è esso stesso un gap, non una rassicurazione**: non sapere se contraddicono non è lo stesso che sapere che non contraddicono. Non verificato in questo task (richiederebbe eseguire tutti e 3 sullo stesso storico — fuori scope, sarebbe un test di performance).

## 4. Ridondanze / doppio-veto trovate (stessa informazione usata più volte)

1. **Già noto** (`INSTITUTIONAL_DECISION_ENGINE_FORENSIC_AUDIT_V1.md` §9): ORDER_BLOCK e FVG_CONT verificano `g_structH1.trend` dentro la propria funzione; se il Modello Istituzionale è attivo, `NXS_ApplyContextQuality` riverifica l'accordo con `g_ctx.htfBias` genericamente su tutti i contributori, inclusi loro due — stessa famiglia di informazione (bias di tendenza superiore), verificata due volte con fonti diverse (`g_structH1.trend` vs `g_ctx.htfBias`, moduli probabilmente diversi).
2. **Nuova in questo task**: `NXS_Strat_ADXRSI()` scarta il proprio segnale se `g_adx < 20.0` (gate locale, proprio ADX). `_nxs_regime_veto()` (quando attivo) scarta lo stesso segnale se il regime calcolato con `NXS_DetectRegimeTF` sullo stesso TF risulta RANGING o CHOPPY — e quella funzione calcola il regime usando **lo stesso identico ADX** (`NXS_ADXv`) sullo stesso TF, con una soglia diversa (ADX≥30/20/15 per i bucket di regime). Sono due soglie diverse sulla stessa identica misura, applicate in due punti diversi della pipeline — non necessariamente un errore, ma un caso concreto di "stessa evidenza usata due volte con criteri scoordinati" da tenere a mente nel futuro schema `component_id`/`source_primitive` proposto dall'utente.

## 5. Cosa può essere unificato

- **Bias di lungo periodo** (§2): i 2-3 test "prezzo vs media mobile lunga" sono il candidato più pulito per una vera unificazione — stesso fenomeno, probabilmente la stessa formula con solo il periodo/tipo di media diverso. Andrebbe verificato (non fatto qui) se producono lo stesso segno sulle stesse barre prima di deciderlo definitivamente, ma è il caso con la probabilità più alta di collassare a 1 solo componente canonico.
- **Volatilità**: i due calcoli ATR-based (Phase 4/5.5 H4, Phase 7.27 D1) potrebbero condividere la stessa implementazione di base (ATR a finestra + tercile), parametrizzata per timeframe, invece di due script indipendenti.

## 6. Cosa deve restare distinto

- **Trend**: le 3 (o 6, contando il livello strategia) metodologie non vanno fuse in una — sono ipotesi metodologiche diverse e genuinamente informative da confrontare empiricamente (quale predice meglio?), non da collassare a priori. Fonderle prematuramente eliminerebbe l'opportunità di scoprire quale definizione di trend è più utile.
- **Context (stato lento: trend/HTF/regime) vs Event/Component evidence (stato rapido: sweep/zona/reazione)**: per costruzione dell'ontologia Phase 4 (`market_ontology.md`), questi sono due livelli diversi (Context vs Event) che `g_ctx` conflaziona in un solo score. Il futuro Unified Engine deve tenerli separati — è esattamente coerente con lo schema `component_id`/`source_primitive`/`phenomenon_id`/`dependency_cluster` proposto dall'utente.
- **Research (Phase 4/5.5, Phase 7.27) vs runtime (g_ctx)**: scopi diversi (stratificazione descrittiva per audit scientifico vs scoring live per apertura trade) — non vanno fusi in un'unica implementazione, ma il runtime dovrebbe eventualmente essere validato CONTRO la metodologia research, non l'inverso.

## 7. Cosa è legacy

- I pesi `InpCtxW_*` di `g_ctx` (nessuna provenance, già segnalato nell'audit precedente).
- Le liste hardcoded di `_nxs_regime_veto` (mean-reversion/trend-follow per nome, mai derivate da `TRADING_EDGE_STATUS_RECONCILIATION_V1.md`).
- L'assenza di una dimensione di volatilità in `g_ctx` — dato che sia Phase 4/5.5 sia Phase 7.27 la trattano come la dimensione a **priorità più alta** (Phase 4/5.5: HIGH_VOL/LOW_VOL dominano sempre la classificazione), la sua assenza nel runtime è probabilmente il gap più consequenziale trovato in questo documento.

## 8. Cosa richiede calibrazione

- Tutti i pesi `InpCtxW_*` — da trattare esplicitamente come **UNVALIDATED_PRIOR** (linguaggio dell'utente), utilizzabili solo come baseline shadow da battere, mai come verità.
- Le soglie di `_nxs_regime_veto` (ADX 20/30/15, soglia volatilità 1.5×) — stesso trattamento.

## 9. Dimensioni sufficienti per Unified Market Intelligence V1 (proposta, non decisione)

Sulla base di questa riconciliazione, l'insieme minimo di dimensioni di contesto che meritano di entrare in `CONTEXTUAL_EDGE_DISCOVERY_V1` prima di qualunque altra: **trend** (una metodologia da scegliere o testare comparativamente, non tutte e 3 subito), **volatilità** (tercile ATR, già 2 implementazioni pronte da riconciliare), **bias HTF** (il candidato di unificazione più pulito). Sessione/ora resta un candidato plausibile (già usato operativamente da strategie reali: JUDAS_SWING/NY_REVERSAL/LONDON_BO) ma **non modellato da nessuno dei 3 sistemi come dimensione di regime** — gap aperto, non chiuso da questa riconciliazione. Struttura/BOS/CHoCH/sweep/zona/reazione restano a livello di Event/Component (non Context) per coerenza con §6.

## 10. Gap non risolti in questo task

- Non verificato se `g_ctx.htfBias` (modulo HTF non letto) sia davvero la stessa formula di `price_above_htf_sma200` (Phase 7.27) o una terza variante — solo ipotizzato per nome/posizione concettuale.
- Non eseguito nessun confronto numerico diretto (stesse date, stesso simbolo) tra i 3 sistemi — la sezione 3 (contraddizioni) resta "nessuna trovata" solo perché nessuna è stata cercata empiricamente, non perché verificata assente.
- Non verificato se `g_ctx` soffra di un bug di timeframe analogo a quello già fixato in `_nxs_regime_veto` (calcolato una volta per tick su un TF implicito, non per-TF-del-contributore) — segnalato come gap nell'audit precedente, ancora aperto qui.

---

## Vincoli rispettati

Nessuna modifica a codice. Nessun backtest di performance. Nessun commit/push. Nessuna scelta del "migliore" tra i 3 sistemi sulla base di risultati di trading (non ne sono stati eseguiti).

CONTEXT_REGIME_RECONCILIATION_V1_READY_FOR_REVIEW
