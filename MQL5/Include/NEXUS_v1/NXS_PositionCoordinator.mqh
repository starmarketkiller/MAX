//+------------------------------------------------------------------+
//| NXS_PositionCoordinator.mqh - one action per position/tick       |
//+------------------------------------------------------------------+
#ifndef __NXS_POSITION_COORDINATOR_MQH__
#define __NXS_POSITION_COORDINATOR_MQH__

#define NXS_PM_MAX_PROPOSALS 512
#define NXS_PM_MAX_APPLIED   512

enum ENUM_NXS_PM_ACTION { NXS_PM_NONE=0, NXS_PM_MODIFY, NXS_PM_PARTIAL, NXS_PM_CLOSE };

struct SNXSPMProposal {
   ulong ticket;
   ENUM_NXS_PM_ACTION action;
   int priority;
   double sl;
   double tp;
   double volume;
   string source;
   string reason;
};

SNXSPMProposal g_nxsPmBest[NXS_PM_MAX_PROPOSALS];
int g_nxsPmBestCount = 0;
ulong g_nxsPmAppliedTicket[NXS_PM_MAX_APPLIED];
string g_nxsPmAppliedSource[NXS_PM_MAX_APPLIED];
int g_nxsPmAppliedCount = 0;

void NXS_PM_BeginCycle(){ g_nxsPmBestCount = 0; }

bool NXS_PM_HasApplied(ulong ticket, string source){
   for(int i=0; i<g_nxsPmAppliedCount; i++)
      if(g_nxsPmAppliedTicket[i] == ticket && g_nxsPmAppliedSource[i] == source) return true;
   return false;
}

void NXS_PM_RecordApplied(ulong ticket, string source){
   if(NXS_PM_HasApplied(ticket, source)) return;
   if(g_nxsPmAppliedCount >= NXS_PM_MAX_APPLIED){
      for(int i=1; i<NXS_PM_MAX_APPLIED; i++){
         g_nxsPmAppliedTicket[i-1] = g_nxsPmAppliedTicket[i];
         g_nxsPmAppliedSource[i-1] = g_nxsPmAppliedSource[i];
      }
      g_nxsPmAppliedCount = NXS_PM_MAX_APPLIED - 1;
   }
   g_nxsPmAppliedTicket[g_nxsPmAppliedCount] = ticket;
   g_nxsPmAppliedSource[g_nxsPmAppliedCount] = source;
   g_nxsPmAppliedCount++;
}

bool NXS_PM_StopDoesNotLoosen(ulong ticket, double proposedSL){
   if(proposedSL <= 0 || !PositionSelectByTicket(ticket)) return proposedSL <= 0;
   long type = PositionGetInteger(POSITION_TYPE);
   double currentSL = PositionGetDouble(POSITION_SL);
   if(currentSL <= 0) return true;
   if(type == POSITION_TYPE_BUY) return proposedSL >= currentSL - g_point;
   if(type == POSITION_TYPE_SELL) return proposedSL <= currentSL + g_point;
   return false;
}

bool NXS_PM_Stricter(const SNXSPMProposal &candidate, const SNXSPMProposal &current){
   if(candidate.priority != current.priority) return candidate.priority > current.priority;
   if(candidate.action != current.action) return candidate.action > current.action;
   if(candidate.action == NXS_PM_MODIFY && PositionSelectByTicket(candidate.ticket)){
      long type = PositionGetInteger(POSITION_TYPE);
      if(type == POSITION_TYPE_BUY && candidate.sl != current.sl) return candidate.sl > current.sl;
      if(type == POSITION_TYPE_SELL && candidate.sl != current.sl) return candidate.sl < current.sl;
   }
   return StringCompare(candidate.source, current.source) < 0;
}

bool NXS_PM_Submit(SNXSPMProposal &proposal){
   if(proposal.ticket == 0 || proposal.action == NXS_PM_NONE) return false;
   if(proposal.action == NXS_PM_MODIFY && !NXS_PM_StopDoesNotLoosen(proposal.ticket, proposal.sl)){
      PrintFormat("[NEXUS MANAGEMENT] rejected stop regression ticket=%I64u source=%s sl=%.8f",
                  proposal.ticket, proposal.source, proposal.sl);
      return false;
   }
   for(int i=0; i<g_nxsPmBestCount; i++){
      if(g_nxsPmBest[i].ticket != proposal.ticket) continue;
      if(NXS_PM_Stricter(proposal, g_nxsPmBest[i])) g_nxsPmBest[i] = proposal;
      return true;
   }
   if(g_nxsPmBestCount >= NXS_PM_MAX_PROPOSALS) return false;
   g_nxsPmBest[g_nxsPmBestCount++] = proposal;
   return true;
}

bool NXS_PM_ProposeModify(ulong ticket, double sl, double tp, int priority,
                          string source, string reason){
   SNXSPMProposal p; p.ticket=ticket; p.action=NXS_PM_MODIFY; p.priority=priority;
   p.sl=sl; p.tp=tp; p.volume=0; p.source=source; p.reason=reason;
   return NXS_PM_Submit(p);
}

bool NXS_PM_ProposePartial(ulong ticket, double volume, int priority,
                           string source, string reason){
   if(NXS_PM_HasApplied(ticket, source)) return false;
   SNXSPMProposal p; p.ticket=ticket; p.action=NXS_PM_PARTIAL; p.priority=priority;
   p.sl=0; p.tp=0; p.volume=volume; p.source=source; p.reason=reason;
   return NXS_PM_Submit(p);
}

bool NXS_PM_ProposeClose(ulong ticket, int priority, string source, string reason){
   SNXSPMProposal p; p.ticket=ticket; p.action=NXS_PM_CLOSE; p.priority=priority;
   p.sl=0; p.tp=0; p.volume=0; p.source=source; p.reason=reason;
   return NXS_PM_Submit(p);
}

void NXS_PM_ApplyCycle(){
   for(int i=0; i<g_nxsPmBestCount; i++){
      SNXSPMProposal p = g_nxsPmBest[i];
      if(!PositionSelectByTicket(p.ticket)) continue;
      bool ok = false;
      if(p.action == NXS_PM_CLOSE) ok = NXS_DoClose(p.ticket);
      else if(p.action == NXS_PM_PARTIAL){
         double step = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
         if(step <= 0) step = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
         double vol = MathFloor(p.volume / step) * step;
         vol = NormalizeDouble(vol, 8);
         if(vol > 0) ok = NXS_DoClosePartial(p.ticket, vol);
      } else if(p.action == NXS_PM_MODIFY && NXS_PM_StopDoesNotLoosen(p.ticket, p.sl))
         ok = NXS_DoModify(p.ticket, NormPrice(p.sl), NormPrice(p.tp));
      PrintFormat("[NEXUS MANAGEMENT] {\"ticket\":\"%I64u\",\"action\":%d,\"priority\":%d,\"source\":\"%s\",\"applied\":%s,\"reason\":\"%s\"}",
                  p.ticket, (int)p.action, p.priority, _JsonEsc(p.source),
                  (ok ? "true" : "false"), _JsonEsc(p.reason));
      if(ok) NXS_PM_RecordApplied(p.ticket, p.source);
   }
   g_nxsPmBestCount = 0;
}

#endif
