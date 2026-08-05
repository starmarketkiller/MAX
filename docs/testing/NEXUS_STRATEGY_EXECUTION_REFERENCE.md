# NEXUS — riferimento esecuzione delle 37 strategie (04/08)

Preparato su richiesta esplicita ("ho bisogno della lista di tutte le
strategie... dimmi come avviene la loro esecuzione 1 per 1"). Copre le
37 strategie "live" del roster NEXUS (più ELLIOTT, che non ha una
versione Python — solo Pine — quindi non è testabile qui). Per ognuna:
famiglia, come genera il segnale, come calcola SL/TP, se la fedeltà
verso il vero MQL5 è stata verificata in questa sessione, e lo stato
attuale.

## Come funziona l'esecuzione in generale (tutte le strategie)

Il motore Python (`server/backtest.py`) valuta **una barra chiusa alla
volta**, mai in tempo reale/tick. Per ogni strategia esiste una funzione
`sig_X(candele, indicatori, i)` che guarda solo dati fino alla barra `i`
(mai barre future — nessun lookahead) e ritorna `1` (compra), `-1`
(vendi) o `0` (niente). Regole comuni a tutte:

1. **Un segnale = un ingresso al prezzo di CHIUSURA della barra** (non
   un ordine pendente al massimo/minimo — approssimazione dichiarata,
   usata ovunque nel motore).
2. **SL/TP**: o generico (multiplo di ATR, configurabile), o **strutturale
   e fisso** se la strategia è nel dict `STRATEGY_SLTP_ALWAYS` (il vero
   MQL5 usa un livello di prezzo — sweep, range asiatico — non un
   multiplo ATR libero; per queste strategie i parametri di stop/target
   generici NON hanno effetto, lezione #17).
3. **Una sola posizione alla volta** (per l'intero motore, non solo per
   strategia) — un nuovo segnale mentre sei già dentro un trade viene
   ignorato. Questo è il limite architetturale di cui abbiamo appena
   parlato (da affrontare).
4. **Filtri opzionali applicabili a QUALUNQUE strategia** dal chiamante
   (non fanno parte della logica della strategia stessa): `htf_filter`
   (trend su media mobile), `confirm_bars` (il segnale deve reggere N
   barre), `breakeven_r`/`trailing_atr` (gestione dopo l'apertura),
   `cooldown_bars`, `session_filter`, e ora `pyramid_max_legs` (vedi
   sessione precedente).

## Legenda colonne

- **Fedeltà**: `✅ verificata` = confrontata riga-per-riga col vero MQL5
  in questa sessione (04/08), corretta se serviva. `⚠️ non verificata` =
  mai confrontata con questo rigore, il codice Python è un'approssimazione
  non controllata. `🔶 nota divergenza` = un problema reale è stato
  trovato ma NON corretto (bassa priorità dichiarata, quasi sempre
  perché la strategia è già disattivata nell'EA reale).
- **SL/TP**: `strutturale` = formula propria fedele (STRATEGY_SLTP_ALWAYS
  o STRATEGY_TARGETS_ALWAYS), `generico` = multiplo ATR configurabile.

---

## Famiglia AMD (Accumulation-Manipulation-Distribution, a sessione)

| Strategia | Selector | Esecuzione | SL/TP | Fedeltà |
|---|---|---|---|---|
| **AMD_CONT** | 28 | Continuazione dopo la fase di manipolazione: rottura del range asiatico + ritorno (retest) sul lato giusto, filtro sessione LONDON/NY | strutturale (livello range asiatico ± buffer ATR) | ✅ verificata (deep-dive completo, 04/08) |
| **AMD_REVERSAL** | 24 | Sweep del range asiatico + CHoCH strutturale (frattale) nella direzione opposta | strutturale (livello di sweep ± buffer ATR) | ✅ verificata (04/08, CHoCH corretto da proxy vecchio) |
| **PO3** | 33 | Ciclo Accumulation→Manipulation→Distribution, entry su CHoCH strutturale | TP strutturale, **SL generico** (formula SL reale non trovata/confermata) | ✅ CHoCH verificato, ⚠️ SL non confermato |

## Famiglia LIQUIDITY (sweep di liquidità)

| Strategia | Selector | Esecuzione | SL/TP | Fedeltà |
|---|---|---|---|---|
| **TURTLE_SOUP** | 17 | Sweep PDH/PDL (o Asia) + candela di rigetto (corpo≥0.4×ATR) che richiude oltre il livello | strutturale (livello di sweep ± 0.5×ATR, TP a 2.0×R) | ✅ verificata, **deep-dive completo (67/100)** |
| **SH_BMS_RTO** | 21 | State machine 3 stadi: sweep → (entro 20 barre) rottura struttura con corpo≥0.8×ATR → attesa ritorno (entro 15 barre) nella zona d'origine | strutturale (min/max sweep+origine ± 0.5×ATR, TP fisso 2.6×ATR) | ✅ verificata (appena riscritta, questa sessione) |
| **SMS_BMS_RTO** | 22 | Controllo composito STESSA barra: failure swing (10 vs 20 barre) + CHoCH opposto + candela di rigetto + prezzo in metà range giusta | strutturale (estremo 10 barre ± 0.5×ATR, TP fisso 2.6×ATR) | ✅ verificata (appena riscritta) |
| **BJORGUM** | 6 | Pattern su finestra di pivot (30 barre) | generico | ✅ verificata (corretto off-by-one) |
| **LIQ_SWEEP** | 7 | Sweep generico | generico (TP strutturale opt-in, mai attivato di default) | ⚠️ parziale (controllata 16/07, prima del rigore attuale) |
| **MALAYSIAN_SNR** | 26 | Livelli H4+W1 con contatore di utilizzo persistente, **indipendente dal TF della strategia stessa** | generico | ⚠️ **non verificabile del tutto**: richiede dati cross-TF che questo motore a singolo TF per run non può replicare fedelmente |
| **STRUCT_REACT** | 16 | Motore "reazione" strutturale dedicato (score composito) | generico | 🔶 divergenza nota, non corretta — **disattivata nell'EA reale** (perde soldi su dati veri) |
| **THREE_BAR_DELIVERY_BREAK** (alias CISD) | 27 | 3 candele consecutive nella stessa direzione poi rottura | generico | ⚠️ non riverificata in questo giro 04/08 |

## Famiglia MOMENTUM

| Strategia | Selector | Esecuzione | SL/TP | Fedeltà |
|---|---|---|---|---|
| **ADX_RSI** | 1 | ADX + RSI incrocio soglie | generico | ✅ verificata, già fedele (nessuna correzione) |
| **MACD** | 3 | Incrocio linea MACD/signal | generico | ✅ verificata, già fedele |
| **RSI_DIV** | 14 | Divergenza prezzo/RSI | generico | ✅ verificata, già fedele |
| **SAR** | 4 | **Condizione di stato** (non flip): SAR vs prezzo + EMA9>EMA21 | generico | ✅ verificata (riscritta da trigger-al-flip a condizione-di-stato) |
| **TSI** | 5 | Vero TSI a doppio smoothing (Blau) + cross linea segnale | generico (testata con successo anche piramidazione) | ✅ verificata (riscritta, prima era una semplificazione mai realmente TSI) |

## Famiglia PATTERN

| Strategia | Selector | Esecuzione | Fedeltà |
|---|---|---|---|
| **ELLIOTT** | 36 | Onde di Elliott | **nessuna versione Python** — solo portata su Pine, non testabile in questo motore |

## Famiglia SESSION (gate orario ICT)

| Strategia | Selector | Esecuzione | SL/TP | Fedeltà |
|---|---|---|---|---|
| **SILVER_BULLET** | 23 | State machine 3 stadi in killzone (Londra/AM/PM, ora US EDT/EST): sweep → displacement+BOS → FVG → ritorno (entro 15 barre) | strutturale (sweep level ± 0.6×ATR, TP fisso 2.8×ATR) | ✅ verificata (riscrittura completa, prima sparava al solo sweep) |
| **JUDAS_SWING** | 29 | Sweep sessione + CHoCH strutturale | strutturale | ✅ verificata (CHoCH corretto) |
| **LDN_REVERSAL** | 30 | Sweep Londra + CHoCH strutturale | strutturale | ✅ verificata (CHoCH corretto) |
| **NY_REVERSAL** | 31 | Sweep NY + CHoCH strutturale | strutturale | ✅ CHoCH corretto, ⚠️ **limite dichiarato**: il vero MQL5 aggrega tick M5 con conversione BST/UTC per l'hi/lo di Londra — non replicabile in questo motore a singolo TF, resta un'approssimazione a finestra di barre H4 |
| **WEEKLY_EXP** | 32 | Sconto/premio settimanale + displacement H4 + BOS/CHoCH + Fibonacci | strutturale (livelli settimanali, TP anche da estensione Fibonacci) | ✅ verificata (prima condivideva un proxy generico con LONDON_BO — corretto) |

## Famiglia SMC (Smart Money Concepts)

| Strategia | Selector | Esecuzione | SL/TP | Fedeltà |
|---|---|---|---|---|
| **ORDER_BLOCK** | 15 | State machine: impulso (corpo≥1.2×ATR) che rompe uno swing a 15 barre (BOS) → zona d'origine (candela opposta prima dell'impulso) → attesa ritorno (20 barre) con rigetto + conferma trend H1 esterno | generico (NXS_DefaultSLTP, nessuna formula propria nel vero MQL5) | ✅ verificata (riscrittura completa questa sessione) — 🔶 gap dichiarato: manca il filtro "reazione globale" (NXS_SMCReactionOK), sottosistema separato non replicato |
| **OB_MIT** | 20 | **Identica a ORDER_BLOCK** — nel vero MQL5 è letteralmente un wrapper che la riusa (solo punteggio/nome diversi) | generico | ✅ verificata (scoperto e corretto: prima aveva logica propria diversa, ora richiama sig_order_block) |
| **IFVG** | 18 | Fair Value Gap invalidato + CHoCH sulla stessa barra | strutturale (bordo del gap ± buffer, TP fisso 2.4×ATR) | ✅ verificata (aggiunti buffer ATR, filtro reazione, CHoCH stessa barra) |
| **FVG_MIT** | 19 | Ritorno maturo (5-7 barre) in una zona FVG vecchia + candela di rigetto | strutturale | ✅ verificata (indici del gap corretti — nomi MQL5 fuorvianti) |
| **FVG_CONT** | 8 | Gap a 3 candele + trend H1 esterno reale | generico | ✅ ragionevolmente fedele (corretto il 16/07, prima del rigore attuale ma già usa il trend vero) |
| **LIQ_VOID** | 34 | **Proxy dichiarato di FVG_CONT**, ma usa la versione con filtro EMA50 locale (non il trend H1 esterno) | generico | ⚠️ non verificata indipendentemente — condivisione di funzione mai controllata a fondo |
| **OTE_CONT** | 25 | Fibonacci H1 cross-TF + gate BOS | generico | 🔶 divergenza nota, non corretta — **disattivata nell'EA reale** |
| **DISP_REBAL** | 35 | Displacement + ribilanciamento | generico | 🔶 divergenza nota, non corretta — **disattivata nell'EA reale** |

## Famiglia TREND

| Strategia | Selector | Esecuzione | SL/TP | Fedeltà |
|---|---|---|---|---|
| **BREAKOUT_ACC** | 9 | Accettazione sopra/sotto un range a 20 barre (2 chiusure consecutive) | generico | ✅ verificata, già fedele |
| **EMA_PULLBACK** | 11 | Trend persistente (5 barre) + impulso precedente + pullback con rigetto + filtro EMA50 | generico | ✅ verificata (riscrittura completa, prima solo un cross istantaneo) |
| **LONDON_BO** | 10 | Rottura del range asiatico in sessione Londra, filtro CLV | generico | ✅ verificata (nuova, prima condivideva un proxy con WEEKLY_EXP) |
| **ICHIMOKU** | 13 | Nuvola Ichimoku con shift 26 barre in avanti | generico | ✅ verificata (shift Kumo corretto) — ma **disattivata nell'EA reale** |

## Famiglia VOLATILITY

| Strategia | Selector | Esecuzione | SL/TP | Fedeltà |
|---|---|---|---|---|
| **BOLLINGER** | 2 | Chiusura fuori banda + rientro | generico | ✅ verificata (corretto bug di mixing-shift) |
| **RANGE_FADE** | 37 | **Identica a BOLLINGER** (stessa funzione, mean-reversion) | generico | ✅ stessa correzione di BOLLINGER |
| **BB_SQUEEZE** | 12 | Compressione bande (percentile) + espansione | generico | 🔶 divergenza nota, non corretta — **disattivata nell'EA reale** |

---

## Le 5 strategie disattivate nell'EA reale (dato di fatto, non nostro)

`NXS_Profile_Enabled()` nel vero MQL5 disabilita di default: **BB_SQUEEZE,
STRUCT_REACT, DISP_REBAL, OTE_CONT, ICHIMOKU** — dati reali sul conto MT5
hanno mostrato che perdono soldi. Per queste 4 su 5 (tutte tranne
ICHIMOKU) le divergenze di fedeltà trovate NON sono state corrette:
priorità bassa deliberata, dato che sono già fuori uso nel prodotto reale.

## Le 2 uniche coppie che condividono la stessa funzione (collisione dichiarata)

- **BOLLINGER / RANGE_FADE**: stessa funzione `sig_bollinger`, stesso
  identico comportamento.
- (La collisione SH_BMS_RTO/SMS_BMS_RTO è stata risolta questa sessione
  — ora hanno logica propria, vedi sopra.)

## Cosa NON è ancora verificato con lo stesso rigore delle altre

`LIQ_VOID`, `LIQ_SWEEP`, `MALAYSIAN_SNR`, `THREE_BAR_DELIVERY_BREAK`, e
le 4 strategie disattivate (`BB_SQUEEZE`, `STRUCT_REACT`, `OTE_CONT`,
`DISP_REBAL`) — i loro numeri nei test vanno presi con la stessa cautela
riservata a qualunque risultato non ancora controllato riga-per-riga.
