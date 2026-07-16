---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, gestione, mfe-mae, sar, macd, rsi-div, adx-rsi]
created: 2026-07-17
updated: 2026-07-17
---

# Gestione d'uscita: analisi MFE/MAE su SAR/MACD/RSI_DIV/ADX_RSI (17/07)

Richiesta dell'utente: questi 4 indicatori (trend/momentum) raramente
sbagliano la direzione — l'osservazione empirica è che "la seguono" la
maggior parte delle volte. Se è vero, il -88.2R sui 6 anni MT5 non è un
problema di **segnale** ma di **come gestiamo il trade dopo l'ingresso**
(SL troppo stretto, TP che taglia il movimento troppo presto). Testato
direttamente invece di continuare a ipotizzare.

## Diagnostica: MFE/MAE indipendente da SL/TP attuali

Per ogni segnale delle 4 strategie (config reale del profilo, motore
sito), seguito il prezzo fino a 40 barre avanti e misurato il massimo
movimento a favore (MFE) e contro (MAE) in multipli di R —
**indipendentemente** da dove sta oggi lo SL/TP:

| Strategia | n segnali | MFE medio | MAE medio | ≥1R favorevole | ≥2R | ≥3R | SL attuale toccato |
|---|---|---|---|---|---|---|---|
| SAR | 135 | 2.74R | 2.19R | 72.6% | 51.9% | 36.3% | 66.7% |
| MACD | 1000 | 2.40R | 1.63R | 70.5% | 48.2% | 25.9% | 60.0% |
| RSI_DIV | 182 | 3.54R | 3.14R | 88.5% | 67.0% | 47.3% | 76.9% |
| ADX_RSI | 947 | 4.52R | 3.53R | 85.6% | 68.6% | 52.0% | 77.3% |

**Confermato**: la direzione è azzeccata la maggior parte delle volte
(70-88% raggiunge almeno 1R a favore in 40 barre) — ma lo SL attuale
viene comunque toccato nel 60-77% dei casi. Non è un conflitto: il
prezzo spesso va nella direzione giusta MA con abbastanza rumore/ritorno
(MAE quasi uguale a MFE) da toccare lo SL prima o dopo aver reso il
massimo. Per MACD e ADX_RSI in particolare, l'MFE medio (2.40R/4.52R)
supera il TP attuale (3.0/4.0) — il TP stretto taglia sistematicamente
un movimento che il trigger aveva già previsto correttamente.

## Test di gestione alternativa (SL più largo, TP molto largo, breakeven, trailing)

Sweep su griglia (SL 1×/1.25×/1.5×/2× il valore profilo, TP fino a 12×
ATR, breakeven 0-1.5R, trailing 0/1.5/2.5×ATR), stessa config
TF/HTF del profilo reale, filtrato a campioni ≥15 trade:

| Strategia | Config attuale | PF/DD/net attuali | Config migliore trovata | PF/DD/net |
|---|---|---|---|---|
| **MACD** | SL2.0/TP3.0/HTF | 1.48 / 6.23% / +2.879 | **SL2.0/TP8.0/BE1.0** | **2.05 / 5.85% / +3.643** |
| **ADX_RSI** | SL1.0/TP4.0/HTF | 1.48 / 11.54% / +7.191 | **SL1.0/TP10.0/BE1.5** | **1.97 / 12.48% / +8.991** |
| RSI_DIV | SL1.0/TP4.5 | 1.34 / 11.91% / +2.275 | SL1.0/TP10.0 | 1.39 / 11.74% / +2.436 (miglioramento marginale) |
| SAR | SL1.5/TP4.0/HTF | 2.41 / 7.15% / +5.734 | SL1.5/TP4.0/BE1.5 | 2.57 / 7.15% / +5.440 (PF su, net giù — non chiaro) |

**Il trailing non ha aiutato in nessun caso** (in ogni config migliore
`trail=0`) — sorprendente visto che altre famiglie (SMC/trend) nel
motore lo usano con successo. Qui la leva è **TP molto più largo +
breakeven**, non un trailing stretto: coerente con l'MFE alto ma rumoroso
(MAE quasi = MFE) — un trailing stretto avrebbe chiuso troppo presto
proprio a causa del rumore, un TP largo con breakeven lascia lo spazio
per il movimento vero senza rischiare il capitale una volta partiti.

## Applicato

**MACD e ADX_RSI**: miglioramento netto su ogni metrica (PF, DD, net) —
applicato in `NXS_StrategyProfiles.mqh` (TP e beR aggiornati). Il
campione si riduce (~25-35% in meno di trade, TP più largo = più trade
che finiscono a TIME invece che TP/SL) ma il trade-off è chiaramente a
favore. **Non applicato per SAR e RSI_DIV**: i miglioramenti trovati sono
marginali o ambigui (PF su ma net giù per SAR, guadagno minimo per
RSI_DIV) — non abbastanza per giustificare un cambio di config data
[[NEXUS EA - Principi]] #4 (campione/beneficio minimo non è una
scoperta). Restano con la config attuale.

## Test 2 (17/07 sera): "serve conferma prima di entrare" + "rientro dopo stop protetto"

Due idee dell'utente, entrambe tradotte in leve nuove nel motore
(riusabili su qualunque delle 36 strategie, non solo queste 4):

- **`confirm_bars`**: il segnale deve restare valido per N barre
  consecutive PRIMA di quella corrente (stessa direzione) prima di
  essere preso — filtra un cross che dura un solo tick e si inverte
  subito.
- **`loss_cooldown_bars`**: cooldown applicato SOLO dopo un'uscita in
  **perdita vera** (pnl<0) — un'uscita a breakeven/trailing (pnl≥0) non
  blocca il rientro immediato. Approssima l'idea "se lo stop era solo
  protettivo e il prezzo ritraccia di nuovo nella direzione giusta,
  vogliamo poter rientrare subito; se era una vera perdita, aspettiamo".

Sweep (confirm_bars 0-3 × loss_cooldown_bars 0/3/5/10) sopra la config
già migliorata (TP largo+BE dove applicato):

| Strategia | Baseline (TP/BE già applicato) | Migliore trovata | Nota |
|---|---|---|---|
| MACD | PF2.05 / DD5.85% / +3.643 (72 trade) | confirm=0, loss_cd=10 → PF2.18 / DD6.04% / **+3.797** (69 trade) | miglioramento piccolo ma pulito (+4% net) |
| ADX_RSI | PF1.97 / DD12.48% / +8.991 (129 trade) | confirm=0, loss_cd=10 → PF2.17 / **DD10.47%** / +7.078 (94 trade) | PF/DD migliorano, **net peggiora** (-21%, 27% meno trade) — trade-off non pulito |
| SAR | PF2.41 / DD7.15% / +5.734 | nessuna combinazione batte la baseline | confirm/loss-cooldown non aiutano qui |
| RSI_DIV | PF1.34 / DD11.91% / +2.275 | confirm=2, loss_cd=10 → PF2.23 / DD2.97% / +1.270 | **campione crolla a 15 trade** — esattamente al limite minimo, non affidabile ([[NEXUS EA - Principi]] #4) |

**Risultato onesto, non quello sperato**: `confirm_bars` (l'ipotesi
"serve una conferma prima di eseguire") **non ha aiutato in nessun caso
con un campione decente** — in ogni caso tranne RSI_DIV la miglior
combo trovata ha `confirm=0`. L'unica leva con un effetto reale è
`loss_cooldown_bars=10` (evitare rientri rapidi SOLO dopo una perdita
vera), ma il beneficio è piccolo per MACD e ambiguo per ADX_RSI (PF/DD
meglio, meno soldi totali). **Nessuna delle due modifiche applicata al
profilo per ora** — nessuna supera la soglia di un miglioramento chiaro
su tutte le metriche insieme, a differenza del fix TP/BE sopra.

**Nota di fedeltà importante**: questo `confirm_bars`/`loss_cooldown_bars`
è un'approssimazione grezza dell'idea originale dell'utente ("dopo un
BE/trailing, se il prezzo ritraccia di nuovo nella zona del MACD,
rientriamo a favore di quella direzione") — qui si è testato solo *se
permettere* un rientro rapido dopo un'uscita protetta, non *se il prezzo
è davvero tornato a ritestare la zona del segnale* (es. un pullback
sulla EMA/signal-line) prima di rientrare. Costruire quella versione più
precisa (un vero motore di re-entry basato su retest, non solo
un'assenza di cooldown) è il prossimo passo naturale se si vuole
approfondire questa pista, non ancora fatto.

`confirm_bars`/`loss_cooldown_bars` restano comunque disponibili come
leve generiche in `run_backtest()` per testare altre strategie deboli in
futuro (mandato esplicito dell'utente: provare ogni combinazione di
gestione possibile, non solo su queste 4).

## Cosa NON risponde ancora

Questo è di nuovo il motore **sito** (dati Yahoo, nessuna simulazione di
spread/sizing/gate) — lo stesso limite già segnalato per il test generale
di ieri. Il fatto che MACD/ADX_RSI migliorino qui non prova che
miglioreranno anche su MT5: è un'ipotesi di gestione più forte di prima
(supportata da un'analisi diretta della direzione, non solo da un altro
sweep SL/TP alla cieca), ma resta da validare — soprattutto perché un TP
più largo espone il trade più a lungo agli stessi problemi di esecuzione
(spread/gate) già sospettati come causa della divergenza sito/MT5.
**Prossimo passo**: includere questi nuovi valori di profilo nello sweep
isolato MT5 quando arriva il turno di ADX_RSI (selector) e MACD.

## Collegamenti
[[MOC - Trading]] · [[Macd]] · [[Adx Rsi]] · [[Sar]] · [[Rsi Div]] · [[NEXUS EA - Test Generale Post-Fix (16-07 notte)]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Principi]]
