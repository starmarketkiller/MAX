---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, level-reaction, merge, pivot-wick, struct-react, malaysian-snr]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — LEVEL_REACTION: merge vero di PIVOT_WICK + STRUCT_REACT + MALAYSIAN_SNR (06/09)

## Perché

LEVEL_CONFLUENCE (chiusa negativa oggi, vedi
[[NEXUS EA - LEVEL_CONFLUENCE Chiusura, il Quasi Pareggio BUY Non Regge su Campione Ampio (06-09)]])
usava SOLO i pivot frattali H1/H4/D1 — non era davvero il merge delle tre
strategie richiesto dall'utente ("perché structure react o pivot wick e
l'altro pivot non riusciamo a metterle insieme... con anche malaysian
snr"), solo un riuso dell'infrastruttura di PIVOT_WICK con conferma a
barre. LEVEL_REACTION è il merge vero: due fonti di livello indipendenti
più un ingrediente completamente nuovo, il gate sulla profondità di
sfondamento.

## Le tre fonti diventano due (con STRUCT_REACT come bonus, non fonte primaria)

| Strategia originale | Cosa contribuisce a LEVEL_REACTION |
|---|---|
| PIVOT_WICK | Fonte 1: pivot frattali H1/H4/D1 (wick-based, pool condiviso `g_pivotWickState`) |
| MALAYSIAN_SNR | Fonte 2: supporti/resistenze "a corpo" H4 (chiusura delle ultime 12 barre, NON wick — un vero secondo tipo di livello, non un duplicato della fonte 1) |
| STRUCT_REACT | Bonus di confluenza: se il livello candidato coincide con una zona SMC attiva (Order Block/FVG, `g_reaction`, stessa infrastruttura di STRUCT_REACT) |

Nessun direction-lock, nessun filtro "storyline" (trend H4/D1) come
nell'originale MALAYSIAN_SNR — la sessione ha già mostrato più volte
(MACD, ADX_RSI, BOLLINGER, STRUCT_REACT) che un filtro di trend in un
mercato fortemente direzionale maschera l'esposizione al trend come
"edge". Testata simmetrica BUY+SELL fin dall'inizio.

## L'ingrediente nuovo: gate sulla profondità di sfondamento

Richiesto esplicitamente dall'utente ("aggiungici quello che hai notato
nel artefatto"). Rifatta da zero l'analisi (non riusata a memoria, per
avere numeri verificabili): 7402 pivot sull'intera storia GOLD M15
(2019-2026, zigzag K=3×ATR14, stesso script del Gold Reversal Map),
misurando quanto in profondità (in pip, convenzione $0.10/pip GOLD) il
prezzo sfonda un livello prima di eventualmente tornare indietro:

| Profondità sfondamento | Tasso di reversal storico | N |
|---|---|---|
| < 20 pip | 99.7% | 2212 |
| 20-50 pip | 99.1% | 1388 |
| 50-100 pip | 96.9% | 874 |
| > 100 pip | **69.1%** | 1619 |

La soglia netta è ~100 pip, non 50 come nella stima approssimativa
precedente: sotto i 100 pip il reversal è quasi certo (96.9-99.7%),
oltre crolla al 69% — probabile rottura strutturale, non più liquidity
grab. **`InpLevelReactMaxBreachPips=100` scarta il candidato PRIMA di
aprire lo stato di osservazione**, non solo lo penalizza nello score.

Inoltre, per gli sfondamenti "profondi" (≥50 pip, `InpLevelReactDeepBreachPips`),
il tempo mediano di richiusura è ~20h (79 barre M15) — molto più lungo
della finestra di conferma a 2 barre (30 min) usata da LEVEL_CONFLUENCE.
Per questo `InpLevelReactExtraConfirmBarsDeep` (default 2) aggiunge
barre di conferma extra solo per gli sfondamenti profondi, invece di
applicare la stessa pazienza a tutti i candidati.

## Cosa NON è cambiato

- Stesso schema di stato pendente (nessun fire al primo tocco, richiede
  N chiusure consecutive dalla parte giusta) di LEVEL_CONFLUENCE.
- Stesso bonus di confluenza multi-fonte (ora esteso: pivot-vs-pivot,
  pivot-vs-SNR, pivot/SNR-vs-zona SMC), stesso toggle
  `InpLevelReactRequireConfluence` (miglior filtro trovato su
  LEVEL_CONFLUENCE, dimezzava il gap dalla soglia di pareggio).
- Stessa coppia di strategie gemelle M15/M5 (`LEVEL_REACTION` /
  `LEVEL_REACTION_M5`, selettori veri 52/53), stesso motivo: il sistema
  di profili supporta un solo TF di esecuzione per strategia.

## Implementazione

`NXS_Strat_LevelReaction()` / `_nxs_levelreact_core()` in
`NXS_Strategies.mqh`. Wiring completo: `NXS_Inputs.mqh` (13 nuovi
input), `NXS_StrategyRegistry.mqh` (count 47→49, whitelist
`NXS_StrategyKnown` — il quarto cancello silenzioso trovato la scorsa
sessione, questa volta aggiunto FIN DALL'INIZIO invece di scoprirlo
per zero-trade misteriosi), `NXS_StrategyProfiles.mqh` (4 funzioni),
`NEXUS_EA_v2.mq5` (dispatch). Compilato pulito (0 errori) il 06/09.

## Non ancora fatto

- Test nudo mai eseguito (in coda, 3 mesi rischio alto, stessa
  metodologia di LEVEL_CONFLUENCE per confronto diretto).
- `InpLevelReactRequireConfluence=true` non testato (ma già sappiamo
  dal predecessore che aiuta — priorità alta dopo il nudo).
- Nessun walk-forward/3-anni ancora fatto.

## Collegamenti
[[NEXUS EA - LEVEL_CONFLUENCE Chiusura, il Quasi Pareggio BUY Non Regge su Campione Ampio (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
