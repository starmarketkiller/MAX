# 06 — Versioning (Canonical Schema v1)

## Versioni correnti
| Cosa | Versione |
|---|---|
| Canonical Schema (questo contratto) | **1.0.0** |
| `knowledge_schema_version` (runtime, nei DB) | 2 |
| `import_engine_version` | 1.1.0 |
| `timeline_engine_version` | 1.0.0 |

## Policy
1. **Additivo = minor bump**, retrocompatibile: nuovi campi opzionali, nuovi enum value, nuove entità.
2. **Cambio di forma/nome = major bump** + migrazione documentata + rigenerazione dei DB derivati.
3. **I file sorgente non si migrano mai** (CSV/manifest/report = verità storica immutabile): si migra solo il derivato.
4. Ogni record porta con sé `import_engine_version`/`knowledge_schema_version` → si sa sempre con quale versione è stato scritto.
5. I DB derivati sono **ricostruibili da zero** in modo deterministico dai sorgenti: la migrazione peggiore possibile è "cancella e rigenera".
6. Il Canonical Schema cambia SOLO con revisione architetturale approvata (registro milestone).
