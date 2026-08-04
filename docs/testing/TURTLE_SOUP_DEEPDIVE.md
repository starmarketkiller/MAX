# TURTLE_SOUP — approfondimento completo, protocollo NQROS v3.1

Terza strategia del ciclo completo (04/08). Unica sopravvissuta con un
edge reale tra le 6 corrette nel giro di verifica fedeltà (LONDON_BO/
WEEKLY_EXP, IFVG, BJORGUM, TURTLE_SOUP, FVG_MIT, ICHIMOKU) — qui la
fedeltà è già stata verificata PRIMA di iniziare il deep-dive (lezione
#11 applicata sul serio, non dopo come per AMD_CONT/SILVER_BULLET).

## Fase 1 — Baseline (già fatta durante la verifica di fedeltà)

H4: PF 1.15, 86 trade, WR 41.9%, MaxDD 12.45% (SL1.5/TP3.0 — ma vedi nota
sotto, per questa strategia SL/TP non è più un multiplo ATR libero).
H1/D1/W1 tutti negativi o pessimi (MaxDD 49% su D1) — solo H4 utilizzabile.

## Fase 2 — Anatomia

- Uscite vincenti: 33 TP + 3 TIME
- Uscite perdenti: 50 SL
- MFE medio vincite: 2.31R — MAE medio vincite: 0.53R
- Perdite "segnale sbagliato" (MFE<0.3R): 18/50 (36%)
- Perdite "quasi vincenti" (MFE≥0.5R): 24/50 (48%)

Stesso pattern di AMD_CONT/SILVER_BULLET — quasi metà delle perdite erano
trade in movimento nella direzione giusta prima di girare.

## Fase 3 — Toggle

| Toggle | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| *(baseline)* | 1.15 | 86 | 41.9 | 0.108 | 12.45 |
| htf_filter=True | 0.74 | 47 | 31.9 | -0.186 | 10.55 |
| confirm_bars=1 | 0.43 | 5 | 20.0 | -0.490 | 4.24 |
| cooldown_bars=2 | 1.12 | 85 | 41.2 | 0.088 | 16.86 |
| cooldown_bars=3 | 1.22 | 81 | 43.2 | 0.149 | 15.36 |
| **cooldown_bars=5** | **1.24** | 76 | 43.4 | **0.160** | 12.34 |
| cooldown_bars=8 | 1.11 | 71 | 40.8 | 0.083 | 11.93 |

`htf_filter`/`confirm_bars` peggiorano (stesso schema già visto altrove).
`cooldown_bars=5` vincitore netto e pulito: PF/ExpR migliorano, MaxDD
invariato (non un compromesso, un miglioramento puro).

## Fase 4 — Robustezza (GATE)

| | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| cooldown_bars=5 — in-sample | 0.84 | 49 | 34.7 | -0.116 | 12.34 |
| cooldown_bars=5 — out-of-sample (retail) | 2.09 | 27 | 55.6 | 0.549 | 3.22 |
| cooldown_bars=5 — out-of-sample (stress) | 1.95 | 27 | 55.6 | 0.503 | 3.37 |
| baseline (no cooldown) — in-sample | 0.79 | 54 | 33.3 | -0.160 | 12.45 |
| baseline (no cooldown) — out-of-sample | 1.96 | 33 | 54.5 | 0.510 | 5.22 |

**Stesso confondimento di regime già documentato su SILVER_BULLET
(lezione #10)**: sia con che senza cooldown il PF esplode nella stessa
metà del periodo (0.79→1.96 senza, 0.84→2.09 con) — non un effetto
specifico del parametro. Il cooldown aggiunge comunque un contributo
incrementale reale (PF migliore, MaxDD quasi dimezzato: 3.22% vs 5.22%).
Pass condizionato, come SILVER_BULLET, non pulito come AMD_CONT.

## Fase 5 — Money Management

`risk_pct=5%` (standard già fissato): **MaxDD 51.49%** — molto più severo
di AMD_CONT (28.96%) o SILVER_BULLET (19.6%), perché la baseline di
TURTLE_SOUP ha un profilo rischio/rendimento meno favorevole a parità di
rischio nominale. Segnalato esplicitamente prima di procedere.

| risk_pct | PF | Return% | MaxDD% |
|---|---|---|---|
| 1.0% | 1.24 | 11.96 | 12.34 |
| 2.0% | 1.23 | 23.28 | 23.65 |
| 3.0% | 1.22 | 33.52 | 33.94 |
| 5.0% | 1.19 | 49.22 | **51.49** |

## Fase 6 — Trade Management

**SL/TP width sono no-op**: da quando TURTLE_SOUP ha una formula SL/TP
strutturale propria (`_turtle_soup_sl_tp`, aggiunta durante la verifica di
fedeltà — SL dal livello di sweep, TP a 2.0×R della distanza di rischio
reale), i parametri `atr_sl`/`atr_tp` passati al motore non hanno più
alcun effetto (bypassati da `STRATEGY_SLTP_ALWAYS`) — verificato: stesso
identico risultato (PF1.19/76tr) su ogni valore di SL/TP testato. Non è
un bug, è la conseguenza corretta della fedeltà: nell'EA reale quel
parametro semplicemente non è regolabile per questa strategia.

Breakeven/trailing: **catastrofici a ogni valore testato**, nessuno batte
la baseline (PF crolla fino a 0.13 con breakeven_r=0.5, MaxDD fino
all'83%). Stesso schema di AMD_CONT/SILVER_BULLET (stringere la gestione
= distruggere l'edge), qui ancora più marcato.

**Nessun miglioramento trovato oltre la Fase 5** — config finale resta
quella della Fase 3+5: `cooldown_bars=5`, `risk_pct=5%`, SL/TP
strutturale (fisso).

## Fase 7 — Advanced

Saltata, stesso motivo delle altre (motore a posizione singola).

## Fase 8 — Stability

| cooldown_bars | PF | Trade | WR% | MaxDD% |
|---|---|---|---|---|
| 3 | 1.18 | 81 | 43.2 | 59.46 |
| 4 | 1.29 | 78 | 44.9 | 54.32 |
| **5** | **1.19** | 76 | 43.4 | 51.49 |
| 6 | 1.07 | 75 | 41.3 | 51.38 |
| 7 | 1.01 | 75 | 40.0 | 52.64 |

Nessuna scogliera (PF 1.01–1.29), config confermata robusta — non un
picco isolato. Nota: MaxDD resta alto (51-59%) su tutto il range, non
solo al valore scelto — è la Fase 5 (risk_pct=5%) a determinarlo, non
`cooldown_bars`.

## Fase 9 — Analisi finale

### Punteggio /100

| Dimensione | Punti | Motivazione |
|---|---|---|
| Edge supera il gate OOS | 20/30 | Pass condizionato, stesso confondimento di regime di SILVER_BULLET — non pulito come AMD_CONT. |
| Stabilità parametri (Fase 8) | 13/15 | Nessuna scogliera, plateau ragionevole. |
| Qualità/ampiezza campione | 8/15 | 76-86 trade, stesso limite di 1.74 anni di storico H4. |
| Comprensione del meccanismo | 12/15 | Diagnosi corretta (Fase 2), cooldown_bars trovato e validato con lo stesso rigore. |
| Fedeltà motore vs vera logica MQL5 | **8/10** | **Verificata PRIMA del deep-dive** (non dopo, lezione #11 applicata) — sweep esteso PDH/PDL fedele, unica riserva: `_sweep_ext_at` manca ancora EQH/EQL e livelli settimanali/mensili (semplificazione già documentata altrove nel motore). |
| Generalizzazione (altri TF) | 4/10 | Solo H4 utilizzabile, resto negativo/pessimo. |
| Gestione rischio operativo | **2/5** | **MaxDD 51.49% a risk 5% è severo** — il peggiore delle tre strategie approfondite finora. Va riconsiderato il risk_pct per questa strategia specificamente. |
| **Totale** | **67/100** | |

### Decisione: OSSERVAZIONE, con un avviso specifico sul rischio

Miglior punteggio di fedeltà finora (verificata da subito, non scoperta
dopo) ma il peggior profilo di rischio operativo delle tre strategie
approfondite. **Prima di "mantieni"**: (1) riconsiderare `risk_pct` per
questa strategia — 51% di drawdown a 5% è difficilmente accettabile anche
isolatamente, figuriamoci in un portafoglio; (2) stesso bisogno di più
storico per disaccoppiare l'edge dal confondimento di regime già visto su
SILVER_BULLET; (3) completare la fedeltà di `_sweep_ext_at` (EQH/EQL,
livelli settimanali/mensili) prima di considerarla definitiva.

## Fase 10 — Memoria

**Lezione nuova per `NQROS_CROSS_STRATEGY_LEARNINGS.md`**: quando una
strategia ha una formula SL/TP strutturale propria (`STRATEGY_SLTP_
ALWAYS`), la Fase 6 "SL/TP width" diventa un no-op — verificarlo PRIMA di
perdere tempo a testare `atr_sl`/`atr_tp` (qui identici su ogni valore).
Solo breakeven/trailing restano testabili per quelle strategie.

**Conferma della lezione #10** (confondimento di regime): il pattern
"PF esplode nella stessa metà indipendentemente dal parametro" si è
ripetuto identico su TURTLE_SOUP — probabilmente un limite dell'intero
campione H4 di 1.74 anni usato per OGNI strategia in questa sessione, non
una caratteristica specifica di una singola strategia. Da tenere a mente
per ogni prossimo deep-dive su questo stesso storico.
