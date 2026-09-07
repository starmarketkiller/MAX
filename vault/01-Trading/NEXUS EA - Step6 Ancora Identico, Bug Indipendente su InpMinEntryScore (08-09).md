---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fvg-cont, bug, entry-score, metodo]
created: 2026-09-08
updated: 2026-09-08
---

# NEXUS EA — Step6 ancora identico: bug indipendente su InpMinEntryScore (08/09)

## Il test

Dopo il fix di `InpRiskProfile` (07/09, aggiunta la keyword `input`,
ricompilato — vedi
[[NEXUS EA - Step5 Ancora Bacato, InpRiskProfile Non e' un Vero Input MQL5 (07-09)]]),
rilanciato `nexus_fvgcont_step6_regimescore75_riskprofile0_fixed_3y`
(PID 1496, 21:53:01→~00:5x), stesso identico setup di step4/step5
(voto75 + regime fix + `InpRiskProfile=0`). Log confermato:
`[NEXUS PRESET] CUSTOM (using raw input values)` alle 21:53:13 — il
fix di ieri funziona, il preset BALANCED non sovrascrive più nulla.

## Risultato: identico al centesimo, per la TERZA volta

| | step2/step4/step5 | **step6 (dopo fix RiskProfile)** |
|---|---|---|
| Net (3 anni) | $2635.26 | **$2635.26** |
| Trade | 168 | **168** |
| PF | 1.92 | **1.92** |
| DD balance/equity | 12.42% / 22.79% | **12.42% / 22.79%** |
| Uscite per motivo (sl/tp/other/dd) | identiche | **identiche** |

`deep_csv_analysis.py` conferma byte-per-byte lo stesso identico
risultato trade-per-trade di step2/4/5.

## Causa: secondo bug indipendente, stessa classe

`InpMinEntryScore` (`NXS_Inputs.mqh:155`) è dichiarato:
```cpp
double   InpMinEntryScore    = 50.0;
```
**senza `input`** — bug indipendente da `InpRiskProfile` (quello era
sul SELETTORE di preset; questo è sulla soglia stessa). Anche con
`InpRiskProfile=0` che impedisce a `NXS_ApplyPreset()` di sovrascrivere
`g_run_MinEntryScore`, la riga `g_run_MinEntryScore = (int)InpMinEntryScore;`
(`NXS_RuntimeSettings.mqh:53`) legge comunque il valore **hardcoded in
fase di compilazione**: l'.ini che scrive `InpMinEntryScore=75.0` non ha
alcun effetto, sempre, indipendentemente da `InpRiskProfile`.

**Prova diretta nei dati**: ogni singolo trade FVG_CONT di step6 (168/168)
ha nel commento `NEXUS_v2.50|FVG_CONT|70.0|PERIO...` — il campo è
`s.score` (punteggio del singolo segnale, `NXS_Execution.mqh:503`), e
**per FVG_CONT risulta fisso a 70.0 su ogni trade, senza eccezioni**.
Se la soglia reale fosse stata 75, ogni segnale (che scora sempre 70.0)
sarebbe stato scartato — **zero trade**, non 168 identici a prima. Il
fatto che il conteggio non sia cambiato di una virgola è la controprova
diretta: la soglia usata a runtime non era 75, qualunque fosse il suo
valore esatto (50 o 70, funzionalmente indistinguibili qui perché
FVG_CONT non produce mai un punteggio tra 50 e 70).

**Nota a margine, da approfondire**: FVG_CONT sembra restituire un punteggio
segnale costante (70.0) invece di un punteggio graduato — non è chiaro se
sia voluto o un altro sintomo di configurazione incompleta.

## Audit più ampio (richiesto dall'utente, cartella MQL5 completa)

Incrociate tutte le 105 chiavi `Inp*` usate in ogni `.ini` del progetto
(non solo FVG_CONT) contro le dichiarazioni in `NXS_Inputs.mqh`.
**5 variabili della stessa classe di bug**, usate da almeno un `.ini`
ma mai realmente impostabili:

| Variabile | Default reale (ignora l'.ini) | Impatto |
|---|---|---|
| `InpMinEntryScore` | 50.0 | Questo — voto75 mai testato, 3 tentativi falliti (step4/5/6) |
| `InpRuinDailyLossPct` | **15.0%**, non 5.0% | Il test "prop-compliant" (step2, 07/09) credeva di aver forzato il freeze-conto al 5%/giorno — in realtà è rimasto al 15%, mai vincolante in quel test. La protezione che ha davvero agito era solo `InpMaxDailyDDPct` (quella è `input` vera) |
| `InpRuinEnable` | true (default) | Innocuo qui: ogni `.ini` provava comunque a metterlo `true` |
| `InpRuinFlatten` | true (default) | Innocuo, stesso motivo |
| `InpGateMode` | 1 (default) | Non usato nei test FVG_CONT finora, impatto altrove non verificato |

Altri 9 nomi apparentemente "non trovati" in `NXS_Inputs.mqh` sono
falsi allarmi: sono `input` corretti, dichiarati in altri file
(`NXS_SplitTrade.mqh`, `NXS_RiskShield.mqh`, `NXS_Strategies.mqh`,
`NXS_ElliottFilter.mqh`) — nessun bug lì.

## Fix necessario (non applicato — in attesa di conferma esplicita)

In `NXS_Inputs.mqh:155`:
```cpp
double   InpMinEntryScore    = 50.0;
```
→
```cpp
input double   InpMinEntryScore    = 50.0;
```
Poi ricompilare. Stesso trattamento raccomandato per `InpRuinDailyLossPct`
se si vuole che i test "prop-compliant" futuri possano davvero fissare
la soglia di freeze-conto giornaliera a un valore diverso dal 15%
hardcoded.

## Prossimo passo

Applicare il fix + ricompilare + rilanciare come `step7` lo stesso
identico setup — sarà il quarto tentativo e, se non emergono altri
cancelli dello stesso tipo, il primo vero test di voto75+regime-fix.

## Collegamenti
[[NEXUS EA - Step5 Ancora Bacato, InpRiskProfile Non e' un Vero Input MQL5 (07-09)]] · [[NEXUS EA - Bug InpRiskProfile, il Preset BALANCED Sovrascriveva Silenziosamente i Parametri Custom (07-09)]] · [[NEXUS EA - FVG_CONT Prop-Compliant, Protezione Giornaliera Non Basta e Bug SLReclaim (07-09)]] · [[MOC - Trading]]
