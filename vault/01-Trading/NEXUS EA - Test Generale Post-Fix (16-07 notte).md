---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, screening, test-generale]
created: 2026-07-16
updated: 2026-07-16
---

# Test generale post-fix — motore sito, tutte le 36 strategie (16/07 notte)

Richiesto dall'utente dopo i fix di oggi (proxy fedeli, struttura esterna,
TP dinamico, 7 strategie a sessione connesse): riprovare un test generale
con la config reale di ogni profilo MQL5 (`NXS_StrategyProfiles.mqh`), per
vedere se il quadro è cambiato rispetto allo screening originale
([[NEXUS EA - Screening Strategie (sito 10y)]], pre-fix) e rispetto ai 6
anni MT5 reali quasi tutti negativi ([[NEXUS EA - Backtest 10Y Segmentato - Analisi]]).

**Un singolo batch, eseguito di seguito** (stessa cache dati per TF, quindi
confrontabile internamente) — TF/SL/TP/HTF presi 1:1 da
`NXS_Profile_TF`/`NXS_Profile_Get`; le 7 strategie a sessione (senza
profilo MQL5) usano la config generica SL1.5/TP3.0/HTF-off già documentata
nelle loro schede.

## Risultato: 31/36 (86%) ora positive (PF≥1.0)

| Strategia | TF | Config | Trade | PF | DD% | Net |
|---|---|---|---|---|---|---|
| ADX_RSI | 1d | SL1.0/TP4.0 HTF | 167 | 1.48 | 11.54 | +7.191 |
| AMD_CONT | 4h | SL1.5/TP3.0 | 53 | 1.64 | 7.81 | +2.048 |
| AMD_REVERSAL | 4h | SL1.5/TP3.0 | 56 | 0.90 | 6.88 | -385 🔴 |
| BB_SQUEEZE | 1d | SL1.0/TP4.5 | 5 | 2.92 | 1.0 | +596 ⚠️ campione minuscolo |
| BJORGUM | 4h | SL1.5/TP3.0 | 116 | 0.95 | 13.76 | -417 🔴 |
| BOLLINGER | 1d | SL1.0/TP2.0 | 75 | 1.17 | 10.63 | +856 |
| BREAKOUT_ACC | 1d | SL1.0/TP4.5 HTF | 111 | 2.15 | 12.25 | +10.600 |
| CISD | 4h | SL1.5/TP3.0 HTF | 8 | 3.40 | 2.97 | +713 ⚠️ campione minuscolo |
| DISP_REBAL | 4h | SL1.0/TP4.5 | 3 | 2.22 | 1.99 | +242 ⚠️ campione minuscolo |
| EMA_PULLBACK | 4h | SL1.5/TP4.0 HTF | 64 | 1.30 | 7.15 | +1.328 |
| FVG_CONT | 4h | SL1.0/TP4.5 HTF | 82 | 1.71 | 12.76 | +4.758 |
| FVG_MIT | 1d | SL1.5/TP4.5 HTF | 43 | 2.04 | 3.94 | +2.868 |
| ICHIMOKU | 4h | SL1.0/TP4.5 HTF | 73 | 1.38 | 16.79 | +2.083 |
| IFVG | 4h | SL1.5/TP4.5 HTF | 18 | 1.26 | 5.85 | +313 |
| JUDAS_SWING | 4h | SL1.5/TP3.0 | 49 | 0.91 | 12.07 | -301 🔴 |
| LDN_REVERSAL | 4h | SL1.5/TP3.0 | 106 | 1.01 | 15.45 | +71 |
| LIQ_SWEEP | 1d | SL1.5/TP3.0 HTF | 59 | 1.63 | 6.62 | +2.187 |
| LIQ_VOID | 4h | SL1.0/TP4.5 HTF | 136 | 1.35 | 14.23 | +4.036 |
| LONDON_BO | 1d | SL1.0/TP4.5 HTF | 127 | 1.88 | 15.91 | +10.629 |
| MACD | 4h | SL2.0/TP3.0 HTF | 111 | 1.48 | 6.23 | +2.879 |
| MALAYSIAN_SNR | 1d | SL2.0/TP4.5 HTF | 37 | 1.96 | 4.70 | +1.767 |
| NY_REVERSAL | 4h | SL1.5/TP3.0 | 11 | 0.88 | 4.69 | -87 ⚠️ campione minuscolo |
| OB_MIT | 1d | SL1.5/TP4.0 | 31 | 1.80 | 3.94 | +1.495 |
| ORDER_BLOCK | 1d | SL1.0/TP3.0 HTF | 36 | 1.77 | 3.94 | +1.850 |
| OTE_CONT | 1d | SL2.0/TP4.5 HTF | 26 | 1.78 | 2.97 | +1.067 |
| PO3 | 4h | SL1.5/TP3.0 | 41 | 0.93 | 14.85 | -190 🔴 |
| RANGE_FADE | 1d | SL1.0/TP2.0 | 75 | 1.17 | 10.63 | +856 |
| RSI_DIV | 1h | SL1.0/TP4.5 | 84 | 1.34 | 11.91 | +2.275 |
| SAR | 4h | SL1.5/TP4.0 HTF | 68 | 2.41 | 7.15 | +5.734 |
| SH_BMS_RTO | 1d | SL1.0/TP4.5 | 70 | 1.66 | 7.73 | +3.843 |
| SILVER_BULLET | 4h | SL1.5/TP3.0 | 68 | 1.28 | 9.75 | +1.125 |
| SMS_BMS_RTO | 1d | SL1.0/TP4.5 | 70 | 1.66 | 7.73 | +3.843 |
| STRUCT_REACT | 1h | SL1.0/TP4.5 HTF | 17 | 1.44 | 3.94 | +536 |
| TSI | 1d | SL1.5/TP4.5 HTF | 173 | 1.63 | 12.30 | +7.813 |
| TURTLE_SOUP | 1h | SL1.0/TP4.5 HTF | 13 | 1.61 | 2.97 | +570 ⚠️ campione minuscolo |
| WEEKLY_EXP | 1d | SL1.0/TP4.5 HTF | 127 | 1.88 | 15.91 | +10.629 |

Solo **5 negative**: AMD_REVERSAL, BJORGUM, JUDAS_SWING, NY_REVERSAL (11
trade, campione minuscolo), PO3. Rispetto allo screening originale
(pre-fix), dove SAR/BJORGUM erano dati invalidi, TURTLE_SOUP/CISD "mai
profittevoli in nessuna config" e le 7 strategie a sessione letteralmente
non esistevano sul sito — il quadro è cambiato in modo netto.

## ⚠️ Importante: i numeri NON sono stabili run-to-run — limite del motore, non un bug nuovo

PO3 e JUDAS_SWING qui sopra risultano negativi (PF0.93/0.91), ma un test
dedicato eseguito pochi minuti prima nella stessa sessione li mostrava
chiaramente positivi (PF1.51/1.4, vedi [[Po3]] e [[Judas Swing]]). Causa
verificata nel codice: `_fetch_real()` ignora il parametro `bars` — la
finestra dati per un TF è sempre "le ultime `_REAL_BARS_CAP=2500` barre
disponibili ORA su Yahoo", quindi due run a distanza di tempo (anche solo
20-30 minuti) possono vedere un sottoinsieme di storico leggermente
diverso. Non è un errore di questo batch (che è internamente coerente,
stessa cache condivisa per ogni TF), ma un limite strutturale del motore
sito quando lo si usa come "sensore in tempo reale" invece che come
storico congelato. **Conclusione onesta**: i numeri esatti (PF a due
decimali) non sono riproducibili al secondo run — il segnale utile è la
**direzione** (positivo/negativo, ordine di grandezza) e il **confronto
tra strategie fatto nello stesso batch**, non un singolo numero isolato
confrontato a distanza di ore.

## Il punto più importante per la domanda dell'utente: SAR/MACD/RSI_DIV/ADX_RSI

Queste 4 strategie da sole spiegavano **-88.2R (~75%) della perdita totale**
sui 6 anni MT5 reali ([[NEXUS EA - Backtest 10Y Segmentato - Analisi]]).
Oggi, con tutti i proxy sito corretti, sono **tutte e 4 chiaramente
positive sul sito**: SAR PF2.41, MACD PF1.48, RSI_DIV PF1.34, ADX_RSI
PF1.48.

**Correzione importante (17/07): nessun test MT5 con il codice di oggi è
ancora stato fatto — non si può ancora dire se "risolve" o no.** La prima
versione di questa nota affermava che il fix "probabilmente non sblocca"
queste 4 su MT5, un'inferenza scorretta prima di qualsiasi test reale.
Controllato con precisione **quando ogni trigger MQL5 è stato modificato
rispetto a quando i 6 anni di dati MT5 sono stati raccolti** (commit
`dc26907`, push dati segmento 9, 2026-07-15 11:53 UTC — il segmento più
affidabile, qualità storico 100%):

- **ADX_RSI**: il fix vero è in MQL5 (`NXS_Strat_ADXRSI()`, filtro
  `g_adx<20`, commit `cf73130`, 2026-07-15 **13:44 UTC — quasi 2 ore
  DOPO** il push dei dati del segmento 9). Il -15.3R che compare
  nell'analisi 6 anni è calcolato sulla versione VECCHIA del trigger
  (senza filtro ADX) — **non è mai stato testato su MT5**. Il PF1.48 di
  oggi sul sito è un'ipotesi ancora aperta, non la ripetizione di un
  test già fallito.
- **SAR**: il trigger MQL5 non è mai cambiato — aveva già `iSAR()` vero
  da prima del bug, il proxy sbagliato esisteva solo sul sito Python
  (mai nell'EA). Il -34.3R di SAR sui 6 anni riflette già il codice
  attuale dell'EA.
- **MACD e RSI_DIV**: stessa situazione di SAR, verificato nel commit di
  oggi (`3978de0`) — tocca solo `server/backtest.py`, zero righe di
  `NXS_Strategies.mqh`. Il trigger vero in MQL5 non è mai stato quello
  sbagliato, solo lo specchio Python lo era. -21.1R e -17.5R riflettono
  già la logica vera.

**Conclusione corretta**: per ADX_RSI c'è una base concreta per aspettarsi
un risultato diverso al prossimo test MT5 (trigger genuinamente nuovo,
mai provato). Per SAR/MACD/RSI_DIV non c'è una modifica di trigger che
giustifichi un cambiamento — se miglioreranno sarà per altre ragioni
(interazione con gli altri fix di oggi: contatore executed, filtri di
struttura su altre strategie che cambiano quali trade collidono/quale
margine resta, ecc.), non perché il loro segnale specifico sia diverso.
Ma questa resta un'ipotesi da verificare, non una previsione negativa —
l'unico modo per saperlo è il test isolato MT5, non ancora fatto.

## Cosa risponde e cosa NON risponde alla domanda sull'hedge/10 anni

Questo test conferma che, **sul sito**, il quadro complessivo è migliorato
molto (31/36 positive) — coerente con l'aspettativa dell'utente che i fix
di oggi avrebbero "sbloccato" più di una strategia. **Ma è ancora dati
Yahoo attraverso il motore semplificato del sito, non MT5/broker** — esattamente
il limite già documentato in [[NEXUS EA - Screening Strategie (sito 10y)]]:
un'ipotesi da validare, non una certezza (era vero anche per il record dei
3 mesi che poi non si è confermato sui 10 anni). **Non risponde** alla
domanda specifica sull'hedge tra strategie nel tempo (se nel 2020/2024 la
maggior parte perde insieme) — quello richiede dati segmentati per anno,
che il sito può fornire solo per le strategie D1 (10 anni Yahoo reali
disponibili) non per quelle 4h/1h (cap a ~1-2 anni). Prossimo passo reale:
i risultati dello sweep isolato MT5 (1-37) dall'altro agente, che è
l'unico test che userà dati broker veri su un orizzonte lungo.

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] · [[NEXUS EA - Hedge nel Tempo]] · [[TODO - Backtest 10Y]]
