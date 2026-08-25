---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, portafoglio, correlazione, drawdown, scoperta]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Portafoglio diversificato: risolto il problema del bucket condiviso (25/08)

## Perché

Il problema di allocazione era in pausa dal 24/08: il bucket
condiviso a 2 slot premia il cluster trend-following ad alta frequenza
e affama le diversificatrici a bassa frequenza (anche quando sono le
migliori strategie del catalogo), e due correzioni provate allora
(slot dedicati, deduplicazione) non risolvevano — la conclusione era
che serviva scegliere DELIBERATAMENTE un sottoinsieme a bassa
correlazione invece di usare tutte le strategie, mai testato. Ripreso
oggi su richiesta esplicita dell'utente ("procedi col portafoglio"),
dopo aver ricalcolato la correlazione con le config aggiornate (vedi
[[NEXUS EA - Correlazione Aggiornata con le Config di Oggi (25-08)]]).

`portfolio_diversified_25-08.py` — stessa disciplina di simulazione
del 16-24/08 (conto EUR1000, rischio EUR10/trade, tetto 0.10 lotti,
tetto rischio EUR40/trade, per confronto diretto), tre portafogli:

## Risultato: il portafoglio piccolo e diversificato batte quello grande su entrambi gli assi

| Portafoglio | Strategie | Trade grezzi | Trade eseguiti | netPnL | DD massimo |
|---|---|---|---|---|---|
| Ieri (24/08), config vecchie | 20 | — | — | +€2.725 | 35.9% |
| **(a) Oggi, catalogo completo, config aggiornate** | 24 | 7336 | 666 | **+€5.471** | **28.0%** |
| **(b) Oggi, diversificato (8 diversificatrici + ADX_RSI)** | 9 | 1610 | 490 | **+€5.754** | **23.3%** |
| (c) Diversificato, max_concorrenti=3 | 9 | 1610 | 657 | +€7.780 | 24.5% |

**Due scoperte separate, entrambe positive**:

1. **Le ottimizzazioni individuali di oggi (trailing + filtro Elliott)
   da sole hanno già quasi raddoppiato il PnL e ridotto il drawdown di
   ieri** (€2.725→€5.471, DD 35.9%→28.0%), a parità di struttura del
   portafoglio (bucket condiviso, 2 slot, tutte le strategie) — un
   effetto collaterale positivo non ancora quantificato prima d'ora.

2. **Il portafoglio diversificato (9 strategie invece di 24) fa
   MEGLIO su entrambi gli assi**, non solo su uno: PnL più alto
   (+€5.754 contro +€5.471) E drawdown più basso (23.3% contro 28.0%)
   — nonostante scarti 15 strategie e faccia 176 trade in meno. La
   diagnosi del 24/08 era corretta: il cluster trend-following non
   aggiunge diversificazione (i suoi membri sono ridondanti tra loro),
   solo rumore di concorrenza per gli slot. **Rimuoverlo quasi per
   intero (tenendo solo ADX_RSI, il più solido) migliora il
   portafoglio, non lo peggiora.**

**Bonus**: dato che le 9 strategie diversificate competono molto meno
tra loro per gli slot (825 scarti-bucket contro 5406 del portafoglio
completo), c'è margine per allentare il tetto di concorrenza. Con
max_concorrenti=3 (invece di 2) il PnL sale a +€7.780 con un
drawdown ancora contenuto (24.5%, appena sopra il 23.3% base) — un
compromesso migliore di qualunque combinazione provata il 24/08 sul
portafoglio a 20 strategie (dove più slot faceva sempre esplodere il
drawdown, fino al 55.8% con 1+3 slot).

## Contributo per strategia (portafoglio diversificato, prima del bucket)

| Strategia | n trade grezzi | sumR |
|---|---|---|
| ADX_RSI | 657 | +576.1 |
| OTE_CONT | 214 | +255.0 |
| EMA_PULLBACK | 223 | +183.9 |
| TURTLE_SOUP | 262 | +97.8 |
| FVG_MIT | 74 | +73.7 |
| STRUCT_REACT | 50 | +50.0 |
| BOLLINGER | 52 | +36.0 |
| RSI_DIV | 48 | +32.7 |
| LDN_REVERSAL | 30 | +10.0 |

Tutte e 9 contribuiscono positivamente — nessuna trascina il
portafoglio in basso, a differenza del 24/08 dove 6/16 strategie erano
in perdita netta dentro il bucket condiviso.

## Verdetto

**Configurazione consigliata (aggiornata dopo gli addendum sotto): 14
strategie (le 8 diversificatrici + ADX_RSI + TSI/LIQ_SWEEP/SAR_FLIP/
LONDON_BO/FVG_CONT_V2), max_concorrenti=3 — netPnL +€9.180, DD 25.2%**.
Sia la versione a 9 sia quella a 14 restano nettamente meglio del
catalogo completo (24 strategie: +€5.471/DD28.0%). Conferma diretta
della diagnosi del 24/08: il problema non era il bucket in sé, era
usarlo con un pool di strategie ridondanti tra loro — un pool piccolo
e davvero indipendente lo risolve senza bisogno di riprogettare il
motore di simulazione (l'ipotesi "budget di rischio indipendente per
strategia" resta un'alternativa più complessa, non più necessaria in
via prioritaria).

## Limiti dichiarati

- FVG_CONT_V2, MALAYSIAN_SNR_BREAKOUT, SAR_FLIP, AMD_CONT, TSI,
  Z_SCORE_BREAKOUT, ML_ADAPTIVE_SUPERTREND, ELLIOTT_WAVE3_CONT non
  incluse in questo portafoglio (né nel cluster né nelle 8
  diversificatrici principali) — meriterebbero una valutazione a
  parte se aggiungerle aiuterebbe o diluirebbe ulteriormente.
- Nessun controllo ancora fatto su regime/periodo (il DD potrebbe
  concentrarsi in una finestra specifica, non ancora scomposto per
  anno come nel backtest 10Y di luglio).
- Simulazione ancora in Python, non nel motore MT5 reale — stessa
  cautela di sempre prima di qualunque passo verso demo/live.

## Addendum — sweep di max_concorrenti: nessuna esplosione, ma serve cautela

Sul portafoglio a 9 strategie, il drawdown **non esplode mai** anche a
concorrenza molto alta — pattern opposto a quello trovato il 24/08 sul
portafoglio correlato (dove più slot faceva salire il DD fino al
55.8%):

| max_concorrenti | netPnL | DD massimo |
|---|---|---|
| 2 | +€5.754 | 23.3% |
| 3 | +€7.780 | 24.5% |
| 5 | +€11.149 | 28.1% |
| 8 | +€15.599 | 27.0% |
| 15 | +€19.910 | 27.2% |
| 20+ (praticamente illimitato) | +€20.034-20.111 | **27.2% (plateau)** |

Il DD si stabilizza intorno al 27% e non sale oltre, anche rimuovendo
ogni tetto — segno che le 9 strategie raramente perdono nello stesso
momento. **Cautela importante**: questo è un limite del metodo, non
una prova che la concorrenza sia priva di rischio — la correlazione
misurata è storica (894-901 giorni 2019-2026), un evento di coda mai
visto nello storico (es. un flash crash che muove tutte le strategie
nella stessa direzione contemporaneamente) non sarebbe catturato. Non
raccomandabile usare concorrenza "illimitata" solo perché il backtest
non mostra un limite — il rendimento marginale oltre max_concorrenti=8
è comunque modesto (+€4.500 da 8 a 20, contro +€10.000 da 2 a 8).

## Addendum — le strategie escluse aggiungono valore, selettivamente

Testate le 8 strategie escluse (né nel cluster né tra le diversificatrici
principali) aggiunte una alla volta al portafoglio a 9 (mc=3, base
+€7.780/DD24.5%):

| Aggiunta | ΔnetPnL | ΔDD | Verdetto |
|---|---|---|---|
| **TSI** | +€655 | +0.3pp | Aggiungere — la migliore |
| **LIQ_SWEEP** | +€356 | +0.1pp | Aggiungere |
| MALAYSIAN_SNR_BREAKOUT | +€411 | **+1.3pp** | Scartare — compromesso peggiore |
| SAR_FLIP | +€245 | +0.0pp | Aggiungere |
| LONDON_BO | +€197 | +0.0pp | Aggiungere |
| FVG_CONT_V2 | +€113 | +0.0pp | Marginale, aggiungibile |
| AMD_CONT | -€1 | +0.4pp | Scartare — netto negativo |
| ELLIOTT_WAVE3_CONT | -€20 | +0.0pp | Scartare — coerente col suo stato provvisorio |

**Portafoglio esteso a 14 strategie** (9 + TSI/LIQ_SWEEP/SAR_FLIP/
LONDON_BO/FVG_CONT_V2), mc=3: **netPnL +€9.180, DD 25.2%** — meglio
del portafoglio a 9 (+€7.780/24.5%) per un costo di rischio modesto
(+0.7pp). A concorrenza più alta però il DD sale più rapidamente che
nel portafoglio puro a 9 (mc=5: DD30.9% contro 28.1%) — alcune delle
5 aggiunte (SAR_FLIP/FVG_CONT_V2, entrambe vicine al cluster)
reintroducono un po' di correlazione ad alta concorrenza. **Consigliato
il portafoglio a 14 strategie con mc=3**, non spingere la concorrenza
oltre su questa versione estesa senza riverificare.

## Prossimi passi aperti

- Scomporre il DD del portafoglio (9 o 14 strategie) per anno/regime —
  non ancora fatto.
- Stress-test qualitativo del rischio di coda non catturato dalla
  correlazione storica (la cautela sopra) — richiede un'ipotesi
  esplicita su cosa simulare, non ancora definita.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Correlazione Aggiornata con le Config di Oggi (25-08)]]
[[NEXUS EA - Correlazione tra le 20 Strategie (24-08)]]
[[NEXUS EA - Portafoglio a 20 Strategie (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
