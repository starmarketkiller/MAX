---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, exit-management, tsi]
created: 2026-08-12
updated: 2026-08-12
---

# TSI — ricerca dedicata uscite (12/08)

TSI è uno dei due "problemi aperti" del nucleo mai risolti in sessione
(vedi [[NEXUS EA - Riverifica su Storico Ampliato (11-08)]] — "SAR e TSI:
i fix trigger vero sono già applicati, non sono opportunità nuove"; e "I
due problemi aperti del nucleo, approfonditi (11/08)" — variante cross
da zona estrema testata e negativa). Il giro sulle 58 strategie di oggi
(griglia grezza) aveva mostrato un primo segnale (PF 1.35→2.60 su soli 21
trade) troppo sottile per fidarsene — qui la ricerca dedicata a griglia
piena, stessa metodologia di CRT/FVG_CONT.

## Baseline vero (live)
sl=1.5×ATR, tp=4.5×ATR, htf=True, be=1.0R, trailing overlay 1.5×ATR
(TrailK esplicito), attivazione 1×ATR (fissa, globale).

- IS: pf **0.73**, n=44 (sotto pareggio!)
- OOS: pf **1.35**, n=31, dd **2.97%**

Nota: IS debole/OOS ok è già di per sé un pattern instabile — coerente
con "problema aperto".

## Griglia
HTF∈{True,False} × SL∈{1.0,1.5,2.0} × TP∈{3.0,4.5,6.0} ×
BE∈{0,1.0,1.5,2.0} × trail-width∈{1.0,1.5,2.0,2.5,3.0} (attivazione
fissa 1×ATR). Filtro IS adattato al campione minuscolo di TSI (D1):
pf IS>1.0 (non 1.10) e n≥15 (non 50).

330 combinazioni testate, **79 hanno battuto il baseline OOS**. I
migliori si raggruppano tutti nella stessa zona di parametri (SL largo,
TP molto largo, HTF acceso) — un plateau, non un picco isolato, il
segnale che ci si aspetterebbe da un vero effetto strutturale piuttosto
che da un artefatto di ricerca.

## Top candidati

| sl | tp | be | htf | trail | IS pf/n | OOS pf/n/dd | Walk-forward | Robustezza | Calmar |
|---|---|---|---|---|---|---|---|---|---|
| 2.0 | 6.0 | 1.0 | True | 2.5 | 2.06/33 | 2.27/23/2.96% | 1.65·2.81·2.30·1.55·2.99 | 1.675 | 0.7635 |
| **2.0** | **6.0** | **1.0** | **True** | **2.0** | 1.92/35 | **2.41**/24/**1.99%** | **1.76·1.91·1.97·1.84·2.95** | 1.648 | **1.0482** |
| 2.0 | 6.0 | 0.0 | True | 2.0 | 1.88/35 | 2.31/24/1.99% | 1.76·1.77·1.97·1.81·2.76 | 1.633 | 1.0121 |

**Vincitore scelto: sl=2.0×ATR / tp=6.0×ATR / be=1.0R / htf=True /
trail=2.0×ATR.** Rispetto al secondo classificato (trail=2.5): drawdown
più basso (1.99% vs 2.96%), calmar più alto (1.05 vs 0.76), walk-forward
più stretta e coerente (1.76-2.95 contro 1.55-2.99) — robustezza quasi
identica (1.648 vs 1.675). Preferito per il drawdown molto più basso a
parità di consistenza.

## Onestà sul limite del campione

Anche il vincitore gira su **22-24 trade OOS** — il campione dedicato
più piccolo di tutta la sessione (contro le migliaia di CRT o le
centinaia di FVG_CONT). 330 combinazioni testate alzano il rischio di
selezione multipla (con abbastanza tentativi, qualcosa sembra sempre
buono per puro caso). Il plateau di candidati vicini che convergono
sulla stessa zona di parametri è un'attenuante reale, non una garanzia:
resta la scoperta più fragile trovata oggi, va trattata come un'ipotesi
forte da confermare ulteriormente (demo, o più storico se mai disponibile),
non come un fatto acquisito al livello di CRT/FVG_CONT.

## Portata in MQL5 (12/08, stesso giorno)

`NXS_StrategyProfiles.mqh`: `NXS_Profile_Get("TSI")` slMult 1.5→2.0,
tpMult 4.5→6.0 (htf e beR restavano già corretti, invariati), e
`NXS_Profile_TrailK("TSI")` 1.5→2.0. Portata insieme a CRT e FVG_CONT
(stesso giro, vedi [[NEXUS EA - Ottimizzazione Uscite Strutturali CRT e FVG_CONT (12-08)]]).
**Non ancora compilata/testata** — dato il campione più sottile di
questa scoperta rispetto alle altre due, verifica locale ancora più
importante prima di fidarsene in demo.

## Collegamenti
[[MOC - Trading]] ·
[[NEXUS EA - Ottimizzazione Uscite Strutturali CRT e FVG_CONT (12-08)]] ·
[[NEXUS EA - Ottimizzazione Uscite Tutte le 58 Strategie (12-08)]]
