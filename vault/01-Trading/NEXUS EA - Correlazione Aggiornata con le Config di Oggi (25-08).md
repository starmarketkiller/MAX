---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, correlazione, portafoglio, diversificazione]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Correlazione aggiornata con le config di oggi (25/08)

## Perché

Il problema di allocazione del portafoglio era in pausa dal 24/08 su
richiesta dell'utente, con la correlazione calcolata sulle config di
allora ([[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]).
Ripreso oggi su indicazione esplicita ("procedi col portafoglio") —
ma il catalogo è cambiato molto da ieri: quasi tutte le strategie
hanno trailing/filtro Elliott/D1-align aggiunti, 3 nuove promosse
(ML_ADAPTIVE_SUPERTREND/BOLLINGER/RSI_DIV — ML_ADAPTIVE_SUPERTREND
non ancora inclusa in questo giro, segnale esterno più complesso da
integrare), 1 nuova nata (ELLIOTT_WAVE3_CONT), TURTLE_SOUP/LDN_REVERSAL
riverificate. Ricalcolare la correlazione con le config attuali era il
prerequisito prima di qualunque decisione — decidere sui dati vecchi
avrebbe rischiato di ottimizzare per un portafoglio che non esiste più.

`correlation_updated_25-08.py` — stesso metodo del 24/08 (bucket
giornaliero di R netto per strategia, Pearson a coppie), 24 strategie
(tutto il catalogo tranne ML_ADAPTIVE_SUPERTREND, escluso per ora
essendo un segnale esterno più costoso da integrare in questo giro).

## Il cluster trend resta, ma la lista dei diversificatori cambia parecchio

**DARVAS_BOX/DONCHIAN_TURTLE ancora al 99.9%** (r=0.999, era 0.997) —
confermato di nuovo, restano essenzialmente la stessa strategia. Il
cluster più ampio (SAR/SAR_ADX20/MACD/ADX_RSI/BREAKOUT_ACC/DARVAS_BOX/
DONCHIAN_TURTLE) resta moderatamente-fortemente correlato tra loro
(r 0.4-0.86) — **il trailing e il filtro Elliott, applicati in modo
abbastanza uniforme su tutto il cluster, non lo hanno scorrelato**:
un ingrediente che migliora il PF di ogni membro allo stesso modo non
cambia la struttura di correlazione sottostante, solo la sua scala.

**La lista dei migliori diversificatori (correlazione media più bassa)
è cambiata**:

| Strategia | Corr. media 24/08 | Corr. media 25/08 | Nota |
|---|---|---|---|
| **FVG_MIT** | +0.015 | **-0.005** | Ora **negativa** — ed è anche la strategia più forte del catalogo (PF3.24) |
| OTE_CONT | +0.028 | +0.008 | Confermata, ancora più bassa |
| STRUCT_REACT | -0.019 | +0.016 | Resta bassa (il filtro Elliott non applicato qui potrebbe spiegare la lieve risalita) |
| **RSI_DIV** | n/a (non esisteva in portafoglio) | **+0.019** | Nuova diversificatrice — non identificata ieri |
| **LDN_REVERSAL** | n/a (provvisoria, esclusa ieri) | **+0.029** | Nuova diversificatrice |
| **BOLLINGER** | n/a (rifiutata ieri) | **+0.031** | Nuova diversificatrice |
| **TURTLE_SOUP** | n/a (esclusa ieri) | **+0.051** | Nuova diversificatrice |
| EMA_PULLBACK | -0.012 | +0.058 | Resta bassa |

**4 nuove diversificatrici emergono** (RSI_DIV, LDN_REVERSAL,
BOLLINGER, TURTLE_SOUP) — tutte strategie che ieri erano rifiutate,
provvisorie o non ancora scoperte, ora riverificate/promosse con gli
ingredienti di oggi. Il pool di buone diversificatrici passa da 5
(ieri) a **8** (oggi): FVG_MIT, OTE_CONT, STRUCT_REACT, RSI_DIV,
LDN_REVERSAL, BOLLINGER, TURTLE_SOUP, EMA_PULLBACK.

## Implicazione

Il problema di fondo diagnosticato ieri (il bucket condiviso a 2 slot
premia il cluster ad alta frequenza e affama le diversificatrici a
bassa frequenza) resta identico nella struttura — ma ora ci sono quasi
il doppio delle diversificatrici disponibili con cui costruire un
portafoglio deliberatamente scorrelato, l'approccio esplicitamente
raccomandato come prossimo passo ieri invece di correggere il bucket
condiviso. Prossimo passo naturale: simulare un portafoglio che
include TUTTE e 8 le diversificatrici più una sola rappresentante del
cluster trend (invece di tutti gli 8 membri correlati), e confrontare
drawdown/PnL con quello a 20 strategie di ieri.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
