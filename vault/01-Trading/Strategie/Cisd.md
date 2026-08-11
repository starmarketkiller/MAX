---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: CISD
created: 2026-07-12
updated: 2026-07-15
---

# Strategia: CISD

## Tipo
SMC/change in state

## Trigger meccanico
3 barre dello stesso segno + rottura dell'estremo (Change in State of Delivery).

## Configurazione attuale (v2.5.0)
- **Timeframe**: H4
- **SL**: 1.5× ATR · **TP**: 3.0× ATR
- **Filtro HTF**: True
- **Trailing**: stretto (incassa presto)
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 57 setup, 1W/2L/1BE, WR 33.3%, expR -0.209, **PF 0.18**
- **3 anni**: 9 setup, 1W/0L/0BE, WR 100.0%, expR +0.323, **PF 99.00**

## Risultati (backtest 10y segmentato v2.5.0, 6 anni affidabili 2019-2024)
18 trade totali (ancora pochi). R per anno: 2019 0.0 · 2020 0.0 · 2021 +0.7 ·
2022 +1.9 · 2023 +0.9 · 2024 -0.3. **Somma +3.2R — 1 anno su 6 negativo**
(2024, comunque marginale). Il primo anno in rosso della sua storia, ma resta
il terzo membro del nucleo hedge con TURTLE_SOUP e BREAKOUT_ACC — vedi
[[NEXUS EA - Hedge nel Tempo]].

## Stato
🟢 PROMETTENTE — aggiornato coi 10 segmenti: **24 trade totali** (appena
sopra la soglia minima di ~15, [[NEXUS EA - Principi]] #4 — ancora borderline,
non "validata" in senso pieno). Il segnale resta coerente su ogni anno
disponibile.

## Verifica fedeltà Blocco 3 (16/07)
Controllato `sig_cisd()` sul motore sito contro `NXS_Strat_CISD()` MQL5:
**logica identica** (3 candele dello stesso colore + chiusura oltre il loro
estremo) — a differenza di BJORGUM/SAR, qui il sito testa davvero la
strategia reale. Nessun bug trovato, nessun cambio di codice — CISD resta
l'unica delle 5 strategie audite nei Blocchi 1-3 senza alcun problema di
fedeltà o di campione insufficiente stroncante. Priorità: continuare a
raccogliere campione (sweep MT5 1-37 in corso), non serve altro intervento
ora.

## Note

**11/08 - correzione a questa nota**: la "logica identica" verificata il
16/07 sopra e' la versione SEMPLIFICATA (3 candele + rottura estremo).
Quello che questa nota non diceva (la storia viveva solo in un commit
git, mai trascritta qui): prima del 10/07 esisteva una versione "vera"
(displacement + ultima candela di delivery OPPOSTA + sweep di liquidita'
+ reclaim, SL/TP hardcoded) che sul sito dava **PF 5.95** ma non
scattava MAI (0 setup su 1067) - sostituita ovunque (sito, MQL5, Python)
dalla versione semplice il 10/07 (commit `dc13566`), rinominata
THREE_BAR_DELIVERY_BREAK il 17/07 (commit `1bb167a`, "nome onesto,
logica invariata"). Riportata e testata a fondo l'11/08 come `CISD_TRUE`
- spara regolarmente sullo storico ampliato ma il walk-forward e'
negativo su 15m/1h/4h, non promossa. Vedi
[[NEXUS EA - CISD_TRUE (versione vera, negativa) e Censimento Completo (11-08)]]
per il dettaglio completo - questa volta la versione scartata NON
nascondeva un edge (a differenza di CRT).

## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Hedge nel Tempo]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - CISD_TRUE (versione vera, negativa) e Censimento Completo (11-08)]]
