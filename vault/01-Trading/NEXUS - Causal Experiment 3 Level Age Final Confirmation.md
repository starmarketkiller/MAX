# NEXUS Causal Research — Experiment 3: Final Confirmation of Level Age

Segue [[NEXUS - Causal Experiment 2 Friday Level Age Confirmation]] (commit `baa9fc2`). Ultimo test sul Level Age prima della decisione finale. Friday **non rianalizzato** (REFUTED, archiviato definitivamente in Experiment 2). Nessuna nuova feature, nessuna nuova combinazione, nessuna soglia modificata.

## Hypothesis congelata

**H2**: `OLD_LEVEL` ha probabilità maggiore di `PLUS_1R_FIRST` rispetto a `YOUNG_LEVEL`.
**Soglia congelata**: **20700 secondi (5.75 ore)** — da Experiment 1, non ricalcolata.

## 1. Dataset — periodo, provenienza, qualità dati

**Periodo**: 2026-01-02 → 2026-03-20 (~2.5 mesi) — indipendente sia da Experiment 1 (2026-06-01→08-25) sia da Experiment 2 (2026-04-01→06-01), precedente a entrambi come da preferenza del task.

**Provenienza dati (dichiarata per trasparenza)**: un primo tentativo di eseguire l'intero trimestre 2026-01-01→04-01 in un'unica run Model=1 non ha raggiunto il completamento pulito ("final balance") entro il budget di sessione — stesso tipo di limite ambientale già documentato nelle fasi precedenti per run lunghe. La run è stata terminata, ma il log conferma che la simulazione interna aveva **già completato** l'elaborazione fino al 2026-03-20 (1632 eventi `[LEVELENGINE][EVENT]` ben formati, sequenza `level_id`/`event_id` continua e senza reset) prima dell'arresto — solo la fase finale di chiusura/report non è stata raggiunta. È stato usato **solo questo prefisso completo e ben formato** (fino all'ultimo evento CREATE valido, 2026-03-20), scartando implicitamente qualunque dato oltre quel punto. Verificato: nessun evento troncato/malformato nel prefisso usato.

Tre run più corte (Gennaio, Febbraio, Marzo separate, ~30gg ciascuna) sono state eseguite come sonde di affidabilità PRIMA di scoprire il prefisso continuo utilizzabile — hanno confermato che ogni singolo mese individualmente completa senza problemi (150-161s ciascuna), ma non sono state usate per il dataset finale per evitare reset artificiali di stato a ogni confine di 30 giorni; il prefisso continuo di 2.5 mesi è metodologicamente preferibile (nessun confine artificiale) ed è quello riportato sotto.

**Metodologia**: identica a Experiment 1/2 — eventi WICK sweep (Model=1, `InpLevelRegistry_WickReadPath=true`), label da barre M1 esportate offline (`NXS_ResearchExportBars.mq5`), 1R = 25 pip simmetrico, ambiguous esclusi, censored separati, nessuna imputazione.

| Metrica | Valore |
|---|---|
| Eventi sweep totali | **186** |
| Risolti | **170** |
| Censored | **0** |
| Ambiguous same-bar (esclusi) | **16** |
| Duplicati/incoerenze | **0** |

## 2. Analisi unica — OLD vs YOUNG (soglia congelata)

| | n | successi | rate | CI95 |
|---|---|---|---|---|
| OLD (≥20700s) | 93 | 40 | **0.430** | [0.334, 0.532] |
| YOUNG (<20700s) | 77 | 37 | **0.481** | [0.373, 0.590] |

- **Uplift assoluto (OLD − YOUNG): −0.050**
- **Uplift relativo: −10.5%**
- CI95 differenza (OLD−YOUNG): [−0.201, 0.100]

**La direzione è opposta a quella ipotizzata** (H2 prevede OLD > YOUNG; qui OLD < YOUNG).

## 3. Stabilità temporale (prima metà vs seconda metà)

| | n | OLD rate | YOUNG rate | uplift |
|---|---|---|---|---|
| Prima metà | 85 | 0.396 (n=48) | 0.459 (n=37) | **−0.064** |
| Seconda metà | 85 | 0.467 (n=45) | 0.500 (n=40) | **−0.033** |

A differenza di Experiment 2 (dove l'effetto si invertiva tra le due metà), qui **l'uplift negativo è stabile in entrambe le metà** — non è un artefatto di una sola porzione del periodo, è consistente lungo tutto il dataset indipendente.

## 4. Robustness — BUY/SELL

| | n | OLD rate | YOUNG rate | uplift |
|---|---|---|---|---|
| BUY | 73 | 0.486 (n=35) | 0.474 (n=38) | +0.012 (~nullo) |
| SELL | 97 | 0.397 (n=58) | 0.487 (n=39) | **−0.091** |

Nessuna inversione "distruttiva" nel senso di un lato fortemente positivo che nasconda un lato fortemente negativo aggregato — BUY è sostanzialmente nullo, SELL è chiaramente negativo. Nessun supporto per H2 in nessuno dei due sottogruppi.

## 5. Decision gate

| Criterio per PROMISING_HYPOTHESIS | Esito |
|---|---|
| OLD > YOUNG sul nuovo periodo | ❌ (OLD < YOUNG) |
| Effetto materialmente positivo | ❌ (negativo, −0.050) |
| Stessa direzione in entrambe le metà temporali | N/A (la direzione è negativa in entrambe, ma è l'opposto di quella richiesta) |
| BUY/SELL non mostrano inversione distruttiva | ✅ (ma irrilevante: nessun lato supporta H2) |
| Sample adeguato | ✅ (93/77) |
| Nessun problema causale/data quality | ✅ |

**Nessun criterio chiave per la promozione è soddisfatto.** La direzione è chiaramente e stabilmente opposta a H2 su questo terzo periodo indipendente.

## Classificazione H2

### **REFUTED**

Non `INCONCLUSIVE_FINAL`: a differenza di Experiment 2 (dove l'effetto si invertiva internamente, giustificando l'incertezza), qui la direzione negativa è **stabile** in entrambe le metà temporali e in entrambi i lati BUY/SELL (nessuno dei due la supporta) — è una confutazione pulita, non un'ambiguità.

## Riepilogo dei 3 esperimenti sul Level Age

| Esperimento | Periodo | n | OLD rate | YOUNG rate | Direzione |
|---|---|---|---|---|---|
| Exp1 (discovery) | giu-ago 2026 | 190 | 0.578 | 0.511 | + |
| Exp2 (conferma 1) | apr-giu 2026 | 135 | 0.552 | 0.429 | + (ma instabile internamente) |
| Exp3 (conferma finale) | gen-mar 2026 | 170 | 0.430 | 0.481 | **−** |

Su 3 periodi indipendenti, la direzione dell'effetto **non è riproducibile**: positiva in 2 (di cui una instabile), negativa e stabile nel terzo. Il pattern osservato in Experiment 1 non regge un test di conferma robusto.

## Verdict finale

### **LEVEL_AGE_REJECTED**

Il filone di ricerca causale **WICK Sweep v1 è formalmente chiuso per assenza di feature predittive robuste**: né Friday (REFUTED in Experiment 2) né Level Age (REFUTED in Experiment 3, dopo un risultato INCONCLUSIVE in Experiment 2) sopravvivono a un test di conferma su dati indipendenti. Delle feature originariamente disponibili in Experiment 1 (direction, session, hour, day of week, level age, touch count, penetration), nessuna produce un segnale che generalizzi in modo affidabile oltre il campione di discovery.

WICK_SWEEP_REV resta, come sempre dichiarato, una **negative research baseline** — non promossa a strategia, non ottimizzata, legacy invariato. Nessuna implementazione derivata da questi risultati.
