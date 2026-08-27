---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, weekly-exp, entry, trailing, risk-size, mql5]
created: 2026-08-26
updated: 2026-08-26
---

# NEXUS EA — WEEKLY_EXP: entry raffinato su M15 + trailing strutturale (26/08)

## Il problema di partenza

Backtest reale a tick sull'intero portafoglio v3.0 (Nov 2025-Ago 2026,
conto $1000 USD): 195 trade, PF1.02, DD 34%. Diagnosi via
`[NEXUS BLOCK]` diagnostics: **RISK_SIZE blocca ~94% dei decision
tick** — al lotto minimo (0.01), il rischio in $ di molte strategie a
stop nativo largo (WEEKLY_EXP: mediana $37-38, cioè 3.7-3.8% di un
conto $1000, ma con outlier ben oltre l'8% di `InpMaxRiskAtMinLotPct`)
supera il tetto e l'ordine viene rifiutato del tutto, non solo ridotto.
Con l'obiettivo esplicito dell'utente di poter partire anche con
€500, il problema si aggrava ulteriormente.

Recuperata una ricerca precedente ([[NEXUS EA - Stop Strutturale M5 su
Segnali H1 (16-08)]]) che aveva già escluso due varianti: stop stretto
+ target fisso largo (R:R esplode, streak di perdite 150+) e stop
stretto + target fisso proporzionalmente scalato (PF crolla 0.71-1.18,
stessi costi-dominanti di CRT). **Variabile mai testata**: stop stretto
+ breakeven/trailing invece di un target fisso, per lasciare correre i
winner senza il vincolo di un obiettivo predefinito.

## Metodologia nuova: LTF-refined entry + trailing strutturale

1. Il trigger H4/settimanale della strategia (invariato) non genera più
   subito il segnale, ma arma uno stato di attesa.
2. Su M15 si aspetta fino a 8 barre una candela di reazione genuina —
   stessa identica formula di `NXS_HasPriceReaction` (pin bar: wick >
   1.5×body e > 0.5×range; oppure chiusura direzionale).
3. Entry con stop stretto ancorato all'estremo di quella candela M15
   ±0.2×ATR(M15) — molto più vicino del target fisso originale.
4. Gestione: breakeven a 1.0R, poi trailing strutturale (minimo/massimo
   della candela M15 precedente ±0.3×ATR) attivato solo dopo 1.5R di
   profitto — i winner corrono invece di fermarsi su un target fisso.

## Primo tentativo (DISP_REBAL) — fallito

`disp_rebal_ltf_entry_structural_trail_26-08.py`: PF nativo 0.86 →
0.16-0.47 con la nuova gestione, streak di perdite peggiorato (9→24).
Causa: lo stop nativo di DISP_REBAL era già stretto (mediana $7.14) —
non era un vero candidato "stop largo", e stringerlo ulteriormente lo
ha spinto nella stessa trappola di costi-dominanti già vista su CRT.
**Lezione applicata**: serve una strategia con stop nativo genuinamente
largo per avere margine di miglioramento reale.

## Secondo tentativo (WEEKLY_EXP) — riuscito

`weekly_exp_ltf_entry_structural_trail_26-08.py`, motore Python con i
gate reali del codice (incluso RISK_SIZE). Stop nativo di WEEKLY_EXP
genuinamente largo (mediana $37-38, da `1.5×ATR(D1)`).

Con filtro CHOCH (ricetta verificata, campione più piccolo ma più
pulito):

| Versione | n | PF | medRiskDist | maxLossStreak |
|---|---|---|---|---|
| Nativo | 16 | 1.18 | $38.22 | 4 |
| LTF-refined + trailing | 15 | **1.64** | **$3.51** | 4 (invariato) |

Rigetti RISK_SIZE su conto $500: 37.5% → 6.7%. Senza filtro CHOCH
(campione più ampio, n=35-36): nativo PF0.84 → nuovo PF2.99, streak
6→3 — risultato ancora più forte ma meno rigorosamente filtrato, preso
come conferma di direzione più che come numero da citare.

## Porting su MQL5

`NXS_Strat_WeeklyRangeExp()` riscritta come state machine a 2 stadi
(`NXS_Strategies_Institutional.mqh`): stage 1 invariato (trigger
H4/weekly con BOS+CHOCH+posizione sul mid weekly), ma ora arma
`g_wexpState` invece di ritornare subito un segnale; stage 2 aspetta
la reazione M15 e genera l'entry con stop stretto.

Gestione dedicata in `NXS_WeeklyExpManage.mqh` (nuovo file): breakeven
1.0R + trailing strutturale 1.5R, con rischio iniziale tracciato per
ticket (necessario perché dopo il primo spostamento dello stop
`POSITION_SL` non riflette più il rischio originale). Agganciata nel
tick loop di `NEXUS_EA_v2.mq5` subito dopo `NXS_TrailATR()`.
`NXS_Profile_TrailForceOff("WEEKLY_EXP")` ora ritorna `true` per
escluderla dal trailing ATR generico (altrimenti le due gestioni
litigherebbero sullo stesso stop).

Compilato pulito (0 errori, i soliti 2 warning preesistenti non
correlati), sincronizzato su entrambi i terminali, commit e push su
`claude/export-advisor-nexus-migrate-htnz34`.

**Ancora da fare**: validazione via MT5 Strategy Tester (selector=32,
isolato) per confrontare l'output MQL5 reale contro i numeri Python;
se il risultato regge, estendere lo stesso schema a SH_BMS_RTO (D1,
PF1.49 nativo) e SMS_BMS_RTO (D1, PF0.92 nativo), altri due candidati a
stop nativo largo.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Stop Strutturale M5 su Segnali H1 (16-08)]]
[[NEXUS EA - CRT Costi-Dominanti Confermati, Elliott H4 BUY-only Attivata (25-08)]]
