---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, crt, elliott, scalp, costi, mql5]
created: 2026-08-25
updated: 2026-08-25
---

# NEXUS EA — CRT: costi-dominanti confermati su tutta la griglia; Elliott attivata H4 BUY-only (25/08)

## CRT — "cosa ci sfugge?"

Richiesta esplicita dell'utente dopo aver visto la disattivazione di CRT
stasera: testare varianti scalp E stop più larghi, per capire se manca
davvero qualcosa. Griglia 2D: 6 timeframe (M5/M15/M30 nativo/H1/H4/D1) ×
2 meccanismi di stop (nativo = ancorato al wick + floor 0.3×ATR come il
vero EA; fisso = 1.0×ATR, target RR2.0, completamente scollegato dal
wick). Pattern classico a 3 candele, fedele a `NXS_Strat_CRT`.

`crt_tf_stop_scan_25-08.py` — risultato: **monotono e senza eccezioni
reali**. Il PF sale costantemente sia con il TF che con lo stop fisso
(più il rischio in dollari cresce, meno i costi fissi pesano in
percentuale — esattamente il meccanismo già diagnosticato ieri), ma
supera 1.0 in un solo caso su 36 combinazioni testate:

| TF | Stop | Direzione | n | PF (m1/m2) | Finestre |
|---|---|---|---|---|---|
| D1 | fisso ATR | BUY-only | 388 | **1.17** (0.92/1.46) | 3/5 |
| H4 | fisso ATR | BUY-only | 1737 | 0.91 (0.89/0.93) | 2/5 |
| D1 | nativo | BUY-only | 389 | 0.55 | 0/5 |
| M30 (nativo) | nativo | simmetrica | 24795 | 0.07 | 0/5 |
| M5 | nativo | simmetrica | 86074 | 0.01 | 0/5 |

L'unico caso sopra pareggio (D1 BUY-only, stop fisso) ha uno split
prima/seconda metà molto sbilanciato (0.92 → 1.46) — più coerente con
un bias rialzista di periodo (bull run dell'oro) che con un edge
stabile del pattern, e richiederebbe comunque due modifiche strutturali
insieme (TF D1 anziché M30, stop ATR anziché wick — un cambio del
meccanismo che definisce il pattern stesso secondo la fonte originale).

**Risposta a "cosa ci sfugge"**: niente di strutturale. Non è un TF
sbagliato né uno stop tecnicamente rimediabile — il pattern (3 candele
consecutive, nessun filtro di contesto) è generico e ad alta frequenza
per costruzione, e il suo edge grezzo (reale ma sottile, PF~1.08 senza
costi secondo la ricerca di ieri) è troppo piccolo per sopravvivere a
qualunque combinazione di costi reali salvo l'angolo estremo (D1,
stop-ATR, solo BUY) — e anche lì il risultato non è abbastanza stabile
da fidarsene. **CRT resta disattivata**, nessuna azione sul codice.

## Le 4 strategie borderline (DISP_REBAL/SH_BMS_RTO/SMS_BMS_RTO/WEEKLY_EXP): stessa conclusione

`remaining_institutional_scalp_wide_scan_25-08.py` — varianti scalp/wide
per tutte e 4, stesso schema di CRT:

| Strategia | Variante | n | PF (m1/m2) | Finestre |
|---|---|---|---|---|
| DISP_REBAL | M15 (scalp) | 744 | 0.15 | 0/5 |
| DISP_REBAL | D1 (largo) | 15 | 2.06 | troppo pochi |
| SH_BMS_RTO v1 | H4 (scalp) | 118 | 0.74 | 1/5 |
| SMS_BMS_RTO | H4 (scalp) | 253 | 0.75 | 0/5 |
| SMS_BMS_RTO | W1 (largo) | 23 | 0.87 | troppo pochi |
| WEEKLY_EXP | H1-displacement (scalp) | 71 | 0.81 | 2/5 |
| WEEKLY_EXP | D1-displacement (largo) | 0 | — | nessun segnale |

DISP_REBAL scalp (M15, n=744) è un caso da manuale di costi-dominanti,
stessa firma di CRT. Nessuna delle 4 ha un TF alternativo chiaramente
migliore del nativo con numeri abbastanza solidi da agire — **tutte e 4
restano invariate**, come stasera.

## Elliott — attivata, ma non come scritta originariamente

`NXS_Strat_Elliott` (mai testata prima, `InpUseStrat_Elliott` era OFF
"backtesta prima") — `elliott_strat_live_signal_25-08.py`:

| TF | Direzione | n | PF (m1/m2) | Finestre |
|---|---|---|---|---|
| M15 (live, fallback InpTFEntry) | simmetrica | 18519 | 0.49 | 0/5 |
| M5 | BUY-only | 146 | 8.58 | non credibile (n piccolo, asimmetria enorme fra meta') |
| H1 | BUY-only | 2213 | 1.06 | 3/5 |
| **H4** | **BUY-only** | **633** | **1.51** | **4/5** |

Ricetta live esatta su M15 in perdita netta, lato SELL rotto su ogni TF.
H4 BUY-only invece campione robusto (n=633) e consistente (4/5
finestre) — stesso schema di correzione già visto oggi per STRUCT_REACT.

**Attivata**: `InpUseStrat_Elliott=true`, `NXS_Profile_TF("ELLIOTT")=H4`,
`NXS_Profile_DirectionLock("ELLIOTT")=1` (solo BUY). Compilato pulito (0
errori), sincronizzato su entrambi i terminali.

## Anche stasera: lottaggio

Su richiesta esplicita ("solo i tetti massimi"): `InpMaxTotalLotMult`
1.5→1.8, `InpMaxDirExposureLots` 0.40→0.50 (+20/+25%). Il rischio base
per trade (`InpRiskPercent=1.0%`) resta invariato — questi sono solo
soffitti, si sentono solo nei casi già al limite.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CRT Range H4 con Conferma M5 (24-08)]]
[[NEXUS EA - Ultimo Lotto Strategie Native e Scoperta NXR Dead-Code (25-08)]]
