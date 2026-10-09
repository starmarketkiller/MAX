import { skillById } from "./skills.js";
export const DEPARTMENTS = [
    { id: "trading", code: "R1", name: "Trading", lede: "Dalla ricerca al gate. Nessun ordine parte da qui." },
    { id: "revenue", code: "R2", name: "Revenue", lede: "Dal segnale all'offerta. Nessun cliente inventato." },
    { id: "fashion", code: "R3", name: "Agency", lede: "Dalla tendenza al passaggio. Nessun credito speso da solo." },
    { id: "social", code: "R4", name: "Social", lede: "Dalla bozza al gate. L'uscita è spenta." },
    { id: "systems", code: "R5", name: "Systems", lede: "Dal requisito al gate di rilascio. Niente deploy." },
    { id: "finance", code: "R6", name: "Finance", lede: "Costi e buchi. Nessuna cifra inventata." },
    { id: "jarvis", code: "R7", name: "Jarvis", lede: "Smista e si ferma dove serve un permesso." },
];
function build(departmentId, workflowId, rows) {
    return rows.map((row, index) => {
        const id = `${departmentId}.${row.code.toLowerCase()}`;
        const gate = row.gate ?? "none";
        const previous = index === 0 ? null : `${departmentId}.${rows[index - 1].code.toLowerCase()}`;
        return {
            id,
            departmentId,
            index,
            code: row.code,
            name: row.name,
            role: row.role,
            workflowId,
            input: row.input,
            output: row.output,
            skills: row.skills,
            tools: ["NON_CONNECTED"],
            worker: row.worker,
            verifier: gate === "none" ? "registry" : "independent-reviewer",
            permissions: gate === "nogo" ? ["read", "never-live"] : gate === "approval" ? ["read", "propose"] : ["read"],
            dependencies: previous ? [previous] : [],
            gate,
            status: "sim",
            live: "not_connected",
            metrics: [{ name: "valore", value: "unknown" }],
            stage: row.stage ?? (index === 0 ? "s1" : gate === "none" ? "s4" : "s5"),
        };
    });
}
const trading = build("trading", "trading.pipeline", [
    { code: "DATA", name: "Market Data", role: "Raccoglie la serie senza inventare un prezzo.", skills: ["extract", "validate"], worker: "data", input: "Feed", output: "Serie con provenienza" },
    { code: "NEWS", name: "News Intelligence", role: "Contesto solo se la fonte c'è.", skills: ["research", "documents"], worker: "research", input: "Headline", output: "Contesto o unknown" },
    { code: "STRUCT", name: "Market Structure", role: "Struttura del prezzo, non un ordine.", skills: ["technical"], worker: "analyst", input: "Serie", output: "Livelli vuoti se la serie manca" },
    { code: "RESEARCH", name: "Strategy Research", role: "Ipotesi di strategia, ancora in ricerca.", skills: ["research"], worker: "research", input: "Struttura", output: "Ipotesi" },
    { code: "IMPLEMENT", name: "Strategy Implementation", role: "Traduce l'ipotesi in regole leggibili.", skills: ["codegen"], worker: "builder", input: "Ipotesi", output: "Regole" },
    { code: "BACKTEST", name: "Backtesting", role: "Prova sulla storia, se la storia c'è.", skills: ["testing"], worker: "builder", input: "Regole", output: "Esito o non eseguito" },
    { code: "OOS", name: "Out-of-Sample", role: "Un secondo campione, non lo stesso.", skills: ["testing", "verify"], worker: "reviewer", input: "Esito", output: "Conferma o scarto" },
    { code: "ROBUST", name: "Cost & Robustness", role: "Costi e fragilità, senza un PnL finto.", skills: ["finance", "testing"], worker: "analyst", input: "Esito", output: "Fragilità o unknown" },
    { code: "VALID", name: "Independent Validation", role: "Chi valida non è chi ha ricercato.", skills: ["verify"], worker: "reviewer", gate: "approval", input: "Pacco ricerca", output: "Stop finché manca la review" },
    { code: "RISK", name: "Risk Engine", role: "Può solo ridurre o rifiutare.", skills: ["finance"], worker: "analyst", input: "Proposta", output: "Tetto o rifiuto" },
    { code: "BOOK", name: "Portfolio Engine", role: "Esposizione, non un conto vero.", skills: ["finance"], worker: "analyst", input: "Rischio", output: "Concentrazione unknown" },
    { code: "SHADOW", name: "Shadow Trading", role: "Osserva senza inviare.", skills: ["performance"], worker: "data", input: "Segnale", output: "Ombra, non un fill" },
    { code: "EXEC", name: "Execution Monitoring", role: "Nessun LLM autorizza un trade.", skills: ["inspect"], worker: "reviewer", gate: "nogo", input: "Ordine proposto", output: "Nessun ordine" },
    { code: "PERF", name: "Performance Analytics", role: "Senza fill il risultato è assente.", skills: ["performance", "report"], worker: "analyst", input: "Fill", output: "Assente" },
    { code: "LIFT", name: "Strategy Improvement", role: "Proposta di modifica, non promozione.", skills: ["experiment", "optimize"], worker: "research", stage: "s6", input: "Scostamento", output: "Ipotesi" },
]);
const revenue = build("revenue", "revenue.pipeline", [
    { code: "FIND", name: "Opportunity Discovery", role: "Segna un'opportunità solo con fonte.", skills: ["research"], worker: "research", input: "Segnale", output: "Opportunità o scarto" },
    { code: "MARKET", name: "Market Research", role: "Contesto del mercato, senza clienti finti.", skills: ["research", "documents"], worker: "research", input: "Opportunità", output: "Nota" },
    { code: "PROSPECT", name: "Prospect Discovery", role: "Un nome reale oppure la riga resta vuota.", skills: ["extract"], worker: "data", input: "Nota", output: "Prospect o vuoto" },
    { code: "QUALIFY", name: "Lead Qualification", role: "Fit contro un obiettivo aperto.", skills: ["crm"], worker: "analyst", input: "Prospect", output: "Fit unknown" },
    { code: "CRM", name: "CRM", role: "Un record, non tre copie.", skills: ["crm", "validate"], worker: "data", input: "Lead", output: "Record deduplicato" },
    { code: "OFFER", name: "Offer Development", role: "Perimetro. Il prezzo resta unknown.", skills: ["writing"], worker: "writer", input: "Fit", output: "Offerta bozza" },
    { code: "PROPOSAL", name: "Proposal Generation", role: "Documento interno.", skills: ["writing", "documents"], worker: "writer", input: "Offerta", output: "Proposta" },
    { code: "OUTREV", name: "Outreach Review", role: "Senza OK il messaggio non esce.", skills: ["quality"], worker: "reviewer", gate: "approval", input: "Proposta", output: "In coda" },
    { code: "FOLLOW", name: "Follow-up", role: "Solo dopo un invio che non c'è stato.", skills: ["crm"], worker: "writer", input: "Invio", output: "Nessun follow-up" },
    { code: "NEGO", name: "Negotiation", role: "Non negozia al posto di un umano.", skills: ["documents"], worker: "writer", input: "Risposta", output: "Nota" },
    { code: "CONVERT", name: "Sales Conversion", role: "Nessuna vendita registrata.", skills: ["crm"], worker: "analyst", gate: "nogo", input: "Trattativa", output: "Nessun contratto" },
    { code: "DELIVER", name: "Service Delivery", role: "Consegna solo ciò che era in offerta.", skills: ["inspect"], worker: "builder", input: "Contratto", output: "Niente da consegnare" },
    { code: "CARE", name: "Customer Support", role: "Nessun cliente in coda.", skills: ["documents"], worker: "writer", input: "Richiesta", output: "Coda vuota" },
    { code: "KEEP", name: "Retention", role: "Senza clienti non c'è retention.", skills: ["performance"], worker: "analyst", input: "Storico", output: "Assente" },
    { code: "STATS", name: "Revenue Analytics", role: "Il ricavo è assente, non zero.", skills: ["finance", "report"], worker: "analyst", input: "Fatti", output: "Unknown" },
    { code: "LIFT", name: "Business Improvement", role: "Lezione, senza abbellire.", skills: ["optimize", "experiment"], worker: "research", stage: "s6", input: "Buco", output: "Proposta" },
]);
const fashion = build("fashion", "fashion.pipeline", [
    { code: "TREND", name: "Trend Research", role: "Una tendenza ripetuta, non un post isolato.", skills: ["research"], worker: "research", input: "Fonti", output: "Segnale o scarto" },
    { code: "DISCOVER", name: "Product Discovery", role: "Solo pezzi descritti.", skills: ["extract"], worker: "data", input: "Catalogo", output: "Candidati" },
    { code: "VERIFY", name: "Product Verification", role: "Il pezzo esiste oppure non entra.", skills: ["validate"], worker: "reviewer", input: "Candidato", output: "Verificato o scarto" },
    { code: "PLAN", name: "Creative Planning", role: "Obiettivo e divieti.", skills: ["writing"], worker: "writer", input: "Segnale", output: "Brief", stage: "s2" },
    { code: "MODEL", name: "Model Management", role: "Scheda di lavoro, non un feed di volti.", skills: ["documents"], worker: "data", input: "Brief", output: "Scheda" },
    { code: "STYLE", name: "Styling", role: "Vincoli di stile, non un render pagato.", skills: ["writing"], worker: "writer", input: "Scheda", output: "Direzione" },
    { code: "CAMPAIGN", name: "Campaign Design", role: "Pacchetto interno.", skills: ["writing"], worker: "writer", input: "Direzione", output: "Campagna bozza" },
    { code: "ASSET", name: "Asset Production", role: "Non spende crediti senza OK.", skills: ["codegen"], worker: "builder", input: "Brief", output: "Nessun asset generato" },
    { code: "QUALITY", name: "Quality Review", role: "Occhio diverso da chi produce.", skills: ["quality"], worker: "reviewer", input: "Asset", output: "Niente da rivedere" },
    { code: "COMPLY", name: "Compliance", role: "Ciò che non si può generare né pubblicare.", skills: ["verify"], worker: "reviewer", input: "Brief", output: "Divieti" },
    { code: "PACK", name: "Content Packaging", role: "Pacchetto per Social, ancora interno.", skills: ["writing"], worker: "writer", input: "Divieti", output: "Pacco" },
    { code: "HANDOFF", name: "Social Handoff", role: "Passa la bozza. Non pubblica.", skills: ["inspect"], worker: "router", input: "Pacco", output: "Handoff interno" },
    { code: "BRAND", name: "Brand Outreach", role: "Nessun contatto parte da solo.", skills: ["crm"], worker: "writer", gate: "approval", input: "Pacco", output: "In coda" },
    { code: "MONEY", name: "Monetization", role: "Nessun ricavo da attribuire.", skills: ["finance"], worker: "analyst", gate: "nogo", input: "Contratto", output: "Assente" },
    { code: "REVIEW", name: "Performance Review", role: "Senza pubblicazione non c'è performance.", skills: ["performance"], worker: "analyst", stage: "s6", input: "Metriche", output: "Assente" },
]);
const social = build("social", "social.pipeline", [
    { code: "TREND", name: "Trend Monitoring", role: "Ascolta solo fonti collegate. Qui non ce ne sono.", skills: ["research"], worker: "research", input: "Fonti", output: "Assente" },
    { code: "AUDIENCE", name: "Audience Research", role: "Non inventa un pubblico.", skills: ["research"], worker: "analyst", input: "Canale", output: "Unknown" },
    { code: "EDIT", name: "Editorial Planning", role: "Perché e per chi.", skills: ["writing"], worker: "writer", input: "Obiettivo", output: "Piano", stage: "s2" },
    { code: "SCRIPT", name: "Script Writing", role: "Una tesi, non dieci slogan.", skills: ["writing"], worker: "writer", input: "Piano", output: "Testo" },
    { code: "CREATE", name: "Creative Production", role: "Bozza privata.", skills: ["writing"], worker: "writer", input: "Testo", output: "Bozza" },
    { code: "CUT", name: "Video/Image Editing", role: "Adatta. Non pubblica.", skills: ["inspect"], worker: "builder", input: "Bozza", output: "Versione" },
    { code: "ADAPT", name: "Platform Adaptation", role: "Formato del canale, se il canale esiste.", skills: ["writing"], worker: "writer", input: "Versione", output: "Formato o unknown" },
    { code: "QC", name: "Quality Control", role: "Claim senza fonte non passano.", skills: ["quality"], worker: "reviewer", input: "Pezzo", output: "Pass o ritorno" },
    { code: "OK", name: "Publishing Approval", role: "Manca l'OK. Quindi non si pubblica.", skills: ["verify"], worker: "reviewer", gate: "approval", input: "Pezzo", output: "Fermo" },
    { code: "SCHED", name: "Scheduling", role: "Slot proposto, non un calendario live.", skills: ["inspect"], worker: "router", input: "OK", output: "Proposta di slot" },
    { code: "PUB", name: "Publishing", role: "L'adapter di uscita è spento.", skills: ["inspect"], worker: "router", gate: "nogo", input: "Slot", output: "Nessun post" },
    { code: "COMMUNITY", name: "Community Management", role: "Nessun thread collegato.", skills: ["writing"], worker: "writer", input: "Commenti", output: "Assente" },
    { code: "STATS", name: "Engagement Analytics", role: "Manca il dato: si scrive assente, non zero.", skills: ["performance"], worker: "analyst", input: "Account", output: "Assente" },
    { code: "LEAD", name: "Lead Attribution", role: "Nessun lead da attribuire.", skills: ["crm"], worker: "analyst", input: "Click", output: "Assente" },
    { code: "OPT", name: "Optimization", role: "Proposta sul piano, non un rilancio.", skills: ["optimize"], worker: "research", stage: "s6", input: "Assenze", output: "Ipotesi" },
]);
const systems = build("systems", "systems.pipeline", [
    { code: "REQ", name: "Requirements", role: "Cosa manca nel flusso, non nel gusto.", skills: ["documents"], worker: "analyst", input: "Richiesta", output: "Requisito" },
    { code: "REPO", name: "Repository Analysis", role: "Cerca l'equivalente già nel programma.", skills: ["inspect", "knowledge"], worker: "builder", input: "Repo", output: "Riuso o buco" },
    { code: "ARCH", name: "Architecture", role: "Si estende o si rompe.", skills: ["inspect"], worker: "builder", input: "Requisito", output: "Scelta", stage: "s2" },
    { code: "REUSE", name: "Capability Reuse", role: "Uno skill, più reparti.", skills: ["knowledge"], worker: "research", input: "Registro", output: "Capability o mancanza" },
    { code: "PLAN", name: "Task Planning", role: "Task atomiche e prove.", skills: ["inspect"], worker: "router", input: "Scelta", output: "Piano" },
    { code: "CODE", name: "Coding", role: "Patch piccola, mai sopra main.", skills: ["codegen"], worker: "builder", input: "Piano", output: "Diff" },
    { code: "UNIT", name: "Unit Testing", role: "Il comportamento nuovo ha una prova.", skills: ["testing"], worker: "builder", input: "Diff", output: "Prova" },
    { code: "INT", name: "Integration Testing", role: "Ciò che già esisteva non si rompe in silenzio.", skills: ["testing"], worker: "builder", input: "Prova", output: "Integrazione o fail" },
    { code: "SEC", name: "Security Testing", role: "Permesso minimo.", skills: ["verify", "inspect"], worker: "reviewer", input: "Diff", output: "Nota di rischio" },
    { code: "REVIEW", name: "Code Review", role: "Non è lo stesso agente che ha scritto.", skills: ["inspect", "quality"], worker: "reviewer", input: "Diff", output: "Review" },
    { code: "CI", name: "CI", role: "La pipeline non è collegata in questa sessione.", skills: ["testing"], worker: "builder", input: "Branch", output: "Non eseguito" },
    { code: "STAGE", name: "Staging", role: "Un ambiente che non è il live.", skills: ["testing"], worker: "builder", input: "Build", output: "Isola" },
    { code: "APPROVE", name: "Deploy Approval", role: "Manca l'OK. Quindi non si rilascia.", skills: ["verify"], worker: "reviewer", gate: "approval", input: "Richiesta", output: "Fermo" },
    { code: "SHIP", name: "Safe Deploy", role: "Nessun rilascio da questo simulatore.", skills: ["inspect"], worker: "reviewer", gate: "nogo", input: "OK", output: "Nessun deploy" },
    { code: "WATCH", name: "Monitoring", role: "Runtime non sondato.", skills: ["incident"], worker: "data", input: "Servizio", output: "Non sondato" },
    { code: "INCIDENT", name: "Incident Recovery", role: "Rollback descritto, non eseguito sul live.", skills: ["incident"], worker: "builder", input: "Sintomo", output: "Piano di ritorno" },
    { code: "DOCS", name: "Documentation", role: "Cosa è riusato e cosa è nuovo.", skills: ["documents"], worker: "writer", input: "Diff", output: "Nota" },
    { code: "OPT", name: "Optimization", role: "Proposta, non un cambiamento in produzione.", skills: ["optimize"], worker: "research", stage: "s6", input: "Attrito", output: "Proposta" },
]);
const finance = build("finance", "finance.pipeline", [
    { code: "INREV", name: "Revenue Intake", role: "Solo ricavi con prova. Qui non ce ne sono.", skills: ["extract", "validate"], worker: "data", input: "Prova", output: "Nessuna riga" },
    { code: "INEXP", name: "Expense Intake", role: "Senza documento non c'è costo.", skills: ["extract", "validate"], worker: "data", input: "Documento", output: "Nessuna riga" },
    { code: "RECON", name: "Data Reconciliation", role: "Osservato, stimato o assente. Mai fusi.", skills: ["validate", "finance"], worker: "analyst", input: "Righe", output: "Scarti" },
    { code: "ATTR", name: "Cost Attribution", role: "I non attribuiti restano visibili.", skills: ["finance"], worker: "analyst", input: "Costo", output: "Non attribuito" },
    { code: "BUDGET", name: "Budget Management", role: "Se il tetto è unknown, la spesa resta bloccata.", skills: ["finance"], worker: "analyst", input: "Tetto", output: "Blocco" },
    { code: "MARGIN", name: "Profitability Analysis", role: "Manca un lato: il margine è unknown.", skills: ["finance"], worker: "analyst", input: "Ricavo e costo", output: "Unknown" },
    { code: "CASH", name: "Cash Flow", role: "Nessun movimento di cassa osservato.", skills: ["finance"], worker: "analyst", input: "Movimenti", output: "Assente" },
    { code: "ROI", name: "ROI Analysis", role: "Senza base non si calcola un ritorno.", skills: ["finance", "performance"], worker: "analyst", input: "Base", output: "Unknown" },
    { code: "FORE", name: "Forecasting", role: "Scenario nominato, sempre SIM.", skills: ["report"], worker: "analyst", input: "Ipotesi", output: "SIM" },
    { code: "RISK", name: "Risk Scenarios", role: "Confini dello scenario, non un allarme finto.", skills: ["finance"], worker: "analyst", input: "Ipotesi", output: "Confine" },
    { code: "REPORT", name: "Financial Reporting", role: "Non emette un report con cifre assenti.", skills: ["report"], worker: "reviewer", gate: "approval", input: "Buchi", output: "Report non emesso" },
    { code: "INVEST", name: "Investment Planning", role: "Opzione, non un impegno.", skills: ["finance"], worker: "analyst", input: "Proposta", output: "Opzione" },
    { code: "OPT", name: "Cost Optimization", role: "Prima elenca cosa manca.", skills: ["optimize"], worker: "research", stage: "s6", input: "Buchi", output: "Proposta" },
]);
const jarvis = build("jarvis", "jarvis.pipeline", [
    { code: "UI", name: "User Interface", role: "Mostra lo stato. Non è un ordine.", skills: ["report"], worker: "router", input: "Stato", output: "Vista", stage: "s1" },
    { code: "INTAKE", name: "Voice/Text Intake", role: "Apre un id. Dedup della richiesta.", skills: ["extract"], worker: "router", input: "Testo", output: "Richiesta", stage: "s1" },
    { code: "INTENT", name: "Intent Classification", role: "Cosa serve, in una frase.", skills: ["knowledge"], worker: "router", input: "Richiesta", output: "Intent", stage: "s2" },
    { code: "CONTEXT", name: "Context Retrieval", role: "Proiezione corta, non il corpus intero.", skills: ["knowledge"], worker: "research", input: "Intent", output: "Contesto", stage: "s2" },
    { code: "STATE", name: "Executive State", role: "Una riga per reparto. Qui è simulata.", skills: ["report"], worker: "analyst", input: "Reparti", output: "Proiezione SIM", stage: "s3" },
    { code: "FAST", name: "Fast Path", role: "Risposta breve. Se compare un side effect, esce.", skills: ["knowledge"], worker: "router", input: "Contesto", output: "Bozza o stop", stage: "s3" },
    { code: "MIND", name: "Cognitive Worker", role: "Worker previsto. Nessun modello collegato.", skills: ["research", "documents"], worker: "research", input: "Task", output: "NON_CONNECTED", stage: "s3" },
    { code: "PLAN", name: "Task Planning", role: "Task, dipendenze, prove.", skills: ["inspect"], worker: "router", input: "Intent", output: "Piano", stage: "s2" },
    { code: "ORCH", name: "Global Orchestrator", role: "Una coda. Non un secondo orchestratore.", skills: ["inspect"], worker: "router", input: "Piano", output: "Assegnazione", stage: "s3" },
    { code: "CAP", name: "Capability Resolution", role: "Quale capacità, non quale marca.", skills: ["knowledge"], worker: "router", input: "Bisogno", output: "Capability o buco", stage: "s3" },
    { code: "GOV", name: "Resource Governor", role: "Tempo, retry, spesa. Unknown blocca la spesa.", skills: ["finance"], worker: "analyst", input: "Tetto", output: "Blocco spesa", stage: "s3" },
    { code: "APPROVAL", name: "Approval Manager", role: "Se serve un umano, la task aspetta.", skills: ["verify"], worker: "reviewer", gate: "approval", input: "Azione", output: "In attesa", stage: "s5" },
    { code: "MONITOR", name: "Execution Monitoring", role: "Stato e errore. Nessun retry di un publish.", skills: ["incident"], worker: "data", input: "Run", output: "Stato", stage: "s4" },
    { code: "RESULT", name: "Result Retrieval", role: "Legge un risultato, non lo abbellisce.", skills: ["extract"], worker: "data", input: "Store", output: "Pacco o assente", stage: "s5" },
    { code: "RESPONSE", name: "Response Generation", role: "Testo fedele al pacco.", skills: ["report"], worker: "writer", input: "Pacco", output: "Risposta", stage: "s5" },
    { code: "DELIVER", name: "Telegram/Web Delivery", role: "Nessun canale di uscita è collegato.", skills: ["inspect"], worker: "router", gate: "nogo", input: "Risposta", output: "Non inviata", stage: "s5" },
    { code: "NOTIFY", name: "Notifications", role: "Solo se un canale esiste. Non esiste.", skills: ["inspect"], worker: "router", input: "Evento", output: "Non inviata", stage: "s5" },
    { code: "AUTO", name: "Automation Monitoring", role: "Le automazioni sono definite, non armate sul live.", skills: ["incident"], worker: "reviewer", input: "Registro", output: "SIM", stage: "s6" },
]);
const council = build("council", "improve.global", [
    { code: "OBS", name: "Observe", role: "Raccoglie solo ciò che un reparto ha segnato.", skills: ["extract"], worker: "data", input: "Feedback", output: "Osservazione", stage: "s6" },
    { code: "DETECT", name: "Detect", role: "Un buco ripetuto, non un'opinione.", skills: ["validate"], worker: "analyst", input: "Osservazione", output: "Problema", stage: "s6" },
    { code: "DIAG", name: "Diagnose", role: "Confine del problema.", skills: ["incident"], worker: "analyst", input: "Problema", output: "Diagnosi", stage: "s6" },
    { code: "HYPO", name: "Hypothesis", role: "Una causa, dichiarata come ipotesi.", skills: ["experiment"], worker: "research", input: "Diagnosi", output: "Ipotesi", stage: "s6" },
    { code: "EXP", name: "Experiment", role: "Prova piccola, fuori dalla produzione.", skills: ["experiment", "testing"], worker: "builder", input: "Ipotesi", output: "Piano di prova", stage: "s6" },
    { code: "MEASURE", name: "Measure", role: "Criterio prima del risultato.", skills: ["performance"], worker: "analyst", input: "Prova", output: "Misura o unknown", stage: "s6" },
    { code: "REVIEW", name: "Independent Review", role: "Chi rivede non è chi ha proposto.", skills: ["verify"], worker: "reviewer", gate: "approval", input: "Misura", output: "In attesa", stage: "s6" },
    { code: "PROPOSE", name: "Propose", role: "Proposta al council, non un merge.", skills: ["report"], worker: "writer", input: "Review", output: "Proposta", stage: "s6" },
    { code: "ADOPT", name: "Adopt/Reject", role: "Il council non modifica la produzione da solo.", skills: ["verify"], worker: "reviewer", gate: "nogo", input: "Proposta", output: "Non adottato", stage: "s6" },
]);
export const STATIONS = [...trading, ...revenue, ...fashion, ...social, ...systems, ...finance, ...jarvis, ...council];
export const WORKFLOWS = [
    { id: "trading.pipeline", departmentId: "trading", name: "Ricerca fino al gate", stationIds: trading.map((item) => item.id) },
    { id: "revenue.pipeline", departmentId: "revenue", name: "Offerta fino al permesso", stationIds: revenue.map((item) => item.id) },
    { id: "fashion.pipeline", departmentId: "fashion", name: "Campagna fino al contatto", stationIds: fashion.map((item) => item.id) },
    { id: "social.pipeline", departmentId: "social", name: "Bozza fino al publish", stationIds: social.map((item) => item.id) },
    { id: "systems.pipeline", departmentId: "systems", name: "Build fino al rilascio", stationIds: systems.map((item) => item.id) },
    { id: "finance.pipeline", departmentId: "finance", name: "Conti fino al report", stationIds: finance.map((item) => item.id) },
    { id: "jarvis.pipeline", departmentId: "jarvis", name: "Smistamento fino alla consegna", stationIds: jarvis.map((item) => item.id) },
    { id: "improve.global", departmentId: "council", name: "Osserva, prova, non adottare da solo", stationIds: council.map((item) => item.id) },
];
export function stationById(id) {
    return STATIONS.find((item) => item.id === id) ?? null;
}
export function stationsByDepartment(departmentId) {
    return STATIONS.filter((item) => item.departmentId === departmentId).sort((a, b) => a.index - b.index);
}
export function workflowById(id) {
    return WORKFLOWS.find((item) => item.id === id) ?? null;
}
export function assertStationSkills() {
    for (const station of STATIONS) {
        for (const skill of station.skills) {
            if (!skillById(skill))
                throw new Error(`${station.id} skill assente: ${skill}`);
        }
    }
}
