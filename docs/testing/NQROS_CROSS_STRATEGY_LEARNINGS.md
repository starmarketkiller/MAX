# NQROS v3.1 — Lezioni cross-strategia

File di memoria richiesto dalla Fase 10 del protocollo NQROS v3.1
(`NQROS_v1.0_Manuale_Operativo` + raffinamenti del 04/08). Ogni strategia
che completa il ciclo Fase 0-10 aggiunge qui le lezioni generalizzabili ad
altre strategie — non i dettagli specifici (quelli restano nel deep-dive
della singola strategia, es. `AMD_CONT_DEEPDIVE.md`).

## Da AMD_CONT (primo ciclo completo, 04/08)

1. **Ri-validare Out-of-Sample ogni volta che si sceglie un parametro via
   ricerca, non solo al gate di Fase 4.** Qualunque cosa "trovata" cercando
   (toggle, SL/TP, filtro sessione) ha lo stesso rischio di overfitting
   dell'ipotesi originale della Fase 4 — va ri-testata con lo stesso
   rigore ogni volta, anche a metà pipeline. Ha già distinto un falso
   positivo (`confirm_bars=1`, crollato da PF 3.39 a 1.40 fuori campione)
   da due veri positivi (SL/TP largo, filtro sessione — entrambi tenuti
   fuori campione).

2. **Per strategie a sessione (session-gated), segmentare i trade per
   sessione è un check economico con alto potenziale**: su AMD_CONT ha
   isolato OVERLAP come ventre molle (PF 1.10 contro 2.54 di LONDON/NY) ed
   escluderla ha quasi dimezzato il MaxDD a parità di PF. Vale la pena
   farlo su ogni strategia con un gate a sessione, non solo su quella che
   l'ha rivelato.

3. **Non dare per scontato che stringere la gestione (breakeven precoce,
   trailing stretto) sia più sicuro.** Su AMD_CONT è stato il contrario:
   breakeven a 0.5R e trailing a 1.0×ATR hanno fatto crollare il PF a
   0.5-0.6 (MaxDD oltre il 50%) perché tagliavano fuori i trade "quasi
   vincenti" (MFE alto) prima che tornassero verso il target. La cura
   giusta era dare PIÙ spazio (SL/TP più larghi), non meno. Il dato di
   Fase 2 (MFE dei perdenti) dice DOVE guardare, non automaticamente in
   CHE DIREZIONE muovere il parametro — va sempre testato, mai dedotto.

4. **Un PF spettacolare su un campione minuscolo (<10-15 trade) è
   un'ipotesi, non un risultato**, anche quando il numero è molto
   allettante (PF 2.60 su 5 trade in AMD_CONT/M5, scartato). Vale per
   qualunque timeframe/config, non solo per la strategia in esame.

5. **Il motore Python di ricerca (`server/backtest.py`) è a posizione
   singola** — non supporta piramidazione/grid/recovery (Fase 7). Per ora
   si salta quella fase su ogni strategia finché non si decide di investire
   nella capacità di motore per costruirla davvero.

6. **Limite dati intraday di Yahoo**: H4/H1 ~2 anni, M30/M15/M5 ~60 giorni.
   Su AMD_CONT questo ha impedito di sapere se il ritmo di trade e l'edge
   tengono sui 10 anni auspicati — vale per ogni strategia intraday testata
   con questo motore, non solo per questa. Per una risposta definitiva
   serve storico più lungo (export MT5, non disponibile da questo
   ambiente per Dukascopy — vedi `server/dukascopy_fetch.py` e le note
   nella sessione precedente).

7. **Fedeltà motore-Python-vs-vera-logica-MQL5 non è mai verificata per
   default** — ogni strategia nel motore Python è una ricostruzione, non
   una copia 1:1 del codice MQL5 reale. Prima di promuovere qualunque
   strategia a "mantieni" (capitale vero), andrebbe fatto un confronto
   riga-per-riga con l'implementazione MQL5 corrispondente.

## Da SILVER_BULLET (secondo ciclo completo, 04/08)

8. **Un toggle che funziona su una strategia può essere inutile (o dannoso)
   su una strategia "gemella" della stessa famiglia.** `htf_filter` era
   ridondante su AMD_CONT (filtro EMA200 già interno) ma un vincitore netto
   e non ridondante su SILVER_BULLET (nessun filtro di trend interno). Non
   generalizzare un toggle-vincente da una strategia all'altra senza
   ritestarlo — dipende da cosa la strategia ha già dentro.

9. **"Dai più spazio a SL/TP" (lezione #3, da AMD_CONT) non è una regola
   universale** — su SILVER_BULLET SL stretto (1.0×ATR) batte quello largo.
   La parte che SI generalizza è più specifica: **breakeven/trailing
   STRETTI sono quasi sempre distruttivi** (confermato identico su
   entrambe le strategie), non "sempre allargare tutto".

10. **Un pass Out-of-Sample che non collassa non è automaticamente pulito.**
    Se OGNI configurazione testata (con/senza filtro, con/senza
    combinazione) mostra lo stesso miglioramento nella stessa metà del
    periodo, è il segno di un effetto di regime/periodo di mercato che
    confonde la lettura — un rischio diverso e più subdolo del semplice
    overfitting sui parametri che il gate normalmente intercetta. Va
    segnalato esplicitamente nel punteggio finale (vedi SILVER_BULLET,
    Fase 9: 62/100, "serve dati" come priorità assoluta), non nascosto
    dietro un PF che "comunque migliora fuori campione".

## Dalla verifica di fedeltà motore-Python-vs-MQL5 (04/08, primo confronto reale)

11. **"Fedeltà mai verificata" (rischio #7) non è un rischio uniforme —
    va verificato per OGNI strategia, non assunto uguale.** Confronto
    riga-per-riga: AMD_CONT ha il cuore della logica (fase AMD, gate
    sessione) fedele, con problemi localizzati (retest su close invece di
    low, HTF bias proxy, SL/TP non implementato affatto - vedi
    `AMD_CONT_DEEPDIVE.md`). SILVER_BULLET invece manca l'INTERO
    meccanismo di conferma (displacement→BOS→FVG→ritorno, 3 stadi su più
    barre) - il Python spara al solo sweep-in-killzone. Stesso rischio
    dichiarato, gravità radicalmente diversa: uno è "impreciso su alcuni
    dettagli", l'altro è "sta testando una strategia diversa". **Priorità
    per la prossima strategia**: fare questo confronto SUBITO dopo la
    Fase 1 (non aspettare fino a dopo un deep-dive completo come successo
    qui) — se il proxy manca un meccanismo intero, tutto il lavoro dopo la
    Fase 1 è sprecato.

12. **Il SL/TP generico del motore (multiplo ATR fisso) non è sempre
    quello che usa la strategia reale.** Molte strategie MQL5 (AMD_CONT
    confermato, probabilmente altre con logica strutturale simile -
    JUDAS_SWING/PO3/LDN_REVERSAL hanno gia' `STRATEGY_TARGETS_ALWAYS` nel
    motore, quindi sono coperte) calcolano SL/TP da livelli di prezzo
    strutturali (range asiatico, swing, sweep level), non da un multiplo
    ATR libero. Se una strategia non è nei dict `STRATEGY_TARGETS_ALWAYS`/
    `STRATEGY_TARGETS_OPTIN` di `backtest.py`, va verificato ESPLICITAMENTE
    se il vero MQL5 ha una formula SL/TP propria prima di fidarsi di
    qualunque ottimizzazione Fase 6 fatta sul multiplo ATR generico -
    altrimenti si ottimizza un parametro che nell'EA reale non esiste.

13. **La verifica di fedeltà è un triangolo, non una linea**: teoria
    pubblica (ICT/fonte esterna) ↔ MQL5 ↔ Python. Verificare solo
    MQL5-vs-Python non basta se si vuole sapere se anche l'MQL5 stesso
    implementa correttamente il concetto che dichiara di implementare. Su
    AMD_CONT e SILVER_BULLET (04/08, ricerca web su EBC/ForexBee/
    GrandAlgo per Silver Bullet, Dhanith/TTrades/InnerCircleTrader per
    AMD/PO3): **in entrambi i casi MQL5 è risultato fedele alla teoria
    pubblica** — il problema è sempre stato nel motore Python, mai in
    MQL5. Non è detto che sia sempre così: se un giorno MQL5 stesso
    risultasse infedele alla teoria dichiarata, sarebbe un problema più
    serio (l'EA reale che gira sul conto, non solo lo strumento di
    ricerca) — vale la pena controllare anche quel lato, non darlo per
    scontato solo perché finora ha sempre retto.

14. **Corretta la fedeltà, i numeri sono crollati — ed è la conferma che
    valeva la pena farlo.** Dopo aver riscritto `sig_amd_cont` (retest
    corretto + vero SL/TP) e `sig_silver_bullet` (state machine completa a
    3 stadi): AMD_CONT H4 passa da PF 1.62 (proxy infedele, punteggio
    72/100) a **PF 1.09** (103 trade); SILVER_BULLET H4 da PF 1.62 a **PF
    1.03** (20 trade, contro i 65 del proxy). Entrambi gli score/decisioni
    Fase 9 precedenti sono superati — non per un errore nel processo Fase
    0-9 in sé (quello ha funzionato bene, ha isolato bottleneck reali e
    scartato overfitting), ma perché era applicato a un segnale sbagliato.
    **Lezione operativa per tutte le prossime strategie**: fare la
    verifica di fedeltà (lezione #11) SUBITO dopo la Fase 1, PRIMA di
    qualunque Fase 2-9 — il costo di scoprirlo dopo (qui: due deep-dive
    completi da rifare) è alto.

## Dal giro di verifica fedeltà su 6 strategie + deep-dive TURTLE_SOUP (04/08)

15. **Applicata la lezione #11 sul serio**: verificata la fedeltà di
    LONDON_BO/WEEKLY_EXP, IFVG, BJORGUM, TURTLE_SOUP, FVG_MIT, ICHIMOKU
    PRIMA di qualunque deep-dive (non dopo, come con AMD_CONT/
    SILVER_BULLET). Risultato: **5 delle 6 "PASS" trovate nel batch
    precedente erano artefatti di proxy infedeli** — solo TURTLE_SOUP
    (H4) ha mostrato un edge reale dopo la correzione. Conferma forte:
    la ricerca di configurazione (grid search su toggle/SL/TP) fatta
    PRIMA della verifica di fedeltà è quasi inutile, produce risultati
    che poi vengono quasi sempre superati.

16. **Tipi di bug di fedeltà trovati, per categoria** (utile come
    checklist per le prossime strategie): proxy generico condiviso che
    nasconde due strategie reali diverse (LONDON_BO/WEEKLY_EXP); filtri
    di conferma mancanti - buffer ATR, forza candela, CHoCH sulla stessa
    barra (IFVG); off-by-one nell'indicizzazione delle barre (BJORGUM);
    uso di un rilevatore di livello generico invece di quello esteso
    già disponibile nel motore (TURTLE_SOUP); indici/candele del gap
    scambiati per via di nomi di variabili MQL5 fuorvianti (FVG_MIT);
    dimenticanza di uno shift temporale nativo dell'indicatore
    (ICHIMOKU, shift Kumo 26 barre). Nessuno di questi si scopre senza
    leggere il codice MQL5 riga per riga - non basta "il concetto è lo
    stesso".

17. **Quando una strategia ha `STRATEGY_SLTP_ALWAYS` (SL/TP strutturale
    fedele), la Fase 6 "SL/TP width" è un no-op** — i parametri
    `atr_sl`/`atr_tp` passati al motore vengono bypassati, verificarlo
    prima di sprecare tempo a testarli (successo su TURTLE_SOUP: stesso
    risultato identico su ogni valore). Solo breakeven/trailing restano
    testabili in Fase 6 per quelle strategie.

18. **Il confondimento di regime (lezione #10) si è ripetuto identico su
    TURTLE_SOUP** — probabile limite dell'intero campione H4 di 1.74 anni
    usato per ogni strategia in questa sessione (Yahoo), non una
    caratteristica di una singola strategia. Aspettarselo su ogni
    prossimo deep-dive che usa lo stesso storico, finché non arriva più
    storico reale (MT5 export).
