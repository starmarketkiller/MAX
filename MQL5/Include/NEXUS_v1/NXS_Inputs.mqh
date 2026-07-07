//+------------------------------------------------------------------+
//|  NXS_Inputs.mqh - All input parameters                            |
//+------------------------------------------------------------------+
#ifndef __NXS_INPUTS_MQH__
#define __NXS_INPUTS_MQH__

input group "=== SCREENING SELECTOR (v2.0.36) ==="
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
input int InpStrategySelector = 0;

input group "=== GENERAL ==="
input long     InpMagic            = 991000;
input string   InpComment          = "NEXUS_v2";
input ENUM_TIMEFRAMES InpTFEntry   = PERIOD_M15;
input ENUM_TIMEFRAMES InpTFMedium  = PERIOD_H1;
input ENUM_TIMEFRAMES InpTFHigh    = PERIOD_H4;

input group "=== PRESET / SCALING ==="
// 0=Custom, 1=Conservative, 2=Balanced, 3=Aggressive, 4=MVP_v206 (5 SMC MVP)
input int      InpRiskProfile      = 2;
input bool     InpAutoScaleByAccount = true;

input group "=== SYMBOL WHITELIST ==="
input bool     InpUseSymbolWhitelist = true;
input string   InpAllowedSymbols   = "GOLD,XAUUSD,EURUSD,GBPUSD,USDJPY,USDCHF,AUDUSD,USDCAD,US30,NAS100,SPX500,GER40,BTCUSD,ETHUSD";

input group "=== LICENSE ==="
input bool     InpEnableLicense    = true;
input string   InpLicenseKey       = "";

input group "=== ROBUSTNESS (Phase 1) ==="
input int      InpHardMaxSpreadPts = 0;     // 0 = use profile default
input int      InpOrderRetries     = 3;     // retries on requote/off-quotes
input bool     InpUseStatePersist  = true;  // resume state after MT5 restart
input bool     InpUseAtrTrail      = true;  // ATR-based trailing stop
input double   InpAtrTrailMult     = 1.5;

input group "=== ON-CHART DASHBOARD ==="
input bool     InpShowDashboard    = true;
input int      InpDashX            = 10;
input int      InpDashY            = 25;

input group "=== NOTIFICATIONS ==="
input bool     InpNotifyPush       = false;   // MT5 mobile push
input bool     InpNotifyEmail      = false;
input bool     InpNotifyTelegram   = false;
input string   InpTelegramChatId   = "";
input bool     InpNotifyOnOpen     = true;
input bool     InpNotifyOnClose    = true;
input bool     InpNotifyOnProtection = true;
input bool     InpNotifyDailySummary = false;

input group "=== RISK MANAGEMENT ==="
input double   InpRiskPercent      = 1.0;
input double   InpMaxLot           = 5.0;
input int      InpMaxTradesPerDay  = 12;
input int      InpMaxConcurrent    = 4;
input double   InpMaxDailyDDPct    = 5.0;
input double   InpMinEntryScore    = 70.0;
input double   InpMalaysianMinScore = 80.0;  // v2.0.14: MALAYSIAN_SNR richiede score >= 80
input int      InpMinMarginLevel   = 200;

input group "=== DATA COLLECTION / SCREENING LIVE (v2.1.1) ==="
// Apre OGNI segnale valido di OGNI strategia a lotto fisso piccolo, saltando i
// gate soft (cooldown/MTF/velocity/exhaustion/exposure/best-per-bar) e la soglia
// di score. Tiene solo la sicurezza dura (spread/margine/stops via preflight).
// Serve a raccogliere dati REALI su TUTTE le strategie nel Journal per capire
// quali hanno edge, senza bocciarne nessuna a priori. USARE SU DEMO.
// NB: per vederle tutte, in .set metti tutti gli InpStrat_*/InpUseStrat_* = true
// e InpStrategySelector = 0.
input bool     InpDataCollectionMode   = false;  // OFF: si usa il grouping istituzionale (raccolta dati solo su demo)
input double   InpDataCollectionLot    = 0.01;   // lotto fisso per trade (piccolo)
input int      InpDataCollectionMaxOpen= 40;     // tetto posizioni aperte contemporanee (sicurezza)

input group "=== INSTITUTIONAL CORE (v2.1.0) ==="
// Master switch del modello istituzionale: lettura unica del mercato ->
// raggruppamento dei segnali per direzione -> 1 posizione per direzione con
// SL/TP scalati sul tier (TF di conferma) -> gestione uniforme grid/recovery.
// OFF di default: l'EA usa il modello attuale (best-per-bar) finché non lo
// attivi in Strategy Tester.
input bool     InpUseInstitutionalCore = true;
input double   InpInstMinConviction    = 60.0;   // conviction netta minima (somma score dir dominante - opposta)
input double   InpInstBaseSL           = 2.0;    // SL base (x ATR) prima dello scaling per tier
input double   InpInstBaseTP           = 4.0;    // TP base (x ATR) prima dello scaling per tier
input int      InpInstMinContributors  = 1;      // min strategie concordi per aprire
// Rete di sicurezza sulla recovery (martingala): tetto configurabile, largo.
input int      InpInstMaxRecoveryDepth  = 4;     // max livelli di recovery per sequenza (0=illimitato SCONSIGLIATO)
input double   InpInstMaxExposureLots   = 1.00;  // max lotti totali per direzione (core+grid+recovery)
input double   InpInstGridStepATR       = 1.0;   // passo griglia/recovery in ATR del tier
input double   InpInstRecoveryMult      = 1.5;   // moltiplicatore lotto per livello di recovery (loss -> add per recuperare)
input double   InpInstGridMult          = 1.0;   // moltiplicatore lotto per livello di grid (profit -> add sul vincente)
input double   InpInstAddLot            = 0.0;   // lotto base degli add (0 = usa lotto della posizione core)
// --- Protezione profitto: trailing (training stop) + runner ---
// Il trailing scatta prima del TP (a InpInstLockATR di profitto) e insegue a
// InpInstTrailATR di distanza, cosi da bloccare sempre un po' di profitto.
input double   InpInstLockATR           = 0.6;   // profitto (x ATR tier) oltre il quale attiva il trailing
input double   InpInstTrailATR          = 1.2;   // distanza del trailing dal prezzo (x ATR tier)
input bool     InpInstRunner            = true;  // ultima op di grid/recovery = runner (segue il profitto oltre il TP)
input double   InpInstRunnerTPmult      = 3.0;   // TP del runner (x TP di gruppo) prima che il trailing lo gestisca
// A) SL del gruppo oltre l'invalidazione strutturale del voto dominante, senza
//    far esplodere l'RR: lo SL puo' allargarsi fino a InpInstMaxSLwiden x lo SL di tier.
input double   InpInstMaxSLwiden        = 1.75;  // max allargamento SL strutturale (x SL di tier); 0=solo tier
// B) Permanenza minima: finche' non passa, il trailing protegge ma NON stringe
//    fino a chiudere -> l'operazione ha spazio per svilupparsi (anche i TF minori).
input int      InpInstMinHoldMin        = 20;    // minuti minimi prima che il trailing possa stringere
// --- Robustezza gestione soldi (v2.1.9) ---
// #6 Recovery intelligente: aggiunge in recovery SOLO se il contesto e' ancora a
//    favore. Non media contro un trend che si e' girato (anti-martingala-suicida).
input bool     InpInstRecoveryNeedsContext = true;
// #5 Breakeven+ dopo il primo add di grid: dato che abbiamo messo size extra sul
//    vincente, blocchiamo il cluster a BE+ -> non puo' piu' tornare in perdita.
input bool     InpInstBEAfterGrid       = true;
input double   InpInstBEbufferATR       = 0.10;  // cuscinetto sopra il BE (x ATR)
// #7 Time-stop: chiude un trade fermo ~0 da troppo tempo (libera margine). OFF di
//    default (0) per non tagliare i trend lenti finche' non lo tariamo sui dati.
input int      InpInstTimeStopMin       = 0;     // minuti; 0=off
input double   InpInstTimeStopATR       = 0.20;  // "fermo" = |profitto| < questo (x ATR)
// --- Filtri NON indispensabili: OFF di default (v2.2.3) ---
// Spenti per non strozzare il numero di trade: il counter-trend drop + la RR
// sanity (sotto) bastano. Riaccendibili singolarmente se i dati veri lo chiedono.
// #9 Veto di regime: ridondante col counter-trend, classifica per nome (fragile).
input bool     InpInstRegimeVeto        = false;
// Premium/Discount (SMC): raffinatezza, non indispensabile.
input bool     InpInstPremDiscVeto      = false;
input int      InpPDLookbackH1          = 20;    // barre H1 per il range operativo
input double   InpPDExtreme             = 0.75;  // buy vetato se pos>questo; sell se pos<1-questo
// Soglia di volatilita' minima: strumento grezzo, rischia di sopprimere tutto.
input double   InpInstMinATRfactor      = 0.0;   // 0=off; >0 = ATR corrente >= questo x media

input group "=== SIZING AGGRESSIVO / ADATTIVO (v2.2.1) ==="
// Moltiplicatore lotto a livello di ACCOUNT (oltre il risk% e i cap per-trade).
// 1.0 = neutro; 1.5-2.0 = piu' aggressivo (lotti piu' alti). ATTENZIONE: amplifica
// SIA i profitti SIA le perdite -> alzarlo solo quando l'edge e' confermato.
input double   InpLotAggressiveness     = 1.0;
// Scala il lotto sull'andamento: sale dopo N vittorie di fila, scende dopo N
// perdite di fila, dentro [floor, cap]. "Alza sui vincita, abbassa sulle perdite".
input bool     InpUseStreakSizing       = true;
input int      InpStreakWinsToScale     = 2;      // vittorie di fila per salire di uno step
input double   InpStreakScaleUp         = 1.25;   // x per step in vincita
input double   InpStreakMaxMult         = 2.00;   // tetto del moltiplicatore
input int      InpStreakLossesToScale   = 2;      // perdite di fila per scendere di uno step
input double   InpStreakScaleDown       = 0.60;   // x per step in perdita
input double   InpStreakMinMult         = 0.40;   // pavimento del moltiplicatore
// --- Qualita' dei voti (prima del raggruppamento) ---
// Allinea la conviction al contesto: i voti concordi col mercato pesano di piu',
// quelli chiaramente controtrend (contro HTF+struttura senza conferma di
// reversal) vengono scartati -> niente short su supporto HTF e simili.
input bool     InpInstUseContextQuality = true;  // pesa/scarta i voti in base al contesto prima di raggruppare
input bool     InpInstCtxDropCounter    = true;  // scarta i voti contro HTF+struttura senza conferma di reversal
input double   InpInstMinRR             = 1.20;  // RR minimo (TP/SL) del voto; sotto -> scartato (0=off)
input double   InpInstMinSLATR          = 0.50;  // SL minimo (x ATR) del voto; sotto -> scartato (troppo stretto, si fa wickare)
// --- MTF: i due tempi devono essere d'accordo (anti-rumore) ---
// Il bias H4 (InpTFHigh) decide la direzione; su M15 (InpTFEntry) si entra in
// continuazione. Un voto sopravvive solo se concorda col bias H4, salvo reversal
// confermato (CHoCH/reazione). E' IL filtro che toglie il rumore dei trade a caso.
input bool     InpMTFRequireHTF         = true;

input group "=== SAFETY CAPS (v2.0.26) ==="
input int      InpMaxNewTradesPerBarDir = 1;    // max NEW independent entries per direction per bar (confluence != multiple opens)
input double   InpMaxTotalLotMult  = 1.5;        // hard cap on the combined lot multiplier (chain x counter-HTF x per-strategy risk x ...)
input double   InpMaxDirExposureLots = 0.40;     // max sum of open lots in one direction (core positions) before new entries are rejected - generic/fallback value
// v2.0.30: a flat lot cap doesn't mean the same thing across symbols with very
// different contract sizes (e.g. BTCUSD vs GOLD) - these optional per-symbol
// overrides let you set a realistic cap for each. 0 = fall back to the
// generic InpMaxDirExposureLots above. Matched by substring against the
// chart's symbol name (see NXS_EffectiveMaxDirExposureLots in NXS_Globals.mqh).
input double   InpMaxDirExposureLots_GOLD = 0.0;
input double   InpMaxDirExposureLots_BTC  = 0.05;

// v2.0.37: TURTLE_SOUP is the only strategy with a double-confirmed edge so
// far (PF 1.92 in both the Step 3 engine-fix screening and the selector
// validation, on the same 3-week window) - a deliberate, isolated lot
// increase for THIS strategy only. Multiplies its lot size on top of the
// normal risk-based sizing; InpMaxTotalLotMult and InpMaxDirExposureLots(*)
// still apply afterward as absolute ceilings, unchanged. Logged separately
// (see NXS_Execution.mqh / NXS_ReusePerformancePack.mqh) so this is
// distinguishable from any other cap/multiplier if something looks off.
input double   InpTurtleSoup_LotMult = 1.5;

// v2.0.33: found via live trade review - a stopped-out position was often
// immediately followed by a new position in the OPPOSITE direction at
// nearly the same price (chasing the reversal), which then also got
// stopped out. Blocks that specific whipsaw without touching the
// strategy's core logic.
input bool     InpUsePostSLCooldown   = true;
input int      InpPostSLCooldownMin  = 20;      // minutes to block opposite-direction entries after a stop-out

// v2.0.34 (audit point 8): universal exhaustion/extension gate - blocks a
// NEW entry that's chasing a move that's already gone too far (consecutive
// HH/LL with no pullback, price too far from EMA200, or RSI diverging
// against the entry direction). Applied in both execution paths.
input bool     InpUseExhaustionGate      = true;
input int      InpExhaustionMaxConsecutive = 5;   // max consecutive HH (buy) / LL (sell) with no pullback before blocking
input double   InpExhaustionEMADistATR    = 3.0;  // block if |price - EMA200| exceeds this many ATRs
input int      InpExhaustionRsiDivLookback= 10;   // bars back to compare for RSI divergence check

input group "=== ANTI-REVENGE ==="
input bool     InpAntiRevenge      = true;
input int      InpAntiRevengeLosses= 3;
input int      InpAntiRevengeMin   = 60;

input group "=== HTF BIAS ==="
input bool     InpUseHTFBias       = false;   // OFF by default — gate must IMPROVE not BLOCK
input int      InpHTF_EMAPeriod    = 50;
input double   InpHTF_MinConf      = 0.55;
input bool     InpHTF_AllowReversal= true;

input group "=== VELOCITY GATE ==="
input bool     InpUseVelocity      = false;   // OFF by default — was blocking too many trades
input int      InpVel_ZLEMA        = 35;
input double   InpVel_ATRMult      = 0.5;

input group "=== NEWS FILTER ==="
input bool     InpUseNews          = true;
input int      InpNewsMinBefore    = 5;     // was 30 — user wants tight buffer 5/5
input int      InpNewsMinAfter     = 5;     // was 30 — user wants tight buffer 5/5
input string   InpNewsCurrencies   = "USD,EUR,XAU";

input group "=== AMD MODEL ==="
input bool     InpUseAMD           = true;
input int      InpAsianStartHour   = 0;
input int      InpAsianEndHour     = 7;

input group "=== BSP (Buyer/Seller Pressure) ==="
input bool     InpUseBSP           = true;
input double   InpBSPWeight        = 0.20;

input group "=== SESSIONS ==="
input bool     InpUseSessions      = true;
input double   InpAsianScoreMin    = 65.0;
input double   InpLondonScoreMin   = 60.0;
input double   InpOverlapScoreMin  = 58.0;
input double   InpNYScoreMin       = 60.0;
input double   InpAfterNYScoreMin  = 70.0;

input group "=== STRATEGIES TOGGLE ==="
input bool     InpStrat_ADX_RSI      = true;
input bool     InpStrat_BOLLINGER    = true;
input bool     InpStrat_MACD         = true;
input bool     InpStrat_SAR          = true;
input bool     InpStrat_TSI          = true;
input bool     InpStrat_BJORGUM      = true;
input bool     InpStrat_LIQ_SWEEP    = true;
input bool     InpStrat_FVG_CONT     = true;
input bool     InpStrat_BREAKOUT_ACC = true;
input bool     InpStrat_LONDON_BO    = true;
input bool     InpStrat_EMA_PULLBACK = true;
input bool     InpStrat_BB_SQUEEZE   = true;
input bool     InpStrat_ICHIMOKU     = true;
input bool     InpStrat_RSI_DIV      = true;
input bool     InpStrat_ORDER_BLOCK  = true;
input bool     InpUseStructReact     = true;

input group "=== STRUCTURE ENGINE ==="
input bool     InpUseStructure       = true;
input int      InpSwingWing          = 3;
input double   InpOBDisplacement     = 1.5;
input double   InpFVGMinBody         = 0.5;

input group "=== REACTION ENGINE ==="
input bool     InpUseReaction        = true;
input double   InpReactionTol        = 0.3;
input bool     InpUseReactionEMA     = true;    // EMA200 come livello dinamico di reazione (confluenza)
input double   InpReactEMABonus      = 12.0;    // bonus qualità reazione se coincide con la EMA200
input double   InpReactEMATolATR     = 0.4;     // tolleranza distanza dalla EMA (× ATR)

input group "=== INDICATORS ==="
input int      InpADX_Period       = 14;
input int      InpRSI_Period       = 14;
input int      InpBB_Period        = 20;
input double   InpBB_Dev           = 2.0;
input int      InpMACD_Fast        = 12;
input int      InpMACD_Slow        = 26;
input int      InpMACD_Signal      = 9;
input double   InpSAR_Step         = 0.02;
input double   InpSAR_Max          = 0.2;
input int      InpATR_Period       = 14;
input int      InpEMA200_Period    = 200;
input int      InpEMA9_Period      = 9;
input int      InpEMA21_Period     = 21;

input group "=== SL / TP ==="
input double   InpATR_SL_Mult      = 2.0;    // v2.0.14: 1.8→2.0 (SL piu' largo su M5 gold)
input double   InpATR_TP_Mult      = 2.6;
input double   InpMinSLMult        = 1.5;    // v2.0.14: pavimento minimo moltiplicatore SL

input group "=== CLOSE & REVERSE ==="
input bool     InpEnableCloseReverse = true;
input double   InpMinScoreReverse    = 70.0;       // v2.0.13: lowered 75→70 (chain smart-reverse can lower further)

input group "=== STRATEGY CHAIN / CONTINUATION (v2.0.13) ==="
input bool     InpChainEnableContinuation     = true;   // dopo profit, riapri in continuazione se setup compatibile
input bool     InpChainEnableSmartReverse     = true;   // abbassa soglia reverse se reaction>=75 AND HTF concorde
input int      InpChainContinuationWindowSec  = 1800;   // 30 min: finestra valida per continuazione
input double   InpChainContinuationLotMult    = 0.6;    // lotto continuazione (60% del base)
input int      InpChainMaxContinuations       = 3;      // n. max continuazioni dopo un trade vincente

input group "=== BREAK EVEN & TRAIL ==="
input double   InpBE_TriggerATR    = 1.0;
input double   InpTrailActivateATR = 1.5;
input double   InpTrailDistanceATR = 1.0;
input double   InpTrailDistancePostBE = 0.7;   // tighter trail once BE reached
input int      InpMaxHoldHours     = 4;        // force-close trade older than this
input bool     InpUseAdaptiveSL    = true;     // dynamic SL by ATR regime
input double   InpSL_HighVol_Mult  = 2.0;      // SL multiplier when ATR > avg
input double   InpSL_LowVol_Mult   = 1.8;      // v2.0.14: 1.5→1.8 (SL piu' largo bassa vol)
input int      InpATR_AvgPeriod    = 20;       // ATR moving-avg window
input double   InpTP1_ATR          = 1.5;      // P1 partial-close at +1.5 ATR (was 1.0)
input double   InpTP2_ATR          = 3.0;      // P2 partial-close at +3.0 ATR (was 2.0)
input double   InpTP1_Pct          = 0.30;     // partial close 30% at TP1 (was 33%)
input double   InpTP2_Pct          = 0.50;     // partial close 50% of remainder at TP2

input group "=== ANTI-BLEED (P2) ==="
input bool     InpUseAntiBleed     = true;
input double   InpAB_RiskMult_1L   = 0.7;      // lot mult after 1 consecutive loss
input double   InpAB_RiskMult_2L   = 0.7;      // after 2
input double   InpAB_RiskMult_3L   = 0.4;      // after 3
input int      InpAB_SkipAfter3L   = 2;        // skip next N signals after 3rd loss
input double   InpAB_DD_Soft       = 2.0;      // DD% threshold for soft risk reduction
input double   InpAB_DD_Hard       = 4.0;      // DD% for hard reduction + stricter score
input double   InpAB_RiskMult_DDSoft= 0.7;
input double   InpAB_RiskMult_DDHard= 0.4;
input double   InpAB_ScoreBonus_DDHard = 10.0; // require MinEntryScore+10 when DD hard

input group "=== GRID / PYRAMID / SPLIT ==="
input bool     InpEnableGrid       = false;
input double   InpGridStepATR      = 1.2;
input bool     InpEnablePyramid    = false;
input bool     InpEnableSplit      = true;

input group "=== WEB BRIDGE ==="
input bool     InpEnableWebSync    = true;                                   // WebSync ON di default
input string   InpWebURL           = "https://nexus-backend-8o4y.onrender.com"; // backend Render di default
input string   InpWebToken         = "NEXUS_BRIDGE_TOKEN_2026";
input int      InpPushIntervalSec  = 5;
input int      InpPollIntervalSec  = 3;
input int      InpHistSyncIntervalSec = 1800;                                  // backfill periodico trade chiusi (sec) — safety net oltre OnInit

input group "=== LOGGING ==="
input bool     InpLogTrades        = true;
input bool     InpDebugLog         = false;

//================================================================
//  NEXUS v2.0 / Phase 3-5 additions (additive — defaults preserve v1 behaviour)
//================================================================
input group "=== RISK PROTECTIONS (v2.0) ==="
input bool     InpUseESL           = true;   // Equity Stop Loss
input bool     InpESL_IsPercent    = true;
input double   InpESL_Value        = 5.0;    // 5% of balance
input bool     InpUseDPT           = false;  // OFF by default — user wants to decide WHEN to stop
input bool     InpDPT_IsPercent    = true;
input double   InpDPT_Value        = 3.0;    // 3% of dayStart balance (only if InpUseDPT=true)
input bool     InpUseMaxHold       = true;   // Max hold time per position
input int      InpProt_MaxHoldHours= 12;
input bool     InpUseMaxLossPos    = true;   // Max loss per position
input double   InpMaxLossPosPct    = 2.0;    // % of balance
input int      InpProt_MinLifeMin  = 15;     // v2.0.14: min minuti vita prima che NXS:RISK chiuda
input bool     InpUseAutoClose     = true;   // Flatten before market close
input int      InpAutoCloseMin     = 15;
input int      InpMarketCloseGMT   = 21;

input group "=== CONFLUENCE + COOLDOWN (Phase 3) ==="
input bool     InpUseConfluence    = true;
input int      InpConfluenceBonus2 = 10;
input int      InpConfluenceBonus3 = 20;
input int      InpConfluenceBonus4 = 30;
input int      InpADXRsiScoreCap   = 70;   // cap anti-dominance

input group "=== MARKET CONTEXT LAYER (v2.0.19) ==="
input bool     InpUseMarketContext   = false;  // OFF di default: pesa la confluenza di contesto sullo score
input double   InpCtxW_HTF           = 8.0;    // peso HTF bias allineato
input double   InpCtxCounterFactor    = 1.0;    // moltiplicatore penalità quando contro-HTF
input double   InpCtxW_Struct         = 5.0;    // peso trend di struttura (HH/HL)
input double   InpCtxW_BOS            = 4.0;    // peso Break of Structure in direzione
input double   InpCtxW_CHoCH          = 4.0;    // peso Change of Character in direzione
input double   InpCtxW_React          = 10.0;   // peso reazione (× qualità/100)
input double   InpCtxW_Sweep          = 6.0;    // peso liquidity sweep confermato
input double   InpCtxW_Zone           = 5.0;    // peso zona FVG/OB attiva vicina in direzione
input double   InpCtxW_AMD            = 3.0;    // bonus fase AMD attiva (manip/distrib)
input double   InpCtxZoneATR          = 1.5;    // distanza max zona dal prezzo (× ATR)
input double   InpCtxMaxBonus         = 20.0;   // tetto bonus totale di contesto
input double   InpCtxMaxPenalty       = 15.0;   // tetto penalità totale di contesto
input bool     InpUseStrategyCD    = true;
input int      InpMaxConsecPerStrat= 3;
input int      InpStratCooldownMin = 30;

input group "=== MTF / SPREAD / VOL REGIME (Audit PDF) ==="
input bool     InpUseMTFValidation = true;
input ENUM_TIMEFRAMES InpMTF_TF1   = PERIOD_H1;
input ENUM_TIMEFRAMES InpMTF_TF2   = PERIOD_H4;
input bool     InpUseDynamicSpread = true;
input double   InpMaxSpreadAtrPct  = 8.0;    // spread > 8% of ATR → block
input int      InpMaxSpreadPoints  = 0;     // 0 = use asset-class profile cap
input bool     InpUseVolRegime     = true;
input double   InpLowVolAtrPct     = 0.15;
input double   InpHighVolAtrPct    = 0.6;

input group "=== GATE MODE (v2.0.2 - sblocco trade) ==="
// 0=Conservative (block aggressive), 1=Balanced, 2=Discovery (very permissive), 3=DebugTrade
input int      InpGateMode                       = 1;
// 0=block, 1=penalty score, 2=allow
input int      InpMTFMixedMode                   = 1;
input int      InpVelocityNeutralMode            = 1;
input bool     InpAllowReversalAgainstMTFOnSweep = true;
input bool     InpTryNextSignalIfBlocked         = true;
input bool     InpDebugDecisionLog               = true;

input group "=== SMC/ICT STRATEGIES (v2.0.2) ==="
input bool     InpStrat_TurtleSoup     = true;
input bool     InpStrat_IFVG           = true;
input bool     InpStrat_FVG_Mit        = true;
input bool     InpStrat_OB_Mit         = true;
input bool     InpStrat_SH_BMS_RTO     = true;
input bool     InpStrat_SMS_BMS_RTO    = true;
input bool     InpStrat_SilverBullet   = true;
input bool     InpStrat_AMD_Reversal   = true;
input bool     InpStrat_OTE_Cont       = true;
input bool     InpStrat_MalaysianSNR   = true;

input group "=== INSTITUTIONAL MODELS (v2.0.7) ==="
input bool     InpUseStrat_CISD          = true;
input bool     InpUseStrat_AMD_Cont      = true;
input bool     InpUseStrat_Judas         = true;
input bool     InpUseStrat_LdnReversal   = true;
input bool     InpUseStrat_NYReversal    = true;
input bool     InpUseStrat_WeeklyExp     = true;
input bool     InpUseStrat_PO3           = true;
input bool     InpUseStrat_LiqVoid       = true;
input bool     InpUseStrat_DispRebal     = true;

input group "=== TIMEFRAME-AWARE SL/TP + LIFE (v2.0.21) ==="
input double   InpTF_SLTP_H1   = 2.0;    // moltiplicatore SL/TP per segnali origine H1 (× ATR chart)
input double   InpTF_SLTP_H4   = 3.5;    // idem H4
input double   InpTF_SLTP_D1   = 5.0;    // idem D1
input double   InpTF_Life_H1   = 8.0;    // moltiplicatore MinLife/MaxHold per origine H1
input double   InpTF_Life_H4   = 20.0;   // idem H4
input double   InpTF_Life_D1   = 60.0;   // idem D1

input group "=== ELLIOTT WAVE (v2.0.20) ==="
input bool     InpUseStrat_Elliott       = false;    // OFF di default: nuova strategia, backtesta prima
input int      InpEllSwingWing           = 3;        // ampiezza fractal per i pivot di swing
input double   InpEllRetraceMin          = 0.382;    // retracement min onda 2 (Fib)
input double   InpEllRetraceMax          = 0.786;    // retracement max onda 2 (Fib)
input double   InpEllMinScore            = 70.0;     // score base dei setup Elliott

input group "=== RANGE / COUNTER-HTF (v2.0.8) ==="
input bool     InpUseStrat_RangeFade     = true;     // mean-revert sui range stretti
input bool     InpEnableCounterHTFSoft   = false;    // OPTIONAL: counter-trend HTF micro-trade
input double   InpCounterHTF_MinReactQ   = 75.0;     // min reaction quality
input double   InpCounterHTF_LotMult     = 0.40;     // lot reducer (40% of base)
input double   InpCounterHTF_TP1Pct      = 70.0;     // % closed at 1R
input double   InpCounterHTF_SLATR       = 1.5;      // v2.0.14: 1.2→1.5 (no SL sotto 1.5)
input double   InpCounterHTF_MinRR       = 1.2;      // minimum reward/risk
input int      InpCounterHTF_MaxPerSession = 1;      // anti-spam

input group "=== ASSET CLASS / BTC (v2.0.8) ==="
input int      InpAssetClass             = 0;        // 0=AUTO 1=FOREX 2=METAL 3=INDEX 4=CRYPTO
input bool     InpCryptoWeekendMode      = true;     // allow trading weekends if crypto
input double   InpCryptoSpreadCapATRPct  = 15.0;     // spread cap relaxed for crypto

input group "=== SHADOW TRADING (v2.0.8) ==="
input bool     InpEnableShadowTrading    = true;     // log blocked signals
input bool     InpShadowPushToBackend    = true;     // WebRequest push
input int      InpShadowExportEverySec   = 300;      // 5 min

input group "=== VISUAL SUITE LAYERS (v2.0.7) ==="
input bool     InpVis_CISD_Level         = false;
input bool     InpVis_Judas_Marker       = false;
input bool     InpVis_PO3_Phase          = false;
input bool     InpVis_LiquidityVoid      = false;
input bool     InpVis_DispRebalZone      = false;
input bool     InpVis_WeeklyRange        = false;
input bool     InpVis_LdnNyReversal      = false;

input group "=== STATS / ANALYTICS (v2.0.5) ==="
input bool     InpStatsEnable          = true;
input int      InpStatsExportEverySec  = 300;   // CSV export interval (sec)
input bool     InpStatsPushToBackend   = false; // optional WebRequest upload

input group "=== SERVER TIME (v2.0.5b) ==="
input int      InpServerGMTOffset      = 2;     // server-time offset to GMT (h). 2 = CEST broker. Set 0 if your broker is UTC.

#endif
