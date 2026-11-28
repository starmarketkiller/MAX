# NEXUS-CHART-HISTORICAL-EXPANSION-01 — report finale

Ramo `dev/chart-historical-expansion-01` (base `f264a705`). Nessun merge, deployment, ordine, costo aggiuntivo, accesso a holdout o avvio di MetaTrader.

| Voce | Stato |
|---|---|
| HISTORICAL_INVENTORY_STATUS | COMPLETO (`HISTORICAL_INVENTORY.md`); matrice esistente/accessibile/autorizzato/usabile |
| DATA_AUTHORIZATION_STATUS | 547 giorni Dukascopy (`development_discovery`, 2023-02-04→2024-08-03) già autorizzati; **nessuna nuova autorizzazione richiesta**; produzione richiede un record `EXPLICIT_WINDOWS` approvato dall'owner (modello + 4 test) |
| HISTORICAL_STORE_STATUS | COSTRUITO e VERIFICATO: 20,4 MiB, 9 TF, verificatore indipendente PASS 13/13 |
| DATA_QUALITY_STATUS | PASS con limiti: UTC e calendario NON verificati, solo bid, D1/W1/MN1 mai COMPLETE |
| H4_COVERAGE | 2.393 barre (1.884 = 78,7 % COMPLETE), 2023-02-05 → 2024-08-02 (vs 61 prima) |
| MULTITIMEFRAME_COVERAGE | 9/9 TF; M1 530.331 (100 % COMPLETE), M5 106.125, M15 35.378, M30 17.690, H1 8.851, D1 464, W1 79, MN1 19 |
| BROWSER_STATUS | storico 43/43; regressioni Lab 65/65, Geometry-01 64/64, paginazione 5/5; frontend 153/153; backend 291/291 |
| RESOURCE_STATUS | solo Windows: RSS 64–78 MiB, H4 completo 817 kB/220 ms (`RESOURCE_ASSESSMENT.md`) |
| LINUX_RUNTIME_STATUS | workflow cumulativo + fixture di scala PREPARATI, **NON ESEGUITI** (Docker assente, push su `infra/chart-cumulative/**` non autorizzato) |
| REVIEW_STATUS | NOT_REVIEWED (solo verifica dell'autore) |
| RENDER_READINESS | BLOCKED (checklist §6 aperta) |
| LIVE_TRADING | NOT_AUTHORIZED |

## Consegnato
Costruttore e verificatore dello store (`tools/build_historical_store.py`, `verify_historical_store.py`), sonda di scala, navigazione ancorata e paginazione all'indietro, striscia panoramica H4 con eventi, finestre pre/post configurabili, collegamento struttura↔geometria in UI, due pane, LIQUIDITY_SPIKES in confronto, sincronizzazione simbolo, workflow cumulativo e checklist.
Correzioni trovate sui dati estesi: race di `focusRange` con paginazione, simbolo/TF effettivi, finestre per scala dopo "vai all'evento" (propagazione sospesa 4 s).

## Limiti
Orologio/calendario Dukascopy non verificati; feed non equivalente a XM; approvazione di CHART-INFRA-FIX-02 solo dichiarata dall'owner; cartella pytest sintetica rimasta nella storia (commit `4fb2cdae`, nessun force-push); dopo "vai all'evento" il pan non propaga per 4 s; nessun rilevatore automatico di inversioni (come richiesto); nessuna misura Linux.
