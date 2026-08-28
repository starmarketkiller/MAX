---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fibonacci, reverse, rifiutata, chiusura]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Fibonacci esaurimento-reverse: chiusura definitiva (25/08)

## Perché

Idea originale dell'utente (24/08): non usare Fibonacci come filtro
d'ingresso, ma come gestione di uscita — quando il prezzo raggiunge
un'estensione Fibonacci (esaurimento del movimento), chiudere il
trade primario in profitto e aprire un reverse (a lotto pieno o
ridotto). Testata una sola volta ieri, solo su STRUCT_REACT, con uno
swing a **finestra fissa di 20 barre** — fallita, ma restava il dubbio
che il fallimento fosse dovuto a uno swing mal definito, non all'idea
in sé. Oggi disponibile un vero rilevatore di pivot (ZigZag), lo
stesso usato per il filtro Elliott — occasione per una riprova più
fedele all'idea originale, ancorando l'estensione Fibonacci alla gamba
d'onda REALMENTE formata invece di una finestra arbitraria.

## Risultato: negativo su 4 strategie, meccanismo confermato non valido

`fib_exhaustion_zigzag_25-08.py` — swing dall'ultimo pivot ZigZag
confermato (dev=2.0, stesso del filtro Elliott), estensione 1.618,
testato su STRUCT_REACT (per confronto diretto), SAR, ADX_RSI, MACD:

| Strategia | (a) Baseline | (b) Uscita anticipata, no reverse | (c) Reverse size piena | (c bis) Reverse lotto ridotto 0.5x |
|---|---|---|---|---|
| STRUCT_REACT | 2.65 (5/5) | 2.56 (4/5) | 1.60 (3/5) | 1.95 (4/5) |
| SAR | 1.51 (5/5) | 1.51 (5/5) | 1.32 (5/5) | 1.41 (5/5) |
| ADX_RSI | 1.77 (5/5) | 1.80 (5/5) | 1.57 (5/5) | 1.68 (5/5) |
| MACD | 1.46 (5/5) | 1.46 (4/5) | 1.30 (4/5) | 1.37 (4/5) |

**(b) uscita anticipata da sola**: sostanzialmente neutra ovunque
(differenze di ±0.03, tranne STRUCT_REACT -0.09) — chiudere prima al
livello di esaurimento non aiuta né danneggia in modo significativo,
il target/trailing esistente cattura già il movimento in modo
comparabile.

**(c)/(c bis) il reverse**: **peggiora in tutti e 4 i casi, senza
eccezioni**, sia a size piena che a lotto ridotto (la richiesta
esplicita dell'utente). Il lotto ridotto attenua il danno ma non lo
elimina mai — resta sempre sotto la baseline. Il pattern è identico
su strategie molto diverse tra loro (mean-reversion selettiva come
STRUCT_REACT, trend-following ad alto volume come SAR/MACD), un segno
forte che non è un caso specifico ma un limite strutturale dell'idea.

## Perché il reverse non funziona (ipotesi)

Quando un movimento raggiunge un'estensione 1.618 del proprio swing
precedente, non è un segnale affidabile di inversione imminente — è
semplicemente un movimento forte che spesso continua (specialmente
nelle strategie trend-following come SAR/MACD, dove "il prezzo è già
esteso" è proprio la condizione in cui il trend tende a persistere sul
gold, coerente con tutto quello che la sessione ha trovato sui trend
2019-2026). Il reverse scommette sistematicamente contro il momentum
residuo nel momento sbagliato.

## Verdetto — chiusura definitiva

**L'idea del reverse su esaurimento Fibonacci è chiusa**, non solo per
STRUCT_REACT ma come meccanismo generale: due implementazioni
indipendenti (finestra fissa ieri, ZigZag reale oggi), 5 strategie
diverse in totale, **mai un solo caso positivo per il reverse**. Non
riprovare senza un'ipotesi radicalmente diversa (es. reverse solo dopo
una conferma multi-barra dell'inversione, non al primo tocco
dell'estensione — ma questo snaturerebbe l'idea originale
dell'esaurimento istantaneo). L'uscita anticipata da sola (senza
reverse) resta neutra e non vale la complessità aggiuntiva rispetto
alla gestione di uscita già in uso (target fisso o trailing).

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - STRUCT_REACT con Fibonacci Esaurimento-Reverse (24-08)]]
[[NEXUS EA - Filtro Elliott Wave Multi-Timeframe, il nuovo ingrediente universale (25-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
