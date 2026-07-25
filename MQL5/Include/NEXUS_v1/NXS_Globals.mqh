//+------------------------------------------------------------------+
//|  NXS_Globals.mqh - Globals, indicator handles, raw trade helpers  |
//|  NO dependency on <Trade\Trade.mqh> - uses only native MQL5 API.  |
//+------------------------------------------------------------------+
#ifndef __NXS_GLOBALS_MQH__
#define __NXS_GLOBALS_MQH__

// v2.0.36: single-strategy screening selector (see InpStrategySelector in
// NXS_Inputs.mqh for the index mapping). 0 = no override, everyone respects
// their own InpStrat_*/InpUseStrat_* toggle as before.
bool NXS_SelectorAllows(int idx){
   return (InpStrategySelector == 0 || InpStrategySelector == idx);
}

// ----- Trade state (replaces CTrade) -----
long                       g_tradeMagic   = 0;
ENUM_ORDER_TYPE_FILLING    g_tradeFilling = ORDER_FILLING_FOK;
uint                       g_tradeRetcode = 0;
// PR2: order ticket dell'ultimo OrderSend, stesso idioma di g_tradeRetcode.
// Necessario (non locale): res.order nasce dentro NXS_DoBuy/DoSell e non ha
// altro canale verso NXS_OpenTrade (SafeBuy/SafeSell ritornano solo bool) —
// serve per correlare l'intent pending del Virtual SL al fill (DEAL_ORDER).
ulong                      g_tradeOrderTicket = 0;

// AUD0-RAW-002 / NXS-RAW-002 — ESITO DI ESECUZIONE STRUTTURATO.
//
// Gli helper conservavano solo `res.order` in una singola variabile globale
// mutabile: niente deal, niente prezzo eseguito, niente volume, nessun modo di
// correlare richiesta e risposta. Con i retry o con due percorsi di ordine nello
// stesso tick, quella globale veniva sovrascritta e il Virtual SL correlava il
// fill SBAGLIATO.
//
// Ora ogni invio produce uno snapshot completo. Il chiamante lo copia subito
// dopo l'invio e lavora sulla propria copia, immune a sovrascritture successive.
struct SNXSExecResult {
   ulong    request_id;    // progressivo locale: correla richiesta e risposta
   ulong    order;
   ulong    deal;
   double   price;         // prezzo EFFETTIVAMENTE eseguito
   double   volume;        // volume effettivamente eseguito
   uint     retcode;
   string   symbol;
   string   comment;       // commento del broker sul risultato
   datetime sent_at;
   bool     done;          // true solo su TRADE_RETCODE_DONE
   bool     placed_only;   // accettato ma non ancora eseguito
};

SNXSExecResult g_lastExec;
ulong          g_execRequestSeq = 0;

void _NXS_CaptureExec(const MqlTradeRequest &req, const MqlTradeResult &res, bool sent){
   g_execRequestSeq++;
   g_lastExec.request_id  = g_execRequestSeq;
   g_lastExec.order       = res.order;
   g_lastExec.deal        = res.deal;
   g_lastExec.price       = res.price;
   g_lastExec.volume      = res.volume;
   g_lastExec.retcode     = res.retcode;
   g_lastExec.symbol      = req.symbol;
   g_lastExec.comment     = res.comment;
   g_lastExec.sent_at     = TimeCurrent();
   g_lastExec.done        = (sent && res.retcode == TRADE_RETCODE_DONE);
   g_lastExec.placed_only = (sent && res.retcode == TRADE_RETCODE_PLACED);
   g_tradeRetcode         = res.retcode;
   g_tradeOrderTicket     = res.order;
}

//: Copia immutabile dell'ultimo esito. Da chiamare SUBITO dopo l'invio.
void NXS_LastExec(SNXSExecResult &out){ out = g_lastExec; }

// NXS-RAW-001 — `TRADE_RETCODE_PLACED` non e' un'esecuzione: e' un'accettazione.
// Tutti gli helper lo trattavano come successo, quindi aperture, chiusure,
// parziali e modifiche potevano essere contate come completate mentre il broker
// non aveva ancora nulla di definitivo.
//
// Il criterio e' ora esplicito: DONE = eseguito; PLACED = accettato, da
// confermare dallo stato reale. Gli helper che possono verificare la
// post-condizione (chiusura, modifica) lo fanno; per l'apertura il ledger e
// OnTradeTransaction restano l'autorita', e il PLACED viene dichiarato nel log.
bool _NXS_ExecAccepted(bool sent, uint rc, string what){
   if(sent && rc == TRADE_RETCODE_DONE) return true;
   if(sent && rc == TRADE_RETCODE_PLACED){
      PrintFormat("[NEXUS EXEC] %s: il broker ha risposto PLACED (accettato, non "
                  "ancora eseguito): l'esito definitivo arrivera' dai deal", what);
      return true;
   }
   return false;
}

// ----- Symbol / context -----
string  g_sym;
double  g_point;
int     g_digits;

// Indicator handles
int g_hADX = INVALID_HANDLE;
int g_hRSI = INVALID_HANDLE;
int g_hBB  = INVALID_HANDLE;
int g_hMACD= INVALID_HANDLE;
int g_hSAR = INVALID_HANDLE;
int g_hATR = INVALID_HANDLE;
int g_hEMA200 = INVALID_HANDLE;
int g_hEMA9   = INVALID_HANDLE;
int g_hEMA21  = INVALID_HANDLE;
int g_hEMA_HTF= INVALID_HANDLE;
int g_hEMA_MTF= INVALID_HANDLE;
int g_hICHI   = INVALID_HANDLE;

// v2.3.0 — TF su cui girano ORA le strategie (single-chart multi-TF). Resta
// InpTFEntry in modalita' normale; nei passaggi multi-TF vale il TF del passaggio.
ENUM_TIMEFRAMES g_activeTF = PERIOD_CURRENT;
// TF effettivo per detector/struttura: g_activeTF oppure InpTFEntry di default.
ENUM_TIMEFRAMES NXS_EffTF(){
   return (g_activeTF == PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)InpTFEntry : g_activeTF;
}

// Cached values (closed bar = 1)
double g_adx, g_adxPlus, g_adxMinus;
double g_rsi;
double g_bbUpper, g_bbLower, g_bbMid;
double g_macd, g_macdSig;
double g_sar;
double g_atr;
double g_atrAvg;  // rolling avg of ATR (for adaptive SL)
double g_ema200, g_ema9, g_ema21;
double g_emaHTF, g_emaMTF;
double g_ichiTenkan, g_ichiKijun, g_ichiSpanA, g_ichiSpanB;

// State
ENUM_NXS_REGIME g_regime  = REGIME_UNKNOWN;
ENUM_NXS_SESSION g_session= SESS_NONE;
bool   g_eaPaused         = false;
int    g_tradesToday      = 0;
int    g_consecLosses     = 0;
// v2.2.1 — sizing account-level adattivo: streak dedicati (non toccati da
// anti-revenge) e moltiplicatore lotto che sale sulle vincite / scende sulle
// perdite, dentro [floor, cap].
int    g_streakWins       = 0;
int    g_streakLosses     = 0;
double g_streakLotMult    = 1.0;
// v2.2.6 - scudo risk-of-ruin: giorno per cui il trading e' congelato.
datetime g_ruinFrozenDay  = 0;

// ---- SAFETY STATE PERSISTENTE ----
// AUD0-STATE-004 / AUD0-RS-007 / AUD0-PROT-004: queste variabili vivono qui,
// e non nei rispettivi moduli, perché NXS_State.mqh (che le serializza) è
// incluso PRIMA di NXS_RiskShield.mqh e NXS_Protections.mqh. Centralizzarle
// rende la persistenza indipendente dall'ordine di include (AUD0-MQL-001).
bool     g_eslHit              = false;
bool     g_dptHit              = false;
bool     g_pausedUntilNextOpen = false;
bool     g_autoClosePending    = false;
// Flatten d'emergenza non completato: resta esposizione da chiudere.
bool     g_flattenPending      = false;
string   g_flattenReason       = "";
int      g_flattenAttempts     = 0;
datetime g_flattenSince        = 0;
// Equity breaker del RiskShield.
datetime g_NXSrsBreakerUntil   = 0;
// AUD0-WEB-008: istante dell'ultimo evento di protezione scattato. Serve al
// raffreddamento che impedisce di disarmare una protezione da remoto nei
// minuti immediatamente successivi all'evento che l'ha fatta scattare.
datetime g_lastProtectionEvent = 0;
// AUD0-MQL-010: salute della lettura indicatori. Vive qui, e non nell'EA,
// perche' NXS_WebBridge.mqh la pubblica nella telemetria ed e' incluso PRIMA
// del corpo dell'EA (l'inclusione in MQL5 e' testuale: l'ordine conta).
int      g_indFailStreak      = 0;
datetime g_indLastFailLog     = 0;
bool     g_indDegraded        = false;
bool NXS_IndicatorsDegraded(){ return g_indDegraded; }
double   g_NXSrsLastSharpe     = 0.0;
datetime g_dayStart       = 0;
double g_balanceDayStart  = 0;
// AUD0-RISK-005: equity di inizio giornata, la baseline corretta del drawdown
// giornaliero (il bilancio ignora il flottante ereditato dalla notte).
double g_equityDayStart   = 0;
datetime g_lastTradeTime  = 0;
datetime g_antiRevengeUntil = 0;
datetime g_lastPushTime   = 0;
datetime g_lastPollTime   = 0;
datetime g_lastBarTime    = 0;
datetime g_lastH1BarTime  = 0;
datetime g_lastHistSyncTime = 0;
// Anti-bleed state
int      g_skipNextSignals  = 0;

// Cached analysis state (kept fresh by OnTick, reused by OnTimer push)
struct SNXSCachedState {
   bool   ready;
   ENUM_NXS_HTF htfBias;
   double htfConf;
   bool   htfRev;
   ENUM_NXS_VEL velState;
   ENUM_NXS_AMD amdPhase;
   double amdHi, amdLo;
   ENUM_NXS_DIR sweepDir;
   bool   sweepConf;
};
SNXSCachedState g_cached;

// ----- Magic helpers -----
bool IsNexusMagic(long m){
   return (m >= InpMagic && m <= InpMagic + MAGIC_SPLIT + 100);
}
bool IsCoreMagic(long m){ return m == InpMagic + MAGIC_CORE; }
bool IsGridMagic(long m){ return m >= InpMagic + MAGIC_GRID    && m < InpMagic + MAGIC_PYRAMID; }
bool IsPyrMagic(long m) { return m >= InpMagic + MAGIC_PYRAMID && m < InpMagic + MAGIC_SPLIT;   }

// ----- JSON string escaping (shared by NXS_WebBridge.mqh + NXS_Protections.mqh) -----
string _JsonEsc(string s){
   string r = s;
   StringReplace(r, "\\", "\\\\");
   StringReplace(r, "\"", "\\\"");
   return r;
}

// ----- ISO-8601 time formatting (shared by WebBridge + Protections + HistorySync) -----
// MT5's TimeToString() emits "YYYY.MM.DD HH:MM:SS", which JS's Date() parser
// does not reliably accept and renders as "Invalid Date" in the dashboard.
string NXS_IsoTime(datetime t){
   if(t <= 0) return "";
   MqlDateTime mt; TimeToStruct(t, mt);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02d",
                       mt.year, mt.mon, mt.day, mt.hour, mt.min, mt.sec);
}

double NormPrice(double p){ return NormalizeDouble(p, g_digits); }

// ----- Raw trade helpers (replace CTrade) -----
void NXS_TradeSetMagic(long m){ g_tradeMagic = m; }

// AUD0-RAW-004: `g_tradeFilling` era inizializzato una sola volta per il
// simbolo del grafico, ma le chiusure ricevono posizioni il cui simbolo si
// legge dal ticket. In operazioni multi-simbolo la modalità di riempimento
// poteva non essere supportata dal simbolo effettivo della richiesta.
// La modalità va risolta PER RICHIESTA, immediatamente prima dell'invio.
ENUM_ORDER_TYPE_FILLING NXS_FillingForSymbol(string sym){
   long mode = (long)SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);
   if((mode & SYMBOL_FILLING_FOK) != 0)      return ORDER_FILLING_FOK;
   if((mode & SYMBOL_FILLING_IOC) != 0)      return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
}

void NXS_TradeSetFillingBySymbol(string sym){
   g_tradeFilling = NXS_FillingForSymbol(sym);
}

// AUD0-RAW-003: `req.deviation = 30` era fisso per ogni strumento. 30 point
// hanno un significato economico completamente diverso su EURUSD, XAUUSD e
// BTCUSD. Si deriva dallo spread corrente del simbolo, con un tetto rigido.
ulong NXS_DeviationForSymbol(string sym){
   long spread = (long)SymbolInfoInteger(sym, SYMBOL_SPREAD);
   if(spread <= 0) return 30;
   long dev = spread * 3;
   if(dev < 10)   dev = 10;
   if(dev > 300)  dev = 300;
   return (ulong)dev;
}

bool NXS_DoBuy(double volume, string sym, double sl, double tp, string comment){
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action      = TRADE_ACTION_DEAL;
   req.symbol      = sym;
   req.volume      = volume;
   req.type        = ORDER_TYPE_BUY;
   req.price       = SymbolInfoDouble(sym, SYMBOL_ASK);
   req.sl          = sl;
   req.tp          = tp;
   req.deviation   = NXS_DeviationForSymbol(sym);
   req.magic       = g_tradeMagic;
   req.comment     = comment;
   req.type_filling= NXS_FillingForSymbol(sym);
   bool ok = OrderSend(req, res);
   _NXS_CaptureExec(req, res, ok);
   return _NXS_ExecAccepted(ok, res.retcode, "apertura " + sym);
}

bool NXS_DoSell(double volume, string sym, double sl, double tp, string comment){
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action      = TRADE_ACTION_DEAL;
   req.symbol      = sym;
   req.volume      = volume;
   req.type        = ORDER_TYPE_SELL;
   req.price       = SymbolInfoDouble(sym, SYMBOL_BID);
   req.sl          = sl;
   req.tp          = tp;
   req.deviation   = NXS_DeviationForSymbol(sym);
   req.magic       = g_tradeMagic;
   req.comment     = comment;
   req.type_filling= NXS_FillingForSymbol(sym);
   bool ok = OrderSend(req, res);
   _NXS_CaptureExec(req, res, ok);
   return _NXS_ExecAccepted(ok, res.retcode, "apertura " + sym);
}

bool NXS_DoClose(ulong ticket){
   if(!PositionSelectByTicket(ticket)) return false;
   string sym = PositionGetString(POSITION_SYMBOL);
   double vol = PositionGetDouble(POSITION_VOLUME);
   long   ptype = PositionGetInteger(POSITION_TYPE);
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action      = TRADE_ACTION_DEAL;
   req.position    = ticket;
   req.symbol      = sym;
   req.volume      = vol;
   req.deviation   = NXS_DeviationForSymbol(sym);
   req.magic       = (long)PositionGetInteger(POSITION_MAGIC);
   req.type_filling= NXS_FillingForSymbol(sym);
   if(ptype == POSITION_TYPE_BUY){
      req.type  = ORDER_TYPE_SELL;
      req.price = SymbolInfoDouble(sym, SYMBOL_BID);
   } else {
      req.type  = ORDER_TYPE_BUY;
      req.price = SymbolInfoDouble(sym, SYMBOL_ASK);
   }
   bool ok = OrderSend(req, res);
   _NXS_CaptureExec(req, res, ok);
   if(!_NXS_ExecAccepted(ok, res.retcode, "chiusura " + sym)) return false;
   // NXS-RAW-001: post-condizione. Su PLACED la position puo' essere ancora
   // aperta: si verifica lo stato reale invece di dichiarare la chiusura fatta.
   if(res.retcode == TRADE_RETCODE_PLACED && PositionSelectByTicket(ticket)){
      PrintFormat("[NEXUS EXEC] chiusura %I64u accettata ma la posizione risulta "
                  "ancora aperta: NON dichiarata chiusa", ticket);
      return false;
   }
   return true;
}

bool NXS_DoClosePartial(ulong ticket, double volume){
   if(!PositionSelectByTicket(ticket)) return false;
   string sym = PositionGetString(POSITION_SYMBOL);
   long   ptype = PositionGetInteger(POSITION_TYPE);

   // AUD0-RAW-005: il volume del chiamante veniva inviato senza alcuna
   // validazione locale contro volume corrente, minimo, step e residuo.
   // Un valore non valido produceva un rifiuto del broker (o, peggio, un
   // residuo non tradabile) invece di un errore chiaro lato EA.
   double curVol = PositionGetDouble(POSITION_VOLUME);
   double vmin   = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double vstep  = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   if(vstep <= 0) vstep = 0.01;
   volume = MathFloor(volume / vstep) * vstep;
   if(volume <= 0 || volume > curVol + 1e-9){
      PrintFormat("[NEXUS EXEC] partial close rifiutato: volume %.4f non valido "
                  "(posizione %.4f) ticket=%I64u", volume, curVol, ticket);
      return false;
   }
   double residual = curVol - volume;
   // Il residuo deve essere zero (chiusura totale) oppure ancora tradabile.
   if(residual > 1e-9 && residual < vmin - 1e-9){
      PrintFormat("[NEXUS EXEC] partial close rifiutato: residuo %.4f sotto il "
                  "minimo broker %.4f ticket=%I64u", residual, vmin, ticket);
      return false;
   }

   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action      = TRADE_ACTION_DEAL;
   req.position    = ticket;
   req.symbol      = sym;
   req.volume      = volume;
   req.deviation   = NXS_DeviationForSymbol(sym);
   req.magic       = (long)PositionGetInteger(POSITION_MAGIC);
   req.type_filling= NXS_FillingForSymbol(sym);
   if(ptype == POSITION_TYPE_BUY){
      req.type  = ORDER_TYPE_SELL;
      req.price = SymbolInfoDouble(sym, SYMBOL_BID);
   } else {
      req.type  = ORDER_TYPE_BUY;
      req.price = SymbolInfoDouble(sym, SYMBOL_ASK);
   }
   bool ok = OrderSend(req, res);
   _NXS_CaptureExec(req, res, ok);
   return _NXS_ExecAccepted(ok, res.retcode, "chiusura parziale " + sym);
}

bool NXS_DoModify(ulong ticket, double sl, double tp){
   if(!PositionSelectByTicket(ticket)) return false;
   string sym = PositionGetString(POSITION_SYMBOL);
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action   = TRADE_ACTION_SLTP;
   req.position = ticket;
   req.symbol   = sym;
   req.sl       = sl;
   req.tp       = tp;
   bool ok = OrderSend(req, res);
   _NXS_CaptureExec(req, res, ok);
   if(!_NXS_ExecAccepted(ok, res.retcode, "modifica SL/TP " + sym)) return false;

   // AUD0-RAW-006 — VERIFICA DELLA POST-CONDIZIONE.
   //
   // L'helper dichiarava successo in base al solo esito dell'invio. Su una
   // modifica di stop questo e' un difetto di protezione: il codice chiamante
   // (breakeven, trailing, riparazione dello stop) crede che la posizione sia
   // protetta al nuovo livello, mentre il broker puo' aver applicato un valore
   // diverso — o nessuno. Qui si rilegge lo stato reale.
   if(!PositionSelectByTicket(ticket)){
      PrintFormat("[NEXUS EXEC] modifica %I64u: posizione non piu' selezionabile, "
                  "stop NON confermato", ticket);
      return false;
   }
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   double tol   = (point > 0 ? point : 1e-8) * 2.0;
   double curSL = PositionGetDouble(POSITION_SL);
   double curTP = PositionGetDouble(POSITION_TP);
   if(sl > 0 && MathAbs(curSL - sl) > tol){
      PrintFormat("[NEXUS EXEC][ALERT] modifica %I64u: SL richiesto %.5f ma la "
                  "posizione riporta %.5f — protezione NON confermata",
                  ticket, sl, curSL);
      return false;
   }
   if(tp > 0 && MathAbs(curTP - tp) > tol){
      PrintFormat("[NEXUS EXEC] modifica %I64u: TP richiesto %.5f ma la posizione "
                  "riporta %.5f", ticket, tp, curTP);
      return false;
   }
   return true;
}

uint NXS_TradeRetcode(){ return g_tradeRetcode; }
ulong NXS_TradeOrderTicket(){ return g_tradeOrderTicket; }   // PR2 (Virtual SL)

// Looks up a closed position's opening-deal time via its position id. Needed by
// OnTradeTransaction, which fires after the position is already gone from
// PositionSelect*, so POSITION_TIME can no longer be read directly there.
datetime NXS_FindPositionOpenTime(ulong positionId, datetime fallback){
   if(!HistorySelectByPosition(positionId)) return fallback;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++){
      ulong dt = HistoryDealGetTicket(i);
      if(dt == 0) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(dt, DEAL_ENTRY) == DEAL_ENTRY_IN)
         return (datetime)HistoryDealGetInteger(dt, DEAL_TIME);
   }
   return fallback;
}

// Looks up a closed position's OPENING-deal comment via its position id, so
// the strategy tag ("prefix|STRAT|score", stamped by NXS_OpenTrade) can be
// recovered even when the broker blanks/overwrites the CLOSING deal's own
// comment on SL/TP/stop-out fills (the same reason NXS_FindPositionOpenTime
// exists — see OnTradeTransaction).
string NXS_FindPositionOpenComment(ulong positionId, string fallback){
   if(!HistorySelectByPosition(positionId)) return fallback;
   int total = HistoryDealsTotal();
   for(int i = 0; i < total; i++){
      ulong dt = HistoryDealGetTicket(i);
      if(dt == 0) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(dt, DEAL_ENTRY) == DEAL_ENTRY_IN)
         return HistoryDealGetString(dt, DEAL_COMMENT);
   }
   return fallback;
}

// ----- Position helpers -----
int NXS_CountPositions(){
   int n = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      n++;
   }
   return n;
}

double NXS_FloatingPnL(){
   double s = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      s += PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   }
   return s;
}

// v2.0.30: symbol-aware exposure cap. A flat lot count means very different
// notional risk on BTCUSD vs GOLD given their contract sizes, so this picks
// a per-symbol override (InpMaxDirExposureLots_BTC/_GOLD) when one is set
// (>0) and the chart symbol matches by substring, else falls back to the
// generic InpMaxDirExposureLots.
double NXS_EffectiveMaxDirExposureLots(){
   if(StringFind(g_sym, "BTC") >= 0 && InpMaxDirExposureLots_BTC > 0)
      return InpMaxDirExposureLots_BTC;
   if((StringFind(g_sym, "XAU") >= 0 || StringFind(g_sym, "GOLD") >= 0) && InpMaxDirExposureLots_GOLD > 0)
      return InpMaxDirExposureLots_GOLD;
   return InpMaxDirExposureLots;
}

// Sum of lots currently open in one direction (core + grid/pyramid/split, any
// NEXUS magic) — used by the v2.0.26 total-exposure cap.
double NXS_DirExposureLots(ENUM_NXS_DIR dir){
   double sum = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      long ptype = PositionGetInteger(POSITION_TYPE);
      bool sameDir = (dir == DIR_BUY  && ptype == POSITION_TYPE_BUY) ||
                     (dir == DIR_SELL && ptype == POSITION_TYPE_SELL);
      if(sameDir) sum += PositionGetDouble(POSITION_VOLUME);
   }
   return sum;
}

// ----- v2.0.26 — new-entry-per-bar/direction cap -----
// Shared by NXS_OpenTrade (classic path) and NXR_OpenTrade (NXR path, which
// InpNXR_Enable routes almost all live signals through) so a confluence of
// several strategies/triggers on the same bar can only open ONE fresh
// position per direction — extra agreeing signals still count toward
// confluence scoring, they just can't each open their own position.
// Grid/Pyramid/Split add-ons bypass this entirely: they call NXS_DoBuy/
// NXS_DoSell directly, never NXS_OpenTrade/NXR_OpenTrade.
datetime g_barDirCapBarTime     = 0;
int      g_newTradesThisBarBuy  = 0;
int      g_newTradesThisBarSell = 0;

void NXS_BarDirCapRollover(){
   datetime bt = iTime(g_sym, InpTFEntry, 0);
   if(bt != g_barDirCapBarTime){
      g_barDirCapBarTime     = bt;
      g_newTradesThisBarBuy  = 0;
      g_newTradesThisBarSell = 0;
   }
}

bool NXS_BarDirCapAllows(ENUM_NXS_DIR dir){
   NXS_BarDirCapRollover();
   int count = (dir == DIR_BUY) ? g_newTradesThisBarBuy : g_newTradesThisBarSell;
   return count < InpMaxNewTradesPerBarDir;
}

void NXS_BarDirCapRegisterOpen(ENUM_NXS_DIR dir){
   NXS_BarDirCapRollover();
   if(dir == DIR_BUY) g_newTradesThisBarBuy++;
   else if(dir == DIR_SELL) g_newTradesThisBarSell++;
}

//+------------------------------------------------------------------+
//| AUD0-SEC-001 (lato EA): credenziali del bridge fail-closed        |
//|                                                                   |
//| InpWebToken aveva come default "NEXUS_BRIDGE_TOKEN_2026", cioe' lo |
//| stesso valore documentato in ogni copia del progetto: chiunque     |
//| conoscesse l'URL del backend poteva impersonare l'EA. Il default   |
//| e' ora vuoto e questo preflight DISATTIVA la sincronizzazione web  |
//| se il token e' assente, e' un segnaposto noto o e' troppo corto,   |
//| oppure se l'URL non e' HTTPS (il token viaggerebbe in chiaro).     |
//|                                                                   |
//| Il trading locale resta operativo: e' la telemetria a spegnersi,   |
//| non le protezioni. Fallire chiuso qui significa "nessun canale     |
//| remoto" invece di "canale remoto non autenticato".                |
//+------------------------------------------------------------------+
bool NXS_IsPlaceholderBridgeToken(string tok){
   string t = tok;
   StringToUpper(t);
   if(t == "NEXUS_BRIDGE_TOKEN_2026") return true;
   if(t == "CAMBIA_QUESTO_TOKEN")     return true;
   if(t == "CHANGEME")                return true;
   if(t == "TEST-TOKEN")              return true;
   if(t == "NEXUS123")                return true;
   if(t == "ADMIN")                   return true;
   return false;
}

void NXS_WebCredentialPreflight(){
   if(!InpEnableWebSync) return;
   string reason = "";
   string url    = InpWebURL;
   StringTrimLeft(url); StringTrimRight(url);

   if(StringLen(InpWebToken) == 0)
      reason = "InpWebToken vuoto";
   else if(NXS_IsPlaceholderBridgeToken(InpWebToken))
      reason = "InpWebToken e' un segnaposto pubblico noto";
   else if(StringLen(InpWebToken) < 24)
      reason = StringFormat("InpWebToken troppo corto (%d caratteri, minimo 24)",
                            StringLen(InpWebToken));
   else if(StringLen(url) == 0)
      reason = "InpWebURL vuoto";
   else if(StringFind(url, "https://") != 0 &&
           StringFind(url, "http://127.0.0.1") != 0 &&
           StringFind(url, "http://localhost") != 0)
      reason = "InpWebURL non e' HTTPS (il token viaggerebbe in chiaro)";

   if(StringLen(reason) == 0) return;

   InpEnableWebSync = false;
   PrintFormat("[NEXUS SEC] Sincronizzazione web DISATTIVATA: %s. "
               "Imposta un token dedicato e un URL HTTPS negli input dell'EA. "
               "Il trading e le protezioni locali restano attivi.", reason);
   Alert("NEXUS: WebSync disattivata — " + reason);
}

#endif
