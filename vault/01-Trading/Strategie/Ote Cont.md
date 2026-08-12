---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: OTE_CONT
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: OTE_CONT

## Tipo
SMC / pattern strutturale

## Trigger meccanico
Optimal Trade Entry continuation (ritracciamento 62-79% in trend). Disabilitata: test reale v2.3.1, 6 trade, -30$.

## Configurazione attuale (v2.5.0)
- **Timeframe**: vedi NXS_StrategyProfiles.mqh
- **SL**: vedi NXS_StrategyProfiles.mqh× ATR · **TP**: vedi NXS_StrategyProfiles.mqh× ATR
- **Filtro HTF**: vedi NXS_StrategyProfiles.mqh
- **Trailing**: vedi NXS_StrategyProfiles.mqh
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: **No — disabilitata in NXS_Profile_Enabled**

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build. (112 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)
- **3 anni**: 0 trade eseguiti in questo build. (29 setup rilevati ma nessuno eseguito — strategia disabilitata/bloccata)

## Stato
🔴 DISABILITATA — Test reale v2.3.1: 6 trade, -30$.

## Aggiornamento 11/08 — storico ampio: stesso pattern IS>OOS di decadimento

Sullo storico Dukascopy ampio (v1, non v2 — v2 ha un bug diverso già
corretto, vedi [[NEXUS EA - Strategie Escluse, Analisi Una-ad-Una (11-08)]]):
su **4h** (miglior TF tra 1h/4h/15m testati) IS PF 1.31/78 → OOS PF
0.86/49 — stesso pattern di decadimento IS→OOS già visto e flaggato come
"DEBOLE" per altre strategie del nucleo (TURTLE_SOUP, LIQ_SWEEP). Coerente
con il test reale MT5 (perdita, seppur su campione minuscolo). Nessun
fix di rigidità applicabile qui — non è un problema di condizioni troppo
strette (il pattern scatta regolarmente, 127 trade su 4h), è che il
trigger stesso non ha edge consistente fuori campione. Chiuso, nessun
margine di miglioramento realistico trovato.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
