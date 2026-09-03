---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, pivot-wick, backtest, mt5, research]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — PIVOT_WICK: step2 (tpMult=1.0) e OneShotLevel analizzati, nessun fix (03/09)

## Perché questa nota

Sessione in background dopo `/clear`, ripartita da
[[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]]
(Fase 0, punto 1: "PIVOT_WICK step2 in coda, aspettare il risultato").
Trovati nel frattempo **tre report Tester MT5 non ancora analizzati** in
`Terminal/D0E8209F.../`: `nxs_pivotwick_step2_tp1.htm`,
`nxs_pivotwick_c1_baseline3m.htm`, `nxs_pivotwick_c2_oneshot.htm` — gli
ultimi due successivi alla nota post-maratona (16:41 e 17:02 del 03/09,
probabilmente prodotti da un'altra sessione/agente desktop in
parallelo). Parsati con `server/research_scripts/parse_mt5_tester_report.py`
+ analisi manuale dei deal CSV grezzi (livelli entrata/uscita, motivo
chiusura, side, streak).

## Risultato 1 — step2 (tpMult 2.2→1.0): ancora negativo

Periodo M15 2025-11-01→2026-08-26 (10 mesi), `InpPivotWickRequireWick=false`.

| Metrica | Valore |
|---|---|
| Trade | 1538 |
| PF | **0.90** |
| Net | **-843.96** |
| Max DD balance | 929.02 |
| Sharpe | -3.81 |

Confermato: abbassare `tpMult` da 2.2 a 1.0 (target più vicino, deciso
dopo l'analisi MFE della sessione precedente) **non basta da solo** —
resta sotto pareggio su campione ampio (1538 trade, non un artefatto di
campione piccolo).

## Risultato 2 — c1 (baseline pulita) vs c2 (OneShotLevel=true)

Stesso periodo per entrambi (M15 2026-06-01→2026-08-26, 3 mesi, per
confronto pulito), stessa build (commit `755f3e4`, che ha aggiunto
`InpPivotWickOneShotLevel`/`InpPivotWickRequireCloseConfirm`/
`InpPivotWickAvoidBuildup`, di default tutti `false`). c2 attiva **solo**
`InpPivotWickOneShotLevel=true` (ogni livello pivot tradabile una sola
volta, la "zona fresh/non-fresh"), gli altri due restano `false`.

| | c1 baseline | c2 OneShotLevel=true | Δ |
|---|---|---|---|
| Trade | 503 | 362 | -28% |
| Win rate | 44.9% | 45.0% | ≈uguale |
| PF | 0.79 | 0.77 | leggero peggioramento |
| Net | -546.74 | -431.07 | meno negativo (meno trade) |
| Avg win | $8.88 | $8.81 | ≈uguale |
| Avg loss | -$9.19 | -$9.36 | leggero peggioramento |
| Max consec losses | 11 | 11 | uguale |
| Buy vs Sell | entrambi negativi, nessun bias direzionale | entrambi negativi | uguale |
| Uscite | 275 SL / 225 TP | 198 SL / 161 TP | proporzione uguale |

**Diagnosi onesta**: OneShotLevel filtra un sottoinsieme dei segnali
(-28% trade) ma **non cambia la qualità** del sottoinsieme che resta —
win rate, avg win/loss e proporzione SL/TP sono statisticamente
identici a c1. Il net loss si riduce solo perché si tradano meno volte
lo stesso edge negativo, non perché l'edge migliori. Coerente con lo
schema già visto altre volte in questa indagine (floor ATR, D1-alignment,
ecc.): **un filtro che riduce il volume non è automaticamente un fix**,
va verificato che cambi PF/expectancy, non solo il net.

## Perché è probabilmente un problema di logica, non di tuning

Win rate 44.9-45.0% con avg win ≈ avg loss (payoff ratio ~0.94-0.96,
cioè target e stop quasi alla pari in valore atteso per trade, coerente
con `tpMult=1.0` cioè R:R ≈1:1) è matematicamente sotto pareggio: a
R:R 1:1 servirebbe WR >50% per essere profittevoli, qui è sotto. Nessun
filtro provato finora (tpMult, wick richiesto flag di default off,
OneShotLevel) ha spostato il win rate — solo il volume. Per la
[[NEXUS EA - MASTER ROADMAP v3]] (§P2.4, punto 1: "trigger base senza
filtri" va verificato PRIMA di ottimizzare le uscite) questo è il
segnale che manca ancora un passaggio: **verificare se il trigger
pivot+wick ha davvero un edge predittivo di direzione**, indipendente da
SL/TP, prima di continuare a girare la manopola dei filtri. Non ancora
fatto: un check diretto (es. % di volte che il prezzo si muove nella
direzione del segnale entro N barre, senza SL/TP fissi — MFE/MAE puro)
per separare "il pattern non predice nulla" da "il pattern predice ma
l'uscita/il timing lo vanifica".

## Addendum — c3 RequireCloseConfirm=true: primo segnale reale (03/09, 17:29)

Scoperta durante la sessione: un'intera batteria di test PIVOT_WICK
(`c1`...`c6`, poi `d1`...`d6`) era già stata costruita e lanciata da
questa stessa sessione **prima** di un riassunto del contesto — gira in
background via `terminal64.exe /config:` orchestrato da script
PowerShell (`wait_and_run_combos.ps1`/`wait_and_run_battery_d.ps1` in
`tmp/strategy_validation/`), non serve un altro agente per lanciarla.
c3 (`InpPivotWickRequireCloseConfirm=true`, stesso periodo 3 mesi di
c1/c2) appena completato:

| | c1 baseline | c2 OneShotLevel | **c3 RequireCloseConfirm** |
|---|---|---|---|
| Trade | 503 | 362 | **278** |
| Win rate | 44.9% | 45.0% | **47.8%** |
| PF | 0.79 | 0.77 | **0.91** |
| Net | -546.74 | -431.07 | **-122.26** |
| Avg win/loss | 8.88/-9.19 | 8.81/-9.36 | 9.32/-9.35 |
| Buy/Sell netPnL | entrambi negativi | entrambi negativi | **Sell +$32.6 (71/138), Buy -$149 (62/140)** |

A differenza di OneShotLevel, qui il **win rate si sposta davvero**
(44.9%→47.8%, +2.9pp) non solo il volume — prima conferma che
richiedere la chiusura della candela prima di validare il pattern (non
solo il tocco intrabar) è un miglioramento di qualità del segnale, non
solo un filtro di quantità. PF resta sotto 1 ma il divario si è
dimezzato. Emerge anche un possibile bias direzionale (Sell positivo,
Buy negativo) da verificare su campione più ampio prima di trarre
conclusioni. **c4 (buildup), c5 (RequireWick), c6 (tutti combinati)**
ancora in coda nella stessa batteria — se c6 combina questi guadagni,
la conclusione "probabile problema di logica" di questa nota andrebbe
rivista.

## Addendum 2 — c4 AvoidBuildup (no-op sospetto) e c5 RequireWick (peggiora) (03/09, 18:19)

| | c1 baseline | c3 CloseConfirm | **c4 AvoidBuildup** | **c5 RequireWick** |
|---|---|---|---|---|
| Trade | 503 | 278 | **503 (identico a c1)** | **87** |
| Win rate | 44.9% | 47.8% | **44.9% (identico)** | **41.4%** |
| PF | 0.79 | 0.91 | **0.79 (identico)** | **0.68** |
| Net | -546.74 | -122.26 | **-546.74 (identico)** | -143.98 |

**c4 (AvoidBuildup=true)**: risultato **identico a c1 fino al centesimo**
(stesso numero di trade, stesso net, stesso DD). Verificato nel report
che il parametro è stato caricato correttamente
(`InpPivotWickAvoidBuildup=true` presente nei "Dati in ingresso"), e
verificato nel codice (`NXS_Strategies.mqh` righe 784-794) che
`buildupOk` è davvero cablato nel gate d'ingresso sia BUY che SELL —
non è un input morto. Conclusione più probabile: **il filtro non ha mai
scartato un solo tocco in 3 mesi** (soglia `BuildupMinATR=0.8` mai
raggiunta in negativo su GOLD M15, o le barre controllate — indice 2 a
2+6, non 1 a 6 — guardano un punto leggermente diverso da quello
inteso). Non ancora isolato quale delle due cause sia quella vera —
richiederebbe un contatore diagnostico nel codice, non fatto qui
(nessuna modifica MQL5 in questa sessione).

**c5 (RequireWick=true)**: chiude la domanda della Fase 0 originale —
**peggiora**, non solo riduce il campione. WR scende sotto la baseline
(44.9%→41.4%), PF scende (0.79→0.68). Il wick di rigetto vero, da solo,
non è un fix.

**Bilancio dei singoli finora**: su 3 fix isolati testati (OneShotLevel,
RequireCloseConfirm, AvoidBuildup, RequireWick — 4 in totale), **solo
RequireCloseConfirm mostra un effetto reale e positivo**. AvoidBuildup
sembra strutturalmente inerte su questo dataset, RequireWick peggiora,
OneShotLevel riduce solo il volume. Prossimo dato decisivo: **c6
(tutti combinati)** — dirà se CloseConfirm da solo regge o se
combinarlo con gli altri (anche quelli inerti/negativi in isolamento)
cambia il quadro.

## Addendum 3 — c6 (tutti e 4 combinati): campione collassato, inconcludente (03/09, 18:41)

`InpPivotWickOneShotLevel=true` + `RequireCloseConfirm=true` +
`AvoidBuildup=true` + `RequireWick=true` insieme, stesso periodo 3 mesi:
**5 trade totali** (PF0.62, net -9.48). Campione troppo piccolo per
qualunque conclusione statistica — non è un risultato "buono" o
"cattivo", è inutilizzabile. RequireWick da solo aveva già ridotto a 87
trade (17% del baseline); impilarci sopra CloseConfirm+OneShotLevel
schiaccia il campione a quasi zero, coerente con la lezione già vista
più volte in questa indagine (mai impilare filtri prima di misurare
l'effetto isolato — qui confermato nel modo più diretto possibile).

## Sintesi round c1-c6 (chiuso)

| Test | Trade | WR | PF | Verdetto |
|---|---|---|---|---|
| c1 baseline | 503 | 44.9% | 0.79 | riferimento |
| c2 OneShotLevel | 362 | 45.0% | 0.77 | solo volume, nessun edge |
| **c3 RequireCloseConfirm** | 278 | **47.8%** | **0.91** | **unico miglioramento reale** |
| c4 AvoidBuildup | 503 | 44.9% | 0.79 | inerte (identico a c1, verificato nel codice) |
| c5 RequireWick | 87 | 41.4% | 0.68 | peggiora |
| c6 tutti combinati | 5 | — | — | campione collassato, inconcludente |

**Conclusione onesta**: nessuno dei 4 fix isolati porta PIVOT_WICK sopra
pareggio da solo. RequireCloseConfirm è l'unico con un effetto di
qualità reale (non solo di volume) ma non basta (PF 0.91 < 1). Non
vale la pena testare altre combinazioni tra questi 4 (AvoidBuildup è
inerte quindi non aggiunge né toglie, RequireWick peggiora quindi va
escluso da qualunque combo futura). La direzione utile ora è il lato
**uscite** (batteria `d1`-`d6`, partial ATR/pip fisso/volume, streak
sizing, veto regime — parte da questa stessa sessione automaticamente
subito dopo c6, sulla baseline nuda non su c3) o accettare che
PIVOT_WICK, con questo trigger, non ha edge sufficiente e richiede una
revisione della logica di ingresso più profonda (non solo filtri
aggiuntivi) prima di continuare a investire tempo qui.

## Addendum 4 — d1 (ATR partial) è un duplicato di c1, non un test nuovo (03/09, ~19:10)

`nexus_pivotwick_d1_atrpartial.ini` imposta solo `InpEnableSplit=true`
— ma verificato in `NXS_Inputs.mqh:575` che il default di
`InpEnableSplit` è **già `true`** dal fix del 01/09 (era una delle 4
variabili senza `input`, quindi sempre attiva silenziosamente in ogni
test di questa sessione, SAR/EMA_PULLBACK inclusi — vedi commento
`NXS_Inputs.mqh:557-564`). Il partial ATR (`InpTP1_ATR=1.5`,
`InpTP2_ATR=3.0`, `NXS_SplitTrade.mqh:121-132`) era quindi **già attivo
nella baseline c1** tanto quanto in d1. Risultato: **d1 identico a c1
al centesimo** (503 trade, PF0.79, net -546.74, DD 606.53) — non
perché il partial non funzioni, ma perché il test non isola nulla
(confronta "split ON" contro "split ON", non contro "split OFF").
Stessa classe di errore metodologico già vista altre volte (§12 Master
Roadmap: "confrontare report senza build/config hash" — qui config
identica travestita da test diverso). **Non ripetuto qui** (nessuna
modifica MQL5, solo osservazione) — se si vuole isolare l'effetto del
partial ATR servirebbe `InpEnableSplit=false` come baseline di
confronto, oppure variare `InpTP1_ATR`/`InpTP2_ATR` dai default.
d2 (`InpUseFixedPipPartial`), d3 (`InpUseVolumePartial`), d5
(`InpProfileRegimeVeto`) sono invece flag genuinamente distinti dal
default — verificati nell'`.ini`, questi restano test validi.

## Addendum 5 — d4 StreakSizing: identico a c1, ma NON per lo stesso motivo di d1-d3 (03/09)

`InpUseStreakSizing=true` (sale dopo vittorie, `InpStreakScaleUp=1.25`
per step, soglia solo 2 vittorie di fila, tetto 2.0×) dà anch'esso
**risultato identico al centesimo** a c1 (503 trade, PF0.79,
-$546.74). Verificato nei deal grezzi: **tutti e 503 i trade usano
esattamente 0.01 lotto, zero variazione**, nonostante streak fino a 7
vittorie di fila osservate (ben oltre la soglia di 2 per attivare lo
scale-up, che a 4 vittorie raggiungerebbe già il tetto 2.0×).

A differenza di d1-d3 (dove l'arrotondamento a zero è una certezza
matematica), qui **non è la stessa spiegazione**: con moltiplicatore
fino a 2.0× il lotto grezzo pre-arrotondamento dovrebbe quasi certamente
attraversare la soglia dei 0.01 lotti successiva in qualche trade su
503. Tracciato nel codice fino a `NXS_EA_OnLogicalClose` →
`NXS_OnTradeClosed` → `_nxs_streak_update` (soglie verificate, tutte
raggiungibili) — non isolato se `NXS_EA_OnLogicalClose` viene davvero
richiamato per ogni chiusura PIVOT_WICK in questa modalità di test, o
se il moltiplicatore si aggiorna ma il lotto grezzo pre-arrotondamento
resta comunque troppo piccolo per attraversare lo step anche a 2×.
**Non risolto** — servirebbe un log/contatore diagnostico (modifica
MQL5, non fatta qui) per chiudere la domanda con certezza.

## Addendum 6 — d5 RegimeVeto: stesso pattern di OneShotLevel, solo volume (03/09)

`InpProfileRegimeVeto=true`: 330 trade (-34% vs baseline), WR 43.6%
(vs 44.9%, invariato/leggermente peggio), PF **identico** 0.79, avg
win/loss ~9.1/-8.9 (invariato). Stesso schema già visto con
OneShotLevel (c2): filtra un sottoinsieme senza cambiarne la qualità —
riduce il rumore statistico, non l'edge.

## Sintesi provvisoria round d (uscite/sizing)

| Test | Trade | WR | PF | Verdetto |
|---|---|---|---|---|
| d1 ATR partial | 503 | 44.9% | 0.79 | test viziato (già default) |
| d2 FixedPip partial | 503 | 44.9% | 0.79 | inerte (arrotondamento a 0.01 lotto) |
| d3 Volume partial | 503 | 44.9% | 0.79 | inerte (stessa causa) |
| d4 StreakSizing | 503 | 44.9% | 0.79 | inerte, causa non isolata |
| d5 RegimeVeto | 330 | 43.6% | 0.79 | solo volume, nessun edge |

Nessuno dei 5 sposta il PF. d6 (best-combo entry, stesso lotto) e d7
(FixedPip a lotto più alto via deposito $5000) ancora in coda.

## Addendum 7 — d6 (best-combo entry) arrivato dopo lo stop: 0 trade (03/09, ~20:40)

d6 (`RequireCloseConfirm` + `OneShotLevel` + `AvoidBuildup` + split,
senza `RequireWick`) era già in coda quando l'utente ha chiesto di
fermarsi — completato comunque in background: **0 trade in 3 mesi**.
Conferma finale del pattern già visto con c6: impilare
`RequireCloseConfirm` (l'unico fix con effetto reale, -45% volume da
solo) sopra `OneShotLevel` (-28% da solo) collassa il campione anche
senza il contributo di `RequireWick`. Nessun'altra azione presa, thread
chiuso come da richiesta.

## Fermata su decisione esplicita dell'utente (03/09, ~19:50)

L'utente ha chiesto di fermarsi su questa strategia dopo il round d1-d5
(d6/d7 fermati prima di partire — i wait/monitor sono stati stoppati,
`terminal64.exe` NON è stato ucciso se un run era già in corso, solo
non più seguito). **Stato finale onesto**: su 9 varianti isolate
testate (c1-c6 entry filters + d1-d5 exit/sizing), **una sola mostra un
miglioramento di qualità reale** (c3 RequireCloseConfirm, PF0.79→0.91,
comunque sotto pareggio). Tutte le altre o non hanno effetto (d1-d4,
per ragioni diverse — arrotondamento a lotto minimo per d1-d3, causa
non isolata per d4) o riducono solo il volume senza cambiare l'edge
(c2, c4, d5) o peggiorano (c5). Nessuna configurazione supera PF1.0 su
questo dataset. Prossima volta che si riprende PIVOT_WICK: partire da
qui, non ripetere questi 9 test.

## Non ancora verificato

- Se il flag `InpPivotWickRequireWick=true` (pianificato in Fase 0 punto
  2 della nota post-maratona) cambia il quadro — non testato in questi
  tre report, tutti con `RequireWick=false`.
- `RequireCloseConfirm` e `AvoidBuildup` (gli altri due flag del commit
  `755f3e4`) — presenti nel `.set` di c1/c2 ma entrambi `false` in
  entrambi i test, quindi non isolati singolarmente ancora.
- Analisi MFE/MAE pura (senza SL/TP) per capire se il trigger ha edge
  direzionale grezzo — prossimo passo naturale prima di provare altri
  filtri di uscita.

## Prossima azione consigliata

Prima di un altro giro di tuning uscite: isolare `RequireWick=true` da
solo (stesso periodo 3 mesi, stessa baseline c1) — se anche questo non
sposta WR/payoff, la conclusione onesta è che PIVOT_WICK come concepito
(pivot frattale + wick di rigetto, senza altro contesto) **non ha edge
su M15 GOLD in questo periodo**, e la strada utile diventa il
"filtro candela + re-entry" già pianificato (Fase 0 punto 2) o
l'archiviazione della strategia come `Rejected` (§10 Master Roadmap) se
anche quello fallisce. Richiede l'agente desktop (MetaEditor/MT5) per
lanciare il prossimo Tester run — questa sessione (background) ha solo
analizzato i report già prodotti, nessuna modifica al codice MQL5 fatta
qui (per [[feedback_no_live_mql5_without_asking]]).

## Collegamenti
[[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]] ·
[[NEXUS EA - MASTER ROADMAP v3]] · [[MOC - Trading]]
