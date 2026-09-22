# NEXUS - Phase 7.9A Postmortem & Candidate Reprioritization

**Baseline:** `f9550050f853c7dd4fefa3ef5c4315aa8ac3fcd7` (Phase 7.8I, `VOLATILITY_BREAKOUT_CONFIRMED` FAIL, `ARCHIVE_CURRENT_DESIGN`). Nessun nuovo backtest, nessuna modifica a strategie, nessun rescue — solo riconciliazione, archiviazione formale, postmortem, checklist permanente, inventario e riprioritizzazione.

---

## 1. Riconciliazione del risultato canonico

**Trovato e corretto un errore reale**: il vault report e il riepilogo narrativo di 7.8I riportavano numeri BUY/SELL sbagliati (BUY n=63/-0,081/PF 0,842, SELL n=120/-0,060/PF 0,881) — **mai presenti nell'artifact canonico**, che ha sempre detto:

| | n | expectancy_R | PF |
|---|---|---|---|
| **BUY** | 56 | **-0,726** | **0,146** |
| **SELL** | 127 | **+0,223** | **1,625** |

**Causa radice**: errore di trascrizione manuale nel report narrativo, non intercettato perché il verificatore indipendente di 7.8I controllava solo l'endpoint primario aggregato, mai i numeri di `direction_asymmetry`. Corretto: (a) il vault 7.8I in-place, con nota di correzione datata; (b) il gap del verificatore, ora colmato in questa fase.

**L'artifact `volatility_breakout_serious_3y_result_v1.json` non è stato toccato** (`canonical_sha256` invariato). **Il verdetto aggregato resta `FAIL`** — expectancy_R=-0,067, PF=0,867, CI95=[-0,281,+0,152].

## 2. Archiviazione formale del lifecycle

`VOLATILITY_BREAKOUT_CONFIRMED`: `research_readiness=REFUTED_ARCHIVED`, `serious_validation=FAIL`, `execution_candidate=false`, `meta_filter_ready=false`, `deployable=false`. Nessun artifact precedente (7.7A, 7.7B, 7.8B-I) modificato — questo è un nuovo layer che chiude il ciclo di evidenza già aperto in 7.7B (`next_required_evidence: "Serious 3Y backtest"` — esattamente ciò che è stato prodotto, con esito negativo).

## 3. L'asimmetria direzionale — cosa è e cosa non è

**SELL positivo (+0,223R, PF 1,625) / BUY fortemente negativo (-0,726R, PF 0,146)** è registrata come **`POST_VALIDATION_OBSERVATION`**, esplicitamente **non** una strategia salvata: l'aggregato resta negativo, nessuna direzione è stata eliminata dal campione. Se in futuro nascerà `VOLATILITY_BREAKOUT_SELL_ONLY`, dovrà essere una **nuova identità di ipotesi** con nuova discovery e nuova preregistrazione — mai il riuso del campione SELL di 7.8I come validazione già acquisita.

## 4. Postmortem — tre categorie tenute separate

**Fallimento di strategia**: expectancy aggregato negativo, PF<1, CI95 include lo zero, stress negativo, solo 1/3 segmenti temporali non-negativo — un FAIL netto, non borderline.

**8 lezioni di pipeline** (stale EX5, master switch di strategia, attivazione Research Mode, semantica del path Expert=, semantica esatta delle date MT5, fingerprint dati window-aware, misura esatta del timezone broker, preflight tecnico prima dei run lunghi) — diventate la checklist permanente sotto.

**3 lezioni di tooling** (ticket sempre 0 per le righe OPEN, header CSV a volte assente, ambiguità di matching in hedging mode) — già corrette negli script di 7.8I, ora documentate come conoscenza di regressione.

## 5. Checklist di preflight permanente

**12 punti**, da verificare in ordine per qualunque futuro Serious validation, salvata standalone in `serious_validation_preflight_checklist_v1.json`: EX5 compilato dal sorgente giusto, hash source/EX5 registrati, l'input della strategia esiste davvero nel binario, master switch ON, selector corretto, Research Mode ON, preflight senza errori fatali, un mini-run tecnico raggiunge davvero il codice della strategia, fingerprint dati window-aware fresco, semantica esatta della finestra, timezone misurato, percorso di raccolta output verificato.

## 6-7. Candidati rimasti e riprioritizzazione

Esclusi come già refutati: `WICK_SWEEP_RECLAIM`, `H015_SAR_EXTERNAL_VALIDATION`, `SAR_LIVE`, `ADX_RSI`, e ora `VOLATILITY_BREAKOUT_CONFIRMED`. Restano aperti solo due candidati (dallo stato reale di 7.7A/7.7B, non riclassificati qui):

| | H006_LIQUIDITY_SWEEP_RECLAIM | BREAKOUT_ACC |
|---|---|---|
| Evidence strength | MEDIUM (holdout borderline) | LOW (solo R-multiple grezzo) |
| Uncertainty remaining | MEDIUM | HIGH (lifecycle non ancora estratto) |
| Independence | LOW (overlap 0,991) | UNKNOWN (mai misurata) |
| Expected information gain | **LOW** (effect size già sotto soglia) | **HIGH** (miglior performer informale, 5/6 anni positivi) |
| Engineering cost | **HIGH** (serve un feed dati esterno nuovo) | **LOW** (solo audit del codice esistente) |
| Compute cost | MEDIUM | LOW |
| Contamination risk | LOW | LOW |
| Distanza da execution validation | FAR | FAR ma il primo passo costa poco |

## 8. Decisione per il prossimo esperimento

**`FORMALIZE_EXISTING_CANDIDATE` → `BREAKOUT_ACC`.** Costo di ricerca più basso (nessun backtest, solo estrazione del lifecycle_contract da `NXS_Strategies.mqh`, lo stesso lavoro già fatto per VOLBRK in Strategy Foundry Phase 3), nessun rischio di contaminazione, potenziale informativo alto. H006 richiederebbe un investimento infrastrutturale (cross-feed validation) per un guadagno atteso basso, dato un effect size già sotto soglia di materialità. **Nessun test lanciato in questa fase.**

## 9. Nuovo backlog item (non prioritizzato)

**`HISTORICAL_VOLUME_CONTRACT_WALLS`**: concentrazione storica di volume + posizionamento futures/opzioni + distanza dal prezzo → comportamento condizionale futuro (rejection probability, breakout continuation/failure, MFE/MAE, realized volatility, time-at-level). Trattato inizialmente come `MARKET_EVENT / STATE_RESEARCH`, non come strategia — esplicito il caveat: non assumere che alto volume/OI equivalga a support/resistance.

## Deliverables

`build_postmortem_and_reprioritization.py`, `phase7_9a_postmortem_and_reprioritization_v1.json`, `serious_validation_preflight_checklist_v1.json` (standalone), `verify_postmortem_and_reprioritization.py`, `test_phase_7_9a.py`, correzione in-place del vault 7.8I.

## Regressione

35/35 PASS sulla nuova suite. 33/35 delle altre suite Phase 7 passano; i 2 fallimenti sono gli stessi già noti e documentati (7.8E whole-file hash legacy, 7.8H EX5 stale reference) — invariati, non "aggiustati".

---

**VOLATILITY_BREAKOUT_CONFIRMED: archiviato definitivamente.**

**Prossimo sblocco: formalizzare BREAKOUT_ACC (nessun backtest — solo audit del codice esistente).**

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
VOLATILITY_BREAKOUT: ARCHIVE_CURRENT_DESIGN ✓
NUOVO CAPITALE SCIENTIFICO: pipeline Serious-validation matura ✓
                             checklist di preflight a 12 punti ✓
FASE ATTUALE: 7.9A completata
PROSSIMO: FORMALIZE_EXISTING_CANDIDATE -> BREAKOUT_ACC
          (nessun backtest - solo estrazione lifecycle dal codice)
BACKLOG (non prioritizzato): HISTORICAL_VOLUME_CONTRACT_WALLS
```
