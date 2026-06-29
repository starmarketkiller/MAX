// Parses <action type="..." ... /> tags embedded in Coach messages.
// Strict format: <action type="X" key1="v1" key2="v2" />  (self-closing only)
// Returns: { cleanText, actions: [{ raw, type, params }] }

const ACTION_TAG_RE = /<action\s+([^/>]+?)\/?>/gi;
const ATTR_RE = /(\w+)\s*=\s*"([^"]*)"/g;

export function parseCoachActions(text) {
  if (!text || typeof text !== "string") {
    return { cleanText: text || "", actions: [] };
  }
  const actions = [];
  let m;
  while ((m = ACTION_TAG_RE.exec(text)) !== null) {
    const attrs = {};
    let am;
    const inner = m[1];
    ATTR_RE.lastIndex = 0;
    while ((am = ATTR_RE.exec(inner)) !== null) {
      attrs[am[1]] = am[2];
    }
    if (attrs.type) {
      actions.push({
        raw: m[0],
        type: attrs.type,
        name: attrs.name,
        params: {
          ...(attrs.duration_h ? { duration_h: parseFloat(attrs.duration_h) } : {}),
          ...(attrs.duration_min ? { duration_min: parseFloat(attrs.duration_min) } : {}),
          ...(attrs.pct ? { pct: parseFloat(attrs.pct) } : {}),
        },
      });
    }
  }
  const cleanText = text.replace(ACTION_TAG_RE, "").trim();
  return { cleanText, actions };
}

// Human-friendly label for each action type
export function describeAction(action) {
  if (!action) return "";
  switch (action.type) {
    case "disable_strategy":
      return `Disabilita ${action.name || "?"}${action.params.duration_h ? ` per ${action.params.duration_h}h` : ""}`;
    case "enable_strategy":
      return `Riattiva ${action.name || "?"}`;
    case "pause_ea":
      return `Pausa EA${action.params.duration_min ? ` per ${action.params.duration_min} min` : ""}`;
    case "resume_ea":
      return "Riprendi EA";
    case "set_risk":
      return `Risk → ${action.params.pct ?? "?"}%`;
    case "reset_daily":
      return "Reset contatori giornalieri";
    default:
      return action.type;
  }
}

// Tone used for the apply button — destructive actions get a red accent
export function actionTone(action) {
  if (!action) return "neutral";
  if (["pause_ea", "disable_strategy", "set_risk"].includes(action.type)) return "warning";
  if (action.type === "reset_daily") return "warning";
  return "neutral";
}
