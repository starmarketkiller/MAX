# AMD_CONT — approfondimento completo, protocollo NQROS v3.1

Prima strategia scelta per l'approfondimento serio "una alla volta" (deciso
dall'utente il 04/08). Scelta su AMD_CONT invece degli altri candidati
Fase-1 perché ha il campione più ampio (64 trade su H4) tra quelli con
PF/WR già decenti, ed è una scoperta nuova di questa sessione (prima esclusa
per errore di giudizio — "nessun TF pulito", smentito dalla Fase 1
multi-timeframe).

## Domanda guida (prima di ogni fase)

"Sto capendo meglio la strategia o sto solo spingendo il PF?" — applicata ad
ogni step sotto. Un caso di "solo spingere" c'è stato davvero (vedi Fase 4)
ed è stato bocciato dal gate, non nascosto.

## Fase 1 — Baseline multi-TF

Da `multi_tf_baseline.py`: miglior TF = H4, PF 1.62, 64 trade, WR 50.0%,
ExpR 0.358, MaxDD 6.47% (parametri default: SL 1.5×ATR, TP 3.0×ATR, nessuna
gestione).

## Fase 2 — Anatomia

Da `anatomy_analysis.py`, sullo stesso H4 baseline:
- Uscite vincenti: 29 TP + 3 TIME (durata media 25.3 barre)
- Uscite perdenti: 32 SL (durata media 13.2 barre)
- MFE medio vincite: 2.24R — MAE medio vincite: 0.42R (ingresso pulito quando funziona)
- Perdite "segnale sbagliato" (MFE<0.3R): 12/32 (38%)
- Perdite "quasi vincenti" (MFE≥0.5R, andate a favore poi girate): 14/32 (44%)

Lettura: quasi la metà delle perdite erano trade che si muovevano nella
direzione giusta prima di girare — indizio che il bottleneck è più
probabile in gestione posizione (Fase 6) che nel segnale d'ingresso.

## Fase 3 — Toggle (un parametro alla volta, baseline invariato)

| Toggle | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| *(baseline)* | 1.62 | 64 | 50.0 | 0.358 | 6.47 |
| htf_filter=True | 1.41 | 54 | 46.3 | 0.256 | 6.42 |
| **confirm_bars=1** | **2.27** | **22** | **59.1** | **0.60** | **2.13** |
| confirm_bars=2 | 0.00 | 1 | — | — | — |
| cooldown_bars=3 | 1.60 | 60 | 50.0 | 0.354 | 6.47 |
| cooldown_bars=6 | 1.54 | 57 | 49.1 | 0.325 | 7.54 |
| loss_cooldown_bars=3 | 1.58 | 62 | 50.0 | 0.334 | 6.47 |
| loss_cooldown_bars=6 | 1.47 | 60 | 48.3 | 0.28 | 7.54 |

`htf_filter` peggiora (ridondante con il filtro EMA200 già interno a
`sig_amd_cont`). `cooldown_bars`/`loss_cooldown_bars` neutri/negativi.
`confirm_bars=1` unico vincitore netto — ma con -66% di trade (64→22),
segnalato subito come sospetto prima ancora del gate.

## Fase 4 — Robustezza (GATE)

Split cronologico 60% in-sample (dove il toggle è stato trovato) / 40%
out-of-sample (mai visto prima), su H4 (~2 anni totali, capped da Yahoo):

| Config | In-sample | Out-of-sample (costi retail) | Out-of-sample (costi stress) |
|---|---|---|---|
| **confirm_bars=1** | PF 3.39, 13tr, WR 69.2% | **PF 1.40, 9tr, WR 44.4%** | PF 1.32, 9tr, WR 44.4% |
| baseline (nessun toggle) | PF 1.58, 43tr, WR 48.8% | **PF 1.55, 22tr, WR 50.0%** | PF 1.47, 22tr, WR 50.0% |

### Verdetto

**`confirm_bars=1` NON supera il gate — bocciato.** Il salto di PF (1.62→2.27
in Fase 3, PF 3.39 nella metà in-sample) non regge fuori campione (crolla a
1.40, WR torna vicino al baseline 44% vs 69% "trovato"): è il segnale
classico di overfitting su un campione già ridotto a 22 trade, esattamente
il rischio segnalato prima di lanciare il test. **Ipotesi smentita** — va in
Fase 10 (diario), non si riprova in altre forme senza un'ipotesi nuova.

**Il baseline di AMD_CONT (nessun toggle) INVECE supera il gate in modo
pulito**: PF pressoché identico in-sample/out-of-sample (1.58 vs 1.55),
WR quasi identico (48.8% vs 50.0%), e resta positivo anche con costi
aumentati (PF 1.47 out-of-sample stress). Non è un caso di "edge sparito" —
è il toggle che era falso, non la strategia.

**Prosegue in Fase 5** (Money Management) con i parametri di baseline
(SL 1.5×ATR, TP 3.0×ATR, nessun toggle d'ingresso) — non con `confirm_bars=1`.

## Fase 5-10

Da fare.
