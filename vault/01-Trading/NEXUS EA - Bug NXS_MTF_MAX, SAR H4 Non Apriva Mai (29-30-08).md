---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar, bug, multi-tf, mql5]
created: 2026-08-30
updated: 2026-08-30
---

# NEXUS EA — Bug NXS_MTF_MAX: SAR (H4) non apriva mai nella config "nuda" (29-30/08)

## Perché

L'utente ha chiesto di spogliare MT5 di tutti i filtri protettivi
(spread gate, cooldown, trailing, anti-revenge, max-loss, auto-close) e
reintegrarli uno alla volta sul Tester reale — stessa metodologia già
usata su TradingView e sul motore Python, ma questa volta direttamente
sul motore vero. Prima di partire, controllato il vault: trovata una
ricetta di ricerca (24-25/08) molto migliore per SAR mai portata in
MQL5 (BUY-only + filtro Elliott Wave multi-TF, PF1.87) — vedi
[[NEXUS EA - Sei Strategie da TradingView Pine Script (28-08)]] e la
scoperta che il filtro Elliott era in realtà già vivo e agganciato a
SAR, solo mai reso configurabile da `.set`.

## Il test "nudo" dava 0 trade — impossibile

Primo passo del piano: config con tutte le protezioni disattivate via
`.set`. Risultato: **0 operazioni in 10 mesi**. Spogliare dovrebbe
aprire PIÙ posizioni, non azzerarle — segnale di un bug vero, non di un
comportamento atteso.

## Debug (non fermarsi al primo sospetto)

1. **Primo sospetto, confermato ma non sufficiente**: 5 gruppi di
   parametri (spread gate, cooldown, trailing, anti-revenge, exhaustion
   gate — ~25 input in `NXS_Inputs.mqh`) erano dichiarati come
   variabili semplici, non `input` — il Tester li ignorava
   silenziosamente. Corretti tutti. Il test tornava comunque a 0 trade.
2. **Diagnostica temporanea** in `NXS_Strat_SAR()`: il segnale si
   genera regolarmente (74% delle chiamate hanno `dir != 0`), ma
   **zero** `OPEN BLOCCATO` e **zero** righe `[NEXUS BLOCK]` in tutto il
   test — il segnale non arriva mai nemmeno al preflight di apertura.
3. **Causa radice trovata**: `NXS_MTF_MAX = 4` (`NEXUS_EA_v2.mq5`) — il
   ciclo multi-timeframe (un passaggio per ogni timeframe di profilo
   usato dal registro strategie, `NXS_CollectAllSignals`) ha solo 4
   slot. Il registro usa **5 timeframe distinti** (verificato contando
   `NXS_Profile_TF` su tutte le voci di `NXS_StrategyProfiles.mqh`:
   D1/H4/M30/M15/H1). `NXS_MTF_Index()` ritorna `-1` silenziosamente
   quando il contatore raggiunge il cap — `NXS_ActivateTF()` fallisce
   per qualunque timeframe scoperto per 5° nell'ordine di scansione del
   registro, e le strategie su quel timeframe **non vengono mai
   valutate**, senza alcun errore visibile a runtime (solo un
   `continue` silenzioso). Diagnostica dal vivo: `passes[]=[H1, D1,
   M30, M15, H4]` — H4 (quello di SAR) è il 5°, `ActivateTF` fallisce a
   **ogni singolo tick**, per tutto il test.

## Fix

Alzato `NXS_MTF_MAX` da 4 a 8 (margine per strategie/timeframe futuri).
Verificato su un test breve (2 settimane): 0 → 4 operazioni con la
stessa config "nuda".

## Il riferimento di stanotte (175 trade) resta valido — verificato, non assunto

Preoccupazione immediata: se questo bug era già presente prima di
stasera, il riferimento usato per TUTTA la calibrazione del motore
Python (175 trade, PF0.92, netto -$118.95 — vedi
[[NEXUS EA - Debug Motore Python Real-Tick su SAR, Tre Bug Trovati (29-08)]]
e le note successive) potrebbe essere stato generato con codice rotto.
**Verificato direttamente**, non assunto: rilanciato lo stesso identico
test a stack completo (spread/cooldown/trailing/max-loss/auto-close/
Elliott/anti-revenge tutti attivi, come stanotte) col codice corretto —
risultato **175 operazioni, PF 0.92, netto -$118.94** (contro -$118.95
di stanotte, differenza di un centesimo, rumore di arrotondamento).
**Il riferimento è confermato corretto e riproducibile** col codice
attuale — il bug NXS_MTF_MAX colpiva specificamente la combinazione
usata nel test "nudo", non la config a stack completo. Non ancora
capito perché esattamente (l'ordine di scoperta dei timeframe dipende
solo dal registro, non dovrebbe dipendere da quali protezioni sono
attive) — ma il dato pratico e verificato è che il numero di riferimento
regge, quindi tutto il lavoro di calibrazione Python di stanotte resta
valido.

## Prossimo passo

Rilanciato il test "nudo" completo a 10 mesi col codice corretto — poi
si procede con la reintegrazione passo-passo (trailing → cooldown →
spread gate → max-loss → auto-close → filtro Elliott → protezioni di
conto) come richiesto dall'utente.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Debug Motore Python Real-Tick su SAR, Tre Bug Trovati (29-08)]]
[[NEXUS EA - Sei Strategie da TradingView Pine Script (28-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
