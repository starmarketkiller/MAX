---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, z-score-breakout, mql5, correzione, trailing]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — Correzione: il trailing di Z_SCORE_BREAKOUT non si traduce così com'è in MQL5 (25/08)

## Perché

Tentativo di applicare al codice MQL5 già in produzione (`NXS_Strat_ZScoreBreakout`)
il miglioramento trovato ieri (trailing 3.0×ATR, PF1.35→1.38 — vedi
[[NEXUS EA - Ottimizzazione Z_SCORE_BREAKOUT (24-08)]]). Prima di
scrivere codice, verificato come il motore live gestisce davvero il
trailing: `NXS_TrailingATR.mqh` sposta solo lo **SL**, il **TP resta un
ordine fisso** al prezzo originale (`NXS_PM_ProposeModify(t, newSL,
curTP, ...)` — `curTP` non cambia mai). Il backtest di ieri, invece,
usava un chandelier **puro senza TP** (il prezzo decide quando finisce
il movimento) — due meccanismi diversi, non lo stesso ingrediente.

## Verifica: con il TP fisso ancora attivo, il trailing non aiuta

Ricreato l'esatto scenario ibrido che girerebbe davvero in produzione se
aggiungessi solo una riga a `NXS_Profile_TrailK` (SL-strutturale-M5 +
overlay trailing con soglia di attivazione 1.0×ATR come da default del
motore + **TP fisso 4.0×ATR ancora vivo come tetto**):

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| Baseline nota (nessun trailing, solo TP fisso) | 1.35 (1.37/1.33) | 4/5 | 524 |
| Ibrido: trail 2.0×ATR + TP4.0 ancora attivo | 1.32 (1.19/1.46) | 4/5 | 525 |
| Ibrido: trail 2.5×ATR + TP4.0 ancora attivo | 1.34 (1.21/1.47) | 4/5 | 525 |
| Ibrido: trail 3.0×ATR + TP4.0 ancora attivo | 1.34 (1.24/1.44) | 4/5 | 525 |
| **Chandelier puro (nessun TP), trail 3.0×ATR — il test di ieri** | **1.40 (1.26/1.56)** | 4/5 | 526 |

Con il TP fisso ancora come tetto, il trailing è **piatto o
leggermente peggiorativo** (1.32-1.34 contro 1.35 baseline) — il
miglioramento di ieri **dipende dalla rimozione del TP**, non
dall'aggiunta del trailing di per sé. Semplicemente aggiungere
`NXS_Profile_TrailK("Z_SCORE_BREAKOUT") = 3.0` al codice attuale (che
tiene ancora `s.tpPrice = entry ± 4.0*atr` come ordine fisso in
`NXS_Strat_ZScoreBreakout`) **non avrebbe replicato il miglioramento
trovato ieri** — sarebbe stata una modifica basata su un confronto non
equivalente.

## Perché non ho proceduto a modificare il codice

Per ottenere davvero il miglioramento servirebbe **rimuovere il TP
fisso** dalla logica della strategia (lasciare che il trailing SL sia
l'unico meccanismo di uscita) — un cambiamento di comportamento più
consequenziale del previsto: cambia il profilo di rischio/rendimento
di una strategia già in produzione (profitto potenzialmente maggiore
ma anche restituito parzialmente prima che il trail più largo lo
protegga), e non posso compilare/testare il codice MQL5 in questo
ambiente per verificare che la modifica sia corretta prima che tocchi
un account reale. Coerente con il principio di non prendere decisioni
consequenziali e difficili da annullare su sistemi live senza
conferma esplicita: **non ho modificato il codice**, ho fermato qui e
documentato la scoperta.

## Verdetto

**Nessuna modifica al codice MQL5 in questo turno.** La scoperta di
ieri resta valida come *risultato di ricerca* (chandelier puro batte
il target fisso), ma la sua applicazione al motore live richiede una
decisione esplicita dell'utente: rimuovere il TP fisso di
Z_SCORE_BREAKOUT (rischio maggiore di dare indietro profitto prima che
il trail lo protegga, ma upside potenzialmente più alto) oppure
lasciare la strategia com'è. Non è una semplice "porta il trailing nel
codice" come sembrava ieri.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Ottimizzazione Z_SCORE_BREAKOUT (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
