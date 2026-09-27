# NEXUS - Phase 7.16 — Semantic Contract EA/Python e Fedeltà della Ricostruzione ORDER_BLOCK

**Baseline:** `906db57` (Phase 7.15). Nessun lavoro concorrente rilevato. Nessun nuovo run Tester pluriennale, nessuna optimization, nessun confronto PF/WR, nessuna ricerca economica, nessuna modifica a ORDER_BLOCK/OB_MIT o attivazione di nuove strategie.

**Obiettivo**: spiegare la prima divergenza causale fra ORDER_BLOCK nell'EA MT5 post-fix e la ricostruzione Python, con scope stretto e una fine definita — anche se Python risulta solo un modello parziale.

---

## 1. Semantic contract matrix

11 dimensioni verificate direttamente sul codice (non assunte): 2 strutturalmente identiche (creazione zona, aggiornamento/scadenza/invalidazione — porting fedele confermato), 6 diverse. **Punto centrale verificato, non assunto**: il trace diagnostico di Phase 7.14 conta un "segnale" esattamente dentro `NXS_OB_UpdateSide()`, PRIMA dei gate H1/SMC — lo stesso livello del funnel della ricostruzione Python (`ob_update_side()`). **8 eventi EA e 7 eventi Python sono confermati essere allo stesso livello del funnel** — l'assunzione contestata dal task è verificata vera, non è la causa della divergenza.

La causa reale, isolata in questo confronto: il test `touched` dell'EA usa il **bid live della barra in formazione** (shift 0, oggi); la ricostruzione Python di Phase 7.13 usa invece **la barra appena chiusa** (shift 1, ieri) — la stessa barra già usata per `rejection`. Il docstring del modulo Phase 7.13 descriveva questo come "stessa barra, non per-tick" — una caratterizzazione imprecisa: non si limita a discretizzare il tick-by-tick, usa la barra sbagliata.

## 2. Prima divergenza causale

Ri-eseguendo la ricostruzione sulla stessa serie D1 locale già disponibile (`phase7_13/multi_tf_dataset_v1.json`, nessun nuovo download), con una versione **corretta** (`touched` su `bars[i+1]` invece di `bars[i]`, `rejection` invariata): la prima divergenza fra versione originale e corretta cade sulla barra D1 indice 49 (2023-12-07→2023-12-08), lato BUY — zona `[1989.72, 1998.38]`. La correzione fa passare il tasso di corrispondenza con l'EA reale (Phase 7.14, trace post-fix) da **1/8** a **6/8** eventi (stessa data + stessa direzione).

**Blocker dichiarato**: l'istrumentazione diagnostica di Phase 7.14 ha registrato solo lo stato della zona e l'operazione, **non le barre D1 OHLC grezze** effettivamente usate dall'EA — non è possibile un confronto input→stato→transizione campo-per-campo fra EA reale e Python sulla stessa barra di prezzo; solo un confronto per sequenza di date/direzioni (fatto sopra). Nessun nuovo run lanciato per colmare questo gap.

## 3. Episodi minimi

4 episodi (1 reale, dati locali già disponibili + 3 sintetici), valori attesi derivati a mano (aritmetica sui numeri grezzi) e poi verificati contro l'esecuzione reale delle due funzioni: EP1 (reale, BUY, correzione aggiunge un segnale), EP2 (sintetico, SELL, l'originale spara un falso positivo che la correzione elimina), EP3 (sintetico, BUY, speculare a EP1), EP4 (controllo negativo: quando ieri e oggi concordano sulla sovrapposizione con la zona, le due versioni concordano — la correzione non altera sistematicamente l'esito).

## 4. Classificazione della fedeltà Python

**`APPROXIMATION_WITH_KNOWN_GAPS`**. Il porting strutturale (displacement/BOS/origine/invalidazione/scadenza/consumo one-shot) resta fedele riga-per-riga. Il fix isolato in questa fase spiega la maggioranza della divergenza (1/8→6/8) ma non tutta (2/8 eventi EA reali restano non spiegati anche dopo la correzione — fonte dati diversa: serie M15-ricampionata vs tick broker, ATR calcolato su storia locale più corta). **Usi validi**: mechanism research, dimostrazione del meccanismo di contaminazione cross-TF (Phase 7.13, non toccata da questo fix). **Usi non validi**: confronto evento-per-evento con date EA specifiche usando la versione originale (Phase 7.13, congelata); qualunque stima di PF/WR/redditività, con o senza correzione.

## 5. Vecchi confronti B/C — stato di utilizzabilità

- Phase 7.13 `ab_simulation_v1.json` (A vs B, interno a Python): **resta valido** per il suo scopo (dimostrare il meccanismo di contaminazione).
- Phase 7.14 A(pre-fix)/B(post-fix), stessi tick EA reali: **pienamente valido, non toccato**.
- Phase 7.14 B vs C (EA vs Python): **già corretto in Phase 7.15** a `CANDIDATE_CAUSE_NOT_ISOLATED` — questa fase fornisce ora la spiegazione causale che allora mancava.
- Phase 7.15 `ea_python_comparison_classification_v1.json`: **confermato e rafforzato** — l'ipotesi "path-dependence su un punto a monte mai isolato" era esattamente il difetto isolato qui.

## 6. Proposta metodologica

Valutato il modello **MT5 = ground truth di segnali/esecuzione; Python = analisi statistica degli eventi esportati** (non un clone eseguibile parallelo). Valutazione: **più robusto per strategie stateful/tick-sensibili come ORDER_BLOCK** — un motore bar-driven Python non può replicare esattamente un contratto che dipende dal prezzo live intrabar, anche con correzioni mirate. Per strategie stateless/bar-driven pure (es. BREAKOUT_ACC post-fix, trigger solo su chiusure) un clone Python **resta valido al 100%**, già dimostrato altrove. **Proposta non applicata globalmente** — dipende dal fatto che la strategia sia tick-sensibile o meno. Raccomandazione pratica se adottata: estendere l'istrumentazione diagnostica già esistente (Phase 7.14) a un export sistematico degli eventi di zona da qualunque run reale futuro, e trattarlo come fonte primaria per l'analisi statistica invece di ricostruire il meccanismo da zero in Python.

## Validazione ORDER_BLOCK preservata

Il confronto A(pre-fix)/B(post-fix) di Phase 7.14, sugli stessi tick MT5 reali, **non è toccato** da questa fase — `FIX_CAUSALLY_VALIDATED` resta la decisione valida. Questa fase riguarda esclusivamente la fedeltà della ricostruzione Python (livello B-vs-C).

## Prossima azione raccomandata

Nessuna ulteriore caccia alla parity perfetta per ORDER_BLOCK/Python — la classificazione `APPROXIMATION_WITH_KNOWN_GAPS` è sufficiente per gli usi validi identificati. Procedere con la prossima voce della coda delle priorità (TSI o la shortlist successiva) per la validazione dell'edge, come indicato dall'utente.

## Deliverables

`build_semantic_contract_matrix.py` + `semantic_contract_matrix_v1.json`, `nxs_order_block_replica_corrected.py` (copia isolata e corretta, l'originale di Phase 7.13 resta congelato/non modificato), `build_first_divergence.py` + `first_divergence_v1.json`, `build_minimal_episodes.py` + `minimal_episodes_v1.json`, `build_fidelity_classification_and_proposal.py` + `fidelity_classification_and_proposal_v1.json`, verificatore indipendente (VERIFY OK), 20/20 test propri, questo vault report.

## Vincoli preservati

Nessun nuovo run Tester lanciato. Nessuna modifica a `MQL5/`. Nessuna optimization, confronto PF/WR o ricerca economica. Nessuna modifica a ORDER_BLOCK/OB_MIT. Nessuna attivazione di nuove strategie. Nessun artifact storico modificato (`nxs_order_block_replica.py` di Phase 7.13 verificato invariato).

---

```
7.15: CHIUSURA PERIMETRO COMPLETATA
7.16: DIAGNOSI BREVE EA/PYTHON COMPLETATA
  causa isolata: touched-check su barra sbagliata (ieri invece di oggi)
  correzione (solo in questa fase, su copia isolata): match EA 1/8 -> 6/8
  classificazione Python: APPROXIMATION_WITH_KNOWN_GAPS
  proposta: MT5=ground truth, Python=analisi statistica - valida per
    strategie tick-sensibili come ORDER_BLOCK, non necessaria dove
    Python e' gia' un clone fedele (es. BREAKOUT_ACC)
VALIDAZIONE ORDER_BLOCK (A/B, stessi tick reali): INTATTA, MAI RIMESSA
  IN DISCUSSIONE
PROSSIMO: nessuna caccia ulteriore alla parity Python - si passa a
  TSI / shortlist successiva per validazione edge
```
