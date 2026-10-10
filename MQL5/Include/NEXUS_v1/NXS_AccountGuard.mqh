//+------------------------------------------------------------------+
//|  NXS_AccountGuard.mqh - DEMO by default, LIVE separately armed    |
//|                                                                    |
//|  NEXUS-ACCT-001: l'EA e' l'unico motore che invia ordini, ma nulla |
//|  gli impediva di aprire su un conto reale. "LIVE disattivato"      |
//|  esisteva solo come flag Python che nessuno leggeva: attaccato a   |
//|  un conto LIVE, l'EA avrebbe tradato come su DEMO.                 |
//|                                                                    |
//|  Regola: nuova esposizione solo se                                 |
//|    - Strategy Tester / ottimizzazione (nessun conto reale), oppure |
//|    - ACCOUNT_TRADE_MODE == DEMO, oppure                            |
//|    - conto REAL/CONTEST con InpLiveTradingAuthorized=true E login  |
//|      del conto == InpLiveAccountLogin (autorizzazione legata a un  |
//|      conto preciso: un .set copiato non arma un altro conto).      |
//|                                                                    |
//|  Chiusure, parziali e modifiche NON passano da qui: ridurre il     |
//|  rischio non deve mai essere bloccabile da un gate di apertura.    |
//+------------------------------------------------------------------+
#ifndef __NXS_ACCOUNT_GUARD_MQH__
#define __NXS_ACCOUNT_GUARD_MQH__

string NXS_AccountModeName(){
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION)) return "TESTER";
   long mode = AccountInfoInteger(ACCOUNT_TRADE_MODE);
   if(mode == ACCOUNT_TRADE_MODE_DEMO)    return "DEMO";
   if(mode == ACCOUNT_TRADE_MODE_CONTEST) return "CONTEST";
   if(mode == ACCOUNT_TRADE_MODE_REAL)    return "LIVE";
   return "UNKNOWN";
}

// Esito del gate. `reason` vuota quando l'apertura e' consentita.
bool NXS_AccountGuard_EntryAllowed(string &reason){
   reason = "";
   string mode = NXS_AccountModeName();
   if(mode == "TESTER" || mode == "DEMO") return true;
   if(mode == "UNKNOWN"){
      reason = "account_mode_unknown: tipo di conto non leggibile";
      return false;
   }
   // REAL o CONTEST: denaro (o classifica) reale.
   if(!InpLiveTradingAuthorized){
      reason = "account_mode_live_not_authorized: conto " + mode +
               ", autorizzazione LIVE spenta";
      return false;
   }
   long login = AccountInfoInteger(ACCOUNT_LOGIN);
   if(InpLiveAccountLogin <= 0 || login != InpLiveAccountLogin){
      reason = StringFormat("account_mode_login_mismatch: conto %I64d, autorizzato %I64d",
                            login, InpLiveAccountLogin);
      return false;
   }
   return true;
}

// Senza effetti collaterali: usato dalla telemetria verso il backend.
bool NXS_AccountGuard_LiveArmed(){
   return InpLiveTradingAuthorized && InpLiveAccountLogin > 0
          && AccountInfoInteger(ACCOUNT_LOGIN) == InpLiveAccountLogin;
}

void NXS_AccountGuard_LogInit(){
   string why;
   bool ok = NXS_AccountGuard_EntryAllowed(why);
   PrintFormat("[NEXUS ACCOUNT] login=%I64d server=%s mode=%s new_entries=%s%s",
               AccountInfoInteger(ACCOUNT_LOGIN), AccountInfoString(ACCOUNT_SERVER),
               NXS_AccountModeName(), ok ? "ALLOWED" : "BLOCKED",
               ok ? "" : (" (" + why + ")"));
}

#endif
