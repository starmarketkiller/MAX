# Nexus — Evidence Rules (M4)

Regole deterministiche con cui `evidence_engine.py` v1.0.0 genera ogni claim di
`evidence_database.json`. Nessun claim nasce fuori da queste regole; ogni regola è
trasparente, ripetibile e verificabile a macchina. **Mai** viene usato Profit Factor,
win rate, expectancy o profittabilità per decidere la forza di un'evidenza.

---

## Vocabolario fisso

- **claim_type ammessi (18)**: `strategy_exists`, `strategy_identity_verified`,
  `run_exists`, `run_completed`, `run_incomplete`, `baseline_run_available`,
  `baseline_run_missing`, `artifact_exists`, `artifact_missing`,
  `artifact_checksum_verified`, `metric_observed`, `bug_recorded`, `bug_fixed`,
  `decision_recorded`, `timeline_event_recorded`, `identity_mismatch_detected`,
  `data_quality_issue_open`, `data_quality_issue_resolved`.
  Tutto il resto (in particolare i giudizi: strategia buona/cattiva/promettente,
  pronta per il live…) è **vietato** e bloccato da assert + selftest.
- **evidence_status**: `supported` · `partially_supported` · `conflicting` ·
  `unsupported` · `invalidated`.
- **evidence_strength**: `strong` · `moderate` · `weak` · `invalid`.
  È un campo proprio del claim: **non è mai** una copia di `Run.confidence`
  (qualità dell'import ≠ supporto di una fonte a un claim — distinzione permanente).
- **data_scope**: `signal_level` · `equity_level` (riservato, mai emesso oggi) ·
  `metadata` · `execution_integrity` · `code_history` · `documentation` ·
  `data_quality`. Le metriche degli sweep sono **sempre** `signal_level`:
  mai rappresentate come PF/PnL/DD di conto, mai inferite oltre il CSV.

## Identità deterministiche

- `claim_id = "clm-" + sha1(claim_type|subject_type|subject_id)[:12]`
- `evidence_id = "evl-" + sha1(claim_id|source_type|source_id|checksum)[:12]`

Stessi input ⇒ stessi ID ⇒ rigenerazione incrementale idempotente: rilanciare il
motore senza dati nuovi produce un file **byte-identico** (nessun timestamp di
generazione nell'output; `output_fingerprint` = hash dei soli claims).

## Aggregazione multi-fonte (Builder.add)

1. Un claim esiste **una sola volta** per `claim_id`; fonti successive si agganciano
   come `evidence_links`, mai come claim duplicati.
2. Una fonte già collegata (stesso `evidence_id`) non viene mai duplicata.
3. `independent_source_count` = numero di **checksum distinti** tra i link; le fonti
   senza checksum si distinguono per `source_type::source_id`. Lo stesso file visto
   da due path conta **1**.
4. Status: domina il **peggiore** (ordine: supported < partially_supported <
   unsupported < conflicting < invalidated).
5. Strength: se una fonte porta `conflicting`/`invalidated` ⇒ strength forzata a
   `invalid`; altrimenti resta la **migliore** raggiunta dalle fonti valide.
6. I motivi (`evidence_reason`) si accumulano con prefisso `[Rxx]`, dedupe esatto.

## Conflitti

Un conflitto (checksum cambiato, file sparito, stato dichiarato senza riferimento)
produce status `conflicting` + apertura **idempotente** di una data_quality_issue.
Il motore **non risolve mai** i conflitti da solo: li registra e li espone.

---

## Le regole R01–R16

### R01 — strategy_exists
- **Input**: voce in `strategy_database.json` (37 strategie).
- **Output**: `supported` / `strong`, scope `metadata`.
- **Razionale**: il database strategie è fonte curata diretta; l'esistenza della
  voce è il fatto stesso che si sta affermando.
- **Esempio**: `clm(strategy_exists, strategy, ADX_RSI)`.
- **Edge case**: nessuno — la regola non guarda risultati o stato della strategia.

### R02 — run_exists
- **Input**: voce in `runs_database.json`.
- **Output**: `supported`; `strong` se l'artefatto col checksum della run esiste nel
  registro artefatti, altrimenti `moderate`. Scope `execution_integrity`.
- **Razionale**: una run ancorata a un artefatto checksummato è più difendibile di
  una registrata senza artefatto rintracciabile.
- **Esempio**: `sweep37-baseline-e6ce816__S01__ADX_RSI__…` → strong.
- **Edge case**: checksum non presente in `artifacts_database.json` → il claim resta
  supported (la run è registrata) ma moderate, con motivo esplicito.

### R03 — run_completed
- **Input**: run con `completed = true`.
- **Output**: `supported` / `strong` se `identity_ok ≠ false`;
  **`invalidated` / `invalid`** se la run ha identity mismatch. Scope `execution_integrity`.
- **Razionale**: una run "completa" ma con contenuto che non corrisponde alla
  passata dichiarata non è una fonte valida per nulla.
- **Edge case**: `identity_ok = null` (non verificabile) non invalida: resta il ramo
  positivo, perché il mismatch va **rilevato**, non presunto.

### R04 — run_incomplete
- **Input**: run con `completed = false`.
- **Output**: `supported` / `strong`, scope `data_quality` (l'incompletezza è
  osservata direttamente nel parse, quindi il *claim di incompletezza* è forte).
- **Edge case**: una run incompleta non partecipa **mai** a R07 (baseline
  disponibile) né produce R11 se non ha metriche parsate.

### R05 — strategy_identity_verified
- **Input**: run con `identity_ok = true` (check selector↔strategia dalla mappa
  estratta dal codice EA).
- **Output**: `supported` / `strong`, scope `execution_integrity`.
- **Edge case**: `identity_ok = null` ⇒ nessun claim (né verificato né mismatch).

### R06 — identity_mismatch_detected
- **Input**: run con `identity_ok = false`.
- **Output**: `supported` / `strong`, scope `data_quality`.
- **Razionale**: il *rilevamento* del mismatch è un fatto certo; sono le run e le
  metriche di quella passata a diventare `invalidated` (R03/R11).
- **Esempio (selftest)**: file S08 con dentro MACD ⇒ questo claim + run invalidata.

### R07 — baseline_run_available
- **Input**: per ogni strategia, almeno una run con `round = sweep37-baseline-e6ce816`,
  `completed = true`, `identity_ok ≠ false`. Se più d'una, si àncora all'ultima in
  ordine deterministico di `run_id`.
- **Output**: `supported` / `strong`, scope `execution_integrity`.
- **Razionale**: "esiste una run baseline valida" richiede tutte e tre le condizioni;
  runs incomplete o con mismatch non contano (validazione 5 del selftest).

### R08a — baseline_run_missing (attesa ma assente)
- **Input**: strategia senza run baseline valida **e** `selector_index ≤` all'indice
  massimo di passata baseline già importato (il gap è dentro la sequenza percorsa).
- **Output**: `supported` / `strong`, scope `data_quality`; il link punta alla
  data_quality_issue se esiste (es. `dqi-missing-S04-sweep37-baseline-e6ce816`).
- **Esempio**: SAR/S04 — lo sweep ha superato S04 ma le stats non sono mai arrivate.
- **Edge case**: se la DQI non esistesse ancora, la fonte resta `runs_database.json`
  (il gap è comunque rilevato deterministicamente).

### R08b — baseline_run_missing (non ancora raggiunta)
- **Input**: strategia senza run baseline valida e `selector_index >` all'indice
  massimo importato.
- **Output**: `supported` / `moderate`, scope `metadata`.
- **Razionale**: assenza attesa e **transitoria** (sweep in corso): vera oggi, ma
  destinata a sparire con i prossimi import — per questo moderate, non strong.
- **Edge case**: al prossimo import il claim viene naturalmente sostituito da R07
  (stesso subject, claim_type diverso ⇒ claim_id diverso; il DB si rigenera).

### R09a — artifact_exists / R09b — artifact_missing
- **Input**: per ogni artefatto registrato, **verifica reale su disco** (`sha256_file`).
- **Output R09a** (file presente): `supported` / `strong`, scope `execution_integrity`.
- **Output R09b** (file assente): `artifact_missing`, **`conflicting` / `invalid`**,
  scope `data_quality` + apertura idempotente di `dqi-missing-file-{artifact_id}`.
- **Razionale**: registro che dice "esiste" e filesystem che dice "non c'è" è un
  conflitto, non un'assenza semplice.

### R10a/b — artifact_checksum_verified
- **Input**: solo per artefatti presenti su disco: sha256 **ricalcolato ora** vs
  checksum registrato all'import.
- **Output**: uguali → `supported` / `strong` (`execution_integrity`);
  diversi → **`conflicting` / `invalid`** (`data_quality`) + apertura idempotente di
  `dqi-checksum-{artifact_id}` (violazione dell'immutabilità V03 dello schema).
- **Edge case**: il motore non "aggiorna" mai il checksum registrato — segnala e basta.

### R11 — metric_observed
- **Input**: run con blocco `metrics` parsato.
- **Output**: scope **sempre `signal_level`** (validazione 7). Status/strength:
  - run baseline valida → `supported` / `strong` (artefatto checksummato);
  - round storico pre-baseline → `supported` / `moderate` (non confrontabile con la
    baseline, DEC-008);
  - run con identity mismatch → **`invalidated` / `invalid`**.
- **Razionale**: la forza riflette la **tracciabilità della fonte**, mai il valore
  delle metriche. Un PF 0.13 e un PF 1.04 da artefatti equivalenti hanno la stessa
  strength.
- **Edge case reale**: run storiche con `trade_eseguiti=0` ma wins/losses>0
  (contatore executed rotto, pre-fix): il claim riporta il dato **così com'è**,
  senza correggerlo né interpretarlo.
- **Vietato**: inferire Net PnL / Max Drawdown di conto dai CSV di sweep; spacciare
  PF di segnale per PF di equity.

### R12 — bug_recorded
- **Input**: voce in `bug_database.json` (31 bug).
- **Output**: `supported` / `strong`, scope `documentation`.

### R13a/b/c — bug_fixed (tre vie)
- **Input**: bug con stato "risolto…"; si estrae uno SHA dal campo `commit_fix` e si
  verifica con `git cat-file -e sha^{commit}`.
- **R13a** SHA esistente nel repo → `supported` / `strong`, scope `code_history`
  (fonte = il commit stesso).
- **R13b** riferimento descrittivo ma non commit-verificabile (es. fix vissuto in
  vault o SHA non risolvibile) → **`partially_supported` / `moderate`**, scope
  `documentation`. Esempio reale: BUG-023 ("pre-sessione, vault Audit Fedeltà Trigger").
- **R13c** stato "risolto" senza alcun riferimento → **`conflicting` / `invalid`**,
  scope `data_quality`: dichiarazione senza pezza d'appoggio è un conflitto documentale.
- **Edge case**: bug aperti non generano alcun claim `bug_fixed` (solo R12).

### R14 — decision_recorded
- **Input**: voce in `decision_database.json` (DEC-001…DEC-013).
- **Output**: `supported` / `strong`, scope `documentation`.
- **Nota**: si certifica che la decisione è **registrata**, non che sia giusta.

### R15 — timeline_event_recorded
- **Input**: ogni evento di `strategy_timelines.json` (309).
- **Output**: `supported`; `strong` solo se l'evento è ancorato a commit o run
  **e** ha confidence high; altrimenti `moderate`. Scope `code_history` se
  commit-backed, altrimenti `documentation`.
- **Razionale**: un evento con SHA verificabile è più difendibile di una data presa
  da un documento.
- **Edge case**: la confidence dell'evento (M2) concorre alla strength ma **non la
  sostituisce** — resta un input tra due, mai copiata nel campo.

### R16 — data_quality_issue_open / _resolved
- **Input**: voce in `data_quality_issues.json`; il claim_type segue lo `status`.
- **Output**: `supported` / `strong`, scope `data_quality`.
- **Edge case**: le issue aperte **dal motore stesso** (R09b/R10b) entrano nel
  registro in questo run e generano il loro claim R16 dal run successivo —
  l'idempotenza garantisce che non vengano mai duplicate.

---

## Validazione finale (validate + selftest)

Prima della scrittura: ogni `related_run_id`/`related_artifact_id`/`related_bug_id`/
`related_decision_id`/`related_event_id` deve esistere nei rispettivi database, ogni
claim deve avere ≥1 evidence_link e un claim_type ammesso. Il selftest (12 controlli)
copre: determinismo del doppio build, dedupe fonti, indipendenza per checksum,
invalidazione su mismatch, esclusione delle run incomplete dalla baseline, S04→DQI,
scope signal_level universale per le metriche, separazione strength/confidence,
integrità referenziale, fonte obbligatoria, divieto di claim speculativi, idempotenza.
