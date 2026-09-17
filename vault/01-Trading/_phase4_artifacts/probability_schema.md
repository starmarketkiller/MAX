# Probability & Uncertainty Engine — schema v1

Nessuna probabilità viene riportata come singolo numero. 7/10 ≠ 700/1000 anche se entrambi "70%" (sezione 7 della richiesta).

## Schema (per ogni stima di probabilità)

```json
{
  "schema_version": 1,
  "estimate_id": "PROB-SETUP-UPTREND_SWEEP_RECLAIM-v1-p1R",
  "setup_id": "SETUP-UPTREND_SWEEP_RECLAIM-v1",
  "target_definition": "+1R before -1R",
  "wins": 0,
  "losses": 0,
  "censored": 0,
  "n": 0,
  "observed_probability": null,
  "confidence_interval_95": {"low": null, "high": null, "method": "Wilson score"},
  "bayesian": {
    "model": "Beta-Binomial",
    "prior_alpha": 1,
    "prior_beta": 1,
    "prior_rationale": "uninformative Beta(1,1) salvo evidenza pregressa esplicita da un baseline comparabile, in quel caso usare i suoi wins/losses come prior informativo dichiarato",
    "posterior_alpha": null,
    "posterior_beta": null,
    "posterior_mean": null,
    "posterior_credible_interval_95": {"low": null, "high": null}
  },
  "effective_sample_size": null,
  "regime_breakdown": [
    {"regime": "TREND_UP", "n": null, "wins": null},
    {"regime": "TREND_DOWN", "n": null, "wins": null},
    {"regime": "RANGE", "n": null, "wins": null}
  ],
  "direction_breakdown": {
    "BUY": {"n": null, "wins": null},
    "SELL": {"n": null, "wins": null}
  },
  "discovery_vs_validation": "DISCOVERY | VALIDATION",
  "discovery_sample_disjoint_from_validation_sample": true
}
```

## Modello Beta-Binomial (interpretabile, non ML)

Con prior Beta(α₀, β₀) e k successi su n prove:
- posterior = Beta(α₀ + k, β₀ + n − k)
- posterior_mean = (α₀ + k) / (α₀ + β₀ + n)
- effective_sample_size (per confronto tra sotto-gruppi) = n del sottogruppo, riportato sempre esplicitamente accanto alla media — MAI riportare solo la media posteriore senza n.

Prior di default: Beta(1,1) (uniforme, non informativo) per ogni nuovo Setup mai osservato prima. Se un Setup è una variante di uno già validato, il prior PUÒ essere informato dal Setup genitore, ma questo va dichiarato esplicitamente in `prior_rationale` — mai un prior scelto per far apparire il risultato migliore.

`discovery_vs_validation` + `discovery_sample_disjoint_from_validation_sample=true` è un requisito strutturale: una stima "VALIDATION" calcolata sullo stesso campione usato per scoprire/definire il Setup non è una validazione indipendente — è lo stesso overfitting mascherato da parole diverse.
