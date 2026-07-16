---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, ricerca, test-ab, sar, macd, rsi_div, adx_rsi, ict]
created: 2026-07-15
updated: 2026-07-15
---

# Ricerca esterna + test A/B reali per strategia (15/07)

Richiesta dell'utente: usare ricerca online (forum, guide) per trovare cosa
serve per correggere le strategie, e **testare davvero** le ipotesi (buy e
sell nello stesso test, non solo leggere teoria). Sotto: la ricerca fatta,
un bug di implementazione scoperto durante la verifica, e 3 test A/B reali
eseguiti sul motore sito (dati Yahoo 10y, XAUUSD D1) per validare o
smentire le ipotesi prima di toccare il codice MQL5.

## Scoperta collaterale: "Strat Diag" (la sezione CSV del sito) era rotta dallo stesso bug del contatore `executed`

Il sito ha già uno strumento — `server/bt_verdict.py`, endpoint
`/api/backtest/analyze_csv` — pensato esattamente per questo: carichi il CSV
per-strategia di un test MT5 e ottieni un verdetto (FORTE/OK/DEBOLE/CRITICA/
BLOCCATA) con raccomandazioni keep/disable. Provandolo sui nostri CSV reali,
**classificava quasi tutto come BLOCCATA o NO_SETUP**, anche strategie con
centinaia di trade veri — perché usava il campo `executed` (rotto, sempre 0,
vedi [[NEXUS EA - Backtest 10Y Segmentato - Analisi]]) come gate principale.

**Fixato** (`server/bt_verdict.py`, funzione `_verdict` e `analyze_stats_rows`):
ora usa `wins+losses+breakeven` come fallback quando `executed` è 0 — la
stessa fonte affidabile già usata nelle nostre analisi manuali. Rieseguito
sui 6 anni aggregati (2019-2024):

| Strategia | Verdetto | Trade | PF | Expectancy | Note |
|---|---|---|---|---|---|
| CISD | **FORTE** | 18 | 3.32 | +0.18R | |
| BREAKOUT_ACC | OK | 101 | 1.47 | +0.05R | |
| LIQ_SWEEP | OK | 22 | 1.21 | +0.01R | **nuovo**: non era ancora nel nucleo hedge, promuoverla in osservazione |
| TURTLE_SOUP | DEBOLE | 247 | 1.00 | 0.00R | conferma il quasi-breakeven post-2024 |
| FVG_CONT, RSI_DIV, ORDER_BLOCK, SAR, MACD, TSI, BOLLINGER, ADX_RSI, OB_MIT, EMA_PULLBACK, BJORGUM | **CRITICA** | vari | 0.51-0.88 | negativa | **TSI passa da "in attesa" a CRITICA** con campione ampio (721 trade) — da promuovere nel gruppo fallite |

Questo strumento ora è riusabile per ogni futuro CSV — è lo stesso motore
dietro alla UI "Strat Diag" del sito, quindi la correzione vale anche lì.

## Test A/B #1: ADX_RSI — scoperto che non usa mai il vero ADX

Verificato nel codice: sia `sig_adx_rsi()` sul sito (`backtest.py:301`) sia
la versione MQL5 (commento esplicito: *"riportata alla logica del sito"*,
`NXS_Strategies.mqh:111`) **non calcolano mai l'indicatore ADX** — il
trigger usa solo la pendenza di EMA50. Il nome della strategia è un
fraintendimento storico, non una svista di questa sessione.

Ricerca esterna (fonti in fondo) conferma che la combinazione classica
ADX+RSI richiede **ADX>25 come filtro di forza del trend** — è il pattern
standard, non un dettaglio opzionale. Ho implementato un vero ADX(14)
Wilder in Python e testato diverse soglie, stesso trigger di base:

| Soglia ADX | Trade | PF | WR% | Net | DD% |
|---|---|---|---|---|---|
| nessuna (baseline) | 212 | 1.26 | 39.2 | +3.625 | 11.44 |
| >15 | 189 | 1.27 | 39.2 | +3.358 | 9.67 |
| >18 | 161 | 1.17 | 37.3 | +1.653 | 8.97 |
| >20 | 148 | 1.23 | 38.5 | +2.142 | 9.72 |
| **>22** | **139** | **1.29** | **39.6** | **+2.521** | **6.88** |
| >25 (soglia "da manuale") | 102 | 1.00 | 34.3 | -3.36 | 15.59 |
| >30 | 65 | 0.99 | 33.8 | -42.35 | 10.53 |

**La soglia da manuale (25) non funziona qui — anzi rovina la strategia.**
La soglia migliore trovata è **ADX>22**: PF sale leggermente (1.26→1.29),
ma soprattutto il **drawdown scende quasi a metà** (11.44%→6.88%) con solo
il 34% dei trade in meno. Oltre 25 il campione crolla e la qualità pure —
segno che ADX alto su XAUUSD daily arriva quando il movimento è già maturo,
non all'inizio.

**Raccomandazione**: implementare `iADX` vero in MQL5 per `ADX_RSI`, soglia
di partenza **20-22** (non 25), poi ri-validare su MT5 — questo è un test
sul motore sito, serve conferma sui dati reali multi-timeframe prima di
mettere in produzione.

## Test A/B #2: SAR — implementato il vero Parabolic SAR (corregge anche il bug del proxy sito)

Come già documentato in [[NEXUS EA - Motore Sito - Audit e Confronto 10Y]],
il proxy sito era identico a EMA_PULLBACK. Ho implementato un vero
Parabolic SAR (algoritmo standard: AF 0.02→0.2, extreme point, flip) +
allineamento con EMA20 (proxy di EMA9/21 vista la disponibilità di
indicatori del motore sito), che è la combinazione raccomandata dalla
ricerca ("pairing SAR with a moving average trend filter").

| Versione | Trade | PF | WR% | Net | DD% |
|---|---|---|---|---|---|
| Proxy vecchio (= EMA_PULLBACK, bacato) | 84 | 1.17 | 38.1 | +842 | 12.38 |
| **SAR reale + EMA** | **100** | **1.28** | **40.0** | **+1.893** | **7.81** |

**Il vero Parabolic SAR batte nettamente il proxy bacato** su tutte le
metriche — PF, win rate, profitto, e soprattutto drawdown quasi dimezzato.
Ho poi provato ad aggiungere lo stesso filtro ADX che ha aiutato ADX_RSI:

| + filtro | Trade | PF | Net | DD% |
|---|---|---|---|---|
| senza ADX | 100 | 1.28 | +1.893 | 7.81 |
| ADX>20 | 54 | 1.15 | +558 | 8.89 |
| ADX>25 | 35 | 1.16 | +370 | 5.07 |

**Qui l'ADX non aiuta** — peggiora PF e taglia il campione senza un
guadagno proporzionale in DD. Conferma diretta di
[[NEXUS EA - Principi]] #2: non esiste una ricetta unica, lo stesso filtro
che aiuta ADX_RSI danneggia SAR.

**Raccomandazione**: (1) implementare vero Parabolic SAR nel proxy sito
(`server/backtest.py`, sostituire `sig_sar`) così lo screening futuro ha
senso; (2) portare la stessa logica reale in MQL5 (oggi già usa Parabolic
SAR vero secondo la doc — verificare che l'implementazione MQL5 nativa
`iSAR` sia effettivamente wired correttamente, dato che qui il miglioramento
viene dal fix del proxy, non da un nuovo algoritmo); (3) NON aggiungere
filtro ADX a SAR, lo peggiora.

## Test A/B #3: TURTLE_SOUP — conferma di struttura (CHoCH proxy) testata, risultato negativo

Richiesta dell'utente (Blocco 1 del framework Setup Buy-Sell): verificare se
TURTLE_SOUP avesse davvero mai tradato (sì — **338 trade reali** nei segmenti
affidabili, il contatore `executed`=0 nei CSV traeva in inganno prima del fix
di Strat Diag) e se il metodo ICT originale richiedesse qualcosa che manca
nel nostro trigger. Ricerca web (fonti in fondo) conferma 3 pilastri del
metodo: bias HTF, sweep fallito, **e conferma di Market Structure Shift
(MSS/CHoCH) sul LTF** — quest'ultima assente nel nostro codice (che oggi
verifica solo sweep + candela di rigetto con corpo forte).

**Implementato un proxy di CHoCH** sul motore sito, riusando la stessa logica
già presente in MQL5 per `SMS_BMS_RTO` (failure swing su finestre 10/20
barre: HL = inizio struttura rialzista, LH = inizio struttura ribassista) e
richiesto come filtro aggiuntivo dopo il segnale base:

| Versione | Trade | PF | WR% | expR | DD% | Net |
|---|---|---|---|---|---|---|
| Baseline (sweep+rigetto, invariato) | 63 | 0.83 | 30.2 | -0.109 | 10.71 | -716 |
| + conferma CHoCH (failure swing) | **4** | **0.66** | 25.0 | -0.25 | 1.99 | -103 |

**Risultato negativo, non applicato**: il filtro non solo non migliora il
PF (peggiora, 0.83→0.66), ma **riduce il campione a 4 trade** — sotto la
soglia minima per qualsiasi giudizio statistico ([[NEXUS EA - Principi]] #4).
Non è la stessa storia di ADX_RSI (dove un filtro mancante dal nome stesso
migliorava le cose): qui il "pilastro mancante" della fonte esterna non si
traduce in un miglioramento misurabile con questa definizione di CHoCH.

⚠️ **Caveat importante, scoperto durante il test**: TURTLE_SOUP su MT5 gira
su **H1** (`NXS_StrategyProfiles.mqh:88`), ma il test sopra — come tutti gli
altri di questa nota — girava sul motore sito **solo su D1**. Per Turtle Soup
il disallineamento di timeframe è più severo che per SAR/ADX_RSI, perché uno
stop-hunt/reversal è per natura un pattern a breve termine.

### Seguito 15/07: sweep multi-TF sul sito (il sito supporta 1h/4h/30m/15m via Yahoo)

Il motore sito **può** girare su timeframe intraday (`_fetch_real`, mappa
`_YF_INTERVAL`: 1h/4h fino a 2 anni di storico, 30m/15m fino a 60 giorni) —
non serve più limitarsi a D1. **Correzione**: il primo test sopra (63 trade,
PF0.83) usava per errore i parametri SL/TP di default del motore
(1.5×/3.0×ATR), non la config reale del profilo TURTLE_SOUP
(`NXS_StrategyProfiles.mqh:50`: **SL1.0×/TP4.5×ATR, filtro HTF acceso**).
Rifatto con la config corretta, su tutti i timeframe disponibili:

**Senza filtro HTF (campione più utilizzabile):**

| TF | Trade | PF | WR% | expR | DD% | Net |
|---|---|---|---|---|---|---|
| 1d | 64 | 0.68 | 14.1 | -0.258 | 21.04 | -1.613 |
| **4h** | **36** | **1.39** | 25.0 | 0.309 | 6.85 | **+1.073** |
| **1h** (= TF reale MT5) | **47** | **1.25** | 25.5 | 0.211 | 5.85 | **+927** |
| 30m | 36 | 1.23 | 25.0 | 0.209 | 10.47 | +690 |
| 15m | 52 | 0.75 | 17.3 | -0.179 | 17.62 | -969 |

Pattern a "U rovesciata": i timeframe estremi (D1 troppo lento, M15 troppo
rumoroso) sono negativi, quelli intermedi (**H4/H1/M30**) sono gli unici
positivi — e **H1 è esattamente il timeframe che il profilo MT5 già usa**,
un segnale di coerenza incoraggiante anche se non è una conferma diretta
(dati/esecuzione restano diversi da MT5, [[NEXUS EA - Principi]] #5).

**Con filtro HTF acceso (config esatta del profilo reale)**: il campione
crolla ovunque a 6-13 trade su tutti i timeframe — sotto la soglia minima
per giudicare ([[NEXUS EA - Principi]] #4). Il sito **non riesce a validare
né smentire** la scelta "HTF filter ON" del profilo reale: non è un
problema del filtro, è che lo storico intraday di Yahoo (2 anni per H1/H4,
60 giorni per M30/M15) è troppo corto per accumulare abbastanza sweep+HTF
allineati, mentre MT5 ha 6-10 anni di storico broker.

**CHoCH ripetuto su ogni TF**: stesso esito del test D1 — il filtro
struttura riduce il campione a 1-5 trade ovunque (con o senza HTF), troppo
poco per giudicare. Non è quindi un problema specifico di D1: **con questa
definizione di CHoCH, il filtro è troppo restrittivo su qualunque
timeframe** testabile sul sito.

**Raccomandazione aggiornata**: non applicare né il filtro CHoCH né trarre
conclusioni definitive sul filtro HTF da questi dati — il sito ha comunque
un limite strutturale di storico intraday che MT5 non ha. Il segnale più
utile qui è "H4/H1 sembrano i TF giusti, coerente con la scelta già fatta
nel profilo" — non una scoperta, ma una non-smentita. Il test che conta
resta **isolato su MT5 H1** (`InpStrategySelector`), con 6-10 anni di dati
veri, non i 2 anni di Yahoo.

## Test A/B #4 e #5 (16/07, Blocco 4): MACD e RSI_DIV — altri 2 bug di proxy trovati, stesso schema di SAR/BJORGUM

Controllando il codice a fondo (richiesta esplicita dell'utente di "non
tralasciare niente"): **né MACD né RSI_DIV sul sito testavano la vera
logica MQL5** — la terza e quarta occorrenza dello stesso tipo di bug
(dopo SAR e BJORGUM).

- **MACD**: `sig_macd()` faceva un incrocio della MACD-line con lo zero.
  La vera `NXS_Strat_MACD()` richiede MACD-line **vs signal-line** (9-EMA
  della MACD-line) **+** MACD dallo stesso lato dello zero **+** prezzo
  vs EMA200 — tre condizioni, non una.
- **RSI_DIV**: `sig_rsi_div()` era solo un rientro RSI da ipercomprato/
  ipervenduto (`rp<30<=r`). La vera `NXS_Strat_RSIDiv()` è una **divergenza
  reale** prezzo/RSI su una finestra di 8 barre (minimo di prezzo più
  basso ma RSI più alto = divergenza rialzista, e viceversa) — concetto
  completamente diverso, non solo una variante più permissiva.

**Corretti entrambi** in `server/backtest.py` (aggiunta anche
`macd_signal_series()`, la linea segnale che mancava del tutto). Ri-testati
con la config reale del profilo:

| Strategia | Config | Trade | PF | DD% | Net |
|---|---|---|---|---|---|
| MACD | H4/HTF ON (=profilo) | 108 | 1.42 | 7.75 | +2.425 |
| MACD | ogni altro TF/HTF provato | 108-141 | 1.15-1.52 | 5.85-9.19 | sempre positivo |
| RSI_DIV | H1/no-HTF (=profilo) | 84 | **1.34** | 11.91 | +2.275 |
| RSI_DIV | HTF ON (qualsiasi TF) | 0-4 | — | — | campione troppo piccolo |

**Scoperta importante**: con la logica VERA (non più il proxy bacato), sia
MACD che RSI_DIV mostrano un **edge ancora più solido di prima** sul sito,
consistente su quasi ogni timeframe/config provato — non un caso limite.
Eppure **MT5 reale li smentisce entrambi** su campione enorme (MACD: 1.496
trade/10y, per lo più CRITICA; RSI_DIV: 678 trade/10y, per lo più CRITICA).

Le config attuali dei profili MQL5 (MACD: SL2.0/TP3.0/HTF ON su H4;
RSI_DIV: SL1.0/TP4.5/no-HTF su H1) **erano già le migliori trovate** anche
col proxy corretto — non serviva cambiarle. **Non toccato nessun parametro
MQL5**, solo aggiornato il commento nel profilo per correggere la
giustificazione invalida ("robusta su sito E MT5" per MACD era basata sul
proxy sbagliato).

**Conclusione che cambia priorità**: questo è ora il **terzo caso**
(dopo FVG_CONT nel Blocco 2) di segnale confermato solido sul sito ma
smentito su MT5 con campione enorme. Con 3 casi indipendenti che puntano
nella stessa direzione, il sospetto di un problema di **esecuzione MT5**
(spread reali, sizing, interazione con gate come `InpMaxPerDirTF`/margine)
diventa la pista più probabile per una fetta importante della perdita
totale del portafoglio — più probabile di continuare a cercare bug nei
trigger. Prossimo passo consigliato: un test isolato MT5 con logging
spread/sizing per-trade su MACD, RSI_DIV e FVG_CONT insieme, non altri fix
al sito.

## ICT/sessione: colmato il gap Tier 3 (Silver Bullet, Judas Swing, AMD/PO3)

Prima bloccati per mancanza di fonti (vedi
[[NEXUS EA - Setup Buy-Sell — Framework]], Tier 3). Trovati orari precisi:

- **Silver Bullet**: 3 finestre di 1 ora — 3:00-4:00 AM ET (apertura Londra),
  10:00-11:00 AM ET (overlap Londra/NY, la finestra con più order flow),
  2:00-3:00 PM ET (ribilanciamento istituzionale fine giornata). È un
  modello di **entrata**, non di direzione — serve un bias HTF già stabilito
  prima di entrare nella finestra. RR tipico 2:1-4:1 (basato sull'ampiezza
  del FVG target).
- **Judas Swing**: probabilità più alta 02:00-05:00 EST, in particolare
  02:00-03:00 EST ("witching hour" — gli algoritmi di Londra spazzano la
  liquidità del range asiatico).
- **AMD/Power of Three**: fase di Manipolazione (Judas Swing) ~2AM-5AM ET —
  in un giorno ribassista, un push sopra il massimo asiatico spazza la
  liquidità buy-side prima dell'inversione reale (Distribuzione).

Da confrontare con le descrizioni già raccolte in
[[NEXUS EA - Fonte Chat WhatsApp (Said)]] (leggermente meno precise sugli
orari) e usare per costruire i setup buy/sell di queste strategie.

## Metodologia: perché i test sono "buy e sell nello stesso test"
Tutti i test A/B sopra usano `run_backtest()` del motore sito senza
filtrare per direzione — il segnale (+1 o -1) emerge naturalmente dal
trigger e viene tradato in entrambe le direzioni nello stesso backtest,
esattamente come richiesto. Non sono simulazioni separate long-only/
short-only — sono le metriche reali di un singolo test che include tutte
le operazioni, in entrambe le direzioni.

## Fonti
- [Parabolic SAR — GoMarkets, LiteFinance, TrendSpider (mistakes/lag/fix)](https://www.gomarkets.com/en-au/articles/strategy-series-mastering-the-parabolic-sar-in-trading-entry-and-exit)
- [MACD lag e zero-lag — Macroption, Medium/Sword Red](https://www.macroption.com/macd-crossover/)
- [RSI Divergence conferme — AlgoAlpha](https://algoalpha.io/blog/rsi-divergence-trading-strategy-how-to-spot-trade-and-avoid-false-signals)
- [ICT Silver Bullet/Judas Swing/AMD — GrandAlgo, InnerCircleTrader, ICTKillzone](https://grandalgo.com/blog/ict-silver-bullet-strategy)
- [ADX+RSI su Gold — FXNX](https://fxnx.com/en/blog/adx-rsi-strategy-master-trend-entries)
- [ICT Turtle Soup — InnerCircleTrader](https://innercircletrader.net/tutorials/ict-turtle-soup-pattern/)
- [ICT Turtle Soup Strategy — FX Replay](https://fxreplay.com/strategies/ict-turtle-soup-strategy)
- [ICT Turtle Soup spiegato — FXOpen Market Pulse](https://fxopen.com/blog/en/what-is-ict-turtle-soup-and-how-can-you-use-it-in-trading/)

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Setup Buy-Sell — Framework]] · [[NEXUS EA - Backtest 10Y Segmentato - Analisi]] · [[NEXUS EA - Motore Sito - Audit e Confronto 10Y]] · [[Sar]] · [[Adx Rsi]] · [[Macd]] · [[Rsi Div]] · [[TODO - Backtest 10Y]]
