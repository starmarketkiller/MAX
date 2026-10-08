# NEXUS MASTERPLAN V4 — Gap Analysis (Masterplan vs Repository Reale)

Documento intenzionalmente breve — il dettaglio step-per-step vive nei [7 documenti di reparto](NEXUS_MASTERPLAN_V4.md#10-indice-completo-dei-documenti-di-questo-set), non duplicato qui.

## Sintesi per reparto

| Reparto | % step IMPLEMENTED (su totale infografica) | Gap principale |
|---|---|---|
| Trading | 5/10 pieni, 4/10 parziali, 1/10 pianificato | Nessun gate di decisione "go-live" codificato (step 6) — vedi [Architecture Review #1](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md#1-high_impact-codificare-il-gate-go-live-per-le-strategie-di-trading) |
| Revenue | 4/9 pieni, 4/9 parziali, 1/9 bloccato by design | Conversione/pagamento deliberatamente manuali — non un gap, una scelta di pivot |
| AI Fashion Agency | 6/10 pieni, 2/10 parziali, 1/10 bloccato by policy, 1/10 pianificato | Pubblicazione/monetizzazione hard-disabled by policy — coerente col vincolo del task, non un gap da colmare ora |
| Social/Content | 0/9 come reparto a sé — assorbito in AI Fashion Agency | Nessun gap reale: scelta architetturale valida con un solo consumatore |
| System & Development | 3/9 pieni, 4/9 parziali, 2/9 pianificati | Un solo template Ministral bounded (read-only) — vedi [Architecture Review #8](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md#8-high_impact-un-template-ministral-bounded-write-capable) |
| Finance & Cost | 0/8 pieni, 4/8 parziali, 4/8 pianificati | Nessun reparto coeso — solo frammenti sparsi; vedi [Architecture Review #4](NEXUS_MASTERPLAN_V4_ARCHITECTURE_REVIEW.md#4-high_impact-aggregatore-finance--cost-cross-reparto) |
| Jarvis & Automation | 8/11 pieni, 3/11 parziali | Il più maturo; unico gap sistematico è il self-improvement locale (100% pianificato, come ovunque) |

## Il gap cross-dipartimentale più significativo

**Self-improvement locale: PLANNED in tutti e 7 i reparti, zero eccezioni.** Nessun Global Improvement Council esiste in nessuna forma. Questo non è un gap di un singolo reparto — è l'unico vero gap strutturale condiviso da tutto il sistema, e il motivo per cui la Fase 3 della roadmap di maturità ([§9 del Masterplan](NEXUS_MASTERPLAN_V4.md#9-roadmap-di-maturità--riconciliata-con-la-realtà)) non è ancora iniziabile in modo coordinato.

## Il secondo gap più significativo

**Nessuna interfaccia formale `DepartmentResponsabile` esiste.** Ogni reparto è cablato ad hoc in `service.py`. "Mai aggirare l'Orchestrator" è rispettato per convenzione osservata (confermato: zero bypass trovati in alcun reparto), non imposto da un contratto verificabile. Proposta in [NEXUS_MASTERPLAN_V4_RESPONSABILE_COORDINATION_MODEL.md](NEXUS_MASTERPLAN_V4_RESPONSABILE_COORDINATION_MODEL.md).

## Cosa NON è un gap (scoperte positive da non perdere nella lettura critica)

- **Zero duplicazione incontrollata di agenti** — ogni census ha confermato riuso dell'Orchestrator esistente, nessun nuovo agente creato per reparto.
- **Disciplina dry-run coerente** su ogni punto che tocca spesa reale o pubblicazione (AI Fashion Agency, Social/Content) — guardrail di codice, non solo di documentazione.
- **Deploy pipeline rigorosa** (Safe Deploy V1) — gate CI→rischio→deploy reale, non aspirazionale.
- **Executive State maturo** — aggregatore a 9 domini con isolamento per-provider, già cablato in produzione.

## Legenda e metodo
Vedi [NEXUS_MASTERPLAN_V4.md §0 e §2](NEXUS_MASTERPLAN_V4.md). Ogni percentuale sopra è un conteggio diretto degli step classificati nei documenti di reparto, non una stima.
