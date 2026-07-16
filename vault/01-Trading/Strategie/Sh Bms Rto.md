---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: SH_BMS_RTO
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: SH_BMS_RTO

## Tipo
SMC / pattern strutturale

## Trigger meccanico
Stop hunt + break of market structure + return to OB/FVG. Rari trade, non ancora validata.

## Configurazione attuale (v2.5.0)
- **Timeframe**: vedi NXS_StrategyProfiles.mqh
- **SL**: vedi NXS_StrategyProfiles.mqh× ATR · **TP**: vedi NXS_StrategyProfiles.mqh× ATR
- **Filtro HTF**: vedi NXS_StrategyProfiles.mqh
- **Trailing**: vedi NXS_StrategyProfiles.mqh
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build.
- **3 anni**: 8 setup, 3W/0L/0BE, WR 100.0%, expR +0.392, **PF 99.00**

## Stato
PENDING — campione troppo piccolo (<15 trade) per giudicare. Confermato sui
10 segmenti reali: **17 trade totali** su 8 anni disponibili (2016+2019-25),
3 anni a zero setup, mai più di 6 trade in un anno singolo.

## Audit Blocco 1 (16/07): fedeltà OK, ma non testabile sul sito
Il codice MQL5 (`NXS_Strat_SH_BMS_RTO`) implementa davvero tutti e 3 i
componenti del nome — Stop Hunt (`sw.confirmed`, `SNXSSweepExt`), Break of
Market Structure (**vero CHoCH**, `g_struct.chochUp/chochDown` — a
differenza di TURTLE_SOUP, qui la conferma di struttura c'è già), Return
to Origin (prezzo che rientra nella zona FVG appena formata, `bid` tra
`h4`/`l2`). Nessun bug di fedeltà.

**Non testabile sul motore sito**: `sig_sh_bms_rto` lì è un proxy dichiarato
che riusa `sig_ob_mit` (vedi [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]])
— un A/B come quelli fatti per TURTLE_SOUP/LIQ_SWEEP darebbe un numero senza
significato, non testerebbe mai la vera logica. L'unica fonte di verità
possibile è MT5 diretto — verrà coperta dallo sweep Optimization 1-37 in
corso lato utente.

**Perché è così raro**: 3 condizioni simultanee sullo stesso bar (sweep
confermato + CHoCH + FVG a 3 candele formato + prezzo già dentro quella
zona) — rarità spiegata dal codice, non un mistero né necessariamente un
difetto. Nessun cambio proposto finché non c'è più campione da MT5.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]
