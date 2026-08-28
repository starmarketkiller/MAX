---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, struct-react, fibonacci, reverse, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — STRUCT_REACT con Fibonacci esaurimento-reverse (24/08)

## Perché

Prima ottimizzazione individuale di una baseline, come richiesto
dall'utente dopo l'analisi di correlazione (STRUCT_REACT è la
diversificatrice più solida trovata oggi). Applicata l'idea esplicita
dell'utente: Fibonacci non come filtro d'ingresso (già provato su
EMA_PULLBACK, inconcludente) ma come **gestione di uscita/reverse** —
quando il prezzo raggiunge un livello di estensione Fibonacci (segno di
possibile esaurimento del trend), chiudere il trade in corso e provare
un reverse a lotto ridotto. `struct_react_fib_exhaustion_24-08.py`.

## Meccanismo

Livello di esaurimento = entry + 1.618 × (range max-min delle 20 barre
precedenti l'ingresso) — estensione Fibonacci classica. Se raggiunto
prima dello SL o del TP originale (2.0/6.0×ATR), il trade primario si
chiude lì e si apre un reverse (SELL, opposto) dallo stesso prezzo,
stesso profilo SL/TP invertito.

## Risultato: baseline già fortissima (PF2.65, 5/5 finestre), il meccanismo non la migliora

| Config | retail aggPF | meta1/meta2 | n |
|---|---|---|---|
| (a) baseline invariata | 2.65 | 2.82/2.48 | 50 |
| (b) uscita anticipata a esaurimento, nessun reverse | 2.63 | 2.82/2.45 | 50 |
| (c) uscita + reverse a size piena | 2.29 | 2.79/1.86 | 58 |
| (c bis) uscita + reverse a lotto ridotto (0.5x) | 2.44 | 2.80/2.10 | 58 |

**(b) è quasi identico ad (a)**: il livello di esaurimento 1.618 scatta
raramente PRIMA del TP originale (6×ATR è già un bersaglio generoso) —
solo **8 volte su 50** segnali. Quando scatta, il risultato ottenuto è
comunque simile a quello che si sarebbe avuto aspettando il TP normale.

**Il reverse peggiora sempre**, sia a size piena che ridotta. Isolati i
soli 8 trade di reverse: 2 vincite (+3R ciascuna) e 6 perdite (-1R
ciascuna) — **PF grezzo esattamente 1.00 prima dei costi**, negativo
dopo. Campione troppo sottile (8 trade) per un verdetto definitivo in
un senso o nell'altro, ma nessun segno di edge nemmeno grezzo.

## Verdetto

Non promosso. Due problemi distinti, non uno:
1. Il trigger di esaurimento (1.618× swing a 20 barre) scatta troppo
   raramente per essere utile come gestione di uscita — il target
   esistente è già competitivo o migliore nella maggior parte dei casi.
2. Il reverse, quando scatta, non mostra edge nemmeno grezzo (PF=1.00
   pre-costi) — ma su un campione di 8 trade non è una prova forte in
   nessuna direzione, solo un'indicazione.

**Non è la stessa cosa** della scoperta BUY/SELL flip vista nella
diagnosi per-data di STRUCT_REACT (dove il SELL era genuinamente forte
in un'intera epoca storica separata, 25 trade, PF2.85) — qui il reverse
è innescato dentro la STESSA finestra temporale del trade BUY, un
meccanismo intraday/a breve termine diverso dal flip di regime pluriennale
già confermato.

## Prossimi passi aperti

- Se si vuole insistere sull'idea: trigger di esaurimento più sensibile
  (estensione 1.272 invece di 1.618, o swing a meno barre) per avere un
  campione più ampio da giudicare — non tentato oggi.
- Il flip BUY/SELL per regime (non per esaurimento intraday) resta la
  scoperta più solida su STRUCT_REACT — vedi [[NEXUS EA - Diagnosi Onesta del BUY-only (24-08)]].
  Un meccanismo che attivasse SELL non ad ogni esaurimento ma quando il
  contesto storico più ampio (es. ER su una finestra lunga) suggerisce
  regime laterale/ribassista potrebbe essere più fedele a quella
  scoperta - idea diversa, non ancora tentata.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]
[[NEXUS EA - Diagnosi Onesta del BUY-only (24-08)]]
