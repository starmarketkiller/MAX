---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: LIQ_SWEEP
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: LIQ_SWEEP

## Tipo
SMC/liquidity sweep

## Trigger meccanico
Sweep di un massimo/minimo con reversal di conferma.

## Configurazione attuale (v2.5.0)
- **Timeframe**: D1
- **SL**: 1.5× ATR · **TP**: 3.0× ATR
- **Filtro HTF**: True
- **Trailing**: largo (famiglia SMC)
- **Rischio per trade**: 0.6%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 234 setup, 1W/1L/1BE, WR 50.0%, expR +0.017, **PF 1.60**
- **3 anni**: 4 setup, 1W/0L/0BE, WR 100.0%, expR +0.053, **PF 99.00**

## Stato
PENDING — campione troppo piccolo (<15 trade) per giudicare. Confermato sui
dati reali segmentati: **26 trade totali** su 8 segmenti disponibili
(2016+2019-2025), max 11/anno (2022, PF3.15 FORTE) — troppo pochi per
qualsiasi verdetto stabile.

## Test A/B 16/07 (Blocco 1): stesso pattern di TURTLE_SOUP, config attuale confermata la migliore trovata
Il trigger MQL5 (`NXS_Strat_LiqSweep`) è concettualmente **lo stesso** di
TURTLE_SOUP (sweep 20 barre + chiusura di rientro) ma più permissivo: nessun
filtro sul corpo della candela (Turtle Soup richiede corpo ≥0.4×ATR),
sweep generico a 20 barre invece della classificazione PDH/PDL/EQH/EQL/Asia
di Turtle Soup. Testato sul sito con la config reale del profilo
(SL1.5/TP3.0, D1, **HTF filter ON** come da profilo):

| TF | HTF | Trade | PF | DD% | Net |
|---|---|---|---|---|---|
| **D1 (= profilo attuale)** | **ON** | **14** | **3.30** | 2.02 | **+1.272** |
| D1 | ON | +filtro corpo 0.4×ATR | 7 | 4.50 | 1.0 | +732 |
| 4h/1h | ON | — | 18-23 | 0.85-0.90 | 6.8-7.0 | negativo |
| D1/4h/1h | OFF | — | 45-132 | 0.79-1.30 | vario | solo H1 positivo (PF1.2-1.3) |

**A differenza di TURTLE_SOUP** (dove D1 era il TF sbagliato), qui **D1 +
HTF ON è la combinazione migliore trovata**, non un compromesso — conferma
indiretta della config attuale del profilo, non una scoperta di errore.
Il filtro corpo (che aiutava Turtle Soup) migliora ulteriormente il PF ma
il campione crolla a 7 — troppo piccolo per applicarlo con fiducia.
**Nessun cambio di codice**: il campione (14 trade anche nel test migliore)
resta sotto soglia di giudizio ([[NEXUS EA - Principi]] #4). Interessante:
la strategia sembra essere legittimamente **a bassa frequenza per design**
(qualità via HTF invece di quantità), non un trigger da correggere — da
riverificare quando arriveranno più anni di dati reali (10y completi +
sweep MT5 1-37).

## Fix reale 16/07: sweep generico sostituito con la definizione ICT vera (PDH/PDL/Asia)

Trovato controllando sistematicamente tutte le strategie: LIQ_SWEEP era
**l'unica rimasta** sulla definizione debole di sweep (`NXS_DetectSweep`,
un estremo di 20 barre qualsiasi). TURTLE_SOUP, SH_BMS_RTO, JUDAS_SWING,
LDN_REVERSAL, PO3, AMD_REVERSAL, SILVER_BULLET usano già
`NXS_DetectSweepExt` — sweep su livelli di liquidità reali (massimo/minimo
del giorno prima, sessione asiatica, massimi/minimi uguali). Corretto sia
in MQL5 (`NXS_Strat_LiqSweep` ora prende `SNXSSweepExt`) sia sul sito
(`sig_liq_sweep_ext`, riusa la stessa funzione scritta per le 7 strategie
a sessione). Rimossa anche `NXS_PickBestSignal()`, funzione legacy morta
che teneva la vecchia firma e avrebbe rotto la compilazione.

Test A/B con la config reale del profilo (SL1.5/TP3.0):

| Config | Trade (prima→dopo) | PF (prima→dopo) | DD% (prima→dopo) |
|---|---|---|---|
| **D1 + HTF ON (= profilo)** | 14 → **141** | 3.30 → 1.27 | 2.02 → 14.25 |
| 4h, senza HTF | 134 → 134 | 0.86 → **1.32** | 20.37 → **8.71** |
| D1, senza HTF | 125 → 182 | 0.85 → 1.02 | 18.31 → 17.44 |

**Non uniformemente migliore** — su 1h e su 4h+HTF il nuovo sweep è
leggermente peggiore. Ma sulla config del profilo (D1+HTF) risolve
esattamente il problema che frenava questa strategia da 8 anni: il
campione cresce di **10 volte** (14→141) restando positivo — il PF più
basso (3.30→1.27) è normale quando un campione minuscolo e potenzialmente
fortunato si allarga, non un peggioramento reale. Su 4h senza HTF il
miglioramento è pulito su ogni metrica.

**Applicato sia a MQL5 che al sito** (non solo al sito come nei fix
precedenti) — dato l'alto grado di conferma incrociata (stesso
meccanismo già validato su 7 altre strategie). **Non ancora testato su
MT5 reale** — prossimo passo naturale è includerlo nello sweep isolato
(selector=7).

**Domanda aperta sulla ridondanza con TURTLE_SOUP**: stesso pattern di
fondo, ma le config migliori trovate sono opposte (Turtle Soup: H1/H4 senza
HTF; LIQ_SWEEP: D1 con HTF) — sembrano **complementari** (stesso concetto
a scale temporali diverse) più che ridondanti, ma serve più campione per
confermarlo.

## Testato (16/07 sera): tenere anche la versione interna come setup parallelo — non conviene
Su richiesta dell'utente di applicare la teoria interna/esterna nella sua
forma completa (due varianti, non una che sostituisce l'altra), testata
l'**unione** (interna OR esterna, spara se una qualsiasi delle due
conferma) contro la sola esterna già applicata:

| Config | Solo esterna | Unione (interna OR esterna) |
|---|---|---|
| D1+HTF (= profilo) | PF1.27, DD14.25%, 141 trade | PF1.30, DD12.51%, 142 trade — quasi identico |
| D1, no HTF | PF1.02, DD17.44% | PF1.15, DD20.40% — trade in più, DD peggiore |
| 4h+HTF | PF0.97, DD18.36% | PF0.95, DD17.86% — sostanzialmente invariato |
| **4h, no HTF (il miglior risultato trovato)** | **PF1.32, DD8.71%** | **PF1.06, DD16.88% — peggiora nettamente** |

**Non applicata**: sulla combinazione con il risultato migliore in
assoluto (4h senza HTF), aggiungere i segnali "interni" **peggiora**
sensibilmente il PF e quasi raddoppia il drawdown — i trade aggiuntivi
sono di qualità più bassa, non un'aggiunta neutra. Sulla config del
profilo attuale (D1+HTF) l'unione è marginalmente migliore ma il
contributo della versione interna è quasi nullo (141→142 trade): le due
si sovrappongono quasi del tutto lì. **Conclusione onesta**: a differenza
di ORDER_BLOCK/OB_MIT/FVG_CONT (dove la struttura esterna come filtro di
direzione ha aiutato ovunque), qui "tenere entrambe le versioni" non è
sempre un vantaggio — dipende dalla combinazione, e nel caso migliore
trovato finora è un peggioramento netto. La sola esterna resta la scelta
applicata. Codice della versione interna (`sig_liq_sweep`) lasciato nel
file per riferimento/test futuri, non richiamato.

## Fix reale 16/07 (sera): filtro qualità Order Block sulla candela di sweep

L'utente ha mostrato 2 screenshot di setup reali da trader ICT (canale
"THE ICT+CRT TRADING HUB") — in entrambi lo schema è identico: **sweep di
liquidità + vera candela Order Block esattamente nello stesso punto**
(corpo forte, "delivery candle" — non un rimbalzo qualsiasi), poi target
sulla liquidità del lato opposto (SSL/BSL). Il nostro trigger chiedeva
solo "chiude verde/rossa" dopo lo sweep — nessun requisito di corpo,
quindi anche un rimbalzo debole contava quanto una vera candela OB.

Aggiunto lo stesso filtro corpo≥0.7×ATR già usato con successo da
TURTLE_SOUP (lì 0.4×, qui serve più forte data la natura del sweep
esteso). Test A/B sulla config reale (D1+HTF):

| Versione | Trade | PF | DD% |
|---|---|---|---|
| Senza filtro corpo (fix precedente) | 141 | 1.27 | 14.25 |
| **+ corpo≥0.7×ATR** | **59** | **1.63** | **6.62** |

Migliora nettamente su 3 config su 4 (D1+HTF, D1 no-HTF, 4h+HTF); peggiora
solo su 4h-no-HTF (che restava comunque la combinazione col PF più alto
già prima di questo fix). Applicato sia al sito (`sig_liq_sweep_ext`) sia
a MQL5 (`NXS_Strat_LiqSweep`). **Non ancora validato su MT5 reale.**

## Idea aperta, non ancora implementata: target sulla liquidità opposta
Negli stessi screenshot il take-profit non è un multiplo fisso di ATR —
è il livello dove sta la **prossima liquidità** (SSL/BSL, spesso uno swing
low/high precedente), con multipli TP1/TP2 su livelli intermedi. Il
motore attuale (sito e MQL5) usa sempre `NXS_DefaultSLTP`/ATR fisso per
ogni strategia — cambiarlo per un TP dinamico basato su livelli di
struttura è un cambio più profondo (tocca il motore di uscita, non solo
il trigger d'ingresso) che richiede modifiche al backtest engine stesso,
non solo alla funzione segnale. Proposto come prossimo passo, da
confermare prima di partire dato il perimetro più ampio.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Turtle Soup]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]]
