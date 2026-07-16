---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: TURTLE_SOUP
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: TURTLE_SOUP

## Tipo
Reversal/liquidity sweep

## Trigger meccanico
Sweep di un estremo recente + rientro nel range (Turtle Soup classico), body[1]>=0.4 ATR per filtrare rumore.

## Configurazione attuale (v2.5.0)
- **Timeframe**: H1
- **SL**: 1.0× ATR · **TP**: 4.5× ATR
- **Filtro HTF**: True
- **Trailing**: largo (corre)
- **Rischio per trade**: 3.0%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 120 setup, 17W/12L/4BE, WR 58.6%, expR +0.298, **PF 3.15**
- **3 anni**: 54 setup, 11W/6L/2BE, WR 64.7%, expR +0.120, **PF 2.12**

## Risultati (backtest 10y segmentato v2.5.0, 6 anni affidabili 2019-2024)
247 trade totali. R per anno: 2019 +2.1 · 2020 -1.8 · 2021 +4.2 · 2022 -0.5 ·
2023 +3.3 · **2024 -7.2**. **Somma +0.1R — 3 anni su 6 positivi.** Il segmento
9 (2024, 66 trade) ha quasi azzerato tutto il guadagno accumulato nei 5 anni
precedenti (+7.3R → +0.1R). Resta comunque parte del miglior angolo del
portafoglio insieme a BREAKOUT_ACC e CISD (+7.6R combinato su 6 anni, contro
-118.1R del portafoglio intero) — vedi [[NEXUS EA - Hedge nel Tempo]].

## Stato
🟢 PROMETTENTE, non più "validata senza riserve" — era profittevole sui 3 anni
(v2.4.8) e sui primi 5 anni segmentati, ma il 2024 ha riportato il totale a
sostanzialmente breakeven. Lezione diretta: anche 5 anni di dati possono
nascondere un singolo anno che ribalta la conclusione ([[NEXUS EA - Principi]]
#1 vale anche oltre i 3 mesi). Da tenere nel nucleo hedge, non più da trattare
come "la strategia sicura".

## Test A/B 15/07 (Blocco 1 Setup Buy-Sell): conferma CHoCH testata, risultato negativo
Verificato che la strategia **ha davvero tradato** (338 trade reali sui
segmenti affidabili — il contatore `executed`=0 nei CSV era il bug già noto,
non assenza di setup). Ricerca esterna sul metodo ICT Turtle Soup originale
conferma 3 pilastri: bias HTF, sweep fallito, **conferma di Market Structure
Shift (CHoCH) sul LTF** — quest'ultimo assente nel nostro trigger. Testato
un proxy CHoCH (stessa logica failure-swing di `SMS_BMS_RTO`) sul motore
sito: **peggiora tutto** (PF 0.83→0.66, trade 63→4, campione troppo piccolo
per giudicare). Caveat: il test gira su D1 mentre TURTLE_SOUP su MT5 usa H1
— il disallineamento di timeframe è più severo qui che per SAR/ADX_RSI, non
è una prova che il concetto non serva su H1 reale. **Non applicato.**
Dettaglio: [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]].

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Hedge nel Tempo]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]]
