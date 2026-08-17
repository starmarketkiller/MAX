---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, debug, audit, bug]
created: 2026-08-16
updated: 2026-08-16
---

# NEXUS EA — Audit di Coerenza su Tutte le 67 Strategie Registrate (16/08)

Seguito del debug framework fornito dall'utente, esteso dal nucleo attivo
(12 strategie, verificate con scenari sintetici) a tutto il catalogo
Python (`server/backtest.py`, `STRATEGIES` dict). Metodo: `run_backtest`
su dati reali per ciascuna strategia, poi controllo automatico che ogni
trade con `reason=SL` o `reason=TP` abbia il prezzo di chiusura dal lato
coerente con `side` e il segno di `r` (`server/research_scripts/
full_catalog_audit_16-08.py`).

## Risultato

46 pulite, 7 con incoerenze reali, 2 senza segnali nel campione (non bug,
solo rari), 0 crash.

## BUG 1 — CRT: target dietro l'entry (`_crt_series`)

Verificato anche nel motore centrale (non solo nello script sperimentale
M5 del 16/08 mattina): **22-33% dei trade CRT/CRT_MINSTOP_FILTER hanno
`reason=TP` con R negativo o quasi nullo** — il target (crl/crh, dal
range di 2 candele prima) risulta già dietro o troppo vicino all'entry
(close della barra segnale) al momento dell'apertura. Il floor
`InpCRT_MinStopATR` protegge lo SL da distanze troppo strette, ma
**nessun controllo equivalente esiste sul lato TP**. Esempio reale
(30m, 2026-07-10 17:00): SELL, entry 4105.605, TP toccato alla barra
successiva con r=-0.17 invece di un vero profitto.

Non richiede azione: CRT è già disattivata e chiusa su basi più solide
(costi, walk-forward, vedi [[NEXUS EA - Motore Costi e Riverifica Nucleo (14-08)]]).
Documentato per completezza del registro bug.

## BUG 2 — famiglia FVG_MIT: SL dal lato sbagliato (`_fvg_mit_sl_tp`)

`_fvg_mit_sl_tp` (righe ~1334) calcola lo SL a partire dal bordo della
zona FVG (`l2 + 0.4×ATR` per una SELL, `h2 - 0.4×ATR` per una BUY),
assumendo implicitamente che l'entry sia vicino a quel bordo. Ma
`sig_fvg_mit` richiede solo che il **minimo/massimo** (wick) della barra
tocchi la zona, non la chiusura — e l'entry reale nel motore è la
**chiusura**. Quando la barra rifiuta con forza (chiusura ben oltre il
bordo della zona), l'entry finisce lontano dal bordo usato per calcolare
lo SL, e lo SL può risultare dal lato sbagliato.

Esempio reale (4h, 2022-01-13 08:00): SELL, entry=1823.692, l2=1820.1555,
SL calcolato=1822.686 — **sotto l'entry su una SELL** (dovrebbe stare
sopra). Verificato che il minimo della barra (1819.087) tocca la zona
come richiesto dal segnale, ma la chiusura (1823.692, il vero entry) è
$3.5 più in alto del bordo usato per lo SL.

Stessa causa probabile per `FVG_MIT_WINDOW` (`_fvg_mit_window_sl_tp`,
8 incoerenze) e verosimilmente `IFVG_CHOCH_WINDOW`/`ORDER_BLOCK_V2`/
`SILVER_BULLET_V2` (1 incoerenza ciascuna, stesso pattern strutturale
zona-based) — non ancora verificate una per una nel dettaglio.

**Nessuna delle strategie coinvolte è nel nucleo live** (FVG_MIT
disattivata da tempo, FVG_MIT_WINDOW disattivata il 14/08, le altre non
sono mai state nel nucleo). Nessuna azione urgente. Se una di queste
venisse mai riconsiderata, il fix corretto è: calcolare SL/TP relativi
all'entry REALE (chiusura), non al bordo della zona assumendo prossimità.

## Cosa NON è un bug

- OTE_CONT_V2, WEEKLY_EXP: zero segnali nel campione di 20.000 barre —
  campione raro (setup a bassa frequenza), non un errore.
- Tutte le altre 46: nessuna incoerenza trovata, incluso l'intero nucleo
  attivo di 12 strategie (già verificato separatamente con scenari
  sintetici formali, vedi nota precedente sul debug LONDON_BO/SAR/MACD/
  EMA_PULLBACK/FVG_CONT/BREAKOUT_ACC/ADX_RSI/TSI/LIQ_SWEEP/AMD_CONT/
  AMD_REVERSAL/LDN_REVERSAL).

## Metodo, limiti

Il controllo di coerenza è un test di sanità (il prezzo di chiusura deve
muoversi nella direzione giusta rispetto a `side` e all'esito), non una
fedeltà MQL5 completa — cattura inversioni di segno e geometrie rotte,
non garantisce che la logica di ingresso rispecchi esattamente l'EA reale
(quello è verificato separatamente, caso per caso, dove già fatto).
