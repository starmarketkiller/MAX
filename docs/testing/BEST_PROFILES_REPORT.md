# Report: profilo migliore per strategia + test portafoglio combinato (04/08)

Eseguito su richiesta esplicita: *"Dobbiamo trovare il profilo migliore per
strategia, poi provare con tutte le strategie attive"*. Segue lo schema NQROS
(vedi `NQROS_v1.0_Manuale_Operativo`, caricato dall'utente lo stesso giorno):
Fase 1 (baseline) + Fase 3 (ottimizzazione SL/TP/gestione) per ogni strategia,
poi un test che le fa girare insieme. **Non è ancora la Fase 4 NQROS
(Out-of-Sample)** — questi numeri sono in-sample, quindi ottimistici per
costruzione. Vedi limiti in fondo.

Motore: `server/backtest.py` (Python, dati Yahoo reali, costi
`COST_PRESETS["retail_standard"]` — spread $2.50 + slippage $0.50, verificati
via ricerca web il 31/07). Script: `server/research_scripts/`.

## Novità motore: `strategy_profiles` (per-strategia)

Prima di questo report, `run_backtest` applicava un SL/TP/breakeven/trailing
**unico e globale** a qualunque strategia scattasse in un test multi-strategia
— quindi "provare tutte le strategie attive insieme, ognuna col suo profilo
migliore" non era possibile. Aggiunto `strategy_profiles={strat_id: {...}}`:
override per-strategia, retrocompatibile (default `None` = comportamento
invariato, 244 test esistenti verdi). Coerente con `NXS_DefaultSLTP` in MQL5,
che è già keyed by `stratName`.

## Fase 1+3: profilo migliore per strategia (29 strategie, TF nativo, MIN_TRADES=15)

| Strategia | TF | Base PF | Opt PF | Trades | WR% | ExpR | MaxDD% | SL | TP | BE | Trail | Note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BB_SQUEEZE | 1d | 1.10 | 2.96 | 5 | 40.0 | 1.008 | 1.14 | 1.0 | 4.0 | 1.5 | 0.0 | **campione<15** |
| IFVG | 4h | 2.06 | 2.28 | 34 | 52.9 | 0.676 | 3.35 | 1.5 | 4.0 | 0.0 | 0.0 | |
| THREE_BAR_DELIVERY_BREAK | 4h | 2.25 | 2.25 | 15 | 53.3 | 0.576 | 2.27 | 1.5 | 3.0 | 0.0 | 0.0 | campione al limite |
| OB_MIT | 1d | 1.35 | 1.75 | 31 | 45.2 | 0.304 | 2.60 | 2.0 | 4.0 | 0.0 | 2.5 | |
| DISP_REBAL | 4h | 1.12 | 1.71 | 9 | 33.3 | 0.553 | 3.49 | 1.0 | 4.0 | 0.0 | 0.0 | **campione<15** |
| OTE_CONT | 1d | 1.34 | 1.59 | 52 | 25.0 | 0.290 | 8.73 | 1.0 | 4.0 | 1.0 | 2.5 | |
| SH_BMS_RTO | 1d | 1.21 | 1.48 | 65 | 41.5 | 0.215 | 5.55 | 2.0 | 4.0 | 0.0 | 2.5 | stessa funzione di SMS_BMS_RTO |
| SMS_BMS_RTO | 1d | 1.21 | 1.48 | 65 | 41.5 | 0.215 | 5.55 | 2.0 | 4.0 | 0.0 | 2.5 | stessa funzione di SH_BMS_RTO |
| SAR | 4h | 1.24 | 1.46 | 77 | 51.9 | 0.229 | 4.80 | 2.0 | 3.0 | 0.0 | 0.0 | |
| BREAKOUT_ACC | 1d | 1.06 | 1.44 | 105 | 41.0 | 0.202 | 5.96 | 2.0 | 4.0 | 1.5 | 2.5 | |
| ICHIMOKU | 4h | 1.05 | 1.41 | 82 | 31.7 | 0.313 | 9.89 | 1.0 | 4.0 | 0.0 | 2.5 | |
| MACD | 4h | 1.20 | 1.37 | 136 | 29.4 | 0.294 | 19.49 | 1.0 | 4.0 | 0.0 | 0.0 | MaxDD alto |
| LONDON_BO | 1d | 1.11 | 1.36 | 137 | 29.9 | 0.304 | 20.42 | 1.0 | 4.0 | 0.0 | 0.0 | stessa funzione di WEEKLY_EXP, MaxDD alto |
| WEEKLY_EXP | 1d | 1.11 | 1.36 | 137 | 29.9 | 0.304 | 20.42 | 1.0 | 4.0 | 0.0 | 0.0 | stessa funzione di LONDON_BO, MaxDD alto |
| EMA_PULLBACK | 4h | 0.91 | 1.28 | 77 | 29.9 | 0.224 | 13.78 | 1.0 | 4.0 | 0.0 | 2.5 | |
| ADX_RSI | 1d | 1.07 | 1.24 | 120 | 42.5 | 0.124 | 7.11 | 2.0 | 4.0 | 0.0 | 2.5 | |
| RSI_DIV | 1h | 0.90 | 1.23 | 64 | 43.8 | 0.135 | 7.17 | 2.0 | 4.0 | 0.0 | 0.0 | |
| TURTLE_SOUP | 1h | 1.01 | 1.22 | 49 | 34.7 | 0.191 | 7.28 | 1.0 | 3.0 | 0.0 | 0.0 | |
| FVG_CONT | 4h | 1.07 | 1.21 | 113 | 27.4 | 0.193 | 17.70 | 1.0 | 4.0 | 0.0 | 0.0 | MaxDD alto |
| TSI | 1d | 1.10 | 1.18 | 186 | 35.5 | 0.131 | 15.31 | 1.5 | 4.0 | 0.0 | 0.0 | MaxDD alto |
| LIQ_VOID | 4h | 1.12 | 1.12 | 135 | 40.0 | 0.085 | 10.93 | 1.5 | 3.0 | 0.0 | 0.0 | |
| FVG_MIT | 1d | 0.91 | 1.10 | 56 | 33.9 | 0.075 | 5.43 | 1.5 | 4.0 | 1.5 | 2.5 | |
| BJORGUM | 4h | 1.06 | 1.09 | 97 | 44.3 | 0.056 | 12.79 | 2.0 | 3.0 | 0.0 | 0.0 | |
| ORDER_BLOCK | 1d | 0.83 | 1.03 | 58 | 41.4 | 0.032 | 7.82 | 1.0 | 2.0 | 0.0 | 0.0 | marginale |
| BOLLINGER | 1d | 0.85 | 1.00 | 71 | 39.4 | 0.004 | 7.69 | 1.5 | 3.0 | 1.0 | 1.5 | pareggio, stessa funzione di RANGE_FADE |
| RANGE_FADE | 1d | 0.85 | 1.00 | 71 | 39.4 | 0.004 | 7.69 | 1.5 | 3.0 | 1.0 | 1.5 | pareggio, stessa funzione di BOLLINGER |
| LIQ_SWEEP | 1d | 0.97 | 0.97 | 101 | 37.6 | -0.010 | 19.45 | 1.5 | 3.0 | 0.0 | 0.0 | negativo anche ottimizzato |
| STRUCT_REACT | 1h | 0.78 | 0.96 | 74 | 25.7 | -0.018 | 17.80 | 1.0 | 4.0 | 0.0 | 0.0 | negativo — coerente col dato MT5 reale (v2.3.1: 85 trade, -102$) |
| MALAYSIAN_SNR | 1d | 0.78 | 0.85 | 189 | 21.7 | -0.134 | 37.53 | 1.0 | 4.0 | 0.0 | 0.0 | negativo anche ottimizzato, MaxDD altissimo |

## Fase "poi provare con tutte le strategie attive insieme"

29 profili → esclusi BB_SQUEEZE e DISP_REBAL (campione <15, profilo non
affidabile) → 27 strategie, ognuna col proprio SL/TP/BE/trailing trovato
sopra, raggruppate per TF (limite del motore: un run lavora su una sola
serie di candele, quindi TF diversi non possono girare in un unico run).

| Gruppo | N strategie | Trade | WinRate | PF | ExpR | MaxDD | NetPnL |
|---|---|---|---|---|---|---|---|
| D1 | 15 | 219 | 36.1% | **1.21** | 0.122 | 16.39% | +2716.89 |
| H4 | 9 | 188 | 31.9% | **1.19** | 0.151 | 23.31% | +2826.63 |
| H1 | 3 | 104 | 37.5% | **1.06** | 0.056 | 9.32% | +461.76 |

Mix di attivazione (gruppo H4): MACD domina il volume (88/188 trade) —
il motore è single-position con priorità d'ordine, quindi le strategie più
"attive" nel gruppo (soglie più larghe) affogano parzialmente il segnale
delle altre. Gruppo D1: ADX_RSI/BREAKOUT_ACC/TSI dominano (54+59+53=166/219).

## Limiti onesti (da leggere prima di agire su questi numeri)

1. **Nessuna validazione Out-of-Sample** (NQROS Fase 4). La griglia SL/TP/BE/
   trailing è stata scelta per PF massimo sugli stessi dati usati per
   valutarla — overfitting in-sample, non ancora dimostrato che regga fuori
   campione. Prossimo passo naturale.
2. **Campione piccolo su molti top performer**: solo IFVG (34) e
   THREE_BAR_DELIVERY_BREAK (15, al limite) hanno un profilo PF>2 con un
   campione minimamente decente. BB_SQUEGE/DISP_REBAL esclusi apposta.
3. **Coppie "collisione"**: SH_BMS_RTO=SMS_BMS_RTO, LONDON_BO=WEEKLY_EXP,
   BOLLINGER=RANGE_FADE condividono la stessa funzione Python — non sono
   conferme indipendenti, sono lo stesso numero duplicato.
4. **Motore single-position**: nei gruppi combinati, solo la prima strategia
   in ordine di lista che scatta in un bar apre il trade. L'EA reale in MT5
   può avere posizioni aperte in parallelo da strategie diverse — quindi
   questi risultati di portafoglio sono un limite inferiore approssimativo
   dell'attività vera, non un equivalente esatto.
5. **MaxDD spesso alto** (>15-20%) anche dove il PF sembra buono (MACD,
   LONDON_BO/WEEKLY_EXP, FVG_CONT, TSI, LIQ_SWEEP, MALAYSIAN_SNR) — da
   valutare se il risk% per trade va abbassato quando più strategie sono
   attive insieme (rischio cumulato, non testato qui: ogni trade usa lo
   stesso risk_pct fisso indipendentemente da quante posizioni sono "attive"
   nel gruppo).
6. Resta un motore di **ricerca/triage su dati Yahoo**, non una validazione
   MT5/TradingView reale — utile per scartare rapidamente i casi deboli
   (MALAYSIAN_SNR, STRUCT_REACT, LIQ_SWEEP restano negativi anche
   ottimizzati), non per certificare i migliori.

## Aggiornamento 04/08: Fase 1 NQROS vera — baseline su TUTTI i timeframe

Il report sopra testava ogni strategia solo sul suo TF "nativo" da profilo
MQL5. Su richiesta ("hai provato anche su vari timeframe?"), rifatto un vero
Fase 1 NQROS: **tutte** le 40 strategie del motore (non solo le 29 con TF
fisso), baseline a parametri di default, su **tutti** i 7 timeframe
disponibili (W1/D1/H4/H1/M30/M15/M5). Script:
`server/research_scripts/multi_tf_baseline.py`. 280 run in 13.4s.

### Miglior TF per strategia (PF più alto tra i TF con ≥15 trade)

| Strategia | TF | PF | Trades | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|---|
| FVG_CONT | W1 | 3.15 | 25 | 64.0 | 0.804 | 2.16 |
| MACD | W1 | 2.94 | 25 | 60.0 | 0.768 | 5.25 |
| THREE_BAR_DELIVERY_BREAK | H4 | 2.25 | 15 | 53.3 | 0.576 | 2.27 |
| IFVG | H4 | 2.06 | 36 | 55.6 | 0.517 | 4.19 |
| LONDON_BO / WEEKLY_EXP | W1 | 1.71 | 27 | 48.1 | 0.398 | 4.09 |
| LIQ_VOID | W1 | 1.69 | 38 | 47.4 | 0.374 | 7.08 |
| AMD_CONT | H4 | 1.62 | 64 | 50.0 | 0.358 | 6.47 |
| ADX_RSI | W1 | 1.57 | 24 | 45.8 | 0.330 | 5.24 |
| SAR | W1 | 1.47 | 18 | 44.4 | 0.280 | 4.26 |
| TSI | W1 | 1.45 | 55 | 43.6 | 0.259 | 9.13 |
| SILVER_BULLET | H4 | 1.37 | 65 | 43.1 | 0.223 | 10.48 |
| OB_MIT | D1 | 1.35 | 32 | 46.9 | 0.226 | 4.41 |
| OTE_CONT | D1 | 1.34 | 43 | 44.2 | 0.210 | 8.55 |
| SH_BMS_RTO / SMS_BMS_RTO | W1 | 1.29 | 17 | 41.2 | 0.188 | 4.56 |
| ... (resto positivo/marginale: FVG_MIT, ORDER_BLOCK, ICHIMOKU, PO3, BJORGUM, TURTLE_SOUP, NY_REVERSAL) | | 0.97–1.24 | | | | |
| LIQ_SWEEP, RSI_DIV, BOLLINGER/RANGE_FADE, MALAYSIAN_SNR, LDN_REVERSAL, STRUCT_REACT, AMD_REVERSAL, JUDAS_SWING | vario | 0.72–0.97 | | | | negativi/deboli su OGNI TF |

CSV completo (40 strategie × 7 TF, tutte le metriche) generato dallo script.

### Scoperte principali

1. **WEEKLY_EXP performa meglio su W1 (1.71) che su D1 (1.11)** dove l'avevo
   testata finora — coerente col nome, correggere il TF_MAP per i prossimi
   batch di ottimizzazione mirata.
2. **AMD_CONT e SILVER_BULLET** (escluse dal batch precedente come "nessun TF
   fisso pulito") mostrano segnale reale su H4 (PF 1.62/64 trade e 1.37/65
   trade) — i gate a sessione (ora GMT letta dal timestamp della candela)
   funzionano anche su bar aggregate H4, non solo su dati intrabar fini.
   Vale la pena approfondirle, non erano da scartare.
3. **JUDAS_SWING, LDN_REVERSAL, AMD_REVERSAL, STRUCT_REACT, MALAYSIAN_SNR**
   restano deboli/negativi su **ogni** timeframe testato — non è un problema
   di TF sbagliato, la logica del segnale stesso non ha edge su questo
   simbolo/periodo.
4. **Attenzione ai risultati W1 (weekly)**: PF alti come 3.15/2.94 girano su
   soli 25 trade in ~10 anni (~1 ogni 4 mesi) — il campione più piccolo di
   tutto il report, quindi il più a rischio dell'esatto errore già
   documentato nella knowledge base (`vault: Lezione Overfitting 3Y` —
   "Sharpe 3.19... poi smentito sui 3 anni"). Trattare come ipotesi da
   validare, non come risultato.
5. **I risultati W1/D1 delle strategie SCALP_* sono da ignorare**: sono
   progettate per momentum intrabar veloce (M15/M5), il PF "decente" che
   mostrano su W1 (es. SCALP_RANGE_BRK 1.51) sta testando una cosa diversa
   dal loro scopo (un incrocio EMA/RSI qualsiasi su barre settimanali, non
   uno scalp) — su M15/M5, il loro vero habitat, sono deboli (0.3–0.9),
   coerente con l'assenza di un vero edge lì.

## Prossimo passo

Out-of-Sample split (NQROS Fase 4) prima di tutto su FVG_CONT/MACD (W1, PF
più alto ma campione minimo) e su IFVG/THREE_BAR_DELIVERY_BREAK (H4) — sono
i profili con PF più alto ma anche il rischio di overfitting più alto. Poi
approfondire AMD_CONT/SILVER_BULLET (scoperta nuova di oggi) e confermare su
TradingView i candidati con campione più solido (SAR, MACD, SH_BMS_RTO/
SMS_BMS_RTO).
