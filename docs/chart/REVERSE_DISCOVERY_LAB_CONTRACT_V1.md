# NEXUS Reverse Discovery Lab — contratto e posizionamento nel master plan Chart

Stato: **solo contratto** (nessun motore, nessuna UI). Macchina-leggibile: `server/reverse_discovery_lab_contract_v1.json`, verificato da test in `server/tests/test_chart_geometry.py`. Missione dedicata futura: **NEXUS-REVERSE-DISCOVERY-LAB-01**.

## Metodo
Osservare uno storico H4 completo → identificare i cambi di direzione più significativi → tornare alle origini → investigare geometrie, strutture e fenomeni precedenti l'evento.

## Tre modalità (non si mescolano)
| Modalità | Futuro visibile | Scopo | Vieta |
|---|---|---|---|
| `RETROSPECTIVE_DISCOVERY` | sì | individuare fenomeni, formulare ipotesi | statistiche presentate come validazione; promuovere un'ipotesi a causale/predittiva; alimentare il replay con coordinate o soglie tarate sul futuro |
| `CAUSAL_REPLAY` | no: oggetto visibile solo se `available_at <= tempo simulato`, barre solo se chiuse | simulare ciò che era conoscibile | leggere dati dopo il tempo simulato; mostrare qualunque record creato in retrospettiva; retrodatare `available_at` |
| `EMPIRICAL_VALIDATION` | solo nella valutazione | valutare ipotesi **preregistrate** | modificare l'ipotesi dopo i risultati; riusare la finestra di scoperta; accedere a `locked_validation`/`final_holdout` |

Flusso a senso unico: retrospettiva → **testo dell'ipotesi preregistrata** → validazione. Mai retrospettiva → replay come dati. Nessuna modalità accede agli holdout: vale la guardia di partizione esistente, non una regola d'interfaccia.

## Tre livelli epistemici (non si promuovono a vicenda)
`GEOMETRIC_ASSOCIATION` (descrittivo) · `CAUSAL_EXPLANATION_CANDIDATE` (ipotesi dell'utente, non verificata) · `PREDICTIVE_EDGE_VALIDATED` (solo da `EMPIRICAL_VALIDATION`, con preregistrazione, controlli, casi analoghi senza inversione e correzione per prove multiple).

## Le 12 capacità e cosa offre già Geometry-01
| # | Capacità | Entità riservata | Geometry-01 |
|---|---|---|---|
| 1 | Selezione intervalli autorizzati | — | riuso guardia di partizione |
| 2 | Catalogo grandi movimenti (manuale, poi automatico) | MoveCatalogEntry | geometrie manuali in (t, price) |
| 3 | Classificazione ampiezza/durata/scala | — | **soglie e scale non definite**: decisione owner |
| 4 | Navigazione verso le inversioni | ReversalPoint | go-to tempo/prezzo già nella Chart |
| 5 | Geometrie precedenti l'evento | PreEventGeometryLink | `links[]`, `available_at` |
| 6 | Esplorazione multiscala sincronizzata | — | stesse coordinate su ogni TF; **sincronizzazione = missione prerequisito** |
| 7 | Spiegazioni manuali | Explanation | descrizione testuale, non causale |
| 8 | Confronto con le 83 strategie | StrategyKnowledgeLink | solo lettura del registro (0 validate); non convalida né è convalidata |
| 9 | Replay causale | — | `available_at`; **replay = missione prerequisito** |
| 10 | Archivio evidenze | EvidenceArchiveItem | `evidence[]`, export/import con sha256 |
| 11 | Casi analoghi senza inversione | AnalogCase | nessuno; regola di selezione definita **prima** |
| 12 | Misurazione statistica | StatisticalMeasurement | nessuno (solo `EMPIRICAL_VALIDATION`) |

## Compatibilità architetturale con Geometry-01 (senza ampliarlo)
* Già presenti: coordinate di dato, `available_at`/`created_at`, origine `MANUAL`, `links[]`, `evidence[]`, revisioni append-only, hash di sessione, isolamento per utente, dominio `GRAPHICAL` separato.
* Campi **riservati e rifiutati** dall'API oggi: `epistemic_mode`, `discovery_session_id`, `move_id`, `reversal_id`, `explanation`, `hypothesis_id`, `preregistration_hash` (test dedicati).
* Alla futura implementazione: `epistemic_mode` immutabile; il caricatore del replay esclude **per costruzione** ogni record `RETROSPECTIVE_DISCOVERY`; in replay `available_at` = tempo simulato di creazione.
* Default sicuro attuale: `available_at` = tempo reale di creazione, quindi una geometria disegnata oggi su dati passati **non** comparirebbe in un replay a tempo simulato passato (fallisce in sicurezza, senza perdita di futuro; testato).

## Sequenza
Geometrie (fatto, in review) → memoria (fatto, in review) → **navigazione multiscala sincronizzata** → **replay causale** → *Reverse Discovery Lab*. Prima di avviarla servono le decisioni dell'owner su soglie di ampiezza/durata/scala e sulle sei proiezioni delle candele.
