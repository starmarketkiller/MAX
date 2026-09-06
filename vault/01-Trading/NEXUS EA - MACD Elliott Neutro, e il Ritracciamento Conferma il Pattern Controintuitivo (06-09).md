---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, macd, elliott, ritracciamento, mae-mfe]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — MACD+Elliott neutro, e il ritracciamento conferma il pattern controintuitivo (06/09)

## Elliott su MACD: neutro, non aiuta né peggiora

| | Nudo (04/09) | + Elliott (06/09) |
|---|---|---|
| Trade | 199 | 197 |
| PF | 1.53 | 1.51 |
| Net (3 anni) | +$1975 | +$1900 |
| BUY | 129 trade, WR37.2%, net+$2273 | 127 trade, WR36.2%, net+$2173 |
| SELL | 70 trade, net+$162 | 70 trade, net+$171 |

Elliott ha tolto solo 2 trade BUY, tutto il resto è quasi identico —
**a differenza di ADX_RSI e BOLLINGER (dove Elliott peggiora
chiaramente), su MACD è sostanzialmente neutro**. Terzo caso testato
sul vero MT5, terzo esito diverso (nessuno positivo finora) — conferma
ulteriore che va verificato caso per caso, mai assunto dal risultato
Python.

## Il vero motivo di questa nota: MACD era l'esempio dell'utente per il ritracciamento

L'utente ha proposto: "dal csv vediamo che la maggior parte delle
operazioni prima di andare a favore del segnale scendono in media di
200 pip, quindi aspettiamo un ritracciamento di tot pip prima di
entrare". Verificato sui dati reali di MACD (lo stesso identico
strumento che aveva ispirato l'idea):

| | MAE mediana (quanto scende prima di chiudersi) |
|---|---|
| Trade **vincenti** | **81 pip** (media 140) |
| Trade **perdenti** | **295 pip** (media 399) |

**Il numero reale (81-140 pip) è più piccolo della stima dell'utente
(200 pip)** — e soprattutto sono i PERDENTI a scendere di più (295
pip mediana), non i vincenti. Stesso pattern già visto su ADX_RSI
(193-216 pip vincenti contro 404 pip perdenti) — non è un caso
isolato, è strutturale su entrambe le strategie controllate finora.

## Simulazione ritracciamento (stessa metodologia di ADX_RSI)

| R (pip di ritracciamento richiesto) | Vincenti catturati | Perdenti evitati |
|---|---|---|
| 50 | 55% (32/58) | 11% (14/133) |
| 100 | 43% (25/58) | 14% (19/133) |
| 200 | 26% (15/58) | 33% (44/133) |
| 300 | 12% (7/58) | 52% (69/133) |

A qualunque soglia, la proporzione di vincenti persi supera quella di
perdenti evitati. **Su MACD come su ADX_RSI, il filtro "aspetta il
ritracciamento" scartato dai dati reali farebbe più danno che bene se
applicato ingenuamente** — perché un ritracciamento profondo è più
spesso il sintomo di un trade che sta per fallire (continua contro la
posizione fino allo stop) che l'anticamera di un trade che sta per
partire bene.

## Perché l'intuizione sbaglia (probabile spiegazione)

I trade vincenti su un segnale trend-following come MACD tendono a
girare **presto e poco** (piccola pausa, poi il momentum prosegue nella
direzione del segnale). I trade perdenti spesso continuano a scendere
a lungo prima di essere fermati dallo stop — quindi "sta scendendo
molto" è più correlato con "il segnale ha sbagliato lato" che con "sta
per tornare a favore". Aspettare un ritracciamento grande seleziona
proprio i casi sbagliati.

## Nota di metodo — limite della simulazione

Come già segnalato per ADX_RSI: questa è un'analisi post-hoc sul CSV
esistente (simula "il trade avrebbe raggiunto quella soglia o no", non
un vero backtest con entrata ritardata — prezzo/stop diversi,
esito potenzialmente diverso). Due strategie su due mostrano lo stesso
pattern controintuitivo, un segnale abbastanza forte da scartare
l'idea così com'è proposta, ma non definitivo al 100% senza un vero
backtest con la logica implementata.

## Collegamenti
[[NEXUS EA - Scoperta ESL, Costo Nascosto Trasversale a Tutti i Test (06-09)]] · [[NEXUS EA - MACD H4 Confermata Positiva, Terza Conferma BUY-Dominante (04-09)]] · [[NEXUS EA - ADX_RSI Filtro Elliott Peggiora, Restare sulla Ricetta Nuda (06-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
