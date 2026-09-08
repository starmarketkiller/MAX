---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: FVG_CONT
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: FVG_CONT

## Tipo
SMC/continuazione

## Trigger meccanico
Gap a 3 candele (low[1]>high[3]) + continuazione nel senso del trend (close vs EMA50) — logica del sito.

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.0× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 0.4%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 443 setup, 15W/21L/2BE, WR 41.7%, expR +0.090, **PF 1.42**
- **3 anni**: 142 setup, 10W/12L/6BE, WR 45.5%, expR -0.009, **PF 0.97**

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
198 trade totali. R per anno: 2019 **-5.7** · 2020 -1.1 · 2021 +1.9 · 2022
+1.9 · 2023 +0.7. **Somma -2.3R — 3 anni su 5 positivi**, trascinata da un
2019 molto negativo; dal 2021 in poi è positiva 3 anni di fila. Dettaglio:
[[NEXUS EA - Backtest 10Y Segmentato - Analisi]].

## Stato
❌ NON VALIDATA nel complesso. Confermato sui 10 segmenti: **440 trade
totali** (il campione più grande del Blocco 2), ma solo 2 dei 10 anni OK,
gli altri CRITICA/DEBOLE — un campione ampio che smentisce stabilmente,
non un caso di dati insufficienti.

## Aggiornamento 07/09 — batteria prop-firm su 3 anni (167-168 trade, H4)
Config reale (SL1.0×ATR/TP4.5×ATR): net 3y ~+$2635-2655 (balance
~$3635-3655 da $1000), PF ~1.92, DD balance 12.4-15.5%, **DD equity
22.7-22.8%** — supera comunque i limiti prop-firm standard (giorno -5%
FTMO-style violato 1 volta, DD totale 10% superato). BE veloce +
SLReclaim (step3) alza il net a $2893 ma il DD esplode a 36.2% per un
bug (SLReclaim bypassa le protezioni di conto). Il test del voto-entrata
75 + fix regime multi-TF (step4, poi step5) **non è mai realmente
girato**: `InpRiskProfile` non è un vero input MQL5, quindi l'.ini non
può mai cambiarlo dal default BALANCED — dettagli in
[[NEXUS EA - Step5 Ancora Bacato, InpRiskProfile Non e' un Vero Input MQL5 (07-09)]].
Serve il fix di codice + ricompilazione prima di poter dire alcunché sul
voto75.

**Aggiornamento 08/09** — fix di `InpRiskProfile` applicato e
ricompilato, ma step6 è uscito di nuovo identico al centesimo:
`InpMinEntryScore` è un secondo bug indipendente (non è `input`,
`NXS_Inputs.mqh:155`). Prova diretta: ogni trade FVG_CONT scora sempre
70.0 nel commento, quindi con soglia reale 75 il risultato sarebbe stato
zero trade, non 168 identici. Voto75 ancora mai testato dopo 3
tentativi (step4/5/6). Dettagli in
[[NEXUS EA - Step6 Ancora Identico, Bug Indipendente su InpMinEntryScore (08-09)]].

**Aggiornamento 08/09 (step7)** — fix di `InpMinEntryScore` applicato
e funzionante, ma step7 esce di nuovo identico. Causa vera: il
punteggio di FVG_CONT è **fisso a 70.0** (non graduato), e
`NXS_ResolvedEntryThreshold()` con `InpGateMode=1` (default) abbassa
il voto globale di 5 punti prima di applicarlo — a voto75 la soglia
reale è 70.0 esatto, che FVG_CONT supera sempre. Con `InpGateMode=0`
(nessuna leniency, non ancora testato) il risultato atteso è **zero
trade**, non un filtro migliore. Dettagli in
[[NEXUS EA - Step7 Ancora Identico, la Vera Causa e' NXS_ResolvedEntryThreshold (08-09)]].

## Test A/B 16/07 (Blocco 2): il sito mostra un edge che MT5 reale non conferma — pattern MACD-like
Testata la config reale del profilo (SL1.0/TP4.5, HTF ON) su più timeframe
sul motore sito — dove FVG_CONT è codice reale, non proxy:

| TF | Trade | PF | DD% | Net |
|---|---|---|---|---|
| 1d | 180 | 1.54 | 17.58 | +8.051 |
| **4h (= TF profilo attuale)** | 126 | **1.62** | 15.46 | **+7.500** |
| 1h | 133 | 1.15 | 16.3 | +1.546 |

Aggiungendo un filtro di corpo (0.4×ATR) il DD migliora leggermente ma il
PF resta sostanzialmente invariato — non la leva giusta qui.

**Il sito mostra un edge solido e consistente su ogni timeframe testato**,
compreso quello nativo (H4, PF1.62, 126 trade — campione ampio). Ma i
**440 trade reali su MT5 sono negativi nella maggioranza degli anni**. Non
è il pattern "campione piccolo sul sito, non replicabile" — qui il sito ha
un campione grande e un edge stabile, eppure MT5 lo smentisce. È lo stesso
pattern già visto per MACD ([[NEXUS EA - Principi]] #6): segnale e
esecuzione MT5 divergono così tanto che il sospetto principale è
**l'esecuzione** (spread reali, sizing, interazione con gli altri gate),
non il trigger stesso. Nessun cambio di codice qui — servirebbe un test
isolato MT5 con logging su spread/sizing per ogni trade, stesso approccio
raccomandato per MACD.

## Fix reale 16/07: filtro EMA50 sostituito con struttura esterna vera
Applicata la teoria interna/esterna dell'utente: il filtro EMA50 (proxy
locale di trend) è stato **sostituito** — non solo affiancato — dal trend
esterno vero (H1, `g_structH1`, mai letta da nessuna strategia prima
d'ora). Config reale del profilo (H4+HTF): **PF 1.45→2.07, DD
18.31%→12.48%**, campione ridotto di ~40% (139→83 trade). Applicato sia
al sito (`sig_fvg_cont_ext`) sia a MQL5 (`NXS_Strat_FVG`). **Non ancora
validato su MT5 reale** — dato il sospetto di problema di esecuzione
sopra, questo fix migliora la qualità del segnale ma non è detto che
risolva la divergenza sito/MT5, che resta il test prioritario.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[Macd]]
