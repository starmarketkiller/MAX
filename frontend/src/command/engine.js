import { stationById, stationsByDepartment } from "./stations.js";
const RANK = {
    idle: 0,
    completed: 1,
    queued: 2,
    failed: 3,
    running: 4,
    waiting: 5,
    blocked: 6,
};
function pipeline(departmentId) {
    return stationsByDepartment(departmentId).map((station) => station.id);
}
function beforeGate(departmentId) {
    const ids = [];
    for (const station of stationsByDepartment(departmentId)) {
        if (station.gate !== "none")
            break;
        ids.push(station.id);
    }
    return ids;
}
export function stopIndex(stationIds, failAt) {
    let gateAt = stationIds.length - 1;
    for (let index = 0; index < stationIds.length; index += 1) {
        const gate = stationById(stationIds[index])?.gate;
        if (gate === "nogo" || gate === "approval") {
            gateAt = index;
            break;
        }
    }
    if (!failAt)
        return gateAt;
    const failIndex = stationIds.indexOf(failAt);
    if (failIndex < 0)
        return gateAt;
    return Math.min(failIndex, gateAt);
}
export const WORLDS = [
    {
        id: "ecosystem",
        name: "Ecosistema",
        lede: "I sette reparti avanzano insieme e si fermano ognuno al proprio gate.",
        runs: [
            { id: "trading", label: "Trading", stationIds: pipeline("trading"), startAt: 0 },
            { id: "revenue", label: "Revenue", stationIds: pipeline("revenue"), startAt: 0 },
            { id: "fashion", label: "Agency", stationIds: pipeline("fashion"), startAt: 0 },
            { id: "social", label: "Social", stationIds: pipeline("social"), startAt: 0 },
            { id: "systems", label: "Systems", stationIds: pipeline("systems"), startAt: 0 },
            { id: "finance", label: "Finance", stationIds: pipeline("finance"), startAt: 0 },
            { id: "jarvis", label: "Jarvis", stationIds: pipeline("jarvis"), startAt: 0 },
            { id: "council", label: "Council", stationIds: pipeline("council"), startAt: 3 },
        ],
    },
    {
        id: "trading",
        name: "Ricerca",
        lede: "La ricerca si ferma sulla validazione indipendente. Nessun ordine.",
        runs: [{ id: "trading", label: "Trading", stationIds: pipeline("trading"), startAt: 0 }],
    },
    {
        id: "revenue",
        name: "Lead",
        lede: "Il lead resta interno. L'uscita aspetta un permesso che non c'è.",
        runs: [{ id: "revenue", label: "Revenue", stationIds: pipeline("revenue"), startAt: 0 }],
    },
    {
        id: "campaign",
        name: "Campagna",
        lede: "Agency prepara e passa a Social. La pubblicazione non parte.",
        runs: [{ id: "campaign", label: "Campagna", stationIds: [...beforeGate("fashion"), ...pipeline("social")], startAt: 0 }],
    },
    {
        id: "build",
        name: "Build",
        lede: "Systems arriva al permesso di rilascio e si ferma.",
        runs: [{ id: "systems", label: "Systems", stationIds: pipeline("systems"), startAt: 0 }],
    },
    {
        id: "fault",
        name: "Test fallito",
        lede: "Un test fallisce. Non diventa un pass e non parte un deploy.",
        runs: [{ id: "fault", label: "Fail", stationIds: pipeline("systems"), startAt: 0, failAt: "systems.unit" }],
    },
    {
        id: "finance",
        name: "Conti",
        lede: "Finance non emette un report: mancano le cifre.",
        runs: [{ id: "finance", label: "Finance", stationIds: pipeline("finance"), startAt: 0 }],
    },
    {
        id: "jarvis",
        name: "Smista",
        lede: "Jarvis classifica e si ferma dove serve un umano.",
        runs: [{ id: "jarvis", label: "Jarvis", stationIds: pipeline("jarvis"), startAt: 0 }],
    },
    {
        id: "improve",
        name: "Migliora",
        lede: "Il council osserva e propone. Non adotta da solo.",
        runs: [{ id: "council", label: "Council", stationIds: pipeline("council"), startAt: 0 }],
    },
];
export function worldById(id) {
    return WORLDS.find((item) => item.id === id) ?? WORLDS[0];
}
export function worldLength(world) {
    return Math.max(1, ...world.runs.map((run) => run.startAt + stopIndex(run.stationIds, run.failAt) + 1));
}
function place(map, id, next) {
    const current = map.get(id) ?? "idle";
    if (RANK[next] >= RANK[current])
        map.set(id, next);
}
export function frameAt(world, beat) {
    const safeBeat = Math.max(0, beat);
    const states = new Map();
    const active = [];
    for (const run of world.runs) {
        const local = safeBeat - run.startAt;
        const stop = stopIndex(run.stationIds, run.failAt);
        if (local < 0) {
            for (const id of run.stationIds)
                place(states, id, "queued");
            continue;
        }
        const cursor = Math.min(local, stop);
        const stuck = local >= stop;
        run.stationIds.forEach((id, index) => {
            if (index < cursor)
                place(states, id, "completed");
            else if (index > cursor)
                place(states, id, "queued");
        });
        const currentId = run.stationIds[cursor];
        const station = stationById(currentId);
        let state = "running";
        if (stuck && run.failAt === currentId)
            state = "failed";
        else if (stuck && station?.gate === "nogo")
            state = "blocked";
        else if (stuck && station?.gate === "approval")
            state = "waiting";
        else if (stuck)
            state = "completed";
        place(states, currentId, state);
        active.push({ runId: run.id, stationId: currentId, state });
    }
    return { states, active };
}
export function eventsAt(world, beat) {
    const events = [];
    for (const run of world.runs) {
        const local = beat - run.startAt;
        const stop = stopIndex(run.stationIds, run.failAt);
        if (local < 0 || local > stop)
            continue;
        const to = run.stationIds[local];
        const from = local === 0 ? null : run.stationIds[local - 1];
        const station = stationById(to);
        const type = run.failAt === to ? "fail" : station && station.gate !== "none" && local === stop ? "gate" : local === 0 ? "start" : "handoff";
        events.push({
            beat,
            runId: run.id,
            from,
            to,
            type,
            provenance: `${world.id}:${run.id}:${beat}`,
        });
    }
    return events;
}
export function stationState(states, station) {
    return states.get(station.id) ?? "idle";
}
