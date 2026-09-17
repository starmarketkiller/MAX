# Edge Component Library — schema v1

Un EDGE_COMPONENT non è una strategia (sezione 12 della richiesta). È un mattone causale riusabile con evidenza empirica propria.

## Schema

```json
{
  "schema_version": 1,
  "component_id": "EC-VOLATILITY_EXPANSION",
  "semantic_definition": "Espansione della volatilità (ATR/true range) oltre un livello recente tende ad associarsi a persistenza direzionale nella barra/e immediatamente successive.",
  "observation_point": "bar_close, true range della barra corrente vs ATR(14) precedente",
  "economic_rationale": "un'espansione di range spesso segnala l'ingresso di nuovo flusso/informazione nel mercato, non rumore puro",
  "baseline": "distribuzione di outcome dello stesso Context SENZA l'evento di espansione di volatilità",
  "expected_effect": {"direction": "ΔP e ΔE attesi positivi per il breakout nella direzione della barra di espansione", "magnitude_hint": "da stimare, non assunto"},
  "empirical_evidence": [
    {"source": "NEXUS - Strategy Foundry Phase 3 Volatility Breakout Implementation.md", "n": 14, "result": "PF 1.156-1.165, expectancy $17.71-$18.80, HOLD_NEEDS_MORE_EVIDENCE", "strength": "LOW (n<30, singola finestra 6 mesi, singolo simbolo/TF)"}
  ],
  "confidence": "LOW|MEDIUM|HIGH",
  "valid_contexts": ["da determinare - candidato: regime di trend attivo"],
  "invalid_contexts": ["da determinare - candidato: range compresso senza direzione"],
  "failure_modes": ["falsa espansione da news/gap di sessione senza continuazione", "espansione catturata da modello di tick sintetico (Model=1) in modo non rappresentativo del comportamento a tick reali (Model=4) - vedi Phase 3 correction"],
  "status": "CANDIDATE|SUPPORTED|REFUTED|UNKNOWN"
}
```

## Componenti candidati iniziali (da popolare con l'evidenza di [[reinterpreted_research]] una volta pronta)

| component_id | idea | stato iniziale (da confermare) |
|---|---|---|
| EC-VOLATILITY_EXPANSION | espansione di ATR/true range → persistenza direzionale | CANDIDATE (unica evidenza diretta oggi: VOLATILITY_BREAKOUT_CONFIRMED, HOLD_NEEDS_MORE_EVIDENCE) |
| EC-TREND_PERSISTENCE | trend esistente → continuazione probabile | CANDIDATE (implicito in ADX_RSI/SAR/MACD già validate positive, ma mai isolato come componente indipendente dal wrapper-strategia) |
| EC-LIQUIDITY_RECLAIM | sweep di un estremo + rientro → move nella direzione del rientro | CANDIDATE (WICK_SWEEP_* e i thread causali RETEST/TRUE_BREAK contengono probabilmente evidenza diretta - vedi re-interpretazione sezione 13) |
| EC-DISPLACEMENT | movimento direzionale ampio e rapido → continuazione a breve termine | UNKNOWN (nessun test diretto isolato finora, solo implicito) |
| EC-COMPRESSION | contrazione di volatilità sostenuta → espansione imminente (direzione non specificata) | UNKNOWN |
| EC-REJECTION | wick significativo → inversione a breve | CANDIDATE (PIVOT_WICK/WICK_SWEEP_REV toccano l'idea ma con risultati misti secondo i report esistenti - vedi re-interpretazione) |
| EC-SESSION_STATE | ora/sessione → probabilità di continuazione/reversal diversa | SUPPORTED (parziale — molti filtri di sessione già in uso e validati empiricamente in NEXUS, es. LONDON_BO, NY_REVERSAL) |

Questa tabella è un punto di partenza da riconciliare con l'output della re-interpretazione della ricerca esistente (sezione 13) prima di essere considerata definitiva — vedi `reinterpreted_research.md` per lo stato aggiornato SUPPORTED/REFUTED/UNKNOWN basato su evidenza già raccolta.
