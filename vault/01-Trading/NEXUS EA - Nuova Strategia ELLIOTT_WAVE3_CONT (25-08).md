---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, elliott-wave, nuova-strategia, wave3-continuation]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Nuova strategia standalone: ELLIOTT_WAVE3_CONT (25/08)

## Perché

Il filtro Elliott di oggi ([[NEXUS EA - Filtro Elliott Wave Multi-Timeframe, il nuovo ingrediente universale (25-08)]])
usa il conteggio d'onda solo in negativo (sopprimi un segnale quando
un impulso è esaurito). Ma l'idea originale dell'utente era più ampia:
"possiamo trovare dove siamo nell'onda, dove può essere la possibile
continuazione dell'onda" — un uso POSITIVO, come trigger d'ingresso
proprio, non solo come filtro su segnali di altre strategie. Prima
implementazione concreta di questo lato mancante.

## Meccanica

Usa lo stesso ZigZag di oggi per riconoscere un assetto "onda 1
(impulso) + onda 2 (correzione)" appena completato, e compra la
ripartenza attesa in onda 3 — di solito la fase più forte di un
impulso Elliott:

1. Ultimi 3 pivot: P0(minimo)→P1(massimo)→P2(minimo) per un setup
   rialzista (mirror per ribassista).
2. Regola 1: onda 2 non ritraccia sotto l'inizio di onda 1 (P2 > P0).
3. Regola 2: profondità della correzione (P1-P2)/(P1-P0) in zona
   Fibonacci plausibile per un'onda 2 (38.2%-78.6%, regola pratica
   standard — né troppo debole né troppo profonda).
4. Segnale: nel momento stesso in cui il pivot P2 si conferma, se le
   regole sono soddisfatte, compra — si scommette sulla ripartenza.

## Risultato: BUY-only promettente, plateau confermato

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| Simmetrica SL2.0/TP6.0 | 1.28 (1.37/1.20) | 4/5 | 116 |
| **BUY-only SL2.0/TP6.0** | **2.06 (1.91/2.23)** | 4/5 | 66 |
| SELL-only SL2.0/TP6.0 | 0.58 (0.65/0.51) | 1/5 | 50 |

Stessa asimmetria BUY/SELL vista su quasi tutto il catalogo oggi.

**Plateau-check sulla zona di ritracciamento** (5 varianti, dev=2.0
fisso): PF 1.70-2.14, tutte con 4/5 finestre — non un valore isolato.
**Plateau-check sulla soglia ZigZag** (4 valori, zona 0.382-0.786
fissa): PF 2.06-3.10, tutti ben sopra 1 — dev=2.5 dà il risultato più
pulito (PF2.53, m1=2.81/m2=2.29, **5/5 finestre**).

## Verifica laterale — coerente ma troppo sottile

BUY laterale: n=8, PF0.0, sumR=-8.8. SELL laterale: n=5, PF0.66.
Entrambi i campioni troppo piccoli per un verdetto definitivo (stessa
soglia di cautela usata tutto il giorno) — pattern coerente con
beta di rally, non ancora una prova, ma nemmeno smentita.

## Verdetto

**Nuova candidata provvisoria**: ELLIOTT_WAVE3_CONT, BUY-only, 4h,
SL2.0/TP6.0 (o dev=2.5 per la versione più bilanciata, PF2.53 5/5),
ER+floor 0.3. Il plateau su due assi indipendenti (zona Fibonacci e
soglia ZigZag) è un buon segno anti-overfitting, ma la finestra
laterale resta troppo sottile per una promozione piena — stesso
livello di fiducia di MALAYSIAN_SNR_BREAKOUT/TSI quando furono trovate
inizialmente. Completa concettualmente il lavoro Elliott di oggi: ora
esiste sia l'uso negativo (filtro di esclusione, 21/25 strategie
migliorate) sia quello positivo (trigger d'ingresso proprio).

Non ancora testato: combinazione col filtro di esaurimento (di grado
superiore, es. D1) come ulteriore conferma; trailing invece del target
fisso; in MQL5.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Filtro Elliott Wave Multi-Timeframe, il nuovo ingrediente universale (25-08)]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
