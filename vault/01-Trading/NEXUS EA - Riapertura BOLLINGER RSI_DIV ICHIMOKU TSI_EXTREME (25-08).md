---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bollinger, rsi-div, ichimoku, tsi-extreme, buy-sell, regime, riverifica]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Riapertura di BOLLINGER, RSI_DIV, ICHIMOKU, TSI_EXTREME (25/08)

## Perché

Seguito diretto della riapertura di Hull Suite/ML Adaptive SuperTrend
(vedi [[NEXUS EA - Riverifica Hull Suite e ML Adaptive SuperTrend con BUY-SELL e Laterale (25-08)]]):
queste 4 strategie native del motore erano state **confermate deboli
solo in forma simmetrica** (griglia SL/TP del 24/08, vedi
[[NEXUS EA - Espansione Baseline con Ricetta Variabile (24-08)]]) — MAI
sottoposte allo split BUY/SELL sistematico (erano fuori dalla lista
delle 14 testate in [[NEXUS EA - Sweep Sistematico BUY-SELL (24-08)]]).
Screening rapido con SL1.5/TP4.0 + ER/floor, split BUY/SELL, verifica
sulla finestra laterale su tutte e 4 insieme.

## Risultato: 2 promosse, 2 confermate deboli

| Strategia | BUY aggregato | SELL aggregato | BUY laterale | SELL laterale | Verdetto |
|---|---|---|---|---|---|
| **BOLLINGER = RANGE_FADE** | PF1.54 (n=67) | PF0.66 (n=117) | PF0.37 (n=7) | **PF3.34 (n=10)** | **Promossa** |
| **RSI_DIV** | PF1.65 (n=53) | PF0.50 (n=250) | PF0.00 (n=3) | **PF1.36 (n=21)** | **Promossa** |
| ICHIMOKU | PF1.61 (n=43) | PF0.49 (n=45) | PF2.16 (n=6) | PF2.21 (n=2) | Inconcludente — campioni troppo sottili (n=2/6) |
| TSI_EXTREME | PF0.92 (n=38) | PF0.74 (n=84) | PF0.00 (n=4) | PF3.65 (n=8) | Non promossa — il BUY-only aggregato è già sotto pareggio (0.92), il pattern SELL-laterale forte non basta a salvarla |

**BOLLINGER/RANGE_FADE** (stesso segnale, verificato identico come già
noto): BUY-only PF1.54 (m1=1.27/m2=1.85, n=67, 4/5 finestre) — entrambe
le metà sopra pari. SELL laterale **PF3.34** (n=10) — forte quanto i
flip genuini confermati oggi, stesso trattamento di ML Adaptive
SuperTrend.

**RSI_DIV**: BUY-only PF1.65 (m1=1.41/m2=1.91, n=53, 4/5 finestre).
SELL laterale PF1.36 su **n=21** — il campione laterale più ampio
verificato oggi tra i "nuovi" candidati, moderato ma non trascurabile.

**ICHIMOKU**: entrambi i lati sembrano positivi nel laterale ma con
campioni ridicolmente sottili (n=2 per SELL) — non abbastanza per
qualunque conclusione, resta nella categoria "confermata debole" di
ieri senza essere né promossa né definitivamente rifiutata su questo
fronte specifico.

**TSI_EXTREME**: l'unica dove il filtro di ammissione base fallisce
già — il BUY-only aggregato è sotto pareggio (0.92), quindi il pattern
SELL-laterale (per quanto forte, 3.65) è irrilevante: non c'è nemmeno
un candidato BUY-only da promuovere. Resta rifiutata.

## Verdetto

**BOLLINGER (=RANGE_FADE) e RSI_DIV promosse** a nuove baseline
candidate (BUY-only, 4h, SL1.5/TP4.0, ER+floor 0.3) — stesso livello
di fiducia "genuina ma da confermare con più dati" di ML Adaptive
SuperTrend/STRUCT_REACT iniziale. **ICHIMOKU e TSI_EXTREME restano non
promosse** — la prima per campione insufficiente, la seconda perché
il lato BUY non regge nemmeno in aggregato.

Con queste 2 nuove promozioni più ML Adaptive SuperTrend, il filone
"riapertura verdetti pre-disciplina-laterale" ha prodotto **3 nuove
baseline in una sessione** — merita di essere applicato sistematicamente
a tutto ciò che è stato scartato solo in forma simmetrica prima di
oggi (BJORGUM e CRT restano esclusi: BJORGUM già diagnosticata beta
per-data con metodo diverso ma altrettanto rigoroso, CRT ha un problema
di costi-dominanti indipendente dalla direzione).

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Riverifica Hull Suite e ML Adaptive SuperTrend con BUY-SELL e Laterale (25-08)]]
[[NEXUS EA - Espansione Baseline con Ricetta Variabile (24-08)]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
