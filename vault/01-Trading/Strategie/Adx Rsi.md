---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: ADX_RSI
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: ADX_RSI

## Tipo
Trend-following

## Trigger meccanico
EMA50 come filtro trend + RSI in banda 45-65 (long) / 35-55 (short) — logica del sito, riportata in v2.3.8.

⚠️ **Scoperta 15/07**: nonostante il nome, **non calcola mai il vero
indicatore ADX** — né sul sito (`backtest.py:301`) né in MQL5 (commento
esplicito "riportata alla logica del sito", `NXS_Strategies.mqh:111`). È un
fraintendimento storico del nome, non un bug di questa sessione. Vedi
[[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]].

## Configurazione attuale (v2.5.1, 17/07)
- **Timeframe**: D1
- **SL**: 1.0× ATR · **TP**: 10.0× ATR (era 4.0, vedi fix sotto)
- **Filtro HTF**: True
- **Breakeven**: 1.5× rischio (nuovo)
- **Trailing**: largo (corre)
- **Rischio per trade**: 1.3%
- **Abilitata nell'EA**: Sì

⚠️ Anche il trigger stesso è cambiato dopo la raccolta dei 6 anni di dati
MT5 sotto (filtro `g_adx<20` aggiunto il 15/07, **dopo** il push dei dati
del segmento 9) — il -15.3R sotto riflette il trigger VECCHIO, non
ancora testato con quello attuale. Vedi [[NEXUS EA - Test Generale Post-Fix (16-07 notte)]].

## Risultati (build v2.4.8, CONFIG PRECEDENTE (diversa da quella sopra))
- **3 mesi**: 4361 setup, 20W/26L/11BE, WR 43.5%, expR +0.014, **PF 1.17**
- **3 anni**: 780 setup, 21W/42L/19BE, WR 33.3%, expR -0.094, **PF 0.45**

## Risultati (backtest 10y segmentato v2.5.0, 6 anni affidabili 2019-2024)
596 trade totali. R per anno: 2019 +0.4 · 2020 -3.0 · 2021 -3.7 · 2022 -4.2 ·
2023 -3.7 · 2024 -1.1. **Somma -15.3R — solo 1 anno su 6 positivo (2019,
marginale +0.4)**. Il 2024 è meno negativo dei tre anni precedenti — primo
segno debole di miglioramento, da confermare col segmento 10. Dettaglio
completo: [[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Test A/B 15/07: filtro ADX reale (motore sito, 10y)
Implementato un vero ADX(14) Wilder e testate varie soglie sullo stesso
trigger. **La soglia da manuale (ADX>25) rovina la strategia** (PF 1.26→1.00,
DD peggiora). **ADX>22 è la soglia migliore trovata**: PF 1.26→1.29, DD
quasi dimezzato (11.44%→6.88%), campione ancora ampio (139 trade). Non
ancora testato su MT5. Dettaglio completo:
[[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]].

## Stato
🔴 FALLITA — confermato su campione ampio (596 trade). Come SAR, l'HTF filter
è correttamente attivo nel codice (`NXS_StrategyProfiles.mqh:23`) ma il fix
non ha invertito la tendenza già vista su v2.4.8 (PF 0.45 sui 3 anni).
**Prossimo passo concreto**: implementare `iADX` reale con soglia ~20-22
(non 25) e ri-testare isolata su MT5 prima di generalizzare.

## Fix reale 17/07: TP largo + breakeven, dall'analisi MFE/MAE
Stessa analisi fatta su MACD/SAR/RSI_DIV (richiesta dell'utente: se il
trigger azzecca la direzione spesso, il problema può essere la
gestione). Seguito ogni segnale 40 barre avanti: **85.6% raggiunge
almeno 1R a favore**, MFE medio **4.52R contro un TP attuale di 4.0** —
di nuovo il TP taglia un movimento già previsto giusto.

Sweep di gestione sulla config reale (D1+HTF): **SL1.0/TP10.0/breakeven
a 1.5R** batte la config attuale su PF e net (DD leggermente peggiore):

| Config | Trade | PF | DD% | Net |
|---|---|---|---|---|
| Attuale (TP4.0, no BE) | 167 | 1.48 | 11.54 | +7.191 |
| **TP10.0 + BE1.5** | **129** | **1.97** | **12.48** | **+8.991** |

Applicato in `NXS_StrategyProfiles.mqh`. **Non ancora validato su MT5** —
e qui la validazione ha un peso doppio, perché a differenza di
SAR/MACD/RSI_DIV il trigger di ADX_RSI **è già cambiato** dopo la
raccolta dei 6 anni di dati (vedi sopra): un test isolato con questa
nuova gestione testerebbe DUE cose nuove insieme (trigger + TP/BE), non
solo una. Dettaglio completo: [[NEXUS EA - Gestione Uscita MFE-MAE (17-07)]].

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]] · [[NEXUS EA - Gestione Uscita MFE-MAE (17-07)]] · [[NEXUS EA - Test Generale Post-Fix (16-07 notte)]]
