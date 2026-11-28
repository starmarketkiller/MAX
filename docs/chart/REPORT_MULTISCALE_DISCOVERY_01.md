# REPORT — NEXUS-CHART-MULTISCALE-DISCOVERY-01 (multigrafico sincronizzato e Reverse Discovery Lab V1)

Branch `dev/chart-multiscale-discovery-01` (figlio di `dev/chart-geometry-01` `75c2bd5f`, lasciato intatto per la review), HEAD vedi `MANIFEST_MS.json`. Nessun merge, deploy, ordine, costo o accesso a holdout. `main` `111431ad` invariato; Safe Deploy `disabled_manually`; 0 file dell'infrastruttura approvata modificati (candidato `7bd569ba` preservato); scansione segreti: 0.

## Verdetti
| Voce | Esito |
|---|---|
| MULTICHART_STATUS | **CANDIDATE_READY_FOR_REVIEW** — 1, 3 e 4 grafici provati nel browser; il layout a 2 grafici è implementato ma non cliccato nella verifica |
| TIMEFRAME_SYNC_STATUS | **CANDIDATE_READY_FOR_REVIEW** — finestra, timestamp e sincronizzazione selettiva provati numericamente; crosshair provato solo a vista; sincronizzazione del simbolo **non esercitata** (l'interruttore c'è; il dataset espone solo gli alias GOLD/XAUUSD dello stesso strumento) |
| GEOMETRIC_SCALE_STATUS | **MANUAL_CLASSIFICATION_IMPLEMENTED** — scale maggiore/intermedia/minore, padre-figlio, origine/ampiezza/durata/direzione; il collegamento struttura↔geometria è nel modello/API, non nella UI |
| REVERSE_DISCOVERY_V1_STATUS | **RETROSPECTIVE_DISCOVERY V1 candidata alla review**; `CAUSAL_REPLAY` ed `EMPIRICAL_VALIDATION` restano **solo contratto** |
| PERSISTENCE_STATUS | **PASS** — riapertura in browser nuovo (profilo vuoto): schede, geometrie e stato della ricerca identici campo per campo |
| BROWSER_VERIFICATION_STATUS | **PASS** — Lab 65/65, regressione Geometry-01 64/64, paginazione 5/5 (Edge reale, dataset XM autorizzato) |
| RESOURCE_STATUS | **MISURATO IN LOCALE (Windows), non su Linux/cgroup** — backend RSS 66,7→70,7 MiB, 69,6 MiB con 4 grafici (limite Render 512 MiB); browser: heap JS 8,7–11,3 MiB, 1.580–2.328 nodi DOM |
| REVIEW_STATUS | **NOT_REVIEWED** — solo test dell'autore |
| RENDER_READINESS | **BLOCKED** (invariato) — nessuna verifica Linux/Docker eseguita su questo codice |
| LIVE_TRADING | **NOT_AUTHORIZED** |

## Test
| Livello | Risultato |
|---|---|
| Backend (Chart esistente 165 + geometria 71 + discovery 38) | **274/274** |
| Frontend (suite completa) | **16 suite / 150 test** (139 preesistenti invariati + 11 nuovi) |
| Browser — Lab (`tools/chart_discovery_browser_verify.mjs`) | **65/65**, 0 errori console |
| Browser — regressione Geometry-01 (`tools/chart_geometry_browser_verify.mjs`) | **64/64** |
| Browser — paginazione all'indietro (`tools/chart_discovery_paging_verify.mjs`) | **5/5**: XM M1 da 1.500 a **6.776 barre in 6 pagine**, pari alla catena API indipendente (nessun buco/duplicato in numero), 0 errori |
| Smoke API per Linux (`tools/linux_geometry_smoke.py`) | 11/11 in locale; **non** eseguito su Linux |
Commit: `09446fa8` backend · `32d15aba` workspace, Lab, pip · `9ed721c2` marcatori, correzioni, doc. Evidenze con sha256: `MANIFEST_MS.json` (59 file) in `NEXUS_CHART_GEOMETRY\`; screenshot in `evidence_ms\screens` (21) e `regress_g01\evidence\screens` (28).

## Le 13 prove richieste (dati XM autorizzati `XM-GOLD-2026-11-16-20`)
1 grafico H4 aperto (30 barre reali) · 2 inversione scelta con clic sul massimo, origine e destinazione sulle candele reali · 3 scheda creata (pivot = High reale; ampiezza 58,55 = 585,5 pip; durata 1g 12h; prima ↑ dopo ↓; autore, scoperta, modalità immutabile, `NOT_VALIDATED`) · 4 apertura sincronizzata H4 + M15 + M5 con finestre H4 > M15 > M5 centrate sull'evento e marcatore su ogni scala · 5 passato precedente all'evento (◀ ×2 poi ritorno) · 6 tre geometrie disegnate in tre scale e associate con timing diverso (prima / durante / riconosciuta dopo) · 7 ancoraggio modificato per valore e con maniglia · 8 due ipotesi alternative (una contraddetta), annotazione, evidenze pro/contro, strutture MAJOR→MINOR padre-figlio · 9 salvataggio automatico · 10 riapertura dopo chiusura del browser, identica · 11 confronto con un secondo evento (e con un caso analogo senza inversione) · 12 isolamento con due account reali sullo stesso database: B non vede nulla di A, 404 su eventi/sessione/export di A, scrittura impossibile · 13 regressione Geometry-01 senza fallimenti.
Timeframe provati uno a uno (M1, M5, M15, M30, H1, H4, D1, W1, MN1): tutti caricano dati reali, geometrie proiettate con coordinate finite, nessun errore. Pan col trascinamento, zoom, trascinamento oggetti, pip configurabili (0,10 → 0,01 → vuoto → 0,10) e pannello chiuso di default verificati nella pagina Chart.

## Difetti trovati dalla verifica reale e corretti
* Il righello non si ridisegnava cambiando il pip (le unità non invalidavano il canvas).
* Mancava un marcatore visivo dell'inversione: aggiunto (pieno = inversione, vuoto = caso senza inversione, arancione = scheda in studio).
* Nei controlli: ipotesi errate su scala prezzi automatica nel pan, selettori troppo larghi, disclaimer contato come dato; corretti nello script, non nel prodotto.

## Percentuali (denominatori espliciti — criteri funzionali delle Fasi 01–06 e 08)
| Fase | Criteri | Verificati nel browser reale | Solo test / progetto | Non esercitati |
|---|---|---|---|---|
| 01 chiusura Geometry | 9 | 8 | 1 (proiezioni non definite: campo riservato) | 0 |
| 02 multigrafico | 12 | 10 | 0 | 2 (layout a 2 grafici, sync simbolo) |
| 03 scale | 6 | 4 | 2 (nessuna teoria d'onda; geometria↔struttura solo API) | 0 |
| 04 Lab V1 | 13 | 12 | 1 (nessuna soglia imposta) | 0 |
| 05 scheda evento | 22 | 21 | 1 (immutabilità lato server, test) | 0 |
| 06 confronto | 12 | 11 | 0 | 1 (classe LIQUIDITY_SPIKES senza dati nel confronto) |
| 08 prove | 13 | 13 | 0 | 0 |
| **Totale** | **87** | **79 (90,8%)** | 4 | 4 |
Implementato: 87/87 dei criteri sopra (con i 4 "non esercitati/solo API" dichiarati). Fase 07 (compatibilità futura) = contratto rispettato (test); motore replay/validazione: 0% per scelta. Fase 09: 3 su 4 completate (riconciliazione 231→230, provenienza `74ad2138`, preparazione Linux); la **registrazione dell'approvazione indipendente di FIX-02 è solo "dichiarata dall'owner"** perché il documento di review non è in mio possesso. Review indipendente: 0%.

## Limiti e rischi residui
* **Lo storico H4 realmente disponibile è corto:** 30 barre per XM (5 giorni) e **61 barre contigue autorizzate** per il dataset Dukascopy nello store locale (2023-02-06→02-17, `has_more` falso): il metodo "storico H4 completo" non è ancora esercitabile su vera scala. La **paginazione all'indietro è invece provata** su un timeframe con più pagine (XM M1: 6.776 barre), non su H4.
* Selezione manuale; nessuna rilevazione automatica; nessuna soglia di ampiezza/durata/scala.
* Le finestre di apertura (70 barre prima, 30 dopo, per scala) sono un mio default, non una definizione dell'owner.
* Il tipo di pivot (massimo/minimo) è dedotto dal campo della candela ed è correggibile prima della creazione.
* `available_at` delle geometrie è il tempo reale di creazione (mai retrodatato): in un futuro replay una geometria disegnata oggi non sarà visibile prima; le schede non sono mai input di replay.
* Misure di risorse: backend su Windows (RSS di processo), non cgroup Linux; il limite Render si verifica solo col workflow Linux (non eseguito, serve autorizzazione per un push `infra/**`).
* Sei proiezioni delle candele: ancora non definite.
* Il sistema ha un solo utente per istanza: l'isolamento è provato con due istanze sullo stesso DB.

## Prossima attività suggerita
Review indipendente di `chart_discovery.py`, `GeometryLayer.jsx`, `ChartPane.jsx`; uno store H4 autorizzato più lungo (lo store Dukascopy locale contiene solo 61 barre H4) per esercitare il metodo su vera scala; esecuzione Linux/Docker (autorizzazione); poi navigazione guidata dei grandi movimenti (rilevazione) e, in missioni separate, `CAUSAL_REPLAY` ed `EMPIRICAL_VALIDATION` con preregistrazione.
