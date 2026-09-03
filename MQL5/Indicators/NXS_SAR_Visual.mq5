//+------------------------------------------------------------------+
//| NXS_SAR_Visual.mq5                                                 |
//| 30/08 - indicatore visuale richiesto dall'utente per capire DOVE   |
//| e QUANDO la strategia SAR chiama la direzione sbagliata piu' volte |
//| di fila. Disegna SAR/EMA9/EMA21 con gli STESSI parametri e lo      |
//| STESSO timeframe (H4) usati davvero da NXS_Strat_SAR() in          |
//| NXS_Strategies.mqh - indipendentemente dal timeframe del grafico   |
//| su cui viene attaccato (si puo' aprire su M15, H1, D1: il valore   |
//| mostrato resta sempre quello H4 che l'EA vede davvero).            |
//| Sovrappone anche gli ingressi/uscite REALI dei 112 trade del test  |
//| "nudo" di stanotte (nxs_sar_nuda_trades.csv, esportato dal report  |
//| Tester) con frecce colorate ed evidenzia in magenta le catene di   |
//| >=2 perdite consecutive nella STESSA direzione, cosi' si vede a    |
//| occhio dove SAR ha insistito nel verso sbagliato.                  |
//+------------------------------------------------------------------+
#property copyright "NEXUS"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 3
#property indicator_plots   3

#property indicator_label1  "SAR (H4)"
#property indicator_type1   DRAW_ARROW
#property indicator_color1  clrSilver
#property indicator_width1  1

#property indicator_label2  "EMA9 (H4)"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrDodgerBlue
#property indicator_width2  1

#property indicator_label3  "EMA21 (H4)"
#property indicator_type3   DRAW_LINE
#property indicator_color3  clrOrange
#property indicator_width3  1

input ENUM_TIMEFRAMES InpSourceTF     = PERIOD_H4;   // timeframe REALE usato da SAR nella strategia (non cambiare senza motivo)
input double          InpSAR_Step     = 0.02;
input double          InpSAR_Max      = 0.2;
input int             InpEMA9_Period  = 9;
input int             InpEMA21_Period = 21;
input string          InpTradesCsv    = "nxs_sar_nuda_trades.csv";  // esportato in MQL5\Files da server/research_scripts
input bool             InpOnlyStreaks  = false;  // true = mostra solo le catene di perdite >= InpMinStreak
input int              InpMinStreak    = 2;
input color            InpColorWin     = clrLimeGreen;
input color            InpColorLoss    = clrTomato;
input color            InpColorStreak  = clrMagenta;

double BufSar[], BufEma9[], BufEma21[];
int    hSar = INVALID_HANDLE, hEma9 = INVALID_HANDLE, hEma21 = INVALID_HANDLE;

struct STrade{
   datetime entryTime, exitTime;
   int      dir;
   double   entryPrice, exitPrice, pnl;
   string   reason;
   int      streak;
};
STrade g_trades[];

//------------------------------------------------------------------
datetime _ParseTime(string s){
   string s2 = s;
   StringReplace(s2, "-", ".");
   return StringToTime(s2);
}

void LoadTradesCsv(){
   ArrayResize(g_trades, 0);
   int h = FileOpen(InpTradesCsv, FILE_READ|FILE_CSV|FILE_ANSI, ';');
   if(h == INVALID_HANDLE){
      PrintFormat("[NXS SAR VISUAL] impossibile aprire '%s' (errno=%d) - nessun trade disegnato",
                  InpTradesCsv, GetLastError());
      return;
   }
   // salta l'intestazione (8 colonne)
   for(int c = 0; c < 8 && !FileIsEnding(h); c++) FileReadString(h);

   int n = 0;
   while(!FileIsEnding(h)){
      string sEntryTime = FileReadString(h);
      if(StringLen(sEntryTime) == 0) break;
      int    dir        = (int)StringToInteger(FileReadString(h));
      double entryPrice = StringToDouble(FileReadString(h));
      string sExitTime  = FileReadString(h);
      double exitPrice  = StringToDouble(FileReadString(h));
      double pnl        = StringToDouble(FileReadString(h));
      string reason     = FileReadString(h);
      int    streak     = (int)StringToInteger(FileReadString(h));

      STrade t;
      t.entryTime  = _ParseTime(sEntryTime);
      t.exitTime   = _ParseTime(sExitTime);
      t.dir        = dir;
      t.entryPrice = entryPrice;
      t.exitPrice  = exitPrice;
      t.pnl        = pnl;
      t.reason     = reason;
      t.streak     = streak;

      ArrayResize(g_trades, n + 1);
      g_trades[n] = t;
      n++;
      if(FileIsEnding(h)) break;
   }
   FileClose(h);
   PrintFormat("[NXS SAR VISUAL] caricati %d trade da '%s'", n, InpTradesCsv);
}

void DrawTrades(){
   ObjectsDeleteAll(0, "NXST_");
   int shown = 0;
   for(int i = 0; i < ArraySize(g_trades); i++){
      STrade t = g_trades[i];
      bool isStreak = (t.streak >= InpMinStreak);
      if(InpOnlyStreaks && !isStreak) continue;
      shown++;

      color col = isStreak ? InpColorStreak : (t.pnl >= 0 ? InpColorWin : InpColorLoss);
      string base = "NXST_" + IntegerToString(i) + "_";

      string nameE = base + "E";
      ObjectCreate(0, nameE, (t.dir == 1) ? OBJ_ARROW_UP : OBJ_ARROW_DOWN, 0, t.entryTime, t.entryPrice);
      ObjectSetInteger(0, nameE, OBJPROP_COLOR, col);
      ObjectSetInteger(0, nameE, OBJPROP_WIDTH, isStreak ? 3 : 1);
      ObjectSetInteger(0, nameE, OBJPROP_ANCHOR, (t.dir == 1) ? ANCHOR_TOP : ANCHOR_BOTTOM);
      ObjectSetInteger(0, nameE, OBJPROP_SELECTABLE, false);
      ObjectSetString(0, nameE, OBJPROP_TOOLTIP,
         StringFormat("%s @ %.2f\n%s\npnl=%.2f  reason=%s  catena=%d",
                       (t.dir == 1 ? "BUY" : "SELL"), t.entryPrice, TimeToString(t.entryTime, TIME_DATE|TIME_MINUTES),
                       t.pnl, t.reason, t.streak));

      string nameX = base + "X";
      ObjectCreate(0, nameX, OBJ_ARROW, 0, t.exitTime, t.exitPrice);
      ObjectSetInteger(0, nameX, OBJPROP_ARROWCODE, 251);
      ObjectSetInteger(0, nameX, OBJPROP_COLOR, col);
      ObjectSetInteger(0, nameX, OBJPROP_SELECTABLE, false);
      ObjectSetString(0, nameX, OBJPROP_TOOLTIP,
         StringFormat("uscita @ %.2f\n%s\npnl=%.2f  reason=%s",
                       t.exitPrice, TimeToString(t.exitTime, TIME_DATE|TIME_MINUTES), t.pnl, t.reason));

      string nameL = base + "L";
      ObjectCreate(0, nameL, OBJ_TREND, 0, t.entryTime, t.entryPrice, t.exitTime, t.exitPrice);
      ObjectSetInteger(0, nameL, OBJPROP_COLOR, col);
      ObjectSetInteger(0, nameL, OBJPROP_STYLE, STYLE_DOT);
      ObjectSetInteger(0, nameL, OBJPROP_WIDTH, isStreak ? 2 : 1);
      ObjectSetInteger(0, nameL, OBJPROP_RAY, false);
      ObjectSetInteger(0, nameL, OBJPROP_BACK, true);
      ObjectSetInteger(0, nameL, OBJPROP_SELECTABLE, false);

      if(isStreak){
         string nameT = base + "T";
         ObjectCreate(0, nameT, OBJ_TEXT, 0, t.exitTime, t.exitPrice);
         ObjectSetString(0, nameT, OBJPROP_TEXT, StringFormat("catena x%d", t.streak));
         ObjectSetInteger(0, nameT, OBJPROP_COLOR, InpColorStreak);
         ObjectSetInteger(0, nameT, OBJPROP_FONTSIZE, 8);
         ObjectSetInteger(0, nameT, OBJPROP_ANCHOR, (t.dir == 1) ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT_UPPER);
         ObjectSetInteger(0, nameT, OBJPROP_SELECTABLE, false);
      }
   }
   PrintFormat("[NXS SAR VISUAL] disegnati %d trade sul grafico", shown);
   ChartRedraw(0);
}

//------------------------------------------------------------------
int OnInit(){
   SetIndexBuffer(0, BufSar,   INDICATOR_DATA);
   SetIndexBuffer(1, BufEma9,  INDICATOR_DATA);
   SetIndexBuffer(2, BufEma21, INDICATOR_DATA);
   PlotIndexSetInteger(0, PLOT_ARROW, 159);
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(2, PLOT_EMPTY_VALUE, EMPTY_VALUE);

   hSar   = iSAR(_Symbol, InpSourceTF, InpSAR_Step, InpSAR_Max);
   hEma9  = iMA(_Symbol, InpSourceTF, InpEMA9_Period,  0, MODE_EMA, PRICE_CLOSE);
   hEma21 = iMA(_Symbol, InpSourceTF, InpEMA21_Period, 0, MODE_EMA, PRICE_CLOSE);
   if(hSar == INVALID_HANDLE || hEma9 == INVALID_HANDLE || hEma21 == INVALID_HANDLE){
      Print("[NXS SAR VISUAL] errore creazione handle indicatori sorgente");
      return INIT_FAILED;
   }

   LoadTradesCsv();
   DrawTrades();

   IndicatorSetString(INDICATOR_SHORTNAME, "NXS SAR Visual [" + EnumToString(InpSourceTF) + "]");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason){
   ObjectsDeleteAll(0, "NXST_");
   if(hSar   != INVALID_HANDLE) IndicatorRelease(hSar);
   if(hEma9  != INVALID_HANDLE) IndicatorRelease(hEma9);
   if(hEma21 != INVALID_HANDLE) IndicatorRelease(hEma21);
}

int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[],
                 const double &open[], const double &high[], const double &low[], const double &close[],
                 const long &tick_volume[], const long &volume[], const int &spread[]){
   int start = (prev_calculated > 2) ? prev_calculated - 2 : 0;

   int need = Bars(_Symbol, InpSourceTF);
   if(need <= 0) return prev_calculated;

   double srcSar[], srcEma9[], srcEma21[];
   ArraySetAsSeries(srcSar, true);
   ArraySetAsSeries(srcEma9, true);
   ArraySetAsSeries(srcEma21, true);
   int gotS   = CopyBuffer(hSar,   0, 0, need, srcSar);
   int gotE9  = CopyBuffer(hEma9,  0, 0, need, srcEma9);
   int gotE21 = CopyBuffer(hEma21, 0, 0, need, srcEma21);
   if(gotS <= 0 || gotE9 <= 0 || gotE21 <= 0) return prev_calculated;
   int gotMin = MathMin(gotS, MathMin(gotE9, gotE21));

   for(int i = start; i < rates_total; i++){
      int shift = iBarShift(_Symbol, InpSourceTF, time[i], false);
      if(shift < 0 || shift >= gotMin){
         BufSar[i] = EMPTY_VALUE; BufEma9[i] = EMPTY_VALUE; BufEma21[i] = EMPTY_VALUE;
         continue;
      }
      BufSar[i]   = srcSar[shift];
      BufEma9[i]  = srcEma9[shift];
      BufEma21[i] = srcEma21[shift];
   }
   return rates_total;
}
