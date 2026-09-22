# NEXUS - Phase 7.9B BREAKOUT_ACC Lifecycle Formalization

**Baseline:** `ea0013e090ae2776fe61565392d19991c6dbecc4` (Phase 7.9A, `FORMALIZE_EXISTING_CANDIDATE` → `BREAKOUT_ACC`). Solo audit statico — nessun backtest, nessuna ottimizzazione, nessun nuovo outcome, nessuna modifica alla strategia.

**La domanda di questa fase non era "BREAKOUT_ACC funziona?" ma "sappiamo esattamente cos'è, e i vecchi risultati appartengono davvero a quella stessa cosa?"**

---

## 1. Identità esatta

`selector_index=9` (verificato contro `contracts/strategy-registry.json`), master switch `InpStrat_BREAKOUT_ACC` (default `true`), funzione `NXS_Strat_BreakoutAcc()` (`NXS_Strategies.mqh`), router (`NEXUS_EA_v2.mq5`, stesso percorso "profili per-strategia" già verificato per VOLBRK), profilo `PERIOD_D1` (coerente col registro), `live_implementation=true`, `research_implementation=true`.

**Attenzione all'enum condiviso**: `STRAT_BREAKOUT_ACC` è condiviso da **tre** strategie distinte (`BREAKOUT_ACC`, `VOLATILITY_BREAKOUT_CONFIRMED`, `Z_SCORE_BREAKOUT`) — la vera identità è sempre `stratName`, verificato distinto per ciascuna. Nessuna confusione trovata nel codice attuale.

## 2. Lifecycle contract — 12 campi, tutti risolti

`SETUP` (range 20 barre, offset shift [3..22]), `TRIGGER` (doppia chiusura consecutiva = "Acceptance", cooldown esplicito 8 barre per direzione — fix del 02/09 per un bug reale trovato dall'utente: 106/201 trade nudi erano inseguimenti dello stesso movimento), `ENTRY` (a mercato, non a chiusura barra), `DIRECTION`, `INVALIDATION_STOP`/`TARGET` (SL 1.0×ATR / TP 4.5×ATR — **non nativi al setup** come in VOLBRK, ma un overlay generico di framework con moltiplicatori dedicati via profilo — classificato `SATISFIED_BY_EQUIVALENT_MECHANISM`), `TIMEOUT` (**assente nativamente**, l'unico overlay di framework — MaxHold 12h — è disattivato in Research Mode, quindi `NOT_REQUIRED_BY_DESIGN`), `MANAGEMENT` (HTF filter attivo, trailing largo 2.5×ATR), `POSITION_SIZING` (0.5%/trade, "Tier C"), `TIMEFRAME` (D1), `INSTRUMENT` (GOLD/XAUUSD).

## 3-4. Overlay del framework separati dalla logica nativa; reachability statica

SL/TP/trailing/timeout sono tutti overlay generici del framework (`NXS_DefaultSLTP`, `NXS_Prot_CheckMaxHold`), non calcolati dalla struttura del setup. **`STATIC_REACHABILITY_PASS`**: master switch → selector → router → funzione → profilo, tutti collegati coerentemente, verificato senza eseguire MT5.

## 5-7. Evidence lineage — una contraddizione reale trovata e risolta

Esaminate **quattro fonti**, non solo quella citata in 7.7A:

| Fonte | Data | Claim | Identità col codice attuale |
|---|---|---|---|
| A — `Breakout Acc.md` | luglio | 101 trade/+4.3R/5-6 anni positivi | **EVIDENCE_IDENTITY_UNVERIFIED** |
| B — Screening sito 10y | luglio | Python, PF 1.32→1.86, n=128 | PARTIAL (manca il cooldown, introdotto dopo) |
| C — Walk-forward 5 finestre | agosto | PF 2.71-2.01, solo 1/5 vincente | **EVIDENCE_IDENTITY_UNVERIFIED** (parametri SL1.5/TP3.0 diversi dal profilo, niente HTF) |
| **D — Phase E** | **16/09** | Parity MT5↔Python dedicata | **EVIDENCE_IDENTITY_CONFIRMED** |

**La scoperta centrale**: Fonte A dichiara 101 trade su ~6 anni; Fonte D (un audit dedicato e molto più rigoroso, **cronologicamente precedente al registro 7.7A**) ha misurato — su quasi lo stesso arco temporale (7,5 anni, storia massima disponibile) — **esattamente 4 trade MT5 reali, tutti in perdita** (prezzi 2019-2020 confermati genuini, non sintetici). I due numeri sono incompatibili sullo stesso esperimento. Fonte A è stata **retrocessa** a `EVIDENCE_IDENTITY_UNVERIFIED` (provenienza non dichiarata con precisione) — **non trattata come discovery evidence canonica**, come richiesto esplicitamente. Nessun file precedente modificato.

**Verdetto ufficiale di Phase E, mai contraddetto qui**: `HOLD_NEEDS_MORE_EVIDENCE` — non per un difetto della logica (su dati Python, storico completo, con cooldown: n=27, PF=3,55, DD=5,77%, "la più pulita delle 4 candidate esaminate"), ma per un limite strutturale di campione sul lato MT5 (0,53 eventi/anno, dichiarato irriducibile con lo storico oggi disponibile).

**Gap di governance segnalato**: il registro 7.7A (21/09) cita solo la Fonte A ottimistica, senza mai menzionare Phase E (16/09, precedente). Stesso pattern già documentato in 7.7A per altri candidati — annotato, non corretto retroattivamente.

## 6. Qualità dell'evidenza — separata dalla formalizzazione

Formalizzazione: **HIGH**. Identità del segnale: **HIGH** (parity Python/MQL5 confermata). Identità dell'esecuzione: **LOW** (solo 4 trade reali). Qualità campionaria: **LOW**. Rigore statistico: **LOW** (mai un Wilson CI o dependence audit). Indipendenza: **UNKNOWN**.

## 8-9. Verdetto e prossimo esperimento

**`FULL_STRATEGY_SPEC_VERIFIED`** (formalizzazione), **`HOLD_NEEDS_MORE_EVIDENCE`** (readiness, invariato da Phase E). Prossimo esperimento ammissibile: **`REANALYZE_EXISTING_RAW_RESULTS`** — il dataset Python n=27 (storico completo, cooldown+HTF, motore condiviso già pronto tramite `breakout_acc_cooldown=True`) va rigenerato (deterministico, nessun nuovo esperimento MT5) e sottoposto finalmente a un trattamento statistico rigoroso. Un nuovo Fast Structural su MT5 ripeterebbe lo stesso gate già dichiarato non soddisfatto da Phase E, sprecando tempo di calcolo. **Nessun test eseguito in questa fase.**

**Questo audit non promuove BREAKOUT_ACC** — resta il candidato aperto col prossimo passo più economico, non una strategia comprovata.

## Vincoli preservati

`VOLATILITY_BREAKOUT_CONFIRMED` e `H006` non riaperti. `HISTORICAL_VOLUME_CONTRACT_WALLS` resta solo backlog.

## Deliverables

`breakout_acc_lifecycle_contract_v1.json`, `breakout_acc_evidence_lineage_v1.json`, `breakout_acc_formalization_decision_v1.json`, `verify_breakout_acc_lifecycle_formalization.py`, `test_phase_7_9b.py`.

## Regressione

33/33 PASS sulla nuova suite. 34/36 delle altre suite Phase 7 passano; i 2 fallimenti sono gli stessi già noti (7.8E, 7.8H), invariati.

---

```
PRIMO SERIOUS BACKTEST: 100% ✓
VERSO DEMO: ~68%
7.9B: COMPLETATA ✓
BREAKOUT_ACC: FULL_STRATEGY_SPEC_VERIFIED
              readiness = HOLD_NEEDS_MORE_EVIDENCE
SCOPERTA: la fonte "+4.3R/101 trade" citata in 7.7A e' inaffidabile -
          Phase E (16/09, mai propagata) trova solo 4 trade MT5 reali
          in 7,5 anni, tutti in perdita - limite di campione, non di logica
PROSSIMO: REANALYZE_EXISTING_RAW_RESULTS (dataset Python n=27 gia' pronto,
          nessun nuovo esperimento MT5)
```
