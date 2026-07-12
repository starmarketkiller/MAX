---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, overfitting, lezione]
created: 2026-07-12
updated: 2026-07-12
---

# Lezione: l'overfitting sui 3 mesi (v2.4.8)

## I numeri, senza addolcirli

| Metrica | 3 mesi (campione di tuning) | 3 anni (fuori-campione) |
|---|---|---|
| Net | **+1050** | **−863** |
| Profit factor | 1.24 | 0.85 |
| Drawdown | 29.6% | **87%** (conto quasi azzerato) |
| Sharpe | 3.19 | **−3.61** |

v2.4.8 era il miglior risultato mai ottenuto sul campione dei 3 mesi. Sui 3 anni,
lo stesso identico build **perde soldi e distrugge il conto**. Non è rumore: è la
firma classica dell'overfitting — abbiamo tarato parametri (trailing, rischio,
riabilitazioni) su una finestra specifica, e quella finestra non generalizza.

## Chi ha retto, chi no

**Robuste su entrambi gli orizzonti** (le uniche a non essere mai state ritoccate
nel tuning fine):
- TURTLE_SOUP — PF 2.12 (3Y) / 3.15 (3M)
- BJORGUM — PF 2.14 (3Y) / 1.31 (3M)
- MACD — PF 1.11 (3Y) / 1.35 (3M)

**Crollate fuori-campione** (tutte "riabilitate" o ritarate nel ciclo v2.3.7→v2.4.8):
- EMA_PULLBACK: 1.49 (3M) → **0.14** (3Y)
- OB_MIT: 1.37 → **0.20**
- ORDER_BLOCK: 1.97 → **0.24**
- ADX_RSI: 1.17 → **0.45**
- RSI_DIV, SAR, FVG_CONT: tutte scendono sotto PF 1.0

## La lezione operativa
> Le uniche cose che hanno retto sono quelle che **non abbiamo toccato**. Ogni
> ottimizzazione fine fatta guardando un solo periodo ha adattato il rumore di
> quel periodo, non creato edge vero.

Conseguenza pratica per il futuro: **nessun tuning va considerato valido finché
non è confermato su almeno due finestre temporali indipendenti** (idealmente non
sovrapposte). Un record sui 3 mesi è un'ipotesi, non una conferma.

## Nota sulla qualità dati
Il test a 3 anni usa tick reali solo per aprile-luglio 2026 (~85% qualità
storico dichiarata); il resto è ricostruito. Questo pesa sul valore assoluto dei
numeri, ma **non spiega il pattern** "solo l'intoccato regge" — quello è
strutturale, non un artefatto dei dati.

## Cosa abbiamo fatto dopo
Screening sistematico di ogni strategia sul motore Python del sito su ~10 anni
di dati Yahoo, per trovare una regola **generalizzabile** invece di un parametro
cucito su una finestra. Risultato: [[NEXUS EA - Screening Strategie (sito 10y)]].

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Log Versioni]] · [[NEXUS EA - Screening Strategie (sito 10y)]]
