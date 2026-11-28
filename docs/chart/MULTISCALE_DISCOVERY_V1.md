# Multigrafico sincronizzato e Reverse Discovery Lab V1 (NEXUS-CHART-MULTISCALE-DISCOVERY-01)

Stato: **candidato di sviluppo** su `dev/chart-multiscale-discovery-01` (figlio di `dev/chart-geometry-01` `75c2bd5f`, che resta intatto per la review). Non approvato da una review indipendente. Pagina: `/app/discovery` (tab "Discovery Lab" nel workspace Market). Nessun merge, deploy, ordine o accesso a holdout.

## Modalità (solo la prima è implementata)
| Modalità | Stato |
|---|---|
| `RETROSPECTIVE_DISCOVERY` | **implementata** (selezione manuale): il futuro è visibile; schede `DISCOVERY_ONLY` |
| `CAUSAL_REPLAY` | solo contratto: nessun motore, nessuna UI |
| `EMPIRICAL_VALIDATION` | solo contratto: nessun motore, nessuna UI |

`epistemic_mode` e `validation_status` (`NOT_VALIDATED`) sono scritti dal server e non modificabili; l'API rifiuta qualunque campo di segnale, ordine, p-value, edge o preregistrazione. Nessuna soglia sui grandi movimenti: pivot, origine e destinazione li sceglie l'utente. Nessun BUY/SELL/WAIT.

## Multigrafico
1–4 grafici, ciascuno con timeframe indipendente tra quelli **realmente disponibili** nel dataset autorizzato (gli altri sono disabilitati: nessuna richiesta fuori copertura). Sincronizzazione **selettiva**: finestra temporale, crosshair, simbolo (interruttori globali) più un flag `sync` per pane; "vai a" un timestamp centra tutti i pane collegati. Cambiare timeframe a un pane conserva la sua finestra temporale. La paginazione all'indietro usa la stessa API e la stessa guardia di partizione della Chart reale.
I tre livelli di scala geometrica **non** coincidono con tre timeframe: le scale sono una classificazione manuale delle strutture, indipendente dai pane.

## Lab V1: flusso
1. **Periodo storico** (inizio/fine in UTC) o "Tutto lo storico caricato" — è una selezione di vista, non un confine di autorizzazione: l'unica barriera resta la guardia di partizione.
2. **Pivot** (clic su massimo/minimo della candela, tipo correggibile), **origine** e **destinazione** → **Crea scheda**.
3. **Apri sulle scale inferiori**: H4 + M15 + M5 (se il dataset le ha) con finestre proporzionali centrate sull'inversione; **◀ passato prima dell'evento** / ▶; **Vai all'inversione**.
4. Disegno delle geometrie sul pane desiderato e **Associa selezionata** con timing: *osservabile prima* / *formata durante* / *riconosciuta retrospettivamente*.
5. **Strutture e scale**: impulso/correzione/gruppo, scala maggiore/intermedia/minore/non classificata, padre-figlio; origine, ampiezza (prezzo e pip), durata e direzione sono derivate e conservate.
6. Annotazioni, **ipotesi alternative** (stato dell'osservazione: aperta / sostenuta / contraddetta / scartata — mai "validata"), evidenze favorevoli e contrarie, **casi analoghi** (con e senza inversione), classificazione manuale.
7. Salvataggio automatico di scheda e stato della ricerca (disposizione, sincronizzazione, unità, periodo, scheda in studio); riapertura identica; export/import dell'intera ricerca con un solo sha256.
8. **Confronto** fra due schede (descrittivo; vedi limiti).

## Regole epistemiche applicate
* Geometria presente nel grafico ≠ conoscenza disponibile prima dell'evento: ogni collegamento riporta `causal_knowledge = NOT_ESTABLISHED` e `geometry_available_at` reale; **`available_at` non si retrodata**.
* Associazione geometrica ≠ spiegazione causale ≠ edge predittivo: nessuna promozione automatica fra i livelli.
* Il confronto non produce frequenze, percentuali, p-value né "tassi": i casi sono scelti a mano e non sono un campione.
* Import: l'autore dichiarato nel file è conservato ma **non autenticato** (`author_verified=false`); l'importatore effettivo è registrato a parte (`imported_by`). L'hash prova l'integrità, non l'autore.

## Unità
Prezzo, pip, point e tick size restano grandezze **separate**. Convenzione iniziale di ricerca XAUUSD/GOLD: **1 pip = 0,10 di variazione di prezzo**, modificabile (anche vuoto: il righello non inventa pip). Le schede registrano le unità usate alla creazione.

## Limiti dichiarati
* Selezione **manuale** dei movimenti; nessuna rilevazione automatica (contratto soltanto).
* Il collegamento struttura↔geometria esiste nel modello/API (`geometry_ids`) ma la UI non lo espone ancora.
* Stato di validazione: solo `NOT_VALIDATED`; nessuna misurazione statistica (missione successiva con preregistrazione).
* Isolamento tra utenti: provato nel browser con due account reali sullo stesso database; il sistema ha un solo utente amministratore per istanza.
* Sei proiezioni delle candele: non definite, `projection_id` resta `null`.
