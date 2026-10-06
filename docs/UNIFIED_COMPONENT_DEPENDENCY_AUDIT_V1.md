# Unified Component Dependency Audit V1

**Stato:** mappa concettuale, non ancora committata. Nessun codice/runtime/registry modificato, nessun backtest nuovo.

**Disciplina di confidenza, dichiarata esplicitamente per ogni affermazione:** **CODE_VERIFIED** (letto nel codice MQL5 reale, come in `UNIFIED_COMPONENT_CATALOG_V1.md`) vs **NAME_PATTERN_INFERRED** (dedotto da nome registry/famiglia, non ancora letto nel codice) vs **HISTORICAL_NOTE** (documentato in una nota vault già esistente). Solo 7 delle 83 strategie sono oggi CODE_VERIFIED a livello di componente (i 7 del catalogo precedente). Il resto di questo documento, dove va oltre quei 7, è esplicitamente marcato come stima preliminare, non conclusione.

---

## 1. Canonical component identity

| Componente (da `UNIFIED_COMPONENT_CATALOG_V1.md`) | Consumer(s) | Relazione | Confidenza |
|---|---|---|---|
| `external_h1_structure_trend` (`g_structH1.trend`) | ORDER_BLOCK, FVG_CONT | **EXACT_SHARED_PRIMITIVE** — stessa variabile globale, stessa condizione, nessuna differenza di implementazione | CODE_VERIFIED |
| `smc_reaction_confirmation` (`NXS_SMCReactionOK()`) | ORDER_BLOCK, FVG_CONT | **EXACT_SHARED_PRIMITIVE** — stessa funzione chiamata identicamente | CODE_VERIFIED |
| `order_block_zone_location` / stato `g_obBuy`/`g_obSell` | ORDER_BLOCK, **OB_MIT** (non uno dei 7, ma documentato in Phase 7.12/7.14 come "chiamata diretta, stessa mutazione di stato") | **EXACT_SHARED_PRIMITIVE** | HISTORICAL_NOTE (Phase 7.12 priority queue, Phase 7.14) |
| Trend via EMA, 3 periodi diversi: `ema50_slope_trend` (ADX_RSI), `ema200_trend_filter` (MACD), `ema9_21_cross_filter` (SAR) | ADX_RSI, MACD, SAR | **SAME_PHENOMENON_DIFFERENT_PROXY** — tutti e 3 rispondono a "c'è un trend", con formula e periodo diversi, mai verificato se producono informazione statisticamente distinguibile | CODE_VERIFIED (esistenza dei 3 componenti) + **UNKNOWN** (se ridondanti in pratica — richiede l'audit di correlazione di §7) |
| `liquidity_sweep_detection` (`NXS_DetectSweepExt`/`sw`) | LIQ_SWEEP (e, per costruzione del motore condiviso, qualunque altra strategia che consumi lo stesso `sw` — non verificato quali altre lo facciano) | **UNKNOWN** (il motore è condiviso per design, ma non ho verificato in questo audit se altre strategie dei 7 lo consumano) | CODE_VERIFIED (solo per LIQ_SWEEP) |
| `delivery_candle_filter` (LIQ_SWEEP), `breakout_cooldown_filter` (BREAKOUT_ACC) | — | **INDEPENDENT** tra loro — nessuna relazione trovata, pattern di implementazione simile (entrambi filtri locali alla funzione) ma non condivisione di stato/primitiva | CODE_VERIFIED |
| `range_breakout_location` (BREAKOUT_ACC) vs `order_block_zone_location`/`fair_value_gap_location` | — | **CORRELATED_BUT_DISTINCT** (ipotesi, non verificata): tutti e 3 misurano "posizione del prezzo rispetto a un livello strutturale", ma con costruzione geometrica diversa (range N-barre vs zona OB vs gap 3-candele) | UNKNOWN |
| `adx_trend_strength` (ADX, ampiezza) vs i 3 proxy di trend sopra (direzione) | — | **INDEPENDENT** — ADX misura la FORZA del trend, non la sua direzione; concettualmente un asse diverso anche se spesso usato insieme alla direzione nello stesso trigger (es. ADX_RSI stesso) | CODE_VERIFIED |

**Precedente già risolto correttamente in questo stesso progetto** (non un rischio, un esempio da seguire): `NEXUS - LEVEL_REACTION, Merge Vero di PIVOT_WICK STRUCT_REACT MALAYSIAN_SNR (06-09).md` ha già affrontato esattamente questo problema per 3 strategie non tra i 7 di oggi — e ha concluso che **PIVOT_WICK (livelli wick-based) e MALAYSIAN_SNR (livelli "a corpo") sono CORRELATED_BUT_DISTINCT, non ridondanti** ("un vero secondo tipo di livello, non un duplicato della fonte 1"), mentre STRUCT_REACT è stato declassato a bonus di confluenza (riusa `g_reaction`, la stessa infrastruttura SMC di ORDER_BLOCK/FVG) invece che fonte primaria indipendente — **PARENT_CHILD rispetto alla stessa infrastruttura SMC condivisa trovata in §1 sopra**.

## 2. Component class

| Componente | Classe |
|---|---|
| `adx_trend_strength`, `ema50_slope_trend`, `rsi_momentum_condition` (ADX_RSI) | MARKET_EVIDENCE |
| `macd_momentum`, `ema200_trend_filter` (MACD) | MARKET_EVIDENCE |
| `parabolic_sar_trend_direction`, `ema9_21_cross_filter` (SAR) | MARKET_EVIDENCE |
| `sar_candle_alignment_filter`, `sar_pressure_contrary_filter` (SAR) | **ELIGIBILITY_CONTROL** — non misurano un fenomeno nuovo, filtrano quando l'evidenza di trend è "abbastanza buona" per agire |
| `liquidity_sweep_detection`, `delivery_candle_filter` (LIQ_SWEEP) | MARKET_EVIDENCE |
| `order_block_zone_location`, `external_h1_structure_trend` (ORDER_BLOCK/FVG_CONT) | MARKET_EVIDENCE |
| `smc_reaction_confirmation` (ORDER_BLOCK/FVG_CONT) | **ELIGIBILITY_CONTROL** — confirma che il mercato ha reagito, non è di per sé una nuova osservazione di mercato indipendente |
| `fair_value_gap_location` (FVG_CONT) | MARKET_EVIDENCE |
| `range_breakout_location` (BREAKOUT_ACC) | MARKET_EVIDENCE |
| `breakout_cooldown_filter` (BREAKOUT_ACC) | **ELIGIBILITY_CONTROL** — esattamente il caso citato dall'utente: un controllo di frequenza, non evidenza di mercato. **Nessun componente di questo catalogo cade in RISK_CONTROL/EXECUTION_CONTROL/POSITION_MANAGEMENT** — questi vivono un livello più in basso (`nexus_policy`, preflight, `NXS_DoBuy`/`NXS_DoSell`), fuori dallo scope dei 7 componenti analizzati, coerente con la separazione Market Intelligence/Risk Engine/Execution di `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` §9 |
| Tutti i trigger finali (`*_entry_trigger`/`*_trigger`) | TRIGGER |

## 3. Temporal identity

| Componente | TF proprio | Observation point | Persistence/freshness | Dipendenza da altro TF | Parent consumer |
|---|---|---|---|---|---|
| `adx_trend_strength`, `rsi_momentum_condition`, `ema50_slope_trend` | TF effettivo (`NXS_EffTF()`) | chiusura barra | ricalcolato ogni barra, nessuno stato persistente | nessuna | ADX_RSI |
| `macd_momentum`, `ema200_trend_filter` | TF effettivo | chiusura barra | nessuno stato persistente | nessuna | MACD |
| `parabolic_sar_trend_direction`, `ema9_21_cross_filter`, `sar_candle_alignment_filter` | TF effettivo | chiusura barra | nessuno stato persistente | nessuna | SAR |
| `sar_pressure_contrary_filter` | **M15, indipendente dal TF effettivo della strategia** | chiusura barra M15, finestra di 8 barre | finestra rolling, nessuno stato tra chiamate | **Sì — dipende sempre da M15 anche se la strategia opera su un TF diverso** | SAR |
| `liquidity_sweep_detection` | TF effettivo | momento di conferma del detector esterno | stato nel motore condiviso `NXS_DetectSweepExt`, non locale alla strategia | nessuna nota in questo audit | LIQ_SWEEP (e potenzialmente altri consumer non verificati) |
| `delivery_candle_filter` | TF effettivo | chiusura barra | nessuno stato | nessuna | LIQ_SWEEP |
| `order_block_zone_location` | **TF dichiarato della strategia (`NXS_Profile_TF`), TF-scoped dopo il fix `17da794`** | chiusura barra, solo sul pass TF corretto | **stato persistente tra barre** (`g_obBuy`/`g_obSell`) — esattamente la classe di variabile che ha causato il defect pre-fix | nessuna (dopo il fix) | ORDER_BLOCK, OB_MIT |
| `external_h1_structure_trend` | **H1, indipendente dal TF effettivo** | chiusura barra H1 | persistente fino al prossimo aggiornamento H1 | **Sì — sempre H1** | ORDER_BLOCK, FVG_CONT |
| `fair_value_gap_location` | TF effettivo | chiusura barra | nessuno stato persistente (ricalcolato su 3 barre a finestra scorrevole) | nessuna | FVG_CONT |
| `range_breakout_location`, `breakout_acceptance_trigger` | **TF dichiarato della strategia, TF-scoped dopo il fix `651d3a2`** | chiusura barra, solo sul pass TF corretto | nessuno stato persistente nel componente location; il trigger sì (vedi sotto) | nessuna (dopo il fix) | BREAKOUT_ACC |
| `breakout_cooldown_filter` | TF dichiarato | — | **stato persistente per direzione** (`lastFireTime[0/1]`) — stessa classe di stato del defect pre-fix | nessuna (dopo il fix) | BREAKOUT_ACC |

**Osservazione strutturale (non assunta, verificata su tutti i 7):** ogni componente con stato persistente tra barre (`order_block_zone_location`, `breakout_cooldown_filter`) è esattamente quello coinvolto nel defect storico `CROSS_TIMEFRAME_STATE_CONTAMINATION` della sua strategia — nessuna coincidenza, è la stessa classe di rischio descritta in `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` §6. I componenti stateless (location/evidence ricalcolati ogni barra) non hanno mai avuto questa classe di defect.

## 4. Dependency graph (le 4 relazioni richieste)

```
ORDER_BLOCK ──┬── order_block_zone_location (proprio) ──> order_block_retest_trigger
              ├── external_h1_structure_trend (CONDIVISO) ──┐
              └── smc_reaction_confirmation (CONDIVISO) ─────┤
                                                              │
FVG_CONT ─────┬── fair_value_gap_location (proprio) ──> fvg_continuation_trigger
              ├── external_h1_structure_trend (CONDIVISO) ───┤ (stesso upstream di ORDER_BLOCK)
              └── smc_reaction_confirmation (CONDIVISO) ──────┘ (stesso upstream di ORDER_BLOCK)

ADX_RSI ── ema50_slope_trend ─┐
MACD ────── ema200_trend_filter ─┼── SAME_PHENOMENON_DIFFERENT_PROXY (trend), nessun upstream condiviso nel codice,
SAR ─────── ema9_21_cross_filter ─┘  solo somiglianza semantica non ancora verificata empiricamente (§7)

LIQ_SWEEP ── liquidity_sweep_detection (upstream: NXS_DetectSweepExt, motore condiviso esterno)
                                        └──> delivery_candle_filter ──> sweep_reversal_trigger
          (nessun secondo consumer dei 7 verificato in questo audit)

BREAKOUT_ACC ── range_breakout_location (proprio, nessun upstream condiviso)
                                        └──> breakout_acceptance_trigger ── [breakout_cooldown_filter] ──> output
          (nessuna relazione trovata con gli altri 6 componenti)
```

**Lettura:** ORDER_BLOCK e FVG_CONT sono le uniche due, tra i 7, che condividono realmente upstream primitivi (2 su 2 verificati). ADX_RSI/MACD/SAR condividono solo un fenomeno semantico, non codice. LIQ_SWEEP e BREAKOUT_ACC sono isolati rispetto agli altri 6 in questo audit.

## 5. Top 10 double-counting risks

| # | Rischio | Severità | Causa | Componenti | Mitigazione proposta | Confidenza |
|---|---|---|---|---|---|---|
| 1 | ORDER_BLOCK e FVG_CONT contati come 2 evidenze indipendenti sul contesto H1/reazione | **ALTA** | Stessa variabile/funzione, non solo stesso fenomeno | `external_h1_structure_trend`, `smc_reaction_confirmation` | In qualunque aggregazione futura, trattare questi 2 come un singolo nodo upstream con 2 consumer, non come 2 osservazioni | CODE_VERIFIED |
| 2 | ORDER_BLOCK e OB_MIT contati come 2 strategie indipendenti | **CRITICA** | "Chiamata diretta, stessa mutazione di stato" (Phase 7.12/7.14) | `order_block_zone_location` | Trattare OB_MIT come consumer dello stesso componente, non come strategia a sé; già riflesso nel `defect_status` propagato in Phase 7.14 | HISTORICAL_NOTE |
| 3 | ADX_RSI, MACD, SAR trattati come 3 evidenze di trend indipendenti | MEDIA | 3 proxy diversi (pendenza EMA50, livello vs EMA200, cross EMA9/21) dello stesso fenomeno "c'è un trend" | `ema50_slope_trend`, `ema200_trend_filter`, `ema9_21_cross_filter` | Applicare `feature_redundancy_audit_v1.md` (Pearson/Spearman) a questi 3 proxy prima di qualunque aggregazione (§7) | UNKNOWN — non verificato empiricamente |
| 4 | Famiglia SCALP (30/83 strategie) trattata come 30 idee indipendenti | **ALTA a livello di registry** | Nomi come `SAR_ADX20`, `SAR_FLIP`, `ORDER_BLOCK_V2`, `SILVER_BULLET_V2`, `SH_BMS_RTO_V2`, `TSI_EXTREME` suggeriscono varianti di esecuzione/timeframe di famiglie già contate altrove (MOMENTUM, SMC, LIQUIDITY), non fenomeni nuovi | 30 strategy_id della famiglia `SCALP` | Verificare per ciascuna se è un wrapper/variante parametrica della base family prima di contarla come fenomeno a sé — non fatto in questo audit (fuori scope dei 7) | NAME_PATTERN_INFERRED |
| 5 | MALAYSIAN_SNR_V2_STAGE1/STAGE3/RETEST/RETEST_OUTRANGE + MALAYSIAN_SNR base | MEDIA | 4 varianti nominative + 1 base, nomi suggeriscono stage di una stessa pipeline, non 5 idee | 5 strategy_id | Lettura codice diretta (non fatta qui) | NAME_PATTERN_INFERRED |
| 6 | TURTLE_SOUP_CHOCH / _DBLBODY / _NEAR + TURTLE_SOUP base | MEDIA | Stesso pattern del #5 | 4 strategy_id | Lettura codice diretta (non fatta qui) | NAME_PATTERN_INFERRED |
| 7 | Cluster FVG/IFVG: FVG_CONT, FVG_CONT_V2, FVG_MIT, FVG_MIT_WINDOW, IFVG, IFVG_CHOCH_WINDOW, LIQ_VOID | MEDIA-ALTA | `docs/architecture/17_STRATEGY_REGISTRY_RECONCILIATION.md` (21/07, stale ma indicativo) dichiara già `LIQ_VOID` come proxy di ricerca di `FVG_CONT` — segnale che il cluster potrebbe collassare a 1-2 fenomeni (location del gap + variante mitigation-vs-continuation) | 7 strategy_id | Stessa decomposizione fatta per FVG_CONT in `UNIFIED_COMPONENT_CATALOG_V1.md`, estesa agli altri 6 — non fatta qui | NAME_PATTERN_INFERRED + 1 HISTORICAL_NOTE |
| 8 | LEVEL_CONFLUENCE_M5 e LEVEL_REACTION_M5 come fenomeni distinti dalle versioni non-M5 | BASSA | Stesso merge già documentato (PIVOT_WICK+MALAYSIAN_SNR+STRUCT_REACT bonus), probabile puro duplicato a timeframe diverso, non nuovo fenomeno | 2 strategy_id | Verificare se sono solo un `NXS_Profile_TF` diverso sullo stesso codice — non fatto qui | NAME_PATTERN_INFERRED |
| 9 | MACD_SMA200 potenzialmente ridondante con il filtro `ema200_trend_filter` già nativo di MACD | MEDIA | Il nome suggerisce lo stesso filtro di trend SMA/EMA200 già trovato DENTRO `NXS_Strat_MACD` in questo stesso audit (§1 del catalogo) — possibile che sia una duplicazione quasi esatta con un indicatore leggermente diverso (SMA vs EMA) | MACD, MACD_SMA200 | Lettura codice diretta di `NXS_Strat_MacdSma200()` (riga 567, non letta in questo audit) | NAME_PATTERN_INFERRED |
| 10 | RSI_DIV vs RSI_DIV_PINE | BASSA | Probabile stessa idea (divergenza RSI), due implementazioni (nativa vs porting da Pine Script) | RSI_DIV, RSI_DIV_PINE | Lettura codice diretta — non fatta qui | NAME_PATTERN_INFERRED |

## 6. Phenomenon collapse — stima preliminare, non definitiva

**Risposta diretta alla domanda:** sulla base dell'evidenza disponibile (7 componenti CODE_VERIFIED + pattern di naming sulle restanti 76 + 1 precedente storico diretto già nel progetto), **è altamente plausibile che le 83 strategie collassino in un numero sostanzialmente più piccolo di fenomeni di mercato distinti** — ma il numero esatto non è determinabile senza la stessa verifica diretta del codice fatta per i 7 di oggi, estesa al resto. Non forzo una cifra precisa.

**Evidenza diretta già nel progetto** (non ipotizzata): `LEVEL_REACTION` è letteralmente il merge dichiarato di 3 strategie precedenti in 2 fonti di livello distinte + 1 bonus di confluenza — un fenomeno di collasso già eseguito e documentato una volta.

**Prima tassonomia di macro-fenomeni** (bottom-up da famiglia registry + i 7 componenti verificati, non forzata dove l'evidenza manca):

| Macro-fenomeno | Famiglia/componenti che vi contribuiscono (verificato o plausibile) | Confidenza |
|---|---|---|
| **Trend/direzione** | `ema50_slope_trend`, `ema200_trend_filter`, `ema9_21_cross_filter`, `external_h1_structure_trend` — famiglia TREND (6) | CODE_VERIFIED per 4 componenti; se e quanto collassano tra loro: UNKNOWN |
| **Momentum (ampiezza, non direzione)** | `adx_trend_strength`, `rsi_momentum_condition`, `macd_momentum` — famiglia MOMENTUM (5: ADX_RSI, MACD, RSI_DIV, SAR, TSI) | CODE_VERIFIED per 3 |
| **Liquidity event (sweep/reclaim)** | `liquidity_sweep_detection` — famiglia LIQUIDITY (9) + probabilmente parte di SCALP (WICK_SWEEP_*, TURTLE_SOUP_*) | CODE_VERIFIED per 1, resto NAME_PATTERN_INFERRED |
| **Structure/location (zone persistenti)** | `order_block_zone_location`, `fair_value_gap_location` — famiglia SMC (8) + parte di SCALP (ORDER_BLOCK_V2, FVG_CONT_V2, ecc.) | CODE_VERIFIED per 2 |
| **Reazione/confluenza (bonus, non fonte primaria)** | `smc_reaction_confirmation` — già declassato a bonus in LEVEL_REACTION | CODE_VERIFIED + HISTORICAL_NOTE |
| **Eligibility/qualità del segnale (non un fenomeno di mercato)** | `delivery_candle_filter`, `sar_candle_alignment_filter`, `sar_pressure_contrary_filter`, `breakout_cooldown_filter` | CODE_VERIFIED — **questi vanno esclusi dal conteggio dei fenomeni, per costruzione (§2)** |
| **Volatility/expansion** | Famiglia VOLATILITY (3: BB_SQUEEZE, BOLLINGER, RANGE_FADE) + `range_breakout_location` (BREAKOUT_ACC, famiglia TREND non VOLATILITY — discrepanza di family tag da segnalare, non risolta qui) | NAME_PATTERN_INFERRED |
| **Session/time** | Famiglia SESSION (5) + AMD (3) | NAME_PATTERN_INFERRED, nessun componente dei 7 verificato in questa famiglia |
| **Mean reversion** | Parte di VOLATILITY (BOLLINGER, RANGE_FADE) — da non confondere con "volatility/expansion" sopra, sono ipotesi opposte (reversion vs breakout) nonostante la stessa family tag registry | NAME_PATTERN_INFERRED — **la family tag "VOLATILITY" del registry conflating due fenomeni opposti è essa stessa un gap di taxonomy, non solo le strategie** |
| **Pattern (non ancora collassabile)** | ELLIOTT — unico membro della famiglia PATTERN, nessuna evidenza per collassarlo altrove | NAME_PATTERN_INFERRED |

**Osservazione sulla famiglia SCALP (30 strategie, la più grande):** non è un fenomeno di mercato — è un tag di variante di esecuzione/timeframe. Molti dei suoi membri sono nominalmente varianti di strategie già contate in altre famiglie (vedi rischi #4-#8 di §5). Se confermato per code-reading (non fatto qui), la famiglia SCALP non aggiungerebbe nuovi fenomeni, solo nuove esecuzioni degli stessi fenomeni — il che sposterebbe la stima del numero di fenomeni distinti sostanzialmente sotto 83, forse nell'ordine delle **8-10 macro-famiglie della tabella sopra**, ma questo resta un limite superiore plausibile, non una cifra verificata.

## 7. Gap non risolvibili senza nuovi test/letture di codice

- Se i 3 proxy di trend (ADX_RSI/MACD/SAR) sono empiricamente ridondanti — richiede applicare `feature_redundancy_audit_v1.md` al livello di componente, non solo di feature di stato (proposto, non eseguito).
- Se il cluster FVG/IFVG (7 strategy_id) collassa realmente a 1-2 fenomeni — richiede la stessa lettura di codice fatta per FVG_CONT, estesa a FVG_CONT_V2/FVG_MIT/FVG_MIT_WINDOW/IFVG/IFVG_CHOCH_WINDOW/LIQ_VOID (non fatta qui).
- Se MALAYSIAN_SNR_V2_* (4 varianti) e TURTLE_SOUP_* (3 varianti) sono stage di una pipeline o 7 idee distinte — richiede lettura di codice (non fatta qui).
- Se MACD_SMA200 duplica il filtro EMA200 già nativo di MACD — richiede lettura di `NXS_Strat_MacdSma200()` (riga 567, non letta in questo audit).
- Se `liquidity_sweep_detection` (il motore condiviso `NXS_DetectSweepExt`) ha altri consumer oltre LIQ_SWEEP tra le 83 strategie — non verificato.
- La cifra esatta di "fenomeni distinti" in §6 resta una stima preliminare con limite superiore plausibile 8-10, non una conclusione — richiederebbe estendere `UNIFIED_COMPONENT_CATALOG_V1.md` dalle 7 strategie di oggi al resto del registry.

---

## Vincoli rispettati

Nessun nuovo backtest. Nessuna modifica a runtime, MQL5 o registry. Ogni affermazione è marcata con la propria confidenza (CODE_VERIFIED/NAME_PATTERN_INFERRED/HISTORICAL_NOTE/UNKNOWN) — nessuna strategia è stata forzata in una categoria senza evidenza sufficiente.

UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1_READY_FOR_REVIEW
