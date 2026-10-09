# Visual Floor

Route: `/app/floor`, pull request `#25`.

Usa `AuthProvider`, il router con basename `/app` e l'Axios di `src/lib/api.js`. Non aggiunge un login e non sostituisce `/research/control-plane`.

`NEXUS_COMMAND_CENTER_FRONTEND_INTEGRATED_V1` resta spento. `NEXUS_COMMAND_FLOOR_PR25_REVIEW_READY` significa solo che la pull request è pronta alla revisione, non che il floor sia operativo.

## Letture

Solo due schemi sono stati osservati davvero: `/ready` e `/dukascopy_status`. Un 200 sugli altri endpoint resta non verificato. Un 404 non è `PLANNED`. Una lettura valida non significa che una postazione stia lavorando.

Il polling riusa `useVisiblePolling`: si ferma se la scheda non è visibile e non sovrappone un giro al precedente. Al massimo tre GET insieme. Dopo un 429 le richieste ancora in coda non partono.

## Limiti non bloccanti

Il Council non è dentro l'elenco dei sette reparti: la pagina lo aggiunge. I nomi delle business unit sono etichette previste, non un registro del backend. I gate fermano la catena simulata; non sono permessi del backend.

## Board

La vista principale è la board della preview: stanze, postazioni e ritratti in `public/bots`. La mappa a cerchi resta solo sul pulsante Mappa. LIVE non disegna la board. Il Council resta nella striscia sotto le stanze, come nella preview. Non c'è un browser in questo ambiente, quindi il confronto con lo screenshot resta da fare a occhio dopo il deploy.

## Diagnostica LIVE

La sezione Diagnostica LIVE legge solo i GET già usati dal Floor. `/ready` e `/dukascopy_status` mostrano i campi dello schema verificato, senza path né segreti. Un 401 è `UNKNOWN` / `AUTH_REQUIRED`, mai `BLOCKED`. Un 200 del ready non rende operative le 119 postazioni. Gli altri endpoint, anche con 200, restano schema non verificato e il payload non viene mostrato. La simulazione non entra in questa sezione.

## CI e deploy

La CI parte sui push di `main`, `claude/**` e `feature/**`, e sulle pull request verso `main`. Questo branch è `feature/floor-live-diagnostics`, quindi un push avvia la CI. Safe Deploy è disabilitato manualmente e questa modifica non lo riattiva.
