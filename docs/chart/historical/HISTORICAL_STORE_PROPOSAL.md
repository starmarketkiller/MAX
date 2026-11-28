# Proposta e scelta dello store esteso (Fase 02)

## Scelta: la partizione `development_discovery` del Phase 7, già autorizzata
| Criterio | Esito |
|---|---|
| Periodo | **2023-02-04 → 2024-08-03** (547 giorni, ~18 mesi) |
| Profondità | **H4 2.393 barre** (vs 30 XM / 61 Dukascopy locale); M1 530.331; tutti i 9 timeframe |
| Approfondimento fino a M1 | sì, sugli stessi eventi (M1, M5, M15, M30, H1 dalla stessa serie) |
| Holdout | **nessuna sovrapposizione**: l'ultimo giorno è 2024-08-03, la partizione successiva (internal validation) inizia il 2024-08-04; locked validation e holdout finale sono più avanti e non sono stati toccati |
| Nuove autorizzazioni | **nessuna**: finestra già autorizzata dalla decisione D2 (`allowed_segment_names: ["development_discovery"]`) |
| Riuso | dati già sul PC; **nessun nuovo download, nessuna duplicazione dei tick** (si leggono i file giornalieri esistenti, guardia interrogata prima di ogni file) |
| Dimensione | **20,4 MB** per l'intero store (Dukascopy + XM) — compatibile con il disco nominale di Render |
| Limiti | feed Dukascopy (solo bid), UTC e calendario non verificati in modo indipendente; **non è il feed XM** e non va mescolato con esso; un solo tipo di regime (2023–metà 2024) |

Perché non altre fonti ora:
* **XM**: solo 5 giorni esportati (16–20/11/2026). Gli storici MT5 `.hcc` sarebbero pluriennali ma sono illeggibili senza MetaTrader/un export e non sono autorizzati → blocco esatto, vedi sotto.
* **Phase 5 / Phase 6 / cache M5**: spesi, holdout o attraversano finestre sigillate; nessun record di autorizzazione.

## Richieste di autorizzazione (NON presentate ora: non necessarie per la metodologia attuale)
Elenco esatto, da decidere dall'owner solo se la ricerca lo richiede:
| Opz. | Dati | Partizione / periodo | Uso richiesto | Conseguenza / rischio |
|---|---|---|---|---|
| X1 | Dukascopy Phase 7 | `development_internal_validation` 2024-08-04 → 2025-05-03 (273 giorni, 50,6 M tick) | solo vista retrospettiva nel Chart (`RETROSPECTIVE_DISCOVERY`), nessuna statistica | **sconsigliata**: è la partizione destinata alla validazione interna dei candidati; ipotesi formulate guardandola non sarebbero più validabili lì. Servirebbe un nuovo record in `chart_authorization.json` e una nuova costruzione dello store (+~10,5 MB) |
| X2 | Archivio Phase 5 (`dukascopy_phaseH`) | 2019-02-03 → 2022-02-03 (1.097 giorni) | solo vista retrospettiva | allunga lo storico di 3 anni; le finestre sono "spese" per la validazione (Phase 5/H004): vanno etichettate; richiede un nuovo `dataset_id`, un record di autorizzazione e un nuovo store (~+42 MB stimati) |
| X3 | Storico XM MT5 (`.hcc`) | da definire dall'owner | export da script MQL5 in un'istanza **isolata** di MetaTrader (decisione D1) | richiede avvio di MetaTrader (non autorizzato), verifica del `clock_basis` del broker (+7.200.307 ms osservati nel 2026) e un nuovo dataset: feed diverso da Dukascopy |
| — | `locked_validation`, `final_holdout`, archivio Phase 6 | — | — | **mai richiesti**: sigillati o holdout |

## Dimensionamento dello store (misurato)
Dukascopy 547 giorni: 21.039.900 byte (M1 15,9 MB; M5 3,2; M15 1,1; M30 0,53; H1 0,27; H4 0,07; D1 0,014; W1/MN1 trascurabili) → **≈38 KB per giorno di calendario**. Stima per X1: +10,5 MB; per X2: +42 MB. Anche con X1+X2 lo store resterebbe < 100 MB.
