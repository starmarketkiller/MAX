---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: IFVG
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: IFVG

## Tipo
SMC / pattern strutturale

## Trigger meccanico
Inverse FVG reversal, richiede MSS opposto + reaction candle. Mai vista in setup su MT5 (0 trade).

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
🔴 **Zero trade confermati su tutti e 10 i segmenti reali (10 anni pieni)** —
non "campione piccolo", proprio nessuno. Qualitativamente diverso da
SMS_BMS_RTO (6 trade/10y): lì il pattern comunque accade, qui mai.

## Indagine Blocco 2 (16/07): nessun bug trovato nel codice, ma l'allineamento richiesto è molto stretto
Il trigger MQL5 richiede **4 condizioni sullo stesso bar di chiusura**: gap
di 3 candele esistito 2-4 barre fa, prezzo che lo invalida COMPLETAMENTE
chiudendo oltre il bordo opposto, candela di rigetto con corpo >0.3×ATR,
**e** vero CHoCH (`g_struct.chochUp/chochDown`) sullo stesso bar. Verificato
che la sincronizzazione multi-TF è corretta (`NXS_UpdateStructure` viene
richiamato sul TF giusto — H4 — prima che IFVG venga valutata, vedi
`NEXUS_EA_v2.mq5:403`) — non è un bug di timeframe sbagliato.

## Seguito (16/07 sera): riconfermato con CHoCH fedele — 0 quasi ovunque, mistero chiuso
Il primo test usava un proxy CHoCH grezzo (rolling-extreme). Implementato
un vero rilevamento a **fractal swing** (fedele a
`NXS_ComputeStructureCore`: pivot simmetrico a `wing` barre, trend da
HH+HL/LH+LL con isteresi — non solo un massimo/minimo su finestra
scorrevole) più una versione **esterna** (stesso algoritmo su un
timeframe superiore reale, ricampionato). Risultato: con la CHoCH interna
fedele, i segnali grezzi scendono da 41 (proxy vecchio, D1) a **6** — con
interna+esterna insieme, **0 su ogni timeframe testato (D1/4h/1h)**.
Conferma con molta più sicurezza la conclusione precedente: non è un bug,
è un allineamento a 4-5 condizioni sullo stesso bar strutturalmente quasi
impossibile — coerente al 100% con lo zero reale su MT5 in 10 anni. Non
serve più cercare un bug qui.

## Nota metodologica dal test (rilevante anche per altre strategie)
Aggiungere una conferma CHoCH **sullo stesso bar** di un altro trigger
specifico è quasi sempre troppo restrittivo — vero anche per TURTLE_SOUP
(vedi scheda), non solo qui. Il valore del framework interna/esterna
sembra stare nell'avere **varianti separate** di un pattern (vedi
[[Liq Sweep]]), non nel gate-are un pattern esistente con una CHoCH
aggiuntiva sullo stesso bar.

Testato sul motore sito (dove IFVG è codice reale, non proxy) con un CHoCH
proxy equivalente (failure-swing, meno severo del vero `g_struct`): la
versione "loose" (solo gap+invalidazione) produce **168 segnali/10y su D1,
46 su H4** — il pattern grezzo non è raro. Con reaction+CHoCH-proxy aggiunti,
scende a **41/D1, 9/H4** — ancora non zero. Il vero `g_struct.chochUp/Down`
(basato su swing fractal reali, non sul mio proxy) è evidentemente più
severo — plausibile causa della rarità estrema, ma non verificabile senza
log diretto da MT5.

**Prossimo passo concreto per isolare la causa** (richiede accesso MT5, non
fattibile dal sito): loggare separatamente le 4 condizioni per qualche mese
di dati reali, per vedere quale delle 4 è il vero collo di bottiglia — non
proporre un fix alla cieca senza sapere quale condizione è il problema.
Nessun cambio di codice applicato.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]
