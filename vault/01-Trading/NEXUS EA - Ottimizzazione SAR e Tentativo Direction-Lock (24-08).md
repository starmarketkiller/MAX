---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar, direction-lock, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale SAR e primo tentativo di direction-lock (24/08)

## Perché

Dodicesima ottimizzazione, prima del "nucleo storico". SAR è già
verificata sulla finestra laterale (fa parte del batch originale di 6
corrette in [[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]:
BUY laterale PF0.55 n=111, SELL laterale PF1.66 n=110) — il campione
**più grande e robusto** di tutto il gruppo di flip confermati, quindi
il candidato migliore per provare l'idea, finora mai costruita, del
"direction-lock condizionato al regime" citata nell'avviso della
tabella master.

## Parte 1 — trailing: miglioramento reale

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| BUY-only, target fisso 1.5/4.0 (nota) | 1.51 (1.36/1.69) | 5/5 | 1471 |
| **BUY + trailing 2.0×ATR** | **1.64 (1.28/2.04)** | 5/5 | 1471 |
| BUY + trailing 2.5×ATR | 1.55 (1.32/1.81) | 5/5 | 1471 |
| BUY + trailing 3.0×ATR | 1.55 (1.12/2.01) | 5/5 | 1471 |

**Adottato trailing 2.0×ATR** — miglioramento pulito sul campione più
grande testato oggi (n=1471), 5/5 finestre in entrambi i casi.

## Parte 2 — direction-lock per regime: tentativo fallito, documentato onestamente

Idea: invece di BUY-only fisso, usare un classificatore di regime
macro (D1, non il singolo ER a 4h già nel filtro) per decidere se
prendere solo BUY (regime rialzista) o solo SELL (regime laterale/
ribassista), sfruttando il fatto che SAR ha un vero flip confermato.

**Classificatore provato**: Efficiency Ratio giornaliero, lookback 120
giorni (~6 mesi) sul close D1 — `ratio=|net|/Σ|Δclose|`, soglia 0.045
(stessa soglia del filtro esistente ma su scala macro invece che
locale). Verificato che il classificatore FUNZIONA bene da solo:
etichetta correttamente gran parte di 2021-2023 come LATERAL/BEAR e
tutto il 2024-2026 come BULL, coerente con la classificazione
indipendente del 15/08.

**Ma applicato come gate sui segnali SAR (BULL→BUY, BEAR/LATERAL→SELL),
non risolve il problema**:

| Config | n totale | PF (m1/m2) | finestre | n nella finestra laterale | PF laterale |
|---|---|---|---|---|---|
| BUY-only fisso (baseline) | 1471 | 1.51 (1.36/1.69) | 5/5 | 111 | 0.55 |
| **Direction-lock D1-macroER** | 1513 | 1.54 (1.32/1.79) | 5/5 | **121** | **0.55** |

Il PF aggregato non cambia in modo significativo (1.51→1.54) e — punto
chiave — **dentro la finestra laterale il risultato resta quasi
identico** (n=121 invece di 111, PF ancora 0.55, sumR -49.3 invece di
-46.0). La causa: il classificatore macro D1 dice "LATERAL/BEAR" per
buona parte di quel periodo, ma **il generatore di segnale SAR (PSAR
flip su 4h, filtrato dall'ER locale a 1000 barre) continua a produrre
quasi solo segnali BUY anche lì** — dei 1513 trade totali, solo 69
(4.6%) sono finiti in direzione SELL. Il mismatch non è nel
classificatore di regime (funziona), è che **il segnale stesso non
genera abbastanza occasioni SELL da poter essere "raddrizzato" da un
gate esterno** — servirebbe un generatore di segnale SELL nativo e
distinto (es. PSAR flip letto in modo diverso, o una logica
controtrend dedicata), non un semplice cambio di direzione sullo
stesso segnale.

## Verdetto

**SAR aggiornata**: trailing 2.0×ATR adottato (PF1.51→1.64).
**Direction-lock**: primo tentativo concreto dell'idea, **non
promosso** — utile capire perché fallisce (mismatch tra frequenza del
segnale e classificazione di regime) prima di riprovarla altrove. Se
si vuole insistere su questa strada, serve ripartire dalla generazione
del segnale SELL, non dal gate di regime.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
