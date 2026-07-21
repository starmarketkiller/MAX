// Generated adapter for contracts/strategy-registry.json (schema 1).
export const STRATEGY_REGISTRY = [
  ["ADX_RSI","ADX + RSI Trend","TREND",true,true], ["BOLLINGER","Bollinger Mean Reversion","REVERSAL",true,true],
  ["MACD","MACD Trend","TREND",true,true], ["SAR","Parabolic SAR","TREND",true,true],
  ["TSI","TSI Momentum","TREND",true,true], ["BJORGUM","Bjorgum Key Levels","REVERSAL",true,true],
  ["LIQ_SWEEP","Liquidity Sweep","SMC",true,true], ["FVG_CONT","FVG Continuation","SMC",true,true],
  ["BREAKOUT_ACC","Breakout Acceptance","TREND",true,true], ["LONDON_BO","London Breakout","TREND",true,true],
  ["EMA_PULLBACK","EMA Pullback","TREND",true,true], ["BB_SQUEEZE","BB Squeeze","REVERSAL",true,true],
  ["ICHIMOKU","Ichimoku Kumo Break","TREND",true,true], ["RSI_DIV","RSI Divergence","REVERSAL",true,true],
  ["ORDER_BLOCK","Order Block Retest","SMC",true,true], ["STRUCT_REACT","Structure Reaction","SMC",true,true],
  ["TURTLE_SOUP","Turtle Soup","SMC",true,true], ["IFVG","Inverted FVG + MSS","SMC",true,true],
  ["FVG_MIT","FVG Mitigation","SMC",true,true], ["OB_MIT","OB Structural Mitigation","SMC",true,true],
  ["SH_BMS_RTO","Stop Hunt BMS RTO","SMC",true,true], ["SMS_BMS_RTO","SMS BMS RTO","SMC",true,true],
  ["SILVER_BULLET","Silver Bullet","SMC",true,true], ["AMD_REVERSAL","AMD Reversal","SMC",true,true],
  ["OTE_CONT","OTE Continuation","SMC",true,true], ["MALAYSIAN_SNR","Malaysian S/R","SMC",true,true],
  ["CISD","Change in State of Delivery","INSTITUTIONAL",true,true], ["AMD_CONT","AMD Continuation","INSTITUTIONAL",true,true],
  ["JUDAS_SWING","Judas Swing","INSTITUTIONAL",true,true], ["LDN_REVERSAL","London Reversal","INSTITUTIONAL",true,true],
  ["NY_REVERSAL","NY Reversal","INSTITUTIONAL",true,true], ["WEEKLY_EXP","Weekly Range Expansion","INSTITUTIONAL",true,true],
  ["PO3","Power of Three","INSTITUTIONAL",true,true], ["LIQ_VOID","Liquidity Void","INSTITUTIONAL",true,true],
  ["DISP_REBAL","Displacement Rebalance","INSTITUTIONAL",true,true], ["ELLIOTT","Elliott Wave","INSTITUTIONAL",true,false],
  ["RANGE_FADE","Range Fade","REVERSAL",true,true], ["THREE_BAR_DELIVERY_BREAK","Three Bar Delivery Break","INSTITUTIONAL",true,false],
  ["SCALP_EMA","Scalp EMA","RESEARCH",false,true], ["SCALP_BB_FADE","Scalp BB Fade","RESEARCH",false,true],
  ["SCALP_RSI_SNAP","Scalp RSI Snap","RESEARCH",false,true], ["SCALP_RANGE_BRK","Scalp Range Break","RESEARCH",false,true],
].map(([strategy_id, display_name, family, live_implementation, research_implementation]) => ({
  strategy_id, display_name, family, live_implementation, research_implementation,
}));

export const LIVE_STRATEGIES = STRATEGY_REGISTRY.filter((s) => s.live_implementation);
export const LIVE_STRATEGY_IDS = LIVE_STRATEGIES.map((s) => s.strategy_id);
export const LIVE_STRATEGY_COUNT = LIVE_STRATEGIES.length;
export const RESEARCH_STRATEGY_IDS = STRATEGY_REGISTRY.filter((s) => s.research_implementation).map((s) => s.strategy_id);

export function requireStrategy(strategyId) {
  const record = STRATEGY_REGISTRY.find((s) => s.strategy_id === strategyId);
  if (!record) throw new Error(`unknown strategy_id: ${strategyId}`);
  return record;
}
