---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, level-reaction, primo-risultato, promettente]
created: 2026-09-07
updated: 2026-09-07
---

# NEXUS EA — LEVEL_REACTION: primo risultato, il migliore della famiglia "livelli" (07/09)

## Il test

Primo test vero (dopo un falso partenza per una gara tra processi
risolta la sera prima — vedi
[[NEXUS EA - ESL Corretto, Disattivarlo Peggiora ADX_RSI (06-09)]]):
M15, 3 mesi (2026.06.05-09.05), rischio 5%, selettore 52. Config nuda
(nessuna confluenza obbligatoria).

## Risultato

| Metrica | Valore |
|---|---|
| Trade | 338 (186 BUY / 152 SELL) |
| PF | 0.95 |
| Net (3 mesi) | -$298.64 |
| Win rate | 39.9% |
| Vincita media | $44.32 |
| Perdita media | -$30.80 |
| Soglia di pareggio | 41.0% |
| **Gap dalla soglia** | **-1.1 punti percentuali** |

## Confronto con tutta la famiglia "reazione a livello" testata in sessione

| Strategia | Trade | Gap dalla soglia di pareggio |
|---|---|---|
| LEVEL_CONFLUENCE touch grezzo | 424 | ~-11pp (stimato da WR34%/soglia45.7%) |
| LEVEL_CONFLUENCE conferma2+HTF | 295 | -10.7pp |
| LEVEL_CONFLUENCE M5 | 346 | -6.2pp (BUY) |
| LEVEL_CONFLUENCE confluenza obbligatoria (3 anni) | 1181 | -3.2pp (BUY) |
| **LEVEL_REACTION nuda (nuova, due fonti + gate sfondamento)** | **338** | **-1.1pp** |

**È il miglior primo risultato di tutta la serie** — il gate sulla
profondità di sfondamento (>100 pip = scartato) e la seconda fonte di
livelli (S/R a corpo H4, non solo pivot frattali) sembrano selezionare
punti d'ingresso genuinamente migliori, non solo aggiungere pazienza.

## BUY vs SELL — bilanciato, buon segno

| | Trade | Net | WR |
|---|---|---|---|
| BUY | 184 | -$282.25 | 39.1% |
| SELL | 154 | +$12.40 | 40.9% |

SELL è quasi esattamente in pareggio. Nessuna asimmetria sospetta tipo
"un lato regge solo per trend" — coerente con l'assenza di qualunque
filtro di trend nella logica (deciso di proposito in fase di design).

## Cautela

- 338 trade su 3 mesi è un campione più ampio del "quasi pareggio" di
  LEVEL_CONFLUENCE che poi non ha retto (73 trade), ma resta solo 3
  mesi — serve la verifica sui 3 anni prima di trarre conclusioni.
- Nessuna confluenza obbligatoria testata ancora qui — su
  LEVEL_CONFLUENCE quel filtro dimezzava il gap; potrebbe fare lo
  stesso qui, portando il gap a zero o oltre.
- Non ancora scomposto per fonte (pivot vs SNR) o per profondità di
  sfondamento — il commento dell'ordine non preserva la reason string
  dettagliata (viene sovrascritto dal formato standard
  `NEXUS_v2.50|LEVEL_REACTION|score`), servirebbe un log dedicato per
  quella scomposizione.

## Non ancora fatto

- Test su 3 anni (verifica campione ampio, priorità alta dato il
  precedente di LEVEL_CONFLUENCE).
- `InpLevelReactRequireConfluence=true`.
- Variante M5 gemella (mai testata).

## Collegamenti
[[NEXUS EA - LEVEL_REACTION, Merge Vero di PIVOT_WICK STRUCT_REACT MALAYSIAN_SNR (06-09)]] · [[NEXUS EA - LEVEL_CONFLUENCE Chiusura, il Quasi Pareggio BUY Non Regge su Campione Ampio (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
