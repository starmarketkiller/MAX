//+------------------------------------------------------------------+
//| NXS_BreakoutAccSharedStateDiagnostic.mq5                          |
//| Phase 7.9E - EA standalone READ-ONLY, zero rischio.                |
//|                                                                    |
//| IPOTESI SPECIFICA da testare (trovata leggendo il codice reale):   |
//| g_breakoutAccState (NXS_Strategies.mqh:1531-1532) e' un UNICO      |
//| struct GLOBALE (lastBarTime + lastFireTime[2]), NON per-timeframe. |
//| Ma NXS_Strat_BreakoutAcc() viene richiamata UNA VOLTA PER OGNI      |
//| PASSAGGIO multi-TF nel collector (NXS_CollectAllSignals, un pass   |
//| per ciascun TF distinto usato da QUALUNQUE strategia nel registro: |
//| M5/M15/M30/H1/H4/D1) - il gate di selettore (NXS_SelectorAllows(9))|
//| non dipende dal TF attivo, quindi la funzione GIRA e AGGIORNA lo   |
//| stato condiviso anche durante i pass H4/H1/M30/M15/M5, usando le   |
//| barre di QUEL TF (non D1) per c1/c2/range/curBar0. Se un pass su   |
//| un TF piu' veloce "spara" un'Acceptance sui SUOI bar, aggiorna     |
//| lastFireTime[dir] con un timestamp MOLTO piu' recente di quanto    |
//| accadrebbe valutando solo D1 - inquinando il cooldown quando poi   |
//| arriva il pass D1 (vero) nella STESSA finestra di tick.            |
//|                                                                    |
//| Questo script replica ESATTAMENTE questo meccanismo (stato         |
//| condiviso fra passaggi multi-TF, stessa cadenza New-Bar-Gate su    |
//| M15) per misurare se collassa il conteggio finale D1 verso ~4.     |
//+------------------------------------------------------------------+
#property strict

string g_sym = "GOLD";
ENUM_TIMEFRAMES g_tfEntry = PERIOD_M15;
datetime g_lastM15Bar = 0;

// Ordine dei pass multi-TF: ESATTO, bit-per-bit, calcolato programmaticamente
// (Phase 7.9F) dal registro reale - NXS_StrategyIdAt(0..52) (NXS_StrategyRegistry.mqh)
// attraversato in ordine, NXS_Profile_TF(id) per ciascuno (NXS_StrategyProfiles.mqh),
// dedup al primo TF distinto incontrato (stessa logica del router reale,
// NEXUS_EA_v2.mq5:683-689). Risultato verificato: H1 (3COMMAS_BOT) -> D1 (ADX_RSI)
// -> M30 (AMD_CONT) -> M15 (AMD_REVERSAL) -> H4 (BJORGUM) -> M5 (LEVEL_CONFLUENCE_M5).
ENUM_TIMEFRAMES g_passes[6] = {PERIOD_H1, PERIOD_D1, PERIOD_M30, PERIOD_M15, PERIOD_H4, PERIOD_M5};

// --- stato CONDIVISO fra tutti i pass, esattamente come g_breakoutAccState reale ---
datetime g_sharedLastBarTime = 0;
datetime g_sharedLastFireTime[2] = {0, 0};   // [0]=buy [1]=sell
long     g_cooldownSecD1 = 8 * 86400;        // cooldown_bars=8 * PeriodSeconds(D1) - COSTANTE nel
                                              // codice reale (calcolato con PeriodSeconds(tf) del
                                              // pass CORRENTE - vedi nota sotto)

long g_nD1RawAccept = 0, g_nD1CooldownPass_isolated = 0, g_nD1CooldownPass_sharedState = 0;
long g_nOtherTfFires = 0;   // quante volte un pass NON-D1 ha "sparato" e sporcato lo stato condiviso
int hAllFires = INVALID_HANDLE;   // log di OGNI sparo (qualunque TF) per l'esempio causale minimo

// stato ISOLATO (solo D1, nessun altro TF tocca questo) - baseline di controllo,
// deve riprodurre il risultato gia' noto (~75-95) se il meccanismo di
// cooldown/cadenza in se' e' corretto.
datetime g_isolatedLastFireTime[2] = {0, 0};

int hOut = INVALID_HANDLE;

// Replica NXS_Strat_BreakoutAcc() per un TF generico, con stato CONDIVISO
// (simula il bug ipotizzato) - ritorna 1=buy -1=sell 0=nessuno, aggiorna SEMPRE
// lo stato condiviso se il gate "gia' valutata questa barra" lo permette.
int EvalSharedState(ENUM_TIMEFRAMES tf){
   datetime curBar0 = iTime(g_sym, tf, 0);
   if(g_sharedLastBarTime == curBar0) return 0;   // stessa barra (qualunque TF) gia' valutata
   g_sharedLastBarTime = curBar0;

   int n = 20;
   int idxHi = iHighest(g_sym, tf, MODE_HIGH, n, 3);
   int idxLo = iLowest(g_sym, tf, MODE_LOW, n, 3);
   if(idxHi < 0 || idxLo < 0) return 0;
   double range_hi = iHigh(g_sym, tf, idxHi);
   double range_lo = iLow(g_sym, tf, idxLo);
   double c1 = iClose(g_sym, tf, 1);
   double c2 = iClose(g_sym, tf, 2);
   bool acceptUp = (c1 > range_hi && c2 > range_hi);
   bool acceptDn = (c1 < range_lo && c2 < range_lo);
   int rawDir = acceptUp ? 1 : (acceptDn ? -1 : 0);
   if(rawDir == 0) return 0;

   // cooldown: nel codice reale, cooldownSec = InpBreakoutAccCooldownBars * PeriodSeconds(tf) -
   // ATTENZIONE: PeriodSeconds(tf) del pass CORRENTE, quindi il cooldown "8 barre" ha un
   // significato in SECONDI diverso per ogni TF (8 barre D1 = 8*86400s, 8 barre H4=8*14400s,
   // ecc.) - replicato fedelmente qui.
   long cooldownSec = 8 * (long)PeriodSeconds(tf);
   int dirIdx = (rawDir == 1) ? 0 : 1;
   bool cooldownOk = (g_sharedLastFireTime[dirIdx] == 0) ||
                     ((curBar0 - g_sharedLastFireTime[dirIdx]) >= cooldownSec);
   if(cooldownOk){
      g_sharedLastFireTime[dirIdx] = curBar0;
      if(tf != PERIOD_D1) g_nOtherTfFires++;
      if(hAllFires != INVALID_HANDLE)
         FileWrite(hAllFires, EnumToString(tf), TimeToString(curBar0, TIME_DATE|TIME_MINUTES),
                   IntegerToString(rawDir), "FIRED_UPDATED_SHARED_STATE");
      return rawDir;
   }
   if(hAllFires != INVALID_HANDLE)
      FileWrite(hAllFires, EnumToString(tf), TimeToString(curBar0, TIME_DATE|TIME_MINUTES),
                IntegerToString(rawDir), "RAW_ACCEPT_BLOCKED_BY_SHARED_COOLDOWN");
   return 0;   // bloccato da cooldown (che puo' essere stato appena aggiornato da un ALTRO TF)
}

// Baseline isolata: stessa logica MA con stato dedicato SOLO a D1 (nessun altro
// TF la tocca) - deve riprodurre ~75-95 (gia' misurato dallo script precedente).
int EvalIsolatedD1(){
   ENUM_TIMEFRAMES tf = PERIOD_D1;
   int n = 20;
   int idxHi = iHighest(g_sym, tf, MODE_HIGH, n, 3);
   int idxLo = iLowest(g_sym, tf, MODE_LOW, n, 3);
   if(idxHi < 0 || idxLo < 0) return 0;
   double range_hi = iHigh(g_sym, tf, idxHi);
   double range_lo = iLow(g_sym, tf, idxLo);
   double c1 = iClose(g_sym, tf, 1);
   double c2 = iClose(g_sym, tf, 2);
   bool acceptUp = (c1 > range_hi && c2 > range_hi);
   bool acceptDn = (c1 < range_lo && c2 < range_lo);
   int rawDir = acceptUp ? 1 : (acceptDn ? -1 : 0);
   if(rawDir == 0) return 0;
   g_nD1RawAccept++;
   long cooldownSec = 8 * 86400;
   int dirIdx = (rawDir == 1) ? 0 : 1;
   bool cooldownOk = (g_isolatedLastFireTime[dirIdx] == 0) ||
                     ((iTime(g_sym, tf, 0) - g_isolatedLastFireTime[dirIdx]) >= cooldownSec);
   if(cooldownOk){
      g_isolatedLastFireTime[dirIdx] = iTime(g_sym, tf, 0);
      g_nD1CooldownPass_isolated++;
      return rawDir;
   }
   return 0;
}

datetime g_lastD1BarForIsolated = 0;

int OnInit(){
   SymbolSelect(g_sym, true);
   hOut = FileOpen("nxs_breakoutacc_sharedstate_diag.csv", FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI, ',');
   if(hOut != INVALID_HANDLE)
      FileWrite(hOut, "d1_bar_time,raw_dir,fired_with_shared_state,event");
   hAllFires = FileOpen("nxs_breakoutacc_sharedstate_allfires.csv", FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_ANSI, ',');
   if(hAllFires != INVALID_HANDLE)
      FileWrite(hAllFires, "tf,bar_time,raw_dir,event");
   return INIT_SUCCEEDED;
}

void OnTick(){
   datetime bt = iTime(g_sym, g_tfEntry, 0);
   if(bt == g_lastM15Bar) return;
   g_lastM15Bar = bt;

   // baseline isolata: valuta D1 UNA VOLTA per nuova barra D1 (indipendente
   // da questo tick M15 - stesso gate del vero g_breakoutAccState.lastBarTime,
   // ma con stato NON condiviso con altri TF).
   datetime d1now = iTime(g_sym, PERIOD_D1, 0);
   if(d1now != g_lastD1BarForIsolated){
      g_lastD1BarForIsolated = d1now;
      EvalIsolatedD1();
   }

   // --- meccanismo con stato CONDIVISO: replica il loop multi-TF reale,
   // un pass per ciascun TF distinto nel registro, TUTTI toccano lo stesso
   // g_sharedLastBarTime/g_sharedLastFireTime.
   int lastD1RawDir = 0;
   for(int p = 0; p < 6; p++){
      int r = EvalSharedState(g_passes[p]);
      if(g_passes[p] == PERIOD_D1) lastD1RawDir = r;
   }
   if(lastD1RawDir != 0){
      if(hOut != INVALID_HANDLE)
         FileWrite(hOut, TimeToString(iTime(g_sym, PERIOD_D1, 0), TIME_DATE), IntegerToString(lastD1RawDir),
                   "1", "D1_FIRED_WITH_SHARED_STATE");
      g_nD1CooldownPass_sharedState++;
   }
}

void OnDeinit(const int reason){
   if(hOut != INVALID_HANDLE) FileClose(hOut);
   if(hAllFires != INVALID_HANDLE) FileClose(hAllFires);
   int hSum = FileOpen("nxs_breakoutacc_sharedstate_diag_summary.txt", FILE_WRITE|FILE_TXT|FILE_COMMON);
   if(hSum != INVALID_HANDLE){
      FileWrite(hSum, "n_d1_raw_accept_isolated=" + IntegerToString(g_nD1RawAccept));
      FileWrite(hSum, "n_d1_cooldown_pass_isolated=" + IntegerToString(g_nD1CooldownPass_isolated));
      FileWrite(hSum, "n_d1_fired_with_shared_state=" + IntegerToString(g_nD1CooldownPass_sharedState));
      FileWrite(hSum, "n_other_tf_fires_that_touched_shared_state=" + IntegerToString(g_nOtherTfFires));
      FileClose(hSum);
   }
   PrintFormat("[SHAREDSTATE_DIAG][SUMMARY] isolated_raw=%d isolated_cooldown_pass=%d "
               "shared_state_d1_fires=%d other_tf_fires=%d",
               g_nD1RawAccept, g_nD1CooldownPass_isolated, g_nD1CooldownPass_sharedState, g_nOtherTfFires);
}
