---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bug, risk-profile, preset, metodo]
created: 2026-09-07
updated: 2026-09-07
---

# NEXUS EA — Bug InpRiskProfile: il preset BALANCED sovrascriveva silenziosamente i parametri custom (07/09)

## Il bug

`InpRiskProfile` (`NXS_Inputs.mqh:42`) ha default `2` (`PRESET_BALANCED`).
In `OnInit()` (`NEXUS_EA_v2.mq5:688-689`) viene chiamato `NXS_Runtime_Init()`
(legge tutti gli `Inp*` custom, incluso quelli passati via `.ini`) e SUBITO
DOPO `NXS_ApplyPreset()` — che se `InpRiskProfile != 0` **sovrascrive
incondizionatamente**:

- `InpRiskPercent` → 1.0%
- `InpMaxLot` → 5.0
- `InpMaxTradesPerDay` → 12
- `InpMaxConcurrent` → 4
- `InpMaxDailyDDPct` → 5.0%
- `InpMinEntryScore` → 70

Nessuno dei file `.ini` di test di oggi (né di sessioni precedenti,
verosimilmente) impostava esplicitamente `InpRiskProfile=0` (Custom).
Risultato: **qualsiasi valore custom messo nell'.ini per questi 6
parametri veniva ignorato**, sostituito dai valori BALANCED.

## Come è stato trovato

Il test `step4` (FVG_CONT, `InpMinEntryScore=75.0`, regime multi-TF
corretto — [[NEXUS EA - Bug Regime Multi-TF nel Voto Finale (07-09)]])
ha prodotto un risultato **identico al centesimo** a `step2`
(`InpMinEntryScore` non impostato = default codice 50, ma protetto a
DD 5%): stesso net ($2635.26), stesso PF (1.92), stessi 168 trade,
stessa ogni singola cifra di drawdown/consecutive/ecc. Impossibile per
caso con un gate di score realmente diverso (50→75, +regime fix).

Confermato in modo definitivo dal log stesso dell'EA
(`Tester\logs\20260907.log`), presente su OGNI test di oggi:
```
[NEXUS PRESET] BALANCED applied | risk=1.00% maxLot=5.00 maxTrades=12
maxConc=4 ddCap=5.0% minScore=70
```
Indipendentemente da cosa dicesse l'.ini.

## Impatto sui test di oggi (FVG_CONT)

| Step | Intento | Cosa girava davvero |
|---|---|---|
| step1 nuda | DD100% (disattivato), maxTrades illimitati | DD 5%, maxTrades 12/g |
| step2 propcompliant | DD 5% (voluto) | DD 5% — **coincide, valido** |
| step3 SLReclaim | DD 5% (voluto), maxTrades illimitati | DD 5% coincide; maxTrades 12/g mai vincolante (~127 trade/anno) — **sostanzialmente valido** |
| step4 regimescore75 | voto 75 + regime fix | voto **70** (il fix non è mai stato testato) — **test invalidato, da rifare** |

Le conclusioni su step2/step3 restano valide (i valori custom
coincidevano con quelli forzati dal preset, o il vincolo non era mai
binding). **Solo step4 è da buttare**: non abbiamo mai davvero
verificato l'effetto di voto-75 + regime corretto.

## Cosa NON è invalidato

La scoperta di [[NEXUS EA - FVG_CONT Prop-Compliant, Protezione Giornaliera Non Basta e Bug SLReclaim (07-09)]]
(protezione giornaliera 5% non basta a contenere un DD che si accumula
su più giorni) è **rinforzata, non invalidata**: la protezione 5% era
davvero attiva (dal preset) durante quel test, e nonostante questo il
DD equity è arrivato al 22.79% — conferma diretta, non per caso.

## Rischio sistemico (non ancora quantificato)

Ogni `.ini` di test scritto in QUALSIASI sessione precedente di questo
progetto che non impostava esplicitamente `InpRiskProfile=0` ha
potenzialmente ignorato i valori custom di risk%/maxLot/maxTrades/
maxConcurrent/DD%/minScore messi nell'.ini, sostituendoli con i valori
BALANCED. Non è detto che questo abbia cambiato i verdetti (spesso i
valori coincidevano o il vincolo non era mai raggiunto — es. maxTrades
12/giorno non stringe quasi mai su H4/D1), ma è un fattore di
incertezza da tenere presente retroattivamente. Non riverificato a
ritroso per costo/tempo — da fare se un risultato dubbio dipende
proprio da uno di questi 6 parametri.

## Fix applicato

Aggiunto `InpRiskProfile=0` esplicito a tutti gli `.ini` di test da
oggi in poi. Rilanciato `step4` come
`nexus_fvgcont_step5_regimescore75_riskprofile0_3y.ini` (stesso
identico setup di step4, con `InpRiskProfile=0` aggiunto) — questo è
il VERO primo test del voto-75 + regime corretto.

## Collegamenti
[[NEXUS EA - FVG_CONT Prop-Compliant, Protezione Giornaliera Non Basta e Bug SLReclaim (07-09)]] · [[NEXUS EA - Bug Regime Multi-TF nel Voto Finale (07-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
