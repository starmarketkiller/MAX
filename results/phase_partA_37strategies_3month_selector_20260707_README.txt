NOTE: This run used InpStrategySelector (1-37) as the swept Optimization
parameter to get true local multi-agent parallelism for the 37-strategy
screen. The OnTester CSV logger (built before InpStrategySelector existed)
does NOT record the selector value per pass, so which row corresponds to
which strategy is NOT certain from this file alone - only the completion
order gives a rough hint (selector swept 1..37 in order, distributed
across 4 local agents). Treat as raw pass data, not strategy-labeled data.
