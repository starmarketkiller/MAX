//+------------------------------------------------------------------+
//| NXS_LevelRegistry.mqh                                             |
//| 13/09 - Unified Level/Reaction Engine, Phase A (telemetry-only).  |
//| Vedi vault "NEXUS - Unified Structure Level Reaction Engine       |
//| Migration Plan v1" e "NEXUS - Unified Level Engine Phase A WICK   |
//| Telemetry Shadow".                                                |
//|                                                                    |
//| Questo modulo definisce SOLO lo stato del livello unificato        |
//| (SNXSUnifiedLevel) e le funzioni che lo aggiornano. NON decide     |
//| nulla, NON genera segnali, NON legge input di trading. Le funzioni |
//| qui dentro sono chiamate ESCLUSIVAMENTE da NXS_ReactionEngine.mqh  |
//| (mai direttamente dalle strategie) tranne la creazione del         |
//| livello, chiamata una sola volta dalla fonte (oggi solo WICK, in   |
//| NXS_Strategies_Experimental.mqh) nel punto esatto in cui il        |
//| vecchio codice crea/sostituisce gia' il proprio livello.           |
//|                                                                    |
//| Fase A, perimetro dichiarato: SOLO famiglia WICK. Il vecchio       |
//| SNxsWickSide/SNxsWickReclaimState resta l'UNICA fonte di verita'   |
//| operativa - questo registro e' un osservatore passivo, mai letto   |
//| da nessuna strategia o gate.                                       |
//+------------------------------------------------------------------+
#ifndef __NXS_LEVEL_REGISTRY_MQH__
#define __NXS_LEVEL_REGISTRY_MQH__

// Fase A: unica fonte. Il campo esiste come string (non enum) perche' lo
// schema target (vedi migration plan) prevede piu' fonti in fasi future
// (pivot, order block, FVG, ...) senza dover ritoccare questo file ogni
// volta - Fase A popola sempre e solo "WICK".
#define NXS_LVLSRC_WICK "WICK"

// Lifecycle target completo (dal migration plan). Fase A NON emette MAI
// NXS_LVLST_APPROACHED ne' NXS_LVLST_BROKEN per la famiglia WICK: il
// vecchio SNxsWickSide non calcola una soglia di prossimita' distinta dal
// touch (quindi APPROACHED non e' osservabile con certezza), e non ha un
// concetto di "rottura strutturale" distinto dallo sweep stesso (lo sweep
// e' gia' il suo equivalente terminale "livello sfondato"). I due valori
// restano nell'enum per completezza dello schema e per fonti future, non
// per essere inventati qui.
enum ENUM_NXS_LEVEL_LIFECYCLE_A {
   NXS_LVLST_CREATED = 0,
   NXS_LVLST_FRESH,
   NXS_LVLST_APPROACHED,     // MAI emesso per WICK in Fase A (vedi sopra)
   NXS_LVLST_TOUCHED,
   NXS_LVLST_SWEPT,
   NXS_LVLST_RECLAIMED,
   NXS_LVLST_BROKEN,         // MAI emesso per WICK in Fase A (vedi sopra)
   NXS_LVLST_INVALIDATED,
   NXS_LVLST_CONSUMED
};

// Campi minimi richiesti per la famiglia WICK (vedi task Phase A) + "side"
// come complemento leggibile di "direction" (stessa informazione, stessa
// convenzione gia' usata da SNxsWickShadowEvent.side/SNxsWickReclaimState.side
// nel vecchio codice - non un campo nuovo di significato, solo di comodo).
struct SNXSUnifiedLevel {
   long                       level_id;         // riusa l'id canonico esistente (SNxsWickSide.id) - NON un nuovo id
   string                     source;           // sempre NXS_LVLSRC_WICK in Fase A
   string                     source_strategy;  // "" finche' nessun path canonico ha osservato reazioni; poi "WICK_SWEEP_REV" e/o "WICK_SWEEP_RECLAIM"
   ENUM_TIMEFRAMES            source_tf;        // sempre PERIOD_H4 in Fase A (fonte del livello, non del follow-up)
   ENUM_NXS_DIR               direction;        // direzione del fade atteso: DIR_SELL per side=HIGH, DIR_BUY per side=LOW
   string                     side;             // "HIGH" / "LOW"
   double                     price;
   datetime                   created_time;
   ENUM_NXS_LEVEL_LIFECYCLE_A state;
   datetime                   first_touch_time;
   int                        touch_count;
   double                     max_penetration;  // pip, stessa convenzione GOLD 1 pip = $0.10 del vecchio WICK
   double                     sweep_depth;       // pip, penetrazione al momento del PRIMO sweep osservato (congelata dopo)
   datetime                   reclaim_time;
   bool                       invalidated;
   bool                       consumed;
   // Fase C - Unified Level Engine, WICK read-path (NXS_Strat_WickSweepReversal).
   // Campo minimo aggiunto perche' mancava nello schema Fase A/B: il legacy
   // limita a un tentativo di apertura per livello per barra H4 tramite
   // SNxsWickSide.lastAttemptBar - senza l'equivalente qui il read-path
   // riaprirebbe piu' volte per barra (comportamento diverso dal legacy).
   // Popolato SOLO dall'hook causale nello stesso punto in cui il legacy
   // gia' scrive side.lastAttemptBar (mai ricostruito ex-post).
   datetime                   last_attempt_bar;
};

// Storage dinamico (ArrayResize a raddoppio) - un test Full Validation
// pluriennale puo' creare piu' livelli di quanti ne stimi un cap fisso;
// meglio ridimensionare che perdere silenziosamente eventi.
SNXSUnifiedLevel g_nxsLevelReg[];
int              g_nxsLevelRegCount = 0;

void _NXS_LevelReg_EnsureCapacity(){
   int cap = ArraySize(g_nxsLevelReg);
   if(g_nxsLevelRegCount >= cap){
      int newCap = (cap == 0) ? 256 : cap * 2;
      ArrayResize(g_nxsLevelReg, newCap);
   }
}

// Ricerca lineare per level_id. Costo trascurabile: anche in un Full
// Validation pluriennale i livelli WICK attesi sono nell'ordine delle
// migliaia, non milioni (un H4 al massimo crea 2 livelli/barra).
int _NXS_LevelReg_Find(long level_id){
   for(int i = g_nxsLevelRegCount - 1; i >= 0; i--)
      if(g_nxsLevelReg[i].level_id == level_id) return i;
   return -1;
}

// Chiamata UNA SOLA VOLTA per livello, dal punto esatto in cui
// _NXS_WickSweep_UpdateLevel() crea/sostituisce g_wickHigh/g_wickLow.
// level_id = SNxsWickSide.id (stesso id canonico, non generato qui) -
// garantisce per costruzione che level_id combaci sempre tra vecchio e
// nuovo, senza bisogno di una mappa di corrispondenza separata.
void NXS_LevelReg_Create(long level_id, string side, ENUM_NXS_DIR direction,
                          double price, datetime created_time, ENUM_TIMEFRAMES source_tf){
   _NXS_LevelReg_EnsureCapacity();
   SNXSUnifiedLevel lv;
   lv.level_id = level_id;
   lv.source = NXS_LVLSRC_WICK;
   lv.source_strategy = "";
   lv.source_tf = source_tf;
   lv.direction = direction;
   lv.side = side;
   lv.price = price;
   lv.created_time = created_time;
   lv.state = NXS_LVLST_FRESH;   // CREATED e' istantaneo, il livello nasce gia' FRESH (non ancora toccato)
   lv.first_touch_time = 0;
   lv.touch_count = 0;
   lv.max_penetration = 0;
   lv.sweep_depth = 0;
   lv.reclaim_time = 0;
   lv.invalidated = false;
   lv.consumed = false;
   lv.last_attempt_bar = 0;
   g_nxsLevelReg[g_nxsLevelRegCount] = lv;
   g_nxsLevelRegCount++;
}

// Fase C - mirror di SNxsWickSide.lastAttemptBar. Chiamata SOLO dal punto
// esatto in cui il legacy gia' scrive side.lastAttemptBar = g_wickLastBar
// (subito prima di emettere il segnale), mai altrove.
void NXS_LevelReg_SetLastAttemptBar(long level_id, datetime bar){
   int idx = _NXS_LevelReg_Find(level_id);
   if(idx < 0) return;
   g_nxsLevelReg[idx].last_attempt_bar = bar;
}

void NXS_LevelReg_SetTouched(long level_id, datetime t){
   int idx = _NXS_LevelReg_Find(level_id);
   if(idx < 0) return;
   if(g_nxsLevelReg[idx].touch_count == 0) g_nxsLevelReg[idx].first_touch_time = t;
   g_nxsLevelReg[idx].touch_count++;
   if(g_nxsLevelReg[idx].state == NXS_LVLST_CREATED || g_nxsLevelReg[idx].state == NXS_LVLST_FRESH)
      g_nxsLevelReg[idx].state = NXS_LVLST_TOUCHED;
}

void NXS_LevelReg_SetSwept(long level_id, string source_strategy, double penetration_pips){
   int idx = _NXS_LevelReg_Find(level_id);
   if(idx < 0) return;
   ENUM_NXS_LEVEL_LIFECYCLE_A st = g_nxsLevelReg[idx].state;
   if(st != NXS_LVLST_RECLAIMED && st != NXS_LVLST_INVALIDATED && st != NXS_LVLST_CONSUMED)
      g_nxsLevelReg[idx].state = NXS_LVLST_SWEPT;
   if(g_nxsLevelReg[idx].sweep_depth == 0) g_nxsLevelReg[idx].sweep_depth = penetration_pips;
   if(penetration_pips > g_nxsLevelReg[idx].max_penetration) g_nxsLevelReg[idx].max_penetration = penetration_pips;
   // due path indipendenti (REV/RECLAIM) possono osservare lo stesso livello:
   // source_strategy accumula entrambi separati da "|" invece di sovrascrivere.
   if(StringFind(g_nxsLevelReg[idx].source_strategy, source_strategy) < 0){
      g_nxsLevelReg[idx].source_strategy =
         (g_nxsLevelReg[idx].source_strategy == "") ? source_strategy
                                                     : g_nxsLevelReg[idx].source_strategy + "|" + source_strategy;
   }
}

void NXS_LevelReg_SetReclaimed(long level_id, datetime t){
   int idx = _NXS_LevelReg_Find(level_id);
   if(idx < 0) return;
   if(g_nxsLevelReg[idx].state == NXS_LVLST_CONSUMED) return;   // terminale, non retrocedere
   g_nxsLevelReg[idx].reclaim_time = t;
   g_nxsLevelReg[idx].state = NXS_LVLST_RECLAIMED;
}

// byReplacement=true quando il motivo e' "una nuova wick ha sostituito
// questo livello" (mirror di g_wickFunnel.levelsReplacedUnused /
// g_wickReclaimFunnel.abandoned); false quando il motivo e' "il prezzo e'
// rientrato prima del consumo" (mirror di g_wickFunnel.levelsInvalidatedByPrice).
// La distinzione vive nel reaction event (reason), non su questo struct,
// per restare fedeli ai campi minimi richiesti.
void NXS_LevelReg_SetInvalidated(long level_id, bool byReplacement){
   int idx = _NXS_LevelReg_Find(level_id);
   if(idx < 0) return;
   if(g_nxsLevelReg[idx].state == NXS_LVLST_CONSUMED) return;   // terminale, non retrocedere (mirror della guardia gia' presente nel vecchio WR_OPENED)
   g_nxsLevelReg[idx].invalidated = true;
   g_nxsLevelReg[idx].state = NXS_LVLST_INVALIDATED;
}

void NXS_LevelReg_SetConsumed(long level_id, string source_strategy){
   int idx = _NXS_LevelReg_Find(level_id);
   if(idx < 0) return;
   g_nxsLevelReg[idx].consumed = true;
   g_nxsLevelReg[idx].state = NXS_LVLST_CONSUMED;   // terminale, vince su qualunque stato precedente
   if(StringFind(g_nxsLevelReg[idx].source_strategy, source_strategy) < 0){
      g_nxsLevelReg[idx].source_strategy =
         (g_nxsLevelReg[idx].source_strategy == "") ? source_strategy
                                                     : g_nxsLevelReg[idx].source_strategy + "|" + source_strategy;
   }
}

#endif
