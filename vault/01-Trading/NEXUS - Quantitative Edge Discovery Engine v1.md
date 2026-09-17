# NEXUS - Quantitative Edge Discovery Engine v1

Prima vera pipeline quantitativa della nuova ontologia: `MARKET STATE + EVENT → CONDITIONAL OUTCOME → EDGE`. Nessuna strategia nominata usata come punto di partenza, nessun nuovo EA, nessuna optimization, nessuna ricerca combinatoria esaustiva. Base approvata: Phase 4 (`ad14e97`), preflight registry fix (`1ebae49`).

Tutti i numeri in questo report sono calcolati da dati reali (tick Dukascopy validati in Phase 4) tramite gli script in `server/research_scripts/phase5/` — nessun numero è stato inventato o stimato a mano. Codice, dataset intermedi e risultati completi sono negli artifact elencati in sezione M.

---

## A. Registry semantic cleanup

Verificate individualmente le 10 strategie con mismatch confermato in Phase 4:

| Strategia | Registry status (prima) | Inp reale | Reachable? | Live impl. reale | Rationale storico |
|---|---|---|---|---|---|
| AMD_CONT | ACTIVE/true | `InpUseStrat_AMD_Cont=false` | Sì | codice presente, corretto 17/07 | mai profittevole, PF 0.53-0.71 |
| BJORGUM | ACTIVE/true | `InpStrat_BJORGUM=false` | Sì | codice presente | -8.6R, 5/6 anni negativi |
| FVG_MIT | ACTIVE/true | `InpStrat_FVG_Mit=false` | **NO** (redirect NXR `InpNXR_Enable=false` hardcoded) | codice morto per costruzione | redesign 17/07 su NXR, mai attivabile |
| IFVG | ACTIVE/true | `InpStrat_IFVG=false` | **NO** (stesso redirect NXR) | codice morto per costruzione | idem FVG_MIT |
| LDN_REVERSAL | ACTIVE/true | `InpUseStrat_LdnReversal=false` | Sì | codice presente | mai profittevole, PF 0.36-0.78 |
| LIQ_VOID | ACTIVE/true | `InpUseStrat_LiqVoid=false` | **NO nella config di default** (richiede `InpUseHTFBias=true`, default false) | codice presente ma dormiente | mai testata per davvero nella config di produzione |
| OB_MIT | ACTIVE/true | `InpStrat_OB_Mit=false` | **NO** (stesso redirect NXR) | codice morto + duplicato letterale di ORDER_BLOCK | idem IFVG/FVG_MIT |
| RANGE_FADE | ACTIVE/true | `InpUseStrat_RangeFade=false` | Sì | riscritta 17/07 | gate di conferma si attiva 6x/10y, tutte in perdita |
| THREE_BAR_DELIVERY_BREAK | ACTIVE/true | `InpUseStrat_CISD=false` | Sì | rinominata onestamente da CISD 17/07 | PF 0.51-0.65 sulla ricetta esatta |
| TURTLE_SOUP | ACTIVE/true | `InpStrat_TurtleSoup=false` | Sì | codice presente | mai robustamente profittevole, PF max 0.94 |

**Correzione applicata** (commit `a7f5a98`): `stato` in `knowledge/strategy_database.json` cambiato da `"attiva"` a `"attiva nel codice, disabilitata in produzione reale"` (stessa convenzione già usata per DISP_REBAL) per tutte e 10, con `decisione_corrente` popolato per-strategia col rationale sopra. Rigenerato e validato: tutte e 10 ora `status: DISABLED, default_enabled: false`, coerenti con l'`Inp*` reale. **Nessuna modifica alla logica di trading** — `NXS_StrategyRegistry.mqh` è risultato bit-identico (status/default_enabled non sono codificati lì), nessuna ricompilazione necessaria.

---

## B. Market State Dataset v1

4809 barre H4 XAUUSD (2019-02-03→2022-02-03), costruite da 148.097.525 tick Dukascopy già validati (Phase 4), OHLC su BID, allineamento UTC fisso. 29 colonne, tutte causali (rolling trailing, prev-day/week shiftati, nessun future pivot). Dettaglio completo: [[phase5_market_state_dataset_schema]]. Warmup NaN concentrato nelle prime 75 barre (finestra più lunga: percentile ATR a 252 barre).

## C. Event layer

8618 eventi su 9 famiglie, detector dichiarati ex-ante (nessuna soglia scelta dopo aver visto un outcome). Conteggi e limitazioni di calibrazione trovate (PULLBACK degenerato all'83% delle barre; condizione BREAKOUT_x_TREND_PERSISTENCE risultata tautologica): [[phase5_event_dataset_and_baseline_methodology]].

## D. Outcome Surface

40 barre di orizzonte, nessuna gestione dinamica. 4 famiglie (BREAKOUT/SWEEP/RECLAIM/RETEST) hanno un'invalidation naturale → R-outcome nativi in `outcomes_v1.csv`. Le altre 5 (VOLATILITY_EXPANSION/DISPLACEMENT/COMPRESSION_RELEASE/PULLBACK/FAILED_BREAKOUT) non hanno un livello di invalidation implicito nella loro stessa definizione → SOLO outcome ATR-normalizzati, mai uno stop inventato. 1861 outcome R-based, 6756 ATR-normalizzati.

## E. Baseline matching

Popolazione di controllo per cella (terzile volatilità × terzile trend × anno), stessa direzione dell'evento — mai barre casuali indiscriminate. Metodologia completa e caveat di indipendenza delle osservazioni: [[phase5_event_dataset_and_baseline_methodology]].

## F-J. Conditional edge tests, probability engine, classificazione

Split 70/30 cronologico dichiarato PRIMA di ogni risultato: discovery = 2019-02-03→2021-03-12 (n=3366 barre), validation = 2021-03-12→2022-02-03 (n=1443 barre). Valuta comune per tutti i confronti evento-vs-baseline: outcome ATR-normalizzato a soglia primaria +1×ATR prima di -1×ATR (soglie complete 0.25-3× riportate nei dati). Probability engine: Wilson CI95 + Beta-Binomial (prior non informativo Beta(1,1)) su ogni stima — dettaglio: [[phase5_probability_engine_output]].

### Risultato per evento, da solo (risponde Q1)

| Famiglia | n | Classificazione | ΔP (validation) | Note |
|---|---|---|---|---|
| BREAKOUT | 724 | NO_EDGE | +0.001 | nessun vantaggio sulla baseline matched |
| FAILED_BREAKOUT | 315 | NO_EDGE | -0.313 | atteso: per definizione il breakout è già fallito |
| SWEEP | 500 | NO_EDGE | +0.022 | lo sweep DA SOLO non porta edge |
| **RECLAIM** | **300** | **SUPPORTED_EDGE** | **+0.299** | vedi sezione K, unico componente promosso |
| RETEST | 337 | NO_EDGE | +0.001 | — |
| DISPLACEMENT | 188 | NO_EDGE | +0.087 | direzione positiva ma non supera le soglie di robustezza |
| COMPRESSION_RELEASE | 482 | OPPOSITE_EDGE* | +0.074 | *segno borderline vicino a zero in discovery (-0.017), non un'inversione drammatica — vedi nota sotto |
| VOLATILITY_EXPANSION | 1782 | NO_EDGE | +0.043 | — |
| PULLBACK | 3988 | NO_EDGE | +0.007 | detector degenerato (sezione C), risultato da leggere con cautela |

*Nota su COMPRESSION_RELEASE*: la regola di classificazione OPPOSITE_EDGE (dichiarata ex-ante, sezione J) si attiva su un'inversione di segno discovery→validation, ma qui l'inversione è fra un valore quasi-nullo (-0.017) e uno modesto (+0.074) — onestamente più vicino a "nessun effetto consistente" che a un vero effetto opposto forte. Riportato secondo la regola meccanica dichiarata, ma senza sovra-interpretarlo come un'inversione drammatica.

### Le 5 interazioni predefinite (risponde Q2/Q5)

| Interazione | n | Classificazione | ΔP (validation) |
|---|---|---|---|
| BREAKOUT × VOLATILITY_EXPANSION | 449 | NO_EDGE | +0.059 |
| BREAKOUT × TREND_PERSISTENCE | 724 | NO_EDGE | +0.001 (condizione tautologica, 100% dei BREAKOUT la soddisfa) |
| SWEEP/RECLAIM × LOCATION | 378 | NO_EDGE | -0.003 |
| COMPRESSION_RELEASE × DIRECTIONAL_EFFICIENCY | 147 | OPPOSITE_EDGE* | +0.111 |
| DISPLACEMENT × VOLATILITY_STATE | 34 | INSUFFICIENT_SAMPLE | n/a (n_validation=9) |

**Nessuna delle 5 interazioni predefinite mostra un edge condizionale oltre la baseline in questo dataset.** Questo è di per sé un risultato onesto e utile (non un fallimento della pipeline): il condizionamento a uno stato di mercato statico (trend/volatilità/location generici) non ha aggiunto valore misurabile sopra l'evento nudo, per nessuna delle 5 combinazioni testate.

**Il vero risultato "evento condizionato" di questa fase non è una delle 5 interazioni pre-registrate, ma la relazione SWEEP→RECLAIM stessa**: SWEEP da solo è NO_EDGE (ΔP≈0.02), ma la specifica transizione di stato "sweep + conferma di reclaim entro 10 barre" isola un edge fortissimo (ΔP≈+0.24/+0.30). Non è tecnicamente una delle 5 interazioni predefinite (RECLAIM è un evento a sé, non "SWEEP condizionato a una variabile di stato statica") — ma è esattamente il tipo di scoperta che l'ontologia MARKET STATE→EVENT→SETUP era pensata per far emergere: l'informazione utile viveva nella sequenza/conferma dell'evento, non in una feature di stato pre-esistente.

## K. Edge Component promosso

**1 componente promosso su un massimo di 3 consentiti** — nessun altro candidato ha superato NO_EDGE/OPPOSITE_EDGE/INSUFFICIENT_SAMPLE, e non sono stati forzati candidati aggiuntivi per riempire il tetto.

**EC-LIQUIDITY_SWEEP_RECLAIM** — vedi record completo in [[edge_component_records_v1]]. Sintesi: P(+1×ATR prima di -1×ATR) = 75-81% (discovery/validation) vs baseline matched 51%, CI95 mai sovrapposte, effetto stabile su BUY/SELL/ogni anno/dopo trimming del 10% migliori outlier. **Non ancora un edge eseguibile**: eredita direttamente il rischio `SHADOW_EXECUTION_ASSUMPTION` già catalogato in Phase 4 (un fenomeno di reclaim quasi identico è collassato da PF shadow 5.80 a PF reale 0.78-0.80 per slippage strutturale) — priorità massima per una validazione di esecuzione reale in Phase 6.

## L. SAR Dukascopy — validazione indipendente

Report completo: [[sar_dukascopy_independent_validation]]. Import di un Simbolo Personalizzato MT5 (`XAUUSD_DSC`) interamente scriptato via API MQL5 (`CustomSymbolCreate`/`CustomTicksAdd`, nessuna interazione GUI — verificato empiricamente in questa fase, capacità non documentata prima in questo progetto), popolato con gli stessi 148.097.525 tick Dukascopy già validati in Phase 4 (0 errori, corrispondenza esatta).

**Verifiche pre-backtest** (tutte superate, dettaglio nel report):
- Allineamento H4: prime 10 barre tutte sulla griglia 4h corretta (stesso offset `InpServerGMTOffset=2` usato ovunque nel progetto).
- Uso di tick reali confermato dalla stessa MT5 (report ufficiale: "Qualità dello Storico: 99% ticks reali"), Model=4.
- Spot-check tick count 2019-02-04: 71.921 vs 72.049 attesi (differenza 0.18%, verosimilmente deduplicazione tick nativa di MT5).

**Risultato backtest SAR congelato** (H4, SL 1.0×ATR, TP 6.0×ATR, candle-align/pressure-contrary off, RAW, no BE/trailing, 2019-02-03→2022-02-03, stesso identico segnale del baseline broker):

| Fonte dati | PF | n trade | BUY | SELL |
|---|---|---|---|---|
| Broker XM (MT5 real-tick, baseline storico) | 1.281 | 240 | PF 1.70 | PF 0.84 (debole) |
| Python engine, pre-2023 Dukascopy | 0.93 / 0.97 | — | debole | PF 0.73-0.78 (debole) |
| **MT5-nativo, Dukascopy tick (questa fase)** | **0.61** | **237** | **WR 11.0%** | **WR 9.9%** |

**Verdetto: `SAR_EXTERNAL_CONFIRMATION_FAIL`.** PF 0.61 su un campione ampio (237 trade, non un campione sottile da scartare), nessun rescue applicato. Su tre fonti dati indipendenti per lo stesso segnale congelato, 2 su 3 (entrambe basate su Dukascopy) sono nettamente negative; solo la fonte broker XM è positiva. A differenza dei due data point precedenti, qui Long e Short sono uniformemente deboli (non si replica l'asimmetria BUY-forte/SELL-debole del broker) — suggerendo che il PF 1.281 misurato su XM sia specifico di quella fonte dati/periodo, non una proprietà robusta e trasferibile del segnale PSAR+EMA9/21.

## M. Output — artifact prodotti

- Report principale: questo file.
- Market State Dataset: `server/research_scripts/phase5/data/market_state_dataset_v1.csv` + schema [[phase5_market_state_dataset_schema]]
- Event dataset: `server/research_scripts/phase5/data/events_v1.csv` + metodologia [[phase5_event_dataset_and_baseline_methodology]]
- Outcome surface: `server/research_scripts/phase5/data/outcomes_v1.csv`
- Risultati edge completi (JSON): `server/research_scripts/phase5/data/edge_results_v1.json`
- Probability engine: `server/research_scripts/phase5/stats_utils.py` + output [[phase5_probability_engine_output]]
- Edge component: [[edge_component_records_v1]]
- SAR Dukascopy independent validation: [[sar_dukascopy_independent_validation]]
- Import Simbolo Personalizzato Dukascopy (nuovo, riusabile per future validazioni indipendenti): `server/research_scripts/convert_dukascopy_for_mt5_import.py` + `MQL5/Scripts/NXS_ImportDukascopyCustomSymbol.mq5`
- Log trade e report ufficiale del backtest SAR Dukascopy: `results/phase5_sar_dukascopy/sar_dukascopy_3y_trades.csv` + `sar_dukascopy_3y_report.htm`
- Codice sorgente completo pipeline: `server/research_scripts/phase5/*.py`

---

## Risposte finali

**1. Quali eventi mostrano edge da soli?**
Solo RECLAIM (SUPPORTED_EDGE). Tutti gli altri 8 (BREAKOUT, FAILED_BREAKOUT, SWEEP, RETEST, DISPLACEMENT, VOLATILITY_EXPANSION, PULLBACK) sono NO_EDGE da soli; COMPRESSION_RELEASE è un'inversione borderline non robusta.

**2. Quali NON mostrano edge da soli ma lo mostrano condizionati allo stato?**
Nessuna delle 5 interazioni predefinite (evento × variabile di stato statica) ha rivelato un edge condizionale. L'unico condizionamento che ha funzionato non è stato "evento + stato statico" ma "evento + conferma della sua stessa evoluzione temporale": SWEEP (NO_EDGE da solo) diventa un edge forte quando si osserva la sua RECLAIM (conferma entro 10 barre) — un condizionamento sequenziale/di evento, non uno statico.

**3. Quali market-state variables aggiungono informazione vera?**
Nessuna delle variabili di stato statiche testate nelle 5 interazioni (volatilità, trend/persistenza, location generica nel range, directional efficiency) ha aggiunto informazione misurabile oltre l'evento nudo in questo dataset. L'informazione che ha funzionato è strutturale/di sequenza (sweep→reclaim), non una feature di stato al momento dell'evento.

**4. Quali sono ridondanti?**
Il condizionamento "trend EMA allineato + persistenza ≥ mediana" per BREAKOUT è risultato ridondante (100% dei breakout lo soddisfano già, zero potere discriminante) — segnala che la definizione di breakout usata qui è già quasi tautologicamente allineata al trend, non un'informazione aggiuntiva indipendente.

**5. Quali interazioni mostrano effetto opposto?**
COMPRESSION_RELEASE (da solo e nell'interazione con DIRECTIONAL_EFFICIENCY) è classificato OPPOSITE_EDGE dalla regola dichiarata ex-ante, ma il flip di segno è vicino allo zero (discovery ≈-0.02, validation ≈+0.07/+0.11) — da trattare come inconcludente/instabile più che come una vera inversione forte.

**6. Quali edge components meritano Phase 6?**
EC-LIQUIDITY_SWEEP_RECLAIM è l'unica priorità chiara: serve una validazione di esecuzione reale (fill a mercato dopo la conferma H4, non alla chiusura idealizzata) prima di poter essere considerato un edge eseguibile, esattamente il test che ha smontato il fenomeno gemello di Phase 4. Priorità secondaria (non promossa, ma degna di un retest con detector corretto): COMPRESSION_RELEASE, il cui detector attuale (basato su PULLBACK-adiacente) merita di essere ririlevato con una definizione di trend/pullback meno degenere prima di trarre conclusioni definitive. Nota collegata: SAR (sezione L) è ora `SAR_EXTERNAL_CONFIRMATION_FAIL` — non merita ulteriore investimento come segnale standalone finché non emerge un'ipotesi causale specifica sul perché differisca così nettamente fra fonti dati.

**7. Cosa è cambiato rispetto al vecchio approccio strategy-first?**
Il vecchio approccio avrebbe richiesto inventare/nominare una nuova "strategia" per ogni variante di detector e backtestarla isolatamente, spesso senza un baseline comparabile esplicito. Qui l'unità di ricerca è stata l'evento/setup, non la strategia: lo stesso identico caveat di esecuzione (`SHADOW_EXECUTION_ASSUMPTION`) scoperto in Phase 4 su una strategia nominata (WICK_SWEEP_RECLAIM, M15) è riemerso automaticamente su un componente ottenuto con un detector indipendente, a un timeframe diverso (H4, rolling range invece di livelli wick) — la stessa lezione di rischio si è generalizzata invece di dover essere riscoperta da zero. La pipeline ha inoltre imposto strutturalmente un confronto con baseline matched e una separazione esplicita fra "il fenomeno è reale" e "il fenomeno è eseguibile", cosa che un singolo numero di PF storicamente confondeva in un'unica cifra. Il caso SAR (sezione L) è l'esempio più diretto: il vecchio approccio aveva dichiarato SAR "confermata positiva" (PF 1.281) sulla sola fonte dati del broker; il nuovo approccio ha imposto esplicitamente una validazione su una fonte dati indipendente come passo dovuto, non opzionale, rivelando che il risultato positivo non sopravvive al cambio di fonte dati (PF 0.61) — una domanda che l'approccio strategy-first, fermandosi al primo backtest positivo, non si sarebbe posta.
