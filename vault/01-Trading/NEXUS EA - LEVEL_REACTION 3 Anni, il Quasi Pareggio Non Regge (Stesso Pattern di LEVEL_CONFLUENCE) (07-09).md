---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, level-reaction, chiusura, campione-ampio]
created: 2026-09-07
updated: 2026-09-07
---

# NEXUS EA — LEVEL_REACTION su 3 anni: il quasi pareggio non regge, stesso pattern di LEVEL_CONFLUENCE (07/09)

## Risultato

| | 3 mesi (338 trade) | 3 anni (1833 trade) |
|---|---|---|
| PF | 0.95 | **0.80** |
| Net | -$298.64 | **-$973.57** |
| Win rate | 39.9% | 31.9% |
| Soglia di pareggio | 41.0% | 36.1% |
| **Gap** | **-1.1pp** | **-4.2pp** |
| Max DD equity | — | $989.36 (quasi tutto il deposito) |

BUY gap -1.7pp, SELL gap -6.4pp (SELL nettamente peggio, a differenza
del quasi-pareggio bilanciato visto sui 3 mesi).

## Verdetto

**Stesso identico pattern di LEVEL_CONFLUENCE**: un risultato quasi in
pareggio su un campione piccolo (338 trade) non regge quando il
campione si allarga di 5.4× (1833 trade) — il gap dalla soglia di
pareggio quadruplica (da -1.1pp a -4.2pp). Il miglioramento reale del
design (gate sfondamento + doppia fonte livelli) ha comunque ridotto
il gap rispetto alla famiglia LEVEL_CONFLUENCE originale (che arrivava
a -10.7pp nella sua prima iterazione equivalente), ma non a
sufficienza per essere profittevole.

**LEVEL_REACTION va chiusa come LEVEL_CONFLUENCE** — stessa lezione di
metodo confermata due volte ora: un piccolo campione vicino al
pareggio non è mai una conferma, sempre verificare su scala ampia
prima di concludere.

## Collegamenti
[[NEXUS EA - LEVEL_REACTION Primo Risultato, il Migliore della Famiglia Livelli (07-09)]] · [[NEXUS EA - LEVEL_CONFLUENCE Chiusura, il Quasi Pareggio BUY Non Regge su Campione Ampio (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
