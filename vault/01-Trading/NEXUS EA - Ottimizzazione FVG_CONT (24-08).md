---
type: note
domain: trading
status: active
tags: [trading, nexus-ea, fvg-cont, ottimizzazione-individuale]
created: 2026-08-24
updated: 2026-08-24
---

# NEXUS EA — Ottimizzazione individuale FVG_CONT (24/08)

## Perché

Quattordicesima ottimizzazione — nucleo storico, BUY-only PF1.51,
n=396, mai spinta con trailing.

## Verifica laterale

BUY-only laterale: n=25, PF0.43, sumR=-13.6 — stessa direzione delle
altre strategie del batch corretto oggi, campione più leggibile di
molti altri ma comunque non conclusivo da solo. Stesso caveat generale
della [[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]].

## Trailing: miglioramento con un compromesso onesto sulle finestre

| Config | retail PF (m1/m2) | finestre | n |
|---|---|---|---|
| BUY-only, target fisso 1.5/4.0 (nota) | 1.51 (1.35/1.69) | 5/5 | 396 |
| **BUY + trailing 2.0×ATR** | **1.63 (1.64/1.63)** | 4/5 | 396 |
| BUY + trailing 2.5×ATR | 1.59 (1.38/1.82) | 4/5 | 396 |
| BUY + trailing 3.0×ATR | 1.83 (1.21/2.53) | 4/5 | 396 |

Trailing 2.0×ATR migliora il PF (1.51→1.63) e **riequilibra quasi
perfettamente le due metà** (1.64 vs 1.63, contro 1.35/1.69 del target
fisso) — ma perde una finestra su cinque (l'ultima, la più recente:
PF0.82, non catastrofica ma sotto 1.0; le altre 4 vanno da 1.11 a 3.41).
3.0×ATR ha il PF più alto ma è nuovamente il pattern già visto oggi
(FVG_CONT_V2, MALAYSIAN_SNR_BREAKOUT): PF trainato da poche operazioni
in fondo allo storico (m2=2.53), meno robusto.

## Verdetto

**Adottato trailing 2.0×ATR** — il compromesso migliore tra PF più
alto ed equilibrio tra le metà, nonostante la finestra più recente sia
leggermente sotto breakeven al netto dei costi. Segnalato onestamente,
non nascosto dietro il PF aggregato. Non ancora in MQL5.

## Collegamenti
[[MOC - Trading]]
[[NEXUS EA - CORREZIONE Il BUY-only e Regime-Dipendente non Universale (24-08)]]
[[NEXUS EA - Tabella Master Strategie Verificate (24-08)]]
