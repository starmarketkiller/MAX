---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fvg-cont, bug, risk-profile, metodo]
created: 2026-09-07
updated: 2026-09-07
---

# NEXUS EA — Step5 ancora bacato: InpRiskProfile non è un vero input MQL5 (07/09)

## Il test

`nexus_fvgcont_step5_regimescore75_riskprofile0_3y` doveva essere il
**vero primo test** di voto-entrata 75 + fix regime multi-TF, rilanciato
dopo aver scoperto che il preset BALANCED sovrascriveva silenziosamente
`InpMinEntryScore` (vedi
[[NEXUS EA - Bug InpRiskProfile, il Preset BALANCED Sovrascriveva Silenziosamente i Parametri Custom (07-09)]]).
L'.ini aggiungeva esplicitamente `InpRiskProfile=0` (Custom) rispetto a
step4.

## Risultato: identico al centesimo a step2/step4, di nuovo

| | step2 (voto 70 reale) | step4 (voto 75 richiesto, bug) | **step5 (voto 75 + fix richiesto)** |
|---|---|---|---|
| Net (3 anni) | $2635.26 | $2635.26 | **$2635.26** |
| Trade | 168 | 168 | **168** |
| PF | 1.92 | 1.92 | **1.92** |
| Sharpe | 2.59 | 2.59 | **2.59** |
| DD balance | 12.42% | 12.42% | **12.42%** |
| DD equity | 22.79% | 22.79% | **22.79%** |

Confermato anche a livello di singolo trade: `deep_csv_analysis.py`
produce output **byte-per-byte identico** (stessi motivi di uscita,
stesso MAE/MFE per bucket, stessi importi) tra step2/step4/step5.

## Causa reale (più grave di quanto scritto ieri)

Il log EA (`Tester\logs\20260907.log`, riga delle 18:11:41.114 — esatto
istante di avvio di step5) mostra ancora:

```
[NEXUS PRESET] BALANCED applied | risk=1.00% maxLot=5.00 maxTrades=12
maxConc=4 ddCap=5.0% minScore=70
```

nonostante l'.ini impostasse esplicitamente `InpRiskProfile=0`. Trovato
il motivo nel codice: in `NXS_Inputs.mqh:42`

```cpp
int      InpRiskProfile      = 2;
```

**la variabile non è dichiarata `input`** — è un `int` globale con
default hardcoded. In MQL5 il file `.ini` del Tester ([TesterInputs])
può impostare **solo** variabili dichiarate `input`; su una variabile
non-`input` la riga dell'.ini viene semplicemente ignorata in silenzio,
senza errori. Non è un problema di "nessun .ini imposta 0" come scritto
ieri — **non esiste alcun modo di impostare `InpRiskProfile` da fuori
il codice**, checché ne dica l'.ini. È strutturalmente sempre 2
(BALANCED), sempre.

## Impatto — più esteso di quanto stimato ieri

Non è invalidato solo step4: **anche step5 non ha mai testato nulla di
diverso**. Il voto-75 + fix regime multi-TF **non è mai stato
verificato**, in nessuna delle due tentate.

Peggio: la nota di ieri diceva "il rischio sistemico non è ancora
quantificato" ipotizzando che bastasse aggiungere `InpRiskProfile=0`
agli `.ini` futuri. **Non basta e non può bastare** — è un bug di
dichiarazione nel codice sorgente, non di configurazione dei test.
Qualsiasi test, passato o futuro, che provi a personalizzare
risk%/maxLot/maxTrades/maxConcurrent/DD%/minScore tramite `.ini` ha
girato e continuerà a girare sempre ai valori BALANCED
(risk 1.0%, maxLot 5.0, maxTrades 12/giorno, maxConc 4, ddCap 5.0%,
minScore 70), **indipendentemente da cosa scriva l'.ini**, finché il
codice sorgente non cambia.

## Fix necessario (non applicato — richiede conferma)

In `NXS_Inputs.mqh:42`, cambiare:
```cpp
int      InpRiskProfile      = 2;
```
in:
```cpp
input int InpRiskProfile      = 2;
```
Un carattere (`input`). Serve poi **ricompilare** l'EA prima di
rilanciare qualunque test che dipenda da questi 6 parametri — non
applicato in questa sessione, per policy nessuna modifica al codice
MQL5 live senza conferma esplicita dell'utente.

## Prossimo passo

Una volta applicato il fix e ricompilato, rilanciare come
`step6` lo stesso identico setup di step4/step5 (voto75 + regime fix +
`InpRiskProfile=0`) — sarà quello il vero primo test.

## Collegamenti
[[NEXUS EA - Bug InpRiskProfile, il Preset BALANCED Sovrascriveva Silenziosamente i Parametri Custom (07-09)]] · [[NEXUS EA - FVG_CONT Prop-Compliant, Protezione Giornaliera Non Basta e Bug SLReclaim (07-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
