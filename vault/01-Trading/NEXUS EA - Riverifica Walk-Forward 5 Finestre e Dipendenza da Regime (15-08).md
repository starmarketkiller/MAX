---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, walk-forward, regime, multi-tf, survival-set]
created: 2026-08-15
updated: 2026-08-15
---

# NEXUS EA — Le 5 "Sopravvissute ai Costi" Non Sono Walk-Forward Stabili (15/08)

Seguito diretto di [[NEXUS EA - Motore Costi e Riverifica Nucleo (14-08)]].
Il batch del 14/08 aveva dichiarato SAR/LONDON_BO/MACD/EMA_PULLBACK/FVG_CONT
"sopravvissute ai costi" usando un solo split OOS (60-100% dei dati). Qui:
walk-forward vero a 5 finestre, poi test se `regime_filter` risolve, poi
test su TF più bassi, poi diagnosi del meccanismo (nessun bug trovato).

## 1. Walk-forward a 5 finestre: tutte e 5 dipendono dal regime recente

Stesso pattern su OGNI strategia: PF che sale dalla finestra 0 (più vecchia)
alla finestra 4 (più recente) — 3-4 finestre su 5 sotto pareggio con costi
retail:

| Strategia | F0 | F1 | F2 | F3 | F4 (= test OOS del 14/08) |
|---|---|---|---|---|---|
| SAR | 0.69 | 0.70 | 0.75 | 0.95 | 1.38 |
| LONDON_BO | 0.44 | 0.66 | 0.44 | 0.88 | 1.44 |
| MACD | 0.90 | 0.66 | 0.64 | 1.08 | 1.88 |
| EMA_PULLBACK | 0.48 | 0.47 | 0.70 | 0.85 | 1.14 |
| FVG_CONT | 0.96 | 0.79 | 0.64 | 1.11 | 1.39 |

Il verdetto "sopravvive" del 14/08 era vero solo sull'ultimo quinto della
storia — il periodo più anomalo del dataset, non un campione rappresentativo.

## 2. Cosa distingue le finestre: non ADX, è il regime dell'oro

ADX medio piatto (25-27) in ogni finestra, % barre up ~50% ovunque — il
classificatore di trend generico non vede differenza. La differenza vera è
prezzo/volatilità:

| Finestra | Periodo (4h) | Var. prezzo | ATR% medio |
|---|---|---|---|
| 0 | 2019-03 → 2020-11 | +44% (include crash COVID) | 0.70% |
| 1 | 2020-11 → 2022-04 | +4.4% — laterale | 0.49% |
| 2 | 2022-04 → 2023-10 | +1.2% — laterale | 0.45% |
| 3 | 2023-10 → 2025-03 | +47.5% | 0.58% |
| 4 | 2025-03 → 2026-08 | +49.9% | **1.19%** (quasi doppia della norma) |

Quasi 3 anni (finestre 1-2) di oro sostanzialmente laterale hanno affondato
tutte e 5 le strategie trend-following. Le finestre 3-4 sono un rally
storico (quasi raddoppio in 18 mesi) — condizioni eccezionali, non la norma.

## 3. `regime_filter` (ADX-based, già nel motore) non risolve

Testato `regime_filter={STRONG_TREND, WEAK_TREND}` sulle stesse 5 finestre:
nessun miglioramento sistematico, in alcuni casi peggiora (SAR F3: 0.95→0.84
col filtro). Il classificatore ADX generico non riesce a isolare "il rally
2023-2026" da "trend normale" — non è chop genericamente definibile e
filtrabile con gli strumenti esistenti.

## 4. Ipotesi utente: TF più bassi per muoversi più veloce? Testata, smentita

Batch 5 strategie × 4 TF (15m/30m/1h/4h) × 5 finestre, stessa ricetta
(`server/research_scripts/multitf_walkforward_15-08.py`). Risultato netto,
opposto all'ipotesi: **più basso il TF, peggio va, su ogni strategia senza
eccezioni**.

| Strategia | 15m | 30m | 1h | 4h |
|---|---|---|---|---|
| SAR | 0/5 finestre PF≥1 | 0/5 | 1/5 | 1/5 |
| LONDON_BO | 0/5 | 0/5 | 1/5 | 1/5 |
| MACD | 0/5 | 0/5 | 1/5 | 2/5 |
| EMA_PULLBACK | 0/5 | 1/5 | 1/5 | 3/5 |
| FVG_CONT | 0/5 | 0/5 | 1/5 | 2/5 |

Su 15m nessuna supera PF 1.0 in nessuna finestra (spesso 0.15-0.30). Motivo:
lo stesso costo fisso ($2.50 spread + $0.50 slippage) pesa una frazione
molto più grande di `risk_dist` più piccolo (stop ATR-based più stretto in
$ a TF basso), moltiplicato per un numero di trade che esplode (es. SAR:
126 trade/finestra a 4h contro 1314 a 15m).

## 5. Diagnosi del meccanismo (nessun bug trovato)

Verifica esplicita richiesta dall'utente ("c'è qualcosa che stai
sbagliando?") dopo il risultato TF basso. Ispezionati `trade_list` reali di
SAR 15m (finestra migliore, PF 0.62, n=1314, DD 96%):
- `avg_loss_mfe_r = 0.78` — i trade perdenti erano andati mediamente a
  +0.78R a favore prima di girare e chiudere in stop
- `near_miss_loss_pct = 55.8%` — più della metà dei perdenti erano
  "quasi vincenti"

Conferma diretta dell'intuizione dell'utente (osservata su TradingView,
specialmente su MACD: "prende il trend poi chiude quasi in pari"): la
direzione è spesso giusta, ma sui TF bassi il rumore a breve termine fa
girare il prezzo prima che tocchi il TP, e lo stop lo intercetta. Coerente
con l'analisi MFE/MAE già fatta il 17/07 per MACD (85.6-70.5% di segnali
che raggiungono ≥1R a favore, ma TP troppo stretto li tagliava) — stesso
fenomeno, non un errore di test. Il TF basso peggiora perché amplifica
proprio questo meccanismo (più rumore relativo, più trade, stesso costo
fisso per trade).

## Conclusione

Nessuna delle 5 "sopravvissute" ha un edge dimostrato stabile su tutta la
storia disponibile. Non è overfitting da parametri (nessun tuning è stato
fatto su queste finestre), è dipendenza dal regime — l'attuale rally
storico dell'oro rende favorevoli strategie trend-following che
avrebbero perso soldi nel 2020-2023. Il TF più basso non è una via
d'uscita: peggiora tutto, in modo sistematico e spiegabile (costo fisso
su stop più stretti + più trade). 4h resta il meno peggio dei TF
disponibili, ma "meno peggio" non è "pronto per il live".

## 6. Ricerca sul catalogo completo (17 candidate, nucleo + escluse, H4/D1)

`server/research_scripts/full_catalog_walkforward_15-08.py`, stesso
protocollo (5 finestre, costi retail, ricetta reale da `NXS_Profile_Get`).
Nessuna scoperta reale:
- **TSI** (1d): 4/5 finestre PF≥1 (1.25/0.48/1.91/1.56/2.45) ma **9-13
  trade a finestra** — campione troppo piccolo per fidarsi, coerente con
  la cautela già espressa nel vault del 12/08 ("la scoperta più fragile
  della sessione").
- **LIQ_VOID** (4h): 3/5 finestre, campione decente (73-90/finestra) —
  ma è un FALSO candidato: `"LIQ_VOID": sig_fvg_cont_ext` nel codice, **la
  stessa identica funzione segnale di FVG_CONT**, con SL/TP più stretti
  (1.0/4.5 vs 1.5/6.0, niente BE). PF leggermente migliore in ogni
  finestra ma DD sistematicamente ~doppio (23.8%/26.6%/30.6%/16.8%/11.4%
  contro 12.9%/20.0%/23.4%/8.8%/7.7% di FVG_CONT) — un trade-off
  PF-vs-DD sullo stesso segnale, non una strategia diversa. Resta 3/5,
  non 5/5: le finestre 1-2 perdono comunque.
- Tutti gli altri 15 candidati D1 hanno campioni da 0 a 21 trade totali
  su ~7 anni di storia — statisticamente inutilizzabili (BB_SQUEEZE,
  MALAYSIAN_SNR, OB_MIT, ORDER_BLOCK, SMS_BMS_RTO, WEEKLY_EXP quasi a
  zero segnali; SH_BMS_RTO/OTE_CONT poco meglio ma comunque <25 trade
  totali).

## 7. Bug reale trovato dopo il dubbio dell'utente (16/08): spread fisso non scalato sul prezzo

L'utente ha insistito giustamente ("c'è qualcosa che non va") dopo il test
multi-TF. Ipotesi specifica (un cambiamento CRT-only rimasto globale):
verificata e ESCLUSA — il cap `MAX_COST_R_PER_TRADE=5.0` non si avvicina
mai a scattare su SAR/MACD/ecc (costo osservato 0.4-0.8R per trade, non
vicino al tetto di 5R).

Trovato invece un problema reale e diverso: `COST_PRESETS["retail_standard"]`
(spread $2.50 + slippage $0.50) è un valore FISSO applicato uniformemente
su tutto il periodo 2019-2026, ma il prezzo dell'oro (e la sua volatilità
assoluta) è variato di 3-4x nello stesso periodo (ATR(14) 4h: $3.26 a
inizio 2019 contro $27-35 nel 2025-2026). Lo stesso costo fisso pesava
61% dello stop nel 2019 contro 6-13% oggi — un difetto di calibrazione
storica, non un errore di calcolo.

**Correzione**: spread/slippage scalati sul prezzo medio di ciascuna
finestra (rispetto a un riferimento di $2500, il livello a cui il preset
`retail_standard` è tarato). Risultato — migliora, non ribalta:

| Strategia | F0 prima→dopo | F1 | F2 | F3 prima→dopo | F4 |
|---|---|---|---|---|---|
| SAR | 0.69→0.79 | 0.70→0.80 | 0.75→0.81 | 0.95→**1.03** | 1.38→1.31 |
| MACD | 0.90→**1.10** | 0.66→0.71 | 0.64→0.68 | 1.08→1.09 | 1.88→1.76 |
| FVG_CONT | 0.96→**1.22** | 0.79→0.88 | 0.64→0.75 | 1.11→**1.43** | 1.39→1.32 |
| LONDON_BO | 0.44→0.51 | 0.66→0.62 | 0.44→0.41 | 0.88→**1.09** | 1.44→1.43 |
| EMA_PULLBACK | 0.48→0.57 | 0.47→0.53 | 0.70→0.82 | 0.85→0.87 | 1.14→1.00 |

La finestra 0 (2019-2020) migliora sensibilmente per 3/5 strategie (ora
sopra pareggio). Le finestre 1-2 (2020-2023) restano sotto pareggio anche
corrette — coerente con la prova indipendente §2 (efficienza direzionale
3.7%/10.5%, calcolata sul solo prezzo, senza nessun costo coinvolto):
quel periodo era genuinamente laterale, non un artefatto di costi.

**Fix reso permanente**: `scaled_cost_for_price()` aggiunta in
`server/backtest.py` (vicino a `COST_PRESETS`), da usare al posto del
preset flat per qualunque futuro walk-forward su periodi storici lunghi
a prezzo oro molto diverso da oggi.

## Conclusione definitiva dell'intero filone 14-15-16/08

Nessuna strategia — nel nucleo attuale o tra le escluse, su nessun TF
testato — ha un edge dimostrato stabile su tutta la storia disponibile
sotto costi realistici, con campione statisticamente credibile. Le 5
"sopravvissute" del 14/08 vivono del rally storico dell'oro 2023-2026,
non di un edge strutturale indipendente dal regime. Punto di decisione
per l'utente, non tecnico: (a) accettare il rischio di regime e trattare
le 5 come "shadow/watch, size minima" scommettendo che il trend prosegua,
(b) investire in una ricerca di edge genuinamente nuova (fuori dal
catalogo attuale), o (c) accettare che oggi NEXUS non ha ancora nulla di
pronto per size vera e ridefinire l'obiettivo a più lungo termine.

## Collegamenti
[[MOC - Trading]]
