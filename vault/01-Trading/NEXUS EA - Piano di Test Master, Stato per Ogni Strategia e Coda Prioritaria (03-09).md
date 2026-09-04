---
type: reference
domain: trading
status: active
tags: [trading, nexus-ea, piano-test, master-queue, riferimento]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — Piano di test master: stato per ogni strategia e coda prioritaria (03/09)

## Perché questa nota

Risposta diretta alla richiesta originale ("crea un piano di test per
trovare la migliore configurazione di ogni strategia"). Il metodo
(§P2.4/P4.1 [[NEXUS EA - MASTER ROADMAP v3]]) esiste già ed è
dettagliato; quello che mancava era **un unico posto che dica, per
ognuna delle 46 strategie registrate, a che punto è** — sparso finora
su ~30 note. Questa nota consolida e resta il punto di riferimento da
aggiornare ad ogni ciclo, invece di ripartire da zero ogni sessione.

## Il quadro reale in 4 categorie

### 1. Validate su motore Python, MAI verificate sul vero MT5 (21)

La [[NEXUS EA - Tabella Master Strategie Verificate (24-08)]] (24-25/08)
ha già trovato una configurazione vincente per 23 strategie sul motore
Python del sito (PF 1.3-3.2, walk-forward verificato, BUY/SELL
separato, filtro Elliott multi-TF). **Solo 2 di queste 23 sono state
portate in MQL5** (SWING_FALSEBREAK, Z_SCORE_BREAKOUT) — le altre 21
hanno una ricetta pronta ma **zero conferma che il motore MT5 reale si
comporti allo stesso modo** (regola Master Roadmap §2.5: "non usare il
nome della strategia come prova che il codice implementi davvero quella
logica" — qui vale anche per la logica del filtro/uscita, non solo il
trigger).

**Coda prioritaria per portare in MQL5 + validare** (ordine per PF
Python, ma vedi nota sotto su cosa contro-verificare prima):

| # | Strategia | PF Python (m1/m2) | Filtro chiave | In MQL5? |
|---|---|---|---|---|
| 1 | FVG_MIT | 3.24 (1.57/5.06) | D1-align+trailing+Elliott | No |
| 2 | ADX_RSI | 2.62 (2.57/2.66) | trailing+Elliott, BUY-only | ✅ **Confermata sul vero MT5 (04/09)**: nudo PF2.04, net+$1676/3anni, BUY domina (conferma diretta). Vedi [[NEXUS EA - ADX_RSI D1 Confermata Positiva sul Vero MT5, BUY Domina (04-09)]]. Trailing+Elliott ancora da aggiungere |
| 3 | STRUCT_REACT | 2.65 (2.82/2.48) | nessun Elliott (peggiora qui), BUY-only | No |
| 4 | FVG_CONT_V2 | 2.40 (2.10/2.93) | trailing+Elliott, BUY-only | No |
| 5 | SAR_FLIP | 2.31 (1.54/3.49) | trailing+Elliott, BUY-only | No |
| 6 | TSI | 2.25 (2.04/2.46) | Elliott, BUY-only, no trailing | No |
| 7 | MALAYSIAN_SNR_BREAKOUT | 2.14 (1.81/2.51) | Elliott, BUY-only | No |
| 8 | OTE_CONT | 2.14 (2.16/2.12) | D1-align+Elliott | No |
| 9 | EMA_PULLBACK | 2.13 (1.44/2.83) | D1-align+trailing+Elliott | Parziale (nuda già confermata robusta oggi/estate, non questa ricetta specifica) |
| 10 | ML_ADAPTIVE_SUPERTREND | 2.13 (1.44/3.13) | Elliott, BUY-only | No (script esterno, mai portato) |
| 11 | SAR_ADX20 | 1.81 (1.28/2.44) | trailing+Elliott, BUY-only | No |
| 12 | AMD_CONT | 1.80 (1.43/2.25) | Elliott, BUY-only | No |
| 13 | MACD | 1.84 (1.53/2.17) | trailing+Elliott | ✅ **Confermata sul vero MT5 (04/09)**: nudo H4 PF1.53, net+$1975/3anni. BUY domina (129 trade, WR37.2%, +$2273) SELL rumore (70 trade, +$162). Vedi [[NEXUS EA - MACD H4 Confermata Positiva, Terza Conferma BUY-Dominante (04-09)]] |
| 14 | LONDON_BO | 1.83 (1.38/2.32) | trailing, BUY-only | No |
| 15 | SAR | 1.87 (1.44/2.36) | trailing+Elliott, BUY-only | **Sì, ma ricetta diversa** — la config live confermata oggi (candle-align H4, PF1.37-1.57) è un'altra scoperta, non questa. Da riconciliare, non assumere che siano la stessa cosa |
| 16 | FVG_CONT | 1.78 (1.66/1.91) | trailing+Elliott, BUY-only | No |
| 17 | LIQ_SWEEP | 1.73 (invariato) | ER+floor, BUY-only | No |
| 18 | DARVAS_BOX | 1.65 (1.43/1.89) | Elliott, BUY-only | No |
| 19 | DONCHIAN_TURTLE | 1.63 (1.45/1.83) | Elliott, BUY-only | No — **correlata 99.7% con DARVAS_BOX, tenerne solo una in portafoglio** |
| 20 | BOLLINGER (=RANGE_FADE) | 1.95 (1.91/1.99) | Elliott, BUY-only, **4h non M5** | No — ⚠️ **diversa dal test M5 di oggi** (negativo, PF0.83) — TF e filtro completamente diversi, non lo stesso esperimento |
| 21 | RSI_DIV | 1.96 (2.21/1.73) | Elliott, BUY-only | No |
| 22 | BREAKOUT_ACC | 1.38 (1.24/1.54) | Elliott, BUY-only | No — ⚠️ diverso dal test scalp M15 del 02/09 (negativo) — TF diverso |
| 23 | LDN_REVERSAL | 1.36 (1.36/1.37) | stop strutturale+Elliott | No |

⚠️ **Nota critica**: BOLLINGER e BREAKOUT_ACC compaiono qui con PF
positivi **su 4h/D1**, ma i test MT5 di oggi/02-09 erano su **M15/M5**
— non sono lo stesso esperimento, non si contraddicono. Prima di
concludere "BOLLINGER non funziona", andrebbe verificata QUESTA
ricetta (4h, BUY-only, filtro Elliott) sul vero MT5 — cosa mai fatta.

**TURTLE_SOUP** (PF1.19, 3/5 finestre) e **ICHIMOKU** (inconcludente)
restano provvisorie anche sul lato Python — bassa priorità.

### 2. Validate sul vero MT5, chiuse con esito positivo (2)

| Strategia | Stato | Config | Fonte |
|---|---|---|---|
| SAR | ✅ Confermata | Lotto naturale, candle-align H4 | [[NEXUS EA - Sintesi Sessione Maratona SAR-EMA_PULLBACK-Scalp-RegimeVeto (01-02-09)]] |
| EMA_PULLBACK | ✅ Confermata robusta | Nuda, nessun filtro trova un miglioramento | Idem |

### 3. Testate sul vero MT5 oggi, chiuse con esito negativo (2)

| Strategia | Stato | Perché | Fonte |
|---|---|---|---|
| PIVOT_WICK | ❌ Chiusa (fermata dall'utente) | 9 varianti isolate, solo 1 migliora la qualità (ancora sotto pareggio) | [[NEXUS EA - PIVOT_WICK step2 e OneShotLevel Analizzati, Nessun Fix (03-09)]] |
| BOLLINGER M5 scalp (+RSI+candela) | ❌ Chiusa | Nessun filtro isolato sposta il win rate | [[NEXUS EA - BOLLINGER Filtro RSI e Candela Testati, Nessuno Alza il Win Rate (03-09)]] |

### 4. Mai testate né su Python né su MT5 (~20)

Dal registro (`NXS_StrategyRegistry.mqh`), tutte quelle non citate
sopra: 3COMMAS_BOT, AMD_REVERSAL, BAR_UPDN (chiusa negativa il 02/09,
va spostata in categoria 3), DISP_REBAL, ELLIOTT, FVG_MIT_WINDOW,
ICHIMOKU_HULL_MACD, IFVG, JUDAS_SWING, LDN_REVERSAL (variante MQL5,
diversa dalla riga Python sopra), LIQ_VOID, MACD_SMA200, NY_REVERSAL,
OB_MIT, ORDER_BLOCK, PMAX, PO3, RANGE_FADE, RSI_DIV_PINE, SH_BMS_RTO,
SILVER_BULLET, SMS_BMS_RTO, THREE_BAR_DELIVERY_BREAK (nessuna
implementazione MQL5 reale, noto), WEEKLY_EXP, 3COMMAS_BOT. Priorità
bassa finché non si esaurisce la coda 1-2.

## Regola operativa per ogni voce della coda

Per ognuna, seguire §P2.4 Master Roadmap: (1) trigger nudo senza
filtri, (2) BUY/SELL separati, (3) TF nativo della ricetta Python, (4)
poi aggiungere Elliott/trailing/D1-align UNO ALLA VOLTA — **mai
assumere che la ricetta Python funzioni identica su MT5**, è un'ipotesi
da verificare, non un fatto (regola generale ribadita più volte nel
vault: proxy Python ≠ motore MT5). Usare
`InpStrategySelector` col numero VERO (grep `NXS_SelectorAllows` in
`NXS_Strategies*.mqh`, **mai** il numero del registro — vedi
[[NEXUS EA - Due Numerazioni Strategia Diverse, InpStrategySelector Non e il Registro (03-09)]]).

## Non ancora fatto

- Nessuna delle 21 righe della categoria 1 verificata oggi — questa
  nota è la mappa, non l'esecuzione. Il prossimo passo naturale è
  scegliere la prima (FVG_MIT, PF3.24) e ripetere il ciclo fatto oggi
  per PIVOT_WICK/BOLLINGER: sbloccare (se serve), testare nudo su MT5,
  poi la ricetta completa.
- BAR_UPDN va riclassificato in categoria 3 (chiuso negativo il 02/09,
  non ancora fatto in questa nota per limiti di tempo).

## Collegamenti
[[NEXUS EA - MASTER ROADMAP v3]] · [[NEXUS EA - Tabella Master Strategie Verificate (24-08)]] ·
[[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]] · [[MOC - Trading]]
