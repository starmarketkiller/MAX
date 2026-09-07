---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fvg-cont, prop-firm, slreclaim, bug]
created: 2026-09-07
updated: 2026-09-07
---

# NEXUS EA — FVG_CONT prop-compliant: la protezione giornaliera non basta, e un bug in SLReclaim (07/09)

## Test 1 — solo protezioni (DailyDD 5% + Ruin 5%+Flatten)

Prime protezioni reali attivate su un test (`InpMaxDailyDDPct=5.0`,
`InpRuinDailyLossPct=5.0`, `InpRuinFlatten=true`, entrambe già nel
codice, mai attivate prima d'oggi).

| | Senza protezioni (baseline) | Con protezioni |
|---|---|---|
| Net (3 anni) | +$2655.19 | +$2635.26 |
| Max DD (picco-valle) | 15.5% | **15.5% — identico** |
| Violazioni -5%/giorno | 1 | **1 — identico** |

**Risultato quasi identico, non un errore**: le protezioni si
azzerano ogni giorno (`g_balanceDayStart` viene ricalcolato a ogni
rollover). Il drawdown del 15.5% di FVG_CONT non nasce da un crollo in
UNA giornata (quello lo prenderebbero), nasce da una **serie di 4
giorni consecutivi in perdita** che, sommati, superano il 10% pur
restando ognuno sotto la soglia giornaliera del 5%. Un controllo
giornaliero non può, per costruzione, fermare un drawdown che si
accumula su più giorni.

**Nel codice non esiste ancora una protezione "drawdown dal picco"**
(trailing max drawdown, quello che le prop firm chiamano davvero "max
total drawdown") — solo controlli per-trade, giornalieri (DailyDD,
Ruin) e l'ESL (% del balance CORRENTE, non del picco). Serve
costruirla per davvero risolvere il problema del 10% totale.

## Test 2 — + BE veloce (0.75R) + rientro dopo riconquista stop

| | Solo protezioni | + BE veloce + SLReclaim |
|---|---|---|
| Trade | 168 | **393** (+134%) |
| Net (3 anni) | +$2635.26 | **+$2893.67** (il migliore) |
| PF | 1.92 | 1.58 |
| Max DD | 15.5% | **36.2%** (peggio) |
| Giorno peggiore | -5.0% | **-10.4%** |
| Violazioni -5%/giorno | 1 | **37** |

Il netto sale (il rientro cattura più movimento), ma dal punto di
vista prop-firm è **molto peggio**, non meglio — e il giorno peggiore
(-10.4%) supera nettamente la soglia protetta del 5%, cosa che non
dovrebbe essere possibile con le protezioni attive.

## Bug trovato: SLReclaim bypassa tutte le protezioni di conto

`NXS_ManageSLReclaim()` (in `NXS_SLReclaim.mqh`) apre le posizioni
chiamando `NXS_SafeBuy()`/`NXS_SafeSell()` **direttamente**, senza mai
passare da `NXS_CheckProtections()` (il gate usato da ogni altro
percorso di apertura, incluso il limite giornaliero e il flag di
congelamento del modulo Ruin). Il commento originale del 30/08
descriveva SLReclaim come "più sicuro di un grid" (nessuna media in
perdita, nessuna esposizione aggiuntiva) — vero per la logica di
sizing, ma **falso per il rispetto delle protezioni di conto**: può
riaprire posizioni anche nel mezzo di una giornata già congelata dal
modulo Ruin o oltre il limite di drawdown giornaliero.

Questo spiega esattamente i numeri sopra: le 37 violazioni e il -10.4%
in un giorno arrivano dai rientri SLReclaim che continuano ad aprirsi
ignorando lo stato di protezione.

**Fix**: aggiungere una chiamata a `NXS_CheckProtections()` (o almeno
un controllo su `NXS_RuinFrozen()`) prima delle due chiamate
`NXS_SafeBuy`/`NXS_SafeSell` in `NXS_ManageSLReclaim()`. Non ancora
applicato al momento di scrivere questa nota — prossimo passo.

## Verdetto provvisorio

- Le protezioni giornaliere da sole non bastano per portare FVG_CONT
  sotto i limiti prop-firm tipici (DD totale 10%) — serve una vera
  protezione trailing dal picco di equity, non ancora costruita.
- BE veloce + SLReclaim, anche a parità di protezioni configurate,
  peggiora nettamente la compatibilità prop-firm a causa del bug
  sopra — da rifare dopo il fix prima di trarre conclusioni sull'idea
  in sé (BE veloce/rientro potrebbero ancora essere validi, ma questo
  test non è una misura pulita finché SLReclaim bypassa le protezioni).

## Non ancora fatto

- Fix del bug SLReclaim.
- Costruire una protezione trailing max-drawdown-dal-picco (nuovo
  meccanismo, non ancora presente nel codice).
- Riprovare test 2 dopo il fix.

## Collegamenti
[[NEXUS EA - Nessuna Strategia Testata Supererebbe una Prop Firm (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
