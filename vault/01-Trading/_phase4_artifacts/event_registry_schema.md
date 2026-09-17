# Event Registry — schema v1

Gli eventi sono separati completamente dalle strategie (vedi [[market_ontology]] — Event). Un detector di evento non implica alcuna azione di trading.

## Schema

```json
{
  "schema_version": 1,
  "event_id": "EVT-20260917-XAUUSD-H4-SWEEP_LOW-000123",
  "event_family": "SWEEP",
  "detector": "sweep_low_v1",
  "detector_version": 1,
  "symbol": "XAUUSD",
  "timeframe": "H4",
  "observation_timestamp": "2026-09-17T04:00:00Z",
  "direction": -1,
  "magnitude": {
    "unit": "ATR",
    "value": 1.3
  },
  "market_state_ref": "MS-20260917-XAUUSD-H4-0400",
  "causal_provenance": {
    "bars_used": ["...timestamps fino a observation_timestamp incluso..."],
    "lookahead_checked": true
  },
  "source_code_ref": "server/backtest.py::detect_sweep_low_v1"
}
```

Campi obbligatori: `event_id` (univoco, deterministico da symbol+tf+family+timestamp+seq), `event_family`, `detector` (nome + versione, per poter distinguere detector riformulati nel tempo), `observation_timestamp`, `direction`, `magnitude` (sempre con unità esplicita, es. ATR o pips, mai un numero nudo), `market_state_ref` (puntatore allo snapshot di Market State Vector all'observation point), `causal_provenance` (dichiarazione esplicita di quali barre sono state usate e che non c'è look-ahead — spot-check obbligatorio in fase di detector review).

## Famiglie candidate (sezione 4 della richiesta)

| event_family | definizione breve | nota causale |
|---|---|---|
| BREAKOUT | prezzo chiude oltre un livello/range di riferimento | confermare solo a chiusura barra, non intrabar, salvo detector esplicitamente tick-based e dichiarato come tale |
| FAILED_BREAKOUT | breakout seguito da rientro nel range entro N barre | l'esito "failed" è per definizione noto solo DOPO — questo è un evento con osservazione ritardata: l'event_id va comunque ancorato al momento del breakout iniziale, con un campo separato `confirmed_at` per quando il fallimento è confermato; non usarlo come feature di stato PRIMA di quel momento |
| SWEEP | prezzo supera un estremo recente (liquidità) e si ritira | l'estremo di riferimento deve essere definito da barre STRETTAMENTE precedenti |
| RECLAIM | prezzo rientra sopra/sotto un livello dopo averlo perso | come sweep, livello di riferimento da barre precedenti |
| REJECTION | wick significativo con chiusura lontana dall'estremo | rischio: la "significatività" del wick va definita con soglia ex-ante (es. % di ATR), non scelta a posteriori |
| RETEST | prezzo ritorna su un livello già rotto/reclaimed | serve un "evento genitore" (il breakout/reclaim originale) — modellare come relazione, non evento isolato |
| DISPLACEMENT | movimento direzionale ampio e rapido rispetto a volatilità recente | soglia di ampiezza ex-ante in unità di ATR |
| IMBALANCE_CREATION | gap price-based (proxy FVG) tra barre consecutive | dipendente da timeframe, va dichiarato |
| COMPRESSION | contrazione di volatilità/range sostenuta su N barre | soglia percentile ex-ante (es. ATR sotto il 20° percentile rolling) |
| VOLATILITY_EXPANSION | espansione di ATR/true range oltre soglia | come VOLATILITY_BREAKOUT_CONFIRMED (già implementato, da migrare come Event condiviso invece che logica interna a una singola strategia) |
| EXHAUSTION | perdita di momentum dopo movimento direzionale prolungato | richiede definizione quantitativa (es. divergenza RSI + decelerazione ROC), non discrezionale |
| RANGE_ACCEPTANCE | prezzo permane dentro un range per N barre dopo un test di estremo | soglia N ex-ante |
| RANGE_REJECTION | prezzo testa un estremo di range e si allontana rapidamente | come REJECTION ma ancorato a un range esplicito, non a un singolo livello |
| TREND_ACCELERATION | slope/ROC in aumento su una direzione già in trend | va distinta da DISPLACEMENT (che non richiede trend pre-esistente) |
| TREND_DECAY | slope/ROC in diminuzione dentro un trend esistente | precursore candidato per un time-stop naturale (sezione survival) |

Ogni detector reale (codice Python/MQL5) va mappato 1:1 a UNA riga di questa tabella con versione esplicita, prima di essere usato in un Setup.
