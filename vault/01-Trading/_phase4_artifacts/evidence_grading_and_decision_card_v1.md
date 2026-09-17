# Evidence Grading Scale + Research Decision Card v1 (Phase 5.5 sec.15-16)

## Evidence Grading Scale

| Grade | Nome | Requisito |
|---|---|---|
| **E0** | OBSERVATION | Un pattern notato, nessun test statistico formale |
| **E1** | DISCOVERY | Test statistico su un campione di scoperta, nessuna conferma out-of-sample |
| **E2** | INTERNAL_VALIDATION | Confermato su uno split interno (stesso dataset/fonte), ma la selezione dell'ipotesi non è stata protetta da contaminazione (vedi Independent Validation Integrity, sec.4) |
| **E3** | TRUE_HOLDOUT_VALIDATION | Confermato su un vero holdout non contaminato (ipotesi congelata PRIMA di guardare il periodo di validazione, nessuna selezione post-hoc da un batch) |
| **E4** | CROSS_SOURCE / CROSS_ENGINE | Confermato su una fonte dati e/o motore di esecuzione indipendenti |
| **E5** | EXECUTION_VALIDATED | Sopravvive a un modello di esecuzione realistico (fill reale, slippage, latenza) |
| **E6** | FORWARD/DEMO_CONFIRMED | Confermato in avanti nel tempo, su un conto demo/forward reale |

**Il grade dipende da evidenza reale, non da PF** — un PF alto con evidenza E1 resta E1.

## SWEEP+RECLAIM → Grade attuale: **E2 (INTERNAL_VALIDATION)**

Non E3: la validazione non è "pulita" — vedi `independent_validation_integrity_v1.md`, classificazione `CONTAMINATED_VALIDATION` (RECLAIM è stata scelta come headline dopo aver visto i risultati di validazione di TUTTE e 14 le ipotesi del batch). Non E1: è andata oltre la semplice scoperta, è stata effettivamente testata su uno split interno con risultato consistente. Il fatto che il p-value resti significativo anche dopo correzione Benjamini-Hochberg per il batch di 14 (sec.3) NON basta a promuoverla a E3 — il multiple-testing ledger è un guardrail aggiuntivo, non un sostituto della validazione indipendente (dichiarato esplicitamente in sec.3).

**Requisiti ancora da superare prima di poter essere chiamato "validated edge"** (risponde alla domanda finale 7):
1. **E3**: un vero test TRUE_HOLDOUT — l'ipotesi "sweep+reclaim genera edge" va ri-testata come ipotesi SINGOLA, congelata esplicitamente, su un periodo/campione che nessuno ha guardato nemmeno in aggregato durante Phase 5 (es. dati futuri via forward-collection, o una finestra storica non ancora toccata).
2. **E4**: conferma su una fonte dati e/o simbolo diversi (stesso schema già impiegato con successo per SAR in Phase 5.L).
3. **E5**: `SIGNAL_TO_FILL_GAP` calcolato con un modello di esecuzione realistico (sec.12) — priorità critica, dato il precedente diretto di un fenomeno quasi identico refutato in esecuzione (Phase 4, WICK_SWEEP_RECLAIM).
4. **E6**: solo dopo E5, un periodo forward/demo.

## Research Decision Card — schema

```json
{
  "hypothesis_id": "H004_EVENT_RECLAIM",
  "pre_registered": "detector si, promozione a headline no (post_hoc_selection_from_batch=true)",
  "discovery_or_validation": "entrambi calcolati nella stessa run - vedi nota di contaminazione",
  "sample": {"n_discovery": 215, "n_validation": 85},
  "baseline": "matched per (terzile volatilita, terzile trend, anno), stessa direzione",
  "delta_p": {"discovery": 0.241, "validation": 0.299},
  "delta_e": {"validation_mfe_atr": 0.694},
  "uncertainty": "Wilson CI95 mai sovrapposte; Beta-Binomial concorde; p raw validation ~4.0e-08, adjusted BH ~4.2e-07 (rank 1/14)",
  "multiple_testing_family": "FAMILY_VALIDATION (14 ipotesi, Phase5 edge-discovery batch)",
  "validation_independence": "CONTAMINATED_VALIDATION (vedi sec.4)",
  "execution_status": "NOT_TESTED (vedi sec.11)",
  "evidence_grade": "E2",
  "failure_risks": [
    "SHADOW_EXECUTION_ASSUMPTION (precedente diretto Phase 4 su fenomeno quasi identico)",
    "post_hoc_selection_from_batch (vedi Hypothesis Registry sec.1)",
    "baseline tercile thresholds calcolate su intero dataset, non solo discovery (Leakage Guard sec.8 - impatto stimato piccolo)"
  ],
  "decision": "POST_HOC_CANDIDATE - non promuovibile a SUPPORTED_EDGE ne' a strategia. Prossimo passo: E3 (vero holdout) poi E5 (esecuzione), in quest'ordine, non in parallelo e non saltando E3."
}
```

Questa card è l'output sintetico che ogni futura conclusione deve produrre — un lettore che legge SOLO questa card (senza aprire nessun altro artifact) ha già l'informazione sufficiente per non fidarsi ciecamente del numero di PF/ΔP.
