---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, decision, comportamento, breaking-change]
created: 2026-07-25
updated: 2026-07-25
---

# DEC — cambi di comportamento dopo la remediation

**Data:** 25/07/2026 · **Stato:** attiva · **Branch:** `claude/file-review-complete-rwq562`

Elenco dei cambiamenti che **alterano numeri o comportamento osservabile**. Vanno
letti prima di confrontare qualsiasi risultato nuovo con uno vecchio, e prima di
allarmarsi vedendo l'EA fare cose che prima non faceva.

---

## Cambiano i NUMERI dei backtest

### 1. Parità tester/live delle protezioni — default **attivo**

`InpTesterProtectionParity = true`. Prima il tester disattivava in blocco pausa
giornaliera, ESL, DPT, AutoClose **e** i cap di conto (DD giornaliero, trade/giorno,
concorrenza, margine, anti-revenge).

**Conseguenza diretta:** i backtest da qui in avanti produrranno **meno trade e
curve diverse** rispetto a tutti quelli passati. Non è una regressione — è che
prima si stava ottimizzando un sistema *senza i vincoli che poi lo governano in
reale*. Il confronto con i risultati storici non è più valido.

Per riprodurre un risultato vecchio: `InpTesterProtectionParity = false`. Ma quei
numeri non descrivono il comportamento reale.

### 2. La R non viene più inventata

Un trade il cui rischio iniziale non è ricostruibile è ora **escluso** dalle
statistiche in R. Prima diventava +1R o −1R a seconda del segno.

**Conseguenza:** expectancy in R, win rate in R e ranking per strategia cambieranno,
e il numero di trade nel campione statistico può scendere. I valori nuovi sono
quelli corretti; i vecchi includevano trade il cui R era fabbricato.

Nel log compare `rischio iniziale ignoto — trade ESCLUSO dalle statistiche in R`.
Se compare **spesso**, è un segnale da indagare: significa che molti ingressi non
registrano il proprio budget di rischio.

### 3. Obiettivo di ottimizzazione composito

`OnTester` non restituisce più il solo profit factor. Ora: zero sotto 30 trade,
zero se il drawdown supera il 35%, zero con aspettativa negativa; altrimenti
`PF × √(recovery factor) × penalità sul drawdown`.

**Conseguenza:** le ottimizzazioni sceglieranno insiemi di parametri **diversi** da
prima — non più quelli con pochi trade fortunati e drawdown insostenibili.

---

## Cambia il comportamento in ESECUZIONE

### 4. L'EA rifiuta i conti non-hedging

Su un conto netting `OnInit` ritorna `INIT_FAILED`. Il modello "una posizione = un
trade logico" non regge sui flip di direzione: P/L, R e conteggi diventerebbero
silenziosamente falsi. Prima era solo una nota nei commenti.

### 5. Le protezioni di conto chiudono TUTTO il conto

`InpProtScopeAccountWide = true` (default). ESL, DPT e ruin chiudono ora **tutte**
le posizioni NEXUS del conto, non solo quelle del simbolo del grafico.

⚠️ **Se fai girare più istanze che si dividono deliberatamente lo stesso conto per
simbolo, mettilo a `false`** — altrimenti l'istanza su XAUUSD chiuderà anche le
posizioni di quella su BTC.

### 6. Baseline del drawdown giornaliero: equity, non bilancio

Il flottante ereditato dalla notte non consuma più (né regala) limite di rischio
prima che la giornata cominci. Il DD giornaliero misurato è ora quello prodotto
**da oggi**.

### 7. Nuovi motivi di blocco all'apertura

Non sono errori: sono gate che prima non esistevano. Nel log compaiono come:

| Motivo | Significato |
|---|---|
| `ledger_degraded` | Lo stato anti-doppione non è affidabile: non si sa quali chiusure siano note |
| `state_restore_failed` | Lo snapshot operativo non è stato ripristinato |
| `indicators_degraded` | Le letture di mercato falliscono da troppo tempo |
| `vsl_persist_unhealthy` | Lo stato del Virtual SL non è persistibile su disco |
| `virtsl_offline_risk_over_cap` | Con lo stop inviato al broker il caso peggiore offline supera il tetto |
| `strategy_risk_disabled` | Il piano di controllo ha messo il moltiplicatore a zero |

Il principio: **incertezza sullo stato = nessuna nuova esposizione**.

### 8. Un moltiplicatore di rischio a zero significa zero

Prima veniva riportato a `1.0`, cioè rischio pieno: il comando "disattiva questa
strategia" faceva l'opposto esatto di quanto chiesto.

### 9. La WebSync si spegne senza token dedicato

`InpWebToken` non ha più un default. Senza un token proprio (≥ 24 caratteri) o
senza URL HTTPS, la sincronizzazione si disattiva con un `Alert`. **Il trading e le
protezioni locali restano attivi** — si spegne la telemetria, non l'EA.

### 10. AutoClose dalle sessioni del broker

La chiusura di fine seduta viene da `SymbolInfoSessionTrade()`, non più da un'ora
GMT fissa. `InpMarketCloseGMT` resta solo come ripiego. Su strumenti 24/7 l'AutoClose
semplicemente non scatta più (prima appiattiva a un'ora arbitraria).

---

## Cambia il comportamento della DASHBOARD

### 11. Disarmare una protezione richiede la password

Le azioni `reset_protections`, `reset_daily`, `reset_anti_revenge` restituiscono
`401 STEPUP_REQUIRED`. Serve prima `POST /api/auth/stepup` con la password; la prova
vale 5 minuti.

### 12. Un payload senza campo `event` non è più una chiusura confermata

`/api/ea/trade_reason` senza etichetta viene trattato come `close_request` (non
autorevole) e non scrive i campi realizzati del trade. Un evento sconosciuto → `422`.

### 13. Le migrazioni possono uscire dall'avvio

Con `NEXUS_AUTO_MIGRATE=false` il servizio non tocca lo schema: si applica con
`python -m app --migrate`. È l'unico modo sicuro con più repliche. Il default resta
l'auto-migrazione.

---

## Nuovi input da conoscere

| Input | Default | Cosa fa |
|---|---|---|
| `InpTesterProtectionParity` | `true` | Protezioni di conto attive anche nel tester |
| `InpProtScopeAccountWide` | `true` | Le protezioni di conto chiudono tutto il conto |
| `InpVSL_MaxOfflineRiskMult` | `2.0` | Tetto del caso peggiore offline (× budget) |
| `InpEnvironment` | `""` | Ambiente dell'istanza; rifiuta comandi di ambienti diversi |
| `InpStatePersistInTester` | `false` | Snapshot nel tester, su file separato |
| `InpProt_HardLossFactor` | `1.5` | Oltre questo multiplo si chiude senza attendere la vita minima |
| `InpWebToken` | `""` | **Era un valore pubblico.** Ora obbligatorio |

## Collegamenti
[[MOC - Trading]] · [[NEXUS EA - Remediation Audit v18]] ·
[[TODO - Agente Desktop (consegna remediation)]] · [[DEC - Baseline tecnica corrente]] ·
[[NEXUS EA - Principi]]
