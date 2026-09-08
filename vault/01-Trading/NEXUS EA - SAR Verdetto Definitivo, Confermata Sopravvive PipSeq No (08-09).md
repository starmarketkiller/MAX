---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar, bug, risk-profile, p0, verdetto-finale]
created: 2026-09-08
updated: 2026-09-08
---

# NEXUS EA — SAR, verdetto definitivo: la config "confermata" sopravvive, PipSeq no (08/09)

## Correzione rispetto alla nota provvisoria di oggi

[[NEXUS EA - SAR Confermata Positiva Invalidata, il Bug Nascondeva un Freno di Sicurezza (08-09)]]
dichiarava (a ragione, sui dati disponibili in quel momento) tutta la
famiglia SAR "in rivalidazione" dopo che **una sola** finestra
(step35) risultava diversa col fix. Completato il re-run delle altre
4 finestre — il quadro è più preciso e **meno grave** di quanto
temuto.

## Risultato: 4 finestre su 5 IDENTICHE, solo step35 differisce

| Finestra | Trade pre-fix | Trade post-fix | PF pre | PF post | Identico? |
|---|---|---|---|---|---|
| step22 (dec2025, 9 mesi) | 89 | 89 | 1.43 | 1.43 | ✅ identico |
| step23 (feb2026, 7 mesi) | 58 | 58 | 1.37 | 1.37 | ✅ identico |
| step24 (apr2026, 5 mesi) | 42 | 42 | 1.52 | 1.52 | ✅ identico |
| step25 (jun2026, 3 mesi) | 30 | 30 | 1.57 | 1.57 | ✅ identico |
| step35 (badwindow, PipSeq) | 29 | 31 | 2.02 | **1.90** | ❌ diverso |

**Il PF1.37-1.57 citato nel piano master (media pesata di step22-25)
è esattamente questa famiglia — verificata byte-per-byte immune al
bug, come FVG_CONT e EMA_PULLBACK.** Il numero nel piano master era
corretto anche sotto il bug.

## Perché step35 è diverso e gli altri no — causa isolata

Confronto diretto degli `.ini`: step35 (a differenza di step22-25)
attiva `InpUsePipSeq=true` — un meccanismo di **rientro a catena**
(apre nuove posizioni in sequenza dopo un certo movimento in pip,
simile a SLReclaim/ProfitReclaim). Questo è esattamente il tipo di
comportamento che **tenta nuove aperture più volte nello stesso
giorno** — quando il DD giornaliero (accumulato da stop su posizioni
già aperte) supera la soglia, il tentativo successivo di PipSeq viene
bloccato dal cap. step22-25 non hanno PipSeq: anche con un DD
intra-day sopra il 5% (misurato in precedenza, 5.94-9.80% su tutte),
non c'è mai un secondo tentativo di apertura quello stesso giorno da
bloccare — il cap non ha mai avuto occasione di mordere.

**Lezione di metodo, confermata due volte oggi (qui e ieri con
CommonExposurePreflight)**: un'esposizione teorica al bug (qui: DD
intra-day sopra soglia) non implica automaticamente un impatto reale
— dipende dal meccanismo esatto della strategia. Va sempre verificato
con un confronto diretto, non assunto dalla sola esposizione.

## Verdetto finale e correzione al piano master

**SAR (config candle-align, PF1.37-1.57, step22-25) è di nuovo
✅ Confermata — verificata immune al bug su tutte le 5... anzi 4 delle
5 finestre disponibili.** Ripristino la classificazione nel piano
master, con una nota a margine su step35.

**`nxs_sar_step35_badwindow_clean_veto` (PipSeq+RegimeVeto, test di
stress su una finestra difficile) resta invalidato** — se questa
variante specifica (non la config base "confermata") viene mai usata
per una decisione, va ripresa dal risultato corretto (PF1.90, non
2.02; DD equity 53.67%, non 45.47%).

## Collegamenti
[[NEXUS EA - SAR Confermata Positiva Invalidata, il Bug Nascondeva un Freno di Sicurezza (08-09)]] · [[NEXUS EA - Controllo CSV SAR-EMA_PULLBACK, EMA_PULLBACK Pulita SAR da Riverificare (08-09)]] · [[NEXUS EA - Impatto Storico Bug InpRiskProfile su Tutto il Corpus di Test (08-09)]] · [[MOC - Trading]]
