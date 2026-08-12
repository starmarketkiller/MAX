---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, strategia]
strategia: SH_BMS_RTO
created: 2026-07-12
updated: 2026-07-12
---

# Strategia: SH_BMS_RTO

## Tipo
SMC / pattern strutturale

## Trigger meccanico
Stop hunt + break of market structure + return to OB/FVG. Rari trade, non ancora validata.

## Configurazione attuale (v2.5.0)
- **Timeframe**: vedi NXS_StrategyProfiles.mqh
- **SL**: vedi NXS_StrategyProfiles.mqh× ATR · **TP**: vedi NXS_StrategyProfiles.mqh× ATR
- **Filtro HTF**: vedi NXS_StrategyProfiles.mqh
- **Trailing**: vedi NXS_StrategyProfiles.mqh
- **Rischio per trade**: 0.5%
- **Abilitata nell'EA**: Sì

## Risultati (build v2.4.8, stessa config di quella sopra)
- **3 mesi**: 0 trade eseguiti in questo build.
- **3 anni**: 8 setup, 3W/0L/0BE, WR 100.0%, expR +0.392, **PF 99.00**

## Stato
PENDING — campione troppo piccolo (<15 trade) per giudicare. Confermato sui
10 segmenti reali: **17 trade totali** su 8 anni disponibili (2016+2019-25),
3 anni a zero setup, mai più di 6 trade in un anno singolo.

## Audit Blocco 1 (16/07): fedeltà OK, ma non testabile sul sito
Il codice MQL5 (`NXS_Strat_SH_BMS_RTO`) implementa davvero tutti e 3 i
componenti del nome — Stop Hunt (`sw.confirmed`, `SNXSSweepExt`), Break of
Market Structure (**vero CHoCH**, `g_struct.chochUp/chochDown` — a
differenza di TURTLE_SOUP, qui la conferma di struttura c'è già), Return
to Origin (prezzo che rientra nella zona FVG appena formata, `bid` tra
`h4`/`l2`). Nessun bug di fedeltà.

**Non testabile sul motore sito**: `sig_sh_bms_rto` lì è un proxy dichiarato
che riusa `sig_ob_mit` (vedi [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]])
— un A/B come quelli fatti per TURTLE_SOUP/LIQ_SWEEP darebbe un numero senza
significato, non testerebbe mai la vera logica. L'unica fonte di verità
possibile è MT5 diretto — verrà coperta dallo sweep Optimization 1-37 in
corso lato utente.

**Perché è così raro**: 3 condizioni simultanee sullo stesso bar (sweep
confermato + CHoCH + FVG a 3 candele formato + prezzo già dentro quella
zona) — rarità spiegata dal codice, non un mistero né necessariamente un
difetto. Nessun cambio proposto finché non c'è più campione da MT5.

## Aggiornamento 11/08 — claim "non testabile" obsoleta; v1 confermata debole, v2 la risolve

~~Non testabile sul motore sito (proxy dichiarato, riusa `sig_ob_mit`)~~
**Correzione: claim obsoleta.** Dal 04/08 esiste un'implementazione reale
fedele (`sig_sh_bms_rto`, commento: "fedele a NXS_SHBMS_UpdateSide, prima
proxy sig_ob_mit") — verificato nel codice. Testata ora sullo storico
ampio (2019-2026): su **1h** il campione non è più minuscolo (204 trade)
ma il trigger v1 (3 condizioni sullo stesso bar) resta debole su entrambi
i lati — **IS PF 0.77/118 → OOS PF 0.81/86**, nessuna direzione positiva.

Conferma quantitativamente quello che si sapeva solo qualitativamente:
**SH_BMS_RTO_V2** (state machine multi-barra sweep→attesa MSS→attesa
ritorno in zona, stesso principio di TURTLE_SOUP_CHOCH) risolve davvero il
problema strutturale della v1 — OOS PF 1.47/224, walk-forward 4/5 finestre
sopra 1.0 (0.84-1.65), drawdown contenuto (7-16%). La v1 non ha ricevuto
(e non riceverà) un fix "finestra" dedicato: la v2 è già la soluzione
migliore trovata per questa famiglia di pattern, nessun motivo di
duplicare lo sforzo. **v2 è la versione da preferire**, v1 chiusa senza
ulteriori tentativi.

## Note


## Collegamenti
[[MOC - Trading]] · [[MOC - Strategie]] · [[NEXUS EA - Screening Strategie (sito 10y)]] · [[NEXUS EA - Lezione Overfitting 3Y]] · [[NEXUS EA - Audit Fedeltà Trigger (tutte le 37 strategie)]]
