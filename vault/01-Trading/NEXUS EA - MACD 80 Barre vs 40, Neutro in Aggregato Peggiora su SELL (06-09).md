---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, macd, time-stop, buy-hold]
created: 2026-09-06
updated: 2026-09-06
---

# NEXUS EA — MACD con time-stop a 80 barre: neutro in aggregato, peggiora su SELL (06/09)

## Perché

Dopo aver scoperto il time-stop nascosto da 40 barre (ora
`InpProfileMaxHoldBars`, vedi
[[NEXUS EA - Il Filtro Sessione Era su un Percorso di Esecuzione Diverso (04-09)]])
e trovato che i trade "salvati" dal limite sono per lo più vincenti,
testata l'ipotesi: raddoppiare la finestra (80 barre = 320h) cattura
più edge o lo perde?

## Risultato — confronto diretto nudo 40 vs nudo 80 (nessun filtro Overlap in nessuno dei due)

| | 40 barre (nudo) | 80 barre (nudo) |
|---|---|---|
| Trade | 199 | 181 |
| Profit factor | 1.53 | 1.53 (identico) |
| Net profit | $1975.49 | $1991.11 (+0.8%, irrilevante) |
| Max DD equity | n/d | $720.30 |
| Sharpe | n/d | 1.20 |
| Calmar (net/DD) | n/d | **2.76** |

In aggregato **non cambia quasi nulla** — stesso PF, profitto netto
sostanzialmente identico, solo 18 trade in meno (199→181, la finestra
più larga tiene aperte più posizioni contemporaneamente più a lungo).

## Ma il dettaglio BUY/SELL peggiora

| | 40 barre (nudo, dato storico) | 80 barre |
|---|---|---|
| BUY | 129 trade, WR37.2%, **+$2273** | 115 trade, WR31.3%, **+$2524** |
| SELL | 70 trade, WR?, **+$162** | 66 trade, WR13.6%, **-$54** (negativo!) |

Allargare la finestra di hold fa "respirare" anche le posizioni SELL
perdenti in un mercato che sale quasi sempre — il risultato è che il
lato SELL, già debole a 40 barre, diventa **francamente negativo** a
80. Ulteriore conferma (vedi
[[NEXUS EA - Il Vero Benchmark e Buy&Hold, Quasi Tutto Oggi lo Perde (05-09)]])
che l'edge di MACD è quasi interamente esposizione al trend: qualunque
cosa dia più tempo alle posizione di "lavorare" aiuta SOLO il lato che
il trend già spinge (BUY) e danneggia l'altro.

### Time-stop a ~320h: stesso pattern ma su campione più piccolo

Solo 12 trade sopravvivono fino a 320h (contro i 31 a 160h), di cui
**10 vincenti (83% WR)**, netto +$842.67 — proporzionalmente identico
al pattern trovato a 40 barre, ma il campione si riduce perché con
una finestra più larga più trade si risolvono prima (SL/TP) invece di
arrivare al limite.

## Confronto con Buy&Hold

Buy&hold 0.01 lot GOLD stesso periodo: net $2434.47, max DD $1628.41,
Calmar 1.49 (vedi
[[NEXUS EA - Il Vero Benchmark e Buy&Hold, Quasi Tutto Oggi lo Perde (05-09)]]).

MACD 80 barre nudo: **82% del rendimento assoluto del buy&hold**, ma
con **Calmar 2.76 contro 1.49** — meno del mezzo drawdown per una
frazione consistente del rendimento. Stesso schema già visto con
Overlap-only a 40 barre (Calmar 3.57): la gestione del rischio di
MACD aggiunge valore vero anche quando il rendimento assoluto non
batte il fare niente.

## Decisione

Il moltiplicatore 40 vs 80 è **sostanzialmente indifferente** in
aggregato — non vale la pena cambiarlo dal default. Il vero risultato
di questo test è la conferma, per la terza volta, che l'edge "extra"
di MACD (quello che non è semplice esposizione al trend) sta nella
gestione del rischio (Calmar sistematicamente sopra il buy&hold), non
nel trigger o nella durata di hold.

## Collegamenti
[[NEXUS EA - Il Filtro Sessione Era su un Percorso di Esecuzione Diverso (04-09)]] · [[NEXUS EA - Il Vero Benchmark e Buy&Hold, Quasi Tutto Oggi lo Perde (05-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
