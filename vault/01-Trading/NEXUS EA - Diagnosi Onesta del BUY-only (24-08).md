---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, buy-sell, regime, metodologia, revisione]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Diagnosi onesta del BUY-only: beta o edge? (24/08)

## Perché

Obiezione dell'utente, metodologicamente corretta: BUY-only profittevole
in un dataset a maggioranza rialzista (oro 2019-2026) può essere solo
beta direzionale ("compra e tieni durante un rally"), non un edge di
segnale genuino. Se il lato SELL non ha ALCUNA qualità nemmeno nei
periodi non rialzisti, "BUY-only" non è interessante — è solo "l'oro
sale". Da verificare con i numeri, non con l'intuizione.
`buyonly_regime_diagnosis_24-08.py`: PF per-finestra CON LE DATE di
inizio/fine, confrontato con la classificazione di regime del 15/08
(F1 2020-11→2022-04 e F2 2022-04→2023-10 = genuinamente LATERALI).

## Scoperta metodologica preliminare (rilevante per TUTTA la giornata, non solo BUY-only)

Le finestre "equal-count" (stesso numero di trade) usate per tutto il
giorno **non sono equal-CALENDAR** quando il segnale è raro: per
BOLLINGER-BUY, la finestra F0 copre **4 anni** (2020-06→2024-04, solo 14
trade) mentre F1-F4 coprono insieme meno di 2 anni (2024-2026, il resto
dei trade). Il filtro ER+floor è così selettivo nel periodo laterale
2020-2023 che quasi nessun segnale BUY lo supera — il campione "vecchio"
non è debole per caso, è quasi assente. Stesso pattern per ICHIMOKU-BUY
(buco di 2.5 anni tra F0 e F1, dicembre 2020 → maggio 2023).

**Implicazione**: le verifiche "due-metà-storia" fatte oggi su segnali a
bassa frequenza (dopo split BUY/SELL, o su strategie già rare come
MALAYSIAN_SNR_BREAKOUT/TSI) hanno una copertura temporale reale minore
di quanto il nome "meta1/meta2" suggerisca — non sono necessariamente
false, ma vanno lette sapendo che gran parte del campione è comunque
concentrato nel 2024-2026. Non invalida i risultati ad alta frequenza
(SAR/MACD/ADX_RSI/DONCHIAN_TURTLE, centinaia-migliaia di trade, coprono
il calendario in modo molto più uniforme), ma abbassa la fiducia sui
candidati a campione già piccolo.

## Risultato per-strategia: evidenza MISTA, non un verdetto unico

| Strategia | BUY F0 (vecchia, laterale-inclusiva) | SELL F0 stessa finestra | Lettura |
|---|---|---|---|
| **STRUCT_REACT** | PF1.52 (n=11) | **PF2.85** (n=25) | **La più genuina**: nella finestra vecchia il SELL era ECCELLENTE (2.85!), crolla nel 2024-2026 (0.35/0.34/0.49/0.95) mentre il BUY esplode negli stessi anni recenti (4.53/3.13/2.17/2.36). Sembra un vero **flip di regime bidirezionale** (il segnale segue la direzione dominante, non è cieco su un lato), non semplice beta long |
| BOLLINGER | PF0.81 (n=14, sotto pari) | PF1.15 (n=26, sopra pari) | Debole ma non damning — nell'unica finestra con vera copertura pre-2024, il SELL batte il BUY. Il PF2.34 aggregato del BUY è quasi tutto guadagnato nel 2024-2026 |
| ICHIMOKU | PF1.51 (n=10, finestra cortissima 6 mesi) | PF1.01 (n=9) | Campione troppo sottile per concludere, buco di 2.5 anni prima del prossimo trade valido su entrambi i lati |
| **BJORGUM** | PF0.92 (n=19, sotto pari) | PF0.97 (n=25, sotto pari) | **La più debole**: BUY e SELL sostanzialmente PARI (e sotto pareggio) nella finestra vecchia — nessuna evidenza di edge bidirezionale genuino, il PF1.60 aggregato è quasi certamente beta del rally 2024-2026, non segnale |

## Verdetto rivisto (non più "7 rescue uniformi")

Il rescue BUY-only di ieri sera va **declassato da uniforme a
differenziato**:
- **STRUCT_REACT**: mantiene status di candidata solida — evidenza reale
  di logica bidirezionale (flip SELL-forte→BUY-forte coerente con
  l'inversione di regime), non solo beta.
- **BOLLINGER**: declassata a "watch", non "candidata" — il PF alto è
  quasi interamente un artefatto del 2024-2026, la finestra vecchia è
  debole su entrambi i lati (0.81 BUY, ma almeno 1.15 SELL).
- **BJORGUM**: **rimossa dalla lista baseline** — nessuna evidenza di
  edge reale su nessun lato nella finestra pre-2024, il numero aggregato
  alto è beta mascherato, esattamente il sospetto dell'utente confermato
  dai dati per questo caso specifico.
- **ICHIMOKU/FVG_MIT/TSI_EXTREME/RSI_DIV**: non ancora diagnosticate con
  questo livello di dettaglio (solo ICHIMOKU controllata, campione
  troppo sottile per concludere) — da fare prima di contarle con piena
  fiducia.

## Sulla proposta di combinare BUY-only + D1

Deliberatamente NON eseguita subito: D1 ha molti meno trade totali per
costruzione (2194 candele contro le ~10-32mila di 4h/1h) — lo stesso
problema di concentrazione temporale trovato qui sopra sarebbe quasi
certamente PEGGIORE su D1, non risolto. Prima di combinare le due leve
ha più senso applicare questa stessa diagnosi per-finestra-con-date a
ICHIMOKU/FVG_MIT/TSI_EXTREME/RSI_DIV BUY-only (i 4 non ancora
verificati) e ai candidati D1 con divario ampio (OTE_CONT/MACD/
DARVAS_BOX/DONCHIAN_TURTLE) prima di aggiungere altro sopra una base non
ancora del tutto verificata.

## Addendum 24/08 (2) — diagnosi completata su tutti i candidati residui

**BUY-only, i 3 non ancora controllati** (FVG_MIT, TSI_EXTREME, RSI_DIV):
nessuno mostra la firma genuina di STRUCT_REACT. FVG_MIT-BUY debole nella
finestra vecchia (0.66, n=5 pochissimi trade) e debole anche nell'ultima
finestra (0.92) — il PF2.20 aggregato vive quasi solo su F1-F3 (2024-2025).
TSI_EXTREME-BUY debole su ENTRAMBE le finestre vecchie (0.89 e 0.37,
quest'ultima copre oltre 3 anni) mentre il SELL nella finestra più vecchia
era positivo (1.09) — stessa firma di BJORGUM, beta mascherato.
RSI_DIV inconcludente (campioni troppo sottili, segnale rumoroso anche
dentro le finestre di rally).

**Verdetto finale sul rescue BUY-only di ieri**: da 7 a **1 sola
confermata** (STRUCT_REACT) + 1 in osservazione (BOLLINGER). BJORGUM,
FVG_MIT, TSI_EXTREME rimosse dalla lista baseline. ICHIMOKU/RSI_DIV
inconcludenti, non contate.

**D1, i 4 candidati a divario ampio**: scoperta aggiuntiva — il filtro
ER+floor su D1 è così selettivo che **nessun trade esiste prima del
2022-02/03** per nessuno dei 4 (l'intero periodo 2019-2022, incluso il
crash COVID, è assente dal test). Dentro la finestra disponibile
(2022-2026):
- **OTE_CONT**: **PF=0.00 nelle prime due finestre** (2022-03→2024-01,
  quasi 2 anni, zero trade vincenti) poi esplode (7.46, 8.91) — non
  fragile, **morta** prima del 2024. Rimossa dalla lista baseline.
- **MACD D1**: prima finestra disponibile (2022-02→2023-04) sotto pari
  (0.67) — stessa dipendenza dal rally già nota per MACD 4h, solo
  confermata anche qui. Resta comunque positiva nell'aggregato e su 4h è
  già una baseline solida — non serve come baseline D1 a sé.
- **DARVAS_BOX / DONCHIAN_TURTLE**: **le uniche pulite** — anche nella
  finestra più vecchia disponibile (2022-2023) restano positive (PF1.29
  e 1.28), ogni finestra successiva migliora ma nessuna è sotto pari.
  Confermate come baseline D1 genuine.

## Bilancio rivisto delle baseline (sostituisce il conteggio di 25)

Rimosse: BJORGUM, FVG_MIT, TSI_EXTREME (BUY-only beta mascherato),
OTE_CONT-D1 (morta pre-2024). Confermate con evidenza genuina: STRUCT_REACT
(BUY-only), DARVAS_BOX-D1, DONCHIAN_TURTLE-D1. Il conteggio "25" di ieri
sera era ottimistico — il numero vero, dopo questa verifica più severa,
è più vicino a **18-19 solide** (le 14 di ieri pre-BUY/D1, meno le
rimozioni nette da questi due esperimenti, più STRUCT_REACT/DARVAS_BOX-D1/
DONCHIAN_TURTLE-D1 come aggiunte reali). Conteggio esatto da ricostruire
con una lista consolidata dedicata, non ancora fatta.

## Prossimi passi aperti

- Diagnosi per-finestra-con-date su ICHIMOKU/FVG_MIT/TSI_EXTREME/RSI_DIV
  BUY-only (non ancora fatta).
- Stessa diagnosi sui candidati D1 a divario ampio (OTE_CONT su tutti,
  m1=0.30 nell'aggregato — probabilmente lo stesso problema di
  concentrazione temporale, da confermare con le date).
- Se la diagnosi conferma il pattern, la lezione generale diventa:
  qualunque candidato con NUMERO DI TRADE basso (sotto ~100) deve avere
  la data delle finestre riportata esplicitamente, non solo il conteggio
  — un cambiamento permanente alla disciplina di verifica, non solo per
  oggi.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Split BUY-SELL e Timeframe D1 (24-08)]]
[[NEXUS EA - Riverifica Walk-Forward 5 Finestre e Dipendenza da Regime (15-08)]]
