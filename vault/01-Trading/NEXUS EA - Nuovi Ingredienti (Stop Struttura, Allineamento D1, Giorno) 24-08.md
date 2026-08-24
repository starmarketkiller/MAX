---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, stop-strutturale, multi-timeframe, giorno-settimana]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Stop strutturale, allineamento D1, giorno della settimana (24/08)

## Perché

Esecuzione della lista di idee residue chiesta dall'utente. Tre
ingredienti mai provati oggi, sulle 6 strategie ancora deboli in forma
simmetrica dopo tutti i test precedenti (BJORGUM/RSI_DIV/FVG_MIT/
LDN_REVERSAL/TSI_EXTREME/STRUCT_REACT). `new_ingredients_24-08.py`.

## Fase C — stop strutturale (swing 10 barre, RR fisso 1:3): un solo esito, campione sottile

Quarto tipo di stop provato oggi (dopo ATR-mult, nativo-wick, trailing-ATR).
Solo **LDN_REVERSAL** emerge: retail PF1.28 (**m1=1.31/m2=1.25**, bilanciate,
4/5 finestre), ECN 1.37. Il primo risultato pulito per LDN_REVERSAL in
tutta la giornata (era sempre stata rumorosa/rifiutata con ogni altro
trattamento). Campione ancora sottile (31) — da confermare, non ancora
contata come baseline piena. Le altre 5 restano deboli.

## Fase D — allineamento D1 (sostituisce il filtro ER, non si somma)

**FVG_MIT è la scoperta pulita di questo round**: retail PF1.48
(m1=1.33/m2=1.64, **5/5 finestre**), ECN 1.69 (5/5). Verificato con le
5 finestre CON I NUMERI (non solo m1/m2, lezione di stamattina) — tutte
e 5 tra 1.35 e 1.83, **nessuna finestra debole**, prezzo dei trade da
~1699 a ~4036 (copertura genuina su tutto lo storico, non concentrata).
Il candidato più solido trovato oggi dopo la revisione severa del
BUY-only.

STRUCT_REACT con questo stesso ingrediente: retail 1.23, ma **stessa
firma rally-dipendente** delle finestre precedenti (0.52→0.79→1.27→
1.89→2.31, monotona) — conferma indipendente che STRUCT_REACT ha logica
reale (converge con la scoperta BUY-only di prima) ma resta ancora
esposta al regime, non una prova pulita quanto FVG_MIT qui.

RSI_DIV: PF1.41 ma m1=0.70/m2=2.57, divario enorme — probabile artefatto
di rally, da NON contare senza diagnosi per-data dedicata (non ancora fatta).

## Fase E — esclude lunedì o venerdì: nessun miglioramento

Tutte e 6 le strategie restano deboli con entrambe le esclusioni
(retail sempre <1.0, tranne STRUCT_REACT no-LUN ECN 1.02, appena sopra
pari). Ingrediente chiuso per questo batch — nessuna promozione.

## Bilancio

**1 baseline nuova solida e ben verificata**: FVG_MIT (con allineamento
D1 al posto del filtro ER). **1 baseline provvisoria** (LDN_REVERSAL con
stop strutturale, campione sottile). STRUCT_REACT ottiene una seconda
conferma indipendente della sua natura genuina ma resta comunque
rally-dipendente.

## Prossimi passi aperti (dalla lista dell'utente, non ancora eseguiti)

- **Filtro news/calendario economico**: non eseguibile in questo
  ambiente Python di ricerca — non esiste una fonte dati calendario
  economico collegata qui (il motore MQL5 ha `InpNewsFilter` ma legge da
  un servizio esterno non disponibile in questa sessione).
- **Filtro tick-volume**: XAUUSD OTC ha solo tick-volume sintetico, già
  scartato il 17/08 per lo stesso limite (VWAP). Potenzialmente
  ancora provabile come proxy di liquidità, non tentato oggi per tempo.
- **Entry a limite invece di mercato**: non tentato — richiede modellare
  fill probability/slippage diverso, un cambiamento più strutturale al
  motore di simulazione.
- **Uscita ibrida (parziale + trailing)**: non tentato, provate solo
  separate finora (trailing puro vs target fisso puro).
- **Target variabile sul percentile di volatilità**: non tentato.
- **Confluenza MACD estesa a tutte le baseline**: non ancora fatto oltre
  ADX_RSI/SAR_FLIP/DONCHIAN_TURTLE.
- **Fibonacci come uscita/reverse** (non filtro d'ingresso) e **Elliott
  Wave**: non ancora tentati, idee dell'utente ancora aperte.
- **Simulazione di portafoglio con la lista aggiornata**, **risk engine
  a streak riprovato col floor**, **backlog porting MQL5**, **validazione
  MT5 su tick reali**: tutti ancora da fare, lavoro sostanziale a sé.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Diagnosi Onesta del BUY-only (24-08)]]
