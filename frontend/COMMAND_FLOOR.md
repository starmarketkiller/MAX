# Visual Floor

Route: `/app/floor`, pull request `#25`.

Usa `AuthProvider`, il router con basename `/app` e l'Axios di `src/lib/api.js`. Non aggiunge un login e non sostituisce `/research/control-plane`.

`NEXUS_COMMAND_CENTER_FRONTEND_INTEGRATED_V1` resta spento. `NEXUS_COMMAND_FLOOR_PR25_REVIEW_READY` significa solo che la pull request è pronta alla revisione, non che il floor sia operativo.

## Letture

Solo due schemi sono stati osservati davvero: `/ready` e `/dukascopy_status`. Un 200 sugli altri endpoint resta non verificato. Un 404 non è `PLANNED`. Una lettura valida non significa che una postazione stia lavorando.

Il polling riusa `useVisiblePolling`: si ferma se la scheda non è visibile e non sovrappone un giro al precedente. Al massimo tre GET insieme. Dopo un 429 le richieste ancora in coda non partono.

## Limiti non bloccanti

Il Council non è dentro l'elenco dei sette reparti: la pagina lo aggiunge. I nomi delle business unit sono etichette previste, non un registro del backend. I gate fermano la catena simulata; non sono permessi del backend.

## Mappa

I collegamenti disegnati sono solo l'assegnazione del passo corrente, dal reparto al worker. L'animazione parte solo se quel passo è in esecuzione. Su schermi sotto i 700 px la mappa usa un disegno più stretto e un testo più grande. Lo sfondo della mappa non fa scorrere la pagina.

Da collaudare su un iPhone vero, perché qui non c'è un browser: trascinare lo sfondo, premere i nodi, usare zoom e controlli, e scorrere la pagina fuori dalla mappa.


## CI e deploy

La CI parte sui push di `main`, `claude/**` e `feature/**`, e sulle pull request verso `main`. `feature/visual-floor-v2` quindi avvia la CI. Safe Deploy è disabilitato manualmente e questa modifica non lo riattiva.
