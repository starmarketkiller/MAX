# NEXUS — Global New-Bar Gate / Signal Sampling Audit

Scoperto validando RECLAIM_TRIGGER per WICK_SWEEP_REV (vedi [[NEXUS EA - WICK_SWEEP Entry Timing Study - HYPOTHESIS STRONGLY SUPPORTED NOT YET EXECUTION-VALIDATED (11-09)]]): il confronto tick-level shadow vs canonico dava parity FAIL (258 vs 182 sweep). Correlando i timestamp esatti, **tutte e 179 le aperture reali di WICK_SWEEP_REV nel test cadono su un boundary `InpTFEntry` esatto** (:00/:15/:30/:45, mai a meta' barra). Causa isolata nel codice.

**NON toccato: ne' il gate, ne' il commento di WICK_SWEEP_REV che lo contraddice.** Solo audit.

## Il meccanismo

`NEXUS_EA_v2.mq5`, dentro `OnTick()`, prima di `NXS_CollectAllSignals()`:

```mql5
// New bar gate
datetime bt = iTime(g_sym, InpTFEntry, 0);
if(bt == g_lastBarTime) return;
g_lastBarTime = bt;
```

Questo gate e' A MONTE di `NXS_CollectAllSignals()` — che a sua volta chiama TUTTE le funzioni strategia (incluso `NXS_Strat_WickSweepReversal()`). Conseguenza: **nessuna strategia del router viene valutata a ogni tick**, indipendentemente da cosa dice il suo commento o dalla sua logica interna — tutte, senza eccezione, vengono chiamate **una sola volta per barra `InpTFEntry`** (default e non modificato in nessun test di questa sessione: `PERIOD_M15`).

Questo e' vero anche per strategie che leggono `SymbolInfoDouble(g_sym, SYMBOL_BID)`/`ASK` dentro il proprio corpo (come fa WICK_SWEEP_REV) - leggono il prezzo LIVE, ma solo nell'istante in cui capitano a essere chiamate, cioe' una volta ogni 15 minuti, non continuamente.

## Il commento fuorviante di WICK_SWEEP_REV

`NXS_Strategies_Experimental.mqh`, riga 16: *"si entra SUBITO ('di pancia', al tick, non alla chiusura barra) nella direzione opposta allo sweep"* — **non corrisponde al comportamento reale**. La funzione legge bid/ask live, ma viene invocata solo al boundary M15. Un vero sweep che scatta e si esaurisce (reclaim) interamente dentro una singola barra M15 e' semplicemente invisibile al sistema: quando la funzione viene finalmente chiamata (al boundary successivo), vede solo lo stato del prezzo IN QUEL MOMENTO, non la sequenza di eventi intrabarra che l'ha preceduto.

## Impatto quantificato (dal test Fast Smoke, stessa finestra usata per lo studio RECLAIM_TRIGGER)

- Sweep genuini a livello di tick (rilevabili solo togliendo il gate, non fatto): sconosciuto esatto, ma lo shadow non allineato (run pre-fix) ne aveva contati fino a 1100 nella sola finestra a 3 mesi prima del fix del gate one-shot, e 258 anche dopo quel fix — contro 182 realmente "visti" dal canonico.
- Con la coorte di rilevazione ora allineata al boundary M15 (fix del 12/09, commit 9a31620), lo shadow dovrebbe finalmente combaciare esattamente con `sweepsDetected` — risultato in verifica nel run in corso.

## Classificazione strategie (SOLO ANALISI, nessuna modifica)

Verificate leggendo il codice sorgente della funzione di segnale. "BAR-CLOSE INTENDED" = la logica stessa usa solo dati di barre GIA' chiuse (shift>=1), quindi il gate M15 non le priva di nulla che intendessero avere. "EVENT/TICK-SENSITIVE" = la logica legge esplicitamente il prezzo LIVE (bid/ask) per decidere un "tocco"/trigger nell'istante presente, quindi PUO' perdere eventi intrabarra a causa del gate.

| Strategia | File:funzione | Classificazione | Nota |
|---|---|---|---|
| **WICK_SWEEP_REV** | NXS_Strategies_Experimental.mqh:`NXS_Strat_WickSweepReversal` | **EVENT/TICK-SENSITIVE** | Caso che ha innescato l'audit. Commento esplicito "al tick" contraddetto dal comportamento reale. |
| TURTLE_SOUP | NXS_Strategies_SMC.mqh:`NXS_Strat_TurtleSoup` | BAR-CLOSE INTENDED | "Sweep previous H/L + close back inside + reversal candle" - tutto su barre chiuse (shift 1+), nessun controllo su bid/ask live. |
| LIQ_SWEEP | NXS_Strategies.mqh:`NXS_Strat_LiqSweep` | BAR-CLOSE INTENDED | Usa `NXS_DetectSweepExt()` su candela H1 chiusa (`h1`,`c1`), stesso pattern delle altre strategie ICT del file (JUDAS_SWING, LDN_REVERSAL, SH_BMS_RTO, PO3, AMD_REVERSAL, SILVER_BULLET - campionate, stesso stile confermato su 2 di esse). |
| SWING_FALSEBREAK | NXS_Strategies_SMC.mqh:`NXS_Strat_SwingFalseBreak` | BAR-CLOSE INTENDED | Sweep su shift 1-3 + `c1`/`o1` di chiusura - nessun bid/ask live. |
| FVG_MIT (plain) | NXS_Strategies_SMC.mqh:`NXS_Strat_FVG_Mitigation` | **EVENT/TICK-SENSITIVE** | Usa `bid >= fvgLo && bid <= fvgHi` LIVE per il tocco zona. Il commento della v2 (FVG_MIT_WINDOW, riga 235) lo ammette esplicitamente: *"valuta ogni gap SOLO all'istante fisso... vs il prezzo di ORA: se il ritorno... non avviene esattamente in quel momento, il segnale e' perso per sempre"* - il gate M15 rende "quel momento" controllabile solo ogni 15 minuti, aggravando un limite gia' noto. |
| FVG_MIT_WINDOW | NXS_Strategies_SMC.mqh:`NXS_Strat_FVG_Mitigation_Window` | EVENT/TICK-SENSITIVE (attenuato) | Stesso controllo bid live per il tocco, MA mantiene un registro di zone attive fino a 15 barre - un tocco perso in una barra puo' ancora essere colto in una barra successiva finche' la zona non scade, quindi la perdita e' meno totale che nella versione plain. |
| ORDER_BLOCK retest | NXS_Strategies.mqh (riga ~2050) | **EVENT/TICK-SENSITIVE** | `bid >= st.obLo && bid <= st.obHi` LIVE per "touched", one-shot (`st.active=false` dopo il primo retest) - un tocco intrabarra mai visto al boundary M15 potrebbe far scadere la zona (`InpOB_MaxWaitBars`) senza che il retest venga mai registrato. |
| LEVEL_REACTION (M15) | NXS_Strategies.mqh:`_nxs_levelreact_core` | BAR-CLOSE INTENDED | Ha gia' un proprio gate `if(st.lastBarTime==curBar0) return` per barra M15 - combacia esattamente con `InpTFEntry`=M15, nessuna perdita aggiuntiva dal gate globale. |
| **LEVEL_REACTION_M5** | NXS_Strategies.mqh:`_nxs_levelreact_core` (istanza M5) | **UNKNOWN / NEEDS REVIEW** | Dichiara esecuzione su M5 (`execTF=PERIOD_M5`, selettore 53) ma il gate globale e' su `InpTFEntry`=M15 - la sua PROPRIA cadenza dichiarata (ogni barra M5) e' silenziosamente degradata a M15 dal gate a monte. Il suo contatore interno `pendingBars` (barre di conferma, 2 base +2 se sfondamento profondo) rischia di avanzare in base a QUANTI check M15 passano, non a quante vere barre M5 si sono chiuse - possibile sottoconferma o sovraconferma mai verificata. Da rivedere prima di fidarsi dei suoi risultati M5-specifici. |
| Session sweep/reversal (JUDAS_SWING, LDN_REVERSAL, NY_REVERSAL, SILVER_BULLET, PO3, AMD_REVERSAL, SH_BMS_RTO, SMS_BMS_RTO) | NXS_Strategies_Institutional.mqh / NXS_Strategies_SMC.mqh | BAR-CLOSE INTENDED (campione parziale) | JUDAS_SWING e LDN_REVERSAL verificati direttamente (candela H1 chiusa `h1`/`c1` + CHOCH strutturale, nessun bid/ask live per il trigger). Le altre 6 non lette riga-per-riga in questo giro - stesso stile di famiglia atteso ma non confermato individualmente. |

### Sintesi

Il rischio reale del gate globale non e' uniforme: colpisce SOLO le strategie che dipendono da un tocco/livello LIVE (bid/ask nell'istante presente) per decidere l'ingresso - **WICK_SWEEP_REV, FVG_MIT (plain e, in misura minore, WINDOW), ORDER_BLOCK retest, e potenzialmente LEVEL_REACTION_M5 per un motivo diverso (mismatch di cadenza dichiarata)**. Le strategie "ICT" a barra chiusa (TURTLE_SOUP, LIQ_SWEEP, SWING_FALSEBREAK, famiglia JUDAS/LDN/NY/SILVER_BULLET/PO3/AMD/SH-SMS_BMS_RTO) sono per design gia' allineate alla cadenza del gate e non perdono nulla.

## Non fatto in questo giro (in attesa di indicazioni)

- Non corretto il gate ne' il commento di WICK_SWEEP_REV.
- Non verificate individualmente le 6 strategie "session" rimanenti.
- Non quantificato l'impatto pratico su FVG_MIT/ORDER_BLOCK/LEVEL_REACTION_M5 (nessun test dedicato lanciato per loro).
