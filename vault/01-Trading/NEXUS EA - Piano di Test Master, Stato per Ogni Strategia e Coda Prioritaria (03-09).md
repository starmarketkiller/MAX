---
type: reference
domain: trading
status: active
tags: [trading, nexus-ea, piano-test, master-queue, riferimento]
created: 2026-09-03
updated: 2026-09-05
---

# NEXUS EA — Piano di test master: stato per ogni strategia e coda prioritaria (03-05/09)

## Bilancio al 05/09 (consolidamento)

**7 strategie testate sul vero MT5 in questa indagine (03-04/09)**:
ADX_RSI, MACD, FVG_CONT, BOLLINGER (M5/M30/H4), PIVOT_WICK. Di queste,
**3 sono confermate positive** (ADX_RSI PF2.04, MACD PF1.53, FVG_CONT
PF1.93 — quest'ultima il risultato migliore, contraddice una nota
storica nel codice), **1 modesta ma pulita** (BOLLINGER H4 BUY-only
PF1.35, Sharpe2.45 — il miglior profilo di rischio trovato), **2
chiuse negative** dopo indagine approfondita (PIVOT_WICK — 10 varianti
isolate su 3 mesi e 3 anni, nessuna regge — e BOLLINGER M5 scalp).
**2 già confermate prima di oggi** (SAR, EMA_PULLBACK — quest'ultima
oggi rafforzata da un walk-forward a 4 finestre mai visto prima,
tutte positive e in miglioramento). Sotto, il dettaglio per categoria.

**3 bug/scoperte infrastrutturali trasversali trovati oggi** (non
specifici di una strategia, rilevanti per QUALUNQUE test futuro):
1. Il registro strategie (`NXS_StrategyRegistry.mqh`) usa una
   numerazione diversa e indipendente da quella che isola davvero una
   strategia (`NXS_SelectorAllows`) — vedi [[NEXUS EA - Due Numerazioni Strategia Diverse, InpStrategySelector Non e il Registro (03-09)]].
2. I meccanismi di parziale (ATR/pip-fisso/volume-spike) sono
   aritmeticamente impossibili a lotto minimo (0.01) — vedi [[NEXUS EA - Bug Infrastrutturale, i Parziali Percentuali Sono Inerti a Lotto Minimo (03-09)]].
3. Il filtro per sessione (`InpXScoreMin`) appartiene a un percorso di
   esecuzione diverso (istituzionale legacy) da quello usato da tutti
   i test di oggi (`InpUseStrategyProfiles=true`) — bypassato di
   proposito, non un bug residuo. Aggiunto un gate diretto
   (`InpProfileOverlapOnly`) nel percorso corretto — vedi [[NEXUS EA - Il Filtro Sessione Era su un Percorso di Esecuzione Diverso (04-09)]].
   **Validato empiricamente il 05/09: aiuta MACD (PF1.53→1.74, trade
   199→166, net +5.7%) ma peggiora BOLLINGER BUY-only (Sharpe 2.45→0.74,
   campione crollato a 11 trade) — non è un filtro universale, va
   testato caso per caso. Vedi [[NEXUS EA - BOLLINGER Overlap-Only Peggiora, Filtro Non Universale (05-09)]].**
4. **Terzo cancello silenzioso** `NXS_Profile_Enabled()`: indipendente
   da `InpStrat_X` e `InpStrategySelector`, blocca l'apertura ordini
   ("profile_disabled") per qualunque strategia non esplicitamente in
   whitelist — zero trade silenziosi anche con selector e flag giusti.
   Trovato su PMAX (28/08), BB_SQUEEZE/ORDER_BLOCK/BOLLINGER (02-03/09),
   e oggi su STRUCT_REACT + audit proattivo di altre 6 (ICHIMOKU,
   RSI_DIV, FVG_MIT, OTE_CONT, MALAYSIAN_SNR, WEEKLY_EXP) — tutte
   sbloccate. **Regola**: prima di un test nudo su una strategia mai
   provata, controllare `grep 'name == "NOME"' NXS_StrategyProfiles.mqh`
   per questa whitelist. Vedi [[NEXUS EA - Terzo Cancello Silenzioso Trovato su 7 Strategie, Audit Proattivo (05-09)]].

**Dal lato analisi dati grezzi** (grafico GOLD H1/M30/M5, 2019-2026,
non backtest MT5): confluenza multi-timeframe (3.06× più livelli M30
vicino a un vero pivot D1) e sessione oraria (36% delle inversioni in
12-16 UTC) sono gli ingredienti più solidi trovati; Fibonacci OTE,
Wyckoff/fasi e Elliott Wave (testato su 5 timeframe con le sue stesse
regole) **non mostrano un edge pulito** su GOLD in questo campione —
vedi [[NEXUS EA - Perché Pochi Trade, Analisi CSV Vera su ADX_RSI e BOLLINGER (04-09)]]
e le note collegate.

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
| 3 | STRUCT_REACT | 2.65 (2.82/2.48) | nessun Elliott (peggiora qui), BUY-only | 🔄 **In test (05/09)**: primo tentativo zero trade — bloccata da un terzo cancello silenzioso (`NXS_Profile_Enabled`), sbloccata e ritestata, risultato in arrivo. Vedi [[NEXUS EA - Terzo Cancello Silenzioso Trovato su 7 Strategie, Audit Proattivo (05-09)]] |
| 4 | FVG_CONT_V2 | 2.40 (2.10/2.93) | trailing+Elliott, BUY-only | No — **verificato 05/09: nessuna implementazione MQL5 esiste nel codice**, non è "da testare", è da scrivere prima |
| 5 | SAR_FLIP | 2.31 (1.54/3.49) | trailing+Elliott, BUY-only | No — **verificato 05/09: nessuna implementazione MQL5 esiste nel codice**, stesso caso di FVG_CONT_V2 |
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
| 16 | FVG_CONT | 1.78 (1.66/1.91) | trailing+Elliott, BUY-only | ✅ **Confermata sul vero MT5 (04/09) — miglior risultato di oggi**: nudo H4 PF1.93, Sharpe2.63, net+$2655/3anni. SELL genuinamente positivo qui (+$581, non solo rumore). Contraddice una nota storica nel codice (PF0.79 su MT5) — discrepanza non indagata. Vedi [[NEXUS EA - FVG_CONT Miglior Risultato di Oggi, Contraddice Nota Storica (04-09)]] |
| 17 | LIQ_SWEEP | 1.73 (invariato) | ER+floor, BUY-only | No |
| 18 | DARVAS_BOX | 1.65 (1.43/1.89) | Elliott, BUY-only | No |
| 19 | DONCHIAN_TURTLE | 1.63 (1.45/1.83) | Elliott, BUY-only | No — **correlata 99.7% con DARVAS_BOX, tenerne solo una in portafoglio** |
| 20 | BOLLINGER (=RANGE_FADE) | 1.95 (1.91/1.99) | Elliott, BUY-only, **4h non M5** | ✅ **Verificata sul vero MT5 (04/09)**: H4 BUY-only nudo PF1.35, Sharpe2.45 (il miglior profilo di rischio di oggi) — Elliott qui PEGGIORA (PF1.23), diverso da Python. M30 molto più debole (PF1.06, 652 trade). M5 nuda negativa (PF0.83) e RSI/candela non la salvano — tre TF ora confrontati, H4 vince nettamente. Vedi [[NEXUS EA - BOLLINGER H4 Nuda, BUY Positivo SELL Negativo, Conferma Python (04-09)]] |
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

### 2. Validate sul vero MT5, confermate positive (6)

| Strategia | Stato | Config | Fonte |
|---|---|---|---|
| SAR | ✅ Confermata | Lotto naturale, candle-align H4, PF1.37-1.57 su 5 finestre | [[NEXUS EA - Sintesi Sessione Maratona SAR-EMA_PULLBACK-Scalp-RegimeVeto (01-02-09)]] |
| EMA_PULLBACK | ✅ Confermata robusta | Nuda; **walk-forward 4 finestre (04/09) tutte positive, PF1.44→1.71 in miglioramento** | [[NEXUS EA - EMA_PULLBACK Walk-Forward 4 Finestre, Tutte Positive (04-09)]] |
| **FVG_CONT** | ✅ Confermata — **il migliore di oggi** | H4 nudo, PF1.93, Sharpe2.63 | [[NEXUS EA - FVG_CONT Miglior Risultato di Oggi, Contraddice Nota Storica (04-09)]] |
| ADX_RSI | ✅ Confermata | D1 nudo (config attuale), PF2.04, BUY domina | [[NEXUS EA - ADX_RSI D1 Confermata Positiva sul Vero MT5, BUY Domina (04-09)]] |
| MACD | ✅ Confermata | H4 nudo, PF1.53, BUY domina | [[NEXUS EA - MACD H4 Confermata Positiva, Terza Conferma BUY-Dominante (04-09)]] |
| BOLLINGER | ✅ Confermata (H4 solo) | H4 BUY-only nudo, PF1.35, **miglior Sharpe (2.45) di tutta l'indagine** — M30/M5 molto più deboli. Overlap-only testato (05/09): peggiora (Sharpe→0.74, 11 trade) — restare sulla ricetta nuda | [[NEXUS EA - BOLLINGER H4 Nuda, BUY Positivo SELL Negativo, Conferma Python (04-09)]] · [[NEXUS EA - BOLLINGER Overlap-Only Peggiora, Filtro Non Universale (05-09)]] |

### 3. Testate sul vero MT5, chiuse con esito negativo dopo indagine approfondita (2)

| Strategia | Stato | Perché | Fonte |
|---|---|---|---|
| PIVOT_WICK | ❌ Chiusa (fermata dall'utente) | 10 varianti isolate (9 su 3 mesi + 1 su 3 anni), solo 1 migliora la qualità e non regge su campione ampio (PF0.91→0.73) | [[NEXUS EA - PIVOT_WICK step2 e OneShotLevel Analizzati, Nessun Fix (03-09)]] |
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

- **17 righe della categoria 1 ancora da verificare** (FVG_MIT
  PF3.24 in cima — architettura più complessa, sistema di zone "NXR"
  condiviso, richiede più studio prima di testarla in sicurezza; poi
  STRUCT_REACT, FVG_CONT_V2, SAR_FLIP, TSI, ecc. in ordine di PF Python).
- Nessuna delle 6 strategie confermate positive oggi (cat. 2) ha
  ancora la ricetta completa Python (trailing+Elliott) — solo il
  trigger nudo è stato verificato. Test isolati su Elliott (BOLLINGER)
  hanno già mostrato che non è garantito che aiuti sul vero MT5.
- Sintesi tentata (livelli+sessione+CloseConfirm su PIVOT_WICK) non
  ancora conclusa: il fix del filtro sessione è arrivato tardi, il
  test con il filtro vero non è stato completato in questa sessione.
- BAR_UPDN va riclassificato in categoria 3 (chiuso negativo il 02/09,
  non ancora fatto in questa nota per limiti di tempo).
- Nessun walk-forward multi-finestra fatto oggi sulle 5 nuove conferme
  (ADX_RSI/MACD/FVG_CONT/BOLLINGER) — solo un'unica finestra 2023-2026,
  a differenza di SAR/EMA_PULLBACK che hanno un walk-forward vero.

## Collegamenti
[[NEXUS EA - MASTER ROADMAP v3]] · [[NEXUS EA - Tabella Master Strategie Verificate (24-08)]] ·
[[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]] · [[MOC - Trading]]
