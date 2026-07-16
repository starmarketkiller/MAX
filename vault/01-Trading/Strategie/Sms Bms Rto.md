---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: SMS_BMS_RTO
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: SMS_BMS_RTO

## Tipo
SMC / pattern strutturale

## Trigger meccanico
Failure swing (HH/LH/LL/HL) + BMS + return to OB/FVG/IFVG. Mai vista in setup su MT5 (0 trade).

## Configurazione attuale (v2.5.0)
- **Timeframe**: vedi NXS_StrategyProfiles.mqh
- **SL**: vedi NXS_StrategyProfiles.mqh× ATR · **TP**: vedi NXS_StrategyProfiles.mqh× ATR
- **Filtro HTF**: vedi NXS_StrategyProfiles.mqh
- **Trailing**: vedi NXS_StrategyProfiles.mqh
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build.
- **3 anni**: 0 trade eseguiti in questo build.

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
Ora esegue (era a 0 trade in v2.4.8): solo 3 trade in 5 anni (0W/1L/2BE), R
totale -0.2. Dato ancora troppo scarso per dire alcunché.

## Stato
🔬 Campione troppo piccolo — confermato sui 10 segmenti reali: **solo 6
trade totali** su 10 anni (1W/3L/2BE, R negativo), la strategia più rara
di tutto il Blocco 1. 6 dei 10 anni a zero setup completo.

## Audit Blocco 1 (16/07): rarità spiegata dal codice — 4 condizioni AND simultanee
`NXS_Strat_SMS_BMS_RTO` richiede **tutte e 4** insieme sullo stesso bar:
(1) failure swing HL/LH su finestre 10/20 barre, (2) vero CHoCH
(`g_struct.chochUp/chochDown`), (3) candela di rigetto con corpo >0.3×ATR,
(4) prezzo già in zona discount/premium (sotto/sopra il punto medio dello
swing). Fedeltà del trigger confermata (fa davvero quello che dice il
nome) — ma un AND a 4 condizioni indipendenti su D1 è strutturalmente raro,
non un bug. **Non testabile sul motore sito** (proxy dichiarato, riusa
`sig_ob_mit` — vedi [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]):
un A/B lì non direbbe nulla sulla vera logica.

Nessun cambio di codice proposto: allentare una delle 4 condizioni senza
dati per validarlo sarebbe esattamente l'overfitting descritto in
[[NEXUS EA - Principi]] #3. In attesa dei risultati dello sweep Optimization
1-37 su MT5 (più anni = più occasioni di accumulare campione anche con un
trigger raro).

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]
