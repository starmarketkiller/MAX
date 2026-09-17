# EDGE_COMPONENT Records v1 (Phase 5)

Schema di riferimento: `edge_component_schema.md`. Popolato SOLO con i candidati che hanno superato la classificazione `SUPPORTED_EDGE` in `edge_discovery.py` (vedi `server/research_scripts/phase5/data/edge_results_v1.json` per i numeri completi). **1 componente promosso** su un massimo di 3 consentiti — non sono stati "riempiti" altri due candidati per raggiungere il tetto: nessun altro evento/interazione testato ha superato NO_EDGE/OPPOSITE_EDGE/INSUFFICIENT_SAMPLE.

---

## EC-LIQUIDITY_SWEEP_RECLAIM (PROMOSSO — SUPPORTED_EDGE)

**component_id**: `EC-LIQUIDITY_SWEEP_RECLAIM`

**semantic_definition**: dopo che il prezzo penetra un estremo rolling a 20 barre H4 (SWEEP: `high[i] > max(high[i-20:i])` con chiusura che rientra sotto il livello, o simmetrico sul lato basso) e poi, entro 10 barre, chiude oltre il livello swept nella direzione OPPOSTA allo sweep (RECLAIM), la barra di conferma del reclaim mostra una probabilità sostanzialmente più alta della baseline di raggiungere +1×ATR prima di -1×ATR nella direzione del reclaim.

**observation_point causale**: chiusura della barra di conferma del reclaim (`confirmed_at_row_index` in `events_v1.csv`) — l'evento SWEEP che lo precede è osservato causalmente alla propria barra; il RECLAIM è per natura un evento a risoluzione ritardata (osservato solo quando si conferma, mai anticipato).

**affected_outcome**: P(+1×ATR before -1×ATR) dalla chiusura della barra di conferma, orizzonte 40 barre H4, nessuna gestione dinamica (nessun trailing/BE).

**baseline**: barre NON-RECLAIM nella stessa cella (terzile di volatilità × terzile di trend × anno) del reclaim, valutate nella stessa direzione — popolazione matched, non barre casuali indiscriminate (n=8780 osservazioni pooled, essendo ogni barra valutabile sia come ipotetica lunga sia corta quando rientra nelle celle richieste per entrambe le direzioni).

**evidence** (da `edge_results_v1.json`, split 70/30 dichiarato prima dei risultati, 2019-02-03→2021-03-12 discovery / 2021-03-12→2022-02-03 validation):

| Split | n | P(evento) | P(baseline) | ΔP | ΔE (MFE medio, ATR) | CI95 non sovrapposte |
|---|---|---|---|---|---|---|
| Discovery | 215 | 75.3% | 51.3% | +0.241 | +1.786 | Sì |
| Validation | 85 | 81.2% | 51.3% | +0.299 | +0.694 | Sì |
| BUY (dir=1) | 196 | 77.6% | 53.6% | +0.239 | +1.732 | Sì |
| SELL (dir=-1) | 104 | 76.0% | 48.9% | +0.271 | +0.695 | Sì |
| 2019 | 79 | 72.2% | 51.3% | +0.209 | +2.365 | Sì |
| 2020 | 110 | 79.1% | 51.3% | +0.278 | +1.947 | Sì |
| 2021 | 102 | 77.5% | 51.3% | +0.262 | +0.468 | Sì |
| 2022 (n piccolo) | 9 | 88.9% | 51.3% | +0.376 | -0.650 | Sì (n troppo piccolo per peso) |

Robustezza: rimuovendo il 10% degli eventi con il miglior MFE singolo in validation (77 rimasti su 85), P resta 80.5% — l'effetto non dipende da pochi outlier. Direzione dell'effetto identica in ogni sottogruppo testato (discovery/validation/BUY/SELL/ogni anno incl. il 2022 a campione minuscolo).

**confidence**: MEDIUM-HIGH per il fenomeno di mercato in sé (ampiezza dell'effetto, stabilità multi-dimensionale, CI mai sovrapposte); NON ANCORA per l'eseguibilità reale (vedi failure mode sotto).

**valid_contexts**: XAUUSD H4, sweep di un estremo rolling a 20 barre, reclaim confermato entro 10 barre — non testato su altri simboli/timeframe in questa fase.

**invalid_contexts**: non noto se l'effetto regge su timeframe più bassi (dove il rumore/i falsi reclaim sono probabilmente più frequenti) o su simboli meno liquidi/più volatili di GOLD.

**failure_modes (critico, eredita una lezione già catalogata in Phase 4)**: questo risultato usa un prezzo di entrata IDEALIZZATO (chiusura della barra di conferma), esattamente lo stesso tipo di misura che in Phase 4 (`NEXUS EA - WICK_SWEEP Entry Timing Study`) si è rivelata un artefatto di esecuzione — un fenomeno di reclaim quasi identico (WR 59.2% shadow vs 16.9% baseline) è collassato a PF 0.78-0.80 in esecuzione reale a causa di uno slippage favorevole medio di 42.6 pip fra il trigger e il fill reale, che gonfiava artificialmente il PF shadow (pattern catalogato: `SHADOW_EXECUTION_ASSUMPTION`, failure_memory.md #3). Questo componente **non deve essere considerato un edge eseguibile finché non è stato validato con un modello di esecuzione realistico** (fill al prezzo di mercato dopo la conferma H4, non alla chiusura esatta della barra di conferma). Nota a favore: qui la conferma è nativa H4 (non gated su M15 come nel caso Phase 4), quindi il ritardo strutturale fra "evento confermato" e "possibile invio ordine" è potenzialmente minore — ma questo è un'ipotesi da verificare, non un fatto assodato. **Priorità massima per Phase 6** (vedi risposta 6 nel report principale).

**Non è una strategia**: nessun TP/SL/trigger di esecuzione è stato scelto qui. Questo record descrive solo che la condizione "sweep + reclaim confermato" sposta la probabilità condizionale, non come tradarla.
