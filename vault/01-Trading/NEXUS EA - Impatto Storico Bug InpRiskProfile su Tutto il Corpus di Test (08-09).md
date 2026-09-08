---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, bug, risk-profile, metodo, p0]
created: 2026-09-08
updated: 2026-09-08
---

# NEXUS EA — impatto storico del bug InpRiskProfile su tutto il corpus di test (08/09)

## Perché questa nota

Richiesta dalla sessione cloud dopo aver riletto i diff reali del
08/09: le note step5/step6/step7 di FVG_CONT documentano il bug
`InpRiskProfile`/`InpMinEntryScore` non-`input` nel contesto di UNA
strategia. Questa nota misura lo **scope reale su tutto il progetto**,
incrociando sistematicamente i 150 `.ini` di test con le date di fix:

- **Fix 1** (`InpRiskProfile` diventa `input`): commit `f382c4f`,
  compilato **07/09 21:47:54**.
- **Fix 2** (`InpMinEntryScore` diventa `input`): commit `478cf34`,
  compilato **08/09 01:33:50**.

## Il fatto centrale

**Praticamente ogni test "nudo"/isolato eseguito prima delle 21:47 del
07/09 — la stragrande maggioranza della storia del progetto — ha
girato con `InpMaxTradesPerDay≤12` e `InpMaxDailyDDPct≤5.0%` forzati
da BALANCED**, indipendentemente da cosa dicesse l'.ini. Verificato
incrociando tutti i 150 `.ini` con l'orario reale di esecuzione
(mtime del `.htm` corrispondente): **~115 test** impostavano
esplicitamente `InpMaxTradesPerDay=999999` e/o `InpMaxDailyDDPct=100.0`
per ottenere un trigger davvero "nudo", senza vincoli — e nessuno di
questi ci è mai riuscito prima delle 21:47 del 07/09, perché
`InpRiskProfile` non era `input` e restava sempre `2` (BALANCED)
qualunque cosa dicesse l'.ini.

## Perché non è detto che cambi i verdetti (ma va verificato)

I due cap forzati sono meccanismi diversi con rischio diverso:

**`InpMaxTradesPerDay≤12`** — bindente solo se una strategia genera
più di 12 segnali nello stesso giorno di calendario. Improbabile per
strategie H4/D1 (raramente >1 trade/giorno), **plausibile per le
strategie M15/M5/M30** elencate sotto.

**`InpMaxDailyDDPct≤5.0%`** — bindente ogni volta che la perdita del
giorno (equity vs balance di inizio giornata) supera il 5%, **su
qualunque timeframe**, perché passa per `NXS_CheckProtections()` nel
percorso di apertura primario (`NXS_TryExecuteRC`, non solo nei moduli
reclaim) — congela le nuove aperture per il resto della giornata.
Questo è lo stesso identico meccanismo confermato oggi con 401 blocchi
nel test di regressione SLReclaim.

## Cosa sappiamo per certo (prova diretta, non ipotesi)

**FVG_CONT — impatto trascurabile, dimostrato empiricamente.** Lo
step1 (`InpMaxDailyDDPct=100.0`, doveva essere senza vincoli) e lo
step2 (`InpMaxDailyDDPct=5.0`, vincolo vero) — girati ENTRAMBI sotto
lo stesso bug, quindi entrambi realmente a DD-cap 5% — differiscono di
appena 167 vs 168 trade e $2655 vs $2635. Se il cap 5%/giorno avesse
davvero tagliato molto, questi due non sarebbero quasi identici. Per
FVG_CONT: verdetto sostanzialmente confermato, il bug non ha cambiato
la sostanza.

**`InpMinEntryScore`** (bug indipendente, fix separato) — **solo
FVG_CONT step4/5/6/7** hanno mai tentato di impostarlo diversamente dal
default. Nessun'altra strategia nel corpus storico ha mai provato a
personalizzare il voto-entrata via `.ini` prima di oggi. Blast radius
contenuto, già interamente documentato in
[[NEXUS EA - Step6 Ancora Identico, Bug Indipendente su InpMinEntryScore (08-09)]]
e [[NEXUS EA - Step7 Ancora Identico, la Vera Causa e' NXS_ResolvedEntryThreshold (08-09)]].

## Cosa NON sappiamo ancora — da verificare prima di fidarsi ciecamente

Non ho ricontrollato, test per test, se il cap 5%/giorno o 12
trade/giorno abbia **davvero** tagliato qualcosa in ognuno dei casi
sotto — solo che ne erano tecnicamente esposti. Ordine di priorità per
la riverifica (rischio più alto per primo):

**Rischio più alto — strategie M15/M5/M30, cap 12 trade/giorno
plausibile + cap DD5%/giorno:**
- `SAR` — **tutte le 43 varianti step0-43** (M15). È tra le strategie
  "confermate positive" del vault (PF1.37-1.57) — la ricetta live
  attuale (candle-align H4, in realtà step20+ girano ancora su M15 per
  il segnale) va riverificata prima di fidarsene per un deploy.
- `EMA_PULLBACK` — tutte le varianti (M15), inclusa quella "confermata
  robusta" con walk-forward 4 finestre.
- `PIVOT_WICK` — tutte le 20+ varianti (chiuse negative comunque, ma
  la chiusura andrebbe confermata sotto le condizioni corrette).
- `LEVEL_CONFLUENCE` / `LEVEL_REACTION` (M15) — già chiuse/in dubbio,
  stesso discorso.
- `BAR_UPDN`, `BREAKOUT_ACC` scalp (M15) — chiuse negative, da
  confermare.
- `BOLLINGER` M5/M30 — chiuse negative, da confermare.

**Rischio medio — H4/D1, cap trade/giorno improbabile ma DD5%/giorno
sempre in gioco:**
- `ADX_RSI` (D1) — confermata positiva, PF2.04.
- `MACD` (H4) — confermata positiva, PF1.53.
- `BOLLINGER` H4 — confermata (miglior Sharpe).
- `STRUCT_REACT` (H4) — confermata, PF1.29.
- `FVG_CONT` step1/3/4 (H4) — **verificato trascurabile** (vedi sopra).

## Raccomandazione

Non consiglio di rifare in blocco tutti gli ~115 test — la maggior
parte (H4/D1, bassa frequenza) probabilmente non ha mai toccato i cap.
Ma **prima di usare SAR o EMA_PULLBACK come base per qualunque
decisione di portfolio/capitale reale**, andrebbero ri-verificati con
`InpRiskProfile=0` esplicito ora che funziona davvero — sono le due
strategie a più alto rischio (M15, "confermate positive", già
considerate per il nucleo demo).

## Collegamenti
[[NEXUS EA - A2+A3+A4 Verificati con Test di Regressione, Storia Completa (08-09)]] · [[NEXUS EA - Bug InpRiskProfile, il Preset BALANCED Sovrascriveva Silenziosamente i Parametri Custom (07-09)]] · [[NEXUS EA - Piano di Test Master, Stato per Ogni Strategia e Coda Prioritaria (03-09)]] · [[MOC - Trading]]
