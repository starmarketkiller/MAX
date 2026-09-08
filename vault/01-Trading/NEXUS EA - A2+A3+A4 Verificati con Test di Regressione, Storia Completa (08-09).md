---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bug, slreclaim, profitreclaim, audit, test-di-regressione, metodo]
created: 2026-09-08
updated: 2026-09-08
---

# NEXUS EA — A2+A3+A4 verificati con test di regressione, storia completa (08/09)

## Riassunto per chi ha fretta

I fix A2 (ProfitReclaim senza protezioni), A3 (SLReclaim col gate
debole) e A4 (magic number stantio) dall'audit esterno sono ora
**applicati e verificati con prova diretta nei log** — non solo
"compila pulito". Il primo giro del fix era **sbagliato** (premessa
falsa ripresa dall'audit), scoperto da un test di regressione dedicato
prima di essere dichiarato buono. Il metodo ha funzionato esattamente
come deve: non fidarsi di un fix finché non lo si vede bloccare per
davvero.

## La sequenza completa

**1. Audit esterno (07/09)** — [[NEXUS EA - Audit Esterno Cartella MQL5, Verificato Punto per Punto (08-09)]]
segnala: SLReclaim usa `NXS_CheckProtections()` (gate "più debole"),
ProfitReclaim non ne usa nessuno, entrambi dovrebbero passare per
`NXS_CommonExposurePreflight()` (il gate "pieno" usato dal percorso
primario). Raccomandazione: sostituire.

**2. Primo fix (08/09, ~mattina)** — Applicato esattamente come
raccomandato: sostituita la chiamata a `NXS_CheckProtections()` con
`NXS_CommonExposurePreflight()` in `NXS_SLReclaim.mqh`, aggiunta la
stessa in `NXS_ProfitReclaim.mqh` (che prima non ne aveva nessuna).
Aggiunto anche `NXS_TradeSetMagic()` (A4) in entrambi. Ricompilato:
**0 errori**. Commit `1ac0437`.

**3. Test di regressione, primo giro — FALLITO** — Costruito un test
mirato (`nxs_regtest_slreclaim_gate_3m`: SAR+SLReclaim, `InpMaxDailyDDPct=0.5`
per forzare freeze frequenti, 3 mesi M15) invece di fidarsi del
compile pulito. Risultato: **80 trade, DD totale 25.42%, 27 riaperture
SLReclaim armate — ZERO bloccate**, tutte "esito=OK". Con un cap
giornaliero dello 0.5% e un DD totale del 25%, un blocco totale è
statisticamente impossibile se il gate funzionasse.

**4. Causa trovata** — Letto il percorso primario (`NXS_TryExecuteRC`,
`NXS_Execution.mqh:712` chiama `NXS_CheckProtections()`, riga `:486`
chiama **separatamente** `NXS_CommonExposurePreflight()`, **entrambe**
nella stessa apertura). L'audit esterno aveva assunto che la seconda
fosse un superset della prima — **falso**. Sono complementari:

| Funzione | Copre |
|---|---|
| `NXS_CheckProtections()` | DD giornaliero (`g_run_MaxDailyDDPct`), margine (`InpMinMarginLevel`), max-trade/giorno, max-concorrenti, anti-revenge, anti-bleed skip |
| `NXS_CommonExposurePreflight()` | Licenza, ruin freeze, ESL/DPT/pausa, stato/indicatori degradati, RiskShield per strategia, cap esposizione direzionale, margine **proiettato** (`InpMinMarginLevelPct`), preflight broker (spread, distanza minima stop) |

Sostituire l'una con l'altra lascia scoperta metà dei controlli — nel
caso di SLReclaim, esattamente il controllo DD-giornaliero che il fix
doveva rinforzare.

**5. Correzione** — `NXS_SLReclaim.mqh` e `NXS_ProfitReclaim.mqh` ora
chiamano **entrambe** le funzioni in sequenza (prima `NXS_CheckProtections`,
poi se passa `NXS_CommonExposurePreflight`), stesso ordine del
percorso primario. Ricompilato: **0 errori**. Commit `f57e0e4`.

**6. Test di regressione, secondo giro — CONFERMATO**

| | SLReclaim | ProfitReclaim |
|---|---|---|
| Eventi totali | — | 37 |
| Riaperture riuscite | — | 22 |
| Bloccate da `NXS_CheckProtections` (`daily_dd`) | **401** | 13 |
| Bloccate da `NXS_CommonExposurePreflight` | — | **2** (una per `hard_spread_cap`, prova diretta che questo secondo gate aggiunge protezione reale, non ridondante) |

401 blocchi su SLReclaim e 15 su ProfitReclaim (13+2), nello stesso
test che prima ne mostrava zero — stesso identico setup, unica
differenza il codice. Il fix funziona, verificato con prova diretta
nel log, non per fede nel compile pulito.

## Lezione di metodo

Un fix che "compila senza errori" e persino "sembra corretto leggendo
il diff" può essere silenziosamente sbagliato se la premessa su cui si
basa (qui: "A è un superset di B") non viene verificata leggendo il
codice che le usa entrambe. Il test di regressione mirato — non il
backtest della strategia originale, ma un test costruito apposta per
far scattare la condizione che il fix dovrebbe gestire — è quello che
ha reso visibile l'errore prima che finisse in produzione o in un
verdetto vault sbagliato.

## Stato finale A2+A3+A4

✅ Applicati, ricompilati, **verificati con prova diretta** che il gate
blocca davvero i rientri durante un freeze di conto, su entrambi i
moduli gemelli.

## Non ancora fatto (in attesa di conferma esplicita dell'utente)

- A1 extra: `Alert()` quando un preset sta per scartare un valore
  custom (raccomandazione: sì); cambiare il default di `InpRiskProfile`
  a 0 (raccomandazione: no, vedi discussione in chat).
- A5 (licenza fail-open su 4xx), A6 (WebPush in OnTick), A7
  (ConsecLossBrake morto) — solo verificati, non applicati.
- Fase B del piano d'azione (integrità dei segnali) — non iniziata.

## Collegamenti
[[NEXUS EA - Audit Esterno Cartella MQL5, Verificato Punto per Punto (08-09)]] · [[NEXUS EA - FVG_CONT Prop-Compliant, Protezione Giornaliera Non Basta e Bug SLReclaim (07-09)]] · [[MOC - Trading]]
