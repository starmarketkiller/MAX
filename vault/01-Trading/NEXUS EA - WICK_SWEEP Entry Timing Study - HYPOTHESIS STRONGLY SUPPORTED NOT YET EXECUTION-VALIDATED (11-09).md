# WICK_SWEEP_REV — Entry Timing Study

## STATO (12/09): PARITÀ ESATTA RAGGIUNTA — CORREZIONE METODOLOGICA SULLA CADENZA — WICK_SWEEP_RECLAIM PROMOSSA

Aggiornamento 12/09 (sera): dopo aver deciso di promuovere RECLAIM_TRIGGER a variante sperimentale separata (`WICK_SWEEP_RECLAIM`), rileggendo `NEXUS_EA_v2.mq5` per implementarla è emerso che **il follow-up dello shadow NON era tick-level come descritto in questa nota e nel codice**: `NXS_WickShadow_OnTick()` (unico call site) e' chiamata DOPO il "New bar gate" globale (`if(iTime(g_sym,InpTFEntry,0)==g_lastBarTime) return;`), quindi tanto l'ARM quanto il monitoraggio reclaim/uscita giravano SOLO una volta per barra `InpTFEntry` (M15) — mai piu' spesso. Confermato empiricamente: **122/123 (99.2%) dei `reclaim_delay_sec` registrati nel run di parita' sono multipli esatti di 900 secondi** (l'unica eccezione, 902s, e' 2 secondi oltre un boundary — coerente con "il primo tick reale della barra e' arrivato con 2s di ritardo", non con un monitoraggio infra-barra).

**Non si cancella la versione precedente di questa nota: si marca esplicitamente la correzione.** *Earlier interpretation corrected: validated shadow follow-up cadence was M15-gated, not tick-level.* I numeri (WR 59.2%/PF 5.80/expectancy +48.98 pip, sezione 7) restano validi e INVARIATI — descrivono correttamente cosa succede aspettando il reclaim del trigger_price al successivo controllo M15, non un monitoraggio continuo. La scoperta non invalida il risultato, lo rende piu' preciso.

**Conseguenza per l'implementazione reale**: `WICK_SWEEP_RECLAIM` (vedi sezione 9) replica fedelmente questa cadenza REALE (M15-gated per ARM e per il controllo del reclaim, nessun bypass del New Bar Gate), non quella erroneamente descritta come tick-level. Una variante tick-level genuina resta un design candidate separato, non implementato: vedi [[NEXUS EA - WICK_SWEEP_RECLAIM_TICK - Design Candidate Non Implementato (12-09)]].

Non implementato nulla nella strategia canonica WICK_SWEEP_REV. RECLAIM_TRIGGER e' stato promosso a variante sperimentale separata `WICK_SWEEP_RECLAIM` (selettore 55) — vedi sezione 9 per l'implementazione e il Fast Smoke reale di equivalenza.

---

## 1. Bug metodologico v1 — perché 18.232 trigger sono INVALIDI (audit trail)

**Il file raw v1 (`wick_sweep_entry_timing.py`/CSV originali) è stato cancellato durante un cleanup PRIMA che arrivasse l'istruzione esplicita di archiviarlo come audit trail — non recuperabile.** Quanto segue è la ricostruzione completa e fedele dalla trascrizione della sessione (metodologia + intero output numerico stampato), sufficiente per capire l'errore e perché invalida i risultati, anche senza il file grezzo.

**Metodologia v1 (sbagliata)**: ogni wick H4 ≥15 pip veniva registrata come un livello INDIPENDENTE E PERMANENTE nella lista `levels[]`, mai rimosso. Per ogni livello, si scandiva in avanti fino a `MAX_TOUCHES_PER_LEVEL=50` touch, su un orizzonte di 5 giorni ciascuno.

**Perché è sbagliato**: la strategia reale (`_NXS_WickSweep_UpdateLevel`, `NXS_Strategies_Experimental.mqh`) mantiene **UN SOLO livello attivo per lato** (alto/basso): ogni nuova wick H4 qualificante **SOSTITUISCE** il livello precedente, anche se non ancora sweeppato. Un livello "vecchio" scartato dal vivo non può più generare touch — ma in v1 restava vivo per sempre nel dataset, generando touch fantasma per anni dopo essere stato dimenticato dalla strategia reale.

**Conseguenza quantificata**: v1 trovava **18.232 trigger** nella sola finestra Fast Smoke (2026.06.01-08.26) contro i **181 realmente osservati dal vivo** (funnel MQL5, `sweepsDetected=181`) — fattore ~100x. Sull'intero dataset 2023-2026, v1 trovava 142.612 trigger totali, di cui la stragrande maggioranza (97.241/142.612 = 68%) su livelli "stantii" di età mediana 74 giorni (contro 14-15 giorni per gli altri bin) — praticamente tutti fantasma. Output numerico v1 completo (dal transcript, per riferimento):

```
BASELINE (IMMEDIATE_FADE) v1: n=142612  SL=138898  TP=3714  NONE=0
Disponibilita' per entry model (v1, INVALIDO):
                model      n  n_available  pct_available
       IMMEDIATE_FADE 142612       142612          100.0
        RECLAIM_LEVEL 142612        22461           15.7
      RECLAIM_TRIGGER 142612        23579           16.5
      REACTION_CANDLE 142612       142517           99.9
MICRO_STRUCTURE_SHIFT 142612       142583          100.0
         LIMIT_RETEST 142612        10702            7.5
```

Questi numeri **non vanno usati per nessuna decisione** — sono qui solo come registro dell'errore trovato e corretto nella stessa sessione, prima che l'utente potesse agire su di essi.

## 2. Fix v2 — un solo livello attivo per lato, come dal vivo

Riscritta l'architettura: non più un loop indipendente per livello, ma una **simulazione sequenziale** (`build_active_level_series` in `wick_sweep_entry_timing.py`) che replica bar-per-bar `_NXS_WickSweep_UpdateLevel`: un solo livello attivo per lato, sostituito (mai accumulato) a ogni nuova wick qualificante. Un cambio di livello attivo azzera qualunque episodio di touch in corso sul livello precedente — esattamente come dal vivo (`NXS_Strat_WickSweepReversal` legge solo `g_wickHigh`/`g_wickLow` correnti).

**Risultato v2**: 2.227 trigger totali sui 3 anni (media 64.1/mese) — **contro i 181 in 3 mesi = 60.3/mese dal vivo: match molto più stretto**, ma non ancora esatto (vedi §3 sotto per la quantificazione richiesta esplicitamente, non liquidata come "rumore").

## 3. Quantificazione del gap residuo 239 vs 181 (richiesta esplicita, non liquidata come rumore)

Nella finestra Fast Smoke, v2 trova **239 trigger** contro i **181** del funnel MQL5 reale — un residuo +32% non ancora spiegato con certezza. Cause plausibili identificate (**da confermare col report SHADOW tick-level**, non ancora certe):

1. **Granularità M15 vs tick**: il Python vede solo l'OHLC ogni 15 minuti; se il prezzo tocca e supera 35 pip PIÙ VOLTE all'interno della stessa finestra M15 in modi che il throttle "1 tentativo per barra H4" del vivo tratterebbe come un solo evento ma che il replay M15 potrebbe contare diversamente in casi limite di sostituzione del livello a cavallo di una barra M15.
2. **Ordine intra-barra non determinabile da OHLC**: quando in una singola barra M15 sia lo sweep che un successivo movimento avvengono, l'OHLC non dice l'ordine ESATTO (es. se il minimo o il massimo è stato toccato prima). Per un evento "istantaneo" (sweep e reclaim nella stessa barra M15) questo può generare falsi trigger o falsi reclaim.
3. Questa è **esattamente la ragione per cui l'utente ha richiesto la validazione SHADOW tick-level** (§5) invece di accettare il numero Python come definitivo.

**Nessuna delle due cifre (239 o 181) è stata trattata come "abbastanza vicina" senza verifica ulteriore** — il gap resta aperto fino al report SHADOW.

## 4. Risultati v2 (validi, ma solo a livello di ipotesi M15 — vedi stato in testa alla nota)

### Tabella principale — intero dataset 2023-2026 (`wick_sweep_entry_timing_summary_all.csv`)

| ENTRY_MODEL | N | N_AVAIL | %AVAIL | model SL | model TP | SL_AVOIDED | SL_AVOIDED% | TP_LOST | TP_LOST% | median MAE_4h | median MFE_4h | median delay(h) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| IMMEDIATE_FADE | 2227 | 2227 | 100.0 | 1871 | 356 | 0 | 0.0 | 0 | 0.0 | 110.4 | 85.7 | 0.00 |
| RECLAIM_LEVEL | 2227 | 1140 | 51.2 | 1022 | 118 | 1102 | 58.9 | 289 | 81.2 | 89.8 | 131.4 | 0.50 |
| **RECLAIM_TRIGGER** | 2227 | 1684 | 75.6 | 1270 | 414 | 606 | 32.4 | 6 | **1.7** | 72.0 | 114.8 | 0.00 |
| REACTION_CANDLE | 2227 | 165 | 7.4 | 132 | 33 | 1752 | 93.6 | 349 | 98.0 | 58.7 | 62.1 | 6.25 |
| MICRO_STRUCTURE_SHIFT | 2227 | 605 | 27.2 | 495 | 110 | 1489 | 79.6 | 322 | 90.4 | 112.4 | 82.2 | 2.00 |
| LIMIT_RETEST | 2227 | 358 | 16.1 | 183 | 175 | 1736 | 92.8 | 286 | 80.3 | 51.5 | 104.7 | 1.25 |

WR baseline 16.0% → RECLAIM_TRIGGER 24.6% (a RR 25/100: expectancy -500/100tr → **+575/100tr**), sacrificando solo l'1.7% dei TP.

### Finestra Fast Smoke 2026.06.01-08.26 (`wick_sweep_entry_timing_summary_fastsmoke.csv`) — confronto diretto con 148 SL/30 TP reali

| ENTRY_MODEL | N | %AVAIL | model SL/TP | WR | SL_AVOIDED% | TP_LOST% |
|---|---|---|---|---|---|---|
| IMMEDIATE_FADE | 239 | 100.0 | 217/22 | 9.2% | — | — |
| RECLAIM_LEVEL | 239 | 56.1 | 129/5 | 3.7% | 50.2 | 95.5 |
| **RECLAIM_TRIGGER** | 239 | 69.9 | 139/28 | **16.8%** | **36.9** | **9.1** |
| REACTION_CANDLE | 239 | 5.4 | 9/4 | 30.8% | 95.9 | 95.5 |
| MICRO_STRUCTURE_SHIFT | 239 | 28.5 | 56/12 | 17.6% | 78.3 | 90.9 |
| LIMIT_RETEST | 239 | 15.5 | 16/21 | **56.8%** | 93.1 | 77.3 |

**Tradotto sui numeri reali (148 SL / 30 TP)**: RECLAIM_TRIGGER avrebbe evitato circa **55 dei 148 SL** (36.9%) sacrificando circa **3 dei 30 TP** (9.1%) — proporzioni applicate ai conteggi reali, non ricalcolate su un campione diverso.

### Segmentazione (dataset completo, IMMEDIATE_FADE baseline)

**Età al trigger** — sotto il modello corretto (un livello attivo per lato), quasi tutti i trigger sono freschissimi: <1g n=2119 (83.8% SL/16.2% TP), 1-7g n=108 (88.9%/11.1%). Nessun bucket oltre 7 giorni esiste più — **il problema BAD LEVEL (livelli stantii) non si applica a WICK_SWEEP_REV**, che per design non tiene mai un livello vecchio.

**Touch number**: 1° tocco n=1757 (84.9%/15.1%), 2° n=378 (80.2%/19.8%), 3-5° n=91 (82.4%/17.6%) — nessuna differenza sistematica forte.

**Penetrazione/ATR**: 0-0.5 n=2203 (84.3%/15.7%), 0.5-0.75 n=20 (55.0%/45.0%, campione troppo piccolo per trarre conclusioni). Quasi tutto cade nello stesso bin — nessuna segmentazione utile qui nel modello corretto (a differenza del dataset STRUCT_LEVEL_SWEEP generale, dove l'artefatto dei livelli stantii rendeva questo bucket molto più informativo).

**Conclusione della segmentazione**: **non è un problema di BAD LEVEL** (età/penetrazione non spiegano la varianza, perché il design "un livello, sostituito subito" la elimina strutturalmente) — è **BAD TIMING**: la stessa identica popolazione di eventi passa da WR 16% a 25% aspettando il reclaim del prezzo di trigger, nessun cambio di livello o soglia.

## 5. Implementazione MQL5 SHADOW/RESEARCH (tick-level, per la validazione richiesta)

File: `MQL5/Include/NEXUS_v1/NXS_Strategies_Experimental.mqh` (esteso), `MQL5/Include/NEXUS_v1/NXS_Inputs.mqh` (nuovo input), `MQL5/Experts/NEXUS_EA_v2.mq5` (wiring).

**Nuovo input**: `InpResearchWickShadow` (default `false`, zero impatto se spento).

**Comportamento**: quando `InpResearchWickShadow=true` E `InpStrat_WickSweep=true`, `NXS_WickShadow_OnTick()` (chiamata da `OnTick()`, dopo `NXS_UpdateIndicators()`) osserva ogni tick lo stesso `g_wickHigh`/`g_wickLow` della strategia canonica e:
- rileva lo stesso identico sweep (stessa soglia `InpWickSweep_SweepPips`, stesso riferimento bid/ask) e logga `[WICKSHADOW][SWEEP] sweep_id=... level_id=... side=... level=... trigger=... time=...`;
- traccia `max_penetration_before_reclaim`, il momento di reclaim del trigger price (`[WICKSHADOW][RECLAIM_TRIGGER]`, con `time_sweep_to_reclaim_sec`) e del livello originale (`[WICKSHADOW][RECLAIM_LEVEL]`);
- alla riconquista del trigger price, apre un **trade VIRTUALE** (nessun OrderSend reale) con `SL=InpWickSweep_SLPips`, `TP=InpWickSweep_TPPips` identici alla strategia canonica, nessun BE/trailing/filtro nuovo — traccia MAE/MFE tick per tick e logga l'uscita (`[WICKSHADOW][EXIT] outcome=SL|TP ...`);
- se il livello osservato viene sostituito da una nuova wick prima che l'evento si risolva, lo **abbandona** esplicitamente (`[WICKSHADOW][ABANDONED] reason=level_replaced`) invece di forzare una risoluzione artificiale;
- a fine test, `[WICKSHADOW][SUMMARY] shadow_sweeps=... canonical_sweepsDetected=... parity=PASS|FAIL` — il controllo di parità richiesto esplicitamente (deve combaciare col funnel canonico `sweepsDetected`, altrimenti FAIL e si cerca la causa prima di fidarsi del resto).

Instrumentazione aggiuntiva **a impatto zero sul comportamento canonico**: campo `id` aggiunto a `SNxsWickSide` (incrementato a ogni sostituzione in `_NXS_WickSweep_UpdateLevel`) — usato SOLO per riconoscere quando lo shadow deve abbandonare un evento, mai letto da nessuna decisione di trading.

Compilato 0 errori (2 warning preesistenti invariati). **Nessun ordine reale RECLAIM_TRIGGER è mai inviato da questo codice** — la strategia canonica continua a fare esattamente quello che faceva (IMMEDIATE_FADE reale), lo shadow gira in parallelo sugli stessi sweep osservati dal vivo.

## 6. Validazione tick-level MQL5 SHADOW/RESEARCH — cronologia dei fix (audit trail completo)

Tre run sono FALLITI sulla verifica di parità prima di raggiungere il PASS. **Nessuno dei tre è stato cancellato**: i log estratti (solo righe `[WICKSHADOW]`/`[RESEARCH][OPEN]`/`[RESEARCH][EXIT]`/`[WICKSWEEP][FUNNEL]`, isolate per finestra wall-clock del run specifico) sono committati in `server/research_scripts/`, ciascuno accanto al commit del fix corrispondente:

| Run | Risultato | File archiviato | Motivazione FAIL | Commit fix |
|---|---|---|---|---|
| 1 | shadow_sweeps=1100 vs canonical=182 | `wick_shadow_INVALID_run1_parity_fail_log_extract.txt` | **shadow one-shot mismatch**: mancava un gate one-shot per livello nello shadow — dopo un'uscita virtuale oltre soglia, il prezzo restava sopra/sotto il trigger e ogni tick generava un "nuovo" sweep sullo stesso livello, a cascata. | `d89c2e9` |
| 2 | shadow_sweeps=258 vs canonical=182 | `wick_shadow_INVALID_run2_parity_fail_258vs182_log_extract.txt` | **shadow before New Bar gate**: lo shadow leggeva bid/ask ad OGNI tick, mentre il canonico (e con esso TUTTE le strategie del router) viene valutato una sola volta per barra `InpTFEntry`=M15 a causa del "New bar gate" globale in `OnTick()` — scoperta architetturale documentata separatamente in [[NEXUS - Global New-Bar Gate - Signal Sampling Audit (12-09)]]. | `9a31620` |
| 3 | shadow_sweeps=213 vs canonical=182 | `wick_shadow_INVALID_run3_parity_fail_213vs182_log_extract.txt` | **shadow before canonical upstream gates**: l'hook shadow era posizionato PRIMA dei gate `paused/entryAllowed/license/protections/spread/news` in `OnTick()` — se uno di questi bloccava il tick, `NXS_CollectAllSignals()` (e quindi la strategia canonica) non veniva mai chiamata quella barra, ma lo shadow (eseguito prima) vedeva comunque lo sweep e lo tradava virtualmente: un evento shadow su una barra che il canonico non aveva mai effettivamente valutato. | `0550f4a` |
| **4** | **shadow_sweeps=181 == canonical=181** | `wick_shadow_VALID_run4_parity_pass_181eq181_log_extract.txt` | **PASS** — hook riallineato subito prima di `NXS_CollectAllSignals()`, dopo TUTTI i gate a monte. | (nessun fix necessario) |

Ogni run è stato ri-eseguito con la STESSA finestra Fast Smoke, gli STESSI parametri (SL25/TP100/sweep35/MinWick15), la STESSA leva 1:500 — cambiava solo il codice dello shadow (mai la strategia canonica, mai SL/TP/parametri WICK).

**Scoperta collegata marcata come requisito futuro** (per l'utente, non ancora implementata): ogni futuro shadow/diagnostic path deve dichiarare esplicitamente a quale punto esatto della pipeline OnTick() si aggancia (prima/dopo quali gate) — la causa del FAIL run 3 è stata proprio un hook che si agganciava a un punto diverso, non dichiarato, rispetto al percorso realmente eseguito dalla strategia canonica.

## 7. Report evento-per-evento (run 4, parità esatta)

**Verifica di parità estesa** (oltre al conteggio aggregato 181==181): è stato fatto un join esatto (stesso secondo, stesso prezzo, stesso side/dir) fra ogni evento `[WICKSHADOW][SWEEP]` e il corrispondente `[RESEARCH][OPEN]` reale. Risultato: **176/181 (97.2%) match esatti**. I restanti 5 sono stati investigati singolarmente e sono interamente spiegati da meccanismi noti, senza alcun impatto sul conteggio di parità:

- **2 eventi (sweep_id 101, 153)**: lo shadow rileva il livello un bar M15 dopo il canonico. Causa: `_NXS_WickShadow_ProcessSide` processa una sola transizione di stato per lato per tick (o chiude il vecchio evento, o ne apre uno nuovo, mai entrambi), mentre il canonico ri-valuta la condizione di sweep sul livello appena sostituito nello STESSO tick — se il prezzo ha già superato la soglia al momento stesso della creazione del nuovo livello ("gap-through"), il canonico entra subito, lo shadow lo rileva un bar dopo. Puramente un artefatto di strumentazione dello shadow, zero effetto sulla strategia reale.
- **3 eventi (sweep_id 45, 147, 180)**: contati da `sweepsDetected` ma mai arrivati a `NXS_WickSweep_OnExecuteResult` (né aperti né rifiutati — coerente con `entryRejected=0` sull'intero test e con `sweepsDetected(181) − entryOpened(178) = 3`). Causa isolata nel loop "PROFILI PER-STRATEGIA" di `NEXUS_EA_v2.mq5`: due gate (riga ~1341 `NXS_StrategyHasOpenPos`, riga ~1347 throttle "una decisione per barra del TF della strategia", quest'ultimo condiviso fra i lati alto/basso di WICK_SWEEP_REV perché chiavato solo sul nome strategia) stanno A MONTE dell'hook, quindi invisibili al funnel. Un diagnostico Print mirato è stato aggiunto in questi due punti (guardato su `stratName=="WICK_SWEEP_REV"`, zero impatto comportamentale) ma **non ancora compilato/eseguito** — non necessario per il report richiesto, dato che questi 3 eventi non hanno comunque un trade reale con cui confrontare l'esito virtuale (finiscono in `NO_BASELINE_ENTRY`, escluso dalle 6 categorie causali).

Matrice completa (181 righe, tutti i campi richiesti: sweep_id/level_id/side/canonical_entry_time/canonical_entry_price/canonical_outcome/reclaim_available/reclaim_time/reclaim_delay_sec/reclaim_entry_price/virtual_outcome/virtual_MAE/virtual_MFE/max_penetration_before_reclaim/categoria) in `server/research_scripts/wick_reclaim_event_matrix.csv`, generata da `server/research_scripts/wick_reclaim_final_report.py`.

### Classificazione causale (181 eventi)

| Categoria | n | % |
|---|---|---|
| BASELINE_SL_AVOIDED | 35 | 19.3% |
| BOTH_SL | 40 | 22.1% |
| BASELINE_TP_PRESERVED (= BOTH_TP) | 21 | 11.6% |
| BASELINE_TP_LOST | 0 | 0.0% |
| RECLAIM_NOT_AVAILABLE | 82 | 45.3% |
| NO_BASELINE_ENTRY (i 3 eventi di cui sopra, nessun trade reale da confrontare) | 3 | 1.7% |

*Nota terminologica*: le etichette richieste `BASELINE_TP_PRESERVED` e `BOTH_TP` descrivono lo stesso esito (baseline TP, reclaim anche TP) — presentate come un'unica riga.

### Destino dei 148 SL baseline

| Esito sotto RECLAIM_TRIGGER | n | % dei 148 |
|---|---|---|
| NO TRADE (reclaim mai disponibile — il prezzo non è mai tornato al trigger prima che il livello fosse sostituito) | 73 | 49.3% |
| Resta SL (BOTH_SL) | 40 | 27.0% |
| Diventa TP (BASELINE_SL_AVOIDED) | 35 | 23.6% |

### Destino dei 30 TP baseline

| Esito sotto RECLAIM_TRIGGER | n | % dei 30 |
|---|---|---|
| Preservato (TP→TP) | 21 | 70.0% |
| Perso per non-trade (reclaim mai disponibile) | 9 | 30.0% |
| Cambia esito in SL (BASELINE_TP_LOST) | 0 | 0.0% |

**Nessun TP baseline si trasforma in SL sotto RECLAIM_TRIGGER quando il reclaim è disponibile** — le mosse abbastanza forti da colpire TP nell'immediato restano vincenti anche aspettando la conferma del reclaim.

### Metriche aggregate

| Metrica | BASELINE (IMMEDIATE_FADE, reale) | RECLAIM_TRIGGER (virtuale, tick-level) |
|---|---|---|
| n | 178 | 98 (disponibilità 54.1% su 181 sweep) |
| WR | 16.9% (30/178) | 59.2% (58/98) |
| PF (pip, 25/100 fissi) | 0.81 | 5.80 |
| Expectancy | -3.93 pip/trade | +48.98 pip/trade |

- **Median MAE (reclaim)**: 0.00 pip — la maggioranza dei trade reclaim sono vincenti con drawdown iniziale nullo (il reclaim stesso funge da conferma, il movimento successivo è spesso immediato e favorevole).
- **Median MFE (reclaim)**: 114.50 pip.
- **Median reclaim delay**: 900 sec (15 min = 1 barra M15). Distribuzione: ≤15min 68 (69%), 15-30min 17 (17%), 30-60min 8 (8%), 1-2h 3 (3%), >2h 2 (2%) — la stragrande maggioranza del reclaim avviene già alla barra M15 successiva.
- **BUY/SELL split (reclaim disponibile)**: BUY(low side) n=50 WR=64.0%; SELL(high side) n=48 WR=54.2% — leggero edge sul lato BUY, campione non enorme per concludere un'asimmetria strutturale.
- **Prima metà vs seconda metà periodo**: 1a metà n=49 WR=63.3%; 2a metà n=49 WR=55.1% — leggero calo ma il miglioramento vs baseline (16.9%) resta ampio e stabile in entrambe le metà.
- **Distribuzione penetrazione aggiuntiva pre-reclaim (pip)**: min 36.6, p25 63.1, mediana 86.4, p75 146.2, max 588.5. Bucket: ≤50pip 15, 50-100pip 42, 100-200pip 25, 200-500pip 14, >500pip 2 — la maggior parte dei reclaim avviene dopo una penetrazione aggiuntiva moderata (50-200 pip), coerente con MAE virtuale spesso nullo (il trade entra già vicino all'estremo del movimento).

### Confronto quantitativo Python (offline M15) vs tick-level MQL5

Lo studio Python offline (v2) aveva stimato **239 trigger** nella stessa finestra Fast Smoke, contro i **181** osservati sia dal funnel canonico originale sia — ora — dallo shadow tick-level a parità esatta. Con la parità MQL5-vs-MQL5 confermata **esatta** (181==181), il gap Python-vs-reale (58 eventi, +32%) è ORA interamente isolato al metodo Python, non a rumore residuo M15-vs-tick nel motore MQL5 stesso (quello è chiuso a zero). Causa più plausibile, quantificabile solo qualitativamente senza strumentare anche il Python con gli stessi gate: **il dataset Python valuta la soglia di sweep sugli estremi High/Low dell'intera barra M15 (OHLC), mentre il canonico/shadow MQL5 campiona bid/ask live SOLO all'istante del tick di cambio-barra M15** — un prezzo che tocca la soglia a metà barra e si ritira prima del prossimo cambio-barra è "visto" da Python (che guarda l'estremo della barra) ma MAI dal vivo (che guarda solo l'istante campionato). Questo é strutturalmente un sovraconteggio one-directional (Python ≥ reale, mai il contrario), coerente con il segno e l'ordine di grandezza del gap osservato (239 > 181, mai sotto). Non quantificato in modo esatto senza rifare il dataset Python con lo stesso campionamento a evento M15 (non fatto, fuori scope di questo report).

## 8. Decisione presa — RECLAIM_TRIGGER promosso a WICK_SWEEP_RECLAIM

Il miglioramento è ampio (WR 16.9%→59.2%, PF 0.81→5.80, expectancy da negativa a +49 pip/trade) ma disponibile solo sul 54.1% dei sweep — il 45.3% (82/181) non avrebbe mai generato un trade sotto RECLAIM_TRIGGER (reclaim mai avvenuto prima che il livello fosse sostituito). Dei 148 SL baseline, quasi metà (49.3%) semplicemente non sarebbero mai stati aperti; dei 30 TP baseline, il 30% sarebbe stato perso per lo stesso motivo. **Non è una sostituzione 1:1 della strategia, è un cambio di profilo: meno trade, ciascuno con probabilità di successo molto più alta.**

L'utente ha deciso (12/09) di promuovere RECLAIM_TRIGGER a variante sperimentale separata `WICK_SWEEP_RECLAIM`, senza modificare WICK_SWEEP_REV. Implementazione e Fast Smoke di equivalenza in sezione 9.

**LIMIT_RETEST resta Candidate #2, non implementato.**

**Non toccato**: SL/TP/parametri WICK, Structure/Reaction Engine, New Bar Gate, altre strategie. I due `Print` diagnostici zero-impatto aggiunti in `NEXUS_EA_v2.mq5` per la precedente indagine sul gap sweepsDetected/entryAttempts (righe ~1341/~1347) sono stati RIMOSSI (non più necessari, causa già identificata e documentata).

## 9. WICK_SWEEP_RECLAIM — implementazione e Fast Smoke di equivalenza

### Identità separata (contract/source-of-truth)

`knowledge/strategy_database.json`: nuova voce `WICK_SWEEP_RECLAIM`, `selector_index: 55` (WICK_SWEEP_REV resta 54, non toccato). Rigenerato `contracts/generate_registry.py` → diff minimale su `contracts/strategy-registry.json`, `frontend/src/contracts/strategyRegistry.js`, `MQL5/Include/NEXUS_v1/NXS_StrategyRegistry.mqh` (solo l'aggiunta della nuova entry, nessuna riga esistente toccata).

`NXS_StrategyProfiles.mqh`: `NXS_Profile_TF("WICK_SWEEP_RECLAIM") = PERIOD_H4` (stessa TF di REV, stessa sorgente evento) e `NXS_Profile_Enabled("WICK_SWEEP_RECLAIM") = true` (altrimenti `OPEN_FAIL_PREFLIGHT/profile_disabled` silenzioso, stesso bug già visto per REV il 10/09).

Nuovo input `InpStrat_WickSweepReclaim` (default `false`), dichiarato in `NXS_Inputs.mqh`. Riusa `InpWickSweep_MinWickPips/SweepPips/SLPips/TPPips` — **nessun parametro nuovo, nessuna ottimizzazione**.

### Correzione di causalità applicata (vedi banner in testa alla nota)

L'istruzione originale chiedeva "detection M15, reclaim tick-level" come replica di quanto lo shadow aveva dimostrato. Rileggendo il codice per implementarla è emerso che lo shadow stesso era M15-gated in entrambe le fasi (vedi banner). **Confermato con l'utente**: `WICK_SWEEP_RECLAIM` replica la cadenza REALE (M15-gated per ARM e per il controllo periodico del reclaim, nessun bypass del New Bar Gate). Una variante tick-level genuina resta un design candidate separato e non implementato: [[NEXUS EA - WICK_SWEEP_RECLAIM_TICK - Design Candidate Non Implementato (12-09)]].

### State machine (`NXS_Strategies_Experimental.mqh`)

```
IDLE → ARMED → RECLAIMED → OPENED
ARMED → ABANDONED (level replacement)
RECLAIMED → ABANDONED (level replacement, se ancora non aperto)
```

Campi tracciati per setup (`SNxsWickReclaimState`): `sweep_id, level_id, side, level_price, trigger_price, sweep_time, max_penetration_pips, reclaim_time`, più `lastArmedLevelId` (one-shot per livello).

Regole di invalidazione **replicate esattamente** da quelle validate nello shadow (non reinventate): one-shot per level_id, ARM solo su nuova coorte `InpTFEntry`, ABANDONED solo su sostituzione livello (`side.id != level_id`) prima di un'apertura riuscita, trigger_price = prezzo osservato reale (non teorico), SL/TP calcolati dal trigger_price.

**Unica regola NON coperta dallo shadow** (che apre sempre con successo, nessun gate reale): un tentativo di apertura reale può essere bloccato. Scelta esplicita, dichiarata (non silenziosa): se bloccato, il setup resta `RECLAIMED` e viene ritentato alla barra `InpTFEntry` successiva, finché non si apre o il livello viene sostituito — stessa filosofia di retry già usata da `NXS_Strat_WickSweepReversal` per i propri tentativi rifiutati.

### Wiring reale (`NEXUS_EA_v2.mq5`)

`NXS_WickReclaim_TryEntries()` (nuova funzione, vive nel .mq5 perché usa `NXS_StrategyHasOpenPos`/`NXS_GetLastTfBar`/`NXS_SetLastTfBar`/`NXS_OpenTrade`, tutte definite/incluse dopo `NXS_Strategies_Experimental.mqh`) chiamata da `OnTick()` nello stesso punto di `NXS_WickShadow_OnTick()` — dopo tutti i gate a monte incluso il New Bar Gate. Per ogni lato con un setup `RECLAIMED`: stesso controllo "una posizione per strategia" + "una decisione per barra TF" del loop PROFILI PER-STRATEGIA, poi `NXS_OpenTrade()` (stesso preflight/execution path di qualunque altra strategia). Log distinti: `[WICKRECLAIM][ARMED]`, `[WICKRECLAIM][RECLAIM_AVAILABLE]`, `[WICKRECLAIM][ENTRY_ATTEMPT]`, `[WICKRECLAIM][OPENED]`, `[WICKRECLAIM][BLOCKED_OPEN_POSITION]`, `[WICKRECLAIM][BLOCKED_TF_THROTTLE]`, `[WICKRECLAIM][BLOCKED_PREFLIGHT]`, `[WICKRECLAIM][BLOCKED_PROTECTION]`, `[WICKRECLAIM][BROKER_REJECT]`, `[WICKRECLAIM][ABANDONED]`, più `[WICKRECLAIM][FUNNEL]` a fine test.

Compilato: **0 errori** (2 warning preesistenti invariati, nessun warning nuovo).

### Fast Smoke reale (2026.06.01→08.26, GOLD H4, leva 1:500, lotto fisso 0.02, RAW)

Stessi identici dati/parametri del run 4 shadow validato, `InpStrategySelector=55` (isola WICK_SWEEP_RECLAIM), `InpStrat_WickSweepReclaim=true`, `InpStrat_WickSweep=false` (REV non attiva in questo test). Unico obiettivo dichiarato: verificare se l'implementazione reale riproduce la coorte shadow, NON dichiarare edge.

### Risultato MT5 ufficiale (report .htm)

112 trade, WR 48.21%, PF 0.80, Sharpe -5.00, drawdown equity 15.06%.

### Reconciliation evento-per-evento (181 sweep, run reale vs run 4 shadow)

**Coorte sweep**: **identica** — 181 ARMED (reale) = 181 SWEEP (shadow), stesso set esatto di `(level_id, side)`. Nessuna divergenza architetturale sulla detection.

**Disponibilità reclaim**: 122 (reale) vs 123 (shadow) — quasi identica. L'unica differenza (`level_id=432, side=HIGH`) è spiegata: nel run reale l'evento precedente su quel lato era ancora `WR_OPENED` (posizione reale aperta) nel momento in cui una nuova wick ha sostituito il livello, quindi il "recycle" dello slot (necessario prima di poter armare il nuovo livello) è avvenuto un ciclo M15 dopo rispetto allo shadow — dove l'evento precedente su quel lato era già risolto. Stesso trigger_price alla fine (4099.60 reale vs 4101.25 shadow, un bar M15 di differenza), stesso meccanismo del "lag di una barra" già documentato in sezione 7 per la coppia shadow-vs-canonico (§7, sweep_id 101/153) — qui riappare fra shadow e reale per lo stesso motivo strutturale (una sola transizione di stato per lato per chiamata).

**Timestamp ed entry**: **coerenti con la cadenza M15** — per tutti gli eventi in comune, `reclaim_delay_sec` combacia ESATTAMENTE fra shadow e reale (900/1800/2700/3600s, verificato su 15+ esempi). Il gate M15 è stato replicato fedelmente, come richiesto.

**Conteggio trade**: 112 reali vs 98 shadow-risolti (98/123 = 79.7%) — il reale converte una quota MAGGIORE dei reclaim disponibili in trade (112/122 = 91.8%), perché a differenza dello shadow (che abbandona un evento "a metà" se il livello viene sostituito prima della risoluzione) un tentativo reale bloccato **viene ritentato alla barra successiva** finché non si apre o il livello non viene sostituito — quindi recupera alcuni eventi che lo shadow non arrivava mai a chiudere. Blocchi osservati su 215 tentativi totali: `BLOCKED_PREFLIGHT`=80, `BLOCKED_TF_THROTTLE`=22, `BLOCKED_OPEN_POSITION`=1 (103 bloccati, 112 aperti = 215 ✓). Il 91% degli ingressi (102/112) avviene comunque sulla stessa barra del reclaim (nessun ritardo aggiuntivo); il ritardo da blocco non è la causa principale del gap economico (vedi sotto).

### La causa quantitativa della divergenza economica: SL/TP ancorati al trigger_price, fill reale ancorato al prezzo M15 corrente

Questa è la scoperta centrale del test. Lo shadow assegna al trade virtuale un **fill idealizzato esattamente al trigger_price** (`sh.virtual_entry_price = sh.trigger_price`), indipendentemente da dove si trova realmente il prezzo nel momento del reclaim. Un ordine di mercato reale, invece, riempie al **prezzo corrente**, che — essendo campionato solo ai confini M15 (stessa causa dei ritardi multipli di 900s) — può già essere scivolato ben oltre il trigger_price nella stessa direzione del reversal (il movimento è, per costruzione, quello che la strategia sta cercando di cavalcare).

Misurato sui 111 trade reali risolti: **slippage mediano fill-vs-trigger = +42.6 pip, |slippage|>10 pip nell'86% dei casi (96/111), range -19.8 a +94.3 pip** — enorme rispetto ai 25/100 pip nominali. Poiché SL/TP restano **prezzi assoluti fissi ancorati al trigger_price** (non ricalcolati sul fill reale, per fedeltà alla regola shadow), un fill scivolato **in favore** del trade AVVICINA il prezzo al TP (vincita più piccola quando arriva) e ALLONTANA il prezzo dallo SL (perdita più rara ma quando arriva è su una escursione più lunga) — un effetto confermato dai dati:

| bucket \|slippage\| | n | WR | pnl mediano |
|---|---|---|---|
| 0-10 pip | 15 | 20.0% | -$4.96 |
| 10-30 pip | 30 | 33.3% | -$6.59 |
| 30-60 pip | 31 | 51.6% | +$7.53 |
| 60-200 pip | 35 | 68.6% | +$2.45 |

Il WR sale nettamente con lo slippage (più il prezzo si è già mosso, più il reversal è confermato) — ma la vincita mediana ($7.89) resta **più piccola** della perdita mediana (-$9.08) perché ogni pip di slippage favorevole riduce la distanza residua al TP (fisso al trigger+100) più di quanto allunghi quella dallo SL (fisso al trigger-25, quindi lontano ma raggiungibile su un'inversione). Risultato aggregato: **PF reale (pnl effettivo) = 0.78** — coerente al decimo col PF ufficiale del report MT5 (0.80).

**Conclusione**: la divergenza economica NON è un bug di implementazione né un fallimento dell'architettura causale (che replica lo shadow esattamente, coorte per coorte, tempo per tempo) — è una conseguenza reale e quantificata del fatto che lo shadow, campionando anch'esso solo a cadenza M15, aveva "barato" implicitamente assumendo un fill impossibile (esattamente al trigger, senza scivolamento) che un ordine di mercato reale non può ottenere quando il prezzo è già scappato di decine di pip nell'intervallo fra due controlli da 15 minuti. **Il PASS/FAIL della task dipende dalla parità causale (raggiunta: coorte, disponibilità reclaim, timing tutti allineati) — su questo criterio la task PASSA.** Mentre il PF economico (0.78 reale vs 5.80 shadow) mostra chiaramente che l'edge NON sopravvive al passaggio da simulazione virtuale a esecuzione reale, per un motivo ora completamente spiegato, non residuo/misterioso.

### Bug di telemetria trovato e corretto (zero impatto sui trade)

Il primo run mostrava 180/181 eventi ARMED marcati `[WICKRECLAIM][ABANDONED]` — il controllo di sostituzione livello scattava anche per eventi già `WR_OPENED` (una posizione reale già aperta, gestita autonomamente dal broker col proprio SL/TP, veniva erroneamente rietichettata come "abbandonata" quando il livello sottostante veniva sostituito da una nuova wick). **Nessun impatto sui trade reali o sulle statistiche economiche riportate sopra** (lo stato interno non governa la gestione della posizione) — solo un'inesattezza di log. Corretto: il reset dello stato resta necessario (serve a liberare lo slot per un futuro nuovo livello), ma il log/conteggio `ABANDONED` ora scatta solo per eventi ARMED/RECLAIMED non ancora aperti. Ricompilato: 0 errori. Non ri-eseguito il Fast Smoke (la correzione non altera nessun trade reale già registrato).

### File

`server/research_scripts/wick_reclaim_run5_fastsmoke_real_log_extract.txt` (log filtrato del run reale), `wick_reclaim_real_vs_shadow_run5.csv` (181 righe, dataset di reconciliation), `wick_reclaim_reconcile_run5.py` (script).

## 10. Audit NXS_OpenTrade/preflight/SafeBuy-SafeSell — quali prezzi sono realmente in gioco

Richiesto prima di qualunque modifica a SL/TP. Nessun codice toccato in questa sezione, solo lettura.

**Quale prezzo viene usato oggi per costruire SL/TP**: quello del SEGNALE, pre-calcolato PRIMA dell'invio dell'ordine. Per `WICK_SWEEP_RECLAIM`, `sig.slPrice`/`sig.tpPrice` sono impostati in `NXS_WickReclaim_HasPendingEntry` come `trigger_price ∓ 25/100 pip` — prezzi assoluti fissi, invariati da lì fino all'invio (`NXS_Execution.mqh:560-561`, `NXS_SafeBuy(lots, g_sym, brokerSL, tp, cm)` dove `brokerSL`/`tp` derivano da `sig.slPrice`/`sig.tpPrice` via `NXS_VSL_PrepareEntry`).

**Quale prezzo viene realmente ottenuto dal tester**: `NXS_DoBuy`/`NXS_DoSell` (`NXS_Globals.mqh:348-382`) costruiscono una `MqlTradeRequest` con `req.price = SymbolInfoDouble(sym, SYMBOL_ASK/BID)` **al momento dell'invio** (ordine di mercato, non pending) — il fill effettivo (`res.price`, catturato in `g_lastExec` da `_NXS_CaptureExec`) è quello che viene loggato come `fillPx` in `[RESEARCH][OPEN] entry=...` (`NXS_Execution.mqh:579,604`). **Il campo `entry=` già usato in tutta questa analisi è quindi il fill reale, non un'approssimazione.** Nel tester "ogni tick" questo fill coincide, tick per tick, col prezzo usato per rilevare il reclaim (stesso tick, nessun tempo trascorso) — la discrepanza di 42+ pip misurata NON è slippage di esecuzione broker, è interamente il prezzo che si è mosso fra il momento in cui `trigger_price` fu fissato (all'ARM, potenzialmente barre M15 prima) e il momento in cui il reclaim viene confermato (anch'esso solo a cadenza M15).

**Se possiamo costruire SL/TP usando BID/ASK live al momento dell'entry attempt**: sì, tecnicamente immediato — `_NXS_WickReclaim_ProcessSide` legge già `bid`/`ask` live nello stesso tick in cui viene tentata l'apertura; basterebbe ancorare `outSig.entryRef`/SL/TP a quel prezzo invece che a `st.trigger_price`. Sarebbe quasi-identico al fill reale (stesso tick, nessun ordine pending in mezzo) ma non è testato in questa sessione (vedi sezione 11: il counterfactual mostra che comunque non basterebbe).

**Se per ancorarli all'esatto fill servirebbe una modifica post-fill**: sì, per essere ESATTI al pip. Un ordine di mercato non garantisce il prezzo di fill prima dell'invio (anche se nel tester "ogni tick" lo scarto è tipicamente minimo) — l'unico modo per essere certi al 100% è: (1) inviare l'ordine, (2) leggere `res.price`/`g_lastExec` col fill reale, (3) `PositionModify`/`OrderModify` per impostare SL/TP esattamente su quel prezzo.

**Rischio di una finestra senza SL aprendo prima e modificando dopo**: reale in modalità LIVE (latenza di rete fra invio e modifica — durante quella finestra la posizione è esposta senza stop protettivo, o con uno stop provvisorio potenzialmente sbagliato; un movimento avverso in quella finestra, per quanto breve, non sarebbe capato). Nel tester MT5 l'invio e la modifica avvengono sincroni nello stesso frame (nessuna latenza di rete simulata di default), quindi il rischio pratico in backtest è trascurabile — ma questo NON si estende alla modalità reale/demo, dove servirebbe una mitigazione esplicita (es. uno stop di sicurezza ampio ma sempre presente inviato CON l'ordine, stretto poi via modifica appena noto il fill reale — mai zero protezione).

## 11. Counterfactual FILL_ANCHORED sui 112 trade reali — ipotesi REFUTATA

Richiesto dall'utente dopo la sezione 9: isolare SE l'ancoraggio SL/TP al `trigger_price` (invece che al fill reale) spiega da solo la perdita di edge. **Nessun nuovo ingresso, nessuna nuova detection/reclaim, nessun rilancio MT5** — replay puro sui 111 trade reali risolti (112 aperti, 1 ancora aperto a fine test), stessi timestamp/fill reali, stesso stream di prezzo successivo. Risoluzione del counterfactual: OHLC M15 (`nxs_m15_gold_extended.csv`, stessa serie GOLD usata in tutta questa ricerca) — **downgrade di risoluzione rispetto al tick-level del backtest reale**: l'esito ATTUALE resta quello vero (noto con certezza dal backtest), solo l'esito CONTROFATTUALE è approssimato a barra M15 (7/111 casi con ambiguità stesso-bar, risolti assegnando l'esito alla soglia più vicina all'open della barra — approssimazione dichiarata, non verificata a livello tick).

**Costruzione**: per ogni trade, `SL_cf`/`TP_cf` = `actual_fill ∓ 25/± 100 pip` (stesso identico RR nominale 25/100, ancorato al fill invece che al trigger).

### Classificazione (111 trade)

| Categoria | n |
|---|---|
| LOSS_SAVED | 0 |
| WIN_PRESERVED | 17 |
| WIN_LOST | 36 |
| BOTH_LOSS | 58 |
| BOTH_WIN | 0 |

**Zero LOSS_SAVED**: nessuna delle 58 perdite reali sarebbe diventata una vincita ancorando al fill. Al contrario, **36 vincite reali sarebbero diventate perdite** sotto FILL_ANCHORED.

### Metriche aggregate

| Metrica | TRIGGER_ANCHORED (reale) | FILL_ANCHORED (counterfactual) |
|---|---|---|
| n | 111 | 111 |
| WR | 47.7% | **15.3%** |
| PF (pip, distanza reale) | 0.76 | 0.72 |
| Expectancy | -6.97 pip | -5.86 pip |
| Avg win | 47.5 pip | 100.0 pip (fisso, per costruzione) |
| Avg loss | -56.8 pip | -25.0 pip (fisso, per costruzione) |
| Realized RR | 0.84 | 4.00 |
| Max DD sequenziale | 873.8 pip | 750.0 pip |
| Max losing streak | 4 | 14 |

(Il PF pip-based 0.76 per TRIGGER_ANCHORED è coerente con il PF $ reale 0.78 già stabilito in sezione 9 — cross-check superato.)

### Segmentazione per |slippage trigger→fill|

| bucket | n | ACTUAL WR / PF | FILL_ANCHORED WR / PF |
|---|---|---|---|
| <10 pip | 15 | 20.0% / 0.83 | 13.3% / 0.62 |
| 10-25 pip | 20 | 30.0% / 0.99 | 20.0% / 1.00 |
| 25-50 pip | 28 | 46.4% / 0.90 | 10.7% / 0.48 |
| 50-75 pip | 35 | 57.1% / 0.59 | 17.1% / 0.83 |
| 75-100 pip | 13 | 84.6% / 0.62 | 15.4% / 0.73 |

**Nessuna monotonicità**: né l'ACTUAL né il FILL_ANCHORED degradano in modo monotono con la distanza trigger→fill. Il PF resta ≤1 (o marginale) in QUASI ogni bucket per entrambi i modelli.

### Perché FILL_ANCHORED non salva nessuna perdita (e ne crea di nuove)

Il meccanismo è l'opposto di quanto ipotizzato: il trigger-anchoring **beneficia** dello scivolamento, non ne è vittima. Quando il prezzo ha già percorso 40-90 pip in direzione favorevole prima che il reclaim venga confermato (a cadenza M15), il TP fisso al `trigger+100` è già "quasi raggiunto" — serve solo il resto del movimento, che spesso arriva (WR 84.6% nel bucket 75-100pip). Ancorare invece SL/TP al fill sposta il traguardo un ulteriore, intero 100 pip più lontano PROPRIO nei casi dove il prezzo aveva già confermato di più — vanificando esattamente la conferma che rendeva quei trade i più affidabili. Lo SL, viceversa, diventa più vicino in termini assoluti rispetto a un prezzo già esteso, più incline a un pull-back.

### Decisione (per istruzione esplicita)

**PF resta ≤1 in entrambi i modelli — SL/TP NON toccati.** L'ipotesi "l'anchor spiega da solo la perdita di edge" è **REFUTATA dai dati**: ancorare al fill reale non migliora l'economia (PF 0.72 vs 0.76, marginalmente PEGGIORE) e distrugge selettivamente le vincite più forti (36 WIN_LOST, 0 LOSS_SAVED). La perdita di edge di WICK_SWEEP_RECLAIM rispetto allo shadow non è quindi (solo) un problema di geometria SL/TP — resta da capire se sia strutturale al modello RECLAIM stesso (il vantaggio "virtuale" dello shadow potrebbe dipendere in modo più fondamentale dal fill idealizzato esattamente al trigger, non correggibile spostando semplicemente l'ancora altrove) o se richieda un'indagine diversa. **Nessuna modifica a SL/TP, nessun tuning, nessun tick-reclaim, nessun Fast Structural, nessuna modifica a WICK_SWEEP_REV o al New Bar Gate** — come da istruzione.

### Nota per la roadmap 95/99 (proposta dall'utente, non ancora aperta come task)

Il meccanismo trovato qui (SL/TP calcolati su un prezzo "teorico" di segnale che può risalire a diverse barre prima dell'ingresso reale) non è specifico di WICK_SWEEP_RECLAIM — è potenzialmente presente in qualunque strategia che calcola SL/TP relativi ad `entryRef` nel momento della GENERAZIONE del segnale piuttosto che dell'ESECUZIONE. Un audit generale "SIGNAL PRICE vs EXECUTION PRICE vs RISK GEOMETRY" su tutte le strategie del router è stato proposto dall'utente come possibile voce futura della roadmap — non aperto come task in questa sessione.

### File

`server/research_scripts/wick_reclaim_counterfactual_fill_anchored.py` (script), `wick_reclaim_counterfactual_fill_anchored.csv` (111 righe, tutti i campi richiesti: sweep_id/side/trigger_price/actual_fill/slippage/actual_SL/actual_TP/counterfactual_SL/counterfactual_TP/actual_outcome/counterfactual_outcome/actual_pnl_pips/counterfactual_pnl_pips/categoria).

## 12. Replay tick-level: RECLAIM_TICK vs RECLAIM_LIMIT_RETEST sui 181 sweep canonici

Richiesto per capire se l'edge shadow (a) non era semplicemente eseguibile, (b) è recuperabile con detection più veloce, o (c) è recuperabile aspettando un retest reale del trigger. Nessun nuovo ingresso reale, nessuna nuova detection/ARM — replay puro sugli stessi 181 sweep, stesso `trigger_price`/`level_id`/`side` già noti da `run5_dataset.json`.

### Fonte dei tick e correzione critica trovata durante il lavoro

Dato tick-level non ottenibile senza rilanciare MT5 (esplicitamente fuori scope) → usato il fetcher Dukascopy già esistente nel progetto (`server/export_dukascopy_ticks_mt5.py`, la stessa fonte usata dal motore Python "del sito"). Due problemi trovati e risolti prima di fidarsi di qualunque numero:

1. **Buco di copertura Dukascopy (~53% delle ore feriali mancanti)** al primo fetch massivo (6 fetch paralleli × 12 connessioni ciascuno, quasi certamente rate-limit lato server). Gap-fill dedicato a bassa concorrenza (6 worker): recuperate 486/808 ore, **322/1521 ore feriali (21.2%) restano mancanti** anche dopo il retry. Aggiunto un flag `data_gap_suspect` (gap >20 min immediatamente prima del tick di ingresso trovato) — questi eventi sono **esclusi dalle statistiche aggregate**, non silenziosamente inclusi: 12/173 per MODEL A, 5/109 per MODEL B.
2. **Bug di fuso orario (la scoperta più importante di questa fase)**: i timestamp MT5 in `run5_dataset.json` sono in ora broker, **UTC+3**, non UTC. Verificato direttamente sui tick (non assunto): il `trigger_price` dello sweep_id=7 (4427.26, armato 2026-06-03 16:45:00 ora broker) compare nel flusso tick Dukascopy (UTC) alle 13:44:58 — esattamente 3h00m02s prima. Senza questa correzione, ogni lookup tick per ogni sweep cadeva sulla finestra oraria SBAGLIATA di 3 ore, producendo "slippage" impossibili di 100-400+ pip e persino esiti TP con pnl negativo (matematicamente impossibile) nella prima passata dello script. Corretto applicando `-timedelta(hours=3)` a tutti i timestamp MT5 prima di ogni lookup tick.

### MODEL A — RECLAIM_TICK

Detection/ARM resta M15 (riusata). Dopo l'ARM, osservato ogni tick per il primo attraversamento di `trigger_price` in direzione di reclaim; `virtual_entry` = bid/ask realmente disponibile in quel tick (non il trigger teorico). SL/TP inizialmente ancorati al trigger (stessa baseline comparativa), scostamento reale registrato a parte.

| Metrica | Valore |
|---|---|
| Availability (pulita, esclusi data_gap_suspect) | 161/181 (89.0%) |
| N entries | 161 |
| WR | 16.8% |
| PF | 0.75 |
| Expectancy | -5.52 pip |
| Median MAE | 27.2 pip |
| Median MFE | 16.5 pip |
| Median entry delay | 0 sec (84% degli ingressi hanno delay=0-pochi secondi: il reclaim tick-level avviene spesso quasi subito dopo l'ARM, coerente con lo slippage enorme già osservato nel modello reale — vedi sezione 9/11) |
| Max losing streak | 17 |
| 1a metà periodo | n=80, WR=17.5% |
| 2a metà periodo | n=81, WR=16.0% |
| BUY | n=79, WR=22.8% |
| SELL | n=82, WR=11.0% |

### MODEL B — RECLAIM_LIMIT_RETEST

ARM M15, reclaim confermato secondo la logica M15 attuale (riusato, non ricalcolato). Dopo la conferma, limit virtuale al trigger_price esatto — nessuna tolleranza arbitraria: entra SOLO se il tick stream tocca realmente quel prezzo (BUY: `ask<=trigger`; SELL: `bid>=trigger`, convenzione standard di fill lato opposto del libro).

| Metrica | Valore |
|---|---|
| Availability (pulita) | 104/181 (57.5%) |
| N entries | 104 |
| WR | 14.4% |
| PF | 0.67 |
| Expectancy | -6.97 pip |
| Median MAE | 25.6 pip |
| Median MFE | 8.2 pip |
| Median entry delay (da ARM) | 2735 sec (~46 min) |
| Max losing streak | 16 |
| 1a metà periodo | n=52, WR=15.4% |
| 2a metà periodo | n=52, WR=13.5% |
| BUY | n=58, WR=12.1% |
| SELL | n=46, WR=17.4% |

### Matrice vs BASELINE (WICK_SWEEP_RECLAIM reale, run5)

| Categoria | MODEL A | MODEL B |
|---|---|---|
| BASELINE_LOSS → MODEL_WIN | 3 | 0 |
| BASELINE_LOSS → NO_TRADE | 3 | 4 |
| BASELINE_WIN → MODEL_WIN | 16 | 14 |
| BASELINE_WIN → MODEL_LOSS | 28 | 28 |
| BASELINE_WIN → NO_TRADE | 9 | 11 |
| BOTH_LOSS | 52 | 54 |
| BOTH_NO_TRADE | 8 | 62 |
| NO_TRADE(baseline) → MODEL_SL | 54 | 7 |
| NO_TRADE(baseline) → MODEL_TP | 8 | 1 |

**Nessuno dei due modelli salva sistematicamente le perdite baseline** (solo 3 e 0 `BASELINE_LOSS→MODEL_WIN` su 148 SL reali) — anzi, entrambi **convertono molte vincite baseline in perdite** (28 `BASELINE_WIN→MODEL_LOSS` per entrambi, su appena 30 TP reali totali: quasi tutte le vincite reali diventano perdite sotto entrambi i modelli).

### Risposta alle 3 domande dell'obiettivo

1. **L'edge shadow era semplicemente non eseguibile?** In parte sì: nessuna delle due implementazioni realistiche (tick genuino, retest esatto) riproduce l'economia dello shadow (WR 59.2%/PF 5.80) — entrambe restano sotto PF 1.
2. **Recuperabile con detection più veloce (MODEL A)?** No: PF 0.75, WR 16.8% — peggiore della baseline reale già debole (WR 47.7%/PF 0.78-0.80).
3. **Recuperabile aspettando un retest reale (MODEL B)?** No, anzi peggio: PF 0.67, WR 14.4%, e disponibile solo sul 57.5% dei setup.

**Nessuna variante è stata implementata.** Come da istruzione: solo replay comparativo, nessuna modifica a WICK_SWEEP_REV/RECLAIM, nessun Fast Structural.

### File

`server/research_scripts/wick_reclaim_tick_replay_modelA_modelB.py` (script, include la correzione UTC+3 documentata nel modulo), `wick_reclaim_modelA_tick.csv`, `wick_reclaim_modelB_limitretest.csv` (181 righe ciascuno, tutti i campi richiesti + `data_gap_suspect`/`gap_before_entry_sec`). I CSV grezzi dei tick Dukascopy (~16.5M righe) non sono committati per dimensione — riproducibili con `server/export_dukascopy_ticks_mt5.py` sullo stesso intervallo (2026-06-01→2026-08-30).
