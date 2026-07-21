// Generated adapter for contracts/settings.schema.json schema version 1.
export const SETTINGS_SCHEMA_VERSION = 1;
export const DEFAULT_SETTINGS = Object.freeze({
  RiskPercent: 1.0, MaxLot: 5.0, MaxTradesPerDay: 12, MaxConcurrent: 4,
  MaxDailyDDPct: 5.0, MinEntryScore: 50,
});

export const SETTINGS_FIELDS = [
  ["RiskPercent","Risk per trade (%)","number",0,10,0.01],
  ["MaxLot","Max lot size","number",0.01,100,0.01],
  ["MaxTradesPerDay","Max trades / day","integer",0,500,1],
  ["MaxConcurrent","Max concurrent positions","integer",0,40,1],
  ["MaxDailyDDPct","Max daily DD (%)","number",0,100,0.01],
  ["MinEntryScore","Min entry score","integer",0,100,1],
  ["ATR_SL_Mult","ATR SL multiplier","number",0.01,20,0.01],
  ["ATR_TP_Mult","ATR TP multiplier","number",0.01,50,0.01],
  ["BE_TriggerATR","BE trigger (ATR)","number",0,20,0.01],
  ["TrailActivateATR","Trail activate (ATR)","number",0,20,0.01],
  ["TrailDistanceATR","Trail distance (ATR)","number",0,20,0.01],
  ["TF_SLTP_H1","SL/TP × H1","number",0.01,20,0.01],
  ["TF_SLTP_H4","SL/TP × H4","number",0.01,20,0.01],
  ["TF_SLTP_D1","SL/TP × D1","number",0.01,20,0.01],
  ["AsianScoreMin","Asian session min score","number",0,100,0.1],
  ["LondonScoreMin","London session min score","number",0,100,0.1],
  ["OverlapScoreMin","Overlap session min score","number",0,100,0.1],
  ["NYScoreMin","NY session min score","number",0,100,0.1],
  ["AfterNYScoreMin","After-NY session min score","number",0,100,0.1],
];

export const SETTINGS_BOOLS = [
  ["UseHTFBias","HTF Bias gate"],
  ["UseVelocityGate","Velocity gate"],
  ["UseNewsFilter","News filter"],
];

export function validateSettings(values) {
  const errors = {};
  for (const [key, , type, min, max] of SETTINGS_FIELDS) {
    const value = values[key];
    if (value === "" || typeof value !== "number" || !Number.isFinite(value)) errors[key] = "Enter a finite number";
    else if (type === "integer" && !Number.isInteger(value)) errors[key] = "Enter a whole number";
    else if (value < min || value > max) errors[key] = `Allowed range: ${min}–${max}`;
  }
  return errors;
}
