# WICK_SWEEP_REV — Entry Timing Study

## STATO: WICK_SWEEP ENTRY TIMING STUDY — HYPOTHESIS STRONGLY SUPPORTED, NOT YET EXECUTION-VALIDATED

Non implementato nulla nella strategia canonica. RECLAIM_TRIGGER resta un'ipotesi supportata da dati Python offline (M15) e da una prima corsa MQL5 SHADOW/RESEARCH (tick-level, in corso/da eseguire) — **non ancora una feature da portare in produzione**. Vedi sezione "Prossimi passi" per cosa serve prima di qualunque A/B Fast Structural.

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

## Prossimi passi (nessuno eseguito ancora)

1. Lanciare un test con `InpResearchWickShadow=true` sulla stessa finestra Fast Smoke (H4/GOLD/2026.06.01-08.26, stessi parametri) su Terminal3.
2. Verificare `shadow_sweeps == sweepsDetected` (parità) — se FAIL, investigare PRIMA di guardare qualunque altro numero.
3. Estrarre dal log: % reclaim/non-reclaim, distribuzione tempo al reclaim, penetrazione aggiuntiva pre-reclaim, virtual WR/PF/expectancy, MAE/MFE, BUY/SELL, prima/seconda metà del periodo.
4. Costruire la matrice evento-per-evento BASELINE_IMMEDIATE vs SHADOW_RECLAIM_TRIGGER (via sweep_id + matching temporale con i log `[RESEARCH][OPEN]`/`[RESEARCH][EXIT]` reali), classificando ogni sweep come BASELINE_SL_AVOIDED / BASELINE_TP_PRESERVED / BASELINE_TP_LOST / BOTH_SL / BOTH_TP / RECLAIM_NOT_AVAILABLE.
5. Identificare eventuali casi intrabar che il Python M15 aveva classificato erroneamente (ordine sweep→reclaim→SL/TP non risolvibile da OHLC M15).
6. **Solo se il tick-level conferma un miglioramento significativo sullo stesso campione di sweep reali**: creare una variante sperimentale separata (`WICK_SWEEP_RECLAIM` o un research-only entry mode distinto), preservando IMMEDIATE_FADE come regression fixture — MAI sostituire la strategia canonica direttamente.
7. Solo a quel punto: Fast Structural A/B.

**LIMIT_RETEST resta Candidate #2, non implementato.** Motivazione della priorità a RECLAIM_TRIGGER: campione molto più ampio (1684 vs 358 eventi disponibili sui 3 anni), sacrifica quasi zero TP (1.7% vs 80.3%), non introduce parametri nuovi (usa lo stesso trigger price già calcolato dalla strategia canonica), rischio di overfitting più basso.

**Non toccato**: SL/TP/parametri WICK, Structure/Reaction Engine, altre strategie.
