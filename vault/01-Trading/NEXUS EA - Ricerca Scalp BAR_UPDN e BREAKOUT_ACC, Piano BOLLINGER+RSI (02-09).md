---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, scalp, m15, bar_updn, breakout_acc, bollinger, risk-shield]
created: 2026-09-02
updated: 2026-09-02
---

# NEXUS EA — Ricerca scalp: BAR_UPDN/BREAKOUT_ACC (negativo), piano BOLLINGER+RSI (02/09)

## Perché

Continuazione del task "ricerca nuove strategie scalp" (fork D1-unlock
BB_SQUEEZE/ORDER_BLOCK/BREAKOUT_ACC). Prima notte intera su BAR_UPDN
(price-action puro, mai verificata su MT5) e BREAKOUT_ACC sbloccata da D1
a M15.

## Scoperta strutturale: il "terzo cancello" NXS_Profile_Enabled

Verificando perché BB_SQUEEZE/ORDER_BLOCK non aprivano trade nel test
isolato: esiste una whitelist separata da `InpStrat_X` e da
`InpStrategySelector` — `NXS_Profile_Enabled(name)` — che quando
`InpUseStrategyProfiles=true` (default) rifiuta in silenzio
(`profile_disabled`) qualunque strategia non esplicitamente elencata.
Stesso bug già trovato il 28/08 per PMAX. Solo **21 delle 48** strategie
del motore erano abilitate. Sbloccate stanotte: BB_SQUEEZE, ORDER_BLOCK
(per il test), e trovato che **anche BOLLINGER è bloccata** nonostante sia
"OK" su D1 con storia reale MT5 (PF1.17) — da sbloccare prima di testarla.

**Prima di testare QUALSIASI strategia isolata**: controllare
`NXS_Profile_Enabled()` in `NXS_StrategyProfiles.mqh` — zero trade senza
errori visibili è il sintomo, non conta solo `InpStrat_X`/selector.

## BAR_UPDN — nuda su M15 (2024, 1 anno): negativo

PF0.72, netto -$165.66, win rate 24.3% (51/210). Nessun filtro di
salvataggio trovato analizzando corpo candela segnale, allineamento
SMA20, momentum nelle 6 barre precedenti, ora del giorno — tutte
differenze marginali tra vincenti e perdenti.

## BREAKOUT_ACC — sbloccata su M15 (2024, 1 anno): negativo

PF0.64, netto -$242.41, win rate 16.4% (33/201, sotto pareggio per
R:R4.5). Stesso esito: nessuna feature di salvataggio trovata (forza
accettazione, ampiezza range, momentum, ora).

**Nota storica** (vedi [[NEXUS EA - Verdetto Finale SCALP (24-08)]] e
correlate): BREAKOUT_ACC era già stata verificata forte su 4h/D1 nel
nucleo hedge con TURTLE_SOUP/CISD. Lo scalp M15 è un contesto nuovo, non
in contraddizione con quel verdetto.

## Bug trovato (ipotesi dell'utente, confermata sui dati): "inseguimento" dello stesso movimento

Sia `NXS_Strat_BarUpDn` sia `NXS_Strat_BreakoutAcc` non avevano alcuno
stato "già tradato questo pattern/breakout" (a differenza di
`NXS_Strat_BBSqueeze`, che ha `g_bbsqState.consumed`). La condizione
torna vera più volte durante lo stesso trend, quindi il motore apriva un
nuovo trade a ogni barra invece di prenderlo una volta sola:

- BAR_UPDN: 134/210 trade raggruppati (stesso verso, entro 6h)
- BREAKOUT_ACC: 106/201 — esempio concreto, 7 sell consecutivi 3-5
  gennaio 2024 sullo stesso movimento: solo il primo (+$20.36) vincente,
  i 6 inseguimenti tutti in perdita (-$2/-5 ciascuno)

**Primo fix tentato (fallito)**: one-shot che si resetta appena una
barra non soddisfa più il pattern — inefficace, il pattern in un trend
reale è intermittente, non continuo bar-su-bar (BAR_UPDN: PF0.72→0.74,
trade 210→207, quasi nessun cambiamento).

**Secondo fix (marginale)**: raffreddamento per direzione a N barre
(`InpBarUpDnCooldownBars`/`InpBreakoutAccCooldownBars`, default 8 =2h su
M15). BAR_UPDN: PF0.72→0.77, netto -$165→-$138, trade 210→202 — meglio
ma "l'inseguimento" non è la causa dominante della debolezza.

## Pattern MFE/giveback confermato anche qui

Stesso fenomeno di stanotte su SAR/EMA_PULLBACK: su BAR_UPDN (versione
raffreddamento), 45/196 trade toccano un profitto flottante reale
(>$3) ma chiudono in perdita — $259.71 di picco totale contro $196.41
di perdita finale netta. Esempio: 05/07/2024 15:15 buy, toccato
+$17.38, chiuso 15 minuti dopo a -$4.76 di stop.

## Infrastruttura: RiskShield EQUITY_BREAKER ora per-strategia

Richiesta esplicita dell'utente: il breaker Sharpe (finestra 50 trade,
soglia 0.30, pausa 24h) bloccava **tutto il conto** quando una sola
strategia aveva una serie negativa. Refattorizzato
(`NXS_RiskShield.mqh`): `NXS_RS_Breaker_Check` ora è una funzione pura
(non tocca più i globali), `NXS_RS_Breaker_Update` calcola lo Sharpe
**separatamente per strategia** (parsing dal commento del deal, stesso
schema di `_NXS_StateParseComment`), stato in array paralleli
per-strategia. `NXS_CommonExposurePreflight` ora riceve `stratName` e lo
passa fino al gate. I 4 call site (PRIMARY/GRID/PYRAMID/INST) aggiornati.
Compilato pulito. **Non cambia i numeri dei test isolati di stanotte**
(un'unica strategia attiva = "blocca solo lei" equivale a "blocca
tutto"), ma è la correzione corretta per quando le strategie gireranno
insieme nel portafoglio reale.

## Piano prossimo: BOLLINGER + RSI + candela di conferma

L'utente ha condiviso una guida esterna sullo scalping con 3 strategie;
la più rilevante è **RSI + Bollinger Bands Reversal**: tocco banda
estrema + RSI 14 (livelli 30/70) NON conferma l'estremo + candela di
inversione (hammer/engulfing su supporto, shooting star/engulfing su
resistenza) → target sulla banda media. Archetipo **mean-reversion**,
diverso da BAR_UPDN/BREAKOUT_ACC (entrambi continuazione, entrambi
falliti stanotte) — vale la pena provarlo.

NEXUS ha già `NXS_Strat_Bollinger` (D1, PF1.17 "OK", ma bloccata dal
terzo cancello, vedi sopra) — logica di rientro in banda già simile
(`ppx <= bbLo[1] && bbLo[0] < px`) ma **senza** filtro RSI né pattern di
candela specifico, e **senza** gate a chiusura barra (stesso rischio di
inseguimento visto sopra, da verificare).

**Ordine deciso con l'utente** ("segna nel vault e lo eseguiamo stanotte"):
1. Sbloccare BOLLINGER dal terzo cancello (stesso trattamento di
   BB_SQUEEZE/ORDER_BLOCK).
2. Testare la logica **as-is** (senza RSI/candela) su M5 nuda, isolata,
   per vedere se l'ipotesi di base D1→scalp regge — Fase 0/1 del piano
   metodologico standard.
3. Se promettente: aggiungere filtro RSI(14) 30/70 + pattern di candela
   di inversione (hammer/engulfing bull, shooting star/engulfing bear)
   come nell'articolo, ritestare.
4. **Attenzione**: [[NEXUS EA - Verdetto Finale SCALP (24-08)]] aveva
   trovato che un filtro ER lungo uccideva il 99.9%+ dei segnali scalp
   per contraddizione strutturale di scala temporale — l'RSI 14 è un
   filtro molto più corto/locale, probabilmente non soggetto allo
   stesso problema, ma verificare il conteggio segnali grezzi vs
   filtrati prima di dichiarare l'idea morta per campione troppo
   piccolo.
5. Aggiungere un gate a chiusura barra (`lastBarTime`) fin da subito
   nella nuova implementazione, per non ripetere il bug di inseguimento
   trovato su BAR_UPDN/BREAKOUT_ACC.

## Idea nuova (non ancora eseguita): pivot extension + wick + volume spike

Emersa il 02/09 sera guardando TradingView a mano mentre si aspettava un
test SAR. L'utente disegna linee orizzontali estese dai pivot (minimi e
massimi), e cerca **buy su tocco di pivot-minimo, sell su tocco di
pivot-massimo**, confermato da un **wick di rigetto** sulla candela di
tocco (stoppino lungo dalla parte del pivot) — visto in screenshot su
GOLD, es. minimo 4282.6 con stoppino inferiore netto seguito da
rimbalzo a 4390+.

(Nota: un successivo commento dell'utente su un filtro di volume — "non
sempre, solo quando c'è più volume in poco tempo" — **non** si riferiva
a questa idea ma a SAR, vedi sezione SAR sopra per il chiarimento in
corso.)

Archetipo mean-reversion da supporto/resistenza, concettualmente vicino
a **MALAYSIAN_SNR** (pivot S/R) + **BAR_UPDN** (pattern di candela, già
provata e debole da sola) + **ORDER_BLOCK**, ma nessuna delle tre nel
motore combina esplicitamente "tocco di linea di pivot estesa + wick +
volume" come condizione unica e più stretta. Non ancora deciso se
formalizzarla come nuova strategia testabile o se resta lettura manuale
del grafico — da chiedere all'utente quando riprende il filo.

## File toccati stanotte

- `NXS_Strategies.mqh`: BAR_UPDN e BREAKOUT_ACC — gate a chiusura barra +
  raffreddamento per direzione.
- `NXS_StrategyProfiles.mqh`: `InpScalpTFOverride`; sbloccate BB_SQUEEZE/
  ORDER_BLOCK dal terzo cancello; profilo SL/TP dedicato per BAR_UPDN
  (R:R 2.5, era sui default globali R:R1.3).
- `NXS_Inputs.mqh`: `InpBarUpDnCooldownBars`, `InpBreakoutAccCooldownBars`,
  `InpScalpTFOverride`, `InpEMAPBFixedLot` (da sessione precedente stessa
  notte).
- `NXS_RiskShield.mqh`, `NXS_Execution.mqh`, `NXS_GridRecovery.mqh`,
  `NXS_Pyramiding.mqh`, `NXS_InstManage.mqh`: breaker per-strategia.

Tutto compilato pulito (0 errori) e pushato su GitHub.
