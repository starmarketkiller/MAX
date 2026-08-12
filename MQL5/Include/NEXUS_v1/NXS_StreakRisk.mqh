//+------------------------------------------------------------------+
//|  NXS_StreakRisk.mqh                                              |
//|  Moltiplicatore di rischio PER-STRATEGIA dopo perdite consecutive |
//|  (12/08, richiesta esplicita dell'utente - conto piccolo, ~200-  |
//|  300 EUR, vuole recuperare piu' in fretta dopo una serie di      |
//|  perdite invece di aspettare passivamente).                      |
//|                                                                    |
//|  ATTENZIONE — e' l'OPPOSTO concettuale di due meccanismi gia'     |
//|  esistenti in NXS_Risk.mqh:                                       |
//|    - NXS_AntiBleedMultiplier (InpUseAntiBleed): RIDUCE il rischio |
//|      dopo perdite consecutive (0.7/0.7/0.4x) - difensivo.         |
//|    - g_streakLotMult (InpUseStreakSizing): sale dopo VITTORIE,    |
//|      scende dopo perdite - "cavalca la mano calda".               |
//|  Questo modulo AUMENTA il rischio dopo perdite - e' martingale-   |
//|  style per costruzione. Cappato esplicitamente (mai un raddoppio  |
//|  puro) e per-strategia, non a livello di conto, per non far       |
//|  scattare tutte le scale insieme se il mercato va storto per      |
//|  tutte le strategie contemporaneamente (correlazione).            |
//|                                                                    |
//|  NON abilitare insieme a InpUseAntiBleed/InpUseStreakSizing sulla |
//|  stessa strategia: direzioni opposte, l'effetto netto (che si     |
//|  moltiplicano in NXS_CalcLotRisk) sarebbe imprevedibile e non     |
//|  auditabile. Restano comunque entrambi soggetti a                 |
//|  InpMaxRiskAtMinLotPct e InpMaxAggregateRiskPct — questo modulo   |
//|  non puo' MAI bypassarli.                                         |
//+------------------------------------------------------------------+
#ifndef __NXS_STREAK_RISK_MQH__
#define __NXS_STREAK_RISK_MQH__

#define NXS_SRISK_MAX_NAMES 48

struct SNxsStreakRisk {
   string name;
   int    consecLosses;
   double mult;          // 1.0 = base, sale fino a InpSRisk_MaxMult
};

SNxsStreakRisk g_streakRisk[NXS_SRISK_MAX_NAMES];
int            g_streakRiskCount = 0;

int _nxs_srisk_idx(const string name){
   for(int i = 0; i < g_streakRiskCount; i++)
      if(g_streakRisk[i].name == name) return i;
   if(g_streakRiskCount >= NXS_SRISK_MAX_NAMES) return -1;
   int idx = g_streakRiskCount;
   g_streakRisk[idx].name = name;
   g_streakRisk[idx].consecLosses = 0;
   g_streakRisk[idx].mult = 1.0;
   g_streakRiskCount++;
   return idx;
}

// Moltiplicatore corrente per la strategia (1.0 = nessuna scalata attiva,
// comportamento invariato se InpUseLossStreakScaling e' off).
double NXS_StreakRisk_Mult(const string name){
   if(!InpUseLossStreakScaling) return 1.0;
   if(StringLen(name) == 0) return 1.0;
   int i = _nxs_srisk_idx(name);
   if(i < 0) return 1.0;
   return g_streakRisk[i].mult;
}

// Da chiamare UNA volta per trade logico chiuso, stesso punto e stesso pnl
// netto gia' usati da NXS_OnTradeClosed (NXS_EA_OnLogicalClose).
void NXS_StreakRisk_OnTradeClosed(const string name, double pnl){
   if(!InpUseLossStreakScaling) return;
   if(StringLen(name) == 0) return;
   int i = _nxs_srisk_idx(name);
   if(i < 0) return;

   if(pnl < 0){
      g_streakRisk[i].consecLosses++;
      int n = g_streakRisk[i].consecLosses;
      int step = MathMax(1, InpSRisk_LossesToScale);
      if(n >= step && n % step == 0){
         double before = g_streakRisk[i].mult;
         double after  = MathMin(InpSRisk_MaxMult, before * InpSRisk_ScaleStep);
         g_streakRisk[i].mult = after;
         if(after > before + 1e-9)
            PrintFormat("[NEXUS SRISK] %s: %d perdite consecutive -> moltiplicatore %.2f -> %.2f (tetto %.2f)",
                        name, n, before, after, InpSRisk_MaxMult);
      }
   } else if(pnl > 0){
      // Reset alla PRIMA vincita — richiesta esplicita dell'utente, non
      // serve azzerare lo streak di perdite prima di tornare a rischio base.
      if(g_streakRisk[i].mult > 1.0 + 1e-9)
         PrintFormat("[NEXUS SRISK] %s: vincita -> moltiplicatore resettato a 1.00 (era %.2f)",
                     name, g_streakRisk[i].mult);
      g_streakRisk[i].consecLosses = 0;
      g_streakRisk[i].mult = 1.0;
   }
   // pnl == 0 (breakeven): stato invariato, ne' scala ne' resetta.
}

// Serializzazione per NXS_State.mqh (persistenza attraverso i riavvii).
int NXS_StreakRisk_Count(){ return g_streakRiskCount; }
string NXS_StreakRisk_NameAt(int i){        return (i>=0 && i<g_streakRiskCount) ? g_streakRisk[i].name : ""; }
int    NXS_StreakRisk_LossesAt(int i){      return (i>=0 && i<g_streakRiskCount) ? g_streakRisk[i].consecLosses : 0; }
double NXS_StreakRisk_MultAt(int i){        return (i>=0 && i<g_streakRiskCount) ? g_streakRisk[i].mult : 1.0; }

void NXS_StreakRisk_Restore(const string name, int losses, double mult){
   if(StringLen(name) == 0) return;
   int i = _nxs_srisk_idx(name);
   if(i < 0) return;
   g_streakRisk[i].consecLosses = MathMax(0, losses);
   g_streakRisk[i].mult = (mult > 0 ? mult : 1.0);
}

#endif
