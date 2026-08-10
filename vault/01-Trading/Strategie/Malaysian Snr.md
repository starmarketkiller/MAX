---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: MALAYSIAN_SNR
created: 2026-07-12
updated: 2026-08-10
---

# Strategia: MALAYSIAN_SNR

## Tipo
SMC / pattern strutturale

## Trigger meccanico
Support/resistance con storyline (fresh/flipped). Attiva ma non ancora validata a fondo su MT5.

## Configurazione attuale (v2.5.0)
- **Timeframe**: vedi NXS_StrategyProfiles.mqh
- **SL**: vedi NXS_StrategyProfiles.mqh× ATR · **TP**: vedi NXS_StrategyProfiles.mqh× ATR
- **Filtro HTF**: vedi NXS_StrategyProfiles.mqh
- **Trailing**: vedi NXS_StrategyProfiles.mqh
- **Rischio per trade**: 0.4%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 6 setup, 1W/0L/1BE, WR 100.0%, expR +0.164, **PF 99.00**
- **3 anni**: 0 trade eseguiti in questo build.

## Risultati (backtest 10y segmentato v2.5.0, 5 anni affidabili 2019-2023)
Ora esegue davvero (era a 0 trade in v2.4.8): 10 trade totali in 5 anni. R per
anno: 2019 +0.3 · 2020 +0.4 · 2021 -0.4 · 2022 +0.1 · 2023 0.0. **Somma +0.4R —
1 anno su 5 negativo**. Ancora troppo pochi trade per giudicare, ma il segnale
è leggermente positivo.

## ⚠️ Trigger attuale molto più semplice della fonte reale (15/07)
Questa strategia prende il nome dal manuale "MSNR x SMC x ICT" (Yanu
Emmanuel), fornito dall'utente — vedi
[[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]]. Il trigger attuale
("Support/resistance con storyline (fresh/flipped)") cattura solo una
frazione minima della metodologia reale: manca l'identificazione SNR
close-to-open (non high/low), la regola di conferma a 2 timeframe, il
"marriage concept" trendline+SNR, il filtro sessione Londra/NY. Primo setup
buy/sell ricostruito dalla fonte: [[NEXUS EA - Setup Buy-Sell — Framework]].

## Stato
🔬 Campione troppo piccolo (dato insufficiente) — ma non più "nessun trade":
ora esegue, va solo lasciata accumulare più campione. **Candidata prioritaria
per il refactor guidato dalla fonte** (Tier 1), non solo per attesa dati.

## Aggiornamento 10/08 — quasi-tautologia trovata, specifica Tier 1 pronta
Diagnosi precisa del perché scatta così di rado: il trigger richiede
simultaneamente "prezzo all'estremo H4 a 12 barre" e "H4 recente già in
inversione" — le due condizioni tendono a contraddirsi. Variante
sperimentale `MALAYSIAN_SNR_BREAKOUT` (tocco→chiusura oltre il livello)
testata con split IS/OOS: segnale diagnostico non ancora probante (limiti
di finestra dati, vedi nota sotto), ma la diagnosi strutturale già
giustifica il refactor. Specifica tecnica completa dei 5 pilastri della
fonte (close-to-open, fresh/unfresh/flip, regola 2 TF, filtro MISS,
killzone) in [[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]].

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Fonte MSNR SMC ICT (Yanu Emmanuel)]] · [[NEXUS EA - Setup Buy-Sell — Framework]] · [[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]]
