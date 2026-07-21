# PR 7 — Settings schema and profiles

Elimina i default divergenti e la validazione mancante: i settings erano definiti
in `NXS_Inputs.mqh`, backend `DEFAULT_SETTINGS`, fallback frontend e seed, con
valori/nomi che potevano divergere; il backend accettava blob arbitrari senza
validazione di tipo/range (NaN inclusi).

## Contratto (fonte unica)

- `contracts/default-settings.json` — 46 default canonici, versionati.
- `contracts/settings.schema.json` — metadata per chiave: `type`, `default`,
  `minimum`/`maximum`, `scope`, `hot_reload`, `requires_restart`, `safety_class`,
  `description`.
- `contracts/generate_settings_schema.py` — generatore deterministico (idempotente).

Un **test** impone la regola cardine: `backend.DEFAULT_SETTINGS == contract` →
i default non possono più divergere silenziosamente.

## Validazione backend (`server/settings_schema.py`)

Requisiti del pack implementati e testati:
1. **chiavi ignote rifiutate** (salvo `allow_unknown=True` per il blob operativo
   che porta anche stato UI come `strategies`);
2. **NaN / infinito / stringhe non numeriche rifiutati**;
3. **int vs decimale** (`MaxConcurrent=3.5` → errore);
4. **range + invarianti cross-field** (DD/rischio ≥ 0, `MarketCloseGMT` 0..23);
5. **errori strutturati** (lista `{key, error, got}`);
6. **schema_version applicata** esposta;
7. **il moltiplicatore 0 non diventa mai 1** — nessuna coercizione di valore.

Le scritture `PUT/POST /api/settings` e `PUT /api/dashboard/settings` validano la
patch (chiavi canoniche strette, extra UI passano) e rispondono **422** con errori
strutturati su input non valido.

## Endpoint

- `GET /api/settings/schema` — metadata + default (il form frontend deve
  validare/generarsi da qui, non da fallback divergenti).
- `POST /api/settings/validate` — dry-run, ritorna errori senza persistere.

## Profili versionati

`build_locked_profile(settings)` produce un profilo con `profile_id`, `version`,
`schema_version`, `created_at/by`, `settings` validati, **`checksum` sha256
deterministico** e `status`. I settings sono validati prima del checksum: un
profilo non può essere costruito da valori invalidi.

## Verifica (ambiente backend — compilato e testato)

- `server/tests/test_settings_schema.py` → 15 test (non-divergenza, NaN/range/
  int, 0≠1, chiavi ignote, errori strutturati, profili con checksum, endpoint).
- Suite backend completa: **46/46**. Generatore idempotente.

## Adapter e verifica desktop

- **Frontend**: il form usa metadata tipati, limiti e validazione locale; un
  campo vuoto non viene trasformato in `NaN`.
- **EA/MQL5**: i default core del contratto sono allineati a `NXS_Inputs.mqh`;
  EA versione 3.30 compilato senza errori o warning.
- I test runtime MT5 non sono stati eseguiti, come richiesto.
