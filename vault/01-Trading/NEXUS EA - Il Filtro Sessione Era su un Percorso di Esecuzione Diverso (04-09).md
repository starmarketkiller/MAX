---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sessioni, p0, architettura, mql5]
created: 2026-09-04
updated: 2026-09-04
---

# NEXUS EA — il filtro sessione era su un percorso di esecuzione diverso da quello usato oggi (04/09)

## Perché

Testando l'idea dell'utente di restringere MACD alla sola sessione
Overlap (12-15 GMT, dove si concentra il 36% delle inversioni
storiche): il primo tentativo (`InpXScoreMin` senza `input`, corretto
in un commit precedente oggi) è rimasto senza effetto **anche dopo il
fix**. Investigato più a fondo.

## La causa vera — non un bug residuo, un'architettura diversa

Il sistema `InpUseSessions`/`InpAsianScoreMin`/.../`InpOverlapScoreMin`
alimenta `NXS_ResolvedEntryThreshold()`, controllato dentro
`NXS_TryExecuteRC()` — ma quella funzione appartiene al **percorso di
esecuzione istituzionale legacy**. Tutti i test di oggi (e, a quanto
pare, la maggior parte della sessione estiva) usano invece
`InpUseStrategyProfiles=true`, che attiva un ciclo di esecuzione
**separato** in `NEXUS_EA_v2.mq5` con un commento esplicito:

> "Ogni strategia apre in INDIPENDENZA col SUO profilo... **senza i
> gate soft (MTF/velocity/exhaustion/score/confluence)**"

Il sistema di soglie per sessione fa parte proprio di quei "gate
soft" bypassati di proposito in questa modalità. Non è un bug nel
senso di "codice rotto" — è un secondo sistema, mai collegato al
percorso realmente in uso da mesi di test.

## Verifica empirica

Test MACD con `InpAsianScoreMin=999` (e le altre 3 sessioni bloccate),
`InpOverlapScoreMin=0`, risultato **identico al centesimo** al nudo
(199 trade, PF1.53). Controllati gli orari reali dei trade: sparsi su
18 ore diverse del giorno, nessuna concentrazione nella finestra
Overlap — conferma diretta che il gate non stava facendo nulla.

## Correzione applicata

Aggiunto `InpProfileOverlapOnly` (default `false`), un gate diretto
dentro il ciclo `if(InpUseStrategyProfiles){...}` (il percorso
realmente in uso): se attivo, scarta ogni segnale a meno che
`g_session == SESS_OVERLAP`. Non tocca il sistema legacy — è un
secondo meccanismo indipendente, scoped al percorso corretto.
Compilato pulito.

## Non ancora fatto

- Non verificato se il sistema legacy (`InpUseSessions`+soglie)
  produce qualche effetto quando `InpUseStrategyProfiles=false` — non
  testato, nessuno dei test di oggi usa quella modalità.
- `InpProfileOverlapOnly` copre solo Overlap — se serve testare le
  altre 4 sessioni singolarmente servirebbe un enum invece di un bool,
  non fatto per ora (scope minimo).
- Test rilanciati con il fix vero, risultati non ancora analizzati al
  momento di scrivere questa nota.

## Collegamenti
[[NEXUS EA - MASTER ROADMAP v3]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
