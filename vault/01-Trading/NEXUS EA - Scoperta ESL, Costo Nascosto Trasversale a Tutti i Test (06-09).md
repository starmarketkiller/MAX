---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, esl, analisi-csv, bug-trasversale, adx-rsi]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — scoperta ESL: un costo nascosto trasversale a tutti i test di oggi (06/09)

## Perché questa nota

L'utente ha giustamente contestato che finora l'analisi CSV si fermava
a PF/net/WR/avg win-loss, senza scendere su **distanza tra ingressi,
PnL flottante durante il trade, e cosa blocca/interrompe i trade** —
esattamente quello che l'obiettivo originale della sessione chiedeva
("analizzando csv livelli apertura e chiusura, equity e bilancio...
analizza i trade e i csv per vedere cambiamenti"). Facendo questa
analisi più profonda su ADX_RSI (il caso più a portata di mano, appena
testato) è emerso un problema reale, non notato prima.

## Metodo

Ricostruiti i trade dal CSV deals, poi per ognuno recuperate le barre
M15 reali (cache locale) tra apertura e chiusura per calcolare il vero
PnL flottante bar-per-bar (MAE = massima escursione avversa, MFE =
massima escursione favorevole) — non dato fornito da MT5 di default,
ricostruito da zero. Script: `deep_csv_analysis.py`.

## Scoperta: le uscite "dd" sono la categoria più dannosa, peggio degli SL veri

| Test | Uscite SL | Uscite "dd" (ESL) |
|---|---|---|
| ADX_RSI nudo (già "confermato positivo" il 04/09) | 29 trade, net -$865, media -$30 | **7 trade, net -$594, media -$85** |
| ADX_RSI + Elliott (06/09) | 26 trade, net -$598, media -$23 | **13 trade, net -$1127, media -$87** |

"dd" nel commento non è uno stop-loss del trade — è `NXS_R_DD =
"NXS:DD"`, il tag di `NXS_Prot_CheckESL()` (Equity Stop Loss):
**un circuit-breaker a livello di CONTO**, non di trade, che chiude
FORZATAMENTE tutte le posizioni aperte se il PnL flottante scende sotto
`-InpESL_Value%` del balance (default 5%, `InpUseESL=true` di default).

## Perché colpisce ADX_RSI in particolare

ADX_RSI ha TP a 10×ATR (bersaglio enorme) e tiene i trade per giorni/
settimane — l'MAE mediano ricostruito è ~300 pip ($30 su lotto
0.01-equivalente), il che con un conto da $1000 e rischio 0.5-5% per
trade sfonda facilmente la soglia ESL del 5% PRIMA che il trade abbia
il tempo di recuperare verso il TP. Il 75-77% delle perdenti erano
andate ALMENO 20 pip in profitto prima di invertire — la strategia non
sbaglia direzione, viene tagliata a metà percorso da una protezione
tarata per uno scenario diverso.

## Punto critico: era già presente nel risultato "confermato positivo"

Il test nudo del 04/09 (PF2.04, net+$1676, mai messo in discussione
finora) aveva GIÀ 7 trade tagliati dall'ESL con un costo di -$594 —
il ~35% della perdita totale lorda del test. Non è un problema
introdotto oggi con Elliott, è strutturale e non era mai stato isolato
perché l'analisi si fermava al PF/net aggregato.

## Test in corso

Lanciato `nxs_adxrsi_step3_noesl_3y` (stessa config nuda, `InpUseESL=false`)
per verificare empiricamente l'ipotesi: se disattivare l'ESL migliora
il netto, conferma che è un costo evitabile per strategie a bersaglio
largo come ADX_RSI (non per forza da disattivare in generale — l'ESL
resta una protezione di sicurezza legittima per altre strategie più
rischiose, da valutare caso per caso come ogni altro filtro).

## Lezione di metodo (per tutti i test futuri)

D'ora in avanti, per ogni strategia con risultato "confermato" o
"chiuso", ripetere questa analisi più profonda prima di considerarla
definitiva:
1. Distanza/sovrapposizione tra ingressi (cluster o gap anomali).
2. MAE/MFE ricostruito da barre reali (non solo dal risultato finale).
3. Rottura del net per motivo di uscita (SL/TP/ESL/altro) — non solo
   il conteggio, il contributo in $ di ciascuna categoria.
4. % di perdenti che erano temporaneamente in profitto prima di
   invertire (rivela se il problema è la direzione o la gestione).

## Collegamenti
[[NEXUS EA - ADX_RSI D1 Confermata Positiva sul Vero MT5, BUY Domina (04-09)]] · [[NEXUS EA - ADX_RSI Filtro Elliott Peggiora, Restare sulla Ricetta Nuda (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
