# NEXUS - Phase 7.8D PRE-RUN DATA SEAL

**Baseline:** `a0fe99e` (Phase 7.8C, `READY_FOR_PRE_RUN_SEAL`). Corregge la segmentazione temporale di 7.8C e verifica **onestamente** l'accesso ai dati storici reali richiesti dal PRE-RUN MANIFEST. Nessun Serious validation eseguito, nessun outcome letto, nessun trade result generato.

**Conferma esplicita: SERIOUS_VALIDATION_NOT_EXECUTED. NO STRATEGY OUTCOME ACCESSED.**

---

## 1. Correzione segmentazione temporale (annotazione, 7.8C non modificato)

**Problema trovato:** `PRIMARY_FRESH_VERDICT_WINDOW` (~2.5 anni) non garantisce tre anni solari completi comparabili - usare implicitamente "Year 1/2/3" (ereditato dal precedente SAR/MACD, che aveva 3 anni pieni) renderebbe il criterio "2 dei 3 segmenti non negativi" dipendente dalla posizione calendariale delle date, non dalla struttura del test.

**Corretto:** `T1/T2/T3` = split cronologico della finestra FRESH in tre blocchi contigui di durata il piu' possibile uguale (tercile temporale, mai anni solari nominali). Vincoli: T1∪T2∪T3 = intera finestra FRESH, nessuna sovrapposizione, nessun buco, durate approssimativamente uguali. **Nessun outcome letto per costruire questi segmenti** - puramente strutturale. I criteri restano in sostanza invariati (2/3 segmenti non-negativi; nessun singolo segmento >100% del risultato netto con gli altri combinati negativi), solo applicati a T1/T2/T3 invece di anni nominali.

## 2. Verifica onesta dell'accesso ai dati (nessun valore fabbricato)

Controlli **eseguiti davvero** al momento del build (non assunti):

| Controllo | Metodo | Risultato |
|---|---|---|
| Processo MT5 in esecuzione | PowerShell `Get-Process -Name terminal64,terminal` | **Nessuno in esecuzione** |
| Capacita' LocalBridge | Ispezione diretta di `LocalBridge/nexus_local_worker.py` (hash verificato) | Handler reali: `ping/compile_ea/restart_mt5/deploy_files/open_chart/apply_template` - **nessuna azione di sync storico o esecuzione Tester** |
| Cache storica GOLD preesistente | Ricerca file `.hcc` su disco | Trovata (2 terminali, XMGlobal-MT5 7/9) ma **stale** - ultimo file modificato 2026-07-20/04-27, ~2 mesi prima della data odierna (2026-09-21) |

**Conclusione:** usare questa cache stale per costruire il manifest equivarrebbe a dichiarare un "sync" mai realmente avvenuto in questa fase - esplicitamente vietato dall'istruzione originale. **Nessuna data/hash/tick-coverage fabbricata.**

## 3-8. Sezioni bloccate (nessun valore inventato dentro di esse)

`exact_windows`, `dataset_identity`, `real_tick_coverage` restano non risolvibili senza un run MT5 reale. **Gli hash di protocollo gia' congelati** (non richiedono dati storici) sono invece gia' pinnabili ORA: strategy commit `f035d30`, hash di prereg (7.8B), hash di authorization (7.8C), hash di cost model - pronti per essere riportati nel manifest reale quando i dati saranno sincronizzabili.

## 9. Final status

**`PRE_RUN_SEAL_BLOCKED`** - motivo: `PRE_RUN_SEAL_BLOCKED_NO_DATA_ACCESS`. Distinto esplicitamente dai blocker concettuali di 7.8B/7.8C (tutti gia' `RESOLVED`): questo e' un blocco di **accesso/ambiente**, non metodologico - il protocollo stesso resta interamente valido e pronto. Si sbloccherebbe con l'esecuzione di questa fase da una sessione con accesso reale a un terminale MT5 collegato al broker, o un'estensione del LocalBridge worker con un'azione dedicata di sync/tester - nessuna delle due disponibile qui.

## Regressione

52/52 PASS su questa suite. **0 regressioni** sulle altre 27 suite Phase 7 (28 totali). Verificato: `volatility_breakout_serious_3y_run_authorization_v1.json` (7.8C) hash invariato.

## Deliverables

`volatility_breakout_prerun_seal_status_v1.json`, `build_volatility_breakout_prerun_seal_status.py`, `test_volatility_breakout_prerun_seal_status.py` - tutti in `server/research_scripts/phase7/phase7_8d/`. Nessuna modifica retroattiva.

---

**SERIOUS_VALIDATION_NOT_EXECUTED. NO STRATEGY OUTCOME ACCESSED. NO TRADE RESULTS GENERATED. NO EDGE DISCOVERY PERFORMED.**

**Progresso verso demo (invariato): ~68%.**

```
PRIMO SERIOUS BACKTEST: 100%
VERSO DEMO: ~68%
██████▊░░░
7.8C:
READY_FOR_PRE_RUN_SEAL ✓
7.8D:
segmentazione T1/T2/T3 corretta ✓
PRE_RUN_SEAL_BLOCKED_NO_DATA_ACCESS
(nessun terminale MT5 raggiungibile
da questa sessione di ricerca)
PROSSIMO:
eseguire questa fase da un ambiente
con accesso MT5 reale
→ PRE-RUN MANIFEST con dati veri
→ verify seal → RUN
```

Il protocollo scientifico e' completo e privo di gradi di liberta' inventati. Cio' che manca ora e' puramente un accesso ambientale, non una decisione di metodo.
