# Chart NEXUS — strumenti geometrici e memoria grafica (CHART-GEOMETRY-01)

Stato: **candidato di sviluppo** sul branch `dev/chart-geometry-01` (base `7bd569ba`). Non approvato da una review indipendente. Nessun merge su `main`, nessun deployment.

## Cosa fa
Sulla Chart reale (`/app/chart`) l'utente può tracciare e conservare geometrie manuali:
linea orizzontale, verticale, diagonale, ray, linea estesa, rettangolo, fascia di prezzo, annotazione testuale, Fibonacci retracement/extension, righello prezzo/tempo.

* **Coordinate canoniche = (tempo, prezzo) del dato.** I pixel sono solo una proiezione ricalcolata a ogni zoom, pan, ridimensionamento, cambio timeframe.
* **Ancoraggi**: liberi oppure agganciati a Open/High/Low/Close di una candela (`ref.kind=CANDLE`, `bar_t`, `field`); modifica numerica di orario e prezzo; passo candela precedente/successiva; maniglie trascinabili. Estendere una linea (`style.extend`) non altera le origini.
* **Forma ≠ significato.** `type` è la forma; `semantic.class` è l'etichetta attribuita dall'utente: Diagonale BUY/SELL, Key level (chiusure congruenti), Livello di liquidità (spike congruenti), Zona BUY TO SELL, Zona SELL TO BUY, Spazio interno tra impulsi, Zona di possibile reazione, Zona di possibile continuazione. Una geometria **non è un segnale** e non genera ordini; il backend rifiuta qualunque campo ordine/segnale.
* **Interazione**: selezione, spostamento rigido, ridimensionamento per maniglia, modifica da ispettore (nome, descrizione, colore, spessore, stile, riempimento, estensione, livello), eliminazione annullabile, **undo/redo** (Ctrl+Z / Ctrl+Y), blocco oggetto, visibilità, livelli (visibilità/blocco).
* **Memoria persistente per utente** (SQLite, append-only per revisioni): `geometry_id`, dataset, fonte, simbolo, timeframe originario, orologio degli orari (`clock_basis`), tipo, ancoraggi, autore (utente autenticato, mai dal client), origine `MANUAL`, `created_at`, `available_at`, `revision`, `status` (`ACTIVE`/`INVALIDATED`/`ARCHIVED`), stile, annotazioni, collegamenti ad altre geometrie. Ogni modifica è una nuova revisione; l'eliminazione archivia (reversibile), la storia non si perde.
* **Sessioni**: più analisi per utente; export JSON canonico con `sha256`, import come nuova sessione (file manomesso rifiutato, import atomico).
* **Isolamento**: ogni query è filtrata per utente; un'altra utenza riceve `404 SESSION_NOT_FOUND` identico a "non esiste".

## API (`/api/chart/geometry/...`)
`GET vocabulary` · `GET|POST sessions` · `GET|PUT sessions/{sid}` · `POST sessions/{sid}/objects` · `GET|PUT sessions/{sid}/objects/{gid}` (`?history=true`) · `POST …/{gid}/archive|restore` · `PUT sessions/{sid}/layers/{lid}` · `GET sessions/{sid}/export` · `POST import`.
Le scritture richiedono `expected_revision` (409 `REVISION_CONFLICT` se l'oggetto è cambiato) e l'autenticazione/CSRF delle altre mutazioni.

## Limiti dichiarati
* **Le sei proiezioni delle candele non sono definite dall'owner**: `anchors[].ref.projection_id` è riservato, deve restare `null` (l'API rifiuta altro). Nessuna teoria imposta; è predisposta solo la rappresentazione (campo e `field` OHLC).
* K1/K2 (key level da chiusure), rango dei pivot, β come regola operativa restano **candidati o da confermare**: l'etichetta è manuale e non valida nulla.
* Pip: il righello mostra Δprezzo, %, barre e durata; non usa pip perché la convenzione è ancora da definire.
* Contesto futuro (tre scale, replay causale, eventi di contatto, Jarvis): solo contratto riservato in `server/chart_geometry_future_context_v1.json`; la memoria empirica è un dominio separato e non è implementata.
* Il pannello laterale può coprire le barre più recenti: si chiude con ☷.
* Verificato nel browser reale su M15, H1, H4 e M5; M1, M30, D1, W1, MN1 non sono stati esercitati con geometrie.
* Lo stato `INVALIDATED` è previsto dal modello e dall'API ma non ha ancora un comando nella UI.
* Orario assoluto: l'orologio XM resta `TERMINAL_CLOCK` (offset broker non verificato); gli orari sono mostrati con la dicitura del dataset.

## Verifica
`server/tests/test_chart_geometry.py` (backend), `frontend/src/lib/geometry/*.test.js` (matematica, hook), `tools/chart_geometry_browser_verify.mjs` (browser reale, Edge/CDP, grafico XM autorizzato `XM-GOLD-2026-11-16-20`).
