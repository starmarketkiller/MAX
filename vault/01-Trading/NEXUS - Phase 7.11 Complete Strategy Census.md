# NEXUS - Phase 7.11 Complete Strategy Census

**Baseline:** `cddf8a929f3bfc259fd1a56ee454d9c8f6508798` (Phase 7.10). Nessuna correzione, nessun ri-test, nessuna modifica a strategie in questa fase — solo censimento strutturale. Nessun dataset economico costruito. Il lavoro su `BREAKOUT_ACC_INTENDED_D1_V1` resta sospeso fino al completamento di questa fase.

**Motivazione:** prima di estendere qualunque audit di integrità (CROSS_TIMEFRAME_STATE_CONTAMINATION o altro) oltre le 20 strategie stateful già trovate in 7.10, verificare che l'universo di riferimento sia completo — non assumere che il registro combinato attuale (`contracts/strategy-registry.json`, 83 identità) rappresenti tutte le strategie mai esistite nel progetto.

---

## Metodo

Scansionate 11 fonti indipendenti (elenco completo in `census_rows[].sources_scanned` dell'artifact): registro combinato, `knowledge/strategy_database.json`, `NXS_StrategyRegistry.mqh`, `NXS_StrategyProfiles.mqh`, i 4 file `NXS_Strategies*.mqh`, `NXS_ReusePerformancePack.mqh` (motore NXR), `server/backtest.py` (dispatch + 71 funzioni `sig_*`), 39 file di `vault/01-Trading/Strategie/`, il documento di architettura pre-esistente, `contracts/generate_registry.py` (PROXY_MAP/ALIASES), e le classificazioni già note di Phase 7.10.

Per ogni identità: `canonical_strategy_id, aliases, variant_of, first_seen, last_seen, current_status, live_mql5, python_implementation, vault_documentation, registry_presence (per-fonte), profile_presence, selector_presence, stateful, canonical_tf, historical_tests, known_parity_status, known_implementation_defects, evidence_status, lineage_notes`.

**Regole applicate rigorosamente**: nessuna fusione per somiglianza di nome; nessuna separazione di identità senza prova nel codice; ogni discrepanza di conteggio fra fonti spiegata esplicitamente, non ignorata.

---

## Output 1 — Totale identità uniche

**83.** Coincide numericamente con `contracts/strategy-registry.json`, ma con una correzione sostanziale sul lato live (vedi Output 2 e sezione "Scoperta principale").

## Output 2 — Conteggio per categoria

| Categoria | N |
|---|---|
| **live** (implementazione MQL5 reale, raggiungibile dal router) | **55** *(corretto — il registro ne dichiara 53)* |
| research (implementazione Python in `backtest.py`) | 68 |
| legacy/deprecated (`current_status == DISABLED`) | 22 |
| alias (identità con almeno un alias noto) | 6 |
| partial (presente solo lato live O solo lato research, non entrambi) | 43 |
| never fully implemented | 3 |

**Le 3 "never fully implemented"**: `CRT`, `FVG_MIT_WINDOW` (entrambe hanno codice MQL5 reale e raggiungibile ma sono strutturalmente bloccate — vedi sotto), e `sig_breakout` lato Python (mai stata un'identità propria, era un proxy condiviso storico per 3 strategie prima che ciascuna ricevesse codice dedicato).

## Output 3 — Mappa lineage/varianti

Costruita in `census_summary_v1.json → output_3_lineage_variant_map`. Famiglia principale: suffisso **`_NXR`** (5 alias: IFVG_NXR, FVG_MIT_NXR, OB_MIT_NXR, MALAYSIAN_SNR_NXR, STRUCT_REACT_NXR — canonicalizzati da `NXS_StrategyCanonicalId()` rimuovendo il suffisso), più `CISD → THREE_BAR_DELIVERY_BREAK` (alias dichiarato in `RESEARCH_ALIASES` di `backtest.py`). Nessuna catena di varianti `_V2/_TRUE/_STAGE*/_EXT/_PINE/_CONFIRMED` risulta collegata a un'identità canonica diversa da sé stessa per prova diretta nel codice — dove tali suffissi esistono (es. le versioni "_ext" pre-esistenti di `sig_fvg_cont`/`sig_liq_sweep`/`sig_ob_mit`/`sig_order_block`), sono trattate come *implementazioni superate della stessa identità*, non come identità figlie separate, perché il dispatch attuale in `STRATEGIES` punta a una sola versione per nome.

## Output 4 — Presenza in una fonte ma assenza nelle altre

Matrice completa in `census_summary_v1.json → output_4_source_presence_discrepancies`. Casi più significativi:

- **CRT, FVG_MIT_WINDOW**: presenti (codice reale, raggiungibile, selettore dedicato) in `NXS_Strategies_SMC.mqh` + chiamate verificate in `NEXUS_EA_v2.mq5`, ma **assenti** da `NXS_StrategyKnown()`/`NXS_StrategyIdAt()` (`NXS_StrategyRegistry.mqh`) e di conseguenza da `contracts/strategy-registry.json` (che le marca erroneamente `live_implementation: false`).
- Le 5 funzioni `NXR_Strat_*` (motore NXR): definite in `NXS_ReusePerformancePack.mqh`, ma **zero call site verificati** in tutto l'albero MQL5 — presenti come codice, assenti come comportamento runtime.
- 5 funzioni Python `sig_*` orfane: definite in `backtest.py` ma mai referenziate nel dizionario `STRATEGIES` — presenti come codice, assenti dal dispatch.

## Output 5 — Possibilmente escluse da audit precedenti

1. **CRT** — un audit basato solo sulla lista dei 53 nomi noti del registro l'avrebbe saltata (Phase 7.10 non l'ha saltata perché ha scansionato `NXS_Strategies*.mqh` direttamente, non il registro).
2. **FVG_MIT_WINDOW** — stesso motivo; inoltre **default `InpStrat_FVG_MIT_WINDOW = true`** (abilitata di default), quindi il rischio pratico è più alto di CRT (default `false`).
3. **Il motore NXR (IFVG/FVG_MIT/OB_MIT/MALAYSIAN_SNR)** — mai scansionato da Phase 7.10 (che ha guardato solo `NXS_Strategies*.mqh`, non `NXS_ReusePerformancePack.mqh`). Se le funzioni `NXR_Strat_*` fossero davvero raggiungibili (non confermato — 0 call site trovati in questo census), sarebbero candidate non ancora auditate per CROSS_TIMEFRAME_STATE_CONTAMINATION.
4. **OB_MIT** — mai auditata separatamente da ORDER_BLOCK perché assunta "la stessa cosa"; in realtà ha proprio `stratName`/selettore/stato derivato indipendentemente a runtime.

## Output 6 — Candidate aggiuntive per failure pattern

- **`CROSS_STRATEGY_STATE_SHARING`** (nuovo, distinto da CROSS_TIMEFRAME_STATE_CONTAMINATION): ORDER_BLOCK e OB_MIT chiamano **entrambi** `NXS_OB_UpdateSide()` sugli **stessi** globali `g_obBuy`/`g_obSell` — verificato: nessuna istanza separata per OB_MIT. Se entrambe abilitate simultaneamente potrebbero corrompersi a vicenda lo stato, indipendentemente da qualunque problema di timeframe. **NOT_ENOUGH_EVIDENCE** per l'impatto pratico — richiederebbe la stessa metodologia sperimentale di 7.9E/F, non eseguita qui.
- **`UNKNOWN_STRATEGY_REGISTRY_GAP`** (nuovo, non è cross-TF contamination ma un pattern di rischio strutturale altrettanto silenzioso): un segnale generato correttamente viene **sempre rifiutato** da un gate di sicurezza indipendente (`NXS_StrategyKnown()`, chiamato da `NXS_OpenTrade()`) perché il registro non riconosce l'identità — zero trade garantiti a prescindere dalla qualità del segnale, indistinguibile da "nessun edge" senza ispezionare il codice. Trovato per **CRT** e **FVG_MIT_WINDOW** (quest'ultima default enabled → severità alta).

---

## Scoperta principale: il conteggio "live" del registro è sottostimato (53 → 55)

**Verificato direttamente sul codice sorgente attuale, non assunto dal registro stesso.** `NXS_Strat_CRT()` e `NXS_Strat_FVG_Mitigation_Window()` esistono in `NXS_Strategies_SMC.mqh`, sono chiamate da `NEXUS_EA_v2.mq5`, hanno un proprio indice di selettore (38 e 39 rispettivamente) e i propri input di attivazione (`InpUseStrat_CRT`, `InpStrat_FVG_MIT_WINDOW`) — sono codice vivo e raggiungibile dal router. Ma **entrambe sono assenti** da `NXS_StrategyKnown()` in `NXS_StrategyRegistry.mqh`, il file dichiarato "Generated by contracts/generate_registry.py. Do not edit." — non rigenerato dopo l'aggiunta di queste due strategie, o il generatore non le include per un motivo non verificato in questa fase.

**Conseguenza pratica**: qualunque segnale che una di queste due funzioni generasse verrebbe **sempre e strutturalmente rifiutato** da `NXS_OpenTrade()` tramite il gate `unknown_strategy` — un blocco silenzioso, totale, indistinguibile da "nessun edge" senza ispezionare il codice. Per FVG_MIT_WINDOW, abilitata di default, questo significa che la strategia genera segnali (verificabile via trace) ma **non ha mai potuto aprire un trade reale**, in nessun momento della sua esistenza nel codice.

Questo è stato nominato **`UNKNOWN_STRATEGY_REGISTRY_GAP`** — un pattern distinto da CROSS_TIMEFRAME_STATE_CONTAMINATION: non è uno stato che si contamina fra pass, è un'identità che il gate di sicurezza non riconosce affatto.

## Correzione documentale: motore "NXR" non ha call site verificati

Una nota di documentazione preesistente nel vault affermava che il motore NXR "esegue realmente trade live" per 4 identità (IFVG/FVG_MIT/OB_MIT/MALAYSIAN_SNR con suffisso `_NXR`). Verificato contro il codice attuale: le funzioni `NXR_Strat_IFVG_Reversal/FVG_Mitigation/OB_Mitigation/MalaysianSNR` esistono in `NXS_ReusePerformancePack.mqh` ma hanno **zero occorrenze di chiamata** in tutto l'albero MQL5 (solo la propria definizione). Questa è dichiarata una **correzione verificata** a documentazione obsoleta — non un'affermazione di certezza nella direzione opposta: resta `NOT_ENOUGH_EVIDENCE` per una risoluzione completa (potrebbe esistere un percorso di chiamata dinamico/indiretto non rilevabile per grep testuale).

## Staleness di `PROXY_MAP` in `contracts/generate_registry.py`

Il `PROXY_MAP` hardcoded (non derivato dinamicamente) risulta stale per 4 delle 6 voci: `LONDON_BO`, `WEEKLY_EXP`, `SH_BMS_RTO`, `SMS_BMS_RTO` hanno ricevuto implementazioni dedicate in data "04/08" (per commento datato nel codice), mai riflesse nel `PROXY_MAP`. Non corretto in questa fase (fuori scope — solo censimento).

---

## Spiegazione esplicita delle discrepanze di conteggio fra fonti

| Fonte | Conteggio | Perché differisce |
|---|---|---|
| `knowledge/strategy_database.json` | 53 (solo live) | Fonte primaria da cui il registro combinato deriva i 53 "live" dichiarati, poi arricchita con i 30 research-only trovati in `backtest.py` per arrivare a 83 totali. |
| `NXS_StrategyKnown()`/`NXS_StrategyIdAt()` | 53, concordi fra loro | Stesso file, probabilmente stesso processo di generazione — concordano fra loro ma **non con la realtà del codice**: CRT e FVG_MIT_WINDOW hanno funzioni reali e raggiungibili ma non sono in questa lista. |
| `contracts/strategy-registry.json` | `live_implementation: false` per CRT/FVG_MIT_WINDOW | Il generatore deriva presumibilmente questo campo dalla stessa fonte di `NXS_StrategyKnown()` invece di scansionare direttamente il codice sorgente delle funzioni `NXS_Strat_*` — stessa causa radice del punto precedente. |
| **Questo census** | **55 live** | Corretto scansionando direttamente `NXS_Strategies*.mqh` + le chiamate reali in `NEXUS_EA_v2.mq5`, non il registro derivato. |

---

## Deliverables

`complete_strategy_census_v1.json` (83 righe, 18+ campi ciascuna), `census_summary_v1.json` (i 6 output richiesti + spiegazione discrepanze), 2 builder (`build_complete_strategy_census.py`, `build_census_summary.py`), verificatore indipendente (`verify_complete_strategy_census.py` — ri-deriva entrambi gli artifact dai builder E ri-verifica da zero sul codice sorgente attuale l'assenza di CRT/FVG_MIT_WINDOW da `NXS_StrategyKnown()`, la raggiungibilità delle loro funzioni, gli zero call site NXR, e che nessun file MQL5/Python sia stato toccato in questa fase), 17 test di consistenza (`test_phase_7_11.py`, 17/17 PASS), questo vault report.

## Vincoli preservati

Nessuna strategia corretta o ri-testata in questa fase (istruzione esplicita dell'utente). `VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti. `HISTORICAL_VOLUME_CONTRACT_WALLS` resta solo backlog. Le 10 strategie DEFECT_CONFIRMED rimanenti da Phase 7.10 restano non corrette. Nessun artifact storico cancellato o sovrascritto.

## Prossima singola task

Riprendere `BUILD_CANONICAL_BREAKOUT_ACC_DATASET` (Phase 7.9H) esattamente come specificato dall'utente prima dell'interruzione — ora con l'universo completo delle identità stabilito. `CRT`, `FVG_MIT_WINDOW` e il pattern `UNKNOWN_STRATEGY_REGISTRY_GAP`/`CROSS_STRATEGY_STATE_SHARING` restano backlog esplicitamente non prioritario, nessuno dei due blocca il percorso BREAKOUT_ACC.

## Regressione

- **Suite propria 7.11 (pytest)**: 17/17 PASS
- **Suite pytest Phase 7 totale** (7.1→7.9G + 7.10 + 7.11, tutti i file `test_*.py` raccolti automaticamente da pytest): **254/254 PASS, 0 fallimenti**
- **4 suite standalone pre-esistenti** (script eseguiti direttamente via `python`, non raccolte da pytest — fasi 7.8E/7.8H/7.8I/7.9B usano un runner proprio con `main()`), fallimenti **noti, invariati, non regressioni**, stessa causa già documentata in 7.10:
  - `phase7_8e`: 68/72 PASS (4 FAIL) — causa nota: confronto whole-file-hash legacy.
  - `phase7_8h`: 18/21 PASS (3 FAIL) — causa nota: riferimento a binario EX5 non aggiornato.
  - `phase7_8i`: 22/23 PASS (1 FAIL) — causa nota: verifica `NXS_Strategies.mqh` contro un hash congelato **prima** del fix 7.9G.
  - `phase7_9b`: 31/33 PASS (2 FAIL) — stessa causa di 7.8I (hash frozen pre-fix).

Nessun fallimento nuovo introdotto da questa fase. I 2 artifact `phase7_9c/breakout_acc_*_event_stream_v1.json` hanno subito l'effetto collaterale noto (timestamp `generated_at` toccato dall'esecuzione della suite, hash canonico invariato) e sono stati ripristinati con `git checkout --` prima del commit.

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.11: COMPLETATA ✓
CENSUS: 83 identita' uniche totali (55 live [corretto da 53], 68
        research, 22 legacy/deprecated, 6 alias, 43 partial, 3 never
        fully implemented: CRT, FVG_MIT_WINDOW, sig_breakout)
SCOPERTA PRINCIPALE: UNKNOWN_STRATEGY_REGISTRY_GAP - CRT e
        FVG_MIT_WINDOW hanno codice MQL5 reale e raggiungibile ma sono
        strutturalmente bloccate da NXS_StrategyKnown() - zero trade
        possibili a prescindere dal segnale. FVG_MIT_WINDOW e' default
        enabled -> severita' alta.
CORREZIONE DOC: motore NXR (IFVG/FVG_MIT/OB_MIT/MALAYSIAN_SNR) - zero
        call site verificati, nota vault precedente corretta
NUOVO CANDIDATO: CROSS_STRATEGY_STATE_SHARING (ORDER_BLOCK/OB_MIT
        condividono g_obBuy/g_obSell) - NOT_ENOUGH_EVIDENCE
PROSSIMO: BUILD_CANONICAL_BREAKOUT_ACC_DATASET (Phase 7.9H) - ripresa
```
