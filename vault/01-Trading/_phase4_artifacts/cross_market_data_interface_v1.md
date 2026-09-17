# Cross-Market Data Interface v1 (Phase 5.5 sec.13)

Interfaccia/schema per poter aggiungere in futuro fonti cross-market — **nessuna fonte integrata in questa fase**, solo lo schema.

## Schema per fonte

```json
{
  "source_name": "DXY | US_10Y_YIELD | XAGUSD | VOL_PROXY | COT_POSITIONING",
  "frequency": "tick|1min|1h|1d|1w",
  "timezone": "IANA tz o UTC esplicito",
  "availability": "NOT_YET_INTEGRATED | INTEGRATED | DEPRECATED",
  "lag": "ritardo tipico fra evento economico e valore osservabile",
  "publication_delay": "vedi nota sotto - CRITICO per dati macro/positioning",
  "causal_safety": "CAUSAL_SAFE | CAUSAL_UNSAFE | CONDITIONAL | UNKNOWN",
  "licensing_cost": "gratuito | a pagamento (specificare)",
  "notes": "..."
}
```

## Nota critica (esplicitamente richiesta): timestamp di disponibilità reale, non data economica nominale

Per dati macro/positioning, il record DEVE usare il timestamp in cui il dato era **realmente disponibile a un partecipante di mercato**, mai la data/periodo a cui il dato SI RIFERISCE. Esempio: il report COT del venerdì si riferisce alla posizione di martedì — usare la data di martedì come timestamp sarebbe un leakage temporale classico (il dato di martedì non era osservabile fino a venerdì). Stesso principio per NFP, CPI, dati PIL: il timestamp di rilascio pubblico, mai la data di riferimento del periodo misurato.

## Fonti candidate (dallo schema Market State Vector v1 di Phase 4, qui formalizzate)

| source_name | frequency | timezone | availability | lag | publication_delay | causal_safety | licensing_cost |
|---|---|---|---|---|---|---|---|
| DXY (USD index) | tick/1min (se da provider FX) | UTC | NOT_YET_INTEGRATED | ~real-time se da feed FX diretto | N/A (prezzo di mercato, non dato macro) | CAUSAL_SAFE se da tick reali sincronizzati; CONDITIONAL se da fonte con revisioni | gratuito via feed FX standard (es. Dukascopy ha un proxy sintetico majors), a pagamento per feed istituzionali |
| US 10Y Treasury Yield | 1min-1d a seconda del provider | America/New_York (mercato) | NOT_YET_INTEGRATED | minuti-ore secondo provider | i rendimenti "ufficiali" di chiusura hanno spesso un ritardo di pubblicazione di ore | CONDITIONAL - molte fonti pubblicano solo chiusure giornaliere con revisioni intraday non tracciate | gratuito (FRED) per dati giornalieri con ritardo; a pagamento per intraday |
| XAGUSD (silver) | tick (stessa fonte Dukascopy già in uso) | UTC | NOT_YET_INTEGRATED | nessuno (stesso downloader già validato in Phase 4) | N/A | CAUSAL_SAFE (stessa pipeline già validata per XAUUSD) | gratuito, stesso costo marginale zero del downloader esistente |
| Proxy di volatilità (es. GVZ - Gold Volatility Index) | 1d | America/New_York | NOT_YET_INTEGRATED | 1 giorno | pubblicazione a fine giornata, nessun accesso intraday gratuito noto | CONDITIONAL | spesso a pagamento per storico esteso |
| COT / positioning (CFTC) | 1w (report del venerdì, riferito al martedì precedente) | America/New_York | NOT_YET_INTEGRATED | **3 giorni** (martedì→venerdì, vedi nota sopra) | il report è pubblicato il venerdì alle 15:30 ET — questo, non il martedì, è il timestamp di disponibilità da usare | CAUSAL_SAFE SE il timestamp di pubblicazione venerdì viene usato correttamente; CAUSAL_UNSAFE se qualcuno usa per errore la data del martedì | gratuito (cftc.gov) |

## Priorità (ereditata da Phase 4, non rivista qui)

XAGUSD (silver/gold ratio) resta il candidato a costo/complessità più basso (stessa pipeline Dukascopy già validata). DXY è il più economicamente plausibile ma richiede una fonte FX aggiuntiva. COT è l'unico per cui la regola "timestamp di disponibilità reale" è assolutamente vincolante fin dal primo giorno di integrazione, per evitare un leakage temporale strutturale fin dalla progettazione.
