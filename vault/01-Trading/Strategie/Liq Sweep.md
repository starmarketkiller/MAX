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

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[Turtle Soup]] · [[NEXUS EA - Ricerca Esterna e Test A-B per Strategia]]
