//+------------------------------------------------------------------+
//|  NXS_Outbox.mqh - coda locale durevole per le consegne HTTP       |
//|                                                                   |
//|  AUD0-PROT-005 / NXS-PROT-005 / AUD0-HSYNC-003                    |
//|                                                                   |
//|  Problema che risolve:                                            |
//|  i moduli che spingono eventi verso il backend (protezioni,       |
//|  history sync, ledger) ritentavano IN LINEA con Sleep(), fino a   |
//|  decine di secondi di blocco del thread dell'EA — e proprio nei   |
//|  momenti peggiori (subito dopo una chiusura di protezione, quando |
//|  Virtual SL, OnTradeTransaction e le altre protezioni DEVONO      |
//|  poter girare). In alternativa perdevano l'evento del tutto.      |
//|                                                                   |
//|  Qui la consegna fallita viene accodata su file (sopravvive a     |
//|  riavvii del terminale) e drenata dal timer, poche entry alla     |
//|  volta, con backoff esponenziale e senza mai bloccare il tick.    |
//|                                                                   |
//|  La coda e' LIMITATA: oltre il tetto si scartano le entry piu'    |
//|  vecchie con un log esplicito, cosi' un backend irraggiungibile   |
//|  per giorni non riempie il disco ne' la RAM.                      |
//+------------------------------------------------------------------+
#ifndef __NXS_OUTBOX_MQH__
#define __NXS_OUTBOX_MQH__

#define NXS_OUTBOX_MAX_ENTRIES     200   // tetto duro della coda
#define NXS_OUTBOX_MAX_ATTEMPTS      8   // oltre: entry scartata con log
#define NXS_OUTBOX_DRAIN_PER_CALL    2   // consegne per chiamata del timer
#define NXS_OUTBOX_TIMEOUT_MS     3000   // timeout breve: mai bloccare l'EA
#define NXS_OUTBOX_BASE_BACKOFF      5   // secondi
#define NXS_OUTBOX_MAX_BACKOFF     300   // secondi
#define NXS_OUTBOX_SEP            "\x1F" // separatore di campo (unit separator)

string   g_nxsOutUrl[];
string   g_nxsOutBody[];
int      g_nxsOutAttempts[];
datetime g_nxsOutNextTry[];
datetime g_nxsOutQueuedAt[];
bool     g_nxsOutLoaded  = false;
bool     g_nxsOutDirty   = false;
long     g_nxsOutDropped = 0;

//: Nome file per conto+magic: due istanze non si sovrascrivono la coda.
string _NXS_OutboxFile(){
   return StringFormat("NEXUS_outbox_%I64d_%I64d.txt",
                       (long)AccountInfoInteger(ACCOUNT_LOGIN),
                       (long)InpMagic);
}

//: Rimuove i caratteri che romperebbero il formato a righe del file.
string _NXS_OutboxSanitize(string s){
   StringReplace(s, "\r", " ");
   StringReplace(s, "\n", " ");
   StringReplace(s, NXS_OUTBOX_SEP, " ");
   return s;
}

int NXS_Outbox_Count(){ return ArraySize(g_nxsOutUrl); }

void _NXS_OutboxRemoveAt(int idx){
   int n = ArraySize(g_nxsOutUrl);
   if(idx < 0 || idx >= n) return;
   for(int i = idx; i < n - 1; i++){
      g_nxsOutUrl[i]      = g_nxsOutUrl[i + 1];
      g_nxsOutBody[i]     = g_nxsOutBody[i + 1];
      g_nxsOutAttempts[i] = g_nxsOutAttempts[i + 1];
      g_nxsOutNextTry[i]  = g_nxsOutNextTry[i + 1];
      g_nxsOutQueuedAt[i] = g_nxsOutQueuedAt[i + 1];
   }
   ArrayResize(g_nxsOutUrl,      n - 1);
   ArrayResize(g_nxsOutBody,     n - 1);
   ArrayResize(g_nxsOutAttempts, n - 1);
   ArrayResize(g_nxsOutNextTry,  n - 1);
   ArrayResize(g_nxsOutQueuedAt, n - 1);
   g_nxsOutDirty = true;
}

//: Persiste la coda. Chiamata solo quando qualcosa e' cambiato.
void NXS_Outbox_Save(){
   if(!g_nxsOutDirty) return;
   int n = ArraySize(g_nxsOutUrl);
   if(n <= 0){
      FileDelete(_NXS_OutboxFile());
      g_nxsOutDirty = false;
      return;
   }
   int h = FileOpen(_NXS_OutboxFile(), FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE){
      PrintFormat("[NEXUS OUTBOX] impossibile scrivere %s (err=%d): la coda resta solo in memoria",
                  _NXS_OutboxFile(), GetLastError());
      return;
   }
   for(int i = 0; i < n; i++){
      string line = IntegerToString((long)g_nxsOutQueuedAt[i]) + NXS_OUTBOX_SEP +
                    IntegerToString(g_nxsOutAttempts[i])       + NXS_OUTBOX_SEP +
                    IntegerToString((long)g_nxsOutNextTry[i])  + NXS_OUTBOX_SEP +
                    g_nxsOutUrl[i]                             + NXS_OUTBOX_SEP +
                    g_nxsOutBody[i];
      FileWriteString(h, line + "\r\n");
   }
   FileClose(h);
   g_nxsOutDirty = false;
}

//: Ricarica la coda dal disco. Idempotente: gira una sola volta.
void NXS_Outbox_Load(){
   if(g_nxsOutLoaded) return;
   g_nxsOutLoaded = true;
   ArrayResize(g_nxsOutUrl, 0);
   ArrayResize(g_nxsOutBody, 0);
   ArrayResize(g_nxsOutAttempts, 0);
   ArrayResize(g_nxsOutNextTry, 0);
   ArrayResize(g_nxsOutQueuedAt, 0);

   if(!FileIsExist(_NXS_OutboxFile())) return;
   int h = FileOpen(_NXS_OutboxFile(), FILE_READ | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return;

   int loaded = 0, malformed = 0;
   while(!FileIsEnding(h)){
      string line = FileReadString(h);
      if(StringLen(line) < 5) continue;
      string parts[];
      int k = StringSplit(line, StringGetCharacter(NXS_OUTBOX_SEP, 0), parts);
      if(k < 5){ malformed++; continue; }
      if(loaded >= NXS_OUTBOX_MAX_ENTRIES){ g_nxsOutDropped++; continue; }
      int idx = ArraySize(g_nxsOutUrl);
      ArrayResize(g_nxsOutUrl,      idx + 1);
      ArrayResize(g_nxsOutBody,     idx + 1);
      ArrayResize(g_nxsOutAttempts, idx + 1);
      ArrayResize(g_nxsOutNextTry,  idx + 1);
      ArrayResize(g_nxsOutQueuedAt, idx + 1);
      g_nxsOutQueuedAt[idx] = (datetime)StringToInteger(parts[0]);
      g_nxsOutAttempts[idx] = (int)StringToInteger(parts[1]);
      g_nxsOutNextTry[idx]  = (datetime)StringToInteger(parts[2]);
      g_nxsOutUrl[idx]      = parts[3];
      // Il body puo' contenere il separatore? No: e' sanificato in push.
      // Si ricompone comunque il resto per tolleranza ai file legacy.
      string body = parts[4];
      for(int p = 5; p < k; p++) body += parts[p];
      g_nxsOutBody[idx] = body;
      loaded++;
   }
   FileClose(h);
   if(loaded > 0 || malformed > 0)
      PrintFormat("[NEXUS OUTBOX] ripristinate %d consegne pendenti (%d righe illeggibili scartate)",
                  loaded, malformed);
}

//: Accoda una consegna fallita. Non blocca e non ritenta qui.
void NXS_Outbox_Push(string url, string body){
   if(StringLen(url) == 0 || StringLen(body) == 0) return;
   NXS_Outbox_Load();

   int n = ArraySize(g_nxsOutUrl);
   // Coda piena: si scarta la piu' VECCHIA, non la nuova. Un backend giu' da
   // ore non deve impedire di registrare l'evento appena avvenuto.
   while(n >= NXS_OUTBOX_MAX_ENTRIES){
      g_nxsOutDropped++;
      PrintFormat("[NEXUS OUTBOX] coda piena (%d): scartata la consegna piu' vecchia "
                  "verso %s (totale scartate: %I64d)",
                  NXS_OUTBOX_MAX_ENTRIES, g_nxsOutUrl[0], g_nxsOutDropped);
      _NXS_OutboxRemoveAt(0);
      n = ArraySize(g_nxsOutUrl);
   }

   ArrayResize(g_nxsOutUrl,      n + 1);
   ArrayResize(g_nxsOutBody,     n + 1);
   ArrayResize(g_nxsOutAttempts, n + 1);
   ArrayResize(g_nxsOutNextTry,  n + 1);
   ArrayResize(g_nxsOutQueuedAt, n + 1);
   g_nxsOutUrl[n]      = _NXS_OutboxSanitize(url);
   g_nxsOutBody[n]     = _NXS_OutboxSanitize(body);
   g_nxsOutAttempts[n] = 0;
   g_nxsOutQueuedAt[n] = TimeCurrent();
   g_nxsOutNextTry[n]  = TimeCurrent();   // primo ritentativo al prossimo timer
   g_nxsOutDirty       = true;
   NXS_Outbox_Save();
}

//: Backoff esponenziale limitato: 5s, 10s, 20s ... max 300s.
datetime _NXS_OutboxBackoff(int attempts){
   int shift = (int)MathMin(attempts, 6);
   int secs  = NXS_OUTBOX_BASE_BACKOFF * (int)MathPow(2.0, (double)shift);
   if(secs > NXS_OUTBOX_MAX_BACKOFF) secs = NXS_OUTBOX_MAX_BACKOFF;
   return TimeCurrent() + secs;
}

//: Drena al massimo NXS_OUTBOX_DRAIN_PER_CALL consegne. Da chiamare dal timer.
//: Non gira mai nel tester (nessun effetto di rete nei backtest deterministici).
void NXS_Outbox_Drain(){
   if(MQLInfoInteger(MQL_TESTER)) return;
   if(!InpEnableWebSync)          return;
   NXS_Outbox_Load();
   if(ArraySize(g_nxsOutUrl) == 0) return;

   string headers = "Content-Type: application/json\r\nX-Nexus-Token: " + InpWebToken + "\r\n";
   datetime now   = TimeCurrent();
   int sent = 0;

   for(int i = 0; i < ArraySize(g_nxsOutUrl) && sent < NXS_OUTBOX_DRAIN_PER_CALL; ){
      if(g_nxsOutNextTry[i] > now){ i++; continue; }

      char post[]; StringToCharArray(g_nxsOutBody[i], post, 0, -1, CP_UTF8);
      ArrayResize(post, ArraySize(post) - 1);
      char result[]; string headersOut;
      int code = WebRequest("POST", g_nxsOutUrl[i], headers,
                            NXS_OUTBOX_TIMEOUT_MS, post, result, headersOut);
      sent++;

      if(code == 200 || code == 201 || code == 202 || code == 409){
         // 409 = gia' registrato lato backend (idempotenza): consegna riuscita.
         _NXS_OutboxRemoveAt(i);
         continue;
      }

      g_nxsOutAttempts[i]++;
      g_nxsOutDirty = true;

      // 4xx diversi da 408/429 non migliorano ritentando: payload o token
      // sbagliati. Si scarta subito invece di consumare il budget per ore.
      bool permanent = (code >= 400 && code < 500 && code != 408 && code != 429);
      if(permanent || g_nxsOutAttempts[i] >= NXS_OUTBOX_MAX_ATTEMPTS){
         g_nxsOutDropped++;
         PrintFormat("[NEXUS OUTBOX] consegna abbandonata dopo %d tentativi "
                     "(code=%d url=%s): evento perso, verra' riconciliato dalla history sync",
                     g_nxsOutAttempts[i], code, g_nxsOutUrl[i]);
         _NXS_OutboxRemoveAt(i);
         continue;
      }
      g_nxsOutNextTry[i] = _NXS_OutboxBackoff(g_nxsOutAttempts[i]);
      i++;
   }

   NXS_Outbox_Save();
}

#endif
