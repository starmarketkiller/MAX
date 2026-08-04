# SILVER_BULLET — approfondimento, protocollo NQROS v3.1

Seconda strategia del ciclo completo (04/08), scelta dall'utente per
riusare l'infrastruttura e le ipotesi già trovate su AMD_CONT (stessa
famiglia: gate a sessione via `_sweep_ext_at`/`_session_amd_series`).
**Riuso dichiarato, non copiato**: ogni ipotesi presa da AMD_CONT è stata
ri-testata da zero su questo segnale, non assunta.

## Fase 1 — Baseline

H4 (unico TF con campione utilizzabile, come per AMD_CONT — stesso limite
strutturale: SILVER_BULLET richiede il gate a killzone orario, che su
W1/D1 non si distingue). Default (SL1.5/TP3.0): **PF 1.37, 65 trade, WR
43.1%, ExpR 0.223, MaxDD 10.48%**.

## Fase 2 — Anatomia (già raccolta in batch precedente, riusata)

- Uscite vincenti: 27 TP + 1 TIME (durata media 22.5 barre)
- Uscite perdenti: 36 SL + 1 TIME (durata media 15.7 barre)
- MFE medio vincite: 2.41R — MAE medio vincite: 0.4R
- Perdite "segnale sbagliato" (MFE<0.3R): 15/37 (41%)
- Perdite "quasi vincenti" (MFE≥0.5R): 15/37 (41%)

Stesso pattern di AMD_CONT (~41-44% perdite "quasi vincenti") — ipotesi
riusata: probabile beneficio da SL/TP più larghi, DA VERIFICARE (non
assumere solo perché ha funzionato sulla strategia gemella).

## Fase 3 — Toggle (un parametro alla volta)

| Toggle | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| *(baseline)* | 1.37 | 65 | 43.1 | 0.223 | 10.48 |
| **htf_filter=True** | **1.62** | 32 | 46.9 | 0.348 | **3.97** |
| confirm_bars=1 | 0.36 | 12 | 16.7 | -0.565 | 6.65 |
| cooldown_bars=3 | 1.32 | 64 | 42.2 | 0.197 | 10.48 |
| loss_cooldown_bars=3 | 1.37 | 65 | 43.1 | 0.223 | 10.48 |

A differenza di AMD_CONT (dove `htf_filter` era ridondante con un filtro
EMA200 già interno), `sig_silver_bullet` non ha alcun filtro di trend
interno — solo ora-killzone + sweep confermato. Qui `htf_filter` aggiunge
valore reale non ridondante. `confirm_bars` di nuovo distruttivo (stesso
motivo di AMD_CONT: segnali "evento", non "stato").

## Fase 4 — Robustezza (GATE) — risultato con una complicazione onesta

| | PF | Trade | WR% | ExpR | MaxDD% |
|---|---|---|---|---|---|
| **Senza filtro** — in-sample | 0.87 | 39 | 33.3 | -0.082 | 10.48 |
| **Senza filtro** — out-of-sample | 2.46 | 26 | 57.7 | 0.680 | 2.10 |
| **htf_filter=True** — in-sample | 0.98 | 17 | 35.3 | -0.001 | 3.97 |
| **htf_filter=True** — out-of-sample (costi retail) | 2.98 | 16 | 62.5 | 0.819 | 2.10 |
| **htf_filter=True** — out-of-sample (costi stress) | 2.84 | 16 | 62.5 | 0.789 | 2.18 |

**Non un pass pulito come AMD_CONT.** Il PF esplode dalla prima alla
seconda metà **in ENTRAMBE le config**, con o senza filtro — segno di un
forte cambio di regime di mercato nella seconda metà dello storico H4
disponibile (~2026), non un effetto specifico del filtro. Il filtro
aggiunge comunque un delta incrementale reale (+2.00 vs +1.59 di
miglioramento, e parte da un livello meno negativo: 0.98 vs 0.87) — ma la
lettura onesta è "htf_filter probabilmente aiuta, ma il segnale è confuso
da un effetto di periodo più grande di quanto vorrei". Verdetto: **pass
condizionato**, non pulito. Da ri-controllare quando ci sarà più storico.

## Segmentazione per killzone (ICT: London 10-11 GMT vs NY 14-15 GMT)

Sui 32 trade di `htf_filter=True`:

| Killzone | Trade | WR% | PF | NetPnL |
|---|---|---|---|---|
| London (10-11 GMT) | 17 | 58.8 | **2.52** | 1.183 |
| NY (14-15 GMT) | 15 | 33.3 | **0.95** | -48 |

London killzone chiaramente più forte. Isolarla con `session_filter=
{"LONDON"}` (che nel motore corrisponde esattamente alla finestra 10-11,
dato il gate orario già interno a `sig_silver_bullet`):

PF 2.51, **17 trade**, MaxDD 2.25%. OOS (split 9/9): in-sample PF 1.32,
out-of-sample **PF 6.42**.

### Scartato deliberatamente

PF 6.42 è esattamente il tipo di numero segnalato nella lezione
cross-strategia #4 (da AMD_CONT): spettacolare ma su **9 trade** per metà
— troppo poco per significare qualcosa, indipendentemente da quanto sia
bello il numero. Impilare `htf_filter` + isolamento killzone ha ridotto il
campione da 65 a 17 trade totali: è "spingere il PF" per accumulo di
filtri, non "capire meglio" — la domanda guida del protocollo lo
segnalerebbe esplicitamente. **Non adottato.**

## Config corrente (in attesa di più dati prima di rifinire oltre)

H4, `htf_filter=True`, SL/TP di default (1.5/3.0) — non ancora ottimizzati
in Fase 6. PF 1.62/32 trade, pass condizionato in Fase 4 (confuso da
effetto di periodo). **Non procedere con l'isolamento per killzone finché
il campione non cresce** (più storico, vedi backlog).

## Fase 5-10

Da fare — sospeso in attesa di decidere come trattare il pass condizionato
di Fase 4 prima di continuare a ottimizzare sopra una base già incerta.
