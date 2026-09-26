# NEXUS - Phase 7.9I BREAKOUT_ACC Mechanism Research

**Baseline:** `4870248` (Phase 7.9H - dataset canonico). Dataset `breakout_acc_intended_d1_v1_dataset.json` trattato come **input frozen** — nessuna modifica a trigger, cooldown, HTF filter, SL/TP, selector, MQL5, o al dataset canonico stesso (verificato: 0 diff). Ogni trasformazione derivata in artifact separati (`server/research_scripts/phase7/phase7_9i/`). Nessuna optimization eseguita.

**Metodo**: EDGE DECOMPOSITION → PATH ANATOMY → NATURAL HORIZON → MECHANISM DISCOVERY, sulle tre popolazioni tenute esplicitamente separate: **A** (67 live-observed), **B** (47 OPENED, con fill/path reali — unica popolazione usata per le analisi basate su MFE/MAE/forward return), **C** (8 B-only, mai eseguiti — solo sensitivity analysis dedicata).

---

## 1. Edge Decomposition

Decomposto per direzione, anno, magnitudine del breakout (terzili naturali, non soglie cercate), contesto HTF causale (nuovo proxy EMA100, distinto dal gate vestigiale `htf_ok` di 7.9H), volatilità (ATR20 causale), distanza dal precedente raw-accept, e stage terminale (su tutti i 75, solo struttura). **Nessuna soglia scelta guardando l'esito.**

**Scoperta principale**: BUY (n=36) e SELL (n=11) mostrano profili radicalmente diversi — non emersa cercandola, ma osservata sulla dimensione esplicitamente richiesta. Breakout di magnitudine maggiore (terzile HIGH) mostrano MFE mediano quasi doppio e MAE mediano dimezzato rispetto a LOW/MID.

## 2. Path Anatomy (Population B, 47 OPENED)

MAE raggiunto prima di MFE nel 57.4% dei casi (vs 42.6% il contrario) — un breve shake-out iniziale è più comune di un movimento immediatamente favorevole. Continuation vs Failure (a 60 barre D1): 25 CONTINUATION, 21 FAILURE, 1 UNKNOWN — **ma questo bilanciamento nasconde un'asimmetria enorme**: BUY 24/36 (66.7%) continuation, SELL 1/11 (9.1%).

## 3. Natural Horizon

Il ritorno medio close-to-close cresce **quasi monotonamente** da bar 1 a bar 60 (barre D1), CI95% (descrittivo) esclude lo zero in modo continuativo dalla barra 18 alla 60 (43 barre consecutive) — **nessun plateau né decadimento visibile entro la finestra osservata**. Non si può concludere che l'informazione "saturi" entro 60 barre: potrebbe estendersi oltre, o riflettere la coda di pochi eventi con movimenti tardivi ampi (dispersione ampia a barre lunghe).

## 4. Mechanism Discovery

6 categorie valutate con evidenza a favore/contro/confidence/alternative esplicite. **Trovata**: `TREND_PERSISTENCE_DIRECTION_DEPENDENT` è la spiegazione più supportata (asimmetria BUY/SELL massiccia + **100% degli eventi OPENED sono trend-aligned rispetto a un proxy EMA100 causale nuovo** — nessun evento contro-trend nel campione, pur non essendoci alcun filtro di trend nel codice di `NXS_Strat_BreakoutAcc()`, verificato). `CONTINUATION_SYMMETRIC_BREAKOUT` è **esplicitamente contraddetta** come meccanismo simmetrico universale. Alternativa principale non esclusa: il campione copre quasi solo un regime di mercato (bull secolare GOLD 2019-2026, ~1280→~4500) — confondimento non risolvibile con questo dataset.

## 5. Sensitivity 67 vs 75

Gli 8 B-only **non influenzano alcuna conclusione primaria** (Population B, unica base di Edge Decomposition/Path Anatomy/Natural Horizon/Mechanism Discovery, li esclude per costruzione — disgiunta da Population C). Impatto strutturale se inclusi erroneamente: marginale (variazione %BUY: -2.1 punti).

## 6. Gate Diagnostic (BLOCKED/BROKER_REJECT — diagnostico, non proposta di modifica)

Path **controfattuale** (prezzo di chiusura della barra di breakout come proxy, mai un fill reale) per i 20 eventi mai eseguiti. BLOCKED (cooldown, N=11): forward return mediano controfattuale **migliore** di OPENED (90.3 vs 11.1) — possibile indicazione (non confermata, N piccolo) che il cooldown elimina anche eventi potenzialmente buoni. BROKER_REJECT (N=9): mediano peggiore (-10.65) — riflette probabilmente la geometria dei segnali respinti dal broker (spread/margine), non un giudizio di qualità.

## 7. BUY/SELL/anno/regime — decomposizione incrociata

Tabella direzione×anno costruita (non solo dimensioni separate). Vedi `breakout_acc_failure_map_and_robustness_v1.json`.

## 8. Gli 8 B-only — capitolo dedicato

Confrontati contro i 67 live-observed su feature causali: concentrati in 4 anni (2019×4, 2021×2, 2022, 2023) su 8 eventi. **Osservazione nuova** (non conclusiva): magnitudine di breakout mediana molto più piccola (7.4 vs 28.25 dei live-observed) — coerente con (non conferma) il meccanismo candidato `INTRADAY_BAR_TIMING_DIFFERENCE` già ipotizzato in Phase 7.9H. Etichettata `POST_HOC_OBSERVATION → NEW HYPOTHESIS`, non conclusione.

## 9. Robustezza minima

N=47 piccolo (SELL=11 in particolare); concentrazione per anno moderata (nessun anno >25%); **dipendenza da direzione FORTE** (il risultato aggregato dipende quasi interamente dal sottogruppo BUY); sensitivity agli 8 B-only nulla sulle analisi primarie; sensitivity ai non-OPENED limitata a un'analisi diagnostica separata con N piccoli. **Confidence complessiva: bassa-moderata.**

## 10. Failure Map

Principale failure mode: **segnale SELL in un mercato con trend rialzista strutturale** (9/11 SELL falliscono a 60 barre) — non un pattern di breakout geometricamente distinguibile (magnitudine/ATR non differiscono nettamente fra FAILURE e CONTINUATION).

---

## Executive Summary (10 righe)

Vedi `breakout_acc_executive_summary_decision_card_v1.json` — sintesi: pattern favorevole convergente ma fortemente direzione-dipendente; 100% trend-aligned; nessun natural horizon netto (crescita senza plateau); continuation simmetrica contraddetta; B-only non influenti sul risultato primario; gate cooldown potrebbe eliminare anche eventi buoni (N piccolo); confidence bassa-moderata.

## Decision Card

| Domanda | Risposta |
|---|---|
| Evidenza di comportamento non casuale? | **SÌ** — pattern convergente su 3 analisi indipendenti |
| Meccanismo comprensibile? | **Parzialmente** — trend-allineamento plausibile ma confuso con l'unico regime osservato |
| Stabile nel tempo? | **Non verificabile con questo campione** — un solo regime (bull GOLD) rappresentato |
| Dipende da pochi anni/direzioni? | **Sì, fortemente (direzione)** — concentrazione per anno solo moderata |
| Natural horizon identificabile? | **Parzialmente** — CI esclude zero da barra 18 a 60, ma senza plateau |
| Failure mode principale | SELL in mercato strutturalmente rialzista |
| Confidence | **Bassa-moderata** |

### Decisione finale: **`MECHANISM_PARTIALLY_SUPPORTED`**

(vocabolario consentito: `MECHANISM_SUPPORTED` / `MECHANISM_PARTIALLY_SUPPORTED` / `MECHANISM_NOT_SUPPORTED` / `INSUFFICIENT_EVIDENCE` — mai PROMOTE/DEPLOY/PROFITABLE, verificato assenza di queste parole nell'output)

## Prossima ipotesi falsificabile (NON implementata)

**`TREND_ALIGNMENT_CONDITIONAL_EDGE`**: il comportamento favorevole di BREAKOUT_ACC è condizionato dall'allineamento con il trend di lungo periodo (proxy EMA100 causale), non dalla geometria del breakout in sé. Falsificabile: richiederebbe un campione con eventi generati durante un regime di mercato diverso (bear o range prolungato) — segnali BUY in un regime non rialzista dovrebbero comportarsi come i SELL qui osservati; se invece si comportassero come i BUY attuali, l'ipotesi sarebbe falsificata. **Non implementata, non testata in questa fase.**

---

## Deliverables

`breakout_acc_feature_engineering_v1.json`, `breakout_acc_edge_decomposition_v1.json`, `breakout_acc_path_anatomy_v1.json`, `breakout_acc_natural_horizon_v1.json`, `breakout_acc_mechanism_discovery_v1.json`, `breakout_acc_sensitivity_67_vs_75_v1.json`, `breakout_acc_gate_diagnostic_v1.json`, `breakout_acc_b_only_comparison_v1.json`, `breakout_acc_failure_map_and_robustness_v1.json`, `breakout_acc_executive_summary_decision_card_v1.json`, modulo condiviso `nxs_mechanism_context.py`, 10 builder, verificatore indipendente, 32 test di consistenza (32/32 PASS), questo vault report.

## Vincoli preservati

Dataset canonico 7.9H invariato (verificato via git diff). Nessun file MQL5/Python modificato. Nessuna optimization (nessuna ricerca di TP/SL/soglia, nessun grid search, nessun rescue). `VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti. `HISTORICAL_VOLUME_CONTRACT_WALLS` resta backlog.

## Regressione

- **Suite propria 7.9I (pytest)**: 32/32 PASS
- **Suite pytest Phase 7 totale**: **318/318 PASS, 0 fallimenti** (286 precedenti + 32 nuovi)
- **4 suite standalone pre-esistenti**, fallimenti noti invariati (nessuna regressione nuova): `phase7_8e` 68/72, `phase7_8h` 18/21, `phase7_8i` 22/23, `phase7_9b` 31/33.

I 2 artifact `phase7_9c/breakout_acc_*_event_stream_v1.json` (effetto collaterale noto: `generated_at` toccato dall'esecuzione suite, hash canonico invariato) ripristinati con `git checkout --` prima del commit.

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.9I: COMPLETATA ✓
MECHANISM RESEARCH: BREAKOUT_ACC mostra un pattern favorevole
        convergente ma FORTEMENTE direzione-dipendente (BUY 66.7%
        continuation vs SELL 9.1%), 100% trend-aligned (proxy EMA100
        causale, nessun filtro di trend nel codice) - CONTINUATION
        SIMMETRICA CONTRADDETTA, TREND_PERSISTENCE la spiegazione
        piu' supportata ma confusa con l'unico regime di mercato
        osservato (bull GOLD 2019-2026)
NATURAL HORIZON: nessun plateau entro 60 barre D1 - crescita quasi
        monotona, CI esclude zero da barra 18 a 60
DECISIONE FINALE: MECHANISM_PARTIALLY_SUPPORTED
PROSSIMA IPOTESI (non implementata): TREND_ALIGNMENT_CONDITIONAL_EDGE
```
