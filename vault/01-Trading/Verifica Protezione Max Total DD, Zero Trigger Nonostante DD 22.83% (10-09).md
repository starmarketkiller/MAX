---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, mql5, protezioni, bug, max-total-dd]
created: 2026-09-10
updated: 2026-09-10
---

# Verifica protezione Max Total DD — zero trigger nonostante DD 22.83% (10/09)

## Test

`nxs_regtest_maxtotaldd_check` — FVG_CONT, stesso periodo/config dello
step2 baseline (2023.09.01-2026.08.26, D1/H4 multi-TF), con
`InpUseMaxTotalDD=true`, `InpMaxTotalDDPct=10.0` aggiunti ieri (09/09).

## Risultato

168 trade, PF1.92, net $2628.45, DD bilancio 12.45%, **DD equity 22.83%**
— praticamente identico allo step2 baseline (168 trade, PF1.92, $2635.26,
DD 12.42%/22.79%). Differenze minime (arrotondamento).

## Problema trovato

`InpMaxTotalDDPct=10.0` significa che la protezione dovrebbe flattenare il
conto e mettere in pausa non appena l'equity scende del 10% dal picco.
L'equity DD massima riportata da MT5 è 22.83% — più del doppio della
soglia. **Zero occorrenze** di `"MAX_TOTAL_DD HIT"` o di qualunque log
`[NEXUS PROT]` relativo nell'intero log di 3 anni: la protezione non è mai
scattata, nonostante il conto abbia sicuramente attraversato un calo del
10%+ dal suo picco corrente in qualche momento della serie (è
matematicamente necessario per arrivare a un max DD del 22.83%).

Non ho investigato la causa esatta (fuori scope rispetto al lavoro di oggi
su SLReclaim/Research Mode, che l'utente ha chiesto di chiudere prima di
aggiungere altro). Ipotesi da verificare in un giro dedicato:
- `g_maxDDPeakEquity` non aggiornato/resettato correttamente in qualche
  percorso (es. dashboard `reset_protections`, riavvio stato);
- `NXS_Prot_CheckMaxTotalDD()` non raggiunta per un `return` precoce in
  `NXS_Prot_OnTick()` (es. `g_pausedUntilNextOpen` rimasto vero più a lungo
  del previsto dopo un altro evento di protezione, saltando il controllo);
- differenza tra equity calcolata internamente (`AccountInfoDouble
  (ACCOUNT_EQUITY)`) e la curva equity riportata da MT5 a fine test.

## Verdetto

**Protezione non verificata come funzionante** — implementata (commit
`7491e42`, 09/09) ma il primo vero test di regressione mostra che non
scatta quando dovrebbe. Da NON considerare operativa finché non si trova e
corregge la causa. Segnalato, non corretto in questa sessione.

## Collegamenti
[[MOC - Trading]]
