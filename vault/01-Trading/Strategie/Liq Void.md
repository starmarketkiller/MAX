---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: LIQ_VOID
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: LIQ_VOID

## Tipo
SMC / pattern strutturale

## Trigger meccanico
Liquidity void (proxy FVG sul sito). Mai vista in setup su MT5 (0 trade).

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

## Stato
PENDING — nessun trade eseguito sui 3 anni, dato insufficiente

## Aggiornamento 11/08 — proxy già corretto in sessione, nessun problema residuo

Il proxy era già stato allineato a `sig_fvg_cont_ext` (10/08, task tracciato
in sessione: "Fix proxy LIQ_VOID -> sig_fvg_cont_ext"). Verificato ora sullo
storico ampio: **LIQ_VOID e FVG_CONT producono risultati identici byte-per-
byte** su 4h (504 trade, PF 1.25, dd 16.72% entrambe) — è un proxy
letterale, non un'approssimazione, quindi eredita esattamente lo stato
"SOLIDA" di [[Fvg Cont]] (nucleo). Non è mai stato promosso a nucleo
probabilmente solo perché ridondante con FVG_CONT stessa, non per un
problema tecnico. Nessun test aggiuntivo necessario — qualunque
miglioramento trovato su FVG_CONT (es. la "ricetta ufficiale" SL1.0/TP4.5/
HTF) si applica identico qui.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]]
