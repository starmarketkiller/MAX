# NEXUS - Phase 3 Semantic and Registry Correction

Correzione bloccante richiesta dopo verifica diretta del commit Phase 3 (VOLATILITY_BREAKOUT_CONFIRMED). Tre problemi analizzati, due corretti nel codice, uno verificato-e-scartato come non-problema.

---

## 1. Entry semantics vs FROZEN_SIGNAL_SPEC_V1 — BLOCCANTE, CORRETTO

**Problema trovato.** FROZEN_SIGNAL_SPEC_V1 dichiara `entry = signal-bar close`. `NXS_Strat_VolatilityBreakoutConfirmed()` invece impostava:
```
s.entryRef = (brkDir==1) ? SymbolInfoDouble(g_sym, SYMBOL_ASK) : SymbolInfoDouble(g_sym, SYMBOL_BID);
```
cioè prezzo live al momento della valutazione, non la chiusura della barra segnale. SL, TP (calcolato come 1R da `entryRef`) e quindi R stesso erano ancorati al prezzo sbagliato rispetto alla specifica congelata. Questo NON è un semplice BAR_ALIGNMENT_DIFFERENCE: cambia il riferimento usato per tutta la matematica di rischio.

**Causa.** `SymbolInfoDouble(...ASK/BID)` è la convenzione DEFAULT del motore (usata da `NXS_DefaultSLTP()`, condivisa da ~40 strategie che non hanno una spec esterna congelata). La nuova strategia ha copiato questa convenzione generica invece di implementare la propria spec esplicita.

**Verifica del percorso di esecuzione (per capire cosa cambia davvero).**
- Detector Python (`server/backtest.py sig_volatility_breakout_confirmed`): entry = `c1` (chiusura barra segnale).
- MQL5 pre-fix: `entryRef` = ASK/BID live.
- SL: `ll`/`hh` (estremo range) in entrambi i casi — invariato.
- TP: `entryRef ± 1R` dove `R = |entryRef - SL|` — dipende da `entryRef`, quindi ERA disallineato pre-fix.
- Esecuzione reale nel tester: `NXS_DoBuy`/`NXS_DoSell` in `NXS_Globals.mqh` impostano SEMPRE `req.price = SymbolInfoDouble(sym, SYMBOL_ASK/BID)` al momento dell'invio ordine, **indipendentemente** da `entryRef`. Questo vale per ogni strategia del motore, non è modificabile qui e non fa parte del problema di specifica — è slippage di esecuzione ordinario.

Quindi `entryRef` pre-fix era doppiamente sbagliato: non serviva né a fissare il prezzo di fill reale (quello è sempre live) né a rispettare la spec (che vuole `c1` come riferimento per R/SL/TP).

**Correzione applicata.** `MQL5/Include/NEXUS_v1/NXS_Strategies.mqh`, funzione `NXS_Strat_VolatilityBreakoutConfirmed()`:
```
s.entryRef = c1;   // era: SymbolInfoDouble(g_sym, SYMBOL_ASK/BID)
```
`c1` era già calcolato in precedenza nella funzione (chiusura barra segnale, usata anche per il check di rottura). Nessun altro valore della spec toccato: N=20, moltiplicatore ATR 1.0x, TP=1R, timeout 40 barre, SL=estremo range — tutti invariati.

**Parity (Model=1, 6 mesi, stesso file .ini riusato).**
- Pre-fix: 16 trade.
- Post-fix: 28 trade.
- Le prime aperture della sequenza sono le STESSE (stesso timestamp, stesso outcome), solo con `entryRef`/TP leggermente diversi (es. prima apertura 2026.03.02 01:30 → entry 5354.51 pre vs 5278.53 post). La divergenza cresce nel tempo: uno spostamento anche piccolo di TP sposta l'orario di chiusura del trade, che sposta la disponibilità degli slot di esposizione (`InpMaxConcurrent=4`, `InpMaxPerDirTF=4`), che a cascata cambia quali segnali successivi riescono a entrare. Quindi il cambio di conteggio è reale e materiale, non rumore — conferma che la correzione NON era cosmetica.

**Fast Structural (Model=4, tick reali, stesso .ini riusato).**
- Pre-fix: n=14, PF=1.165, net=$263.20, expectancy=$18.80, BUY PF=0.734, SELL PF=2.236, DD=7.99%.
- Post-fix: n=14, PF=1.156, net=$247.90, expectancy=$17.71, BUY PF=0.721, SELL PF=2.236, DD=7.99%.
- Stesso numero di trade, stessi mesi, stesso split BUY/SELL (9/5), stessa ripartizione sl/tp (7/7). Solo il P&L per trade cambia leggermente (anchor price leggermente diverso → livelli SL/TP leggermente diversi).

**Riconciliazione della differenza fra i due test (richiesta esplicitamente).** Model=1 genera tick sintetici interpolati da OHLC a 1 minuto: il prezzo "live" disponibile alla valutazione può discostarsi in modo non trascurabile dalla vera chiusura di barra `c1`, quindi il gap pre-fix (ASK/BID vs c1) era abbastanza ampio da spostare TP/orari di chiusura e innescare la cascata sugli slot di esposizione descritta sopra. Model=4 usa tick reali continui: in un mercato continuo il primo tick disponibile dopo la chiusura di barra è già vicinissimo a `c1`, quindi il gap pre-fix era piccolo fin dall'inizio — la correzione sposta i livelli di poco e non cambia quali segnali passano i filtri di esposizione. Conclusione: l'impatto "grande" osservato in parity è in parte un artefatto della granularità di Model=1, non una prova che il trading reale sarebbe cambiato in modo drastico — ma la correzione resta corretta e necessaria perché la spec è vincolante indipendentemente dalla dimensione dell'effetto misurato in un dato modello di test.

**Verdetto invariato.** Il verdetto della strategia resta HOLD_NEEDS_MORE_EVIDENCE (n=14 è comunque sotto soglia per conclusioni forti); PF, expectancy e DD restano nello stesso ordine di grandezza pre/post.

---

## 2. Registry source-of-truth — BLOCCANTE, CORRETTO

**Problema trovato.** In Phase 3, `MQL5/Include/NEXUS_v1/NXS_StrategyRegistry.mqh` (file generato automaticamente) era stato patchato a mano per aggiungere `VOLATILITY_BREAKOUT_CONFIRMED`, perché `knowledge/strategy_database.json` non la conosceva e `contracts/generate_registry.py` l'avrebbe quindi rigenerata senza di essa, ributtando fuori tutti i segnali via preflight (`NXS_StrategyKnown()` li blocca tutti se l'id non è in whitelist). Questo non è uno stato finale accettabile: al primo run del generatore la patch manuale sarebbe andata persa silenziosamente.

**Causa.** `knowledge/strategy_database.json` (la vera source-of-truth) non era mai stato aggiornato quando è stata implementata la nuova strategia in Phase 3.

**Correzione.**
1. Aggiunta voce a `knowledge/strategy_database.json` → `strategie`: `nome=VOLATILITY_BREAKOUT_CONFIRMED`, `selector_index=56`, `stato=attiva`, `implementata=si`, con nota in `fix_applicati` sulla correzione dell'entry semantics. `totale_strategie` aggiornato 51→53 (52→53 di fatto, essendo 51 già disallineato rispetto alla lista prima del mio intervento — inconsistenza preesistente, non introdotta da me, non corretta oltre il necessario).
2. Aggiunta `"VOLATILITY_BREAKOUT_CONFIRMED": "TREND"` a `FAMILY_MAP` in `contracts/generate_registry.py` (necessaria perché il generatore richiede una famiglia nota).
3. Rigenerato tramite `python3 contracts/generate_registry.py` → `contracts/strategy-registry.json`, `MQL5/Include/NEXUS_v1/NXS_StrategyRegistry.mqh`, `frontend/src/contracts/strategyRegistry.js` — TUTTI dalla stessa fonte canonica, nessuna patch manuale residua (il commento di warning "AGGIUNTA MANUALE" aggiunto in Phase 3 è sparito, correttamente).
4. Validato con `python3 contracts/validate_registry.py` → `registry: {'total': 83, 'live': 53, 'research_only': 30}`, `validazione: OK`, `riconciliazione: OK`.
5. Verificato che `VOLATILITY_BREAKOUT_CONFIRMED` resti presente in `NXS_StrategyKnown()` e in `NXS_StrategyIdAt(48)`; `NXS_LIVE_STRATEGY_COUNT=53`.
6. Ricompilato: 0 errori, 2 warning preesistenti/non correlati (ridefinizione macro `NXS_MAX_SIGNALS`, conversione `ulong`→`long` riga ~1021) — invariati rispetto a prima.

Comportamento non cambiato: stessa strategia, stesso selector_index, stessa presenza in whitelist — solo il percorso con cui il dato arriva al file `.mqh` è ora quello corretto (generatore, non patch manuale).

---

## 3. Identità della strategia (`s.strat` vs `s.stratName`) — VERIFICATO, NESSUNA CORREZIONE NECESSARIA

**Domanda posta.** `s.strat = STRAT_BREAKOUT_ACC` mentre `s.stratName = "VOLATILITY_BREAKOUT_CONFIRMED"`: collisione semantica/contabile con BREAKOUT_ACC?

**Verifica (non assunta, tracciata nel codice).** `.strat` (enum `ENUM_NXS_STRAT` nel struct `SNXSSignal`, `NXS_Defines.mqh`) è stato tracciato in tutto il codebase: non risulta MAI letto/confrontato per filtri, registry, statistiche o esecuzione ordini. È un campo scritto e mai riletto — puramente decorativo. L'identità reale usata da `NXS_StrategyKnown()`, dalle funzioni `NXS_Profile_*` e dalle statistiche/telemetria CSV è sempre `.stratName` (stringa). Precedente già esistente nel codebase: `Z_SCORE_BREAKOUT` (selector 42) riusa già `s.strat = STRAT_BREAKOUT_ACC` con `stratName` distinto, senza problemi noti.

Controllo aggiuntivo mirato: in `NXS_EdgeAdaptive.mqh` esiste un campo chiamato `strat` (stringa) su una struttura diversa (`NXS_EA_Learner_IsDisabled`) — nome uguale ma struct e tipo diversi, nessuna relazione con `SNXSSignal.strat`. Nessuna collisione.

**Conclusione.** Non è un bug. Nessuna modifica applicata. Il riuso di `STRAT_BREAKOUT_ACC` come valore enum decorativo è coerente con un pattern già presente nel codebase.

---

## Conferma: nessun parametro ottimizzato

L'unica modifica ai valori economici della strategia è la sostituzione del prezzo di RIFERIMENTO per entry/SL/TP (da ASK/BID live a `c1`, chiusura barra segnale), per allineare il codice alla specifica già congelata in Phase 3. Non sono stati toccati: N=20 (ampiezza range), moltiplicatore di conferma ATR (1.0x), definizione di TP come 1R, timeout a 40 barre, formula SL (estremo range opposto), o qualunque altro parametro. La direzione dell'effetto (leggero peggioramento in Fast Structural: PF 1.165→1.156) non è stata scelta a posteriori — la correzione è stata applicata per fedeltà alla spec prima di eseguire qualunque test, e il risultato è stato misurato dopo, non selezionato.

---

## File modificati

- `MQL5/Include/NEXUS_v1/NXS_Strategies.mqh` — fix entry semantics.
- `knowledge/strategy_database.json` — vera source-of-truth aggiornata.
- `contracts/generate_registry.py` — aggiunta `FAMILY_MAP` per la nuova strategia.
- `contracts/strategy-registry.json`, `MQL5/Include/NEXUS_v1/NXS_StrategyRegistry.mqh`, `frontend/src/contracts/strategyRegistry.js` — rigenerati dal generatore, patch manuale rimossa.
- `results/strategy_foundry_phase3/volbrk_parity_trades_mt5_POST_correction.csv`, `results/strategy_foundry_phase3/volbrk_fast_structural_6mo_trades_POST_correction.csv` — nuovi log post-correzione.

## Commit SHA

`<inserire dopo commit>`
