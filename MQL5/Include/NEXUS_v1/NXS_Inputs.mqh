//+------------------------------------------------------------------+
//|  NXS_Inputs.mqh - All input parameters                            |
//+------------------------------------------------------------------+
#ifndef __NXS_INPUTS_MQH__
#define __NXS_INPUTS_MQH__

input group "=== NEXUS v2.3.0 — PARAMETRI ATTIVI ==="

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
// 15/07: era un semplice "int" (mai esposto al Tester/Optimization nonostante
// il commento sopra lo descrivesse gia' da v2.0.36) - reso "input" cosi'
// l'Optimization 1..37 descritta sopra e' davvero lanciabile, invece di dover
// ricompilare 37 EA separati. Default 0 invariato: comportamento normale
// (tutte le strategie secondo i loro toggle) resta identico finche' non lo si
// tocca esplicitamente nella scheda Input del Tester.
input int InpStrategySelector = 0;

// input group "=== GENERAL ==="
input long     InpMagic            = 991000;
input string   InpComment          = "NEXUS_v2.50";  // build v2.5.0 (HTF filter universale dallo sweep sito 10y)
ENUM_TIMEFRAMES InpTFEntry   = PERIOD_M15;
ENUM_TIMEFRAMES InpTFMedium  = PERIOD_H1;
ENUM_TIMEFRAMES InpTFHigh    = PERIOD_H4;

// input group "=== PRESET / SCALING ==="
// 0=Custom, 1=Conservative, 2=Balanced, 3=Aggressive, 4=MVP_v206 (5 SMC MVP)
int      InpRiskProfile      = 2;
// 25/08 - disattivato di default su richiesta esplicita dell'utente
// (account demo 318337486, balance<1000): con true il rischio del
// preset BALANCED (1.0%) veniva dimezzato a 0.5% effettivo, troppo
// stretto per far passare anche il lotto minimo su GOLD ai prezzi
// attuali (~$4370). Nota: anche a 1.0% pieno un trade che richiede il
// lotto minimo puo' ancora essere rifiutato se lo stop e' molto largo -
// non e' una leva che garantisce l'esecuzione, solo raddoppia il
// budget di rischio disponibile.
bool     InpAutoScaleByAccount = false;

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
double   InpAtrTrailMult     = 2.5;   // v2.4.4: 1.5->2.5 "lascia correre" - trail piu' largo, le vincenti cavalcano il movimento
double   InpAtrTrailActivateATR = 1.0; // v2.4.4: attiva il trail solo dopo +1.0 ATR (era 0.5) - da' spazio al trade per svilupparsi

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
input int      InpMaxPerDirTF      = 4;      // v2.4.8: HEDGE ON - corsie indipendenti, ogni strategia la sua (regolate dal gate margine)
input double   InpMaxDailyDDPct    = 5.0;
// v2.4.1 — GATE SUL MARGINE: il conto stesso regola quante strategie possono
// stare aperte insieme. Apri un nuovo trade solo se il margin level PROIETTATO
// (equity / margine usato dopo il trade) resta sopra la soglia. Cosi' un trade
// in profitto alza l'equity -> alza il livello -> APRE spazio ad altre; un
// drawdown lo abbassa -> frena da solo. "profitto = margine = spazio".
input bool     InpUseMarginGate    = true;    // v2.4.8: HEDGE ON - regola la concorrenza col margine (freno di sicurezza sul DD)
input double   InpMinMarginLevelPct = 500.0; // livello margine minimo proiettato per aprire (0=off)
// 10/08 - CAP DI RISCHIO AGGREGATO: InpMaxConcurrent limita il NUMERO di
// posizioni ma non la loro somma in %. Con la config demo a 15+ strategie
// indipendenti (rischio individuale fino al 5%, vedi NXS_StrategyProfiles.mqh,
// ritarato 12/08 per conto piccolo) piu' segnali possono scattare sulla stessa
// barra e sommare un'esposizione ben oltre il rischio "per trade" nominale -
// vedi vault NEXUS EA - Config Demo 15 Strategie (10-08). 0 = disattivo
// (comportamento identico a prima). Controllato in NXS_CheckProtections via
// NXS_OpenRiskPct() (NXS_Globals.mqh): se il rischio GIA' aperto (somma su
// tutte le posizioni NEXUS, distanza SL ATTUALE non quella storica
// all'apertura) e' gia' al tetto, un nuovo ingresso viene rifiutato
// indipendentemente dalla sua size - stesso stile "reject esplicito, mai
// clamp silenzioso" di AUD0-RISK-002/003.
// 12/08 - alzato 15.0->25.0: coi tier per-strategia ora fino al 5% (contro il
// 3% massimo precedente), 15% avrebbe bloccato l'operativita' normale gia'
// con 3 strategie tier S aperte insieme (15%). 25% resta un freno reale (il
// caso limite teorico con tutte e 16 le strategie del nucleo aperte insieme
// sarebbe ~31% - vedi vault "Rischio a Livelli e Moltiplicatore da Streak"),
// non un cap simbolico.
input double   InpMaxAggregateRiskPct = 25.0;
// v2.5.x — tetto ESPLICITO al rischio quando il lotto minimo broker supera il
// budget calcolato (vedi AUD0-RISK-002 in NXS_Risk.mqh). Default 0 = comportamento
// invariato: l'ordine viene rifiutato. Se > 0, il lotto minimo viene comunque
// accettato a patto che il rischio EFFETTIVO in quel trade non superi questa %
// del saldo (indipendente dal rischio% nominale della strategia) — pensato per
// conti piccoli (~€200-1000) dove il lotto minimo e' strutturalmente sopra il
// budget nominale su XAUUSD. Ogni sforamento viene loggato come tale, mai silente.
// 12/08 - alzato 0.0->8.0: con un conto ~200-300 EUR il lotto minimo XAUUSD
// supera quasi sempre il budget nominale sui tier bassi (0.3-0.5%), quindi a
// 0.0 l'EA di fatto non tradava la maggior parte dei segnali - vedi vault
// "Rischio a Livelli e Moltiplicatore da Streak" (12/08).
input double   InpMaxRiskAtMinLotPct = 8.0;

input group "=== RISCHIO A LIVELLI: MOLTIPLICATORE DA PERDITE CONSECUTIVE (12/08) ==="
// Richiesta esplicita dell'utente (conto ~200-300 EUR): dopo una serie di
// perdite consecutive SULLA STESSA STRATEGIA, il rischio di quella strategia
// sale temporaneamente per recuperare piu' in fretta, invece di restare
// piatto. E' l'OPPOSTO concettuale di InpUseAntiBleed/InpUseStreakSizing
// sotto (quelli RIDUCONO il rischio dopo perdite) - NON abilitare insieme
// sulla stessa strategia, l'effetto netto sarebbe imprevedibile. Vedi
// NXS_StreakRisk.mqh per i dettagli e i guardrail. Default OFF (comportamento
// invariato) - l'utente lo abilita esplicitamente sul proprio conto live.
input bool     InpUseLossStreakScaling = false;
// Ogni quante perdite consecutive scatta uno step di scalata (ripetuto: alla
// 3a, 6a, 9a... perdita di fila, fino al tetto InpSRisk_MaxMult).
input int      InpSRisk_LossesToScale  = 3;
// Moltiplicatore applicato ad ogni step (non un raddoppio: 1.3x per step,
// non 2x - un martingale puro con InpSRisk_LossesToScale=3 impiegherebbe
// solo 3 serie di 3 perdite per arrivare a 8x il rischio base).
input double   InpSRisk_ScaleStep      = 1.3;
// Tetto assoluto: il moltiplicatore non supera mai questo valore,
// indipendentemente da quante perdite consecutive si accumulano. Con i
// default sopra servono 9 perdite consecutive sulla stessa strategia per
// arrivare al tetto (1.3^3 = 2.197, cappato a 2.0).
input double   InpSRisk_MaxMult        = 2.0;
double   InpMinEntryScore    = 50.0;   // v2.2.8: abbassato, il backtest prende il segnale (i profili filtrano)
double   InpMalaysianMinScore = 80.0;  // v2.0.14: MALAYSIAN_SNR richiede score >= 80
int      InpMinMarginLevel   = 200;

input group "=== DATA COLLECTION / SCREENING LIVE (v2.1.1) ==="
// Apre OGNI segnale valido di OGNI strategia a lotto fisso piccolo, saltando i
// gate soft (cooldown/MTF/velocity/exhaustion/exposure/best-per-bar) e la soglia
// di score. Tiene solo la sicurezza dura (spread/margine/stops via preflight).
// Serve a raccogliere dati REALI su TUTTE le strategie nel Journal per capire
// quali hanno edge, senza bocciarne nessuna a priori. USARE SU DEMO.
// NB: per vederle tutte, in .set metti tutti gli InpStrat_*/InpUseStrat_* = true
// e InpStrategySelector = 0.
// 16/07: erano "bool"/"double"/"int" semplici (mai esposti al Tester nonostante
// il commento sopra lo descrivesse gia' da v2.1.1) - resi "input" su richiesta
// esplicita di non far contendere alle strategie gli slot/il margine: questo
// percorso (NXS_SafeBuy/NXS_SafeSell diretti) salta InpMaxConcurrent,
// InpMaxPerDirTF, InpUseMarginGate/InpMinMarginLevelPct, InpMaxDirExposureLots
// e InpMaxTotalLotMult - resta solo NXS_PreFlight (spread/margine/stop) e il
// tetto di sicurezza InpDataCollectionMaxOpen sotto. Default invariati (OFF).
input bool     InpDataCollectionMode   = false;  // OFF: si usa il grouping istituzionale (raccolta dati solo su demo)
input double   InpDataCollectionLot    = 0.01;   // lotto fisso per trade (piccolo)
input int      InpDataCollectionMaxOpen= 40;     // tetto posizioni aperte contemporanee (sicurezza)

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
bool     InpUseStreakSizing       = false;  // v2.4.0: OFF -> sizing prevedibile come nel backtest
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
// v2.5.x — erano variabili semplici, non `input`: MetaTrader non le espone
// nei file .set ne' nel tester a riga di comando, quindi restavano sempre al
// default hardcoded qui sotto qualunque cosa dicesse un preset. Nessun test
// esterno le ha mai potute davvero pilotare finora (vedi TODO desktop punto 3
// per l'isolamento di LIQ_VOID, che dipende proprio da questo flag).
input bool     InpUseHTFBias       = false;   // OFF by default — gate must IMPROVE not BLOCK
input int      InpHTF_EMAPeriod    = 50;
input double   InpHTF_MinConf      = 0.55;
input bool     InpHTF_AllowReversal= true;

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

input group "=== STRATEGIES TOGGLE ==="
// 16/07: erano "bool" semplici - mai esposti al Tester nonostante fossero
// l'unico modo (oltre a InpStrategySelector, che isola UNA sola strategia)
// per testare COMBINAZIONI scelte a mano (es. nucleo hedge BREAKOUT_ACC+
// CISD+TURTLE_SOUP) senza ricompilare. Resi "input", default invariati
// (tutte true = comportamento normale identico finche' non le tocchi).
input bool     InpStrat_ADX_RSI      = true;
input bool     InpStrat_BOLLINGER    = true;
input bool     InpStrat_MACD         = true;
input bool     InpStrat_SAR          = true;
input bool     InpStrat_TSI          = true;
// 17/07 notte - audit esterno: la vecchia "TSI" non calcolava il True
// Strength Index (era RSI+EMA20), solo il nome coincideva. Periodi veri di
// Blau: long=25 (primo smoothing), short=13 (secondo smoothing), signal=7.
int InpTSI_LongPeriod   = 25;
int InpTSI_ShortPeriod  = 13;
int InpTSI_SignalPeriod = 7;
// 25/08 - disattivata: riverificata sulla ricetta live esatta (4h,
// SL1.5/TP3.0, no HTF), PF 0.61-0.67 su tutto lo storico Dukascopy
// con QUALUNQUE larghezza di trailing provata - in perdita, non un
// problema di uscita. Coerente con la diagnosi indipendente di luglio
// (-8.6R reali, 5/6 anni negativi). Vedi
// server/research_scripts/live_recipe_trailing_verify_25-08.py.
input bool     InpStrat_BJORGUM      = false;
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
bool     InpUseSMCReactionGate = true;    // v2.4.2: FVG/OB entrano solo con conferma reazione (structure+react engine)

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
// 17/07 - erano tutti plain (non `input`) nonostante il commento "input
// group": ogni riga di un .set file per questo gruppo era gia' inerte,
// stesso tipo di bug trovato oggi su altrove (i 37 toggle strategia,
// InpStrategySelector, InpDataCollectionMode). Verificato: nessuna di
// queste viene mai riassegnata a runtime nel codice, sicuro renderle
// input. InpMaxHoldHours in particolare e' il fallback 4h coinvolto
// nell'indagine di oggi sul cap di durata massima.
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

// input group "=== ANTI-BLEED (P2) ==="
bool     InpUseAntiBleed     = false;    // v2.4.0: OFF -> niente taglio lotto in DD, size = rischio profilo
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
// AUD0-SEC-001: il default era "NEXUS_BRIDGE_TOKEN_2026", identico in ogni
// copia del progetto e presente nella documentazione pubblica. Ora e' vuoto:
// senza un token dedicato NXS_WebCredentialPreflight() spegne la WebSync.
input string   InpWebToken         = "";                               // token bridge dedicato (obbligatorio, >=24 caratteri)
int      InpPushIntervalSec  = 5;
int      InpPollIntervalSec  = 3;
int      InpHistSyncIntervalSec = 1800;                                  // backfill periodico trade chiusi (sec) — safety net oltre OnInit

// input group "=== LOGGING ==="
input bool     InpLogTrades        = true;
input bool     InpDebugLog         = false;
// 17/07 sera - NEXUS_trades.csv non veniva mai svuotato (append infinito da
// ogni sweep), fino a 24.8MB+ e sospettato di rallentare i passaggi Tester
// piu' recenti. Opt-in esplicito, non automatico: va attivato a mano per UNA
// run quando si e' deciso che i dati fin qui raccolti sono stati letti/usati
// e si puo' ripartire puliti. Di default false per non perdere dati per
// errore. Il vecchio file viene archiviato (rinominato con timestamp), mai
// cancellato silenziosamente.
input bool     InpResetTradesLogOnInit = false;

//================================================================
//  NEXUS v2.0 / Phase 3-5 additions (additive — defaults preserve v1 behaviour)
//================================================================
// input group "=== RISK PROTECTIONS (v2.0) ==="
// 17/07 - stesso bug del gruppo BREAK EVEN & TRAIL sopra: tutti plain,
// ogni riga di un .set file per questo gruppo era gia' inerte. Questo e'
// il gruppo che contiene InpUseMaxHold/InpProt_MaxHoldHours, al centro
// dell'indagine di oggi sul cap di durata massima da 12h - prima di
// questo fix, anche volendo, non era possibile testare un valore diverso
// via .set. Verificato: nessuna riassegnazione a runtime nel codice.
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
// AUD0-PROT-007: oltre questo multiplo del limite di perdita, la chiusura NON
// attende il tempo minimo di vita. Il grace period serve contro il rumore, non
// per lasciar correre una perdita che ha gia' superato il limite duro.
input double   InpProt_HardLossFactor = 1.5;  // moltiplicatore del limite oltre cui si chiude subito
input bool     InpUseAutoClose     = true;   // Flatten before market close
input int      InpAutoCloseMin     = 15;
// AUD0-PROT-008: usato solo come RIPIEGO quando il broker non espone le
// sessioni di trading del simbolo. La chiusura reale viene da
// SymbolInfoSessionTrade().
input int      InpMarketCloseGMT   = 21;     // ripiego se il broker non espone sessioni

// AUD0-PROT-009 / AUD0-RISK-004: nel Strategy Tester le protezioni di conto
// (pausa giornaliera, ESL, DPT, AutoClose) venivano disattivate in blocco.
// I backtest misuravano quindi un sistema DIVERSO da quello che gira in
// reale, e le curve prodotte non erano confrontabili con il live.
//
// Con parita' attiva (default) il tester applica le stesse regole del live,
// in modo deterministico. Impostare false SOLO per riprodurre risultati
// storici prodotti prima di questa correzione: i numeri ottenuti in quel
// modo non sono rappresentativi del comportamento reale.
input bool     InpTesterProtectionParity = true;  // tester: stesse protezioni del live

// AUD0-STATE-008: la persistenza dello stato era disattivata in blocco nel
// tester, quindi il comportamento di riavvio/ripresa — inclusa la garanzia
// "una sola gestione per posizione" e il recupero dopo un crash — non era
// verificabile da nessuna parte. Attivandolo, lo snapshot usa un nome
// dedicato al tester e non tocca mai i file del conto reale.
input bool     InpStatePersistInTester = false;  // tester: abilita snapshot (file separato)

// AUD0-PROT-001 / AUD0-RISK-006: ESL, DPT e scudo di ruin ricavano le soglie
// dall'equity del CONTO ma chiudevano solo il simbolo del grafico. Con questo
// attivo il perimetro segue la soglia. Disattivalo solo se piu' istanze si
// dividono deliberatamente lo stesso conto per simbolo.
input bool     InpProtScopeAccountWide = true;  // protezioni di conto: chiudi tutte le posizioni NEXUS

// NXS-EXEC-001: in modalita' Virtual SL EXECUTE il broker riceve uno stop piu'
// largo di quello logico. Se l'EA e' offline la perdita reale e' quella dello
// stop del broker: questo e' il moltiplicatore massimo del budget di rischio
// che si accetta come caso peggiore. Oltre, l'ordine non parte.
input double   InpVSL_MaxOfflineRiskMult = 2.0;  // tetto del rischio offline (x budget)

// NEXUS-ARCH-003: ambiente dichiarato di questa istanza. L'EA rifiuta i comandi
// provenienti da un ambiente diverso: un backend condiviso non deve poter far
// eseguire a un'istanza LIVE un comando pensato per una DEMO. Vuoto = nessun
// controllo (solo per installazioni a ambiente unico).
input string   InpEnvironment      = "";     // DEVELOPMENT|SIMULATION|DEMO|PAPER|LIVE

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
// 25/08 - disattivata: prima ricerca DA ZERO (non porting) sul vero
// segnale live (sweep PDH/PDL/EQH/EQL + candela di rientro forte, stop
// nativo, RR2.0 fisso - completamente diverso dal pattern Python
// "TURTLE_SOUP" usato nel resto della sessione, che condivide solo il
// nome). Testato su H1(live)/4h/30m, simmetrica e BUY/SELL-only:
// **mai profittevole in modo robusto** (max PF0.94 su 4h BUY-only,
// 3/5 finestre) - non un problema di timeframe o direzione, il pattern
// stesso non ha edge su XAUUSD. Vedi
// server/research_scripts/turtle_soup_live_signal_25-08.py.
input bool     InpStrat_TurtleSoup     = false;
input bool     InpStrat_IFVG           = true;
input bool     InpStrat_FVG_Mit        = true;
// 13/08 - variante a registro (15 barre) della strategia sopra, vedi
// NXS_Strat_FVG_Mitigation_Window() in NXS_Strategies_SMC.mqh e vault
// "NEXUS EA - Incidente Sicurezza e Setup Desktop (13-08)".
input bool     InpStrat_FVG_MIT_WINDOW = true;
input bool     InpStrat_OB_Mit         = true;
input bool     InpStrat_SH_BMS_RTO     = true;
// 14/08 - state machine indipendente (regole diverse, non un refactor della
// v1 sopra), vedi NXS_Strat_SH_BMS_RTO_V2 in NXS_Strategies_SMC.mqh.
input bool     InpStrat_SH_BMS_RTO_V2  = true;
input bool     InpStrat_SMS_BMS_RTO    = true;
input bool     InpStrat_SilverBullet   = true;
input bool     InpStrat_AMD_Reversal   = true;
input bool     InpStrat_OTE_Cont       = true;
input bool     InpStrat_MalaysianSNR   = true;
// 24/08 - vedi NXS_Strat_SwingFalseBreak in NXS_Strategies_SMC.mqh e vault
// "NEXUS EA - Idee da Script TradingView Esterni (17-08)", addendum 24/08.
input bool     InpStrat_SwingFalseBreak = true;
// 24/08 - vedi NXS_Strat_ZScoreBreakout in NXS_Strategies.mqh, validata
// 17/08 su H1 (retail PF1.29 4/5, ECN PF1.71 5/5, 557 trade).
input bool     InpStrat_ZScoreBreakout  = true;

// input group "=== INSTITUTIONAL MODELS (v2.0.7) ==="
// 25/08 - disattivata (THREE_BAR_DELIVERY_BREAK, stratName di questa
// strategia): riverificata sulla ricetta live esatta (4h, SL1.5/TP3.0,
// HTF), PF 0.51-0.65 con qualunque larghezza di trailing - in perdita
// su tutto lo storico. Vedi live_recipe_trailing_verify_25-08.py.
input bool     InpUseStrat_CISD          = false;
// 25/08 - disattivata (AMD_CONT): ricerca da zero sul vero segnale live
// (fase AMD_CONTINUATION_DISTRIBUTION su M15 InpTFEntry + retest nativo
// su EffTF M30), mai in profitto ne' su M30/M15/H1 ne' su BUY/SELL-only
// (PF 0.53-0.71, max 1/5 finestre positive). Vedi
// amd_cont_ldn_reversal_live_signal_25-08.py e _tf_scan_25-08.py.
input bool     InpUseStrat_AMD_Cont      = false;
input bool     InpUseStrat_Judas         = true;
// 25/08 - disattivata (LDN_REVERSAL): stesso trattamento, segnale
// nativo (sweep AsiaHi/PDH/EQH + CHOCH) mai in profitto su M15/M30/H1
// ne' su BUY/SELL-only (PF 0.36-0.78, max 1/5 finestre positive). Vedi
// amd_cont_ldn_reversal_live_signal_25-08.py e _tf_scan_25-08.py.
input bool     InpUseStrat_LdnReversal   = false;
input bool     InpUseStrat_NYReversal    = true;
input bool     InpUseStrat_WeeklyExp     = true;
input bool     InpUseStrat_PO3           = true;
input bool     InpUseStrat_LiqVoid       = true;
input bool     InpUseStrat_DispRebal     = true;
// 11/08 - CRT (Candle Range Theory): promettente all'inizio (walk-forward
// 5/5 su 3 timeframe) ma la riverifica costi del 24/08 l'ha confermata
// definitivamente rotta (saga costi-dominanti mai risolta) - esclusa dal
// registro canonico generato (contracts/generate_registry.py). Il
// generatore di segnale in NXS_Strategies_SMC.mqh, NXS_Strat_CRT(), resta
// nel codice ma senza una voce nel registro ogni segnale viene bloccato a
// valle da NXS_Contract ("strategy_id sconosciuto 'CRT'") - innocuo ma
// rumoroso nei log a ogni barra. 25/08: disattivata di default per non
// generare segnali morti in partenza; lasciata come input per chi vuole
// riabilitarla manualmente per un test isolato.
input bool     InpUseStrat_CRT           = false;
// 12/08 — floor minimo sulla distanza dello stop di CRT (in multipli di ATR
// del TF di CRT). Lo stop e' ancorato al wick della candela di sweep, non a
// un multiplo ATR fisso - quando il wick e' minimo il rischio flottante puo'
// esplodere prima che il trade chiuda (107% osservato in una finestra, vedi
// vault "Fase C Recovery Baseline e Rischio Flottante"). 0 = disattivo
// (comportamento originale, mai un floor). Vedi NXS_Strat_CRT().
input double   InpCRT_MinStopATR         = 0.3;

// input group "=== TIMEFRAME-AWARE SL/TP + LIFE (v2.0.21) ==="
double   InpTF_SLTP_H1   = 2.0;    // moltiplicatore SL/TP per segnali origine H1 (× ATR chart)
double   InpTF_SLTP_H4   = 3.5;    // idem H4
double   InpTF_SLTP_D1   = 5.0;    // idem D1
double   InpTF_Life_H1   = 8.0;    // moltiplicatore MinLife/MaxHold per origine H1
double   InpTF_Life_H4   = 20.0;   // idem H4
double   InpTF_Life_D1   = 60.0;   // idem D1

// input group "=== ELLIOTT WAVE (v2.0.20) ==="
input bool     InpUseStrat_Elliott       = false;    // OFF di default: nuova strategia, backtesta prima
int      InpEllSwingWing           = 3;        // ampiezza fractal per i pivot di swing
double   InpEllRetraceMin          = 0.382;    // retracement min onda 2 (Fib)
double   InpEllRetraceMax          = 0.786;    // retracement max onda 2 (Fib)
double   InpEllMinScore            = 70.0;     // score base dei setup Elliott

// input group "=== RANGE / COUNTER-HTF (v2.0.8) ==="
input bool     InpUseStrat_RangeFade     = true;     // mean-revert sui range stretti
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
