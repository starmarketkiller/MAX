//+------------------------------------------------------------------+
//|  NXS_Strategies_Elliott.mqh - Elliott Wave (strategia #37)        |
//|  Conta le onde su swing high/low alternati e propone:            |
//|   - CONTINUAZIONE a fine onda 2 (entry per l'onda 3) e onda 4     |
//|     (entry per l'onda 5), sul retracement di Fibonacci.          |
//|   - REVERSAL a fine onda 5 (impulso completo -> correzione).      |
//|  Entry a mercato quando il prezzo è nella zona Fib con conferma.  |
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGIES_ELLIOTT_MQH__
#define __NXS_STRATEGIES_ELLIOTT_MQH__

// Estrae fino a 8 pivot di swing ALTERNATI (più recenti prima).
// type: +1 swing high, -1 swing low. Ritorna il numero di pivot trovati.
int _nxs_ell_pivots(int wing, int maxScan, double &price[], int &type[]){
   int cnt = 0, lastType = 0;
   // Parti da wing+1 così lo swing è confermato da barre reali su entrambi i lati
   // (evita pivot "prematuri" letti su barre future inesistenti).
   for(int i = wing + 1; i <= maxScan && cnt < 8; i++){
      bool sh = NXS_IsSwingHigh(g_sym, InpTFEntry, i, wing);
      bool sl = NXS_IsSwingLow (g_sym, InpTFEntry, i, wing);
      int t = sh ? +1 : (sl ? -1 : 0);
      if(t == 0 || t == lastType) continue;   // salta pivot dello stesso tipo consecutivi
      price[cnt] = (t == +1) ? iHigh(g_sym, InpTFEntry, i) : iLow(g_sym, InpTFEntry, i);
      type[cnt]  = t;
      lastType   = t;
      cnt++;
   }
   return cnt;
}

double _nxs_ell_retrace(double a, double b, double cur){
   double range = MathAbs(b - a);
   if(range <= 0) return -1;
   return MathAbs(b - cur) / range;   // frazione ritracciata da b verso a
}

SNXSSignal NXS_Strat_Elliott(){
   SNXSSignal s; ZeroMemory(s); s.dir = DIR_NONE;
   s.strat = STRAT_STRUCT_REACT; s.stratName = "ELLIOTT";
   if(!InpUseStrat_Elliott) return s;

   double atr = (g_atr > 0 ? g_atr : g_point * 100.0);
   int    wing = (InpEllSwingWing > 0 ? InpEllSwingWing : 3);
   double p[8]; int t[8];
   int np = _nxs_ell_pivots(wing, 100, p, t);
   if(np < 3) return s;

   double bid = SymbolInfoDouble(g_sym, SYMBOL_BID);
   double ask = SymbolInfoDouble(g_sym, SYMBOL_ASK);
   double c1  = iClose(g_sym, InpTFEntry, 1);
   double o1  = iOpen (g_sym, InpTFEntry, 1);
   bool bull1 = c1 > o1;   // conferma barra rialzista
   bool bear1 = c1 < o1;

   double rMin = InpEllRetraceMin, rMax = InpEllRetraceMax;
   double sc   = InpEllMinScore;

   // ---------------- CONTINUAZIONE (fine onda 2 -> onda 3) ----------------
   // UP: pivot[0]=L2(-1), pivot[1]=H1(+1), pivot[2]=L0(-1)
   if(t[0] == -1 && t[1] == +1 && t[2] == -1){
      double L2 = p[0], H1 = p[1], L0 = p[2];
      if(H1 > L0 && L2 > L0){                       // onda1 su, onda2 non rompe l'inizio
         double retr = _nxs_ell_retrace(L0, H1, L2);
         if(retr >= rMin && retr <= rMax && bull1 && bid <= H1){
            s.dir = DIR_BUY; s.entryRef = ask;
            s.slPrice = MathMin(L2, L0) - 0.4 * atr;
            s.tpPrice = L2 + 1.618 * (H1 - L0);      // proiezione onda 3
            s.score   = sc + 4.0;
            s.reason  = "ELLIOTT W2->W3 buy";
            return s;
         }
      }
   }
   // DOWN: pivot[0]=H2(+1), pivot[1]=L1(-1), pivot[2]=H0(+1)
   if(t[0] == +1 && t[1] == -1 && t[2] == +1){
      double H2 = p[0], L1 = p[1], H0 = p[2];
      if(L1 < H0 && H2 < H0){
         double retr = _nxs_ell_retrace(H0, L1, H2);
         if(retr >= rMin && retr <= rMax && bear1 && bid >= L1){
            s.dir = DIR_SELL; s.entryRef = bid;
            s.slPrice = MathMax(H2, H0) + 0.4 * atr;
            s.tpPrice = H2 - 1.618 * (H0 - L1);
            s.score   = sc + 4.0;
            s.reason  = "ELLIOTT W2->W3 sell";
            return s;
         }
      }
   }

   // ---------------- CONTINUAZIONE (fine onda 4 -> onda 5) ----------------
   // UP: L4(-1),H3(+1),L2(-1),H1(+1),L0(-1) — no overlap: L4 > H1
   if(np >= 5 && t[0] == -1 && t[1] == +1 && t[2] == -1 && t[3] == +1 && t[4] == -1){
      double L4 = p[0], H3 = p[1], L2 = p[2], H1 = p[3], L0 = p[4];
      if(H3 > H1 && H1 > L0 && L2 > L0 && L4 > H1){   // impulso valido, onda4 non entra nell'onda1
         double retr = _nxs_ell_retrace(L2, H3, L4);
         if(retr >= 0.236 && retr <= 0.618 && bull1 && bid <= H3){
            s.dir = DIR_BUY; s.entryRef = ask;
            s.slPrice = L4 - 0.4 * atr;
            s.tpPrice = L4 + 1.0 * (H3 - L2);          // onda5 ~ onda1..3
            s.score   = sc;
            s.reason  = "ELLIOTT W4->W5 buy";
            return s;
         }
      }
   }
   // DOWN
   if(np >= 5 && t[0] == +1 && t[1] == -1 && t[2] == +1 && t[3] == -1 && t[4] == +1){
      double H4 = p[0], L3 = p[1], H2 = p[2], L1 = p[3], H0 = p[4];
      if(L3 < L1 && L1 < H0 && H2 < H0 && H4 < L1){
         double retr = _nxs_ell_retrace(H2, L3, H4);
         if(retr >= 0.236 && retr <= 0.618 && bear1 && bid >= L3){
            s.dir = DIR_SELL; s.entryRef = bid;
            s.slPrice = H4 + 0.4 * atr;
            s.tpPrice = H4 - 1.0 * (H2 - L3);
            s.score   = sc;
            s.reason  = "ELLIOTT W4->W5 sell";
            return s;
         }
      }
   }

   // ---------------- REVERSAL (fine onda 5) ----------------
   // UP impulse completo: H5,L4,H3,L2,H1,L0 crescenti -> attesa correzione (SELL)
   if(np >= 6 && t[0] == +1 && t[1] == -1 && t[2] == +1 && t[3] == -1 && t[4] == +1 && t[5] == -1){
      double H5 = p[0], L4 = p[1], H3 = p[2], L2 = p[3], H1 = p[4], L0 = p[5];
      if(H5 > H3 && H3 > H1 && L4 > L2 && L2 > L0 && bear1 && bid < H5){
         s.dir = DIR_SELL; s.entryRef = bid;
         s.slPrice = H5 + 0.5 * atr;
         s.tpPrice = H5 - 0.5 * (H5 - L0);            // ritracciamento 50% dell'impulso
         s.score   = sc - 4.0;
         s.reason  = "ELLIOTT W5 reversal sell";
         return s;
      }
   }
   // DOWN impulse completo -> attesa correzione (BUY)
   if(np >= 6 && t[0] == -1 && t[1] == +1 && t[2] == -1 && t[3] == +1 && t[4] == -1 && t[5] == +1){
      double L5 = p[0], H4 = p[1], L3 = p[2], H2 = p[3], L1 = p[4], H0 = p[5];
      if(L5 < L3 && L3 < L1 && H4 < H2 && H2 < H0 && bull1 && ask > L5){
         s.dir = DIR_BUY; s.entryRef = ask;
         s.slPrice = L5 - 0.5 * atr;
         s.tpPrice = L5 + 0.5 * (H0 - L5);
         s.score   = sc - 4.0;
         s.reason  = "ELLIOTT W5 reversal buy";
         return s;
      }
   }

   return s;
}

#endif
