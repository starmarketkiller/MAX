---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fonte, cronologia, said, riassunto-ea]
created: 2026-07-15
updated: 2026-07-15
---

# Fonte: chat WhatsApp con Said (15/04-13/07/26)

A differenza delle altre fonti in questa cartella, questa non è un manuale
di trading esterno — è **cronologia di progetto** (conversazione tra
l'utente/Max e il collega Said, socio/utilizzatore dell'EA su conto reale
piccolo) più alcuni **esempi di ragionamento discrezionale dal vivo**. Utile
soprattutto come conferma incrociata di problemi già noti e come contesto
storico. ⚠️ Il file originale conteneva credenziali in chiaro (login MT5,
URL/credenziali pannello admin) — **non riportate qui**, consigliato
cambiarle.

## Il riassunto tecnico dell'EA (24/06, scritto da Max per Said)
Nel mezzo della chat c'è un riassunto tecnico completo di NEXUS
(`v2.0.12_GATES_OFF`) scritto dall'utente stesso. Conferma quasi tutto già
nel vault, con alcuni dettagli aggiuntivi non ancora documentati altrove:

- **Timeframe usati**: M5 (conferma precisa), M15 (tempo principale segnale),
  H1 (contesto), H4 (direzione/struttura).
- **Score**: aumenta con confluenza multi-strategia, allineamento HTF, falsa
  rottura coerente, vicinanza a livello importante, candela di conferma
  forte, pressione buyer/seller favorevole. Diminuisce con mercato confuso,
  contro-trend HTF, spread peggiore del normale.
- **Profilo di rischio "Balanced" (default all'epoca)**: 1% rischio/trade,
  lotto max 5, max 12 trade/giorno, max 4 posizioni contemporanee, blocco
  dopo ~5% perdita giornaliera, **score minimo 70** (adattato da
  sessione/router). — Rilevante: la nostra scoperta che lo score non ha
  potere predittivo per SAR/MACD/RSI_DIV ([[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]])
  va confrontata con questa soglia 70 di allora.
- **Prese di profitto parziali**: 30% a ~+1.5× volatilità media, 50% del
  rimanente a ~+3× — non documentato altrove nel vault, verificare se ancora
  attivo in v2.5.0.
- **Due sistemi di trailing in parallelo** (da coordinare — rischio di
  modifiche eccessive allo stop) e **due limiti di durata separati** (4h e
  12h, il primo che scatta chiude) — **verificato 15/07: ancora presente in
  v2.5.0**. `NXS_ManageBreakevenAndTrail()` (`NXS_Management.mqh:29`) chiude
  a `InpMaxHoldHours` (4h, ma scalato a ~40 barre del TF se il profilo
  strategia è attivo); `NXS_Prot_CheckMaxHold()` (`NXS_Protections.mqh:190`,
  gate separato `InpUseMaxHold`) chiude indipendentemente a
  `InpProt_MaxHoldHours` (12h, scalato con `NXS_TF_LifeFactor`). Sono due
  meccanismi realmente indipendenti che possono chiudere la stessa posizione
  con logiche di scaling diverse — quello che scatta per primo vince. Da
  unificare in un solo controllo, come l'utente stesso aveva già notato il
  24/06.
- **Bug noto all'epoca**: chiusura pre-weekend non realmente limitata al
  venerdì nonostante il commento nel codice lo dica.
- **Moduli dichiarati ma non collegati bene** (Locked Profile, Learner
  automatico, Risk Shield avanzato, History Sync) — pattern sistemico già
  visto nella nostra indagine (il contatore `executed` rotto,
  [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]): **funzionalità
  "avanzate" presenti nel codice ma non richiamate dal percorso reale che
  apre i trade**. Vale la pena un audit sistematico di "cosa è collegato
  davvero" prima di aggiungere altre funzionalità.
- **Descrizioni delle 36 strategie**, incluse le versioni a sessione/ICT
  (Silver Bullet, AMD Reversal/Continuation, Judas Swing, London/NY
  Reversal, Power of Three, OTE Continuation) con un dettaglio di trigger
  leggermente maggiore di quanto avevamo — utile per il Tier 3 di
  [[NEXUS EA - Setup Buy-Sell — Framework]] (in attesa di altro materiale).

## Bug auto-osservato dall'utente (03/07)
> "L'unico errore è che ho attivato il confluence HTF... se in D1/H4 il
> trend è buy lui continua a cercare dei buy"

Osservazione diretta dell'utente su un problema del filtro di confluenza
HTF — coerente con quanto trovato in
[[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]] (il filtro HTF attuale
non taglia abbastanza il lato debole). Conferma che il problema era già
notato prima della nostra analisi, non solo un artefatto dei dati.

## Piano "Said Style" — proposto ma mai completato
Il 30/06 l'utente propone di creare un modulo `NXS_Strategy_Colleague.mqh`
per formalizzare il metodo discrezionale di Said in una strategia vera e
propria, con un template di 15 domande esplicite (in quali condizioni
buy/sell, che zona deve raggiungere il prezzo, wick o chiusura, timeframe di
costruzione/conferma, dove SL/TP, gestione uscita, orari/notizie da evitare,
tentativi permessi, rischio fisso, situazioni emotive da escludere) più il
requisito di **almeno 20 operazioni corrette e 20 setup scartati con
screenshot pre-ingresso**. **Non risulta mai completato nella chat** — resta
un'idea, non un metodo estratto. Se l'utente vuole procedere, serve
rispondere esplicitamente alle 15 domande (elencate qui sopra in forma
riassunta, vedi anche [[NEXUS EA - Setup Buy-Sell — Framework]] per lo
stesso schema applicato alle strategie esistenti).

## Esempio di ragionamento discrezionale dal vivo (01/07, Max)
> "L'altro ieri ha sweeppato un minimo in H4, ha rintracciato in buy,
> sellato di nuovo vicino ai minimi che corrisponde con la trend line che è
> stata ritestata, ultimo minimo dopo il retest non è stato invalidato, per
> me è buy... se guardi in H1 ha sweeppato anche il massimo precedente"

Un esempio reale di analisi multi-timeframe: liquidity sweep su H4 →
validazione con retest di trendline → conferma su H1 con secondo sweep. Più
avanti, principio dichiarato: *"Trader grandissimi operano sullo sweep
dell'ultimo massimo/minimo"*. Coerente con la logica ZIKIR/MSNR già raccolta
nelle altre fonti — un'ulteriore conferma indipendente dello stesso pattern
(breakout/sweep → pullback/retest → entry), stavolta dalla viva voce
dell'utente sul suo modo di leggere il grafico.

## Conferma: il conto reale ha bruciato nello stesso periodo dei backtest negativi
11/07: *"il conto è bruciato ma sto continuando a vedere e aggiornare su
altro"*. Timeline coerente con i risultati negativi del backtest 10y
segmentato (dello stesso periodo) — il problema non è solo nel backtest, si
è manifestato anche sul conto reale in parallelo.

## Cosa NON c'è in questa fonte
Nessuna regola di trading nuova, formalizzata e pronta da implementare — è
soprattutto conferma/contesto. Le foto/video/audio del pacchetto media
(controllati in precedenza) non aggiungono altro (non trading-relevant).

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Setup Buy-Sell — Framework]] · [[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[TODO - Backtest 10Y]]
