#nexus #trading #multi-agent #audit #todo

# Audit Livello A — coerenza logica strategie (agente logico) — verifica e prossimi passi

**Fonte:** `NEXUS_EA_Audit_Livello_A_Coerenza_Logica.md`, prodotto dall'agente logico (analisi statica, nessun accesso a GitHub, nessuna modifica al codice). Relayed dall'utente il 17/07 sera.

**Scope dichiarato:** solo coerenza logica statica (il nome della strategia corrisponde al codice? le condizioni possono diventare vere? ci sono incoerenze temporali/dimensionali?). Esclude le 7 strategie già auditate in sessione precedente (SAR, BJORGUM, MACD, RSI_DIV, BREAKOUT_ACC, LIQ_SWEEP, ADX_RSI).

## Verifica indipendente (fatta da me, sul codice reale attuale)

Ho riletto il sorgente MQL5 corrente per 6 delle affermazioni chiave dell'audit, senza fidarmi a scatola chiusa. **Tutte confermate, nessuna imprecisione trovata.**

### 1. WEEKLY_EXP — CONFERMATO, bug reale (non solo sospetto)
`NXS_Strategies_Institutional.mqh:258-303` (`NXS_Strat_WeeklyRangeExp`). `_inst_atr()` (riga 18) restituisce `g_atr`, che nel passaggio multi-TF di questa strategia è l'ATR del **TF di profilo = D1**. Il gate displacement (riga 276): `bH4 < atrM*0.8 → return` con `cH4/oH4` letti su `InpTFHigh` (H4, righe 273-275). Quindi: **corpo H4 confrontato con l'80% dell'ATR D1**, non dell'ATR H4. Un ATR(14) D1 sull'oro è tipicamente 3-5x più grande di un ATR(14) H4 — la soglia richiede di fatto un evento quasi estremo per scattare.

Questo NON è un problema di taratura soglia, è un errore di coerenza dimensionale (TF sbagliato per l'ATR). Candidato per fix diretto (usare ATR H4, non D1), non serve necessariamente la diagnostica prima — a differenza degli altri 3 casi sotto.

### 2. LIQ_VOID — CONFERMATO, mismatch concettuale
`NXS_Strategies_Institutional.mqh:343-370` (`NXS_Strat_LiquidityVoid`). Lato bullish:
```
voidHi = iHigh(g_sym, tf, dispIdx)      // high della candela displacement
voidLo = iHigh(g_sym, tf, dispIdx + 2)  // high di due barre dopo (verso il presente)
```
Entrambi sono **high**, non il gap low/high di un vero FVG a 3 candele (che richiederebbe `low[dispIdx] > high[dispIdx+2]` o simile). `l_disp` (low della displacement) viene letto ma mai usato nel confronto. La zona costruita non è la void/FVG dichiarata nel commento — può classificare come "void" un normale impulso che fa un nuovo massimo.

### 3. OB_MIT — CONFERMATO al 100%, wrapper letterale
`NXS_Strategies_SMC.mqh:129-140`. La funzione chiama direttamente `NXS_Strat_OrderBlock()`, copia il segnale (`s = raw`), cambia solo `stratName` e `reason`. Non è una logica di mitigation indipendente — è ORDER_BLOCK travestito. Riduce la diversificazione reale tra le 37 strategie (2 "strategie" diverse possono produrre segnali identici sullo stesso setup).

### 4. RANGE_FADE — CONFERMATO, mix barra-chiusa/prezzo-live
`NXS_Strategies_Institutional.mqh:442-486`. Rejection valutata su `c1/o1/h1/l1` (barra chiusa, shift 1), ma prossimità al bordo del range valutata su `bid` (prezzo live, shift 0/tick corrente). Stesso pattern di inconsistenza temporale già osservato in altre parti del codebase questa settimana (vedi nota HTF filter shift0-vs-shift1 nel piano Pine Script per l'agente desktop).

## Giudizio complessivo

Lavoro accurato, non superficiale — letture riga per riga del codice reale, zero affermazioni inventate nei punti verificati. Le priorità "Critica" (WEEKLY_EXP, LIQ_VOID, IFVG, NY_REVERSAL, ELLIOTT) sono coerenti con quanto trovato.

Metodologia proposta dall'agente logico — **diagnostica per gate prima di toccare soglie** — pienamente condivisa: stesso principio già stabilito con l'utente sul gate DD ("non è una vera soluzione, è un camuffamento" se si aggiusta il sintomo senza capire la causa).

**Distinzione che aggiungo:** non tutti i 4 casi del Gruppo 1 sono uguali:
- **WEEKLY_EXP**: errore di coerenza dimensionale chiaro (ATR del TF sbagliato) → fixabile direttamente, non richiede diagnostica preliminare.
- **LIQ_VOID, IFVG, RANGE_FADE**: richiedono davvero i contatori per gate prima di decidere cosa cambiare — il documento propone uno schema YAML (`bars_evaluated / gate_N_pass / raw_setup_count / router_survivor_count / executed_trade_count`) sensato e riusabile.

## Prossimi passi (non ancora eseguiti)

1. Decidere se scrivere l'istrumentazione diagnostica leggera (solo log/contatori, nessuna modifica alla logica di trading) per le strategie del Gruppo 1+2 dell'audit (WEEKLY_EXP, LIQ_VOID, IFVG, RANGE_FADE, NY_REVERSAL, FVG_MIT, SH_BMS_RTO, OTE_CONT) — da coordinare con NEXUS Bot per non interferire con lo sweep 1-37 in corso.
2. Valutare il fix diretto di WEEKLY_EXP (ATR H4 invece di D1) separatamente, come correzione di coerenza — non come tuning.
3. Cross-check della matrice completa (sezione 4 del documento, tutte le strategie non ancora auditate a Livello A) prima di considerare "chiuso" l'audit statico.
4. Solo dopo diagnostica/fix Livello A+B per queste strategie, procedere a un nuovo Livello C (statistica) — le zero-trade non vanno ancora interpretate come "pattern inesistente su XAUUSD".

## Collegamenti
[[MOC - Trading]]
