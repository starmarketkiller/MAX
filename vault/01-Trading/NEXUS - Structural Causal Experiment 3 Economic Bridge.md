# NEXUS Causal Research Thread 2 — Structural Causal Experiment 3: Economic Bridge

Segue [[NEXUS - Structural Causal Experiment 2 Confirmatory]] (commit `321fe1f`, verdict `STRUCTURAL_HYPOTHESIS_CONFIRMED` su `penetration_per_atr > 0.058713928652578955`). Terzo periodo indipendente: prima re-verifica la replicazione strutturale (senza modificare nulla), poi valuta se il predittore ha valore economico via `AT_TRUE_BREAK`.

## 1. Periodo

**wA: 2025-05-01 → 2025-09-01** (4 mesi) — precedente a `2025-09-01` come richiesto, zero overlap con `w0` (2025-09-01→2026-01-01) e `w1-w4` (2026-01-01→2026-08-25). Dati GOLD H4/M1 disponibili e affidabili per questo periodo (storico dal 2005-04-06) — nessuno STOP necessario.

## 2. Ricostruzione identica

Nessuna modifica: stesso detector fix `9b77f83`, stesso `assign_episodes()`/`build_episode_lifecycle_index()` con chiavi `(window_id, event_id)`, stessa exclusion policy, stessi snapshot causali. Verificato:

| Check | Esito |
|---|---|
| Orphan | **0** |
| Malformed | **0** |
| Outcome da evento post-close usato nella population | **0** (11 episodi esclusi per questo motivo) |

| | n |
|---|---|
| Episodi totali | 907 |
| `NO_LIFECYCLE_OBSERVED` | 179 |
| Esclusi (esito post-close) | 11 |
| **Population valida** | **717** |

## 3. Structural replication (soglia congelata, NESSUNA modifica)

| | n | rate | uplift assoluto | CI95 |
|---|---|---|---|---|
| Baseline (tutta la population) | 717 | 7.95% | — | — |
| `penetration_per_atr > 0.0587...` | 194 | 14.43% | **+6.48pp** | [10.2%, 20.1%] |

- **Direzione**: positiva, coerente con Experiment 1/2 (stesso segno).
- **Significatività**: p=9.3e-05 (z=3.91) — statisticamente solido.
- **BUY**: n=85, uplift +7.47pp. **SELL**: n=109, uplift +5.68pp — nessuna inversione, entrambi positivi.
- **Prima metà**: n=94, uplift +7.80pp. **Seconda metà**: n=100, uplift +5.31pp — coerente, nessuna contraddizione.
- **Ma l'uplift assoluto (+6.48pp) è sotto la soglia di materialità dichiarata in Experiment 1/2 (0.10 = 10pp)** — la stessa identica soglia usata per promuovere l'ipotesi a `CONFIRMED` in Experiment 2 (dove l'uplift era +11.3pp).

**Classificazione della replicazione strutturale: sotto soglia di materialità → per la disciplina già applicata in questo thread (Causal Experiment 1→2→3 su WICK Sweep: un solo mancato superamento della soglia pre-registrata su un test finale = chiusura, mai un abbassamento della soglia per salvare l'ipotesi), questo equivale a un fallimento della replicazione per gli standard dichiarati.**

## 4. Economic bridge — `AT_TRUE_BREAK`

Verificata nel codice la semantica BUY/SELL prima di procedere (nessuna assunzione): in `NXS_SHBMS_UpdateSide`, `dir==+1 → s.dir=DIR_BUY`, `dir==-1 → s.dir=DIR_SELL`; la direzione è congelata in `st.structDir` al momento dello SWEEP e riportata invariata su TRUE_BREAK/RETEST/INVALIDATE — il campo `direction` del rigo TRUE_BREAK è quindi la stessa direzione dello sweep originario, nessuna ambiguità.

**Join causale esplicito verificato**: `penetration_per_atr` usata per il filtro del Gruppo B è quella **dello SWEEP originario** (letta da `sweeps_by_episode[episode_id]`), **mai** ricalcolata sui campi propri del rigo TRUE_BREAK (che descrivono lo stato al momento del break, non dello sweep) — implementato tramite lookup diretto sull'evento SWEEP via `structural_episode_id`, non per timestamp.

| | n |
|---|---|
| TRUE_BREAK totali (esito affidabile, non post-close) | 57 |
| Risolti (PLUS_1R_FIRST/MINUS_1R_FIRST) | 31 |
| **Ambiguous (stessa barra)** | **26 (45.6%)** |
| Censored | 0 (0.0%) |

L'ambiguity rate è molto alta (45.6%) — R=25 pip fisso è stretto rispetto alla volatilità H4 di GOLD, coerente con quanto già osservato in Causal Experiment 1/2/3 (WICK Sweep) e in Experiment 1 di questo thread.

| Gruppo | n | PLUS_1R_FIRST | rate | CI95 |
|---|---|---|---|---|
| **A** — tutti i TRUE_BREAK risolti (baseline) | 31 | 15 | 48.4% | [32.0%, 65.2%] |
| **B** — TRUE_BREAK da sweep con penetration/ATR > soglia | 13 | 9 | 69.2% | [42.4%, 87.3%] |

Uplift B vs A: **+20.8pp** (z=1.97, p=0.048 — al limite della significatività convenzionale, su un campione minuscolo).

- **BUY** (Gruppo B): n=6, rate=83.3%. **SELL** (Gruppo B): n=7, rate=57.1% — entrambi sopra la baseline, nessuna inversione, ma **n a singola cifra per lato**.
- **Prima metà**: n=6, rate=50.0%. **Seconda metà**: n=7, rate=85.7% — direzione non contraddittoria, ma campioni minuscoli.

## 5. Secondary bridge — `RETEST_HOLD_OR_FAIL`

Solo **1** episodio del Gruppo B ha un RETEST osservato (esito: HOLD). **Campione totalmente insufficiente** — non usato per promuovere né bocciare la candidata, come da istruzione esplicita.

## 6. Correlazione / concentrazione (Gruppo B)

| | n |
|---|---|
| `structural_episode_id` unici | 13 |
| `structural_level_id` unici | 13 |

Nessuna concentrazione anomala: ogni episodio del Gruppo B è un `structural_level_id` distinto (nessun livello ripetuto più volte), distribuiti su 11 giorni diversi (3 episodi il 2025-06-03, il resto 1 per giorno) e su 6 levelTag diversi (Equal-High=4, Daily-High=2, Equal-Low=2, Asia-Low=2, Daily-Low=2, Weekly-High=1) — nessun singolo tag/giorno domina il campione.

**CI95 clusterizzato per giorno** (bootstrap, 2000 resample, resampling di giorni interi per correggere la correlazione infra-giorno): **[45.5%, 90.9%]** — leggermente più ampio del CI95 naive [42.4%, 87.3%] come atteso, ma non cambia la sostanza: il campione (n=13, 11 giorni) è troppo piccolo perché un aggiustamento per clustering sia la parte determinante dell'incertezza.

## 7. Gate — perché non ECONOMIC_BRIDGE_CONFIRMED

Il criterio (a) del gate («structural uplift resta nella stessa direzione») è soddisfatto nominalmente — direzione sempre positiva. Ma:

- Il primo criterio di ammissibilità implicito — che la replicazione strutturale regga secondo lo STESSO standard usato per promuoverla in Experiment 2 — **non è soddisfatto** (§3): +6.48pp contro la soglia di 10pp già applicata due volte in questo thread.
- Anche isolando il solo economic bridge: **n=13 nel Gruppo B è un campione microscopico** — 6 BUY e 7 SELL, un solo giorno con più di un episodio, zero RETEST osservabili per la secondary bridge. Il p-value marginale (0.048) su un campione così piccolo non è una base sufficiente per dichiarare valore economico accertato, specialmente dopo aver già trovato un'attenuazione strutturale nello stesso periodo.

## Verdict

### **STRUCTURAL_HYPOTHESIS_REFUTED_FINAL**

La replicazione strutturale su questo terzo periodo indipendente non conferma il predittore secondo lo standard di materialità già applicato (10pp) — l'effetto resta nella stessa direzione e statisticamente significativo, ma si è attenuato sotto la soglia usata per promuoverlo in Experiment 2. Per la stessa disciplina già seguita nel filone WICK Sweep (nessun abbassamento di soglia per salvare un'ipotesi su un test finale), questo chiude il filone: **`penetration_per_atr` al momento dello SWEEP non regge una terza conferma indipendente agli standard dichiarati.**

I numeri dell'economic bridge (§4-6) sono riportati per completezza come richiesto, ma **non sono decisivi** — il campione (n=13 nel Gruppo B) è troppo piccolo per essere la base di una decisione, ed è comunque subordinato all'esito della replicazione strutturale (§3), che ha già determinato il verdict.

**Nessuna implementazione.** Nessun filtro aggiunto a `SH_BMS_RTO` o all'EA. Il filone di ricerca causale su `penetration_per_atr` come predittore strutturale/economico è da considerarsi chiuso in assenza di nuovi elementi.
