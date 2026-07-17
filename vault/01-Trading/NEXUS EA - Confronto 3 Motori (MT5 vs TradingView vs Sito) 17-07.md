#nexus #trading #multi-agent #pinescript #confronto

# Confronto SAR/MACD/ADX_RSI/RSI_DIV su 3 motori indipendenti (17/07 notte)

Dopo i test Pine Script su TradingView (`pinescript/README.md`), ho fatto girare le stesse 4 strategie (baseline vs variante TP-largo±breakeven) anche sul motore Python del sito (`server/backtest.py`, dati reali Yahoo, `bars=2500`), per triangolare — non per sostituire nessuno dei tre, ognuno ha il suo modello di fill/spread/dati.

## Tabella comparativa (direzione del cambiamento baseline→variante)

| Strategia | Metrica | TradingView | Sito (Python) | Accordo? |
|---|---|---|---|---|
| **SAR** | Trade | 406→404 | 84→89 | — |
| | Win Rate | 37,44%→34,65% (↓) | 40,5%→32,6% (↓) | ✅ stessa direzione |
| | PF | 1,276→1,30 (↑) | 1,61→1,50 (↓) | ❌ **direzione opposta** |
| | Max DD | 7,52%→7,79% | 7,73%→7,73% (=) | parziale |
| **MACD** | Trade | 292→192 (↓ forte) | 109→77 (↓ forte) | ✅ |
| | Win Rate | 48,29%→28,65% (↓ forte) | 49,5%→28,6% (↓ forte) | ✅ **quasi identico in valore assoluto** |
| | PF | 1,321→1,459 (↑) | 1,43→1,72 (↑) | ✅ |
| | Max DD | 7,61%→6,44% (↓) | 7,75%→6,79% (↓) | ✅ |
| **ADX_RSI** | Trade | 217→199 | 170→133 | — |
| | Win Rate | 29,49%→24,62% (↓) | 26,5%→15,0% (↓ forte) | ✅ stessa direzione |
| | PF | 1,326→1,672 (↑) | 1,4→1,92 (↑) | ✅ |
| | Max DD | 5,25%→4,65% (↓) | 10,47%→10,64% (≈+) | ❌ direzione opposta (minore) |
| **RSI_DIV** | PF baseline | 0,931 (**perdita**) | 1,34 (profittevole) | ❌ **disaccordo forte** |
| | PF variante | 0,989 (~breakeven) | 1,39 (profittevole) | ❌ **disaccordo forte** |

## Lettura

**MACD è la conferma più forte di tutta la sessione**: tre motori indipendenti (produzione MT5/sito che ha originato il fix il 17/07, TradingView, e ora anche questo secondo run sul sito) concordano che allargare il TP a 8×ATR + breakeven a 1R migliora PF e riduce drawdown, pagando un calo di win rate — e il calo di win rate è quasi lo stesso identico numero sui due motori indipendenti (48,29%→28,65% TV vs 49,5%→28,6% sito). Non è un caso statistico isolato.

**ADX_RSI conferma nella direzione principale** (PF e win rate concordano), ma diverge sul drawdown (TV lo migliora, il sito lo peggiora leggermente) — variabile secondaria, non inverte il verdetto complessivo.

**SAR resta ambiguo come già annotato nel README Pine** — qui la conferma è ancora più netta: i due motori indipendenti sono in disaccordo diretto sulla direzione del PF (TV migliora, sito peggiora). Non applicare questo cambiamento senza altri dati.

**RSI_DIV è il caso più interessante**: non è un semplice disaccordo tra motori, è un disaccordo su **se la strategia sia profittevole o no** nel periodo osservato. TradingView (solo ~1,5 anni di storico intraday H1 disponibile sul piano Basic) la mostra in perdita; il sito (finestra diversa, dati Yahoo) la mostra profittevole. Combinato con l'audit "3 anni vs 10 anni" di prima — è un segnale che RSI_DIV potrebbe essere **regime-dipendente** (buona in certi periodi, cattiva in altri), non un errore di uno dei due motori. Da tenere d'occhio quando arriveranno i dati MT5 reali del sweep in corso.

## Cosa NON fare con questi dati

Nessuna modifica a `MQL5/` sulla base di questo confronto da solo — resta un terzo/quarto punto di osservazione, non un tie-breaker (principio già stabilito). Il fix MACD è già in produzione (applicato il 17/07) ed è quello con più conferme incrociate. Per SAR e RSI_DIV, aspettare più dati (sweep MT5 in corso, eventuale finestra dati più lunga) prima di decidere.
