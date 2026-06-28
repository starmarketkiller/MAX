//+------------------------------------------------------------------+
//|  NXS_ShadowTrading.mqh                                           |
//|  NEXUS v2.0.8 — Shadow Trade Logger + Forensics                  |
//|                                                                   |
//|  Registra signal generati ma BLOCCATI dai gate. Dopo N barre     |
//|  valuta retroattivamente se TP1/SL sarebbero stati colpiti e     |
//|  esporta CSV/JSON/MD + push backend.                              |
//+------------------------------------------------------------------+
#ifndef __NXS_SHADOWTRADING_MQH__
#define __NXS_SHADOWTRADING_MQH__

#define NXS_SHADOW_MAX     512    // ring buffer entries
#define NXS_SHADOW_EVAL_BARS 24   // lookahead bars for forensics

enum ENUM_NXS_SHADOW_OUTCOME {
   SHADOW_PENDING  = 0,
   SHADOW_WOULD_WIN,        // TP1 hit before SL
   SHADOW_WOULD_LOSS,       // SL hit before TP1
   SHADOW_WOULD_BE,         // TP1 hit then closed at BE
   SHADOW_STILL_OPEN,       // expired N bars without TP/SL
   SHADOW_INVALID_DATA,     // missing OHLC
};

struct SNXSShadowEntry {
   long      bornBarTime;        // bar time at signal generation
   string    symbol;
   string    timeframe;
   string    strategy;
   int       dir;                // +1 buy / -1 sell
   double    baseScore;
   double    finalScore;
   double    threshold;
   string    blockerPrimary;
   string    blockerSecondary;
   double    entryRef;
   double    slPrice;
   double    tp1Price;
   double    tp2Price;
   string    reasonBlock;
   string    htfBias;
   string    velocityState;
   string    sweepState;
   string    sessionName;
   double    spreadPts;
   double    atrAtBirth;
   string    marketRegime;
   // forensics (filled by evaluator)
   int       outcome;            // ENUM_NXS_SHADOW_OUTCOME
   double    mfeR;               // max favorable excursion (in R units)
   double    maeR;               // max adverse excursion
   double    realizedR;          // final R if WOULD_WIN/LOSS
   int       barsToOutcome;
   bool      evaluated;
};

SNXSShadowEntry g_shadow[NXS_SHADOW_MAX];
int g_shadowCount = 0;
int g_shadowHead  = 0;            // ring buffer head
datetime g_shadowLastExport = 0;
datetime g_shadowLastPush   = 0;

string _shadow_tf_str(){
   // v2.0.9 — independent from chart period: use configured entry TF
   ENUM_TIMEFRAMES tf = (ENUM_TIMEFRAMES)InpTFEntry;
   return EnumToString(tf);
}

string _shadow_outcome_str(int oc){
   switch(oc){
      case SHADOW_WOULD_WIN:   return "WOULD_WIN";
      case SHADOW_WOULD_LOSS:  return "WOULD_LOSS";
      case SHADOW_WOULD_BE:    return "WOULD_BE";
      case SHADOW_STILL_OPEN:  return "STILL_OPEN";
      case SHADOW_INVALID_DATA:return "INVALID_DATA";
      default:                 return "PENDING";
   }
}

// Push (record) a blocked signal into the shadow log
void NXS_Shadow_Record(const SNXSSignal &sig,
                      const double finalScore,
                      const double threshold,
                      const string blockerPrimary,
                      const string blockerSecondary,
                      const string reasonBlock,
                      const string htfBias,
                      const string velocityState,
                      const string sweepState,
                      const string sessionName,
                      const string marketRegime)
{
   if(!InpEnableShadowTrading) return;
   if(sig.dir == DIR_NONE) return;
   // dedup: same strategy+dir within 2 bars
   datetime t0 = iTime(g_sym, InpTFEntry, 0);
   for(int i = 0; i < g_shadowCount; i++){
      int idx = (g_shadowHead - 1 - i + NXS_SHADOW_MAX) % NXS_SHADOW_MAX;
      if(g_shadow[idx].bornBarTime < (long)t0 - 2 * PeriodSeconds(InpTFEntry)) break;
      if(g_shadow[idx].strategy == sig.stratName &&
         g_shadow[idx].dir      == sig.dir       &&
         !g_shadow[idx].evaluated) return;
   }
   SNXSShadowEntry e; ZeroMemory(e);
   e.bornBarTime    = (long)t0;
   e.symbol         = g_sym;
   e.timeframe      = _shadow_tf_str();
   e.strategy       = sig.stratName;
   e.dir            = (sig.dir == DIR_BUY ? +1 : (sig.dir == DIR_SELL ? -1 : 0));
   e.baseScore      = sig.score;
   e.finalScore     = finalScore;
   e.threshold      = threshold;
   e.blockerPrimary = blockerPrimary;
   e.blockerSecondary = blockerSecondary;
   e.entryRef       = sig.entryRef;
   e.slPrice        = sig.slPrice;
   e.tp1Price       = sig.tpPrice;     // primary TP
   // TP2 = 2x reward
   double slDist    = MathAbs(sig.entryRef - sig.slPrice);
   e.tp2Price       = (e.dir > 0)
                      ? sig.entryRef + 2.0 * slDist
                      : sig.entryRef - 2.0 * slDist;
   e.reasonBlock    = reasonBlock;
   e.htfBias        = htfBias;
   e.velocityState  = velocityState;
   e.sweepState     = sweepState;
   e.sessionName    = sessionName;
   e.spreadPts      = (double)(SymbolInfoInteger(g_sym, SYMBOL_SPREAD));
   e.atrAtBirth     = g_atr;
   e.marketRegime   = marketRegime;
   e.outcome        = SHADOW_PENDING;
   e.evaluated      = false;
   g_shadow[g_shadowHead] = e;
   g_shadowHead = (g_shadowHead + 1) % NXS_SHADOW_MAX;
   if(g_shadowCount < NXS_SHADOW_MAX) g_shadowCount++;
}

// Evaluate any pending shadow entries that have aged >= NXS_SHADOW_EVAL_BARS
void NXS_Shadow_Evaluate(){
   if(!InpEnableShadowTrading) return;
   datetime tNow = iTime(g_sym, InpTFEntry, 0);
   long secPerBar = PeriodSeconds(InpTFEntry);

   for(int k = 0; k < g_shadowCount; k++){
      int idx = (g_shadowHead - 1 - k + NXS_SHADOW_MAX) % NXS_SHADOW_MAX;
      if(g_shadow[idx].evaluated) continue;
      long age = ((long)tNow - g_shadow[idx].bornBarTime) / secPerBar;
      if(age < NXS_SHADOW_EVAL_BARS) continue;
      if(g_shadow[idx].symbol != g_sym) continue;
      // walk bars from oldest to newest checking TP1/SL hit
      double slP   = g_shadow[idx].slPrice;
      double tp1P  = g_shadow[idx].tp1Price;
      double entry = g_shadow[idx].entryRef;
      double slDist = MathAbs(entry - slP);
      if(slDist <= 0){
         g_shadow[idx].outcome = SHADOW_INVALID_DATA;
         g_shadow[idx].evaluated = true;
         continue;
      }
      bool tpHit = false, slHit = false;
      double mfeAbs = 0.0, maeAbs = 0.0;
      int hitBar = NXS_SHADOW_EVAL_BARS;
      // iterate from oldest bar (idx 1) up to (NXS_SHADOW_EVAL_BARS)
      // we look back from current bar to find post-signal bars
      for(int b = NXS_SHADOW_EVAL_BARS; b >= 1; b--){
         datetime bt = iTime(g_sym, InpTFEntry, b);
         if(bt < g_shadow[idx].bornBarTime) continue;   // before signal
         double h = iHigh(g_sym, InpTFEntry, b);
         double l = iLow (g_sym, InpTFEntry, b);
         double mfe = (g_shadow[idx].dir > 0) ? (h - entry) : (entry - l);
         double mae = (g_shadow[idx].dir > 0) ? (entry - l) : (h - entry);
         if(mfe > mfeAbs) mfeAbs = mfe;
         if(mae > maeAbs) maeAbs = mae;
         if(g_shadow[idx].dir > 0){
            if(l <= slP && !tpHit){ slHit = true; hitBar = b; break; }
            if(h >= tp1P){ tpHit = true; hitBar = b; break; }
         } else {
            if(h >= slP && !tpHit){ slHit = true; hitBar = b; break; }
            if(l <= tp1P){ tpHit = true; hitBar = b; break; }
         }
      }
      g_shadow[idx].mfeR = mfeAbs / slDist;
      g_shadow[idx].maeR = maeAbs / slDist;
      g_shadow[idx].barsToOutcome = NXS_SHADOW_EVAL_BARS - hitBar;
      if(tpHit){
         g_shadow[idx].outcome = SHADOW_WOULD_WIN;
         g_shadow[idx].realizedR = MathAbs(tp1P - entry) / slDist;
      } else if(slHit){
         g_shadow[idx].outcome = SHADOW_WOULD_LOSS;
         g_shadow[idx].realizedR = -1.0;
      } else {
         g_shadow[idx].outcome = SHADOW_STILL_OPEN;
         g_shadow[idx].realizedR = 0.0;
      }
      g_shadow[idx].evaluated = true;
   }
}

string NXS_Shadow_RowCSV(const SNXSShadowEntry &e){
   string s = "";
   s += IntegerToString(e.bornBarTime) + ",";
   s += e.symbol + ",";
   s += e.timeframe + ",";
   s += e.strategy + ",";
   s += IntegerToString(e.dir) + ",";
   s += DoubleToString(e.baseScore,2) + ",";
   s += DoubleToString(e.finalScore,2) + ",";
   s += DoubleToString(e.threshold,2) + ",";
   s += e.blockerPrimary + ",";
   s += e.blockerSecondary + ",";
   s += DoubleToString(e.entryRef,5) + ",";
   s += DoubleToString(e.slPrice,5) + ",";
   s += DoubleToString(e.tp1Price,5) + ",";
   s += DoubleToString(e.tp2Price,5) + ",";
   s += e.htfBias + ",";
   s += e.velocityState + ",";
   s += e.sweepState + ",";
   s += e.sessionName + ",";
   s += DoubleToString(e.spreadPts,1) + ",";
   s += DoubleToString(e.atrAtBirth,5) + ",";
   s += e.marketRegime + ",";
   s += _shadow_outcome_str(e.outcome) + ",";
   s += DoubleToString(e.mfeR,2) + ",";
   s += DoubleToString(e.maeR,2) + ",";
   s += DoubleToString(e.realizedR,2) + ",";
   s += IntegerToString(e.barsToOutcome);
   return s;
}

void NXS_Shadow_ExportCSV(){
   if(!InpEnableShadowTrading) return;
   string fn = StringFormat("NEXUS\\nexus_shadow_%s_%s.csv",
                            g_sym, _shadow_tf_str());
   int fh = FileOpen(fn, FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON, ',');
   if(fh == INVALID_HANDLE){
      fh = FileOpen(fn, FILE_WRITE|FILE_CSV|FILE_ANSI, ',');
   }
   if(fh == INVALID_HANDLE){ PrintFormat("[NXS Shadow] cannot open %s", fn); return; }
   FileWrite(fh,
      "bornBarTime","symbol","tf","strategy","dir","baseScore","finalScore","threshold",
      "blockerPrimary","blockerSecondary","entry","sl","tp1","tp2",
      "htf","vel","sweep","session","spread_pts","atr","regime",
      "outcome","mfeR","maeR","realizedR","barsToOutcome");
   for(int k = 0; k < g_shadowCount; k++){
      int idx = (g_shadowHead - 1 - k + NXS_SHADOW_MAX) % NXS_SHADOW_MAX;
      string line = NXS_Shadow_RowCSV(g_shadow[idx]);
      FileWriteString(fh, line + "\n");
   }
   FileClose(fh);
}

string NXS_Shadow_AggregateJSON(){
   // aggregate counters by strategy + outcome
   string buf = "{\"version\":\"2.0.8\",\"symbol\":\"" + g_sym +
                "\",\"timeframe\":\"" + _shadow_tf_str() + "\"," +
                "\"generated_at\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS) +
                "\",\"total\":" + IntegerToString(g_shadowCount) + ",\"entries\":[";
   bool first = true;
   for(int k = 0; k < g_shadowCount; k++){
      int idx = (g_shadowHead - 1 - k + NXS_SHADOW_MAX) % NXS_SHADOW_MAX;
      if(!first) buf += ",";
      first = false;
      buf += "{";
      buf += "\"bornBarTime\":" + IntegerToString(g_shadow[idx].bornBarTime) + ",";
      buf += "\"strategy\":\""  + g_shadow[idx].strategy + "\",";
      buf += "\"dir\":"         + IntegerToString(g_shadow[idx].dir) + ",";
      buf += "\"baseScore\":"   + DoubleToString(g_shadow[idx].baseScore,2) + ",";
      buf += "\"finalScore\":"  + DoubleToString(g_shadow[idx].finalScore,2) + ",";
      buf += "\"threshold\":"   + DoubleToString(g_shadow[idx].threshold,2) + ",";
      buf += "\"blockerPrimary\":\"" + g_shadow[idx].blockerPrimary + "\",";
      buf += "\"entry\":"  + DoubleToString(g_shadow[idx].entryRef,5) + ",";
      buf += "\"sl\":"     + DoubleToString(g_shadow[idx].slPrice,5)  + ",";
      buf += "\"tp1\":"    + DoubleToString(g_shadow[idx].tp1Price,5) + ",";
      buf += "\"htf\":\""  + g_shadow[idx].htfBias + "\",";
      buf += "\"vel\":\""  + g_shadow[idx].velocityState + "\",";
      buf += "\"sweep\":\"" + g_shadow[idx].sweepState + "\",";
      buf += "\"session\":\"" + g_shadow[idx].sessionName + "\",";
      buf += "\"outcome\":\"" + _shadow_outcome_str(g_shadow[idx].outcome) + "\",";
      buf += "\"mfeR\":"    + DoubleToString(g_shadow[idx].mfeR,2)    + ",";
      buf += "\"maeR\":"    + DoubleToString(g_shadow[idx].maeR,2)    + ",";
      buf += "\"realizedR\":" + DoubleToString(g_shadow[idx].realizedR,2);
      buf += "}";
   }
   buf += "]}";
   return buf;
}

void NXS_Shadow_ExportJSON(){
   if(!InpEnableShadowTrading) return;
   string fn = StringFormat("NEXUS\\nexus_shadow_%s_%s.json",
                            g_sym, _shadow_tf_str());
   int fh = FileOpen(fn, FILE_WRITE|FILE_BIN|FILE_ANSI|FILE_COMMON);
   if(fh == INVALID_HANDLE){
      fh = FileOpen(fn, FILE_WRITE|FILE_BIN|FILE_ANSI);
   }
   if(fh == INVALID_HANDLE) return;
   string j = NXS_Shadow_AggregateJSON();
   uchar bytes[];
   StringToCharArray(j, bytes, 0, StringLen(j));
   FileWriteArray(fh, bytes);
   FileClose(fh);
}

void NXS_Shadow_ExportMD(){
   if(!InpEnableShadowTrading) return;
   // aggregate per-strategy
   string names[64]; int countBlock[64]; int countWin[64]; int countLoss[64];
   double sumR[64]; int N = 0;
   for(int k = 0; k < g_shadowCount; k++){
      int idx = (g_shadowHead - 1 - k + NXS_SHADOW_MAX) % NXS_SHADOW_MAX;
      string sn = g_shadow[idx].strategy;
      int found = -1;
      for(int j = 0; j < N; j++) if(names[j] == sn){ found = j; break; }
      if(found < 0 && N < 64){
         found = N; names[N] = sn; countBlock[N]=0; countWin[N]=0; countLoss[N]=0; sumR[N]=0; N++;
      }
      if(found >= 0){
         countBlock[found]++;
         if(g_shadow[idx].outcome == SHADOW_WOULD_WIN){ countWin[found]++; sumR[found] += g_shadow[idx].realizedR; }
         if(g_shadow[idx].outcome == SHADOW_WOULD_LOSS){ countLoss[found]++; sumR[found] -= 1.0; }
      }
   }
   string fn = "NEXUS\\nexus_shadow_report.md";
   int fh = FileOpen(fn, FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   if(fh == INVALID_HANDLE) fh = FileOpen(fn, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(fh == INVALID_HANDLE) return;
   FileWriteString(fh, "# NEXUS Shadow Trading Report v2.0.8\n\n");
   FileWriteString(fh, StringFormat("Generated: %s · Symbol: %s · TF: %s · Total shadows: %d\n\n",
                                    TimeToString(TimeCurrent()), g_sym, _shadow_tf_str(), g_shadowCount));
   FileWriteString(fh, "| Strategy | Blocked | Would-Win | Would-Loss | WinRate% | Net R |\n");
   FileWriteString(fh, "|----------|--------:|----------:|-----------:|---------:|------:|\n");
   for(int j = 0; j < N; j++){
      int decided = countWin[j] + countLoss[j];
      double wr = decided > 0 ? 100.0 * countWin[j] / decided : 0.0;
      FileWriteString(fh, StringFormat("| %s | %d | %d | %d | %.1f | %+.2f |\n",
         names[j], countBlock[j], countWin[j], countLoss[j], wr, sumR[j]));
   }
   FileClose(fh);
}

void NXS_Shadow_Tick(){
   if(!InpEnableShadowTrading) return;
   NXS_Shadow_Evaluate();
   datetime now = TimeCurrent();
   if((now - g_shadowLastExport) >= InpShadowExportEverySec){
      NXS_Shadow_ExportCSV();
      NXS_Shadow_ExportJSON();
      NXS_Shadow_ExportMD();
      g_shadowLastExport = now;
   }
   if(InpShadowPushToBackend && (now - g_shadowLastPush) >= InpShadowExportEverySec){
      // best-effort WebRequest push
      string url = InpWebURL + "/api/ea/shadow_trades";
      string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";
      string body = NXS_Shadow_AggregateJSON();
      char post[]; ArrayResize(post, StringToCharArray(body, post, 0, StringLen(body), CP_UTF8) - 1);
      char result[]; string resHeaders;
      int rc = WebRequest("POST", url, headers, 5000, post, result, resHeaders);
      if(rc == 200 || rc == 201) g_shadowLastPush = now;
   }
}

#endif // __NXS_SHADOWTRADING_MQH__
