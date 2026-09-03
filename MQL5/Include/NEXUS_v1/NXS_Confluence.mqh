//+------------------------------------------------------------------+
//|  NXS_Confluence.mqh - Phase 3: Confluence scoring + per-strategy |
//|  cooldown + ADX_RSI score cap (anti-dominance).                  |
//+------------------------------------------------------------------+
#ifndef __NXS_CONFLUENCE_MQH__
#define __NXS_CONFLUENCE_MQH__

// Per-bar accumulation of strategy directions (filled during scoring loop)
int  g_confBuyCount  = 0;
int  g_confSellCount = 0;

void NXS_ConfluenceReset(){
   g_confBuyCount = 0;
   g_confSellCount = 0;
}

void NXS_ConfluenceRegister(int dir){
   if(dir == +1) g_confBuyCount++;
   else if(dir == -1) g_confSellCount++;
}

// Bonus for the winning direction once all signals have been registered.
int NXS_ConfluenceBonus(int winningDir){
   if(!InpUseConfluence) return 0;
   int n = (winningDir == +1) ? g_confBuyCount : g_confSellCount;
   if(n >= 4) return InpConfluenceBonus4;
   if(n == 3) return InpConfluenceBonus3;
   if(n == 2) return InpConfluenceBonus2;
   return 0;
}

// ---------- Per-strategy cooldown ----------
// Simple parallel arrays keyed by strategy name string.
#define NXS_CD_MAX 32
string   g_cdName[NXS_CD_MAX];
int      g_cdConsec[NXS_CD_MAX];
datetime g_cdUntil[NXS_CD_MAX];
int      g_cdCount = 0;

int _NXS_CD_FindOrCreate(string name){
   for(int i = 0; i < g_cdCount; i++){
      if(g_cdName[i] == name) return i;
   }
   if(g_cdCount >= NXS_CD_MAX) return -1;
   g_cdName[g_cdCount] = name;
   g_cdConsec[g_cdCount] = 0;
   g_cdUntil[g_cdCount] = 0;
   int idx = g_cdCount;
   g_cdCount++;
   return idx;
}

bool NXS_StrategyOnCooldown(string name){
   if(!InpUseStrategyCD) return false;
   int idx = _NXS_CD_FindOrCreate(name);
   if(idx < 0) return false;
   if(g_cdUntil[idx] == 0) return false;
   return TimeCurrent() < g_cdUntil[idx];
}

void NXS_StrategyRegisterTrade(string name){
   if(!InpUseStrategyCD) return;
   int idx = _NXS_CD_FindOrCreate(name);
   if(idx < 0) return;
   // Reset other counters that aren't this strategy (consec means consecutive of same)
   for(int i = 0; i < g_cdCount; i++){
      if(i == idx) continue;
      g_cdConsec[i] = 0;
   }
   g_cdConsec[idx]++;
   if(g_cdConsec[idx] >= InpMaxConsecPerStrat){
      g_cdUntil[idx] = TimeCurrent() + (datetime)(InpStratCooldownMin * 60);
      g_cdConsec[idx] = 0;   // reset after triggering cooldown
      PrintFormat("[NEXUS CD] Strategy '%s' on cooldown until %s",
                  name, TimeToString(g_cdUntil[idx], TIME_MINUTES));
   }
}

// ---------- Per-strategy cooldown DIREZIONALE ----------
// 30/08 - ipotesi ragionata dopo step10: il cooldown esistente (sopra) e'
// cieco alla direzione - blocca "3 trade di fila" anche se alternano
// buy/sell (inversioni legittime), eppure ha alzato il win rate di SAR dal
// 25.9% al 66.9% da solo. Spiegazione probabile: i segnali ravvicinati
// capitano soprattutto nel whipsaw (prezzo che oscilla vicino al punto di
// flip SAR), e la patologia caratterizzata ieri notte era specificamente
// la STESSA direzione ripetuta (catene di 3-4 perdite consecutive stesso
// verso sulla nuda). Questa versione conta solo le ripetizioni nella
// STESSA direzione - non penalizza un'inversione vera, dovrebbe colpire
// il whipsaw in modo piu' chirurgico del cooldown generico.
#define NXS_CDDIR_MAX 32
string   g_cdDirName[NXS_CDDIR_MAX];
int      g_cdDirLast[NXS_CDDIR_MAX];     // ultima direzione vista per questa strategia (+1/-1/0)
int      g_cdDirConsec[NXS_CDDIR_MAX];   // trade consecutivi nella stessa direzione
datetime g_cdDirUntil[NXS_CDDIR_MAX];
int      g_cdDirCount = 0;

int _NXS_CDDIR_FindOrCreate(string name){
   for(int i = 0; i < g_cdDirCount; i++)
      if(g_cdDirName[i] == name) return i;
   if(g_cdDirCount >= NXS_CDDIR_MAX) return -1;
   g_cdDirName[g_cdDirCount] = name;
   g_cdDirLast[g_cdDirCount] = 0;
   g_cdDirConsec[g_cdDirCount] = 0;
   g_cdDirUntil[g_cdDirCount] = 0;
   int idx = g_cdDirCount;
   g_cdDirCount++;
   return idx;
}

bool NXS_StrategyOnDirCooldown(string name){
   if(!InpUseDirCooldown) return false;
   int idx = _NXS_CDDIR_FindOrCreate(name);
   if(idx < 0) return false;
   if(g_cdDirUntil[idx] == 0) return false;
   return TimeCurrent() < g_cdDirUntil[idx];
}

void NXS_StrategyRegisterDirTrade(string name, int dir){
   if(!InpUseDirCooldown) return;
   int idx = _NXS_CDDIR_FindOrCreate(name);
   if(idx < 0) return;
   if(g_cdDirLast[idx] == dir) g_cdDirConsec[idx]++;
   else{ g_cdDirLast[idx] = dir; g_cdDirConsec[idx] = 1; }
   if(g_cdDirConsec[idx] >= InpMaxConsecSameDir){
      g_cdDirUntil[idx] = TimeCurrent() + (datetime)(InpDirCooldownMin * 60);
      g_cdDirConsec[idx] = 0;
      PrintFormat("[NEXUS CDDIR] Strategy '%s' dir=%d in cooldown direzionale fino a %s",
                  name, dir, TimeToString(g_cdDirUntil[idx], TIME_MINUTES));
   }
}

// Snapshot for backend push (compact JSON fragment)
string NXS_CooldownsJSON(){
   string s = "{";
   bool first = true;
   for(int i = 0; i < g_cdCount; i++){
      if(g_cdUntil[i] == 0 && g_cdConsec[i] == 0) continue;
      if(!first) s += ",";
      s += "\"" + g_cdName[i] + "\":{";
      s += "\"consec\":"  + IntegerToString(g_cdConsec[i]) + ",";
      s += "\"untilTs\":" + IntegerToString((int)g_cdUntil[i]);
      s += "}";
      first = false;
   }
   s += "}";
   return s;
}

// ---------- ADX_RSI Score Cap ----------
double NXS_ApplyScoreCap(string stratName, double rawScore){
   if(stratName == "ADX_RSI" && rawScore > InpADXRsiScoreCap){
      return (double)InpADXRsiScoreCap;
   }
   return rawScore;
}

#endif
