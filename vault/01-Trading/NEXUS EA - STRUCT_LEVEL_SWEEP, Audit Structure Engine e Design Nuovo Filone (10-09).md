# STRUCT_LEVEL_SWEEP - audit del percorso reale e design (nessun codice toccato)

Richiesto dall'utente il 10/09 come **nuovo filone separato su Terminal3**, senza interferire con i 4 RAW ufficiali (ADX_RSI ESL off/on gia' fatti, EMA_PULLBACK/FVG_CONT in corso su Terminal1/2). Solo audit + design in questa nota: **nessun codice modificato, nessun test lanciato**.

## 1. Audit Structure Engine (`NXS_Structure.mqh`, 298 righe)

| Funzione | File:riga | TF | Lookback | HIGH strutturale | LOW strutturale | Wick o body | Swing/pivot | BOS | CHOCH | Nascita livello | Persistenza | Consumo | Invalidation | Storico o solo stato | Multi-touch | 1°/2° touch | Sweep depth |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `NXS_ComputeStructureCore` | Structure.mqh:200 | TF passato (entry-TF per `g_struct`, sempre H1 per `g_structH1`) | scan=60 barre, wing=`InpSwingWing`=3 | `iHigh` frattale (`NXS_IsSwingHigh`) | `iLow` frattale (`NXS_IsSwingLow`) | **Wick puro** (`iHigh`/`iLow` grezzi) | Frattale simmetrico: wing barre a sx E dx piu' basse/alte, nessuna tolleranza ATR | Break di `lastSwingHigh/Low` che **conferma** il trend precedente (mutex con CHOCH da v2.0.34) | Stesso break ma **contraddice** il trend precedente | Al primo frattale confermato scandendo indietro (solo per `g_struct`, `addLevels=true`; MAI per `g_structH1`) | Nessuna scadenza esplicita sullo swing stesso | N/A (lo swing come dato non "si consuma", solo `g_levels[]` lo fa via mitigazione) | Nessuna invalidation dedicata per lo swing in se' | **`g_struct`/`g_structH1`: SOLO stato corrente** (trend/bosUp/chochUp sovrascritti ogni call) | — | — | — |
| `NXS_AddLevel` | Structure.mqh:48 | — | — | — | — | — | — | — | — | Ogni volta che uno swing/OB/FVG viene rilevato (dedup su prezzo+tempo, tolleranza 5 point) | Fino a 40 livelli nel pool, poi compattazione (drop il piu' vecchio inattivo, o index 0) | — | — | **`g_levels[]`: STORICO fino a 40**, misto swing+OB+FVG | Si, vedi `NXS_MitigateLevels` | Si (vedi sotto) | **No** - nessun campo di profondita' di sfondamento nel livello |
| `NXS_MitigateLevels` | Structure.mqh:160 | — (usa BID corrente) | — | — | — | Zone (OB/FVG): tocco se prezzo in `[priceBot,priceTop]`; swing: tocco se `\|price-priceRef\|<=5 point` | — | — | — | — | — | **Si**: livello disattivato (`active=false`) al **secondo** tocco, non al primo | Al 2° tocco (`mitigations>=2`) | — | **Si esplicitamente**: 1° tocco -> `mitigated=true, mitigations=1` (resta attivo); 2° tocco -> `mitigations=2` -> `active=false` | **Nessuna misura di profondita'** - `NXS_MitigateLevels` sa SOLO se il prezzo e' dentro la zona/tolleranza, non di quanto l'ha superata |
| `NXS_DetectOrderBlocks` | Structure.mqh:100 | TF passato | 30 barre (esclude le 3 piu' recenti) | — | — | **Body** (`MathMax/Min(open,close)` della candela pre-displacement) | Candela opposta al colore + displacement successivo >= `g_atr*InpOBDisplacement`(1.5) | n/a | n/a | Alla scansione, se il displacement supera soglia | Pool condiviso (40, compattazione) | Come sopra | Mitigazione generica | Storico (pool condiviso) | Si (mitigazione generica) | Si (mitigazione generica) | No |
| `NXS_DetectFVG` | Structure.mqh:122 | TF passato | 30 barre | — | — | Filtro minimo su **body** (`>=g_atr*InpFVGMinBody`=0.5) della candela di mezzo; il gap stesso e' wick-to-wick | Gap 3-candele classico | n/a | n/a | Alla scansione | Pool condiviso | Come sopra | Mitigazione generica | Storico (pool condiviso) | Si | Si | No |

**Sintesi per la domanda esplicita "storico o solo stato corrente"**: **ENTRAMBI**, a seconda del dato. `g_struct`/`g_structH1` (trend, BOS, CHOCH, ultimo swing) = solo stato corrente, sovrascritto ogni chiamata. `g_levels[]` (i livelli stessi: swing/OB/FVG) = storico reale, fino a 40 elementi.

**Sintesi sweep depth**: lo Structure Engine **non misura mai** quanto il prezzo ha sfondato un livello oltre il livello stesso - sa solo SE il prezzo e' "dentro tolleranza" (tocco) oppure no. Questa e' esattamente la lacuna che LEVEL_REACTION (#52) ha colmato per i SUOI livelli (pivot + SNR), calcolando `breachPips = (l1 - lvl) / NXS_LEVELREACT_PIP_USD`, ma quel calcolo vive SOLO dentro `_nxs_levelreact_core`, non nello Structure Engine condiviso - un futuro STRUCT_LEVEL_SWEEP che vuole la profondita' di sfondamento deve replicarla, non puo' riusare `g_levels[]`/`NXS_MitigateLevels` cosi' come sono.

## A. Diagramma del percorso reale

```
                         ┌─────────────────────────────┐
                         │   NXS_UpdateStructure(tf)    │  (chiamata 1x/barra, e 1x per
                         │   Structure.mqh:253          │   passaggio multi-TF - vedi nota*)
                         └──────────────┬───────────────┘
                                        │
                 ┌──────────────────────┼───────────────────────┐
                 ▼                      ▼                       ▼
     NXS_ComputeStructureCore   NXS_DetectOrderBlocks    NXS_DetectFVG
     (swing H/L, trend,         (body+displacement)      (gap 3-candele)
      BOS/CHOCH) -> g_struct           │                       │
                 │                      └──────────┬────────────┘
                 │                                 ▼
                 │                        NXS_AddLevel() -> g_levels[] (pool storico, max 40)
                 │                                 │
                 │                                 ▼
                 │                        NXS_MitigateLevels() (touch/2°touch->inactive)
                 │                                 │
                 └───────────────┬─────────────────┘
                                 ▼
                  NXS_DetectReaction(sym, tf)  Reaction.mqh:40
                  legge g_levels[] (zone attive) + g_struct (trend/swing)
                  richiede NXS_HasPriceReaction() (pin/chiusura direzionale)
                  su OGNI zona/swing/EMA200 in tolleranza -> tiene il MIGLIOR
                  candidato (bestQuality) -> g_reaction {detected,direction,
                  levelPrice,levelType,quality}
                                 │
                 ┌───────────────┼────────────────────────────┐
                 ▼                                             ▼
   NXS_Strat_StructureReaction()                    NXS_ReactionScoreMod() / NXS_SMCReactionOK()
   (STRUCT_REACT, #16)                              (score generale / gate OB-FVG - vedi §2)
   GATE ASSOLUTO: if(!g_reaction.detected) return;
   dir = g_reaction.direction
   score = 55 + quality*0.35 (+6 trend, +5 BOS/CHOCH)
                                 │
                                 ▼
                    NXS_DefaultSLTP() -> SNXSSignal
                                 │
                                 ▼
              NXS_CollectAllSignals -> out[] -> loop "PROFILI PER-STRATEGIA"
              (NXS_StrategyHasOpenPos, 1 decisione/barra TF) -> NXS_OpenTrade()

  * NOTA multi-TF: NXS_UpdateStructure/NXS_DetectReaction vengono richiamate
    UNA VOLTA PER OGNI passaggio TF quando InpProfileMultiTF=true (stesso
    meccanismo che ha causato il bug di WICK_SWEEP_REV) - g_struct/g_reaction
    sono overwrite globali, non per-TF: qualunque strategia che li legge deve
    essere assegnata al TF giusto via NXS_Profile_TF() o legge lo stato del
    TF sbagliato.
```

## 2. Audit STRUCT_REACT (`NXS_Strat_StructureReaction`, Strategies.mqh:2087)

Pipeline **level -> reaction detection -> signal -> entry**:

1. **Level**: nessuna logica propria - legge `g_levels[]` (zone OB/FVG attive) e `g_struct` (ultimo swing high/low + trend), gia' popolati dallo Structure Engine.
2. **Reaction detection** (`NXS_DetectReaction`, Reaction.mqh:40): per ogni zona attiva in tolleranza `InpReactionTol`(0.3)*ATR dal BID, richiede `NXS_HasPriceReaction()` sulla candela appena chiusa (pin bar: wick opposto >1.5x body E >50% range; OPPURE chiusura direzionale coerente) - **e' un gate booleano**, senza reazione di prezzo la zona e' scartata, non solo penalizzata. Se passa: quality=60 +20 se direzione=trend +15 se mai mitigata. Stessa logica per swing (quality 55) e EMA200 opzionale (quality 58). Tiene il MIGLIORE tra tutti i candidati.
3. `g_reaction.detected=true` **solo se almeno un candidato ha superato NXS_HasPriceReaction**. `direction`=direzione del candidato migliore, `quality`=punteggio, `levelType`=stringa (es. "OB_BULL","SWING_HIGH","EMA200"), `levelPrice`=`priceRef` del livello.
4. **Signal** (`NXS_Strat_StructureReaction`): `if(!g_reaction.detected) return s;` - **gate assoluto e unico**, nessun'altra condizione propria. `s.dir = g_reaction.direction`. `s.score = 55 + quality*0.35` (+6 se `g_reaction.direction==g_struct.trend`, +5 se BOS/CHOCH coerente).
5. **Entry**: `NXS_DefaultSLTP(s)` - profilo dedicato `slMult=2.0, tpMult=6.0`×ATR(H4) (RR 1:3), TF forzato H4, **direction-lock BUY-only** in produzione (ricetta simmetrica H1 era PF0.61, H4 BUY-only sale a PF2.32-2.43 - vedi `NXS_Profile_DirectionLock`).

**Trend/BOS/CHOCH: gate o modificatore?** Risposta univoca per STRUCT_REACT: **SOLO modificatori dello score** (+6 e +5 punti), MAI un gate. L'unico gate reale e' `g_reaction.detected`. (Per contro, in altre strategie come OB/OB_MIT, `NXS_SMCReactionOK` fa della reazione un gate booleano a doppia condizione - la risposta dipende da CHI consuma `g_reaction`, non e' universale, come gia' chiarito nell'audit precedente del 10/09.)

## B. Tabella Level Type (Structure Engine attuale)

| Level Type | Source TF | Wick/Body | Creation Rule | Persistence | Reaction Rule | Invalidation | Multi-touch |
|---|---|---|---|---|---|---|---|
| SWING_HIGH/LOW | TF di `NXS_UpdateStructure` chiamante (entry-TF per `g_struct`, H1 fisso per `g_structH1`) | Wick (`iHigh`/`iLow`) | Frattale simmetrico, wing=3 barre a sx e dx | In `g_levels[]` fino a 2 mitigazioni o compattazione pool (max 40) | Pin bar o chiusura direzionale entro tolleranza ATR | 2° tocco -> `active=false`; nessuna invalidation per "rottura" | Si, tracciato (`mitigations` 0/1/2+) |
| OB_BULL/BEAR | TF chiamante | **Body** (open/close pre-displacement) | Candela opposta + displacement successivo >=1.5xATR | Come sopra | Come sopra (+ gate `NXS_SMCReactionOK` per OB/OB_MIT) | Come sopra | Si |
| FVG_BULL/BEAR | TF chiamante | Gap wick-to-wick, filtro minimo su body candela centrale (>=0.5xATR) | Gap 3-candele classico | Come sopra | Come sopra | Come sopra | Si |

Nessuna riga misura la **profondita' di sfondamento** (sweep depth) - confermato assente in tutto `NXS_Structure.mqh`/`NXS_Reaction.mqh`.

## 3. Confronto con l'ipotesi STRUCT_LEVEL_SWEEP (design, dati NON ancora raccolti)

### Level creation proposta
Su H4, a chiusura barra: `upperWick = high - max(open,close)`, `lowerWick = min(open,close) - low`. Se wick >= soglia minima (misurabile/significativa, es. in ATR o pip fissi - da tarare sui dati, non assunta), registra il livello e **lo mantiene nel tempo** (a differenza del prototipo WICK_SWEEP_REV attuale che sostituisce il livello a ogni nuova wick anche se non consumato - qui invece serve un **pool storico multi-livello**, piu' vicino a `g_levels[]` che al design attuale di `NXS_Strategies_Experimental.mqh`).

### Revisit - binning penetrazione (1 pip = $0.10 su GOLD, convenzione Nexus/vault)
Bin: **0-10 / 10-20 / 20-30 / 30-40 / 40-50 / 50-75 / 75-100 / 100+** pip oltre il wick extreme. Nessuna soglia assunta ottimale a priori (coerente con quanto gia' notato per i 35 pip di WICK_SWEEP_REV nell'audit precedente).

### Reaction study - metriche da calcolare per ogni penetrazione (design, non calcolate)
Per ciascun evento di penetrazione, dataset con: MAE, MFE, massimo overshoot oltre il livello, se/quando il prezzo ritorna al livello, se/quando ritorna al body high/low della candela d'origine, tempo (in barre/minuti) per raggiungere +20/+30/+50/+75/+100/+150/+200 pip favorevoli dal punto di ingresso ipotetico, ed eventuale continuazione senza reversal (nessun ritorno al livello entro un orizzonte definito).

**Nessuno di questi numeri e' stato calcolato in questa sessione** - servirebbe uno script dedicato (Python offline su storico M1/M5 GOLD, sul modello del "Gold Reversal Map" gia' citato per LEVEL_REACTION, oppure un logger MQL5 in Data Collection Mode) che qui non e' stato ancora scritto, per esplicita richiesta di NON implementare ancora.

## 4. Level validity - classificazione proposta (confini da dedurre dai dati, non assunti)

| Categoria | Definizione proposta (provvisoria) | Nota |
|---|---|---|
| Touch | Prezzo tocca il livello senza superarlo (0 pip di sfondamento) | Nessuna azione |
| Shallow sweep | Sfondamento nel bin basso (es. 0-20 pip, **da confermare col dataset**) | Ipotesi: alta probabilita' di reversal (per analogia con LEVEL_REACTION: <50 pip -> 99.5% storico sui pivot M15, MA quel dato e' su un ALTRO tipo di livello e non e' stato riverificato qui) |
| Optimal sweep | Bin intermedio dove la probabilita'/magnitudo di reversal e' massima | Sconosciuto finche' non misurato - e' esattamente l'obiettivo del punto 3 |
| Deep sweep | Sfondamento profondo ma ancora recuperabile | Confine con la rottura strutturale da stabilire empiricamente |
| Structural break | Sfondamento oltre il quale il reversal diventa raro/il livello e' strutturalmente rotto | Analogia LEVEL_REACTION: >100 pip -> 69.1% (studio pivot M15, non su livelli a wick H4) |

Come richiesto: **e' il dataset (non ancora costruito) a dover fissare questi confini**, non un'assunzione a priori.

## 5. STRUCT_LEVEL_SWEEP - design (NON implementato)

```
H4 wick level (creato a chiusura barra, mantenuto in un pool storico multi-livello)
   -> ritorno futuro del prezzo al livello (revisit, in qualunque barra successiva)
   -> penetration threshold (soglia da tarare sui bin del punto 3, non assunta)
   -> ingresso immediato contro lo sweep (stesso principio del prototipo attuale)
   -> SL stretto oltre la penetration area (non oltre l'intero range storico come oggi: 25 pip fissi)
   -> TP iniziale (primo target, non necessariamente il TP fisso attuale da 100 pip)
   -> BE (a differenza del prototipo attuale, che e' puro RAW senza BE)
   -> runner (posizione parziale lasciata correre oltre il primo TP)
```

**Re-entry esplicitamente NON grid/martingale**: se Level A fallisce (SL colpito), Level A viene invalidato (non ritentato sullo stesso livello) e si attende il prossimo Level B, generato indipendentemente - **nessun aumento di size, nessuna media del prezzo**, ogni operazione e' indipendente. Questo e' concettualmente diverso dal SLReclaim esistente nel codice (che riapre sullo STESSO livello/direzione dopo uno stop) - qui la re-entry e' su un livello NUOVO, non una riapertura del precedente.

## C. Confronto STRUCT_REACT (attuale) vs STRUCT_LEVEL_SWEEP (proposto)

| | STRUCT_REACT (attuale, #16) | STRUCT_LEVEL_SWEEP (proposto) |
|---|---|---|
| Livello sorgente | Zone SMC (OB/FVG) + swing + EMA200, da `g_levels[]`/`g_struct` condivisi | Wick H4 dedicato, pool storico proprio (non condiviso con lo Structure Engine esistente) |
| Persistenza livello | Fino a 2 mitigazioni, storico fino a 40 nel pool condiviso | Mantenuto nel tempo fino a invalidazione esplicita (non sostituito automaticamente da una nuova wick) |
| Sweep richiesto | No - basta un touch/pin/chiusura direzionale in zona | **Si, obbligatorio** - la profondita' di sfondamento e' parte del setup, non uno scarto |
| Profondita' di sfondamento | Non misurata | **Misurata e classificata** (touch/shallow/optimal/deep/structural break) |
| Timing di entrata | Immediato alla rilevazione (stessa barra) | Immediato al raggiungimento della soglia (stesso principio) |
| SL | Fisso 2.0xATR(H4) (largo) | Stretto, oltre la penetration area misurata (da tarare) |
| TP | Fisso 6.0xATR(H4) | Target iniziale + runner (non tutto il size su un solo TP fisso) |
| Gestione post-ingresso | Nessuna (RAW puro nei test attuali) | BE + runner |
| Re-entry dopo stop | N/A in RAW; SLReclaim (se attivo) riapre sullo STESSO livello | Livello A invalidato, si attende un livello B NUOVO e indipendente - mai grid/martingale |
| Direction lock | Si, BUY-only in produzione (ricetta live) | Da verificare - nessuna assunzione ancora |

## D. Dati per un primo Fast Structural test (spec, nessun test lanciato)

Un primo test (non 3 anni pieni) dovrebbe estrarre, PRIMA di validare qualunque edge:
- conteggio livelli creati/rivisitati per bin di penetrazione (gli 8 bin del punto 3);
- per ogni bin: n. eventi, MAE/MFE medi, tasso di ritorno al livello, tasso di ritorno al body della candela d'origine, tempo medio ai traguardi +20/.../+200 pip, tasso di continuazione senza reversal;
- separazione BUY/SELL (simmetria, come da regola del protocollo di test);
- **nessun trade reale necessario per questa fase** - e' un'analisi di comportamento del prezzo attorno al livello, non ancora una strategia eseguita. Va deciso se costruirla come script Python offline (piu' veloce da iterare, come gia' fatto per LEVEL_REACTION) o come logger MQL5 in Data Collection Mode (piu' fedele all'esecuzione reale ma piu' lento da modificare).

Non lanciato nessun test. In attesa di conferma su quale via (Python offline vs logger MQL5) prima di scrivere qualunque script.

## Verifica leva 1:500

Controllati tutti i file .ini usati in sessione:
- `nxs_fastsmoke_wicksweep.ini` (Terminal3, WICK_SWEEP_REV): **Leverage=500** - corretto.
- `nxs_research_adxrsi_esl.ini`, `nxs_research_adxrsi_noesl.ini`, `nxs_research_emapullback.ini`, `nxs_research_fvgcont.ini` (i 4 RAW ufficiali, Terminal1/2): **Leverage=100** - NON 1:500.

**Non ho toccato i 2 processi in corso** (EMA_PULLBACK su Terminal2, FVG_CONT su Terminal1) - modificare il loro .ini ora non avrebbe comunque effetto retroattivo (il Tester carica le impostazioni una sola volta all'avvio). A leva 100:1 vs 500:1, con lotti fissi 0.01-0.02 su un conto $1000, il margine richiesto resta comunque trascurabile in entrambi i casi (GOLD 0.01 lotto ~ pochi $ di margine anche a 100:1) - **e' molto improbabile che questo abbia alterato PF/trade/exit dei 4 RAW gia' fatti o in corso**, ma resta una configurazione incoerente rispetto a quanto richiesto ora. Ho aggiornato SOLO i template .ini in `tmp/strategy_validation` (non i processi live) a Leverage=500 per qualunque futuro rilancio - dimmi se vuoi che li lasci cosi' o se preferisci un valore diverso per i test ufficiali futuri.
