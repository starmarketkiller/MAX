# Probability Engine — output v1 (Phase 5.G)

Implementazione: `server/research_scripts/phase5/stats_utils.py`. Ogni stima di probabilità in `edge_results_v1.json` porta SEMPRE: `n, wins, losses, censored, observed_p, wilson_ci95_low/high, beta_binomial{prior_alpha, prior_beta, posterior_alpha, posterior_beta, posterior_mean, posterior_ci95_low/high}`. Mai un win-rate nudo.

**Wilson score interval** (frequentista, z=1.96 per il 95%): usato come primo controllo di non-sovrapposizione fra evento e baseline (`ci95_non_overlapping` in ogni risultato).

**Beta-Binomial** (Bayesiano, interpretabile): prior Beta(1,1) non informativo per default su ogni nuovo evento/interazione — nessun prior informativo è stato usato in questa fase (nessun componente aveva un "genitore" validato da cui ereditare un prior). Posteriore calcolato esattamente (scipy.stats.beta.ppf), non approssimato.

**Esempio reale** (EC-LIQUIDITY_SWEEP_RECLAIM, validation): n=85, wins=69, losses=16, censored=0 → observed_p=0.812, Wilson CI95=[0.716, 0.881], posteriore Beta(70,17) media=0.805 CI95=[0.716, 0.880] — frequentista e Bayesiano concordano da vicino (prior debole, campione non piccolissimo).

**Nessun outcome è mai stato ridotto a un singolo numero** nei file prodotti da questa fase — vedi `edge_results_v1.json` per la struttura completa di ogni record (discovery/validation/BUY/SELL/per-anno, ciascuno con il record di probabilità pieno).
