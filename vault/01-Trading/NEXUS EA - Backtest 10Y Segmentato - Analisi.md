---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, backtest, 10y, v2.5.0, bug]
created: 2026-07-15
updated: 2026-07-15
---

# Backtest 10 anni segmentato (v2.5.0) — analisi completa

Il test di validazione a 10 anni (2016-2026, diviso in 10 segmenti da 1 anno per
limiti dell'istanza isolata) è la validazione fuori-campione promessa dopo
[[NEXUS EA - Screening Strategie (sito 10y)]]. Al 15/07 sono arrivati **8 dei 10
segmenti** (9 e 10 ancora in esecuzione). Fonte: `results/reports/V250_1Y_*` su
`origin/main` (commit `ec100ce`).

## Quali segmenti sono affidabili

| Segmento | Periodo reale | Barre | Trade | Esito |
|---|---|---|---|---|
| 1 (2016) | 1970.01.01–1970.01.01 | 0 | 0 | 🔴 Test mai partito — dati vuoti |
| 2 (2017) | 2017.07.11–2018.07.11 | 23.562 | 5 | 🔴 Dati presenti ma EA quasi inattivo |
| 3 (2018) | 2018.07.11–2019.07.11 | 23.524 | 68 | 🔴 Stesso problema, meno grave |
| 4 (2019) | 2019.07.11–2020.07.11 | 23.615 | 631 | 🟢 Affidabile |
| 5 (2020) | 2020.07.11–2021.07.11 | 23.495 | 726 | 🟢 Affidabile |
| 6 (2021) | 2021.07.11–2022.07.11 | 23.621 | 699 | 🟢 Affidabile |
| 7 (2022) | 2022.07.11–2023.07.11 | 23.653 | 919 | 🟢 Affidabile |
| 8 (2023) | 2023.07.11–2024.07.11 | 23.745 | 686 | 🟢 Affidabile |
| 9, 10 | — | — | — | ⏳ Non ancora pushati (verificato 15/07, nessuna traccia su nessun branch) |

I segmenti 1-3 condividono la stessa classe di bug (race condition tra lanci
consecutivi del tester sulla stessa istanza, già citata nel commit del fix del
segmento 2) e vanno **ri-eseguiti**, non presi come "la strategia non tradava in
quegli anni". **Tutte le analisi sotto usano solo i segmenti 4-8 (5 anni, 2019-2023).**

## Bug trovato #1: il contatore `executed` è rotto (falso negativo diagnostico)

In `MQL5/Include/NEXUS_v1/NXS_StratStats.mqh`, il campo `executed` (e tutto ciò
che ne dipende: `exec_rate_pct`, `dominant_blocker`, `health`) risulta **0 per
tutte le 38 strategie in tutti e 5 i segmenti**, anche dove ci sono centinaia di
trade reali. Il codice (`NXS_Stats_RecordExec`, riga 117-124) è correttamente
chiamato dal path principale (`NEXUS_EA_v2.mq5:933`, dentro `if(rc==EXEC_OK)`),
quindi non è ovvio perché resti a 0 — non ho trovato la causa esatta (richiede
o i log MT5 dal vivo o strumentazione aggiuntiva).

**Ma i dati wins/losses/breakeven per strategia sono reali**, non dipendono da
questo contatore: vengono letti direttamente dallo storico dei deal chiusi
(`NXS_Stats_ProcessClosedTrades`, `HistoryDealGetTicket`) con il nome strategia
preso dal commento dell'ordine. **Conclusione operativa: ignora `health` /
`dominant_blocker` / `exec_rate_pct` nei CSV finché il bug non è fixato — usa
solo wins/losses/breakeven/avg_R_win/avg_R_loss, che sono affidabili.**

## Bug/gap #2: nessuna protezione sul drawdown cumulato

`InpMaxDailyDDPct=5.0` in `NXS_Risk.mqh:90-93` confronta l'equity di oggi con
`g_balanceDayStart` (saldo a **inizio giornata**) — è un gate che si resetta
ogni giorno. Non esiste in tutto il codice (verificato per `peakEquity` /
`maxEquity` / `TotalDD` / `OverallDD`: zero risultati) **nessun gate sul
drawdown cumulato dal picco equity**. Risultato: il segmento 2020 (v2.5.0) ha
fatto **87.22% di drawdown equity** — lo stesso identico numero di v2.4.8 sui 3
anni ([[NEXUS EA - Lezione Overfitting 3Y]]) — nonostante il limite giornaliero
del 5%. Non è un bug (il codice fa esattamente quello che è scritto), è un buco
di design: 5% al giorno per molti giorni di fila, su settimane, non è limitato
da nulla.

## I 5 anni buoni: risultati aggregati (deposito 1.000 EUR)

| Segmento | Profitto Netto | Profit Factor | Drawdown Max (Equity) | Sharpe |
|---|---|---|---|---|
| 2019 | -557.06 | 0.75 | 61.08% | -5.00 |
| 2020 | -855.44 | 0.63 | **87.22%** | -5.00 |
| 2021 | -247.79 | 0.89 | 50.98% | -5.00 |
| 2022 | -322.29 | 0.89 | 45.83% | -5.00 |
| 2023 | -39.20 | 0.98 | 31.15% | -0.43 |

**Tutti e 5 gli anni sono in perdita.** Trend positivo di miglioramento
2019→2023 (DD scende da 87% a 31%, PF sale da 0.63 a 0.98) ma nessun anno
supera PF 1.0.

## Ranking per strategia — chi guida la perdita (R totale, 5 anni)

| Strategia | Trade | R totale | Note |
|---|---|---|---|
| **SAR** | 838 | **-29.2** | 🔴 peggiore in assoluto, 0/5 anni positivi |
| **MACD** | 713 | **-18.5** | 🔴 era VALIDATA su v2.4.8 (PF 1.11), "raffinata" in v2.5.0 e ora è la 2ª peggiore |
| **ADX_RSI** | 452 | **-14.2** | 🔴 1/5 anni positivi |
| RSI_DIV | 285 | -7.4 | trascinata da un solo anno pessimo (2022: -9.4) |
| BJORGUM | 46 | -6.6 | negativa 4/5 anni — smentisce l'ottimismo PF 2.14 basato su 5 trade (vedi [[NEXUS EA - Principi]] #4) |
| TSI | 539 | -5.8 | negativa 4/5 anni |
| OB_MIT | 108 | -4.6 | |
| FVG_CONT | 198 | -2.3 | |
| ORDER_BLOCK | 60 | -1.7 | |
| EMA_PULLBACK | 73 | -1.4 | |
| CISD | 15 | +3.5 | 🟢 mai un anno negativo (0/5) |
| BREAKOUT_ACC | 73 | +3.9 | 🟢 4/5 anni positivi |
| **TURTLE_SOUP** | 181 | **+7.3** | 🟢 conferma [[Turtle Soup]] |

Somma di tutte le strategie: **-78.4R**. Solo SAR+MACD+ADX_RSI spiegano **-62R,
circa l'80% dell'intera perdita**.

## Perché il fix HTF di v2.5.0 non ha funzionato per SAR/MACD/ADX_RSI

Non è un bug di implementazione — verificato in `NXS_StrategyProfiles.mqh`
(righe 23, 38, 45): l'HTF filter è correttamente attivo per tutte e tre, con i
numeri dello screening sito citati inline (SAR→PF1.52, MACD→PF1.63,
ADX_RSI→PF1.48). Due letture diverse:

- **SAR** non compare nemmeno nella tabella delle config vincenti in
  [[NEXUS EA - Screening Strategie (sito 10y)]] — il fix le è stato applicato
  per generalizzazione del pattern ("HTF alza l'edge quasi ovunque"), non
  perché il suo screening individuale lo confermasse. Coerente con il fatto
  che sia la peggiore in assoluto sui dati MT5 reali.
- **MACD** invece era già validata (PF 1.11 su 3 anni, v2.4.8) prima del
  "raffinamento" v2.5.0 basato sullo screening sito — e ora è la seconda
  peggiore. Questo è il [[NEXUS EA - Principi]] #5 (motore sito ≠ motore MT5)
  che si verifica su scala molto più ampia di quanto documentato finora: non
  solo l'edge del sito non si trasferisce, ma **ha peggiorato una strategia
  che già funzionava**.

**Nuova regola da aggiungere ai principi**: un edge trovato sullo screening
sito va sempre confermato su MT5 PRIMA di sostituire una config che sui dati
MT5 reali era già validata — altrimenti si rischia di rompere qualcosa che
funzionava per inseguire un segnale di un motore meno fedele.

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Log Versioni]] · [[NEXUS EA - Principi]] · [[NEXUS EA - Hedge nel Tempo]] · [[MOC - Strategie]]
