# NEXUS Causal Research — Experiment 2: Confirmatory Test of Friday + Level Age

Segue [[NEXUS - Causal Experiment 1 WICK Sweep 1R Outcome]] (commit `d9df94a`). Esperimento **confermativo**, non esplorativo: nessuna nuova feature, nessuna nuova combinazione, nessuna soglia ricalcolata sui nuovi dati, nessuna ottimizzazione di WICK.

## 0. Freeze delle ipotesi (prima del test)

- **H1**: Friday ha una probabilità di `PLUS_1R_FIRST` superiore agli altri giorni.
- **H2**: `OLD_LEVEL` ha una probabilità di `PLUS_1R_FIRST` superiore a `YOUNG_LEVEL`.
- **Soglia OLD/YOUNG congelata**: **20700 secondi (5.75 ore)** — mediana `level_age_seconds` calcolata in Experiment 1. Verificato che il valore coincide **esattamente** sia calcolandolo sul solo train (W1+W2, n=133) sia sull'intero risolto di Experiment 1 (n=190) — nessuna ambiguità su quale sottoinsieme usare, nessun ricalcolo su questi nuovi dati.

## 1. Dataset indipendente

**Periodo**: 2026-04-01 → 2026-06-01 (2 mesi), **immediatamente precedente e non sovrapposto** a W1 di Experiment 1 (che iniziava il 2026-06-01) — dati temporalmente mai usati in Experiment 1, come richiesto in via preferenziale.

**Granularità**: stessa metodologia di Experiment 1 — Tester Model=1 per generare gli eventi WICK (`InpLevelRegistry_WickReadPath=true`, stessa configurazione parametri), label calcolata su barre M1 esportate offline (`NXS_ResearchExportBars.mq5`, stesso script, nessuna modifica). Il tentativo di Model=4 real-tick su periodi lunghi resta impraticabile nell'ambiente (stesso limite documentato in Fase A/B/E) — dichiarato esplicitamente, non forzato.

**Parity check** (a corredo, stessa infrastruttura Fase D): `checks=3463 mismatches=0`, `field_mismatches=0 stale_active_levels=0 total_levels=437` — il read-path resta equivalente al legacy anche su questo periodo mai visto prima.

## 2. Qualità dati

| Metrica | Valore |
|---|---|
| Eventi sweep totali | **137** |
| Risolti (+1R o -1R) | **135** |
| Censored | **0** |
| Ambiguous same-bar (esclusi) | **2** |
| Sweep duplicati per livello | 0 |
| `level_id`/`event_id` duplicati | 0 |
| `created_time` mancante | 0 |
| Record incoerenti | 0 |

Nessuna imputazione silenziosa — stesse regole di Experiment 1.

## 3. H1 — Friday vs Non-Friday

| | n | rate | CI95 |
|---|---|---|---|
| Friday | 23 | **0.435** | [0.256, 0.632] |
| Non-Friday | 112 | **0.491** | [0.400, 0.582] |

- Absolute uplift (Friday − NonFriday): **−0.056**
- Relative uplift: **−11.5%**
- CI95 differenza: [−0.279, 0.166] (include ampiamente lo zero)
- Confronto con Experiment 1: Friday=0.657 (n=35) → qui **0.435**

**L'effetto si INVERTE completamente di segno** rispetto a Experiment 1 (positivo lì, negativo qui). Fallisce il primo criterio del confirmation gate ("l'effetto mantiene la stessa direzione").

## 4. H2 — OLD vs YOUNG (soglia congelata 20700s)

| | n | rate | CI95 |
|---|---|---|---|
| OLD (≥20700s) | 58 | **0.552** | [0.425, 0.673] |
| YOUNG (<20700s) | 77 | **0.429** | [0.324, 0.540] |

- Absolute uplift (OLD − YOUNG): **+0.123**
- Relative uplift: **+28.7%**
- CI95 differenza: [−0.046, 0.292] (sfiora lo zero al limite inferiore, non lo esclude con certezza)
- Confronto con Experiment 1: OLD=0.578 (n=102) vs YOUNG=0.511 (n=88), uplift +0.067 → qui **+0.123** (stessa direzione, magnitudo non collassata, anzi maggiore)

Sulla carta H2 supera più criteri del confirmation gate (direzione mantenuta, campione ragionevole, uplift non collassato) — ma vedi §5, la sensitivity la ridimensiona.

## 5. Sensitivity (nessun tuning, solo robustezza)

### Split temporale grossolano (prima metà vs seconda metà del periodo indipendente)

| | n | Friday rate | NonFriday rate | OLD rate | YOUNG rate |
|---|---|---|---|---|---|
| Prima metà | 67 | 0.500 (n=8) | 0.441 (n=59) | **0.433** (n=30) | **0.459** (n=37) |
| Seconda metà | 68 | 0.400 (n=15) | 0.547 (n=53) | **0.679** (n=28) | **0.400** (n=40) |

**H2 si inverte di segno tra le due metà** del periodo indipendente stesso: OLD < YOUNG nella prima metà, OLD >> YOUNG nella seconda. Il risultato aggregato positivo di H2 è trainato quasi interamente dalla seconda metà — non è uniforme nel periodo. **Evidenziato esplicitamente come richiesto.**

### BUY/SELL separati (solo robustness check)

| | n | Friday rate | NonFriday rate | OLD rate | YOUNG rate |
|---|---|---|---|---|---|
| BUY | 73 | 0.500 (n=12) | 0.443 (n=61) | 0.519 (n=27) | 0.413 (n=46) |
| SELL | 62 | 0.364 (n=11) | 0.549 (n=51) | 0.581 (n=31) | 0.452 (n=31) |

**H2 (OLD>YOUNG) è concorde in entrambe le direzioni** (BUY e SELL) — punto a favore della sua robustezza rispetto a H1.
**H1 (Friday) è discorde tra BUY (leggermente positivo) e SELL (nettamente negativo)** — l'inversione aggregata di H1 è trainata soprattutto dal lato SELL, ulteriore evidenza che non è un effetto stabile.

Nessuna osservazione casuale aggiuntiva da segnalare come `UNTESTED_OBSERVATION` oltre a quanto già nei confronti pre-registrati e nei robustness check approvati.

## 6. Limitazioni

- Stesso limite Model=1 di Experiment 1 (discovery evidence, non execution evidence) — dichiarato di nuovo qui.
- Campione indipendente modesto (135 risolti) — sufficiente per un test di direzione ma non per una stima di precisione fine.
- Il periodo indipendente stesso mostra eterogeneità interna (vedi split prima/seconda metà) — un limite ulteriore alla generalizzabilità di qualunque pattern trovato, non solo di H1/H2.

## 7. Classificazione

| Ipotesi | Direzione mantenuta | Campione sufficiente | Uplift non collassato | CI compatibile | Nessun problema causale/qualità | Non da pochi casi | **Classificazione** |
|---|---|---|---|---|---|---|---|
| **H1 (Friday)** | ❌ **invertita** | n=23 (modesto) | n/a (segno opposto) | n/a | ✅ | — | **REFUTED** |
| **H2 (Level age)** | ✅ | ✅ (58/77) | ✅ (cresciuto, non collassato) | ✅ (quasi) | ✅ | ⚠️ **instabile tra le due metà del periodo** | **INCONCLUSIVE** |

H2 non è promosso a `PROMISING_HYPOTHESIS` nonostante superi la maggior parte dei criteri formali del gate: la sensitivity (§5) mostra che il risultato aggregato è trainato da metà del periodo e si inverte nell'altra metà — esattamente il tipo di fragilità che il gate anti-data-mining chiede di penalizzare ("risultato non deve dipendere da pochi casi/sotto-periodo"). Non è nemmeno `REFUTED` perché la direzione aggregata e lo split BUY/SELL restano concordi.

## Verdict finale

### **NO_HYPOTHESIS_CONFIRMED**

Nessuna delle due ipotesi pre-registrate soddisfa il confirmation gate su dati indipendenti. H1 (Friday) è refutata (inversione di segno). H2 (level age) resta un'osservazione debole e instabile (`INCONCLUSIVE`), non abbastanza solida da diventare `PROMISING_HYPOTHESIS_CONFIRMED` senza ulteriori dati che ne verifichino la stabilità tra sotto-periodi. Nessuna implementazione come strategia in questa o nessuna fase precedente.
