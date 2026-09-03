---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bollinger, scalp, m5, mean-reversion]
created: 2026-09-03
updated: 2026-09-03
---

# NEXUS EA — BOLLINGER su M5 nuda: primo risultato vero (03/09)

## Perché

Step 2 del piano [[NEXUS EA - Ricerca Scalp BAR_UPDN e BREAKOUT_ACC, Piano BOLLINGER+RSI (02-09)]]:
testare la logica Bollinger *as-is* (nessun RSI, nessuna candela di
conferma) su M5 nuda, per vedere se l'ipotesi D1→scalp regge prima di
aggiungere filtri. Due tentativi falliti per errori miei (selector
sbagliato preso dal registro invece del vero
[[NEXUS EA - Due Numerazioni Strategia Diverse, InpStrategySelector Non e il Registro (03-09)]],
poi TF override non ricompilato) — terzo tentativo corretto e
verificato (`InpStrategySelector=2`, `InpScalpTFOverride=5` entrambi
confermati nel report echoed).

## Risultato

Periodo M5, 2026.06.01-2026.08.26 (3 mesi), GOLD, nessun filtro oltre
al trigger nudo delle bande.

| Metrica | Valore |
|---|---|
| Trade | 306 (~3.4/giorno) |
| Win rate | 28.1% |
| Avg win | $10.99 |
| Avg loss | -$5.10 |
| Payoff ratio | ~2.15:1 |
| PF | 0.83 |
| Net | -$186.23 |
| Max DD balance | $222.34 |

## Lettura

Il payoff ratio è già favorevole (vincite ~2.15× le perdite) — il
problema non è la gestione dell'uscita, è il **win rate troppo basso**
(28.1% contro un pareggio teorico al 31.7% dato questo payoff). Questo
è esattamente il sintomo che il filtro RSI+candela del piano (step 3)
è pensato per correggere: il tocco nudo della banda genera troppi
falsi segnali (306 in 3 mesi, ~1 ogni 7 ore su M5), un filtro di
conferma dovrebbe tagliare selettivamente i falsi positivi e alzare il
win rate verso/oltre la soglia di pareggio, sfruttando un R:R già
buono. Diverso dal caso PIVOT_WICK (dove nessun filtro isolato
spostava mai il win rate) — qui c'è una ragione strutturale concreta
per aspettarsi che un filtro di qualità funzioni.

## Non ancora fatto

- Filtro RSI(14) 30/70 + pattern di candela di inversione (hammer/
  engulfing su supporto, shooting star/engulfing su resistenza) —
  step 3 del piano, richiede scrivere nuova logica in
  `NXS_Strat_Bollinger()` (non solo un flag/config, un'aggiunta di
  codice reale) — **non fatto senza conferma esplicita dell'utente**,
  vedi [[feedback_no_live_mql5_without_asking]].
- Gate a chiusura barra (`lastBarTime`) — step 5 del piano, per evitare
  il bug di inseguimento già trovato su BAR_UPDN/BREAKOUT_ACC. Non
  verificato se `NXS_Strat_Bollinger()` ce l'ha già o va aggiunto prima
  del filtro RSI.
- BUY vs SELL non ancora separato in questo primo giro.

## Collegamenti
[[NEXUS EA - Ricerca Scalp BAR_UPDN e BREAKOUT_ACC, Piano BOLLINGER+RSI (02-09)]] ·
[[NEXUS EA - Piano d'Azione Post-Maratona, Stato Reale e Prossimi Passi (03-09)]] ·
[[MOC - Trading]]
