# NEXUS - Phase 7.9J — Revisione Metodologica Mirata di Phase 7.9I

**Baseline:** `b9dafda` (Phase 7.9I). Dataset canonico `breakout_acc_intended_d1_v1_dataset.json` (Phase 7.9H) e raw data **preservati e invariati** (verificato via git diff). Nessuna optimization, nessuna modifica all'EA, nessuna promozione live.

**Obiettivo**: revisione mirata dell'integrità metodologica di Phase 7.9I sui 5 punti sollevati, prima di procedere con `TREND_ALIGNMENT_CONDITIONAL_EDGE` o altre strategie.

---

## 1. Causalità temporale — bug confermato, corretto, impatto misurato: nullo

**Confermato**: `causal_ema()` in `nxs_mechanism_context.py` usava `<=`, includendo la chiusura **finale** della barra D1 del giorno del segnale — un valore non disponibile fino alla mezzanotte successiva, quindi **nel futuro** rispetto a qualunque decisione/fill intraday reale (esempio concreto verificato: evento 2019.06.05, fill 17:30 — la chiusura finale della barra 2019.06.05 non è nota fino al 2019.06.06 00:00).

**Corretto**: `<` stretto, identico a `causal_atr()` (già corretto dall'origine, verificato). `breakout_magnitude_*` (c1/c2) verificata riga-per-riga sul sorgente MQL5 (`NXS_BreakoutAccSignalDiagnostic.mq5`): `c1 = rates[i].close` è la chiusura della barra **precedente**, già nota all'inizio del giorno del segnale — nessun leakage.

**Impatto misurato (prima/dopo su tutti i 75 eventi)**: il valore EMA100 causale cambia fino a 15.94 unità di prezzo — il bug era reale — ma **0 flip su 75** del flag booleano `trend_aligned`. Il finding "100% trend-aligned" di Phase 7.9I è **confermato indipendente dal bug**. Aggiunto anche un secondo proxy (EMA20, trend locale, stessa correzione), anch'esso 100% allineato.

**Secondo problema trovato, CONFERMATO ma NON corretto (upstream in Phase 7.9H, frozen)**: la ricerca della prima barra D1 ≥ `entry_time` salta il giorno di ingresso stesso (per ingressi intraday, tutti i 47 casi reali) — "barra 1" nei risultati di Path Anatomy/Natural Horizon/Mechanism Discovery corrisponde in realtà a **2 giorni di calendario dopo l'ingresso**, non 1. Offset costante e simmetrico fra tutte le popolazioni (nessun bias BUY/SELL) — documentato, non corretto per non creare un'incoerenza fra il dataset congelato 7.9H e le sue proprie ricostruzioni.

## 2. Popolazioni e sensitivity — 67 vs 75 estesa al percorso

Confermato ricostruibile (contrariamente al rischio paventato): percorso controfattuale (proxy = prezzo di chiusura della barra di breakout, **mai** un fill/P&L reale) calcolato per tutti gli 8 B-only e i 20 BLOCKED/BROKER_REJECT, con la stessa metodologia del Gate Diagnostic. Ogni riga esplicitamente etichettata `REAL_FILL` o `COUNTERFACTUAL_PROXY_C1`. Delta sul forward return mediano a 60 barre fra Population A (67) e tutti i 75: **-6.33 unità di prezzo — non trascurabile**, ma questo confronto **non altera** le analisi primarie (Path Anatomy/Natural Horizon/Mechanism Discovery restano basate esclusivamente sui 47 REAL_FILL).

## 3. Trend alignment — confondimento totale confermato

Verificato su **tutti i 75 eventi** (non solo i 47 OPENED): **0 eventi non allineati**, su entrambi i proxy (EMA100 regime, EMA20 locale), per l'intera storia 2019-2026. Direzione e allineamento di trend sono **perfettamente collineari** — non esiste un solo evento con cui stimare un effetto di allineamento indipendente dalla direzione. Nota aggiuntiva: l'allineamento EMA20 potrebbe essere parzialmente tautologico rispetto alla definizione stessa di Acceptance (rottura di un range di 20 barre); solo l'allineamento EMA100 (orizzonte indipendente) è un test genuinamente separato — e anche quello è 100%. `TREND_PERSISTENCE_DIRECTION_DEPENDENT` resta un'**etichetta descrittiva candidata**, non una spiegazione causale isolata o testata. Nessuna nuova ipotesi implementata.

## 4. Natural Horizon — declassato a puramente descrittivo

Quantificato: il 70% dei gap fra eventi consecutivi (32/46) è ≤60 giorni — le finestre forward **si sovrappongono** sostanzialmente nel tempo di calendario, e i valori entro-evento sono per costruzione fortemente autocorrelati (traiettoria continua, non un nuovo campionamento a ogni barra). Il CI95% originale (mean ± 1.96·SE) **assume indipendenza, violata su entrambi i fronti** — gli intervalli mostrati sono probabilmente più stretti del reale. **Declassamento esplicito**: `stable_horizon_identified` passa da `True` (7.9I) a `False` (7.9J, revisione). Il pattern di crescita resta descrittivamente osservabile, ma non costituisce una prova statisticamente valida né dell'esistenza né dell'assenza di un vero natural horizon.

## 5. Forza delle conclusioni — linguaggio corretto

"3 analisi indipendenti" e "non spiegabile da rumore" **rimossi/riformulati** in `build_mechanism_discovery.py` e `build_executive_summary_and_decision_card.py`: continuation rate, MFE/MAE e HTF proxy sono **tre statistiche calcolate sugli stessi 47/36/11 eventi**, non tre campioni indipendenti — nessun test d'ipotesi formale eseguito. Distinzione ora esplicita fra pattern descrittivo (asimmetria BUY/SELL, effect size ampio), spiegazione candidata (trend persistence, non isolata) ed edge incrementale (**mai stimato** — nessun confronto con un benchmark buy-and-hold o modello nullo in nessuna fase).

---

## Confronto prima/dopo

| Elemento | Phase 7.9I (prima) | Phase 7.9J (dopo) |
|---|---|---|
| `causal_ema()` | `<=` (leakage 1 barra) | `<` stretto (corretto) |
| Trend-aligned (OPENED) | 47/47 (100%) | 47/47 (100%) — **invariato** |
| Trend-aligned (tutti i 75) | non verificato | **0/75 non-allineati** (nuovo controllo) |
| Trend locale (EMA20) | non esisteva | aggiunto, anch'esso 100% allineato |
| Natural Horizon | "parzialmente identificabile" | **declassato a puramente descrittivo** |
| Sensitivity 67 vs 75 | solo strutturale | estesa al percorso (controfattuale, ricostruibile) |
| "3 analisi indipendenti" | affermato | **corretto**: stesse osservazioni, lenti diverse |
| Confidence complessiva | bassa-moderata | **bassa** (declassata) |
| Decisione finale | `MECHANISM_PARTIALLY_SUPPORTED` | `MECHANISM_PARTIALLY_SUPPORTED` (**invariata**) |

## Problemi confermati, esclusi, non risolti

- **Confermato e corretto**: leakage in `causal_ema()` (impatto nullo sulle conclusioni booleane).
- **Confermato, non corretto (documentato)**: offset di 1 barra nel path forward, upstream in Phase 7.9H frozen.
- **Confermato**: confondimento totale direzione/trend-alignment (0 variazione su 75 eventi).
- **Confermato**: dipendenza/sovrapposizione delle finestre nel Natural Horizon (CI non validi).
- **Escluso**: `causal_atr()` e `breakout_magnitude` (c1/c2) — verificati causalmente puliti dall'origine.
- **Non risolto/dichiarato come limite**: nessuno — il confronto 67 vs 75 di percorso si è rivelato ricostruibile, contrariamente al rischio paventato nell'istruzione.

## Artifact corretti (lineage e supersessione)

- `nxs_mechanism_context.py` — `causal_ema()` corretta, `causal_ema20_d1_local_trend` aggiunto, `lineage_note` nel payload di `build_feature_table()`.
- `breakout_acc_feature_engineering_v1.json`, `..._edge_decomposition_v1.json`, `..._path_anatomy_v1.json`, `..._sensitivity_67_vs_75_v1.json`, `..._gate_diagnostic_v1.json`, `..._b_only_comparison_v1.json`, `..._failure_map_and_robustness_v1.json` — rigenerati (hash identici a prima: fix senza impatto numerico su questi).
- `breakout_acc_mechanism_discovery_v1.json`, `breakout_acc_executive_summary_decision_card_v1.json` — **linguaggio rivisto**, `lineage_note` aggiunta, hash cambiato.
- `breakout_acc_natural_horizon_v1.json` — `superseded_by_note` aggiunta (numeri invariati, interpretazione qualificata da 7.9J).
- Originali pre-fix preservati in `phase7_9j/raw_data_pre_fix/*_ORIGINAL_pre_temporal_fix.json`.

## Deliverables Phase 7.9J

`breakout_acc_temporal_causality_audit_v1.json`, `breakout_acc_sensitivity_67_vs_75_path_v1.json`, `breakout_acc_direction_alignment_outcome_v1.json`, `breakout_acc_natural_horizon_reconciliation_v1.json`, 4 builder, verificatore indipendente (include test di non-leakage causale diretto), 26 test di consistenza (26/26 PASS), questo vault report.

## Decision Card aggiornata

| Domanda | Phase 7.9J |
|---|---|
| Evidenza di comportamento non casuale? | Sì, come pattern descrittivo (non "non spiegabile da rumore" — nessun test formale) |
| Meccanismo comprensibile? | Parzialmente — ma direzione/trend-alignment sono osservazionalmente indistinguibili (0/75 non-allineati) |
| Stabile nel tempo? | Non verificabile — un solo regime di mercato |
| Dipende da pochi anni/direzioni? | Sì, fortemente — e totalmente dal trend-alignment (collineare al 100%) |
| Natural horizon identificabile? | **No — solo descrittivo** (declassato) |
| Failure mode principale | SELL in mercato strutturalmente rialzista (invariato) |
| Confidence | **Bassa** (declassata da bassa-moderata) |

**Decisione finale: `MECHANISM_PARTIALLY_SUPPORTED` (invariata)** — la giustificazione è ora più conservativa e precisa, non la conclusione stessa.

## Prossimo passo (una sola proposta, non implementata)

Restare su `TREND_ALIGNMENT_CONDITIONAL_EDGE` (Phase 7.9I) come unica ipotesi falsificabile in sospeso — ma con la qualifica aggiuntiva emersa qui: dato il confondimento totale (0/75 eventi non-allineati), il test di falsificazione richiede necessariamente un campione con **variazione nell'allineamento** (un regime di mercato diverso o uno strumento diverso), non è ottenibile da nessuna ulteriore analisi di questo stesso dataset. Non implementata, non esplorata oltre.

## Vincoli preservati

Phase 7.9H e i raw data invariati (verificato via git diff). Nessun file MQL5/Python modificato. Nessuna optimization. `VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti.

## Regressione

- **Suite propria 7.9J (pytest)**: 26/26 PASS
- **Suite pytest Phase 7 totale**: **344/344 PASS, 0 fallimenti** (318 precedenti + 26 nuovi)
- **4 suite standalone pre-esistenti**, fallimenti noti invariati (nessuna regressione nuova): `phase7_8e` 68/72, `phase7_8h` 18/21, `phase7_8i` 22/23, `phase7_9b` 31/33.
- Suite propria 7.9I (32/32) verificata ancora passante dopo le modifiche in-place.

I 2 artifact `phase7_9c/breakout_acc_*_event_stream_v1.json` (effetto collaterale noto, hash canonico invariato) ripristinati con `git checkout --` prima del commit.

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.9J: COMPLETATA ✓
REVISIONE METODOLOGICA: bug di causalita' EMA100 confermato e corretto
        (impatto nullo su trend-alignment: 47/47 invariato); confondimento
        totale direzione/trend confermato (0/75 non-allineati); Natural
        Horizon declassato a puramente descrittivo (finestre sovrapposte,
        dipendenza entro-evento); linguaggio "analisi indipendenti"/"non
        spiegabile da rumore" corretto
DECISIONE FINALE: MECHANISM_PARTIALLY_SUPPORTED (INVARIATA - solo la
        giustificazione e' piu' conservativa)
PROSSIMO: TREND_ALIGNMENT_CONDITIONAL_EDGE resta l'unica ipotesi in
          sospeso, richiede un campione con variazione di allineamento
          (non ottenibile da questo dataset) - non implementata
```
