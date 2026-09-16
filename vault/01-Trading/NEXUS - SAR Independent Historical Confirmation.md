# NEXUS — Phase G: SAR Independent Historical Confirmation

Base: commit `e557b22` (First Serious 3Y Validation, approvato). MACD chiuso, nessun rescue. Nessun BUY/SELL cambiato, nessun SL/TP cambiato, nessuna ottimizzazione, nessuna sessione/TF/filtro modificato.

**Esito anticipato**: il punto 3 del task (finestra indipendente MT5 real-tick pre-2023-09) si è rivelato **impossibile da soddisfare alla lettera** per un limite di dati strutturale scoperto durante l'esecuzione (§3). Riportato con piena trasparenza, non aggirato.

---

## 1. Historical contamination audit

Ricostruiti tutti i test SAR reperibili nel vault (97 documenti menzionano "SAR", filtrati ai casi che testano/backtestano effettivamente SAR su dati storici reali, non semplici citazioni o letture di codice).

| Periodo | Motore | Config SAR | Motivo | Risultato chiave | Ha influenzato decisioni? | Classificazione |
|---|---|---|---|---|---|---|
| 2026-06-01→2026-08-01 (probe 2 mesi) | MT5 real-tick | Frozen (attuale) | Probe fattibilità Model=4 | 26 trade | Sì — ha validato la fattibilità del real-tick per le fasi successive | **PREVIOUSLY_OBSERVED** (ma post-2023-09, non rilevante per la finestra indipendente) |
| 2026-03-01→2026-09-01 (Fase D) | MT5 real-tick | Frozen | Baseline Fast Structural | 41 trade, PF1.19, DD6.36% | Sì — baseline congelata di riferimento | **PREVIOUSLY_OBSERVED** |
| 2025-09-01→2026-03-01 (Fase E) | MT5 real-tick | Frozen | Replica temporale indipendente (6 mesi) | 40 trade, PF1.90, DD4.44% | Sì — ha confermato stabilità, sbloccato READY | **PREVIOUSLY_OBSERVED** |
| 2023-09-01→2026-09-01 (Fase F) | MT5 real-tick | Frozen | Serious 3Y Validation | 240 trade, PF1.281, DD6.65% | Sì — verdetto BORDERLINE, oggetto di questa Fase G | **PREVIOUSLY_OBSERVED** |
| 2020-11→2023-10 ("finestra laterale") | **Python** (`server/backtest.py`) | **Diversa**: SAR con trailing 2.0×ATR + tentativo direction-lock su classificatore di regime (mai adottato in produzione) | [[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]], [[NEXUS EA - Ottimizzazione SAR e Tentativo Direction-Lock (24-08)]] | BUY PF0.55 n=111, SELL PF1.66 n=110 nella finestra laterale; walk-forward 5 finestre n=1471 totale | Sì — ha portato all'adozione del trailing 2.0×ATR (poi non presente nella config frozen attuale, quindi quella specifica decisione non è più in vigore) e al tentativo (fallito, documentato) di direction-lock | **PARTIALLY_OBSERVED** (motore diverso, config diversa, ma stessa finestra di mercato) |
| 2019-2024 | "Motore sito" (TradingView Pine, terzo motore indipendente) | Non specificata in dettaglio nel documento reperito | [[NEXUS EA - Analisi Trade-Level SAR MACD RSI_DIV]] | Analisi qualitativa su report HTM, non un PF isolato per SAR | Non decisionale direttamente, ma fornisce consapevolezza pregressa del comportamento nel periodo | **PARTIALLY_OBSERVED** (terzo motore, logica di esecuzione probabilmente diversa da entrambi Python e MQL5) |
| Nov 2025→Ago 2026 (conto demo multi-strategia) | MT5 live/demo (non Research Mode isolato) | Frozen-simile ma in esecuzione concorrente con altre 14 strategie, conto $1000, gate RISK_SIZE attivo | [[NEXUS EA - Diff Python vs MQL5 su SAR-EMA_PULLBACK, Limite Strutturale del Motore Ricerca (28-08)]] | PF0.92 su conto reale (vs stima Python ottimistica) | Sì — ha portato a documentare il limite del motore Python sul lotto minimo | **PREVIOUSLY_OBSERVED** (ma interamente post-2023-09, già coperto da Fase F) |
| ~2023-08→2026-08 (bar_range OOS 60-100% dei batch Python 67-strategie) | Python | Frozen (SL/TP nativi, dopo la correzione di Fase Triage/D) | Cost Calibration, Triage, native_sltp_correction | n=271, PF1.35, DD15.80% (SL/TP nativi, nessun costo) | Sì — ha portato alla promozione FAST_STRUCTURAL_CANDIDATE | **PREVIOUSLY_OBSERVED** (si sovrappone quasi interamente al periodo 2023-09→2026-09, tocca il pre-2023-09 solo per ~1 mese, trascurabile) |

### UNTOUCHED

**Nessun periodo prima del 2023-09-01 risulta completamente UNTOUCHED da ogni motore.** L'intero intervallo pre-2023-09 è stato almeno `PARTIALLY_OBSERVED`: il motore Python ha già osservato (con una config diversa, trailing+tentativo direction-lock) tutta la "finestra laterale" 2020-11→2023-10 e probabilmente il periodo precedente nel walk-forward a 5 finestre; il "motore sito" ha coperto genericamente 2019-2024. Non esiste quindi, in questo progetto, un segmento storico SAR mai osservato da nessun motore prima di settembre 2023.

**Nessun periodo prima del 2023-09-01 è mai stato osservato da MT5 Research Mode con la config frozen attuale** — su questo fronte specifico (quello rilevante per la validazione pre-deployment), tutto il pre-2023-09 è `UNTOUCHED_MT5_FROZEN_CONFIG`.

---

## 2. Frozen SAR configuration (invariata)

Selettore 4, GOLD, H4 nativo, SL ATR=1.0, TP ATR=6.0, `InpSAR_RequireCandleAlign=false`, `InpSAR_RequirePressureContrary=false`, Research RAW (DPT/Ruin/ESL/DailyDD/TotalDD off), nessun BE/trailing aggiunto, nessuna protezione esterna. Identica a Fase D/E/F.

---

## 3. Finestra storica indipendente — BLOCKER SCOPERTO

**Finestra dichiarata PRIMA di leggere il risultato**: seguendo l'audit del punto 1 (nessun periodo pre-2023-09 è completamente untouched; la finestra laterale 2020-11→2023-10 è quella più pesantemente osservata da Python), scelta per **massimizzare la porzione genuinamente meno osservata** mantenendo ~3 anni: **2019-02-03 → 2022-02-03** (allineata all'inizio dei dati reali Python per comparabilità, 3 anni esatti). Config Model=4 (real ticks), costi nativi Tester, avviata.

**Durante l'esecuzione** (log Tester, righe multiple, confermato identico in **ogni** run real-tick eseguito in questa intera sessione — Fase D, E, F e questo tentativo):

```
GOLD : real ticks begin from 2023.09.11 00:00:00, every tick generation used
```

**I tick reali per il simbolo GOLD su questo broker/demo esistono solo a partire dal 2023-09-11.** Qualunque test Model=4 richiesto per una data precedente non userebbe tick reali ma tick generati/sintetizzati dalle barre OHLC (M1) disponibili — esattamente il tipo di dato che il task istruisce di NON usare senza dichiararlo esplicitamente come sostituzione.

**Run interrotto immediatamente** (dopo ~15 minuti, ancora nella fase iniziale 2019-02) non appena scoperto il messaggio, per non produrre un risultato etichettato "real ticks" che in realtà non lo è.

### Implicazione strutturale

La finestra Serious 3Y già validata in Fase F (2023-09-01→2026-09-01) **coincide quasi esattamente con l'intero archivio tick reali disponibile su questo broker demo** (i tick reali iniziano 10 giorni dopo l'inizio di quella finestra). **Non esiste, in questo ambiente, alcuna finestra storica precedente al 2023-09-01 che possa essere testata con veri tick reali.** Non è una questione di scelta del periodo — è un limite di dati assoluto del demo/broker usato in questo progetto.

### Analisi supplementare (dichiarata come tale, non un sostituto del test richiesto)

Per non lasciare il punto completamente vuoto, eseguita un'analisi supplementare **sul motore Python** (`server/backtest.py`, stessa config frozen: `atr_sl=1.0, atr_tp=6.0`, nessun trailing/BE, nessun filtro aggiuntivo — NON MT5, NON tick reali, sizing a rischio% invece di lotto fisso, quindi **non direttamente comparabile in valore assoluto** a MT5) sull'intero storico reale disponibile (Dukascopy, 2019-02-03→2026-08-14), isolando la porzione pre-2023-09:

| Sotto-periodo | n | PF | Win rate | BUY PF | SELL PF |
|---|---|---|---|---|---|
| 2019-08→2021-08 | 239 | 0.97 | 18.0% | 1.02 | 0.78 |
| 2021-08→2023-08 | ~200* | 0.93 | 19.0% | 1.04 | 0.73 |

*(limite tecnico di `run_backtest()`: `trade_list` restituisce solo gli ultimi 200 trade su un totale di 439 per l'intero intervallo 2019-2023; i due segmenti sopra sono stati isolati con `bar_range` separati per aggirare il limite, quindi sono conteggi completi per ciascun sotto-periodo, non un campione troncato)

**Lettura onesta**: su un motore diverso, con un sizing diverso, la config frozen di SAR mostra PF leggermente **sotto 1** in entrambi i sotto-periodi pre-2023-09, con lo stesso pattern di debolezza SELL già visto nel Serious 3Y (SELL PF 0.73-0.78 qui, contro BUY PF ~1.0-1.04). Questo NON conferma né smentisce in modo definitivo l'edge — è un motore diverso — ma **non fornisce supporto positivo** all'ipotesi di un edge indipendente dal periodo 2023-2026either.

---

## 4-5. Metrics / No rescue

Non applicabile nella forma richiesta (nessun test MT5 real-tick completato per il periodo indipendente, per il blocker del punto 3). Nessun rescue comunque applicato in nessuna delle analisi disponibili — riportati SELL debole e BUY forte così come emergono, senza filtri.

---

## 6. Cross-period comparison (Serious 2023-2026 vs supplementare pre-2023, con tutti i caveat del caso)

| | Serious 2023-09→2026-09 (MT5 real-tick, frozen) | Pre-2023-09 supplementare (Python, frozen, sizing diverso) |
|---|---|---|
| PF | 1.281 | 0.93-0.97 |
| SELL PF | 0.84 | 0.73-0.78 |
| BUY PF | 1.70 | 1.02-1.04 |
| Motore | MT5 real-tick | Python (proxy, non comparabile in $ assoluti) |

**L'asimmetria SELL persiste** in entrambi i periodi e su entrambi i motori — non è specifica del 2023-2026, sembra strutturale al segnale SAR stesso (PSAR flip + cross EMA9/21) più che a un singolo regime di mercato. **Il PF assoluto sembra più debole nel periodo precedente** (sotto 1 su entrambi i sotto-segmenti Python) rispetto al Serious 3Y (1.281) — ma il confronto attraversa un cambio di motore e di sizing, quindi va trattato come indicativo, non probante.

---

## 7. Stability verdict

### `SAR_INDEPENDENT_CONFIRMATION_BORDERLINE`

**Motivazione — cosa impedisce il PASS**:

1. **Il test richiesto (MT5 real-tick, periodo indipendente pre-2023-09) è strutturalmente impossibile in questo ambiente**: i tick reali per GOLD iniziano il 2023-09-11, 10 giorni dopo l'inizio della finestra Serious 3Y già validata. Non esiste modo di soddisfare "real ticks" per un periodo precedente senza usare dati generati/sintetici mascherati da reali — cosa esplicitamente non fatta.
2. **L'unica evidenza disponibile per il periodo precedente (Python, motore diverso, sizing diverso) non è positiva**: PF 0.93-0.97 in entrambi i sotto-segmenti 2019-2023, sotto la soglia di 1 richiesta per un PASS.
3. **L'asimmetria SELL persiste e non migliora** nel periodo precedente (SELL PF 0.73-0.78, peggiore del già debole 0.84 del Serious 3Y) — nessun segnale che si tratti di un problema limitato al 2023-2026.

Non è un `FAIL` netto perché: (a) il test decisivo richiesto non è stato eseguibile per limite di dati, non per un risultato negativo del test stesso; (b) l'unica evidenza disponibile proviene da un motore/sizing diverso da quello di deployment, quindi ha valore indicativo ma non probante; (c) il Serious 3Y su MT5 reale resta comunque BORDERLINE (non FAIL) con OOS che migliora.

**Non è un PASS** perché l'obiettivo dichiarato della fase — "determinare se SAR possiede edge indipendente dal periodo 2023-09→2026-09" — non può essere confermato con l'evidenza rigorosa richiesta (MT5 real-tick), e l'unica evidenza surrogata disponibile va nella direzione opposta a una conferma.

---

## 9. Conseguenza (regola BORDERLINE)

Come da istruzione: nessun tuning applicato. Il motivo esatto del mancato PASS è riportato sopra (§7). **Mi fermo qui**, senza procedere al prossimo step ipotizzato per il caso PASS (Risk & Distribution Validation con Monte Carlo/bootstrap/risk-of-ruin) né senza chiudere SAR come nel caso FAIL — resta nello stato intermedio esplicitamente prodotto da questa fase: **evidenza indipendente non ottenibile in modo rigoroso in questo ambiente, evidenza surrogata non favorevole**.

---

## File prodotti

- Nessun trade CSV MT5 per la finestra indipendente (run abortito per il blocker — nessun dato "real tick" fuorviante salvato)
- Analisi Python supplementare eseguita inline, risultati riportati sopra (non salvata come file separato — analisi di 5 minuti, non uno script riutilizzabile, dato il carattere di blocco della fase)

## Commit

`b14a4e6`
