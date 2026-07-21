//+------------------------------------------------------------------+
//|  NXS_EdgeAdaptive.mqh — Sprint 3 (edge / adaptive layer)         |
//|  #5 Reaction cache · #7 SL virtualizzato · #8 OnTradeTransaction |
//|  #9 Slippage per sessione · #12 Volatility regime · #13 Learner  |
//|  v2.0.9 — completes the 15-point performance roadmap             |
//+------------------------------------------------------------------+
#ifndef __NXS_EDGEADAPTIVE_MQH__
#define __NXS_EDGEADAPTIVE_MQH__

// =====================================================================
// #5 — REACTION ENGINE CACHE  (compute once per new M5 bar)
// =====================================================================
struct SNXSReactionCache {
   datetime barTime;
   bool     detected;
   int      direction;
   double   quality;
   double   priceLo;
   double   priceHi;
   string   tag;
};
SNXSReactionCache g_NXSeaReact;

bool NXS_EA_ReactionShouldRecompute(){
   datetime cur = iTime(_Symbol, PERIOD_M5, 0);
   if(cur == 0) return false;
   if(cur == g_NXSeaReact.barTime) return false;
   g_NXSeaReact.barTime = cur;
   return true;
}

// =====================================================================
// #7 — VIRTUALIZED STOP LOSS  (PR2: broker hard SL wide, real SL internal)
// =====================================================================
// Ciclo completo: Register-dopo-fill -> ARMED -> (hit) TRIGGERED ->
// CLOSE_REQUESTED -> (conferma reale) CONFIRMED, con ESCALATED non terminale.
// Modalita' esplicita OFF/OBSERVE/EXECUTE (default OFF = baseline byte-for-byte).
// Vedi docs/architecture/PR2_VIRTUAL_SL.md.
enum ENUM_NXS_VSL_MODE { NXS_VSL_OFF = 0, NXS_VSL_OBSERVE = 1, NXS_VSL_EXECUTE = 2 };
enum ENUM_NXS_VSL_STATE {
   NXS_VSLS_ARMED = 0, NXS_VSLS_TRIGGERED = 1, NXS_VSLS_CLOSE_REQ = 2,
   NXS_VSLS_CONFIRMED = 3, NXS_VSLS_ESCALATED = 4
};

input ENUM_NXS_VSL_MODE InpVirtSL_Mode          = NXS_VSL_OFF;  // OFF=baseline
input double            InpVirtSL_HardSL_ATRMult = 4.0;   // broker hard SL = entry +/- k*ATR
input int               InpVirtSL_MaxTries       = 5;     // tentativi prima di ESCALATED
input int               InpVirtSL_BackoffMs      = 1500;  // backoff tra tentativi (CLOSE_REQ)
input int               InpVirtSL_EscBackoffMs   = 15000; // backoff piu' lungo in ESCALATED
input int               InpVirtSL_PendingTTLsec  = 120;   // scadenza intent pending senza fill
input bool              InpVirtSL_BlockIfNoHardSL = false;// hard SL invalido: true=blocca entrata, false=fallback SL logico

#define NXS_VSL_PERSIST_VER 2

// ----- record posizione armata -----
struct SNXSVirtSL {
   ulong    positionId;
   string   symbol;
   long     magic;
   int      direction;      // +1 buy / -1 sell
   double   virtPrice;      // SL logico virtualizzato
   double   brokerHardSL;   // hard SL congelato all'ingresso
   int      state;          // ENUM_NXS_VSL_STATE
   int      attempts;       // tentativi di chiusura effettuati
   uint     lastAttemptMs;  // GetTickCount dell'ultimo tentativo
   datetime triggerTime;    // quando ARMED->TRIGGERED
   string   confirmSource;  // "" | "LEDGER_FINAL" | "POSITION_GONE"
};
SNXSVirtSL g_NXSeaVSL[];

// ----- intent pending (request -> fill) correlato via order_ticket -----
struct SNXSVSLPending {
   ulong    orderTicket;
   string   symbol;
   long     magic;
   int      direction;
   string   strategy;
   datetime requestTime;
   double   virtSL;
   double   brokerSL;
};
SNXSVSLPending g_NXSeaVSLPend[];

string NXS_VSL_StateName(int s){
   switch(s){
      case NXS_VSLS_ARMED:      return "ARMED";
      case NXS_VSLS_TRIGGERED:  return "TRIGGERED";
      case NXS_VSLS_CLOSE_REQ:  return "CLOSE_REQUESTED";
      case NXS_VSLS_CONFIRMED:  return "CONFIRMED";
      case NXS_VSLS_ESCALATED:  return "ESCALATED";
   }
   return "?";
}

bool NXS_VSL_Active(){ return (InpVirtSL_Mode != NXS_VSL_OFF); }

// Hard SL largo, normalizzato a tick e vincolo stops-level del broker.
// Ritorna false se non calcolabile/valido: MAI restituisce uno SL=0 usabile.
bool NXS_VSL_ComputeHardSL(int dir, double entry, double atr, double &outHard){
   outHard = 0.0;
   if(atr <= 0.0 || entry <= 0.0) return false;
   double dist = InpVirtSL_HardSL_ATRMult * atr;
   if(dist <= 0.0) return false;
   double raw = (dir == +1) ? entry - dist : entry + dist;
   double ts  = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE);
   if(ts <= 0.0) ts = g_point;
   if(ts > 0.0) raw = MathRound(raw / ts) * ts;
   // rispetta lo stops level minimo rispetto al prezzo corrente
   int    stopsLvl = (int)SymbolInfoInteger(g_sym, SYMBOL_TRADE_STOPS_LEVEL);
   double minDist  = stopsLvl * g_point;
   double px = (dir == +1) ? SymbolInfoDouble(g_sym, SYMBOL_BID)
                           : SymbolInfoDouble(g_sym, SYMBOL_ASK);
   if(px > 0.0 && minDist > 0.0){
      if(dir == +1 && (px - raw) < minDist) raw = px - minDist;
      if(dir == -1 && (raw - px) < minDist) raw = px + minDist;
   }
   raw = NormalizeDouble(raw, g_digits);
   if(raw <= 0.0) return false;
   outHard = raw;
   return true;
}

int _nxs_vsl_findByPos(ulong posId){
   for(int i = ArraySize(g_NXSeaVSL) - 1; i >= 0; i--)
      if(g_NXSeaVSL[i].positionId == posId) return i;
   return -1;
}

// Intent registrato al momento della richiesta d'ordine (dopo OrderSend, con
// l'order ticket reale). Correla request->fill senza "last order ticket".
void NXS_VSL_PendingAdd(ulong orderTicket, string symbol, long magic, int dir,
                        string strat, double virtSL, double brokerSL){
   if(!NXS_VSL_Active() || orderTicket == 0) return;
   int n = ArraySize(g_NXSeaVSLPend);
   ArrayResize(g_NXSeaVSLPend, n + 1);
   g_NXSeaVSLPend[n].orderTicket = orderTicket;
   g_NXSeaVSLPend[n].symbol      = symbol;
   g_NXSeaVSLPend[n].magic       = magic;
   g_NXSeaVSLPend[n].direction   = dir;
   g_NXSeaVSLPend[n].strategy    = strat;
   g_NXSeaVSLPend[n].requestTime = TimeCurrent();
   g_NXSeaVSLPend[n].virtSL      = virtSL;
   g_NXSeaVSLPend[n].brokerSL    = brokerSL;
}

int _nxs_vsl_pendIdxByOrder(ulong orderTicket){
   for(int i = ArraySize(g_NXSeaVSLPend) - 1; i >= 0; i--)
      if(g_NXSeaVSLPend[i].orderTicket == orderTicket) return i;
   return -1;
}

void _nxs_vsl_pendRemove(int idx){
   int n = ArraySize(g_NXSeaVSLPend);
   if(idx < 0 || idx >= n) return;
   for(int i = idx + 1; i < n; i++) g_NXSeaVSLPend[i - 1] = g_NXSeaVSLPend[i];
   ArrayResize(g_NXSeaVSLPend, n - 1);
}

void NXS_VSL_PruneExpiredPending(){
   if(InpVirtSL_PendingTTLsec <= 0) return;
   datetime now = TimeCurrent();
   for(int i = ArraySize(g_NXSeaVSLPend) - 1; i >= 0; i--){
      if((long)now - (long)g_NXSeaVSLPend[i].requestTime > InpVirtSL_PendingTTLsec){
         PrintFormat("[NXS VirtSL] pending scaduto senza fill order=%I64u strat=%s",
                     g_NXSeaVSLPend[i].orderTicket, g_NXSeaVSLPend[i].strategy);
         _nxs_vsl_pendRemove(i);
      }
   }
}

// Registra il record armato (idempotente per positionId).
void NXS_EA_VirtSL_Register(ulong posId, string symbol, long magic, int dir,
                            double virtPrice, double brokerHardSL){
   if(!NXS_VSL_Active() || posId == 0) return;
   if(_nxs_vsl_findByPos(posId) >= 0) return;   // gia' registrato: no duplicati
   int n = ArraySize(g_NXSeaVSL);
   ArrayResize(g_NXSeaVSL, n + 1);
   g_NXSeaVSL[n].positionId    = posId;
   g_NXSeaVSL[n].symbol        = symbol;
   g_NXSeaVSL[n].magic         = magic;
   g_NXSeaVSL[n].direction     = dir;
   g_NXSeaVSL[n].virtPrice     = virtPrice;
   g_NXSeaVSL[n].brokerHardSL  = brokerHardSL;
   g_NXSeaVSL[n].state         = NXS_VSLS_ARMED;
   g_NXSeaVSL[n].attempts      = 0;
   g_NXSeaVSL[n].lastAttemptMs = 0;
   g_NXSeaVSL[n].triggerTime   = 0;
   g_NXSeaVSL[n].confirmSource = "";
   PrintFormat("[NXS VirtSL] ARMED pos=%I64u %s virt=%.5f hardSL=%.5f dir=%d",
               posId, symbol, virtPrice, brokerHardSL, dir);
}

// ----- API per il percorso d'ingresso (chiamate come FUNZIONI, forward-ref:
// NXS_Execution.mqh e' incluso prima di questo file, quindi non puo' vedere
// l'enum/gli input direttamente — solo funzioni). -----
bool NXS_VSL_ModeIsExecute(){ return InpVirtSL_Mode == NXS_VSL_EXECUTE; }

// Da chiamare subito PRIMA dell'invio ordine: decide lo SL da mandare al broker.
// Ritorna false SOLO se hard SL invalido e InpVirtSL_BlockIfNoHardSL: entrata da bloccare.
// Mai imposta SL=0: in OFF/OBSERVE o fallback -> SL logico.
bool NXS_VSL_PrepareEntry(int dir, double entry, double logicalSL, double atr,
                          double &brokerSLout){
   brokerSLout = logicalSL;                 // baseline: SL logico al broker
   if(!NXS_VSL_Active()) return true;        // OFF
   if(InpVirtSL_Mode == NXS_VSL_OBSERVE) return true;  // broker tiene lo SL logico
   double hard;                              // EXECUTE: allarga al hard SL congelato
   if(NXS_VSL_ComputeHardSL(dir, entry, atr, hard)){ brokerSLout = hard; return true; }
   if(InpVirtSL_BlockIfNoHardSL) return false;         // hard SL invalido -> blocca
   brokerSLout = logicalSL;                             // fallback esplicito: SL logico
   return true;
}

// Da chiamare subito DOPO un invio riuscito, con l'order ticket reale.
void NXS_VSL_OnRequested(ulong orderTicket, string sym, long magic, int dir,
                         string strat, double logicalSL, double brokerSLused){
   if(!NXS_VSL_Active() || orderTicket == 0) return;
   // virtSL = SL logico (sempre); brokerSL registrato = quello davvero inviato.
   NXS_VSL_PendingAdd(orderTicket, sym, magic, dir, strat, logicalSL, brokerSLused);
}

// Aggancio "dopo il fill reale": dal deal risale a order+position, matcha il
// pending per DEAL_ORDER e registra con DEAL_POSITION_ID.
void NXS_EA_VirtSL_OnFill(ulong dealTicket){
   if(!NXS_VSL_Active() || dealTicket == 0) return;
   if(!HistoryDealSelect(dealTicket)) return;
   if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(dealTicket, DEAL_ENTRY) != DEAL_ENTRY_IN) return;
   ulong orderTicket = (ulong)HistoryDealGetInteger(dealTicket, DEAL_ORDER);
   int   pidx = _nxs_vsl_pendIdxByOrder(orderTicket);
   if(pidx < 0) return;   // fill non nostro / senza intent (grid/pyramid esclusi)
   ulong posId = (ulong)HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
   NXS_EA_VirtSL_Register(posId, g_NXSeaVSLPend[pidx].symbol,
                          g_NXSeaVSLPend[pidx].magic, g_NXSeaVSLPend[pidx].direction,
                          g_NXSeaVSLPend[pidx].virtSL, g_NXSeaVSLPend[pidx].brokerSL);
   _nxs_vsl_pendRemove(pidx);
}

// ----- macchina a stati PURA (testabile senza broker) -----
struct SNXSVSLDecision {
   int    newState;
   bool   issueClose;
   bool   confirmed;
   string confirmSource;
   bool   escalated;
};

void NXS_VSL_Decide(const SNXSVirtSL &r, int mode, bool posExists,
                    bool ledgerFinal, bool hit, uint nowMs, SNXSVSLDecision &d){
   d.newState = r.state; d.issueClose = false; d.confirmed = false;
   d.confirmSource = ""; d.escalated = false;
   if(r.state == NXS_VSLS_CONFIRMED) return;

   // Conferma reale: mai da DONE/PLACED. Preferisci ledger FINAL, poi position-gone.
   if(ledgerFinal){
      d.newState = NXS_VSLS_CONFIRMED; d.confirmed = true; d.confirmSource = "LEDGER_FINAL"; return;
   }
   if(!posExists){
      d.newState = NXS_VSLS_CONFIRMED; d.confirmed = true; d.confirmSource = "POSITION_GONE"; return;
   }

   if(mode == NXS_VSL_OBSERVE){
      // Osserva soltanto: il broker ha lo SL logico e chiudera' da solo.
      if(r.state == NXS_VSLS_ARMED && hit) d.newState = NXS_VSLS_TRIGGERED;
      return;
   }
   // EXECUTE
   if(r.state == NXS_VSLS_ARMED){
      if(hit) d.newState = NXS_VSLS_TRIGGERED;
      return;
   }
   if(r.state == NXS_VSLS_TRIGGERED){
      d.newState = NXS_VSLS_CLOSE_REQ; d.issueClose = true; return;   // primo tentativo
   }
   if(r.state == NXS_VSLS_CLOSE_REQ || r.state == NXS_VSLS_ESCALATED){
      uint backoff = (r.state == NXS_VSLS_ESCALATED)
                     ? (uint)InpVirtSL_EscBackoffMs : (uint)InpVirtSL_BackoffMs;
      if(nowMs - r.lastAttemptMs < backoff) return;                  // rispetta il ritmo
      if(r.state == NXS_VSLS_CLOSE_REQ && r.attempts >= InpVirtSL_MaxTries){
         d.newState = NXS_VSLS_ESCALATED; d.escalated = true; d.issueClose = true; return;
      }
      d.issueClose = true;   // ESCALATED continua a ritentare (non terminale)
      return;
   }
}

void _nxs_vsl_confirm(int i, string src){
   g_NXSeaVSL[i].state         = NXS_VSLS_CONFIRMED;
   g_NXSeaVSL[i].confirmSource = src;
   PrintFormat("[NXS VirtSL] CONFIRMED pos=%I64u via=%s attempts=%d",
               g_NXSeaVSL[i].positionId, src, g_NXSeaVSL[i].attempts);
}

int NXS_EA_VirtSL_Check(){
   if(!NXS_VSL_Active()) return 0;    // OFF: no-op assoluto
   NXS_VSL_PruneExpiredPending();
   int acted = 0;
   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
   uint   now = GetTickCount();
   bool   changed = false;
   for(int i = 0; i < ArraySize(g_NXSeaVSL); i++){
      if(g_NXSeaVSL[i].state == NXS_VSLS_CONFIRMED) continue;
      bool posExists  = PositionSelectByTicket(g_NXSeaVSL[i].positionId);
      bool ledgerFin  = NXS_Ledger_Emitted(g_NXSeaVSL[i].positionId);  // PR1
      bool hit = (g_NXSeaVSL[i].direction == +1)
                  ? (bid <= g_NXSeaVSL[i].virtPrice)
                  : (ask >= g_NXSeaVSL[i].virtPrice);
      SNXSVSLDecision d;
      NXS_VSL_Decide(g_NXSeaVSL[i], (int)InpVirtSL_Mode, posExists, ledgerFin, hit, now, d);

      if(d.newState != g_NXSeaVSL[i].state && d.newState == NXS_VSLS_TRIGGERED){
         g_NXSeaVSL[i].triggerTime = TimeCurrent();
         PrintFormat("[NXS VirtSL] TRIGGERED pos=%I64u virt=%.5f mode=%d",
                     g_NXSeaVSL[i].positionId, g_NXSeaVSL[i].virtPrice, (int)InpVirtSL_Mode);
      }
      if(d.escalated)
         PrintFormat("[NXS VirtSL][ALERT] ESCALATED pos=%I64u attempts=%d — chiusura non confermata, retry rallentato",
                     g_NXSeaVSL[i].positionId, g_NXSeaVSL[i].attempts);

      if(d.issueClose){
         bool ok = NXS_Prot_ClosePositionWithReason(g_NXSeaVSL[i].positionId, "NXS:VSL");
         g_NXSeaVSL[i].attempts++;
         g_NXSeaVSL[i].lastAttemptMs = now;
         acted++;
         PrintFormat("[NXS VirtSL] CLOSE_REQUEST pos=%I64u attempt=%d send_ok=%d (DONE/PLACED != conferma)",
                     g_NXSeaVSL[i].positionId, g_NXSeaVSL[i].attempts, ok);
      }
      if(d.newState != g_NXSeaVSL[i].state){
         g_NXSeaVSL[i].state = d.newState;
         changed = true;
      }
      if(d.confirmed){ _nxs_vsl_confirm(i, d.confirmSource); changed = true; }
   }
   if(changed) NXS_VSL_Persist();
   return acted;
}

// ----- persistenza versionata, per-account+magic, atomica -----
string _nxs_vsl_file(){
   return StringFormat("NEXUS\\virtsl_%I64d_%I64d.csv",
                       (long)AccountInfoInteger(ACCOUNT_LOGIN), (long)InpMagic);
}

void NXS_VSL_Persist(){
   if(!NXS_VSL_Active()) return;            // OFF: nessun file (baseline)
   if(MQLInfoInteger(MQL_TESTER)) return;   // il tester riparte pulito
   string tmp = _nxs_vsl_file() + ".tmp";
   int h = FileOpen(tmp, FILE_WRITE|FILE_CSV|FILE_ANSI, ';');
   if(h == INVALID_HANDLE) return;
   FileWrite(h, "NXVSL", NXS_VSL_PERSIST_VER,
             (long)AccountInfoInteger(ACCOUNT_LOGIN), (long)InpMagic);
   for(int i = 0; i < ArraySize(g_NXSeaVSL); i++){
      if(g_NXSeaVSL[i].state == NXS_VSLS_CONFIRMED) continue;   // niente record chiusi
      FileWrite(h, "A", (long)g_NXSeaVSL[i].positionId, g_NXSeaVSL[i].symbol,
                (long)g_NXSeaVSL[i].magic, g_NXSeaVSL[i].direction,
                DoubleToString(g_NXSeaVSL[i].virtPrice, g_digits),
                DoubleToString(g_NXSeaVSL[i].brokerHardSL, g_digits),
                g_NXSeaVSL[i].state, g_NXSeaVSL[i].attempts,
                (long)g_NXSeaVSL[i].triggerTime, g_NXSeaVSL[i].confirmSource);
   }
   for(int i = 0; i < ArraySize(g_NXSeaVSLPend); i++){
      FileWrite(h, "P", (long)g_NXSeaVSLPend[i].orderTicket, g_NXSeaVSLPend[i].symbol,
                (long)g_NXSeaVSLPend[i].magic, g_NXSeaVSLPend[i].direction,
                g_NXSeaVSLPend[i].strategy, (long)g_NXSeaVSLPend[i].requestTime,
                DoubleToString(g_NXSeaVSLPend[i].virtSL, g_digits),
                DoubleToString(g_NXSeaVSLPend[i].brokerSL, g_digits));
   }
   FileClose(h);
   FileMove(tmp, 0, _nxs_vsl_file(), FILE_REWRITE);   // sostituzione atomica
}

// Boot: carica, valida (account+magic+versione), riconcilia con broker/ledger.
void NXS_VSL_Restore(){
   if(!NXS_VSL_Active()) return;
   ArrayResize(g_NXSeaVSL, 0);
   ArrayResize(g_NXSeaVSLPend, 0);
   int h = FileOpen(_nxs_vsl_file(), FILE_READ|FILE_CSV|FILE_ANSI, ';');
   if(h == INVALID_HANDLE) return;
   string tag   = FileReadString(h);
   int    ver   = (int)StringToInteger(FileReadString(h));
   long   login = (long)StringToInteger(FileReadString(h));
   long   mg    = (long)StringToInteger(FileReadString(h));
   if(tag != "NXVSL" || ver != NXS_VSL_PERSIST_VER ||
      login != (long)AccountInfoInteger(ACCOUNT_LOGIN) || mg != (long)InpMagic){
      FileClose(h);
      PrintFormat("[NXS VirtSL] persist ignorato (mismatch account/magic/versione)");
      return;   // nessuna contaminazione tra account/istanze
   }
   int armed = 0, pend = 0;
   while(!FileIsEnding(h)){
      string kind = FileReadString(h);
      if(kind == "A"){
         ulong  posId = (ulong)StringToInteger(FileReadString(h));
         string sym   = FileReadString(h);
         long   rmg   = (long)StringToInteger(FileReadString(h));
         int    dir   = (int)StringToInteger(FileReadString(h));
         double virt  = StringToDouble(FileReadString(h));
         double hard  = StringToDouble(FileReadString(h));
         int    st    = (int)StringToInteger(FileReadString(h));
         int    att   = (int)StringToInteger(FileReadString(h));
         datetime tt  = (datetime)StringToInteger(FileReadString(h));
         string src   = FileReadString(h);
         if(posId == 0) continue;
         // riconciliazione: posizione gia' chiusa offline -> scarta;
         // FINAL gia' nel ledger -> scarta (no doppia richiesta);
         // altrimenti riarma ARMED/TRIGGERED, o CLOSE_REQ da ri-verificare.
         if(!PositionSelectByTicket(posId)) continue;
         if(NXS_Ledger_Emitted(posId))      continue;
         int n = ArraySize(g_NXSeaVSL);
         ArrayResize(g_NXSeaVSL, n + 1);
         g_NXSeaVSL[n].positionId = posId; g_NXSeaVSL[n].symbol = sym;
         g_NXSeaVSL[n].magic = rmg; g_NXSeaVSL[n].direction = dir;
         g_NXSeaVSL[n].virtPrice = virt; g_NXSeaVSL[n].brokerHardSL = hard;
         g_NXSeaVSL[n].state = st; g_NXSeaVSL[n].attempts = att;
         g_NXSeaVSL[n].lastAttemptMs = 0; g_NXSeaVSL[n].triggerTime = tt;
         g_NXSeaVSL[n].confirmSource = src;
         armed++;
      } else if(kind == "P"){
         ulong  ot  = (ulong)StringToInteger(FileReadString(h));
         string sym = FileReadString(h);
         long   rmg = (long)StringToInteger(FileReadString(h));
         int    dir = (int)StringToInteger(FileReadString(h));
         string str = FileReadString(h);
         datetime rt = (datetime)StringToInteger(FileReadString(h));
         double virt = StringToDouble(FileReadString(h));
         double brk  = StringToDouble(FileReadString(h));
         if(ot == 0) continue;
         int n = ArraySize(g_NXSeaVSLPend);
         ArrayResize(g_NXSeaVSLPend, n + 1);
         g_NXSeaVSLPend[n].orderTicket = ot; g_NXSeaVSLPend[n].symbol = sym;
         g_NXSeaVSLPend[n].magic = rmg; g_NXSeaVSLPend[n].direction = dir;
         g_NXSeaVSLPend[n].strategy = str; g_NXSeaVSLPend[n].requestTime = rt;
         g_NXSeaVSLPend[n].virtSL = virt; g_NXSeaVSLPend[n].brokerSL = brk;
         pend++;
      }
   }
   FileClose(h);
   PrintFormat("[NXS VirtSL] restore: %d armati, %d pending riconciliati", armed, pend);
}

// =====================================================================
// #8 — ONTRADETRANSACTION  (event-driven fill capture)
// =====================================================================
ulong g_NXSeaLastDealTicket = 0;
uint  g_NXSeaLastFillMs     = 0;

void NXS_EA_OnTradeTx(const MqlTradeTransaction &tx){
   if(tx.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(tx.deal == 0) return;
   g_NXSeaLastDealTicket = tx.deal;
   g_NXSeaLastFillMs     = GetTickCount();
}

ulong NXS_EA_GetLastDeal(){ return g_NXSeaLastDealTicket; }
uint  NXS_EA_GetFillMs (){ return g_NXSeaLastFillMs;     }

// =====================================================================
// #9 — SESSION-AWARE SLIPPAGE CAP
// =====================================================================
int InpSlip_Asian   = 8;
int InpSlip_London  = 15;
int InpSlip_NewYork = 22;
int InpSlip_Overlap = 30;
int InpSlip_Off     = 12;

int NXS_EA_SlippageCap(int sessionCode){
   switch(sessionCode){
      case 1: return InpSlip_Asian;
      case 2: return InpSlip_London;
      case 3: return InpSlip_NewYork;
      case 4: return InpSlip_Overlap;
      default: return InpSlip_Off;
   }
}

// =====================================================================
// #12 — VOLATILITY REGIME ADAPTER  (ATR percentile rolling 100 bars)
// =====================================================================
bool InpVolAdapt_Enable    = true;
int  InpVolAdapt_LookbackN = 100;

double g_NXSeaVolWin[];
int    g_NXSeaVolN = 0;

void NXS_EA_VolAdapt_Sample(double atr){
   if(atr <= 0) return;
   if(ArraySize(g_NXSeaVolWin) < InpVolAdapt_LookbackN)
      ArrayResize(g_NXSeaVolWin, InpVolAdapt_LookbackN);
   int idx = g_NXSeaVolN % InpVolAdapt_LookbackN;
   g_NXSeaVolWin[idx] = atr;
   g_NXSeaVolN++;
}

double NXS_EA_VolAdapt_Pct(double curAtr){
   int n = MathMin(g_NXSeaVolN, InpVolAdapt_LookbackN);
   if(n < 20) return 0.5;
   int below = 0;
   for(int i = 0; i < n; ++i)
      if(g_NXSeaVolWin[i] < curAtr) below++;
   return (double)below / (double)n;
}

void NXS_EA_VolAdapt_Multipliers(double atr, double &slMult, double &tpMult){
   slMult = 1.0; tpMult = 1.0;
   if(!InpVolAdapt_Enable) return;
   double pct = NXS_EA_VolAdapt_Pct(atr);
   if(pct < 0.33){ slMult = 0.7; tpMult = 0.9; return; }
   if(pct > 0.75){ slMult = 1.5; tpMult = 1.3; return; }
}

// =====================================================================
// #13 — SESSION×STRATEGY AUTO-LEARNER  (CSV: NEXUS\auto_disable.csv)
// =====================================================================
bool InpLearner_Enable = true;

struct SNXSAutoDisable { string strat; int session; string reason; };
SNXSAutoDisable g_NXSeaAD[];
int             g_NXSeaAD_N = 0;

int NXS_EA_Learner_Load(){
   if(!InpLearner_Enable) return 0;
   int fh = FileOpen("NEXUS\\auto_disable.csv",
                     FILE_READ | FILE_CSV | FILE_ANSI | FILE_COMMON, ',');
   if(fh == INVALID_HANDLE) return 0;
   ArrayResize(g_NXSeaAD, 0);
   g_NXSeaAD_N = 0;
   while(!FileIsEnding(fh)){
      string c1 = FileReadString(fh);
      if(c1 == "" || c1 == "strategy") continue;
      string c2 = FileReadString(fh);
      string c3 = FileReadString(fh);
      ArrayResize(g_NXSeaAD, g_NXSeaAD_N + 1);
      g_NXSeaAD[g_NXSeaAD_N].strat   = c1;
      g_NXSeaAD[g_NXSeaAD_N].session = (int)StringToInteger(c2);
      g_NXSeaAD[g_NXSeaAD_N].reason  = c3;
      g_NXSeaAD_N++;
   }
   FileClose(fh);
   PrintFormat("[NXS Learner] loaded %d auto-disable rules", g_NXSeaAD_N);
   return g_NXSeaAD_N;
}

bool NXS_EA_Learner_IsDisabled(string strat, int session, string &reason){
   if(!InpLearner_Enable) return false;
   for(int i = 0; i < g_NXSeaAD_N; ++i){
      if(g_NXSeaAD[i].strat == strat && g_NXSeaAD[i].session == session){
         reason = StringFormat("LEARNER %s/%d %s", strat, session, g_NXSeaAD[i].reason);
         return true;
      }
   }
   return false;
}

// =====================================================================
// VirtSL self-test (deterministico, senza broker). Pilota la macchina a
// stati PURA e le collezioni; da chiamare solo prima del trading.
// =====================================================================
bool NXS_EA_VirtSL_SelfTest(){
   bool ok = true;
   #define VSL_CHK(name,cond) { if(cond){ Print("[VSL TEST] PASS - ", name); } else { ok=false; Print("[VSL TEST] FAIL - ", name); } }

   SNXSVirtSL r; SNXSVSLDecision d;

   // helper record base ARMED buy, virt 2400
   r.positionId=1; r.symbol="GOLD"; r.magic=1; r.direction=+1; r.virtPrice=2400.0;
   r.brokerHardSL=2380.0; r.state=NXS_VSLS_ARMED; r.attempts=0; r.lastAttemptMs=0;
   r.triggerTime=0; r.confirmSource="";

   // 1. OFF == baseline: Active() falso, Check no-op
   //    (verifica statica: la modalita' OFF non arma nulla)
   VSL_CHK("OFF: nessun record armato con mode OFF",
           (InpVirtSL_Mode==NXS_VSL_OFF) ? (ArraySize(g_NXSeaVSL)==0) : true);

   // 2. hard SL invalido -> false, mai SL=0
   double hs;
   VSL_CHK("hard SL invalido (atr<=0) -> false",
           NXS_VSL_ComputeHardSL(+1, 2400.0, 0.0, hs)==false && hs==0.0);

   // 3. ARMED + no hit -> resta ARMED (EXECUTE)
   NXS_VSL_Decide(r, NXS_VSL_EXECUTE, true, false, false, 1000, d);
   VSL_CHK("ARMED senza hit resta ARMED", d.newState==NXS_VSLS_ARMED && !d.issueClose);

   // 4. ARMED + hit -> TRIGGERED, nessuna chiusura ancora
   NXS_VSL_Decide(r, NXS_VSL_EXECUTE, true, false, true, 1000, d);
   VSL_CHK("ARMED+hit -> TRIGGERED", d.newState==NXS_VSLS_TRIGGERED && !d.issueClose);

   // 5. TRIGGERED -> CLOSE_REQ con primo tentativo
   r.state=NXS_VSLS_TRIGGERED;
   NXS_VSL_Decide(r, NXS_VSL_EXECUTE, true, false, true, 1000, d);
   VSL_CHK("TRIGGERED -> CLOSE_REQ + issueClose", d.newState==NXS_VSLS_CLOSE_REQ && d.issueClose);

   // 6. CONFIRMED mai da DONE/PLACED: solo posExists==false o ledgerFinal
   r.state=NXS_VSLS_CLOSE_REQ; r.attempts=1; r.lastAttemptMs=1000;
   NXS_VSL_Decide(r, NXS_VSL_EXECUTE, true, true, true, 99999, d);   // ledgerFinal
   VSL_CHK("conferma via LEDGER_FINAL", d.confirmed && d.confirmSource=="LEDGER_FINAL");
   NXS_VSL_Decide(r, NXS_VSL_EXECUTE, false, false, true, 99999, d); // position gone
   VSL_CHK("conferma via POSITION_GONE", d.confirmed && d.confirmSource=="POSITION_GONE");

   // 7. backoff: non ritenta prima del tempo
   r.state=NXS_VSLS_CLOSE_REQ; r.attempts=1; r.lastAttemptMs=1000;
   NXS_VSL_Decide(r, NXS_VSL_EXECUTE, true, false, true, 1000+50, d);
   VSL_CHK("CLOSE_REQ rispetta backoff (no retry immediato)", !d.issueClose);

   // 8. escalation dopo MaxTries, e ESCALATED continua a ritentare
   r.state=NXS_VSLS_CLOSE_REQ; r.attempts=InpVirtSL_MaxTries; r.lastAttemptMs=0;
   NXS_VSL_Decide(r, NXS_VSL_EXECUTE, true, false, true, 999999, d);
   VSL_CHK("MaxTries -> ESCALATED (non terminale) + retry", d.newState==NXS_VSLS_ESCALATED && d.escalated && d.issueClose);
   r.state=NXS_VSLS_ESCALATED; r.attempts=InpVirtSL_MaxTries+3; r.lastAttemptMs=0;
   NXS_VSL_Decide(r, NXS_VSL_EXECUTE, true, false, true, 999999, d);
   VSL_CHK("ESCALATED continua a ritentare finche' non confermato", d.issueClose && d.newState==NXS_VSLS_ESCALATED);

   // 9. OBSERVE: ARMED+hit -> TRIGGERED ma MAI issueClose
   r.state=NXS_VSLS_ARMED;
   NXS_VSL_Decide(r, NXS_VSL_OBSERVE, true, false, true, 1000, d);
   VSL_CHK("OBSERVE: hit segnala TRIGGERED ma non chiude", d.newState==NXS_VSLS_TRIGGERED && !d.issueClose);

   // 10. partial close NON conferma: posizione ancora presente, ledger non FINAL
   r.state=NXS_VSLS_CLOSE_REQ; r.attempts=1; r.lastAttemptMs=0;
   NXS_VSL_Decide(r, NXS_VSL_EXECUTE, true, false, true, 999999, d);
   VSL_CHK("partial close non conferma il record", !d.confirmed && d.newState!=NXS_VSLS_CONFIRMED);

   // 11. due pending contemporanei + fill in ordine inverso (match per order_ticket)
   ArrayResize(g_NXSeaVSLPend, 0);
   if(NXS_VSL_Active()){
      NXS_VSL_PendingAdd(1001, "GOLD", 1, +1, "MACD", 2400.0, 2380.0);
      NXS_VSL_PendingAdd(1002, "GOLD", 1, -1, "TSI",  2500.0, 2520.0);
      VSL_CHK("due pending contemporanei", ArraySize(g_NXSeaVSLPend)==2);
      VSL_CHK("match fill inverso: 1002 poi 1001",
              _nxs_vsl_pendIdxByOrder(1002)>=0 && _nxs_vsl_pendIdxByOrder(1001)>=0);
      _nxs_vsl_pendRemove(_nxs_vsl_pendIdxByOrder(1002));
      VSL_CHK("dopo fill 1002 resta solo 1001",
              ArraySize(g_NXSeaVSLPend)==1 && _nxs_vsl_pendIdxByOrder(1001)>=0);
      ArrayResize(g_NXSeaVSLPend, 0);
   } else {
      Print("[VSL TEST] SKIP pending (mode OFF) — riesegui con mode OBSERVE/EXECUTE");
   }

   // 12. Register idempotente (fill parziale/multiplo dello stesso ordine=1 pos)
   ArrayResize(g_NXSeaVSL, 0);
   if(NXS_VSL_Active()){
      NXS_EA_VirtSL_Register(7001, "GOLD", 1, +1, 2400.0, 2380.0);
      NXS_EA_VirtSL_Register(7001, "GOLD", 1, +1, 2400.0, 2380.0);
      VSL_CHK("Register idempotente per positionId", ArraySize(g_NXSeaVSL)==1);
      ArrayResize(g_NXSeaVSL, 0);
   }

   Print(ok ? "[VSL TEST] TUTTI I TEST PASS" : "[VSL TEST] FALLIMENTI PRESENTI");
   #undef VSL_CHK
   return ok;
}

#endif // __NXS_EDGEADAPTIVE_MQH__
