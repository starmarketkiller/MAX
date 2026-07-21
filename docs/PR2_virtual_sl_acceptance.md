# PR 2 — Virtual SL: acceptance test (agente desktop)

Branch `feature/pr2-virtual-sl` (stacked su PR1). Questo ambiente non ha MetaEditor:
compilazione ed esecuzione a carico del desktop, su **HEAD del branch**.

## 0. Compilazione
- Compilare `NEXUS_EA_v2.mq5` (build 5833): **0 errori, 0 warning nuovi**.
  File toccati: `NXS_EdgeAdaptive.mqh`, `NXS_Globals.mqh`, `NXS_Execution.mqh`,
  `NXS_ReusePerformancePack.mqh`, `NEXUS_EA_v2.mq5`.
- Non toccare il terminale dello sweep.

## 1. Self-test logico (senza broker)
Chiamare `NXS_EA_VirtSL_SelfTest()` (da uno script o una chiamata temporanea in
OnInit di un chart di prova). Atteso nel log: **tutti PASS** — hard SL invalido,
transizioni ARMED→…→CONFIRMED, CONFIRMED mai da DONE/PLACED, backoff, escalation
non terminale, OBSERVE non chiude, due pending + fill inverso, Register idempotente.
(La logica della macchina a stati è già stata verificata con un port deterministico:
13/13.)

## 2. Non-regressione OFF == baseline (obbligatorio)
`InpVirtSL_Mode = OFF`. Strategy Tester, stesso set/periodo di `d0a94f3`:
- nessun file `virtsl_*.csv` creato;
- SL inviato al broker = SL logico (identico alla baseline);
- trade count, PF, DD, ordine operazioni **identici** a `d0a94f3`.

## 3. OBSERVE (shadow)
`InpVirtSL_Mode = OBSERVE`. Verificare nel log: `ARMED` alla registrazione dopo il
fill, `TRIGGERED` al tocco del livello logico, **nessuna** `CLOSE_REQUEST`; il broker
chiude al suo SL logico. Nessun cambiamento di comportamento operativo vs OFF.

## 4. EXECUTE — ciclo completo
`InpVirtSL_Mode = EXECUTE`, su GOLD:
1. **register dopo fill**: aprire un trade classic → `[NXS VirtSL] ARMED pos=… virt=… hardSL=…`; lo SL sul broker è l'hard SL largo (≈4×ATR), non quello logico.
2. **trigger + chiusura reale**: al tocco del livello logico → `TRIGGERED` → `CLOSE_REQUEST` → posizione chiusa davvero → `CONFIRMED via=LEDGER_FINAL` (o POSITION_GONE).
3. **institutional (NXR)**: ripetere con una strategia sul percorso NXR → stesso ciclo.
4. **retry/escalation**: (se riproducibile con requote/mercato chiuso) tentativi con backoff, poi `[ALERT] ESCALATED`, retry rallentato che continua fino a chiusura confermata.

## 5. Restart / riconciliazione
Con EXECUTE: aprire un trade (ARMED), riavviare il terminale → al boot
`[NXS VirtSL] restore: N armati…` e il record riprende. Provare anche il riavvio
con un record in TRIGGERED/CLOSE_REQUESTED (es. chiudere il terminale subito dopo un
trigger): al boot il record va riverificato senza doppia chiusura; una posizione
chiusa offline **non** deve essere ri-richiesta (scarto via ledger FINAL / position gone).
Verificare che `virtsl_<login>_<magic>.csv` non venga letto se account/magic diversi.

## 6. Split
Con EXECUTE e split attivo: una chiusura parziale del padre **non** deve confermare
né cancellare il Virtual SL; il record resta valido sul volume residuo.

## Limiti dichiarati
- grid/pyramid restano senza stop (aprono con SL=0): fuori scope PR2 (→ PR3/PR4).
- In EXECUTE lo SL mostrato sul broker è l'hard SL largo (osservabilità).
- Se il virtual close fallisce a ripetizione, la perdita massima è l'hard SL 4×ATR.
