# NEXUS - Phase 6.5: Dependent Evidence & Directional Baseline Hardening

Fase infrastrutturale: corregge due limiti metodologici emersi in Phase 6 (dipendenza temporale/clustering degli eventi; baseline non direction-aware) **prima** di qualunque nuova edge discovery. Nessun nuovo edge, nessun test H007, nessuna promozione/ri-validazione di H006, nessuna strategia, nessuna optimization. H006 è usato **esclusivamente come caso di test infrastrutturale** — ogni risultato qui prodotto è `METHODOLOGICAL_AUDIT_ONLY`.

---

## 1-2. Event Dependence Model + Effective Sample Size

Implementazione: `server/research_scripts/phase6_5/dependence_diagnostics.py`, applicata a H006 (115 eventi RECLAIM confermati nell'holdout).

| Diagnostica | Valore |
|---|---|
| Gap mediano fra eventi | 6 barre (min 0, max 89) |
| Clustering rate entro 1/2/3/5/10 barre | 37.4% / 48.7% / 57.4% / 70.4% / 83.5% |
| n_clusters (soglia catena 10 barre) | **46** |
| Cluster più grande | 8 eventi |
| Autocorrelazione outcome, lag 1-10 | lag1=0.161, lag2=0.025, ..., lag6=-0.234 (nessun lag supera 1.96/√n=0.183 in valore assoluto) |
| `dependence_flag` | **HIGH** |

**3 stime di n_effective, deliberatamente non unificate in un'unica formula:**

| Metodo | n_effective | Riduzione da n_nominal=115 |
|---|---|---|
| Cluster-count approximation | **46** | -60% |
| Autocorrelation-based | **115** | 0% (vedi nota) |
| Block-bootstrap-variance-based | **91.1** | -21% |

**Nota importante sul disaccordo fra metodi**: il metodo basato su autocorrelazione tronca la somma al primo lag il cui \|ρ\| scende sotto la soglia di significatività (1.96/√n≈0.183) — qui questo accade già al lag 1 (ρ₁=0.161<0.183), quindi il metodo non rileva **nessuna** inflazione di varianza da autocorrelazione, anche se il clustering temporale (misurato da gap/overlap) è chiaramente forte. Questo NON è un bug: autocorrelazione del **valore** dell'outcome (l'esito è simile fra eventi vicini?) e clustering/overlap **temporale** (gli eventi osservano lo stesso tratto di mercato?) sono due forme distinte di dipendenza — qui la seconda è forte, la prima è debole. I tre metodi non vanno mai fusi in un solo numero: il disaccordo stesso (46 vs 91 vs 115) è l'informazione, non un errore da risolvere.

## 3. Block Bootstrap

Implementazione: `server/research_scripts/phase6_5/block_bootstrap.py`. Moving Block Bootstrap, lunghezza blocco L=⌈n^(1/3)⌉=5 (criterio dichiarato prima di guardare l'effetto, stessa formula per ogni futuro campione).

| | iid bootstrap | Block bootstrap (L=5) |
|---|---|---|
| CI95 | [50.43%, 68.70%] | [49.57%, 69.57%] |
| Ampiezza CI | 0.1826 | 0.2000 |
| n_effective implicito | 115 (per costruzione) | **91.1** |

CI più ampia del **9.5%** con il block bootstrap — un allargamento reale ma non drammatico, coerente con l'idea che la dipendenza qui è moderata-alta ma non estrema quanto suggerito dal solo overlap delle finestre di outcome.

## 4. Directional Baseline Engine v3

Implementazione: `server/research_scripts/phase6_5/directional_baseline_v3.py`. La direzione è ora parte del **contratto di matching**: ogni evento è confrontato SOLO con barre di controllo valutate nella sua stessa direzione (stesso coarsened+NN matching, stessa normalizzazione congelata di Phase 6 — nessuna soglia ricalcolata).

| | BUY | SELL |
|---|---|---|
| n eventi | 63 | 52 |
| P evento | 52.38% | 67.31% |
| **P baseline direzionale** | **50.48%** | **56.92%** |
| ΔP (baseline direzionale) | **+0.019** | **+0.104** |
| ΔP (baseline aggregato, Phase 6 originale) | -0.010 | +0.139 |
| CI95 non sovrapposte | No | No |

**Scoperta chiave**: la baseline BUY-only (50.5%) e SELL-only (56.9%) **non sono comparabili fra loro** — differiscono di 6.4pp indipendentemente da RECLAIM. Il baseline aggregato usato in Phase 6 mescolava queste due popolazioni diverse, distorcendo la lettura: il ΔP BUY passa da leggermente negativo (-0.010) a leggermente positivo (+0.019) una volta confrontato con la baseline corretta; il ΔP SELL si **riduce** da +0.139 a +0.104. L'asimmetria BUY/SELL **persiste** ma è meno marcata di quanto Phase 6 suggerisse — nessuno dei due lati supera comunque la soglia di non-sovrapposizione CI95.

## 5. Directional Diagnostics Policy

Politica formalizzata in `directional_diagnostics_policy.json`: un'asimmetria BUY/SELL osservata post-hoc non promuove mai automaticamente il lato positivo — può al massimo generare una nuova ipotesi candidata, che richiede freeze esplicito + un nuovo holdout indipendente (stesso standard di H004→H006).

**Osservazione registrata**: `SELL_SWEEP_RECLAIM_ASYMMETRY`, status **`POST_HOC_OBSERVATION`**, esplicitamente **non un edge**. Nessun test H007 eseguito in questa fase.

## 6. Overlapping Outcome Windows

Calcolato dentro `dependence_diagnostics.py` (orizzonte 40 barre, stesso di Phase 5/6):

| Classificazione | n eventi | % |
|---|---|---|
| Independent | 1 | 0.9% |
| Partially overlapping | 6 | 5.2% |
| **Heavily overlapping** | **92** | **80.0%** |
| (implicito, somma) overlap_rate complessivo | — | **99.1%** |

Con un gap mediano di 6 barre e un orizzonte di outcome di 40 barre, quasi ogni evento condivide la maggioranza della propria finestra futura con almeno un altro evento — i 115 eventi osservano un numero di movimenti di mercato realmente distinti molto più vicino a 46-91 che a 115.

## 7. Evidence Engine v2

Schema esteso: `evidence_engine_v2_schema.json` — aggiunge n_nominal/n_effective (3 metodi)/event_clusters/overlap_rate/iid_uncertainty/dependence_aware_uncertainty/baseline_method/direction_specific_baseline_status/grade_cap_reason (obbligatorio se dependence_flag≠LOW). Record completo per H006 popolato come esempio lavorato — **non cambia il grade E2 di H006**, dimostra solo che lo schema è applicabile e che H006 avrebbe ricevuto un `grade_cap_reason` esplicito anche se il ΔP nominale fosse stato sopra soglia.

## 8. Retroactive Audit — cosa NON è cambiato

- Il verdetto Phase 6 di H006 resta **BORDERLINE**.
- Nessuna promozione del lato SELL.
- Nessun grade E3 assegnato.
- Nessun risultato di questa fase è un nuovo edge — tutto è etichettato `METHODOLOGICAL_AUDIT_ONLY`.

## 9. Automated Gate: DEPENDENCE_AUDIT_PASS

Implementazione: `server/research_scripts/phase6_5/dependence_audit_gate.py`. Verifica meccanica (non di merito) che un record di evidenza contenga la strumentazione minima richiesta.

- **Record H006 completato con i campi Phase 6.5**: `DEPENDENCE_AUDIT_PASS` (0 campi mancanti).
- **Record H006 ORIGINALE di Phase 6** (prima di questa fase, senza n_effective/overlap_rate/dependence_aware_uncertainty/ecc.): **`DEPENDENCE_AUDIT_FAIL`** — 7 campi mancanti. Questo dimostra concretamente che il gate avrebbe bloccato Phase 6 stessa se fosse stato già in vigore, senza bisogno di scoprire il problema a posteriori.

---

## Risposte finali

**1. Quanto differisce n_effective da n_nominal su H006?**
Da 115 nominale a: 46 (cluster-count, -60%), 115 (autocorrelation-based, 0%), 91.1 (block-bootstrap-variance, -21%). I tre metodi divergono sostanzialmente — il disaccordo è dichiarato esplicitamente, non risolto in un unico numero.

**2. Quanto sono sovrapposte le outcome window?**
Moltissimo: 99.1% degli eventi ha una finestra di outcome (40 barre) parzialmente o pesantemente sovrapposta a quella di un altro evento; l'80% è "heavily overlapping". Solo 1 evento su 115 è pienamente indipendente per finestra di outcome.

**3. L'iid bootstrap era troppo ottimistico?**
Moderatamente sì. La CI iid (ampiezza 0.183) è più stretta della CI block-bootstrap (ampiezza 0.200, +9.5%), e l'ESS implicito dal block bootstrap (91.1) è inferiore al nominale (115). Non una distorsione drammatica in questo caso specifico, ma reale e nella direzione attesa.

**4. Quanto cambia l'incertezza col block bootstrap?**
CI95 si allarga del 9.5% (da [50.4%,68.7%] a [49.6%,69.6%]) — un cambiamento reale ma più contenuto di quanto il clustering/overlap estremo (99%) potrebbe far pensare, a conferma che dipendenza-nel-tempo e dipendenza-nel-valore-dell'outcome sono aspetti distinti.

**5. BUY e SELL hanno baseline comparabili quando trattati separatamente?**
**No.** Baseline BUY-only P=50.5% vs baseline SELL-only P=56.9% — una differenza strutturale di 6.4pp indipendente da RECLAIM. Il baseline aggregato di Phase 6 non era un metro di paragone equo per nessuno dei due lati singolarmente.

**6. Quali nuovi failure mode sono ora automaticamente bloccabili?**
(a) Record di evidenza privi di strumentazione di dipendenza/overlap/ESS (`DEPENDENCE_AUDIT_FAIL`, dimostrato bloccando retroattivamente il record originale di Phase 6). (b) `dependence_flag≠LOW` senza `grade_cap_reason` esplicito. (c) Confronto direzionale (BUY/SELL) contro un baseline aggregato quando le baseline direzionali differiscono materialmente fra loro — ora rilevabile confrontando esplicitamente baseline BUY-only vs SELL-only. (d) Riferimento silenzioso a un solo metodo di ESS senza dichiarare se altri metodi concordano (`methods_agree`).

**7. Cosa resta human-review only?**
Decidere se un'asimmetria BUY/SELL osservata post-hoc merita l'investimento di una nuova ipotesi pre-registrata con un holdout dedicato (giudizio di costo/beneficio, non meccanico). Validare che la soglia di clustering (10 barre) e il criterio di lunghezza blocco (n^(1/3)) restino sensati su un dataset con caratteristiche molto diverse (es. un timeframe diverso da H4). Interpretare SOSTANZIALMENTE perché due metodi di ESS divergono (il calcolo è automatico, la spiegazione causale — qui, autocorrelazione debole del valore vs clustering forte nel tempo — richiede sintesi umana). Decidere se e quando investire in un E4/E5 dopo un eventuale futuro E3.

---

## Artifact prodotti

- `server/research_scripts/phase6_5/dependence_diagnostics.py` + `h006_dependence_audit.json`
- `server/research_scripts/phase6_5/block_bootstrap.py` + `h006_block_bootstrap_audit.json`
- `server/research_scripts/phase6_5/directional_baseline_v3.py` + `h006_directional_baseline_v3.json`
- `server/research_scripts/phase6_5/directional_diagnostics_policy.json`
- `server/research_scripts/phase6_5/evidence_engine_v2_schema.json`
- `server/research_scripts/phase6_5/dependence_audit_gate.py` + `dependence_audit_gate_result_H006.json`
