---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, escluse, molteplicità, bugfix]
created: 2026-08-11
updated: 2026-08-11
---

# Strategie escluse dal nucleo — analisi una-ad-una (11/08)

Richiesta esplicita dell'utente: applicare alle 34 strategie escluse lo
stesso metodo usato per il nucleo (vault prima, poi git, poi test sul
motore vero), una alla volta, cercando miglioramenti reali.

## 1. MALAYSIAN_SNR_BREAKOUT — chiuso, nessun miglioramento

Il vault (nota MALAYSIAN_SNR Porting Tier 1) aveva già la risposta: IS
37 trade PF 0.74 (in perdita), OOS 32 trade PF 1.88. Con la disciplina
IS-blind di tutta la sessione questa configurazione non verrebbe mai
scelta — il numero attraente è solo sull'OOS, l'IS dice il contrario.
Stesso pattern già visto con BREAKOUT_ACC su 1d. Nessun test aggiuntivo
necessario, il vault aveva già chiuso la domanda.

## 2. Le varianti "_v2" — 3 bug reali trovati e corretti

Git log (`2a5c2f1`) rivela che le 5 varianti "_v2" (portate da un brief
esterno, "Decomposizione Edge Strategie NEXUS") avevano 3 bug REALI
documentati e mai corretti (portati fedelmente, "non corretti
silenziosamente"), confermati a 0 trade:

- **SILVER_BULLET_V2**: check "FVG fresh" auto-referenziale — la barra
  che definisce il bordo del gap veniva confrontata contro se stessa
  (sempre vera), quindi `fresh` era sempre falso.
- **FVG_CONT_V2**: check "EntryAt50Pct" auto-referenziale — stesso
  meccanismo (`fvg_hi` definito come la barra corrente, sempre sopra il
  proprio centro per costruzione).
- **OTE_CONT_V2**: `fib618`/`fib705` invertiti sul lato SELL —
  intervallo impossibile (soglia superiore più bassa di quella
  inferiore), 0 trade SELL garantiti.

### Corretti e testati (storico ampio, walk-forward a 5 finestre)

| Strategia | TF | IS→OOS | Walk-forward | Verdetto |
|---|---|---|---|---|
| SILVER_BULLET_V2 | 15m | 2.19/22 → 1.52/13 | erratico, campioni 3-13/finestra | **troppo sottile per giudicare** |
| FVG_CONT_V2 | 4h | 1.11/50 → 1.73/42 | 3/5, oscilla 0.63-2.32 | **reale ma non ancora robusto** |
| OTE_CONT_V2 | tutti i TF | 0 trade anche dopo il fix | — | **strutturalmente morto** (lato BUY già quasi tautologico di suo, indipendente dal bug SELL) |

Nessuno dei tre è pronto per il nucleo, ma **il fix era comunque
corretto da fare**: passare da "0 trade, dead code" a "segnali reali,
seppur deboli" è di per sé un miglioramento onesto rispetto a codice
rotto ereditato da un brief esterno mai verificato. FVG_CONT_V2 è il più
promettente dei tre — da tenere d'occhio, stesso status di
TURTLE_SOUP_CHOCH (promettente, non confermato).

## Prossimi passi
Restano da coprire: BB_SQUEEZE, BJORGUM, BOLLINGER, DISP_REBAL, ICHIMOKU,
IFVG, JUDAS_SWING, LIQ_VOID (proxy dichiarato di FVG_CONT, probabilmente
da saltare), MALAYSIAN_SNR, MALAYSIAN_SNR_V2_RETEST/STAGE1/STAGE3 (già
ampiamente studiate in sessione), NY_REVERSAL, OB_MIT, ORDER_BLOCK,
ORDER_BLOCK_V2, OTE_CONT (v1), PO3, RANGE_FADE (proxy di BOLLINGER),
RSI_DIV, SCALP_BB_FADE/EMA/RANGE_BRK/RSI_SNAP, SH_BMS_RTO, SH_BMS_RTO_V2,
SILVER_BULLET (v1), SMS_BMS_RTO, STRUCT_REACT, WEEKLY_EXP.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - CISD_TRUE (versione vera, negativa) e Censimento Completo (11-08)]] ·
[[NEXUS EA - MALAYSIAN_SNR Porting Tier 1 (Specifica Tecnica)]]
