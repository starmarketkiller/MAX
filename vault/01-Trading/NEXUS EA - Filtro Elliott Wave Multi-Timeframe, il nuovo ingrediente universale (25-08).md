---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, elliott-wave, multi-timeframe, frattale, filtro, scoperta]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Filtro Elliott Wave multi-timeframe: il nuovo ingrediente più universale trovato finora (25/08)

## Perché

Prima implementazione concreta dell'idea Elliott Wave dell'utente
(mai attaccata prima, chiesta all'inizio della sessione del 24/08:
"i pattern di elliot sono meccanici in sé, la soggettività sta solo
nell'interpretazione"). L'utente ha aggiunto durante il lavoro
un'osservazione decisiva: **"il sistema Elliott penso sia
multidimensionale nel mercato, o frattale — si ripete da TF più grande
a più piccoli con onde e rintracciamenti per ogni wave"** — questo ha
cambiato l'approccio da singolo-timeframe a multi-timeframe a metà
del test, con un risultato molto più forte.

## Meccanica

`elliott_wave_filter_25-08.py`: ZigZag su prezzo (soglia = 2.0×ATR),
poi le 3 regole classiche di un impulso Elliott a 5 onde su ogni
timeframe indipendentemente:
1. onda 2 non ritraccia sotto l'inizio dell'onda 1
2. onda 3 non è la più corta tra onda1/onda3/onda5
3. onda 4 non sovrappone il territorio dell'onda 1

Quando un impulso a 5 onde valido si conclude su un timeframe, quel
timeframe entra in stato "ESAURITO" nella direzione dell'impulso
(aspettati correzione) finché non si forma un nuovo pivot. Usato per
**sopprimere** segnali di ingresso nella stessa direzione dell'impulso
appena esaurito — non come sistema di ingresso proprio, come filtro di
contesto sopra le strategie esistenti (stesso ruolo di ER/floor/D1-align).

## Test 1 — singolo timeframe (4h): già positivo, ma non il massimo

Su 5 strategie (ADX_RSI/STRUCT_REACT/EMA_PULLBACK/SAR/MACD), il filtro
sul solo 4h migliora quasi tutte (dev=2.0 il punto migliore): ADX_RSI
1.77→1.94, SAR 1.51→1.58, MACD 1.46→1.50, EMA_PULLBACK 1.30→1.36,
STRUCT_REACT stabile. Consistente ma modesto.

## Test 2 — multi-timeframe (4h + D1): il salto vero, conferma l'idea frattale

Quattro combinazioni testate (4h-solo, D1-solo, **confluenza AND**
[richiede esaurimento su ENTRAMBI], **unione OR** [basta un timeframe
qualsiasi]) su ADX_RSI/SAR/MACD:

| Strategia | Baseline | 4h solo | D1 solo | AND (entrambi) | **OR (uno qualsiasi)** |
|---|---|---|---|---|---|
| ADX_RSI | 1.77 | 1.94 | 1.86 | 1.77 (~nessun effetto) | **2.04** |
| SAR | 1.51 | 1.58 | 1.58 | 1.51 (~nessun effetto) | **1.65** |
| MACD | 1.46 | 1.50 | 1.49 | 1.46 (~nessun effetto) | **1.53** |

**AND è quasi inerte** (i due timeframe raramente si esauriscono
esattamente insieme — troppo raro per filtrare qualcosa). **OR è
nettamente il migliore** su tutti e 3 — l'esaurimento a QUALSIASI
scala conta, non serve che concordino. Conferma diretta e testata
dell'osservazione dell'utente: il sistema è frattale, un'onda 5
esaurita sul 4h è un segnale valido di correzione imminente anche se
il D1 non ha ancora completato la propria onda di grado superiore, e
viceversa.

**Terza scala (1h) provata e scartata**: aggiungere 1h all'unione
(1h+4h+D1) non migliora ulteriormente (ADX_RSI 2.06 vs 2.04, SAR 1.62
vs 1.65 — sostanzialmente pari o leggermente peggio) — il 1h è troppo
rumoroso rispetto al timeframe di ingresso (4h) e i suoi falsi
esaurimenti diluiscono il filtro invece di rafforzarlo. **4h+D1 resta
la combinazione ottimale**, non 3 scale.

## Test 3 — validazione su 8 strategie con la combinazione vincente (4h+D1 OR)

| Strategia | Baseline PF (m1/m2) | +Filtro Elliott PF (m1/m2) | Finestre |
|---|---|---|---|
| ADX_RSI | 1.77 (1.92/1.63) | **2.04 (2.28/1.83)** | 5/5 → 5/5 |
| SAR | 1.51 (1.36/1.69) | **1.65 (1.48/1.84)** | 5/5 → 5/5 |
| MACD | 1.46 (1.39/1.54) | **1.53 (1.46/1.62)** | 5/5 → 5/5 |
| EMA_PULLBACK | 1.30 (1.14/1.48) | **1.45 (1.21/1.72)** | 3/5 → 4/5 |
| FVG_CONT | 1.51 (1.35/1.69) | **1.62 (1.39/1.89)** | 5/5 → 5/5 |
| SAR_ADX20 | 1.49 (1.35/1.64) | **1.61 (1.45/1.77)** | 5/5 → 5/5 |
| TSI | 2.03 (1.97/2.10) | **2.25 (2.04/2.46)** | 5/5 → 5/5 |
| STRUCT_REACT | 2.65 (2.82/2.48) | 2.28 (2.61/2.01) | 5/5 → **4/5** (peggiora) |

**7 strategie su 8 migliorano**, quasi sempre mantenendo o migliorando
la robustezza per finestra e SENZA sbilanciare m1/m2 (anzi spesso
riequilibrando, es. TSI m1 1.97→2.04). Unica eccezione: STRUCT_REACT
peggiora — coerente col pattern già visto oggi (STRUCT_REACT resiste o
peggiora con quasi ogni filtro extra provato: trailing, Fibonacci
esaurimento — è una strategia che vuole rimanere "pulita").

## Test 4 — estensione a 12 strategie in più: conferma su larga scala

Con la stessa combinazione vincente (4h+D1, OR), esteso ad altre 12
strategie (config SL/TP di baseline nota, non necessariamente la
config finale già ottimizzata con trailing/D1-align — qui l'obiettivo
è isolare l'effetto del filtro Elliott, non sommare tutti gli
ingredienti insieme):

| Strategia | Baseline PF (m1/m2, finestre) | +Filtro Elliott | Verdetto |
|---|---|---|---|
| OTE_CONT | 1.61 (1.69/1.52, 3/5) | **1.99 (2.29/1.70, 5/5)** | Forte — anche le finestre saltano da 3/5 a 5/5 |
| SAR_FLIP | 1.78 (1.40/2.27, 4/5) | **2.07 (1.50/2.86, 4/5)** | Forte |
| MALAYSIAN_SNR_BREAKOUT | 1.93 (1.83/2.04, 5/5) | **2.14 (1.81/2.51, 5/5)** | Buono |
| AMD_CONT | 1.62 (1.26/2.06, 4/5) | **1.80 (1.43/2.25, 4/5)** | Buono |
| BREAKOUT_ACC | 1.33 (1.19/1.48, 4/5) | **1.38 (1.24/1.54, 5/5)** | Modesto ma sale anche la robustezza — **unica strategia che aveva resistito al trailing ieri e qui migliora** |
| DONCHIAN_TURTLE | 1.56 (1.47/1.67, 5/5) | **1.63 (1.45/1.83, 5/5)** | Modesto — anche questa aveva resistito al trailing |
| DARVAS_BOX | 1.58 (1.44/1.73, 5/5) | **1.65 (1.43/1.89, 5/5)** | Modesto, idem |
| BOLLINGER | 1.54 (1.27/1.85, 4/5) | **1.95 (1.91/1.99, 3/5)** | Forte sul PF ma **finestre 4/5→3/5**, unico costo di robustezza visto oggi |
| RSI_DIV | 1.65 (1.41/1.91, 4/5) | **1.96 (2.21/1.73, 4/5)** | Buono |
| LIQ_SWEEP | 1.73 (1.73/1.73, 5/5) | 1.73 (1.62/1.85, 5/5) | Neutro — PF identico, leggermente meno bilanciato |
| LONDON_BO | 1.60 (1.71/1.49, 4/5) | 1.60 (1.71/1.49, 4/5) | Neutro — nessun trade filtrato in questo campione (n invariato) |
| FVG_MIT (config base, non quella con D1-align+trailing) | 0.97 (0.83/1.13, 3/5) | 1.03 (0.72/1.42, 3/5) | Marginale, ma questa non è la config promossa di FVG_MIT (quella usa D1-align, non ancora testata col filtro Elliott) |

**Bilancio complessivo su 20 strategie testate (8 del primo giro + 12
di questo)**: **16 migliorano** (di cui 9 in modo netto), **2 neutre**
(nessun danno), **1 marginale** (FVG_MIT nella sua config non
ottimale), **1 peggiora** (STRUCT_REACT). Nessun'altra strategia
testata oggi o ieri ha un tasso di successo così alto e così pochi
effetti collaterali negativi — il filtro Elliott multi-timeframe è
oggettivamente l'ingrediente con l'hit-rate più alto trovato in tutta
la sessione di 2 giorni.

**Non ancora testate**: FVG_CONT_V2, Z_SCORE_BREAKOUT (1h, richiede
mappatura D1 diversa), TURTLE_SOUP, LDN_REVERSAL (stop strutturali,
richiedono adattare il collector), ML_ADAPTIVE_SUPERTREND (segnale
esterno più complesso). Nessuna di queste testata per limiti di tempo
in questo turno, non per un problema noto.

## Perché è la scoperta più importante della giornata

Rispetto agli altri ingredienti trovati in 2 giorni di lavoro (floor
ATR: aiuta ~5/14 strategie; D1-align: aiuta solo le strategie
border-line ER; trailing: aiuta 11/19 ma in modo imprevedibile,
peggiora la robustezza altrove) — il filtro Elliott multi-timeframe,
su **20 strategie testate in totale**, **migliora 16** (9 in modo
netto), **non danneggia altre 2**, è marginale su 1 (in una config non
ottimale) e peggiora solo **1** (STRUCT_REACT). Nessun altro
ingrediente trovato in tutta la sessione ha un tasso di successo così
alto con così pochi effetti collaterali — inclusi 3 casi (BREAKOUT_ACC,
DONCHIAN_TURTLE, DARVAS_BOX) che avevano **resistito al trailing**
ieri e qui migliorano comunque. È il candidato più vicino a un
ingrediente universale trovato finora, pur restando da verificare
sulle ~7 strategie ancora non testate (stop strutturali/segnali
esterni più complessi da adattare) prima di trattarlo come tale.

## Cosa NON è stato fatto

Nessuna modifica al codice MQL5 — su richiesta esplicita dell'utente
(vedi [[NEXUS EA - Correzione Trailing Z_SCORE_BREAKOUT, il TP fisso lo annullava (25-08)]]
e la memoria salvata), questo resta un risultato di ricerca Python,
documentato ma non applicato al motore live.

## Prossimi passi aperti

- Testare le ~7 strategie rimaste (FVG_CONT_V2, Z_SCORE_BREAKOUT,
  TURTLE_SOUP, LDN_REVERSAL, ML_ADAPTIVE_SUPERTREND) — richiedono
  adattare il collector a stop strutturali/segnali esterni.
- Provare la sensibilità alla soglia ZigZag (dev_mult) più a fondo —
  finora solo 1.5/2.0/2.5 testati sul 4h-solo, non riottimizzati per la
  versione 4h+D1.
- Capire perché STRUCT_REACT è l'unica a peggiorare — potrebbe
  condividere la stessa causa della sua resistenza al trailing/Fibonacci
  (segnale già molto selettivo, ogni filtro aggiuntivo taglia solo
  campione senza guadagno).
- Capire perché BOLLINGER è l'unica a perdere robustezza per finestra
  (4/5→3/5) pur guadagnando molto in PF — vale la pena controllare
  quale finestra specifica peggiora prima di considerarla equivalente
  agli altri miglioramenti "puliti".
- Combinare il filtro Elliott con le config già ottimizzate ieri
  (trailing, D1-align) per vedere se gli effetti si sommano o si
  sovrappongono — non ancora provato, ogni test di oggi ha isolato
  l'Elliott da solo sopra la baseline non ottimizzata.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
[[NEXUS EA - Correzione Trailing Z_SCORE_BREAKOUT, il TP fisso lo annullava (25-08)]]
