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
su **H1** (`NXS_StrategyProfiles.mqh:88`), ma questo test — come tutti gli
altri di questa nota — gira sul motore sito che usa **D1**. Per Turtle Soup
il disallineamento di timeframe è più severo che per SAR/ADX_RSI, perché uno
stop-hunt/reversal è per natura un pattern a breve termine — su D1 la
finestra di "sweep + rigetto" cattura un fenomeno strutturalmente diverso da
H1. **Questo risultato negativo non è una prova che il concetto CHoCH non
serva su H1 reale** — è una prova che il test *su D1* non lo conferma. Il
filtro sessione (Londra/NY, l'altro pilastro trovato in ricerca) è
**impossibile da testare qui**: D1 non ha risoluzione intraday, quindi il
motore sito non può nemmeno porre la domanda.

**Raccomandazione**: non applicare il filtro CHoCH così com'è. Se si vuole
verificare i pilastri mancanti (struttura + sessione) per davvero, serve un
test isolato **su MT5 H1** (`InpStrategySelector`), non altro tuning sul
motore sito — qui abbiamo raggiunto il limite di cosa il sito può dirci per
questa strategia specifica.

## Ricerca (non ancora testata): MACD, RSI_DIV — cosa dicono le fonti esterne

**MACD**: il lag è strutturale (media mobile = elabora dati storici, i
segnali arrivano quando lo slancio è già iniziato). Le fonti raccomandano
un **MACD "zero-lag"** (doppio smoothing delle EMA veloce/lenta) o
richiedere **almeno 2 conferme indipendenti** prima di entrare (vicinanza a
supporto/resistenza, breakout di pattern, volume). Il nostro trigger attuale
ha già 1 filtro (prezzo sopra EMA200) — da testare se un secondo filtro
(es. ADX o pattern di breakout) aiuta, senza però ripetere ciecamente la
formula "più filtri = meglio" (vedi test SAR sopra, dove ADX non ha aiutato).

**RSI_DIV**: la fonte più diretta e utile — *"la divergenza è un avviso, non
un trigger. La maggior parte dei trader perde entrando sulla divergenza
stessa."* Serve conferma: pattern di reversal candlestick, rottura di una
mini-trendline, o **RSI che rientra sopra/sotto 50** dopo la divergenza. Il
nostro trigger (`rp<30<=r` nel sito) già cattura un parziale ri-attraversamento,
ma non ha conferma di prezzo. Timeframe: le fonti raccomandano **1H e
superiori** — il nostro RSI_DIV è già su H1, coerente. Da testare: aggiungere
un secondo filtro di conferma prezzo (rottura trendline o pattern reversal).

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
