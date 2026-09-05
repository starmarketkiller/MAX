---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bug, p0, profile-enabled, struct-react]
created: 2026-09-05
updated: 2026-09-05
---

# NEXUS EA — terzo cancello silenzioso: STRUCT_REACT + altre 6 strategie mai testabili, audit proattivo (05/09)

## Perché

Prima verifica in assoluto su MT5 reale di STRUCT_REACT (PF Python 2.65,
selettore vero 16, profilo H4/BUY-only già definito in
`NXS_StrategyProfiles.mqh`): risultato **zero trade su 3 anni**, con
`InpStrategySelector=16` e `InpUseStructReact=true` correttamente
echeggiati nel report — nessun errore di configurazione visibile.

## La causa — stesso bug del 28/08 e 02-03/09, mai chiuso davvero

`NXS_Profile_Enabled(name)` è un **terzo cancello indipendente** da
`InpStrat_X` (voglio provarla) e `InpStrategySelector` (isolamento):
risponde alla domanda "questa strategia è abbastanza validata da
aprire ordini" — `return false` = `OPEN_FAIL_PREFLIGHT
/"profile_disabled"`, silenzioso, zero trade a prescindere da tutto
il resto. STRUCT_REACT era esplicitamente commentata alla riga 645
come "già spenta da prima per perdite reali confermate" — ma quella
nota risale a prima di qualunque verifica su questo motore, mai
controllata empiricamente fino ad oggi.

Il bug era già stato trovato e corretto **due volte prima** (PMAX il
28/08, BB_SQUEEZE/ORDER_BLOCK/BOLLINGER il 02-03/09) ma ogni volta
sbloccando solo la strategia del momento, non l'intera classe di
rischio. Oggi, prima di procedere con la coda di test, **audit
proattivo di tutta la coda prioritaria del piano master**.

## Trovate altre 6 strategie reali bloccate allo stesso modo

Hanno un profilo completo (SL/TP/HTF definito in `NXS_Profile_Get`)
ma NON erano nella whitelist `NXS_Profile_Enabled` — qualunque test
nudo futuro avrebbe dato zero trade silenziosi, esattamente come
STRUCT_REACT:

| Strategia | Selettore vero | Flag toggle |
|---|---|---|
| ICHIMOKU | 13 | `InpStrat_ICHIMOKU` |
| RSI_DIV | 14 | `InpStrat_RSI_DIV` |
| FVG_MIT | 19 | `InpStrat_FVG_Mit` |
| OTE_CONT | 25 | `InpStrat_OTE_Cont` |
| MALAYSIAN_SNR | 26 | `InpStrat_MalaysianSNR` |
| WEEKLY_EXP | 32 | `InpUseStrat_WeeklyExp` |

Tutte e 6 sbloccate insieme a STRUCT_REACT in un solo commit
(`NXS_Profile_Enabled` in `NXS_StrategyProfiles.mqh`). `InpStrat_X`
resta `false` di default per ognuna — "abilitata al test" non è
"abilitata di default", la vera protezione resta lì.

## Non ancora fatto

- Nessuna delle 6 appena sbloccate è stata ancora testata sul vero
  MT5 — solo resa testabile. Prossimo giro di code dopo aver
  chiuso la coda attuale (FVG_CONT_V2/SAR_FLIP/TSI — questi ultimi
  due però non hanno implementazione MQL5 reale, vedi nota sotto).
- **FVG_CONT_V2, SAR_FLIP, SAR_ADX20, DARVAS_BOX, DONCHIAN_TURTLE**:
  cercati per nome esatto in tutto `NXS_Strategies*.mqh`, **nessuna
  implementazione MQL5 trovata** — non sono nemmeno arrivabili con
  questo bug, semplicemente non esistono ancora nel codice. La coda
  del piano master le segnava "No" in colonna MQL5: confermato, non
  sono "quasi pronte", sono assenti.
- Non controllato se `NXS_Profile_Enabled` nasconde altre strategie
  oltre a queste 7 — fatto solo per la coda prioritaria del piano
  master (categoria 1), non per l'intero registro di 46.
- **Regola operativa aggiunta**: prima di lanciare un test nudo di
  QUALUNQUE strategia mai provata su MT5, controllare `grep 'name ==
  "NOME"' NXS_StrategyProfiles.mqh` per vedere se compare in
  `NXS_Profile_Enabled` — altrimenti il risultato "zero trade" non
  prova che la strategia sia negativa, prova solo che è bloccata qui.

## Collegamenti
[[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[NEXUS EA - MASTER ROADMAP v3]] · [[MOC - Trading]]
