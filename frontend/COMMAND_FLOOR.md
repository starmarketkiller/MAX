# Visual Floor

Route: `/app/floor`.

È una pagina del frontend React esistente. Usa `AuthProvider`, il router con basename `/app` e l'Axios di `src/lib/api.js`. Non aggiunge un login.

La simulazione resta separata dal pulsante Dati veri. Quel pulsante fa solo GET attraverso il client condiviso. Senza cookie le letture protette rispondono 401 e restano `LIVE_UNAVAILABLE`.

Il marker `NEXUS_COMMAND_CENTER_FRONTEND_INTEGRATED_V1` è spento: la pagina è in questa copia locale, non è stata pubblicata.

Per portarla nel repository principale, copia `frontend/src/command/`, `frontend/src/pages/CommandFloorPage.jsx` e le modifiche a `App.js`, `Dashboard.jsx`, `workspaces.js`, `Sidebar.jsx`, `CommandPalette.jsx`. Non sostituire `/research/control-plane`, che è già il Command Center di ricerca.
