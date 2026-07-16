---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: MACD
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: MACD

## Tipo
Trend-following

## Trigger meccanico
MACD > signal e sopra 0, prezzo sopra EMA200 (long, speculare per short).

## Configurazione attuale (v2.5.1, 17/07)
- **Timeframe**: H4
- **SL**: 2.0× ATR · **TP**: 8.0× ATR (era 3.0, vedi fix sotto)
- **Filtro HTF**: True
- **Breakeven**: 1.0× rischio (nuovo)
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 1.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 2134 setup, 72W/48L/24BE, WR 60.0%, expR +0.062, **PF 1.35**
- **3 anni**: 742 setup, 52W/42L/13BE, WR 55.3%, expR +0.023, **PF 1.11**

## Risultati (backtest 10y segmentato v2.5.0, 6 anni affidabili 2019-2024)
994 trade totali. R per anno: 2019 -6.2 · 2020 -11.9 · 2021 +2.5 · 2022 -4.4 ·
2023 +1.5 · 2024 -2.6. **Somma -21.1R — 2 anni su 6 positivi**, dominata da
due anni catastrofici (2019 e 2020). Il 2024 resta negativo ma meno grave dei
peggiori. Dettaglio completo: [[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Analisi trade-level (15/07, corretta)
Score interno senza potere predittivo. Bias direzionale forte: LONG 52.0% WR
vs SHORT 43.6% WR — il trigger short è strutturalmente più debole del
trigger long. **Non significa "disattivare gli short"** (correzione esplicita
dell'utente, vedi [[NEXUS EA - Principi]] #9): significa che MACD ha bisogno
di un **setup SELL indipendente**, con trigger/TF/parametri propri, non lo
stesso trigger del buy applicato al ribasso. Nota: l'R-sum a 6 anni è
negativo (-21.1R) mentre il $ sum grezzo è positivo (+468.6$) — le due
metriche divergono, merita uno sguardo più attento su cosa lo spiega.
Dettaglio: [[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]].

## Stato
🔴 REGREDITA — questa è la scoperta più importante su MACD: sotto v2.4.8 era
**già validata** (PF 1.11 sui 3 anni, 94 trade). Il "raffinamento" v2.5.0
basato sullo screening sito (motore Python/Yahoo, non MT5) l'ha resa la
**seconda peggiore strategia del portafoglio**. Conferma [[NEXUS EA -
Principi]] #5 su scala molto più ampia: un edge del sito non va sostituito a
una config MT5 già validata senza prima confermarlo su MT5. Da valutare se
tornare alla config v2.4.8 (SL/TP diversi, vedi log commit) e ri-testare.

## Fix Blocco 4 (16/07): bug di proxy sul sito, stesso tipo di SAR/BJORGUM
`sig_macd()` sul motore sito era un semplice incrocio della MACD-line con
lo zero — non testava mai MACD-line vs signal-line + filtro EMA200 come la
vera funzione qui sopra. Corretto (aggiunta la signal-line mancante). Con
la logica vera, il sito è **ancora più positivo** di prima su ogni
timeframe/HTF provato (PF1.15-1.52, 108-141 trade) — non un artefatto del
bug. La config attuale (H4/HTF ON) resta la migliore trovata, nessun
cambio numerico applicato al profilo, solo corretto il commento che
citava "robusta su sito E MT5" (era basato sul proxy sbagliato).

**Implicazione**: con segnale confermato solido **due volte** (proxy
vecchio e nuovo) ma **1.496 trade reali su MT5 in maggioranza negativi**,
il sospetto di un problema di esecuzione MT5 (non di trigger) si rafforza
molto — vedi [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] per
il quadro complessivo con FVG_CONT e RSI_DIV (stesso pattern, 3 casi ora).

## Fix reale 17/07: TP largo + breakeven, dall'analisi MFE/MAE
Richiesta dell'utente: se il trigger azzecca la direzione la maggior parte
delle volte, il problema può essere la gestione (SL/TP), non il segnale.
Verificato con un'analisi diretta: seguito ogni segnale 40 barre avanti
misurando il massimo movimento a favore (MFE) indipendentemente da dove
sta oggi SL/TP. Risultato: **70.5% dei segnali raggiunge almeno 1R a
favore**, MFE medio **2.40R contro un TP attuale di soli 3.0** — il TP
stretto tagliava sistematicamente un movimento che il trigger aveva già
previsto giusto.

Sweep di gestione (SL/TP/breakeven/trailing) sulla config reale
(H4+HTF): **SL2.0/TP8.0/breakeven a 1R** batte nettamente la config
attuale su ogni metrica:

| Config | Trade | PF | DD% | Net |
|---|---|---|---|---|
| Attuale (TP3.0, no BE) | 111 | 1.48 | 6.23 | +2.879 |
| **TP8.0 + BE1.0** | **72** | **2.05** | **5.85** | **+3.643** |

Il trailing NON ha aiutato (0 in ogni config migliore trovata) — la leva
è TP molto più largo + breakeven, non un trailing stretto. Applicato in
`NXS_StrategyProfiles.mqh`. **Non ancora validato su MT5** — anzi un TP
più largo espone il trade più a lungo agli stessi problemi di esecuzione
già sospettati (vedi sotto), quindi la validazione qui è ancora più
importante del solito. Dettaglio completo (tutte e 4 le strategie
analizzate insieme): [[NEXUS EA - Gestione Uscita MFE-MAE (17-07)]].

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] · [[NEXUS EA - Gestione Uscita MFE-MAE (17-07)]] · [[Fvg Cont]]
