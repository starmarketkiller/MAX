//+------------------------------------------------------------------+
//|  NXS_Execution.mqh - Open trades with gates + Close & Reverse     |
//|  AUDITPATCH: precise preflight RC, GateMode, Counter-HTF sizing    |
//+------------------------------------------------------------------+
#ifndef __NXS_EXECUTION_MQH__
#define __NXS_EXECUTION_MQH__

enum ENUM_NXS_OPEN_RC {
   OPEN_OK = 0,
   OPEN_FAIL_INVALID_STOPS,
   OPEN_FAIL_INVALID_VOLUME,
   OPEN_FAIL_PREFLIGHT,
   OPEN_FAIL_SEND
};

// NXS_Protections.mqh è incluso DOPO questo file nell'entrypoint, ma il
// preflight comune deve poter interrogare il blocco protezioni: dichiarazione
// anticipata per non dipendere dall'ordine di include (AUD0-MQL-001).
bool NXS_Prot_EntryBlocked();

string g_nxsLastOpenFailure = "";
int g_nxsCounterSessionKey = -1;
// v2.1.7 — il modello istituzionale lo alza SOLO per l'apertura di gruppo di un
// setup REVERSAL: il gate exhaustion (prezzo lontano da EMA200) ha senso per una
// continuazione che insegue, ma un reversal parte per definizione da un estremo.
// Alzato/riabbassato attorno alla singola NXS_OpenTrade nel branch istituzionale.
bool g_nxsBypassExhaustion = false;
// v2.2.0 — tag di contesto per il comment del trade (4o campo): il branch
// istituzionale lo riempie con "TF-C/R" (es. "H4-R" = timeframe H4, Reversal).
// Se vuoto, NXS_OpenTrade ripiega sul TF di origine del segnale -> ogni trade
// mostra almeno il timeframe. Cosi' guardando la posizione in MT5 si vede
// SUBITO su che TF e con che tipo di setup e' stata aperta.
string g_nxsOpenCtxTag = "";
datetime g_nxsCounterDay = 0;
int g_nxsCounterCount = 0;

void NXS_GateTelemetry(string route, string gateId, bool passed,
                       double observed, double threshold, string reason){
   PrintFormat("[NEXUS GATE] {\"route\":\"%s\",\"gate_id\":\"%s\",\"passed\":%s,\"observed\":%.8g,\"threshold\":%.8g,\"reason\":\"%s\"}",
               _JsonEsc(route), _JsonEsc(gateId), (passed ? "true" : "false"),
               observed, threshold, _JsonEsc(reason));
}

//+------------------------------------------------------------------+
//| Invariante unica di creazione esposizione.                        |
//|                                                                   |
//| L'audit (AUD0-ADD-001/002/003, AUD0-INST-001/002) ha rilevato che |
//| esistevano tre pipeline distinte con sottoinsiemi DIVERSI di       |
//| controlli:                                                        |
//|   1. entry primaria  -> licenza, ruin, margine, RiskShield...     |
//|   2. grid/pyramid    -> solo RiskShield + cap direzionale         |
//|   3. istituzionale   -> nessuno dei precedenti                    |
//|                                                                   |
//| Le verifiche non aggirabili sono state spostate QUI, così ogni     |
//| chiamante le eredita per costruzione e non per convenzione.        |
//+------------------------------------------------------------------+
bool NXS_CommonExposurePreflight(string route, ENUM_NXS_DIR dir, double lots,
                                 ENUM_ORDER_TYPE otype, double price,
                                 double &sl, double &tp, string &reason){
   // --- (1) Licenza / entitlement -----------------------------------------
   // AUD0-ADD-001 / AUD0-EXEC-001: grid e pyramid giravano durante la gestione
   // posizioni, PRIMA che il router raggiungesse il gate di licenza esterno.
   bool licOK = NXS_License_Enforce();
   NXS_GateTelemetry(route, "LICENSE", licOK, 0, 0, licOK ? "" : "license_denied");
   if(!licOK){ reason = "license_denied"; return false; }

   // --- (2) Kill switch di conto ------------------------------------------
   // AUD0-ADD-002: il freeze risk-of-ruin era verificato solo in NXS_OpenTrade,
   // quindi gli add potevano creare esposizione a conto congelato.
   bool ruinOK = !NXS_RuinFrozen();
   NXS_GateTelemetry(route, "RUIN_FREEZE", ruinOK, 0, 0, ruinOK ? "" : "ruin_frozen");
   if(!ruinOK){ reason = "ruin_frozen"; return false; }

   // --- (3) Protezioni giornaliere / pausa --------------------------------
   bool protOK = !NXS_Prot_EntryBlocked();
   NXS_GateTelemetry(route, "PROTECTIONS", protOK, 0, 0, protOK ? "" : "protections_block");
   if(!protOK){ reason = "protections_block"; return false; }

   // --- (4) Stop di protezione obbligatorio -------------------------------
   // AUD0-ADD-005 / AUD0-INST-007 / NXS-EXP-002: grid, pyramid e add
   // istituzionali inviavano ordini con sl=0, cioè posizioni prive di stop
   // lato broker. Nessun percorso può creare esposizione non protetta.
   bool stopPresent = (sl > 0.0);
   NXS_GateTelemetry(route, "HARD_STOP", stopPresent, sl, 0,
                     stopPresent ? "" : "missing_broker_stop");
   if(!stopPresent){
      reason = "missing_broker_stop: ogni ordine deve avere uno stop valido";
      return false;
   }

   // --- (4a) NEXUS-RISK-002: incertezza sullo stato -> nessuna esposizione ---
   //
   // "Uncertainty about live state MUST block new exposure until
   // reconciliation." I singoli stati degradati erano gia' rilevati, ma
   // nessuno di essi impediva di APRIRE: l'EA continuava a creare esposizione
   // mentre non sapeva piu' cosa fosse gia' aperto, con quali stop o con quali
   // impostazioni.
   //
   // Le tre incertezze che contano:
   //   - ledger anti-doppione degradato: non si sa quali chiusure siano note;
   //   - snapshot di stato non ripristinato: non si conosce lo stato gestionale
   //     delle posizioni gia' aperte;
   //   - indicatori illeggibili: la decisione stessa non e' fondata.
   if(NXS_Ledger_IsDegraded()){
      NXS_GateTelemetry(route, "STATE_UNCERTAIN", false, 0, 0, "ledger_degraded");
      reason = "ledger_degraded: stato anti-doppione non affidabile, "
               "nessuna nuova esposizione fino alla riconciliazione";
      return false;
   }
   if(!NXS_State_EntryAllowed()){
      NXS_GateTelemetry(route, "STATE_UNCERTAIN", false, 0, 0, "state_restore_failed");
      reason = "state_restore_failed: snapshot operativo non ripristinato";
      return false;
   }
   if(NXS_IndicatorsDegraded()){
      NXS_GateTelemetry(route, "STATE_UNCERTAIN", false, 0, 0, "indicators_degraded");
      reason = "indicators_degraded: letture di mercato non affidabili";
      return false;
   }

   // --- (4b) Durabilita' del Virtual SL ------------------------------------
   // NXS-VSL-006: in modalita' EXECUTE lo stop LOGICO e' applicato dall'EA
   // mentre al broker arriva uno stop piu' largo. E' una scelta deliberata, ma
   // regge solo finche' l'EA gira, riceve tick e riesce a persistere il proprio
   // stato. Se la persistenza e' rotta, aprire nuova esposizione significa
   // creare posizioni la cui protezione reale e' solo in memoria.
   if(NXS_VSL_Active() && !NXS_VSL_PersistHealthy()){
      NXS_GateTelemetry(route, "VSL_DURABILITY", false, 0, 0, "vsl_persist_unhealthy");
      reason = "vsl_persist_unhealthy: stato Virtual SL non persistibile, "
               "nessuna nuova esposizione";
      return false;
   }

   // --- (5) RiskShield -----------------------------------------------------
   string rsReason = "";
   bool rsBlocked = NXS_RS_BlockEntry(g_sym, rsReason);
   NXS_GateTelemetry(route, "RISKSHIELD", !rsBlocked, 0, 0, rsReason);
   if(rsBlocked){ reason = rsReason; return false; }

   // --- (6) Cap di esposizione direzionale --------------------------------
   double existing = NXS_DirExposureLots(dir);
   double cap = NXS_EffectiveMaxDirExposureLots();
   bool exposureOK = (existing + lots <= cap + 1e-9);
   string exposureReason = exposureOK ? "" :
      StringFormat("existing=%.2f+new=%.2f>cap=%.2f", existing, lots, cap);
   NXS_GateTelemetry(route, "DIR_EXPOSURE", exposureOK, existing + lots, cap,
                     exposureReason);
   if(!exposureOK){ reason = "dir_exposure_cap " + exposureReason; return false; }

   // --- (7) Margine proiettato ---------------------------------------------
   // AUD0-ADD-003: il gate viveva in NXS_OpenTrade, quindi grid e pyramid lo
   // saltavano completamente.
   if(InpUseMarginGate && InpMinMarginLevelPct > 0){
      double marginReq = 0.0;
      if(OrderCalcMargin(otype, g_sym, lots, price, marginReq) && marginReq > 0){
         double equity     = AccountInfoDouble(ACCOUNT_EQUITY);
         double usedMargin = AccountInfoDouble(ACCOUNT_MARGIN);
         double projLevel  = (usedMargin + marginReq > 0)
                             ? equity / (usedMargin + marginReq) * 100.0 : 1e9;
         bool marginOK = (projLevel >= InpMinMarginLevelPct);
         NXS_GateTelemetry(route, "PROJECTED_MARGIN", marginOK, projLevel,
                           InpMinMarginLevelPct, marginOK ? "" : "margin_gate");
         if(!marginOK){
            reason = StringFormat("margin_gate proj=%.0f<%.0f", projLevel,
                                  InpMinMarginLevelPct);
            return false;
         }
      }
   }

   // --- (8) Preflight broker -----------------------------------------------
   string pfReason = "";
   bool preflightOK = NXS_PreFlight(otype, lots, price, sl, tp, pfReason);
   NXS_GateTelemetry(route, "BROKER_PREFLIGHT", preflightOK, lots, 0, pfReason);
   if(!preflightOK){ reason = pfReason; return false; }

   // Post-condizione: il preflight non deve poter azzerare lo stop.
   if(sl <= 0.0){
      NXS_GateTelemetry(route, "HARD_STOP_POST", false, sl, 0, "stop_cleared_by_preflight");
      reason = "preflight_cleared_stop";
      return false;
   }

   reason = "";
   return true;
}

void NXS_CounterSessionRollover(){
   MqlDateTime mt; TimeToStruct(TimeCurrent(), mt);
   mt.hour = 0; mt.min = 0; mt.sec = 0;
   datetime day = StructToTime(mt);
   int sess = (int)g_session;
   if(day != g_nxsCounterDay || sess != g_nxsCounterSessionKey){
      g_nxsCounterDay = day;
      g_nxsCounterSessionKey = sess;
      g_nxsCounterCount = 0;
   }
}

bool NXS_IsCounterHTFDirection(ENUM_NXS_DIR dir, SNXSHTF &htf){
   return (dir == DIR_BUY  && htf.bias == HTF_BEAR) ||
          (dir == DIR_SELL && htf.bias == HTF_BULL);
}

// AUD0-EXEC-007 — questo elenco duplica il contratto delle strategie: e' una
// TERZA lista mantenuta a mano, dopo il registro canonico e i profili. Una
// strategia aggiunta al registro e dimenticata qui perde silenziosamente
// l'idoneita' counter-HTF (o la ottiene per sbaglio se rinominata).
//
// La lista resta qui perche' "price action / reversal" e' una proprieta' di
// TASSONOMIA che il registro non modella ancora, ma ora e' VERIFICATA contro
// il registro: un nome che non esiste piu' viene segnalato all'avvio invece di
// restare per anni come voce morta.
bool NXS_IsCounterHTFPriceActionStrategy(string name){
   return (name == "BOLLINGER" || name == "RSI_DIV" || name == "BJORGUM" ||
           name == "BB_SQUEEZE" || name == "LIQ_SWEEP" || name == "FVG_MIT" ||
           name == "IFVG" || name == "OB_MIT" || name == "ORDER_BLOCK" ||
           name == "STRUCT_REACT" || name == "TURTLE_SOUP" ||
           name == "SH_BMS_RTO" || name == "SMS_BMS_RTO" ||
           name == "SILVER_BULLET" || name == "AMD_REVERSAL" ||
           name == "MALAYSIAN_SNR" || name == "THREE_BAR_DELIVERY_BREAK" || name == "JUDAS_SWING" ||
           name == "LDN_REVERSAL" || name == "NY_REVERSAL" || name == "PO3" ||
           name == "DISP_REBAL" || name == "RANGE_FADE");
}

//: AUD0-EXEC-007 — verifica di coerenza all'avvio fra la lista counter-HTF e
//: il registro canonico. Segnala le voci che non corrispondono a nessuna
//: strategia viva, cioe' la deriva di contratto che l'audit descrive.
void NXS_CounterHTF_AuditList(){
   string names[] = {"BOLLINGER","RSI_DIV","BJORGUM","BB_SQUEEZE","LIQ_SWEEP",
                     "FVG_MIT","IFVG","OB_MIT","ORDER_BLOCK","STRUCT_REACT",
                     "TURTLE_SOUP","SH_BMS_RTO","SMS_BMS_RTO","SILVER_BULLET",
                     "AMD_REVERSAL","MALAYSIAN_SNR","THREE_BAR_DELIVERY_BREAK",
                     "JUDAS_SWING","LDN_REVERSAL","NY_REVERSAL","PO3",
                     "DISP_REBAL","RANGE_FADE"};
   int stale = 0;
   for(int i = 0; i < ArraySize(names); i++){
      if(!NXS_StrategyKnown(names[i])){
         stale++;
         PrintFormat("[NEXUS][CONTRATTO] '%s' e' nella lista counter-HTF ma non "
                     "esiste nel registro canonico", names[i]);
      }
   }
   if(stale == 0)
      Print("[NEXUS] lista counter-HTF coerente con il registro canonico");
}

bool NXS_CounterHTFSoftEligible(SNXSSignal &sig, SNXSHTF &htf){
   if(!InpEnableCounterHTFSoft) return false;
   if(!NXS_IsCounterHTFDirection(sig.dir, htf)) return false;
   if(!NXS_IsCounterHTFPriceActionStrategy(sig.stratName)) return false;
   int d = (sig.dir == DIR_BUY) ? +1 : -1;
   if(!g_reaction.detected || g_reaction.direction != d) return false;
   if(g_reaction.quality < InpCounterHTF_MinReactQ) return false;
   NXS_CounterSessionRollover();
   if(InpCounterHTF_MaxPerSession > 0 && g_nxsCounterCount >= InpCounterHTF_MaxPerSession)
      return false;
   return true;
}

void NXS_ApplyCounterHTFProfile(SNXSSignal &sig){
   double atr = (g_atr > 0 ? g_atr : g_point * 100.0);
   double entry = (sig.dir == DIR_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                                       : SymbolInfoDouble(g_sym, SYMBOL_BID);
   sig.entryRef = entry;
   double slMult = MathMax(0.1, InpCounterHTF_SLATR);
   double minRR  = MathMax(0.1, InpCounterHTF_MinRR);
   if(sig.dir == DIR_BUY){
      sig.slPrice = entry - slMult * atr;
      double target = entry + minRR * (entry - sig.slPrice);
      if(sig.tpPrice <= entry || sig.tpPrice < target) sig.tpPrice = target;
   } else {
      sig.slPrice = entry + slMult * atr;
      double target = entry - minRR * (sig.slPrice - entry);
      if(sig.tpPrice >= entry || sig.tpPrice > target) sig.tpPrice = target;
   }
}

ENUM_NXS_OPEN_RC NXS_OpenTrade(SNXSSignal &sig, long magic, double lotMult){
   g_nxsLastOpenFailure = "";
   if(!NXS_StrategyKnown(sig.stratName)){
      g_nxsLastOpenFailure = "unknown_strategy:" + sig.stratName;
      PrintFormat("[NEXUS CONTRACT] OPEN BLOCCATO: strategy_id sconosciuto '%s'", sig.stratName);
      return OPEN_FAIL_PREFLIGHT;
   }
   // v2.2.6 - scudo risk-of-ruin: se congelato per la perdita del giorno, stop.
   if(NXS_RuinFrozen()){
      g_nxsLastOpenFailure = "ruin_frozen";
      return OPEN_FAIL_PREFLIGHT;
   }
   // v2.2.8 - "come nel backtest": le strategie che nel backtest PERDONO o hanno
   // dati insufficienti non aprono (STRUCT_REACT/DISP_REBAL/BB_SQUEEZE).
   if(InpUseStrategyProfiles && !NXS_Profile_Enabled(sig.stratName)){
      g_nxsLastOpenFailure = "profile_disabled";
      return OPEN_FAIL_PREFLIGHT;
   }
   // v2.3.0 — "ogni strategia sul suo TF": la strategia apre solo se il TF del
   // grafico coincide col suo timeframe ottimale (dal backtest multi-TF). Cosi'
   // basta far girare un'istanza per TF (D1/H4/H1) e ognuna tradera' solo le SUE
   // strategie. PERIOD_CURRENT nel profilo = nessun vincolo (usa il TF globale).
   // In modalita' InpProfileMultiTF il TF e' gia' garantito dal collector -> no gate.
   if(InpUseStrategyProfiles && InpProfileTFGate && !InpProfileMultiTF){
      ENUM_TIMEFRAMES pTF = NXS_Profile_TF(sig.stratName);
      if(pTF != PERIOD_CURRENT && (int)pTF != (int)InpTFEntry){
         g_nxsLastOpenFailure = "wrong_tf";
         return OPEN_FAIL_PREFLIGHT;
      }
   }
   // Disattivazione strategia da remoto (dashboard): blocca l'apertura in runtime.
   if(NXS_Runtime_StrategyBlocked(sig.stratName)){
      g_nxsLastOpenFailure = "strategy_disabled_dashboard";
      PrintFormat("[NEXUS] OPEN BLOCCATO: strategia '%s' disattivata dalla dashboard",
                  sig.stratName);
      return OPEN_FAIL_PREFLIGHT;
   }
   // v2.0.26 — one fresh entry per direction per bar. Other agreeing signals
   // on the same bar still contribute to confluence scoring upstream; they
   // just can't each open an independent position (was tripling risk on a
   // single market event read by 2-3 overlapping strategies).
   if(!NXS_BarDirCapAllows(sig.dir)){
      g_nxsLastOpenFailure = "bar_dir_cap";
      PrintFormat("[NEXUS RISK] OPEN BLOCCATO: gia' aperta %d posizione/i %s su questa barra (cap=%d) strat=%s",
                  (sig.dir == DIR_BUY ? g_newTradesThisBarBuy : g_newTradesThisBarSell),
                  NXS_DirName(sig.dir), InpMaxNewTradesPerBarDir, sig.stratName);
      return OPEN_FAIL_PREFLIGHT;
   }
   // v2.3.4 — SETUP MATRIX: cap di setup APERTI per direzione E PER TIMEFRAME
   // (come richiesto: "max 2 per direzione e per timeframe"). Il vecchio cap era
   // per-direzione GLOBALE -> TSI(D1)+MACD(H4) riempivano i 2 posti buy e le SMC
   // (CISD su H4) restavano bloccate (54/57 setup persi). Ora ogni TF ha il suo
   // budget: D1, H4, H1 contano separatamente.
   if(InpMaxPerDirTF > 0){
      ENUM_TIMEFRAMES sigTF = NXS_Profile_TF(sig.stratName);
      int sameDirTF = 0;
      for(int pi = PositionsTotal()-1; pi >= 0; pi--){
         ulong pt = PositionGetTicket(pi);
         if(pt == 0) continue;
         if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
         if(!IsNexusMagic((long)PositionGetInteger(POSITION_MAGIC))) continue;
         long ptype = PositionGetInteger(POSITION_TYPE);
         bool sameDir = (sig.dir == DIR_BUY  && ptype == POSITION_TYPE_BUY) ||
                        (sig.dir == DIR_SELL && ptype == POSITION_TYPE_SELL);
         if(!sameDir) continue;
         // AUD0-EXEC-006 / NXS-EXEC-002: il TF della posizione veniva dedotto
         // dal COMMENTO.
         // Un commento troncato dal broker (o una posizione manuale/legacy)
         // faceva risultare la posizione "senza TF", quindi fuori dal budget:
         // il cap per direzione/timeframe si allargava da solo, in silenzio.
         // Il registro degli intenti porta l'identita' decisa all'esecuzione.
         string posStrat = "";
         SNxsIntent pIntent;
         if(NXS_Intent_ByPosition((ulong)PositionGetInteger(POSITION_IDENTIFIER), pIntent))
            posStrat = pIntent.strategy;
         if(posStrat == ""){
            string pcm = PositionGetString(POSITION_COMMENT);
            string pp[]; int npp = StringSplit(pcm, '|', pp);
            if(npp >= 2) posStrat = pp[1];
         }
         ENUM_TIMEFRAMES posTF = (StringLen(posStrat) > 0)
                                 ? NXS_Profile_TF(posStrat) : PERIOD_CURRENT;
         if(posTF == PERIOD_CURRENT){
            // Identita' non risolvibile: la posizione conta comunque nel
            // budget del TF del segnale. Ignorarla significherebbe permettere
            // di aprirne altre proprio quando non si sa cosa c'e' gia' aperto.
            posTF = sigTF;
         }
         if(posTF == sigTF) sameDirTF++;
      }
      if(sameDirTF >= InpMaxPerDirTF){
         g_nxsLastOpenFailure = "setup_matrix_cap";
         PrintFormat("[NEXUS MATRIX] OPEN BLOCCATO: gia' %d setup %s su %s (cap/dir/TF=%d) strat=%s",
                     sameDirTF, NXS_DirName(sig.dir), EnumToString(sigTF), InpMaxPerDirTF, sig.stratName);
         return OPEN_FAIL_PREFLIGHT;
      }
   }
   // v2.0.33 — post-stop-loss directional cooldown: don't chase the reversal
   // right after getting stopped out the other way (whipsaw pattern found
   // in live trade review, mostly on MALAYSIAN_SNR_NXR in choppy conditions).
   if(NXS_PostSLCooldownBlocks(sig.dir)){
      g_nxsLastOpenFailure = "post_sl_cooldown";
      PrintFormat("[NEXUS RISK] OPEN BLOCCATO: cooldown post-SL attivo per direzione opposta a %s (cap=%d min) strat=%s",
                  NXS_DirName(sig.dir), InpPostSLCooldownMin, sig.stratName);
      return OPEN_FAIL_PREFLIGHT;
   }
   // v2.0.34 (audit point 8): exhaustion/extension gate.
   // v2.1.7: bypass sui reversal di gruppo (vedi g_nxsBypassExhaustion).
   string exhReason = "";
   if(!g_nxsBypassExhaustion && NXS_ExhaustionBlocks(sig.dir, sig.stratName, exhReason)){
      g_nxsLastOpenFailure = exhReason;
      PrintFormat("[NEXUS RISK] OPEN BLOCCATO: %s dir=%s strat=%s", exhReason, NXS_DirName(sig.dir), sig.stratName);
      return OPEN_FAIL_PREFLIGHT;
   }
   double sl = sig.slPrice, tp = sig.tpPrice;
   double slDist = MathAbs(sig.entryRef - sl);
   if(slDist <= 0){ g_nxsLastOpenFailure = "invalid_sl_distance"; return OPEN_FAIL_INVALID_STOPS; }

   // v2.3.6 — rischio PER-STRATEGIA DIRETTO: il lotto e' dimensionato al rischio%
   // del profilo (non piu' un moltiplicatore sul globale, che il cap
   // InpMaxTotalLotMult schiacciava -> tutti i lotti finivano a 0.01). Il rischio
   // di default (InpRiskPercent) resta solo per le strategie SENZA profilo.
   double prPct = (InpUseStrategyProfiles) ? NXS_Profile_Risk(sig.stratName) : 0.0;
   double lots = (prPct > 0) ? NXS_CalcLotRisk(slDist, prPct, sig.stratName) : NXS_CalcLot(slDist);
   if(lots <= 0){ g_nxsLastOpenFailure = "lot_calc_zero"; return OPEN_FAIL_INVALID_VOLUME; }

   // Moltiplicatori residui (counter-HTF/chain via lotMult + auto-scaler runtime),
   // capati da InpMaxTotalLotMult. Il rischio per-strategia NON e' piu' qui:
   // e' gia' nel sizing base -> il cap non lo tocca.
   double stratRisk = NXS_Runtime_StrategyLotMult(sig.stratName);
   // AUD0-EXEC-008: qui un moltiplicatore a zero veniva RIPORTATO A 1.0, cioe'
   // l'istruzione "non operare con questa strategia" diventava "opera a
   // rischio pieno". Ora zero significa zero: nessuna apertura.
   if(stratRisk <= 0.0){
      g_nxsLastOpenFailure = "strategy_risk_disabled";
      PrintFormat("[NEXUS RISK] OPEN BLOCCATO: %s ha moltiplicatore di rischio "
                  "nullo dal piano di controllo", sig.stratName);
      return OPEN_FAIL_PREFLIGHT;
   }
   double rawMult = MathMax(0.01, lotMult) * stratRisk;
   double cappedMult = MathMin(rawMult, InpMaxTotalLotMult);
   if(cappedMult < rawMult - 1e-9){
      PrintFormat("[NEXUS RISK] %s lot multiplier capped x%.2f -> x%.2f (limite InpMaxTotalLotMult=%.2f)",
                  sig.stratName, rawMult, cappedMult, InpMaxTotalLotMult);
   }
   if(MathAbs(cappedMult - 1.0) > 1e-6){
      PrintFormat("[NEXUS RISK] %s lot multiplier effettivo applicato: x%.2f (lots base %.4f -> %.4f)",
                  sig.stratName, cappedMult, lots, lots * cappedMult);
   }
   lots *= cappedMult;

   // Re-align volume after a Counter-HTF risk multiplier.
   double step = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
   if(step <= 0) step = 0.01;
   lots = MathFloor(lots / step) * step;
   lots = NormalizeDouble(lots, 8);
   lots = NXS_License_CapLot(lots);

   // v2.0.26 — total exposure cap per direction (sum of open lots + this
   // new order must not exceed InpMaxDirExposureLots). Rejects rather than
   // resizing, per spec: a chain of same-direction adds that would otherwise
   // balloon total risk just doesn't get the next leg.
   ENUM_ORDER_TYPE otype = (sig.dir == DIR_BUY) ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double refPrice = (sig.dir == DIR_BUY) ? SymbolInfoDouble(g_sym, SYMBOL_ASK)
                                          : SymbolInfoDouble(g_sym, SYMBOL_BID);
   // v2.4.1 — GATE SUL MARGINE: apri solo se il margin level PROIETTATO (equity
   // / margine usato dopo questo trade) resta sopra la soglia. E' il conto stesso
   // a regolare la concorrenza: un trade aperto in profitto alza l'equity ->
   // alza il livello -> apre spazio ad altre strategie; un drawdown lo abbassa
   // -> frena. Sostituisce la contesa arbitraria per slot con "profitto=margine".
   //
   // Il controllo è stato SPOSTATO dentro NXS_CommonExposurePreflight: qui
   // copriva solo l'entry primaria, mentre grid, pyramid e add istituzionali
   // lo saltavano (AUD0-ADD-003). La chiamata qui sotto lo eredita.
   string pfReason = "";
   if(!NXS_CommonExposurePreflight("PRIMARY:" + sig.stratName, sig.dir, lots,
                                   otype, refPrice, sl, tp, pfReason)){
      g_nxsLastOpenFailure = pfReason;
      PrintFormat("[NEXUS] OPEN BLOCKED common gate: %s strat=%s", pfReason, sig.stratName);
      return OPEN_FAIL_PREFLIGHT;
   }

   // Persist broker-adjusted/tick-normalized values for logging and management.
   sig.slPrice = sl;
   sig.tpPrice = tp;

   NXS_TradeSetMagic(magic);
   // 4o campo = contesto: tag ricco dal branch istituzionale ("TF-C/R"), oppure
   // fallback sul TF di origine del segnale. Il backend tollera il campo [3].
   string ctxTag = g_nxsOpenCtxTag;
   if(StringLen(ctxTag) == 0 && sig.sourceTF != PERIOD_CURRENT)
      ctxTag = StringSubstr(EnumToString(sig.sourceTF), 7);   // "M15","H1","H4","D1"
   string cm = StringFormat("%s|%s|%.1f", InpComment, sig.stratName, sig.score);
   if(StringLen(ctxTag) > 0) cm = cm + "|" + ctxTag;
   // PR2 Virtual SL: decide lo SL da inviare al broker (hard SL largo in EXECUTE,
   // SL logico in OFF/OBSERVE/fallback). Il sizing sopra resta sullo SL logico.
   int    vdir = (sig.dir == DIR_BUY) ? +1 : -1;
   double brokerSL = sl;
   if(!NXS_VSL_PrepareEntry(vdir, sig.entryRef, sl, g_atr, brokerSL)){
      g_nxsLastOpenFailure = "virtsl_hardSL_invalid";
      PrintFormat("[NEXUS] OPEN BLOCCATO: hard SL Virtual SL non valido strat=%s", sig.stratName);
      return OPEN_FAIL_INVALID_STOPS;
   }

   // NXS-EXEC-001 — IL RISCHIO REALE E' QUELLO DELLO STOP INVIATO AL BROKER.
   //
   // Il lotto e' dimensionato sulla distanza dello SL LOGICO, ma in modalita'
   // EXECUTE al broker arriva uno stop piu' LARGO (basato su ATR). Lo stop
   // logico vale solo finche' l'EA gira e riceve tick; se il terminale e'
   // spento, la rete cade o l'EA e' bloccato, la perdita effettiva e' quella
   // dello stop del broker — cioe' MOLTO PIU' GRANDE del budget approvato.
   //
   // Il rischio di caso peggiore viene ora calcolato sullo stop realmente
   // inviato e confrontato con un tetto esplicito. Oltre il tetto l'ordine non
   // parte: meglio non aprire che aprire un'esposizione il cui peggior caso
   // nessuno ha approvato.
   double brokerDist = MathAbs(sig.entryRef - brokerSL);
   if(brokerDist > slDist * 1.0000001){
      double worstCase = NXS_Intent_RiskMoney(g_sym, sig.entryRef, brokerSL, lots);
      double budget    = AccountInfoDouble(ACCOUNT_BALANCE)
                       * ((prPct > 0) ? prPct : g_run_RiskPercent) / 100.0;
      double cap       = budget * MathMax(1.0, InpVSL_MaxOfflineRiskMult);
      if(budget > 0 && worstCase > cap){
         g_nxsLastOpenFailure = "virtsl_offline_risk_over_cap";
         PrintFormat("[NEXUS RISK] OPEN BLOCCATO: con lo stop inviato al broker "
                     "(%.5f) il caso peggiore offline sarebbe %.2f, oltre il tetto "
                     "%.2f (budget %.2f x %.2f) strat=%s",
                     brokerSL, worstCase, cap, budget, InpVSL_MaxOfflineRiskMult,
                     sig.stratName);
         return OPEN_FAIL_PREFLIGHT;
      }
      PrintFormat("[NEXUS RISK] stop broker piu' largo dello stop logico: caso "
                  "peggiore offline %.2f su budget %.2f (tetto %.2f)",
                  worstCase, budget, cap);
   }

   bool ok = false;
   if(sig.dir == DIR_BUY)       ok = NXS_SafeBuy(lots, g_sym, brokerSL, tp, cm);
   else if(sig.dir == DIR_SELL) ok = NXS_SafeSell(lots, g_sym, brokerSL, tp, cm);

   // NXS-RAW-002: si copia SUBITO l'esito in una struttura locale. Leggere
   // g_tradeOrderTicket piu' avanti significa correlare il Virtual SL a
   // qualunque ordine sia stato inviato nel frattempo da un altro percorso.
   SNXSExecResult exec; NXS_LastExec(exec);

   if(ok){
      // registra l'intent pending correlato all'order ticket reale (match al fill)
      NXS_VSL_OnRequested(exec.order, g_sym, magic, vdir,
                          sig.stratName, sig.slPrice, brokerSL);
      // AUD0-LEDGER-004/006/010: identita' e budget di rischio registrati QUI,
      // dove sono un fatto. Il ledger non dovra' piu' dedurli dal commento ne'
      // dallo stop del primo deal. groupId=0 => questa entrata apre una nuova
      // sequenza logica; le gambe di grid/piramide vi si agganceranno.
      // AUD0-RAW-002: il prezzo EFFETTIVAMENTE eseguito, quando disponibile,
      // e' un denominatore di rischio migliore del prezzo di riferimento
      // pre-invio (che ignora slippage).
      double fillPx = (exec.price > 0 ? exec.price : refPrice);
      NXS_Intent_Record(exec.order, sig.stratName, sig.score,
                        NXS_Intent_RiskMoney(g_sym, fillPx, sl, lots),
                        "primary", 0, g_atr, lots);
      g_tradesToday++;
      g_lastTradeTime = TimeCurrent();
      NXS_BarDirCapRegisterOpen(sig.dir);
      PrintFormat("[NEXUS] OPEN %s %s lots=%.4f sl=%.5f tp=%.5f score=%.1f reason=%s",
                  NXS_DirName(sig.dir), sig.stratName, lots, sl, tp, sig.score, sig.reason);
      NXS_Notify_TradeOpen(sig.stratName, NXS_DirName(sig.dir), lots, refPrice, sig.score);
      return OPEN_OK;
   }

   g_nxsLastOpenFailure = StringFormat("order_send_retcode=%u", NXS_TradeRetcode());
   NXS_Diag_TradeFail(sig.stratName, (int)sig.dir, lots, refPrice, (int)NXS_TradeRetcode());
   return OPEN_FAIL_SEND;
}

void NXS_CloseOppositeIfBetter(ENUM_NXS_DIR newDir, double newScore){
   if(!InpEnableCloseReverse) return;
   if(newScore < InpMinScoreReverse) return;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsCoreMagic(mg)) continue;
      long ptype = PositionGetInteger(POSITION_TYPE);
      bool oppToBuy  = (newDir == DIR_BUY  && ptype == POSITION_TYPE_SELL);
      bool oppToSell = (newDir == DIR_SELL && ptype == POSITION_TYPE_BUY);
      if(!(oppToBuy || oppToSell)) continue;
      double profit = PositionGetDouble(POSITION_PROFIT);
      if(profit > 0) continue;
      // AUD0-EXEC-002: si chiamava NXS_DoClose e si stampava "closing" senza
      // guardare l'esito. Il chiamante procedeva ad aprire la direzione
      // opposta assumendo che la posizione fosse sparita.
      //
      // NXS-EXEC-003: la chiusura resta DIRETTA e non passa dal coordinatore.
      // E' una scelta, non una dimenticanza: il close-and-reverse deve
      // completarsi PRIMA dell'apertura opposta nello stesso tick, mentre il
      // coordinatore applica le proposte a fine ciclo — la posizione
      // resterebbe aperta mentre si apre il lato opposto, creando esattamente
      // l'esposizione bilaterale che il reverse vuole evitare.
      //
      // Il conflitto con una proposta concorrente sullo stesso ticket viene
      // neutralizzato registrando l'azione nel coordinatore subito dopo: una
      // proposta successiva sulla stessa posizione trovera' un ticket che non
      // esiste piu' e verra' scartata in NXS_PM_ApplyCycle.
      bool closed = NXS_DoClose(t);
      if(closed) NXS_PM_RecordApplied(t, "CLOSE_REVERSE");
      PrintFormat("[NEXUS] Close&Reverse %I64u esito=%s retcode=%d",
                  t, (closed ? "OK" : "FALLITO"), NXS_TradeRetcode());
      if(!closed)
         PrintFormat("[NEXUS][ALERT] Close&Reverse: la posizione %I64u resta APERTA; "
                     "l'ingresso opposto creerebbe esposizione su due lati", t);
   }
}

// v2.0.13 — Smart Close & Reverse: dynamic threshold based on reaction + HTF
void NXS_SmartCloseOppositeIfBetter(ENUM_NXS_DIR newDir, double newScore, SNXSHTF &htf){
   if(!InpEnableCloseReverse) return;
   double thresholdUsed = InpMinScoreReverse;
   bool ok = false;
   if(InpChainEnableSmartReverse){
      int dirInt = (newDir == DIR_BUY) ? +1 : -1;
      double reactQ = g_reaction.detected ? g_reaction.quality : 0.0;
      ok = NXS_Chain_ShouldSmartReverse(dirInt, newScore, reactQ, htf.bias, thresholdUsed);
   } else {
      ok = (newScore >= thresholdUsed);
   }
   if(!ok) return;
   for(int i = PositionsTotal()-1; i >= 0; i--){
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != g_sym) continue;
      long mg = (long)PositionGetInteger(POSITION_MAGIC);
      if(!IsCoreMagic(mg)) continue;
      long ptype = PositionGetInteger(POSITION_TYPE);
      bool oppToBuy  = (newDir == DIR_BUY  && ptype == POSITION_TYPE_SELL);
      bool oppToSell = (newDir == DIR_SELL && ptype == POSITION_TYPE_BUY);
      if(!(oppToBuy || oppToSell)) continue;
      double profit = PositionGetDouble(POSITION_PROFIT);
      bool allowLossClose = (newScore >= thresholdUsed + 10.0);
      if(profit > 0 || allowLossClose){
         // AUD0-EXEC-002: stesso difetto del percorso non-smart.
         bool closed = NXS_DoClose(t);
         PrintFormat("[NEXUS] Smart Close&Reverse %I64u esito=%s (score=%.1f thr=%.1f profit=%.2f retcode=%d)",
                     t, (closed ? "OK" : "FALLITO"), newScore, thresholdUsed,
                     profit, NXS_TradeRetcode());
         if(!closed)
            PrintFormat("[NEXUS][ALERT] Smart Close&Reverse: posizione %I64u ancora aperta", t);
      }
   }
}

enum ENUM_NXS_EXEC_RC {
   EXEC_OK = 0,
   EXEC_FAIL_NO_DIR,
   EXEC_FAIL_PROTECTIONS,
   EXEC_FAIL_NEWS,
   EXEC_FAIL_HTF,
   EXEC_FAIL_VELOCITY,
   EXEC_FAIL_SCORE_BELOW,
   EXEC_FAIL_INVALID_STOPS,
   EXEC_FAIL_INVALID_VOLUME,
   EXEC_FAIL_PREFLIGHT,
   EXEC_FAIL_ORDER_SEND
};

// GateMode semantics advertised in Inputs are now functional:
// 0 Conservative = never lower global threshold
// 1 Balanced     = session may lower it by at most 5 points
// 2 Discovery    = use the lower of global/session threshold
// 3 DebugTrade   = Discovery threshold minus 10, floor 40
// This does not bypass risk, margin, spread or protection gates.
double NXS_ResolvedEntryThreshold(){
   double globalTh = (double)g_run_MinEntryScore;
   double sessionTh = InpUseSessions ? NXS_SessionMinScore(g_session) : globalTh;
   if(InpGateMode <= 0) return MathMax(globalTh, sessionTh);
   if(InpGateMode == 1) return MathMax(sessionTh, globalTh - 5.0);
   if(InpGateMode == 2) return MathMin(globalTh, sessionTh);
   return MathMax(40.0, MathMin(globalTh, sessionTh) - 10.0);
}

ENUM_NXS_EXEC_RC NXS_TryExecuteRC(SNXSSignal &sig, SNXSAMD &amd, SNXSSweep &sw,
                                  SNXSHTF &htf, SNXSVel &vel, double &finalScoreOut,
                                  double &threshOut){
   finalScoreOut = sig.score; threshOut = 0;
   if(sig.dir == DIR_NONE) return EXEC_FAIL_NO_DIR;

   string r;
   if(!NXS_CheckProtections(r)) return EXEC_FAIL_PROTECTIONS;
   if(NXS_NewsBlocking())       return EXEC_FAIL_NEWS;

   bool rawCounter  = NXS_IsCounterHTFDirection(sig.dir, htf);
   bool counterSoft = NXS_CounterHTFSoftEligible(sig, htf);
   // In Balanced/Conservative, enabling Counter-HTF Soft must not become a
   // blanket bypass: an ineligible counter signal is still rejected here.
   if(rawCounter && InpEnableCounterHTFSoft && !counterSoft && InpGateMode < 2)
      return EXEC_FAIL_HTF;
   if(NXS_HTFBlocks(sig.dir, htf) && !counterSoft) return EXEC_FAIL_HTF;
   if(NXS_VelocityBlocks(sig.dir, vel))            return EXEC_FAIL_VELOCITY;

   if(counterSoft) NXS_ApplyCounterHTFProfile(sig);

   double finalScore = NXS_FinalScore(sig, amd, sw);
   sig.score = finalScore; finalScoreOut = finalScore;
   double thresh = NXS_DynamicScoreThreshold(NXS_ResolvedEntryThreshold());
   thresh = MathMax(thresh, NXS_StrategyMinScoreFloor(sig.stratName));  // v2.0.14
   threshOut = thresh;
   if(finalScore < thresh) return EXEC_FAIL_SCORE_BELOW;

   NXS_SmartCloseOppositeIfBetter(sig.dir, finalScore, htf);
   double lotMult = counterSoft ? MathMax(0.01, InpCounterHTF_LotMult) : 1.0;
   // v2.0.13 — apply chain continuation lot multiplier
   if(g_chainPendingLotMult > 0.0 && g_chainPendingLotMult < 1.0)
      lotMult *= g_chainPendingLotMult;
   g_chainPendingLotMult = 1.0;  // reset
   // v2.0.37 — TURTLE_SOUP-only lot increase (double-confirmed edge), applied
   // on top of the multiplier stack above; InpMaxTotalLotMult/
   // InpMaxDirExposureLots(*) still cap the result inside NXS_OpenTrade.
   if(sig.stratName == "TURTLE_SOUP" && InpTurtleSoup_LotMult != 1.0){
      lotMult *= InpTurtleSoup_LotMult;
      PrintFormat("[NEXUS LOT] TURTLE_SOUP lot mult applied: x%.2f -> effective mult=%.3f (caps still apply)",
                  InpTurtleSoup_LotMult, lotMult);
   }
   ENUM_NXS_OPEN_RC openRc = NXS_OpenTrade(sig, InpMagic + MAGIC_CORE, lotMult);
   if(openRc == OPEN_OK){
      if(counterSoft){ NXS_CounterSessionRollover(); g_nxsCounterCount++; }
      return EXEC_OK;
   }
   if(openRc == OPEN_FAIL_INVALID_STOPS)  return EXEC_FAIL_INVALID_STOPS;
   if(openRc == OPEN_FAIL_INVALID_VOLUME) return EXEC_FAIL_INVALID_VOLUME;
   if(openRc == OPEN_FAIL_PREFLIGHT)      return EXEC_FAIL_PREFLIGHT;
   return EXEC_FAIL_ORDER_SEND;
}

bool NXS_TryExecute(SNXSSignal &sig, SNXSAMD &amd, SNXSSweep &sw, SNXSHTF &htf, SNXSVel &vel){
   double f, t;
   return (NXS_TryExecuteRC(sig, amd, sw, htf, vel, f, t) == EXEC_OK);
}

#endif
