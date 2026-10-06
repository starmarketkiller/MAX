# Unified Component Catalog V1

**Stato:** catalogo concettuale, non ancora committato. Nessun codice, runtime o registry modificato. Nessun peso assegnato, nessun aggregatore proposto, nessun backtest nuovo. Ogni riga è verificata leggendo il codice MQL5 reale (`MQL5/Include/NEXUS_v1/NXS_Strategies.mqh`, `NXS_Strategies_SMC.mqh`), non solo le descrizioni nel registry — dove il registry e il codice divergono, lo dichiaro esplicitamente.

**Fonti canoniche:** `market_ontology.md` (Phase 4), `contracts/edge-validation-registry.json`/`.schema.json` (Codex, `3a0906a`), `docs/UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` (`cfcdef8`), codice MQL5 corrente (HEAD `cfcdef8`).

---

## Catalogo per strategia

### ADX_RSI (`NXS_Strat_ADXRSI`, riga 261)

| Component | Role | Fenomeno osservato | Input causali | TF | Observation point | Output |
|---|---|---|---|---|---|---|
| `adx_trend_strength` | REGIME_DETECTOR | Forza del trend (ADX) come gate di ammissibilità | `g_adx` (ADX(14)) | TF effettivo | chiusura barra | booleano: ADX≥20 |
| `ema50_slope_trend` | **MOMENTUM_FEATURE — non ancora nel registry come componente separato** | Direzione trend via pendenza EMA50 | `g_EMAv(50, tf, 1)` vs `shift 2` | TF effettivo | chiusura barra | trendUp/trendDown |
| `rsi_momentum_condition` | MOMENTUM_FEATURE | RSI in banda 45-65 (buy) / 35-55 (sell), non ipercomprato/ipervenduto puro | `g_rsi` (RSI 14) | TF effettivo | chiusura barra | booleano |
| `adx_rsi_entry_trigger` | ENTRY_TRIGGER | Combinazione: trend+RSI in banda+prezzo vs EMA50 | tutti i precedenti + `close[1]` vs EMA50 | TF effettivo | chiusura barra | direzione |

**Divergenza dal registry:** il registry lista solo 3 componenti (`adx_trend_strength`, `rsi_momentum_condition`, `adx_rsi_entry_trigger`) — la pendenza EMA50 (`ema50_slope_trend`), che è una condizione di trend indipendente dall'ADX e genuinamente separata nel codice, non è catalogata a parte.

### MACD (`NXS_Strat_MACD`, riga 358)

| Component | Role | Fenomeno osservato | Input causali | TF | Observation point | Output |
|---|---|---|---|---|---|---|
| `macd_momentum` | MOMENTUM_FEATURE | MACD line vs signal line, sopra/sotto zero | `g_macd`, `g_macdSig` | TF effettivo | chiusura barra | direzione momentum |
| `ema200_trend_filter` | **CONTEXT_FEATURE — non nel registry, componente nascosto** | Prezzo sopra/sotto EMA200 (trend di lungo periodo) | `g_ema200`, `close[1]` | TF effettivo | chiusura barra | booleano |
| `macd_cross_trigger` | ENTRY_TRIGGER | Combinazione momentum+trend | i due precedenti | TF effettivo | chiusura barra | direzione |

**Divergenza dal registry:** il registry lista solo `macd_momentum` e `macd_cross_trigger` — il filtro `price > g_ema200` è una condizione di contesto genuinamente separata (misura trend di lungo periodo, non momentum) e manca come componente proprio. **Rilevante per `CONTEXTUAL_EDGE_DISCOVERY_V1`**: il pilot MACD testerà "MACD ha valore condizionale" trattando MACD come feature di momentum pura — ma il codice live non isola mai MACD da questo filtro EMA200. Se Codex replica la logica di generazione segnale per il pilot, userà implicitamente anche questo filtro; se invece isola solo l'histogram/crossover come feature pura (come indicato nel design doc), sta testando qualcosa di volutamente più semplice della strategia live — una differenza da rendere esplicita, non un errore.

### SAR (`NXS_Strat_SAR`, riga 406)

| Component | Role | Fenomeno osservato | Input causali | TF | Observation point | Output |
|---|---|---|---|---|---|---|
| `parabolic_sar_trend_direction` | MOMENTUM_FEATURE | Posizione del punto SAR vs prezzo | `g_sar`, `close[1]` | TF effettivo | chiusura barra | direzione |
| `ema9_21_cross_filter` | **MOMENTUM_FEATURE — non nel registry, componente nascosto** | Trend via cross EMA9/EMA21 | `g_ema9`, `g_ema21` | TF effettivo | chiusura barra | booleano, deve concordare col SAR |
| `sar_candle_alignment_filter` (opzionale, `InpSAR_RequireCandleAlign`) | **FILTER — non nel registry** | Candela H4 appena chiusa concorde con la direzione (bullish/bearish) | `open[1]`, `close[1]` | TF effettivo | chiusura barra | booleano — empiricamente PF1.33→1.92 quando attivo (nota 31/08) |
| `sar_pressure_contrary_filter` (opzionale, `InpSAR_RequirePressureContrary`) | **FILTER — non nel registry** | Pressione delle ultime 8 barre M15 CONTRARIA alla direzione (cattura inversione, non inseguimento) | 8 barre M15 (open/close) | **M15, diverso dal TF effettivo della strategia** | chiusura barra M15 | booleano |
| `sar_flip_trigger` | ENTRY_TRIGGER | Combinazione di tutti i precedenti | tutti | TF effettivo | chiusura barra | direzione finale |

**Divergenza dal registry — la più grande dei 7:** il registry lista solo 2 componenti (`parabolic_sar_trend_direction`, `sar_flip_trigger`). Il codice reale ha **4 componenti aggiuntivi**, due obbligatori (EMA9/21 cross) e due opzionali ma con evidenza storica forte già documentata nel codice stesso (nota 31/08: combinati, PF3.47 su 18 trade vs PF0.04 su 13 trade quando nessuno dei due è soddisfatto — la nota dichiara esplicitamente "non ridondanti, si sommano"). Il filtro di pressione usa un **timeframe diverso (M15)** da quello effettivo della strategia — un dettaglio di temporal logic (§6 di `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md`) da non perdere in qualunque futura decomposizione.

### LIQ_SWEEP (`NXS_Strat_LiqSweep`, riga 1455)

| Component | Role | Fenomeno osservato | Input causali | TF | Observation point | Output |
|---|---|---|---|---|---|---|
| `liquidity_sweep_detection` | LIQUIDITY_EVENT | Sweep confermato di un livello (Daily/Weekly/Monthly/Asia/Equal High-Low) | `sw.confirmed`, `sw.dir`, `sw.levelTag` (da `NXS_DetectSweepExt`, motore condiviso esterno) | TF effettivo | momento di conferma del detector | evento + livello |
| `delivery_candle_filter` | **FILTER — non nel registry** | Candela di "delivery" genuina, non un rimbalzo qualsiasi: corpo ≥0.7×ATR | `close[1]`, `open[1]`, `g_atr` | TF effettivo | chiusura barra | booleano |
| `sweep_reversal_trigger` | ENTRY_TRIGGER | Direzione della candela concorde col lato dello sweep | `close[1]` vs `open[1]`, `sw.dir` | TF effettivo | chiusura barra | direzione |

**Divergenza dal registry:** manca `delivery_candle_filter` — una condizione di qualità del segnale (ampiezza candela ≥0.7×ATR) distinta sia dal detector di sweep sia dal trigger di direzione.

**Nota architetturale:** `liquidity_sweep_detection` non vive nel codice della strategia stessa — è un motore condiviso (`NXS_DetectSweepExt`) chiamato da fuori e passato come parametro (`SNXSSweepExt &sw`). Questo lo rende probabilmente il componente più vicino, tra i 7, a un vero "sensore" riusabile indipendente dalla strategia — coerente con l'osservazione del registry (`SH_BMS_RTO` nella Phase 7.10 condivide la stessa classe di contaminazione come conseguenza di toccare lo stesso genere di stato condiviso).

### ORDER_BLOCK (`NXS_Strat_OrderBlock`, riga 2142)

| Component | Role | Fenomeno osservato | Input causali | TF | Observation point | Output |
|---|---|---|---|---|---|---|
| `order_block_zone_location` | LOCATION_FEATURE | Zona order block attiva (buy/sell side), via `NXS_OB_UpdateSide` | `g_obBuy`/`g_obSell` (stato persistente, TF-scoped dopo il fix `17da794`) | TF dichiarato della strategia (`NXS_Profile_TF`) | chiusura barra, solo sul pass TF corretto | zona attiva + direzione candidata |
| `external_h1_structure_trend` | **CONTEXT_FEATURE — non nel registry, condiviso con FVG_CONT** | Trend di struttura esterna H1 deve confermare la direzione del retest | `g_structH1.trend` | **H1, indipendente dal TF effettivo** | chiusura barra H1 | booleano di conferma |
| `smc_reaction_confirmation` (opzionale, `InpUseSMCReactionGate`) | **CONFIRMATION — non nel registry, condiviso con FVG_CONT** | Il prezzo respinge il blocco (reazione vera), non lo attraversa | `NXS_SMCReactionOK()` | TF effettivo | post-retest | booleano |
| `order_block_retest_trigger` | ENTRY_TRIGGER | Combinazione di tutti i precedenti | tutti | TF dichiarato | chiusura barra | direzione finale |

**Divergenza dal registry e relazione parent/child reale (non ipotizzata — verificata nel codice):** `g_structH1.trend` e `NXS_SMCReactionOK()` sono **esattamente gli stessi due componenti**, chiamati con la stessa identica logica, da **ORDER_BLOCK e FVG_CONT** (vedi sotto). Non è una somiglianza, è condivisione letterale di stato/funzione. Questo è il candidato più solido di questo catalogo per una relazione parent/child: `external_h1_structure_trend` e `smc_reaction_confirmation` dovrebbero esistere come **due componenti genitore unici**, con ORDER_BLOCK e FVG_CONT come consumatori, non come due copie indipendenti.

### FVG_CONT (`NXS_Strat_FVG`, riga 1488)

| Component | Role | Fenomeno osservato | Input causali | TF | Observation point | Output |
|---|---|---|---|---|---|---|
| `fair_value_gap_location` | LOCATION_FEATURE | Gap a 3 candele (`low[1]>high[3]` o mirror) | `high[3]`, `low[3]`, `high[1]`, `low[1]` | TF effettivo | chiusura barra | zona gap + direzione candidata |
| `external_h1_structure_trend` | **CONTEXT_FEATURE — identico a ORDER_BLOCK, vedi sopra** | Trend H1 concorde | `g_structH1.trend` | H1 | chiusura barra H1 | booleano |
| `smc_reaction_confirmation` (opzionale, `InpUseSMCReactionGate`) | **CONFIRMATION — identico a ORDER_BLOCK, vedi sopra** | Reazione di prezzo confermata | `NXS_SMCReactionOK()` | TF effettivo | post-gap | booleano |
| `fvg_continuation_trigger` | ENTRY_TRIGGER | Combinazione di tutti i precedenti | tutti | TF effettivo | chiusura barra | direzione finale |

**Nota sul defect noto (`SLRECLAIM_ACCOUNT_PROTECTION_BYPASS`, `UNKNOWN_REMEDIATION`):** riguarda una variante di trade management (SLReclaim) non rappresentata in questa decomposizione — i 4 componenti sopra descrivono la generazione del segnale di entrata, non la gestione post-entry. Nessuna delle due cose invalida l'altra; vanno tenute distinte (coerente con `market_ontology.md`, sez. Trade Management, validata separatamente dal Setup).

### BREAKOUT_ACC (`NXS_Strat_BreakoutAcc`, riga 1535) — decomposizione mancante, ricostruita qui

Il registry ha `role_in_system: []` e `potential_reusable_components: []` — nessuna decomposizione esiste oggi. Ricostruita leggendo il codice reale (post-fix `651d3a2`):

| Component | Role | Fenomeno osservato | Input causali | TF | Observation point | Output |
|---|---|---|---|---|---|---|
| `range_breakout_location` | LOCATION_FEATURE | Prezzo (2 chiusure consecutive) oltre un range strutturale di 20 barre (shift 3-22) | `high`/`low` su 20 barre, `close[1]`, `close[2]` | TF dichiarato della strategia (`NXS_Profile_TF`, dopo il fix) | chiusura barra, solo sul pass TF corretto | direzione candidata (accettazione sopra/sotto range) |
| `breakout_acceptance_trigger` | ENTRY_TRIGGER | 2 chiusure consecutive fuori range = "accettazione", non una singola rottura | `acceptUp`/`acceptDn` dal componente precedente | TF dichiarato | chiusura barra | direzione finale |
| `breakout_cooldown_filter` | **FILTER — non un segnale di mercato, un controllo di frequenza di esecuzione** | Nessuno (non osserva il mercato — limita quante volte la strategia può ri-sparare nella stessa direzione) | `InpBreakoutAccCooldownBars`, `lastFireTime[dir]` | TF dichiarato | — | booleano, per-direzione |

**Nota storica:** `breakout_cooldown_filter` è esattamente il meccanismo che ha ospitato il defect originale (`COOLDOWN_STATE_CONTAMINATION`, Phase 7.9F, oggi `REMEDIATED`) — lo stato era condiviso tra pass multi-TF prima del fix `651d3a2`. Separarlo come componente proprio (invece che implicito dentro il trigger) rende più visibile dove quella classe di defect può ricorrere in futuro, coerente con §6 di `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md`.

---

## Componenti probabilmente ridondanti (stesso fenomeno, proxy diversi)

**Trend/direzione via EMA, a 3 periodi diversi, in 3 strategie diverse** — nessuna delle tre dichiarata oggi come collegata alle altre:

| Componente | Strategia | Proxy di trend usato |
|---|---|---|
| `ema50_slope_trend` | ADX_RSI | Pendenza EMA50 (shift1 vs shift2) |
| `ema200_trend_filter` | MACD | Prezzo vs EMA200 (livello, non pendenza) |
| `ema9_21_cross_filter` | SAR | Cross EMA9/EMA21 |

Non verificato empiricamente in questo catalogo (richiederebbe dati, fuori scope qui) — ma è esattamente il pattern già confermato altrove nel progetto: `feature_redundancy_audit_v1.md` (Phase 5.5) ha già trovato che pendenza EMA e posizione-nel-range sono correlate 0.79-0.95 nello stesso dataset. **Raccomandazione per Phase 2+ (non eseguita qui):** applicare la stessa identica metodologia (Pearson/Spearman su serie causali) a questi 3 proxy prima di trattarli come 3 evidenze indipendenti in qualunque futura aggregazione.

## Componenti semanticamente indipendenti (non ridondanti per costruzione)

`liquidity_sweep_detection` (evento discreto, livello di liquidità), `order_block_zone_location`/`fair_value_gap_location` (location, zone persistenti), `adx_trend_strength`/`rsi_momentum_condition` (ampiezza/momentum, non direzione) misurano fenomeni di mercato genuinamente diversi (evento vs posizione vs forza) anche se tutti SMC/momentum-flavored — non ci sono nel codice dipendenze condivise tra questi, a differenza del caso sotto.

## Componenti che misurano lo stesso fenomeno con la stessa identica implementazione (non solo proxy simile)

**`external_h1_structure_trend` e `smc_reaction_confirmation`** — condivisi letteralmente, stessa variabile globale (`g_structH1.trend`) e stessa funzione (`NXS_SMCReactionOK()`), tra **ORDER_BLOCK e FVG_CONT**. Non è un caso di "proxy diversi dello stesso fenomeno" (come le 3 EMA sopra) — è lo stesso identico componente consumato due volte. Qualunque futuro aggregatore che conti il consenso di ORDER_BLOCK e FVG_CONT come 2 evidenze indipendenti su questo aspetto starebbe contando la stessa informazione due volte.

## Gap di decomposizione (riassunto)

| Strategia | Gap |
|---|---|
| BREAKOUT_ACC | Nessuna decomposizione esistente nel registry — ricostruita qui (3 componenti) |
| SAR | 4 componenti reali nel codice, solo 2 nel registry (manca EMA9/21 cross + 2 filtri opzionali con evidenza storica forte già in nota) |
| LIQ_SWEEP | Manca `delivery_candle_filter` (qualità del segnale, ≥0.7×ATR) |
| ORDER_BLOCK, FVG_CONT | Mancano entrambi `external_h1_structure_trend` e `smc_reaction_confirmation` — e la mancanza nasconde che sono condivisi, non solo assenti |
| ADX_RSI | Manca `ema50_slope_trend` come componente separato dall'ADX |
| MACD | Manca `ema200_trend_filter` come componente separato dal momentum MACD |

Nessuna di queste mancanze è stata corretta nel registry in questo documento — sono proposte di decomposizione da riconciliare con Codex, coerente col vincolo "non modificare codice o registry" di questo task.

---

## Vincoli rispettati

Nessun peso assegnato. Nessun aggregatore proposto. Nessun backtest nuovo eseguito — ogni riga viene dalla lettura statica del codice MQL5 esistente e dei documenti canonici già citati. Nessuna modifica a `contracts/edge-validation-registry.json` o al codice MQL5.

UNIFIED_COMPONENT_CATALOG_V1_READY_FOR_REVIEW
