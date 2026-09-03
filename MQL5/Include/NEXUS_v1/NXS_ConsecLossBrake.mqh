//+------------------------------------------------------------------+
//| NXS_ConsecLossBrake.mqh                                            |
//| 31/08 - freno alle perdite consecutive per strategia, agganciato   |
//| nel POSTO GIUSTO stavolta.                                         |
//|                                                                    |
//| Scoperto stanotte: InpUseStrategyCD (cooldown), InpUseDirCooldown  |
//| e InpAntiRevenge vivono tutti in un blocco di NEXUS_EA_v2.mq5 che  |
//| gira SOLO quando InpUseStrategyProfiles=false - ma SAR (e ogni     |
//| strategia con un profilo) passa dal percorso "a profili" (riga     |
//| ~1226), che chiama NXS_OpenTrade() direttamente e non attraversa   |
//| mai quel blocco. Verificato con un test A/B identico (stesso PF    |
//| 0.29, stesso -$808.46, 17 perdite consecutive) con anti-revenge    |
//| acceso o spento - zero differenza, zero log "anti_revenge".        |
//|                                                                    |
//| NXS_OpenTrade() e' invece il vero gatekeeper (confermato: chiama   |
//| NXS_CommonExposurePreflight, dove RiskShield/CLUSTER_CAP - che     |
//| infatti scattavano regolarmente - vivono davvero). Il freno va     |
//| quindi controllato LI', non nel blocco morto.                      |
//+------------------------------------------------------------------+
#ifndef __NXS_CONSECLOSSBRAKE_MQH__
#define __NXS_CONSECLOSSBRAKE_MQH__

#define NXS_CLB_MAX 32
string   g_clbName[NXS_CLB_MAX];
int      g_clbConsec[NXS_CLB_MAX];
datetime g_clbUntil[NXS_CLB_MAX];
int      g_clbCount = 0;

int _NXS_CLB_FindOrCreate(string name){
   for(int i = 0; i < g_clbCount; i++)
      if(g_clbName[i] == name) return i;
   if(g_clbCount >= NXS_CLB_MAX) return -1;
   g_clbName[g_clbCount] = name;
   g_clbConsec[g_clbCount] = 0;
   g_clbUntil[g_clbCount] = 0;
   int idx = g_clbCount;
   g_clbCount++;
   return idx;
}

// Chiamato da NXS_OpenTrade prima di aprire - true = blocca l'ingresso.
bool NXS_ConsecLossBrake_Blocked(string stratName){
   if(!InpUseConsecLossBrake) return false;
   int idx = _NXS_CLB_FindOrCreate(stratName);
   if(idx < 0) return false;
   if(g_clbUntil[idx] == 0) return false;
   return TimeCurrent() < g_clbUntil[idx];
}

// Chiamato da NXS_EA_OnLogicalClose per OGNI chiusura di posizione (di
// qualunque strategia) - pnl>=0 azzera la catena, pnl<0 la incrementa e,
// raggiunta la soglia, mette la strategia in pausa.
void NXS_ConsecLossBrake_OnClose(string stratName, double pnl){
   if(!InpUseConsecLossBrake) return;
   int idx = _NXS_CLB_FindOrCreate(stratName);
   if(idx < 0) return;
   if(pnl >= 0){
      g_clbConsec[idx] = 0;
      return;
   }
   g_clbConsec[idx]++;
   if(g_clbConsec[idx] >= InpConsecLossBrakeMax){
      g_clbUntil[idx] = TimeCurrent() + (datetime)(InpConsecLossBrakeMin * 60);
      g_clbConsec[idx] = 0;
      PrintFormat("[NEXUS CLB] '%s' in pausa per %d min dopo %d perdite consecutive",
                  stratName, InpConsecLossBrakeMin, InpConsecLossBrakeMax);
   }
}

#endif
