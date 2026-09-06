---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, adx-rsi, elliott, filtro-non-universale]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — ADX_RSI: il filtro Elliott peggiora, restare sulla ricetta nuda (06/09)

## Il test

Prossimo elemento in coda dopo LEVEL_CONFLUENCE: completare la ricetta
Python per ADX_RSI (PF Python 2.62 con trailing+Elliott) aggiungendo
il filtro Elliott — già cablato e whitelistato nel codice per questa
strategia (`NXS_Profile_UseElliott("ADX_RSI")=true`), quindi solo un
cambio di config (`InpUseElliottFilter=true`), nessuna modifica MQL5.
Stesso D1, 3 anni, stessa config altrimenti identica al test nudo
confermato il 04/09.

Nota: il trailing (`trailATR`) per ADX_RSI è invece fissato a 0.0 nel
profilo hardcoded — il flag globale `InpUseAtrTrail` non ha effetto
per questa strategia, servirebbe una vera modifica di codice, non
testata (da chiedere prima).

## Risultato — peggiora, come già visto su BOLLINGER

| Metrica | Nudo (04/09) | Con Elliott (06/09) |
|---|---|---|
| Trade | 51 | 53 |
| PF | **2.04** | **1.65** |
| Net (3 anni) | **+$1675.65** | **+$1233.62** (-26%) |
| Win rate | 29.4% | ~28% |
| Sharpe | 1.20 | 0.98 |

## Dettaglio BUY/SELL con Elliott

| | Trade | Net (lordo, senza swap/comm) | WR |
|---|---|---|---|
| BUY | 46 (vs 44 nudo) | $1820.64 | 28.3% |
| SELL | 7 (identici a nudo) | $36.51 | 14.3% |

Interessante: il filtro Elliott **non ha eliminato nessuna delle 7
SELL** (stesse esatte operazioni del test nudo) e ha addirittura
aggiunto 2 trade BUY in più — non sta semplicemente "togliendo i
trade peggiori", sta spostando quali giorni vengono tradati, con
esito netto peggiore.

## Interpretazione

**Seconda conferma della regola già stabilita con BOLLINGER
Overlap-only**: un filtro che aiuta sul motore Python non è garanzia
che aiuti sul motore MT5 reale — va sempre testato caso per caso, mai
assunto. Per ADX_RSI, il filtro Elliott multi-TF fa parte della
ricetta Python vincente (PF2.62) ma su MT5 **peggiora** la versione
già confermata (PF2.04→1.65). **Restare sulla ricetta nuda** come
configurazione di riferimento per ADX_RSI.

## Non ancora fatto

- Trailing 2.5×ATR non testato (richiede modifica al profilo
  hardcoded — da chiedere prima di procedere).
- BUY-only esplicito (rimuovere le 7 SELL via codice) ancora non
  isolato con un test dedicato.

## Collegamenti
[[NEXUS EA - ADX_RSI D1 Confermata Positiva sul Vero MT5, BUY Domina (04-09)]] · [[NEXUS EA - BOLLINGER Overlap-Only Peggiora, Filtro Non Universale (05-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
