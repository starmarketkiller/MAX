---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, regime, dipendenza-rally, atr, breakeven, scoperta]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Attacco alla dipendenza dal rally 2023-2026 (24/08)

## Perché

Il problema più vecchio e mai risolto dell'indagine: ogni strategia
trend-following del nucleo (SAR/MACD/LONDON_BO/FVG_CONT, e oggi anche
Hull Suite/ML Adaptive SuperTrend) mostra edge concentrato nel rally
storico 2023-2026, debole o sotto pari nel 2019-2023. Diagnosticato più
volte (vedi [[NEXUS EA - Riverifica Walk-Forward 5 Finestre e Dipendenza da Regime (15-08)]]:
regime ADX non risolve, TF più bassi peggiorano, la finestra 2020-11→
2023-10 è genuinamente laterale anche misurata solo sul prezzo, senza
costi coinvolti). Il filtro Efficiency Ratio (16/08) migliora ma non
chiude il divario (riconfermato oggi su Hull Suite/ML SuperTrend). Fin
qui: sempre diagnosticato, mai attaccato con una correzione testata.

Richiesta esplicita dell'utente: affrontare il problema prima di
continuare a cercare nuove strategie, con test sistematici, non teoria.

## Tre leve testate su SAR e MACD (4h, walk-forward 5 finestre, costi
scalati sul prezzo storico, retail/ECN) — `rally_dependency_attack_24-08.py`

### Blocco 1 — Breakeven sul "near-miss": RIGETTATO, effetto opposto a quello atteso

La diagnosi del 15/08 aveva trovato che il 55.8% dei trade perdenti erano
"near-miss" (arrivati a +0.78R prima di girare in stop) — mai testata una
correzione. Sweep beR 0.5/0.7/1.0/1.5: **peggiora sempre, in modo netto**,
su entrambe le strategie e su ogni preset di costo (es. SAR retail:
baseline PF1.16 → beR=0.5 PF0.71, meta1 0.52 invece di 1.01).

**Meccanismo reale** (opposto all'intuizione): il breakeven non salva i
near-miss perdenti quanto UCCIDE i trade VINCENTI che prima ritracciano e
poi continuano fino al TP pieno — un pattern "shake-out poi trend"
frequente su questo strumento. L'edge aggregato vive più dei vincenti
pieni che si perdono spostando lo stop, che di quanto si guadagni
salvando i perdenti. Chiuso, non riprovare varianti di breakeven senza
una nuova ipotesi.

### Blocco 2 — Floor di volatilità assoluta: **LA SCOPERTA**

Ipotesi: il filtro ER misura la FORMA del movimento (quanto è diretto),
non la sua AMPIEZZA assoluta. Un trend "efficiente" in un periodo a bassa
volatilità assoluta (es. 2020-2022, ATR% quasi la metà di oggi — vedi
tabella nella nota 15/08) può restare troppo piccolo perché un target
ATR-multiplo lo catturi prima che il rumore lo cancelli. Gate aggiuntivo
ORTOGONALE al filtro ER esistente: percentile di ATR sulla sua
distribuzione storica mobile (2000 barre), non solo soglia ER fissa.

Baseline warmup-allineata (ER fisso 0.045, nessun floor) vs floor al 30°
percentile:

| Strategia | Preset | meta1 (senza floor) | meta1 (floor 0.3) | meta2 senza | meta2 con | finestre PF≥1 |
|---|---|---|---|---|---|---|
| SAR | retail | 1.01 | **1.09** | 1.32 | 1.33 | 3/5 → **5/5** |
| SAR | ECN | 1.17 | **1.24** | 1.47 | 1.48 | 4/5 → **5/5** |
| MACD | retail | 1.27 | **1.39-1.41** | 1.57 | 1.52-1.54 | 4/5 → 4-5/5 |
| MACD | ECN | 1.46 | **1.59-1.62** | 1.75 | 1.70-1.72 | 4/5 → **5/5** |
| FVG_CONT | retail | 1.15 | **1.19** | 1.35 | 1.41 | 4/5 → **5/5** |
| FVG_CONT | ECN | 1.32 | **1.35** | 1.50 | 1.55 | 5/5 → 5/5 |

**Plateau reale, non un punto isolato**: percentili 0.2-0.5 danno tutti
risultati simili e coerenti (verificato su griglia 0.0/0.2/0.3/0.4/0.5/0.6
per SAR e MACD) — il miglioramento non dipende da un valore fragile.
`floor_pctl≈0.3` è il punto di equilibrio migliore su tutte e 3 le
strategie riprovate.

**Non universale — verificato, non assunto**: su **LONDON_BO** il floor
PEGGIORA la metà recente (meta2 1.29→0.93 a floor 0.4) mentre migliora
ulteriormente una prima metà già forte (meta1 1.37→1.65) — LONDON_BO non
ha lo stesso problema da correggere (campione già piccolo, 98 trade,
finestre rumorose 0.78-2.37 PF). **Non applicare il floor meccanicamente
a tutto il portafoglio** — stessa lezione già imparata il 17/08 col
filtro trend/laterale di BB_SQUEEZE: va verificato per strategia, non
assunto.

### Blocco 3 — Soglia ER adattiva (percentile mobile vs fissa): effetto reale ma più debole e meno affidabile

Sweep pctl_thr 0.5-0.8: migliora rispetto alla soglia fissa (es. MACD
retail meta1 0.6→1.06-1.26 a seconda della soglia) ma con campioni via
via più sottili e finestre molto più rumorose alle soglie alte (MACD
pctl_thr=0.7: finestre 0.88|2.00|0.84|2.16|1.14 — oscillazione enorme,
segno di un campione che si sta assottigliando troppo, non di un edge
pulito). Più debole e meno affidabile del floor ATR.

**Combinazione floor+adattiva testata**: PEGGIORA rispetto al floor da
solo su tutte e 3 le strategie (es. MACD retail meta1 1.39→1.11 quando
si aggiunge anche la soglia ER adattiva) — le due leve non si sommano
bene, il floor ATR fa gran parte del lavoro da solo e la soglia adattiva
sopra ci sottrae campione senza aggiungere qualità. **Non combinare.**

## Raccomandazione operativa

Adottare **ER fisso ≥0.045 (invariato) + floor ATR al 30° percentile
della sua distribuzione mobile (2000 barre)** come nuovo standard per le
strategie trend-following del nucleo dove il floor è stato verificato
utile (SAR, MACD, FVG_CONT confermate oggi). Non applicarlo a LONDON_BO
senza riverificare (probabilmente non necessario, campione già troppo
sottile per giudicare con sicurezza). Da riverificare su Hull Suite/ML
Adaptive SuperTrend/Z_SCORE_BREAKOUT/SWING_FALSEBREAK — non ancora fatto,
prossimo passo naturale.

Il divario meta1/meta2 SI RIDUCE sostanzialmente (non sparisce) — MACD
retail passa da "prima metà debole, seconda forte" (1.27/1.57) a "prima
metà quasi alla pari con la seconda" (1.39-1.41/1.52-1.54). Non è la
soluzione completa al problema (resta un divario residuo, e la finestra
1 - 2020-11→2022-04 - resta la più debole in assoluto anche col floor),
ma è il primo miglioramento REALE e riproducibile trovato su questo
fronte in tutta l'indagine dal 14/08 a oggi.

## Addendum 24/08 (2) — floor ATR riverificato sui 4 candidati di oggi: 2 su 4 rispondono

`rally_dependency_attack_part2_24-08.py` — stessa verifica "per
strategia, non meccanica" promessa sopra, applicata a Hull Suite/ML
Adaptive SuperTrend/Z_SCORE_BREAKOUT/SWING_FALSEBREAK (tutti e 4
mostravano la firma prima-meta-debole quando scoperti oggi, prima di
questo attacco).

| Strategia | meta1 retail senza floor | meta1 retail floor 0.3 | floor 0.4 | Verdetto |
|---|---|---|---|---|
| **Z_SCORE_BREAKOUT** | 1.20 | **1.37** | **1.39** | **Risponde bene** — stesso pattern di SAR/MACD/FVG_CONT, aggPF 1.29→1.35-1.37, ECN 5/5 finestre mantenuto |
| Hull Suite (len25) | 0.95 | 1.01 | 0.98 | Neutro — miglioramento minimo, non un plateau pulito (finestre 2/5→4/5 non monotone) |
| ML Adaptive SuperTrend (f1.5) | 0.92 | 0.93 | 0.87 | Neutro/leggermente negativo a floor piu' alto |
| SWING_FALSEBREAK | 1.14 | 1.04 | 1.20 | **Non monotono** — peggiora a 0.3, migliora a 0.4, campione gia' sottile (234→195-206 trade) prima ancora di dividerlo in 5 finestre; rumore piu' probabile di un edge reale |

**Conclusione**: il floor ATR non è un fix universale nemmeno tra i
candidati nuovi — 2 su 4 (Z_SCORE_BREAKOUT chiaramente, nessun altro con
la stessa pulizia). La differenza plausibile: SAR/MACD/FVG_CONT/
Z_SCORE_BREAKOUT hanno tutti campioni da centinaia a migliaia di trade;
Hull Suite/ML SuperTrend/SWING_FALSEBREAK partivano già più sottili
(234-370 trade) — a quella scala, un ulteriore taglio a percentile
comincia a intaccare la significatività statistica invece di isolare
selettivamente il rumore. **Lezione**: il floor va provato e verificato
per ogni strategia, non assunto come miglioramento automatico — quarta
conferma diretta di questo principio nella stessa giornata (dopo
LONDON_BO, e ora Hull Suite/ML SuperTrend/SWING_FALSEBREAK).

## Prossimi passi aperti

- Riverificare il floor ATR su Hull Suite/ML Adaptive SuperTrend (stessa
  firma retail-debole-prima-meta trovata oggi prima di questo attacco) e
  su Z_SCORE_BREAKOUT/SWING_FALSEBREAK.
- Non ancora provato: floor ATR su 1h (qui testato solo su 4h).
- Non ancora provato: floor calcolato su una finestra mobile diversa da
  2000 barre (scelta di comodo, non ottimizzata).
- La finestra 1 (2020-11→2022-04) resta la più debole anche col floor in
  quasi tutte le combinazioni — potrebbe essere davvero irriducibile con
  gli strumenti provati finora (stessa conclusione già raggiunta il
  15-16/08 per quel periodo specifico).

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Riverifica Walk-Forward 5 Finestre e Dipendenza da Regime (15-08)]]
[[NEXUS EA - Filtro di Regime e Portafoglio 5 Strategie (16-08)]]
