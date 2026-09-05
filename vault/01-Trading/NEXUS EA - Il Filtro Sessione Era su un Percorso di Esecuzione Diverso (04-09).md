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

## Addendum (05/09) — tre falsi negativi prima del vero risultato

Il primo test con `InpProfileOverlapOnly=true` (MACD H4, 3 anni) è
uscito **identico al centesimo** al nudo (199 trade, PF1.53,
net $1975.49) — sembrava confermare che il gate non facesse nulla.
Non era così: erano tre problemi infrastrutturali distinti, non un
altro bug architetturale.

1. **`NEXUS_EA_v2.mq5` non era stato copiato nei terminali.** Il gate
   era stato scritto solo nel repo git; i terminali (sia quello
   "live" usato da MetaEditor per compilare, sia quello Tester)
   avevano ancora l'.mq5 di giorni prima. Ricompilare senza prima
   copiare il sorgente aggiornato ha prodotto un .ex5 senza il gate —
   stesso identico comportamento del nudo, per costruzione.
   (Tentativo di verificare via string-search nel binario compilato:
   **inconcludente** — MQL5 non mantiene i nomi degli input come
   stringhe leggibili nel .ex5, nemmeno per input sicuramente
   dichiarati come `InpUseStrategyProfiles`. Non è un metodo valido
   per verificare cosa sia stato compilato.)
2. **Il lancio da Bash non passava `/config`.** `& "terminal64.exe"
   /config:"..." &` da Git Bash ha aperto il terminale in modo
   interattivo, senza avviare il Tester — zero righe "AutoTesting" nel
   Journal, il file .htm restava quello di prima. Il metodo affidabile
   resta `Start-Process` in PowerShell (o lo script `.ps1` già usato
   nella coda).
3. **Il test genuino è lentissimo, non bloccato.** Con `Model=4` (tick
   reali) su 3 anni H4, il codice esporta un CSV di 42 strategie ogni
   5 minuti simulati (`[NXS Stats] CSV exported`) — un collo di
   bottiglia I/O che porta il test a ~2h45m reali. La CPU quasi a zero
   durante i controlli ravvicinati aveva fatto temere un hang; il log
   `Tester/logs/<data>.log` (distinto dal Journal principale) mostra
   invece la data simulata che avanza in modo lineare — è il modo
   giusto per distinguere "lento" da "bloccato".

### Risultato vero (dopo il fix reale)

MACD H4, 3 anni, Overlap-only, EA ricompilato e copiato correttamente
in entrambi i terminali:

| | Nudo (baseline) | Overlap-only |
|---|---|---|
| Trade | 199 | **166** |
| Profit factor | 1.53 | **1.74** |
| Net profit | $1975.49 | **$2088.06** |
| Recovery factor | — | 3.57 |
| Max DD equity | — | $584.22 |

Orari di ingresso verificati sul CSV grezzo: concentrati **solo** su
3 ore server (14, 15, 16 — corrispondenti a 12-15 GMT con l'offset del
broker), contro le 24 ore sparse del nudo. Il gate ora restringe
davvero il trading alla sessione Overlap, con meno trade ma qualità
nettamente superiore (PF e profitto netto entrambi in salita).

Il fix è dunque validato empiricamente: `InpProfileOverlapOnly`
funziona come previsto una volta che l'EA compilato riflette
davvero il sorgente aggiornato.

### Analisi CSV per-trade (05/09, richiesta esplicita dell'utente)

Oltre alle statistiche aggregate, analizzati i 166 trade uno per uno
(motivo di chiusura, durata, direzione):

- **Motivo chiusura**: 112 stop loss (67%), 18 take profit (11%), 36
  "altro" (22%) — di questi 36, **4 sono chiusure da protezione
  drawdown** (`NXS:DD` in `NXS_Protections.mqh`, un Equity Stop-Loss
  separato da `InpMaxDailyDDPct` che nell'ini era impostato a 100 per
  disattivarlo — evidentemente non basta a coprire questo meccanismo,
  **non ancora risolto**).

### I 31 trade senza commento — indagati (05/09): un time-stop nascosto molto redditizio

Causa trovata: `NXS_MaxHold_LimitSec()` in `NXS_Strategies.mqh:112`
applica **~40 barre del TF di profilo** come limite di durata massimo
ogni volta che `InpUseStrategyProfiles=true` — **indipendente** da
`InpUseMaxHold`/`InpMaxHoldHours`/`InpProt_MaxHoldHours` (quei flag
coprono solo il ramo "nessun profilo risolto", mai raggiunto quando
il commento della posizione contiene un nome strategia valido, come
sempre in questi test). Per MACD su H4: 40×4h = **160.0h esatte** —
combacia al decimo con tutti e 31 i trade, che infatti hanno
`durata=160.0h` esatta e nessun tag SL/TP (il time-stop chiude prima
che la posizione possa toccare uno dei due).

**Scoperta rilevante**: di questi 31, **30 sono vincenti (WR 96.8%)**,
contributo netto **+$2425.46** — più dell'intero profitto netto del
test ($2088.06). Significa che i restanti 135 trade (chiusi da
SL/TP nativi) sono **collettivamente in perdita di ~-$337**. L'edge
di MACD in questa configurazione sembra concentrarsi quasi tutto nei
trade che sopravvivono fino al time-stop invece di essere chiusi
prima — indizio che il TP sia raramente raggiungibile organicamente
(solo 18 hit su 166) o che lo SL sia troppo stretto rispetto al
respiro naturale del trade.

**Non ancora fatto** (ipotesi da testare, non implementata): il
moltiplicatore "40 barre" è un numero magico hardcoded, non esposto
come input — varrebbe la pena esporlo e testare se allargare la
finestra (es. 60-80 barre) o allontanare il TP catturi più di questo
edge organicamente invece di dipendere da un limite di tempo fisso.
- **Durata**: i trade vincenti restano aperti in media **144h (6
  giorni)**, quelli perdenti solo **56h (2.3 giorni)** — rapporto
  2.6:1, tagliare le perdite e lasciar correre i vincenti, coerente
  con un PF>1 nonostante un win rate basso.
- **BUY vs SELL**: BUY 111 trade/net $2029/WR33.3%, SELL 55
  trade/net $444/WR21.8% — conferma ancora una volta lo schema
  BUY-domina già visto su ADX_RSI/FVG_CONT.
- **Slippage sugli stop**: 0.32 medio, un outlier a 9.74 — frizione
  di mercato reale minima, non un problema strutturale.

Per BOLLINGER Overlap-only (11 trade, vedi nota dedicata): pattern
opposto e preoccupante — le perdite si chiudono in **6.1h**, i
vincenti impiegano **38.6h**, il contrario del comportamento sano
visto su MACD. Coerente con la conclusione già scritta (il filtro
comprime troppo il campione e distorce anche questa dinamica).

## Collegamenti
[[NEXUS EA - MASTER ROADMAP v3]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
