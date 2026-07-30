# NEXUS — CONSEGNA DELLA FASE A

> Fase A del `NEXUS_CLOUD_STRATEGY_WORK_PACKAGE_v1`, autorizzata dal
> proprietario. Obiettivo dichiarato: **rendere il registro epistemologicamente
> corretto** — distinguere cio' che e' implementato, misurato, duplicato,
> surrogato o ignoto. Non modificare le strategie.

| | |
|---|---|
| Commit | `8d1d62f` |
| Base | `1b12bc1` (consegna 1) · baseline congelata `4465873` |
| Branch | `claude/strategy-work-package-v1` |
| File toccati | 17 (2809 inserimenti, 413 rimozioni) |
| Test | **244 passati, 1 saltato** (erano 211) |
| Build frontend | riuscita |
| Compilazione MQL5 | **non eseguita** — MetaEditor non esiste in questo ambiente |

---

## 1. Diff completo

```
 .github/workflows/ci.yml                        |   16 +
 MQL5/Include/NEXUS_v1/NXS_Inputs.mqh            |   20 +
 MQL5/Include/NEXUS_v1/NXS_InstitutionalCore.mqh |  107 ++-
 contracts/extract_selectors.py                  |  275 ++++++   (nuovo)
 contracts/gen_strategy_docs.py                  |  294 ++++++   (nuovo)
 contracts/generate_registry.py                  |  274 +++++-
 contracts/strategy-registry.json                | 1104 +++++++++++++-----   (generato)
 contracts/validate_registry.py                  |  127 +++
 docs/NEXUS_STRATEGY_EVIDENCE_PROVENANCE.md      |  115 +++       (generato)
 docs/NEXUS_STRATEGY_INVENTORY.md                |  231 +++--     (generato)
 frontend/src/contracts/strategyRegistry.js      |  109 ++-       (generato)
 frontend/src/pages/dashboard/StrategiesPage.jsx |   66 +-
 frontend/src/pages/dashboard/shared.jsx         |   30 +-
 knowledge/strategy_database.json                |   29 +-        (canonico)
 server/backtest.py                              |   21 +-
 server/strategy_registry.py                     |   18 +-
 server/tests/test_strategy_contract_phase_a.py  |  386 ++++++++  (nuovo)
```

`git diff 1b12bc1 8d1d62f` per il testo completo.

## 2. File canonici modificati

Sono le **fonti**, quelle da cui tutto il resto deriva.

| File | Modifica | Perche' canonica |
|---|---|---|
| `knowledge/strategy_database.json` | 14 `selector_index` compilati + campo di provenienza | E' l'anagrafica da cui nasce il registro. Correggere solo il generato avrebbe lasciato il buco a monte |
| `contracts/generate_registry.py` | deriva selector e interruttori dal codice; emette evidenza, collisioni, conflitti; `null` invece di `"*"` | E' il generatore: cambia cio' che il registro *puo'* affermare |
| `contracts/validate_registry.py` | +127 righe di controlli bloccanti | E' il gate |
| `server/backtest.py` | chiave canonica + alias + deduplicazione | E' il motore research |
| `server/strategy_registry.py` | `research_ids()` e `require_strategy()` tornano l'id canonico | E' il resolver del backend |
| `MQL5/.../NXS_Inputs.mqh` | nuovo input `InpInstCorrelationWeighting = false` | E' la superficie di configurazione dell'EA |
| `MQL5/.../NXS_InstitutionalCore.mqh` | euristica isolata dietro l'input | E' il percorso della conviction |

### I 14 `selector_index` compilati

Derivati dal codice, non scelti: `SMS_BMS_RTO` 22 · `SILVER_BULLET` 23 ·
`AMD_REVERSAL` 24 · `OTE_CONT` 25 · `MALAYSIAN_SNR` 26 ·
`THREE_BAR_DELIVERY_BREAK` 27 · `AMD_CONT` 28 · `JUDAS_SWING` 29 ·
`LDN_REVERSAL` 30 · `NY_REVERSAL` 31 · `WEEKLY_EXP` 32 · `PO3` 33 ·
`LIQ_VOID` 34 · `DISP_REBAL` 35.

Verifica che conta: sui **23 valori gia' presenti** l'estrattore ha trovato
**zero divergenze**. Dove qualcuno aveva scritto un indice a mano, il codice
dice lo stesso numero — quindi l'estrattore legge la cosa giusta, e i 14 nuovi
non sono un'invenzione.

## 3. File generati

Tutti rigenerabili, nessuno da modificare a mano:

| Artefatto | Generatore |
|---|---|
| `contracts/strategy-registry.json` | `contracts/generate_registry.py` |
| `frontend/src/contracts/strategyRegistry.js` | idem |
| `MQL5/Include/NEXUS_v1/NXS_StrategyRegistry.mqh` | idem (invariato in questa fase) |
| `docs/NEXUS_STRATEGY_INVENTORY.md` | `contracts/gen_strategy_docs.py` |
| `docs/NEXUS_STRATEGY_EVIDENCE_PROVENANCE.md` | idem |

## 4. Test aggiunti

`server/tests/test_strategy_contract_phase_a.py` — **33 test**, ognuno legato al
finding che impedisce di ripresentarsi.

| Area | Test | Cosa dimostra |
|---|---|---|
| MM-01 selector | 6 | mappa completa e contigua, registro == codice == knowledge base, e **3 test che rompono il registro** per verificare che il validatore fallisca davvero |
| MM-04/05 collisioni | 4 | le 3 coppie sono dichiarate, il gruppo vale un generatore, gli id restano, 5 proxy su 6 sono marcati come non corrispondenti |
| MM-06 evidenza | 4 | 8/1/28, `SAR` etichettata SURROGATE, le MEASURED citano il round corrente, il validatore rifiuta un'evidenza contraddittoria |
| MM-07 `null` | 3 | nessun `"*"`, le 8 senza TF dichiarano `null`, il validatore rifiuta `"*"` |
| MM-08 alias | 4 | chiave canonica, alias ancora risolto, 36 su 37 hanno research, alias+canonico non raddoppiano i trade |
| MM-02 conflitti | 4 | `DISP_REBAL` ed `ELLIOTT` registrati e **non risolti**, default letti dal codice |
| MM-13 euristica | 6 | default `false`, conviction canonica = somma, ramo unico e guardato, tassonomia mai consultata a interruttore spento, riga identica alla baseline `866a1bc^`, e controprova che accesa cambierebbe il numero |
| Riproducibilita' | 2 | registro rigenerabile senza diff, documenti non stale |

I tre test che **rompono** il registro sono deliberati: senza di loro i controlli
potrebbero essere inerti — e' esattamente il difetto trovato sull'equity breaker
durante la remediation v18, un gate documentato che non veniva mai alimentato.

### CI

Tre passi nuovi in `.github/workflows/ci.yml`: registro rigenerabile senza diff,
documenti allineati, selector completi e contigui.

## 5. Risultato dei test

```
244 passed, 1 skipped, 2 warnings in 10.57s
```

Baseline prima della Fase A: 211 passati, 1 saltato. Nessun test preesistente e'
stato modificato o rimosso.

**Build frontend:** `Compiled successfully.` — verificata anche l'assenza di
credenziali nel bundle appena costruito (`nexus123`: 0 occorrenze;
`X-Nexus-Csrf`: presente).

**Non eseguito:** compilazione MetaEditor e Strategy Tester. Non esistono in
questo ambiente. La verifica sul codice MQL5 e' statica: bilanciamento di
graffe su tutti i 67 file (0 regressioni), ordine di dichiarazione
(`InpInstCorrelationWeighting` e' in `NXS_Inputs.mqh`, incluso alla riga 21,
usato in `NXS_InstitutionalCore.mqh`, incluso alla riga 59), e i 6 test statici
sulla forma del sorgente.

## 6. Collisioni rimaste

Tutte e tre, per scelta: la Fase A le **registra**, non le risolve.

| Gruppo | Funzione condivisa | Rappresentante | Stato |
|---|---|---|---|
| `BOLLINGER` ≡ `RANGE_FADE` | `sig_bollinger` | `BOLLINGER` | `UNRESOLVED` / `PENDING_OWNER_REVIEW` |
| `LONDON_BO` ≡ `WEEKLY_EXP` | `sig_breakout` | `LONDON_BO` | `UNRESOLVED` / `PENDING_OWNER_REVIEW` |
| `SH_BMS_RTO` ≡ `SMS_BMS_RTO` | `sig_ob_mit` | `SH_BMS_RTO` | `UNRESOLVED` / `PENDING_OWNER_REVIEW` |

Per ciascuna, le quattro classificazioni candidate sono scritte nel record:
`INTENTIONAL_ALIAS`, `DISTINCT_CONCEPT_PROXY_IMPL`, `ACCIDENTAL_DUPLICATE`,
`INCOMPLETE_PLACEHOLDER`. Nessuna assegnata: serve sapere cosa la strategia
doveva essere, e quella e' informazione che non e' nel repository.

Regola operativa gia' attiva: `counts_as_independent_signal_generator` marca un
solo membro per gruppo, e `independentSignalGenerators()` nel frontend applica
la deduplicazione. **I sei id restano tutti**, e nessuna implementazione e'
stata fusa.

Restano inoltre aperti i **5 proxy dichiarati su 6** che puntano a un bersaglio
diverso dalla funzione realmente condivisa: `LIQ_VOID`, `LONDON_BO`,
`SH_BMS_RTO`, `SMS_BMS_RTO`, `WEEKLY_EXP`. `PROXY_MAP` non e' stata corretta a
mano — sarebbe stata un'altra asserzione. Il fatto verificabile e' accanto
(`proxy_target_shares_function`).

## 7. Impatto sul comportamento

### Un solo cambio, quello approvato

`InpInstCorrelationWeighting`, default `false`.

- Con `false` — **il default, e quindi il comportamento di chiunque non tocchi
  nulla** — la conviction e' `MathAbs(buySum - sellSum)`. E' letteralmente la
  riga del commit `866a1bc^`, cioe' il codice precedente all'introduzione
  dell'euristica, e un test la confronta contro quel commit.
- L'euristica e' l'unico chiamante di `_nxs_inst_family()`. A interruttore
  spento la tassonomia a sottostringhe non viene mai consultata: e' cio' che
  rende vera l'affermazione "non cambia nulla", e c'e' un test dedicato.
- Rispetto a **ieri** questo *riduce* l'esposizione, non l'aumenta: l'euristica
  attenuava la conviction e quindi in alcuni casi bloccava setup che ora
  passano. Rispetto alla **baseline pre-euristica** e' identico. Nessuno dei due
  confronti apre esposizione nuova rispetto al comportamento storico del
  sistema.

### Tutto il resto: nessun cambio

Il backend, il registro e il frontend cambiano **cosa sanno dire**, non cosa
fanno.

| Cosa | Stato |
|---|---|
| Entry, exit, stop, target, filtri | **invariati** — nessuna riga toccata in nessun file di strategia |
| Sizing e rischio | **invariati** |
| Default enable/disable delle 37 strategie | **invariati** — `code_default_enabled` li *legge*, non li scrive |
| `DISP_REBAL` | **invariata**: gira, `auto_disable_eligible` resta `false`, il conflitto e' solo registrato |
| Permessi del control plane | **invariati** — `AUTO_DISABLE_IDS` deriva ancora da `auto_disable_eligible`, che non e' cambiato per nessuna strategia |
| Coppie duplicate | **non fuse**, nessun id riscritto |
| LIVE | **non toccata** — `autoDeploy` resta disattivato in `render.yaml` |

Un solo comportamento **corretto** oltre a D1, e vale la pena dichiararlo:
`run_backtest` ora deduplica alias e id canonico. Prima passare
`["CISD", "THREE_BAR_DELIVERY_BREAK"]` avrebbe fatto girare la strategia due
volte; era impossibile prima di questa fase, perche' la chiave canonica non
esisteva. Non e' una regressione: e' la protezione che il nuovo alias richiede.

### Cosa cambia per chi guarda la dashboard

Ogni strategia mostra ora `Misurata` / `Dato surrogato` / `Mai misurata`, e le
implementazioni condivise sono marcate. Prima 37 strategie apparivano
equivalenti: una con 915 trade misurati e una mai eseguita avevano lo stesso
aspetto. **Il conteggio onesto e' 8 su 37.**

## 8. Dichiarazione esplicita

> **Entry, exit, stop, target, filtri, sizing e rischio non sono cambiati.**
>
> L'unica modifica al comportamento dell'EA e' l'introduzione di
> `InpInstCorrelationWeighting` con default `false`, che riporta la conviction
> alla formula precedente all'euristica 1/(n+1). Nessun default di
> abilitazione e' stato toccato. `DISP_REBAL` gira esattamente come prima.
> Nessuna coppia duplicata e' stata fusa. Nessun id e' stato riscritto senza
> alias di compatibilita'. Nessun cambiamento e' stato applicato alla LIVE.
>
> **Questo non significa "pronto per la produzione".** Il codice MQL5 non e'
> mai stato compilato, in questa fase come nelle precedenti. Lo stato resta
> NO-GO.

## 9. Piano di rollback

Tre livelli, dal piu' leggero al piu' completo.

### Rollback del solo comportamento — nessun deploy

Non serve toccare il codice: il default e' gia' quello sicuro. Per tornare
all'euristica attiva basta `InpInstCorrelationWeighting = true` nei parametri
dell'EA. Per il resto della Fase A non esiste comportamento da annullare.

### Rollback del commit

```bash
git revert --no-commit 8d1d62f
git commit -m "revert Fase A"
```

Sicuro perche' il commit e' autonomo: non dipende da migrazioni di dati e non
ha scritto nulla su disco fuori dal repository. Effetti collaterali del revert,
da conoscere:

- il knowledge base torna con 14 `selector_index` a `null`;
- `server/backtest.py` torna a indicizzare solo `"CISD"` — chi nel frattempo
  avesse salvato `"THREE_BAR_DELIVERY_BREAK"` come nome di strategia in una
  richiesta persistita riceverebbe un errore esplicito, mai un fallback
  silenzioso (`UnknownStrategyError`);
- i tre passi nuovi di CI spariscono e il registro puo' tornare a divergere.

### Rollback parziale

Le parti sono indipendenti e possono essere annullate singolarmente:

| Parte | File | Revert isolato |
|---|---|---|
| D1 euristica | `NXS_Inputs.mqh`, `NXS_InstitutionalCore.mqh` | sì |
| selector | `knowledge/…json`, `contracts/…` | sì, ma rigenerare il registro |
| chiave canonica | `server/backtest.py`, `server/strategy_registry.py` | sì |
| frontend | `StrategiesPage.jsx`, `shared.jsx` | sì |

### Verifica dopo qualsiasi rollback

```bash
python3 contracts/validate_registry.py
python3 contracts/gen_strategy_docs.py --check
cd server && python -m pytest tests -q
```

## 10. Decisioni ancora necessarie

| # | Decisione | Stato | Cosa serve |
|---|---|---|---|
| **D1** | euristica 1/(n+1) | ✅ **risolta** — input, default `false`, EXPERIMENTAL, documentata, testata | — |
| **D2** | chi e' la fonte di verita' per "accesa/spenta" | ⏳ aperta | Fase A ha reso *visibile* il conflitto (`code_default_enabled` accanto a `default_enabled`) senza sceglierne uno |
| **D3** | `DISP_REBAL` | ⏳ aperta — conflitto registrato, comportamento invariato | **Quattro cose che non sono nel repository:** (a) "disabilitata in produzione reale" descrive un'intenzione o un fatto? (b) esiste una configurazione runtime che la disattiva? (c) il default `true` nel codice e' accidentale? (d) quali risultati storici le sono attribuiti? |
| **D4** | le 3 collisioni | ⏳ aperta — classificate `PENDING_OWNER_REVIEW` | Per ciascuna, quale delle quattro classificazioni |
| **D5** | `ELLIOTT` | ⏳ aperta — conflitto registrato | Implementare la controparte research, o dichiararla non testabile |
| **D6** | ampiezza della campagna di misura | ⏳ aperta | 29 passate isolate mancanti (28 mai fatte + `SAR`) |
| **D7** | le 8 strategie di sessione/AMD | ⏳ aperta | Esistono candele intraday reali per il motore Python? |
| **D8** | documenti d'origine | ⏳ **bloccante per la Fase B** | `NEXUS_CORPUS_SEMANTIC_AUDIT_PRELIMINARY_v1.md`, i materiali di corso e il Master aggiornato **non sono ancora arrivati**: nella cartella di caricamento ci sono solo il Master v18 e il Work Package |

### Una raccomandazione fuori dallo scope della Fase A

Non l'ho fatta, perche' non era fra i sette punti autorizzati: il bundle React
distribuito in `server/static/app/` e' ancora quello vecchio e contiene le
credenziali di default (`admin@nexus.local / nexus123`) e nessuna protezione
CSRF. In questa fase ho verificato che `npm run build` funziona e che il bundle
appena costruito e' pulito. La ricostruzione resta il punto 1 di
`vault/01-Trading/TODO - Agente Desktop (consegna remediation).md`.

---

## Verifica di riproducibilita'

Eseguita su un **clone pulito** al commit `8d1d62f`, con un ambiente Python
creato da zero.

```text
clean checkout        git clone → checkout 8d1d62f → 0 file modificati
   ↓
generatori            contracts/generate_registry.py
                      contracts/gen_strategy_docs.py
   ↓
confronto artefatti   git status --porcelain → VUOTO
                      → la rigenerazione e' deterministica
   ↓
validatori            validate_registry.py      exit 0
                      extract_selectors.py      exit 0
                      gen_strategy_docs --check exit 0
   ↓
test                  244 passed, 1 skipped
   ↓
stato finale          nessun artefatto modificato dall'esecuzione
```

Nessun diff inatteso. I documenti generati non contengono la data proprio per
questo: una data li renderebbe diversi a ogni run e la verifica sopra
fallirebbe sempre.

## Collegamenti

`docs/NEXUS_STRATEGY_INVENTORY.md` · `docs/NEXUS_STRATEGY_MISMATCH_REPORT.md` ·
`docs/NEXUS_STRATEGY_PRIORITY_MATRIX.md` ·
`docs/NEXUS_STRATEGY_EVIDENCE_PROVENANCE.md` · `docs/NORMATIVE_CONFORMANCE.md`
