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
[[NEXUS EA - Screening Strategie (sito 10y)]]. Al 15/07 sono arrivati **9 dei 10
segmenti** (10 ancora in esecuzione). Fonte: `results/reports/V250_1Y_*` su
`origin/main` (commit `dc26907`).

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
| 9 (2024) | 2024.07.11–2025.07.11 | 23.565 | 1.349 | 🟢 Affidabile — **100% qualità storico**, il primo segmento con dati tick reali completi |
| 10 | — | — | — | ⏳ Ancora in esecuzione (verificato 15/07) |

I segmenti 1-3 condividono la stessa classe di bug (race condition tra lanci
consecutivi del tester sulla stessa istanza, già citata nel commit del fix del
segmento 2) e vanno **ri-eseguiti**, non presi come "la strategia non tradava in
quegli anni". **Tutte le analisi sotto usano i segmenti 4-9 (6 anni, 2019-2024).**

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
fatto 87.22% di drawdown equity — lo stesso identico numero di v2.4.8 sui 3
anni ([[NEXUS EA - Lezione Overfitting 3Y]]) — nonostante il limite giornaliero
del 5%, e il segmento 2024 lo ha superato con **88.69%**, il peggiore di tutto
il dataset finora (con qualità storico 100%, quindi non un artefatto). Non è
un bug (il codice fa esattamente quello che è scritto), è un buco di design:
5% al giorno per molti giorni di fila, su settimane, non è limitato da nulla.
Il fatto che il DD peggiore sia arrivato nell'anno più recente, non nel primo
test, dice che il buco non si sta chiudendo da solo col tempo.

## I 6 anni buoni: risultati aggregati (deposito 1.000 EUR)

| Segmento | Profitto Netto | Profit Factor | Drawdown Max (Equity) | Sharpe |
|---|---|---|---|---|
| 2019 | -557.06 | 0.75 | 61.08% | -5.00 |
| 2020 | -855.44 | 0.63 | 87.22% | -5.00 |
| 2021 | -247.79 | 0.89 | 50.98% | -5.00 |
| 2022 | -322.29 | 0.89 | 45.83% | -5.00 |
| 2023 | -39.20 | 0.98 | 31.15% | -0.43 |
| 2024 | -854.85 | 0.83 | **88.69%** | -3.89 |

**Tutti e 6 gli anni sono in perdita.** Il "trend positivo" 2019→2023 (DD sceso
da 87% a 31%) **si è invertito bruscamente nel 2024**: DD 88.69%, il peggiore
di tutto il dataset, e con il primo segmento a qualità storico 100% (quindi
non è un artefatto di dati incompleti — è il segnale più pulito che abbiamo).
Non fidarsi mai di un trend di 3-4 punti come se fosse consolidato.

## Ranking per strategia — chi guida la perdita (R totale, 6 anni 2019-2024)

| Strategia | R totale | Note |
|---|---|---|
| **SAR** | **-34.3** | 🔴 peggiore in assoluto |
| **MACD** | **-21.1** | 🔴 era VALIDATA su v2.4.8 (PF 1.11), "raffinata" in v2.5.0 e ora è la 2ª peggiore |
| **RSI_DIV** | **-17.5** | 🔴 sale al 3° posto: 2024 è stato il suo anno peggiore in assoluto (-10.1), peggio del 2022 (-9.4) |
| **ADX_RSI** | -15.3 | |
| FVG_CONT | -9.3 | 2024 pessimo (-7.0) dopo 3 anni di ripresa (2021-2023 tutti positivi) |
| BJORGUM | -8.6 | negativa 5/6 anni |
| TSI | -7.9 | |
| EMA_PULLBACK | -5.5 | |
| OB_MIT | -4.1 | |
| ORDER_BLOCK | -1.5 | |
| BOLLINGER | -0.7 | |
| FVG_MIT | -0.6 | |
| SH_BMS_RTO | -0.3 | |
| LONDON_BO | 0.0 | |
| **TURTLE_SOUP** | **+0.1** | ⚠️ **quasi azzerata**: 2024 è stata negativa (-7.2), la prima volta in assoluto — vedi sotto |
| SMS_BMS_RTO | +0.1 | |
| LIQ_SWEEP | +0.2 | |
| MALAYSIAN_SNR | +0.7 | |
| CISD | +3.2 | anche qui il 2024 è stato leggermente negativo (-0.3), prima volta |
| **BREAKOUT_ACC** | **+4.3** | 🟢 unica a restare solidamente positiva anche nel 2024 (+0.4) |

Somma di tutte le strategie: **-118.1R** (era -78.4R su 5 anni). Solo
SAR+MACD+RSI_DIV+ADX_RSI spiegano **-88.2R, circa il 75% dell'intera perdita**.

## Aggiornamento importante: TURTLE_SOUP si è quasi azzerata con il segmento 9

Prima della scoperta del segmento 9, TURTLE_SOUP era la strategia migliore in
assoluto (+7.3R su 5 anni, "validata"). Il 2024 (-7.2R, 66 trade) ha cancellato
quasi tutto il guadagno accumulato: **+0.1R su 6 anni**, sostanzialmente
breakeven. Non è più corretto chiamarla "validata" senza riserve — vedi
[[NEXUS EA - Hedge nel Tempo]] per il dettaglio e cosa cambia per il nucleo
hedge. Lezione diretta: anche 5 anni di dati possono nascondere un singolo
anno che ribalta tutto — [[NEXUS EA - Principi]] #1 vale anche qui, non solo
per i test brevi.

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

## Segmento 10 arrivato (15/07) — non ancora integrato in questa analisi

Il segmento 10 (2025-26, 1.559 trade totali — il volume più alto di tutti)
è stato pushato da un'altra sessione insieme a
[[NEXUS EA - Backtest 10Y Segmentato (v2.5.0)]], che documenta anche un bug
di pipeline (report duplicati per race condition, stesso bug del segmento 2)
e un'anomalia non ancora spiegata: **i segmenti 2016-2019 hanno solo
17/3/59 trade** contro le 500-1500+ degli anni successivi — non spiegata
dai contatori BLOCKED_BY_GATE, ipotesi principale è qualità dei dati
storici ricostruiti. Questo va incrociato con la scoperta di questa nota
(segmenti 1-3 falliti per bug del tester) — potrebbero essere la stessa
causa vista da due angolazioni diverse, o due problemi distinti. **TODO**:
estendere il ranking R-per-strategia (6 anni → 7 anni) includendo il
segmento 10, e chiarire se l'anomalia 2016-2019 è lo stesso bug o un'altra
causa. Vedi [[TODO - Backtest 10Y]].

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Log Versioni]] · [[NEXUS EA - Principi]] · [[NEXUS EA - Hedge nel Tempo]] · [[MOC - Strategie]] · [[NEXUS EA - Backtest 10Y Segmentato (v2.5.0)]]
