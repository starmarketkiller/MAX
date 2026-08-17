//+------------------------------------------------------------------+
//|  NXS_StrategyProfiles.mqh - Profili PER-STRATEGIA dal backtest    |
//|                                                                    |
//|  "L'EA deve operare come nel backtest": ogni strategia usa i SUOI  |
//|  parametri (ATR SL/TP), i SUOI gate, il SUO timeframe e il SUO     |
//|  rischio. I valori vengono dall'ottimizzazione MULTI-TIMEFRAME per |
//|  strategia su dati reali (XAUUSD, D1/H4/H1 -> ognuna tenuta sul TF |
//|  dove rende meglio). Fonte: results/best_per_strategy_multitf_*.   |
//|                                                                    |
//|  Dietro InpUseStrategyProfiles. Se una strategia non ha profilo,   |
//|  restano i valori globali (retrocompatibile).                      |
//+------------------------------------------------------------------+
#ifndef __NXS_STRATEGY_PROFILES_MQH__
#define __NXS_STRATEGY_PROFILES_MQH__

// Ritorna true se la strategia ha un profilo dal backtest, riempiendo i suoi
// parametri: slMult/tpMult (x ATR), htf (richiede allineamento HTF), beR
// (breakeven a beR x rischio, 0=off), trailATR (trailing a trailATR x ATR, 0=off).
bool NXS_Profile_Get(const string name, double &slMult, double &tpMult,
                     bool &htf, double &beR, double &trailATR){
   slMult = 0; tpMult = 0; htf = false; beR = 0; trailATR = 0;
   // --- Ricetta multi-TF ottimale per-strategia (XAUUSD, dati reali) ---
   // 17/07: analisi MFE/MAE sul sito (segnale ADX_RSI seguito 40 barre a
   // prescindere da dove sta oggi SL/TP) - 85.6% dei segnali raggiunge
   // almeno 1R a favore, MFE medio 4.52R contro un TP di 4.0 - il trigger
   // azzecca la direzione, il TP stretto tagliava il movimento. TP10.0 +
   // breakeven a 1.5R (lascia correre ma protegge una volta partiti):
   // PF1.48->1.97, net +7.191->+8.991 (10y sito). DD leggermente peggiore
   // (11.54%->12.48%, campione -23%) - non ancora validato su MT5.
   // 10/08 - AMD_CONT/LDN_REVERSAL/AMD_REVERSAL: mai avuto un profilo (erano
   // nel gruppo "session/Elliott, da ottimizzare su MT5/intraday"). Config
   // demo 15-strategie: scan multi-TF su dati Dukascopy reali (35 strategie x
   // 15m/30m/1h/4h/1d, IS/OOS) - SL/TP di default (nessuna leva d'uscita
   // migliora, verificato oggi su tutte e 15 le candidate demo), htf=false
   // (mai testato), TF dal miglior OOS PF con campione credibile. Terreno
   // vergine su MT5 reale - nessuna storia precedente ne' a favore ne' contro,
   // a differenza di MACD/FVG_CONT (vedi NXS_Profile_Risk sotto).
   if(name == "AMD_CONT")          { slMult=1.5; tpMult=3.0; htf=false; beR=0.0; trailATR=0.0; return true; }  // 30m OOS PF1.52 n169
   if(name == "LDN_REVERSAL")      { slMult=1.5; tpMult=3.0; htf=false; beR=0.0; trailATR=0.0; return true; }  // 15m OOS PF1.23 n66
   if(name == "AMD_REVERSAL")      { slMult=1.5; tpMult=3.0; htf=false; beR=0.0; trailATR=0.0; return true; }  // 15m OOS PF1.97 n59
   if(name == "ADX_RSI")           { slMult=1.0; tpMult=10.0; htf=true ; beR=1.5; trailATR=0.0; return true; }  // v2.5.1 - vedi commento sopra
   if(name == "BB_SQUEEZE")        { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d POCHI_DATI PF2.92 R2.0
   // 16/07: la "PF3.46" sopra veniva dallo screening sito, ma il proxy
   // sig_bjorgum() del sito era un EMA ribbon (bug, stesso tipo di quello
   // gia' trovato su SAR il 15/07) - non testava mai la vera logica pivot-
   // bounce di questa funzione. Sui 6 anni reali MT5 questa config e' -8.6R,
   // 5/6 anni negativi. Corretto il proxy sito e rifatto lo sweep con la
   // logica vera: senza filtro HTF (che qui schiaccia il campione a 3-6
   // trade/10y, troppo pochi per giudicare) SL1.5/TP3.0 e' la config con
   // miglior DD trovata (PF1.20, DD13.4%, 110 trade/10y) - ipotesi da
   // validare su MT5 isolato (selector=6), non ancora confermata.
   if(name == "BJORGUM")           { slMult=1.5; tpMult=3.0; htf=false; beR=0.0; trailATR=0.0; return true; }  // 4h - fix 16/07, vedi commento sopra
   if(name == "BOLLINGER")         { slMult=1.0; tpMult=2.0; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d OK PF1.17 R0.94
   if(name == "BREAKOUT_ACC")      { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.86 R0.63
   // 12/08 - CRT non aveva mai una voce qui: la sua SL/TP e' SEMPRE quella
   // ancorata al wick/sweep (NXS_Strat_CRT in NXS_Strategies_SMC.mqh, "dai
   // livelli reali del pattern, NON da NXS_DefaultSLTP") - slMult/tpMult
   // sotto sono INERTI per costruzione (mai letti per questa strategia,
   // verificato prima di aggiungerli - vedi NXS_DefaultSLTP: usa il
   // profilo solo se pSl>0 && pTp>0, qui restano 0). Aggiunta solo per
   // portare beR (breakeven) dalla ricerca dedicata di oggi: baseline vero
   // OOS PF1.25/DD36.73% (drawdown flottante gia' noto, vedi vault "Fase C
   // Recovery Baseline e Rischio Flottante"), con be=1.0R + overlay
   // trailing 1.0x (vedi NXS_Profile_TrailK sotto) OOS PF1.25->1.39,
   // DD36.73%->28.05%, walk-forward 1.24/1.39/1.59/1.34/1.40 - vedi vault
   // "NEXUS EA - Ottimizzazione Uscite Strutturali CRT e FVG_CONT (12-08)".
   if(name == "CRT")               { slMult=0.0; tpMult=0.0; htf=false; beR=1.0; trailATR=0.0; return true; }  // 30m - vedi nota 12/08 sopra, slMult/tpMult inerti
   if(name == "THREE_BAR_DELIVERY_BREAK")              { slMult=1.5; tpMult=3.0; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 4h; trail ora via overlay per-strategia (v2.4.5)
   if(name == "DISP_REBAL")        { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF1.68 R2.0
   if(name == "EMA_PULLBACK")      { slMult=1.5; tpMult=4.0; htf=true ; beR=0.0; trailATR=0.0; return true; }  // v2.5.0 sweep 10y: HTF ON + SL1.5/TP4.0 -> PF1.52
   // 12/08 - ricerca dedicata uscite post-scoperta overlay trailing sempre
   // attivo (NXS_TrailingATR.mqh, vedi NXS_Profile_TrailK sotto): il vero
   // baseline live (sl1.0/tp4.5/htf/overlay 2.5x) dava OOS PF1.55/DD13.41%.
   // Testato sl/tp/be sopra l'overlay FISSO (non disattivabile per-strategia
   // con l'architettura attuale): OOS PF1.55->1.74, DD13.41%->7.06% (quasi
   // dimezzato), walk-forward 1.36/1.21/0.96/1.72/1.67 - vedi vault "NEXUS
   // EA - Ottimizzazione Uscite Strutturali CRT e FVG_CONT (12-08)".
   if(name == "FVG_CONT")          { slMult=1.5; tpMult=6.0; htf=true ; beR=1.5; trailATR=0.0; return true; }  // 4h - vedi nota 12/08 sopra
   if(name == "FVG_MIT")           { slMult=1.5; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF2.04 R2.0
   // 13/08 - FVG_MIT_WINDOW: slMult/tpMult restano inerti come per CRT (SL/TP
   // sono calcolati dal registro zone in NXS_Strat_FVG_Mitigation_Window, non
   // da un multiplo ATR fisso) - qui conta solo htf. htf=true viene dal
   // miglior candidato del batch grid 12/08 (non da una ricerca dedicata come
   // CRT/FVG_CONT/TSI - meno certo di quei tre, vedi commento nella funzione).
   if(name == "FVG_MIT_WINDOW")    { slMult=0.0; tpMult=0.0; htf=true ; beR=0.0; trailATR=0.0; return true; }
   if(name == "ICHIMOKU")          { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF1.75 R1.13
   if(name == "IFVG")              { slMult=1.5; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF2.51 R2.0
   if(name == "LIQ_SWEEP")         { slMult=1.5; tpMult=3.0; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF2.48 R2.0
   if(name == "LIQ_VOID")          { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 4h FORTE PF1.67 R0.65
   if(name == "LONDON_BO")         { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.86 R0.63
   // 16/07: "robusta su sito E MT5" sopra era basato su un proxy sito
   // sbagliato (incrocio MACD-line/zero, non MACD/signal+EMA200 come la
   // vera funzione qui sotto - stesso tipo di bug di SAR/BJORGUM). Proxy
   // corretto e ri-testato: con la logica VERA, il sito resta positivo su
   // OGNI timeframe/HTF provato (PF1.15-1.52, 108-141 trade) - ancora piu'
   // forte di prima. Eppure MT5 reale (1496 trade su 10 anni) e' negativo
   // in 5 anni su 10. Segnale confermato robusto due volte, esecuzione MT5
   // no: rinforza il sospetto di un problema di esecuzione (spread/sizing/
   // interazione gate), non di trigger - vedi vault NEXUS EA - Ricerca
   // Esterna e Test A-B per Strategia.
   // 17/07: analisi MFE/MAE sul sito (segnale MACD seguito 40 barre a
   // prescindere da dove sta oggi SL/TP) - 70.5% dei segnali raggiunge
   // almeno 1R a favore, MFE medio 2.40R contro un TP di 3.0 - il trigger
   // azzecca la direzione piu' spesso di quanto il TP stretto la catturi.
   // TP8.0 + breakeven a 1R: PF1.48->2.05, DD6.23%->5.85%, net
   // +2.879->+3.643 (10y sito, campione -35%). Non ancora validato su MT5.
   if(name == "MACD")              { slMult=2.0; tpMult=8.0; htf=true ; beR=1.0; trailATR=0.0; return true; }  // v2.5.1 - vedi commento sopra
   if(name == "MALAYSIAN_SNR")     { slMult=2.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.96 R2.0
   if(name == "OB_MIT")            { slMult=1.5; tpMult=4.0; htf=false; beR=0.0; trailATR=0.0; return true; }  // v2.5.0 sweep 10y: SL1.5/TP4.0 + trail -> PF1.80
   if(name == "ORDER_BLOCK")       { slMult=1.0; tpMult=3.0; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.55 R1.71
   if(name == "OTE_CONT")          { slMult=2.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.78 R2.0
   if(name == "RANGE_FADE")        { slMult=1.0; tpMult=2.0; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d OK PF1.17 R0.94
   // 16/07: il proxy sito era un semplice rientro RSI da ipercomprato/
   // ipervenduto, non una vera divergenza prezzo/RSI come questa funzione
   // (stesso tipo di bug di SAR/BJORGUM/MACD). Corretto e ri-testato: con
   // la divergenza vera, H1 senza HTF (= config attuale) resta la migliore
   // (PF1.34, 84 trade) - config gia' giusta. Ma MT5 reale (678 trade)
   // resta CRITICA la maggior parte degli anni: stesso sospetto di
   // esecuzione trovato su MACD/FVG_CONT, non di trigger/config.
   if(name == "RSI_DIV")           { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // config invariata (gia' la migliore trovata anche col proxy corretto)
   if(name == "SAR")               { slMult=1.5; tpMult=4.0; htf=true ; beR=0.0; trailATR=0.0; return true; }  // v2.5.0 sweep 10y: HTF ON + SL1.5/TP4.0 -> PF1.52
   if(name == "SH_BMS_RTO")        { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.66 R1.29
   // 14/08 - SH_BMS_RTO_V2: slMult/tpMult inerti come CRT (SL/TP calcolati
   // dalla state machine in NXS_Strat_SH_BMS_RTO_V2, non da un multiplo ATR
   // fisso). htf=false: il gate ADX>=20+trend di struttura e' gia' interno
   // alla state machine (fedele a Python), non serve il gate HTF generico.
   if(name == "SH_BMS_RTO_V2")     { slMult=0.0; tpMult=0.0; htf=false; beR=0.0; trailATR=0.0; return true; }
   if(name == "SMS_BMS_RTO")       { slMult=1.0; tpMult=4.5; htf=false; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.66 R1.29
   if(name == "STRUCT_REACT")      { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1h FORTE PF1.87 R2.0
   // 12/08 - ricerca dedicata uscite: TSI e' un "problema aperto" del
   // nucleo mai risolto (vedi vault "I due problemi aperti del nucleo,
   // approfonditi", 11/08). Baseline vero (sl1.5/tp4.5/be1.0/htf/overlay
   // 1.5x) OOS PF1.35/DD2.97%/n31, IS addirittura sotto pareggio (0.73).
   // Griglia da 330 combinazioni: 79 sopra baseline, i migliori raggruppati
   // sulla stessa zona (SL/TP molto larghi) - un plateau, non un picco
   // isolato. Vincitore: OOS PF1.35->2.41, DD2.97%->1.99%, walk-forward
   // 1.76/1.91/1.97/1.84/2.95 (mai sotto 1.76). Campione ancora sottile
   // (22-24 trade OOS, D1) - la scoperta piu' fragile di oggi, trattarla
   // come ipotesi forte da confermare, non un fatto acquisito come CRT/
   // FVG_CONT. Vedi vault "NEXUS EA - TSI Ricerca Dedicata Uscite (12-08)".
   if(name == "TSI")               { slMult=2.0; tpMult=6.0; htf=true ; beR=1.0; trailATR=0.0; return true; }  // 1d - vedi nota 12/08 sopra
   if(name == "TURTLE_SOUP")       { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1h FORTE PF1.83 R2.0
   if(name == "WEEKLY_EXP")        { slMult=1.0; tpMult=4.5; htf=true ; beR=0.0; trailATR=0.0; return true; }  // 1d FORTE PF1.86 R0.63
   // Le session/Elliott (SILVER_BULLET, AMD_*, JUDAS, LDN/NY_REVERSAL, PO3,
   // ELLIOTT): da ottimizzare su MT5/intraday -> nessun profilo, usano i globali.
   return false;
}

// Timeframe ottimale per la strategia (multi-TF). L'EA deve cercare il trigger
// di ogni strategia su QUESTO timeframe. Se non c'e' profilo -> PERIOD_CURRENT
// (usa il TF di ingresso globale InpTFEntry, retrocompatibile).
ENUM_TIMEFRAMES NXS_Profile_TF(const string name){
   if(name == "ADX_RSI")           return PERIOD_D1;
   if(name == "BB_SQUEEZE")        return PERIOD_D1;
   if(name == "BJORGUM")           return PERIOD_H4;
   if(name == "BOLLINGER")         return PERIOD_D1;
   if(name == "BREAKOUT_ACC")      return PERIOD_D1;
   if(name == "THREE_BAR_DELIVERY_BREAK")              return PERIOD_H4;
   if(name == "DISP_REBAL")        return PERIOD_H4;
   // 10/08 - scan multi-TF (Dukascopy reale, 5 TF, IS/OOS): EMA_PULLBACK
   // rendeva meglio su H1 (OOS PF1.54, 124 trade - campione ampio e
   // credibile, non un caso limite) invece di H4. Aggiornato. Le altre
   // strategie con profilo esistente restano sul loro TF anche dove lo scan
   // di oggi suggeriva un'alternativa (es. TSI/SAR): un solo split IS/OOS
   // di oggi non basta a scavalcare un TF gia' radicato nel profilo
   // esistente - vedi vault NEXUS EA - Config Demo 15 Strategie (10-08).
   if(name == "EMA_PULLBACK")      return PERIOD_H1;
   if(name == "FVG_CONT")          return PERIOD_H4;
   // 11/08 - FVG_MIT/LONDON_BO: il profilo diceva D1, ma la riverifica
   // sullo storico ampliato mostra che era sbagliato - su D1 il campione
   // era troppo sottile per essere reale (LONDON_BO: 4-5 trade totali!),
   // 4h e' il TF gia' confermato dallo scan multi-TF del 10/08 e ora
   // ri-confermato con campioni utilizzabili (LONDON_BO OOS PF1.38/99,
   // walk-forward 4/5; FVG_MIT OOS PF1.01/78, quasi pareggio ma almeno
   // un campione vero). Vedi NEXUS EA - Riverifica su Storico Ampliato.
   if(name == "FVG_MIT")           return PERIOD_H4;
   if(name == "FVG_MIT_WINDOW")    return PERIOD_H4;
   if(name == "ICHIMOKU")          return PERIOD_H4;
   if(name == "IFVG")              return PERIOD_H4;
   if(name == "LIQ_SWEEP")         return PERIOD_D1;
   if(name == "LIQ_VOID")          return PERIOD_H4;
   if(name == "LONDON_BO")         return PERIOD_H4;
   if(name == "MACD")              return PERIOD_H4;
   if(name == "AMD_CONT")          return PERIOD_M30;
   if(name == "LDN_REVERSAL")      return PERIOD_M15;
   if(name == "AMD_REVERSAL")      return PERIOD_M15;
   if(name == "MALAYSIAN_SNR")     return PERIOD_D1;
   if(name == "OB_MIT")            return PERIOD_D1;
   if(name == "ORDER_BLOCK")       return PERIOD_D1;
   if(name == "OTE_CONT")          return PERIOD_D1;
   if(name == "RANGE_FADE")        return PERIOD_D1;
   if(name == "RSI_DIV")           return PERIOD_H1;
   if(name == "SAR")               return PERIOD_H4;
   if(name == "SH_BMS_RTO")        return PERIOD_D1;
   if(name == "SH_BMS_RTO_V2")     return PERIOD_H1;
   if(name == "SMS_BMS_RTO")       return PERIOD_D1;
   if(name == "STRUCT_REACT")      return PERIOD_H1;
   if(name == "TSI")               return PERIOD_D1;
   if(name == "TURTLE_SOUP")       return PERIOD_H1;
   if(name == "WEEKLY_EXP")        return PERIOD_D1;
   // 11/08 - CRT: 30m e' il TF con il campione piu' ampio E il walk-forward
   // piu' pulito dopo la riverifica sullo storico ampliato (5/5 su tutti e
   // tre i TF provati - 4h/1h/30m - ma 30m ha quasi 12.000 trade totali
   // contro le centinaia degli altri, il campione statisticamente piu'
   // solido). Vedi NEXUS EA - Riverifica su Storico Ampliato (11-08).
   if(name == "CRT")               return PERIOD_M30;
   return PERIOD_CURRENT;
}

// Rischio % per-strategia (dimensionato a budget di drawdown ~10% nel backtest).
// Ritorna <=0 se non c'e' profilo -> usa il rischio globale InpRiskPercent.
//
// 12/08 — RITARATO per conto piccolo (~200-300 EUR), su richiesta esplicita
// dell'utente: a 0.5% flat il lotto minimo XAUUSD spesso supera il budget
// nominale (vedi InpMaxRiskAtMinLotPct), quindi l'EA di fatto non tradava.
// Nuova fascia a 5 livelli per le 16 strategie del nucleo attivo (demo/live),
// costruita incrociando DUE evidenze indipendenti - non una sola:
//   1) PF reale MT5 (dove esiste una storia — la piu' affidabile, e' quello
//      che il conto ha davvero visto, comprende slippage/spread/esecuzione)
//   2) OOS + walk-forward Python sullo storico Dukascopy ampio 2019-2026
//      (vedi vault "NEXUS EA - Riverifica su Storico Ampliato" e "NEXUS EA -
//      Diagnosi per strategia", 11/08)
// Le red flag di esecuzione reale nota (MACD, FVG_CONT — CRITICA su MT5 pur
// con backtest Python forte) SOVRASCRIVONO un buon numero Python: eseguire
// male dal vivo conta piu' di un backtest pulito. Le altre 20 strategie non
// nel nucleo attuale restano ai valori precedenti (fuori scope di questo
// giro, nessuna nuova evidenza raccolta su quelle).
//
double NXS_Profile_Risk(const string name){
// Tier S (5.0%) — doppia conferma forte, nessuna red flag:
   if(name == "EMA_PULLBACK")      return 5.0;    // reale PF1.63 + Python WF4/5 (1.47->1.52 ricetta uff.)
   if(name == "SAR")               return 5.0;    // reale PF1.31/196 trade (workhorse) + Python OOS1.22/276
   // TURTLE_SOUP: reale PF2.04 "la stella" e' con la RICETTA UFFICIALE attiva
   // (slMult1.0/tpMult4.5/htf, vedi NXS_Profile_Get sopra) - sul flat baseline
   // il Python e' debole (0.96/398, quasi pareggio), con la stessa ricetta
   // sale a 1.15 WF4/5. Coerente, non contraddittorio: la ricetta e' cio' che
   // gira davvero, non il flat.
   if(name == "TURTLE_SOUP")       return 5.0;
// Tier A (2.5%) — terreno vergine su MT5 ma Python solido/campione ampio,
// oppure singola conferma forte con una riserva strutturale nota:
   if(name == "LONDON_BO")         return 2.5;    // Python OOS1.38/99 WF4/5, nessuna storia reale
   if(name == "AMD_CONT")          return 2.5;    // Python OOS1.38/282 WF4/5, campione grande
   if(name == "ADX_RSI")           return 2.5;    // reale PF1.14 positivo, ma campione D1 sottile -> non tier S
   // CRT: l'evidenza Python e' la piu' forte di tutta la sessione (WF5/5 su
   // 3 TF, ~20.000 trade) ma resta terreno vergine su MT5 E ha una riserva
   // strutturale nota (stop ancorato al wick del sweep, non un multiplo ATR -
   // drawdown flottante 107% osservato in una finestra quando il wick e'
   // minimo, vedi vault "Fase C Recovery Baseline e Rischio Flottante").
   // Floor minimo sullo stop aggiunto in NXS_Strat_CRT stesso giro (12/08) -
   // tier A e non S finche' il floor non e' verificato su MT5 reale.
   if(name == "CRT")               return 2.5;
   // 14/08 - SH_BMS_RTO_V2: terreno vergine su MT5, ma walk-forward 5/5 su
   // 1h (il piu' pulito trovato in sessione, campioni grandi e consistenti
   // 60-68 trade/finestra) - Tier A coerente con AMD_CONT/LONDON_BO (stessa
   // qualita' di evidenza: vergine + campione ampio + WF pulito).
   if(name == "SH_BMS_RTO_V2")     return 2.5;
// Tier B (1.2%) — terreno vergine, Python piu' modesto o meno pulito:
   if(name == "LDN_REVERSAL")      return 1.2;    // Python OOS1.22/145 WF4/5
   if(name == "AMD_REVERSAL")      return 1.2;    // Python OOS1.59/117 ma WF solo 3/5
// Tier C (0.5%) — red flag di esecuzione reale nota, o debolezza Python
// conclamata (DEBOLE/IS negativo/WF incoerente): vive ma a size minima,
// stesso principio "non spente, tagliate" gia' in uso prima di questo giro.
   if(name == "MACD")              return 0.5;    // CRITICA storica su MT5 (PF1.10 al limite, mai chiarita)
   if(name == "FVG_CONT")          return 0.5;    // CRITICA su MT5 reale (PF0.79) pur con backtest Python forte
   if(name == "BREAKOUT_ACC")      return 0.5;    // Python DEBOLE, OOS2.71 smentito da WF reale 1/5 (rumore D1)
   if(name == "LIQ_SWEEP")         return 0.5;    // Python DEBOLE, IS 0.91 sotto pareggio
   if(name == "THREE_BAR_DELIVERY_BREAK") return 0.5;  // Python DEBOLE, WF 2/5 incoerente tra finestre
   // FVG_MIT: 13/08 - portata in MQL5 la variante FVG_MIT_WINDOW (vedi
   // NXS_Profile_Enabled sotto: sostituisce FVG_MIT nel nucleo demo). Stessa
   // fascia di rischio della base finche' non c'e' storia reale su MT5 -
   // il porting cambia il trigger, non lo status "da verificare dal vivo".
   if(name == "FVG_MIT")           return 0.5;
   if(name == "FVG_MIT_WINDOW")    return 0.5;
// Tier D (0.3%) — problema aperto confermato, nessuna soluzione trovata
// dopo piu' tentativi, l'unica del nucleo sotto pareggio in OOS:
   if(name == "TSI")               return 0.3;    // reale PF0.86 "in ripresa" ma OOS Python 0.71/39
// --- Fuori dal nucleo attuale, valori precedenti invariati (fuori scope) ---
   // 12/08 - BJORGUM: commento precedente ("PF 1.90 reale") era STALE -
   // superato dalla chiusura di sessione dell'11/08 (-8.6R reali, 5/6 anni
   // negativi, vedi vault "Strategie Escluse... §5"). Corretto qui perche'
   // trovato durante questo giro, anche se BJORGUM non e' nel nucleo attivo
   // (nessun profilo enabled): 2.5 sarebbe stato un tier alto ingiustificato
   // se mai riattivata.
   if(name == "BJORGUM")           return 0.4;
   if(name == "ICHIMOKU")          return 1.8;    // PF 1.91 reale (campione piccolo)
   if(name == "RSI_DIV")           return 1.5;    // PF 1.21 reale, 98 trade
   if(name == "ORDER_BLOCK")       return 0.5;    // PF 0.67
   if(name == "OB_MIT")            return 0.5;    // PF 0.38 (crollata per interazione)
   if(name == "MALAYSIAN_SNR")     return 0.4;    // PF 0.00
   if(name == "BOLLINGER")         return 0.6;    // riportata 2.4.0, in osservazione
   if(name == "BB_SQUEEZE")        return 0.6;
   if(name == "DISP_REBAL")        return 0.5;
   if(name == "IFVG")              return 0.5;
   if(name == "LIQ_VOID")          return 0.5;
   if(name == "OTE_CONT")          return 0.5;
   if(name == "RANGE_FADE")        return 0.6;
   if(name == "SH_BMS_RTO")        return 0.5;
   if(name == "SMS_BMS_RTO")       return 0.5;
   if(name == "STRUCT_REACT")      return 0.5;
   if(name == "WEEKLY_EXP")        return 0.5;
   return 0.0;
}

// v2.4.5 — Larghezza del TRAILING per-strategia (x ATR), dai dati reali del test
// v2.4.4: il trail largo (2.5) fa VOLARE le trend/continuazione ma DISTRUGGE le
// mean-reversion (restituiscono i profitti). Quindi:
//   - trend/continuazione -> trail LARGO (2.5): "lascia correre"
//   - mean-reversion/alto-WR -> trail STRETTO (1.5): prendi profitto presto
// Ritorna <=0 se non specificato -> l'overlay usa il globale InpAtrTrailMult.
double NXS_Profile_TrailK(const string name){
   // --- LARGO 2.5 (trend/continuazione: corrono) ---
   if(name == "TURTLE_SOUP")   return 2.5;   // 2.04->2.72 col largo
   if(name == "FVG_CONT")      return 2.5;   // 0.88->1.99
   if(name == "ORDER_BLOCK")   return 2.5;   // 0.94->2.03
   if(name == "OB_MIT")        return 2.5;   // 0.46->1.52
   if(name == "SAR")           return 2.5;   // 1.14->1.21
   if(name == "ADX_RSI")       return 2.5;   // 1.03->1.15
   if(name == "LIQ_SWEEP")     return 2.5;   // stessa famiglia SMC
   if(name == "LIQ_VOID")      return 2.5;
   if(name == "SH_BMS_RTO")    return 2.5;
   if(name == "SMS_BMS_RTO")   return 2.5;
   if(name == "IFVG")          return 2.5;
   if(name == "FVG_MIT")       return 2.5;
   if(name == "FVG_MIT_WINDOW") return 3.0;  // 13/08 - batch grid 12/08, piu' largo della base
   if(name == "LONDON_BO")     return 2.5;   // breakout continuation
   if(name == "BREAKOUT_ACC")  return 2.5;
   if(name == "WEEKLY_EXP")    return 2.5;
   if(name == "OTE_CONT")      return 2.5;
   if(name == "DISP_REBAL")    return 2.5;
   // --- STRETTO 1.5 (mean-reversion/alto-WR: prendono profitto) ---
   if(name == "RSI_DIV")       return 1.5;   // 1.21->0.81 col largo -> stringi
   if(name == "BJORGUM")       return 1.5;   // 1.89->0.89
   if(name == "ICHIMOKU")      return 1.5;   // 2.34->0
   if(name == "EMA_PULLBACK")  return 1.5;   // 1.37->1.00
   if(name == "MACD")          return 1.5;   // 1.27 vs 1.23 ~neutro -> stretto
   // 12/08 - TSI: ricerca dedicata uscite (vedi NXS_Profile_Get sopra),
   // 1.5->2.0 - il vincitore usava un trail piu' largo del default stretto
   // qui sotto, coerente con l'SL/TP molto piu' larghi trovati nello
   // stesso giro (il pattern di TSI si comporta piu' da trend/continuazione
   // con questa configurazione che da mean-reversion).
   if(name == "TSI")           return 2.0;
   if(name == "BOLLINGER")     return 1.5;   // mean-reversion
   if(name == "BB_SQUEEZE")    return 1.5;
   if(name == "RANGE_FADE")    return 1.5;
   if(name == "STRUCT_REACT")  return 1.5;
   if(name == "MALAYSIAN_SNR") return 1.5;
   if(name == "THREE_BAR_DELIVERY_BREAK")          return 1.5;
   // 12/08 - CRT non aveva mai una voce qui (fallback al globale 2.5).
   // Ricerca dedicata: 1.0 (piu' stretto del globale) e' il vincitore
   // insieme a be=1.0R (vedi NXS_Profile_Get sopra) - coerente con lo SL
   // di CRT gia' stretto per natura (ancorato al wick), un trail piu'
   // stretto lo segue meglio invece di lasciargli troppo spazio.
   if(name == "CRT")           return 1.0;
   return 0.0;   // fallback -> globale
}

// v2.4.6 — Soglia di ATTIVAZIONE del trailing per-strategia (x ATR di profitto
// prima che il trail inizi a stringere). Le vincite PICCOLE vanno protette SUBITO
// (0.5), altrimenti il trail non scatta mai e restituiscono tutto (era il bug di
// ICHIMOKU: a +1.0 ATR non arrivava -> 0 protezione -> tutte perse). Le vincite
// GRANDI (trend) hanno spazio per svilupparsi (1.0). <=0 -> usa il globale.
double NXS_Profile_TrailActivate(const string name){
   // --- PRESTO 0.5 (vincita piccola/mean-reversion: proteggi subito) ---
   if(name == "ICHIMOKU")      return 0.5;   // il fix: a +1.0 non arrivava mai
   if(name == "ADX_RSI")       return 0.5;   // vincite ~0.2R
   if(name == "BJORGUM")       return 0.5;
   if(name == "ORDER_BLOCK")   return 0.5;
   if(name == "OB_MIT")        return 0.5;
   if(name == "RSI_DIV")       return 0.5;
   if(name == "EMA_PULLBACK")  return 0.5;
   if(name == "MACD")          return 0.5;
   if(name == "TSI")           return 0.5;
   if(name == "BOLLINGER")     return 0.5;
   if(name == "BB_SQUEEZE")    return 0.5;
   if(name == "RANGE_FADE")    return 0.5;
   if(name == "STRUCT_REACT")  return 0.5;
   if(name == "MALAYSIAN_SNR") return 0.5;
   if(name == "THREE_BAR_DELIVERY_BREAK")          return 0.5;
   if(name == "LONDON_BO")     return 0.5;
   if(name == "LIQ_SWEEP")     return 0.5;
   // --- TARDI 1.0 (vincita grande/trend: lascia sviluppare) ---
   if(name == "TURTLE_SOUP")   return 1.0;
   if(name == "FVG_CONT")      return 1.0;
   if(name == "SAR")           return 1.0;
   if(name == "FVG_MIT")       return 1.0;
   if(name == "FVG_MIT_WINDOW") return 1.0;
   if(name == "IFVG")          return 1.0;
   if(name == "LIQ_VOID")      return 1.0;
   if(name == "SH_BMS_RTO")    return 1.0;
   if(name == "SMS_BMS_RTO")   return 1.0;
   if(name == "BREAKOUT_ACC")  return 1.0;
   if(name == "WEEKLY_EXP")    return 1.0;
   if(name == "OTE_CONT")      return 1.0;
   if(name == "DISP_REBAL")    return 1.0;
   return 0.0;   // fallback -> globale
}

// Solo SL/TP (per NXS_DefaultSLTP). Ritorna true se c'e' il profilo.
bool NXS_Profile_SLTP(const string name, double &slMult, double &tpMult){
   bool htf; double beR, trailATR;
   return NXS_Profile_Get(name, slMult, tpMult, htf, beR, trailATR);
}

// Gate HTF per la strategia. hasProfile=true se ha profilo; htf=valore richiesto.
bool NXS_Profile_HTF(const string name, bool &htf){
   double sl, tp, be, tr; bool h;
   if(NXS_Profile_Get(name, sl, tp, h, be, tr)){ htf = h; return true; }
   htf = false; return false;
}

// Va tradata? false per le strategie che PERDONO in modo sistematico su MT5
// (dati broker), indipendentemente dal verdetto del sito (dati Yahoo).
// Disabilitate dal test reale v2.3.1 (3 settimane): la loro logica MQL5 non
// regge sui dati del broker -> perdite confermate, si spengono finche' non le
// riallineiamo al motore del sito.
//
// 10/08 - FASE DEMO 15-STRATEGIE: su richiesta esplicita, il conto demo deve
// far lavorare solo le 15 candidate scelte dal report di stato ottimizzazione
// (buone + benino + potenziale, non le "rare per design"/CRITICA), non tutte
// e 35. Questo e' l'UNICO gate uniforme che vale per tutte le strategie a
// prescindere che abbiano anche un InpStrat_XXX dedicato (solo 9 delle 15 lo
// hanno - vedi NXS_Inputs.mqh "STRATEGIES TOGGLE"; le altre 6, incluse
// TURTLE_SOUP/FVG_MIT, non hanno alcun altro modo di essere isolate senza
// ricompilare). Default cambiato da true a false: attivo SOLO dietro
// InpUseStrategyProfiles=true, quindi non tocca un conto che lo tiene off.
// Per tornare al comportamento "tutte attive" di prima: default a true, o
// InpUseStrategyProfiles=false in .set. Vedi vault NEXUS EA - Config Demo
// 15 Strategie (10-08).
bool NXS_Profile_Enabled(const string name){
   if(name == "BREAKOUT_ACC")           return true;
   // 14/08 - TURTLE_SOUP disattivata: era Tier S (la piu' fidata, doppia
   // conferma MT5+Python) ma il batch di riverifica costi di oggi (dati
   // Dukascopy ampi, costi retail_standard in R, n=250 OOS - campione
   // largo, non rumore) mostra PF 0.55 e DD 62.7%. Il vecchio PF2.04 "reale
   // MT5" citato in NXS_Profile_Risk sotto non aveva mai visto questo
   // standard di costi. Vedi batch nucleus_cost_reverify_14-08.py.
   if(name == "TURTLE_SOUP")            return false;
   if(name == "MACD")                   return true;
   if(name == "LONDON_BO")              return true;
   // 14/08 - FVG_MIT_WINDOW disattivata: stesso batch costi di oggi mostra
   // PF retail 0.98 (da 1.64 senza costi) e DD che salta da 6% a 21.4% -
   // non regge il gate. La "doppia conferma" del 13/08 (vedi sotto) era
   // anch'essa senza costi realistici applicati.
   if(name == "FVG_MIT_WINDOW")         return false;
   if(name == "LIQ_SWEEP")              return true;
   if(name == "AMD_CONT")               return true;
   if(name == "FVG_CONT")               return true;
   if(name == "TSI")                    return true;
   if(name == "ADX_RSI")                return true;
   if(name == "SAR")                    return true;
   if(name == "EMA_PULLBACK")           return true;
   if(name == "THREE_BAR_DELIVERY_BREAK") return true;
   if(name == "LDN_REVERSAL")           return true;
   if(name == "AMD_REVERSAL")           return true;
   // 14/08 - CRT disattivata: il WF5/5 citato sotto era SENZA costi. Con
   // costi retail applicati in R (spread/risk_dist esplode sugli stop a
   // wick di CRT) il PF crolla a 0.08-0.25 e il DD chiuso arriva al 100%
   // su OGNI combinazione di floor MinStopATR testata (0/0.3/0.5/0.8) -
   // revisione approfondita 14/08, nessun parametro salva l'edge. Vedi
   // vault e nucleus_cost_reverify_14-08.py.
   if(name == "CRT")                    return false;
   // 14/08 - SH_BMS_RTO_V2 disattivata: Gate 1 del Validator Framework con
   // costi retail dava gia' PF 0.75/DD 50%; il batch nucleo (campione piu'
   // ampio, n=140) conferma PF 0.89 - sotto pareggio, non un quasi.
   if(name == "SH_BMS_RTO_V2")          return false;
   // Le rimanenti restano note per la cronaca (gia' spente da prima per
   // perdite reali confermate, non fanno parte del nucleo demo):
   //   BB_SQUEEZE, STRUCT_REACT, DISP_REBAL, OTE_CONT, ICHIMOKU.
   return false;   // 10/08 - era true: tutte le altre spente per la fase demo
}

#endif
