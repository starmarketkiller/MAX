# Independent Validation Integrity — tassonomia v1 (Phase 5.5 sec.4)

Ogni conclusione futura DEVE dichiarare quale di queste 6 categorie usa. Nessuna conclusione può auto-dichiararsi `TRUE_HOLDOUT` se il periodo di validazione ha, anche indirettamente, influenzato quale ipotesi è stata scelta per essere promossa/riportata.

## Definizioni

| Categoria | Definizione | Requisito chiave |
|---|---|---|
| `TRUE_HOLDOUT` | Il periodo/dataset di validazione non è mai stato osservato, nemmeno in aggregato, prima che l'ipotesi fosse congelata E selezionata come quella da riportare | La SCELTA di quale ipotesi promuovere deve precedere qualunque calcolo sul periodo di validazione |
| `TEMPORAL_HOLDOUT` | Split cronologico dichiarato ex-ante fra discovery e validation, sullo STESSO dataset/fonte | Valido come disciplina di split, ma NON garantisce l'assenza di contaminazione nella fase di selezione (vedi CONTAMINATED_VALIDATION) |
| `CROSS_FEED_VALIDATION` | Stesso segnale/ipotesi testato su una fonte dati diversa (es. Dukascopy vs broker) per lo stesso tipo di periodo | Il segnale deve essere stato congelato PRIMA di vedere la nuova fonte dati |
| `CROSS_ENGINE_VALIDATION` | Stesso segnale testato su un motore di esecuzione diverso (es. Python backtest vs MT5 nativo) | Idem: segnale congelato prima del nuovo motore |
| `CONTAMINATED_VALIDATION` | Il periodo/dataset di validazione ha influenzato, anche indirettamente, quale ipotesi è stata selezionata o riportata come interessante | Si applica ogni volta che un umano (o un processo) guarda I RISULTATI DI VALIDAZIONE di più candidati prima di scegliere quale evidenziare |
| `DISCOVERY_REUSE` | La "validazione" usa lo stesso campione (in tutto o in parte) usato per la scoperta | Nessun valore probatorio indipendente |

## Classificazione delle conclusioni Phase 5

| Conclusione | Categoria assegnata | Motivazione |
|---|---|---|
| **RECLAIM / "SWEEP+RECLAIM" come headline finding** | **`CONTAMINATED_VALIDATION`** | Lo split 70/30 era dichiarato ex-ante (buona pratica, di per sé `TEMPORAL_HOLDOUT`) — MA `edge_discovery.py` ha calcolato discovery E validation per tutte e 14 le ipotesi nella STESSA esecuzione, e RECLAIM è stata scelta come headline/EDGE_COMPONENT **dopo aver visto** che era l'unica ipotesi positiva su ENTRAMBI gli split. La decisione di quale ipotesi riportare è stata quindi informata dai numeri di validazione — la validazione non è "pulita" per lo scopo specifico della promozione. Questo è esattamente il motivo per cui il Hypothesis Registry (sec.1) marca RECLAIM `POST_HOC_CANDIDATE` e non `SUPPORTED`. |
| Le altre 8 ipotesi event-alone (BREAKOUT, SWEEP da solo, RETEST, ecc.) | `TEMPORAL_HOLDOUT` | Split ex-ante rispettato; nessuna decisione di promozione basata su un confronto post-hoc fra candidati (sono risultati negativi, non selezionati per essere "il migliore") |
| Le 5 interazioni predefinite | `TEMPORAL_HOLDOUT` | Idem — dichiarate ex-ante, nessuna selezionata a posteriori come "vincitrice" (tutte negative/insufficienti) |
| **SAR — validazione MT5-nativa su Dukascopy (Phase 5.L)** | **`CROSS_FEED_VALIDATION`** (pulita, non contaminata) | Il segnale SAR (parametri, soglie) era congelato da fasi precedenti del progetto, PRIMA che questo test esistesse o che il dataset Dukascopy fosse anche solo costruito. Nessuna selezione post-hoc: SAR non è stata scelta perché "sembrava promettente" nel nuovo dataset, è stata testata perché era già l'unica ipotesi in coda per questo tipo di verifica (task L, esplicitamente richiesto dall'utente prima di vedere alcun risultato) |
| SAR — cross-check Python su Dukascopy pre-2023 (Phase 4, riferimento storico) | `CROSS_FEED_VALIDATION` + `CROSS_ENGINE_VALIDATION` (combinato, pulita) | Stessa logica: segnale congelato, fonte dati E motore di esecuzione entrambi diversi da dove il segnale era stato scoperto |
| Strategy Foundry Phase 2 → Phase 3 (VOLATILITY_BREAKOUT_CONFIRMED, riferimento storico Phase 3/4) | `TEMPORAL_HOLDOUT` (buona pratica già riconosciuta in Phase 4 come "modello di metodologia corretta") | Split 70/30 dichiarato ex-ante, nessuna promozione contaminata riportata all'epoca |

## Regola operativa per il futuro

Prima di scrivere qualunque `Research Decision Card` (sec.16), rispondere esplicitamente: **"la decisione di riportare/promuovere questa ipotesi è stata presa PRIMA o DOPO aver visto i numeri di validazione di TUTTI i candidati del batch?"** Se DOPO → la categoria massima ammissibile è `CONTAMINATED_VALIDATION`, mai `TRUE_HOLDOUT` né una validazione "pulita", indipendentemente da quanto rigoroso fosse lo split originale. L'unico modo per ottenere un vero `TRUE_HOLDOUT` in futuro è congelare l'ipotesi SINGOLA (non un batch) e il criterio di successo PRIMA di calcolare qualunque statistica sul periodo di validazione, poi calcolare la validazione una sola volta, per quella sola ipotesi.
