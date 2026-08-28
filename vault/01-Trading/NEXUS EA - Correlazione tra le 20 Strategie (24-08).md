---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, correlazione, portafoglio, ridondanza]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Correlazione tra le 20 strategie (24/08)

## Perché

Il portafoglio a 20 strategie ([[NEXUS EA - Portafoglio a 20 Strategie (24-08)]])
mostrava drawdown esplosivo aprendo più posizioni concorrenti — segno
che molte strategie non sono indipendenti. Verifica diretta:
`correlation_analysis_24-08.py`, matrice giorno×strategia di R netto
(non filtrato dal bucket a 2 slot — la correlazione del SEGNALE, non
dell'esecuzione), correlazione di Pearson a coppie su 894 giorni.

## Risultato: un cluster di trend-following molto correlato + 5 vere diversificatrici

**DARVAS_BOX e DONCHIAN_TURTLE sono correlate al 99.7%** (r=0.997) —
praticamente la stessa strategia, non due strategie diverse. Un cluster
più ampio di trend/breakout su XAUUSD 4h è moderatamente-fortemente
correlato tra loro: SAR↔SAR_ADX20 (0.838), BREAKOUT_ACC↔DONCHIAN_TURTLE
(0.819), MACD↔SAR (0.787), e a cascata quasi tutte le combinazioni tra
{SAR, SAR_ADX20, MACD, ADX_RSI, BREAKOUT_ACC, DARVAS_BOX,
DONCHIAN_TURTLE, FVG_CONT} (r tipicamente 0.45-0.84).

**Le vere diversificatrici** (correlazione media con tutte le altre
vicina a zero o negativa): **STRUCT_REACT (-0.019, e NEGATIVAMENTE
correlata con SAR -0.118 e SAR_ADX20 -0.133 — un hedge naturale
genuino)**, EMA_PULLBACK (-0.012), FVG_MIT (+0.015), OTE_CONT (+0.028),
LIQ_SWEEP (+0.084).

## La causa del portafoglio squilibrato, ora chiara

Le 4 strategie che nel portafoglio a 2 slot non hanno eseguito NESSUN
trade (MALAYSIAN_SNR_BREAKOUT, STRUCT_REACT, BREAKOUT_ACC, SAR_ADX20)
includono proprio la strategia con il miglior profilo di
diversificazione (STRUCT_REACT) — esclusa non perché cattiva, ma perché
troppo rara per competere con un cluster che genera migliaia di segnali
grezzi. LIQ_SWEEP (la peggiore nel portafoglio, -€207) ha una
correlazione media bassa (0.084) — non è danneggiata dal cluster, è
semplicemente troppo poco frequente per accedere agli slot quando il
cluster li occupa quasi sempre.

## Due tentativi di correzione: nessuno risolve da solo

**Slot dedicati (cluster vs diversificatrici)**: testato con diverse
combinazioni (1+1, 1+2, 2+2, 1+3 slot). Risultato misto, non un
miglioramento pulito — dare più accesso alle diversificatrici riduce il
numero di strategie nette perdenti (da 6 a 3-4) ma **il drawdown
peggiora sempre** (dal 35.9% originale fino al 55.8% con 1+3 slot) —
stessa firma già vista nel sweep di max_concorrenti: più esposizione
concorrente, anche "intelligente", costa in drawdown più di quanto renda
in PnL.

**Deduplicazione semplice (rimuovere DONCHIAN_TURTLE)**: netPnL e
drawdown restano quasi identici (2725→2733, DD 35.9%→35.7%) — rimuovere
UN membro del cluster non cambia nulla perché un altro membro quasi
identico (DARVAS_BOX o un altro del cluster) prende comunque lo slot
quasi nello stesso momento. Il cluster nel suo insieme monopolizza le
risorse, non un singolo membro.

## Conclusione

Il problema non si risolve con un aggiustamento rapido di parametri —
serve un ripensamento più profondo dell'architettura di allocazione,
probabilmente **un budget di rischio indipendente per strategia**
(ognuna con la sua fetta fissa di capitale, non in competizione per un
pool condiviso di slot) invece del bucket condiviso attuale, pensato
per 4-5 strategie di frequenza comparabile e non scalato bene a 20
strategie eterogenee. Non ancora implementato/testato — richiede un
cambiamento più strutturale del motore di simulazione, non un parametro.

Su richiesta dell'utente, questo lavoro si ferma qui per ora: il prossimo
passo concordato è ottimizzare le strategie singolarmente (test meno
ovvi per strategia) prima di tornare al problema di allocazione del
portafoglio.

## Prossimi passi aperti

- Budget di rischio indipendente per strategia (architettura alternativa
  al bucket condiviso) — non ancora tentato.
- Usare la matrice di correlazione per scegliere DELIBERATAMENTE un
  sottoinsieme di ~8-10 strategie a bassa correlazione reciproca invece
  delle 20 intere, prima di un'altra simulazione di portafoglio.
- Rifare la correlazione includendo TURTLE_SOUP/LDN_REVERSAL una volta
  riverificate.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Portafoglio a 20 Strategie (24-08)]]
