# SILVER_BULLET — approfondimento, protocollo NQROS v3.1

Seconda strategia del ciclo completo (04/08), scelta dall'utente per
riusare l'infrastruttura e le ipotesi già trovate su AMD_CONT (stessa
famiglia: gate a sessione via `_sweep_ext_at`/`_session_amd_series`).
**Riuso dichiarato, non copiato**: ogni ipotesi presa da AMD_CONT è stata
ri-testata da zero su questo segnale, non assunta.

## Fase 1 — Baseline

H4 (unico TF con campione utilizzabile, come per AMD_CONT — stesso limite
strutturale: SILVER_BULLET richiede il gate a killzone orario, che su
W1/D1 non si distingue). Default (SL1.5/TP3.0): **PF 1.37, 65 trade, WR
43.1%, ExpR 0.223, MaxDD 10.48%**.

## Fase 2 — Anatomia (già raccolta in batch precedente, riusata)

- Uscite vincenti: 27 TP + 1 TIME (durata media 22.5 barre)
- Uscite perdenti: 36 SL + 1 TIME (durata media 15.7 barre)
- MFE medio vincite: 2.41R — MAE medio vincite: 0.4R
- Perdite "segnale sbagliato" (MFE<0.3R): 15/37 (41%)
- Perdite "quasi vincenti" (MFE≥0.5R): 15/37 (41%)

Stesso pattern di AMD_CONT (~41-44% perdite "quasi vincenti") — ipotesi
riusata: probabile beneficio da SL/TP più larghi, DA VERIFICARE (non
assumere solo perché ha funzionato sulla strategia gemella).

## Fase 3 — Toggle (un parametro alla volta)

| Toggle | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| *(baseline)* | 1.37 | 65 | 43.1 | 0.223 | 10.48 |
| **htf_filter=True** | **1.62** | 32 | 46.9 | 0.348 | **3.97** |
| confirm_bars=1 | 0.36 | 12 | 16.7 | -0.565 | 6.65 |
| cooldown_bars=3 | 1.32 | 64 | 42.2 | 0.197 | 10.48 |
| loss_cooldown_bars=3 | 1.37 | 65 | 43.1 | 0.223 | 10.48 |

A differenza di AMD_CONT (dove `htf_filter` era ridondante con un filtro
EMA200 già interno), `sig_silver_bullet` non ha alcun filtro di trend
interno — solo ora-killzone + sweep confermato. Qui `htf_filter` aggiunge
valore reale non ridondante. `confirm_bars` di nuovo distruttivo (stesso
motivo di AMD_CONT: segnali "evento", non "stato").

## Fase 4 — Robustezza (GATE) — risultato con una complicazione onesta

| | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| **Senza filtro** — in-sample | 0.87 | 39 | 33.3 | -0.082 | 10.48 |
| **Senza filtro** — out-of-sample | 2.46 | 26 | 57.7 | 0.680 | 2.10 |
| **htf_filter=True** — in-sample | 0.98 | 17 | 35.3 | -0.001 | 3.97 |
| **htf_filter=True** — out-of-sample (costi retail) | 2.98 | 16 | 62.5 | 0.819 | 2.10 |
| **htf_filter=True** — out-of-sample (costi stress) | 2.84 | 16 | 62.5 | 0.789 | 2.18 |

**Non un pass pulito come AMD_CONT.** Il PF esplode dalla prima alla
seconda metà **in ENTRAMBE le config**, con o senza filtro — segno di un
forte cambio di regime di mercato nella seconda metà dello storico H4
disponibile (~2026), non un effetto specifico del filtro. Il filtro
aggiunge comunque un delta incrementale reale (+2.00 vs +1.59 di
miglioramento, e parte da un livello meno negativo: 0.98 vs 0.87) — ma la
lettura onesta è "htf_filter probabilmente aiuta, ma il segnale è confuso
da un effetto di periodo più grande di quanto vorrei". Verdetto: **pass
condizionato**, non pulito. Da ri-controllare quando ci sarà più storico.

## Segmentazione per killzone (ICT: London 10-11 GMT vs NY 14-15 GMT)

Sui 32 trade di `htf_filter=True`:

| Killzone | Trade | WR% | PF | NetPnL |
|---|---|---|---|---|
| London (10-11 GMT) | 17 | 58.8 | **2.52** | 1.183 |
| NY (14-15 GMT) | 15 | 33.3 | **0.95** | -48 |

London killzone chiaramente più forte. Isolarla con `session_filter=
{"LONDON"}` (che nel motore corrisponde esattamente alla finestra 10-11,
dato il gate orario già interno a `sig_silver_bullet`):

PF 2.51, **17 trade**, MaxDD 2.25%. OOS (split 9/9): in-sample PF 1.32,
out-of-sample **PF 6.42**.

### Scartato deliberatamente

PF 6.42 è esattamente il tipo di numero segnalato nella lezione
cross-strategia #4 (da AMD_CONT): spettacolare ma su **9 trade** per metà
— troppo poco per significare qualcosa, indipendentemente da quanto sia
bello il numero. Impilare `htf_filter` + isolamento killzone ha ridotto il
campione da 65 a 17 trade totali: è "spingere il PF" per accumulo di
filtri, non "capire meglio" — la domanda guida del protocollo lo
segnalerebbe esplicitamente. **Non adottato.**

## Config corrente (in attesa di più dati prima di rifinire oltre)

H4, `htf_filter=True`, SL/TP di default (1.5/3.0) — non ancora ottimizzati
in Fase 6. PF 1.62/32 trade, pass condizionato in Fase 4 (confuso da
effetto di periodo). **Non procedere con l'isolamento per killzone finché
il campione non cresce** (più storico, vedi backlog).

## Fase 5 — Money Management

`risk_pct` (stesso standard di AMD_CONT, decisione utente esplicita, non
ridiscussa per ogni strategia): **5%**. Su base `htf_filter=True` (SL1.5/
TP3.0): PF 1.57, return 59.49%, **MaxDD 19.6%** (vs 3.97% a risk_pct=1%).

## Fase 6 — Trade Management

| Parametro | Config | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|---|
| SL | 1.0×ATR | 1.70 | 32 | 40.6 | 0.496 | 20.68 |
| SL | 3.0×ATR | 1.52 | 29 | 62.1 | 0.210 | 11.80 |
| TP | 2.0×ATR | 1.58 | 34 | 58.8 | 0.296 | 15.68 |
| TP | 4.0×ATR | 1.54 | 32 | 43.8 | 0.403 | 15.68 |
| Breakeven | qualunque valore | ≤baseline | — | — | — | — |
| Trailing | 1.0-1.5×ATR | 0.50-0.59 | — | — | — | 29-35 (catastrofico) |
| **Trailing** | **2.5×ATR** | **1.70** | 33 | 48.5 | 0.344 | **10.72** |

A differenza di AMD_CONT, SL/TP largo insieme NON è il vincitore qui (anzi
SL più stretto va leggermente meglio). Ma **stessa lezione cross-strategia
confermata**: breakeven/trailing stretti sono distruttivi (catastrofico a
1.0-1.5×ATR), mentre trailing LARGO (2.5×ATR) è il vincitore netto.

### Combinazione dichiarata: trailing_atr=2.5 + TP=4.0

PF 1.85, 33 trade, WR 48.5%, ExpR 0.447, MaxDD 10.72% — da 1.57 baseline.

### Ri-validazione Out-of-Sample

| | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| In-sample | 1.66 | 17 | 41.2 | 0.388 | 10.72 |
| Out-of-sample (costi retail) | 2.28 | 17 | 58.8 | 0.634 | 10.28 |
| Out-of-sample (costi stress) | 2.17 | 17 | 52.9 | 0.602 | 10.66 |

**Non collassa** — anzi migliora fuori campione, coerente col pattern di
regime già segnalato in Fase 4 (tutta la seconda metà dello storico è
stata più favorevole). Non è la validazione "piatta" e pulita di AMD_CONT:
qui il miglioramento out-of-sample è probabilmente in parte periodo, non
solo il merito della combinazione. Trattarlo come segnale reale ma non
definitivo.

## Fase 7 — Advanced

Saltata, stesso motivo di AMD_CONT (motore a posizione singola).

## Fase 8 — Stability

Griglia attorno a TP=4.0/trailing=2.5:

| TP\\Trail | 2.0 | 2.5 | 3.0 |
|---|---|---|---|
| 3.5 | 1.61 | 1.66 | 1.53 |
| 4.0 | 1.69 | **1.85** | 1.71 |
| 4.5 | 1.72 | 1.83 | 1.63 |

Nessuna scogliera (range 1.53-1.85), ma più "a picco" del plateau largo di
AMD_CONT (1.77-2.06) — il vincitore è chiaramente il migliore dei 9, non
uno dei tanti equivalenti. Trailing=2.5 dà comunque il MaxDD migliore
(10.72%) su ogni valore di TP testato, quello è il pattern robusto.

**Config finale SILVER_BULLET**: H4, risk_pct=5%, `htf_filter=True`,
SL=1.5×ATR (default), TP=4.0×ATR, trailing_atr=2.5×ATR.

## Fase 9 — Analisi finale

### Punteggio /100 (stessa rubrica di AMD_CONT, per confrontabilità)

| Dimensione | Punti | Motivazione |
|---|---|---|
| Edge supera il gate OOS | 20/30 | Non collassa mai, ma **ogni** validazione qui è confusa dallo stesso effetto di periodo (seconda metà storico favorevole) — meno pulito del pass di AMD_CONT. |
| Stabilità parametri (Fase 8) | 12/15 | Nessuna scogliera, ma più "a picco" (il vincitore è chiaramente il migliore, non uno dei tanti equivalenti). |
| Qualità/ampiezza campione | 6/15 | 33 trade, ancora più corto di AMD_CONT (48) — stesso limite di 1.74 anni Yahoo. |
| Comprensione del meccanismo | 13/15 | Diagnosi corretta e non forzata: `htf_filter` verificato come non-ridondante (a differenza di AMD_CONT), killzone London>NY isolata correttamente, MA l'isolamento è stato **scartato** per campione troppo piccolo invece di essere spacciato per un risultato — applicazione diretta della disciplina del protocollo. |
| Fedeltà motore vs vera logica MQL5 | 3/10 | Stesso rischio aperto di AMD_CONT, mai verificato. |
| Generalizzazione (altri TF) | 4/10 | Solo H4, stesso limite strutturale (gate a killzone orario). |
| Gestione rischio operativo | 4/5 | MaxDD 10.72% a risk 5%, ragionevole. |
| **Totale** | **62/100** | |

### Decisione: OSSERVAZIONE (più cauta di AMD_CONT)

Stessa categoria di AMD_CONT ma con un rischio aperto specifico e più
serio: **il possibile effetto di regime/periodo non è stato disaccoppiato
dal merito della strategia/combinazione** — ogni test di robustezza qui ha
mostrato la stessa firma (seconda metà dello storico più forte,
indipendentemente dai parametri). Non si può escludere che gran parte del
risultato positivo sia semplicemente "l'oro ha fatto un movimento favorevole
in quel periodo", non un edge specifico di SILVER_BULLET. **Serve più
storico più di quanto servisse per AMD_CONT** prima di fidarsi. Non
"archivia": la logica del segnale (sweep+killzone ICT) è comprensibile e
il filtro/trailing aggiungono valore reale anche tenendo conto del
confondimento. **Serve dati** (storico più lungo) è la priorità assoluta
qui, più che per qualunque altra strategia vista finora.

## Fase 10 — Memoria

**Scoperta più sorprendente**: `htf_filter`, inutile su AMD_CONT (ridondante
con un filtro interno), è invece un vincitore netto e non ridondante su
SILVER_BULLET — stessa famiglia di strategie, stessa leva, effetto
opposto. Non si può generalizzare "questo toggle funziona per le strategie
a sessione": dipende da cosa la strategia ha già internamente.

**Ipotesi smentita**: "SL/TP largo funziona sempre per questa famiglia" (da
AMD_CONT) — qui SL stretto (1.0×ATR) va leggermente meglio di quello largo.
La lezione vera non è "dai più spazio", è più specifica: **trailing/
breakeven STRETTI sono quasi sempre distruttivi**, quello sì si è ripetuto
identico su entrambe le strategie.

**Lezione nuova per `NQROS_CROSS_STRATEGY_LEARNINGS.md`**: un pass
Out-of-Sample che non collassa non basta se **ogni** configurazione
testata (col filtro, senza il filtro, con/senza combinazione) mostra la
stessa firma di miglioramento nella stessa metà del periodo — è il segnale
di un effetto di regime/periodo che confonde qualunque conclusione sui
parametri specifici, non solo il rischio normale di overfitting che il
gate già intercetta. Va segnalato esplicitamente, non nascosto dietro un
PF che "comunque migliora".
