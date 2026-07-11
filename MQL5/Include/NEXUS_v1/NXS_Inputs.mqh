//+------------------------------------------------------------------+
//|  NXS_Inputs.mqh - All input parameters                            |
//+------------------------------------------------------------------+
#ifndef __NXS_INPUTS_MQH__
#define __NXS_INPUTS_MQH__

input group "=== NEXUS v2.3.0 — PARAMETRI ATTIVI ==="

// input group "=== SCREENING SELECTOR (v2.0.36) ==="
// 0 = disabled (normal behavior, each InpStrat_*/InpUseStrat_* toggle applies
// as usual). 1-37 = isolate EXACTLY that one strategy for this run,
// overriding all individual toggles - lets a single genetic/full Optimization
// job (Optimization=1, this one input swept 1..37) screen all 37 strategies
// as separate "passes" that MT5 (and MQL5 Cloud Network) can distribute
// across agents, instead of 37 separate sequential terminal64.exe launches.
// Index order matches scripts/generate_sets.ps1's $AllStrategyToggles list
// exactly, so results are directly comparable to the prior single-.set
// screenings: 1=ADX_RSI 2=BOLLINGER 3=MACD 4=SAR 5=TSI 6=BJORGUM
// 7=LIQ_SWEEP 8=FVG_CONT 9=BREAKOUT_ACC 10=LONDON_BO 11=EMA_PULLBACK
// 12=BB_SQUEEZE 13=ICHIMOKU 14=RSI_DIV 15=ORDER_BLOCK 16=STRUCT_REACT
// 17=TurtleSoup 18=IFVG 19=FVG_Mit 20=OB_Mit 21=SH_BMS_RTO 22=SMS_BMS_RTO
// 23=SilverBullet 24=AMD_Reversal 25=OTE_Cont 26=MalaysianSNR 27=CISD
// 28=AMD_Cont 29=Judas 30=LdnReversal 31=NYReversal 32=WeeklyExp 33=PO3
// 34=LiqVoid 35=DispRebal 36=Elliott 37=RangeFade
int InpStrategySelector = 0;

// input group "=== GENERAL ==="
input long     InpMagic            = 991000;
input string   InpComment          = "NEXUS_v2.39";  // prefisso commento trade: distingue i trade del build v2.3.0 (multi-TF)
ENUM_TIMEFRAMES InpTFEntry   = PERIOD_M15;
ENUM_TIMEFRAMES InpTFMedium  = PERIOD_H1;
ENUM_TIMEFRAMES InpTFHigh    = PERIOD_H4;

// input group "=== PRESET / SCALING ==="
// 0=Custom, 1=Conservative, 2=Balanced, 3=Aggressive, 4=MVP_v206 (5 SMC MVP)
int      InpRiskProfile      = 2;
bool     InpAutoScaleByAccount = true;

// input group "=== SYMBOL WHITELIST ==="
bool     InpUseSymbolWhitelist = true;
string   InpAllowedSymbols   = "GOLD,XAUUSD,EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,US30,NAS100,SPX500,GER40,BTCUSD,ETHUSD";

// input group "=== LICENSE ==="
input bool     InpEnableLicense    = true;
input string   InpLicenseKey       = "";

// input group "=== ROBUSTNESS (Phase 1) ==="
int      InpHardMaxSpreadPts = 0;     // 0 = use profile default
int      InpOrderRetries     = 3;     // retries on requote/off-quotes
bool     InpUseStatePersist  = true;  // resume state after MT5 restart
bool     InpUseAtrTrail      = true;  // ATR-based trailing stop
double   InpAtrTrailMult     = 1.5;

// input group "=== ON-CHART DASHBOARD ==="
input bool     InpShowDashboard    = true;
int      InpDashX            = 10;
int      InpDashY            = 25;

// input group "=== NOTIFICATIONS ==="
bool     InpNotifyPush       = false;   // MT5 mobile push
bool     InpNotifyEmail      = false;
bool     InpNotifyTelegram   = false;
string   InpTelegramChatId   = "";
bool     InpNotifyOnOpen     = true;
bool     InpNotifyOnClose    = true;
bool     InpNotifyOnProtection = true;
bool     InpNotifyDailySummary = false;

// input group "=== RISK MANAGEMENT ==="
input double   InpRiskPercent      = 1.0;
double   InpMaxLot           = 5.0;
int      InpMaxTradesPerDay  = 12;
input int      InpMaxConcurrent    = 4;
input int      InpMaxPerDirTF      = 2;      // v2.3.0 SETUP MATRIX: max setup per direzione/TF (0=off)
input double   InpMaxDailyDDPct    = 5.0;
double   InpMinEntryScore    = 50.0;   // v2.2.8: abbassato, il backtest prende il segnale (i profili filtrano)
double   InpMalaysianMinScore = 80.0;  // v2.0.14: MALAYSIAN_SNR richiede score >= 80
int      InpMinMarginLevel   = 200;

// input group "=== DATA COLLECTION / SCREENING LIVE (v2.1.1) ==="
// Apre OGNI segnale valido di OGNI strategia a lotto fisso piccolo, saltando i
// gate soft (cooldown/MTF/velocity/exhaustion/exposure/best-per-bar) e la soglia
// di score. Tiene solo la sicurezza dura (spread/margine/stops via preflight).
// Serve a raccogliere dati REALI su TUTTE le strategie nel Journal per capire
// quali hanno edge, senza bocciarne nessuna a priori. USARE SU DEMO.
// NB: per vederle tutte, in .set metti tutti gli InpStrat_*/InpUseStrat_* = true
// e InpStrategySelector = 0.
bool     InpDataCollectionMode   = false;  // OFF: si usa il grouping istituzionale (raccolta dati solo su demo)
double   InpDataCollectionLot    = 0.01;   // lotto fisso per trade (piccolo)
int      InpDataCollectionMaxOpen= 40;     // tetto posizioni aperte contemporanee (sicurezza)

// input group "=== INSTITUTIONAL CORE (v2.1.0) ==="
// Master switch del modello istituzionale: lettura unica del mercato ->
// raggruppamento dei segnali per direzione -> 1 posizione per direzione con
// SL/TP scalati sul tier (TF di conferma) -> gestione uniforme grid/recovery.
// OFF di default: l'EA usa il modello attuale (best-per-bar) finché non lo
// attivi in Strategy Tester.
bool     InpUseInstitutionalCore = false;  // v2.2.8: OFF -> best-per-bar, 1 posizione per strategia (come nel backtest)
// v2.2.8 - "operare come nel backtest": ogni strategia usa i SUOI parametri
// (ATR SL/TP dal backtest per-strategia) e le perdenti confermate non aprono.
bool     InpUseStrategyProfiles  = true;
bool     InpProfileTFGate        = true;   // v2.3.0: ogni strategia apre solo sul suo TF (gira 1 istanza per TF: D1/H4/H1)
input bool     InpProfileMultiTF       = true;  // v2.3.0: UN grafico solo -> l'EA calcola ogni strategia sul suo TF (D1/H4/H1) internamente
double   InpInstMinConviction    = 60.0;   // conviction netta minima (somma score dir dominante - opposta)
double   InpInstBaseSL           = 2.0;    // SL base (x ATR) prima dello scaling per tier
double   InpInstBaseTP           = 4.0;    // TP base (x ATR) prima dello scaling per tier
int      InpInstMinContributors  = 1;      // min strategie concordi per aprire
// Rete di sicurezza sulla recovery (martingala): tarata per un conto PICCOLO.
// v2.2.5 - FIX BLOWUP: su GOLD 1 lotto = ~$100/pip; su €200 il vecchio tetto di
// 1.00 lotti azzerava il conto in ~2 pip. Il tetto ora e' minuscolo e la recovery
// NON escala piu' la size (mult=1.0). Alzali SOLO man mano che il conto cresce.
int      InpInstMaxRecoveryDepth  = 2;     // max livelli di recovery (era 4)
double   InpInstMaxExposureLots   = 0.03;  // max lotti TOTALI per direzione (era 1.00) - adatto a ~200-500€
double   InpInstGridStepATR       = 1.0;   // passo griglia/recovery in ATR del tier
double   InpInstRecoveryMult      = 1.0;   // NIENTE martingala di default (era 1.5): add stessa size, non crescente
// Il tetto di esposizione SCALA col saldo (crescita geometrica sicura): a
// InpInstExposureRefBalance vale InpInstMaxExposureLots, e cresce/cala in
// proporzione al balance -> piccolo su €200, piu' largo man mano che cresce.
double   InpInstExposureRefBalance = 200.0; // saldo di riferimento per il tetto esposizione
double   InpInstGridMult          = 1.0;   // moltiplicatore lotto per livello di grid (profit -> add sul vincente)
double   InpInstAddLot            = 0.0;   // lotto base degli add (0 = usa lotto della posizione core)
// --- Protezione profitto: trailing (training stop) + runner ---
// Il trailing scatta prima del TP (a InpInstLockATR di profitto) e insegue a
// InpInstTrailATR di distanza, cosi da bloccare sempre un po' di profitto.
double   InpInstLockATR           = 0.6;   // profitto (x ATR tier) oltre il quale attiva il trailing
double   InpInstTrailATR          = 1.2;   // distanza del trailing dal prezzo (x ATR tier)
bool     InpInstRunner            = true;  // ultima op di grid/recovery = runner (segue il profitto oltre il TP)
double   InpInstRunnerTPmult      = 3.0;   // TP del runner (x TP di gruppo) prima che il trailing lo gestisca
// A) SL del gruppo oltre l'invalidazione strutturale del voto dominante, senza
//    far esplodere l'RR: lo SL puo' allargarsi fino a InpInstMaxSLwiden x lo SL di tier.
double   InpInstMaxSLwiden        = 1.75;  // max allargamento SL strutturale (x SL di tier); 0=solo tier
// B) Permanenza minima: finche' non passa, il trailing protegge ma NON stringe
//    fino a chiudere -> l'operazione ha spazio per svilupparsi (anche i TF minori).
int      InpInstMinHoldMin        = 20;    // minuti minimi prima che il trailing possa stringere
// --- Robustezza gestione soldi (v2.1.9) ---
// #6 Recovery intelligente: aggiunge in recovery SOLO se il contesto e' ancora a
//    favore. Non media contro un trend che si e' girato (anti-martingala-suicida).
bool     InpInstRecoveryNeedsContext = true;
// #5 Breakeven+ dopo il primo add di grid: dato che abbiamo messo size extra sul
//    vincente, blocchiamo il cluster a BE+ -> non puo' piu' tornare in perdita.
bool     InpInstBEAfterGrid       = true;
double   InpInstBEbufferATR       = 0.10;  // cuscinetto sopra il BE (x ATR)
// #7 Time-stop: chiude un trade fermo ~0 da troppo tempo (libera margine). OFF di
//    default (0) per non tagliare i trend lenti finche' non lo tariamo sui dati.
int      InpInstTimeStopMin       = 0;     // minuti; 0=off
double   InpInstTimeStopATR       = 0.20;  // "fermo" = |profitto| < questo (x ATR)
// --- Filtri NON indispensabili: OFF di default (v2.2.3) ---
// Spenti per non strozzare il numero di trade: il counter-trend drop + la RR
// sanity (sotto) bastano. Riaccendibili singolarmente se i dati veri lo chiedono.
// #9 Veto di regime: ridondante col counter-trend, classifica per nome (fragile).
bool     InpInstRegimeVeto        = false;
// Premium/Discount (SMC): raffinatezza, non indispensabile.
bool     InpInstPremDiscVeto      = false;
int      InpPDLookbackH1          = 20;    // barre H1 per il range operativo
double   InpPDExtreme             = 0.75;  // buy vetato se pos>questo; sell se pos<1-questo
// Soglia di volatilita' minima: strumento grezzo, rischia di sopprimere tutto.
double   InpInstMinATRfactor      = 0.0;   // 0=off; >0 = ATR corrente >= questo x media

// input group "=== SIZING AGGRESSIVO / ADATTIVO (v2.2.1) ==="
// Moltiplicatore lotto a livello di ACCOUNT (oltre il risk% e i cap per-trade).
// 1.0 = neutro; 1.5-2.0 = piu' aggressivo (lotti piu' alti). ATTENZIONE: amplifica
// SIA i profitti SIA le perdite -> alzarlo solo quando l'edge e' confermato.
double   InpLotAggressiveness     = 1.0;
// Scala il lotto sull'andamento: sale dopo N vittorie di fila, scende dopo N
// perdite di fila, dentro [floor, cap]. "Alza sui vincita, abbassa sulle perdite".
bool     InpUseStreakSizing       = true;
int      InpStreakWinsToScale     = 2;      // vittorie di fila per salire di uno step
double   InpStreakScaleUp         = 1.25;   // x per step in vincita
double   InpStreakMaxMult         = 2.00;   // tetto del moltiplicatore
int      InpStreakLossesToScale   = 2;      // perdite di fila per scendere di uno step
double   InpStreakScaleDown       = 0.60;   // x per step in perdita
double   InpStreakMinMult         = 0.40;   // pavimento del moltiplicatore

// input group "=== SCUDO RISK-OF-RUIN (v2.2.6) ==="
// Se la perdita del GIORNO supera la soglia, congela il trading fino al giorno
// dopo (e opzionalmente chiude tutto). Vale ANCHE in backtest -> i test mostrano
// la vera preservazione del capitale invece del blowup.
bool     InpRuinEnable            = true;
double   InpRuinDailyLossPct      = 15.0;  // perdita giornaliera % che congela il trading
bool     InpRuinFlatten           = true;  // alla soglia, chiude tutte le posizioni NEXUS
// --- Qualita' dei voti (prima del raggruppamento) ---
// Allinea la conviction al contesto: i voti concordi col mercato pesano di piu',
// quelli chiaramente controtrend (contro HTF+struttura senza conferma di
// reversal) vengono scartati -> niente short su supporto HTF e simili.
bool     InpInstUseContextQuality = true;  // pesa/scarta i voti in base al contesto prima di raggruppare
bool     InpInstCtxDropCounter    = true;  // scarta i voti contro HTF+struttura senza conferma di reversal
double   InpInstMinRR             = 1.20;  // RR minimo (TP/SL) del voto; sotto -> scartato (0=off)
double   InpInstMinSLATR          = 0.50;  // SL minimo (x ATR) del voto; sotto -> scartato (troppo stretto, si fa wickare)
// --- MTF: i due tempi devono essere d'accordo (anti-rumore) ---
// Il bias H4 (InpTFHigh) decide la direzione; su M15 (InpTFEntry) si entra in
// continuazione. Un voto sopravvive solo se concorda col bias H4, salvo reversal
// confermato (CHoCH/reazione). E' IL filtro che toglie il rumore dei trade a caso.
bool     InpMTFRequireHTF         = false;  // v2.2.8: sostituito dal gate HTF PER-STRATEGIA (profili)

// input group "=== SAFETY CAPS (v2.0.26) ==="
int      InpMaxNewTradesPerBarDir = 8;    // v2.3.4: non-binding; il vero cap e' la Setup Matrix per-TF
double   InpMaxTotalLotMult  = 1.5;        // hard cap on the combined lot multiplier (chain x counter-HTF x per-strategy risk x ...)
double   InpMaxDirExposureLots = 0.40;     // max sum of open lots in one direction (core positions) before new entries are rejected - generic/fallback value
// v2.0.30: a flat lot cap doesn't mean the same thing across symbols with very
// different contract sizes (e.g. BTCUSD vs GOLD) - these optional per-symbol
// overrides let you set a realistic cap for each. 0 = fall back to the
// generic InpMaxDirExposureLots above. Matched by substring against the
// chart's symbol name (see NXS_EffectiveMaxDirExposureLots in NXS_Globals.mqh).
double   InpMaxDirExposureLots_GOLD = 0.0;
double   InpMaxDirExposureLots_BTC  = 0.05;

// v2.0.37: TURTLE_SOUP is the only strategy with a double-confirmed edge so
// far (PF 1.92 in both the Step 3 engine-fix screening and the selector
// validation, on the same 3-week window) - a deliberate, isolated lot
// increase for THIS strategy only. Multiplies its lot size on top of the
// normal risk-based sizing; InpMaxTotalLotMult and InpMaxDirExposureLots(*)
// still apply afterward as absolute ceilings, unchanged. Logged separately
// (see NXS_Execution.mqh / NXS_ReusePerformancePack.mqh) so this is
// distinguishable from any other cap/multiplier if something looks off.
double   InpTurtleSoup_LotMult = 1.5;

// v2.0.33: found via live trade review - a stopped-out position was often
// immediately followed by a new position in the OPPOSITE direction at
// nearly the same price (chasing the reversal), which then also got
// stopped out. Blocks that specific whipsaw without touching the
// strategy's core logic.
bool     InpUsePostSLCooldown   = true;
int      InpPostSLCooldownMin  = 0;       // v2.2.8: il backtest non ha cooldown post-SL      // minutes to block opposite-direction entries after a stop-out

// v2.0.34 (audit point 8): universal exhaustion/extension gate - blocks a
// NEW entry that's chasing a move that's already gone too far (consecutive
// HH/LL with no pullback, price too far from EMA200, or RSI diverging
// against the entry direction). Applied in both execution paths.
bool     InpUseExhaustionGate      = false;  // v2.2.8: il backtest non ha exhaustion gate
int      InpExhaustionMaxConsecutive = 5;   // max consecutive HH (buy) / LL (sell) with no pullback before blocking
double   InpExhaustionEMADistATR    = 3.0;  // block if |price - EMA200| exceeds this many ATRs
int      InpExhaustionRsiDivLookback= 10;   // bars back to compare for RSI divergence check

// input group "=== ANTI-REVENGE ==="
bool     InpAntiRevenge      = true;
int      InpAntiRevengeLosses= 3;
int      InpAntiRevengeMin   = 60;

// input group "=== HTF BIAS ==="
bool     InpUseHTFBias       = false;   // OFF by default — gate must IMPROVE not BLOCK
int      InpHTF_EMAPeriod    = 50;
double   InpHTF_MinConf      = 0.55;
bool     InpHTF_AllowReversal= true;

// input group "=== VELOCITY GATE ==="
bool     InpUseVelocity      = false;   // OFF by default — was blocking too many trades
int      InpVel_ZLEMA        = 35;
double   InpVel_ATRMult      = 0.5;

// input group "=== NEWS FILTER ==="
bool     InpUseNews          = false;   // v2.2.8: il backtest non ha news filter
int      InpNewsMinBefore    = 5;     // was 30 — user wants tight buffer 5/5
int      InpNewsMinAfter     = 5;     // was 30 — user wants tight buffer 5/5
string   InpNewsCurrencies   = "USD,EUR,XAU";

// input group "=== AMD MODEL ==="
bool     InpUseAMD           = true;
int      InpAsianStartHour   = 0;
int      InpAsianEndHour     = 7;

// input group "=== BSP (Buyer/Seller Pressure) ==="
bool     InpUseBSP           = true;
double   InpBSPWeight        = 0.20;

// input group "=== SESSIONS ==="
bool     InpUseSessions      = true;
double   InpAsianScoreMin    = 65.0;
double   InpLondonScoreMin   = 60.0;
double   InpOverlapScoreMin  = 58.0;
double   InpNYScoreMin       = 60.0;
double   InpAfterNYScoreMin  = 70.0;

// input group "=== STRATEGIES TOGGLE ==="
bool     InpStrat_ADX_RSI      = true;
bool     InpStrat_BOLLINGER    = true;
bool     InpStrat_MACD         = true;
bool     InpStrat_SAR          = true;
bool     InpStrat_TSI          = true;
bool     InpStrat_BJORGUM      = true;
bool     InpStrat_LIQ_SWEEP    = true;
bool     InpStrat_FVG_CONT     = true;
bool     InpStrat_BREAKOUT_ACC = true;
bool     InpStrat_LONDON_BO    = true;
bool     InpStrat_EMA_PULLBACK = true;
bool     InpStrat_BB_SQUEEZE   = true;
bool     InpStrat_ICHIMOKU     = true;
bool     InpStrat_RSI_DIV      = true;
bool     InpStrat_ORDER_BLOCK  = true;
bool     InpUseStructReact     = true;

// input group "=== STRUCTURE ENGINE ==="
bool     InpUseStructure       = true;
int      InpSwingWing          = 3;
double   InpOBDisplacement     = 1.5;
double   InpFVGMinBody         = 0.5;

// input group "=== REACTION ENGINE ==="
bool     InpUseReaction        = true;
double   InpReactionTol        = 0.3;
bool     InpUseReactionEMA     = true;    // EMA200 come livello dinamico di reazione (confluenza)
double   InpReactEMABonus      = 12.0;    // bonus qualità reazione se coincide con la EMA200
double   InpReactEMATolATR     = 0.4;     // tolleranza distanza dalla EMA (× ATR)

// input group "=== INDICATORS ==="
int      InpADX_Period       = 14;
int      InpRSI_Period       = 14;
int      InpBB_Period        = 20;
double   InpBB_Dev           = 2.0;
int      InpMACD_Fast        = 12;
int      InpMACD_Slow        = 26;
int      InpMACD_Signal      = 9;
double   InpSAR_Step         = 0.02;
double   InpSAR_Max          = 0.2;
int      InpATR_Period       = 14;
int      InpEMA200_Period    = 200;
int      InpEMA9_Period      = 9;
int      InpEMA21_Period     = 21;

// input group "=== SL / TP ==="
double   InpATR_SL_Mult      = 2.0;    // v2.0.14: 1.8→2.0 (SL piu' largo su M5 gold)
double   InpATR_TP_Mult      = 2.6;
double   InpMinSLMult        = 1.5;    // v2.0.14: pavimento minimo moltiplicatore SL

// input group "=== CLOSE & REVERSE ==="
bool     InpEnableCloseReverse = true;
double   InpMinScoreReverse    = 70.0;       // v2.0.13: lowered 75→70 (chain smart-reverse can lower further)

// input group "=== STRATEGY CHAIN / CONTINUATION (v2.0.13) ==="
bool     InpChainEnableContinuation     = true;   // dopo profit, riapri in continuazione se setup compatibile
bool     InpChainEnableSmartReverse     = true;   // abbassa soglia reverse se reaction>=75 AND HTF concorde
int      InpChainContinuationWindowSec  = 1800;   // 30 min: finestra valida per continuazione
double   InpChainContinuationLotMult    = 0.6;    // lotto continuazione (60% del base)
int      InpChainMaxContinuations       = 3;      // n. max continuazioni dopo un trade vincente

// input group "=== BREAK EVEN & TRAIL ==="
double   InpBE_TriggerATR    = 1.0;
double   InpTrailActivateATR = 1.5;
double   InpTrailDistanceATR = 1.0;
double   InpTrailDistancePostBE = 0.7;   // tighter trail once BE reached
int      InpMaxHoldHours     = 4;        // force-close trade older than this
bool     InpUseAdaptiveSL    = true;     // dynamic SL by ATR regime
double   InpSL_HighVol_Mult  = 2.0;      // SL multiplier when ATR > avg
double   InpSL_LowVol_Mult   = 1.8;      // v2.0.14: 1.5→1.8 (SL piu' largo bassa vol)
int      InpATR_AvgPeriod    = 20;       // ATR moving-avg window
double   InpTP1_ATR          = 1.5;      // P1 partial-close at +1.5 ATR (was 1.0)
double   InpTP2_ATR          = 3.0;      // P2 partial-close at +3.0 ATR (was 2.0)
double   InpTP1_Pct          = 0.30;     // partial close 30% at TP1 (was 33%)
double   InpTP2_Pct          = 0.50;     // partial close 50% of remainder at TP2

// input group "=== ANTI-BLEED (P2) ==="
bool     InpUseAntiBleed     = true;
double   InpAB_RiskMult_1L   = 0.7;      // lot mult after 1 consecutive loss
double   InpAB_RiskMult_2L   = 0.7;      // after 2
double   InpAB_RiskMult_3L   = 0.4;      // after 3
int      InpAB_SkipAfter3L   = 2;        // skip next N signals after 3rd loss
double   InpAB_DD_Soft       = 2.0;      // DD% threshold for soft risk reduction
double   InpAB_DD_Hard       = 4.0;      // DD% for hard reduction + stricter score
double   InpAB_RiskMult_DDSoft= 0.7;
double   InpAB_RiskMult_DDHard= 0.4;
double   InpAB_ScoreBonus_DDHard = 10.0; // require MinEntryScore+10 when DD hard

// input group "=== GRID / PYRAMID / SPLIT ==="
bool     InpEnableGrid       = false;
double   InpGridStepATR      = 1.2;
bool     InpEnablePyramid    = false;
bool     InpEnableSplit      = true;

// input group "=== WEB BRIDGE ==="
bool     InpEnableWebSync    = true;                                   // WebSync ON di default
input string   InpWebURL           = "https://nexus-backend-8o4y.onrender.com"; // backend Render di default
input string   InpWebToken         = "NEXUS_BRIDGE_TOKEN_2026";
int      InpPushIntervalSec  = 5;
int      InpPollIntervalSec  = 3;
int      InpHistSyncIntervalSec = 1800;                                  // backfill periodico trade chiusi (sec) — safety net oltre OnInit

// input group "=== LOGGING ==="
bool     InpLogTrades        = true;
bool     InpDebugLog         = false;

//================================================================
//  NEXUS v2.0 / Phase 3-5 additions (additive — defaults preserve v1 behaviour)
//================================================================
// input group "=== RISK PROTECTIONS (v2.0) ==="
bool     InpUseESL           = true;   // Equity Stop Loss
bool     InpESL_IsPercent    = true;
double   InpESL_Value        = 5.0;    // 5% of balance
bool     InpUseDPT           = false;  // OFF by default — user wants to decide WHEN to stop
bool     InpDPT_IsPercent    = true;
double   InpDPT_Value        = 3.0;    // 3% of dayStart balance (only if InpUseDPT=true)
bool     InpUseMaxHold       = true;   // Max hold time per position
int      InpProt_MaxHoldHours= 12;
bool     InpUseMaxLossPos    = true;   // Max loss per position
double   InpMaxLossPosPct    = 2.0;    // % of balance
int      InpProt_MinLifeMin  = 15;     // v2.0.14: min minuti vita prima che NXS:RISK chiuda
bool     InpUseAutoClose     = true;   // Flatten before market close
int      InpAutoCloseMin     = 15;
int      InpMarketCloseGMT   = 21;

// input group "=== CONFLUENCE + COOLDOWN (Phase 3) ==="
bool     InpUseConfluence    = true;
int      InpConfluenceBonus2 = 10;
int      InpConfluenceBonus3 = 20;
int      InpConfluenceBonus4 = 30;
int      InpADXRsiScoreCap   = 70;   // cap anti-dominance

// input group "=== MARKET CONTEXT LAYER (v2.0.19) ==="
bool     InpUseMarketContext   = false;  // OFF di default: pesa la confluenza di contesto sullo score
double   InpCtxW_HTF           = 8.0;    // peso HTF bias allineato
double   InpCtxCounterFactor    = 1.0;    // moltiplicatore penalità quando contro-HTF
double   InpCtxW_Struct         = 5.0;    // peso trend di struttura (HH/HL)
double   InpCtxW_BOS            = 4.0;    // peso Break of Structure in direzione
double   InpCtxW_CHoCH          = 4.0;    // peso Change of Character in direzione
double   InpCtxW_React          = 10.0;   // peso reazione (× qualità/100)
double   InpCtxW_Sweep          = 6.0;    // peso liquidity sweep confermato
double   InpCtxW_Zone           = 5.0;    // peso zona FVG/OB attiva vicina in direzione
double   InpCtxW_AMD            = 3.0;    // bonus fase AMD attiva (manip/distrib)
double   InpCtxZoneATR          = 1.5;    // distanza max zona dal prezzo (× ATR)
double   InpCtxMaxBonus         = 20.0;   // tetto bonus totale di contesto
double   InpCtxMaxPenalty       = 15.0;   // tetto penalità totale di contesto
bool     InpUseStrategyCD    = true;
int      InpMaxConsecPerStrat= 3;
int      InpStratCooldownMin = 30;

// input group "=== MTF / SPREAD / VOL REGIME (Audit PDF) ==="
bool     InpUseMTFValidation = false;   // v2.2.8: il backtest non ha MTF validation
ENUM_TIMEFRAMES InpMTF_TF1   = PERIOD_H1;
ENUM_TIMEFRAMES InpMTF_TF2   = PERIOD_H4;
bool     InpUseDynamicSpread = true;
double   InpMaxSpreadAtrPct  = 8.0;    // spread > 8% of ATR → block
int      InpMaxSpreadPoints  = 0;     // 0 = use asset-class profile cap
bool     InpUseVolRegime     = true;
double   InpLowVolAtrPct     = 0.15;
double   InpHighVolAtrPct    = 0.6;

// input group "=== GATE MODE (v2.0.2 - sblocco trade) ==="
// 0=Conservative (block aggressive), 1=Balanced, 2=Discovery (very permissive), 3=DebugTrade
int      InpGateMode                       = 1;
// 0=block, 1=penalty score, 2=allow
int      InpMTFMixedMode                   = 1;
int      InpVelocityNeutralMode            = 1;
bool     InpAllowReversalAgainstMTFOnSweep = true;
bool     InpTryNextSignalIfBlocked         = true;
bool     InpDebugDecisionLog               = true;

// input group "=== SMC/ICT STRATEGIES (v2.0.2) ==="
bool     InpStrat_TurtleSoup     = true;
bool     InpStrat_IFVG           = true;
bool     InpStrat_FVG_Mit        = true;
bool     InpStrat_OB_Mit         = true;
bool     InpStrat_SH_BMS_RTO     = true;
bool     InpStrat_SMS_BMS_RTO    = true;
bool     InpStrat_SilverBullet   = true;
bool     InpStrat_AMD_Reversal   = true;
bool     InpStrat_OTE_Cont       = true;
bool     InpStrat_MalaysianSNR   = true;

// input group "=== INSTITUTIONAL MODELS (v2.0.7) ==="
bool     InpUseStrat_CISD          = true;
bool     InpUseStrat_AMD_Cont      = true;
bool     InpUseStrat_Judas         = true;
bool     InpUseStrat_LdnReversal   = true;
bool     InpUseStrat_NYReversal    = true;
bool     InpUseStrat_WeeklyExp     = true;
bool     InpUseStrat_PO3           = true;
bool     InpUseStrat_LiqVoid       = true;
bool     InpUseStrat_DispRebal     = true;

// input group "=== TIMEFRAME-AWARE SL/TP + LIFE (v2.0.21) ==="
double   InpTF_SLTP_H1   = 2.0;    // moltiplicatore SL/TP per segnali origine H1 (× ATR chart)
double   InpTF_SLTP_H4   = 3.5;    // idem H4
double   InpTF_SLTP_D1   = 5.0;    // idem D1
double   InpTF_Life_H1   = 8.0;    // moltiplicatore MinLife/MaxHold per origine H1
double   InpTF_Life_H4   = 20.0;   // idem H4
double   InpTF_Life_D1   = 60.0;   // idem D1

// input group "=== ELLIOTT WAVE (v2.0.20) ==="
bool     InpUseStrat_Elliott       = false;    // OFF di default: nuova strategia, backtesta prima
int      InpEllSwingWing           = 3;        // ampiezza fractal per i pivot di swing
double   InpEllRetraceMin          = 0.382;    // retracement min onda 2 (Fib)
double   InpEllRetraceMax          = 0.786;    // retracement max onda 2 (Fib)
double   InpEllMinScore            = 70.0;     // score base dei setup Elliott

// input group "=== RANGE / COUNTER-HTF (v2.0.8) ==="
bool     InpUseStrat_RangeFade     = true;     // mean-revert sui range stretti
bool     InpEnableCounterHTFSoft   = false;    // OPTIONAL: counter-trend HTF micro-trade
double   InpCounterHTF_MinReactQ   = 75.0;     // min reaction quality
double   InpCounterHTF_LotMult     = 0.40;     // lot reducer (40% of base)
double   InpCounterHTF_TP1Pct      = 70.0;     // % closed at 1R
double   InpCounterHTF_SLATR       = 1.5;      // v2.0.14: 1.2→1.5 (no SL sotto 1.5)
double   InpCounterHTF_MinRR       = 1.2;      // minimum reward/risk
int      InpCounterHTF_MaxPerSession = 1;      // anti-spam

// input group "=== ASSET CLASS / BTC (v2.0.8) ==="
int      InpAssetClass             = 0;        // 0=AUTO 1=FOREX 2=METAL 3=INDEX 4=CRYPTO
bool     InpCryptoWeekendMode      = true;     // allow trading weekends if crypto
double   InpCryptoSpreadCapATRPct  = 15.0;     // spread cap relaxed for crypto

// input group "=== SHADOW TRADING (v2.0.8) ==="
bool     InpEnableShadowTrading    = true;     // log blocked signals
bool     InpShadowPushToBackend    = true;     // WebRequest push
int      InpShadowExportEverySec   = 300;      // 5 min

// input group "=== VISUAL SUITE LAYERS (v2.0.7) ==="
bool     InpVis_CISD_Level         = false;
bool     InpVis_Judas_Marker       = false;
bool     InpVis_PO3_Phase          = false;
bool     InpVis_LiquidityVoid      = false;
bool     InpVis_DispRebalZone      = false;
bool     InpVis_WeeklyRange        = false;
bool     InpVis_LdnNyReversal      = false;

// input group "=== STATS / ANALYTICS (v2.0.5) ==="
bool     InpStatsEnable          = true;
int      InpStatsExportEverySec  = 300;   // CSV export interval (sec)
bool     InpStatsPushToBackend   = false; // optional WebRequest upload

// input group "=== SERVER TIME (v2.0.5b) ==="
input int      InpServerGMTOffset      = 2;     // server-time offset to GMT (h). 2 = CEST broker. Set 0 if your broker is UTC.

#endif
