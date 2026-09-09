---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, audit, bug, mql5, code-review]
created: 2026-09-08
updated: 2026-09-08
---

# NEXUS EA — Audit esterno della cartella MQL5, verificato punto per punto (08/09)

## Origine

Audit statico ricevuto dall'utente (`NEXUS_EA_Code_Audit_20260907.md`),
condotto da un agente esterno che ha clonato `starmarketkiller/MAX` e
letto tutta `MQL5/` (73 `.mqh` + 7 `.mq5`, ~25.600 righe) incrociandola
col vault. Snapshot preso al commit `650033d` (07/09, prima dei fix di
stanotte su `InpRiskProfile`/`InpMinEntryScore`). Ogni punto sotto è
stato **riverificato da me direttamente sul codice attuale**, non
accettato per fede — vedi comando/prova per ciascuno.

## Il tema di fondo (confermato)

Una strategia deve passare **4 controlli indipendenti** mantenuti a
mano in file diversi, senza fonte di verità unica: `InpStrat_X`
(flag), `InpStrategySelector`→`NXS_SelectorAllows` (indice storico),
`NXS_Profile_Enabled(name)` (whitelist terzo cancello), e per
IFVG/FVG_MIT/OB_MIT/MALAYSIAN_SNR anche `NXR_ZoneStrategyEnabled`
(quarto gate, motore ombra parallelo). Nessuna collisione trovata
sull'indice selettore (buona notizia). Raccomandazione: consolidare in
un unico `struct NXS_StrategyDef[]`, coerente col P0.5 del roadmap —
non urgente ma il rapporto costo/beneficio più alto sul lungo periodo.

## CRITICI — verificati uno per uno

| # | Finding | Verifica | Esito |
|---|---|---|---|
| 2.1 | `InpRiskProfile` sovrascrive parametri custom | Snapshot 07/09 pre-fix: **vero allora**. Verificato ora: `NXS_Inputs.mqh:42` = `input int InpRiskProfile = 2;`, commit `f382c4f` (stanotte). Log runtime 07/09 21:53 conferma `[NEXUS PRESET] CUSTOM (using raw input values)` | ✅ **Già risolto stanotte, prima di ricevere l'audit** — finding ora obsoleto |
| 2.2 | `NXS_ProfitReclaim.mqh:73-79` bypassa tutte le protezioni | `grep SafeBuy\|SafeSell\|CheckProtections` sul file: righe 75/78 chiamano `NXS_SafeBuy/SafeSell` diretti, **nessuna** chiamata a `NXS_CheckProtections` nel file | ✅ **Confermato, ancora aperto** |
| 2.3 | SLReclaim usa il gate più debole (`NXS_CheckProtections` invece di `NXS_CommonExposurePreflight`) | `NXS_SLReclaim.mqh:112` chiama solo `NXS_CheckProtections`; il percorso normale (`NXS_Execution.mqh:486`) chiama `NXS_CommonExposurePreflight` | ✅ **Confermato, ancora aperto** |
| 2.4 | SLReclaim/ProfitReclaim ereditano un magic number stantio | Cercati tutti i caller di `NXS_TradeSetMagic()`: EA principale, Grid, Pyramid, InstManage, ReusePerformancePack — **né SLReclaim né ProfitReclaim compaiono** | ✅ **Confermato, ancora aperto** |
| 2.5 | 15 strategie bloccate da `NXS_Profile_Enabled` | Verificate a campione BJORGUM, ELLIOTT, JUDAS_SWING, SILVER_BULLET: **assenti** dalla whitelist (`NXS_StrategyProfiles.mqh:621-...`, `return false` di default a fine funzione, 49 righe `if` prima) | ✅ **Confermato per il campione** (lista completa di 15 non riverificata nome per nome) |
| 2.6 | `NXS_ConsecLossBrake.mqh` è codice morto | `grep -rl "NXS_ConsecLossBrake"` su tutto `MQL5/`: **solo il file stesso**, nessun `#include`/chiamata altrove | ✅ **Confermato** |
| 2.7 | `NXS_StructureMultiLayer.mqh` fabbrica un breakout rialzista su storico insufficiente | Non riverificato riga per riga (solo lettura del finding, non del codice indicato) | ⚠️ **Non verificato da me, plausibile** |
| 2.8 | `NXS_WebPush` sincrono in `OnTick`, timeout 20s | `NEXUS_EA_v2.mq5:1048`: `if(!MQLInfoInteger(MQL_TESTER)) NXS_WebPush(...)` dentro `OnTick()` (che parte riga 981); `NXS_WebBridge.mqh:249` conferma `WebRequest(..., 20000, ...)` | ✅ **Confermato — ma il guard `MQL_TESTER` esclude i nostri backtest**: rischio reale solo in demo/live, non nei test fatti finora |
| 2.9 | Licenza fallisce aperta su HTTP ambiguo (401/403 = irraggiungibile) | Visto solo il pattern "backend unreachable → TRIAL/grace" in `NXS_License.mqh`, non la distinzione 4xx vs timeout riga per riga | ⚠️ **Non verificato a fondo, plausibile** |

**Bonus trovato durante la verifica** (non nell'audit originale):
`InpMinMarginLevelPct` (`input`, default 500%, usato in
`NXS_Execution.mqh`) e `InpMinMarginLevel` (variabile semplice, **non**
`input`, default 200, usato separatamente in `NXS_Risk.mqh:155`) sono
due gate di margine diversi e indipendenti — chi imposta il margine via
`.set` vede solo il primo, il secondo resta fisso e invisibile.

## ALTA priorità — un finding già superato

L'audit segnala anche `InpMinEntryScore` (`NXS_Inputs.mqh:155`) non
`input` — **già risolto stanotte** (commit `478cf34`), stessa serata
in cui l'audit è stato scritto ma prima che arrivasse. Vedi
[[NEXUS EA - Step6 Ancora Identico, Bug Indipendente su InpMinEntryScore (08-09)]].
Buona notizia: conferma indipendente che il fix era necessario e
corretto.

Altri finding ALTA/MEDIA/BASSA nel documento originale non ancora
riverificati singolarmente (vedi file allegato originale per
l'elenco completo) — qualità comprovata dal tasso di conferma sopra
(8/8 controllabili confermati, salvo i 2 già risolti stanotte).

## Priorità d'azione proposta (ordine dell'audit, condiviso)

1. **2.2+2.3+2.4 insieme**: instradare SLReclaim e ProfitReclaim su
   `NXS_CommonExposurePreflight()` (non solo `NXS_CheckProtections`) +
   aggiungere `NXS_TradeSetMagic(InpMagic + MAGIC_CORE)` prima di ogni
   riapertura in entrambi i file. Stessa famiglia di bug, un solo giro
   di modifica + un test di regressione (rientro tentato durante freeze
   di conto, deve fallire).
2. **2.5**: decidere quali delle 15 strategie sbloccare per test
   isolato, una alla volta, come già fatto per le precedenti 7+1.
3. **2.6**: agganciare `NXS_ConsecLossBrake` per davvero, o rimuoverlo
   per evitare falsa sicurezza.
4. **2.7, 2.8**: 2.8 non urgente per i nostri test (guardia `MQL_TESTER`
   li esclude), ma da sistemare prima di qualunque demo/live reale.
   2.7 da riverificare e poi sistemare.
5. Consolidamento architetturale (§1) — investimento a lungo termine,
   non blocca nulla oggi.

**Nessuna di queste modifiche è stata applicata.** Come da regola del
progetto, nessun cambio a codice MQL5 live senza conferma esplicita
dell'utente per ciascun intervento.

## Collegamenti
[[NEXUS EA - Step6 Ancora Identico, Bug Indipendente su InpMinEntryScore (08-09)]] · [[NEXUS EA - Step5 Ancora Bacato, InpRiskProfile Non e' un Vero Input MQL5 (07-09)]] · [[NEXUS EA - FVG_CONT Prop-Compliant, Protezione Giornaliera Non Basta e Bug SLReclaim (07-09)]] · [[MOC - Trading]]
