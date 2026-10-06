# Canonical Component/Context Model V1

**Stato:** sintesi finale, non committata. Nessun codice modificato, nessun backtest, nessun peso assegnato, nessun commit/push. Questo documento non introduce nuova evidenza di codice — consolida i 7 audit già prodotti (`UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1`, `UNIFIED_COMPONENT_CATALOG_V1`, `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1`, `COMPONENT_COLLAPSE_HIGH_VALUE_VERIFICATION_V1`, `STRATEGY_IDENTITY_ATTRIBUTION_PREAUDIT_V1`, `INSTITUTIONAL_DECISION_ENGINE_FORENSIC_AUDIT_V1`, `CONTEXT_REGIME_RECONCILIATION_V1`) in un unico modello operativo. Dove una riga di questo documento non è già citata in uno di quei 7, è marcata esplicitamente come proposta nuova, non come fatto verificato.

Questo è, per costruzione del task, l'ultimo documento di architettura prima della ripartenza dei test scientifici.

---

## 1. I 7 layer formali, separati

| Layer | Definizione | Direzionale? | Esempi già trovati negli audit |
|---|---|---|---|
| **MARKET_REGIME** | Stato lento del mercato, categorico, **indipendente da qualunque direzione candidata** — "che tipo di mercato è questo" | **No** | Phase 4/5.5 (5 stati: HIGH_VOL/LOW_VOL/TRANSITION/TRENDING/RANGING), Phase 7.27 (trend×vol_tercile) |
| **DIRECTIONAL_CONTEXT** | Quanto lo stato di mercato attuale sostiene una direzione specifica (BUY o SELL) già proposta | **Sì, per costruzione** | `g_ctx.htfBias`, `g_ctx.structTrend` (letti come direzione, non come categoria) |
| **EVENT** | Accadimento discreto, timestampato, rilevato da un detector causale, indipendente da qualunque strategia | Sì (ha una direzione intrinseca all'evento) | Liquidity sweep, BOS/CHoCH, FVG/OB zone creation |
| **COMPONENT** | Evidenza di mercato riusabile con stato/osservazione propria (quello che era "MARKET_EVIDENCE" in `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md` §2) | Sì | `adx_trend_strength`, `liquidity_sweep_detection`, `order_block_zone_location`, ecc. |
| **TRIGGER** | Condizione precisa che, dato un Component/Setup attivo, genera il momento esatto del Signal | Sì | `sweep_reversal_trigger`, `breakout_acceptance_trigger`, ecc. |
| **ELIGIBILITY_CONTROL** | Filtro che decide SE un'evidenza/trigger è ammesso ad agire — non osserva un nuovo fenomeno, qualifica quello già osservato | N/A (è un gate, non un'osservazione) | `delivery_candle_filter`, `sar_candle_alignment_filter`, `breakout_cooldown_filter`, `_nxs_regime_veto`, RR-sanity |
| **RISK/EXECUTION** | Dimensionamento posizione, SL/TP, preflight, invio ordine — indipendente dal merito del Setup | N/A | `nexus_policy.HARD_CAPS_HARDENED`, `NXS_Prot_EntryBlocked`, `NXS_DoBuy`/`NXS_DoSell` |

**Correzione esplicita rispetto a `g_ctx` reale (da `CONTEXT_REGIME_RECONCILIATION_V1.md` §0):** nel codice odierno, `NXS_Context_DirectionalScore` mescola DIRECTIONAL_CONTEXT (`htfBias`, `structTrend`) con EVENT (`sweepDir`, `zoneDir`, `reactionDir`×qualità) in un unico score. Il modello canonico qui separa questi due layer per costruzione — qualunque implementazione futura del Unified Engine deve calcolarli come due output distinti, anche se poi combinati più avanti nella pipeline.

---

## 2. Feature table

| canonical_id | Fenomeno | source_primitive | Timeframe | Observation point | Freshness | Direction-dependent | Dependency cluster | Causal safety | Runtime/Research |
|---|---|---|---|---|---|---|---|---|---|
| `REGIME.VOLATILITY_TERCILE` | Volatilità | `atr_percentile` (Phase4/5.5, H4) / `atr14` tercile (Phase7.27, D1) | H4 / D1 | bar_close | Ricalcolato ogni barra | No | Nessuno nel runtime (assente, gap) | Dichiarata (soglie da sola finestra discovery) | **Solo research** — assente runtime |
| `REGIME.TREND_PERSISTENCE` | Freschezza del trend | `trend_persistence_bars` (Phase4/5.5) | H4 | bar_close | Ricalcolato ogni barra | No | Nessuno | Dichiarata | Solo research |
| `CONTEXT.TREND_MA_SLOPE` | Trend (famiglia MA) | `ema50_slope_trend` (ADX_RSI) / `ema9_21_cross_filter` (SAR) / `ema200_trend_filter` (MACD) / `sma50_slope` (Phase7.27) | TF proprio della strategia / D1 | bar_close | Ricalcolato ogni barra | Sì | **Cluster MA-trend** (vedi §3) | CODE_VERIFIED (nessun look-ahead trovato) | Runtime (3) + Research (1) |
| `CONTEXT.TREND_EFFICIENCY` | Trend (efficienza di percorso) | `directional_efficiency` (Phase4/5.5) | H4 | bar_close | Ricalcolato ogni barra | No (è parte della definizione categorica di regime, non un voto direzionale) | Nessuno — metodologia indipendente | Dichiarata | Solo research |
| `CONTEXT.TREND_STRUCTURE` | Trend (rottura di struttura) | `g_struct.trend` (swing HH/HL/LH/LL) | TF live (non dichiarato esplicitamente in `g_ctx`) | aggiornamento di `g_struct` (non verificato il TF esatto in questo filone) | Persistente fino al prossimo BOS | Sì | Alimenta anche `bosDir`/`chochDir` — **stesso modulo sorgente, 3 letture correlate** | **Non verificata** in questo filone — gap | Solo runtime |
| `CONTEXT.HTF_BIAS` | Bias di lungo periodo | `price_above_htf_sma200` (Phase7.27) / `ema200_trend_filter` (MACD, stesso test concettuale) / `g_ctx.htfBias` (modulo HTF non letto) | D1 / TF strategia / TF HTF non dichiarato | bar_close | Ricalcolato ogni barra | Sì | **Candidato di unificazione più forte di tutto il documento** (§2 di `CONTEXT_REGIME_RECONCILIATION_V1.md`) | Dichiarata (Phase7.27) / CODE_VERIFIED (MACD) / non verificata (g_ctx) | Runtime (2) + Research (1) |
| `EVENT.LIQUIDITY_SWEEP` | Sweep di liquidità | `liquidity_sweep_detection` (`NXS_DetectSweepExt`) | TF effettivo | momento di conferma del detector | Evento puntuale, non persistente | Sì (intrinseca) | Condiviso da LIQ_SWEEP e TURTLE_SOUP (`EXACT_SHARED_PRIMITIVE`, `COMPONENT_COLLAPSE_HIGH_VALUE_VERIFICATION_V1.md`) | CODE_VERIFIED | Solo runtime (nessun equivalente research trovato) |
| `EVENT.STRUCTURE_BREAK` | BOS/CHoCH | `g_struct.bosUp/bosDown/chochUp/chochDown` | Stesso modulo di `CONTEXT.TREND_STRUCTURE` | aggiornamento `g_struct` | Evento puntuale | Sì | Stesso modulo sorgente di `CONTEXT.TREND_STRUCTURE` — **non due componenti indipendenti, un solo modulo con 3 output derivati** | Non verificata | Solo runtime |
| `COMPONENT.LOCATION_OB` | Zona Order Block | `order_block_zone_location` (`g_obBuy`/`g_obSell`) | TF dichiarato strategia | bar_close, solo pass TF corretto (post-fix) | **Persistente tra barre** | Sì | Condiviso con OB_MIT (`EXACT_SHARED_PRIMITIVE`) | CODE_VERIFIED | Runtime + research (parity approssimata) |
| `COMPONENT.LOCATION_FVG` | Gap/imbalance | `fair_value_gap_location` | TF effettivo | bar_close, finestra 3 barre | Non persistente (ricalcolato) | Sì | Condiviso (parzialmente) con IFVG/FVG_MIT/FVG_MIT_WINDOW (`VARIANT_OF_SAME_SETUP`) | CODE_VERIFIED | Runtime + research |
| `CONTEXT.ZONE_PROXIMITY` | Prossimità a zona attiva | `g_ctx.zoneDir` | Live, tolleranza ATR-scalata | ogni tick/barra | Dipende dalla persistenza delle zone sottostanti | Sì | Deriva da `g_levels[]`, probabilmente lo stesso registro di zone usato da `COMPONENT.LOCATION_OB`/`LOCATION_FVG` — **non verificato se sia lo stesso array o una copia** (gap) | Non verificata | Solo runtime |
| `CONTEXT.REACTION_QUALITY` | Qualità della reazione di prezzo | `g_reaction.detected/direction/quality` (`NXS_SMCReactionOK`) | TF effettivo | post-evento | Puntuale | Sì | Condiviso da ORDER_BLOCK e FVG_CONT (`EXACT_SHARED_PRIMITIVE`, già noto) | CODE_VERIFIED | Solo runtime |
| `COMPONENT.MOMENTUM_ADX` | Forza del trend (ampiezza, non direzione) | `adx_trend_strength` | TF effettivo | bar_close | Ricalcolato ogni barra | No (è ampiezza, non direzione) | Letto anche da `_nxs_regime_veto` — **stessa misura ADX usata due volte con soglie diverse** (gap da `CONTEXT_REGIME_RECONCILIATION_V1.md` §4) | CODE_VERIFIED | Solo runtime |
| `COMPONENT.MOMENTUM_RSI` | Momentum RSI | `rsi_momentum_condition` | TF effettivo | bar_close | Ricalcolato ogni barra | Sì | Nessuno trovato | CODE_VERIFIED | Runtime |
| `EVENT.BREAKOUT_ACCEPTANCE` | Accettazione fuori range | `range_breakout_location` + `breakout_acceptance_trigger` | TF dichiarato (post-fix) | 2 chiusure consecutive | Puntuale (il cooldown è un ELIGIBILITY_CONTROL separato, non il fenomeno stesso) | Sì | Nessuno diretto; concettualmente adiacente a `COMPONENT.LOCATION_*` (tutti "posizione rispetto a un livello strutturale") | CODE_VERIFIED | Runtime + research (3 varianti: BREAKOUT_ACC/VOLATILITY_BREAKOUT_CONFIRMED/Z_SCORE_BREAKOUT, stesso enum ma formule distinte) |
| `COMPONENT.MEAN_REVERSION_LOCATION` | Posizione in banda/range per reversal | Bollinger bands, range fade | TF effettivo | bar_close | Ricalcolato ogni barra | Sì | Non analizzato a livello di codice in questo filone — **gap, non ancora catalogato** | UNKNOWN | Runtime |

## 3. Classificazione dei 6 proxy di trend

| Proxy | Fonte | Metodologia | Classificazione |
|---|---|---|---|
| `ema50_slope_trend` (ADX_RSI) | Strategia | EMA50, pendenza (shift1 vs shift2) | — |
| `ema9_21_cross_filter` (SAR) | Strategia | Cross EMA9/EMA21 | — |
| `ema200_trend_filter` (MACD) | Strategia | Prezzo vs EMA200 (livello, non pendenza) | — |
| `sma50_slope` (Phase 7.27) | Research | SMA50, pendenza 5 barre, soglia ±0.1% | — |

**Questi 4 → RELATED_PROXY tra loro.** Stessa famiglia metodologica (media mobile, in forma slope o cross o livello), periodi e timeframe diversi, mai verificato se producono lo stesso segno sulle stesse barre. Non sono `SAME_INFORMATION` per costruzione (nessuna prova di equivalenza numerica), ma la probabilità a priori di forte correlazione è alta (coerente col precedente reale di `feature_redundancy_audit_v1.md`: coppie EMA-based già trovate correlate 0.79-0.95 in questo stesso progetto).

| `directional_efficiency` (Phase 4/5.5) | Research | Efficienza di percorso (spostamento netto / percorso totale) | **COMPLEMENTARY** rispetto al cluster MA — metodologia matematicamente indipendente (non deriva da nessuna media mobile), misura una proprietà diversa (quanto "diretto" è il movimento, non la sua pendenza) |
| `g_struct.trend` (g_ctx/runtime) | Runtime | Rottura di struttura su swing high/low | **COMPLEMENTARY/DISTINCT** — può divergere dal cluster MA per costruzione (una rottura di struttura può avvenire mentre una media mobile è ancora piatta, e viceversa) |

**Nessuno dei 6 è classificato `SAME_INFORMATION`** — non esiste oggi la prova numerica che richiederebbe quella classificazione (richiederebbe l'audit di correlazione Pearson/Spearman già proposto come Phase 2+ in `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md` §7, non eseguito). La raccomandazione dell'utente è corretta: **vanno trattati come proxy diversi dello stesso fenomeno macro (trend), con dipendenza esplicita dichiarata** (il cluster MA è una dipendenza dichiarata; efficiency e structure restano fuori dal cluster, dipendenza assente per ora, da verificare non da assumere).

## 4. Dependency cluster riepilogati (da tutti gli audit precedenti + 2 nuovi trovati nella riconciliazione regime)

**Nota di vocabolario:** `UNIFIED_COMPONENT_DEPENDENCY_AUDIT_V1.md` usa la taxonomy EXACT_SHARED_PRIMITIVE/PARENT_CHILD/SAME_PHENOMENON_DIFFERENT_PROXY/CORRELATED_BUT_DISTINCT/INDEPENDENT/UNKNOWN; `COMPONENT_COLLAPSE_HIGH_VALUE_VERIFICATION_V1.md` usa SAME_COMPONENT/SAME_PHENOMENON_DIFFERENT_PROXY/VARIANT_OF_SAME_SETUP/GENUINELY_DISTINCT/UNKNOWN (vocabolario diverso, richiesto esplicitamente dal task che l'ha prodotto). Sono due etichettature dello stesso tipo di relazione, non due conclusioni diverse — es. ORDER_BLOCK↔OB_MIT è `EXACT_SHARED_PRIMITIVE` nel primo documento e `SAME_COMPONENT` nel secondo: stessa evidenza di codice, stessa conclusione, nomi diversi per task diversi. Qui sotto si usa la taxonomy del Dependency Audit come riferimento unico.

1. **Cluster MA-trend** (§3) — 4 membri, RELATED_PROXY.
2. **ORDER_BLOCK ↔ OB_MIT** — `EXACT_SHARED_PRIMITIVE` (= `SAME_COMPONENT` in `COMPONENT_COLLAPSE_HIGH_VALUE_VERIFICATION_V1.md`), stato di zona condiviso.
3. **ORDER_BLOCK ↔ FVG_CONT** — `EXACT_SHARED_PRIMITIVE` su `CONTEXT.HTF_BIAS`-locale e `CONTEXT.REACTION_QUALITY`.
4. **FVG_CONT ↔ IFVG ↔ FVG_MIT ↔ FVG_MIT_WINDOW** — `VARIANT_OF_SAME_SETUP` (stesso termine in entrambi i documenti).
5. **LIQ_SWEEP ↔ TURTLE_SOUP** — `EXACT_SHARED_PRIMITIVE` sull'`EVENT.LIQUIDITY_SWEEP`.
6. **`CONTEXT.TREND_STRUCTURE` ↔ `EVENT.STRUCTURE_BREAK`** (nuovo in questo documento) — stesso modulo sorgente (`g_struct`), non due osservazioni indipendenti ma 3 letture derivate (trend/bos/choch) dello stesso stato strutturale.
7. **`COMPONENT.MOMENTUM_ADX` ↔ veto di regime** (da `CONTEXT_REGIME_RECONCILIATION_V1.md` §4) — stessa lettura ADX, due soglie scoordinate.
8. **`CONTEXT.ZONE_PROXIMITY` ↔ `COMPONENT.LOCATION_OB`/`LOCATION_FVG`** (nuovo, non verificato) — sospetto, non confermato, se condividono lo stesso registro `g_levels[]`.

## 5. Minimum viable feature set per il primo shadow test del Unified Engine

**Non tutto il catalogo — un sottoinsieme deliberatamente piccolo**, coerente con la sequenza data dall'utente e con la disciplina di `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` (Phase 1 piccola e falsificabile):

- **1 dimensione MARKET_REGIME**: `REGIME.VOLATILITY_TERCILE` — priorità assoluta secondo questo stesso documento (§1 di `CONTEXT_REGIME_RECONCILIATION_V1.md`: la volatilità ha priorità massima nei sistemi di ricerca ed è assente dal runtime; è il gap più consequenziale trovato in tutto il filone). Richiede riconciliare le 2 implementazioni research esistenti (H4 vs D1) prima dell'uso, non costruirne una terza.
- **1 dimensione CONTEXT**: `CONTEXT.HTF_BIAS` — il candidato di unificazione più pulito, già quasi pronto.
- **1 proxy di trend, non tutti e 6**: scegliere **uno** dal cluster MA (coerente col pilot MACD già in corso con Codex — se MACD è il componente pilota, il suo stesso `ema200_trend_filter` è il candidato naturale, evitando di introdurre un quarto/quinto proxy prima che il primo abbia un verdetto).
- **Componenti decorrelati**: i cluster già mappati in §4 — nessun componente che faccia parte di un cluster `EXACT_SHARED_PRIMITIVE`/`VARIANT_OF_SAME_SETUP` va contato più di una volta nel set iniziale.
- **1 TRIGGER per componente incluso** — già esistenti, nessuna nuova costruzione necessaria.
- **ELIGIBILITY_CONTROL esistenti, riusati tali e quali** (RR-sanity, cooldown, candle-alignment dove già presenti) — non ridisegnati qui.
- **Nessun RISK/EXECUTION nuovo** — SL/TP calcolati separatamente dal layer di conviction (correggendo il coupling trovato in `INSTITUTIONAL_DECISION_ENGINE_FORENSIC_AUDIT_V1.md` §12), riusando i gate deterministici esistenti (`NXS_Prot_EntryBlocked`, `nexus_policy`) invariati.

**Esplicitamente escluso da questo primo set**: gli altri 5 proxy di trend, gli altri 5 componenti nominati originariamente (ADX_RSI, LIQ_SWEEP, ORDER_BLOCK, FVG_CONT, BREAKOUT_ACC) finché il pilot MACD non ha un verdetto, qualunque meccanismo di aggregazione/peso (resta un'opzione aperta in `UNIFIED_MARKET_INTELLIGENCE_ARCHITECTURE_V1.md` §4, non scelta qui).

## 6. Dopo questo documento: cosa significa "tornare ai test"

Il confronto proposto dall'utente — `regime canonico + volatilità + directional context + componenti decorrelati + trigger → unified conviction` **contro** `singolo segnale standalone`, con OOS/costi/sample-size/dipendenza/robustezza — è esattamente la Phase 1 già specificata in `CONTEXTUAL_EDGE_DISCOVERY_V1_DESIGN.md` (preregistrazione, BH-FDR, ESS a 3 metodi, benchmark regime-matchato, cost stress), **non un nuovo protocollo da scrivere**. Questo documento aggiunge solo la precondizione che mancava: un modello di feature canoniche e deduplicate su cui applicare quel protocollo, invece di un insieme di nomi di strategia non riconciliati. Il passo successivo naturale è lasciare che Codex (o la stessa pipeline già in corso per MACD) estenda il test includendo `REGIME.VOLATILITY_TERCILE` e `CONTEXT.HTF_BIAS` riconciliati come covariate — non un nuovo documento di architettura.

---

## Vincoli rispettati

Nessun peso assegnato. Nessun backtest. Nessuna modifica a codice/registro. Nessuna delle 6 classificazioni di trend proxy è `SAME_INFORMATION` senza prova numerica — nessuna forzata.

CANONICAL_COMPONENT_CONTEXT_MODEL_V1_READY_FOR_REVIEW
