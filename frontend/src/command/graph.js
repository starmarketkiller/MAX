import { DEPARTMENTS } from "./stations.js";
export const AUTOMATIONS = [
    { id: "lead-in", on: "lead.created", when: "C'è una fonte e non è un duplicato", workflowId: "revenue.pipeline", capabilities: ["crm"], approval: "none", retry: 2, timeout: "30s", dedupe: "lead.created:source", onFail: "stop", emits: "revenue.reviewed", output: "Lead in coda, non contattato" },
    { id: "opportunity-in", on: "opportunity.found", when: "Il segnale non è un prezzo", workflowId: "trading.pipeline", capabilities: ["research"], approval: "none", retry: 1, timeout: "30s", dedupe: "opportunity.found:id", onFail: "stop", emits: "trading.researched", output: "Ricerca, non un ordine" },
    { id: "product-in", on: "product.found", when: "Il pezzo è descritto", workflowId: "fashion.pipeline", capabilities: ["research"], approval: "none", retry: 1, timeout: "30s", dedupe: "product.found:id", onFail: "stop", emits: "fashion.packed", output: "Pacco interno" },
    { id: "asset-ok", on: "asset.approved", when: "La review non è dell'autore", workflowId: "social.pipeline", capabilities: ["writing"], approval: "required", retry: 0, timeout: "30s", dedupe: "asset.approved:id", onFail: "stop", emits: "social.drafted", output: "Bozza, non un post" },
    { id: "content-ok", on: "content.approved", when: "Manca ancora il permesso di uscita", workflowId: "social.pipeline", capabilities: ["quality"], approval: "required", retry: 0, timeout: "30s", dedupe: "content.approved:id", onFail: "stop", emits: "social.scheduled", output: "Slot proposto" },
    { id: "strategy-new", on: "strategy.new", when: "È una ipotesi, non una promozione", workflowId: "trading.pipeline", capabilities: ["research"], approval: "none", retry: 1, timeout: "60s", dedupe: "strategy.new:id", onFail: "stop", emits: "trading.backtested", output: "Backtest o non eseguito" },
    { id: "backtest-done", on: "trading.backtested", when: "Il campione di test non è quello di validazione", workflowId: "trading.pipeline", capabilities: ["testing"], approval: "none", retry: 1, timeout: "60s", dedupe: "trading.backtested:id", onFail: "stop", emits: "trading.robust", output: "Robustezza o unknown" },
    { id: "test-failed", on: "test.failed", when: "Il fail è riproducibile", workflowId: "systems.pipeline", capabilities: ["testing", "incident"], approval: "none", retry: 2, timeout: "60s", dedupe: "test.failed:id", onFail: "stop", emits: "systems.diagnosed", output: "Diagnosi, non un deploy" },
    { id: "task-done", on: "task.completed", when: "C'è un result packet", workflowId: "jarvis.pipeline", capabilities: ["report"], approval: "none", retry: 1, timeout: "30s", dedupe: "task.completed:id", onFail: "stop", emits: "jarvis.reported", output: "Report SIM" },
    { id: "kpi-down", on: "kpi.negative", when: "La base è osservata, non stimata", workflowId: "improve.global", capabilities: ["performance"], approval: "none", retry: 0, timeout: "30s", dedupe: "kpi.negative:dept", onFail: "stop", emits: "improve.detected", output: "Problema in council" },
    { id: "cost-anomaly", on: "cost.anomaly", when: "La riga ha una fonte", workflowId: "finance.pipeline", capabilities: ["finance"], approval: "required", retry: 1, timeout: "30s", dedupe: "cost.anomaly:id", onFail: "stop", emits: "finance.flagged", output: "Spesa ferma se il tetto manca" },
    { id: "improve-verified", on: "improve.verified", when: "La review è indipendente", workflowId: "improve.global", capabilities: ["verify"], approval: "required", retry: 0, timeout: "30s", dedupe: "improve.verified:id", onFail: "stop", emits: "improve.proposal", output: "Proposta, non un'adozione" },
];
export const FLOWS = [
    { id: "j-trading", from: "jarvis", to: "trading", packet: "Task di ricerca. Non è un ordine." },
    { id: "j-revenue", from: "jarvis", to: "revenue", packet: "Richiesta commerciale." },
    { id: "j-fashion", from: "jarvis", to: "fashion", packet: "Richiesta di campagna." },
    { id: "j-social", from: "jarvis", to: "social", packet: "Bozza da tenere interna." },
    { id: "j-systems", from: "jarvis", to: "systems", packet: "Richiesta di build." },
    { id: "j-finance", from: "jarvis", to: "finance", packet: "Domanda di tetto, senza cifra." },
    { id: "trading-finance", from: "trading", to: "finance", packet: "Rischio e costi. Nessun PnL." },
    { id: "finance-jarvis", from: "finance", to: "jarvis", packet: "Report non emesso." },
    { id: "fashion-social", from: "fashion", to: "social", packet: "Asset non pubblicato." },
    { id: "social-revenue", from: "social", to: "revenue", packet: "Lead assenti, non zero." },
    { id: "revenue-finance", from: "revenue", to: "finance", packet: "Ricavo assente." },
    { id: "revenue-systems", from: "revenue", to: "systems", packet: "Specifica. Non un deploy." },
    { id: "systems-trading", from: "systems", to: "trading", packet: "Capability non rilasciata." },
    { id: "systems-revenue", from: "systems", to: "revenue", packet: "Capability non rilasciata." },
    { id: "systems-fashion", from: "systems", to: "fashion", packet: "Capability non rilasciata." },
    { id: "systems-social", from: "systems", to: "social", packet: "Capability non rilasciata." },
    { id: "systems-finance", from: "systems", to: "finance", packet: "Capability non rilasciata." },
    { id: "systems-jarvis", from: "systems", to: "jarvis", packet: "Capability non rilasciata." },
    { id: "trading-council", from: "trading", to: "council", packet: "Ipotesi, non un cambiamento." },
    { id: "revenue-council", from: "revenue", to: "council", packet: "Ipotesi, non un cambiamento." },
    { id: "fashion-council", from: "fashion", to: "council", packet: "Ipotesi, non un cambiamento." },
    { id: "social-council", from: "social", to: "council", packet: "Ipotesi, non un cambiamento." },
    { id: "systems-council", from: "systems", to: "council", packet: "Ipotesi, non un cambiamento." },
    { id: "finance-council", from: "finance", to: "council", packet: "Ipotesi, non un cambiamento." },
    { id: "jarvis-council", from: "jarvis", to: "council", packet: "Ipotesi, non un cambiamento." },
];
export const BUSINESS_UNITS = [
    { id: "workos", name: "WorkOS / Industrial Intelligence", status: "planned", departments: ["systems", "jarvis", "finance"] },
    { id: "automation-agency", name: "AI Automation Agency", status: "planned", departments: ["revenue", "social", "systems", "jarvis"] },
    { id: "digital-products", name: "Digital Products", status: "planned", departments: ["revenue", "systems", "finance", "social"] },
    { id: "future", name: "Future Ventures", status: "planned", departments: ["revenue", "finance", "jarvis"] },
];
export const REVENUE_VENTURES = {
    expected: 4,
    names: [],
    status: "not_listed",
    note: "Il masterplan parla di quattro venture. I nomi non sono in questo repo: non ne invento.",
};
export function roomEdges() {
    const ids = new Set(DEPARTMENTS.map((item) => item.id));
    const seen = new Set();
    const edges = [];
    for (const flow of FLOWS) {
        if (!ids.has(flow.from) || !ids.has(flow.to))
            continue;
        const key = [flow.from, flow.to].sort().join(":");
        if (seen.has(key))
            continue;
        seen.add(key);
        edges.push({ a: flow.from, b: flow.to });
    }
    return edges;
}
export function automationCycles() {
    const listeners = new Map();
    for (const item of AUTOMATIONS) {
        const list = listeners.get(item.on) ?? [];
        list.push(item);
        listeners.set(item.on, list);
    }
    const cycles = [];
    const walk = (event, stack) => {
        if (stack.includes(event)) {
            cycles.push([...stack, event].join(" → "));
            return;
        }
        for (const item of listeners.get(event) ?? [])
            walk(item.emits, [...stack, event]);
    };
    for (const item of AUTOMATIONS)
        walk(item.on, []);
    return cycles;
}
