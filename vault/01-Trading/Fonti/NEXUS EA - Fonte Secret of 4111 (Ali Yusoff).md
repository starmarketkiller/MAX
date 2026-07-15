---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fonte, breakout, engulfing, zikir]
created: 2026-07-15
updated: 2026-07-15
---

# Fonte: "Secret of 4.11" (Ali Yusoff)

Deck fornito dall'utente il 15/07. Nonostante il nome file suggerisse 216
pagine, il PDF reale contiene **16 slide** (immagini, senza testo
estraibile — lette via rendering + visione diretta). Sistema di trading
100% price-action basato su breakout/pullback e un metodo proprietario di
marcatura delle zone tramite candele "engulfing".

## Il ciclo "ZIKIR" — la regola base, ripetuta ovunque nel deck
Ogni setup segue sempre 3 passi, nell'ordine:
1. **BREAKOUT** — rottura del massimo (resistenza) o minimo (supporto) più
   recente.
2. **PULLBACK** — ritorno del prezzo verso il livello appena rotto.
3. **ENTRY** — ingresso al pullback, nella direzione del breakout.

**Criterio di breakout**: serve una rottura "2 volte" — il deck mostra
diagrammi espliciti BREAKOUT vs NO BREAKOUT: un semplice nuovo massimo/minimo
non basta, serve un pattern doppio di conferma (due swing successivi che
rompono nella stessa direzione) prima di considerare valido il breakout.

**Setup BUY vs Setup SELL sono simmetrici ma distinti**: nel setup SELL,
"hint breakout" parte da un minimo, rottura al ribasso, poi pullback verso
l'alto = entrata short. Nel setup BUY, è l'opposto — stessa logica, livelli
e candele diverse. Il deck tratta esplicitamente le due direzioni come **due
diagrammi separati**, non come uno specchiato automaticamente — coerente con
quanto l'utente ci ha chiesto di fare per NEXUS ([[NEXUS EA - Principi]] #9).

## Fresh vs Non-fresh — definizione diversa da MSNR (nota il conflitto)
Qui "fresh" è definito rispetto al ciclo ZIKIR completo, non al semplice
tocco del prezzo:
- **FRESH** = lo ZIKIR (breakout+pullback+entry) **non è ancora stato
  completato** su quel livello — anche se il prezzo lo ha già toccato più
  volte, resta fresh finché nessuna vera ENTRY è scattata lì.
- **NON-FRESH** = lo ZIKIR è stato completato (un'entrata è già avvenuta):
  il livello è "già usato".

⚠️ Questo **contraddice** la definizione di [[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]],
dove "fresh" = mai toccato da wick o body, punto. Sono due scuole diverse:
MSNR è più conservativa (qualunque tocco consuma la freschezza), 4.11 è più
permissiva (solo un'entrata reale la consuma). Da tenere presente quando si
implementa: sono due varianti valide, non un errore da correggere — vanno
scelte consapevolmente per strategia, non mescolate a caso.

## ISL / HSL e le "5 tipologie di Engulfing" — il metodo di marcatura zone
- **ISL (Intermediate Significant Level)** = il livello del breakout di
  prezzo corrente.
- **HSL (Historical Significant Level)** = una zona di "night market" — una
  zona storica dove il prezzo ha congestionato molto (molti buyer/seller
  concentrati) prima del breakout attuale.
- La zona di entrata (marcata in giallo negli esempi) si disegna sul **corpo
  pieno della candela ISL, incluso wick/shadow**.
- **5 tipi di Engulfing** riconosciuti (tutti richiedono ISL+HSL): Perfect
  Engulf, Quasimodo/HNS Engulf, Dominant Engulf, Hidden Engulf (richiede
  multi-timeframe), Gap Engulf. Ognuno marca la zona in modo leggermente
  diverso a seconda di quale candela "contiene" l'ISL.
- Principio esplicito: **"non esiste breakout falso" — un breakout è sempre
  un breakout**, non c'è un concetto di fakeout da filtrare a parte; se
  sembra "fake", significa solo che la zona di marcatura era sbagliata.

## Multi-Timeframe: HTF/LTF espliciti e regola "TF Roadblock"
- **HTF usato**: W1, D1, H4. **LTF usato**: H1, M30, M15.
- Se sei uno **swinger**: usa solo HTF, "entra e dimentica" ma devi sapere
  dove uscire.
- Se sei **scalper/intraday**: usa LTF ma resta vincolato alla direzione HTF.
- **Regola "TF Roadblock"**: la tabella nel deck mostra che entry/take-profit/
  stop-loss vanno presi su timeframe consistenti tra loro — tipicamente
  **entry sul TF scelto, take-profit sullo stesso TF o uno sotto, stop-loss
  sullo stesso TF o uno sotto**. Il roadblock (ostacolo strutturale) capita
  normalmente **un timeframe sotto** quello di entrata.

## MISS / DEEP / ACCURATE — il tipo di pullback dipende dallo strumento
Tre tipologie di profondità di ritracciamento, legate alla natura dello
strumento:
- **MISS** (ritracciamento debole/superficiale): coppie "lente" — NZD, AUD,
  CAD.
- **DEEP** (ritracciamento profondo): coppie "veloci" — GBP, JPY.
- **ACCURATE** (il ritracciamento più pulito/affidabile): strumenti ad alta
  volatilità — **USD, GOLD, SILVER, US30**.

**Nota diretta per noi**: XAUUSD (GOLD) è esplicitamente nel gruppo
"ACCURATE" — secondo questo sistema, i pullback su oro sono il tipo più
pulito e affidabile da tradare, non il più rumoroso. Un dato di conforto
sulla scelta dello strumento, indipendente dai problemi di esecuzione
dell'EA trovati finora.

## Applicazione concreta
Nessuna strategia NEXUS è ancora ricostruita da questa fonte in dettaglio —
il concetto ZIKIR (breakout+pullback+entry) è generico e si applica
potenzialmente a `BREAKOUT_ACC`, `TURTLE_SOUP`, `LIQ_SWEEP`, `ORDER_BLOCK`,
`SH_BMS_RTO`/`SMS_BMS_RTO`. Da incrociare quando si costruiscono i loro
setup buy/sell — vedi [[NEXUS EA - Setup Buy-Sell — Framework]] e
[[TODO - Backtest 10Y]].

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]] · [[NEXUS EA - Setup Buy-Sell — Framework]] · [[NEXUS EA - Principi]]
