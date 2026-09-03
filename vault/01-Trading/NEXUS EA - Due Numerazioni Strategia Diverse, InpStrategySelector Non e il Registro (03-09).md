---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, p0, registry, selector, mql5, methodology]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — Due numerazioni diverse per le strategie: `InpStrategySelector` NON usa il registro (03/09)

## Perché

Il primo test isolato di BOLLINGER (M5 nuda, `InpStrategySelector=7`,
preso da `NXS_StrategyRegistry.mqh`) ha dato **0 trade**. L'utente ha
notato dal vivo che la curva equity restava piatta durante l'intero
test — segnale corretto, non rumore. Indagando: `InpStrategySelector=7`
non isola affatto BOLLINGER.

## Il problema

`NXS_StrategyRegistry.mqh` mappa nome→indice **alfabeticamente**:

```
0=3COMMAS_BOT  1=ADX_RSI  2=AMD_CONT  3=AMD_REVERSAL  4=BAR_UPDN
5=BB_SQUEEZE   6=BJORGUM  7=BOLLINGER 8=BREAKOUT_ACC  9=DISP_REBAL ...
```

Ma il gate che **davvero** isola la strategia nel Tester —
`NXS_SelectorAllows(idx)` in `NXS_Globals.mqh`, richiamato all'inizio
di ogni `NXS_Strat_X()` in `NXS_Strategies*.mqh` — usa una numerazione
**completamente diversa e indipendente** (storica, ordine di
introduzione nel codice, non alfabetica):

```mql5
// NXS_Globals.mqh
bool NXS_SelectorAllows(int idx){
   return (InpStrategySelector == 0 || InpStrategySelector == idx);
}

// NXS_Strategies.mqh (una riga per strategia)
if(!InpStrat_ADX_RSI  || !NXS_SelectorAllows(1))  return s;
if(!InpStrat_BOLLINGER|| !NXS_SelectorAllows(2))  return s;   // <- non 7!
if(!InpStrat_MACD     || !NXS_SelectorAllows(3))  return s;
if(!InpStrat_SAR      || !NXS_SelectorAllows(4))  return s;
if(!InpStrat_TSI      || !NXS_SelectorAllows(5))  return s;
if(!InpStrat_BJORGUM  || !NXS_SelectorAllows(6))  return s;
...
if(!InpStrat_PivotWick|| !NXS_SelectorAllows(49)) return s;
```

Con `InpStrategySelector=7` (il numero registro di BOLLINGER),
`NXS_SelectorAllows(2)` valuta `7==0` falso, `7==2` falso → la
funzione ritorna un segnale vuoto **prima ancora di guardare le
bande di Bollinger** — zero trade garantiti, indipendentemente dal
mercato, dal timeframe, da qualunque altro parametro. Non è "BOLLINGER
non ha edge su M5", è "BOLLINGER non è mai stata eseguita".

## Tabella di confronto (parziale, strategie con `NXS_SelectorAllows` verificato)

| Strategia | Indice registro (alfabetico) | Indice `NXS_SelectorAllows` (vero) | Coincidono? |
|---|---|---|---|
| ADX_RSI | 1 | 1 | ✅ (caso) |
| **BOLLINGER** | **7** | **2** | ❌ |
| MACD | 22 | 3 | ❌ |
| SAR | 35 | 4 | ❌ |
| TSI | 42 | 5 | ❌ |
| BJORGUM | 6 | 6 | ✅ (caso) |
| LIQ_SWEEP | 19 | 7 | ❌ |
| FVG_CONT | 12 | 8 | ❌ |
| BREAKOUT_ACC | 8 | 9 | ❌ |
| LONDON_BO | 21 | 10 | ❌ |
| EMA_PULLBACK | 11 | 11 | ✅ (caso) |
| BB_SQUEEZE | 5 | 12 | ❌ |
| ICHIMOKU | 14 | 13 | ❌ |
| RSI_DIV | 33 | 14 | ❌ |
| ORDER_BLOCK | 27 | 15 | ❌ |
| STRUCT_REACT | 39 | 16 | ❌ |
| SWING_FALSEBREAK | 40 | 41 | ❌ |
| Z_SCORE_BREAKOUT | 45 | 42 | ❌ |
| BAR_UPDN | 4 | 43 | ❌ |
| PMAX | 30 | 44 | ❌ |
| MACD_SMA200 | 23 | 45 | ❌ |
| RSI_DIV_PINE | 34 | 46 | ❌ |
| ICHIMOKU_HULL_MACD | 15 | 47 | ❌ |
| 3COMMAS_BOT | 0 | 48 | ❌ |
| **PIVOT_WICK** | 29 | **49** | ❌ (ma i test di oggi hanno usato correttamente 49, non 29) |
| IFVG | 16 | 18 | ❌ |
| FVG_MIT | 13 | 19 | ❌ |
| OB_MIT | 26 | 20 | ❌ |
| MALAYSIAN_SNR | 24 | 26 | ❌ |

**Su 29 strategie verificate, solo 3 coincidono per puro caso**
(ADX_RSI, BJORGUM, EMA_PULLBACK). Tutte le altre, se isolate usando il
numero del registro invece di quello vero, **non aprono mai un trade**
o — scenario peggiore — **isolano silenziosamente una strategia
diversa da quella richiesta** (es. registro 22=MACD potrebbe
coincidere con l'indice vero di un'altra strategia, aprendo trade
attribuiti per errore).

## Perché i test di oggi su PIVOT_WICK sono salvi

Tutta la batteria PIVOT_WICK di oggi (c1-c6, d1-d6) ha usato
`InpStrategySelector=49` — che è il numero **vero**
(`NXS_SelectorAllows(49)`), non quello del registro (29). Chi ha
costruito quei file `.ini` (questa stessa sessione, prima di un
riassunto del contesto) evidentemente già sapeva di usare il numero
giusto. Il mio errore su BOLLINGER è stato prendere il numero dal
registro (fonte comoda ma sbagliata per questo scopo) invece di
grep-are `NXS_SelectorAllows(` direttamente in `NXS_Strategies*.mqh`.

## Rischio per i dati storici

Il roadmap (`MASTER ROADMAP v3`, §P0.5) avvertiva esattamente di
questo rischio: "Eliminare mappe duplicate... Nessuna strategia può
finire su un default generico senza errore esplicito." Qui il rischio
non è teorico: **qualunque sweep storico che abbia usato il numero del
registro invece del numero vero ha prodotto risultati nulli o
attribuiti alla strategia sbagliata, senza errore visibile** (nessun
crash, nessun log di avviso — solo un segnale sempre vuoto o un'altra
strategia in esecuzione senza saperlo). Non ho verificato se questo
sia successo in passato (richiederebbe controllare quale numero è
stato usato in ogni `.ini`/`.set` storico) — segnalato come rischio
aperto, non confermato come già accaduto.

## Correzione applicata

Rilanciato il test BOLLINGER M5 nuda con `InpStrategySelector=2`
(il numero vero), report `nxs_bollinger_step1b_m5_nuda_selector2`, in
corso.

## Regola operativa da questo punto in poi

**Mai usare il numero di `NXS_StrategyRegistry.mqh` per
`InpStrategySelector`.** L'unica fonte affidabile è grep-are
`NXS_SelectorAllows(N)` nella riga di guardia della funzione
`NXS_Strat_X()` specifica in `NXS_Strategies*.mqh` (o
`NXS_ReusePerformancePack.mqh`/`NXS_Strategies_SMC.mqh` per le
strategie che vivono lì). Il registro serve per nome→stringa (dashboard,
report), non per isolare una strategia nel Tester.

## Non ancora verificato

- Le ~17 strategie rimanenti del registro (AMD_CONT, AMD_REVERSAL,
  DISP_REBAL, ELLIOTT, JUDAS_SWING, LDN_REVERSAL, LIQ_VOID,
  NY_REVERSAL, OTE_CONT, PO3, RANGE_FADE, SH_BMS_RTO, SILVER_BULLET,
  SMS_BMS_RTO, THREE_BAR_DELIVERY_BREAK, TURTLE_SOUP, WEEKLY_EXP) non
  hanno una chiamata `NXS_SelectorAllows` trovata nei file controllati
  — o vivono altrove (non cercato ovunque), o non hanno
  un'implementazione MQL5 reale (coerente con quanto già noto per
  THREE_BAR_DELIVERY_BREAK).
- Se qualche `.set`/`.ini` storico abbia davvero usato il numero
  registro invalidando risultati passati — non controllato, richiede
  un audit dedicato se si vuole chiuderlo con certezza.
- Nessuna modifica alla numerazione stessa fatta qui (correggere il
  disallineamento — es. far coincidere i due schemi — è un cambiamento
  con impatto ampio su ogni `.ini`/`.set` esistente, richiede
  discussione esplicita prima di toccare `NXS_Globals.mqh`/
  `NXS_StrategyRegistry.mqh`).

## Collegamenti
[[NEXUS EA - MASTER ROADMAP v3]] · [[NEXUS EA - Ricerca Scalp BAR_UPDN e BREAKOUT_ACC, Piano BOLLINGER+RSI (02-09)]] · [[MOC - Trading]]
