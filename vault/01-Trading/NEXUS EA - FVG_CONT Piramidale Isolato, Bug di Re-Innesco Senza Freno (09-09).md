---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fvg-cont, pyramid, bug, chiusura]
created: 2026-09-09
updated: 2026-09-09
---

# NEXUS EA — FVG_CONT + piramidale isolato: bug di re-innesco senza freno, non un semplice aumento di rischio (09/09)

## Il test

`nxs_fvgcont_step8_pyramid_3y` — baseline step2 (prop-compliant, DD5%
reale, `InpRiskProfile=0`) + `InpEnablePyramid=true`, unica variabile
isolata. Durata di esecuzione ~5h30 (contro le ~3h abituali per un
FVG_CONT 3 anni H4) — il volume di trade generato spiega il rallentamento.

## Risultato: non un peggioramento, un collasso

| | step2 baseline (senza piramide) | **step8 (piramidale isolato)** |
|---|---|---|
| Trade totali | 168 | **2255** |
| Net (3 anni) | +$2635.26 | **-$846.49** |
| PF | 1.92 | **0.75** |
| Sharpe | 2.59 | **-5.00** |
| DD balance | 12.42% | **84.66%** |
| DD equity | 22.79% | **84.80%** |

## Causa: bug di re-innesco, non "il piramidale rischia di più" in senso normale

Scomposizione dei trade: **2203 gambe piramide (`NEXUS_PYR`) contro
solo 52 ingressi core FVG_CONT** (contro i 168 core della baseline —
crollati anche quelli, vedi sotto). In un singolo giorno di
esecuzione (06/09/2023) si contano **25 gambe piramide aperte in
sequenza**.

Il meccanismo (`NXS_ManagePyramid()`, `NXS_Pyramiding.mqh`) apre una
gamba quando la posizione core è in profitto ≥1×ATR, con uno stop a
1×ATR di distanza. Non esiste alcun **cooldown o marcatore persistente**
che impedisca di riaprire subito un'altra gamba non appena quella
precedente viene stoppata — la condizione controllata è solo "il
conteggio totale di gambe piramide aperte è sotto 3" e "la posizione
core è ancora nominalmente in profitto". Risultato osservato nel CSV:
la gamba piramide viene stoppata dopo pochi minuti (spread/rumore
normale), e se la core resta sopra la soglia di profitto, **ne apre
immediatamente un'altra sostitutiva** — un ciclo apri-stop-riapri che
si ripete decine di volte nella stessa sessione, ognuna delle quali
paga commissioni/spread senza guadagnare nulla di sostanziale (gli
esiti sono quasi tutti pareggi/piccole perdite, `sl` a pochi centesimi
dal prezzo di apertura). L'emorragia di piccoli costi ripetuti brucia
il conto abbastanza in fretta da far scattare **11 flatten da
protezione DD (`NXS:DD`)** solo nel campione ispezionato.

**Anche i trade core sono crollati** (52 invece di 168): l'esposizione
extra e il DD accumulato dal churn della piramide fanno scattare più
spesso il cap di esposizione direzionale e il freeze da DD giornaliero
(`NXS_CommonExposurePreflight`), bloccando anche i normali ingressi
FVG_CONT che nella baseline passavano senza problemi.

## Verdetto

**Il piramidale, così com'è implementato, non è utilizzabile su
FVG_CONT** — non per un giudizio di rischio/rendimento sfavorevole,
ma perché il meccanismo stesso è rotto: manca un freno che impedisca
il re-innesco immediato dopo uno stop. Coerente con quanto già notato
nel vault per SAR/EMA_PULLBACK ("PF1.02→0.98" nel test di portfolio
del 28/08) — lì l'effetto era diluito in un portfolio multi-strategia,
qui isolato è catastrofico e inequivocabile.

**Non è un bug da toccare senza discussione esplicita** (regola del
progetto sul codice MQL5 live) — servirebbe aggiungere un cooldown per
posizione core (es. "non riaggiungere entro N minuti dall'ultimo stop
di una gamba piramide su questa posizione" o "solo una gamba per
livello di ATR raggiunto, non ri-armabile allo stesso livello") prima
di poter anche solo valutare se l'idea di fondo (caricare su un trend
confermato) ha un edge. Così com'è, il test è chiuso: **non
proseguire con questa configurazione**, la domanda "il piramidale
aiuta FVG_CONT?" resta senza risposta finché il bug non è corretto.

## Collegamenti
[[NEXUS EA - FVG_CONT Prop-Compliant, Protezione Giornaliera Non Basta e Bug SLReclaim (07-09)]] · [[NEXUS EA - Audit Esterno Cartella MQL5, Verificato Punto per Punto (08-09)]] · [[MOC - Trading]]
