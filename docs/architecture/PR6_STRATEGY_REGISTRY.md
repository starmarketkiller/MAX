# PR 6 — Canonical Strategy Registry

Elimina il drift 35/36/37: le strategie erano definite in modo indipendente in
EA, backend (`STRAT_NAMES_36`), backtest (`STRATEGIES`, con 4 `SCALP_*` extra),
frontend e knowledge. Ora c'è **una sola fonte di verità** e tutti derivano da lei.

## Artefatto canonico

- `contracts/strategy-registry.json` — 41 record: **37 live** + **4 research-only** (SCALP_*).
- `contracts/strategy-registry.schema.json` — JSON Schema (enum status/parity/family/risk_class).
- `contracts/generate_registry.py` — generatore **deterministico** dalle fonti reali
  (knowledge id+selector, `NXS_Profile_TF` per i timeframe, `backtest.STRATEGIES`
  per la presenza research). Rigenerabile, idempotente.
- `contracts/validate_registry.py` — valida (id univoci, alias senza collisioni,
  selector_index unici tra i live, coerenza flag, **Regola 1: unknown = errore**)
  e **riconcilia** contro backend/backtest/knowledge.

## Drift risolto (dati reali)

| fonte | prima | note |
|---|---|---|
| backend `STRAT_NAMES_36` | **36** | usava `CISD`, mancava `ELLIOTT` |
| backtest `STRATEGIES` | **40** | 36 + `CISD` + 4 `SCALP_*` |
| frontend | 37 | lista propria hardcoded |
| knowledge | 37 | id canonici (`THREE_BAR_DELIVERY_BREAK`, `ELLIOTT`) |
| **registry (ora)** | **41** | 37 live (CISD = alias) + 4 research-only |

Decisioni chiave:
- `CISD` è **alias** di `THREE_BAR_DELIVERY_BREAK`, non una strategia separata.
- `ELLIOTT`: live ma **senza** controparte research → `research_parity = NOT_IMPLEMENTED`
  (rename `FIVE_SWING_IMPULSE` resta parcheggiato, non applicato qui).
- `DISP_REBAL`: `DISABLED` (attiva nel codice, disabilitata in produzione).
- `SCALP_*`: `RESEARCH_ONLY`, `live_implementation=false`, mai `default_enabled`.

## Backend

- `STRAT_LIST = strategy_registry.live_ids()` (37) — **non più** `backtest.STRAT_NAMES_36` (36).
- `server/strategy_registry.py`: loader canonico con `resolve()` che **solleva
  `UnknownStrategyError`** (mai fallback), `canonical_id()` (alias→id), conteggi.
- Endpoint: `/api/backtest/strategies` ora riporta `total_ea=37` + `research_only`;
  nuovi `/api/strategies/registry` (artefatto) e `/api/strategies/resolve/{name}`
  (404 su ignoto, dimostra la Regola 1).
- I loop UI (status per-strategia) usano gli id canonici → compare `ELLIOTT`,
  sparisce l'alias `CISD`. Il motore di backtest (`backtest.STRATEGIES`) non è
  toccato (piano research, PR11).

## Campi provvisori (domain judgment, revisionabili senza codice)

`family` è una tassonomia **provvisoria** in `FAMILY_MAP` (generatore), non un dato
estratto. `supported_timeframes` deriva da `NXS_Profile_TF` dove presente, `["*"]`
per le 8 strategie senza profilo TF (AMD_*, JUDAS, LDN/NY_REVERSAL, PO3,
SILVER_BULLET, ELLIOTT). `risk_class` = STANDARD/RESEARCH.

## Adapter generati

Il JSON è la fonte e `contracts/generate_registry.py` genera anche:
- **MQL5**: `NXS_StrategyRegistry.mqh`, con normalizzazione `_NXR` e alias
  `CISD`; gli identificatori sconosciuti bloccano il preflight di esecuzione.
- **Frontend**: `strategyRegistry.js`, consumato dalle pagine senza liste o
  conteggi hardcoded.
- **Backend/backtest**: loader canonico, alias espliciti e validation error per
  gli identificatori sconosciuti.

## Verifica

`python3 contracts/validate_registry.py` → validazione OK, riconciliazione OK.
La suite backend verifica anche gli adapter generati e il rifiuto degli ID
sconosciuti. La build frontend e la compilazione MetaEditor completano la
verifica statica; i test runtime MT5 sono esclusi su richiesta.
