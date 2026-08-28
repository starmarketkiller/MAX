#nexus #trading #decision #baseline #p0

# DEC — Baseline tecnica corrente (INFRA-001 / P0.1)

**Data**: 18/07/2026 · **Stato**: attiva · **Fonte**: MASTER ROADMAP v3, ticket P0.1

## Decisione

La baseline tecnica del progetto è congelata su:

| Campo | Valore |
|---|---|
| Commit codice MQL5 | `e6ce816` (ultimo commit che tocca `MQL5/` prima dello sweep 1:500) |
| Ref git | branch `baseline-post-infra-audit` (il proxy git rifiuta i tag: usato il branch, opzione equivalente prevista dalla roadmap) |
| Versione EA | `2.50` (`#property version`) |
| Hash aggregato sorgenti MQL5 | `04fa338252b13ab2db6062e9fb84d566` (riproducibile, vedi manifest) |
| Compilazione | 0 errori / 0 warning su entrambi i terminali (18/07, agente desktop) |
| Config sweep | `results/sets/SWEEP_37_DataCollectionMode.set`, deposito €1000, **leva 1:500**, timeout 6h/passata, identity check attivo |

Manifest completo (macchina-leggibile): `results/manifests/baseline_manifest.json`.

## Cosa significa

Tutti i risultati prodotti da qui in avanti si confrontano contro QUESTA baseline. Qualsiasi risultato precedente al 18/07 è considerato **non confrontabile** (due cause indipendenti: gate "1 posizione per strategia" mancante fino al 17/07 sera; leva 1:100 invece di 1:500 fino al 18/07 — margin gate falsava le aperture).

## Campi ancora da completare (agente desktop, non bloccanti)

Il manifest ha campi `DA_COMPILARE_AGENTE_DESKTOP`: checksum `.ex5`, build MetaEditor/MT5, broker e specifica simbolo, timezone server, finestra date/modalità tick/spread/quality del Tester. Vanno riempiti alla prossima occasione utile — il criterio "done" del ticket (un secondo operatore ricrea la stessa build e ottiene lo stesso identificatore) è soddisfacibile solo con il checksum `.ex5` registrato.

## Vincolo

Ogni modifica futura a `MQL5/` sposta la baseline SOLO se accompagnata da: nuovo tag, manifest aggiornato, ricompilazione verificata. Non esistono più "build implicite".

## Collegamenti

[[MOC - Trading]] · [[NEXUS EA - MASTER ROADMAP v3]] · [[NEXUS EA - Roadmap verso il Live]] · [[NEXUS EA - Caccia al Bug Esecuzione (17-07)]]
