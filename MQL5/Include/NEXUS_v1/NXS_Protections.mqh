//+------------------------------------------------------------------+
//|  NXS_Protections.mqh - Risk Protections (NEXUS v2.0 spec)         |
//|  ESL · DPT · MaxHoldTime · MaxLossPerPosition · AutoClose         |
//|  + Trade Reason Codes pushed to backend on close.                 |
//+------------------------------------------------------------------+
#ifndef __NXS_PROTECTIONS_MQH__
#define __NXS_PROTECTIONS_MQH__

// ----- State -----
// g_eslHit / g_dptHit / g_pausedUntilNextOpen / g_autoClosePending e lo stato
// di flatten sono dichiarati in NXS_Globals.mqh: vanno serializzati da
// NXS_State.mqh, che è incluso PRIMA di questo file.
datetime g_dptResetDay         = 0;

// v2.0.33 — post-stop-loss directional cooldown. Found via live trade
// review: a position gets stopped out, and within seconds a NEW position
// opens in the OPPOSITE direction at nearly the same price (chasing the
// reversal), which itself then gets stopped out too - a whipsaw pattern
// most visible on MALAYSIAN_SNR_NXR in choppy/ranging BTC conditions.
// Recording the close time per direction here; NXS_PostSLCooldownBlocks()
// below is the check called from NXS_OpenTrade/NXR_OpenTrade.
datetime g_lastSLCloseTime_BUY  = 0;   // last time a BUY position was stopped out
datetime g_lastSLCloseTime_SELL = 0;   // last time a SELL position was stopped out

void NXS_RegisterSLClose(ENUM_NXS_DIR closedDir){
   if(closedDir == DIR_BUY)  g_lastSLCloseTime_BUY  = TimeCurrent();
   if(closedDir == DIR_SELL) g_lastSLCloseTime_SELL = TimeCurrent();
}

// Blocks a NEW entry in `dir` if a position in the OPPOSITE direction was
// stopped out less than InpPostSLCooldownMin minutes ago.
bool NXS_PostSLCooldownBlocks(ENUM_NXS_DIR dir){
   if(!InpUsePostSLCooldown) return false;
   datetime oppositeCloseTime = (dir == DIR_BUY) ? g_lastSLCloseTime_SELL : g_lastSLCloseTime_BUY;
   if(oppositeCloseTime <= 0) return false;
   return (TimeCurrent() - oppositeCloseTime) < InpPostSLCooldownMin * 60;
}

// ----- Reason codes -----
#define NXS_R_TREND   "NXS:TREND"
#define NXS_R_PROFIT  "NXS:PROFIT"
#define NXS_R_DD      "NXS:DD"
#define NXS_R_TIME    "NXS:TIME"
#define NXS_R_NEWS    "NXS:NEWS"
#define NXS_R_BE      "NXS:BE"
#define NXS_R_RISK    "NXS:RISK"

// ----- Push Trade Reason to backend (retries w/ backoff — cold-start safe) --
// PR1: il payload dichiara ora il proprio "event" (close / resync /
// close_request) e porta trade_uid + position_id, cosi' il backend puo'
// essere idempotente per trade LOGICO invece di sovrascrivere alla cieca.
// "close_request" = push pre-chiusura di NXS_Prot_ClosePositionWithReason
// (PnL flottante, prezzo richiesto): non deve MAI diventare il PnL del trade.
void NXS_Prot_PushTradeReason(ulong ticket, long magic, string strategy,
                              string side, double lots, double openPrice,
                              double closePrice, double pnl, string reason,
                              datetime openTime, datetime closeTime,
                              // AUD0-PROT-006: default NON autorevole. Solo il
                              // ledger, che vede il deal eseguito, puo' inviare
                              // "close" e scrivere i campi realizzati.
                              string eventKind = "close_request",
                              int partialCount = 0, double volumeOut = 0.0,
                              string posSymbolIn = ""){
   if(!InpEnableWebSync) return;
   // NXS-PROT-003 / AUD0-WEB-012: il payload serializzava g_sym e g_digits,
   // cioe' il simbolo e la precisione del GRAFICO, non quelli della posizione
   // chiusa. Su un'operazione multi-simbolo il backend riceveva il simbolo
   // sbagliato e prezzi troncati alla precisione di un altro strumento.
   string posSymbol = (StringLen(posSymbolIn) > 0) ? posSymbolIn : g_sym;
   int    posDigits = (int)SymbolInfoInteger(posSymbol, SYMBOL_DIGITS);
   if(posDigits <= 0) posDigits = g_digits;
   long account = (long)AccountInfoInteger(ACCOUNT_LOGIN);
   string body = "{";
   body += "\"ticket\":"     + IntegerToString((long)ticket) + ",";
   body += "\"magic\":"      + IntegerToString(magic) + ",";
   body += "\"symbol\":\""   + posSymbol + "\",";
   body += "\"strategy\":\""  + _JsonEsc(strategy) + "\",";
   body += "\"side\":\""     + side + "\",";
   body += "\"lots\":"       + DoubleToString(lots, 2) + ",";
   body += "\"openPrice\":"  + DoubleToString(openPrice, posDigits) + ",";
   body += "\"closePrice\":" + DoubleToString(closePrice, posDigits) + ",";
   body += "\"pnl\":"        + DoubleToString(pnl, 2) + ",";
   body += "\"openTime\":\"" + NXS_IsoTime(openTime) + "\",";
   body += "\"closeTime\":\""+ NXS_IsoTime(closeTime) + "\",";
   body += "\"reason\":\""   + _JsonEsc(reason) + "\",";
   body += "\"event\":\""    + eventKind + "\",";
   body += "\"positionId\":" + IntegerToString((long)ticket) + ",";
   body += "\"tradeUid\":\"" + IntegerToString(account) + ":" + IntegerToString((long)ticket) + "\",";
   body += "\"partialCount\":" + IntegerToString(partialCount) + ",";
   body += "\"volumeOut\":"  + DoubleToString(volumeOut, 2);
   body += "}";

   string url = InpWebURL + "/api/ea/trade_reason";
   char post[]; StringToCharArray(body, post, 0, -1, CP_UTF8);
   ArrayResize(post, ArraySize(post) - 1);
   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";

   // AUD0-PROT-005 / NXS-PROT-005: qui c'erano 3 tentativi con timeout 20s e
   // Sleep di 1s+2s, cioe' fino a ~63 SECONDI di blocco del thread dell'EA,
   // eseguiti subito DOPO una chiusura di protezione — esattamente il momento
   // in cui il Virtual SL, le altre protezioni e OnTradeTransaction devono
   // poter girare.
   //
   // Un solo tentativo con timeout breve: la consegna non e' critica per la
   // sicurezza (il ledger e la history sync riconciliano comunque), mentre il
   // blocco dell'event loop lo e'. I fallimenti finiscono in un outbox locale
   // che il timer drena senza bloccare nulla.
   char result[]; string headersOut;
   int code = WebRequest("POST", url, headers, 3000, post, result, headersOut);
   if(code == 200) return;
   PrintFormat("[NEXUS PROT] PushTradeReason non consegnato (code=%d ticket=%d reason=%s): "
               "accodato nell'outbox", code, ticket, reason);
   NXS_Outbox_Push(url, body);
}

// ----- Close one position w/ reason in comment + push to backend -----
bool NXS_Prot_ClosePositionWithReason(ulong ticket, string reason){
   if(!PositionSelectByTicket(ticket)) return false;
   long mg = (long)PositionGetInteger(POSITION_MAGIC);
   if(!IsNexusMagic(mg)) return false;
   string sym = PositionGetString(POSITION_SYMBOL);
   double openP = PositionGetDouble(POSITION_PRICE_OPEN);
   double lots  = PositionGetDouble(POSITION_VOLUME);
   long   ptype = PositionGetInteger(POSITION_TYPE);
   double pnl   = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
   string side  = (ptype == POSITION_TYPE_BUY) ? "BUY" : "SELL";
   string strat = PositionGetString(POSITION_COMMENT);
   datetime openTm = (datetime)PositionGetInteger(POSITION_TIME);

   // Build close request w/ reason in comment so audit is readable in MT5 History
   MqlTradeRequest req;  ZeroMemory(req);
   MqlTradeResult  res;  ZeroMemory(res);
   req.action      = TRADE_ACTION_DEAL;
   req.position    = ticket;
   req.symbol      = sym;
   req.volume      = lots;
   // AUD0-RAW-003 / AUD0-RAW-004 / NXS-PROT-003: deviation fissa e filling
   // globale, entrambi calibrati sul simbolo del GRAFICO, mentre qui il
   // simbolo arriva dal ticket selezionato.
   req.deviation   = NXS_DeviationForSymbol(sym);
   req.magic       = mg;
   req.type_filling= NXS_FillingForSymbol(sym);
   req.comment     = reason;
   if(ptype == POSITION_TYPE_BUY){
      req.type  = ORDER_TYPE_SELL;
      req.price = SymbolInfoDouble(sym, SYMBOL_BID);
   } else {
      req.type  = ORDER_TYPE_BUY;
      req.price = SymbolInfoDouble(sym, SYMBOL_ASK);
   }
   bool ok = OrderSend(req, res);
   g_tradeRetcode = res.retcode;
   bool success = ok && (res.retcode == TRADE_RETCODE_DONE || res.retcode == TRADE_RETCODE_PLACED);
   if(success){
      double closeP = req.price;
      // PR1: questo e' un pre-push col PnL FLOTTANTE (commissioni escluse) e
      // il prezzo RICHIESTO — il close vero arrivera' dal ledger via
      // OnTradeTransaction. Marcato close_request: il backend lo archivia
      // come evento ma non sovrascrive il trade.
      // NXS-PROT-004: `strat` conteneva l'INTERO commento della posizione,
      // non l'identificativo di strategia. Si estrae il campo corretto.
      string stratId = strat;
      string cparts[]; int cn = StringSplit(strat, '|', cparts);
      if(cn >= 2 && StringLen(cparts[1]) > 0) stratId = cparts[1];
      NXS_Prot_PushTradeReason(ticket, mg, stratId, side, lots, openP, closeP, pnl, reason,
                               openTm, TimeCurrent(), "close_request", 0, 0.0, sym);
   }
   return success;
}

// ----- Close ALL positions w/ reason -----
//
// AUD0-PROT-002: la funzione restituiva quante posizioni erano state chiuse,
// ma i chiamanti alzavano comunque i flag di protezione. Se una chiusura
// falliva, il sistema si dichiarava "in pausa dopo aver chiuso tutto" mentre
// l'esposizione era ancora aperta, e NXS_Prot_OnTick usciva subito senza
// riprovare. Lo stato FLATTEN_PENDING qui sotto rende esplicito quel caso.
// g_flattenPending / g_flattenReason / g_flattenAttempts: NXS_Globals.mqh.

//: Conta le posizioni NEXUS ancora aperte sul simbolo corrente.
// AUD0-PROT-001 / AUD0-RISK-006 — PERIMETRO DELLE PROTEZIONI DI CONTO.
//
// ESL, DPT e lo scudo di ruin ricavano le loro soglie da BILANCIO ed EQUITY DEL
// CONTO, ma chiudevano solo le posizioni del simbolo del GRAFICO. Su un conto
// multi-simbolo questo significa: l'equity del conto scende sotto il limite,
// l'istanza su XAUUSD appiattisce XAUUSD e si mette in pausa — e le posizioni
// su BTCUSD, EURUSD e indici restano aperte, con la stessa equity che
// continua a scendere e nessuno che le chiuda.
//
// Il perimetro e' ora coerente con la soglia: una protezione di CONTO agisce
// su tutte le posizioni NEXUS del conto. InpProtScopeAccountWide permette di
// tornare al comportamento per-simbolo dove piu' istanze si dividono
// deliberatamente il conto.
bool _nxs_prot_inScope(string posSymbol){
   if(InpProtScopeAccountWide) return true;
   return (posSymbol == g_sym);
}

int NXS_Prot_OpenNexusCount(){
   int n = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(!_nxs_prot_inScope(PositionGetString(POSITION_SYMBOL))) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      n++;
   }
   return n;
}

int NXS_Prot_CloseAllWithReason(string reason){
   int closed = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      // AUD0-PROT-001: perimetro coerente con la soglia che ha fatto scattare
      // la protezione (di conto, non di simbolo).
      if(!_nxs_prot_inScope(PositionGetString(POSITION_SYMBOL))) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      if(NXS_Prot_ClosePositionWithReason(t, reason)) closed++;
   }
   return closed;
}

//: Esegue un flatten e registra se e' rimasta esposizione.
//: Ritorna true solo quando NON resta piu' nulla di aperto.
bool NXS_Prot_FlattenAll(string reason){
   // AUD0-WEB-008: da qui parte il raffreddamento che blocca i reset
   // remoti delle protezioni nei minuti successivi all'evento.
   g_lastProtectionEvent = TimeCurrent();
   int closed    = NXS_Prot_CloseAllWithReason(reason);
   int remaining = NXS_Prot_OpenNexusCount();
   if(remaining > 0){
      if(!g_flattenPending){
         g_flattenPending = true;
         g_flattenReason  = reason;
         g_flattenSince   = TimeCurrent();
         g_flattenAttempts = 0;
      }
      g_flattenAttempts++;
      PrintFormat("[NEXUS PROT][ALERT] FLATTEN INCOMPLETO (%s): chiuse=%d, "
                  "ANCORA APERTE=%d, tentativo %d",
                  reason, closed, remaining, g_flattenAttempts);
      return false;
   }
   if(g_flattenPending){
      PrintFormat("[NEXUS PROT] FLATTEN COMPLETATO (%s) dopo %d tentativi",
                  g_flattenReason, g_flattenAttempts);
      g_flattenPending  = false;
      g_flattenReason   = "";
      g_flattenAttempts = 0;
      g_flattenSince    = 0;
   }
   return true;
}

// ===================================================================
//   PROTECTION 1: Equity Stop Loss (ESL)
// ===================================================================
void NXS_Prot_CheckESL(){
   if(!InpUseESL || g_eslHit) return;
   double bal   = AccountInfoDouble(ACCOUNT_BALANCE);
   double floatL = NXS_FloatingPnL();
   double limit = InpESL_IsPercent ? -(bal * InpESL_Value / 100.0) : -InpESL_Value;
   if(floatL <= limit){
      // Il blocco di nuove entrate scatta SUBITO: e' l'unica parte che non
      // dipende dall'esito delle chiusure.
      g_eslHit = true;
      g_pausedUntilNextOpen = true;
      bool flat = NXS_Prot_FlattenAll(NXS_R_DD);
      PrintFormat("[NEXUS PROT] ESL HIT: floatPnL=%.2f <= limit=%.2f. Flat=%s. Paused.",
                  floatL, limit, (flat ? "SI" : "NO - retry in corso"));
   }
}

// ===================================================================
//   PROTECTION 2: Daily Profit Target (DPT)
// ===================================================================
void NXS_Prot_CheckDPT(){
   if(!InpUseDPT || g_dptHit) return;
   double bal0 = g_balanceDayStart > 0 ? g_balanceDayStart : AccountInfoDouble(ACCOUNT_BALANCE);
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double profit = equity - bal0;
   double target = InpDPT_IsPercent ? (bal0 * InpDPT_Value / 100.0) : InpDPT_Value;
   if(profit >= target){
      g_dptHit = true;
      g_pausedUntilNextOpen = true;
      bool flat = NXS_Prot_FlattenAll(NXS_R_PROFIT);
      PrintFormat("[NEXUS PROT] DPT HIT: profit=%.2f >= target=%.2f. Flat=%s. Paused for day.",
                  profit, target, (flat ? "SI" : "NO - retry in corso"));
   }
}

// ===================================================================
//   PROTECTION 3: Max Hold Time per position
// ===================================================================
void NXS_Prot_CheckMaxHold(){
   if(!InpUseMaxHold) return;
   datetime now = TimeCurrent();
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      // NXS-PROT-006: la scelta del limite e la partizione di competenza sono
      // ora in NXS_MaxHold_LimitSec() (NXS_Strategies.mqh), unica autorita'.
      // Qui si agisce SOLO sulle posizioni la cui strategia non e' risolvibile
      // dal commento — le altre appartengono a NXS_Management.mqh, che le
      // gestisce nello stesso loop di breakeven e trailing.
      string posComment = PositionGetString(POSITION_COMMENT);
      bool holdResolved = false;
      long limit = NXS_MaxHold_LimitSec(posComment, holdResolved);
      if(holdResolved) continue;   // competenza di NXS_Management.mqh
      if(limit <= 0) continue;
      datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      if(now - opened >= limit){
         NXS_Prot_ClosePositionWithReason(t, NXS_R_TIME);
         PrintFormat("[NEXUS PROT] MaxHold: closed ticket=%d (held %d s)", t, (int)(now - opened));
      }
   }
}

// ===================================================================
//   PROTECTION 4: Max Loss Per Position
// ===================================================================
void NXS_Prot_CheckMaxLossPerPos(){
   if(!InpUseMaxLossPos) return;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double lim = -(bal * InpMaxLossPosPct / 100.0);
   datetime now = TimeCurrent();
   long baseMinLife = (long)InpProt_MinLifeMin * 60;   // v2.0.14
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
      // v2.0.14 — non chiudere prima del tempo minimo di vita (anti stop-out su rumore M5).
      // v2.0.21 — il minimo scala col TF di origine: un trade H4/D1 vive di più
      // prima che NXS:RISK possa chiuderlo.
      datetime opened = (datetime)PositionGetInteger(POSITION_TIME);
      long minLife = (long)(baseMinLife * NXS_TF_LifeFactor(NXS_PosSourceTF(PositionGetString(POSITION_COMMENT))));
      double pl = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);

      // AUD0-PROT-007: il periodo di grazia serve a non farsi stoppare dal
      // rumore, ma veniva applicato ANCHE al limite monetario duro: una
      // posizione poteva superare la perdita massima e restare aperta perché
      // "troppo giovane". Si separano le due cose:
      //   - soglia di gestione del rumore: rispetta il tempo minimo di vita;
      //   - LIMITE DURO: non aspetta nulla.
      // Il limite duro è un multiplo della soglia ordinaria: oltre quello, la
      // perdita non è più rumore.
      double hardLim = lim * MathMax(1.0, InpProt_HardLossFactor);
      bool hardBreach = (pl <= hardLim);

      if(!hardBreach && (now - opened) < minLife) continue;
      if(pl <= lim){
         NXS_Prot_ClosePositionWithReason(t, NXS_R_RISK);
         PrintFormat("[NEXUS PROT] MaxLossPos: closed ticket=%d pl=%.2f <= lim=%.2f "
                     "age=%ds hard=%s",
                     t, pl, lim, (int)(now - opened), (hardBreach ? "SI" : "no"));
      }
   }
}

// ===================================================================
//   PROTECTION 5: AutoClose before market close (Friday-aware)
// ===================================================================
//: AUD0-PROT-008 — chiusura di sessione ricavata dal BROKER, non da un'ora fissa.
//:
//: InpMarketCloseGMT (21) presuppone che ogni strumento chiuda alla stessa ora
//: GMT. E' falso per indici, metalli, cripto (24/7) e per ogni festivita' o
//: chiusura anticipata: l'EA restava esposto oltre la chiusura reale, oppure
//: appiattiva il conto a meta' seduta.
//:
//: Qui si interroga SymbolInfoSessionTrade() per il giorno corrente e si usa
//: la fine dell'ULTIMA sessione di trading del simbolo. Se il broker non
//: espone sessioni (o lo strumento e' 24/7 con sessione unica a giornata
//: intera) si ricade sul valore configurato, segnalandolo una sola volta.
//:
//: Ritorna false se per oggi non esiste una chiusura significativa
//: (nessuna sessione = mercato chiuso, oppure copertura 24h).
bool NXS_Prot_SessionCloseMin(string sym, int &closeMinOut, bool &fromBroker){
   fromBroker  = false;
   closeMinOut = InpMarketCloseGMT * 60;

   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   ENUM_DAY_OF_WEEK dow = (ENUM_DAY_OF_WEEK)dt.day_of_week;

   datetime from = 0, to = 0;
   int  session = 0;
   long lastEnd = -1;
   long firstBeg = -1;
   while(SymbolInfoSessionTrade(sym, dow, session, from, to)){
      if(firstBeg < 0) firstBeg = (long)from;
      if((long)to > lastEnd) lastEnd = (long)to;
      session++;
      if(session > 8) break;   // guardia: nessun broker espone piu' sessioni
   }

   if(session == 0) return false;               // oggi il simbolo non tratta
   if(firstBeg <= 0 && lastEnd >= 24 * 3600 - 60) return false;  // 24h continue

   // from/to sono secondi dall'inizio del giorno nell'ora del SERVER.
   closeMinOut = (int)(lastEnd / 60);
   fromBroker  = true;
   return true;
}

bool g_autoCloseFallbackLogged = false;

void NXS_Prot_CheckAutoClose(){
   if(!InpUseAutoClose) return;

   int  closeMin   = 0;
   bool fromBroker = false;
   if(!NXS_Prot_SessionCloseMin(g_sym, closeMin, fromBroker)){
      // Nessuna chiusura odierna (mercato chiuso o strumento 24/7): non c'e'
      // niente da appiattire per fine seduta.
      g_autoClosePending = false;
      return;
   }
   if(!fromBroker && !g_autoCloseFallbackLogged){
      g_autoCloseFallbackLogged = true;
      PrintFormat("[NEXUS PROT] AutoClose: il broker non espone sessioni per %s, "
                  "si usa InpMarketCloseGMT=%02d:00 come ripiego", g_sym, InpMarketCloseGMT);
   }

   // Orario coerente con la sorgente: ora server se viene dal broker,
   // ora GMT se e' il ripiego configurato.
   MqlDateTime dt;
   TimeToStruct(fromBroker ? TimeCurrent() : TimeGMT(), dt);
   int nowMin = dt.hour * 60 + dt.min;

   if(nowMin >= closeMin - InpAutoCloseMin && nowMin < closeMin){
      if(!g_autoClosePending){
         g_autoClosePending = true;
         g_pausedUntilNextOpen = true;
         bool flat = NXS_Prot_FlattenAll(NXS_R_TIME);
         PrintFormat("[NEXUS PROT] AutoClose %02d:%02d (chiusura %02d:%02d, fonte=%s) flat=%s",
                     dt.hour, dt.min, closeMin / 60, closeMin % 60,
                     (fromBroker ? "sessioni broker" : "InpMarketCloseGMT"),
                     (flat ? "SI" : "NO - retry in corso"));
      }
   } else {
      g_autoClosePending = false;
   }
}

// ===================================================================
//   Daily resume hook
// ===================================================================
void NXS_Prot_OnNewDay(){
   // AUD0-PROT-002: se resta esposizione da un flatten mai completato, il
   // nuovo giorno NON deve riabilitare il trading: il conto e' ancora nello
   // stato che ha fatto scattare la protezione.
   if(g_flattenPending && NXS_Prot_OpenNexusCount() > 0){
      PrintFormat("[NEXUS PROT][ALERT] nuovo giorno con flatten INCOMPIUTO (%s): "
                  "il blocco resta attivo", g_flattenReason);
      g_dptResetDay = TimeCurrent();
      return;
   }
   g_eslHit = false;
   g_dptHit = false;
   g_pausedUntilNextOpen = false;
   g_autoClosePending = false;
   g_flattenPending = false;
   g_flattenAttempts = 0;
   g_dptResetDay = TimeCurrent();
}

// ===================================================================
//   Master gate
// ===================================================================
bool NXS_Prot_EntryBlocked(){
   // v2.0.31: in Strategy Tester, don't let daily-pause/ESL/DPT/AutoClose
   // gates silence most of the 37 strategies for a big chunk of every test
   // window (this is what the Phase 2c per-strategy diagnostic found as the
   // dominant blocker for nearly all of them). Live behavior is completely
   // untouched - MQL_TESTER is only true while backtesting/optimizing.
   //
   // AUD0-PROT-009 / AUD0-RISK-004: il bypass rendeva i backtest NON
   // rappresentativi dei vincoli live — si ottimizzava un sistema che nel
   // reale non esiste. Ora e' governato da InpTesterProtectionParity, che di
   // default applica al tester le STESSE regole del live.
   //
   // Un flatten incompiuto blocca sempre, in ogni modalita': e' uno stato di
   // sicurezza, non un filtro di ricerca.
   if(g_flattenPending) return true;
   if(MQLInfoInteger(MQL_TESTER) && !InpTesterProtectionParity) return false;
   return g_pausedUntilNextOpen || g_eslHit || g_dptHit || g_autoClosePending;
}

// ===================================================================
//   Master tick
// ===================================================================
void NXS_Prot_OnTick(){
   // AUD0-PROT-002: qui la funzione usciva SUBITO quando la pausa era attiva.
   // Se il flatten che aveva causato la pausa era fallito, nessuno riprovava
   // mai a chiudere: le posizioni restavano aperte a tempo indeterminato,
   // mentre il sistema si dichiarava "in pausa dopo aver chiuso tutto".
   if(g_flattenPending){
      if(NXS_Prot_OpenNexusCount() > 0){
         // Ritenta a cadenza limitata per non martellare il broker.
         static datetime lastRetry = 0;
         if(TimeCurrent() - lastRetry >= 5){
            lastRetry = TimeCurrent();
            NXS_Prot_FlattenAll(g_flattenReason);
         }
      } else {
         NXS_Prot_FlattenAll(g_flattenReason);   // chiude lo stato pendente
      }
      return;   // finche' resta esposizione da chiudere, nient'altro conta
   }

   if(g_pausedUntilNextOpen) return;
   NXS_Prot_CheckMaxHold();
   NXS_Prot_CheckMaxLossPerPos();
   NXS_Prot_CheckESL();
   NXS_Prot_CheckDPT();
   NXS_Prot_CheckAutoClose();
}

#endif
