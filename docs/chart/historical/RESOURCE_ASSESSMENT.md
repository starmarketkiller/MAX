# Risorse (Fase 06) — misure SOLO su Windows locale

Nessuna misura su Linux/Render (Docker non disponibile sul PC; workflow cumulativo preparato, non eseguito).

| Voce | Misura |
|---|---|
| Store Dukascopy (547 g, 9 TF) | 21.039.900 B (20,4 MiB) |
| Aggiornamento senza rollback / con rollback | ~42 MB / ~63 MB |
| RSS backend a riposo | 64,3 MiB |
| RSS di picco (probe di scala + concorrenza 8×12) | 77,5 MiB; dopo 76,1 MiB |
| RSS con 4 grafici (suite Lab) | 70,1 MiB |
| H4 completo (2.393 barre) | 817 kB, 220 ms |
| D1 completo (464 barre) | 183 kB, 114 ms |
| Paginazione M1 (26 pagine, 26.500 barre totali) | p50 149 ms, p95 224 ms, max pagina 488 kB, totale 8,6 MB |
| Concorrenza 96 richieste (8 client × 12) | 96/96 OK, 9,9 req/s, p50 752 ms, p95 1.244 ms |
| Browser, 4 pane | heap JS 15 MB, 2.170 nodi DOM, 741 listener |

## Osservazioni
- Il lettore apre solo i segmenti mensili necessari: la RAM non dipende dalla lunghezza dello store (nessun caricamento dell'archivio tick; i 61,4 M di tick sono stati letti solo dal costruttore, a flusso, una volta).
- La risposta `/api/chart/ohlc` duplica i dati in `bars` e `candles` e non è compressa (nessun middleware gzip): ~2× overhead di banda. Miglioramento proposto (non applicato: tocca l'API approvata): gzip o rimozione di `candles`.
- Limite Render 512 MiB: margine ampio sui valori locali (≈ 15 %); da confermare su Linux con la fixture di scala (`tools/make_scale_fixture.py`, 547 giorni sintetici) nel workflow cumulativo, che richiede autorizzazione.
- Spazio libero reale su Render **sconosciuto**: criterio ≥ 200 MB liberi prima dell'installazione.
