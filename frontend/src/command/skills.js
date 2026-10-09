export const SKILLS = [
    { id: "research", name: "Research", input: "Domanda e fonti", output: "Nota con provenienza", requires: "Una fonte citabile", limits: "Non crea fatti mancanti", verifier: "registry" },
    { id: "extract", name: "Data Extraction", input: "Documento o feed", output: "Campi strutturati", requires: "Origine del dato", limits: "Non completa i buchi", verifier: "registry" },
    { id: "validate", name: "Data Validation", input: "Record", output: "Valido o scarto", requires: "Schema del record", limits: "Non corregge in silenzio", verifier: "independent-reviewer" },
    { id: "documents", name: "Document Analysis", input: "Testo", output: "Estratto e dubbi", requires: "Testo integrale", limits: "Non firma per l'autore", verifier: "registry" },
    { id: "technical", name: "Technical Analysis", input: "Serie", output: "Struttura, senza ordine", requires: "Serie con provenienza", limits: "Non autorizza un trade", verifier: "independent-reviewer" },
    { id: "report", name: "Report Generation", input: "Fatti verificati", output: "Report etichettato SIM o assente", requires: "Ogni cifra ha una fonte", limits: "Non presenta un SIM come consuntivo", verifier: "independent-reviewer" },
    { id: "writing", name: "Content Writing", input: "Brief", output: "Bozza", requires: "Vincoli e divieti", limits: "Non pubblica", verifier: "registry" },
    { id: "inspect", name: "Code Inspection", input: "Diff", output: "Note di review", requires: "Diff limitato alla task", limits: "Il reviewer non è l'autore", verifier: "independent-reviewer" },
    { id: "codegen", name: "Code Generation", input: "Task", output: "Patch proposta", requires: "Requisito e prova attesa", limits: "Non fa deploy e non tocca main", verifier: "registry" },
    { id: "testing", name: "Testing", input: "Comportamento atteso", output: "Pass, fail o non eseguito", requires: "Un caso osservabile", limits: "Un fail non diventa un pass", verifier: "independent-reviewer" },
    { id: "quality", name: "Quality Review", input: "Artefatto", output: "Pass o ritorno", requires: "Criterio scritto", limits: "Non è l'autore del pezzo", verifier: "independent-reviewer" },
    { id: "crm", name: "CRM Qualification", input: "Lead con fonte", output: "Fit o scarto", requires: "Dedup", limits: "Non inventa un cliente", verifier: "registry" },
    { id: "finance", name: "Financial Analysis", input: "Righe osservate", output: "Classe: osservato, stimato, assente", requires: "Fonte della riga", limits: "Non fonde stimato e osservato", verifier: "independent-reviewer" },
    { id: "performance", name: "Performance Analysis", input: "Esiti verificati", output: "Scostamento o assente", requires: "Base reale", limits: "Senza base il valore è unknown", verifier: "independent-reviewer" },
    { id: "optimize", name: "Workflow Optimization", input: "Attrito osservato", output: "Proposta", requires: "Misura prima", limits: "Non cambia la produzione da sola", verifier: "independent-reviewer" },
    { id: "incident", name: "Incident Diagnosis", input: "Sintomo", output: "Ipotesi e confine", requires: "Log o riproduzione", limits: "Non riavvia la produzione", verifier: "registry" },
    { id: "knowledge", name: "Knowledge Retrieval", input: "Domanda", output: "Passi citati", requires: "Indice", limits: "Non cita ciò che non c'è", verifier: "registry" },
    { id: "experiment", name: "Experiment Design", input: "Ipotesi", output: "Prova e criterio di stop", requires: "Una variabile", limits: "Non è già un'adozione", verifier: "independent-reviewer" },
    { id: "verify", name: "Independent Verification", input: "Risultato altrui", output: "Conferma o rifiuto", requires: "Autore diverso", limits: "Non allenta il gate", verifier: "independent-reviewer" },
];
export const WORKERS = [
    { id: "data", name: "Data worker", note: "Estrae e valida. Non esegue ordini." },
    { id: "research", name: "Research worker", note: "Cerca. Non pubblica e non vende." },
    { id: "writer", name: "Writer worker", note: "Scrive bozze. Non invia." },
    { id: "builder", name: "Builder worker", note: "Propone patch e test. Non fa deploy." },
    { id: "reviewer", name: "Reviewer worker", note: "Controlla un lavoro non suo." },
    { id: "router", name: "Router worker", note: "Smista. Non apre una seconda coda." },
    { id: "analyst", name: "Analyst worker", note: "Legge. Non inventa cifre." },
];
export function skillById(id) {
    return SKILLS.find((item) => item.id === id) ?? null;
}
export function workerById(id) {
    return WORKERS.find((item) => item.id === id) ?? null;
}
