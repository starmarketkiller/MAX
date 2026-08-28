---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, session, scalp, m15, m30, negativo]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Famiglia sessione e SCALP su M15/M30 (24/08)

## Perché

Su richiesta dell'utente: le strategie a sessione fissa (JUDAS_SWING,
SILVER_BULLET, NY_REVERSAL, AMD_REVERSAL, PO3, WEEKLY_EXP) e le SCALP_*
sono state testate finora solo su 4h/1h con un hold fino a 200 barre e
target multi-ATR — una scala sbagliata per una tesi che si esaurisce in
ore, non giorni. `session_scalp_baseline_24-08.py`: M15/M30 (TF nativo),
SL/TP più stretti (1.0/3.0 ATR), uscita forzata a fine giornata (stesso
campo `date` del motore) se né SL né TP scattano prima. Nessun filtro ER
(la tesi è il timing di sessione, non la forza del trend).

## Risultato: negativo su tutta la linea, tre assi diversi provati

**13 strategie × 2 TF (M15/M30) = 26 combinazioni, zero baseline
profittevoli.** Retail PF 0.24-0.55 ovunque, mai vicino a pareggio. ECN
0.49-0.92, sempre sotto 1. Firma da cost-dominance classica (gap
retail/ECN ~2x su quasi tutte).

**Verificato non un problema di stop troppo stretto**: riprovato SL1.5/
TP4.5 e SL2.0/TP6.0 (lo stesso ordine di grandezza che funziona su 4h)
sui 3 candidati più vicini al pareggio (NY_REVERSAL/SILVER_BULLET/
JUDAS_SWING, M30) — migliora (JUDAS_SWING retail 0.24→0.59) ma **resta
sempre sotto 1.0** anche con lo stop più largo. Tre assi indipendenti
provati (TF, larghezza stop, timing di uscita) — nessuno risolve.

## Conclusione

La famiglia sessione/AMD e le SCALP_* non hanno un edge baseline
dimostrabile su questo storico con nessuna delle ricette provate oggi —
coerente con la debolezza già osservata per questa famiglia in sessioni
precedenti (campioni sempre sottili, PF sempre marginale su ogni TF
tentato in passato). Non escluso che un ingrediente ancora diverso
(entry più selettiva, un filtro di contesto specifico per il timing di
sessione invece di ER/floor) possa aiutare, ma i tre assi più ovvi
(scala TF, ampiezza stop, durata dell'uscita) sono ora chiusi.

## Prossimi passi aperti

- Non provato: filtro sul giorno della settimana o sulla news
  (InpNewsFilter esiste già nel motore MQL5, mai collegato a questo
  test Python).
- Non provato: entry a limite invece che a mercato (potrebbe cambiare la
  qualità del fill su mosse intraday strette, dove lo slippage pesa di
  più).
- Bilancio giornata: **14 baseline totali trovate e verificate**
  (invariato da prima di questo test) — nessuna aggiunta da questa
  famiglia.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Espansione Baseline con Ricetta Variabile (24-08)]]
