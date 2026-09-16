# NEXUS — First Serious 3-Year Validation: SAR + MACD

Base: commit `f3272b5` (Phase E, approvato). Nessun segnale, parametro, TF, SL/TP, filtro, risk logic o gate modificato. Nessuna ottimizzazione, nessun tuning, nessuna scelta di sottoperiodo dopo aver visto i risultati.

**Finestra dichiarata PRIMA dell'esecuzione**: ultimo intervallo continuo di 3 anni disponibile che termina alla data corrente del dataset MT5 (history sincronizzata fino a 2026.09.04) → **2023-09-01 → 2026-09-01**, GOLD H4, Model=4 (real ticks), costi nativi Tester, nessun cherry-picking.

Ordine di esecuzione rispettato: SAR eseguito e salvato per primo, MACD lanciato solo dopo. Nessun mescolamento dei risultati.

---

## Configurazioni congelate (invariate da Fase D/E)

| | SAR | MACD |
|---|---|---|
| Selettore | 4 | 3 |
| TF | H4 nativo (`InpProfileMultiTF`) | H4 nativo |
| SL/TP ATR | 1.0 / 6.0 | 2.0 / 8.0 |
| Filtri opzionali | `InpSAR_RequireCandleAlign=false`, `InpSAR_RequirePressureContrary=false` (default, nessun override) | gate EMA200 nativo (intrinseco al segnale, vedi Fase E §3) |
| Modalità | Research RAW (DPT/Ruin/ESL/DailyDD/TotalDD off) | Research RAW |

---

## SAR — metriche complete (3 anni, 2023-09-01 → 2026-08-28)

| Metrica | Valore |
|---|---|
| Trade count | 240 |
| Profit Factor | **1.281** |
| Net profit | $1449.50 |
| Expectancy/trade | $6.04 |
| Max DD % | 6.65% |
| Max DD assoluto | $693.60 |
| Win rate | 19.2% |
| Avg win | $143.66 |
| Avg loss | $26.59 |
| Payoff ratio | 5.40 |
| BUY / SELL split | 148 / 92 |
| BUY PF / SELL PF | **1.70 / 0.84** |
| Max consecutive losses | 29 |
| Longest flat period | 207 giorni |
| MAE / MFE | non disponibili (il formato `NEXUS_trades.csv` non logga high-water/low-water intrabar) |

**Monthly PnL**: 36 mesi, disponibile integralmente in `sar_serious_3y_analysis.txt`. Nessun mese distrugge il conto (peggior mese: 2026-02, -$283.60; miglior mese: 2026-01, +$864.50).

**Yearly PnL**: 2023 (parziale, 4 mesi) -$33.00 · 2024 +$161.40 · 2025 +$232.80 · 2026 (parziale, 8 mesi) +$1088.30

### Temporal decomposition

| Segmento | n | PF | Expectancy | DD% |
|---|---|---|---|---|
| Year 1 | 72 | 1.004 | $0.04 | 2.22% |
| Year 2 | 91 | 0.934 | -$1.04 | 6.65% |
| Year 3 | 77 | 1.527 | $20.02 | 5.75% |
| First half | 112 | 1.096 | $1.09 | 2.22% |
| Second half | 128 | 1.342 | $10.37 | 6.73% |

Year 2 è marginalmente negativo (PF 0.934, expectancy -$1.04) — non materiale rispetto alla scala tipica del trade (avg loss $26.59). Year 1 è sostanzialmente flat (PF 1.004). Year 3 porta la quasi totalità del profitto netto.

### OOS check (ultimo ~22.5%, split 2025-12-26)

| | IS (77.5%) | OOS (22.5%) |
|---|---|---|
| n | 189 | 51 |
| PF | 1.143 | **1.453** |
| Expectancy | $2.16 | $20.42 |
| DD% | 6.65% | 6.01% |
| SELL PF | 0.28 | **1.26** |

**L'OOS non solo non collassa: migliora su ogni metrica.** Nota rilevante: la debolezza SELL (vedi sotto) è concentrata nell'IS/anni 1-2; nell'OOS il lato SELL torna positivo.

### Cost robustness (stress post-trade, dichiarato)

MT5 Tester non permette di impostare in modo pulito un override di spread coerente su un intero run real-tick senza alterare la semantica dell'esecuzione (il prezzo reale a ogni tick determina fill/SL/TP) — applicato quindi lo **stress post-trade**: costo aggiuntivo = (pip_target − 5.5 pip nativi) × valore-pip-per-lotto (convenzione GOLD 100oz/lotto, $0.01/pip per 0.01 lotto), sottratto una volta per trade round-trip.

| Profilo | PF | Net | Expectancy | DD% |
|---|---|---|---|---|
| Native (Tester) | 1.281 | $1449.50 | $6.04 | 6.65% |
| Conservative (+1.5 pip → 7.0 pip) | 1.280 | $1445.90 | $6.02 | 6.65% |
| Stress (+7.5 pip → 13.0 pip) | 1.277 | $1431.50 | $5.96 | 6.68% |

Impatto minimo in valore assoluto: il lotto fisso di ricerca (0.01-0.02) rende il costo spread aggiuntivo piccolo in termini assoluti ($0.01-0.02/pip per trade). L'edge non collassa in nessuno scenario di costo.

### Verdetto SAR: **SERIOUS_VALIDATION_BORDERLINE**

Motivazione — 7 degli 8 criteri passano chiaramente (PF>1, expectancy>0, OOS non collassa anzi migliora, 2 dei 3 anni non materialmente negativi, conservative non distrugge l'edge, stress non collassa, DD compatibile col profilo già osservato in Fase D/E). **Un solo criterio è borderline**: la dipendenza direzionale — SELL PF=0.84 sull'intero periodo (92 trade, 38% del campione, non "pochi trade") è un lato strutturalmente in perdita nell'aggregato a 3 anni, anche se concentrato negli anni 1-2 e risolto nell'OOS. Non è "estrema" (non è un collasso, PF 0.84 non 0.2), ma è un'asimmetria reale e quantificabile che impedisce un PASS pulito. Nessuna correzione applicata (no rescue).

---

## MACD — metriche complete (3 anni, 2023-09-06 → 2026-08-26)

| Metrica | Valore |
|---|---|
| Trade count | 115 |
| Profit Factor | **1.122** |
| Net profit | $548.80 |
| Expectancy/trade | $4.77 |
| Max DD % | 9.52% |
| Max DD assoluto | $1042.00 |
| Win rate | 25.2% |
| Avg win | $174.02 |
| Avg loss | $52.30 |
| Payoff ratio | 3.33 |
| BUY / SELL split | 79 / 36 |
| BUY PF / SELL PF | **1.50 / 0.61** |
| Max consecutive losses | 17 |
| Longest flat period | 499 giorni |
| MAE / MFE | non disponibili |

**Yearly PnL**: 2023 (parziale) -$120.70 · 2024 -$63.50 · 2025 +$98.80 · 2026 (parziale) +$634.20

### Temporal decomposition

| Segmento | n | PF | Expectancy | DD% |
|---|---|---|---|---|
| Year 1 | 40 | **0.791** | **-$4.13** | 3.04% |
| Year 2 | 42 | **0.962** | **-$1.17** | 7.05% |
| Year 3 | 33 | 1.314 | $23.12 | 9.34% |
| First half | 57 | 0.849 | -$3.21 | 3.04% |
| Second half | 58 | 1.223 | $12.61 | 9.37% |

**Solo 1 dei 3 anni è positivo.** Year 1 e Year 2 sono entrambi netti negativi (-$165.10 e -$49.00), Year 3 da solo produce +$762.90 — più dell'intero risultato netto a 3 anni.

### OOS check (ultimo ~22.5%, split 2025-12-25)

| | IS (77.5%) | OOS (22.5%) |
|---|---|---|
| n | 95 | 20 |
| PF | **0.968** | 1.343 |
| Expectancy | -$0.90 | $31.71 |
| DD% | 7.16% | 9.45% |
| SELL PF | **0.13** | 1.07 |

L'IS (77.5% del campione, 95 trade) è **nettamente in perdita** (PF<1). L'intero risultato positivo a 3 anni dipende dal 22.5% finale (20 trade). L'OOS non collassa in senso stretto (anzi è forte), ma questo significa anche che il 3-year PF>1 complessivo esiste solo grazie a una finestra recente ristretta, non a una performance distribuita nel tempo.

### Cost robustness

| Profilo | PF | Net | Expectancy | DD% |
|---|---|---|---|---|
| Native (Tester) | 1.122 | $548.80 | $4.77 | 9.52% |
| Conservative | 1.122 | $547.08 | $4.76 | 9.53% |
| Stress | 1.120 | $540.17 | $4.70 | 9.54% |

Anche qui impatto minimo (stesso motivo del lotto fisso di ricerca) — il costo non è ciò che distrugge l'edge di MACD.

### Verdetto MACD: **SERIOUS_VALIDATION_FAIL**

Motivazione — **due criteri falliscono in modo netto, non borderline**:

1. "Almeno 2 dei 3 anni non negativi in modo materiale" → **fallito**: solo 1 dei 3 anni (Year 3) è positivo; Year 1 (-$165.10) e Year 2 (-$49.00) sono entrambi negativi, e Year 1 in particolare è negativo su una scala paragonabile al trade medio (avg loss $52.30).
2. "Nessuna dipendenza estrema da una sola direzione" → **fallito**: SELL PF=0.61 sull'intero periodo, e **SELL PF=0.13 nell'IS** (77.5% del campione) — il lato SELL è quasi interamente perdente per la maggior parte dello storico testato, non un'asimmetria lieve.

PF totale (1.122) ed expectancy (4.77) sono tecnicamente positivi ma per un margine sottile, e l'intero risultato positivo è concentrato nel 22.5% più recente del campione (Year 3 / OOS) mentre il 77.5% precedente è netto negativo. Questo combina due segnali di fragilità strutturale (non solo di rumore statistico) — coerente con `SERIOUS_VALIDATION_FAIL`, non `BORDERLINE`.

**Nessuna azione di rescue applicata** (nessun cambio SL/TP, nessun filtro mesi/direzioni/sessioni, nessuna ricerca di parametri migliori), come esplicitamente richiesto. Il fallimento è documentato, non corretto.

---

## Comparison SAR vs MACD

| | SAR | MACD |
|---|---|---|
| n (3y) | 240 | 115 |
| PF | 1.281 | 1.122 |
| Expectancy | $6.04 | $4.77 |
| DD% | 6.65% | 9.52% |
| Anni positivi | 2 di 3 (Y1 flat, Y2 lieve neg, Y3 forte) | 1 di 3 (Y1 e Y2 negativi) |
| OOS vs IS | OOS migliora ovunque | OOS forte ma IS negativo (PF 0.968) |
| SELL PF (3y) | 0.84 | 0.61 |
| SELL PF (IS) | 0.28 | 0.13 |
| Cost robustness | non distrugge l'edge | non distrugge l'edge (ma l'edge nativo è già debole) |
| Verdetto | **BORDERLINE** | **FAIL** |

SAR ha un campione più ampio (240 vs 115 trade), un PF più alto, una DD più contenuta, e — criticamente — 2 dei 3 anni non materialmente negativi contro l'1 di 3 di MACD. Entrambe condividono la stessa direzione di debolezza strutturale (SELL side sotto-performante, specialmente nell'IS), ma in SAR è un'asimmetria contenuta e in via di risoluzione nell'OOS, mentre in MACD è quasi un collasso totale del lato SELL nell'IS (PF 0.13) che il PF complessivo positivo nasconde.

**Non combinate.** Nessuna azione di portfolio-combination eseguita, come richiesto.

---

## Blocker e limiti dichiarati

1. **Costo stress post-trade, non a livello Tester**: MT5 non permette un override di spread pulito su un run real-tick senza cambiare la semantica dell'esecuzione tick-by-tick — applicato uno stress additivo post-trade, dichiarato esplicitamente (non un limite dei risultati, ma della metodologia di stress test).
2. **MAE/MFE non disponibili**: il formato `NEXUS_trades.csv` non logga high-water/low-water intrabar.
3. **Lotto di ricerca fisso (0.01-0.02)**: rende gli importi in dollari dei test di cost-robustness piccoli in valore assoluto — l'impatto percentuale su PF resta comunque informativo e riportato.
4. **MACD FAIL non è rescue-eligible in questa task**: per istruzione esplicita, nessun tentativo di correzione. Il verdetto resta un fallimento documentato.

---

## File prodotti

- `results/cost_calibration_67_rerun/sar_serious_3y_trades.csv` — trade log grezzo MT5 (240 trade)
- `results/cost_calibration_67_rerun/macd_serious_3y_trades.csv` — trade log grezzo MT5 (115 trade)
- `results/cost_calibration_67_rerun/sar_serious_3y_metrics.json` — metriche aggregate + yearly/monthly + OOS + cost robustness
- `results/cost_calibration_67_rerun/macd_serious_3y_metrics.json` — idem
- `results/cost_calibration_67_rerun/{sar,macd}_serious_3y_analysis.txt` — output completo leggibile
- `server/research_scripts/phase_f_analyze_serious_3y.py` — script di analisi riusabile

## Commit

`e557b22`
