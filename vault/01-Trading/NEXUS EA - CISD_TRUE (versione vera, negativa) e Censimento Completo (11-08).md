---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, cisd, censimento, walk-forward]
created: 2026-08-11
updated: 2026-08-11
---

# CISD_TRUE: il tentativo "come per CRT" che questa volta non regge (11/08)

Richiesta esplicita dell'utente: guardare la storia git di ogni
strategia per vedere se una versione scartata nascondeva qualcosa di
buono (come CRT), e provare piccoli cambiamenti d'ingresso sulle
strategie deboli.

## La pista trovata

`git log` su `server/backtest.py` e MQL5 rivela che **THREE_BAR_DELIVERY_
BREAK (ex CISD)** ha una storia quasi identica a CRT: sul sito, la
versione "vera" (displacement + ultima candela di delivery OPPOSTA +
sweep di liquidita' + reclaim, SL/TP hardcoded) dava **PF 5.95**, ma
**non scattava mai** nel test live (0 setup su 1067) - sostituita ovunque
(sito, MQL5, Python) con una versione molto piu' semplice (3 candele
dello stesso segno + rottura del loro estremo), quella tuttora in uso e
debole (OOS PF 1.49 ma solo 24 trade, walk-forward 2/5 fragile).

## Verifica: perche' non scattava?

Diagnostica di frequenza (`cisd_real_diagnostic.py`) sullo storico
ampliato (2019-2026, molto piu' lungo del test live che dava 0/1067):
la logica vera SPARA regolarmente - 2236 segnali su 15m, 631 su 1h, 265
su 4h. Il collo di bottiglia e' il flag di sweep di liquidita' (solo
~17% dei displacement bar hanno un vero sweep PDL/EQL/AsiaLow), non
un'assenza totale di setup come sul test live originale (probabilmente
una finestra troppo corta).

## Il test onesto: negativo

Registrata come strategia vera e propria (`CISD_TRUE` in
`server/backtest.py`, riusa `_sweep_ext_at()` - lo stesso rilevatore di
sweep fedele gia' usato da TURTLE_SOUP/JUDAS_SWING), testata con
`run_backtest()` (stesso motore di esecuzione di CRT, non una
reimplementazione parallela) IS/OOS + walk-forward a 5 finestre su
15m/1h/4h:

| TF | IS PF/n | OOS PF/n | Walk-forward | Verdetto |
|---|---|---|---|---|
| 15m | 0.84/1145 | 0.97/668 | 0.75\|0.91\|0.98\|1.04\|0.92 (1/5) | negativo |
| 1h | 0.91/287 | 0.92/197 | 0.71\|1.01\|1.04\|1.01\|0.82 (3/5, marginale) | negativo |
| 4h | 0.77/127 | 2.03/75 | 1.04\|0.97\|0.5\|1.67\|2.56 (3/5, erratico) | non robusto |

A differenza di CRT (dove un'implementazione scorretta nascondeva un
edge reale, 15/15 finestre positive), qui l'idea era ben motivata e
concettualmente vicina a CRT (sweep + reclaim + target opposto), ma il
test onesto non conferma un vantaggio: nessun TF regge, il 4h ha un
singolo split IS/OOS ingannevole (esattamente il pattern gia' visto con
BREAKOUT_ACC su 1d) smentito dal walk-forward. **Non promossa.** Resta
registrata come EXPERIMENTAL/research-only per la cronaca (come
STAGE1/STAGE3 di MALAYSIAN_SNR).

Lezione: non ogni "versione scartata" e' una CRT nascosta - a volte la
versione semplice sopravvissuta e' davvero la scelta migliore
disponibile, e vale la pena verificarlo comunque prima di scartare
l'ipotesi per pigrizia.

## Censimento completo: 50 strategie, stesso metodo

Su richiesta dell'utente ("quali sono i dati per le strategie che
abbiamo, quali tenute fuori"): un solo censimento coerente
(`full_census.py`) - flat baseline SL1.5x/TP3.0x, no HTF/BE, stesso
storico ampliato, IS(60%)/OOS(40%), TF di profilo dove esiste altrimenti
il miglior TF gia' trovato in sessioni precedenti - invece di numeri
raccolti da script diversi in momenti diversi.

**Nucleo (16, gia' in NXS_Profile_Enabled)**: BREAKOUT_ACC, TURTLE_SOUP,
MACD, LONDON_BO, FVG_MIT, LIQ_SWEEP, AMD_CONT, FVG_CONT, TSI, ADX_RSI,
SAR, EMA_PULLBACK, THREE_BAR_DELIVERY_BREAK, LDN_REVERSAL, AMD_REVERSAL,
CRT.

**Escluse (34)**: BB_SQUEEZE, BJORGUM, BOLLINGER, DISP_REBAL,
FVG_CONT_V2, ICHIMOKU, IFVG, JUDAS_SWING, LIQ_VOID, MALAYSIAN_SNR,
MALAYSIAN_SNR_BREAKOUT, MALAYSIAN_SNR_V2_RETEST, MALAYSIAN_SNR_V2_STAGE1,
MALAYSIAN_SNR_V2_STAGE3, NY_REVERSAL, OB_MIT, ORDER_BLOCK,
ORDER_BLOCK_V2, OTE_CONT, OTE_CONT_V2, PO3, RANGE_FADE, RSI_DIV,
SCALP_BB_FADE, SCALP_EMA, SCALP_RANGE_BRK, SCALP_RSI_SNAP, SH_BMS_RTO,
SH_BMS_RTO_V2, SILVER_BULLET, SILVER_BULLET_V2, SMS_BMS_RTO,
STRUCT_REACT, WEEKLY_EXP.

Dati completi (IS/OOS PF, n trade, drawdown) per tutte e 50: vedi
`full_census.py` / `/tmp/full_census.log` e l'artefatto pubblicato in
chat. Candidati piu' deboli nel nucleo per il prossimo giro di piccoli
cambiamenti d'ingresso: **TSI** (OOS 0.71/39, unica del nucleo sotto
pareggio in OOS), **TURTLE_SOUP** (OOS 0.96/398, quasi pareggio su
campione enorme), **THREE_BAR_DELIVERY_BREAK** (appena testato, vedi
sopra).

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Fase C Recovery Baseline e Rischio Flottante (11-08)]] ·
[[NEXUS EA - Riverifica su Storico Ampliato (11-08)]]
