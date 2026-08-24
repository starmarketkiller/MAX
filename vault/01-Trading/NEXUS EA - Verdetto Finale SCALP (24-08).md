---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, scalp, m15, verdetto-finale, costi-dominanti]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Verdetto finale sulle SCALP_* (24/08)

## Perché

Su richiesta esplicita dell'utente ("scoprire cosa le farebbe diventare
profittevoli"), continuato l'indagine sulle 4 SCALP_* dopo il verdetto
negativo di ieri sera (famiglia sessione/scalp su M15/M30, tre assi
provati - TF, ampiezza stop, timing di uscita - nessuno risolutivo).
Oggi altri due ingredienti mai provati.

## Ingrediente 4: filtro ER lungo (167 giorni, lo stesso di tutto il resto del catalogo)

`scalp_rescue_24-08.py`. Risultato: **il filtro ER da solo (senza
nemmeno il floor) uccide il 99.9%+ dei segnali**. Verificato
direttamente contando i segnali grezzi vs quelli che superano l'ER:

| Strategia | Segnali grezzi | Superano SOLO ER (167gg) |
|---|---|---|
| SCALP_BB_FADE | 3.434 | **1** |
| SCALP_EMA | 7.227 | **4** |
| SCALP_RANGE_BRK | 11.087 | **7** |
| SCALP_RSI_SNAP | 3.770 | **4** |

**Causa capita, non solo osservata**: l'Efficiency Ratio a 167 giorni
misura se il mercato sta facendo un trend su una scala di MESI - una
condizione quasi mai vera nello stesso istante in cui scatta un segnale
di microstruttura M15 (incrocio EMA, RSI estremo, rottura di range).
Richiedere ENTRAMBE le condizioni insieme non e' un filtro severo, e'
quasi una contraddizione strutturale tra scale temporali.

## Ingrediente 5: ER a finestra corta (12.5-50 ore) + target stretto coerente con lo scalping

Ipotesi diretta dalla diagnosi sopra: non abbandonare il filtro di
regime, ADATTARLO alla scala giusta (12.5-50 ore invece di 167 giorni),
insieme a un target davvero da scalp (SL0.5/TP1.0×ATR invece di
1.0/3.0+). Risultato: **catastrofico**, PF 0.05-0.12 su tutte e 4 le
strategie, tutte le combinazioni di finestra provate (50/100/200 barre).

**Causa**: stessa lezione della saga CRT e dello stop M5 del 16/08 -
uno stop cosi' stretto (0.5×ATR) rende il costo fisso (spread+slippage)
dominante rispetto al rischio per trade, indipendentemente da quanto
sia "giusto" il filtro di regime a monte.

## Verdetto finale

**Cinque ingredienti indipendenti provati su due sessioni, nessuno
funziona**: timeframe (M15/M30), ampiezza dello stop (stretto E largo),
timing di uscita (fine giornata), filtro di regime a finestra lunga
(uccide il campione), filtro di regime a finestra corta + target stretto
(costi dominanti). Non è più "non abbiamo trovato la ricetta giusta" -
è una conferma multi-angolo che **le SCALP_* così come sono codificate
non hanno edge sfruttabile su questo strumento e questa struttura di
costi**, indipendentemente dalla gestione di ingresso/uscita.

Non escluso che un segnale di trigger DIVERSO (non le attuali
SCALP_BB_FADE/EMA/RANGE_BRK/RSI_SNAP, che sono varianti semplici di
indicatori classici) possa avere edge — ma questo è un problema di
segnale, non più di parametri o filtri, fuori dallo scope di
un'ottimizzazione di ricetta.

## Prossimi passi aperti

- Se si vuole insistere sulle SCALP_*, serve un segnale nuovo (non un
  altro filtro/uscita sul segnale esistente) - fuori scope per oggi.
- Chiuso definitivamente il filone "rendere profittevole la famiglia
  scalp esistente" salvo nuova ipotesi sul segnale stesso.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Famiglia Sessione e SCALP su M15-M30 (24-08)]]
