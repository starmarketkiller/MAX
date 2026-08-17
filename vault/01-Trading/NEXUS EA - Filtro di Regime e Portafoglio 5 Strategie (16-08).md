---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, regime-filter, portfolio, profittabilita]
created: 2026-08-16
updated: 2026-08-16
---

# NEXUS EA — Filtro di Regime (Efficiency Ratio) e Primo Portafoglio Profittevole (16/08)

Seguito diretto di [[NEXUS EA - Riverifica Walk-Forward 5 Finestre e Dipendenza da Regime (15-08)]].
Domanda di partenza: "come creiamo un sistema profittevole?" — dopo giorni
in cui ogni singola strategia falliva la stabilità nel tempo (dipendenza
dal rally 2023-2026, vedi nota linkata), primo tentativo di risolvere il
problema di fondo (regime) invece di aggiungere un'altra entry.

## Il rilevatore di regime: Efficiency Ratio di Kaufman

Metrica: `|close[i]-close[i-N]| / Σ|close[k]-close[k-1]|` su una finestra
di N barre — quanto del percorso totale del prezzo si traduce in
progresso netto. Stesso concetto usato il 15/08 per spiegare a posteriori
perché le finestre 1-2 (2020-2023) erano ostili al trend-following, qui
trasformato in un vero filtro applicabile prima dell'ingresso.

Calibrazione: a lookback corti (100 barre 4h) non distingue nulla
(0.11-0.13 ovunque). Serve una scala lunga, ~1000 barre 4h (~167 giorni,
5-6 mesi) perché la separazione tra regimi emerga: finestre "cattive"
(2020-2023) intorno a 0.02-0.03, finestre "buone" intorno a 0.07-0.09.
Soglia scelta: 0.045 (a metà tra le due).

## Test su SAR, poi generalizzato a MACD/LONDON_BO/FVG_CONT

Walk-forward 5 finestre, costi scalati sul prezzo storico, retail+ECN.
Pattern identico e consistente su 4 strategie indipendenti:

| Finestra | Effetto del filtro |
|---|---|
| 0 | Migliora sempre |
| 1 | Migliora sempre, spesso molto (LONDON_BO retail 0.51→1.57) |
| **2** | **Peggiora sempre, spesso PF=0.0** (MACD, LONDON_BO, FVG_CONT) |
| 3 | Migliora quasi sempre |
| 4 | Migliora quasi sempre |

### Il meccanismo del fallimento in finestra 2 (capito, non solo osservato)

Finestra 2 = 2022-04→2023-10, contiene i due punti di svolta più
importanti dell'oro del periodo: il picco di marzo 2022 (shock
Russia-Ucraina) e il minimo di novembre 2022. Un filtro con lookback di
5-6 mesi vede correttamente "c'è stato un trend forte" ma non sa che è
già finito — esempio reale: 13-18 aprile 2022, segnali BUY perché il
prezzo di 1000 barre prima era molto più basso, ma il picco vero
(8 marzo 2022, ~2070) era già passato e l'oro stava scendendo. Stesso
meccanismo speculare a dicembre 2022 (SELL proprio mentre l'oro aveva
già toccato il minimo di novembre e stava per iniziare il rally 2023).

Non risolvibile con un'altra soglia — è il limite strutturale di
qualunque filtro di tendenza ai punti di svolta. Testata una mitigazione
(richiedere che il prezzo sia vicino, non già ritracciato, da un
estremo recente a 250 barre): migliora parzialmente la finestra 2
(PF 0.68→0.28-0.57 a seconda della tolleranza) ma peggiora la finestra 0
e riduce il campione — fermato prima di scivolare in overfitting sui
parametri contro una finestra storica nota.

## Portafoglio: prima simulazione netta positiva di tutta l'indagine

5 strategie (SAR, MACD, LONDON_BO, FVG_CONT, EMA_PULLBACK — quest'ultima
su 1h con lookback scalato 4x) unite su un'unica curva equity in euro
reali, non 5 backtest separati. Rischio fisso €10/trade, tetto lotti
0.10, max 2 posizioni contemporanee, contratto 1oz/0.01 lotto (confermato
dall'utente), leva 1:500.

**Bug reale trovato e corretto durante la costruzione**: formula di
sizing mancava una divisione per 100 (`lots = risk_eur/risk_dist` invece
di `risk_eur/(100×risk_dist)`) — mascherato nella simulazione CRT del
pomeriggio perché il tetto lotti interveniva sempre comunque data la sua
distanza di rischio minuscola, ma su SAR/MACD (stop molto più larghi)
produceva size 100x troppo grandi, portando a DD >100% (impossibile).

### Risultato (dopo la correzione)

| Conto | Retail netPnL | Retail DD | ECN netPnL | ECN DD |
|---|---|---|---|---|
| €300 | **-€319.64 (rovina)** | 104% (il conto si azzera davvero) | +€1685 | 90.7% |
| €500 | +€431.70 | 93.2% | +€1669 | 66.3% |
| €1000 | +€446.69 | 68.6% | +€1685 | 50.2% |
| €2000 | +€446.69 | 54.0% | +€1685 | 41.6% |
| €5000 | +€446.69 | 33.0% | +€1685 | 27.4% |

A €300 il conto può davvero fallire sotto costi retail — non per un
singolo trade enorme, ma perché il pavimento del lotto minimo (0.01)
forza un rischio minimo che, quando l'equity si è già eroso vicino a
zero, rappresenta una frazione enorme del capitale residuo. Dimezzare il
rischio per trade (€10→€5) non risolve il problema a €300 (fallisce
comunque), conferma che è il pavimento del lotto la causa, non il target
di rischio.

**Da €500-1000 in su il sistema è stabile e netto positivo su 7 anni**,
sia a costi retail che ECN — la prima volta in tutta l'indagine (14-16/08)
che un sistema completo (non una singola strategia) supera la prova
economica invece di fallirla.

### Tentativo di ridurre il drawdown: non riuscito senza costo

Testato max 1 posizione contemporanea invece di 2: DD scende solo
leggermente (68.6%→64.5% a €1000 retail) ma il numero di trade eseguiti
crolla (550→296, il bucket a 1 slot scarta trade buoni non solo quelli
rischiosi) e il PnL netto retail diventa **negativo** (-€176.56). Non è
un compromesso favorevole — fermato, max_concorrenti=2 resta la scelta
migliore tra quelle testate.

## Stato finale (16/08)

Prima base solida trovata in tutta l'indagine: filtro di regime reale
(non un altro filtro che sposta l'aggregato su una finestra fortunata),
portafoglio a 5 strategie netto positivo su 7 anni con capitale ≥€500-1000,
DD ancora severo (50-93% a seconda di capitale/costi) — non ancora pronto
per soldi veri, ma la prima volta che il sistema nel suo complesso supera
la prova invece di fallirla.

## Addendum — il vero vincolo è il lotto minimo, non il target di rischio (scoperto testando lo streak-risk)

Tentativo di ridurre il DD con un moltiplicatore di rischio dopo N
perdite consecutive (tecnica nota, non tarata sul campione): **nessun
effetto misurabile**, identico risultato a mult=0.3 e mult=0.5. Causa
trovata: il lotto minimo (0.01) è quasi sempre già il vincolo vincolante
PRIMA di qualunque streak — il rischio "desiderato" (`risk_eur=10`) è
quasi sempre sotto quello che 0.01 lotti comporta già.

Verificato sui dati reali: risk_dist varia $13.64 (p10) - $23.14 (p50) -
$61.09 (p90) tra i trade del portafoglio. A lotto minimo 0.01, il
rischio EFFETTIVO è quindi €13.64-€61.09 per trade, **mai i €10
target** — fino a 6× più del previsto sui trade con stop più largo. Il
DD severo trovato in questa nota (50-93%) non è "il sistema è rischioso
in astratto": è che si stava rischiando 1.5-6× il previsto senza
saperlo, un problema di sizing scoperto solo provando lo streak-risk
(che non aveva margine sotto il pavimento per funzionare).

**Implicazione pratica**: per controllare davvero il rischio per trade
con questo gruppo di strategie (stop molto più larghi di CRT, dove
invece il tetto lotti — non il minimo — era il vincolo), serve un
conto dove anche €61 per trade sia una frazione piccola e ragionevole —
non €500-1000 come stimato sopra, più realisticamente **€3000-5000+**
per restare sotto ~1-2% di rischio reale anche sui trade con stop più
largo. Le tabelle conto€500-5000 sopra restano valide come NUMERI (PnL/DD
osservati), ma vanno rilette sapendo che il rischio reale per trade non
era mai quello dichiarato.

## Addendum 2 — tetto diretto in euro sul rischio per trade: la vera soluzione al DD

Lo streak-risk non funzionava perche' il minimo lotto era gia' il
vincolo (vedi addendum sopra). La correzione diretta: **tetto massimo in
euro sul rischio per trade** (non solo il minimo di 0.01 lotti) — se il
rischio forzato dal lotto minimo su un trade a stop largo supera il
tetto, il trade viene scartato del tutto (non c'e' modo di scendere
sotto 0.01 lotti per quello specifico trade).

Su conto €5000, sweep di tetti €15-50: **plateau ampio** (DD stabile
8.7-12.3% su tutto il range €28-50), non un punto fragile isolato — buon
segno di generalita', non overfitting su un valore specifico. Risultato
al tetto €40 (buon equilibrio profitto/DD nel plateau):

| | Retail | ECN |
|---|---|---|
| PnL netto (7 anni, base €5000) | +€1.685,79 | +€2.737,63 |
| Drawdown massimo | **10.8%** | **8.7%** |
| Confronto: stesso conto senza tetto € | +€446,69 / DD 33.0% | +€1.685,17 / DD 27.4% |

**Non un compromesso — miglioramento su entrambi i fronti insieme**
(profitto piu' alto, DD piu' basso), a differenza del tentativo
max_concorrenti=1 di prima (che scambiava DD per profitto). Il
meccanismo: il tetto rimuove selettivamente i trade con lo stop piu'
largo (che il lotto minimo costringerebbe a rischiare fino a €61) — sono
proprio quelli col peggior rapporto costo/beneficio.

**Validazione su due meta della storia** (non solo aggregato): prima
meta (2020-2024) netPnL +€149/+€640 (retail/ECN), DD 10.8%/8.7%; seconda
meta (2024-2026, include il rally) netPnL +€1394/+€1981, DD 11.0%/8.8%.
Nessuna meta negativa — il risultato non dipende da un singolo periodo
fortunato.

## Addendum 3 — EMA_PULLBACK tolta: 4 strategie meglio di 5

Revisione sistematica del contributo per-strategia (R totale, PF, non a
bucket) su tutto il portafoglio: **EMA_PULLBACK è l'unica delle 5 con R
totale NEGATIVO** anche col filtro di regime attivo (-65.7R retail,
-27.6R ECN, PF 0.70/0.85) — le altre 4 (SAR, LONDON_BO, FVG_CONT, MACD)
sono tutte solidamente positive (PF 1.12-1.59). Tolta dal portafoglio.

Risultato (tetto €45, conto €5000, 4 strategie invece di 5):

| | Retail (5→4 strat) | ECN (5→4 strat) |
|---|---|---|
| PnL netto | €2.106 → **€2.494** | €3.177 → **€3.434** |
| Drawdown | 10.9% → 10.9% (invariato) | 8.7% → 8.7% (invariato) |

Miglioramento netto, non un compromesso — stesso DD, più profitto.
Validato sulle due metà della storia: entrambe migliorano rispetto alla
versione a 5 strategie (prima metà retail €149→€239, ECN €640→€707),
nessuna metà negativa.

**Portafoglio finale raccomandato**: SAR + MACD + LONDON_BO + FVG_CONT
(4h, tutte), filtro regime (Efficiency Ratio lookback 1000 barre,
soglia 0.045), tetto €40-45 sul rischio per trade, max 2 posizioni
contemporanee, conto ≥€5000.

## Addendum 4 — RSI(2) mean-reversion in regime laterale: provato, non regge

Idea: coprire il buco lasciato dal filtro di regime (finestra 2,
2022-2023, resistente a ogni correzione trend-following) con RSI(2) di
Connors (esterno, noto), attivo SOLO quando l'efficiency ratio è sotto
soglia (regime laterale). Primo test incoraggiante (ECN, finestra 2:
PF 1.37), ma la verifica di robustezza (griglia di soglie RSI 5-20 e
SL/TP) mostra **PF oscillante 0.93-1.19 senza mai staccarsi chiaramente
sopra 1** — effetto marginale/rumore, non un edge stabile come il tetto
€ (che reggeva su un plateau ampio). **Non adottato.** Il buco della
finestra 2 resta aperto — plausibilmente non ha una soluzione tecnica
semplice, essendo dominato da punti di svolta imprevedibili per
definizione.

## Prossimi passi aperti
- Il drawdown resta il problema principale da risolvere prima di
  qualunque uso reale — nessuna leva provata oggi (concorrenza, rischio
  per trade) lo riduce senza costare profittabilità.
- Non ancora testato: gestione dinamica del rischio (ridurre size dopo
  una serie di perdite, non solo size fissa), o un criterio di priorità
  nel bucket (non solo primo-arrivato) quando più segnali competono per
  gli stessi 2 slot.
- Validazione MT5 tick-reale (infrastruttura già pronta, `C:\MT5-Tester`)
  ha senso ora che esiste un candidato che supera la prova economica —
  prima non ne valeva la pena (vedi discussione 16/08 su OHLC vs tick).
