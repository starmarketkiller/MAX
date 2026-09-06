---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, level-confluence, confluenza, buy-quasi-pareggio]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — LEVEL_CONFLUENCE con confluenza obbligatoria: miglior risultato finora, BUY quasi in pareggio (06/09)

## Il test

Ultima ipotesi rimasta prima di chiudere la strategia
([[NEXUS EA - LEVEL_CONFLUENCE M5 vs M15, Stesso Esito Negativo su Entrambi i TF (06-09)]]):
`InpLevelConfRequireConfluence=true` — entra SOLO sui livelli dove 2+
delle tre TF alte (H1/H4/D1) coincidono, non su livelli isolati.
Stessa finestra 3 mesi, M15, conferma 2 barre, rischio 5%.

## Risultato — il migliore delle 5 iterazioni

| Iterazione | Trade | PF | Net |
|---|---|---|---|
| 1. touch, M15/M30, 3 mesi | 424 | 0.89 | -$646.14 |
| 2. touch, M15/M30, 3 anni | 1958 | 0.81 | -$974.82 |
| 3. conferma2+HTF, M15, 3 mesi | 295 | 0.83 | -$837.33 |
| 4. conferma2+HTF, M5, 3 mesi | 346 | 0.78 | -$894.47 |
| **5. conferma2+HTF+confluenza obbligatoria, M15, 3 mesi** | **120** | **0.88** | **-$283.44** |

La confluenza obbligatoria taglia il campione del 59% (295→120) ma
riduce la perdita netta dell'66% (-$837→-$283) — non è solo "meno
trade quindi meno perdita in proporzione", il PF stesso migliora
(0.83→0.88, il migliore delle 5).

## Il dettaglio per lato — qui la scoperta vera

| | Trade | Net | WR | Vincita media | Perdita media | Soglia pareggio |
|---|---|---|---|---|---|---|
| **BUY** | 73 | **-$0.51** | 35.6% | $49.78 | -$27.55 | 35.6% |
| SELL | 47 | -$273.13 | 31.9% | $49.31 | -$31.65 | 39.1% |

**Il lato BUY è praticamente in pareggio esatto** (-$0.51 su 73 trade,
5% di rischio a trade) — il win rate (35.6%) coincide quasi
esattamente con la soglia di pareggio calcolata dal proprio rapporto
vincita/perdita (35.6%). Il lato SELL resta negativo con un gap più
ampio (WR 31.9% contro soglia 39.1%).

## Interpretazione — cautela sul campione

73 trade BUY è un campione piccolo: un risultato "quasi pareggio" a
questa scala può facilmente diventare +$200 o -$200 con la prossima
manciata di trade, quindi **non è ancora una conferma**, è un segnale
che vale la pena approfondire. Due letture possibili:

1. **La confluenza obbligatoria è il filtro di selezione che mancava**
   — riduce il rumore (livelli isolati, poco significativi) e lascia
   solo i punti dove il prezzo ha davvero una ragione strutturale per
   reagire. Il lato SELL potrebbe solo aver bisogno di più campione o
   di un aggiustamento minore (es. tolleranza diversa in un mercato
   che nella finestra testata è salito).
2. Oppure è un caso favorevole di piccolo campione (73 trade) che non
   regge su una finestra più ampia — da verificare prima di
   festeggiare, esattamente come già successo con altre strategie
   (BOLLINGER Overlap-only ha peggiorato invece di migliorare).

## Prossimo passo naturale (da confermare con l'utente prima di toccare il codice)

Testare BUY-only con confluenza obbligatoria richiederebbe un nuovo
flag `InpLevelConf...BuyOnly` (non esiste ancora, analogo a
`InpBollingerBuyOnly`) — è una modifica al codice MQL5 condiviso,
quindi da confermare prima di procedere (regola del vault: non
applicare modifiche a MQL5 live senza chiedere). In alternativa, si
può allargare la finestra a 3 anni con la stessa configurazione per
vedere se il quasi-pareggio BUY regge su un campione più grande, senza
toccare il codice — questo sì fattibile subito.

## Collegamenti
[[NEXUS EA - LEVEL_CONFLUENCE M5 vs M15, Stesso Esito Negativo su Entrambi i TF (06-09)]] · [[NEXUS EA - Conferma 2 Barre e Livelli HTF, Migliora il Rapporto ma Resta Negativo (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
