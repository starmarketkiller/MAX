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
