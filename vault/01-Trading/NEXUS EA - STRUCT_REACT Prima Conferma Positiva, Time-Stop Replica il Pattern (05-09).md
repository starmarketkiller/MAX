---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, struct-react, confermata, time-stop]
created: 2026-09-05
updated: 2026-09-05
---

# NEXUS EA — STRUCT_REACT prima conferma positiva su MT5 reale, il time-stop da 40 barre si ripete (05/09)

## Risultato

Prima verifica in assoluto sul vero motore MT5 (dopo aver sbloccato
il terzo cancello silenzioso `NXS_Profile_Enabled`, vedi
[[NEXUS EA - Terzo Cancello Silenzioso Trovato su 7 Strategie, Audit Proattivo (05-09)]]):
H4, 3 anni, selettore vero 16, profilo BUY-only nativo.

| Metrica | Valore |
|---|---|
| Trade | 211 (tutti BUY — direction-lock del profilo confermata) |
| Win rate | 42.7% (90/211... nota: 92 nel dettaglio per-trade, differenza da arrotondamento deal/trade) |
| Profit factor | 1.29 |
| Net profit | $1560.22 |
| Sharpe | 1.10 |
| Max DD equity | $1109.18 (alto in proporzione al deposito di $1000) |

Positiva ma non tra le migliori di oggi (FVG_CONT PF1.93, ADX_RSI
PF2.04 restano sopra) — PF Python era 2.65, ennesima conferma che il
proxy Python sovrastima sempre rispetto al motore reale.

## Analisi CSV per-trade

- **Motivo chiusura**: 98 stop loss (46%), 33 take profit (16%), 70
  chiusure senza commento, 9 protezione drawdown (`NXS:DD`), 1 fine
  test.
- **Il time-stop da 40 barre si ripete identico a MACD**: 60 dei 70
  trade "senza commento" cadono esattamente a ~160h (40 barre H4),
  di cui **50 vincenti (83% WR)**, netto **+$2318.10** — di nuovo più
  dell'intero profitto del test. Vedi
  [[NEXUS EA - Il Filtro Sessione Era su un Percorso di Esecuzione Diverso (04-09)]]
  per la scoperta originale su MACD e la causa tecnica
  (`NXS_MaxHold_LimitSec`, ora esposta come `InpProfileMaxHoldBars`).
- **Durata vincenti/perdenti**: media 136.6h sui vincenti contro 58.7h
  sui perdenti — stesso rapporto ~2.3:1 già visto su MACD, tagliare le
  perdite e lasciar correre i vincenti funziona anche qui.
- Non è quindi una particolarità di MACD: **il time-stop da 40 barre
  sembra un meccanismo strutturalmente utile a più strategie**,
  rafforza la priorità di testare `InpProfileMaxHoldBars` più ampio
  (test 80 barre già in coda su MACD al momento di scrivere questa nota).

## Addendum (06/09) — BUY-only è un salvataggio, non un progetto trend-following

Punto dell'utente: il confronto con buy&hold (vedi
[[NEXUS EA - Il Vero Benchmark e Buy&Hold, Quasi Tutto Oggi lo Perde (05-09)]])
ha senso solo per strategie che NON sono progettate per seguire il
trend — per quelle, se SELL non regge mentre BUY sì, è la prova che
non c'è edge, solo esposizione al rally. Controllato il codice
(`NXS_StrategyProfiles.mqh` riga 165-169): **la versione simmetrica
di STRUCT_REACT (BUY+SELL, H1) era testata ed era IN PERDITA (PF0.61
su tutto lo storico Dukascopy)** — il BUY-only attuale è stato scelto
il 25/08 *dopo* aver visto che SELL non reggeva, non è una scelta di
progetto per una strategia trend-following.

Questo riclassifica STRUCT_REACT nello stesso gruppo di MACD/ADX_RSI/
BOLLINGER: "confermata positiva" (PF1.29) era vero alla lettera ma
probabile riflesso del rally, non di un segnale genuino — coerente
col Calmar già leggermente sotto il buy&hold (1.41 vs 1.49) trovato
nella nota sul benchmark. **Non testata** una finestra storica con
mercato ribassista o laterale per verificare se BUY-only regge anche
lì (unico modo per distinguere vero edge da semplice beta lunga).

## Non ancora fatto

- Nessun filtro/ricetta aggiuntiva testata (Elliott, RSI, sessione) —
  solo il trigger nudo col profilo nativo.
- Il conteggio win (90 dal report aggregato vs 92 dal dettaglio
  per-trade) ha una piccola discrepanza di arrotondamento non
  investigata — probabile un trade a profitto zero o±.

## Collegamenti
[[NEXUS EA - Terzo Cancello Silenzioso Trovato su 7 Strategie, Audit Proattivo (05-09)]] · [[NEXUS EA - Il Filtro Sessione Era su un Percorso di Esecuzione Diverso (04-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
