---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, sar, backtest, mql5, risk-management]
created: 2026-08-31
updated: 2026-08-31
---

# NEXUS EA — Spoglia e reintegra su SAR: filtro candela H4 trovato e validato su 5 punti nel tempo (30-31/08)

## Perché

Continuazione diretta di [[NEXUS EA - Bug NXS_MTF_MAX, SAR H4 Non Apriva Mai (29-30-08)]].
Dopo aver sistemato il bug che azzerava i trade, l'utente ha chiesto di
proseguire il piano "spoglia e reintegra" (SAR isolata, `InpStrategySelector=4`,
tutti i filtri spenti, riaccesi uno alla volta) direttamente sul vero
Tester MT5, sempre sullo stesso periodo a tick reali disponibile:
**2025.11.01 → 2026.08.26** (10 mesi, l'unico blocco con tick reali
scaricati per questo conto — il resto della storia è solo OHLC).

## La catena "spoglia e reintegra" (step0→step7)

| Step | Aggiunge | Risultato |
|---|---|---|
| 0 — nuda | niente (solo entrata SAR grezza) | 112 trade, PF 1.33, +$1109-1228 |
| 1-6 | trailing ATR, cooldown, spread dinamico, max-loss, auto-close, Elliott | (intermedi, non salvati singolarmente) |
| 7 — stack completo | + anti-revenge, DD giornaliero 5%, max 12 trade/giorno | 175 trade, PF 0.92, **-$118.94** |

Causa identificata: `InpUseAutoClose` taglia un edge trend-following che
ha bisogno di holding lunghi (vincenti mediana 144h, perdenti mediana
12.7h — win/loss ratio 3.81:1, 97% dei vincenti tenuti oltre 24h).

## Bug strutturale: tre protezioni "morte" per le strategie a profilo

Verificato con test A/B identici (stessa configurazione, solo il gate
sotto esame acceso/spento): **zero differenza, bit a bit**, per:
- `InpUseStrategyCD` (cooldown per-strategia)
- `InpUseDirCooldown` (cooldown direzionale, costruito apposta stanotte)
- `InpAntiRevenge` (pausa dopo N perdite consecutive)
- `InpChainEnableContinuation` (era anche un bug separato: non era `input`)

Causa: SAR (come ogni strategia con un profilo, `InpUseStrategyProfiles=true`)
passa dal percorso "a profili" in `NEXUS_EA_v2.mq5` (riga ~1226), che
chiama `NXS_OpenTrade()` direttamente e poi fa `return` — non attraversa
MAI il blocco più sotto (riga ~1261) dove vivono cooldown/chain/anti-revenge.
`NXS_StrategyRegisterTrade()` viene comunque chiamato (il contatore
incrementa) ma `NXS_StrategyOnCooldown()` non viene mai controllato — si
registra ma non si applica mai.

Il vero gatekeeper è `NXS_OpenTrade()` (`NXS_Execution.mqh:279`), che
chiama davvero `NXS_CommonExposurePreflight` — dove vivono RiskShield
(`EQUITY_BREAKER` Sharpe-based, `CLUSTER_CAP` correlazione GOLD) e i gate
di margine/esposizione, VERI e attivi per SAR.

Costruito `NXS_ConsecLossBrake.mqh` (freno perdite consecutive, agganciato
nel posto giusto stavolta) ma **non collegato** — messo in pausa su
richiesta esplicita dell'utente durante la sessione, file presente ma inerte.

## Il lotto fisso è fragile, non solo "diverso"

Test con lotto fisso 0.05 (`InpUsePipSeq=true`, stage1/2 a soglie
altissime per disattivare la gestione a stadi, solo l'override del
lotto attivo) dava PF 1.86, +$5226.07 — sembrava un miglioramento
enorme. Isolato con test di controllo (cooldown/chain-continuation
provati spenti uno per uno): **il lotto fisso da solo spiegava tutto**.

Ma aggiungendo il filtro candela (vedi sotto) SOPRA il lotto fisso, il
risultato è **crollato**: PF 0.69, -$804.14, stesso periodo. Causa
verificata nei log: a lotto piccolo (0.01) il margine non è mai un
vincolo (`PROJECTED_MARGIN` 0% di rifiuto); a lotto grande (0.05) sì —
e un piccolo cambiamento nell'ordine dei trade iniziali (dovuto al
filtro) sposta la traiettoria di equity abbastanza da innescare una
spirale di auto-blocco (`margin_gate` bloccava il 95.7% dei tentativi).
**Conclusione: il lotto fisso grande dall'inizio è strutturalmente
fragile — non impilarci sopra altri miglioramenti finché non si capisce
meglio l'interazione col margine.** Lezione applicata: l'utente ha
proposto lotto piccolo di base + lotto grande SOLO alla riconquista dopo
uno stop (esattamente lo schema già esistente in `NXS_SLReclaim.mqh`,
mai testato).

## La vera scoperta: filtro allineamento candela H4

Analisi offline sui 112 trade nudi (dati reali + indicatori H4
precalcolati, `nxs_h4_gold_indicators_29-08.csv`): tra spessore corpo
candela, distanza SAR-prezzo in ATR, spread EMA9-21 in ATR e "freschezza"
del trend SAR — **solo una caratteristica fa differenza**: se la candela
H4 appena chiusa al momento dell'ingresso è nella STESSA direzione del
segnale (bullish per buy, bearish per sell).

- Vincenti: 69% allineati (77% tra i grandi vincenti)
- Perdenti: 46% allineati (50% tra i grandi perdenti — quasi casuale)

Filtrando storicamente solo gli allineati: PF 1.33→1.92, netto
$1227.85→$1594.93, su meno trade (112→58). Gli scartati da soli erano
in perdita netta (PF 0.81) — non diluivano il risultato, lo
peggioravano attivamente.

Implementato come `InpSAR_RequireCandleAlign` (default `false`) in
`NXS_Strat_SAR()` (`NXS_Strategies.mqh`).

### Validazione sul vero Tester, su 5 punti nel tempo (nudo 0.01, non lotto fisso)

| Partenza | PF senza filtro | PF con filtro |
|---|---|---|
| Nov 2025 (piena, 10 mesi) | 1.33→1.86* | 1.45 |
| Dic 2025 | 0.83 (perdita) | 1.43 |
| Feb 2026 | 0.29 (disastro, 17 perdite di fila) | 1.37 |
| Apr 2026 | 1.30 | 1.52 |
| Giu 2026 | (non testato senza filtro) | 1.57 |

\* 1.33 = nuda pura, 1.86 = con lotto fisso (fragile, vedi sopra)

Prima del filtro il PF oscillava selvaggiamente (0.29-1.86) a seconda
del punto di partenza — segno di un edge non robusto, dipendente dalla
sequenza. Con il filtro: **consistentemente 1.37-1.57 su tutti e 5 i
punti**, incluso il caso che prima era un disastro totale (feb 2026).
Prima vera conferma di robustezza su SAR in questa sessione.

## Altre analisi fatte sui 112 trade nudi

- **Distanza di stop**: mediana $39.83, range $11.21-$97.59 — coerente
  con sizing ATR-based, nessuna anomalia.
- **Il prezzo inverte dopo lo stop?** 53.7% delle volte torna oltre il
  livello di entrata originale entro 24h (6 barre H4) — margine reale ma
  modesto. Matematicamente: dato il rapporto vincita/perdita medio reale
  (~3.8:1, vincita media $169.63 / perdita media $44.48), la soglia di
  pareggio è solo ~20.8% di win rate — ben sotto sia il 25.9% osservato
  che il 53.7% del rientro grezzo.
- **Struttura (minimi crescenti/massimi decrescenti, 3 barre prima
  dell'entrata)**: NON funziona — i perdenti la mostrano più spesso
  (41.0%) dei vincenti (34.5%). Ipotesi scartata dai dati.
- **Buy vs Sell**: 56/56, nessun bias direzionale in nessuna versione
  testata.

## Prossimi passi (non ancora fatti)

1. Testare `NXS_SLReclaim.mqh` (mai lanciato) sopra la base nudo+filtro
   candela — lotto piccolo di base, lotto grande solo alla riconquista
   confermata (chiusura M15 oltre la linea dello stop), catena capata a
   2 perdite consecutive (`InpSLReclaimMaxChain`).
2. Riapplicare lo stesso metodo (spoglia e reintegra, test multi-punto,
   analisi vincenti/perdenti sui dati reali) alle altre strategie
   (EMA_PULLBACK, WEEKLY_EXP, ecc.) — strumenti già pronti: indicatore
   visuale `NXS_SAR_Visual.mq5`, script di parsing report Tester.
3. Eventualmente aumentare il lotto in modo più sicuro (graduale/legato
   a un margine di sicurezza) invece del fisso dall'inizio, una volta
   capita meglio la fragilità margine-dipendente trovata oggi.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - Bug NXS_MTF_MAX, SAR H4 Non Apriva Mai (29-30-08)]]
[[NEXUS EA - Debug Motore Python Real-Tick su SAR, Tre Bug Trovati (29-08)]]
