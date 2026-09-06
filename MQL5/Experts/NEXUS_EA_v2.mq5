//+------------------------------------------------------------------+
//|                                                NEXUS_EA_v2.mq5   |
//|                          Italian Traders Club - NEXUS EA v2.0    |
//|                  Commercial-grade Multi-Symbol EA for MT5         |
//+------------------------------------------------------------------+
#property copyright "Italian Traders Club"
#property link      "https://nexus.local"
#property version   "3.60"
#property strict
#property description "NEXUS EA v2.0 - Commercial-grade adaptive multi-strategy EA"
#property description "Multi-symbol | License-gated | Confluence scoring | Risk Protections"

//+------------------------------------------------------------------+
//| NO dependency on <Trade\Trade.mqh> / <Object.mqh> / <Arrays\*>.   |
//| The EA uses only native MQL5 functions. All trade ops live in    |
//| NXS_Globals.mqh as raw helpers (NXS_DoBuy / NXS_DoSell / ...).   |
//| Compiles on every MT5 build, even when standard library missing. |
//+------------------------------------------------------------------+

#include <NEXUS_v1\NXS_Defines.mqh>
#include <NEXUS_v1\NXS_Inputs.mqh>
#include <NEXUS_v1\NXS_StrategyProfiles.mqh>
#include <NEXUS_v1\NXS_Globals.mqh>
// AUD0-PROT-005 / AUD0-HSYNC-003: coda locale durevole per le consegne HTTP
// fallite. Deve stare PRIMA di ogni modulo che spinge eventi al backend
// (protezioni, history sync, ledger), che vi accodano invece di ritentare
// in linea con Sleep().
#include <NEXUS_v1\NXS_Outbox.mqh>
// AUD0-LEDGER-004/006/010, NXS-TX-002: registro dell'intento di esecuzione.
// Deve precedere sia i moduli che aprono posizioni sia il ledger che ne
// ricostruisce identita' e rischio.
#include <NEXUS_v1\NXS_Intent.mqh>
#include <NEXUS_v1\NXS_StrategyRegistry.mqh>
#include <NEXUS_v1\NXS_RuntimeSettings.mqh>
#include <NEXUS_v1\NXS_Presets.mqh>
#include <NEXUS_v1\NXS_SymbolProfile.mqh>
#include <NEXUS_v1\NXS_StreakRisk.mqh>
#include <NEXUS_v1\NXS_Risk.mqh>
#include <NEXUS_v1\NXS_Slippage.mqh>
#include <NEXUS_v1\NXS_SafeOrder.mqh>
#include <NEXUS_v1\NXS_State.mqh>
#include <NEXUS_v1\NXS_License.mqh>
#include <NEXUS_v1\NXS_Sessions.mqh>
#include <NEXUS_v1\NXS_NewsFilter.mqh>
#include <NEXUS_v1\NXS_HTFBias.mqh>
#include <NEXUS_v1\NXS_Velocity.mqh>
#include <NEXUS_v1\NXS_AMDModel.mqh>
#include <NEXUS_v1\NXS_Pressure.mqh>
#include <NEXUS_v1\NXS_MarketAnalysis.mqh>
#include <NEXUS_v1\NXS_Structure.mqh>
#include <NEXUS_v1\NXS_StructureMultiLayer.mqh>
#include <NEXUS_v1\NXS_Reaction.mqh>
#include <NEXUS_v1\NXS_MarketContext.mqh>
#include <NEXUS_v1\NXS_FibonacciContext.mqh>
#include <NEXUS_v1\NXS_Strategies.mqh>
#include <NEXUS_v1\NXS_BlockerDiagnostics.mqh>
#include <NEXUS_v1\NXS_ElliottFilter.mqh>
#include <NEXUS_v1\NXS_Strategies_SMC.mqh>
#include <NEXUS_v1\NXS_Strategies_Institutional.mqh>
#include <NEXUS_v1\NXS_Strategies_Elliott.mqh>
#include <NEXUS_v1\NXS_InstitutionalCore.mqh>
#include <NEXUS_v1\NXS_SignalQuality.mqh>
#include <NEXUS_v1\NXS_ShadowTrading.mqh>
#include <NEXUS_v1\NXS_EntryScore.mqh>
#include <NEXUS_v1\NXS_RiskShield.mqh>
#include <NEXUS_v1\NXS_Execution.mqh>
#include <NEXUS_v1\NXS_SignalRouter.mqh>
// v2.0.9 — Performance roadmap (Sprint 1+2+3): all auto-active.
#include <NEXUS_v1\NXS_Performance.mqh>
#include <NEXUS_v1\NXS_EdgeAdaptive.mqh>
#include <NEXUS_v1\NXS_PositionCoordinator.mqh>
#include <NEXUS_v1\NXS_Management.mqh>
#include <NEXUS_v1\NXS_GridRecovery.mqh>
#include <NEXUS_v1\NXS_Pyramiding.mqh>
#include <NEXUS_v1\NXS_SplitTrade.mqh>
#include <NEXUS_v1\NXS_PipSequence.mqh>
#include <NEXUS_v1\NXS_SLReclaim.mqh>
#include <NEXUS_v1\NXS_ProfitReclaim.mqh>
#include <NEXUS_v1\NXS_InstManage.mqh>
#include <NEXUS_v1\NXS_Confluence.mqh>
#include <NEXUS_v1\NXS_MTFSpreadVol.mqh>
#include <NEXUS_v1\NXS_Protections.mqh>
#include <NEXUS_v1\NXS_TrailingATR.mqh>
#include <NEXUS_v1\NXS_WeeklyExpManage.mqh>
#include <NEXUS_v1\NXS_Notify.mqh>
#include <NEXUS_v1\NXS_Dashboard.mqh>
#include <NEXUS_v1\NXS_HistorySync.mqh>
#include <NEXUS_v1\NXS_TradeLedger.mqh>   // PR1 - ciclo di vita trade (deal/order/position/logico)
#include <NEXUS_v1\NXS_Diagnostics.mqh>
#include <NEXUS_v1\NXS_StratStats.mqh>
#include <NEXUS_v1\NXS_WebBridge.mqh>
#include <NEXUS_v1\NXS_VisualBridge.mqh>
#include <NEXUS_v1\NXS_VisualBridgeHTTP.mqh>
#include <NEXUS_v1\NXS_LockedProfile.mqh>
#include <NEXUS_v1\NXS_StrategyChain.mqh>
#include <NEXUS_v1\NXS_Logging.mqh>

//+------------------------------------------------------------------+
//| Indicator handle helpers                                          |
//+------------------------------------------------------------------+
bool NXS_CreateHandles(){
   g_hADX   = iADX(g_sym, InpTFEntry, InpADX_Period);
   g_hRSI   = iRSI(g_sym, InpTFEntry, InpRSI_Period, PRICE_CLOSE);
   g_hBB    = iBands(g_sym, InpTFEntry, InpBB_Period, 0, InpBB_Dev, PRICE_CLOSE);
   g_hMACD  = iMACD(g_sym, InpTFEntry, InpMACD_Fast, InpMACD_Slow, InpMACD_Signal, PRICE_CLOSE);
   g_hSAR   = iSAR(g_sym, InpTFEntry, InpSAR_Step, InpSAR_Max);
   g_hATR   = iATR(g_sym, InpTFEntry, InpATR_Period);
   g_hEMA200= iMA(g_sym, InpTFEntry, InpEMA200_Period, 0, MODE_EMA, PRICE_CLOSE);
   g_hEMA9  = iMA(g_sym, InpTFEntry, InpEMA9_Period,   0, MODE_EMA, PRICE_CLOSE);
   g_hEMA21 = iMA(g_sym, InpTFEntry, InpEMA21_Period,  0, MODE_EMA, PRICE_CLOSE);
   g_hEMA_HTF = iMA(g_sym, InpTFHigh,   InpHTF_EMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_hEMA_MTF = iMA(g_sym, InpTFMedium, InpHTF_EMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
   g_hICHI    = iIchimoku(g_sym, InpTFEntry, 9, 26, 52);

   if(g_hADX == INVALID_HANDLE || g_hRSI == INVALID_HANDLE || g_hBB == INVALID_HANDLE
      || g_hMACD == INVALID_HANDLE || g_hSAR == INVALID_HANDLE || g_hATR == INVALID_HANDLE
      || g_hEMA200 == INVALID_HANDLE || g_hEMA9 == INVALID_HANDLE || g_hEMA21 == INVALID_HANDLE
      || g_hEMA_HTF == INVALID_HANDLE || g_hEMA_MTF == INVALID_HANDLE || g_hICHI == INVALID_HANDLE){
      Print("[NEXUS] Indicator handle creation failed.");
      return false;
   }
   return true;
}

// v2.3.0 — handle "originali" del TF di ingresso, catturati per poterli
// RIPRISTINARE dopo un passaggio multi-TF (evita leak/double-release).
int g_orig_hADX, g_orig_hRSI, g_orig_hBB, g_orig_hMACD, g_orig_hSAR, g_orig_hATR,
    g_orig_hEMA200, g_orig_hEMA9, g_orig_hEMA21, g_orig_hICHI;
bool g_origCaptured = false;

void NXS_CaptureOriginalHandles(){
   g_orig_hADX=g_hADX; g_orig_hRSI=g_hRSI; g_orig_hBB=g_hBB; g_orig_hMACD=g_hMACD;
   g_orig_hSAR=g_hSAR; g_orig_hATR=g_hATR; g_orig_hEMA200=g_hEMA200;
   g_orig_hEMA9=g_hEMA9; g_orig_hEMA21=g_hEMA21; g_orig_hICHI=g_hICHI;
   g_origCaptured = true;
}

void NXS_ReleaseHandles(){
   // Rilascia SEMPRE gli originali (non i puntatori correnti, che in multi-TF
   // possono puntare alla cache -> li rilascia NXS_MTF_Release).
   int hs[] = { g_origCaptured?g_orig_hADX:g_hADX, g_origCaptured?g_orig_hRSI:g_hRSI,
                g_origCaptured?g_orig_hBB:g_hBB, g_origCaptured?g_orig_hMACD:g_hMACD,
                g_origCaptured?g_orig_hSAR:g_hSAR, g_origCaptured?g_orig_hATR:g_hATR,
                g_origCaptured?g_orig_hEMA200:g_hEMA200, g_origCaptured?g_orig_hEMA9:g_hEMA9,
                g_origCaptured?g_orig_hEMA21:g_hEMA21, g_hEMA_HTF, g_hEMA_MTF,
                g_origCaptured?g_orig_hICHI:g_hICHI };
   for(int i = 0; i < ArraySize(hs); i++)
      if(hs[i] != INVALID_HANDLE) IndicatorRelease(hs[i]);
}

// ---------------------------------------------------------------------------
// v2.3.0 — SINGLE-CHART MULTI-TIMEFRAME
// Cache di handle per TF (D1/H4/H1...): una sola istanza puo' calcolare ogni
// strategia sul SUO timeframe ripuntando i g_h* alla cache e rifacendo
// NXS_UpdateIndicators(). Le funzioni-strategia (che leggono i VALORI globali
// g_adx/g_atr/g_ema200...) non vengono toccate.
// ---------------------------------------------------------------------------
// 30/08 - BUG TROVATO durante l'esperimento "spoglia MT5" (richiesto
// dall'utente): con 4 slot, il registro strategie usa GIA' 5 timeframe
// distinti (D1/H4/M30/M15/H1 - verificato contando NXS_Profile_TF su
// tutte le voci di NXS_StrategyProfiles.mqh). NXS_MTF_Index() ritorna -1
// silenziosamente quando g_mtfCount raggiunge il cap, quindi
// NXS_ActivateTF() fallisce per QUALUNQUE timeframe scoperto per 5°
// (l'ordine dipende dall'ordine di scansione del registro) - le
// strategie su quel timeframe non vengono MAI valutate, senza errori
// visibili (solo uno "skip" silenzioso, vedi NXS_CollectAllSignals).
// Verificato dal vivo su SAR (H4): passes[]=[H1,D1,M30,M15,H4], H4 5°
// della lista, ActivateTF fallisce sempre, SAR non apre mai un trade.
// Alzato a 8 con margine per eventuali nuove strategie/timeframe futuri.
#define NXS_MTF_MAX 8
ENUM_TIMEFRAMES g_mtfTF[NXS_MTF_MAX];
int g_mtf_hADX[NXS_MTF_MAX], g_mtf_hRSI[NXS_MTF_MAX], g_mtf_hBB[NXS_MTF_MAX],
    g_mtf_hMACD[NXS_MTF_MAX], g_mtf_hSAR[NXS_MTF_MAX], g_mtf_hATR[NXS_MTF_MAX],
    g_mtf_hEMA200[NXS_MTF_MAX], g_mtf_hEMA9[NXS_MTF_MAX], g_mtf_hEMA21[NXS_MTF_MAX],
    g_mtf_hICHI[NXS_MTF_MAX];
int g_mtfCount = 0;   // g_activeTF e NXS_EffTF() ora in NXS_Globals.mqh

int NXS_MTF_Index(ENUM_TIMEFRAMES tf){
   for(int i = 0; i < g_mtfCount; i++) if(g_mtfTF[i] == tf) return i;
   if(g_mtfCount >= NXS_MTF_MAX) return -1;
   int i = g_mtfCount;
   g_mtf_hADX[i]   = iADX(g_sym, tf, InpADX_Period);
   g_mtf_hRSI[i]   = iRSI(g_sym, tf, InpRSI_Period, PRICE_CLOSE);
   g_mtf_hBB[i]    = iBands(g_sym, tf, InpBB_Period, 0, InpBB_Dev, PRICE_CLOSE);
   g_mtf_hMACD[i]  = iMACD(g_sym, tf, InpMACD_Fast, InpMACD_Slow, InpMACD_Signal, PRICE_CLOSE);
   g_mtf_hSAR[i]   = iSAR(g_sym, tf, InpSAR_Step, InpSAR_Max);
   g_mtf_hATR[i]   = iATR(g_sym, tf, InpATR_Period);
   g_mtf_hEMA200[i]= iMA(g_sym, tf, InpEMA200_Period, 0, MODE_EMA, PRICE_CLOSE);
   g_mtf_hEMA9[i]  = iMA(g_sym, tf, InpEMA9_Period, 0, MODE_EMA, PRICE_CLOSE);
   g_mtf_hEMA21[i] = iMA(g_sym, tf, InpEMA21_Period, 0, MODE_EMA, PRICE_CLOSE);
   g_mtf_hICHI[i]  = iIchimoku(g_sym, tf, 9, 26, 52);
   if(g_mtf_hADX[i]==INVALID_HANDLE || g_mtf_hRSI[i]==INVALID_HANDLE ||
      g_mtf_hBB[i]==INVALID_HANDLE  || g_mtf_hMACD[i]==INVALID_HANDLE ||
      g_mtf_hSAR[i]==INVALID_HANDLE || g_mtf_hATR[i]==INVALID_HANDLE ||
      g_mtf_hEMA200[i]==INVALID_HANDLE || g_mtf_hEMA9[i]==INVALID_HANDLE ||
      g_mtf_hEMA21[i]==INVALID_HANDLE || g_mtf_hICHI[i]==INVALID_HANDLE)
      return -1;
   g_mtfTF[i] = tf; g_mtfCount++;
   return i;
}

// Punta i g_h* alla cache del TF e ricalcola i valori. false se non pronto.
bool NXS_ActivateTF(ENUM_TIMEFRAMES tf){
   int i = NXS_MTF_Index(tf);
   if(i < 0) return false;
   g_hADX=g_mtf_hADX[i]; g_hRSI=g_mtf_hRSI[i]; g_hBB=g_mtf_hBB[i]; g_hMACD=g_mtf_hMACD[i];
   g_hSAR=g_mtf_hSAR[i]; g_hATR=g_mtf_hATR[i]; g_hEMA200=g_mtf_hEMA200[i];
   g_hEMA9=g_mtf_hEMA9[i]; g_hEMA21=g_mtf_hEMA21[i]; g_hICHI=g_mtf_hICHI[i];
   g_activeTF = tf;
   return NXS_UpdateIndicators();
}

// Ripristina gli handle del TF di ingresso e ricalcola i valori.
void NXS_ActivateOriginal(){
   if(!g_origCaptured) return;
   g_hADX=g_orig_hADX; g_hRSI=g_orig_hRSI; g_hBB=g_orig_hBB; g_hMACD=g_orig_hMACD;
   g_hSAR=g_orig_hSAR; g_hATR=g_orig_hATR; g_hEMA200=g_orig_hEMA200;
   g_hEMA9=g_orig_hEMA9; g_hEMA21=g_orig_hEMA21; g_hICHI=g_orig_hICHI;
   g_activeTF = InpTFEntry;
   NXS_UpdateIndicators();
}

void NXS_MTF_Release(){
   for(int i = 0; i < g_mtfCount; i++){
      int hs[] = { g_mtf_hADX[i],g_mtf_hRSI[i],g_mtf_hBB[i],g_mtf_hMACD[i],g_mtf_hSAR[i],
                   g_mtf_hATR[i],g_mtf_hEMA200[i],g_mtf_hEMA9[i],g_mtf_hEMA21[i],g_mtf_hICHI[i] };
      for(int j = 0; j < ArraySize(hs); j++)
         if(hs[j] != INVALID_HANDLE) IndicatorRelease(hs[j]);
   }
   g_mtfCount = 0;
}

// v2.3.1 — "UNA posizione per strategia alla volta" (come il motore del sito,
// che tiene pos=None finche' non chiude). Evita lo stacking di entrate correlate
// che gonfia i trade e il drawdown. Legge il nome strategia dal comment (campo [1]).
bool NXS_StrategyHasOpenPos(const string name){
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      string cmt = PositionGetString(POSITION_COMMENT);
      string pp[]; int npp = StringSplit(cmt, '|', pp);
      if(npp >= 2 && pp[1] == name) return true;
   }
   return false;
}

// v2.3.1 — "UNA decisione per barra del TF della strategia" (come il sito, che
// valuta ogni strategia una volta per barra). Senza, una strategia D1 viene
// rivalutata a OGNI barra M15 e produce lo stesso segnale ~96 volte/giorno,
// inondando gli slot (caso TSI: 555 "setup" in 2 settimane).
// AUD0-MQL-004: la capacita' era il numero magico 48 (e 64 nel percorso
// multi-TF), scollegato dal numero reale di strategie. Aggiungendone abbastanza
// il troncamento sarebbe avvenuto in SILENZIO: alcune strategie semplicemente
// non sarebbero piu' state valutate, senza alcun errore.
//
// La capacita' deriva ora dal registro canonico generato, con margine per le
// varianti (_NXR) e per i segnali multipli della stessa strategia.
#define NXS_MAX_SIGNALS (NXS_LIVE_STRATEGY_COUNT * 2 + 16)

string   g_tfbarName[NXS_MAX_SIGNALS];
datetime g_tfbarTime[NXS_MAX_SIGNALS];
int      g_tfbarN = 0;
bool     g_signalOverflowReported = false;
datetime NXS_GetLastTfBar(const string name){
   for(int i = 0; i < g_tfbarN; i++) if(g_tfbarName[i] == name) return g_tfbarTime[i];
   return 0;
}
void NXS_SetLastTfBar(const string name, datetime t){
   for(int i = 0; i < g_tfbarN; i++){ if(g_tfbarName[i] == name){ g_tfbarTime[i] = t; return; } }
   if(g_tfbarN < NXS_MAX_SIGNALS){
      g_tfbarName[g_tfbarN] = name; g_tfbarTime[g_tfbarN] = t; g_tfbarN++;
   } else if(!g_signalOverflowReported){
      g_signalOverflowReported = true;
      PrintFormat("[NEXUS][ALERT] tabella barre-per-TF piena (%d): la regola "
                  "'una decisione per barra' non e' piu' applicata a '%s' e alle "
                  "strategie successive", NXS_MAX_SIGNALS, name);
   }
}

// AUD0-MQL-010 — un fallimento di CopyBuffer faceva uscire la funzione con
// `false` e OnTick tornava indietro in silenzio. L'EA poteva restare CIECO per
// ore — nessuna decisione, nessun errore, nessuna traccia — e l'unico sintomo
// era l'assenza di operazioni.
//
// Ora il fallimento e' contato, segnalato a cadenza limitata, e oltre una
// soglia gli handle vengono ricreati; lo stato degradato e' esposto a chi
// decide se e' sicuro aprire nuova esposizione.
// Lo STATO (g_indFailStreak / g_indDegraded / NXS_IndicatorsDegraded) vive in
// NXS_Globals.mqh: la telemetria lo pubblica e NXS_WebBridge.mqh e' incluso
// prima di questo file. Qui resta la LOGICA, che deve poter chiamare
// NXS_ReleaseHandles/NXS_CreateHandles definite nell'EA.
#define NXS_IND_FAIL_ALERT     5     // fallimenti consecutivi prima dell'allarme
#define NXS_IND_FAIL_RECREATE 20     // fallimenti consecutivi prima di ricreare
#define NXS_IND_LOG_EVERY_SEC 60

void _NXS_IndicatorFailure(string which){
   g_indFailStreak++;
   if(g_indFailStreak >= NXS_IND_FAIL_ALERT){
      g_indDegraded = true;
      if(TimeCurrent() - g_indLastFailLog >= NXS_IND_LOG_EVERY_SEC){
         g_indLastFailLog = TimeCurrent();
         PrintFormat("[NEXUS][ALERT] lettura indicatori fallita %d volte di fila "
                     "(ultimo: %s, err=%d): l'EA non sta prendendo decisioni",
                     g_indFailStreak, which, GetLastError());
      }
   }
   if(g_indFailStreak == NXS_IND_FAIL_RECREATE){
      Print("[NEXUS] ricreazione degli handle indicatore dopo fallimenti persistenti");
      NXS_ReleaseHandles();
      NXS_CreateHandles();
   }
}

void _NXS_IndicatorSuccess(){
   if(g_indFailStreak > 0)
      PrintFormat("[NEXUS] lettura indicatori ripristinata dopo %d fallimenti",
                  g_indFailStreak);
   g_indFailStreak = 0;
   g_indDegraded   = false;
}

// AUD0-MQL-009 — LETTURE INDICATORE SEQUENZIALI.
//
// La funzione esegue ~20 CopyBuffer separati, chiamati a ogni tick e di nuovo a
// ogni attivazione di timeframe nel percorso multi-TF. Il costo non e' nel
// singolo CopyBuffer ma nel loro NUMERO moltiplicato per la frequenza.
//
// Le letture riguardano tutte la BARRA CHIUSA (shift 1), che per definizione
// non cambia finche' non si forma una barra nuova: rileggerle a ogni tick
// produce esattamente gli stessi valori. Qui si aggiunge una cache per barra e
// per timeframe attivo; la rilettura avviene solo quando la barra cambia,
// oppure quando l'ultimo tentativo era fallito (per non restare bloccati su
// valori vecchi durante un degrado).
datetime g_indCachedBar = 0;
ENUM_TIMEFRAMES g_indCachedTF = PERIOD_CURRENT;

bool NXS_UpdateIndicators(){
   ENUM_TIMEFRAMES etf = NXS_EffTF();
   datetime curBar = iTime(g_sym, etf, 0);
   if(curBar > 0 && curBar == g_indCachedBar && etf == g_indCachedTF &&
      g_indFailStreak == 0)
      return true;   // stessa barra, stesso TF, ultima lettura riuscita

   double a[]; ArraySetAsSeries(a, true);
   if(CopyBuffer(g_hADX, 0, 1, 1, a) <= 0){ _NXS_IndicatorFailure("ADX"); return false; }
   g_adx = a[0];
   if(CopyBuffer(g_hADX, 1, 1, 1, a) <= 0){ _NXS_IndicatorFailure("ADX"); return false; } g_adxPlus = a[0];
   if(CopyBuffer(g_hADX, 2, 1, 1, a) <= 0){ _NXS_IndicatorFailure("ADX"); return false; } g_adxMinus= a[0];
   if(CopyBuffer(g_hRSI, 0, 1, 1, a) <= 0){ _NXS_IndicatorFailure("RSI"); return false; } g_rsi = a[0];
   if(CopyBuffer(g_hBB, 1, 1, 1, a) <= 0){ _NXS_IndicatorFailure("BollingerBands"); return false; } g_bbUpper = a[0];
   if(CopyBuffer(g_hBB, 2, 1, 1, a) <= 0){ _NXS_IndicatorFailure("BollingerBands"); return false; } g_bbLower = a[0];
   if(CopyBuffer(g_hBB, 0, 1, 1, a) <= 0){ _NXS_IndicatorFailure("BollingerBands"); return false; } g_bbMid   = a[0];
   if(CopyBuffer(g_hMACD, 0, 1, 1, a) <= 0){ _NXS_IndicatorFailure("MACD"); return false; } g_macd    = a[0];
   if(CopyBuffer(g_hMACD, 1, 1, 1, a) <= 0){ _NXS_IndicatorFailure("MACD"); return false; } g_macdSig = a[0];
   if(CopyBuffer(g_hSAR, 0, 1, 1, a) <= 0){ _NXS_IndicatorFailure("SAR"); return false; } g_sar = a[0];
   if(CopyBuffer(g_hATR, 0, 1, 1, a) <= 0){ _NXS_IndicatorFailure("ATR"); return false; } g_atr = a[0];
   double atrArr[];
   if(CopyBuffer(g_hATR, 0, 1, InpATR_AvgPeriod, atrArr) > 0){
      double s = 0; int n = ArraySize(atrArr); for(int k=0;k<n;k++) s += atrArr[k];
      g_atrAvg = (n>0) ? s/n : g_atr;
   } else g_atrAvg = g_atr;
   if(CopyBuffer(g_hEMA200, 0, 1, 1, a) <= 0){ _NXS_IndicatorFailure("EMA200"); return false; } g_ema200 = a[0];
   if(CopyBuffer(g_hEMA9,   0, 1, 1, a) <= 0){ _NXS_IndicatorFailure("EMA9"); return false; } g_ema9   = a[0];
   if(CopyBuffer(g_hEMA21,  0, 1, 1, a) <= 0){ _NXS_IndicatorFailure("EMA21"); return false; } g_ema21  = a[0];
   if(CopyBuffer(g_hICHI, 0, 1, 1, a) <= 0){ _NXS_IndicatorFailure("Ichimoku"); return false; } g_ichiTenkan = a[0];
   if(CopyBuffer(g_hICHI, 1, 1, 1, a) <= 0){ _NXS_IndicatorFailure("Ichimoku"); return false; } g_ichiKijun  = a[0];
   if(CopyBuffer(g_hICHI, 2, 1, 1, a) <= 0){ _NXS_IndicatorFailure("Ichimoku"); return false; } g_ichiSpanA  = a[0];
   if(CopyBuffer(g_hICHI, 3, 1, 1, a) <= 0){ _NXS_IndicatorFailure("Ichimoku"); return false; } g_ichiSpanB  = a[0];
   g_indCachedBar = curBar;
   g_indCachedTF  = etf;
   _NXS_IndicatorSuccess();
   return true;
}

// NXR reuse/performance pack: include at file scope, after the original
// NXS_UpdateIndicators() definition and before signal/router functions.
#include <NEXUS_v1\NXS_ReusePerformancePack.mqh>

// NXS_PickBestSignal() rimossa il 16/07: funzione legacy mai chiamata da
// nessun punto del codice (superata da NXS_CollectRaw/NXS_CollectAllSignals,
// il vero router in uso). Teneva una firma vecchia di NXS_Strat_LiqSweep
// (SNXSSweep invece di SNXSSweepExt) che avrebbe rotto la compilazione dopo
// il fix del sweep su LIQ_SWEEP - rimossa invece di tenerla in sincrono per
// una funzione morta.

// AUD0-MQL-003 — DERIVA FRA ROUTER, SELETTORE E REGISTRO.
//
// Il router chiama a mano ogni strategia e assegna numeri di selettore fissi
// (1..37). Esistono pero' tre elenchi paralleli della stessa cosa: questo
// codice, la mappa dei numeri di selettore in NXS_Inputs.mqh e il registro
// canonico generato. Rinominare o aggiungere una strategia in uno solo dei tre
// non produce alcun errore: produce una strategia che non viene mai valutata,
// o un numero di selettore che isola quella sbagliata.
//
// Unificare i tre in una tabella dati sola e' una riscrittura del router. Qui
// si chiude il buco che conta: la DERIVA diventa VISIBILE all'avvio invece di
// restare silenziosa per mesi.
void NXS_Router_AuditRegistry(){
   int missing = 0;
   for(int i = 0; i < NXS_LIVE_STRATEGY_COUNT; i++){
      string id = NXS_StrategyIdAt(i);
      if(StringLen(id) == 0) continue;
      bool mapped = false;
      _NXS_StrategyToggle(id, mapped);
      if(!mapped){
         missing++;
         PrintFormat("[NEXUS][CONTRATTO] '%s' e' nel registro canonico ma il "
                     "router non ha un interruttore per essa: non verra' mai "
                     "valutata", id);
      }
   }
   if(missing == 0)
      PrintFormat("[NEXUS] router allineato al registro canonico (%d strategie)",
                  NXS_LIVE_STRATEGY_COUNT);
   else
      PrintFormat("[NEXUS][CONTRATTO][ALERT] %d strategie del registro non sono "
                  "raggiungibili dal router", missing);
}

// ============================================================
// PHASE 2 — Signal Router with fallback.
// Collects every signal (classic + SMC), applies score cap +
// confluence + MTF/Velocity family factor, then tries the best
// signal first; if a non-critical gate blocks it, falls back to
// the next-best until one passes or the list is exhausted.
// ============================================================
// v2.3.0 — raccolta "grezza": chiama tutte le strategie e applica il gate HTF
// per-strategia sul TF ATTIVO (g_activeTF). Estratta da NXS_CollectAllSignals
// per poter essere richiamata una volta per TF nel multi-timeframe.
int NXS_CollectRaw(SNXSSweep &sw, SNXSSweepExt &swExt, SNXSAMD &amd,
                   SNXSSignal &out[]){
   int n = 0;
   // Classic 16
   out[n++] = NXS_Strat_ADXRSI();
   out[n++] = NXS_Strat_Bollinger();
   out[n++] = NXS_Strat_MACD();
   out[n++] = NXS_Strat_SAR();
   out[n++] = NXS_Strat_TSI();
   out[n++] = NXS_Strat_Bjorgum();
   out[n++] = NXS_Strat_LiqSweep(swExt);
   out[n++] = NXS_Strat_FVG();
   out[n++] = NXS_Strat_BreakoutAcc();
   out[n++] = NXS_Strat_LondonBO();
   out[n++] = NXS_Strat_EMAPullback();
   out[n++] = NXS_Strat_BBSqueeze();
   out[n++] = NXS_Strat_Ichimoku();
   out[n++] = NXS_Strat_RSIDiv();
   out[n++] = NXS_Strat_OrderBlock();
   out[n++] = NXS_Strat_StructureReaction();
   // SMC/ICT 10 (v2.0.36: && NXS_SelectorAllows(N) - see InpStrategySelector)
   if(InpStrat_TurtleSoup    && NXS_SelectorAllows(17)) out[n++] = NXS_Strat_TurtleSoup(swExt);
   if(InpStrat_IFVG          && NXS_SelectorAllows(18)) out[n++] = NXS_Strat_IFVG_Reversal();
   if(InpStrat_FVG_Mit       && NXS_SelectorAllows(19)) out[n++] = NXS_Strat_FVG_Mitigation();
   // 13/08 - variante a registro (15 barre), vedi NXS_Strategies_SMC.mqh
   if(InpStrat_FVG_MIT_WINDOW && NXS_SelectorAllows(39)) out[n++] = NXS_Strat_FVG_Mitigation_Window();
   if(InpStrat_OB_Mit        && NXS_SelectorAllows(20)) out[n++] = NXS_Strat_OB_Mitigation_Structural();
   if(InpStrat_SH_BMS_RTO    && NXS_SelectorAllows(21)) out[n++] = NXS_Strat_SH_BMS_RTO(swExt);
   // 14/08 - state machine V2 indipendente, walk-forward 5/5 su 1h (vedi vault)
   if(InpStrat_SH_BMS_RTO_V2 && NXS_SelectorAllows(40)) out[n++] = NXS_Strat_SH_BMS_RTO_V2(swExt);
   if(InpStrat_SMS_BMS_RTO   && NXS_SelectorAllows(22)) out[n++] = NXS_Strat_SMS_BMS_RTO();
   if(InpStrat_SilverBullet  && NXS_SelectorAllows(23)) out[n++] = NXS_Strat_SilverBullet(swExt);
   if(InpStrat_AMD_Reversal  && NXS_SelectorAllows(24)) out[n++] = NXS_Strat_AMD_Reversal(swExt, amd);
   if(InpStrat_OTE_Cont      && NXS_SelectorAllows(25)) out[n++] = NXS_Strat_OTE_Continuation();
   if(InpStrat_MalaysianSNR  && NXS_SelectorAllows(26)) out[n++] = NXS_Strat_MalaysianSNR_Rejection();
   // 24/08 - pivot di swing maggiore, vedi NXS_Strategies_SMC.mqh
   if(InpStrat_SwingFalseBreak && NXS_SelectorAllows(41)) out[n++] = NXS_Strat_SwingFalseBreak();
   // 24/08 - z-score + regime SMA200, stop strutturale M5, vedi NXS_Strategies.mqh
   if(InpStrat_ZScoreBreakout  && NXS_SelectorAllows(42)) out[n++] = NXS_Strat_ZScoreBreakout();

   // v2.0.7 INSTITUTIONAL MODELS (9)
   SNXSHTF htfInst = NXS_GetHTFBias();
   if(InpUseStrat_CISD        && NXS_SelectorAllows(27)) out[n++] = NXS_Strat_CISD(swExt);
   if(InpUseStrat_AMD_Cont    && NXS_SelectorAllows(28)) out[n++] = NXS_Strat_AMD_Continuation(amd, htfInst);
   if(InpUseStrat_Judas       && NXS_SelectorAllows(29)) out[n++] = NXS_Strat_JudasSwing(swExt, amd);
   if(InpUseStrat_LdnReversal && NXS_SelectorAllows(30)) out[n++] = NXS_Strat_LondonReversal(swExt, amd);
   if(InpUseStrat_NYReversal  && NXS_SelectorAllows(31)) out[n++] = NXS_Strat_NYReversal(swExt);
   if(InpUseStrat_WeeklyExp   && NXS_SelectorAllows(32)) out[n++] = NXS_Strat_WeeklyRangeExp();
   if(InpUseStrat_PO3         && NXS_SelectorAllows(33)) out[n++] = NXS_Strat_PO3(swExt, amd);
   if(InpUseStrat_LiqVoid     && NXS_SelectorAllows(34)) out[n++] = NXS_Strat_LiquidityVoid(htfInst);
   if(InpUseStrat_DispRebal   && NXS_SelectorAllows(35)) out[n++] = NXS_Strat_DisplacementRebalance();

   // v2.0.8 — Range Fade
   if(InpUseStrat_RangeFade   && NXS_SelectorAllows(37)) out[n++] = NXS_Strat_RangeFade();

   // v2.0.20 — Elliott Wave (#37)
   if(InpUseStrat_Elliott     && NXS_SelectorAllows(36)) out[n++] = NXS_Strat_Elliott();

   // 11/08 — CRT (Candle Range Theory, #38)
   if(InpUseStrat_CRT         && NXS_SelectorAllows(38)) out[n++] = NXS_Strat_CRT();

   // 28/08 — BarUpDn, portata da script Pine TradingView pubblico (#43)
   if(InpStrat_BarUpDn        && NXS_SelectorAllows(43)) out[n++] = NXS_Strat_BarUpDn();

   // 28/08 — PMax, portata da script Pine TradingView pubblico (#44)
   if(InpStrat_PMax           && NXS_SelectorAllows(44)) out[n++] = NXS_Strat_PMax();

   // 28/08 — MACD+SMA200, portata da script Pine TradingView pubblico (#45)
   if(InpStrat_MacdSma200     && NXS_SelectorAllows(45)) out[n++] = NXS_Strat_MacdSma200();

   // 28/08 — RSI Divergence su pivot, portata da script Pine TradingView pubblico (#46)
   if(InpStrat_RsiDivPine     && NXS_SelectorAllows(46)) out[n++] = NXS_Strat_RsiDivPine();

   // 28/08 — Ichimoku+HullMA+MACD, portata da script Pine TradingView pubblico (#47)
   if(InpStrat_IchimokuHull   && NXS_SelectorAllows(47)) out[n++] = NXS_Strat_IchimokuHullMacd();

   // 28/08 — 3Commas Bot, portata da script Pine TradingView pubblico (#48)
   if(InpStrat_3CommasBot     && NXS_SelectorAllows(48)) out[n++] = NXS_Strat_3CommasBot();

   // 02/09 — Pivot Extension + Wick Rejection, idea originale utente (#49)
   if(InpStrat_PivotWick      && NXS_SelectorAllows(49)) out[n++] = NXS_Strat_PivotWick();

   // 06/09 — LEVEL_CONFLUENCE: merge PIVOT_WICK/STRUCT_REACT/MALAYSIAN_SNR
   // con bonus di confluenza multi-TF e trigger touch/sweep, idea utente (#50)
   if(InpStrat_LevelConfluence && NXS_SelectorAllows(50)) out[n++] = NXS_Strat_LevelConfluence();

   // 06/09 — LEVEL_CONFLUENCE gemella su M5: livelli H1/H4/D1, esecuzione M5
   // invece di M15, idea utente "segnamo i livelli D1 H4 H1 e entriamo su
   // M15 e M5" (#51)
   if(InpStrat_LevelConfluenceM5 && NXS_SelectorAllows(51)) out[n++] = NXS_Strat_LevelConfluence_M5();

   // 06/09 — LEVEL_REACTION: merge VERO di PIVOT_WICK+STRUCT_REACT+MALAYSIAN_SNR
   // (due fonti di livello indipendenti + gate sulla profondita' di
   // sfondamento in pip tarato sull'analisi fresca del grafico), idea utente
   // dopo aver notato che sono la stessa idea implementata quattro volte (#52)
   if(InpStrat_LevelReaction && NXS_SelectorAllows(52)) out[n++] = NXS_Strat_LevelReaction();

   // 06/09 — LEVEL_REACTION gemella su M5 (#53)
   if(InpStrat_LevelReactionM5 && NXS_SelectorAllows(53)) out[n++] = NXS_Strat_LevelReaction_M5();

   // v2.2.8 — gate HTF PER-STRATEGIA (come nel backtest): se il profilo della
   // strategia richiede l'allineamento HTF, il segnale sopravvive solo se e' nel
   // senso del trend (prezzo vs EMA200 sul TF di entrata, proxy del filtro trend).
   if(InpUseStrategyProfiles){
      // px200 sul TF ATTIVO: in multi-TF ogni passaggio confronta col trend del
      // suo timeframe; in single-TF NXS_EffTF() resta InpTFEntry (invariato).
      double px200 = iClose(g_sym, NXS_EffTF(), 0);
      for(int k = 0; k < n; k++){
         if(out[k].dir == DIR_NONE) continue;
         bool needHtf;
         if(NXS_Profile_HTF(out[k].stratName, needHtf) && needHtf && g_ema200 > 0){
            if((out[k].dir == DIR_BUY  && px200 < g_ema200) ||
               (out[k].dir == DIR_SELL && px200 > g_ema200)){
               out[k].dir = DIR_NONE;   // controtrend -> scartato per questa strategia
            }
         }
         // 25/08 - blocco direzione per strategia (NXS_Profile_DirectionLock):
         // verificato oggi che alcune strategie rendono nettamente meglio
         // solo in una direzione sulla loro ricetta live reale - prima
         // conferma concreta STRUCT_REACT (simmetrica H1 PF0.61 in perdita,
         // BUY-only 4h PF2.32-2.43). Altre strategie della ricerca 24/08
         // (SAR/ADX_RSI/ecc.) mostravano lo stesso pattern ma NON ancora
         // riverificate sulla ricetta live esatta - non attivato per loro
         // finche' non c'e' lo stesso livello di conferma.
         if(out[k].dir != DIR_NONE){
            int lock = NXS_Profile_DirectionLock(out[k].stratName);
            if((lock > 0 && out[k].dir == DIR_SELL) || (lock < 0 && out[k].dir == DIR_BUY)){
               out[k].dir = DIR_NONE;
            }
         }
      }
   }
   return n;
}

//+------------------------------------------------------------------+
//| Raccolta segnali: single-TF (default) oppure MULTI-TF su un solo  |
//| grafico (InpProfileMultiTF) -> ogni strategia sul suo timeframe.  |
//+------------------------------------------------------------------+
int NXS_CollectAllSignals(SNXSSweep &sw, SNXSSweepExt &swExt, SNXSAMD &amd,
                          SNXSSignal &out[]){
   int n = 0;
   if(InpUseStrategyProfiles && InpProfileMultiTF){
      // Un passaggio per TF: attiva gli handle del TF, raccogli, e tieni solo
      // le strategie il cui TF ottimale (dal backtest) coincide col passaggio.
      // AUD0-MQL-005: i passaggi erano fissi a D1/H4/H1. Un profilo canonico
      // che scegliesse M30 o M15 non veniva MAI valutato — la strategia
      // spariva senza un errore. I timeframe si ricavano ora dai profili reali
      // delle strategie del registro: aggiungerne uno nuovo non richiede di
      // ricordarsi di toccare questo elenco.
      ENUM_TIMEFRAMES passes[16];
      int npasses = 0;
      for(int si = 0; si < NXS_LIVE_STRATEGY_COUNT && npasses < 16; si++){
         ENUM_TIMEFRAMES stf = NXS_Profile_TF(NXS_StrategyIdAt(si));
         if(stf == PERIOD_CURRENT) continue;
         bool dup = false;
         for(int q = 0; q < npasses; q++) if(passes[q] == stf){ dup = true; break; }
         if(!dup) passes[npasses++] = stf;
      }
      if(npasses == 0){   // nessun profilo con TF: comportamento storico
         passes[0] = PERIOD_D1; passes[1] = PERIOD_H4; passes[2] = PERIOD_H1;
         npasses = 3;
      }
      for(int p = 0; p < npasses; p++){
         if(!NXS_ActivateTF(passes[p])) continue;   // handle non pronti: salta il TF
         // Phase 2: struttura + sweep ricalcolati sul TF del passaggio, cosi'
         // anche le strategie SMC (LIQ_SWEEP, OB, FVG...) girano sul loro TF.
         NXS_UpdateStructure(g_sym, passes[p]);
         g_reaction = NXS_DetectReaction(g_sym, passes[p]); // v2.4.2: reazione sul TF del passaggio (per le SMC)
         SNXSSweep    swP  = NXS_DetectSweep();
         SNXSSweepExt swxP = NXS_DetectSweepExt();
         SNXSSignal tmp[NXS_MAX_SIGNALS];
         int m = NXS_CollectRaw(swP, swxP, amd, tmp);
         for(int k = 0; k < m && n < ArraySize(out); k++){
            if(NXS_Profile_TF(tmp[k].stratName) != passes[p]) continue;
            out[n++] = tmp[k];
         }
      }
      NXS_ActivateOriginal();               // ripristina il TF di ingresso
      NXS_UpdateStructure(g_sym, InpTFEntry); // ripristina la struttura al TF di ingresso
      g_reaction = NXS_DetectReaction(g_sym, InpTFEntry); // ripristina la reazione al TF di ingresso
   } else {
      n = NXS_CollectRaw(sw, swExt, amd, out);
   }

   // v2.0.5 stats + sourceTF (una volta sola, sui segnali tenuti)
   for(int k = 0; k < n; k++){
      if(out[k].sourceTF == PERIOD_CURRENT)
         out[k].sourceTF = NXS_StrategySourceTF(out[k].stratName);
      if(StringLen(out[k].stratName) > 0) NXS_Stats_RecordCalled(out[k].stratName);
      if(out[k].dir != DIR_NONE)          NXS_Stats_RecordSetup(out[k].stratName);
   }
   return n;
}

//+------------------------------------------------------------------+
//| OnInit                                                            |
//+------------------------------------------------------------------+
int OnInit(){
   g_testerPassStart = TimeCurrent();   // AUD0-MQL-014
   g_sym    = _Symbol;
   g_point  = SymbolInfoDouble(g_sym, SYMBOL_POINT);
   g_digits = (int)SymbolInfoInteger(g_sym, SYMBOL_DIGITS);
   NXS_ResetTradesLogIfRequested();   // 17/07 sera - vedi NXS_Logging.mqh, opt-in, mai automatico

   // AUD0-LEDGER-007: il ledger assume "una position = un trade logico", vero
   // solo sui conti HEDGING. Su netting la position sopravvive ai flip di
   // direzione: P/L, R e conteggi dei trade diventano silenziosamente falsi, e
   // grid/piramide/istituzionale non possono nemmeno esistere come gambe
   // separate. Finora era solo una nota nei commenti: ora e' un rifiuto.
   ENUM_ACCOUNT_MARGIN_MODE marginMode =
      (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE);
   if(marginMode != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING){
      PrintFormat("[NEXUS ERROR] conto NON hedging (margin_mode=%s). Il modello "
                  "'una position = un trade logico' non regge: il ledger, la R "
                  "e le gambe grid/piramide darebbero numeri falsi. EA fermo.",
                  EnumToString(marginMode));
      Alert("NEXUS: conto non hedging — EA non avviato");
      return INIT_FAILED;
   }
   // AUD0-SEC-001: prima di QUALSIASI chiamata al backend (il fetch del profilo
   // qui sotto e' la prima) si verifica che il token del bridge non sia il
   // segnaposto pubblico e che l'URL sia HTTPS. Altrimenti la WebSync si spegne.
   NXS_WebCredentialPreflight();
   // AUD0-MQL-011 — ORDINE DI INIZIALIZZAZIONE.
   //
   // Il profilo bloccato veniva scaricato PRIMA di: validazione della
   // whitelist simboli, creazione degli handle indicatore, inizializzazione
   // delle impostazioni runtime, applicazione dei preset, verifica della
   // licenza e caricamento dello stato persistito. Quindi valori remoti
   // potevano sovrascrivere — o essere sovrascritti da — layer che non erano
   // ancora stati inizializzati, in un ordine che nessuno aveva dichiarato.
   //
   // Il fetch e' ora RINVIATO a fine OnInit, quando tutti i layer locali
   // esistono e la precedenza e' esplicita: locale prima, remoto dopo.
   // v2.0.9 — load Sprint 3 learner CSV + reset handle pool
   NXS_HandlePool_Release();
   NXS_EA_Learner_Load();
   NXS_TradeSetMagic(InpMagic);
   NXS_TradeSetFillingBySymbol(g_sym);
   g_balanceDayStart = AccountInfoDouble(ACCOUNT_BALANCE);
   NXS_DailyRollover();

   // === Phase 2: symbol profile + presets ===
   NXS_BuildSymbolProfile();
   if(!g_profile.allowed){
      PrintFormat("[NEXUS ERROR] Symbol %s NOT in whitelist (InpAllowedSymbols). EA will not trade.",
                  _Symbol);
      return INIT_FAILED;
   }

   if(!NXS_CreateHandles()) return INIT_FAILED;
   NXS_CaptureOriginalHandles();   // v2.3.0: per il ripristino dopo i passaggi multi-TF
   g_activeTF = InpTFEntry;
   NXS_MTF_CreateHandles();

   NXS_Runtime_Init();
   NXS_ApplyPreset();

   // Apply profile defaults for spread cap if user kept 0
   if(InpHardMaxSpreadPts == 0){
      Print("[NEXUS] Using profile default hard spread cap: ", g_profile.maxSpreadPts, " points");
   }

   // === Phase 3: license verification ===
   if(!NXS_License_Verify()){
      Print("[NEXUS ERROR] License verification FAILED - EA in IDLE mode (no trading)");
      // Continue init but trading disabled
   }

   // === Phase 1: state persistence resume ===
   NXS_Blk_Reset();
   NXS_State_Load();

   // Diagnostics
   NXS_Diag_OnInit();
   // AUD0-EXEC-007: verifica una volta all'avvio che le liste di strategie
   // mantenute a mano non siano andate alla deriva rispetto al registro.
   NXS_CounterHTF_AuditList();
   NXS_Router_AuditRegistry();

   // AUD0-MQL-012 — una licenza non valida NON fa fallire OnInit: l'EA resta
   // caricato in modalita' inerte e dipende dal gate di licenza che ogni
   // percorso di esposizione attraversa (gate 1 di NXS_CommonExposurePreflight).
   // E' una scelta di recuperabilita' — una licenza puo' tornare valida senza
   // riattaccare l'EA — ma va DICHIARATA, altrimenti un EA "caricato" sembra
   // operativo mentre non lo e'.
   if(InpEnableLicense && !NXS_License_Enforce()){
      Print("[NEXUS][LICENZA] EA caricato in MODALITA' INERTE: nessuna nuova "
            "esposizione finche' la licenza non e' valida. La gestione delle "
            "posizioni gia' aperte e le protezioni restano attive.");
   }
   NXS_Stats_Init();   // v2.0.5 strategy stats tracker

   // PR1 - Trade Ledger: riconcilia lo stato con la history (emitted-set +
   // chiusure avvenute offline). Parita' storica: le chiusure offline NON
   // rigenerano notifiche/stats locali (non lo facevano nemmeno prima); il
   // loro push al backend resta a NXS_SyncRecentClosedTrades (idempotente).
   {
      int offlineFinals = NXS_Ledger_Boot(7);
      SNxsLedgerTrade bootTc;
      while(NXS_Ledger_PopClosed(bootTc)){
         PrintFormat("[NEXUS LEDGER] chiusura offline riconciliata: pos=%I64u strat=%s pnl=%.2f partials=%d",
                     bootTc.position_id, bootTc.strategy, bootTc.pnl, bootTc.partial_count);
      }
      if(offlineFinals > 0)
         PrintFormat("[NEXUS LEDGER] boot: %d trade logici chiusi offline riconciliati", offlineFinals);
   }

   // PR2 - Virtual SL: ricostruzione stato armato dopo restart (validato per
   // account+magic, riconciliato con broker/ledger). No-op in modalita' OFF.
   NXS_VSL_Restore();

   PrintFormat("[NEXUS v%s] Initialized on %s | Profile=%s | Magic=%I64d | WebSync=%s URL=%s",
               NEXUS_VERSION, g_sym, g_profile.className, InpMagic,
               (InpEnableWebSync ? "ON":"OFF"), InpWebURL);
   // v2.0.9 — explicit MTF independence declaration
   PrintFormat("[NEXUS MTF] Chart TF=%s · Entry=%s · Medium=%s · High=%s · System is CHART-INDEPENDENT (uses configured TFs only)",
               EnumToString((ENUM_TIMEFRAMES)Period()),
               EnumToString((ENUM_TIMEFRAMES)InpTFEntry),
               EnumToString((ENUM_TIMEFRAMES)InpTFMedium),
               EnumToString((ENUM_TIMEFRAMES)InpTFHigh));
   if((int)Period() != (int)InpTFEntry){
      PrintFormat("[NEXUS MTF] WARNING: chart TF (%s) differs from Entry TF (%s) — EA will still trade %s correctly.",
                  EnumToString((ENUM_TIMEFRAMES)Period()),
                  EnumToString((ENUM_TIMEFRAMES)InpTFEntry),
                  EnumToString((ENUM_TIMEFRAMES)InpTFEntry));
   }
   EventSetTimer(1);

   if(InpEnableWebSync && !MQLInfoInteger(MQL_TESTER)){
      // AUD0-MQL-007 — qui partivano una push immediata e la riconciliazione di
      // 7 giorni di storico, entrambe con WebRequest bloccanti. Con un backend
      // lento o irraggiungibile l'aggancio dell'EA al grafico restava appeso, e
      // un riavvio di MT5 con piu' grafici moltiplicava l'attesa.
      //
      // OnInit fa ora solo lavoro locale: carica l'outbox e ARMA il primo
      // ciclo. La prima push e il backfill avvengono al primo scatto di timer,
      // dove esiste gia' un budget e nulla blocca l'avvio.
      NXS_Outbox_Load();
      g_lastPushTime     = 0;   // il timer eseguira' subito la prima push
      g_lastHistSyncTime = 0;   // ... e subito dopo il backfill dello storico
      Print("[NEXUS] sincronizzazione web armata: la prima consegna avviene dal "
            "timer, l'avvio non attende la rete");
   }

   // AUD0-MQL-011: il profilo bloccato si applica QUI, dopo che whitelist,
   // handle, preset, licenza e stato persistito esistono gia'. La precedenza
   // e' dichiarata: il remoto sovrascrive il locale, mai il contrario.
   NXS_LockedProfile_Fetch();

   // Initial dashboard render
   if(InpShowDashboard) NXS_Dashboard_Render();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason){
   EventKillTimer();
   NXS_EA_DrainLedger();    // PR1: non perdere chiusure logiche in coda allo shutdown
   NXS_Stats_Deinit();      // v2.0.5 final export
   NXS_Ledger_Persist();    // PR1: emitted-set su disco (no-op nel tester)
   NXS_VSL_Persist();       // PR2: stato Virtual SL su disco (no-op nel tester/OFF)
   NXS_State_Save(true);       // PR5: shutdown snapshot bypasses periodic throttle
   NXS_ActivateOriginal();     // v2.3.0: assicura g_h* = originali prima di rilasciarli
   NXS_ReleaseHandles();
   NXS_MTF_Release();          // v2.3.0: cache handle multi-TF per-strategia
   NXS_MTF_ReleaseHandles();
   NXS_HandlePool_Release();   // v2.0.9 Sprint 1
   if(InpShowDashboard) NXS_Dashboard_Cleanup();
   PrintFormat("[NEXUS] Deinit reason=%d", reason);
}

//+------------------------------------------------------------------+
//| OnTester - v2.0.29: logs one row per optimization pass to a plain |
//| CSV. MT5 has no command-line way to export the .opt binary       |
//| optimization results, so we write our own log here, mirroring    |
//| the NXS_StratStats CSV export pattern already used elsewhere.    |
//| Each parallel tester "agent" writes to its own sandboxed          |
//| MQL5\Files, so a batch run must collect+merge across all agents.  |
//+------------------------------------------------------------------+
// AUD0-MQL-013 — l'obiettivo di ottimizzazione era il SOLO profit factor.
//
// Il profit factor non contiene numero di operazioni, drawdown, recupero ne'
// stabilita': l'ottimizzatore premiava insiemi di parametri con pochissimi
// trade fortunati e drawdown insostenibili, che poi non reggevano in reale.
//
// Il criterio e' ora composito ed esplicito:
//   - sotto un numero minimo di operazioni il risultato vale 0 (campione non
//     informativo, non "ottimo");
//   - il profit factor viene scalato dal recovery factor (profitto rispetto al
//     drawdown massimo), cosi' un drawdown grande non puo' essere compensato
//     da un profit factor alto;
//   - un drawdown oltre il limite di rischio dichiarato azzera il punteggio.
#define NXS_TESTER_MIN_TRADES   30
#define NXS_TESTER_MAX_DD_PCT   35.0

double NXS_TesterObjective(){
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < NXS_TESTER_MIN_TRADES) return 0.0;

   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   if(pf <= 0.0) return 0.0;

   double ddPct = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   if(ddPct >= NXS_TESTER_MAX_DD_PCT) return 0.0;

   double recovery = TesterStatistics(STAT_RECOVERY_FACTOR);
   if(recovery <= 0.0) recovery = 0.01;

   double expectancy = TesterStatistics(STAT_EXPECTED_PAYOFF);
   if(expectancy <= 0.0) return 0.0;   // aspettativa negativa: mai "ottimo"

   // Penalita' lineare sul drawdown: a parita' di PF vince chi soffre meno.
   double ddPenalty = 1.0 - (ddPct / NXS_TESTER_MAX_DD_PCT);
   return pf * MathSqrt(recovery) * ddPenalty;
}

// AUD0-MQL-014: identita' stabile della passata di ottimizzazione. Deriva dai
// parametri della passata, quindi due agenti che eseguono la STESSA
// combinazione producono lo stesso id — cosi' un duplicato si riconosce invece
// di sembrare due risultati distinti.
datetime g_testerPassStart = 0;

string _nxs_tester_runId(){
   string seed = StringFormat("%s|%s|%.4f|%.4f|%.1f|%d",
                              _Symbol, EnumToString((ENUM_TIMEFRAMES)Period()),
                              InpATR_SL_Mult, InpATR_TP_Mult, InpMinEntryScore,
                              InpStrategySelector);
   long h = 5381;
   for(int i = 0; i < StringLen(seed); i++)
      h = ((h * 33) ^ (long)StringGetCharacter(seed, i)) & 0x7FFFFFFFFFFF;
   return StringFormat("%I64X", h);
}

double OnTester(){
   string fname = "NEXUS\\nexus_optimization_log.csv";
   bool isNew = !FileIsExist(fname);
   int h = FileOpen(fname, FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ, ';');
   if(h == INVALID_HANDLE) return 0.0;
   FileSeek(h, 0, SEEK_END);
   if(isNew){
      // v2.0.31: also log the per-strategy-specific knobs (FVG/OB size
      // thresholds, ADX_RSI score cap, Elliott params) - always, regardless
      // of which strategy is under test, so a run's grid dimension is never
      // silently missing from the CSV again (lost for the FVG_Mit pilot).
      // AUD0-MQL-014: ogni agente del tester scrive nella propria sandbox. Senza
      // identita' del run e dell'agente, unire i CSV produce righe che nessuno
      // sa piu' a quale passata appartengano — o duplicati indistinguibili.
      FileWrite(h, "run_id","agent","pass_started_at",
                "atr_sl_mult","atr_tp_mult","min_entry_score",
                "nxr_min_fvg_size_atr","nxr_displacement_atr","adxrsi_score_cap",
                "ell_swing_wing","ell_retrace_min","ell_retrace_max","ell_min_score",
                "trades","net_profit","profit_factor","expected_payoff",
                "max_equity_dd_pct","recovery_factor","sharpe_ratio","win_rate_pct");
   }
   double trades  = TesterStatistics(STAT_TRADES);
   double wins    = TesterStatistics(STAT_PROFIT_TRADES);
   double winRate = (trades > 0) ? (wins / trades * 100.0) : 0.0;
   FileWrite(h,
      // AUD0-MQL-014: identita' del run e dell'agente in ogni riga, cosi' un
      // merge fra sandbox e' deterministico e i duplicati sono riconoscibili.
      _nxs_tester_runId(),
      IntegerToString((long)TerminalInfoInteger(TERMINAL_BUILD)) + ":" +
        IntegerToString((long)MQLInfoInteger(MQL_MEMORY_USED)),
      TimeToString(g_testerPassStart, TIME_DATE|TIME_SECONDS),
      DoubleToString(InpATR_SL_Mult, 2),
      DoubleToString(InpATR_TP_Mult, 2),
      DoubleToString(InpMinEntryScore, 1),
      DoubleToString(InpNXR_MinFVGSizeATR, 3),
      DoubleToString(InpNXR_DisplacementATR, 3),
      DoubleToString(InpADXRsiScoreCap, 1),
      InpEllSwingWing,
      DoubleToString(InpEllRetraceMin, 3),
      DoubleToString(InpEllRetraceMax, 3),
      DoubleToString(InpEllMinScore, 1),
      (int)trades,
      DoubleToString(TesterStatistics(STAT_PROFIT), 2),
      DoubleToString(TesterStatistics(STAT_PROFIT_FACTOR), 3),
      DoubleToString(TesterStatistics(STAT_EXPECTED_PAYOFF), 3),
      DoubleToString(TesterStatistics(STAT_EQUITY_DDREL_PERCENT), 2),
      DoubleToString(TesterStatistics(STAT_RECOVERY_FACTOR), 3),
      DoubleToString(TesterStatistics(STAT_SHARPE_RATIO), 3),
      DoubleToString(winRate, 2)
   );
   FileClose(h);
   return NXS_TesterObjective();
}

// AUD0-MQL-006: tetto di tempo per uno scatto di timer.
#define NXS_TIMER_BUDGET_MS 400
bool g_timerBudgetWarned = false;

void OnTimer(){
   // AUDITPATCH: no WebRequest side effects during deterministic backtests.
   if(!MQLInfoInteger(MQL_TESTER)){
      // AUD0-MQL-006 — il timer a 1 secondo invocava NOVE attivita' di rete e
      // I/O a ogni scatto: push, polling, bridge visuale, riconciliazione,
      // sweep del ledger, licenza, salvataggio stato, dashboard, statistiche.
      // Ognuna con il proprio throttle interno, ma nessun budget complessivo:
      // in una giornata lenta gli scatti si accavallavano.
      //
      // Ora c'e' un BUDGET per scatto. Le attivita' sono in ordine di
      // priorita'; quando il budget e' esaurito le restanti slittano al
      // secondo successivo invece di allungare lo scatto corrente. Le
      // protezioni e il ledger stanno fuori dal budget: non slittano mai.
      uint tmBudgetStart = GetTickCount();
      NXS_Outbox_Drain();
      // AUD0-MQL-008: il pull delle impostazioni vive qui, non nel tick.
      NXS_PullSettings();
      if(GetTickCount() - tmBudgetStart < NXS_TIMER_BUDGET_MS) NXS_WebPushSafe();
      if(GetTickCount() - tmBudgetStart < NXS_TIMER_BUDGET_MS) NXS_WebPoll();
      if(GetTickCount() - tmBudgetStart < NXS_TIMER_BUDGET_MS)
         NXS_VisualBridge_PushHTTP();   // v2.0.9 — push OB/FVG/SNR to web Live Chart
      else if(!g_timerBudgetWarned){
         g_timerBudgetWarned = true;
         PrintFormat("[NEXUS] budget del timer esaurito (%d ms): attivita' non "
                     "critiche rimandate al prossimo scatto", NXS_TIMER_BUDGET_MS);
      }
      // Safety net: re-run the closed-trade backfill periodically (not just at
      // OnInit) so trades lost to a transient push failure (e.g. backend cold
      // start) still land in the backend even if the EA runs for days without
      // restarting.
      // AUD0-HSYNC-002: la sync consegna un lotto per chiamata. Finche'
      // dichiara di avere altro da consegnare si continua al tick di timer
      // successivo, invece di aspettare l'intervallo pieno e perdere tutto
      // cio' che eccedeva il primo lotto.
      if(InpEnableWebSync &&
         (NXS_HSync_HasMore() ||
          TimeCurrent() - g_lastHistSyncTime >= InpHistSyncIntervalSec)){
         g_lastHistSyncTime = TimeCurrent();
         NXS_SyncRecentClosedTrades();
      }
   }
   // PR1 - rete di sicurezza: chiusure il cui ultimo deal e' arrivato mentre
   // la position era ancora visibile (o evento perso) vengono riconciliate qui.
   if(NXS_Ledger_SweepPending() > 0) NXS_EA_DrainLedger();
   NXS_License_Verify();     // tester-safe; live hourly re-validation
   // AUD0-RS-008: l'equity breaker non era mai alimentato — il gate esisteva
   // ma non poteva scattare. Qui viene ricalcolato a cadenza limitata (5 min),
   // fuori dal percorso del tick perche' scansiona lo storico dei deal.
   NXS_RS_Breaker_Update();
   NXS_State_Save();
   if(InpShowDashboard) NXS_Dashboard_Render();
   if(InpStatsEnable){
      NXS_Stats_OnTick(InpStatsExportEverySec);
      NXS_EA_DrainLedger();   // PR1: chiusure trovate dallo scanner stats
   }
}

void OnTick(){
   // v2.0.9 Sprint 1 — skid protection: drop stale ticks (>InpMaxTickAgeMs)
   if(!NXS_IsFreshTick()) return;
   // v2.0.9 Sprint 2 — keep spread rolling window fresh + virt SL check
   NXS_RS_SpreadSample();
   NXS_EA_VirtSL_Check();
   // AUD0-MQL-008: qui c'era NXS_PullSettings(), che esegue una WebRequest con
   // timeout 3s SUL PERCORSO DEL TICK. Anche con il throttling interno, ogni
   // volta che scattava il tick restava bloccato fino a 3 secondi — e in quella
   // finestra non giravano Virtual SL, protezioni e OnTradeTransaction.
   // Il pull vive ora nel timer; il tick usa i valori gia' scaricati.
   datetime prevDay = g_dayStart;
   NXS_DailyRollover();
   if(g_dayStart != prevDay){
      NXS_Prot_OnNewDay();
      if(InpNotifyDailySummary) NXS_Notify_DailySummary();
   }
   NXS_Ruin_OnTick();
   NXS_Prot_OnTick();
   if(!NXS_UpdateIndicators()) return;

   g_regime  = NXS_DetectRegime();
   g_session = NXS_GetSession();

   SNXSHTF   htf   = NXS_GetHTFBias();
   SNXSVel   vel   = NXS_GetVelocity();
   SNXSAMD   amd   = NXS_GetAMD();
   SNXSSweep sweep = NXS_DetectSweep();

   // PR4: modules submit proposals; one deterministic action wins per ticket.
   NXS_PM_BeginCycle();
   // 02/09 - BUG TROVATO: NXS_State_ReconcileBroker() (che copia l'ATR
   // d'ingresso e le altre info dal registro intenti nell'array di stato
   // vivo g_managedState[], usato da NXS_State_EntryAtr/NXS_State_HasApplied
   // ecc.) veniva chiamata SOLO dentro NXS_State_Save()/Load(), entrambe
   // dietro il flag InpStatePersistInTester (default FALSE). Risultato: nel
   // Tester g_managedState[] non veniva MAI popolato, e ogni consumer di
   // NXS_State_EntryAtr cadeva SEMPRE sul fallback (g_atr, l'ATR del
   // timeframe del grafico/M15) invece del vero ATR di ingresso registrato -
   // scoperto testando un parziale su EMA_PULLBACK che scattava a 1/4-1/6
   // della soglia prevista. La riconciliazione in memoria e' un concetto
   // diverso dal salvataggio su disco (persistenza tra riavvii): va fatta
   // ogni tick a prescindere da InpStatePersistInTester.
   NXS_State_ReconcileBroker();
   // Management on every tick
   NXS_ManageFixedBE();
   NXS_ManageBreakevenAndTrail();
   NXS_TrailATR();                // NEW: ATR-based trailing overlay
   NXS_WeeklyExpManage();         // 26/08: breakeven+trailing strutturale dedicato a WEEKLY_EXP
   NXS_ManageSplit();
   NXS_ManageFixedPipPartial();
   NXS_ManageVolumePartial();
   NXS_ManagePipSequence();
   NXS_ManageSLReclaim();
   NXS_ManageProfitReclaim();
   if(InpUseInstitutionalCore){
      // Modello istituzionale: la sequenza (core+grid/recovery) e il trailing
      // "training stop" + runner sono gestiti qui. Grid/pyramid classici OFF
      // per non aggiungere due volte sulla stessa posizione.
      NXS_InstManage_OnTick();
   } else {
      NXS_ManageGrid();
      NXS_ManagePyramid(vel);
   }
   NXS_PM_ApplyCycle();

   // Web push (disabled in Strategy Tester)
   if(!MQLInfoInteger(MQL_TESTER)) NXS_WebPush(htf, vel, amd, sweep);

   // Diagnostic summary
   NXS_Diag_OnTick(NXS_HTFName(htf.bias), NXS_VelName(vel.state),
                   NXS_AMDName(amd.phase), NXS_GetBSP());

   // === v2.0.4: Visual Bridge export (lightweight ~20 GV sets) ===
   // Uses static cache of last "best" so HUD shows last decision strategy.
   static SNXSSignal s_visualBest; static bool s_visualInit = false;
   if(!s_visualInit){ ZeroMemory(s_visualBest); s_visualInit = true; }
   NXS_ExportStateToGV(htf, vel, amd, s_visualBest);

   // v2.0.13 — track extremum prezzo durante posizione aperta (per chain re-entry)
   NXS_Chain_TrackExtremum();

   // New bar gate
   datetime bt = iTime(g_sym, InpTFEntry, 0);
   if(bt == g_lastBarTime) return;
   g_lastBarTime = bt;

   NXS_UpdateStructure(g_sym, InpTFEntry);
   // v2.0.34: independent H1 structure context, recomputed only on H1 bar
   // close (not every entry-TF bar) since it tracks a slower timeframe.
   datetime h1Bar = iTime(g_sym, PERIOD_H1, 0);
   if(h1Bar != g_lastH1BarTime){
      g_lastH1BarTime = h1Bar;
      NXS_UpdateStructureH1(g_sym);
   }
   g_reaction = NXS_DetectReaction(g_sym, InpTFEntry);
   // Market Context Layer: snapshot direzionale (OFF di default via flag).
   if(InpUseMarketContext) NXS_Context_Update(htf, sweep, amd);

   // AUDITPATCH: count/report every closed-bar decision, including upstream vetoes.
   NXS_Blk_DecisionTick();
   if(g_eaPaused){ NXS_Blk_Bump(BLK_PAUSED); NXS_Blk_MaybeReport(); return; }
   if(!NXS_State_EntryAllowed()){
      NXS_Blk_Bump(BLK_PROTECTIONS); NXS_Blk_MaybeReport(); return;
   }
   if(!NXS_License_Enforce()){ NXS_Blk_Bump(BLK_LICENSE); NXS_Blk_MaybeReport(); return; }
   if(NXS_Prot_EntryBlocked()){ NXS_Blk_Bump(BLK_PROTECTIONS); NXS_Blk_MaybeReport(); return; }
   if(!NXS_SpreadOK()){ NXS_Blk_Bump(BLK_SPREAD); NXS_Blk_MaybeReport(); return; }
   if(NXS_NewsBlocking()){ NXS_Blk_Bump(BLK_NEWS); NXS_Blk_MaybeReport(); return; }

   NXS_ML_RefreshAll();

   // ---- Phase 2 router with fallback ----
   SNXSSweepExt swExt = NXS_DetectSweepExt();
   // AUD0-MQL-004: dimensione derivata dal registro, non un numero magico.
   SNXSSignal all[NXS_MAX_SIGNALS];
   int n = NXS_CollectAllSignals(sweep, swExt, amd, all);
   int directionalSignals = 0;
   for(int ds = 0; ds < n; ds++) if(all[ds].dir != DIR_NONE) directionalSignals++;

   // Confluence + score cap (only consider valid signals)
   NXS_ConfluenceReset();
   for(int i = 0; i < n; i++){
      if(all[i].dir == DIR_NONE) continue;
      int d = (all[i].dir == DIR_BUY) ? +1 : -1;
      NXS_ConfluenceRegister(d);
      all[i].score = NXS_ApplyScoreCap(all[i].stratName, all[i].score);
   }
   for(int i = 0; i < n; i++){
      if(all[i].dir == DIR_NONE) continue;
      int wd = (all[i].dir == DIR_BUY) ? +1 : -1;
      all[i].score = MathMin(100.0, all[i].score + (double)NXS_ConfluenceBonus(wd));
      // Market Context Layer: pesa la confluenza di contesto (bonus/penalità).
      all[i].score = NXS_Context_ApplyBonus(wd, all[i].score);
   }
   NXS_SignalSort(all, n);

   // v2.0.4: cache best signal for Visual Bridge HUD
   if(n > 0 && all[0].dir != DIR_NONE){ s_visualBest = all[0]; }

   // === MODALITÀ RACCOLTA DATI / SCREENING (v2.1.1) =================
   // Apre OGNI segnale valido a lotto fisso piccolo, taggato per strategia,
   // saltando i gate soft e la soglia di score. Solo sicurezza dura (preflight:
   // spread/margine/stops). Serve a far girare TUTTE le strategie e vedere nel
   // Journal quali hanno edge, senza escluderne nessuna a priori. Solo demo.
   if(InpDataCollectionMode){
      NXS_Context_Update(htf, sweep, amd);   // per taggare il contesto (tier HTF/LTF)
      double dstep = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP); if(dstep <= 0) dstep = 0.01;
      double dminL = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);  if(dminL <= 0) dminL = 0.01;
      double dlots = MathMax(dminL, MathFloor(InpDataCollectionLot / dstep) * dstep);
      int baseOpen = PositionsTotal();
      int openedNow = 0;
      for(int i = 0; i < n; i++){
         if(all[i].dir == DIR_NONE) continue;
         if(baseOpen + openedNow >= InpDataCollectionMaxOpen) break;   // tetto sicurezza
         SNXSSignal s = all[i];
         // 17/07 fix - trovato analizzando NEXUS_trades.csv di uno sweep reale:
         // a differenza del path standard (riga ~821, NXS_StrategyHasOpenPos),
         // qui mancava del tutto il gate "1 posizione per strategia alla volta".
         // Un segnale a stato persistente (la maggior parte lo sono, non solo
         // un evento singolo) riapriva una NUOVA posizione a ogni tick finche'
         // restava valido - una sola strategia (MALAYSIAN_SNR_NXR) arrivava a
         // 17.218 aperture nel file osservato. Le posizioni accumulate,
         // correlate sullo stesso simbolo, facevano scattare in continuazione
         // NXS_Prot_CheckESL() (equity flottante <= -5% saldo, chiude TUTTE le
         // posizioni) - il vero motivo per cui quasi nessun trade arrivava mai
         // a vedere il proprio TP (1 "tp" su quasi 4000 chiusure nel file
         // controllato), non il cap di durata gia' corretto in precedenza.
         if(NXS_StrategyHasOpenPos(s.stratName)) continue;
         if(s.slPrice <= 0 || s.tpPrice <= 0) continue;                 // serve SL/TP valido
         // Contesto del segnale: tier (0=local..3=D1) e tipo (Cont/Rev) -> visibile nel trade
         int ddir  = (s.dir == DIR_BUY) ? +1 : -1;
         int dtier = _nxs_inst_tier(ddir);
         int dsetup= _nxs_inst_setupType(ddir);
         string dctx = StringFormat("T%d%s", dtier, (dsetup == NXS_SETUP_REVERSAL ? "R" : "C"));
         double refP = (s.dir == DIR_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                                          : SymbolInfoDouble(g_sym, SYMBOL_BID);
         double dsl = s.slPrice, dtp = s.tpPrice; string dpf = "";
         ENUM_ORDER_TYPE dot = (s.dir == DIR_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
         if(!NXS_PreFlight(dot, dlots, refP, dsl, dtp, dpf)) continue;   // sicurezza dura
         NXS_TradeSetMagic(InpMagic + MAGIC_CORE);
         // Comment: strategia resta il campo [1] (parsing sito invariato); il
         // contesto e' il campo [3] -> visibile in MT5 e sincronizzabile.
         string dcm = StringFormat("%s|%s|%.1f|%s", InpComment, s.stratName, s.score, dctx);
         bool dok = (s.dir == DIR_BUY) ? NXS_SafeBuy(dlots, g_sym, dsl, dtp, dcm)
                                       : NXS_SafeSell(dlots, g_sym, dsl, dtp, dcm);
         if(dok){
            openedNow++;
            NXS_StrategyRegisterTrade(s.stratName);
            // 16/07: mancava la chiamata a NXS_Stats_RecordExec in questo path -
            // "executed" restava a 0 anche qui (bug diverso ma imparentato a
            // quello gia' noto del path standard). wins/losses restano comunque
            // affidabili (letti dallo storico deal chiuso), ma ora anche
            // "executed"/exec_rate_pct sono corretti quando si usa questa
            // modalita' (es. lo sweep 1-37 in corso).
            double dSpread = (double)SymbolInfoInteger(g_sym, SYMBOL_SPREAD);
            NXS_Stats_RecordExec(s.stratName, s.score, dSpread);
            // 17/07: ticket=0/lots=0 hardcoded impedivano di collegare la riga
            // OPEN alla sua CLOSE nel CSV - cercato il ticket appena assegnato
            // (stesso comment, appena aperto) invece di scartarlo. resolved_tf
            // e' il TF che NXS_Protections.mqh usera' per scalare durata/vita
            // di QUESTA posizione - visibile subito nel CSV da oggi in poi.
            ulong dticket = 0;
            for(int pp = PositionsTotal() - 1; pp >= 0; pp--){
               ulong ptk = PositionGetTicket(pp);
               if(ptk == 0) continue;
               if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
               if(PositionGetString(POSITION_COMMENT) != dcm) continue;
               dticket = ptk; break;
            }
            string dResolvedTF = EnumToString(NXS_Profile_TF(s.stratName));
            NXS_LogTradeCSV("OPEN", dticket, s.stratName, refP, dlots, dsl, dtp, s.score,
                            s.reason + "|" + dctx, 0, 0, dResolvedTF);
            PrintFormat("[NEXUS DATA] OPEN %s %s %s lots=%.2f score=%.1f",
                        NXS_DirName(s.dir), s.stratName, dctx, dlots, s.score);
         }
      }
      if(openedNow > 0) g_lastTradeTime = TimeCurrent();
      return;   // in raccolta dati non si usa né best-per-bar né istituzionale
   }

   // === MODELLO ISTITUZIONALE (v2.1.0) ==============================
   // Sostituisce il best-per-bar: raggruppa i segnali per direzione in
   // un'unica decisione e apre 1 posizione con SL/TP scalati sul tier.
   // Gestione (BE/trail/grid/pyramid) gira già a inizio OnTick.
   if(InpUseInstitutionalCore){
      NXS_Context_Update(htf, sweep, amd);            // serve per il tier
      // Qualita' dei voti PRIMA del raggruppamento: pesa/scarta i segnali
      // in base al contesto (controtrend scartati, RR degeneri scartati) ->
      // la conviction sommata riflette la qualita', non solo il numero.
      NXS_ApplyContextQuality(all, n);
      SNXSDecision dec = NXS_Institutional_Decide(all, n);
      // 1 posizione per direzione: se esiste già, non riaprire (gli add di
      // grid/recovery su variazione di prezzo arrivano in Fase 3).
      if(dec.valid && NXS_Inst_OpenPositionsInDir(dec.dir) == 0
         && !NXS_Prot_EntryBlocked() && NXS_SpreadOK()){
         SNXSSignal isig; ZeroMemory(isig);
         isig.dir      = dec.dir;
         isig.score    = MathMin(100.0, dec.confidence);
         isig.strat    = STRAT_STRUCT_REACT;
         // Il nome del trade = la firma della collaborazione (quali strategie
         // erano concordi in quel momento) -> visibile nel comment e nel Journal.
         isig.stratName= dec.group;
         isig.entryRef = dec.entryRef;
         isig.slPrice  = dec.slPrice;
         isig.tpPrice  = dec.tpPrice;
         isig.sourceTF = dec.tierTF;
         isig.reason   = dec.reason;
         // v2.1.7: su un setup REVERSAL bypassa il gate exhaustion (un reversal
         // parte da un estremo; l'exhaustion serve a non inseguire le continuazioni).
         g_nxsBypassExhaustion = (dec.setupType == NXS_SETUP_REVERSAL);
         // Tag contesto nel comment: TF del tier + C/R -> es. "H4-R" visibile in MT5.
         g_nxsOpenCtxTag = NXS_Inst_CtxTag(dec);
         ENUM_NXS_OPEN_RC orc = NXS_OpenTrade(isig, InpMagic + MAGIC_CORE, 1.0);
         g_nxsBypassExhaustion = false;
         g_nxsOpenCtxTag = "";
         if(orc == OPEN_OK){
            // g_tradesToday/g_lastTradeTime già aggiornati dentro NXS_OpenTrade
            NXS_StrategyRegisterTrade(dec.topStrat);
            NXS_LogTradeCSV("OPEN", 0, dec.group, dec.entryRef,
                            0, dec.slPrice, dec.tpPrice, isig.score, dec.reason);
            PrintFormat("[NEXUS INST] OPEN %s", dec.reason);
         } else {
            // v2.1.7: registra il blocco del gruppo sul bucket giusto (non piu'
            // "PREFLIGHT ambiguous") cosi' il prossimo test dice PERCHE' non apre.
            ENUM_NXS_BLOCK blk = NXS_BlkFromFailure(g_nxsLastOpenFailure);
            NXS_Blk_Bump(blk);
            NXS_Stats_RecordBlock(dec.topStrat, (int)blk);
            PrintFormat("[NEXUS INST] open rc=%d blocco=%s (%s)",
                        (int)orc, g_nxsLastOpenFailure, dec.reason);
         }
      }
      return;   // il modello istituzionale sostituisce il best-per-bar
   }

   // === PROFILI PER-STRATEGIA (v2.3.0) — "COME NEL BACKTEST DEL SITO" ========
   // Ogni strategia apre in INDIPENDENZA col SUO profilo (SL/TP/HTF/rischio/TF),
   // senza i gate soft (MTF/velocity/exhaustion/score/confluence) e senza il
   // best-per-bar che apriva 1 sola op per barra. Restano solo: profilo
   // abilitato, gate TF (bypass in multi-TF), Setup Matrix (max per direzione),
   // scudo risk-of-ruin e sicurezza dura (preflight in NXS_OpenTrade).
   // NB: NIENTE grid/recovery — il backtest del sito non li usa (era la
   // martingala del core istituzionale, spenta apposta).
   if(InpUseStrategyProfiles){
      bool anyOpened = false;
      for(int i = 0; i < n; i++){
         SNXSSignal s = all[i];
         if(s.dir == DIR_NONE) continue;
         // 04/09 - filtro sessione minimo per il percorso "profili per-strategia"
         // (quello usato da tutti i test di oggi): il sistema di soglie per
         // sessione (InpXScoreMin) appartiene al percorso istituzionale legacy
         // ed e' bypassato di proposito qui (vedi commento sopra) - questo e'
         // un gate diretto, non collegato a quel sistema. Default false =
         // comportamento invariato.
         if(InpProfileOverlapOnly && g_session != SESS_OVERLAP) continue;
         // una posizione per strategia alla volta (come il backtest del sito):
         // niente nuova entrata se la strategia ha gia' un trade aperto.
         if(NXS_StrategyHasOpenPos(s.stratName)) continue;
         // una decisione per barra del TF della strategia: niente segnali D1
         // duplicati a ogni barra M15.
         ENUM_TIMEFRAMES sTF = NXS_Profile_TF(s.stratName);
         if(sTF == PERIOD_CURRENT) sTF = (ENUM_TIMEFRAMES)InpTFEntry;
         datetime sBar = iTime(g_sym, sTF, 0);
         if(sBar > 0 && NXS_GetLastTfBar(s.stratName) == sBar) continue;
         if(s.slPrice <= 0 || s.tpPrice <= 0) NXS_DefaultSLTP(s);   // assicura SL/TP del profilo
         if(s.slPrice <= 0 || s.tpPrice <= 0) continue;
         g_nxsOpenCtxTag = EnumToString(sTF);  // TF della strategia nel comment
         ENUM_NXS_OPEN_RC orc = NXS_OpenTrade(s, InpMagic + MAGIC_CORE, 1.0);
         g_nxsOpenCtxTag = "";
         if(orc == OPEN_OK){
            anyOpened = true;
            NXS_SetLastTfBar(s.stratName, sBar);   // marca la barra TF come gia' agita
            NXS_StrategyRegisterTrade(s.stratName);
            NXS_LogTradeCSV("OPEN", 0, s.stratName, s.entryRef, 0,
                            s.slPrice, s.tpPrice, s.score, s.reason);
         } else {
            ENUM_NXS_BLOCK blk = NXS_BlkFromFailure(g_nxsLastOpenFailure);
            NXS_Blk_Bump(blk);
            NXS_Stats_RecordBlock(s.stratName, (int)blk);
         }
      }
      if(anyOpened) g_lastTradeTime = TimeCurrent();
      return;   // percorso profili: sostituisce best-per-bar e istituzionale
   }

      bool opened = false;
      ENUM_NXS_EXEC_RC lastRc = EXEC_FAIL_NO_DIR;
      for(int i = 0; i < n; i++){
         SNXSSignal sig = all[i];
         if(sig.dir == DIR_NONE) continue;
         if(NXS_StrategyOnCooldown(sig.stratName)){
            NXS_Blk_Bump(BLK_COOLDOWN);
            NXS_Stats_RecordBlock(sig.stratName, (int)BLK_COOLDOWN);
            continue;
         }
         if(NXS_StrategyOnDirCooldown(sig.stratName)){
            NXS_Blk_Bump(BLK_COOLDOWN);
            NXS_Stats_RecordBlock(sig.stratName, (int)BLK_COOLDOWN);
            continue;
         }

         string mtfReason, velReason;
         double baseScore = sig.score;
         double mtfFactor = NXS_MTF_FamilyFactor((sig.dir == DIR_BUY ? +1 : -1),
                                                 sig.stratName, mtfReason);
         if(mtfFactor <= 0.0){
            NXS_Blk_Bump(BLK_MTF);
            NXS_Stats_RecordBlock(sig.stratName, (int)BLK_MTF);
            NXS_Blk_LogDecision(sig.stratName, NXS_DirName(sig.dir),
                                baseScore, 0, 0, 0,
                                mtfReason, "MTF blocked");
            NXS_Shadow_Record(sig, 0.0, 0.0, "MTF", "", mtfReason,
                              NXS_HTFName(htf.bias), NXS_VelName(vel.state),
                              (sweep.confirmed ? "CONFIRMED" : "NONE"),
                              NXS_SessionName(g_session),
                              EnumToString(NXS_DetectRegime()));
            if(!InpTryNextSignalIfBlocked) return;
            continue;
         }
         double penalizedScore = baseScore * mtfFactor;

         double velFactor = NXS_Vel_FamilyFactor(sig.dir, vel, sig.stratName, velReason);
         if(velFactor <= 0.0){
            NXS_Blk_Bump(BLK_VELOCITY);
            NXS_Stats_RecordBlock(sig.stratName, (int)BLK_VELOCITY);
            NXS_Blk_LogDecision(sig.stratName, NXS_DirName(sig.dir),
                                baseScore, penalizedScore, 0, 0,
                                mtfReason + "|" + velReason, "VEL blocked");
            NXS_Shadow_Record(sig, penalizedScore, 0.0, "VELOCITY", "MTF",
                              mtfReason + "|" + velReason,
                              NXS_HTFName(htf.bias), NXS_VelName(vel.state),
                              (sweep.confirmed ? "CONFIRMED" : "NONE"),
                              NXS_SessionName(g_session),
                              EnumToString(NXS_DetectRegime()));
            if(!InpTryNextSignalIfBlocked) return;
            continue;
         }
         penalizedScore *= velFactor;
         sig.score = penalizedScore;

         // v2.0.13 — Chain continuation: se è continuazione di trade vincente, applica bonus score + lot mult
         double chainLotMult = 1.0;
         string chainReason  = "";
         bool isContinuation = NXS_Chain_IsContinuation(sig.stratName,
                                                        (sig.dir == DIR_BUY ? +1 : -1),
                                                        chainLotMult, chainReason);
         g_chainPendingLotMult = isContinuation ? chainLotMult : 1.0;
         if(isContinuation){
            sig.score = MathMin(100.0, sig.score + 8.0); // bonus continuazione
            sig.reason = sig.reason + "|" + chainReason;
            PrintFormat("[NEXUS CHAIN] %s lotMult=%.2f score+8 → %.1f",
                        chainReason, chainLotMult, sig.score);
         }

         double finalScore = 0, thresh = 0;
         ENUM_NXS_EXEC_RC rc = NXS_TryExecuteRC(sig, amd, sweep, htf, vel, finalScore, thresh);
         lastRc = rc;
         string gates = mtfReason + "|" + velReason;

         if(rc == EXEC_OK){
            if(isContinuation) NXS_Chain_OnContinuationOpen();
            NXS_StrategyRegisterTrade(sig.stratName);
            NXS_StrategyRegisterDirTrade(sig.stratName, (sig.dir == DIR_BUY ? +1 : -1));
            double curSpread = (double)SymbolInfoInteger(g_sym, SYMBOL_SPREAD);
            NXS_Stats_RecordScoreSample(sig.stratName, baseScore, finalScore, thresh);
            NXS_Stats_RecordExec(sig.stratName, finalScore, curSpread);
            NXS_LogTradeCSV("OPEN", 0, sig.stratName, sig.entryRef,
                            0, sig.slPrice, sig.tpPrice, sig.score, sig.reason);
            NXS_Blk_LogDecision(sig.stratName, NXS_DirName(sig.dir),
                                baseScore, penalizedScore, finalScore, thresh,
                                gates, "EXEC_OK");
            opened = true;
            break;
         }
         // map rc → counter
         ENUM_NXS_BLOCK blkCode = BLK_PREFLIGHT;
         if(rc == EXEC_FAIL_PROTECTIONS){ blkCode = BLK_PROTECTIONS; gates += "|PROT"; }
         else if(rc == EXEC_FAIL_NEWS)  { blkCode = BLK_NEWS;        gates += "|NEWS"; }
         else if(rc == EXEC_FAIL_HTF)   { blkCode = BLK_HTF;         gates += "|HTF";  }
         else if(rc == EXEC_FAIL_VELOCITY){ blkCode = BLK_VELOCITY;  gates += "|VEL2"; }
         else if(rc == EXEC_FAIL_SCORE_BELOW){ blkCode = BLK_SCORE_BELOW; gates += "|SCORE"; }
         else if(rc == EXEC_FAIL_INVALID_STOPS){ blkCode = BLK_PREFLIGHT; gates += "|BAD_STOPS"; }
         else if(rc == EXEC_FAIL_INVALID_VOLUME){ blkCode = BLK_PREFLIGHT; gates += "|BAD_VOLUME"; }
         else if(rc == EXEC_FAIL_PREFLIGHT){ blkCode = BLK_PREFLIGHT; gates += "|PRE:" + g_nxsLastOpenFailure; }
         else if(rc == EXEC_FAIL_ORDER_SEND ){ blkCode = BLK_SEND_FAILED; gates += "|SEND:" + g_nxsLastOpenFailure; }
         else                              { blkCode = BLK_PREFLIGHT;    gates += "|PRE";  }
         NXS_Blk_Bump(blkCode);
         NXS_Stats_RecordBlock(sig.stratName, (int)blkCode);
         NXS_Stats_RecordScoreSample(sig.stratName, baseScore, finalScore, thresh);
         if(rc == EXEC_FAIL_INVALID_STOPS){
            NXS_Stats_RecordSLTPInvalid(sig.stratName);
         }

         NXS_Blk_LogDecision(sig.stratName, NXS_DirName(sig.dir),
                             baseScore, penalizedScore, finalScore, thresh,
                             gates, "exec_rc=" + IntegerToString((int)rc));
         // v2.0.8 shadow record for any non-EXEC_OK outcome
         NXS_Shadow_Record(sig, finalScore, thresh,
                           EnumToString(blkCode), "",
                           "exec_rc=" + IntegerToString((int)rc),
                           NXS_HTFName(htf.bias), NXS_VelName(vel.state),
                           (sweep.confirmed ? "CONFIRMED" : "NONE"),
                           NXS_SessionName(g_session),
                           EnumToString(NXS_DetectRegime()));
         if(!InpTryNextSignalIfBlocked) return;
      }
      // AUDITPATCH: NO_SIGNAL means exactly that. Signals rejected by score/MTF/etc.
      // already have their own counters and must not be double-counted as absent.
      if(!opened && directionalSignals == 0) NXS_Blk_Bump(BLK_NO_SIGNAL);
      // v2.0.8c — diagnose HTF blockage: reaction detected but no strategy emitted
      // a same-direction signal → strong indicator that internal HTF gates inside
      // strategies are vetoing all 36 trigger sources at once.
      if(directionalSignals == 0 && g_reaction.detected){
         int reactDir = g_reaction.direction;
         int htfBias  = htf.bias;   // +1 bull, -1 bear, 0 neutral
         bool counter = (reactDir == +1 && htfBias == -1) || (reactDir == -1 && htfBias == +1);
         if(counter){
            NXS_Blk_Bump(BLK_HTF);
            PrintFormat("[NEXUS BLOCK] reaction=%s qual=%.0f vs HTF=%s → all strategies "
                        "self-vetoed (counter-trend). Enable Counter-HTF Soft or lower "
                        "%s ScoreMin to allow.",
                        (reactDir == +1 ? "BULL" : "BEAR"),
                        g_reaction.quality,
                        NXS_HTFName(htf.bias),
                        NXS_SessionName(g_session));
         }
      }
      NXS_Blk_MaybeReport();
      // v2.0.8 — Shadow logger tick (evaluate + export + push)
      NXS_Shadow_Tick();
}

//+------------------------------------------------------------------+
//| PR1 - pipeline di chiusura del TRADE LOGICO (exactly-once).       |
//| Prima girava per OGNI deal OUT: un trade chiuso in N parziali     |
//| produceva N "TRADE_CLOSED" (stats gonfiate, chain/notify/push     |
//| duplicati, PnL parziale spacciato per PnL del trade). Ora gira    |
//| UNA volta per position, con i valori AGGREGATI del ledger.        |
//+------------------------------------------------------------------+
// NXS-TX-003 — quali effetti di una chiusura sono RIGIOCABILI dopo un periodo
// offline, e quali no.
//
// Prima le chiusure trovate dal resync di boot venivano soltanto loggate: lo
// stato locale (streak di perdite, anti-revenge, catene, statistiche per
// strategia) restava fermo a prima del downtime, mentre il backend riceveva
// comunque i trade dalla history sync. I due lati divergevano in silenzio.
//
// Politica, ora esplicita:
//   RIGIOCABILI  — stato di protezione (streak/anti-revenge), statistiche per
//                  strategia, catene, riga CSV: descrivono FATTI accaduti e
//                  devono valere anche se l'EA non era in esecuzione;
//   NON RIGIOCABILI — notifiche (Telegram/push) e cooldown direzionali basati
//                  sul tempo: allertare ore dopo l'evento e' rumore, e un
//                  cooldown partito adesso per un SL di ieri bloccherebbe il
//                  trading per un motivo gia' esaurito.
void NXS_EA_OnLogicalClose(SNxsLedgerTrade &tc){
   // Protezioni loss-streak (anti-revenge, anti-bleed, streak sizing):
   // ESATTAMENTE una volta per trade logico, con il PnL AGGREGATO
   // (docs/architecture: "consecutive-loss protections run exactly once per
   // logical trade"). Prima un trade chiuso in 3 parziali in perdita contava
   // 3 perdite consecutive e poteva innescare anti-revenge da solo.
   NXS_OnTradeClosed(tc.pnl);
   // 30/08 - NXS_SLReclaim: se il trade e' uscito per stop nativo, arma
   // l'attesa di una chiusura M15 che riconquisti quel livello (vedi
   // NXS_SLReclaim.mqh). tc.close_reason viene dal ledger, "trigger
   // dell'ultimo OUT" - un pareggio/trailing/max-loss non e' uno stop
   // nativo in senso stretto, solo "sl" (il broker) lo e'.
   if(StringFind(tc.close_reason, "sl") == 0)
      NXS_SLReclaim_Arm(tc.vwap_out, (tc.side == "BUY") ? 1 : -1, tc.pnl);
   else
      NXS_SLReclaim_OnTradeClosed(tc.pnl);   // un TP o altra uscita in guadagno rompe comunque la catena
   // 12/08 — moltiplicatore da perdite consecutive PER-STRATEGIA: stesso
   // punto/stesso pnl AGGREGATO di NXS_OnTradeClosed sopra (esattamente una
   // volta per trade logico, non per deal parziale). No-op se
   // InpUseLossStreakScaling e' off. Vedi NXS_StreakRisk.mqh.
   NXS_StreakRisk_OnTradeClosed(tc.strategy, tc.pnl);

   string reason = tc.close_reason;
   if(reason == "unknown") reason = (tc.pnl >= 0) ? NXS_R_PROFIT : NXS_R_DD;

   // v2.0.33 — post-SL directional cooldown (invariato, ma ora scatta solo
   // quando il trade e' davvero finito in SL, non su un parziale qualunque).
   // NXS-TX-003: NON rigiocabile — il cooldown e' una finestra temporale che
   // per una chiusura offline e' gia' scaduta.
   if(reason == "sl" && !tc.from_boot)
      NXS_RegisterSLClose((tc.side == "BUY") ? DIR_BUY : DIR_SELL);

   double holdSec = (double)((long)tc.close_time - (long)tc.open_time);
   // AUD0-LEDGER-005: quando il rischio iniziale non e' ricostruibile la R non
   // esiste. Prima veniva forzata a +1/-1 e finiva comunque in statistiche e
   // ranking: expectancy e win rate in R misuravano un sistema inventato.
   bool   hasR    = NXS_Ledger_HasR(tc);
   double rMult   = hasR ? NXS_Ledger_RMultiple(tc) : 0.0;
   string tf      = EnumToString(NXS_Profile_TF(tc.strategy));
   if(!hasR)
      PrintFormat("[NEXUS LEDGER] pos %I64u (%s): rischio iniziale ignoto — "
                  "trade ESCLUSO dalle statistiche in R", tc.position_id, tc.strategy);

   // riga CLOSE unica: lots = volume totale entrato, pnl = realizzato totale,
   // prezzo = VWAP di uscita; i parziali hanno le loro righe PARTIAL.
   NXS_LogTradeCSV("CLOSE", tc.position_id, tc.strategy, tc.vwap_out, tc.vol_in,
                   0, 0, tc.pnl, reason, holdSec, rMult, tf);

   // v2.5.1 PR1: outcome stats registrato QUI (unico punto), non piu' un
   // outcome per ogni deal OUT dentro NXS_Stats_ProcessClosedTrades.
   if(hasR) NXS_Stats_RecordOutcome(tc.strategy, rMult, tc.score, holdSec);

   NXS_Prot_PushTradeReason(tc.position_id, tc.magic, tc.strategy, tc.side,
                            tc.vol_in, tc.vwap_in, tc.vwap_out, tc.pnl, reason,
                            tc.open_time, tc.close_time,
                            (tc.from_boot ? "resync" : "close"),
                            tc.partial_count, tc.vol_out);

   // v2.0.13 — hook chain
   int closeDir = (tc.side == "BUY") ? +1 : -1;
   NXS_Chain_OnTradeClose(tc.strategy, closeDir, tc.vwap_out, tc.pnl);

   // NXS-TX-003: non rigiocabile — nessuna notifica per chiusure avvenute
   // mentre l'EA era spento.
   if(!tc.from_boot) NXS_Notify_TradeClose(tc.strategy, tc.pnl, reason);
}

// Svuota la coda delle chiusure logiche (di norma 0 o 1 elemento).
void NXS_EA_DrainLedger(){
   SNxsLedgerTrade tc;
   while(NXS_Ledger_PopClosed(tc)){
      // NXS-TX-003: le chiusure di boot venivano SCARTATE qui, lasciando lo
      // stato locale (streak, statistiche, catene) fermo a prima del downtime
      // mentre il backend le riceveva comunque. Ora passano dallo stesso
      // gestore, che decide da solo quali effetti rigiocare.
      NXS_EA_OnLogicalClose(tc);
   }
}

void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& tradeReq,
                        const MqlTradeResult& tradeRes){
   // v2.0.9 Sprint 3 — event-driven fill capture (replaces polling)
   NXS_EA_OnTradeTx(trans);
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;

   // PR2 - Virtual SL: aggancio "dopo il fill reale". Filtra DEAL_ENTRY_IN
   // internamente, matcha l'intent pending per DEAL_ORDER e registra con
   // DEAL_POSITION_ID. No-op in modalita' OFF.
   NXS_EA_VirtSL_OnFill(trans.deal);

   // PR1 - tutto il ciclo di vita passa dal ledger: il deal fa ri-aggregare
   // la sua position e l'evento nasce dal DIFF di stato, quindi replay di
   // deal duplicati e disordine di consegna non producono mai doppi eventi.
   double realizedDelta = 0.0;
   int ev = NXS_Ledger_OnDeal(trans.deal, realizedDelta);
   if(ev == NXS_LEDGER_EV_NONE) return;

   // NB: NXS_OnTradeClosed (contatore perdite consecutive / anti-revenge /
   // streak sizing) NON viene piu' chiamato qui per ogni deal OUT: scatta
   // una sola volta per trade logico dentro NXS_EA_OnLogicalClose, col PnL
   // aggregato. I gate daily-DD non passano da qui (usano balance/equity).
   // realizedDelta resta per la riga CSV PARTIAL.

   if(ev == NXS_LEDGER_EV_PARTIAL && HistoryDealSelect(trans.deal)){
      // riga PARTIAL: pnl/lots del singolo deal, cosi' il CSV mostra ogni
      // uscita parziale senza mai contarla come trade chiuso.
      ulong  posId = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
      double dLots = HistoryDealGetDouble(trans.deal, DEAL_VOLUME);
      double dPx   = HistoryDealGetDouble(trans.deal, DEAL_PRICE);
      string dRsn  = _NXS_HistTrigger(HistoryDealGetInteger(trans.deal, DEAL_REASON));
      // NXS-TX-002: l'attribuzione del parziale nasceva dal parsing del
      // commento della posizione — testo che il broker puo' troncare o
      // riscrivere. Si consulta prima il registro degli intenti, che porta
      // l'identita' decisa all'esecuzione.
      string strat = "";
      SNxsIntent pIntent;
      if(NXS_Intent_ByPosition(posId, pIntent)) strat = pIntent.strategy;
      if(strat == ""){
         string cm = NXS_FindPositionOpenComment(posId, "");
         int p1 = StringFind(cm, "|");
         if(p1 >= 0){
            int p2 = StringFind(cm, "|", p1+1);
            strat = (p2 > p1) ? StringSubstr(cm, p1+1, p2-p1-1) : StringSubstr(cm, p1+1);
         }
      }
      NXS_LogTradeCSV("PARTIAL", posId, strat, dPx, dLots, 0, 0, realizedDelta,
                      dRsn, 0, 0, EnumToString(NXS_Profile_TF(strat)));
   }

   NXS_EA_DrainLedger();
}
//+------------------------------------------------------------------+
