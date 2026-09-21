# NEXUS - Phase 7.8A Value-of-Information Contract: VOLATILITY_BREAKOUT_CONFIRMED

**Baseline:** `fdab6e7` (Phase 7.7A/7.7B, meta-filter ready 0/7). Contratto decisionale **ex-ante**: stabilisce se il Serious 3Y e' davvero il prossimo esperimento a maggior valore informativo per VOLATILITY_BREAKOUT_CONFIRMED - PRIMA di eseguirlo. Nessun backtest, nessun nuovo outcome, nessuna optimization di parametri, nessuna applicazione di MECH-23.

**Conferma esplicita: NO SERIOUS 3Y EXECUTED. NO NEW OUTCOME DATA ACCESSED. NO EDGE DISCOVERY PERFORMED.**

---

## 1. Stato dell'evidenza attuale (solo da artifact canonici)

| | |
|---|---|
| Lifecycle | `FULL_STRATEGY_SPEC` - unico candidato con contratto interamente estratto |
| Signal parity Python/MQL5 | 927/927 identici, `SIGNAL_LOGIC_DIFFERENCE=0` |
| Discovery | delta_p=+0.037R |
| Internal validation | delta_p=+0.133R, n~927 |
| Full backtest engine | 243 trade, PF=1.20, expectancy=0.068R **a costo zero** |
| Fast structural (tick reali, 6 mesi) | n=**14**, PF=1.165, concentrazione temporale forte (2/5 mesi = quasi tutto il profitto), BUY PF=0.734 vs SELL PF=2.236 |
| Cost robustness a scala | **Mai testata** - il PF a campione ampio (243 trade) e' esplicitamente "a costo zero" |
| External evidence | **Assente** - nessuna cross-feed validation mai tentata |
| Gate attuale | `STRUCTURALLY_ELIGIBLE` + `NEEDS_MORE_EVIDENCE` → gate non superato |

## 2. Decisione da informare

`A_ABANDON_ARCHIVE` / `B_HOLD_NEED_MORE_EVIDENCE` (stato attuale) / `C_ADVANCE_TO_NEXT_VALIDATION_GATE`. **`GO_LIVE` non e' mai un'azione diretta** - richiederebbe comunque EXECUTION_VALIDATION (gia' mostrato critico da WICK_SWEEP_RECLAIM) e una valutazione di portfolio/rischio separata.

## 3. Cosa risolverebbe il Serious 3Y

| Asse | Livello attuale |
|---|---|
| Sign uncertainty | MEDIUM-LOW (4 letture concordi positive) |
| Magnitude uncertainty | **HIGH** |
| Temporal stability | **HIGH** |
| Direction asymmetry | **HIGH** |
| Cost robustness | **HIGH** |
| Regime concentration | **HIGH** |
| Sample adequacy | **HIGH** (n=14 ben sotto ogni soglia minima gia' in uso nel progetto) |

Il Serious 3Y indirizza **5 assi su 7** simultaneamente - il segno e' gia' relativamente stabilito, quindi il suo contributo marginale piu' importante e' su magnitudo/stabilita'/costi/concentrazione/campione.

## 4-5. Alternative confrontate (nessuna eseguita)

| Alternativa | Assi indirizzati | Costo |
|---|---|---|
| **Serious 3Y** | 5/7 assi + parziale asimmetria | Compute HIGH, ma engineering gia' fatto (parita' verificata) |
| Bar-level piu' economico | sample/temporal parziale | Basso ma non tocca cost_robustness ne' regime_concentration reale |
| Cross-feed validation | validita' esterna (asse nuovo) | Medio, pattern gia' riusato da SAR/H015 |
| Holdout recente aggiuntivo | temporal parziale | Il piu' economico, incremento informativo piccolo |
| Direction-specific diagnostic | asimmetria direzionale | Economico ma **alto rischio di rescue post-hoc** se non pre-registrato su campione fresco |
| Nessun test / attesa | sample (lentamente) | Nessun costo di ricerca, ma nessun progresso decisionale in tempi prevedibili |

## 6. Decision tree congelata prima del test

| Esito | Azione |
|---|---|
| Refutazione forte, campione ampio | `A_ABANDON_ARCHIVE` |
| Nullo/inconclusivo | `B_HOLD_NEED_MORE_EVIDENCE` (innesca stopping logic) |
| Positivo ma instabile | `B_HOLD_NEED_MORE_EVIDENCE` - **mai promozione automatica** |
| Positivo e robusto | `C_ADVANCE_TO_NEXT_VALIDATION_GATE` - **mai GO_LIVE direttamente** |

## 7. VoI formale

**`NUMERIC_VOI_NOT_IDENTIFIED`** - nessuna prior calibrata su P(edge reale), nessuna funzione di utilita'/costo esplicita esiste nel progetto. Usato invece un framework ordinale trasparente (LOW/MEDIUM/HIGH con rationale per cella) - **nessun punteggio numerico aggregato inventato**.

## 9. Stopping logic

`STRONG_WIDE_SAMPLE_REFUTATION` / **`COST_ROBUSTNESS_FAILURE`** (esattamente il pattern gia' documentato per WICK_SWEEP_RECLAIM in Failure Memory: shadow PF=5.80 → reale PF=0.78-0.80 - se si ripetesse qui, sarebbe uno stop forte, non un problema da aggiustare) / `EXECUTION_INCOMPATIBILITY` / `PERSISTENT_INSUFFICIENT_EFFECTIVE_SAMPLE`.

## 10. Verdetto

**`SERIOUS_3Y_IS_NEXT_BEST_EXPERIMENT`** - l'unico test che indirizza la maggioranza degli assi HIGH simultaneamente, con basso rischio di contaminazione (spec gia' congelata) e basso costo di ingegneria residuo (parita' gia' verificata).

**Caveat esplicito:** condizionale alla disponibilita' di budget compute/dati/tempo - nessun budget di ricerca formale e' dichiarato nel progetto, quindi questo contratto non puo' verificarlo. Se il budget non fosse disponibile ora, l'holdout recente aggiuntivo diventerebbe il secondo miglior test praticabile - per vincolo di risorse, non perche' scientificamente superiore.

## 11. Prerequisiti per un VoI numerico futuro

Prior edge distribution, candidate base-rate storico, costo di falsa promozione, costo di falso rigetto, compute cost reale, capital opportunity cost - **nessuno di questi esiste oggi** nel progetto.

## Regressione

98/98 PASS su questa suite. **0 regressioni** sulle altre 24 suite Phase 7 (25 totali).

## Deliverables

`volatility_breakout_voi_contract_v1.json`, `build_volatility_breakout_voi_contract.py`, `test_volatility_breakout_voi_contract.py` - tutti in `server/research_scripts/phase7/phase7_8a/`. Nessuna modifica retroattiva.

---

**NO SERIOUS 3Y EXECUTED. NO MECH-23 APPLIED. NO EDGE DISCOVERY PERFORMED.**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
FASE ATTUALE:
VoI contract completato -
Serious 3Y confermato come
prossimo esperimento a maggior
valore informativo (condizionale
al budget disponibile)
PROSSIMO SBLOCCO:
decisione umana: allocare
budget per il Serious 3Y,
oppure scegliere l'alternativa
piu' economica (holdout recente)
```

Nota: la richiesta di deploy su Render nel messaggio precedente non e' stata eseguita in questa sessione - letta come diretta al lavoro Codex/Company Control Plane (deploy infrastrutturale), fuori dalla portata di questo lavoro di ricerca Quant.
